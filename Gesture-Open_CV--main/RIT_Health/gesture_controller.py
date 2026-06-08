import time

class GestureController:
    def __init__(self):
        self.last_action_time = 0
        self.last_hand_time = time.time()
        self.cooldown = 0.5  # Seconds between any two actions
        self.repeat_interval = 2.0  # Seconds to wait for repeat action if held
        self.lock_timeout = 5.0 # Seconds to auto-lock if no hand
        
        self.current_gesture = "NO_HAND"
        self.gesture_start_time = 0
        self.gesture_action_count = 0
        self.prev_pinch_dist = None
        self.zoom_scale = 1.0 # Current zoom level
        self.min_zoom = 0.5
        self.zoom_sensitivity = 15.0 # Boosted for responsiveness
        self.last_pinch_time = 0

    def update_hand_presence(self, gesture):
        """
        Updates the timestamp of the last seen hand.
        """
        if gesture != "NO_HAND":
            self.last_hand_time = time.time()

    def should_lock(self):
        """
        Returns True if no hand has been seen for 'lock_timeout' seconds.
        """
        if (time.time() - self.last_hand_time) > self.lock_timeout:
            return True
        return False

    def execute(self, gesture, finger_count=0, norm_pinch_dist=1.0):
        """
        Determines action based on gesture, duration, and cooldowns.
        """
        self.update_hand_presence(gesture)
        current_time = time.time()
        self.norm_pinch_dist = norm_pinch_dist # Update internal state

        self.norm_pinch_dist = norm_pinch_dist # Update internal state for process_zoom

        # Handle Gesture State Change
        if gesture != self.current_gesture:
            self.current_gesture = gesture
            self.gesture_start_time = current_time
            self.gesture_action_count = 0
        
        # Check for Lock Command (Immediate)
        if gesture == "FIST":
            return "LOCK_SYSTEM"

        action = "NO_ACTION"
        time_since_last_action = current_time - self.last_action_time

        if gesture == "OPEN_PALM":
            # Suppress OPEN_PALM if we just finished a PINCH (1.5s grace period)
            # to prevent accidental zoom resets when spreading fingers wide.
            pinch_grace = current_time - self.last_pinch_time < 1.5
            if self.gesture_action_count == 0 and time_since_last_action > self.cooldown and not pinch_grace:
                action = "OPEN_DOCUMENT"
                self.gesture_action_count += 1
        
        elif gesture == "ONE_FINGER":
            # 1. Fire immediately (if cooldown allows)
            # 2. Fire again every 2.0 seconds if held
            if self.gesture_action_count == 0:
                if time_since_last_action > self.cooldown:
                    action = "NEXT_PAGE"
                    self.gesture_action_count += 1
            else:
                # Repeat logic: more than repeat_interval since the LAST action
                if time_since_last_action >= self.repeat_interval:
                    action = "NEXT_PAGE"
                    self.gesture_action_count += 1
            
        elif gesture == "TWO_FINGERS":
            # Fire once per gesture session
            if self.gesture_action_count == 0 and time_since_last_action > self.cooldown:
                action = "ANALYZE"
                self.gesture_action_count += 1
        
        elif gesture == "PINCH":
            # Pinch is handled continuously, not as a one-shot action
            action = "ZOOM"
            self.last_pinch_time = current_time

        if action != "NO_ACTION":
            self.last_action_time = current_time
            
        return action

    def process_zoom(self, current_pinch_dist):
        """
        Calculates zoom delta based on pinch distance change.
        Returns the updated zoom_scale.
        """
        if self.prev_pinch_dist is None or self.current_gesture != "PINCH":
            self.prev_pinch_dist = current_pinch_dist
            return self.zoom_scale
        
        # Calculate delta
        delta = current_pinch_dist - self.prev_pinch_dist
        
        # Update scale ADDITIVELY (Reverting from multiplicative)
        self.zoom_scale += delta * self.zoom_sensitivity
        
        # Clamp zoom range (Keep lower limit for usability)
        self.zoom_scale = max(self.min_zoom, self.zoom_scale)
        
        # Update prev for next frame
        self.prev_pinch_dist = current_pinch_dist
        
        return self.zoom_scale
