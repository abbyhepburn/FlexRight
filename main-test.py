import gradio as gr
import os
from data_manager import FlexDatabase
from dotenv import load_dotenv

load_dotenv()
db_helper = FlexDatabase(os.getenv("MONGO_URI"))

# --- DATABASE BRIDGE FUNCTIONS ---
def get_available_users():
    """
    Replaces get_available_professionals.
    Returns a list of ALL usernames so anyone can be found.
    """
    try:
        # We query all users, but only return their IDs
        all_users = db_helper.users.find({}, {"user_id": 1})
        return [u["user_id"] for u in all_users]
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []
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

# --- AUTH & NAVIGATION LOGIC ---

def handle_login(username, password):
    if not username or not password:
        return gr.update(visible=False), gr.update(visible=True), "⚠️ Enter both fields", "", ""
        
    success, profile = db_helper.login_user(username, password)
    
    if success:
        welcome_msg = f"## ✅ Login Successful! Welcome, {profile['name']}"
        return (
            gr.update(visible=True),   # Show protected_view
            gr.update(visible=False),  # Hide login_gate
            welcome_msg, 
            profile['role'], 
            username
        )
    else:
        # Show error message on the login screen
        return gr.update(visible=False), gr.update(visible=True), f"❌ {profile}", "", ""

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
            return f"⚠️ Error: {label} field is required!"
            
    return db_helper.register_new_user(uname, pword, fname, email, role)

# --- INTERFACE ---

with gr.Blocks(title="FlexRight: Secure AI Recovery") as demo:
    # State variables to track the session
    current_user_id = gr.State("")
    current_user_role = gr.State("")

    gr.Markdown("# 🛡️ FlexRight")
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
                    webcam = gr.Image(sources=["webcam"], streaming=True, label="Live Feed")
                    stats = gr.Label(label="Live Performance Metrics")

            # TAB: DATA PRIVACY (Member 2)
            
            with gr.Tab("Data Privacy"):
                gr.Markdown("## 🔐 Your Data, Your Choice")
                with gr.Row():
                    share_input = gr.Textbox(label="Enter Trainer ID", placeholder="Search by ID...")
                    add_btn = gr.Button("Grant Access", variant="primary")
                
                # Note: get_available_professionals() runs once at startup
                access_list = gr.CheckboxGroup(
                    label="Current Authorized Professionals", 
                    choices=get_available_users() 
                )
                status_msg = gr.Markdown()

            with gr.Tab("Shared Stats"):
                gr.Markdown("## 🔍 Search Shared Progress")
                gr.Markdown("Enter a Username to view their metrics (Note: They must have granted you access first).")
                
                with gr.Row():
                    search_input = gr.Textbox(
                        label="Enter Username", 
                        placeholder="e.g. user123",
                        max_lines=1
                    )
                    search_btn = gr.Button("Search Metrics", variant="primary")
                
                # The area where the reps and dates will appear
                metrics_display = gr.Markdown("Enter a username above to begin.")
    # --- UPDATED EVENT LOGIC ---

    # 1. Fill the dropdown with people who shared with the logged-in user
    search_btn.click(
        fn=search_user_metrics,
        inputs=[current_user_id, search_input],
        outputs=metrics_display
    )

   
    # --- EVENT LOGIC ---

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

if __name__ == "__main__":
    demo.launch(inbrowser=True)