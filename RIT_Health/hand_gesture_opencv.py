import cv2
import mediapipe as mp
import collections

class HandGesture:
    def __init__(self, history_len=10):
        self.history = collections.deque(maxlen=history_len)
        self.last_stable_gesture = "NO_HAND"
        self.consecutive_count = 0
        
        # MediaPipe Initialization - Robust Import Strategy
        try:
            import mediapipe.python.solutions.hands as mp_hands
            import mediapipe.python.solutions.drawing_utils as mp_draw
            self.mp_hands = mp_hands
            self.mp_draw = mp_draw
        except ImportError:
            try:
                from mediapipe.python import solutions
                self.mp_hands = solutions.hands
                self.mp_draw = solutions.drawing_utils
            except ImportError:
                try:
                    import mediapipe.solutions.hands as mp_hands
                    import mediapipe.solutions.drawing_utils as mp_draw
                    self.mp_hands = mp_hands
                    self.mp_draw = mp_draw
                except ImportError:
                    raise ImportError("Could not find 'mediapipe.solutions'. Please check your install.")

        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.5
        )
        self.raw_pinch_dist = 0
        self.norm_pinch_dist = 0
        self.smooth_pinch_dist = 0
        self.pinch_history = collections.deque(maxlen=5) # Smoothing window
        self.thumb_tip_coords = None
        self.index_tip_coords = None
        self.finger_count = 0

    def detect_gesture(self, frame):
        """
        Detects hand gestures using MediaPipe Hands (Skeletal Tracking).
        """
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.hands.process(frame_rgb)
        
        # Reset coords
        self.thumb_tip_coords = None
        self.index_tip_coords = None

        current_gesture = "NO_HAND"
        
        if results.multi_hand_landmarks:
            # We only take the first hand
            hand_landmarks = results.multi_hand_landmarks[0]
            
            # Optional: Draw landmarks on frame? 
            # The ui_app.py calls this method and expects a string. 
            # If we want to draw, we'd need to modify ui_app logic or draw on a copy.
            # For now, we return the string.
            
            current_gesture = self._classify_landmarks(hand_landmarks, frame.shape)
 
        self.history.append(current_gesture)

        # Robust Debouncing: State Machine
        if len(self.history) >= 2 and self.history[-1] == self.history[-2]:
             self.consecutive_count += 1
        else:
             self.consecutive_count = 1
             
        if self.consecutive_count >= 3:
            self.last_stable_gesture = current_gesture
            
        # Update smoothed pinch distance if we are pinching
        if current_gesture == "PINCH":
            self.pinch_history.append(self.norm_pinch_dist)
            self.smooth_pinch_dist = sum(self.pinch_history) / len(self.pinch_history)
        else:
            self.pinch_history.clear()
            self.smooth_pinch_dist = 0

        return self.last_stable_gesture

    def _classify_landmarks(self, landmarks, frame_shape):
        """
        Classifies the gesture based on landmark positions (Rotation Invariant).
        """
        # Indices
        WRIST = 0
        THUMB_TIP = 4
        INDEX_TIP, INDEX_PIP, INDEX_MCP = 8, 6, 5
        MIDDLE_TIP, MIDDLE_PIP, MIDDLE_MCP = 12, 10, 9
        RING_TIP, RING_PIP, RING_MCP = 16, 14, 13
        PINKY_TIP, PINKY_PIP, PINKY_MCP = 20, 18, 17
        
        lms = landmarks.landmark
        
        # Store Tip pixel coordinates for drawing
        h, w, c = frame_shape
        self.thumb_tip_coords = (int(lms[THUMB_TIP].x * w), int(lms[THUMB_TIP].y * h))
        self.index_tip_coords = (int(lms[INDEX_TIP].x * w), int(lms[INDEX_TIP].y * h))

        # Helper: Euclidean Distance 
        def dist(idx1, idx2):
            return ((lms[idx1].x - lms[idx2].x)**2 + (lms[idx1].y - lms[idx2].y)**2)**0.5
            
        # Scale Reference: Distance from Wrist to Middle MCP (Palm Size)
        palm_size = dist(WRIST, MIDDLE_MCP)
        if palm_size == 0: palm_size = 1 # Avoid div by zero
        
        # Helper: Check if finger is extended (Tip further from wrist than PIP + buffer)
        # Buffer helps avoid flickering when half-curled
        def is_extended(tip, pip):
            return dist(WRIST, tip) > (dist(WRIST, pip) + 0.0 * palm_size)
            
        # Fingers
        index_ext = is_extended(INDEX_TIP, INDEX_PIP)
        middle_ext = is_extended(MIDDLE_TIP, MIDDLE_PIP)
        ring_ext = is_extended(RING_TIP, RING_PIP)
        pinky_ext = is_extended(PINKY_TIP, PINKY_PIP)
        
        # Thumb: Harder bc it curls across palm.
        # Check if Thumb Tip is "far" from Index MCP relative to palm size
        # And also compare Thumb Tip dist to wrist vs Thumb IP dist to wrist (not always reliable for thumb)
        # Better: Thumb Tip distance to Pinky MCP (17) should be LARGE if extended?
        # Standard robust check: Angle or simple "Tip is far from Index MCP"
        # Let's use: Distance(ThumbTip, IndexMCP) > 0.3 * PalmSize?
        thumb_out_dist = dist(THUMB_TIP, INDEX_MCP)
        thumb_is_out = thumb_out_dist > (0.2 * palm_size)
        
        # Refined Thumb: also ensure it's not tucked in (close to pinky mcp)
        if dist(THUMB_TIP, PINKY_MCP) < (0.3 * palm_size):
            thumb_is_out = False
            
        finger_count = 0
        if index_ext: finger_count += 1
        if middle_ext: finger_count += 1
        if ring_ext: finger_count += 1
        if pinky_ext: finger_count += 1
        if thumb_is_out: finger_count += 1
        
        self.finger_count = finger_count
        
        # Pinch Distance Logic
        # Euclidean distance between Thumb Tip (4) and Index Tip (8)
        self.raw_pinch_dist = dist(THUMB_TIP, INDEX_TIP)
        # Normalize distance by palm size for consistency across hand distances from cam
        self.norm_pinch_dist = self.raw_pinch_dist / palm_size
        
        # Classification
        # Pinch detection: Index extended, others (middle, ring, pinky) tucked, 
        # but thumb and index are VERY close.
        # Actually, if we want to zoom, both index and thumb must be "active".
        # A simple pinch is when ONLY index is extended (according to is_extended) 
        # but its tip is very close to thumb tip.
        
        # 1. Detect Pinch (Thumb-Index meeting)
        # Use hysteresis: 0.6 to maintain, 0.4 to initiate
        thresh = 0.6 if self.last_stable_gesture == "PINCH" else 0.4
        is_pinching_dist = self.norm_pinch_dist < thresh
        
        # PINCH: Distance is small, and index/thumb are the main active fingers (low count)
        if is_pinching_dist and self.finger_count <= 2:
            return "PINCH"

        # 2. General Classifications
        if finger_count == 5:
            return "OPEN_PALM"
            
        elif finger_count == 0:
            # Only call it FIST if we aren't already pinching
            return "FIST"
            
        elif finger_count == 1 and thumb_is_out:
            # Thumbs up or just thumb out - usually treat as status quo or FIST for locking
            return "FIST"
            
        elif index_ext and not middle_ext and not ring_ext and not pinky_ext:
            # ONE FINGER (Index) - Ignore thumb state (relaxed or tucked)
            return "ONE_FINGER"
            
        elif index_ext and middle_ext and not ring_ext and not pinky_ext:
            return "TWO_FINGERS"
        
        # Special: "Paper/Palm" with thumb tucked is still mostly open? 
        # Requirement: "OPEN PALM" usually implies all 5.
        
        return "UNKNOWN"
