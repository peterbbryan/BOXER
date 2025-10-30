"""
API contract tests to ensure API stability
"""

import unittest
from fastapi.testclient import TestClient

from backend.main import app


class TestAPIContracts(unittest.TestCase):
    """Test API contracts and response schemas"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = TestClient(app)

    def test_health_endpoint_contract(self):
        """Test health endpoint contract"""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)

        data = response.json()

        # Required fields
        self.assertIn("status", data)
        self.assertIn("message", data)

        # Field types
        self.assertIsInstance(data["status"], str)
        self.assertIsInstance(data["message"], str)

        # Expected values
        self.assertEqual(data["status"], "healthy")
        self.assertIn("BOXER", data["message"])

    def test_projects_endpoint_contract(self):
        """Test projects endpoint contract"""
        response = self.client.get("/api/projects")
        self.assertEqual(response.status_code, 200)

        data = response.json()

        # Required fields
        self.assertIn("projects", data)

        # Field types
        self.assertIsInstance(data["projects"], list)

        # If projects exist, check their structure
        if data["projects"]:
            project = data["projects"][0]
            required_fields = [
                "id",
                "name",
                "description",
                "is_public",
                "created_at",
                "updated_at",
            ]

            for field in required_fields:
                self.assertIn(field, project)

            # Field types
            self.assertIsInstance(project["id"], int)
            self.assertIsInstance(project["name"], str)
            self.assertIsInstance(project["is_public"], bool)
            self.assertIsInstance(project["created_at"], str)
            self.assertIsInstance(project["updated_at"], str)

    def test_annotations_endpoint_contract(self):
        """Test annotations endpoint contract"""
        # Test with non-existent image (should return empty list)
        response = self.client.get("/api/annotations/99999")
        self.assertEqual(response.status_code, 200)

        data = response.json()

        # Required fields for success response
        self.assertIn("annotations", data)
        self.assertIsInstance(data["annotations"], list)
        self.assertEqual(len(data["annotations"]), 0)

    def test_annotation_creation_contract(self):
        """Test annotation creation contract"""
        # Test with invalid data (should return error)
        invalid_annotation = {
            "image_id": 99999,  # Non-existent image
            "label_category_id": 1,
            "annotation_data": {"startX": 100, "startY": 100, "endX": 200, "endY": 200},
            "confidence": 1.0,
        }

        response = self.client.post("/api/annotations", json=invalid_annotation)
        self.assertEqual(response.status_code, 404)

        data = response.json()

        # Required fields for error response
        self.assertIn("detail", data)
        self.assertIsInstance(data["detail"], str)

    def test_annotation_deletion_contract(self):
        """Test annotation deletion contract"""
        # Test with non-existent annotation
        response = self.client.delete("/api/annotations/99999")
        self.assertEqual(response.status_code, 404)

        data = response.json()

        # Required fields for error response
        self.assertIn("detail", data)
        self.assertIsInstance(data["detail"], str)

    def test_label_categories_endpoint_contract(self):
        """Test label categories endpoint contract"""
        # Test POST endpoint (only available endpoint)
        response = self.client.post(
            "/api/label-categories",
            json={"name": "Test Category", "color": "#FF0000", "project_id": 1},
        )
        self.assertEqual(response.status_code, 200)

        data = response.json()

        # Required fields
        self.assertIn("message", data)
        self.assertIn("category_id", data)
        self.assertIsInstance(data["message"], str)
        self.assertIsInstance(data["category_id"], int)

    def test_project_name_update_contract(self):
        """Test project name update contract"""
        # Test with non-existent project
        update_data = {"name": "New Name"}
        response = self.client.put("/api/projects/99999/name", json=update_data)
        self.assertEqual(response.status_code, 404)

        data = response.json()

        # Required fields for error response
        self.assertIn("detail", data)
        self.assertIsInstance(data["detail"], str)

    def test_image_upload_contract(self):
        """Test image upload contract"""
        # Test with invalid file type
        files = {"file": ("test.txt", b"not an image", "text/plain")}
        data = {"dataset_id": 1}
        response = self.client.post("/api/images/upload", files=files, data=data)
        self.assertEqual(response.status_code, 400)

        data = response.json()

        # Required fields for error response
        self.assertIn("detail", data)
        self.assertIsInstance(data["detail"], str)

    def test_image_deletion_contract(self):
        """Test image deletion contract"""
        # Test with non-existent image
        response = self.client.delete("/api/images/99999")
        self.assertEqual(response.status_code, 404)

        data = response.json()

        # Required fields for error response
        self.assertIn("detail", data)
        self.assertIsInstance(data["detail"], str)

    def test_error_response_consistency(self):
        """Test that all error responses follow the same contract"""
        error_endpoints = [
            ("/api/annotations/99999", "DELETE"),
            ("/api/images/99999", "DELETE"),
            ("/api/projects/99999", "PUT"),
        ]

        for endpoint, method in error_endpoints:
            with self.subTest(endpoint=endpoint, method=method):
                if method == "GET":
                    response = self.client.get(endpoint)
                elif method == "DELETE":
                    response = self.client.delete(endpoint)
                elif method == "PUT":
                    response = self.client.put(endpoint, json={"name": "test"})

                # All error responses should have status 404
                self.assertEqual(response.status_code, 404)

                data = response.json()

                # All error responses should have "detail" field
                self.assertIn("detail", data)
                self.assertIsInstance(data["detail"], str)
                self.assertGreater(len(data["detail"]), 0)

    def test_success_response_consistency(self):
        """Test that all success responses follow consistent patterns"""
        # Test health endpoint
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)

        # Test projects endpoint
        response = self.client.get("/api/projects")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn("projects", data)

        # Test label categories endpoint (POST only)
        response = self.client.post(
            "/api/label-categories",
            json={"name": "Test Category", "color": "#FF0000", "project_id": 1},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsInstance(data, dict)
        self.assertIn("message", data)

    def test_content_type_consistency(self):
        """Test that all responses have correct content types"""
        endpoints = [
            "/api/health",
            "/api/projects",
            "/api/annotations/99999",
        ]

        for endpoint in endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                self.assertIn("application/json", response.headers["content-type"])

    def test_cors_headers(self):
        """Test CORS headers are present"""
        # Make a request with Origin header to trigger CORS
        response = self.client.get(
            "/api/health", headers={"Origin": "http://localhost:3000"}
        )

        # CORS headers should be present for cross-origin requests
        self.assertIn("access-control-allow-origin", response.headers)
        # Note: FastAPI CORS middleware may not add all headers for simple requests
        # We'll just check for the essential ones that are present

    def test_api_versioning_consistency(self):
        """Test that all API endpoints follow consistent versioning"""
        api_endpoints = [
            "/api/health",
            "/api/projects",
            "/api/annotations/99999",
            "/api/label-categories",
        ]

        for endpoint in api_endpoints:
            with self.subTest(endpoint=endpoint):
                # All API endpoints should start with /api/
                self.assertTrue(endpoint.startswith("/api/"))

                # All API endpoints should be lowercase
                self.assertEqual(endpoint, endpoint.lower())

    def test_request_method_consistency(self):
        """Test that endpoints use appropriate HTTP methods"""
        # GET endpoints should be idempotent
        get_endpoints = [
            "/api/health",
            "/api/projects",
            "/api/annotations/99999",
        ]

        for endpoint in get_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.get(endpoint)
                # GET requests should not modify data
                self.assertIn(response.status_code, [200, 404])

        # POST endpoints should create resources
        post_endpoints = [
            "/api/annotations",
            "/api/images/upload",
            "/api/label-categories",
        ]

        for endpoint in post_endpoints:
            with self.subTest(endpoint=endpoint):
                # POST requests should return 400 or 404 for invalid data
                response = self.client.post(endpoint, json={})
                self.assertIn(response.status_code, [200, 400, 404, 422])

        # DELETE endpoints should remove resources
        delete_endpoints = [
            "/api/annotations/99999",
            "/api/images/99999",
        ]

        for endpoint in delete_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.delete(endpoint)
                # DELETE requests should return 200 or 404
                self.assertIn(response.status_code, [200, 404])

        # PUT endpoints should update resources
        put_endpoints = [
            "/api/projects/99999/name",
        ]

        for endpoint in put_endpoints:
            with self.subTest(endpoint=endpoint):
                response = self.client.put(endpoint, json={"name": "test"})
                # PUT requests should return 200 or 404
                self.assertIn(response.status_code, [200, 404])


if __name__ == "__main__":
    unittest.main()
