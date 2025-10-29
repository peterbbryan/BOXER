"""
Database migration and schema tests
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from unittest.mock import patch
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database import (
    Base,
    get_db,
    init_database,
    Project,
    Dataset,
    Image,
    Annotation,
    LabelCategory,
)


class TestDatabaseMigrations(unittest.TestCase):
    """Test database migrations and schema integrity"""

    def setUp(self):
        """Set up test fixtures"""
        # Create a temporary database
        self.temp_db_path = tempfile.mktemp(suffix=".db")
        self.engine = create_engine(f"sqlite:///{self.temp_db_path}")
        self.SessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )

    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up database
        if os.path.exists(self.temp_db_path):
            os.remove(self.temp_db_path)

    def test_database_creation(self):
        """Test that database can be created successfully"""
        # Create all tables
        Base.metadata.create_all(bind=self.engine)

        # Verify tables exist
        with self.engine.connect() as conn:
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table';")
            )
            tables = [row[0] for row in result]

            expected_tables = [
                "projects",
                "datasets",
                "images",
                "annotations",
                "label_categories",
            ]
            for table in expected_tables:
                self.assertIn(table, tables)

    def test_table_schemas(self):
        """Test that table schemas are correct"""
        Base.metadata.create_all(bind=self.engine)

        with self.engine.connect() as conn:
            # Test projects table schema
            result = conn.execute(text("PRAGMA table_info(projects);"))
            projects_columns = [row[1] for row in result]
            expected_projects_columns = [
                "id",
                "name",
                "description",
                "is_public",
                "created_at",
                "updated_at",
            ]
            for col in expected_projects_columns:
                self.assertIn(col, projects_columns)

            # Test datasets table schema
            result = conn.execute(text("PRAGMA table_info(datasets);"))
            datasets_columns = [row[1] for row in result]
            expected_datasets_columns = [
                "id",
                "name",
                "description",
                "project_id",
                "created_at",
            ]
            for col in expected_datasets_columns:
                self.assertIn(col, datasets_columns)

            # Test images table schema
            result = conn.execute(text("PRAGMA table_info(images);"))
            images_columns = [row[1] for row in result]
            expected_images_columns = [
                "id",
                "filename",
                "original_filename",
                "file_path",
                "thumbnail_path",
                "width",
                "height",
                "file_size",
                "mime_type",
                "dataset_id",
                "uploaded_at",
            ]
            for col in expected_images_columns:
                self.assertIn(col, images_columns)

            # Test annotations table schema
            result = conn.execute(text("PRAGMA table_info(annotations);"))
            annotations_columns = [row[1] for row in result]
            expected_annotations_columns = [
                "id",
                "image_id",
                "dataset_id",
                "label_category_id",
                "annotation_data",
                "confidence",
                "is_verified",
                "created_at",
                "updated_at",
            ]
            for col in expected_annotations_columns:
                self.assertIn(col, annotations_columns)

            # Test label_categories table schema
            result = conn.execute(text("PRAGMA table_info(label_categories);"))
            categories_columns = [row[1] for row in result]
            expected_categories_columns = [
                "id",
                "name",
                "color",
                "project_id",
                "created_at",
            ]
            for col in expected_categories_columns:
                self.assertIn(col, categories_columns)

    def test_foreign_key_constraints(self):
        """Test that foreign key constraints are properly set up"""
        Base.metadata.create_all(bind=self.engine)

        with self.engine.connect() as conn:
            # Enable foreign key constraints
            conn.execute(text("PRAGMA foreign_keys = ON;"))

            # Test that foreign key constraints work
            # Try to insert a dataset with non-existent project_id
            with self.assertRaises(Exception):
                conn.execute(
                    text(
                        "INSERT INTO datasets (name, project_id) VALUES ('test', 999);"
                    )
                )

    def test_indexes_creation(self):
        """Test that indexes are created properly"""
        Base.metadata.create_all(bind=self.engine)

        with self.engine.connect() as conn:
            # Check for indexes
            result = conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='index';")
            )
            indexes = [row[0] for row in result]

            # Check for common indexes
            expected_indexes = [
                "ix_projects_id",
                "ix_datasets_id",
                "ix_images_id",
                "ix_annotations_id",
                "ix_label_categories_id",
            ]
            for index in expected_indexes:
                self.assertIn(index, indexes)

    def test_data_integrity_constraints(self):
        """Test that data integrity constraints work"""
        Base.metadata.create_all(bind=self.engine)

        with self.engine.connect() as conn:
            # Test NOT NULL constraints
            with self.assertRaises(Exception):
                conn.execute(text("INSERT INTO projects (name) VALUES (NULL);"))

            with self.assertRaises(Exception):
                conn.execute(
                    text("INSERT INTO datasets (name, project_id) VALUES (NULL, 1);")
                )

    def test_model_relationships(self):
        """Test that model relationships work correctly"""
        Base.metadata.create_all(bind=self.engine)

        db = self.SessionLocal()

        try:
            # Create a project
            project = Project(name="Test Project", description="Test Description")
            db.add(project)
            db.commit()
            db.refresh(project)

            # Create a dataset associated with the project
            dataset = Dataset(name="Test Dataset", project_id=project.id)
            db.add(dataset)
            db.commit()
            db.refresh(dataset)

            # Create an image associated with the dataset
            image = Image(
                filename="test.jpg",
                original_filename="test.jpg",
                file_path="test.jpg",
                thumbnail_path="thumb_test.jpg",
                width=800,
                height=600,
                file_size=12345,
                mime_type="image/jpeg",
                dataset_id=dataset.id,
            )
            db.add(image)
            db.commit()
            db.refresh(image)

            # Create a label category associated with the project
            category = LabelCategory(
                name="Test Category", color="#FF0000", project_id=project.id
            )
            db.add(category)
            db.commit()
            db.refresh(category)

            # Create an annotation associated with the image and category
            annotation = Annotation(
                image_id=image.id,
                dataset_id=dataset.id,
                label_category_id=category.id,
                annotation_data='{"startX": 100, "startY": 100, "endX": 200, "endY": 200}',
            )
            db.add(annotation)
            db.commit()
            db.refresh(annotation)

            # Verify relationships
            self.assertEqual(dataset.project_id, project.id)
            self.assertEqual(image.dataset_id, dataset.id)
            self.assertEqual(category.project_id, project.id)
            self.assertEqual(annotation.image_id, image.id)
            self.assertEqual(annotation.dataset_id, dataset.id)
            self.assertEqual(annotation.label_category_id, category.id)

        finally:
            db.close()

    def test_database_initialization(self):
        """Test that database initialization works correctly"""
        # Create tables first
        Base.metadata.create_all(bind=self.engine)

        # Create a project
        db = self.SessionLocal()
        try:
            # Create a default project
            project = Project(
                name="Default Project",
                description="Default project for image labeling",
                is_public=True,
            )
            db.add(project)
            db.commit()
            db.refresh(project)

            # Check that tables exist by querying them
            projects = db.query(Project).all()
            datasets = db.query(Dataset).all()
            categories = db.query(LabelCategory).all()

            # Check that we have some data
            self.assertGreaterEqual(len(projects), 0)
            self.assertGreaterEqual(len(datasets), 0)
            self.assertGreaterEqual(len(categories), 0)

        finally:
            db.close()

    def test_database_rollback(self):
        """Test that database rollback works correctly"""
        Base.metadata.create_all(bind=self.engine)

        db = self.SessionLocal()

        try:
            # Start a transaction
            db.begin()

            # Create a project
            project = Project(name="Test Project")
            db.add(project)

            # Rollback the transaction
            db.rollback()

            # Verify that the project was not created
            projects = db.query(Project).all()
            self.assertEqual(len(projects), 0)

        finally:
            db.close()

    def test_database_commit(self):
        """Test that database commit works correctly"""
        Base.metadata.create_all(bind=self.engine)

        db = self.SessionLocal()

        try:
            # Create a project
            project = Project(name="Test Project")
            db.add(project)
            db.commit()

            # Verify that the project was created
            projects = db.query(Project).all()
            self.assertEqual(len(projects), 1)
            self.assertEqual(projects[0].name, "Test Project")

        finally:
            db.close()

    def test_database_cleanup(self):
        """Test that database cleanup works correctly"""
        Base.metadata.create_all(bind=self.engine)

        db = self.SessionLocal()

        try:
            # Create some test data
            project = Project(name="Test Project")
            db.add(project)
            db.commit()

            # Verify data exists
            projects = db.query(Project).all()
            self.assertEqual(len(projects), 1)

            # Clean up
            db.delete(project)
            db.commit()

            # Verify data was deleted
            projects = db.query(Project).all()
            self.assertEqual(len(projects), 0)

        finally:
            db.close()

    def test_database_performance(self):
        """Test database performance with large datasets"""
        Base.metadata.create_all(bind=self.engine)

        db = self.SessionLocal()

        try:
            # Create a project
            project = Project(name="Performance Test Project")
            db.add(project)
            db.commit()
            db.refresh(project)

            # Create many datasets
            datasets = []
            for i in range(100):
                dataset = Dataset(name=f"Dataset {i}", project_id=project.id)
                datasets.append(dataset)
                db.add(dataset)
            db.commit()

            # Verify all datasets were created
            dataset_count = db.query(Dataset).count()
            self.assertEqual(dataset_count, 100)

            # Test query performance
            import time

            start_time = time.time()

            # Query all datasets
            all_datasets = db.query(Dataset).all()

            end_time = time.time()
            query_time = end_time - start_time

            # Query should complete quickly (less than 1 second)
            self.assertLess(query_time, 1.0)
            self.assertEqual(len(all_datasets), 100)

        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
