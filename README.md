# Interdisciplinary Project Team Formation

A Flask web application to help students form teams for interdisciplinary projects according to specific university requirements.

![Team Formation App](https://i.imgur.com/RHJ6sLw.png)

## Features

- Modern, responsive UI with Bootstrap 5
- User registration with branch/cluster identification
- Team creation and management
- Automatic team composition validation (2 CS, 2 EC, 1+ ME students)
- Team join requests
- Team merge functionality
- Team listing with filtering options
- Team leader management
- Visual progress tracking for team completion

## Project Requirements

- Teams must have 5-6 students total
- Team composition requirements:
  - 2 students from CS cluster (AI, CS, IS, CD, CY)
  - 2 students from EC cluster (EC, EE, EI, ET)
  - At least 1 student from ME cluster (AS, BT, CH, IM, ME)
- Students cannot form teams within the same cluster

## Technical Requirements

- Python 3.8+
- MongoDB (local instance or Atlas)
- Web browser with JavaScript enabled

## Installation

1. Clone the repository:
```
git clone <repository-url>
cd team_finder
```

2. Install dependencies:
```
pip install -r requirements.txt
```

3. Configure MongoDB:
   - Create a `.env` file based on `.env.example`
   - Add your MongoDB URI or use the local MongoDB instance

## Database Setup

The application can connect to:
1. MongoDB Atlas (cloud)
2. Local MongoDB instance
3. In-memory MongoDB (for development)

To initialize the database with sample data:
```
python init_db.py
```

This creates sample users from all clusters with the following credentials:
- CS Cluster: 1RV21CS001 (password: password)
- EC Cluster: 1RV21EC005 (password: password)
- ME Cluster: 1RV21ME009 (password: password)

## Running the Application

```
python app.py
```

The application will be available at `http://localhost:5000`.

## Usage Guide

1. **Registration**: Register with your USN, name, branch and contact information
2. **Create a Team**: Create your own team or browse available teams to join
3. **Find Members**: Send join requests to teams that need members from your cluster
4. **Team Management**: Team leaders can accept/reject join requests
5. **Team Merging**: Teams can merge to meet composition requirements

## UI Improvements

- Modern card-based design
- Responsive layout works on mobile devices
- Interactive filtering for team lists
- Visual progress tracking
- Color-coded cluster identification
- Improved form validation
- Team completion visualization

## Screenshots

- Login Page: [View Screenshot](#)
- Dashboard: [View Screenshot](#)
- Team List: [View Screenshot](#)
- Registration: [View Screenshot](#) 