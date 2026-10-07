import os
import cv2
import json
import numpy as np

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_VIDEO = os.path.join(PROJECT_DIR, "raw_recording.avi")
INPUT_METADATA = os.path.join(PROJECT_DIR, "mouse_log.json")
OUTPUT_VIDEO = os.path.join(PROJECT_DIR, "final_smooth_recording.avi")

DEFAULT_ZOOM = 1.0
CLICK_ZOOM = 1.6
ZOOM_SPEED = 0.08
SMOOTHING_FACTOR = 0.1

def load_mouse_log():
    try:
        with open(INPUT_METADATA, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Could not find metadata file at {INPUT_METADATA}")
        return []

def render_smooth_video():
    mouse_events = load_mouse_log()
    if not mouse_events:
        return

    cap = cv2.VideoCapture(INPUT_VIDEO)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0

    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, fps, (width, height))

    cam_x, cam_y = width / 2, height / 2
    target_x, target_y = cam_x, cam_y
    current_zoom = DEFAULT_ZOOM

    frame_idx = 0
    print("\n Rendering smooth auto-zoomed video... Please wait.")

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        current_time = frame_idx / fps

        active_clicks = []
        latest_mouse_pos = None

        for event in mouse_events:
            if event["time"] <= current_time:
                latest_mouse_pos = (event["x"], event["y"])
                if event["event"] == "click" and abs(current_time - event["time"]) < 1.0:
                    active_clicks.append(event)

        if latest_mouse_pos:
            target_x, target_y = latest_mouse_pos

        target_zoom = CLICK_ZOOM if active_clicks else DEFAULT_ZOOM

        cam_x += (target_x - cam_x) * SMOOTHING_FACTOR
        cam_y += (target_y - cam_y) * SMOOTHING_FACTOR
        current_zoom += (target_zoom - current_zoom) * ZOOM_SPEED

        crop_w = int(width / current_zoom)
        crop_h = int(height / current_zoom)

        min_x = max(0, min(int(cam_x - crop_w / 2), width - crop_w))
        min_y = max(0, min(int(cam_y - crop_h / 2), height - crop_h))

        cropped = frame[min_y : min_y + crop_h, min_x : min_x + crop_w]
        zoomed_frame = cv2.resize(cropped, (width, height), interpolation=cv2.INTER_CUBIC)

        if latest_mouse_pos:
            cursor_render_x = int((latest_mouse_pos[0] - min_x) * current_zoom)
            cursor_render_y = int((latest_mouse_pos[1] - min_y) * current_zoom)

            cv2.circle(zoomed_frame, (cursor_render_x, cursor_render_y), 10, (255, 255, 255), -1)
            cv2.circle(zoomed_frame, (cursor_render_x, cursor_render_y), 12, (0, 165, 255), 2)

            if active_clicks:
                cv2.circle(zoomed_frame, (cursor_render_x, cursor_render_y), 22, (0, 255, 0), 3)

        out.write(zoomed_frame)
        frame_idx += 1

    cap.release()
    out.release()
    print("="*50)
    print(f" SUCCESS! Video generated at:")
    print(f" {OUTPUT_VIDEO}")
    print("="*50)

if __name__ == "__main__":
    render_smooth_video()