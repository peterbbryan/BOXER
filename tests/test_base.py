"""
Base test class with database setup for integration tests
"""

import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.database import Base, get_db
from backend.main import app


class DatabaseTestCase(unittest.TestCase):
    """Base test case class that sets up an in-memory database for testing"""

    @classmethod
    def setUpClass(cls):
        """Set up test database once for all tests in this class"""
        # Create in-memory SQLite database for testing
        cls.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        cls.TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=cls.engine
        )

    def setUp(self):
        """Set up test fixtures before each test"""
        # Create all tables
        Base.metadata.create_all(bind=self.engine)

        # Override the database dependency
        def override_get_db():
            try:
                db = self.TestingSessionLocal()
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

        # Create test client
        self.client = app.test_client() if hasattr(app, "test_client") else None
        if not self.client:
            from fastapi.testclient import TestClient

            self.client = TestClient(app)

        # Create default test data (project and dataset) for convenience
        self._create_default_test_data()

    def _create_default_test_data(self):
        """Create default test project, dataset, and label category"""
        from backend.database import Project, Dataset, LabelCategory

        db = self.TestingSessionLocal()
        try:
            # Create a test project
            project = Project(
                name="Test Project",
                description="Test project for integration tests",
                is_public=True,
            )
            db.add(project)
            db.commit()
            db.refresh(project)
            self.test_project_id = project.id

            # Create a test dataset
            dataset = Dataset(
                name="Test Dataset",
                description="Test dataset for integration tests",
                project_id=project.id,
            )
            db.add(dataset)
            db.commit()
            db.refresh(dataset)
            self.test_dataset_id = dataset.id

            # Create a test label category
            category = LabelCategory(
                name="Test Category", color="#FF0000", project_id=project.id
            )
            db.add(category)
            db.commit()
            db.refresh(category)
            self.test_category_id = category.id
        finally:
            db.close()

    def tearDown(self):
        """Clean up after each test"""
        # Drop all tables
        Base.metadata.drop_all(bind=self.engine)
        # Clear dependency overrides
        app.dependency_overrides.clear()
