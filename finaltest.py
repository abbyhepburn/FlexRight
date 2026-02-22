# -*- coding: utf-8 -*-
import gradio as gr
import os
import subprocess
import json
import time
from data_manager import FlexDatabase
from dotenv import load_dotenv

load_dotenv()
db_helper = FlexDatabase(os.getenv("MONGO_URI"))

SUMMARY_PATH = os.path.join(os.path.dirname(__file__), "session_result.json")

# --- Styling ---
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

# --- Helpers ---
def get_available_users():
    try:
        return [u["user_id"] for u in db_helper.users.find({}, {"user_id": 1})]
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []

def search_user_metrics(my_id, target_id):
    if not target_id:
        return "⚠️ Please enter a User ID to search."
    target_id = target_id.lower().strip()
    permission_check = db_helper.users.find_one({
        "user_id": target_id, "shared_with": my_id
    })
    if not permission_check:
        return f"❌ Access Denied: '{target_id}' has not shared their data with you, or the user does not exist."
    sessions = list(db_helper.sessions.find({"user_id": target_id}).sort("timestamp", -1))
    if not sessions:
        return f"✅ Access Verified for {permission_check.get('name', target_id)}, but no workout data was found."
    output = f"## 📈 Progress for {permission_check.get('name', target_id)}\n\n"
    for s in sessions:
        date_str = s['timestamp'].strftime("%Y-%m-%d %I:%M %p")
        output += f"**{date_str}** | 🏃 {s['exercise']} | {s['reps']} Reps | {s['accuracy_score']}% Score\n\n---\n"
    return output

def get_live_metrics(uid):
    if not uid:
        return {}, "### ⚠️ Please log in to view your metrics."
    sessions = list(db_helper.sessions.find({"user_id": uid}).sort("timestamp", -1).limit(10))
    if not sessions:
        return {"No Data": 0}, "### 🏋️ No workout data found yet. Start a session in 'The Gym'!"
    latest = sessions[0]
    label_data = {"Overall Form Accuracy": latest.get('accuracy_score', 0) / 100}
    history_md  = f"## 🔥 Latest Session: {latest['reps']} Reps of {latest['exercise']}\n"
    history_md += f"### Average Form: {latest.get('accuracy_score', 0)}%\n"
    history_md += "---\n### 📜 Activity Log\n"
    history_md += "| Date | Exercise | Reps | Accuracy |\n|:--- |:--- |:--- |:--- |\n"
    for s in sessions:
        date_str = s['timestamp'].strftime("%b %d, %I:%M %p")
        history_md += f"| {date_str} | {s['exercise']} | {s['reps']} | {s.get('accuracy_score', 0)}% |\n"
    return label_data, history_md
def refresh_sharing_view(uid):
    all_users     = get_available_users()
    already_shared = db_helper.check_shared(uid)
    return gr.update(choices=all_users, value=already_shared)

def launch_workout(uid):
    if not uid:
        return "⚠️ Please login first."
    try:
        python_exe = os.path.join(os.path.dirname(__file__), "venv", "Scripts", "python.exe")
        if not os.path.exists(python_exe):
            python_exe = os.path.join(os.path.dirname(__file__), "venv", "bin", "python")
        subprocess.Popen([python_exe,
                          os.path.join(os.path.dirname(__file__), "yolo_test.py"),
                          uid])
        return "✅ Workout launched! Complete your session, then click **Refresh Summary** below."
    except Exception as e:
        return f"❌ Launch failed: {str(e)}"

def load_session_summary(uid):
    """
    Read session_result.json written by yolo_test.py, save it to MongoDB,
    then return a formatted markdown summary for the website.
    """
    if not os.path.exists(SUMMARY_PATH):
        return "No session data yet. Complete a workout first, then click Refresh."

    try:
        with open(SUMMARY_PATH, "r") as f:
            data = json.load(f)
    except Exception:
        return "⚠️ Could not read session file. Try again after your workout."

    # Only show results belonging to this user
    if data.get("user_id", "guest") != uid and uid:
        return "No session data for your account yet. Complete a workout first."

    # Save to MongoDB (avoid double-saving by checking timestamp)
    existing = db_helper.sessions.find_one({
        "user_id":   data["user_id"],
        "timestamp": {"$gte": __import__("datetime").datetime.strptime(
                          data["timestamp"], "%Y-%m-%d %H:%M:%S")}
    })
    if not existing:
        db_helper.save_session_summary(
            user_id   = data["user_id"],
            exercise  = data["exercise"],
            reps      = data["reps"],
            rep_goal  = data["rep_goal"],
            warnings  = data["warnings"]
        )

    reps        = data["reps"]
    rep_goal    = data["rep_goal"]
    exercise    = data["exercise"].upper()
    over_count  = data["over_count"]
    under_count = data["under_count"]
    warnings    = data["warnings"]
    ts          = data["timestamp"]

    md  = f"## 🏋️ Session Summary — {ts}\n\n"
    md += f"**Exercise:** {exercise} &nbsp;|&nbsp; "
    md += f"**Reps:** {reps} / {rep_goal} &nbsp;|&nbsp; "
    md += f"**Warnings:** {len(warnings)} (Over: {over_count}, Under: {under_count})\n\n"
    md += "---\n\n"

    if not warnings:
        md += "✅ **No form warnings — great session!**\n"
    else:
        md += "### ⚠️ Form Warnings\n\n"
        md += "| Rep | Type | Detail |\n|-----|------|--------|\n"
        for w in warnings:
            badge = "🔴 Over" if w["type"] == "overextension" else "🟠 Under"
            md += f"| {w['rep']} | {badge} | {w['message']} |\n"

    return md

# --- Auth ---
def handle_login(username, password):
    if not username or not password:
        return gr.update(visible=False), gr.update(visible=True), "⚠️ Enter both fields", ""
    success, profile = db_helper.login_user(username, password)
    if success:
        welcome_msg = f"##Welcome!"
        return gr.update(visible=True), gr.update(visible=False), welcome_msg, username
    return gr.update(visible=False), gr.update(visible=True), f"❌ {profile}", ""

def handle_logout():
    return gr.update(visible=False), gr.update(visible=True), "Logged out successfully."

def handle_initial_register(uname, fname, email):
    if not uname or not fname or not email:
        return gr.update(visible=True), gr.update(visible=False), "⚠️ All fields are required."
    return gr.update(visible=False), gr.update(visible=True), f"Almost there, {fname}! Create a secure password."

def handle_final_signup(uname, pword, fname, email):
    result = db_helper.register_new_user(uname, pword, fname, email)
    if "Success" in result:
        return gr.Tabs(selected="login_tab"), gr.update(visible=True), gr.update(visible=False), f"✅ {result} Please Login."
    return gr.Tabs(selected="signup_tab"), gr.update(visible=False), gr.update(visible=True), f"❌ {result}"

def refresh_ui_data(uid):
    label_output, markdown_output = get_live_metrics(uid)
    return label_output, markdown_output

# --- Interface ---
with gr.Blocks(theme=flex_theme, css=custom_css, title="FlexRight") as demo:
    current_user_id = gr.State("")

    gr.Markdown("# 🛡️ <span class='lavender-text'>FlexRight</span>")

    # Login / Signup gate
    with gr.Column(visible=True) as login_gate:
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
                    finish_btn = gr.Button("Complete Account Setup ✅", variant="primary")
                reg_status = gr.Markdown()

    # --- Protected App Content ---
    with gr.Column(visible=False, variant="panel") as protected_view:
        with gr.Row():
            user_welcome = gr.Markdown("## Welcome back!")
            logout_btn   = gr.Button("Logout", variant="stop", size="sm")

        # Tabs should be directly under protected_view
        with gr.Tabs():
            # ── The Gym ──────────────────────────────────────────────────────
            with gr.Tab("The Gym"):
                gr.Markdown("## 🏋️ User Workspace")
                launch_btn     = gr.Button("▶️ Start Workout", variant="primary", size="lg")
                workout_status = gr.Markdown("Click the button to launch the AI camera.")

                gr.Markdown("---")
                gr.Markdown("### 📋 Last Session Summary")
                session_summary_display = gr.Markdown(
                    "Complete a workout then click **Refresh Summary**."
                )
                refresh_btn = gr.Button("🔄 Refresh Summary", variant="secondary")
            with gr.Tab("Privacy & Sharing"):
                gr.Markdown("## 🔐 Manage Access")
                with gr.Row():
                    share_input = gr.Textbox(label="Grant Access to User",
                                             placeholder="Search by Username...")
                    add_btn     = gr.Button("Grant Access", variant="primary")
                access_tags = gr.Dropdown(
                    label="Users who can see your data",
                    choices=get_available_users(),
                    multiselect=True,
                    interactive=True,
                    info="Remove a tag to revoke access instantly."
                )
                status_msg = gr.Markdown()

            # ── Shared Stats ──────────────────────────────────────────────────
            with gr.Tab("Shared Stats"):
                gr.Markdown("## Progress Shared with You")
                with gr.Row():
                    search_input = gr.Textbox(label="Enter Username",
                                              placeholder="e.g. abby123")
                    search_btn   = gr.Button("Search Metrics", variant="primary")
                metrics_display = gr.Markdown("Enter a username above to begin.")

    # --- Wiring ---
    login_btn.click(
        fn=handle_login,
        inputs=[user_input, pass_input],
        outputs=[protected_view, login_gate, user_welcome, current_user_id]
    ).then(
        fn=lambda uid: gr.update(value=db_helper.check_shared(uid)),
        inputs=[current_user_id],
        outputs=[access_tags]
    )

    logout_btn.click(
        fn=handle_logout,
        outputs=[protected_view, login_gate, login_status]
    )

    next_btn.click(handle_initial_register,
                   [reg_user, reg_name, reg_email],
                   [reg_step1, reg_step2, reg_status])
    finish_btn.click(handle_final_signup,
                     [reg_user, reg_pass, reg_name, reg_email],
                     [auth_tabs, reg_step1, reg_step2, reg_status])

    search_btn.click(search_user_metrics,
                     [current_user_id, search_input],
                     metrics_display)

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

    launch_btn.click(
        fn=launch_workout,
        inputs=[current_user_id],
        outputs=workout_status
    )

    refresh_btn.click(
        fn=load_session_summary,
        inputs=[current_user_id],
        outputs=session_summary_display
    )


if __name__ == "__main__":
    demo.launch(inbrowser=True)
#end