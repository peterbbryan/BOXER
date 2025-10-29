"""
Unit tests for FastAPI endpoints
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from fastapi.testclient import TestClient
import sys
import os
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.main import app
from backend.database import get_db, init_database


class TestAPIEndpoints(unittest.TestCase):
    """Test FastAPI endpoints"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = TestClient(app)

        # Mock the database session
        self.mock_db = Mock()
        self.app_patcher = patch("backend.main.get_db")
        self.mock_get_db = self.app_patcher.start()
        self.mock_get_db.return_value = self.mock_db

    def tearDown(self):
        """Clean up test fixtures"""
        self.app_patcher.stop()

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("VibeCortex", data["message"])

    def test_root_endpoint_returns_html(self):
        """Test root endpoint returns HTML response"""
        with patch("backend.main.get_db") as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            # Mock database queries
            mock_db.query.return_value.order_by.return_value.desc.return_value.first.return_value = (
                None
            )
            mock_db.query.return_value.filter.return_value.first.return_value = None
            mock_db.query.return_value.filter.return_value.all.return_value = []

            response = self.client.get("/")
            self.assertEqual(response.status_code, 200)
            self.assertIn("text/html", response.headers["content-type"])
            self.assertIn("VibeCortex", response.text)

    def test_projects_endpoint(self):
        """Test projects endpoint"""
        with patch("backend.main.get_db") as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            # Mock project data
            mock_project = Mock()
            mock_project.id = 1
            mock_project.name = "Test Project"
            mock_project.description = "Test Description"
            mock_project.is_public = True
            mock_project.created_at = "2023-01-01T00:00:00"
            mock_project.updated_at = "2023-01-01T00:00:00"

            mock_db.query.return_value.all.return_value = [mock_project]

            response = self.client.get("/api/projects")
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertIn("projects", data)
            self.assertEqual(len(data["projects"]), 1)
            self.assertEqual(data["projects"][0]["name"], "Test Project")

    def test_annotations_endpoint_get(self):
        """Test getting annotations for an image"""
        with patch("backend.main.get_db") as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            # Mock annotation data
            mock_annotation = Mock()
            mock_annotation.id = 1
            mock_annotation.image_id = 1
            mock_annotation.label_category_id = 1
            mock_annotation.tool = "bbox"
            mock_annotation.annotation_data = (
                '{"startX": 100, "startY": 100, "endX": 200, "endY": 200}'
            )
            mock_annotation.created_at = "2023-01-01T00:00:00"

            mock_db.query.return_value.filter.return_value.all.return_value = [
                mock_annotation
            ]

            response = self.client.get("/api/annotations/1")
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertIn("annotations", data)
            self.assertEqual(len(data["annotations"]), 1)
            self.assertEqual(data["annotations"][0]["tool"], "bbox")

    def test_annotations_endpoint_post(self):
        """Test creating a new annotation"""
        with patch("backend.main.get_db") as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            # Mock database operations
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_db.refresh = Mock()

            annotation_data = {
                "image_id": 1,
                "label_category_id": 1,
                "tool": "bbox",
                "coordinates": {"startX": 100, "startY": 100, "endX": 200, "endY": 200},
            }

            response = self.client.post("/api/annotations", json=annotation_data)
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertIn("message", data)
            self.assertEqual(data["message"], "Annotation created successfully")

    def test_annotations_endpoint_delete(self):
        """Test deleting an annotation"""
        with patch("backend.main.get_db") as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            # Mock annotation to delete
            mock_annotation = Mock()
            mock_annotation.id = 1
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_annotation
            )
            mock_db.delete = Mock()
            mock_db.commit = Mock()

            response = self.client.delete("/api/annotations/1")
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertIn("message", data)
            self.assertEqual(data["message"], "Annotation deleted successfully")

    def test_annotations_endpoint_delete_not_found(self):
        """Test deleting a non-existent annotation"""
        with patch("backend.main.get_db") as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            # Mock annotation not found
            mock_db.query.return_value.filter.return_value.first.return_value = None

            response = self.client.delete("/api/annotations/999")
            self.assertEqual(response.status_code, 404)

            data = response.json()
            self.assertIn("detail", data)
            self.assertEqual(data["detail"], "Annotation not found")

    def test_label_categories_endpoint(self):
        """Test label categories endpoint"""
        with patch("backend.main.get_db") as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            # Mock label category data
            mock_category = Mock()
            mock_category.id = 1
            mock_category.name = "Test Category"
            mock_category.color = "#FF0000"
            mock_category.created_at = "2023-01-01T00:00:00"

            mock_db.query.return_value.filter.return_value.all.return_value = [
                mock_category
            ]

            response = self.client.get("/api/label-categories")
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertIn("categories", data)
            self.assertEqual(len(data["categories"]), 1)
            self.assertEqual(data["categories"][0]["name"], "Test Category")

    def test_project_name_update_endpoint(self):
        """Test updating project name"""
        with patch("backend.main.get_db") as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            # Mock project data
            mock_project = Mock()
            mock_project.id = 1
            mock_project.name = "Old Name"
            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_project
            )
            mock_db.commit = Mock()

            update_data = {"name": "New Name"}
            response = self.client.put("/api/projects/1/name", json=update_data)
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertIn("message", data)
            self.assertEqual(data["message"], "Project name updated successfully")

    def test_project_name_update_not_found(self):
        """Test updating non-existent project name"""
        with patch("backend.main.get_db") as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            # Mock project not found
            mock_db.query.return_value.filter.return_value.first.return_value = None

            update_data = {"name": "New Name"}
            response = self.client.put("/api/projects/999/name", json=update_data)
            self.assertEqual(response.status_code, 404)

            data = response.json()
            self.assertIn("detail", data)
            self.assertEqual(data["detail"], "Project not found")

    def test_image_upload_endpoint(self):
        """Test image upload endpoint"""
        with patch("backend.main.get_db") as mock_get_db, patch(
            "backend.main.process_uploaded_image"
        ) as mock_process:
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            # Mock database operations
            mock_db.add = Mock()
            mock_db.commit = Mock()
            mock_db.refresh = Mock()

            # Mock image processing
            mock_process.return_value = {
                "filename": "test.jpg",
                "file_path": "uploads/images/test.jpg",
                "thumbnail_path": "uploads/thumbnails/thumb_test.jpg",
                "width": 800,
                "height": 600,
                "file_size": 12345,
                "mime_type": "image/jpeg",
            }

            # Create a test file
            test_file_content = b"fake image content"
            files = {"file": ("test.jpg", test_file_content, "image/jpeg")}

            response = self.client.post("/api/upload", files=files)
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertIn("message", data)
            self.assertEqual(data["message"], "Image uploaded successfully")

    def test_image_delete_endpoint(self):
        """Test image deletion endpoint"""
        with patch("backend.main.get_db") as mock_get_db, patch(
            "backend.main.delete_image_files"
        ) as mock_delete_files:
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            # Mock image data
            mock_image = Mock()
            mock_image.id = 1
            mock_image.filename = "test.jpg"
            mock_image.file_path = "uploads/images/test.jpg"
            mock_image.thumbnail_path = "uploads/thumbnails/thumb_test.jpg"

            mock_db.query.return_value.filter.return_value.first.return_value = (
                mock_image
            )
            mock_db.delete = Mock()
            mock_db.commit = Mock()
            mock_delete_files.return_value = True

            response = self.client.delete("/api/images/1")
            self.assertEqual(response.status_code, 200)

            data = response.json()
            self.assertIn("message", data)
            self.assertEqual(data["message"], "Image deleted successfully")

    def test_image_delete_not_found(self):
        """Test deleting non-existent image"""
        with patch("backend.main.get_db") as mock_get_db:
            mock_db = Mock()
            mock_get_db.return_value = mock_db

            # Mock image not found
            mock_db.query.return_value.filter.return_value.first.return_value = None

            response = self.client.delete("/api/images/999")
            self.assertEqual(response.status_code, 404)

            data = response.json()
            self.assertIn("detail", data)
            self.assertEqual(data["detail"], "Image not found")


if __name__ == "__main__":
    unittest.main()
