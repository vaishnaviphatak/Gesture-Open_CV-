# ICU Touchless Monitoring System - User Guide

This document explains the touchless gesture-based interface for the ICU Report Monitoring System. The system uses computer vision to detect hand gestures and perform actions without the need for physical contact.

## Hand Gestures & Functionality

### 🖐 OPEN PALM: Unlock & Load Reports
- **Action**: Initializes the system or **Unlocks** it if it's in a locked state.
- **Behavior**: 
    - If the system is **LOCKED**, showing an open palm will unlock it and simultaneously load/reload the reports.
    - If already unlocked, it scans for PNG files and displays the first report.
    - This action triggers **once** per palm gesture. To reload, you must remove your hand and show the palm again.
    - Use this to reset the view or start a new monitoring session.

### ☝ ONE FINGER: Navigation (Next Image)
- **Action**: Moves the display to the next available patient report.
- **Behavior**:
    - **Immediate Pop-up**: As soon as you show one finger (index), the system transitions to the next image immediately.
    - **Hold-to-Repeat**: If you keep holding your finger up for more than **2 seconds**, the system will automatically cycle to the next image every 2 seconds.
    - **Looping**: Reaching the last report will automatically cycle back to the first one.

### ✌ TWO FINGERS: Analyze Current Report
- **Action**: Runs a diagnostic analysis on the currently displayed report image.
- **Behavior**:
    - The system performs OCR (Optical Character Recognition) to extract vitals like Heart Rate, SpO2, and Blood Pressure.
    - **Automated Alerts**: If any values are outside the normal clinical range, critical alerts will flash on the screen.
    - This action triggers **once** per gesture session to prevent repeated analysis of the same image.

### ✊ FIST: Lock System
- **Action**: Manually locks the interface to prevent accidental gesture triggers.
- **Behavior**:
    - Showing a fist immediately puts the system into a **LOCKED** state.
- While locked, the system will not execute navigation or analysis actions to prevent accidental triggers.
- **To Unlock**: Show an **Open Palm** 🖐 or use the **Manual Unlock** button in the sidebar.

---

## System Automation

### 🔒 Auto-Locking
- The system monitors hand presence. If no hand is detected for **5 seconds**, the system will automatically lock itself as a safety precaution.
- A toast notification will appear in the bottom right corner when an auto-lock occurs.

### 🕒 Safety Cooldowns
- A global **0.5-second cooldown** is applied between any two actions to ensure stability and prevent "double-triggering" during rapid hand movements.

### 📈 Live Feedback
- The **Live Feed** shows your hand with skeletal tracking.
- The **Gesture Overlay** (top left of video) displays what the system currently "sees" (e.g., OPEN_PALM, ONE_FINGER).
- The **Action Overlay** (top left of video, below gesture) indicates when a command is being executed.
