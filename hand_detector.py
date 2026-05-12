# hand_detector.py
import numpy as np
import mediapipe as mp

class HandDetector:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.8,
            min_tracking_confidence=0.7
        )
        self.mp_drawing = mp.solutions.drawing_utils
    
    def process(self, frame_rgb):
        return self.hands.process(frame_rgb)
    
    def detect_gesture(self, hand_landmarks):
        thumb_tip = hand_landmarks.landmark[4]
        index_tip = hand_landmarks.landmark[8]
        middle_tip = hand_landmarks.landmark[12]
        ring_tip = hand_landmarks.landmark[16]
        pinky_tip = hand_landmarks.landmark[20]
        
        pinch_distance = np.sqrt(
            (thumb_tip.x - index_tip.x)**2 + 
            (thumb_tip.y - index_tip.y)**2
        )
        
        index_up = index_tip.y < hand_landmarks.landmark[6].y
        middle_up = middle_tip.y < hand_landmarks.landmark[10].y
        ring_down = ring_tip.y > hand_landmarks.landmark[14].y
        pinky_down = pinky_tip.y > hand_landmarks.landmark[18].y
        
        fingers_spread = np.sqrt((index_tip.x - middle_tip.x)**2 + 
                                 (index_tip.y - middle_tip.y)**2) > 0.05
        
        is_peace = (index_up and middle_up and ring_down and 
                   pinky_down and fingers_spread)
        
        return {
            'pinch_distance': pinch_distance,
            'is_peace': is_peace
        }
    
    def draw_landmarks(self, frame_rgb, hand_landmarks):
        self.mp_drawing.draw_landmarks(
            frame_rgb, hand_landmarks, self.mp_hands.HAND_CONNECTIONS
        )
