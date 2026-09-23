import os
import cv2
import numpy as np
import unittest
from pathlib import Path
from backend.ai.detector import FaceDetectorEngine
from backend.ai.embedder import FaceEmbedderEngine
from backend.ai.clusterer import FaceClusterer
from backend.db.database import DatabaseManager
from backend.services.scanner import PhotoScannerService
from backend.services.organizer import PhotoOrganizerService

class TestOfflineFaceOrganizer(unittest.TestCase):

    def setUp(self):
        self.test_dir = Path("d:/E/Git/FaceRecorgnization/test_sample_photos")
        self.test_dir.mkdir(exist_ok=True)
        self.target_dir = Path("d:/E/Git/FaceRecorgnization/test_organized_photos")
        self.db = DatabaseManager()

    def create_synthetic_photo(self, filename: str, num_faces: int = 1):
        img = np.ones((600, 800, 3), dtype=np.uint8) * 200 # Light grey background
        
        # Draw basic face features for testing
        for i in range(num_faces):
            cx = 200 + i * 250
            cy = 300
            # Face oval
            cv2.ellipse(img, (cx, cy), (80, 100), 0, 0, 360, (180, 150, 120), -1)
            # Eyes
            cv2.circle(img, (cx - 30, cy - 20), 10, (255, 255, 255), -1)
            cv2.circle(img, (cx - 30, cy - 20), 4, (0, 0, 0), -1)
            cv2.circle(img, (cx + 30, cy - 20), 10, (255, 255, 255), -1)
            cv2.circle(img, (cx + 30, cy - 20), 4, (0, 0, 0), -1)
            # Nose
            cv2.line(img, (cx, cy - 10), (cx, cy + 20), (100, 80, 60), 3)
            # Mouth
            cv2.ellipse(img, (cx, cy + 40), (30, 15), 0, 0, 180, (50, 50, 200), 3)

        file_path = self.test_dir / filename
        cv2.imwrite(str(file_path), img)
        return file_path

    def test_detection_and_embedding(self):
        detector = FaceDetectorEngine()
        embedder = FaceEmbedderEngine()
        
        photo_path = self.create_synthetic_photo("solo_person.jpg", num_faces=1)
        img = cv2.imread(str(photo_path))
        
        faces = detector.detect_faces(img)
        print(f"Detected {len(faces)} faces in synthetic test photo.")
        
        if len(faces) > 0:
            raw = faces[0]['raw']
            aligned = embedder.align_and_crop(img, raw)
            embedding = embedder.extract_embedding(aligned)
            self.assertEqual(embedding.shape[0], 512)
            self.assertAlmostEqual(np.linalg.norm(embedding), 1.0, places=4)

    def test_recluster_and_foreign_keys(self):
        scanner = PhotoScannerService(self.db)
        
        # Populate DB with mock image and faces
        self.db.save_image({
            "image_id": "img1", "file_path": "d:/test.jpg", "file_name": "test.jpg",
            "width": 800, "height": 600, "file_size": 1024, "datetime_taken": None,
            "face_count": 2, "sharpness": 100.0
        })
        
        emb1 = np.random.randn(512).astype(np.float32)
        emb1 /= np.linalg.norm(emb1)
        emb2 = np.random.randn(512).astype(np.float32)
        emb2 /= np.linalg.norm(emb2)

        self.db.save_person("Person_1", "Person 1", "d:/thumb1.jpg", 1)
        self.db.save_person("Person_2", "Person 2", "d:/thumb2.jpg", 1)

        self.db.save_faces([
            {"face_id": "f1", "image_id": "img1", "bbox_x": 0, "bbox_y": 0, "bbox_w": 50, "bbox_h": 50,
             "confidence": 0.9, "embedding": emb1, "person_id": "Person_1", "thumbnail_path": "d:/thumb1.jpg",
             "is_primary": True, "area_ratio": 0.05, "sharpness": 120.0},
            {"face_id": "f2", "image_id": "img1", "bbox_x": 100, "bbox_y": 100, "bbox_w": 50, "bbox_h": 50,
             "confidence": 0.9, "embedding": emb2, "person_id": "Person_2", "thumbnail_path": "d:/thumb2.jpg",
             "is_primary": True, "area_ratio": 0.05, "sharpness": 110.0}
        ])

        # Test recluster does not raise Foreign Key error
        res = scanner.recluster(distance_threshold=0.48)
        self.assertIn("persons_count", res)
        self.assertGreater(res["persons_count"], 0)

        # Test merge & unmerge
        persons = self.db.get_all_persons()
        if len(persons) >= 2:
            p1, p2 = persons[0]['person_id'], persons[1]['person_id']
            group_id = self.db.merge_persons(p2, p1)
            groups = self.db.get_merge_groups()
            self.assertEqual(len(groups), 1)

            success = self.db.unmerge_group(group_id)
            self.assertTrue(success)
            self.assertEqual(len(self.db.get_merge_groups()), 0)

    def test_couple_filter_strict_isolation(self):
        organizer = PhotoOrganizerService(self.db)
        self.db.clear_cache()

        photo1 = self.create_synthetic_photo("couple_img.jpg", num_faces=2)
        photo2 = self.create_synthetic_photo("other_person_img.jpg", num_faces=1)

        self.db.save_image({
            "image_id": "img_couple", "file_path": str(photo1), "file_name": photo1.name,
            "width": 800, "height": 600, "file_size": 1024, "datetime_taken": None,
            "face_count": 2, "sharpness": 100.0
        })
        self.db.save_image({
            "image_id": "img_other", "file_path": str(photo2), "file_name": photo2.name,
            "width": 800, "height": 600, "file_size": 1024, "datetime_taken": None,
            "face_count": 1, "sharpness": 100.0
        })

        self.db.save_person("P_Groom", "Amit", "d:/thumb_g.jpg", 1)
        self.db.save_person("P_Bride", "Sunita", "d:/thumb_b.jpg", 1)
        self.db.save_person("P_Stranger", "Stranger", "d:/thumb_s.jpg", 1)

        dummy_emb = np.zeros(512, dtype=np.float32)

        self.db.save_faces([
            {"face_id": "fg", "image_id": "img_couple", "bbox_x": 0, "bbox_y": 0, "bbox_w": 50, "bbox_h": 50,
             "confidence": 0.9, "embedding": dummy_emb, "person_id": "P_Groom", "thumbnail_path": "d:/thumb_g.jpg",
             "is_primary": True, "area_ratio": 0.05, "sharpness": 120.0},
            {"face_id": "fb", "image_id": "img_couple", "bbox_x": 100, "bbox_y": 100, "bbox_w": 50, "bbox_h": 50,
             "confidence": 0.9, "embedding": dummy_emb, "person_id": "P_Bride", "thumbnail_path": "d:/thumb_b.jpg",
             "is_primary": True, "area_ratio": 0.05, "sharpness": 110.0},
            {"face_id": "fs", "image_id": "img_other", "bbox_x": 0, "bbox_y": 0, "bbox_w": 50, "bbox_h": 50,
             "confidence": 0.9, "embedding": dummy_emb, "person_id": "P_Stranger", "thumbnail_path": "d:/thumb_s.jpg",
             "is_primary": True, "area_ratio": 0.05, "sharpness": 100.0}
        ])

        target_export = self.target_dir / "CoupleExportTest"
        res = organizer.execute_organization(
            target_dir=str(target_export),
            couple_pair=["P_Groom", "P_Bride"],
            couple_folder_name="AmitWedsSunita"
        )

        # Verify only 1 image (the couple image) was exported, and stranger image was filtered out!
        self.assertEqual(res["processed_count"], 1)

if __name__ == "__main__":
    unittest.main()
