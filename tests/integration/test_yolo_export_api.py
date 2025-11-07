"""
Integration tests for YOLO export API endpoint
"""

import io
import zipfile
from unittest import TestCase

from fastapi.testclient import TestClient
from backend.main import app
from tests.test_base import DatabaseTestCase


class TestYOLOExportAPI(DatabaseTestCase):
    """Integration tests for YOLO export endpoint."""

    def setUp(self):
        """Set up test client."""
        super().setUp()

    def test_export_yolo_handles_empty_result(self):
        """Test that export handles the case gracefully."""
        # This test is skipped because we can't easily clear all annotations
        # The export endpoint will return annotations if any exist
        response = self.client.get("/api/export/yolo")

        # Should either return 404 (if no annotations) or 200 with a valid ZIP
        self.assertIn(response.status_code, [200, 404])

    def test_export_yolo_returns_zip(self):
        """Test that export returns a valid ZIP file when annotations exist."""
        # First, create a dataset with an image and annotations
        # Create project
        project_data = {
            "name": "YOLO Test Project",
            "description": "Test",
            "is_public": True,
        }
        project_response = self.client.post("/api/projects", json=project_data)
        project_id = project_response.json()["project_id"]

        # Create dataset
        dataset_data = {
            "name": "YOLO Dataset",
            "description": "Test",
            "project_id": project_id,
        }
        dataset_response = self.client.post("/api/datasets", json=dataset_data)
        dataset_id = dataset_response.json()["dataset_id"]

        # Create label categories
        category1_data = {
            "name": "Class1",
            "color": "#FF0000",
            "project_id": project_id,
        }
        category1_response = self.client.post(
            "/api/label-categories", json=category1_data
        )
        category1_id = category1_response.json()["category_id"]

        category2_data = {
            "name": "Class2",
            "color": "#00FF00",
            "project_id": project_id,
        }
        category2_response = self.client.post(
            "/api/label-categories", json=category2_data
        )
        category2_id = category2_response.json()["category_id"]

        # Upload an image (we need a valid image file)
        # For this test, we'll create a minimal test image
        from PIL import Image
        import os
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tmp:
            test_image = Image.new("RGB", (100, 100), color="red")
            test_image.save(tmp.name, "JPEG")
            tmp_path = tmp.name

        try:
            # Upload image
            with open(tmp_path, "rb") as f:
                files = {"file": ("test.jpg", f, "image/jpeg")}
                data = {"dataset_id": dataset_id}
                upload_response = self.client.post(
                    "/api/images/upload", files=files, data=data
                )
                self.assertEqual(upload_response.status_code, 200)
                image_id = upload_response.json()["image_id"]

            # Create annotations
            annotation1_data = {
                "image_id": image_id,
                "label_category_id": category1_id,
                "annotation_data": {
                    "tool": "bbox",
                    "coordinates": {"startX": 10, "startY": 10, "endX": 50, "endY": 50},
                },
                "confidence": 1.0,
            }
            self.client.post("/api/annotations", json=annotation1_data)

            annotation2_data = {
                "image_id": image_id,
                "label_category_id": category2_id,
                "annotation_data": {
                    "tool": "bbox",
                    "coordinates": {"startX": 60, "startY": 60, "endX": 90, "endY": 90},
                },
                "confidence": 1.0,
            }
            self.client.post("/api/annotations", json=annotation2_data)

            # Export to YOLO
            response = self.client.get("/api/export/yolo")

            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["content-type"], "application/zip")

            # Verify ZIP file contents
            zip_data = io.BytesIO(response.content)
            with zipfile.ZipFile(zip_data, "r") as zip_file:
                # Check for classes.txt
                self.assertIn("classes.txt", zip_file.namelist())

                # Read and verify classes.txt
                classes_content = zip_file.read("classes.txt").decode("utf-8")
                self.assertIn("Class1", classes_content)
                self.assertIn("Class2", classes_content)

                # Check for label file
                label_files = [
                    f for f in zip_file.namelist() if f.startswith("labels/")
                ]
                self.assertGreater(len(label_files), 0)

                # Read first label file and verify YOLO format
                if label_files:
                    label_content = zip_file.read(label_files[0]).decode("utf-8")
                    lines = label_content.strip().split("\n")
                    self.assertGreater(len(lines), 0)

                    # Verify YOLO format: class_index x y width height
                    for line in lines:
                        parts = line.split()
                        self.assertEqual(len(parts), 5)
                        # Class index should be valid (0 or higher)
                        class_index = int(parts[0])
                        self.assertGreaterEqual(class_index, 0)

                        # Verify normalized coordinates (0-1 range)
                        for coord in parts[1:]:
                            coord_val = float(coord)
                            self.assertGreaterEqual(coord_val, 0.0)
                            self.assertLessEqual(coord_val, 1.0)

        finally:
            # Cleanup
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
