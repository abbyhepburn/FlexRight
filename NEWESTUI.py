import gradio as gr
import pymongo
import certifi
from datetime import datetime

# --- 1. MONGODB CONNECTION ---
MONGO_URI = "mongodb+srv://abbyhepburn526:AbbyMay26!@flexcluster.sdbddiz.mongodb.net/?appName=FlexCluster"

try:
    client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client["FlexCluster"]
    users_col = db["users"]
    sessions_col = db["sessions"]
    print("✅ FlexCluster Connected!")
except Exception as e:
    print(f"❌ Connection Error: {e}")

# --- 2. CUSTOM UI STYLING (SOFT THEME / NO BLACK) ---
custom_css = """
body, .gradio-container {
    margin: 0;
    font-family: 'Inter', system-ui, sans-serif;
    background: #F8F9FE !important;
}
footer { display: none !important; }

.main-card {
    background: #E8EAF6 !important; 
    border-radius: 30px !important;
    padding: 40px !important;
    max-width: 850px !important;
    margin: 20px auto;
    box-shadow: 0 10px 30px rgba(139, 124, 246, 0.1);
}

.inner-card {
    background: #F1F3F9 !important;  
    border: 2px solid #DDE1EE !important;
    border-radius: 20px !important;
    padding: 30px !important;
    margin-top: 15px;
}

h1, h2, h3, .gr-markdown, label, span, p {
    font-weight: 700 !important;
    text-align: center;
    color: #8A8AAB !important; 
}

.accent { color: #8B7CF6 !important; }

input, textarea {
    background: white !important;
    color: #8A8AAB !important; 
    border: 1px solid #C5CAE9 !important;
    border-radius: 12px !important;
    padding: 12px !important;
}

.tab-nav button {
    font-weight: 600 !important;
    font-size: 16px !important;
    color: #B0B0C5 !important;
    background: none !important;
    border: none !important;
}

.tab-nav button[aria-selected="true"] {
    color: #8B7CF6 !important;
    border-bottom: 3px solid #8B7CF6 !important;
}

button.primary {
    background-color: #8B7CF6 !important;
    color: #E0E0EB !important; 
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    font-size: 18px !important;
    cursor: pointer;
}

button.primary:hover {
    background-color: #796AE0 !important;
}
"""

flex_theme = gr.themes.Soft(primary_hue="violet", neutral_hue="slate")

# --- 3. BACKEND LOGIC ---
def handle_register(fname, uname, email, pwd):
    if not all([fname, uname, email, pwd]):
        return "⚠️ All fields are required."
    
    if "@" not in email:
        return "⚠️ Please enter a valid email address."
    
    if len(pwd) < 6:
        return "⚠️ Password must be at least 6 characters."

    if users_col.find_one({"username": uname}):
        return "❌ Username already taken."

    # Database insert
    users_col.insert_one({
        "full_name": fname,
        "username": uname,
        "email": email,
        "password": pwd,
        "role": "patient",
        "created_at": datetime.now().strftime("%Y-%m-%d")
    })
    return "✅ Account created! Please click the 'Login' tab above."

def handle_login(username, password):
    user = users_col.find_one({"username": username, "password": password})
    if user:
        return gr.update(visible=False), gr.update(visible=True), f"Welcome back, {user['full_name']}!"
    return gr.update(visible=True), gr.update(visible=False), "❌ Invalid username or password."

def logout():
    return gr.update(visible=True), gr.update(visible=False)

# --- 4. INTERFACE ---
with gr.Blocks(theme=flex_theme, css=custom_css, title="FlexRight") as demo:

    # WINDOW 1: AUTHENTICATION
    with gr.Column(visible=True) as auth_container:
        with gr.Column(elem_classes="main-card"):
            gr.Markdown("# <span class='accent'>FlexRight</span>")
            gr.Markdown("###  Your Workout Journey Starts Here")

            with gr.Tabs() as main_tabs:
                with gr.Tab("Sign Up", id="Sign Up"):
                    with gr.Column(elem_classes="inner-card"):
                        gr.Markdown("### Create Your Profile")
                        new_full_name = gr.Textbox(label="Full Name", placeholder="John Doe")
                        new_user_id = gr.Textbox(label="Username", placeholder="johndoe123")
                        new_email = gr.Textbox(label="Email Address", placeholder="john@example.com")
                        new_pwd = gr.Textbox(label="Password", type="password")
                        signup_btn = gr.Button("Create Account", variant="primary")
                        signup_status = gr.Markdown()

                with gr.Tab("Login", id="Login"):
                    with gr.Column(elem_classes="inner-card"):
                        gr.Markdown("### Welcome Back")
                        user_input = gr.Textbox(label="Username")
                        pass_input = gr.Textbox(label="Password", type="password")
                        login_btn = gr.Button("Login", variant="primary")
                        login_msg = gr.Markdown("Please sign in to proceed.")

    # WINDOW 2: RECOVERY WORKSPACE
    with gr.Column(visible=False) as protected_view:
        with gr.Column(elem_classes="main-card"):
            gr.Markdown("# <span class='accent'>Recovery Workspace</span>")
            user_welcome = gr.Markdown("### Welcome")
            
            with gr.Tabs():
                with gr.Tab("Gym Session"):
                    with gr.Row():
                        gr.Image(sources=["webcam"], label="Skeletal Tracking Feed")
                        with gr.Column(elem_classes="inner-card"):
                            gr.Label(label="Range of Motion (ROM)")
                            gr.Markdown("Calibration active...")
                
                with gr.Tab("Progress"):
                    with gr.Column(elem_classes="inner-card"):
                        gr.Markdown("### Mobility Trends")
                        gr.Plot(label="Recovery Journey")
            
            logout_btn = gr.Button("Logout", variant="secondary")

    # --- EVENTS ---
    # Sign Up Event - Capturing all 4 fields at once
    signup_btn.click(
        handle_register, 
        [new_full_name, new_user_id, new_email, new_pwd], 
        signup_status
    )
    
    # Login & Workspace Logic
    login_btn.click(handle_login, [user_input, pass_input], [auth_container, protected_view, user_welcome])
    logout_btn.click(logout, None, [auth_container, protected_view])

if __name__ == "__main__":
    demo.launch()