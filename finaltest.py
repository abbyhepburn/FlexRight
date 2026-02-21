import gradio as gr
import pymongo
import certifi

# --- 1. MONGODB CONNECTION ---
# Using the credentials provided by Member 2 (Abby)
MONGO_URI = "mongodb+srv://abbyhepburn526:AbbyMay26!@flexcluster.sdbddiz.mongodb.net/?appName=FlexCluster"

try:
    # certifi.where() is crucial for connecting from different laptops safely
    client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where())
    db = client["FlexCluster"] # Database Name
    
    # Using Member 2's specific Collection names
    users_col = db["users"]
    exercises_col = db["exercises"]
    sessions_col = db["sessions"]
    
    print("✅ Connection Successful: FlexCluster is Live!")
except Exception as e:
    print(f"❌ Connection Error: {e}")

# --- 2. THE CUSTOM UI STYLING ---
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

# --- 3. BACKEND LOGIC ---

def handle_initial_register(uname, fname):
    """Transitions from Name entry to Password entry"""
    if not uname or not fname:
        return gr.Column(visible=True), gr.Column(visible=False), "⚠️ Please enter a Username and Full Name."
    return gr.Column(visible=False), gr.Column(visible=True), f"Almost there, {fname}! Create a secure password."

def handle_final_submit(uname, fname, pwd):
    """The 'Register' logic: Saves to MongoDB and jumps to Login Tab"""
    if not pwd or len(pwd) < 6:
        return gr.Tabs(selected="signup_tab"), "❌ Password too short (min 6 characters)."
    
    # Check if user already exists in Abby's DB
    if users_col.find_one({"username": uname}):
        return gr.Tabs(selected="signup_tab"), "❌ Username already taken! Try another."

    # Create the user document
    new_user = {
        "username": uname,
        "full_name": fname,
        "password": pwd,  # Note: For a real launch, you'd use bcrypt to hash this
        "role": "patient",
        "created_at": "2026-02-21"
    }
    
    # PERMANENT STORAGE IN MONGODB
    users_col.insert_one(new_user)
    
    # Return: Switch to login tab, show success message
    return gr.Tabs(selected="login_tab"), f"✅ Welcome to the team, {uname}! Now login to start."

def handle_login(username, password):
    """Verification Logic: Queries MongoDB for the user"""
    user = users_col.find_one({"username": username, "password": password})
    
    if user:
        # Check if they have any saved exercise sessions
        sessions = sessions_col.count_documents({"username": username})
        return gr.Column(visible=True), f"✅ Logged in: **{user['full_name']}** | {sessions} Sessions Found"
    
    return gr.Column(visible=False), "❌ Invalid Credentials. Please register first."

# --- 4. THE INTERFACE ---
with gr.Blocks(theme=flex_theme, css=custom_css, title="FlexRight") as demo:
    
    gr.Markdown("# 🛡️ <span class='lavender-text'>FlexRight</span>")
    gr.Markdown("### AI-Powered Recovery & Skeletal Tracking")
    
    with gr.Tabs() as main_tabs:
        
        # --- SIGN UP TAB ---
        with gr.Tab("Sign Up", id="signup_tab"):
            # Step 1: Info
            with gr.Column(visible=True) as register_step:
                gr.Markdown("### 👤 Step 1: Create Your Profile")
                new_user_id = gr.Textbox(label="Username", placeholder="Choose a unique ID")
                full_name = gr.Textbox(label="Full Name", placeholder="Your legal name")
                register_btn = gr.Button("Register", variant="primary")
            
            # Step 2: Password (Hides step 1 when clicked)
            with gr.Column(visible=False) as password_step:
                gr.Markdown("### 🔐 Step 2: Set Your Security")
                new_pwd = gr.Textbox(label="Create Password", type="password")
                submit_btn = gr.Button("Complete Account Setup ✅", variant="primary")

            signup_status = gr.Markdown()

        # --- LOGIN TAB ---
        with gr.Tab("Login", id="login_tab"):
            gr.Markdown("### 🔐 Secure Sign-In")
            user_input = gr.Textbox(label="Username")
            pass_input = gr.Textbox(label="Password", type="password")
            login_btn = gr.Button("Login", variant="primary")
            login_msg = gr.Markdown("Please sign in to access the Gym.")

    # --- PROTECTED WORKSPACE (Hidden until login) ---
    with gr.Column(visible=False) as protected_view:
        with gr.Tab("The Gym"):
            gr.Markdown("## 🏋️ Your Recovery Workspace")
            with gr.Row():
                webcam = gr.Image(sources=["webcam"], streaming=True, label="Live AI Skeletal Feed")
                stats = gr.Label(label="Live Performance Metrics")
        
        with gr.Tab("Professional Portal"):
            gr.Markdown("## 🏥 Clinical Telemetry")
            client_id = gr.Dropdown(label="Authorized Client", choices=["Alex", "Jordan", "New User"])
            plot = gr.Plot(label="Recovery Progress (Last 30 Days)")

    # --- THE WIRING ---

    # 1. Register -> Reveal Password
    register_btn.click(
        fn=handle_initial_register, 
        inputs=[new_user_id, full_name], 
        outputs=[register_step, password_step, signup_status]
    )

    # 2. Submit -> Save to MongoDB & Jump to Login
    submit_btn.click(
        fn=handle_final_submit,
        inputs=[new_user_id, full_name, new_pwd],
        outputs=[main_tabs, signup_status]
    )

    # 3. Login -> Verify with MongoDB & Reveal Gym
    login_btn.click(
        fn=handle_login, 
        inputs=[user_input, pass_input], 
        outputs=[protected_view, login_msg]
    )

if __name__ == "__main__":
    demo.launch()
    demo.launch(share=True, inbrowser=True)