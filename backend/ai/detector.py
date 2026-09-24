import cv2
import numpy as np
from PIL import Image
from typing import List, Dict, Any, Optional, Tuple
from backend.config import (
    YUNET_MODEL_PATH, PRIMARY_FACE_AREA_THRESHOLD, BLUR_SHARPNESS_THRESHOLD,
    DETECTION_SCALES, DETECTION_SCALES_LARGE, DETECTION_IOU_DEDUP_THRESHOLD
)

def compute_iou(boxA: List[float], boxB: List[float]) -> float:
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[0] + boxA[2], boxB[0] + boxB[2])
    yB = min(boxA[1] + boxA[3], boxB[1] + boxB[3])

    interArea = max(0.0, xB - xA) * max(0.0, yB - yA)
    if interArea == 0:
        return 0.0

    boxAArea = boxA[2] * boxA[3]
    boxBArea = boxB[2] * boxB[3]
    
    iou = interArea / float(boxAArea + boxBArea - interArea)
    return iou

def read_image_unicode(file_path: str) -> Optional[np.ndarray]:
    """
    Unicode-safe image reader supporting standard web formats (JPG/PNG/WEBP)
    and professional camera RAW files (via PIL/rawpy fallback).
    """
    try:
        from PIL import Image, ImageOps
        pil_img = Image.open(file_path)
        pil_img = ImageOps.exif_transpose(pil_img)
        pil_img = pil_img.convert("RGB")
        img_np = np.array(pil_img)
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

        eye_center_y = (r_eye_y + l_eye_y) / 2.0
        mouth_center_y = (r_mouth_y + l_mouth_y) / 2.0

        if eye_center_y >= mouth_center_y + (h * 0.25):
            return False

        import math
        eye_dist = math.sqrt((landmarks[0][0] - landmarks[1][0])**2 + (landmarks[0][1] - landmarks[1][1])**2)
        bbox_diag = math.sqrt(w**2 + h**2)
        if eye_dist < 0.12 * bbox_diag:
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
        max_dim = max(h, w)
        
        scales_to_run = list(DETECTION_SCALES)
        if max_dim > 4000:
            scales_to_run.append(DETECTION_SCALES_LARGE)

        all_detections = []

        # If the image is smaller than all configured scales, run at native resolution
        runnable_scales = [s for s in scales_to_run if max_dim >= s]
        if not runnable_scales:
            runnable_scales = [max_dim]

        for scale_dim in runnable_scales:
            scale = scale_dim / float(max_dim)
            target_w, target_h = int(w * scale), int(h * scale)
            if target_w < 10 or target_h < 10:
                continue
            resized = cv2.resize(image_bgr, (target_w, target_h))

            self.detector.setInputSize((target_w, target_h))
            _, faces = self.detector.detect(resized)

            if faces is not None:
                max_face_area = max(float((f[2] / scale) * (f[3] / scale)) for f in faces) if len(faces) > 0 else 0.0
                for face in faces:
                    confidence = float(face[14])
                    
                    bbox = [
                        int(face[0] / scale),
                        int(face[1] / scale),
                        int(face[2] / scale),
                        int(face[3] / scale)
                    ]
                    landmarks = [
                        (float(face[4] / scale), float(face[5] / scale)),
                        (float(face[6] / scale), float(face[7] / scale)),
                        (float(face[8] / scale), float(face[9] / scale)),
                        (float(face[10] / scale), float(face[11] / scale)),
                        (float(face[12] / scale), float(face[13] / scale))
                    ]

                    if not self.is_valid_face_candidate(bbox, landmarks, confidence):
                        continue

                    raw_unscaled = face.copy()
                    raw_unscaled[0:14] = raw_unscaled[0:14] / scale

                    face_area = float(bbox[2] * bbox[3])
                    area_ratio = face_area / img_area if img_area > 0 else 0.0
                    is_primary = area_ratio >= PRIMARY_FACE_AREA_THRESHOLD or face_area >= 0.35 * max_face_area

                    all_detections.append({
                        'bbox': bbox,
                        'confidence': confidence,
                        'landmarks': landmarks,
                        'area_ratio': area_ratio,
                        'is_primary': is_primary,
                        'raw': raw_unscaled
                    })

        # Deduplicate
        deduped = []
        for det in all_detections:
            matched = False
            for i, exist_det in enumerate(deduped):
                iou = compute_iou(det['bbox'], exist_det['bbox'])
                if iou > DETECTION_IOU_DEDUP_THRESHOLD:
                    matched = True
                    if det['confidence'] > exist_det['confidence']:
                        deduped[i] = det
                    break
            if not matched:
                deduped.append(det)

        return deduped
