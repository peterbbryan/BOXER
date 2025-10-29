"""
Integration tests for full workflows
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from PIL import Image
import json

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.main import app
from backend.database import (
    get_db,
    init_database,
    Project,
    Dataset,
    Image as ImageModel,
    Annotation,
    LabelCategory,
)


class TestFullWorkflows(unittest.TestCase):
    """Test complete workflows from start to finish"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
        self.temp_dir = tempfile.mkdtemp()

        # Create test directories
        self.uploads_dir = os.path.join(self.temp_dir, "uploads")
        self.images_dir = os.path.join(self.uploads_dir, "images")
        self.thumbnails_dir = os.path.join(self.uploads_dir, "thumbnails")
        os.makedirs(self.images_dir)
        os.makedirs(self.thumbnails_dir)

    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up test files
        for root, dirs, files in os.walk(self.temp_dir):
            for file in files:
                os.remove(os.path.join(root, file))
        os.rmdir(self.images_dir)
        os.rmdir(self.thumbnails_dir)
        os.rmdir(self.uploads_dir)
        os.rmdir(self.temp_dir)

    def test_complete_annotation_workflow(self):
        """Test complete workflow: upload image, create annotations, retrieve annotations"""
        # Step 1: Create a test image
        test_image_path = os.path.join(self.temp_dir, "test_workflow.jpg")
        img = Image.new("RGB", (800, 600), color="red")
        img.save(test_image_path, "JPEG")

        # Step 2: Upload the image
        with open(test_image_path, "rb") as f:
            files = {"file": ("test_workflow.jpg", f, "image/jpeg")}
            data = {"dataset_id": 1}
            response = self.client.post("/api/images/upload", files=files, data=data)

        self.assertEqual(response.status_code, 200)
        upload_data = response.json()
        self.assertIn("image_id", upload_data)
        image_id = upload_data["image_id"]

        # Step 3: Create a bounding box annotation
        bbox_annotation = {
            "image_id": image_id,
            "label_category_id": 1,
            "annotation_data": {
                "tool": "bbox",
                "coordinates": {"startX": 100, "startY": 100, "endX": 300, "endY": 200},
            },
            "confidence": 1.0,
        }

        response = self.client.post("/api/annotations", json=bbox_annotation)
        self.assertEqual(response.status_code, 200)
        bbox_data = response.json()
        self.assertIn("annotation_id", bbox_data)
        bbox_id = bbox_data["annotation_id"]

        # Step 4: Create a point annotation
        point_annotation = {
            "image_id": image_id,
            "label_category_id": 1,
            "annotation_data": {
                "tool": "point",
                "coordinates": {"startX": 150, "startY": 150},
            },
            "confidence": 1.0,
        }

        response = self.client.post("/api/annotations", json=point_annotation)
        self.assertEqual(response.status_code, 200)
        point_data = response.json()
        self.assertIn("annotation_id", point_data)
        point_id = point_data["annotation_id"]

        # Step 5: Create a polygon annotation
        polygon_annotation = {
            "image_id": image_id,
            "label_category_id": 1,
            "annotation_data": {
                "tool": "polygon",
                "coordinates": {
                    "points": [
                        {"x": 200, "y": 200},
                        {"x": 400, "y": 200},
                        {"x": 400, "y": 300},
                        {"x": 200, "y": 300},
                    ]
                },
            },
            "confidence": 1.0,
        }

        response = self.client.post("/api/annotations", json=polygon_annotation)
        self.assertEqual(response.status_code, 200)
        polygon_data = response.json()
        self.assertIn("annotation_id", polygon_data)
        polygon_id = polygon_data["annotation_id"]

        # Step 6: Retrieve all annotations for the image
        response = self.client.get(f"/api/annotations/{image_id}")
        self.assertEqual(response.status_code, 200)
        annotations_data = response.json()

        self.assertIn("annotations", annotations_data)
        annotations = annotations_data["annotations"]
        self.assertEqual(len(annotations), 3)

        # Verify annotation types
        annotation_tools = [ann["tool"] for ann in annotations]
        self.assertIn("bbox", annotation_tools)
        self.assertIn("point", annotation_tools)
        self.assertIn("polygon", annotation_tools)

        # Step 7: Delete one annotation
        response = self.client.delete(f"/api/annotations/{bbox_id}")
        self.assertEqual(response.status_code, 200)

        # Step 8: Verify annotation was deleted
        response = self.client.get(f"/api/annotations/{image_id}")
        self.assertEqual(response.status_code, 200)
        annotations_data = response.json()
        annotations = annotations_data["annotations"]
        self.assertEqual(len(annotations), 2)

        # Step 9: Delete the image
        response = self.client.delete(f"/api/images/{image_id}")
        self.assertEqual(response.status_code, 200)

    def test_project_management_workflow(self):
        """Test complete project management workflow"""
        # Step 1: Get initial projects
        response = self.client.get("/api/projects")
        self.assertEqual(response.status_code, 200)
        initial_projects = response.json()["projects"]
        initial_count = len(initial_projects)

        # Step 2: Update project name
        if initial_count > 0:
            project_id = initial_projects[0]["id"]
            new_name = "Updated Project Name"

            response = self.client.put(
                f"/api/projects/{project_id}", json={"name": new_name}
            )
            self.assertEqual(response.status_code, 200)

            # Step 3: Verify name was updated
            response = self.client.get("/api/projects")
            self.assertEqual(response.status_code, 200)
            updated_projects = response.json()["projects"]

            # Find the updated project
            updated_project = next(
                (p for p in updated_projects if p["id"] == project_id), None
            )
            self.assertIsNotNone(updated_project)
            self.assertEqual(updated_project["name"], new_name)

    def test_image_upload_and_processing_workflow(self):
        """Test complete image upload and processing workflow"""
        # Step 1: Create test images in different formats
        test_images = []
        formats = [("JPEG", "jpg"), ("PNG", "png"), ("BMP", "bmp")]

        for format_name, ext in formats:
            test_image_path = os.path.join(self.temp_dir, f"test.{ext}")
            img = Image.new("RGB", (400, 300), color="blue")
            img.save(test_image_path, format_name)
            test_images.append((test_image_path, f"test.{ext}"))

        # Step 2: Upload each image
        uploaded_images = []
        for image_path, filename in test_images:
            with open(image_path, "rb") as f:
                files = {
                    "file": (
                        filename,
                        f,
                        f"image/{format_name.lower() if format_name != 'JPEG' else 'jpeg'}",
                    )
                }
                data = {"dataset_id": 1}
                response = self.client.post(
                    "/api/images/upload", files=files, data=data
                )

            self.assertEqual(response.status_code, 200)
            upload_data = response.json()
            self.assertIn("image_id", upload_data)
            uploaded_images.append(upload_data["image_id"])

        # Step 3: Verify all images were uploaded
        self.assertEqual(len(uploaded_images), len(test_images))

        # Step 4: Create annotations for each image
        for image_id in uploaded_images:
            annotation = {
                "image_id": image_id,
                "label_category_id": 1,
                "annotation_data": {
                    "tool": "bbox",
                    "coordinates": {
                        "startX": 50,
                        "startY": 50,
                        "endX": 150,
                        "endY": 100,
                    },
                },
                "confidence": 1.0,
            }

            response = self.client.post("/api/annotations", json=annotation)
            self.assertEqual(response.status_code, 200)

        # Step 5: Verify annotations were created
        for image_id in uploaded_images:
            response = self.client.get(f"/api/annotations/{image_id}")
            self.assertEqual(response.status_code, 200)
            annotations_data = response.json()
            self.assertEqual(len(annotations_data["annotations"]), 1)

        # Step 6: Clean up - delete all uploaded images
        for image_id in uploaded_images:
            response = self.client.delete(f"/api/images/{image_id}")
            self.assertEqual(response.status_code, 200)

    def test_error_handling_workflow(self):
        """Test error handling in various scenarios"""
        # Test 1: Upload invalid file
        invalid_file_path = os.path.join(self.temp_dir, "invalid.txt")
        with open(invalid_file_path, "w") as f:
            f.write("This is not an image")

        with open(invalid_file_path, "rb") as f:
            files = {"file": ("invalid.txt", f, "text/plain")}
            data = {"dataset_id": 1}
            response = self.client.post("/api/images/upload", files=files, data=data)

        self.assertEqual(response.status_code, 400)

        # Test 2: Create annotation for non-existent image
        invalid_annotation = {
            "image_id": 99999,
            "label_category_id": 1,
            "annotation_data": {
                "tool": "bbox",
                "coordinates": {"startX": 100, "startY": 100, "endX": 200, "endY": 200},
            },
            "confidence": 1.0,
        }

        response = self.client.post("/api/annotations", json=invalid_annotation)
        self.assertEqual(response.status_code, 404)

        # Test 3: Get annotations for non-existent image
        response = self.client.get("/api/annotations/99999")
        self.assertEqual(response.status_code, 200)
        annotations_data = response.json()
        self.assertEqual(len(annotations_data["annotations"]), 0)

        # Test 4: Delete non-existent annotation
        response = self.client.delete("/api/annotations/99999")
        self.assertEqual(response.status_code, 404)

        # Test 5: Delete non-existent image
        response = self.client.delete("/api/images/99999")
        self.assertEqual(response.status_code, 404)

    def test_concurrent_operations_workflow(self):
        """Test concurrent operations don't interfere with each other"""
        # Create multiple test images
        test_images = []
        for i in range(3):
            test_image_path = os.path.join(self.temp_dir, f"concurrent_{i}.jpg")
            img = Image.new("RGB", (200, 200), color=(i * 80, 100, 150))
            img.save(test_image_path, "JPEG")
            test_images.append(test_image_path)

        # Upload all images concurrently (simulated)
        uploaded_images = []
        for i, image_path in enumerate(test_images):
            with open(image_path, "rb") as f:
                files = {"file": (f"concurrent_{i}.jpg", f, "image/jpeg")}
                data = {"dataset_id": 1}
                response = self.client.post(
                    "/api/images/upload", files=files, data=data
                )

            self.assertEqual(response.status_code, 200)
            upload_data = response.json()
            uploaded_images.append(upload_data["image_id"])

        # Create annotations for all images
        for i, image_id in enumerate(uploaded_images):
            annotation = {
                "image_id": image_id,
                "label_category_id": 1,
                "annotation_data": {
                    "tool": "bbox",
                    "coordinates": {
                        "startX": i * 50,
                        "startY": i * 50,
                        "endX": (i + 1) * 50,
                        "endY": (i + 1) * 50,
                    },
                },
                "confidence": 1.0,
            }

            response = self.client.post("/api/annotations", json=annotation)
            self.assertEqual(response.status_code, 200)

        # Verify all annotations exist
        for image_id in uploaded_images:
            response = self.client.get(f"/api/annotations/{image_id}")
            self.assertEqual(response.status_code, 200)
            annotations_data = response.json()
            self.assertEqual(len(annotations_data["annotations"]), 1)

        # Clean up
        for image_id in uploaded_images:
            response = self.client.delete(f"/api/images/{image_id}")
            self.assertEqual(response.status_code, 200)

    def test_data_persistence_workflow(self):
        """Test that data persists across requests"""
        # Step 1: Upload an image
        test_image_path = os.path.join(self.temp_dir, "persistence_test.jpg")
        img = Image.new("RGB", (300, 200), color="green")
        img.save(test_image_path, "JPEG")

        with open(test_image_path, "rb") as f:
            files = {"file": ("persistence_test.jpg", f, "image/jpeg")}
            data = {"dataset_id": 1}
            response = self.client.post("/api/images/upload", files=files, data=data)

        self.assertEqual(response.status_code, 200)
        upload_data = response.json()
        image_id = upload_data["image_id"]

        # Step 2: Create an annotation
        annotation = {
            "image_id": image_id,
            "label_category_id": 1,
            "annotation_data": {
                "tool": "point",
                "coordinates": {"startX": 150, "startY": 100},
            },
            "confidence": 1.0,
        }

        response = self.client.post("/api/annotations", json=annotation)
        self.assertEqual(response.status_code, 200)

        # Step 3: Make multiple requests to verify persistence
        for _ in range(3):
            response = self.client.get(f"/api/annotations/{image_id}")
            self.assertEqual(response.status_code, 200)
            annotations_data = response.json()
            self.assertEqual(len(annotations_data["annotations"]), 1)

            # Verify annotation data is correct
            annotation_data = annotations_data["annotations"][0]
            self.assertEqual(annotation_data["tool"], "point")
            self.assertEqual(annotation_data["coordinates"]["startX"], 150)
            self.assertEqual(annotation_data["coordinates"]["startY"], 100)

        # Clean up
        response = self.client.delete(f"/api/images/{image_id}")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
