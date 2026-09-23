import os
import cv2
import numpy as np
from pathlib import Path
from backend.db.database import DatabaseManager
from backend.services.scanner import PhotoScannerService
from backend.services.organizer import PhotoOrganizerService

def create_face_image(width=600, height=600, center_x=300, center_y=300, skin_color=(180, 150, 120)):
    img = np.ones((height, width, 3), dtype=np.uint8) * 220
    # Head
    cv2.ellipse(img, (center_x, center_y), (100, 130), 0, 0, 360, skin_color, -1)
    # Eyes
    cv2.circle(img, (center_x - 35, center_y - 25), 14, (255, 255, 255), -1)
    cv2.circle(img, (center_x - 35, center_y - 25), 6, (0, 0, 0), -1)
    cv2.circle(img, (center_x + 35, center_y - 25), 14, (255, 255, 255), -1)
    cv2.circle(img, (center_x + 35, center_y - 25), 6, (0, 0, 0), -1)
    # Nose
    cv2.line(img, (center_x, center_y - 10), (center_x, center_y + 25), (120, 90, 70), 3)
    # Mouth
    cv2.ellipse(img, (center_x, center_y + 50), (40, 20), 0, 0, 180, (60, 60, 200), 3)
    return img

def run_test():
    sample_dir = Path("d:/E/Git/FaceRecorgnization/test_photos_sample")
    sample_dir.mkdir(parents=True, exist_ok=True)
    target_dir = Path("d:/E/Git/FaceRecorgnization/test_photos_organized")

    # Create 3 test photos
    cv2.imwrite(str(sample_dir / "photo_solo_1.jpg"), create_face_image(center_x=300, center_y=300))
    cv2.imwrite(str(sample_dir / "photo_solo_2.jpg"), create_face_image(center_x=300, center_y=300))
    
    # Scenery photo (0 faces)
    scenery = np.zeros((400, 400, 3), dtype=np.uint8)
    cv2.imwrite(str(sample_dir / "scenery_landscape.jpg"), scenery)

    db = DatabaseManager()
    scanner = PhotoScannerService(db)
    organizer = PhotoOrganizerService(db)

    print("Running scan on sample folder...")
    scan_res = scanner.scan_directory(str(sample_dir))
    print("Scan Result:", scan_res)

    print("Running organization to target folder...")
    org_res = organizer.execute_organization(target_dir=str(target_dir), operation_mode="copy")
    print("Organize Result:", org_res)

    print("Verification completed successfully!")

if __name__ == "__main__":
    run_test()
