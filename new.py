# File structure:
# team_formation_app/
#   ├── app.py
#   ├── requirements.txt
#   ├── templates/
#   │   ├── base.html
#   │   ├── index.html
#   │   ├── login.html
#   │   ├── register.html
#   │   ├── dashboard.html
#   │   └── team_management.html
#   └── static/
#       └── styles.css

# app.py
import os
import re
import certifi
import secrets
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from pymongo import MongoClient
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# MongoDB Configuration
uri = "mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority&ssl=true"
client = MongoClient(uri, tlsCAFile=certifi.where())
db = client['team_formation_app']

# Helper Functions
def normalize_skills(skills_str):
    """Normalize and clean skills input."""
    return [skill.strip().lower() for skill in skills_str.split(',') if skill.strip()]

def calculate_skill_match(skills1, skills2):
    """Calculate skill match percentage between two users."""
    skills1 = set(skills1)
    skills2 = set(skills2)
    match_percentage = len(skills1.intersection(skills2)) / len(skills1.union(skills2)) * 100
    return match_percentage

# Routes
@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')
        skills = normalize_skills(request.form.get('skills'))
        contact = request.form.get('contact')
        
        if db.users.find_one({'username': username}):
            flash('Username already exists. Please choose another.', 'danger')
            return redirect(url_for('register'))
        
        user_data = {
            'username': username,
            'password': generate_password_hash(password),
            'name': name,
            'skills': skills,
            'contact': contact,
            'team_id': None,
            'is_team_leader': False,
            'available_for_team': True,
            'registered_at': datetime.now()
        }
        db.users.insert_one(user_data)
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        user = db.users.find_one({'username': username})
        
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            session['user_id'] = str(user['_id'])
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'danger')
    
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    current_user = db.users.find_one({'username': session['username']})
    
    # Find potential team matches
    potential_matches = []
    all_users = list(db.users.find({
        'username': {'$ne': session['username']},
        'team_id': None,
        'available_for_team': True
    }))
    
    for user in all_users:
        match_percentage = calculate_skill_match(current_user['skills'], user['skills'])
        if match_percentage > 50:
            potential_matches.append({
                'user': user,
                'match_percentage': match_percentage
            })
    
    # Sort matches by skill match percentage
    potential_matches.sort(key=lambda x: x['match_percentage'], reverse=True)
    
    return render_template('dashboard.html', 
                           user=current_user, 
                           potential_matches=potential_matches)

@app.route('/create_team', methods=['POST'])
def create_team():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    team_name = request.form.get('team_name')
    team_data = {
        'name': team_name,
        'leader_username': session['username'],
        'members': [session['username']],
        'created_at': datetime.now()
    }
    
    team_id = db.teams.insert_one(team_data).inserted_id
    
    # Update user as team leader and add team_id
    db.users.update_one(
        {'username': session['username']}, 
        {'$set': {'team_id': str(team_id), 'is_team_leader': True, 'available_for_team': False}}
    )
    
    flash('Team created successfully!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/send_team_request', methods=['POST'])
def send_team_request():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    target_username = request.form.get('target_username')
    current_user = db.users.find_one({'username': session['username']})
    
    request_data = {
        'from_username': session['username'],
        'to_username': target_username,
        'type': 'team_join',
        'status': 'pending',
        'created_at': datetime.now()
    }
    
    db.requests.insert_one(request_data)
    flash('Team join request sent!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/manage_requests')
def manage_requests():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    # Get team requests for the current user
    team_requests = list(db.requests.find({
        'to_username': session['username'],
        'status': 'pending',
        'type': 'team_join'
    }))
    
    return render_template('team_management.html', requests=team_requests)

@app.route('/process_request', methods=['POST'])
def process_request():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    request_id = request.form.get('request_id')
    action = request.form.get('action')
    
    request_obj = db.requests.find_one({'_id': ObjectId(request_id)})
    
    if action == 'accept':
        # Add user to team
        db.users.update_one(
            {'username': request_obj['from_username']},
            {'$set': {'team_id': request_obj['team_id'], 'available_for_team': False}}
        )
        
        # Update team members
        db.teams.update_one(
            {'_id': ObjectId(request_obj['team_id'])},
            {'$push': {'members': request_obj['from_username']}}
        )
    
    # Update request status
    db.requests.update_one(
        {'_id': ObjectId(request_id)},
        {'$set': {'status': 'processed'}}
    )
    
    flash(f'Request {action}ed successfully!', 'success')
    return redirect(url_for('manage_requests'))

@app.route('/recommend_teams')
def recommend_teams():
    if 'username' not in session:
        return redirect(url_for('login'))
    
    current_user = db.users.find_one({'username': session['username']})
    
    # Find teams with similar skill sets
    recommended_teams = []
    teams = list(db.teams.find())
    
    for team in teams:
        team_skills = set()
        for member_username in team['members']:
            member = db.users.find_one({'username': member_username})
            team_skills.update(member['skills'])
        
        match_percentage = calculate_skill_match(current_user['skills'], list(team_skills))
        
        if match_percentage > 50:
            recommended_teams.append({
                'team': team,
                'match_percentage': match_percentage
            })
    
    # Sort recommended teams by skill match percentage
    recommended_teams.sort(key=lambda x: x['match_percentage'], reverse=True)
    
    return render_template('recommended_teams.html', recommended_teams=recommended_teams)

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

# Deployment Configuration
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)