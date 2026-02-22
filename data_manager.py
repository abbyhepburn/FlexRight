import os
import datetime
from pymongo import MongoClient
from dotenv import load_dotenv
import certifi
import bcrypt
load_dotenv()
#creation of class to allow functions to be accesed easier
class FlexDatabase:
    def __init__(self, connection_string):
        #connect to MongoDB
        self.client = MongoClient(connection_string, tlsCAFile=certifi.where())
        #connect to main database
        self.db = self.client['FlexRightDB']
        #connect to users database
        self.users = self.db['users']
        self.sessions = self.db['sessions']
    #Register new user
    def register_new_user(self, username, password, full_name, user_email):
        #takes username input and checks if it already exists
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        user_id = username.lower().strip()
        if self.users.find_one({"user_id": user_id}):
            return "Error: User already exists"
        #dictionary of all of users info
        new_user = {
            "user_id": user_id,
            "password": hashed_password,
            "name": full_name,
            "email": user_email,
            "shared_with": []
        }
        #inserts dictionary into usersDB
        self.users.insert_one(new_user)
        return f"Success: {full_name} registered!"
    def login_user(self, username, password):
        user_id = username.lower().strip()
        user = self.users.find_one({"user_id": user_id})
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password']):
            return True, user
        return False, "Invalid username or password"
    #adds other users to shared list
    def add_shared_access(self, current_user_id, pro_id_to_add):
        #adds shareid to dict of allowed users
        self.users.update_one(
            {"user_id": current_user_id},
            {"$addToSet": {"shared_with": pro_id_to_add}}
        )
        return f"Access granted to {pro_id_to_add}!"
    #saves workout info
    def save_workout(self, user_id, exercise_name, reps, score):
        ##saves all inputs to dict and pushes it to sessions db
        session_data = {
            "user_id": user_id,
            "exercise": exercise_name,
            "reps": reps,
            "accuracy_score": score,
            "timestamp": datetime.datetime.now()
        }
        self.sessions.insert_one(session_data)
        return "Workout saved!"
    #finds exercise info and criteria for a rep
    def get_exercise_details(self, exercise_name):
        return self.db['exercises'].find_one({"name": exercise_name})
        #fine_one allows MongoDB to find the exact one document that matches name
    def capture_exercise_template(self, name, difficulty, observed_angle):
        template = {
            "name": name,
            "difficulty": difficulty,
            "target_angle": observed_angle,
            "created_at": datetime.datetime.now()
        }
        # This saves it to the 'exercises' collection
        self.db['exercises'].update_one(
            {"name": name},
            {"$set": template},
            upsert=True
        )
        return f"Template for {name} saved at {observed_angle} degrees"
    def get_user_sessions(self, user_id):
        try:
            # Sort by timestamp descending so newest is first
            sessions = list(self.sessions.find({"user_id": user_id}).sort("timestamp", -1))
            if not sessions:
                return "No workout data found for this user."
            
            # Format the data into a readable string or list for the UI
            report = ""
            for s in sessions:
                date = s['timestamp'].strftime("%Y-%m-%d %H:%M")
                report += f"📅 **{date}** | 🏃 {s['exercise']} | ✅ Reps: {s['reps']} | 🎯 Score: {s['accuracy_score']}%\n\n---\n"
            return report
        except Exception as e:
            return f"Error fetching sessions: {e}"
    def check_shared(self, my_id):
        """
        Returns a list of User IDs that the logged-in user (my_id) 
        has already granted access to.
        """
        # 1. Fetch the logged-in user's document
        user_doc = self.users.find_one({"user_id": my_id}, {"shared_with": 1})
        
        if not user_doc or "shared_with" not in user_doc:
            return []

        # 2. Get the list of IDs you've shared with
        shared_ids = user_doc["shared_with"]

        # 3. Optional: Verify these users still exist and return their IDs
        # This finds all users whose user_id is IN your shared_ids list
        valid_shares = self.users.find({"user_id": {"$in": shared_ids}}, {"user_id": 1})
        
        return [u["user_id"] for u in valid_shares]
    # Add this to your FlexDatabase class in data_manager.py
    def remove_shared_access(self, my_id, pro_id_to_remove):
        """Removes a specific user from the shared_with list."""
        self.users.update_one(
            {"user_id": my_id},
            {"$pull": {"shared_with": pro_id_to_remove}}
        )
        return f"Access revoked for {pro_id_to_remove}."
    # In FlexDatabase class
    def sync_sharing(self, my_id, selected_list):
        """Overwrites the shared_with list to match the UI checkboxes."""
        self.users.update_one(
            {"user_id": my_id},
            {"$set": {"shared_with": selected_list}}
        )
        return f"Permissions updated: {len(selected_list)} users authorized."

    def save_session_summary(self, user_id, exercise, reps, rep_goal, warnings):
        """Saves a full session including the warnings log to MongoDB."""
        over_count  = sum(1 for w in warnings if w["type"] == "overextension")
        under_count = sum(1 for w in warnings if w["type"] == "underextension")
        total = len(warnings)
        accuracy = max(0, round(100 - (total / max(reps, 1)) * 20))
        session_data = {
            "user_id":      user_id,
            "exercise":     exercise,
            "reps":         reps,
            "rep_goal":     rep_goal,
            "accuracy_score": accuracy,
            "warnings":     warnings,
            "over_count":   over_count,
            "under_count":  under_count,
            "timestamp":    datetime.datetime.now()
        }
        self.sessions.insert_one(session_data)
        return "Session saved!"

    def get_latest_session_summary(self, user_id):
        """Returns the most recent session document for a user."""
        return self.sessions.find_one(
            {"user_id": user_id},
            sort=[("timestamp", -1)]
        )