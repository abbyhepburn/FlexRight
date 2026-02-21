import os
import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# Part 1: Setup and Security Config
# Load private credentials to prevent them out of the soruce code (.env file)
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

def get_db_connection():
    # Make a secure connection and monitored connection to database (MongoDB Atlas)
    try:
        # 5 second timeout in case database is unreachable
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info() # Forces a call to verify the connection is live
        print("Security Log: Successfully connected to FlexRight Database.")
        return client["FlexRightDB"]
    except Exception as e:
        print(f"Security Alert: Connection failed. Check your .env or IP Whitelist. Error: {e}")
        return None

# Initialize the database object
db = get_db_connection()

# Part 2: Taking in data from DB
def log_workout_session(user_id, exercise_type, performance_metrics):
    # Recieves "math" from the OpenCV/MediaPipe and saves to user history
    # Strucutred DB record
    if db is None: return False

    session_entry = {
        "exercise": exercise_type,
        "metrics": performance_metrics, 
        "timestamp": datetime.datetime.now(),
        "verified": True
    }

    # Push the new sessioj into "sessions" array in the User document
    result = db.users.update_one(
        {"user_id": user_id},
        {"$push": {"sessions": session_entry}}
    )
    
    return result.modified_count > 0

# Part 3: Granular Access Control 
def get_authorized_client_data(trainer_id, client_id):

    # User WALL: Make sure the Professiojal can only see data is user adds them to "shared_with" list
    if db is None: return None

    # HIPPA privacy: Identity must match and permission must exsit
    access_query = {
        "user_id": client_id,
        "shared_with": trainer_id
    }

    # Only return the "sessions" field
    # Protect the rest of the user profile
    user_data = db.users.find_one(access_query, {"sessions": 1, "name": 1, "_id": 0})

    if user_data:
        return user_data.get("sessions", [])
    else:
        print(f"Access Denied: Trainer {trainer_id} attempted to view Client {client_id}.")
        return None

# Part 4: Trainor dashboard information
def get_trainer_client_list(trainer_id):

    # Finds the users who have shared their data with this specific trainer
    if db is None: return []

    # Aggregrate Pipeline: Finds all documents where the trainer_id is in the 'shared_with" array
    pipeline = [
        {"$match": {"shared_with": trainer_id}},
        {"$project": {"user_id": 1, "name": 1, "_id": 0}}
    ]
    
    clients = list(db.users.aggregate(pipeline))
    # Returns a lost for the UI
    return [(c['name'], c['user_id']) for c in clients]