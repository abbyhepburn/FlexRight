import gradio as gr
import pymongo
import certifi
import os
import numpy as np
import cv2
from ultralytics import YOLO

# --- 1. INITIALIZATION ---
model = YOLO('yolov8n-pose.pt')
counter = 0
stage = "UP"

# --- 2. MONGODB CONNECTION ---
MONGO_URI = "mongodb+srv://abbyhepburn526:AbbyMay26!@flexcluster.sdbddiz.mongodb.net/?appName=FlexCluster"

try:
    client = pymongo.MongoClient(MONGO_URI, tlsCAFile=certifi.where(), serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
    db = client["FlexCluster"]
    users_col = db["users"]
    exercises_col = db["exercises"]
    sessions_col = db["sessions"]
    print("[OK] Connection Successful: FlexCluster is Live!")
except Exception as e:
    print(f"[ERROR] Connection Error: {e}")
    users_col = exercises_col = sessions_col = None

# --- 3. CUSTOM UI STYLING ---
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

# --- 4. BACKEND LOGIC ---

def calculate_angle(a, b, c):
    """Math logic for Member 1"""
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    return 360 - angle if angle > 180.0 else angle

def predict_pose(img):
    global counter, stage 
    
    if img is None:
        return None
    
    # Convert Gradio (RGB) to OpenCV (BGR)
    img_bgr = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    results = model(img_bgr, verbose=False)
    
    # Logic for counting
    for r in results:
        if r.keypoints is not None and len(r.keypoints.xy) > 0:
            points = r.keypoints.xy[0].cpu().numpy()
            
            # Check for Left Arm: Shoulder(5), Elbow(7), Wrist(9)
            if len(points) > 9:
                p5, p7, p9 = points[5], points[7], points[9]
                
                # Only calculate if points are visible (not [0,0])
                if p7[0] > 0 and p9[0] > 0:
                    angle = calculate_angle(p5, p7, p9)

                    # Curl State Machine
                    if angle > 160:
                        stage = "DOWN"
                    if angle < 30 and stage == "DOWN":
                        stage = "UP"
                        counter += 1

    # Get the skeleton drawing
    annotated_frame = results[0].plot()
    
    # Draw the count on the frame
    # (Using BGR colors: (75, 0, 130) is a deep purple)
    cv2.putText(annotated_frame, f"Reps: {counter}", (50, 80), 
                cv2.FONT_HERSHEY_DUPLEX, 1.5, (75, 0, 130), 3)
    cv2.putText(annotated_frame, f"Stage: {stage}", (50, 130), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 100, 100), 2)
                
    # Convert back to RGB for Gradio
    return cv2.cvtColor(annotated_frame, cv2.COLOR_BGR2RGB)

def handle_initial_register(uname, fname):
    if not uname or not fname:
        return gr.Column(visible=True), gr.Column(visible=False), "[WARNING] Please enter a Username and Full Name."
    return gr.Column(visible=False), gr.Column(visible=True), f"Almost there, {fname}! Create a secure password."

def handle_final_submit(uname, fname, pwd):
    if not pwd or len(pwd) < 6:
        return gr.Tabs(selected="signup_tab"), "[ERROR] Password too short (min 6 characters)."
    if users_col is None:
        return gr.Tabs(selected="signup_tab"), "[WARNING] Database offline."
    
    if users_col.find_one({"username": uname}):
        return gr.Tabs(selected="signup_tab"), "[ERROR] Username already taken!"

    new_user = {
        "username": uname, "full_name": fname, "password": pwd,
        "role": "patient", "created_at": "2026-02-21"
    }
    users_col.insert_one(new_user)
    return gr.Tabs(selected="login_tab"), f"[OK] Welcome, {uname}! Now login."

def handle_login(username, password):
    DEMO_CREDENTIALS = {"demo": "demo123", "test": "test123"}
    if username in DEMO_CREDENTIALS and DEMO_CREDENTIALS[username] == password:
        return gr.Column(visible=True), f"[OK] Demo Login Successful! Welcome, {username}!"
    
    if users_col is not None:
        user = users_col.find_one({"username": username, "password": password})
        if user:
            return gr.Column(visible=True), f"[OK] Logged in: **{user['full_name']}**"
    
    return gr.Column(visible=False), "[ERROR] Invalid Credentials."

# --- 5. THE INTERFACE ---
with gr.Blocks(title="FlexRight", theme=flex_theme, css=custom_css) as demo:
    
    gr.Markdown("# 🛡️ <span class='lavender-text'>FlexRight</span>")
    gr.Markdown("### AI-Powered Recovery & Skeletal Tracking")
    
    with gr.Tabs() as main_tabs:
        
        # --- SIGN UP TAB ---
        with gr.Tab("Sign Up", id="signup_tab"):
            with gr.Column(visible=True) as register_step:
                gr.Markdown("### 👤 Step 1: Create Your Profile")
                new_user_id = gr.Textbox(label="Username")
                full_name = gr.Textbox(label="Full Name")
                register_btn = gr.Button("Register", variant="primary")
            
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

    # --- PROTECTED WORKSPACE ---
    with gr.Column(visible=False) as protected_view:
        with gr.Tabs():
            with gr.Tab("The Gym"):
                gr.Markdown("## Live AI Skeletal Tracking")
                webcam = gr.Image(sources=["webcam"], streaming=True, label="AI Feed")
                # Wiring the stream
                webcam.stream(fn=predict_pose, inputs=webcam, outputs=webcam, time_interval=0.1)
                workout_status = gr.Markdown("Position yourself in the camera to see the tracking.")

            with gr.Tab("Professional Portal"):
                gr.Markdown("## [HOSPITAL] Clinical Telemetry")
                client_id = gr.Dropdown(label="Authorized Client", choices=["Alex", "Jordan", "New User"])
                gr.Markdown("*(Database Reports loading...)*")

    # --- THE WIRING ----
    register_btn.click(fn=handle_initial_register, inputs=[new_user_id, full_name], outputs=[register_step, password_step, signup_status])
    submit_btn.click(fn=handle_final_submit, inputs=[new_user_id, full_name, new_pwd], outputs=[main_tabs, signup_status])
    login_btn.click(fn=handle_login, inputs=[user_input, pass_input], outputs=[protected_view, login_msg])

if __name__ == "__main__":
    demo.launch(share=True)