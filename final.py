# -*- coding: utf-8 -*-
import gradio as gr
import os
import subprocess
import json
from data_manager import FlexDatabase
from dotenv import load_dotenv

# Load database helper
load_dotenv()
db_helper = FlexDatabase(os.getenv("MONGO_URI"))

# --- UI STYLING: FULL SCREEN, CENTERED, LAVENDER THEME ---
custom_css = """
.gradio-container {
    max-width: 100% !important;
    width: 100% !important;
    margin: 0 !important;
    padding: 0 !important;
}

body, .gradio-container {
    font-family: 'Inter', system-ui, sans-serif;
    background: #E8E6EB !important;
}
footer { display: none !important; }

.main-card {
    background: #E6E0F0 !important; 
    border-radius: 20px !important;
    padding: 40px !important;
    width: 95% !important;
    max-width: 1600px !important;
    margin: 20px auto;
    box-shadow: 0 10px 30px rgba(123, 107, 168, 0.15);
}

.inner-card {
    background: #EDE8F2 !important;  
    border: 1px solid #E8E6EB !important;
    border-radius: 20px !important;
    padding: 30px !important;
    margin-top: 15px;
    display: flex !important;
    flex-direction: column !important;
    align-items: center !important;
}

h1, h2, h3, .gr-markdown, label, span, p {
    font-weight: 700 !important;
    text-align: center !important;
    color: #9A96A3 !important; 
}

.accent { color: #7B6BA8 !important; font-size: 36px !important; letter-spacing: 0.1em !important; }

input, textarea, .gr-input {
    background: white !important;
    color: #000 !important; 
    border: 1px solid #E8E6EB !important;
    border-radius: 12px !important;
    padding: 12px !important;
    text-align: center !important;
    max-width: 500px !important;
    margin: 0 auto !important;
}

button.primary {
    background-color: #7B6BA8 !important;
    color: #F5F3F8 !important; 
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 18px !important;
    padding: 15px 30px !important;
    width: 300px !important;
    margin: 20px auto !important;
    cursor: pointer;
}

.activity-log-content table {
    width: 100% !important;
    margin: 20px auto !important;
    border-collapse: collapse !important;
    background: white !important;
    border-radius: 12px !important;
    overflow: hidden !important;
}

.activity-log-content th, .activity-log-content td {
    border: 1px solid #E8E6EB !important;
    padding: 14px !important;
    text-align: center !important;
    color: #000 !important;
}

.activity-log-content th {
    background: #7B6BA8 !important;
    color: white !important;
}
"""

flex_theme = gr.themes.Soft(primary_hue="violet", neutral_hue="slate").set(
    body_background_fill="#E8E6EB",
    block_background_fill="#EDE8F2",
    button_primary_background_fill="#7B6BA8",
    button_primary_text_color="#F5F3F8",
)

# --- BACKEND FUNCTIONS ---

def get_available_users():
    try:
        all_users = db_helper.users.find({}, {"user_id": 1})
        return [u["user_id"] for u in all_users]
    except:
        return []

def search_user_metrics(my_id, target_id):
    if not target_id: return "Please enter a User ID."
    target_id = target_id.lower().strip()
    permission_check = db_helper.users.find_one({"user_id": target_id, "shared_with": my_id})
    if not permission_check: return f"Access Denied: '{target_id}' has not shared their data."
    
    sessions = list(db_helper.sessions.find({"user_id": target_id}).sort("timestamp", -1))
    if not sessions: return "No workout data found."
    
    md += "| Date | Exercise | Reps | Over | Under |\n|:---:|:---:|:---:|:---:|:---:|\n"
    for s in sessions:
        date_str = s['timestamp'].strftime("%Y-%m-%d %I:%M %p")
        md += f"| {date_str} | {s['exercise']} | {s['reps']} | {s.get('over_count', 0)} | {s.get('under_count', 0)} |\n"
    return md

def get_live_metrics(uid):
    if not uid: return "### Please log in to view your metrics."
    sessions = list(db_helper.sessions.find({"user_id": uid}).sort("timestamp", -1).limit(15))
    if not sessions: return "### No workout data found yet."
    
    latest = sessions[0]
    history_md = f"## Latest Session: {latest['reps']} Reps of {latest['exercise']}\n"
    history_md += f"### Over: {latest.get('over_count', 0)} | Under: {latest.get('under_count', 0)}\n---\n"
    history_md += "### Full Activity Log\n"
    history_md += "| Date | Exercise | Reps | Overext. | Underext. |\n|:---:|:---:|:---:|:---:|:---:|\n"
    
    for s in sessions:
        date_str = s['timestamp'].strftime("%b %d, %I:%M %p")
        history_md += f"| {date_str} | {s['exercise']} | {s['reps']} | {s.get('over_count', 0)} | {s.get('under_count', 0)} |\n"
    
    return history_md

def refresh_sharing_view(uid):
    all_users = get_available_users()
    already_shared = db_helper.check_shared(uid)
    return gr.update(choices=all_users, value=already_shared)

def handle_login(username, password):
    if not username or not password:
        return gr.update(visible=False), gr.update(visible=True), "Enter both fields", "", gr.update()
    success, profile = db_helper.login_user(username, password)
    if success:
        return gr.update(visible=True), gr.update(visible=False), f"## Welcome, {username}!", username, gr.update(choices=get_available_users(), value=db_helper.check_shared(username))
    return gr.update(visible=False), gr.update(visible=True), f"{profile}", "", gr.update()
def handle_logout():
    # This explicitly resets all data-sensitive components to defaults
    return [
        gr.update(visible=False), # protected_view
        gr.update(visible=True),  # auth_container
        "",                       # current_user_id (state)
        "",                       # user_welcome
        "History cleared.",       # history_display
        "Enter a username above to begin.", # metrics_display
        gr.update(value=[], choices=[]),    # access_tags
        ""                        # status_msg
    ]
def launch_workout(uid):
    if not uid: return "Please login first."
    try:
        python_exe = os.path.join(os.path.dirname(__file__), "venv", "bin", "python.exe")
        subprocess.Popen([python_exe, os.path.join(os.path.dirname(__file__), "yolo_test.py"), uid])
        return f"Workout launched for {uid}!"
    except Exception as e:
        return f"Launch failed: {str(e)}"

# --- INTERFACE ---

with gr.Blocks(theme=flex_theme, css=custom_css, title="FlexRight") as demo:
    current_user_id = gr.State("")

    # AUTH CONTAINER
    with gr.Column(visible=True) as auth_container:
        with gr.Column(elem_classes="main-card"):
            gr.Markdown("# <span class='accent'>FlexRight</span>")
            with gr.Tabs() as auth_tabs:
                with gr.Tab("Login", id="login_tab"):
                    with gr.Column(elem_classes="inner-card"):
                        user_input = gr.Textbox(label="Username")
                        pass_input = gr.Textbox(label="Password", type="password")
                        login_btn = gr.Button("Login", variant="primary")
                        login_msg = gr.Markdown()
                with gr.Tab("Sign Up", id="signup_tab"):
                    with gr.Column(elem_classes="inner-card"):
                        reg_user = gr.Textbox(label="Username")
                        reg_name = gr.Textbox(label="Full Name")
                        reg_email = gr.Textbox(label="Email")
                        reg_pass = gr.Textbox(label="Password", type="password")
                        reg_btn = gr.Button("Create Account", variant="primary")
                        reg_status = gr.Markdown()

    # PROTECTED VIEW
    with gr.Column(visible=False) as protected_view:
        with gr.Column(elem_classes="main-card"):
            gr.Markdown("# <span class='accent'>FlexRight</span>")
            user_welcome = gr.Markdown("### Welcome")
            logout_btn = gr.Button("Logout", variant="secondary")

            with gr.Tabs():
                with gr.Tab("Gym Session"):
                    with gr.Column(elem_classes="inner-card"):
                        launch_btn = gr.Button("Start Workout", variant="primary")
                        workout_status = gr.Markdown("Tracking window will open separately.")
                        refresh_btn = gr.Button("Refresh Log")
                
                with gr.Tab("Progress"):
                    with gr.Column(elem_classes="inner-card"):
                        history_display = gr.Markdown(elem_classes=["activity-log-content"])

                with gr.Tab("Privacy & Sharing"):
                    with gr.Column(elem_classes="inner-card"):
                        share_input = gr.Textbox(label="Grant Access to User", placeholder="Enter username...")
                        add_btn = gr.Button("Grant Access", variant="primary")
                        access_tags = gr.Dropdown(
                            label="Users who can see your data",
                            choices=[], 
                            multiselect=True, 
                            interactive=True,
                            info="Remove a tag to revoke access instantly."
                        )
                        status_msg = gr.Markdown()

                with gr.Tab("Shared Stats"):
                    with gr.Column(elem_classes="inner-card"):
                        search_input = gr.Textbox(label="Enter Friend's Username")
                        search_btn = gr.Button("View Progress", variant="primary")
                        metrics_display = gr.Markdown()

    # --- EVENTS ---
    login_btn.click(
        fn=handle_login, 
        inputs=[user_input, pass_input], 
        outputs=[protected_view, auth_container, user_welcome, current_user_id, access_tags]
    ).then(
        fn=get_live_metrics, 
        inputs=[current_user_id], 
        outputs=[history_display]
    )

    refresh_btn.click(fn=get_live_metrics, inputs=[current_user_id], outputs=[history_display])
    launch_btn.click(fn=launch_workout, inputs=[current_user_id], outputs=workout_status)
    search_btn.click(search_user_metrics, [current_user_id, search_input], metrics_display)
    
    # Restored Access Management Logic
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

    logout_btn.click(
        fn=handle_logout, 
        outputs=[protected_view, auth_container, current_user_id, user_welcome, history_display, metrics_display, access_tags, status_msg]
    )
if __name__ == "__main__":
    demo.launch(inbrowser=True)