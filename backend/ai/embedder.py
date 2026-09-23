import cv2
import numpy as np
from typing import Optional
from backend.config import SFACE_MODEL_PATH

class FaceEmbedderEngine:
    """OpenCV SFace Local ONNX Feature Embedding Engine (512D)."""

    def __init__(self):
        self.model_path = str(SFACE_MODEL_PATH)
        self.recognizer = cv2.FaceRecognizerSF.create(
            self.model_path,
            ""
        )

    def align_and_crop(self, image_bgr: np.ndarray, raw_face_array: np.ndarray) -> np.ndarray:
        """Align face using facial landmarks and crop to 112x112."""
        aligned_face = self.recognizer.alignCrop(image_bgr, raw_face_array)
        return aligned_face

    def extract_embedding(self, aligned_face: np.ndarray) -> np.ndarray:
        """
        Extract 512-dimensional feature vector from an aligned face image.
        Returns 1D normalized float32 numpy array.
        """
        feature = self.recognizer.feature(aligned_face)
        # Flatten and L2 normalize
        embedding = feature.flatten().astype(np.float32)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        return embedding

    def match_distance(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine distance (1.0 - cosine similarity)."""
        similarity = cv2.FaceRecognizerSF.match(
            self.recognizer, embedding1.reshape(1, -1), embedding2.reshape(1, -1), cv2.FaceRecognizerSF_FR_COSINE
        )
        return float(1.0 - similarity)
