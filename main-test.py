# -*- coding: utf-8 -*-
import gradio as gr
import os
import subprocess
from data_manager import FlexDatabase
from dotenv import load_dotenv

load_dotenv()
db_helper = FlexDatabase(os.getenv("MONGO_URI"))

# --- DATABASE BRIDGE FUNCTIONS ---

def get_available_professionals():
    try:
        trainers = db_helper.users.find({"role": "trainer"})
        # Returns a list of names for the CheckboxGroup
        return [t.get("name", t["user_id"]) for t in trainers]
    except Exception as e:
        print(f"Warning: Could not connect to database: {e}")
        return []  # Return empty list if database unavailable

def get_authorized_patients(trainer_username):
    if not trainer_username:
        return []
    # Search for users where trainer_username is in their 'shared_with' list
    query = {"shared_with": trainer_username}
    patients = db_helper.users.find(query)
    
    # Return list of tuples (Display Name, ID) for the dropdown
    return gr.Dropdown(choices=[(p["name"], p["user_id"]) for p in patients])

def launch_workout():
    """Launch the yolo_test.py fitness app"""
    try:
        # Launch yolo_test.py in a separate process
        subprocess.Popen([
            os.path.join(os.path.dirname(__file__), "venv", "Scripts", "python.exe"),
            os.path.join(os.path.dirname(__file__), "yolo_test.py")
        ])
        return "[OK] Workout app launched! Check your workout window."
    except Exception as e:
        return f"[ERROR] Error launching workout: {str(e)}"

# --- AUTH & NAVIGATION LOGIC ---

def handle_login(username, password):
    if not username or not password:
        return gr.update(visible=False), gr.update(visible=True), "[WARNING] Enter both fields", "", ""
        
    success, profile = db_helper.login_user(username, password)
    
    if success:
        welcome_msg = f"## [OK] Login Successful! Welcome, {profile['name']}"
        return (
            gr.update(visible=True),   # Show protected_view
            gr.update(visible=False),  # Hide login_gate
            welcome_msg, 
            profile['role'], 
            username
        )
    else:
        # Show error message on the login screen
        return gr.update(visible=False), gr.update(visible=True), f"[ERROR] {profile}", "", ""

def handle_logout():
    # Reverse the visibility
    return gr.update(visible=False), gr.update(visible=True), "Logged out successfully."
def handle_sign_up(uname, pword, fname, email, role):
    # Dictionary mapping internal names to user-friendly labels
    fields = {
        "Username": uname,
        "Password": pword,
        "Full Name": fname,
        "Email": email
    }
    for label, value in fields.items():
        if not value or str(value).strip() == "":
            return f"[WARNING] Error: {label} field is required!"
            
    return db_helper.register_new_user(uname, pword, fname, email, role)

# --- INTERFACE ---

with gr.Blocks(title="FlexRight: Secure AI Recovery") as demo:
    # State variables to track the session
    current_user_id = gr.State("")
    current_user_role = gr.State("")

    gr.Markdown("# [SHIELD] FlexRight")
# --- 1. THE LOGIN/SIGNUP GATE ---
    with gr.Column(visible=True) as login_gate:
        with gr.Tabs():
            with gr.Tab("Login"):
                user_input = gr.Textbox(label="Username")
                pass_input = gr.Textbox(label="Password", type="password")
                login_btn = gr.Button("Login", variant="primary")
                login_status = gr.Markdown() # TARGET FOR LOGIN MESSAGES

            with gr.Tab("Sign Up"):
                reg_user = gr.Textbox(label="Username")
                reg_pass = gr.Textbox(label="Password", type="password")
                reg_name = gr.Textbox(label="Full Name")
                reg_email = gr.Textbox(label="Email")
                reg_role = gr.Radio(["patient", "trainer"], label="Role", value="patient")
                reg_btn = gr.Button("Create Account")
                reg_status = gr.Markdown() # TARGET FOR SIGNUP MESSAGES
# --- PROTECTED APP CONTENT ---
    with gr.Column(visible=False, variant="panel") as protected_view:        # Put the Welcome message and Logout button at the very top
        with gr.Row():
            user_welcome = gr.Markdown("## Loading Dashboard...")
            logout_btn = gr.Button("Logout", variant="stop", size="sm")

        with gr.Tabs():
            # TAB: THE GYM (Member 1)
            with gr.Tab("The Gym"):
                gr.Markdown("## User Workspace")
                with gr.Row():
                    launch_btn = gr.Button("[PLAY] Click to Start Workout", variant="primary", size="lg", scale=1)
                    stats = gr.Label(label="Live Performance Metrics")
                
                workout_status = gr.Markdown("Click the button to launch your workout program")

            # TAB: DATA PRIVACY (Member 2)
            with gr.Tab("Data Privacy"):
                gr.Markdown("## [LOCK] Your Data, Your Choice")
                with gr.Row():
                    share_input = gr.Textbox(label="Enter Trainer ID", placeholder="Search by ID...")
                    add_btn = gr.Button("Grant Access", variant="primary")
                
                # Note: get_available_professionals() runs once at startup
                access_list = gr.CheckboxGroup(
                    label="Current Authorized Professionals", 
                    choices=get_available_professionals() 
                )
                status_msg = gr.Markdown()

            # TAB: TRAINER PORTAL (Member 4)
            with gr.Tab("Trainer Portal"):
                gr.Markdown("## [HOSPITAL] Professional Portal")
                client_id = gr.Dropdown(label="Select Authorized Client", choices=[])
                refresh_btn = gr.Button("Find My Clients")
                plot = gr.Plot(label="Recovery Telemetry (Skeletal Angles)")

    # --- EVENT LOGIC ---

    # Launch Workout Button
    launch_btn.click(
        fn=launch_workout,
        outputs=workout_status
    )

    # Sign Up: Output goes to 'reg_status'
    reg_btn.click(handle_sign_up, [reg_user, reg_pass, reg_name, reg_email, reg_role], reg_status)

    # Login: Outputs go to multiple places including 'login_status'
    login_btn.click(
        fn=handle_login,
        inputs=[user_input, pass_input],
        outputs=[protected_view, login_gate, login_status, current_user_role, current_user_id]
    )

    # Logout: Resets visibility
    logout_btn.click(
        fn=handle_logout,
        outputs=[protected_view, login_gate, login_status]
    )

    # Sharing Logic
    add_btn.click(
        fn=lambda u, t: db_helper.add_shared_access(u, t), 
        inputs=[current_user_id, share_input], 
        outputs=status_msg
    )

    # Trainer Refresh Logic
    refresh_btn.click(
        fn=get_authorized_patients, 
        inputs=[current_user_id], 
        outputs=client_id
    )

if __name__ == "__main__":
    demo.launch(inbrowser=True)