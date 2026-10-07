import os
import sys
import time
import json
import threading
import tkinter as tk
from tkinter import messagebox
import cv2
import numpy as np
from mss import mss
from pynput import mouse

# --- FILE PATH SETUP ---
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
RAW_VIDEO = os.path.join(PROJECT_DIR, "raw_recording.mp4")
METADATA = os.path.join(PROJECT_DIR, "mouse_log.json")
FINAL_VIDEO = os.path.join(PROJECT_DIR, "final_smooth_recording.mp4")

# --- CAMERA & SMOOTHING SETTINGS ---
RECORD_FPS = 30.0             # Stable 30 FPS screen capture
DEFAULT_ZOOM = 1.0            # Normal full screen scale
CLICK_ZOOM = 1.55             # Zoom level on click (1.55x)
CAM_SMOOTHING = 0.06          # Liquid camera movement factor (Lower = Smoother)
ZOOM_SMOOTHING = 0.07         # Smooth zoom-in / zoom-out transition speed

is_recording = False
mouse_data = []
start_time = 0

def track_mouse():
    """Captures every single mouse movement and click with exact timestamps."""
    global start_time, is_recording, mouse_data
    
    def on_move(x, y):
        if is_recording:
            mouse_data.append({"time": time.time() - start_time, "x": x, "y": y, "event": "move"})
            
    def on_click(x, y, button, pressed):
        if is_recording and pressed:
            mouse_data.append({"time": time.time() - start_time, "x": x, "y": y, "event": "click"})

    with mouse.Listener(on_move=on_move, on_click=on_click) as listener:
        while is_recording:
            time.sleep(0.005)
        listener.stop()

def record_loop():
    """Captures raw video frames consistently without dropping fps."""
    global start_time, is_recording, mouse_data
    mouse_data = []
    
    sct = mss()
    monitor = sct.monitors[1]
    width, height = monitor["width"], monitor["height"]
    
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(RAW_VIDEO, fourcc, RECORD_FPS, (width, height))

    if not out.isOpened():
        print("Error: Could not start video recorder.")
        return

    start_time = time.time()
    threading.Thread(target=track_mouse, daemon=True).start()

    frame_interval = 1.0 / RECORD_FPS
    next_frame_time = time.time()

    while is_recording:
        now = time.time()
        if now >= next_frame_time:
            sct_img = sct.grab(monitor)
            frame = cv2.cvtColor(np.array(sct_img), cv2.COLOR_BGRA2BGR)
            out.write(frame)
            next_frame_time += frame_interval
        else:
            time.sleep(0.002)

    out.release()

    with open(METADATA, "w") as f:
        json.dump(mouse_data, f, indent=2)

def render_smooth():
    """Renders the final video with liquid camera panning and cluster click zoom."""
    if not os.path.exists(RAW_VIDEO) or os.path.getsize(RAW_VIDEO) == 0:
        return False, "Raw video file is missing or empty."

    try:
        with open(METADATA, "r") as f:
            events = json.load(f)
    except Exception as e:
        return False, f"Error loading mouse log: {e}"

    cap = cv2.VideoCapture(RAW_VIDEO)
    if not cap.isOpened():
        return False, "Could not open raw recording file."

    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS) or RECORD_FPS

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(FINAL_VIDEO, fourcc, fps, (width, height))

    # Initialize camera position at center of screen
    cam_x, cam_y = width / 2.0, height / 2.0
    current_zoom = DEFAULT_ZOOM
    frame_idx = 0

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        c_time = frame_idx / fps
        
        # 1. Get current mouse position
        pos = None
        for e in events:
            if e["time"] <= c_time:
                pos = (e["x"], e["y"])
            else:
                break

        # 2. Capture ALL clicks happening within a 2.2-second window
        recent_clicks = [e for e in events if e["event"] == "click" and (0 <= c_time - e["time"] <= 2.2)]

        if recent_clicks:
            target_zoom = CLICK_ZOOM
            # If fast clicks happen in multiple spots, focus smoothly on their average center
            target_x = sum(c["x"] for c in recent_clicks) / len(recent_clicks)
            target_y = sum(c["y"] for c in recent_clicks) / len(recent_clicks)
        else:
            target_zoom = DEFAULT_ZOOM
            target_x, target_y = pos if pos else (cam_x, cam_y)

        # 3. Liquid Camera Interpolation (Lerp Engine)
        cam_x += (target_x - cam_x) * CAM_SMOOTHING
        cam_y += (target_y - cam_y) * CAM_SMOOTHING
        current_zoom += (target_zoom - current_zoom) * ZOOM_SMOOTHING

        # 4. Crop & Scale Frame
        crop_w = int(width / current_zoom)
        crop_h = int(height / current_zoom)

        min_x = max(0, min(int(cam_x - crop_w / 2), width - crop_w))
        min_y = max(0, min(int(cam_y - crop_h / 2), height - crop_h))

        cropped = frame[min_y:min_y + crop_h, min_x:min_x + crop_w]
        zoomed = cv2.resize(cropped, (width, height), interpolation=cv2.INTER_CUBIC)

        # 5. Draw Cursor Ring Overlay
        if pos:
            cx = int((pos[0] - min_x) * (width / crop_w))
            cy = int((pos[1] - min_y) * (height / crop_h))
            
            # Pointer Ring
            cv2.circle(zoomed, (cx, cy), 10, (255, 255, 255), -1)
            cv2.circle(zoomed, (cx, cy), 12, (0, 140, 255), 2)
            
            # Click Ring Highlight
            if recent_clicks:
                cv2.circle(zoomed, (cx, cy), 22, (0, 255, 120), 3)

        out.write(zoomed)
        frame_idx += 1

    cap.release()
    out.release()
    return True, FINAL_VIDEO

# --- GUI INTERFACE ---
root = tk.Tk()
root.title("Smooth Recorder - Auto-Zoom")
root.geometry("360x200")
root.resizable(False, False)

status_label = tk.Label(root, text="Ready to record", font=("Segoe UI", 11))
status_label.pack(pady=15)

def start_rec():
    global is_recording
    is_recording = True
    status_label.config(text="🔴 Recording... Perform actions", fg="red")
    btn_start.config(state="disabled")
    btn_stop.config(state="normal")
    threading.Thread(target=record_loop, daemon=True).start()

def stop_rec():
    global is_recording
    is_recording = False
    status_label.config(text="⌛ Processing smooth video...", fg="orange")
    btn_stop.config(state="disabled")
    root.update()

    def process():
        time.sleep(0.5)
        success, result_msg = render_smooth()
        if success:
            status_label.config(text="✅ Complete! Smooth video rendered.", fg="green")
            messagebox.showinfo("Success", f"Smooth recording saved at:\n{result_msg}")
        else:
            status_label.config(text="❌ Rendering Failed", fg="red")
            messagebox.showerror("Error", f"Failed to generate video:\n{result_msg}")
            
        btn_start.config(state="normal")

    threading.Thread(target=process, daemon=True).start()

btn_start = tk.Button(root, text="Start Recording", command=start_rec, width=22, bg="#0078D4", fg="white", font=("Segoe UI", 10, "bold"))
btn_start.pack(pady=5)

btn_stop = tk.Button(root, text="Stop & Render", command=stop_rec, width=22, state="disabled", font=("Segoe UI", 10))
btn_stop.pack(pady=5)

root.mainloop()