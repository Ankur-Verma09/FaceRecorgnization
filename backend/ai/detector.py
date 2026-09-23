import cv2
import numpy as np
from PIL import Image
from typing import List, Dict, Any, Optional, Tuple
from backend.config import YUNET_MODEL_PATH, PRIMARY_FACE_AREA_THRESHOLD, BLUR_SHARPNESS_THRESHOLD

def read_image_unicode(file_path: str) -> Optional[np.ndarray]:
    """
    Unicode-safe image reader supporting standard web formats (JPG/PNG/WEBP)
    and professional camera RAW files (via PIL/rawpy fallback).
    """
    try:
        # Try standard OpenCV imdecode with binary stream first
        with open(file_path, "rb") as f:
            bytes_data = bytearray(f.read())
            numpy_array = np.asarray(bytes_data, dtype=np.uint8)
            img = cv2.imdecode(numpy_array, cv2.IMREAD_COLOR)
            if img is not None:
                return img
    except Exception:
        pass

    # Fallback to PIL Image for RAW/HEIC/TIF formats
    try:
        pil_img = Image.open(file_path)
        pil_img = pil_img.convert("RGB")
        img_np = np.array(pil_img)
        # Convert RGB to BGR for OpenCV
        return cv2.cvtColor(img_np, cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"Error reading image file {file_path}: {e}")
        return None

def write_image_unicode(file_path: str, img: np.ndarray) -> bool:
    """Unicode-safe image writer for Windows paths."""
    try:
        is_success, buffer = cv2.imencode(".jpg", img)
        if is_success:
            with open(file_path, "wb") as f:
                f.write(buffer)
            return True
    except Exception as e:
        print(f"Error writing thumbnail file {file_path}: {e}")
    return False

def calculate_sharpness(image_bgr: np.ndarray) -> float:
    """Calculate image sharpness score using Laplacian Variance."""
    if image_bgr is None or image_bgr.size == 0:
        return 0.0
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    variance = cv2.Laplacian(gray, cv2.CV_64F).var()
    return float(variance)

class FaceDetectorEngine:
    """
    Professional Face Detector Engine using OpenCV YuNet ONNX.
    Includes subject area ratio computation (Primary vs Background Crowd)
    and image sharpness analysis.
    """

    def __init__(self, score_threshold: float = 0.65, nms_threshold: float = 0.3, top_k: int = 5000):
        self.score_threshold = score_threshold
        self.nms_threshold = nms_threshold
        self.top_k = top_k
        self.model_path = str(YUNET_MODEL_PATH)
        
        self.detector = cv2.FaceDetectorYN.create(
            self.model_path,
            "",
            (300, 300),
            self.score_threshold,
            self.nms_threshold,
            self.top_k
        )

    def is_valid_face_candidate(self, bbox: List[int], landmarks: List[tuple], confidence: float) -> bool:
        """Strict validation rules to eliminate non-face false positives."""
        x, y, w, h = bbox

        # 1. Minimum Face Dimension Filter (must be at least 32x32 pixels)
        if w < 32 or h < 32:
            return False

        # 2. Aspect Ratio Filter (Human face width-to-height ratio is generally 0.45 to 1.6)
        aspect_ratio = float(w) / float(h)
        if aspect_ratio < 0.45 or aspect_ratio > 1.6:
            return False

        # 3. Landmark Topology Sanity Check
        # Landmarks: [0: Right Eye, 1: Left Eye, 2: Nose, 3: Right Mouth, 4: Left Mouth]
        r_eye_y = landmarks[0][1]
        l_eye_y = landmarks[1][1]
        r_mouth_y = landmarks[3][1]
        l_mouth_y = landmarks[4][1]

        # Eyes must be positioned above mouth corners
        if r_eye_y >= r_mouth_y or l_eye_y >= l_mouth_y:
            return False

        # Confidence check
        if confidence < self.score_threshold:
            return False

        return True

    def detect_faces(self, image_bgr: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect faces in a BGR image array with primary subject area scoring.
        """
        if image_bgr is None or image_bgr.size == 0:
            return []

        h, w, _ = image_bgr.shape
        img_area = float(w * h)
        
        # Resize large images to max dimension 1280 while preserving aspect ratio
        max_dim = 1280
        scale = 1.0
        if max(h, w) > max_dim:
            scale = max_dim / float(max(h, w))
            target_w, target_h = int(w * scale), int(h * scale)
            resized = cv2.resize(image_bgr, (target_w, target_h))
        else:
            resized = image_bgr
            target_w, target_h = w, h

        self.detector.setInputSize((target_w, target_h))
        _, faces = self.detector.detect(resized)

        results = []
        if faces is not None:
            for face in faces:
                bbox = [
                    int(face[0] / scale),
                    int(face[1] / scale),
                    int(face[2] / scale),
                    int(face[3] / scale)
                ]
                landmarks = [
                    (float(face[4] / scale), float(face[5] / scale)),   # Right Eye
                    (float(face[6] / scale), float(face[7] / scale)),   # Left Eye
                    (float(face[8] / scale), float(face[9] / scale)),   # Nose Tip
                    (float(face[10] / scale), float(face[11] / scale)), # Right Mouth Corner
                    (float(face[12] / scale), float(face[13] / scale))  # Left Mouth Corner
                ]
                confidence = float(face[14])

                # Filter non-face false positives
                if not self.is_valid_face_candidate(bbox, landmarks, confidence):
                    continue

                # Face Area Ratio
                face_area = float(bbox[2] * bbox[3])
                area_ratio = face_area / img_area if img_area > 0 else 0.0
                is_primary = area_ratio >= PRIMARY_FACE_AREA_THRESHOLD

                raw_unscaled = face.copy()
                raw_unscaled[0:14] = raw_unscaled[0:14] / scale

                results.append({
                    'bbox': bbox,
                    'confidence': confidence,
                    'landmarks': landmarks,
                    'area_ratio': area_ratio,
                    'is_primary': is_primary,
                    'raw': raw_unscaled
                })

        return results
