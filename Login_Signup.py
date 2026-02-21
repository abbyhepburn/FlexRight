import gradio as gr

# --- MOCK LOGIC ---
def handle_sign_up(uname, fname, email, role):
    if not uname or not fname:
        return "❌ Error: Username and Name are required!"
    return f"✅ Success! {fname} ({uname}) registered. You can now go to the Login tab."

def handle_login(username, password):
    if len(username) > 2 and len(password) > 5:
        # If login works, we show a success message and "unlock" the app
        return gr.update(visible=True), gr.update(visible=False), f"Welcome back, {username}!"
    return gr.update(visible=False), gr.update(visible=True), "❌ Invalid Credentials"

# --- THE INTERFACE ---
with gr.Blocks(title="FlexRight: Secure AI Recovery") as demo:
    gr.Markdown("# 🛡️ FlexRight")
    
    # 1. THE SIGN UP TAB (Always Visible)
    with gr.Tab("Sign Up"):
        gr.Markdown("## 👤 Create New Account")
        with gr.Row():
            new_user_id = gr.Textbox(label="Username")
            full_name = gr.Textbox(label="Full Name")
        role_input = gr.Radio(choices=["patient", "trainer"], label="Role", value="patient")
        signup_btn = gr.Button("Register", variant="primary")
        signup_status = gr.Markdown()
        signup_btn.click(handle_sign_up, [new_user_id, full_name, gr.State(""), role_input], signup_status)

    # 2. THE LOGIN TAB (Always Visible)
    with gr.Tab("Login"):
        gr.Markdown("## 🔐 Access your Portal")
        user_input = gr.Textbox(label="Username")
        pass_input = gr.Textbox(label="Password", type="password")
        login_btn = gr.Button("Login")
        login_msg = gr.Markdown("Please login to see your workout and data.")

    # 3. THE PROTECTED CONTENT (Hidden by default)
    # We put the "real" app inside this Column so we can hide it all at once
    with gr.Column(visible=False) as protected_view:
        with gr.Tab("The Gym"):
            gr.Markdown("## User Workspace")
            webcam = gr.Image(sources=["webcam"], streaming=True)
            stats = gr.Label(label="Live Performance Metrics")

        with gr.Tab("Data Privacy"):
            gr.Markdown("## 🔐 Privacy Settings")
            share_input = gr.Textbox(label="Trainer ID")
            add_btn = gr.Button("Grant Access")
            
        with gr.Tab("Trainer Portal"):
            gr.Markdown("## 🏥 Professional Portal")
            client_id = gr.Dropdown(label="Authorized Client", choices=["Alex", "Jordan"])
            plot = gr.Plot(label="Telemetry")

    # LOGIC TO UNLOCK
    login_btn.click(
        fn=handle_login,
        inputs=[user_input, pass_input],
        outputs=[protected_view, login_msg] # This makes the protected_view visible!
    )

if __name__ == "__main__":
    # NOTICE: We removed 'auth=' from here so the app actually loads
    demo.launch(inbrowser=True, share=True)