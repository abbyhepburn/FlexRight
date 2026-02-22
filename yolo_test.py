from ultralytics import YOLO
import cv2
import numpy as np
import tkinter as tk
import time
import sys
import json
import os

# Get User ID from command line arguments
USER_ID = sys.argv[1] if len(sys.argv) > 1 else "guest_user"
# UI font presets
FONT_HEADER = cv2.FONT_HERSHEY_TRIPLEX
FONT_LARGE  = cv2.FONT_HERSHEY_DUPLEX
FONT_MED    = cv2.FONT_HERSHEY_SIMPLEX
FONT_SMALL  = cv2.FONT_HERSHEY_COMPLEX_SMALL

# User ID passed from finaltest.py (optional – falls back to "guest")
user_id = sys.argv[1] if len(sys.argv) > 1 else "guest"

# --- STEP 1: Exercise selector pop-up ---
exercise_choice = None
rep_goal = 10

def select_exercise(choice):
    global exercise_choice, rep_goal
    exercise_choice = choice
    try:
        rep_goal = int(rep_var.get())
        if rep_goal < 1:
            rep_goal = 10
    except:
        rep_goal = 10
    root.destroy()

root = tk.Tk()
root.title("FlexRight Launcher")
root.geometry("460x380")
root.configure(bg="#F6F3FB")

LAUNCH_FONT_TITLE = ("Segoe UI", 16, "bold")
LAUNCH_FONT_LABEL = ("Segoe UI", 12)
LAUNCH_BTN_FONT   = ("Segoe UI", 11)

tk.Label(root, text="Select Your Exercise", font=LAUNCH_FONT_TITLE,
         bg="#F6F3FB", fg="#3A2B5A").pack(pady=12)

btn_frame = tk.Frame(root, bg="#F6F3FB")
btn_frame.pack(pady=6)

tk.Button(btn_frame, text="Bicep Curls", width=18, font=LAUNCH_BTN_FONT,
          bg="#E6E6FA", fg="#3A2B5A", activebackground="#D9D4F6", bd=0,
          command=lambda: select_exercise("curl")).grid(row=0, column=0, padx=8, pady=6)

tk.Button(btn_frame, text="Squats", width=18, font=LAUNCH_BTN_FONT,
          bg="#E6E6FA", fg="#3A2B5A", activebackground="#D9D4F6", bd=0,
          command=lambda: select_exercise("squat")).grid(row=0, column=1, padx=8, pady=6)

tk.Button(btn_frame, text="Push-ups", width=18, font=LAUNCH_BTN_FONT,
          bg="#E6E6FA", fg="#3A2B5A", activebackground="#D9D4F6", bd=0,
          command=lambda: select_exercise("pushup")).grid(row=1, column=0, padx=8, pady=6)

tk.Button(btn_frame, text="Lateral Raises", width=18, font=LAUNCH_BTN_FONT,
          bg="#E6E6FA", fg="#3A2B5A", activebackground="#D9D4F6", bd=0,
          command=lambda: select_exercise("lateral")).grid(row=1, column=1, padx=8, pady=6)

tk.Label(root, text="Rep Goal:", font=LAUNCH_FONT_LABEL,
         bg="#F6F3FB", fg="#3A2B5A").pack(pady=(18, 6))

rep_var = tk.StringVar(value="10")
tk.Entry(root, textvariable=rep_var, font=LAUNCH_FONT_LABEL,
         width=8, justify='center').pack(pady=4)

root.mainloop()

if not exercise_choice:
    exercise_choice = "curl"

# --- STEP 2: Vision helpers ---
def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    return 360 - angle if angle > 180.0 else angle

def is_keypoint_valid(points, indices):
    if points is None or len(points) == 0:
        return False
    return all(i < len(points) for i in indices)

def draw_skeleton(frame, points):
    connections = [
        (0,1),(0,2),(1,3),(2,4),
        (5,6),(5,7),(7,9),(6,8),(8,10),
        (5,11),(6,12),(11,12),
        (11,13),(13,15),(12,14),(14,16)
    ]
    for s, e in connections:
        if s < len(points) and e < len(points):
            sp = tuple(points[s].astype(int))
            ep = tuple(points[e].astype(int))
            if sp[0] > 0 and ep[0] > 0:
                cv2.line(frame, sp, ep, (180, 200, 255), 2)
    for p in points:
        if p[0] > 0 and p[1] > 0:
            cv2.circle(frame, tuple(p.astype(int)), 4, (120, 40, 160), -1)

def draw_angle_arc(frame, p1, p2, p3, angle):
    p2i = tuple(p2.astype(int))
    cv2.circle(frame, p2i, 10, (255, 255, 255), -1)
    cv2.putText(frame, f"{int(angle)} deg", (p2i[0]+15, p2i[1]-15),
                FONT_MED, 0.7, (40, 40, 40), 2, cv2.LINE_AA)

# --- STEP 3: Model + camera ---
model = YOLO('yolov8n-pose.pt')
cap = cv2.VideoCapture(0)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
cv2.namedWindow("FlexRight Coach", cv2.WINDOW_NORMAL)
cv2.resizeWindow("FlexRight Coach", 1280, 720)

# --- STEP 4: Countdown ---
COUNTDOWN_SECONDS = 5
countdown_start = time.time()

while True:
    ret, frame = cap.read()
    if not ret:
        break
    h, w = frame.shape[:2]
    elapsed   = time.time() - countdown_start
    remaining = COUNTDOWN_SECONDS - int(elapsed)

    overlay = frame.copy()
    cv2.rectangle(overlay, (0, 0), (w, h), (30, 10, 50), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    if remaining > 0:
        msg = "Get Into Position!"
        (mw, _), _ = cv2.getTextSize(msg, FONT_HEADER, 1.4, 2)
        cv2.putText(frame, msg, ((w-mw)//2, h//2-60),
                    FONT_HEADER, 1.4, (255, 255, 255), 2, cv2.LINE_AA)
        num = str(remaining)
        (nw, _), _ = cv2.getTextSize(num, FONT_HEADER, 5.0, 4)
        cv2.putText(frame, num, ((w-nw)//2, h//2+80),
                    FONT_HEADER, 5.0, (200, 130, 255), 4, cv2.LINE_AA)
    else:
        go = "GO!"
        (gw, _), _ = cv2.getTextSize(go, FONT_HEADER, 5.0, 4)
        cv2.putText(frame, go, ((w-gw)//2, h//2+40),
                    FONT_HEADER, 5.0, (100, 255, 150), 4, cv2.LINE_AA)
        cv2.imshow("FlexRight Coach", frame)
        cv2.waitKey(600)
        break

    cv2.imshow("FlexRight Coach", frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        cap.release()
        cv2.destroyAllWindows()
        sys.exit(0)

# --- STEP 5: Workout state ---
counter      = 0
stage        = "START"
frame_height = None
frame_width  = None
frame_count  = 0
threshold_frames = 3
finished     = False
finished_time = None

selected_arm    = None
left_state      = "START"
right_state     = "START"
left_frame_count  = 0
right_frame_count = 0

# Warning tracking
warnings_log      = []
last_warning_time = 0.0
WARNING_COOLDOWN  = 1.5

CURL_OVER_THRESH   = 170   # warn if angle reaches here (overextension)
CURL_UNDER_THRESH  = 20    # warn if angle drops to here (underextension)
SQUAT_OVER_THRESH  = 110   # warn if not squatting past here at bottom
SQUAT_UNDER_THRESH = 55    # warn if squatting dangerously deep

active_warning_text  = ""
active_warning_color = (0, 0, 255)
active_warning_until = 0.0

# Rep congratulation state
congrat_text  = ""
congrat_until = 0.0
CONGRATS = [
    "Great rep!", "Keep it up!", "Nice work!", "You're crushing it!",
    "Awesome!", "Stay strong!", "One more!", "Let's go!"
]
congrat_idx = 0

def check_form_warnings(angle, stage, rep_count, exercise):
    if exercise == "curl":
        if stage == "DOWN" and angle < CURL_UNDER_THRESH:
            return ("underextension",
                    f"Underextended – arm not fully extended ({int(angle)} deg)",
                    (0, 80, 255))
        if stage == "START" and angle > CURL_OVER_THRESH:
            return ("overextension",
                    f"Overextended – curl higher ({int(angle)} deg)",
                    (0, 165, 255))
    elif exercise == "squat":
        if stage == "DOWN":
            if angle > SQUAT_OVER_THRESH:
                return ("overextension",
                        f"Overextended – squat deeper ({int(angle)} deg)",
                        (0, 165, 255))
            if angle < SQUAT_UNDER_THRESH:
                return ("underextension",
                        f"Underextended – too deep, risk of injury ({int(angle)} deg)",
                        (0, 80, 255))
    return None

# --- STEP 6: Main workout loop ---
while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break
    if frame_height is None:
        frame_height, frame_width = frame.shape[:2]

    results = model(frame, save=False, conf=0.5, verbose=False)
    angle   = None
    indices = None

    if len(results) > 0 and results[0].keypoints is not None:
        r = results[0]
        if len(r.keypoints.xy) > 0:
            points = r.keypoints.xy[0].cpu().numpy()
            draw_skeleton(frame, points)

            if len(points) >= 16:
                if exercise_choice == "curl":
                    left_idx  = [5, 7, 9]
                    right_idx = [6, 8, 10]
                    start_thresh, end_thresh = 150, 55

                    left_valid  = is_keypoint_valid(points, left_idx)
                    right_valid = is_keypoint_valid(points, right_idx)
                    angle_left  = calculate_angle(points[5], points[7], points[9])  if left_valid  else None
                    angle_right = calculate_angle(points[6], points[8], points[10]) if right_valid else None

                    if selected_arm is None:
                        if left_state == "START":
                            if angle_left is not None and angle_left < end_thresh:
                                left_frame_count += 1
                                if left_frame_count >= threshold_frames:
                                    left_state = "DOWN"; left_frame_count = 0
                            else:
                                left_frame_count = 0
                        elif left_state == "DOWN":
                            if angle_left is not None and angle_left > start_thresh:
                                left_frame_count += 1
                                if left_frame_count >= threshold_frames:
                                    selected_arm = 'left'; counter += 1
                                    stage = 'START'; left_frame_count = 0
                                    congrat_text  = CONGRATS[congrat_idx % len(CONGRATS)]
                                    congrat_until = time.time() + 1.8
                                    congrat_idx  += 1
                            else:
                                left_frame_count = 0

                        if right_state == "START":
                            if angle_right is not None and angle_right < end_thresh:
                                right_frame_count += 1
                                if right_frame_count >= threshold_frames:
                                    right_state = "DOWN"; right_frame_count = 0
                            else:
                                right_frame_count = 0
                        elif right_state == "DOWN":
                            if angle_right is not None and angle_right > start_thresh:
                                right_frame_count += 1
                                if right_frame_count >= threshold_frames:
                                    selected_arm = 'right'; counter += 1
                                    stage = 'START'; right_frame_count = 0
                                    congrat_text  = CONGRATS[congrat_idx % len(CONGRATS)]
                                    congrat_until = time.time() + 1.8
                                    congrat_idx  += 1
                            else:
                                right_frame_count = 0

                    if selected_arm == 'left':
                        angle = angle_left; indices = left_idx
                    elif selected_arm == 'right':
                        angle = angle_right; indices = right_idx
                else:
                    indices = [11, 13, 15]
                    if is_keypoint_valid(points, indices):
                        angle = calculate_angle(points[11], points[13], points[15])
                        start_thresh, end_thresh = 160, 100

                # Rep state machine
                if angle is not None and not finished:
                    rep_angles.append(angle) 
                    
                    if stage == "START":
                        if angle < end_thresh:
                            frame_count += 1
                            if frame_count >= threshold_frames:
                                stage = "DOWN"; frame_count = 0
                        else:
                            frame_count = 0
                            
                    elif stage == "DOWN":
                        if angle > start_thresh:
                            frame_count += 1
                            if frame_count >= threshold_frames:
                                stage = "START"; counter += 1; frame_count = 0
                                congrat_text  = CONGRATS[congrat_idx % len(CONGRATS)]
                                congrat_until = time.time() + 1.8
                                congrat_idx  += 1
                        else:
                            frame_count = 0

                # Warning check
                if angle is not None and not finished:
                    now = time.time()
                    if now - last_warning_time >= WARNING_COOLDOWN:
                        result = check_form_warnings(angle, stage, counter, exercise_choice)
                        if result:
                            wtype, wmsg, wcolor = result
                            warnings_log.append({"rep": counter, "type": wtype,
                                                  "message": wmsg, "time": now})
                            active_warning_text  = wmsg
                            active_warning_color = wcolor
                            active_warning_until = now + 2.5
                            last_warning_time    = now

                if angle is not None and indices is not None:
                    draw_angle_arc(frame, points[indices[0]], points[indices[1]],
                                   points[indices[2]], angle)

    # --- HUD ---
    overlay    = frame.copy()
    hud_height = 130
    cv2.rectangle(overlay, (0, 0), (frame_width, hud_height), (250, 230, 250), -1)
    cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

    purple = (130, 0, 75)
    cv2.putText(frame, exercise_choice.upper(), (20, 32),
                FONT_HEADER, 1.0, purple, 1, cv2.LINE_AA)
    cv2.putText(frame, f"Reps: {counter} / {rep_goal}", (20, 70),
                FONT_LARGE, 0.95, purple, 2, cv2.LINE_AA)

    pill = f"Status: {stage}"
    (tw, _), _ = cv2.getTextSize(pill, FONT_SMALL, 0.8, 2)
    px, py = frame_width - tw - 40, 20
    cv2.rectangle(frame, (px-10, py-25), (px+tw+10, py+5), (245,240,255), -1)
    cv2.rectangle(frame, (px-10, py-25), (px+tw+10, py+5), (200,200,200), 1)
    cv2.putText(frame, pill, (px, py), FONT_SMALL, 0.8, purple, 2, cv2.LINE_AA)

    bar_w, bar_h = 400, 18
    bar_x = (frame_width - bar_w) // 2
    bar_y = hud_height - 35
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x+bar_w, bar_y+bar_h), (235,230,250), -1)
    if rep_goal > 0:
        prog_w = int(min(1.0, counter/rep_goal) * bar_w)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x+prog_w, bar_y+bar_h), (170,80,200), -1)
    cv2.rectangle(frame, (bar_x, bar_y), (bar_x+bar_w, bar_y+bar_h), (200,200,200), 2)

    if angle is not None:
        cv2.putText(frame, f"{int(angle)} deg", (frame_width-170, hud_height-30),
                    FONT_LARGE, 0.9, purple, 2, cv2.LINE_AA)

    cv2.putText(frame, "Q: Quit  |  R: Reset", (20, hud_height-8),
                FONT_SMALL, 0.72, purple, 1, cv2.LINE_AA)

    now = time.time()

    # Congrats banner (green, bottom of HUD)
    if congrat_text and now < congrat_until:
        alpha = min(1.0, (congrat_until - now) / 0.5)  # fade out last 0.5 s
        cb_y1 = hud_height + 10
        cb_y2 = hud_height + 58
        cov = frame.copy()
        cv2.rectangle(cov, (0, cb_y1), (frame_width, cb_y2), (30, 160, 80), -1)
        cv2.addWeighted(cov, 0.75, frame, 0.25, 0, frame)
        (cw, _), _ = cv2.getTextSize(congrat_text, FONT_LARGE, 1.0, 2)
        cv2.putText(frame, congrat_text, ((frame_width-cw)//2, cb_y1+36),
                    FONT_LARGE, 1.0, (255, 255, 255), 2, cv2.LINE_AA)

    # Warning banner (below congrats if both active, otherwise same slot)
    warn_y1 = (hud_height + 68) if (congrat_text and now < congrat_until) else (hud_height + 10)
    if active_warning_text and now < active_warning_until:
        wov = frame.copy()
        cv2.rectangle(wov, (0, warn_y1), (frame_width, warn_y1+48),
                      active_warning_color, -1)
        cv2.addWeighted(wov, 0.72, frame, 0.28, 0, frame)
        (ww, _), _ = cv2.getTextSize(active_warning_text, FONT_LARGE, 0.85, 2)
        cv2.putText(frame, active_warning_text,
                    ((frame_width-ww)//2, warn_y1+32),
                    FONT_LARGE, 0.85, (255, 255, 255), 2, cv2.LINE_AA)

    if counter >= rep_goal and not finished:
        finished = True
        finished_time = time.time()

    if finished:
        cv2.rectangle(frame,
                      (0, frame_height//2-60), (frame_width, frame_height//2+60),
                      (160, 40, 140), -1)
        cv2.putText(frame, "WORKOUT COMPLETE!",
                    (frame_width//2-260, frame_height//2+15),
                    FONT_HEADER, 1.8, (255, 255, 255), 3, cv2.LINE_AA)
        if time.time() - finished_time > 1.6:
            break

    cv2.imshow("FlexRight Coach", frame)
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('r'):
        counter = 0; stage = 'START'; frame_count = 0
        selected_arm = None
        left_state = 'START'; right_state = 'START'
        left_frame_count = 0; right_frame_count = 0
        warnings_log.clear()
        active_warning_text = ""; active_warning_until = 0.0
        congrat_text = ""; congrat_until = 0.0; congrat_idx = 0

cap.release()
cv2.destroyAllWindows()

# --- STEP 7: Save session summary to a temp JSON file for the website ---
over_count  = sum(1 for w in warnings_log if w["type"] == "overextension")
under_count = sum(1 for w in warnings_log if w["type"] == "underextension")

session_summary = {
    "user_id":     user_id,
    "exercise":    exercise_choice,
    "reps":        counter,
    "rep_goal":    rep_goal,
    "warnings":    [{"rep": w["rep"], "type": w["type"], "message": w["message"]}
                    for w in warnings_log],
    "over_count":  over_count,
    "under_count": under_count,
    "timestamp":   time.strftime("%Y-%m-%d %H:%M:%S")
}

summary_path = os.path.join(os.path.dirname(__file__), "session_result.json")
with open(summary_path, "w") as f:
    json.dump(session_summary, f)

print(f"Session saved → {summary_path}")
sys.exit(0)
