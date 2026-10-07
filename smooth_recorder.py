import os
import time
import json
import threading
import cv2
import numpy as np
from mss import mss
from pynput import mouse

# --- GET EXACT FOLDER PATH ---
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_VIDEO = os.path.join(PROJECT_DIR, "raw_recording.avi")
OUTPUT_METADATA = os.path.join(PROJECT_DIR, "mouse_log.json")
FPS = 30

mouse_data = []
is_recording = True
start_time = 0

def track_mouse():
    global start_time, is_recording, mouse_data

    def on_move(x, y):
        if is_recording:
            elapsed = time.time() - start_time
            mouse_data.append({"time": elapsed, "x": x, "y": y, "event": "move"})

    def on_click(x, y, button, pressed):
        if is_recording and pressed:
            elapsed = time.time() - start_time
            mouse_data.append({"time": elapsed, "x": x, "y": y, "event": "click"})

    with mouse.Listener(on_move=on_move, on_click=on_click) as listener:
        while is_recording:
            time.sleep(0.01)
        listener.stop()

def record_screen():
    global start_time, is_recording
    
    sct = mss()
    monitor = sct.monitors[1]
    width, height = monitor["width"], monitor["height"]

    # Use XVID codec for guaranteed Windows compatibility
    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    out = cv2.VideoWriter(OUTPUT_VIDEO, fourcc, FPS, (width, height))

    print("\n" + "="*50)
    print(" 🎥 RECORDING STARTED!")
    print(f" Saving output to: {OUTPUT_VIDEO}")
    print(" Press 'CTRL + C' in terminal to stop.")
    print("="*50 + "\n")

    start_time = time.time()

    mouse_thread = threading.Thread(target=track_mouse, daemon=True)
    mouse_thread.start()

    frame_duration = 1.0 / FPS

    try:
        while True:
            loop_start = time.time()
            
            sct_img = sct.grab(monitor)
            frame = np.array(sct_img)
            frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            out.write(frame_bgr)

            elapsed = time.time() - loop_start
            sleep_time = frame_duration - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    except KeyboardInterrupt:
        print("\nStopping recording...")
        is_recording = False

    out.release()

    with open(OUTPUT_METADATA, "w") as f:
        json.dump(mouse_data, f, indent=2)

    print("\n" + "="*50)
    print(" Recording complete!")
    print(f" Video saved: {OUTPUT_VIDEO}")
    print("="*50)

if __name__ == "__main__":
    record_screen()