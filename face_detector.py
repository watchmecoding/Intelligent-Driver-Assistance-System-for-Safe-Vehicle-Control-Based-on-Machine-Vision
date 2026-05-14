# face_detector.py
import cv2
import numpy as np
import mediapipe as mp
from settings_manager import SettingsManager

LEFT_EYE_IDX  = [33,  160, 158, 133, 153, 144]
RIGHT_EYE_IDX = [362, 385, 387, 263, 373, 380]

_MODEL_3D = np.array([
    [   0.0,    0.0,    0.0],
    [   0.0, -330.0,  -65.0],
    [-225.0,  170.0, -135.0],
    [ 225.0,  170.0, -135.0],
    [-150.0, -150.0, -125.0],
    [ 150.0, -150.0, -125.0],
], dtype=np.float64)
_MODEL_LM = [1, 152, 263, 33, 287, 57]


class FaceDetector:
    def __init__(self):
        self.settings = SettingsManager()
        mp_fm = mp.solutions.face_mesh
        self.face_mesh = mp_fm.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
        )
        self.mouth_indices = [61, 291, 13, 14]
        self._prev_pitch = 0.0
        self._prev_yaw   = 0.0

    def process(self, frame_rgb):
        return self.face_mesh.process(frame_rgb)

    def calculate_EAR(self, landmarks, indices, w, h):
        try:
            eye  = np.array([(landmarks[i].x * w, landmarks[i].y * h)
                             for i in indices])
            hor  = np.linalg.norm(eye[0] - eye[3])
            ver1 = np.linalg.norm(eye[1] - eye[5])
            ver2 = np.linalg.norm(eye[2] - eye[4])
            return (ver1 + ver2) / (2.0 * hor) if hor > 0 else 0.0
        except Exception:
            return 0.3

    def calculate_MAR(self, landmarks, indices, w, h):
        try:
            mouth = np.array([(landmarks[i].x * w, landmarks[i].y * h)
                              for i in indices])
            hor = np.linalg.norm(mouth[0] - mouth[1])
            ver = np.linalg.norm(mouth[2] - mouth[3])
            return ver / hor if hor > 0 else 0.0
        except Exception:
            return 0.0

    def estimateheadpose(self, landmarks, w, h):
        try:
            imgpts = np.array(
                [[landmarks[i].x * w, landmarks[i].y * h] for i in _MODEL_LM],
                dtype=np.float64
            )
            focal = float(w)
            cam = np.array([[focal, 0, w/2.0],
                            [0, focal, h/2.0],
                            [0, 0, 1.0]], dtype=np.float64)
            dist = np.zeros((4, 1), dtype=np.float64)
            ok, rvec, _ = cv2.solvePnP(_MODEL_3D, imgpts, cam, dist,
                                        flags=cv2.SOLVEPNP_ITERATIVE)
            if not ok:
                return self._prev_pitch, self._prev_yaw
            
            R, _ = cv2.Rodrigues(rvec)
            sy = np.sqrt(R[0,0]**2 + R[1,0]**2)
            pitch = np.arctan2(R[2,1], R[2,2]) if sy > 1e-6 else np.arctan2(-R[1,2], R[1,1])
            yaw   = np.arctan2(-R[2,0], sy)
            pitch_deg = float(np.degrees(pitch))
            yaw_deg   = -float(np.degrees(yaw))
            # Згладжування:
            pitch_deg = self._prev_pitch * 0.5 + pitch_deg * 0.5
            yaw_deg   = self._prev_yaw   * 0.5 + yaw_deg   * 0.5
            self._prev_pitch = pitch_deg
            self._prev_yaw   = yaw_deg
            return pitch_deg, yaw_deg
        except Exception:
            return self._prev_pitch, self._prev_yaw

    def get_metrics(self, landmarks, w, h):
        s = self.settings

        left_ear  = self.calculate_EAR(landmarks, LEFT_EYE_IDX,  w, h)
        right_ear = self.calculate_EAR(landmarks, RIGHT_EYE_IDX, w, h)
        pitch, yaw = self.estimateheadpose(landmarks, w, h)

        # Вибір найближчого ока при повороті
        angle_left  = s.head_turn_angle_left
        angle_right = s.head_turn_angle_right

        if yaw < -angle_left:
            ear = right_ear
        elif yaw > angle_right:
            ear = left_ear
        else:
            ear = (left_ear + right_ear) / 2.0

        mar = self.calculate_MAR(landmarks, self.mouth_indices, w, h)

        return {
            'EAR':       ear,
            'MAR':       mar,
            'yaw':       yaw,
            'pitch':     pitch,
            'left_ear':  left_ear,
            'right_ear': right_ear,
        }

    def draw_landmarks(self, frame_rgb, landmarks, w, h):
        for idx in LEFT_EYE_IDX + RIGHT_EYE_IDX + self.mouth_indices:
            x = int(landmarks[idx].x * w)
            y = int(landmarks[idx].y * h)
            cv2.circle(frame_rgb, (x, y), 2, (0, 255, 0), -1)
        x_min = int(min(lm.x for lm in landmarks) * w)
        x_max = int(max(lm.x for lm in landmarks) * w)
        y_min = int(min(lm.y for lm in landmarks) * h)
        y_max = int(max(lm.y for lm in landmarks) * h)
        return (x_min, y_min, x_max, y_max)
