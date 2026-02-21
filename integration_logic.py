import os
import datetime
from pymongo import MongoClient
from dotenv import load_dotenv

# 1. SETUP & SECURITY CONFIGURATION
# Load secret credentials from the .env file to keep them out of the source code
load_dotenv()
MONGO_URI = os.getenv("MONGO_URI")

def get_db_connection():
    #Establish a secure, monitored connection to MongoDB Atlas
    try:
        # We set a 5-second timeout so the app doesn't hang if the DB is unreachable
        client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        client.server_info() # Forces a call to verify the connection is live
        print("Security Log: Successfully connected to FlexRight Database.")
        return client["FlexRightDB"]
    except Exception as e:
        print(f"Security Alert: Connection failed. Check your .env or IP Whitelist. Error: {e}")
        return None

# Initialize the database object
db = get_db_connection()

# 2. DATA INGESTION (The Handshake with Member 1)
def log_workout_session(user_id, exercise_type, performance_metrics):
    """
    Receives 'Skeletal Math' from the OpenCV/MediaPipe engine and saves it to the user's history.
    Member 1's vision output is transformed into a structured database record here.
    """
    if db is None: return False

    session_entry = {
        "exercise": exercise_type,
        "metrics": performance_metrics, # e.g., {"angle": 102, "depth_percent": 95}
        "timestamp": datetime.datetime.now(),
        "verified": True
    }

    # Atomically push the new session into the 'sessions' array in the User document
    result = db.users.update_one(
        {"user_id": user_id},
        {"$push": {"sessions": session_entry}}
    )
    
    return result.modified_count > 0

# 3. GRANULAR ACCESS CONTROL (The Handshake with Member 3)
def get_authorized_client_data(trainer_id, client_id):
    """
    The 'Gatekeeper' function. It ensures a Professional can only see data if 
    the User has explicitly added them to their 'shared_with' list.
    """
    if db is None: return None

    # This query enforces HIPAA-style privacy: Identity must match AND Permission must exist
    access_query = {
        "user_id": client_id,
        "shared_with": trainer_id
    }

    # Only return the 'sessions' field; protect the rest of the user profile (Least Privilege)
    user_data = db.users.find_one(access_query, {"sessions": 1, "name": 1, "_id": 0})

    if user_data:
        return user_data.get("sessions", [])
    else:
        print(f"Access Denied: Trainer {trainer_id} attempted to view Client {client_id}.")
        return None

# 4. TRAINER DASHBOARD AGGREGATION
def get_trainer_client_list(trainer_id):
    """
    Finds all users who have shared their data with this specific trainer.
    This populates the Dropdown menu in Member 3's Trainer Portal.
    """
    if db is None: return []

    # Aggregation Pipeline: Find all documents where the trainer_id is in the 'shared_with' array
    pipeline = [
        {"$match": {"shared_with": trainer_id}},
        {"$project": {"user_id": 1, "name": 1, "_id": 0}}
    ]
    
    clients = list(db.users.aggregate(pipeline))
    # Returns a clean list for the UI: e.g., [("Alex", "user_01"), ("Jordan", "user_02")]
    return [(c['name'], c['user_id']) for c in clients]