import os
from datetime import datetime
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Connect to MongoDB
try:
    # First try the configured connection
    uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/')
    client = MongoClient(uri)
    # Test the connection
    client.admin.command('ping')
    print("Connected to MongoDB successfully")
except Exception as e:
    print(f"Could not connect to MongoDB: {e}")
    print("Using local MongoDB")
    client = MongoClient('mongodb://localhost:27017/')

db = client['team_formation_app']

# Clear existing collections
db.users.drop()
db.teams.drop()
db.requests.drop()

# Create sample users
users = [
    # CS Cluster
    {
        'usn': '1RV21CS001',
        'password': generate_password_hash('password'),
        'name': 'Aditya Sharma',
        'branch': 'CS',
        'cluster': 'CS',
        'phone': '9876543201',
        'team_id': None,
        'is_team_leader': False,
        'registered_at': datetime.now()
    },
    {
        'usn': '1RV21IS002',
        'password': generate_password_hash('password'),
        'name': 'Bhavana Patel',
        'branch': 'IS',
        'cluster': 'CS',
        'phone': '9876543202',
        'team_id': None,
        'is_team_leader': False,
        'registered_at': datetime.now()
    },
    {
        'usn': '1RV21CS003',
        'password': generate_password_hash('password'),
        'name': 'Chetan Kumar',
        'branch': 'CS',
        'cluster': 'CS',
        'phone': '9876543203',
        'team_id': None,
        'is_team_leader': False,
        'registered_at': datetime.now()
    },
    {
        'usn': '1RV21AI004',
        'password': generate_password_hash('password'),
        'name': 'Deepika Reddy',
        'branch': 'AI',
        'cluster': 'CS',
        'phone': '9876543204',
        'team_id': None,
        'is_team_leader': False,
        'registered_at': datetime.now()
    },
    
    # EC Cluster
    {
        'usn': '1RV21EC005',
        'password': generate_password_hash('password'),
        'name': 'Esha Singh',
        'branch': 'EC',
        'cluster': 'EC',
        'phone': '9876543205',
        'team_id': None,
        'is_team_leader': False,
        'registered_at': datetime.now()
    },
    {
        'usn': '1RV21EE006',
        'password': generate_password_hash('password'),
        'name': 'Farhan Khan',
        'branch': 'EE',
        'cluster': 'EC',
        'phone': '9876543206',
        'team_id': None,
        'is_team_leader': False,
        'registered_at': datetime.now()
    },
    {
        'usn': '1RV21EC007',
        'password': generate_password_hash('password'),
        'name': 'Gayatri Mohan',
        'branch': 'EC',
        'cluster': 'EC',
        'phone': '9876543207',
        'team_id': None,
        'is_team_leader': False,
        'registered_at': datetime.now()
    },
    {
        'usn': '1RV21EI008',
        'password': generate_password_hash('password'),
        'name': 'Harish Kumar',
        'branch': 'EI',
        'cluster': 'EC',
        'phone': '9876543208',
        'team_id': None,
        'is_team_leader': False,
        'registered_at': datetime.now()
    },
    
    # ME Cluster
    {
        'usn': '1RV21ME009',
        'password': generate_password_hash('password'),
        'name': 'Ishaan Mehta',
        'branch': 'ME',
        'cluster': 'ME',
        'phone': '9876543209',
        'team_id': None,
        'is_team_leader': False,
        'registered_at': datetime.now()
    },
    {
        'usn': '1RV21CH010',
        'password': generate_password_hash('password'),
        'name': 'Juhi Patel',
        'branch': 'CH',
        'cluster': 'ME',
        'phone': '9876543210',
        'team_id': None,
        'is_team_leader': False,
        'registered_at': datetime.now()
    },
    {
        'usn': '1RV21ME011',
        'password': generate_password_hash('password'),
        'name': 'Karan Malhotra',
        'branch': 'ME',
        'cluster': 'ME',
        'phone': '9876543211',
        'team_id': None,
        'is_team_leader': False,
        'registered_at': datetime.now()
    },
    {
        'usn': '1RV21BT012',
        'password': generate_password_hash('password'),
        'name': 'Lakshmi Rao',
        'branch': 'BT',
        'cluster': 'ME',
        'phone': '9876543212',
        'team_id': None,
        'is_team_leader': False,
        'registered_at': datetime.now()
    }
]

result = db.users.insert_many(users)
print(f"Inserted {len(result.inserted_ids)} users")

print("Sample data inserted successfully")
print("All users have password: 'password'")
print("USNs range from 1RV21CS001 to 1RV21BT012") 