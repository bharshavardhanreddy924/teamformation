import os
import re
import certifi
import secrets
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError
from bson.objectid import ObjectId
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# MongoDB Configuration
try:
    # First try the Atlas connection
    uri = "mongodb+srv://bharshavardhanreddy924:516474Ta@data-dine.5oghq.mongodb.net/?retryWrites=true&w=majority&ssl=true"
    client = MongoClient(uri, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000)
    # Test the connection
    client.admin.command('ping')
    print("Connected to MongoDB Atlas successfully")
except (ConnectionFailure, ConfigurationError) as e:
    print(f"Could not connect to MongoDB Atlas: {e}")
    print("Trying local MongoDB instance...")
    try:
        # Fallback to local MongoDB
        client = MongoClient('mongodb://localhost:27017/', serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print("Connected to local MongoDB successfully")
    except Exception as e:
        print(f"Could not connect to local MongoDB: {e}")
        print("Using in-memory MongoDB for development")
        # This is a last resort - in a real app you'd handle this differently
        from pymongo_inmemory import MongoClient
        client = MongoClient()

db = client['team_formation_app']

# Constants for clusters
CS_CLUSTER = ['AI', 'CS', 'IS', 'CD', 'CY']
EC_CLUSTER = ['EC', 'EE', 'EI', 'ET']
ME_CLUSTER = ['AS', 'BT', 'CH', 'IM', 'ME']
ALL_CLUSTERS = {'CS': CS_CLUSTER, 'EC': EC_CLUSTER, 'ME': ME_CLUSTER}

# Helper Functions
def get_cluster(branch):
    """Determine which cluster a branch belongs to."""
    for cluster_name, branches in ALL_CLUSTERS.items():
        if branch in branches:
            return cluster_name
    return None

def validate_team_composition(team_members):
    """Check if team meets the required composition."""
    cluster_counts = {'CS': 0, 'EC': 0, 'ME': 0}
    
    for member in team_members:
        user = db.users.find_one({'_id': ObjectId(member)})
        if user:
            cluster = user['cluster']
            cluster_counts[cluster] += 1
    
    # Check requirements: 2 CS, 2 EC, at least 1 ME, total 5-6 students
    return (cluster_counts['CS'] == 2 and 
            cluster_counts['EC'] == 2 and 
            cluster_counts['ME'] >= 1 and 
            5 <= sum(cluster_counts.values()) <= 6)

def get_team_stats(team_id):
    """Get statistics about team composition."""
    team = db.teams.find_one({'_id': ObjectId(team_id)})
    if not team:
        return None
    
    stats = {'CS': 0, 'EC': 0, 'ME': 0, 'total': 0}
    
    for member_id in team['member_ids']:
        user = db.users.find_one({'_id': ObjectId(member_id)})
        if user:
            stats[user['cluster']] += 1
            stats['total'] += 1
    
    stats['needs'] = {
        'CS': max(0, 2 - stats['CS']),
        'EC': max(0, 2 - stats['EC']),
        'ME': max(0, 1 - stats['ME'])
    }
    
    stats['can_accept_more'] = stats['total'] < 6
    stats['is_complete'] = (stats['CS'] == 2 and stats['EC'] == 2 and 
                           stats['ME'] >= 1 and stats['total'] >= 5)
                           
    return stats

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        usn = request.form.get('usn')
        password = request.form.get('password')
        name = request.form.get('name')
        branch = request.form.get('branch')
        phone = request.form.get('phone')
        
        # Validate USN format (e.g., "1RV21CS001")
        if not re.match(r'^\d{1}RV\d{2}[A-Z]{2}\d{3}$', usn):
            flash('Invalid USN format', 'danger')
            return redirect(url_for('register'))
        
        if db.users.find_one({'usn': usn}):
            flash('USN already registered', 'danger')
            return redirect(url_for('register'))
        
        # Determine cluster from branch
        cluster = get_cluster(branch)
        if not cluster:
            flash('Invalid branch selected', 'danger')
            return redirect(url_for('register'))
        
        user_data = {
            'usn': usn,
            'password': generate_password_hash(password),
            'name': name,
            'branch': branch,
            'cluster': cluster,
            'phone': phone,
            'team_id': None,
            'is_team_leader': False,
            'registered_at': datetime.now()
        }
        
        db.users.insert_one(user_data)
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html', 
                          cs_branches=CS_CLUSTER,
                          ec_branches=EC_CLUSTER,
                          me_branches=ME_CLUSTER)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        usn = request.form.get('usn')
        password = request.form.get('password')
        
        user = db.users.find_one({'usn': usn})
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = str(user['_id'])
            session['usn'] = usn
            session['name'] = user['name']
            session['cluster'] = user['cluster']
            
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid USN or password', 'danger')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.users.find_one({'_id': ObjectId(user_id)})
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    team = None
    team_stats = None
    pending_invitations = []
    
    if user['team_id']:
        team = db.teams.find_one({'_id': ObjectId(user['team_id'])})
        team_stats = get_team_stats(user['team_id'])
        
        # Get team members
        if team:
            team_members = []
            for member_id in team['member_ids']:
                member = db.users.find_one({'_id': ObjectId(member_id)})
                if member:
                    team_members.append({
                        'name': member['name'],
                        'usn': member['usn'],
                        'branch': member['branch'],
                        'cluster': member['cluster'],
                        'phone': member['phone'] if member['is_team_leader'] else None,
                        'is_leader': member['is_team_leader']
                    })
            team['members'] = team_members
    else:
        # Find pending invitations for users without teams
        invitations = list(db.requests.find({
            'to_user_id': ObjectId(user_id),
            'type': 'team_invitation',
            'status': 'pending'
        }))
        
        for invitation in invitations:
            team = db.teams.find_one({'_id': invitation['from_team_id']})
            if team:
                leader = db.users.find_one({'_id': team['leader_id']})
                if leader:
                    pending_invitations.append({
                        '_id': str(invitation['_id']),
                        'team_name': team['name'],
                        'leader_name': leader['name'],
                        'leader_phone': leader['phone']
                    })
    
    # Get pending requests
    pending_requests = list(db.requests.find({
        'to_team_id': user['team_id'] if user['team_id'] and user['is_team_leader'] else None,
        'status': 'pending'
    }))
    
    # Find available teams for users without a team
    available_teams = []
    
    if not user['team_id']:
        teams = list(db.teams.find())
        
        for team_item in teams:
            stats = get_team_stats(team_item['_id'])
            
            # Check if this team needs members from this cluster
            needs_cluster = stats['needs'].get(user['cluster'], 0) > 0
            
            if needs_cluster and stats['can_accept_more']:
                leader = db.users.find_one({'_id': team_item['leader_id']})
                available_teams.append({
                    'id': str(team_item['_id']),
                    'name': team_item['name'],
                    'stats': stats,
                    'leader': {
                        'name': leader['name'],
                        'usn': leader['usn'],
                        'phone': leader['phone']
                    }
                })
    
    # Find mergeable teams for team leaders
    mergeable_teams = []
    
    if user['team_id'] and user['is_team_leader'] and team_stats:
        current_team = team_stats
        teams = list(db.teams.find({'_id': {'$ne': ObjectId(user['team_id'])}}))
        
        for team_item in teams:
            other_stats = get_team_stats(team_item['_id'])
            
            # Check if the combined team would meet requirements or get closer
            # This is a simplified check; actual logic would be more complex
            can_merge = (current_team['total'] + other_stats['total'] <= 6 and
                        not (current_team['CS'] + other_stats['CS'] > 2 or
                            current_team['EC'] + other_stats['EC'] > 2 or
                            current_team['ME'] + other_stats['ME'] > 3))
            
            if can_merge:
                leader = db.users.find_one({'_id': ObjectId(team_item['leader_id'])})
                mergeable_teams.append({
                    'id': str(team_item['_id']),
                    'name': team_item['name'],
                    'stats': other_stats,
                    'leader': {
                        'name': leader['name'],
                        'usn': leader['usn'],
                        'phone': leader['phone']
                    }
                })
    
    return render_template('dashboard.html',
                          user=user,
                          team=team,
                          team_stats=team_stats,
                          pending_requests=pending_requests,
                          pending_invitations=pending_invitations, 
                          available_teams=available_teams,
                          mergeable_teams=mergeable_teams)

@app.route('/create_team', methods=['POST'])
def create_team():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.users.find_one({'_id': ObjectId(user_id)})
    
    if user['team_id']:
        flash('You are already part of a team', 'warning')
        return redirect(url_for('dashboard'))
    
    team_name = request.form.get('team_name')
    
    team_data = {
        'name': team_name,
        'leader_id': ObjectId(user_id),
        'member_ids': [ObjectId(user_id)],
        'created_at': datetime.now()
    }
    
    team_id = db.teams.insert_one(team_data).inserted_id
    
    # Update user as team leader
    db.users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {'team_id': team_id, 'is_team_leader': True}}
    )
    
    flash('Team created successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/send_join_request', methods=['POST'])
def send_join_request():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    team_id = request.form.get('team_id')
    
    user = db.users.find_one({'_id': ObjectId(user_id)})
    team = db.teams.find_one({'_id': ObjectId(team_id)})
    
    if not team:
        flash('Team not found', 'danger')
        return redirect(url_for('dashboard'))
    
    if user['team_id']:
        flash('You are already part of a team', 'warning')
        return redirect(url_for('dashboard'))
    
    # Check if there's already a pending request
    existing_request = db.requests.find_one({
        'from_user_id': ObjectId(user_id),
        'to_team_id': ObjectId(team_id),
        'status': 'pending',
        'type': 'user_join'
    })
    
    if existing_request:
        flash('You already have a pending request to this team', 'warning')
        return redirect(url_for('dashboard'))
    
    # Check if the team needs a member from user's cluster
    team_stats = get_team_stats(team_id)
    if team_stats['needs'][user['cluster']] <= 0:
        flash(f'This team already has enough members from {user["cluster"]} cluster', 'warning')
        return redirect(url_for('dashboard'))
    
    if not team_stats['can_accept_more']:
        flash('This team is already full', 'warning')
        return redirect(url_for('dashboard'))
    
    request_data = {
        'from_user_id': ObjectId(user_id),
        'to_team_id': ObjectId(team_id),
        'type': 'user_join',
        'status': 'pending',
        'created_at': datetime.now()
    }
    
    db.requests.insert_one(request_data)
    flash('Join request sent!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/send_merge_request', methods=['POST'])
def send_merge_request():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    target_team_id = request.form.get('team_id')
    
    user = db.users.find_one({'_id': ObjectId(user_id)})
    
    if not user['team_id'] or not user['is_team_leader']:
        flash('You must be a team leader to request a merge', 'warning')
        return redirect(url_for('dashboard'))
    
    # Check if there's already a pending request
    existing_request = db.requests.find_one({
        'from_team_id': ObjectId(user['team_id']),
        'to_team_id': ObjectId(target_team_id),
        'status': 'pending',
        'type': 'team_merge'
    })
    
    if existing_request:
        flash('Your team already has a pending merge request with this team', 'warning')
        return redirect(url_for('dashboard'))
    
    request_data = {
        'from_user_id': ObjectId(user_id),
        'from_team_id': ObjectId(user['team_id']),
        'to_team_id': ObjectId(target_team_id),
        'type': 'team_merge',
        'status': 'pending',
        'created_at': datetime.now()
    }
    
    db.requests.insert_one(request_data)
    flash('Team merge request sent!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/process_request', methods=['POST'])
def process_request():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    request_id = request.form.get('request_id')
    action = request.form.get('action')
    
    user = db.users.find_one({'_id': ObjectId(user_id)})
    request_obj = db.requests.find_one({'_id': ObjectId(request_id)})
    
    if not request_obj:
        flash('Request not found', 'danger')
        return redirect(url_for('dashboard'))
    
    if not user['is_team_leader'] or str(user['team_id']) != str(request_obj['to_team_id']):
        flash('You are not authorized to process this request', 'danger')
        return redirect(url_for('dashboard'))
    
    if action == 'accept':
        if request_obj['type'] == 'user_join':
            # Add user to team
            requestor = db.users.find_one({'_id': request_obj['from_user_id']})
            
            # Verify team can still accept this member
            team_stats = get_team_stats(user['team_id'])
            if team_stats['needs'][requestor['cluster']] <= 0 or not team_stats['can_accept_more']:
                flash('Your team composition has changed and can no longer accept this member', 'warning')
                db.requests.update_one(
                    {'_id': ObjectId(request_id)},
                    {'$set': {'status': 'rejected'}}
                )
                return redirect(url_for('dashboard'))
            
            db.users.update_one(
                {'_id': request_obj['from_user_id']},
                {'$set': {'team_id': user['team_id']}}
            )
            
            # Update team members
            db.teams.update_one(
                {'_id': user['team_id']},
                {'$push': {'member_ids': request_obj['from_user_id']}}
            )
            
            flash('User added to team!', 'success')
            
        elif request_obj['type'] == 'team_merge':
            # Merge teams
            from_team = db.teams.find_one({'_id': request_obj['from_team_id']})
            to_team = db.teams.find_one({'_id': request_obj['to_team_id']})
            
            # Verify combined team meets requirements
            combined_members = []
            combined_members.extend(from_team['member_ids'])
            combined_members.extend(to_team['member_ids'])
            
            if len(combined_members) > 6:
                flash('Combined team would exceed maximum size of 6 members', 'warning')
                db.requests.update_one(
                    {'_id': ObjectId(request_id)},
                    {'$set': {'status': 'rejected'}}
                )
                return redirect(url_for('dashboard'))
            
            # Update all members of the from_team
            for member_id in from_team['member_ids']:
                db.users.update_one(
                    {'_id': member_id},
                    {'$set': {'team_id': to_team['_id'], 'is_team_leader': False}}
                )
            
            # Keep the original leader of the to_team
            
            # Add members to the to_team
            db.teams.update_one(
                {'_id': to_team['_id']},
                {'$push': {'member_ids': {'$each': from_team['member_ids']}}}
            )
            
            # Delete the from_team
            db.teams.delete_one({'_id': from_team['_id']})
            
            flash('Teams merged successfully!', 'success')
    
    # Update request status
    db.requests.update_one(
        {'_id': ObjectId(request_id)},
        {'$set': {'status': action}}
    )
    
    return redirect(url_for('dashboard'))

@app.route('/team_list')
def team_list():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.users.find_one({'_id': ObjectId(user_id)})
    
    teams = list(db.teams.find())
    team_details = []
    
    for team in teams:
        stats = get_team_stats(team['_id'])
        leader = db.users.find_one({'_id': team['leader_id']})
        
        # Only show teams that aren't complete yet
        if not stats['is_complete']:
            team_details.append({
                'id': str(team['_id']),
                'name': team['name'],
                'members': stats['total'],
                'cs_count': stats['CS'],
                'ec_count': stats['EC'],
                'me_count': stats['ME'],
                'needs': stats['needs'],
                'leader_name': leader['name'],
                'leader_usn': leader['usn'],
                'leader_phone': leader['phone'],
                'can_join': not user['team_id'] and stats['needs'][user['cluster']] > 0 and stats['can_accept_more'],
                'can_merge': user['team_id'] and user['is_team_leader'] and team['_id'] != user['team_id']
            })
    
    return render_template('team_list.html', teams=team_details, user=user)

@app.route('/leave_team', methods=['POST'])
def leave_team():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.users.find_one({'_id': ObjectId(user_id)})
    
    if not user['team_id']:
        flash('You are not part of a team', 'warning')
        return redirect(url_for('dashboard'))
    
    team = db.teams.find_one({'_id': user['team_id']})
    
    if user['is_team_leader']:
        # If leader is leaving, assign a new leader or disband the team
        if len(team['member_ids']) > 1:
            # Find a new leader among remaining members
            new_leader_id = next((id for id in team['member_ids'] if str(id) != user_id), None)
            
            if new_leader_id:
                # Update new leader
                db.users.update_one(
                    {'_id': new_leader_id},
                    {'$set': {'is_team_leader': True}}
                )
                
                # Update team
                db.teams.update_one(
                    {'_id': team['_id']},
                    {'$set': {'leader_id': new_leader_id},
                     '$pull': {'member_ids': ObjectId(user_id)}}
                )
                
                flash('You have left the team. A new leader has been assigned.', 'success')
            else:
                # This should not happen but handle just in case
                db.teams.delete_one({'_id': team['_id']})
                flash('You have left the team. The team has been disbanded.', 'success')
        else:
            # Leader is the only member, disband the team
            db.teams.delete_one({'_id': team['_id']})
            flash('You have left the team. The team has been disbanded.', 'success')
    else:
        # Regular member leaving
        db.teams.update_one(
            {'_id': team['_id']},
            {'$pull': {'member_ids': ObjectId(user_id)}}
        )
        flash('You have left the team', 'success')
    
    # Update user
    db.users.update_one(
        {'_id': ObjectId(user_id)},
        {'$set': {'team_id': None, 'is_team_leader': False}}
    )
    
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/available_members')
def available_members():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.users.find_one({'_id': ObjectId(user_id)})
    
    # Only team leaders can access this page
    if not user['team_id'] or not user['is_team_leader']:
        flash('Only team leaders can access this page', 'warning')
        return redirect(url_for('dashboard'))
    
    # Get current team info to calculate best matches
    team = db.teams.find_one({'_id': user['team_id']})
    team_stats = get_team_stats(user['team_id'])
    
    # Find available members that would fit the team requirements
    available_members = []
    
    # Query users who are not in teams and are available
    users_query = {
        '_id': {'$nin': team['member_ids']},
        'team_id': None,
    }
    
    # Prioritize users from clusters the team needs
    all_users = list(db.users.find(users_query))
    
    # Calculate team skills to find skills match
    team_skills = set()
    for member_id in team['member_ids']:
        member = db.users.find_one({'_id': ObjectId(member_id)})
        if member and 'skills' in member:
            team_skills.update(member.get('skills', []))
    
    for potential_member in all_users:
        # Calculate match percentage with team skills
        user_skills = set(potential_member.get('skills', []))
        if team_skills and user_skills:
            skill_intersection = team_skills.intersection(user_skills)
            skill_union = team_skills.union(user_skills)
            if skill_union:
                match_percentage = len(skill_intersection) / len(skill_union) * 100
            else:
                match_percentage = 0
        else:
            match_percentage = 0
        
        # Check if this user's cluster is needed
        cluster_needed = team_stats['needs'].get(potential_member['cluster'], 0) > 0
        
        available_members.append({
            '_id': str(potential_member['_id']),
            'name': potential_member['name'],
            'usn': potential_member['usn'],
            'cluster': potential_member['cluster'],
            'skills': potential_member.get('skills', []),
            'phone': potential_member['phone'],
            'match_percentage': match_percentage,
            'cluster_needed': cluster_needed
        })
    
    # Sort by: 1. cluster needed, 2. match percentage
    available_members.sort(key=lambda x: (-1 if x['cluster_needed'] else 0, -x['match_percentage']))
    
    return render_template('available_members.html', available_members=available_members, user=user, team_stats=team_stats)

@app.route('/send_invitation', methods=['POST'])
def send_invitation():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.users.find_one({'_id': ObjectId(user_id)})
    
    # Only team leaders can send invitations
    if not user['team_id'] or not user['is_team_leader']:
        flash('Only team leaders can send invitations', 'warning')
        return redirect(url_for('dashboard'))
    
    member_id = request.form.get('member_id')
    if not member_id:
        flash('Invalid request', 'danger')
        return redirect(url_for('available_members'))
    
    team = db.teams.find_one({'_id': user['team_id']})
    if not team:
        flash('Team not found', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if team is already full
    team_stats = get_team_stats(user['team_id'])
    if team_stats['total'] >= 6:
        flash('Your team is already full', 'warning')
        return redirect(url_for('available_members'))
    
    # Check if request already exists
    existing_request = db.requests.find_one({
        'from_team_id': user['team_id'],
        'to_user_id': ObjectId(member_id),
        'status': 'pending'
    })
    
    if existing_request:
        flash('You have already sent an invitation to this user', 'info')
        return redirect(url_for('available_members'))
    
    # Create the invitation
    invitation = {
        'type': 'team_invitation',
        'from_team_id': user['team_id'],
        'from_user_id': ObjectId(user_id),
        'to_user_id': ObjectId(member_id),
        'team_name': team['name'],
        'status': 'pending',
        'created_at': datetime.now()
    }
    
    db.requests.insert_one(invitation)
    flash('Invitation sent successfully', 'success')
    return redirect(url_for('available_members'))

@app.route('/process_invitation', methods=['POST'])
def process_invitation():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = db.users.find_one({'_id': ObjectId(user_id)})
    
    # Users who are already in a team can't accept invitations
    if user['team_id']:
        flash('You are already in a team', 'warning')
        return redirect(url_for('dashboard'))
    
    invitation_id = request.form.get('invitation_id')
    action = request.form.get('action')
    
    if not invitation_id or action not in ['accept', 'reject']:
        flash('Invalid request', 'danger')
        return redirect(url_for('dashboard'))
    
    invitation = db.requests.find_one({
        '_id': ObjectId(invitation_id),
        'to_user_id': ObjectId(user_id),
        'status': 'pending',
        'type': 'team_invitation'
    })
    
    if not invitation:
        flash('Invitation not found', 'danger')
        return redirect(url_for('dashboard'))
    
    if action == 'accept':
        # Check if the team still exists
        team = db.teams.find_one({'_id': invitation['from_team_id']})
        if not team:
            flash('The team no longer exists', 'warning')
            db.requests.update_one(
                {'_id': ObjectId(invitation_id)},
                {'$set': {'status': 'rejected'}}
            )
            return redirect(url_for('dashboard'))
        
        # Check if the team is already full
        team_stats = get_team_stats(invitation['from_team_id'])
        if team_stats['total'] >= 6:
            flash('The team is already full', 'warning')
            db.requests.update_one(
                {'_id': ObjectId(invitation_id)},
                {'$set': {'status': 'rejected'}}
            )
            return redirect(url_for('dashboard'))
        
        # Check if the user's cluster would exceed the limits
        user_cluster_count = team_stats[user['cluster']]
        if (user['cluster'] == 'CS' and user_cluster_count >= 2) or \
           (user['cluster'] == 'EC' and user_cluster_count >= 2) or \
           (user['cluster'] == 'ME' and user_cluster_count >= 3):
            flash(f'The team already has the maximum number of {user["cluster"]} members', 'warning')
            db.requests.update_one(
                {'_id': ObjectId(invitation_id)},
                {'$set': {'status': 'rejected'}}
            )
            return redirect(url_for('dashboard'))
        
        # Add user to the team
        db.teams.update_one(
            {'_id': invitation['from_team_id']},
            {'$push': {'member_ids': ObjectId(user_id)}}
        )
        
        # Update user
        db.users.update_one(
            {'_id': ObjectId(user_id)},
            {'$set': {'team_id': invitation['from_team_id'], 'is_team_leader': False}}
        )
        
        flash('You have joined the team!', 'success')
    else:
        flash('You have declined the invitation', 'info')
    
    # Update invitation status
    db.requests.update_one(
        {'_id': ObjectId(invitation_id)},
        {'$set': {'status': action}}
    )
    
    # Reject all other pending invitations
    if action == 'accept':
        db.requests.update_many(
            {
                'to_user_id': ObjectId(user_id),
                'status': 'pending',
                'type': 'team_invitation',
                '_id': {'$ne': ObjectId(invitation_id)}
            },
            {'$set': {'status': 'rejected'}}
        )
    
    return redirect(url_for('dashboard'))
    
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
