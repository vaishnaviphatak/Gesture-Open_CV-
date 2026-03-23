import streamlit as st
import cv2
import os
import numpy as np
import time
import glob
import speech_recognition as sr
from PIL import Image
from hand_gesture_opencv import HandGesture
from gesture_controller import GestureController
from document_analyzer import analyze_image

# Page Config
st.set_page_config(layout="wide", page_title="ICU Touchless Monitor", page_icon="🏥")

# Custom CSS for ICU High Contrast Theme
st.markdown("""
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    .critical-alert { background-color: #FF0000; color: #FFFFFF; padding: 20px; border-radius: 10px; font-size: 24px; font-weight: bold; animation: blink 1s infinite; }
    .normal-status { background-color: #00FF00; color: #000000; padding: 10px; border-radius: 5px; font-weight: bold; }
    @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
    .big-font { font-size: 40px !important; font-weight: bold; }
    .gesture-box { border: 2px solid #00FFFF; padding: 10px; border-radius: 5px; text-align: center; }
    </style>
""", unsafe_allow_html=True)



# Initialize Session State
if "detector" not in st.session_state:
    st.session_state.detector = HandGesture()
if "controller" not in st.session_state:
    st.session_state.controller = GestureController()
if "locked" not in st.session_state:
    st.session_state.locked = False
if "alerts" not in st.session_state:
    st.session_state.alerts = []
if "report_images" not in st.session_state:
    st.session_state.report_images = []
if "current_page" not in st.session_state:
    st.session_state.current_page = 0
if "zoom_scale" not in st.session_state:
    st.session_state.zoom_scale = 1.0
if "pending_audio" not in st.session_state:
    st.session_state.pending_audio = None
if "last_prescription" not in st.session_state:
    st.session_state.last_prescription = None
    
# --- SIDEBAR ---
with st.sidebar:
    st.title("🏥 ICU Controls")
    st.markdown("---")
    st.markdown("**Gestures:**")
    st.markdown("🖐 **OPEN PALM**: Load Reports")
    st.markdown("☝ **ONE FINGER**: Next Image")
    st.markdown("✌ **TWO FINGERS**: Analyze Current")
    st.markdown("👌 **PINCH**: Zoom In/Out")
    st.markdown("✊ **FIST**: Lock System")
    st.markdown("---")
    
    st.markdown("**🎙️ Voice Prescription:**")
    audio_value = st.audio_input("Record Prescription")
    if audio_value and audio_value != st.session_state.pending_audio:
        st.session_state.pending_audio = audio_value
        st.rerun()
    if st.session_state.last_prescription:
        if st.session_state.last_prescription.startswith("⚠️"):
            st.error(st.session_state.last_prescription)
        else:
            st.success(f"Saved: {st.session_state.last_prescription}")
    st.markdown("---")
    
    lock_status = "🔒 LOCKED" if st.session_state.locked else "🔓 ACTIVE"
    st.metric("System Status", lock_status)
    if st.session_state.locked:
        if st.button("Manual Unlock"):
            st.session_state.locked = False
            st.rerun()

# --- Process pending prescription audio (before camera loop blocks) ---
if st.session_state.pending_audio:
    try:
        r = sr.Recognizer()
        with sr.AudioFile(st.session_state.pending_audio) as source:
            audio_data = r.record(source)
        text = r.recognize_google(audio_data)
        st.session_state.last_prescription = text
        os.makedirs("Patients_data", exist_ok=True)
        with open("Patients_data/data1.txt", "a") as f:
            f.write(text + "\n")
    except sr.UnknownValueError:
        st.session_state.last_prescription = "⚠️ Could not understand audio"
    except sr.RequestError as e:
        st.session_state.last_prescription = f"⚠️ Speech service error: {e}"
    except Exception as e:
        st.session_state.last_prescription = f"⚠️ Error: {e}"
    finally:
        st.session_state.pending_audio = None

# --- MAIN LAYOUT ---
col_cam, col_doc = st.columns([1, 1])

with col_cam:
    st.subheader("Live Feed & Gestures")
    cam_placeholder = st.empty()
    
    # Debug Info
    st.write("Debug Info:")
    m_col1, m_col2, m_col3 = st.columns(3)
    metric_gesture = m_col1.empty()
    metric_action = m_col2.empty()
    metric_count = m_col3.empty()

with col_doc:
    st.subheader("Patient Report View")
    doc_placeholder = st.empty()
    alert_placeholder = st.empty()

# --- CAMERA CONTROL & LOOP ---
col_control, col_status = st.columns([1, 4])
with col_control:
    run_camera = st.checkbox("Start System", value=True)
with col_status:
    report_count = len(glob.glob("icu_reports/*.png"))
    st.info(f"📁 ICU Reports Found: {report_count}")

if run_camera:
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        st.error("Camera not accessible!")
    else:
        while run_camera:
            ret, frame = cap.read()
            if not ret:
                st.error("Camera feed lost.")
                break

            frame = cv2.flip(frame, 1)
            
            # 1. Detect Gesture
            gesture = st.session_state.detector.detect_gesture(frame)
            
            # 2. Add Overlay
            cv2.putText(frame, f"GESTURE: {gesture}", (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
            
            # 3. Process Action
            if st.session_state.controller.should_lock() and not st.session_state.locked:
                 st.session_state.locked = True
                 st.toast("Auto-locked due to inactivity", icon="🔒")
            
            # 3. Process Action
            detector = st.session_state.detector
            temp_action = st.session_state.controller.execute(
                gesture, 
                finger_count=detector.finger_count, 
                norm_pinch_dist=detector.norm_pinch_dist
            )
            
            action = "NO_ACTION"
            if st.session_state.locked:
                if temp_action == "OPEN_DOCUMENT":
                    st.session_state.locked = False
                    action = "OPEN_DOCUMENT" # Proceed to load/reload reports
                    st.toast("System Unlocked", icon="🔓")
                else:
                    cv2.putText(frame, "SYSTEM LOCKED", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            else:
                action = temp_action
                
                if action == "LOCK_SYSTEM":
                    st.session_state.locked = True
                    st.toast("System Locked by Gesture", icon="🔒")
                
                elif action == "OPEN_DOCUMENT":
                    # Load images from directory
                    img_files = sorted(glob.glob("icu_reports/*.png"))
                    if img_files:
                        st.session_state.report_images = img_files
                        st.session_state.current_page = 0
                        st.session_state.zoom_scale = 1.0 # Reset zoom
                        st.session_state.alerts = [] # Reset alerts on reload
                        st.toast("ICU Reports Loaded", icon="✅")
                    else:
                        st.toast("No images in icu_reports/!", icon="⚠️")

                elif action == "NEXT_PAGE":
                    if st.session_state.report_images:
                        st.session_state.current_page = (st.session_state.current_page + 1) % len(st.session_state.report_images)
                        st.session_state.alerts = [] # Clear alerts when turning page
                
                elif action == "ANALYZE":
                    if st.session_state.report_images:
                        current_img_path = st.session_state.report_images[st.session_state.current_page]
                        with st.spinner(f"Analyzing {os.path.basename(current_img_path)}..."):
                            st.session_state.alerts = analyze_image(current_img_path)
                        st.toast("Analysis Complete", icon="📊")

                elif action == "ZOOM":
                    detector = st.session_state.detector
                    if detector.thumb_tip_coords and detector.index_tip_coords:
                        cv2.line(frame, detector.thumb_tip_coords, detector.index_tip_coords, (255, 0, 255), 3)
                        cv2.circle(frame, detector.thumb_tip_coords, 6, (0, 255, 0), -1)
                        cv2.circle(frame, detector.index_tip_coords, 6, (0, 255, 0), -1)
                        
                        # Calculate and update zoom scale
                        old_pinch = st.session_state.controller.prev_pinch_dist
                        st.session_state.zoom_scale = st.session_state.controller.process_zoom(detector.smooth_pinch_dist)
                        
                        # On-screen visual feedback
                        if old_pinch is not None:
                            curr = detector.smooth_pinch_dist
                            # Use a very low threshold for immediate feedback
                            if abs(curr - old_pinch) > 0.0005: 
                                txt = "ZOOMING IN" if curr > old_pinch else "ZOOMING OUT"
                                cv2.putText(frame, txt, (10, 150), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 255, 0), 3)

            if action != "NO_ACTION" and not st.session_state.locked:
                cv2.putText(frame, f"ACTION: {action}", (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

            # Display Feed
            cam_placeholder.image(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB), channels="RGB", use_container_width=True)
            
            # Debug Metrics
            metric_gesture.metric("Raw Gesture", gesture)
            metric_action.metric("Action", action)
            metric_count.metric("Count", st.session_state.detector.consecutive_count)
            
            # Document Display
            if st.session_state.report_images:
                img_path = st.session_state.report_images[st.session_state.current_page]
                img = cv2.imread(img_path)
                if img is not None:
                    scale = st.session_state.zoom_scale
                    h, w = img.shape[:2]
                    
                    if scale != 1.0:
                        # 1. Resize the image
                        new_w, new_h = int(w * scale), int(h * scale)
                        zoomed = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                        
                        # 2. Crop or Pad to original size (H, W) to keep centering
                        # Center of zoomed image:
                        cx, cy = new_w // 2, new_h // 2
                        
                        # Viewport bounds
                        x1 = max(0, cx - w // 2)
                        y1 = max(0, cy - h // 2)
                        x2 = min(new_w, x1 + w)
                        y2 = min(new_h, y1 + h)
                        
                        # Final crop
                        display_img = zoomed[y1:y2, x1:x2]
                        
                        # If zoom is < 1.0, pad to keep same canvas size
                        if scale < 1.0:
                            dh, dw = display_img.shape[:2]
                            top = (h - dh) // 2
                            bottom = h - dh - top
                            left = (w - dw) // 2
                            right = w - dw - left
                            display_img = cv2.copyMakeBorder(display_img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[0, 0, 0])
                    else:
                        display_img = img

                    doc_placeholder.image(cv2.cvtColor(display_img, cv2.COLOR_BGR2RGB), 
                                        caption=f"Report {st.session_state.current_page + 1} / {len(st.session_state.report_images)} | Zoom: {scale:.2f}x", 
                                        use_container_width=True)
                else:
                    doc_placeholder.error(f"Failed to load image: {img_path}")
            else:
                doc_placeholder.warning("⚠️ Show **OPEN_PALM** 🖐 to Load ICU Reports")
                
            # Alert Display
            if st.session_state.alerts:
                alert_html = ""
                for alert in st.session_state.alerts:
                    color = "#FF4B4B" if alert['status'] != "NORMAL" else "#00CC00"
                    alert_html += f"<div style='border: 2px solid {color}; margin: 5px; padding: 10px; background-color: #222;'>"
                    alert_html += f"<span style='font-size: 20px; font-weight: bold; color: {color}'>{alert['param']}</span><br>"
                    alert_html += f"<span style='font-size: 18px;'>{alert['value']} {alert['unit']}</span><br>"
                    alert_html += f"<span style='font-size: 14px; color: #888;'>Range: {alert['range']}</span> | "
                    alert_html += f"<span style='font-weight: bold; color: {color}'>{alert['status']}</span></div>"
                alert_placeholder.markdown(alert_html, unsafe_allow_html=True)
            
            time.sleep(0.01)

    cap.release()
