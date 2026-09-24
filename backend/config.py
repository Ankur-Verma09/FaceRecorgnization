import sys
import os
from pathlib import Path

if getattr(sys, 'frozen', False):
    # PyInstaller bundle directory (Read-only assets in Program Files)
    BASE_DIR = Path(getattr(sys, '_MEIPASS', Path(sys.executable).parent))
    # Write DB and thumbnails to user LocalAppData directory
    APPDATA_DIR = Path(os.environ.get('LOCALAPPDATA', os.path.expanduser('~'))) / "OfflineFacePhotoOrganizer"
    CACHE_DIR = APPDATA_DIR / ".cache"
else:
    BASE_DIR = Path(__file__).resolve().parent.parent
    CACHE_DIR = BASE_DIR / ".cache"

BACKEND_DIR = BASE_DIR / "backend"
MODELS_DIR = BACKEND_DIR / "models_onnx"
DB_PATH = CACHE_DIR / "photo_organizer.db"
THUMBNAILS_DIR = CACHE_DIR / "thumbnails"

# Ensure directories exist
MODELS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
THUMBNAILS_DIR.mkdir(parents=True, exist_ok=True)

# ONNX Model Paths
YUNET_MODEL_PATH = MODELS_DIR / "face_detection_yunet_2023mar.onnx"
SFACE_MODEL_PATH = MODELS_DIR / "face_recognition_sface_2021dec.onnx"

YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
SFACE_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"

# Supported Photo Extensions (Including Professional Camera RAW Formats)
SUPPORTED_EXTENSIONS = {
    ".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tiff", ".tif", ".heic",
    ".cr2", ".cr3", ".nef", ".arw", ".dng", ".raf", ".orf", ".rw2", ".pef"
}

# Default AI & Photography Thresholds
DEFAULT_DETECTION_CONFIDENCE = 0.65
# Cosine distance threshold for clustering: 0.48 allows pose angles (profile/3/4 views) of same person to group cleanly
DEFAULT_COSINE_THRESHOLD = 0.48  
DEFAULT_GROUP_THRESHOLD = 3      # Primary faces >= 3 categorized as group photos
PRIMARY_FACE_AREA_THRESHOLD = 0.006 # Faces smaller than 0.6% of total photo area are treated as background crowd
BLUR_SHARPNESS_THRESHOLD = 45.0 # Laplacian variance below 45 is flagged as blurry/out of focus

# ── Phase 1: Embedding Quality Gate ──
# Faces below these thresholds are stored but excluded from clustering to prevent noise
MIN_FACE_SIZE_FOR_EMBEDDING = 48      # Minimum bbox width/height in original-image pixels
MIN_CONFIDENCE_FOR_CLUSTERING = 0.75  # Detection confidence floor for cluster-eligible faces
MIN_SHARPNESS_FOR_CLUSTERING = 40.0   # Aligned-crop Laplacian variance floor

# ── Phase 2: Multi-Scale Detection ──
DETECTION_SCALES = [1280, 1920]       # Run YuNet at each of these max-dimension caps
DETECTION_SCALES_LARGE = 2560         # Additional scale for images wider than 4000px
DETECTION_IOU_DEDUP_THRESHOLD = 0.50  # IoU overlap threshold for deduplicating cross-scale detections

# ── Phase 3: Adaptive Clustering ──
TIGHT_CLUSTER_THRESHOLD = 0.38       # Pass 1: high-purity micro-clusters
MAX_CENTROID_MERGE_THRESHOLD = 0.60  # Pass 2: max allowed centroid distance for merging
MIN_PAIRWISE_SAFETY_THRESHOLD = 0.55 # Pass 2: safety check — min distance between any face pair across clusters
