import gradio as gr

# --- THE DYNAMIC DATABASE BRIDGE (Member 4 will fill these) ---

def check_credentials(username, password):
    # This checks MongoDB for ANY user
    # Logic: return True if user exists and password matches
    return len(username) > 2 and len(password) > 5 

def get_available_professionals():
    # Returns a list of all Trainers/Doctors in the system
    # Member 2 provides the list: db.users.find({"role": "trainer"})
    return ["Dr. Smith", "Coach Mike", "PT Sarah", "Clinic A"]

def get_authorized_patients(trainer_name):
    # Returns only patients who shared data with THIS trainer
    # Member 4 logic: db.users.find({"shared_with": trainer_name})
    if trainer_name:
        return ["Alex", "Jordan", "New Patient"]
    return []

# --- MEMBER 3: THE MULTI-ROLE INTERFACE ---

with gr.Blocks(title="FlexRight: Secure AI Recovery") as demo:
    gr.Markdown("# 🛡️ FlexRight")
    gr.Markdown("### Privacy-First AI Fitness")

    with gr.Tab("The Gym"):
        gr.Markdown("## User Workspace")
        with gr.Row():
            # Real-time webcam streaming for Member 1's logic
            webcam = gr.Image(sources=["webcam"], streaming=True, label="Live Feed")
            stats = gr.Label(label="Live Performance Metrics")
        
        # This is where Member 1's skeletal math function goes
        # webcam.stream(fn=Member1_function, inputs=webcam, outputs=stats)

    with gr.Tab("Data Privacy"):
        gr.Markdown("## 🔐 Your Data, Your Choice")
        gr.Markdown("Search and grant access to health professionals.")
        
        with gr.Row():
            share_input = gr.Textbox(label="Enter Trainer/Doctor ID", placeholder="Search by ID...")
            add_btn = gr.Button("Grant Access", variant="primary")
        
        # This list updates based on who is in the system
        access_list = gr.CheckboxGroup(
            label="Current Authorized Professionals", 
            choices=get_available_professionals()
        )
        
        status_msg = gr.Markdown()
        add_btn.click(fn=lambda x: f"✅ Access granted to {x}", inputs=share_input, outputs=status_msg)

    with gr.Tab("Trainer Portal"):
        gr.Markdown("## 🏥 Professional Portal")
        gr.Markdown("View telemetry for patients who have granted you access.")
        
        # This dropdown starts empty and populates dynamically
        client_id = gr.Dropdown(label="Select Authorized Client", choices=[])
        
        # Trigger to refresh the list based on permissions
        refresh_btn = gr.Button("Find My Clients")
        refresh_btn.click(fn=get_authorized_patients, inputs=client_id, outputs=client_id)
        
        plot = gr.Plot(label="Recovery Telemetry (Skeletal Angles)")

# --- THE SECURE LAUNCH ---
if __name__ == "__main__":
    # The 'auth' function allows ANYONE in the DB to log in
    demo.launch(
        inbrowser=True, 
        share=True, 
        auth=check_credentials,
        auth_message="Please log in to FlexRight to access your secure telemetry."
    )