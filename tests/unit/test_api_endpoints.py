"""
Unit tests for FastAPI endpoints
"""

import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from backend.main import app
from backend.database import get_db


class TestAPIEndpoints(unittest.TestCase):
    """Test FastAPI endpoints"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a mock database session
        self.mock_db = MagicMock()

        # Override the dependency
        def override_get_db():
            yield self.mock_db

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

    def tearDown(self):
        """Clean up test fixtures"""
        # Clear dependency overrides
        app.dependency_overrides.clear()

    def test_health_endpoint(self):
        """Test health check endpoint"""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertIn("BOXER", data["message"])

    def test_root_endpoint_returns_html(self):
        """Test root endpoint returns HTML response"""
        # Configure mock database session
        self.mock_db.query.return_value.order_by.return_value.desc.return_value.first.return_value = (
            None
        )
        self.mock_db.query.return_value.filter.return_value.first.return_value = None
        self.mock_db.query.return_value.filter.return_value.all.return_value = []

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/html", response.headers["content-type"])
        self.assertIn("BOXER", response.text)

    def test_projects_endpoint(self):
        """Test projects endpoint"""
        # Configure mock database session
        self.mock_db.query.return_value.all.return_value = []

        response = self.client.get("/api/projects")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("projects", data)
        self.assertIsInstance(data["projects"], list)

    def test_annotations_endpoint_get(self):
        """Test annotations endpoint GET"""
        # Configure mock database session
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            MagicMock(id=1)
        )
        self.mock_db.query.return_value.filter.return_value.all.return_value = []

        response = self.client.get("/api/annotations/1")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("annotations", data)
        self.assertIsInstance(data["annotations"], list)

    def test_annotations_endpoint_post(self):
        """Test annotations endpoint POST"""
        # Configure mock database session
        mock_image = MagicMock(id=1, dataset_id=1)
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            mock_image
        )

        # Create a mock annotation that will be returned after refresh
        mock_annotation = MagicMock()
        mock_annotation.id = 123
        self.mock_db.refresh.return_value = None

        # After refresh, the annotation should have an id
        def mock_refresh(annotation):
            annotation.id = 123

        self.mock_db.refresh.side_effect = mock_refresh

        annotation_data = {
            "image_id": 1,
            "label_category_id": 1,
            "annotation_data": {"startX": 10, "startY": 10, "endX": 100, "endY": 100},
            "confidence": 0.95,
        }

        response = self.client.post("/api/annotations", json=annotation_data)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("annotation_id", data)
        self.assertIsInstance(data["annotation_id"], int)

    def test_annotations_endpoint_delete(self):
        """Test annotations endpoint DELETE"""
        # Configure mock database session
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            MagicMock(id=1)
        )

        response = self.client.delete("/api/annotations/1")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Annotation deleted successfully")

    def test_label_categories_endpoint(self):
        """Test label categories endpoint"""
        # Configure mock database session
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            MagicMock(id=1)
        )

        category_data = {"name": "Test Category", "color": "#FF0000", "project_id": 1}

        response = self.client.post("/api/label-categories", json=category_data)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Label category created successfully")

    def test_project_name_update_endpoint(self):
        """Test project name update endpoint"""
        # Configure mock database session
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            MagicMock(id=1)
        )

        update_data = {"name": "Updated Project Name"}

        response = self.client.put("/api/projects/1", json=update_data)
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Project updated successfully")

    def test_project_name_update_not_found(self):
        """Test project name update with non-existent project"""
        # Configure mock database session
        self.mock_db.query.return_value.filter.return_value.first.return_value = None

        update_data = {"name": "Updated Project Name"}

        response = self.client.put("/api/projects/999", json=update_data)
        self.assertEqual(response.status_code, 404)

        data = response.json()
        self.assertIn("detail", data)
        self.assertEqual(data["detail"], "Project not found")

    @patch("builtins.open")
    @patch("backend.main.process_uploaded_image")
    @patch("backend.main.validate_image")
    def test_image_upload_endpoint(self, mock_validate, mock_process, mock_open):
        """Test image upload endpoint"""
        # Configure mock database session
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            MagicMock(id=1)
        )

        # Mock validation to return True
        mock_validate.return_value = True

        # Mock file operations
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock process_uploaded_image to return the expected structure
        mock_process.return_value = {
            "filename": "test.jpg",
            "original_filename": "test.jpg",
            "file_path": "uploads/images/test.jpg",
            "thumbnail_path": "uploads/thumbnails/test.jpg",
            "width": 100,
            "height": 100,
            "file_size": 1024,
            "mime_type": "image/jpeg",
        }

        # Mock the image object returned after commit
        mock_image = MagicMock()
        mock_image.id = 1
        self.mock_db.add = MagicMock()
        self.mock_db.commit = MagicMock()
        self.mock_db.refresh = MagicMock(side_effect=lambda img: setattr(img, "id", 1))

        files = {"file": ("test.jpg", b"fake image data", "image/jpeg")}
        data = {"dataset_id": 1}

        response = self.client.post("/api/images/upload", files=files, data=data)
        self.assertEqual(response.status_code, 200)

        response_data = response.json()
        self.assertIn("image_id", response_data)
        self.assertIn("message", response_data)

    @patch("os.path.exists")
    @patch("os.remove")
    def test_image_delete_endpoint(self, mock_remove, mock_exists):
        """Test image delete endpoint"""
        # Configure mock database session
        self.mock_db.query.return_value.filter.return_value.first.return_value = (
            MagicMock(id=1, file_path="test.jpg", thumbnail_path="thumb.jpg")
        )

        mock_exists.return_value = True

        response = self.client.delete("/api/images/1")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertIn("message", data)
        self.assertEqual(data["message"], "Image deleted successfully")


if __name__ == "__main__":
    unittest.main()
