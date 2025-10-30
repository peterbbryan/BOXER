"""Integration tests for YOLO classes import API."""

import unittest
import tempfile
import os
from fastapi.testclient import TestClient
from backend.main import app
from backend.database import get_db, Project, LabelCategory
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Create in-memory SQLite database for testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


class TestYOLOImportAPI(unittest.TestCase):
    """Integration tests for YOLO classes import API."""

    def setUp(self):
        """Set up test database and client."""
        # Override the database dependency
        app.dependency_overrides[get_db] = override_get_db

        # Create tables
        from backend.database import Base

        Base.metadata.create_all(bind=engine)

        # Create test client
        self.client = TestClient(app)

        # Create a test project
        with TestingSessionLocal() as db:
            project = Project(
                name="Test Project", description="Test project for YOLO import"
            )
            db.add(project)
            db.commit()
            self.project_id = project.id

    def tearDown(self):
        """Clean up after tests."""
        app.dependency_overrides.clear()

    def test_import_yolo_classes_integration(self):
        """Test full integration of YOLO classes import."""
        # Create a temporary classes.txt file
        classes_content = "person\ncar\ntruck\nbicycle\nmotorcycle"

        response = self.client.post(
            "/api/import/yolo-classes",
            files={"file": ("classes.txt", classes_content, "text/plain")},
            data={"project_id": self.project_id},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_classes"], 5)
        self.assertEqual(len(data["classes"]), 5)

        # Verify categories were created in database
        with TestingSessionLocal() as db:
            categories = (
                db.query(LabelCategory)
                .filter(LabelCategory.project_id == self.project_id)
                .all()
            )

            self.assertEqual(len(categories), 5)
            category_names = [cat.name for cat in categories]
            self.assertIn("person", category_names)
            self.assertIn("car", category_names)
            self.assertIn("truck", category_names)
            self.assertIn("bicycle", category_names)
            self.assertIn("motorcycle", category_names)

    def test_import_yolo_classes_with_duplicates(self):
        """Test import with duplicate class names (should be skipped)."""
        # First, create some existing categories
        with TestingSessionLocal() as db:
            existing_category = LabelCategory(name="person", project_id=self.project_id)
            db.add(existing_category)
            db.commit()

        # Import classes including the existing one
        classes_content = "person\ncar\ntruck"  # person already exists

        response = self.client.post(
            "/api/import/yolo-classes",
            files={"file": ("classes.txt", classes_content, "text/plain")},
            data={"project_id": self.project_id},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_classes"], 3)
        self.assertEqual(len(data["classes"]), 2)  # Only car and truck created

        # Verify only new categories were created
        with TestingSessionLocal() as db:
            categories = (
                db.query(LabelCategory)
                .filter(LabelCategory.project_id == self.project_id)
                .all()
            )

            self.assertEqual(len(categories), 3)  # 1 existing + 2 new
            category_names = [cat.name for cat in categories]
            self.assertIn("person", category_names)
            self.assertIn("car", category_names)
            self.assertIn("truck", category_names)

    def test_import_yolo_classes_empty_lines_and_whitespace(self):
        """Test import with empty lines and whitespace (should be handled correctly)."""
        classes_content = "person\n\ncar\n  truck  \n\nbicycle\n"

        response = self.client.post(
            "/api/import/yolo-classes",
            files={"file": ("classes.txt", classes_content, "text/plain")},
            data={"project_id": self.project_id},
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["total_classes"], 4)
        self.assertEqual(len(data["classes"]), 4)

        # Verify categories were created with trimmed names
        with TestingSessionLocal() as db:
            categories = (
                db.query(LabelCategory)
                .filter(LabelCategory.project_id == self.project_id)
                .all()
            )

            self.assertEqual(len(categories), 4)
            category_names = [cat.name for cat in categories]
            self.assertIn("person", category_names)
            self.assertIn("car", category_names)
            self.assertIn("truck", category_names)  # Should be trimmed
            self.assertIn("bicycle", category_names)

    def test_import_yolo_classes_nonexistent_project(self):
        """Test import with non-existent project ID."""
        classes_content = "person\ncar"

        response = self.client.post(
            "/api/import/yolo-classes",
            files={"file": ("classes.txt", classes_content, "text/plain")},
            data={"project_id": 99999},
        )

        self.assertEqual(response.status_code, 404)
        self.assertIn("Project not found", response.json()["detail"])

    def test_import_yolo_classes_invalid_file_type(self):
        """Test import with invalid file type."""
        response = self.client.post(
            "/api/import/yolo-classes",
            files={"file": ("classes.csv", "person,car", "text/csv")},
            data={"project_id": self.project_id},
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn("File must be a .txt file", response.json()["detail"])

    def test_import_yolo_classes_missing_project_id(self):
        """Test import without project_id parameter."""
        classes_content = "person\ncar"

        response = self.client.post(
            "/api/import/yolo-classes",
            files={"file": ("classes.txt", classes_content, "text/plain")},
        )

        self.assertEqual(response.status_code, 422)  # Validation error


if __name__ == "__main__":
    unittest.main()
