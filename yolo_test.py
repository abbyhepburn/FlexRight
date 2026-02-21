from ultralytics import YOLO
import cv2

# Load a pre-trained Pose model (it will download automatically)
model = YOLO('yolov8n-pose.pt')

# Open the webcam
cap = cv2.VideoCapture(0)

print("--- YOLO Vision Starting... Press 'q' to exit ---")

while cap.isOpened():
    success, frame = cap.read()
    if not success:
        break

    # Run YOLOv8 pose detection
    results = model(frame, save=False, conf=0.5, verbose=False)

    # Visualize the results on the frame
    annotated_frame = results[0].plot()

    # Display the window
    cv2.imshow("FlexRight YOLO Test", annotated_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()