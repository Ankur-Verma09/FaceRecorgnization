import os
import requests
from backend.config import YUNET_MODEL_PATH, SFACE_MODEL_PATH, YUNET_URL, SFACE_URL

def download_file(url: str, dest_path: str):
    print(f"Downloading model from {url} to {dest_path}...")
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(dest_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    print(f"Model saved successfully to {dest_path}")

def ensure_models_exist():
    """Ensure local ONNX model files exist. Download if missing."""
    if not os.path.exists(YUNET_MODEL_PATH):
        download_file(YUNET_URL, str(YUNET_MODEL_PATH))
    
    if not os.path.exists(SFACE_MODEL_PATH):
        download_file(SFACE_URL, str(SFACE_MODEL_PATH))

    return os.path.exists(YUNET_MODEL_PATH) and os.path.exists(SFACE_MODEL_PATH)

if __name__ == "__main__":
    ensure_models_exist()
