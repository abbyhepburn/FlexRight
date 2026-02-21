from ultralytics import YOLO
import cv2
import numpy as np
import tkinter as tk
from tkinter import messagebox
import time

# UI font presets
FONT_HEADER = cv2.FONT_HERSHEY_TRIPLEX
FONT_LARGE = cv2.FONT_HERSHEY_DUPLEX
FONT_MED = cv2.FONT_HERSHEY_SIMPLEX
FONT_SMALL = cv2.FONT_HERSHEY_COMPLEX_SMALL

# --- STEP 1: The Pop-up Menu (Member 1 UX) ---
exercise_choice = None
rep_goal = 10  # Default goal

def select_exercise(choice):
    global exercise_choice
    exercise_choice = choice
    root.destroy() # Closes the pop-up window

root = tk.Tk()
root.title("FlexRight Launcher")
root.geometry("460x320")
root.configure(bg="#F6F3FB")  # soft lavender background

# Fonts for launcher
LAUNCH_FONT_TITLE = ("Segoe UI", 16, "bold")
LAUNCH_FONT_LABEL = ("Segoe UI", 12)
LAUNCH_BTN_FONT = ("Segoe UI", 11)

label = tk.Label(root, text="Select Your Exercise", font=LAUNCH_FONT_TITLE, bg="#F6F3FB", fg="#3A2B5A")
label.pack(pady=12)

btn_frame = tk.Frame(root, bg="#F6F3FB")
btn_frame.pack(pady=6)

btn_curl = tk.Button(btn_frame, text="Bicep Curls", width=18, font=LAUNCH_BTN_FONT,
                     bg="#E6E6FA", fg="#3A2B5A", activebackground="#D9D4F6", bd=0,
                     command=lambda: select_exercise("curl"))
btn_curl.grid(row=0, column=0, padx=8, pady=6)

btn_squat = tk.Button(btn_frame, text="Squats", width=18, font=LAUNCH_BTN_FONT,
                     bg="#E6E6FA", fg="#3A2B5A", activebackground="#D9D4F6", bd=0,
                     command=lambda: select_exercise("squat"))
btn_squat.grid(row=0, column=1, padx=8, pady=6)

# Rep goal input
rep_label = tk.Label(root, text="Rep Goal:", font=LAUNCH_FONT_LABEL, bg="#F6F3FB", fg="#3A2B5A")
rep_label.pack(pady=(18, 6))

rep_var = tk.StringVar(value="10")
rep_entry = tk.Entry(root, textvariable=rep_var, font=LAUNCH_FONT_LABEL, width=8, justify='center')
rep_entry.pack(pady=4)

def set_rep_goal():
    global rep_goal, exercise_choice
    try:
        rep_goal = int(rep_var.get())
        if rep_goal < 1:
            rep_goal = 10
    except:
        rep_goal = 10
    # If user hasn't selected an exercise, default to curl
    if not exercise_choice:
        exercise_choice = "curl"
    root.destroy()

btn_start = tk.Button(root, text="Start Workout", width=20, font=LAUNCH_BTN_FONT,
                      bg="#8D7BE9", fg="#FFFFFF", activebackground="#6F55D9", bd=0, command=set_rep_goal)
btn_start.pack(pady=14)

root.mainloop()

# If the user closes the window without picking, default to curl
if not exercise_choice:
    exercise_choice = "curl"

# --- STEP 2: The Vision Logic ---
def calculate_angle(a, b, c):
    """Calculate angle between three points in degrees"""
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    return 360 - angle if angle > 180.0 else angle


def is_keypoint_valid(points, indices, confidence_threshold=0.5):
    """Check if all required keypoints indexes exist"""
    if points is None or len(points) == 0:
        return False
    return all(i < len(points) for i in indices)


def draw_skeleton(frame, points):
    """Draw the pose skeleton with lines and circles"""
    connections = [
        (0, 1), (0, 2), (1, 3), (2, 4),
        (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
        (5, 11), (6, 12), (11, 12),
        (11, 13), (13, 15), (12, 14), (14, 16)
    ]
    for start, end in connections:
        if start < len(points) and end < len(points):
            s = tuple(points[start].astype(int))
            e = tuple(points[end].astype(int))
            if s[0] > 0 and e[0] > 0:
                cv2.line(frame, s, e, (180, 200, 255), 2)
    for p in points:
        if p[0] > 0 and p[1] > 0:
            cv2.circle(frame, tuple(p.astype(int)), 4, (120, 40, 160), -1)


def draw_angle_arc(frame, p1, p2, p3, angle):
    p2 = tuple(p2.astype(int))
    cv2.circle(frame, p2, 10, (255, 255, 255), -1)
    cv2.putText(frame, f"{int(angle)} deg", (p2[0] + 15, p2[1] - 15), FONT_MED, 0.7, (40, 40, 40), 2, cv2.LINE_AA)

# Initialize model and camera
model = YOLO('yolov8n-pose.pt')
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cv2.namedWindow("FlexRight Coach", cv2.WINDOW_NORMAL)
cv2.resizeWindow("FlexRight Coach", 1280, 720)

counter = 0
stage = "START"
frame_height = None
frame_width = None
frame_count = 0
threshold_frames = 5
finished = False
finished_time = None

# Selection and per-arm pre-selection states
selected_arm = None
left_state = "START"
right_state = "START"
left_frame_count = 0
right_frame_count = 0

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break
    if frame_height is None:
        frame_height, frame_width = frame.shape[:2]

    results = model(frame, save=False, conf=0.5, verbose=False)
    angle = None

    if len(results) > 0 and results[0].keypoints is not None:
        r = results[0]
        if len(r.keypoints.xy) > 0:
            points = r.keypoints.xy[0].cpu().numpy()
            draw_skeleton(frame, points)

            if len(points) >= 16:
                if exercise_choice == "curl":
                    left_idx = [5, 7, 9]
                    right_idx = [6, 8, 10]
                    start_thresh, end_thresh = 160, 40

                    left_valid = is_keypoint_valid(points, left_idx)
                    right_valid = is_keypoint_valid(points, right_idx)

                    angle_left = calculate_angle(points[5], points[7], points[9]) if left_valid else None
                    angle_right = calculate_angle(points[6], points[8], points[10]) if right_valid else None

                    # If no arm selected yet, run per-arm small state machines
                    if selected_arm is None:
                        # left
                        if left_state == "START":
                            if angle_left is not None and angle_left < end_thresh:
                                left_frame_count += 1
                                if left_frame_count >= threshold_frames:
                                    left_state = "DOWN"
                                    left_frame_count = 0
                            else:
                                left_frame_count = 0
                        elif left_state == "DOWN":
                            if angle_left is not None and angle_left > start_thresh:
                                left_frame_count += 1
                                if left_frame_count >= threshold_frames:
                                    selected_arm = 'left'
                                    counter += 1
                                    stage = 'START'
                                    left_frame_count = 0
                            else:
                                left_frame_count = 0

                        # right
                        if right_state == "START":
                            if angle_right is not None and angle_right < end_thresh:
                                right_frame_count += 1
                                if right_frame_count >= threshold_frames:
                                    right_state = "DOWN"
                                    right_frame_count = 0
                            else:
                                right_frame_count = 0
                        elif right_state == "DOWN":
                            if angle_right is not None and angle_right > start_thresh:
                                right_frame_count += 1
                                if right_frame_count >= threshold_frames:
                                    selected_arm = 'right'
                                    counter += 1
                                    stage = 'START'
                                    right_frame_count = 0
                            else:
                                right_frame_count = 0

                    # once selected, use that arm for angle and counting
                    if selected_arm == 'left':
                        angle = angle_left
                        indices = left_idx
                        joint_idx = left_idx[1]
                    elif selected_arm == 'right':
                        angle = angle_right
                        indices = right_idx
                        joint_idx = right_idx[1]
                    else:
                        angle = None
                else:
                    indices = [11, 13, 15]
                    if is_keypoint_valid(points, indices):
                        angle = calculate_angle(points[11], points[13], points[15])
                        start_thresh, end_thresh = 170, 90
                        joint_idx = 13

                # shared rep state machine
                if angle is not None and not finished:
                    if stage == "START":
                        if angle < end_thresh:
                            frame_count += 1
                            if frame_count >= threshold_frames:
                                stage = "DOWN"
                                frame_count = 0
                        else:
                            frame_count = 0
                    elif stage == "DOWN":
                        if angle > start_thresh:
                            frame_count += 1
                            if frame_count >= threshold_frames:
                                stage = "START"
                                counter += 1
                                frame_count = 0
                        else:
                            frame_count = 0

                if angle is not None:
                    draw_angle_arc(frame, points[indices[0]], points[indices[1]], points[indices[2]], angle)

    # HUD - lavender translucent header
    overlay = frame.copy()
    hud_height = 130
    cv2.rectangle(overlay, (0, 0), (frame_width, hud_height), (250, 230, 250), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    purple_text = (130, 0, 75)
    cv2.putText(frame, f"{exercise_choice.upper()}", (20, 32), FONT_HEADER, 1.0, purple_text, 1, cv2.LINE_AA)
    cv2.putText(frame, f"Reps: {counter} / {rep_goal}", (20, 70), FONT_LARGE, 0.95, purple_text, 2, cv2.LINE_AA)

    pill_text = f"Status: {stage}"
    (tw, th), _ = cv2.getTextSize(pill_text, FONT_SMALL, 0.8, 2)
    pill_x = frame_width - tw - 40
    pill_y = 20
    pill_bg = (245, 240, 255)
    cv2.rectangle(frame, (pill_x - 10, pill_y - 25), (pill_x + tw + 10, pill_y + 5), pill_bg, -1)
    cv2.rectangle(frame, (pill_x - 10, pill_y - 25), (pill_x + tw + 10, pill_y + 5), (200,200,200), 1)
    status_color = purple_text
    cv2.putText(frame, pill_text, (pill_x, pill_y), FONT_SMALL, 0.8, status_color, 2, cv2.LINE_AA)

    # progress bar
    bar_w = 400
    bar_h = 18
    bar_x = (frame_width - bar_w) // 2
    bar_y = hud_height - 35
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (235, 230, 250), -1)
    if rep_goal > 0:
        prog = min(1.0, counter / rep_goal)
        prog_w = int(prog * bar_w)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + prog_w, bar_y + bar_h), (170, 80, 200), -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + bar_h), (200, 200, 200), 2)

    if angle is not None:
        angle_text = f"{int(angle)} deg"
        cv2.putText(frame, angle_text, (frame_width - 170, hud_height - 30), FONT_LARGE, 0.9, purple_text, 2, cv2.LINE_AA)

    hint_text = "Q: Quit  |  R: Reset"
    cv2.putText(frame, hint_text, (20, hud_height - 8), FONT_SMALL, 0.72, purple_text, 1, cv2.LINE_AA)

    if counter >= rep_goal and not finished:
        finished = True
        finished_time = time.time()

    if finished:
        cv2.rectangle(frame, (0, frame_height // 2 - 60), (frame_width, frame_height // 2 + 60), (160, 40, 140), -1)
        cv2.putText(frame, "WORKOUT COMPLETE!", (frame_width // 2 - 260, frame_height // 2 + 15), FONT_HEADER, 1.8, (255,255,255), 3, cv2.LINE_AA)
        if time.time() - finished_time > 1.6:
            break

    cv2.imshow("FlexRight Coach", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('r'):
        counter = 0
        stage = 'START'
        frame_count = 0
        selected_arm = None
        left_state = 'START'
        right_state = 'START'
        left_frame_count = 0
        right_frame_count = 0

cap.release()
cv2.destroyAllWindows()
print(f"Workout Complete! Total Reps: {counter} / {rep_goal}")
if counter >= rep_goal:
    print("🎉 Goal Reached! Great job!")
import sys
sys.exit(0)
