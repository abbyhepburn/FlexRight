FlexRight: AI-Powered Recovery
FlexRight is an AI-driven physical therapy assistant designed to bridge the gap between clinical visits and home recovery. By turning a standard webcam into a high-precision digital coach, we ensure patients perform exercises with the correct form, making recovery safer and more data-driven.

Home recovery is often hindered by the lack of professional supervision. Many users are unsure if their form is correct, which can lead to injury or ineffective rehabilitation. We built FlexRight to provide the confidence of a professional trainer from the comfort of home.

Language: Python

AI & Computer Vision: Ultralytics (YOLOv8-Pose), OpenCV

Web Framework: Gradio

Database: MongoDB Atlas (NoSQL)

Mathematics: NumPy (Skeletal trigonometry)

Development Environment: VS Code

Real-Time Tracking: Maps 17 skeletal keypoints to monitor movement live.

Instant Feedback: Provides real-time rep counting and "stage" detection (e.g., Up/Down).

Joint Angle Analysis: Calculates precise angles to ensure the user reaches the required range of motion.

Cloud Sync: Securely saves workout session data to MongoDB for long-term progress tracking and clinical review.


Installation & Setup
Clone the repo: git clone https://github.com/your-username/FlexRight.git

Install dependencies: pip install -r requirements.txt

Run the app: python final.py
