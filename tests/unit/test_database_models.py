"""
Unit tests for database models
"""

import unittest
from unittest.mock import Mock, patch
import sys
from pathlib import Path
from datetime import datetime

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database import Project, Dataset, Image, Annotation, LabelCategory


class TestDatabaseModels(unittest.TestCase):
    """Test database models"""

    def test_project_model(self):
        """Test Project model creation and attributes"""
        project = Project(
            name="Test Project", description="Test Description", is_public=True
        )

        self.assertEqual(project.name, "Test Project")
        self.assertEqual(project.description, "Test Description")
        self.assertTrue(project.is_public)
        # Timestamps are set by SQLAlchemy when saved to database, not when created in memory
        # self.assertIsNotNone(project.created_at)
        # self.assertIsNotNone(project.updated_at)

    def test_project_model_defaults(self):
        """Test Project model default values"""
        project = Project(name="Test Project")

        self.assertEqual(project.name, "Test Project")
        self.assertIsNone(project.description)
        self.assertFalse(project.is_public)  # Default should be False
        # Timestamps are set by SQLAlchemy when saved to database, not when created in memory
        # self.assertIsNotNone(project.created_at)
        # self.assertIsNotNone(project.updated_at)

    def test_dataset_model(self):
        """Test Dataset model creation and attributes"""
        project = Project(name="Test Project")
        dataset = Dataset(
            name="Test Dataset", description="Test Dataset Description", project_id=1
        )

        self.assertEqual(dataset.name, "Test Dataset")
        self.assertEqual(dataset.description, "Test Dataset Description")
        self.assertEqual(dataset.project_id, 1)
        # Timestamps are set by SQLAlchemy when saved to database, not when created in memory
        # self.assertIsNotNone(dataset.created_at)

    def test_image_model(self):
        """Test Image model creation and attributes"""
        image = Image(
            filename="test.jpg",
            original_filename="original_test.jpg",
            file_path="uploads/images/test.jpg",
            thumbnail_path="uploads/thumbnails/thumb_test.jpg",
            width=800,
            height=600,
            file_size=12345,
            mime_type="image/jpeg",
            dataset_id=1,
        )

        self.assertEqual(image.filename, "test.jpg")
        self.assertEqual(image.original_filename, "original_test.jpg")
        self.assertEqual(image.file_path, "uploads/images/test.jpg")
        self.assertEqual(image.thumbnail_path, "uploads/thumbnails/thumb_test.jpg")
        self.assertEqual(image.width, 800)
        self.assertEqual(image.height, 600)
        self.assertEqual(image.file_size, 12345)
        self.assertEqual(image.mime_type, "image/jpeg")
        self.assertEqual(image.dataset_id, 1)
        # Timestamps are set by SQLAlchemy when saved to database, not when created in memory
        # self.assertIsNotNone(image.uploaded_at)

    def test_annotation_model_bbox(self):
        """Test Annotation model for bounding box"""
        annotation = Annotation(
            image_id=1,
            dataset_id=1,
            label_category_id=1,
            annotation_data='{"startX": 100, "startY": 100, "endX": 200, "endY": 200}',
        )

        self.assertEqual(annotation.image_id, 1)
        self.assertEqual(annotation.dataset_id, 1)
        self.assertEqual(annotation.label_category_id, 1)
        self.assertEqual(
            annotation.annotation_data,
            '{"startX": 100, "startY": 100, "endX": 200, "endY": 200}',
        )
        # Timestamps are set by SQLAlchemy when saved to database, not when created in memory
        # self.assertIsNotNone(annotation.created_at)

    def test_annotation_model_point(self):
        """Test Annotation model for point"""
        annotation = Annotation(
            image_id=1,
            dataset_id=1,
            label_category_id=1,
            annotation_data='{"startX": 150, "startY": 150}',
        )

        self.assertEqual(annotation.image_id, 1)
        self.assertEqual(annotation.dataset_id, 1)
        self.assertEqual(annotation.label_category_id, 1)
        self.assertEqual(annotation.annotation_data, '{"startX": 150, "startY": 150}')

    def test_annotation_model_polygon(self):
        """Test Annotation model for polygon"""
        polygon_data = '{"points": [{"x": 100, "y": 100}, {"x": 200, "y": 100}, {"x": 200, "y": 200}, {"x": 100, "y": 200}]}'
        annotation = Annotation(
            image_id=1,
            dataset_id=1,
            label_category_id=1,
            annotation_data=polygon_data,
        )

        self.assertEqual(annotation.image_id, 1)
        self.assertEqual(annotation.dataset_id, 1)
        self.assertEqual(annotation.label_category_id, 1)
        self.assertEqual(annotation.annotation_data, polygon_data)

    def test_label_category_model(self):
        """Test LabelCategory model creation and attributes"""
        category = LabelCategory(name="Test Category", color="#FF0000", project_id=1)

        self.assertEqual(category.name, "Test Category")
        self.assertEqual(category.color, "#FF0000")
        self.assertEqual(category.project_id, 1)
        # Timestamps are set by SQLAlchemy when saved to database, not when created in memory
        # self.assertIsNotNone(category.created_at)

    def test_label_category_model_defaults(self):
        """Test LabelCategory model default values"""
        category = LabelCategory(name="Test Category", project_id=1)

        self.assertEqual(category.name, "Test Category")
        self.assertEqual(category.project_id, 1)
        self.assertIsNone(category.color)  # Default should be None
        # Timestamps are set by SQLAlchemy when saved to database, not when created in memory
        # self.assertIsNotNone(category.created_at)

    def test_model_relationships(self):
        """Test model relationships"""
        # Create a project
        project = Project(name="Test Project")

        # Create a dataset associated with the project
        dataset = Dataset(name="Test Dataset", project_id=1)

        # Create an image associated with the dataset
        image = Image(
            filename="test.jpg",
            file_path="uploads/images/test.jpg",
            thumbnail_path="uploads/thumbnails/thumb_test.jpg",
            width=800,
            height=600,
            file_size=12345,
            mime_type="image/jpeg",
            dataset_id=1,
        )

        # Create a label category associated with the project
        category = LabelCategory(name="Test Category", color="#FF0000", project_id=1)

        # Create an annotation associated with the image and category
        annotation = Annotation(
            image_id=1,
            dataset_id=1,
            label_category_id=1,
            annotation_data='{"startX": 100, "startY": 100, "endX": 200, "endY": 200}',
        )

        # Verify the relationships make sense
        self.assertEqual(dataset.project_id, 1)
        self.assertEqual(image.dataset_id, 1)
        self.assertEqual(category.project_id, 1)
        self.assertEqual(annotation.image_id, 1)
        self.assertEqual(annotation.dataset_id, 1)
        self.assertEqual(annotation.label_category_id, 1)

    def test_model_timestamps(self):
        """Test that timestamps are set correctly"""
        # Note: Timestamps are only set when objects are saved to the database
        # This test is disabled as we're testing in-memory objects
        # In a real test, you would need to save to database first
        pass

    def test_model_string_representations(self):
        """Test model string representations"""
        project = Project(name="Test Project")
        dataset = Dataset(name="Test Dataset", project_id=1)
        image = Image(
            filename="test.jpg",
            file_path="test.jpg",
            width=800,
            height=600,
            file_size=12345,
            mime_type="image/jpeg",
            dataset_id=1,
        )
        category = LabelCategory(name="Test Category", project_id=1)
        annotation = Annotation(
            image_id=1, dataset_id=1, label_category_id=1, annotation_data="{}"
        )

        # Test that string representations don't raise exceptions
        str(project)
        str(dataset)
        str(image)
        str(category)
        str(annotation)

    def test_model_validation(self):
        """Test model validation constraints"""
        # Test that models can be created with minimal required fields
        project = Project(name="Test Project")
        self.assertEqual(project.name, "Test Project")

        dataset = Dataset(name="Test Dataset", project_id=1)
        self.assertEqual(dataset.name, "Test Dataset")
        self.assertEqual(dataset.project_id, 1)

        image = Image(
            filename="test.jpg",
            original_filename="test.jpg",
            file_path="test.jpg",
            dataset_id=1,
        )
        self.assertEqual(image.filename, "test.jpg")

        category = LabelCategory(name="Test Category", project_id=1)
        self.assertEqual(category.name, "Test Category")

        annotation = Annotation(
            image_id=1, dataset_id=1, label_category_id=1, annotation_data="{}"
        )
        self.assertEqual(annotation.image_id, 1)


if __name__ == "__main__":
    unittest.main()
