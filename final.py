import gradio as gr
import os
import subprocess
import json
from data_manager import FlexDatabase
import datetime
from dotenv import load_dotenv

load_dotenv()
db_helper = FlexDatabase(os.getenv("MONGO_URI"))
SUMMARY_PATH = os.path.join(os.path.dirname(__file__), "session_result.json")
custom_css = """
body, .gradio-container, .main-card, .inner-card, .gr-dropdown, .gr-dropdown-content, .gr-dropdown-content button {
    background-color: #E8E6EB !important;
    font-family: 'Inter', system-ui, sans-serif;
}

footer { display: none !important; }

.gr-block, .gr-form, .gr-box, .gr-group, .form, .block, .fieldset, .padded,
div[class*="gr-"], div[class*="block"], .gradio-group {
    background-color: #E8E6EB !important;
    background: #E8E6EB !important;
    border: none !important;
    box-shadow: none !important;
}

h1, h2, h3, .accent, .accent span {
    color: #7B6BA8 !important;
    font-weight: 700 !important;
    text-align: center !important;
}
.accent { font-size: 36px !important; letter-spacing: 0.1em !important; }

p, span, label, .gr-markdown p, .gr-markdown span, .activity-log-content td {
    color: #4A4A4A !important;
}

.tabs button {
    color: #4A4A4A !important;
    font-weight: 600 !important;
    background: transparent !important;
}
.tabs button.selected {
    color: #7B6BA8 !important;
    border-bottom: 2px solid #7B6BA8 !important;
}
.tabs button:hover {
    background-color: #000000 !important;
    color: #FFFFFF !important;
}

input, textarea, .gr-input {
    background-color: #FFFFFF !important;
    color: #4A4A4A !important;
    border: 1px solid #7B6BA8 !important;
    border-radius: 12px !important;
}

button.primary, button.secondary {
    background-color: #7B6BA8 !important;
    color: #FFFFFF !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
}
button.primary:hover, button.secondary:hover {
    background-color: #000000 !important;
}
.gr-form label span, .block label span, .gr-input-label {
    color: #9B8EC0 !important; /* Muted Light Purple */
    font-weight: 600 !important;
}
.token, .gr-selection-item {
    background-color: #FFFFFF !important;  /* White background like your inputs */
    border: 1px solid #9B8EC0 !important;   /* Light purple border */
    color: #4A4A4A !important;             /* Dark grey text */
    border-radius: 8px !important;
    padding: 2px 8px !important;
    margin: 2px !important;
    box-shadow: none !important;
}

.token-remove, .gr-selection-item button {
    color: #9B8EC0 !important;             /* Match the border color */
    background: transparent !important;
    border: none !important;
}

.token-remove:hover {
    color: #7B6BA8 !important;             /* Darkens slightly on hover */
    background: #E8E6EB !important;        /* Subtle lavender highlight */
}

.gr-input-label, .gr-form label span, .info {
    color: #9B8EC0 !important;             /* Muted light purple text */
    font-weight: 600 !important;
}
#login_btn, #signup_btn, button.primary {
    background-color: #9B8EC0 !important; /* Muted Light Purple background */
    color: #FFFFFF !important;            /* Keep text white for readability */
    border: none !important;
    box-shadow: 0 4px 10px rgba(155, 142, 192, 0.2) !important; /* Soft purple glow */
}

#login_btn:hover, #signup_btn:hover, button.primary:hover {
    background-color: #000000 !important; /* Turns black on hover as requested */
    color: #FFFFFF !important;
}
.gr-form label span, .block label span, .gr-input-label {
    color: #9B8EC0 !important; /* Muted Light Purple */
    font-weight: 600 !important;
    background: transparent !important;
}

input[type="text"], input[type="password"], textarea, .gr-input {
    border: 2px solid #9B8EC0 !important; /* Light purple border */
    background-color: #FFFFFF !important;  /* Keep inside white for typing */
    border-radius: 12px !important;
    color: #4A4A4A !important;            /* Dark grey text inside */
}

input:focus, textarea:focus {
    border-color: #7B6BA8 !important;     /* Slightly darker purple when active */
    outline: none !important;
    box-shadow: 0 0 5px rgba(155, 142, 192, 0.5) !important;
}

::placeholder {
    color: #B8AED6 !important;            /* Even lighter purple for hint text */
}
input[type="text"], input[type="password"] {
    color: #4A4A4A !important;
    border: 1px solid #9B8EC0 !important; /* Matching light purple border */
}
.activity-log-content table td {
    color: #4A4A4A !important;
    background-color: #FFFFFF !important; /* Keeps the cell background white */
}

/* 2. Target the Table Headers */
.activity-log-content table th {
    background-color: #9B8EC0 !important; /* Muted Light Purple for the header */
    color: #FFFFFF !important;            /* White text is okay for the purple header */
    font-weight: bold !important;
}

/* 3. Handle the Markdown table globally just in case */
.prose table td, .prose table th {
    color: #4A4A4A !important;
}

/* 4. Ensure the table border doesn't create a "white out" effect */
.activity-log-content table {
    border: 1px solid #9B8EC0 !important;
    border-collapse: collapse !important;
    width: 100% !important;
}
"""
flex_theme = gr.themes.Soft(primary_hue="violet", neutral_hue="slate").set(
    body_background_fill="#E8E6EB",
    block_background_fill="#EDE8F2",
    button_primary_background_fill="#7B6BA8",
    button_primary_text_color="#F5F3F8",
)

#functions
def get_available_users():
    try:
        all_users = db_helper.users.find({}, {"user_id": 1})
        return [u["user_id"] for u in all_users]
    except:
        return []

def search_user_metrics(my_id, target_id):
    md =""
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
    if not uid: 
        return "### Please log in to view your metrics."
    
    sessions = list(db_helper.sessions.find({"user_id": uid}).sort("timestamp", -1).limit(15))
    
    if not sessions: 
        return "### No workout data found yet. Complete a session to see results!"
    
    latest = sessions[0]
    history_md = f"## Latest Session: {latest['reps']} Reps of {latest['exercise']}\n"
    history_md += f"### Over: {latest.get('over_count', 0)} | Under: {latest.get('under_count', 0)}\n\n---\n"
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
def load_session_summary(uid):
    if not uid:
        return "Please login first."
        
    if not os.path.exists(SUMMARY_PATH):
        return "No session data yet. Complete a workout first."

    try:
        with open(SUMMARY_PATH, "r") as f:
            data = json.load(f)

        if data.get("user_id", "guest") != uid:
            return "No new data for your account."

        db_helper.save_session_summary(
            user_id   = data["user_id"],
            exercise  = data["exercise"],
            reps      = data["reps"],
            rep_goal  = data["rep_goal"],
            warnings  = data["warnings"]
        )

        reps, goal, exercise = data["reps"], data["rep_goal"], data["exercise"].upper()
        ts, warnings = data["timestamp"], data["warnings"]
        
        summary_md = f"## Session Summary — {ts}\n\n"
        summary_md += f"**{exercise}**: {reps}/{goal} Reps\n\n"
        
        if warnings:
            summary_md += "### Form Details\n\n"
            summary_md += "| Rep | Type | Detail |\n"
            summary_md += "|:---:|:---:|:---|\n"
            for w in warnings:
                badge = "Over" if w["type"] == "overextension" else "Under"
                summary_md += f"| {w['rep']} | {badge} | {w['message']} |\n"
        else:
            summary_md += "\n**Clean Session!**"

        return summary_md

    except Exception as e:
        return f"Error loading session: {str(e)}"
def handle_login(username, password):
    if not username or not password:
        return gr.update(visible=False), gr.update(visible=True), "Enter both fields", "", gr.update()
    success, profile = db_helper.login_user(username, password)
    if success:
        return gr.update(visible=True), gr.update(visible=False), f"## Welcome, {username}!", username, gr.update(choices=get_available_users(), value=db_helper.check_shared(username))
    return gr.update(visible=False), gr.update(visible=True), f"{profile}", "", gr.update()
def handle_initial_register(uname, fname, email):
    if not uname or not fname or not email:
        return gr.update(visible=True), gr.update(visible=False), " All fields are required."
    return gr.update(visible=False), gr.update(visible=True), f"Almost there, {fname}! Create a secure password."

def handle_final_signup(uname, pword, fname, email):
    result = db_helper.register_new_user(uname, pword, fname, email)
    if "Success" in result:
        return gr.Tabs(selected="login_tab"), gr.update(visible=True), gr.update(visible=False), f"✅ {result} Please Login."
    return gr.Tabs(selected="signup_tab"), gr.update(visible=False), gr.update(visible=True), f"❌ {result}"

def handle_logout():
    return [
        gr.update(visible=False),
        gr.update(visible=True),  
        "",                      
        "",                      
        "History cleared.",       
        "Enter a username above to begin.",
        gr.update(value=[], choices=[]),    
        ""                        
    ]
def launch_workout(uid):
    if not uid: return "Please login first."
    try:
        python_exe = os.path.join(os.path.dirname(__file__), "venv", "bin", "python")
        subprocess.Popen([python_exe, os.path.join(os.path.dirname(__file__), "yolo_test.py"), uid])
        return f"Workout launched for {uid}!"
    except Exception as e:
        return f"Launch failed: {str(e)}"

#gradio interface
with gr.Blocks(theme=flex_theme, css=custom_css, title="FlexRight") as demo:
    current_user_id = gr.State("")

    #login/signup view
    with gr.Column(visible=True) as auth_container:
        with gr.Column(elem_classes="main-card"):
            gr.Markdown("# <span class='accent'>FlexRight</span>")
            with gr.Tabs() as auth_tabs:
                with gr.Tab("Login", id="login_tab"):
                    user_input   = gr.Textbox(label="Username")
                    pass_input   = gr.Textbox(label="Password", type="password")
                    login_btn    = gr.Button("Login", variant="primary")
                    login_status = gr.Markdown()

                with gr.Tab("Sign Up", id="signup_tab"):
                    with gr.Column(visible=True) as reg_step1:
                        reg_user  = gr.Textbox(label="Username")
                        reg_name  = gr.Textbox(label="Full Name")
                        reg_email = gr.Textbox(label="Email")
                        next_btn  = gr.Button("Next Step")
                    with gr.Column(visible=False) as reg_step2:
                        reg_pass   = gr.Textbox(label="Password", type="password")
                        finish_btn = gr.Button("Complete Account Setup ", variant="primary")
                    reg_status = gr.Markdown()

    # tabs
    with gr.Column(visible=False) as protected_view:
        with gr.Column(elem_classes="main-card"):
            gr.Markdown("# <span class='accent'>FlexRight</span>")
            user_welcome = gr.Markdown("### Welcome")
            logout_btn = gr.Button("Logout", variant="secondary")

            with gr.Tabs():
                with gr.Tab("Gym Session"):
                    with gr.Column(elem_classes="inner-card"):
                        launch_btn = gr.Button("Start Workout", variant="primary")
                        workout_status = gr.Markdown("Pressing start will trigger a seperate window for tracking.")
                        session_summary_display = gr.Markdown()                        
                        
                        refresh_btn = gr.Button("Refresh Log", variant="secondary")
                
                with gr.Tab("Progress", id="progress_tab"): 
                    with gr.Column(elem_classes="inner-card"):
                        history_display = gr.Markdown(elem_classes=["activity-log-content"])
                with gr.Tab("Privacy & Sharing"):
                    with gr.Column(elem_classes="inner-card"):
                        share_input = gr.Textbox(label="Grant Access to User", placeholder="Enter username...")
                        add_btn = gr.Button("Grant Access", variant="primary")
                        access_tags = gr.Dropdown(
                            label="",              
                            show_label=False,      
                            choices=[], 
                            multiselect=True, 
                            interactive=True,
                            info="Remove a tag to revoke access instantly.",
                            container=False        
                        )
                        status_msg = gr.Markdown()

                with gr.Tab("Shared Stats"):
                    gr.Markdown("## Progress Shared with You")
                    with gr.Row():
                        search_input = gr.Textbox(label="Enter Username",
                                                placeholder="e.g. abby123")
                        search_btn   = gr.Button("Search Metrics", variant="primary")
                    metrics_display = gr.Markdown("Enter a username above to begin.")

    # Buttons
    login_btn.click(
        fn=handle_login, 
        inputs=[user_input, pass_input], 
        outputs=[protected_view, auth_container, user_welcome, current_user_id, access_tags]
    ).then(
        fn=get_live_metrics, 
        inputs=[current_user_id], 
        outputs=[history_display]
    )

    refresh_btn.click(
        fn=load_session_summary,
        inputs=[current_user_id],
        outputs=[session_summary_display] 
    )
    launch_btn.click(fn=launch_workout, inputs=[current_user_id], outputs=workout_status)
    search_btn.click(search_user_metrics, [current_user_id, search_input], metrics_display)
    next_btn.click(handle_initial_register,
                   [reg_user, reg_name, reg_email],
                   [reg_step1, reg_step2, reg_status])
    finish_btn.click(handle_final_signup,
                     [reg_user, reg_pass, reg_name, reg_email],
                     [auth_tabs, reg_step1, reg_step2, reg_status])
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