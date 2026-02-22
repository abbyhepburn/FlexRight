# -*- coding: utf-8 -*-
import gradio as gr
import os
import subprocess
from data_manager import FlexDatabase
from dotenv import load_dotenv

# Load database helper
load_dotenv()
db_helper = FlexDatabase(os.getenv("MONGO_URI"))

# --- 1. THE CUSTOM UI STYLING ---
custom_css = """
.gradio-container {background-color: #FFFFFF !important}
footer {display: none !important} 
.lavender-text { color: #B299FF !important; font-weight: bold; }
"""

flex_theme = gr.themes.Soft(primary_hue="purple", neutral_hue="slate").set(
    body_background_fill="white",
    block_background_fill="white",
    button_primary_background_fill="#B299FF",
    button_primary_text_color="white",
)

def get_available_users():
    try:
        # We query all users, but only return their IDs
        all_users = db_helper.users.find({}, {"user_id": 1})
        return [u["user_id"] for u in all_users]
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []
def check_shared(my_id, target_id):
    target_id = target_id.lower().strip()

    # 1. Check if the user exists and if they shared with the logged-in user
    # Logic: Search for a user where user_id is the target AND my_id is in their shared_with list
    all_users = db_helper.users.find({}, {"user_id": 1}) 
    for u in all_users:
        user2 = u["user_id"]
        permission_check = db_helper.users.find_one({
            "user_id": my_id,
            "shared_with": user2
        })
def search_user_metrics(my_id, target_id):
    """
    Checks if 'target_id' exists and if they have shared data with 'my_id'.
    """
    if not target_id:
        return "⚠️ Please enter a User ID to search."
    
    target_id = target_id.lower().strip()
    
    # 1. Check if the user exists and if they shared with the logged-in user
    # Logic: Search for a user where user_id is the target AND my_id is in their shared_with list
    permission_check = db_helper.users.find_one({
        "user_id": target_id,
        "shared_with": my_id
    })

    if not permission_check:
        return f"❌ Access Denied: '{target_id}' has not shared their data with you, or the user does not exist."

    # 2. If valid, fetch their sessions
    sessions = list(db_helper.sessions.find({"user_id": target_id}).sort("timestamp", -1))
    
    if not sessions:
        return f"✅ Access Verified for {permission_check.get('name', target_id)}, but no workout data was found."
    
    # 3. Format the stats
    output = f"## 📈 Progress for {permission_check.get('name', target_id)}\n\n"
    for s in sessions:
        date_str = s['timestamp'].strftime("%Y-%m-%d %I:%M %p")
        output += f"**{date_str}** | 🏃 {s['exercise']} | {s['reps']} Reps | {s['accuracy_score']}% Score\n\n---\n"
    
    return output

def display_shared_metrics(target_user_id):
    if not target_user_id: 
        return "Select a user to view metrics."
    # Queries the sessions collection for that specific user
    sessions = list(db_helper.sessions.find({"user_id": target_user_id}).sort("timestamp", -1))
    if not sessions:
        return "No session data found for this user."
    
    output = "### 📊 Activity History\n\n"
    for s in sessions:
        date_str = s['timestamp'].strftime("%Y-%m-%d")
        output += f"**{date_str}** | {s['exercise']} | {s['reps']} Reps | {s['accuracy_score']}% Accuracy\n\n"
    return output
def get_live_metrics(uid):
    if not uid:
        return {}, "### ⚠️ Please log in to view your metrics."
    
    # 1. Fetch the 10 most recent sessions for this user
    sessions = list(db_helper.sessions.find({"user_id": uid}).sort("timestamp", -1).limit(10))
    
    if not sessions:
        return {"No Data": 0}, "### 🏋️ No workout data found yet. Start a session in 'The Gym'!"

    # 2. Extract the latest session
    latest = sessions[0]
    
    # 3. Format the Label Data (The 'Form Accuracy' ring)
    # Gradio Labels expect a float between 0 and 1 for the 'confidence' bar look
    label_data = {
        "Overall Form Accuracy": latest.get('accuracy_score', 0) / 100
    }

    # 4. Format the History Markdown Table
    # We use a Markdown table for a cleaner, professional look
    history_md = f"## 🔥 Latest Session: {latest['reps']} Reps of {latest['exercise']}\n"
    history_md += f"### Average Form: {latest.get('accuracy_score', 0)}%\n"
    history_md += "---\n"
    history_md += "### 📜 Activity Log\n"
    history_md += "| Date | Exercise | Reps | Accuracy |\n"
    history_md += "|:--- |:--- |:--- |:--- |\n"
    
    for s in sessions:
        # Format the timestamp nicely (e.g., Oct 24, 02:30 PM)
        date_str = s['timestamp'].strftime("%b %d, %I:%M %p")
        history_md += f"| {date_str} | {s['exercise']} | {s['reps']} | {s.get('accuracy_score', 0)}% |\n"
        
    return label_data, history_md
def refresh_sharing_view(uid):
    all_users = get_available_users()# Everyone in the system
    already_shared = db_helper.check_shared(uid) # Only those shared with
    
    # We update the CheckboxGroup: 
    # choices = everyone, value = only the ones currently shared
    return gr.update(choices=all_users, value=already_shared)
def launch_workout(uid):
    if not uid:
        return "⚠️ Please login first."
    try:
        # Get path to your python executable
        python_exe = os.path.join(os.path.dirname(__file__), "venv", "bin", "python")
        if os.name == 'nt':
            python_exe = os.path.join(os.path.dirname(__file__), "venv", "Scripts", "python.exe")
            
        # PASS 'uid' as a command line argument
        subprocess.Popen([python_exe, os.path.join(os.path.dirname(__file__), "yolo_test.py"), uid])
        return f"🚀 Workout launched for {uid}!"
    except Exception as e:
        return f"❌ Launch failed: {str(e)}"

# --- 3. AUTH & NAVIGATION LOGIC ---

def handle_login(username, password):
    if not username or not password:
        return gr.update(visible=False), gr.update(visible=True), "⚠️ Enter both fields", "", ""
    
    success, profile = db_helper.login_user(username, password)
    if success:
        welcome_msg = f"##Welcome!"
        return gr.update(visible=True), gr.update(visible=False), welcome_msg, username
    return gr.update(visible=False), gr.update(visible=True), f"❌ {profile}", ""
def handle_logout():
    # Reverse the visibility
    return gr.update(visible=False), gr.update(visible=True), "Logged out successfully."

def handle_initial_register(uname, fname, email):
    if not uname or not fname or not email:
        return gr.update(visible=True), gr.update(visible=False), "⚠️ All fields are required."
    return gr.update(visible=False), gr.update(visible=True), f"Almost there, {fname}! Create a secure password."

def handle_final_signup(uname, pword, fname, email):
    # Call the database helper to register
    result = db_helper.register_new_user(uname, pword, fname, email)
    if "Success" in result:
        # Reset the view and go to login
        return gr.Tabs(selected="login_tab"), gr.update(visible=True), gr.update(visible=False), f"✅ {result} Please Login."
    else:
        return gr.Tabs(selected="signup_tab"), gr.update(visible=False), gr.update(visible=True), f"❌ {result}"
def refresh_ui_data(uid):
    label_output, markdown_output = get_live_metrics(uid)
    return label_output, markdown_output
# --- 4. INTERFACE ---

with gr.Blocks(theme=flex_theme, css=custom_css, title="FlexRight") as demo:
    current_user_id = gr.State("")

    gr.Markdown("# 🛡️ <span class='lavender-text'>FlexRight</span>")
    
    # --- 1. THE LOGIN/SIGNUP GATE ---
    with gr.Column(visible=True) as login_gate:
        with gr.Tabs() as auth_tabs:
            with gr.Tab("Login", id="login_tab"):
                user_input = gr.Textbox(label="Username")
                pass_input = gr.Textbox(label="Password", type="password")
                login_btn = gr.Button("Login", variant="primary")
                login_status = gr.Markdown()

            with gr.Tab("Sign Up", id="signup_tab"):
                # Step 1
                with gr.Column(visible=True) as reg_step1:
                    reg_user = gr.Textbox(label="Username")
                    reg_name = gr.Textbox(label="Full Name")
                    reg_email = gr.Textbox(label="Email")
                    next_btn = gr.Button("Next Step")
                # Step 2
                with gr.Column(visible=False) as reg_step2:
                    reg_pass = gr.Textbox(label="Password", type="password")
                    finish_btn = gr.Button("Complete Account Setup ✅", variant="primary")
                reg_status = gr.Markdown()

   # --- 2. PROTECTED APP CONTENT ---
    with gr.Column(visible=False, variant="panel") as protected_view:
        with gr.Row():
            user_welcome = gr.Markdown("## Welcome back!")
            logout_btn = gr.Button("Logout", variant="stop", size="sm")

        # Tabs should be directly under protected_view
        with gr.Tabs():
            with gr.Tab("The Gym"):
                gr.Markdown("## 🏋️ User Workspace")
                with gr.Row():
                    launch_btn = gr.Button("▶️ Start Workout", variant="primary")
                    refresh_btn = gr.Button("🔄 Refresh Stats")
                
                # Added workout_status back so the launch button works
                workout_status = gr.Markdown("Ready to train?") 
                
                with gr.Row():
                    stats_label = gr.Label(label="Latest Session Highlights")
                    history_display = gr.Markdown("History will appear here...")
            with gr.Tab("Privacy & Sharing"):
                gr.Markdown("## 🔐 Manage Access")
                with gr.Row():
                    share_input = gr.Textbox(label="Grant Access to User", placeholder="Search by Username...")
                    # THIS IS THE DEFINITION
                    add_btn = gr.Button("Grant Access", variant="primary")
                # This dropdown will display current shares as removable tags
                    access_tags = gr.Dropdown(
                        label="Users who can see your data",
                        choices=get_available_users(), # All possible users
                        multiselect=True,
                        interactive=True,
                        info="Remove a tag to revoke access instantly."
                    )
                
                status_msg = gr.Markdown()

            with gr.Tab("Shared Stats"):
                gr.Markdown("## Progress Shared with You")
                with gr.Row():
                    search_input = gr.Textbox(label="Enter Username", placeholder="e.g. abby123")
                    search_btn = gr.Button("Search Metrics", variant="primary")
                metrics_display = gr.Markdown("Enter a username above to begin.")

    # --- 5. THE WIRING ---

    # 1. Login & Auto-Refresh
    login_btn.click(
        fn=handle_login,
        inputs=[user_input, pass_input],
        outputs=[protected_view, login_gate, user_welcome, current_user_id]
    ).then(
        fn=refresh_ui_data, 
        inputs=[current_user_id],
        outputs=[stats_label, history_display]
    ).then(
        fn=lambda uid: gr.update(value=db_helper.check_shared(uid)),
        inputs=[current_user_id],
        outputs=[access_tags]
    )

    # 2. Manual Refresh Logic
    refresh_btn.click(
    fn=refresh_ui_data,
    inputs=[current_user_id],
    outputs=[stats_label, history_display]
    )

    # 3. Workout Launch
    launch_btn.click(
        fn=launch_workout, 
        inputs=[current_user_id], 
        outputs=workout_status
    )

    # 4. Sharing & Search Logic
    search_btn.click(search_user_metrics, [current_user_id, search_input], metrics_display)
    
    add_btn.click(
        fn=db_helper.add_shared_access, 
        inputs=[current_user_id, share_input], 
        outputs=status_msg
    ).then(
        fn=refresh_sharing_view, 
        inputs=[current_user_id],
        outputs=[access_tags]
    )

    access_tags.change(
        fn=db_helper.sync_sharing, 
        inputs=[current_user_id, access_tags],
        outputs=status_msg
    )

    # 5. Logout & Signup
    logout_btn.click(fn=handle_logout, outputs=[protected_view, login_gate, login_status])
    next_btn.click(handle_initial_register, [reg_user, reg_name, reg_email], [reg_step1, reg_step2, reg_status])
    finish_btn.click(handle_final_signup, [reg_user, reg_pass, reg_name, reg_email], [auth_tabs, reg_step1, reg_step2, reg_status])

if __name__ == "__main__":
    demo.launch(inbrowser=True)