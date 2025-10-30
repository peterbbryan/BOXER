"""
Database configuration and models for BOXER Data Labeling Tool
"""

import os
from datetime import datetime
from typing import Generator

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship, sessionmaker

# Database configuration
# Use an absolute path for the database file
current_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(current_dir, "..", "data")
os.makedirs(data_dir, exist_ok=True)  # Ensure the data directory exists
DATABASE_URL = f"sqlite:///{os.path.join(data_dir, 'vibecortex.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Database Models
class Project(Base):
    """SQLAlchemy model for projects.

    Attributes:
        id: Primary key identifier.
        name: Project name (max 100 characters).
        description: Optional project description.
        is_public: Whether the project is publicly accessible.
        created_at: Timestamp when project was created.
        updated_at: Timestamp when project was last updated.
        datasets: Relationship to associated datasets.
        label_categories: Relationship to associated label categories.
    """

    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    datasets = relationship("Dataset", back_populates="project")
    label_categories = relationship("LabelCategory", back_populates="project")


class Dataset(Base):
    """SQLAlchemy model for datasets.

    Attributes:
        id: Primary key identifier.
        name: Dataset name (max 100 characters).
        description: Optional dataset description.
        project_id: Foreign key to the parent project.
        created_at: Timestamp when dataset was created.
        project: Relationship to parent project.
        images: Relationship to associated images.
        annotations: Relationship to associated annotations.
    """

    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    project = relationship("Project", back_populates="datasets")
    images = relationship("Image", back_populates="dataset")
    annotations = relationship("Annotation", back_populates="dataset")


class Image(Base):
    """SQLAlchemy model for images.

    Attributes:
        id: Primary key identifier.
        filename: Unique generated filename.
        original_filename: Original filename from upload.
        file_path: Relative path to the image file.
        thumbnail_path: Relative path to the thumbnail file.
        width: Image width in pixels.
        height: Image height in pixels.
        file_size: Image file size in bytes.
        mime_type: MIME type of the image.
        dataset_id: Foreign key to the parent dataset.
        uploaded_at: Timestamp when image was uploaded.
        is_processed: Whether the image has been processed.
        dataset: Relationship to parent dataset.
        annotations: Relationship to associated annotations.
    """

    __tablename__ = "images"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=False)
    thumbnail_path = Column(String(500))
    width = Column(Integer)
    height = Column(Integer)
    file_size = Column(Integer)
    mime_type = Column(String(100))
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    is_processed = Column(Boolean, default=False)

    # Relationships
    dataset = relationship("Dataset", back_populates="images")
    annotations = relationship("Annotation", back_populates="image")


class LabelCategory(Base):
    """SQLAlchemy model for label categories.

    Attributes:
        id: Primary key identifier.
        name: Category name (max 100 characters).
        color: Hex color code for displaying the category.
        project_id: Foreign key to the parent project.
        created_at: Timestamp when category was created.
        project: Relationship to parent project.
        annotations: Relationship to associated annotations.
    """

    __tablename__ = "label_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    color = Column(String(7), default="#3B82F6")  # Hex color
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Add unique constraint: category names must be unique within a project
    __table_args__ = (
        UniqueConstraint("project_id", "name", name="uq_project_category_name"),
    )

    # Relationships
    project = relationship("Project", back_populates="label_categories")
    annotations = relationship("Annotation", back_populates="label_category")


class Annotation(Base):
    """SQLAlchemy model for annotations.

    Attributes:
        id: Primary key identifier.
        image_id: Foreign key to the annotated image.
        dataset_id: Foreign key to the parent dataset.
        label_category_id: Foreign key to the label category.
        annotation_data: JSON data containing annotation geometry
            (bounding boxes, polygons, points, etc.).
        confidence: Confidence score for the annotation (0.0 to 1.0).
        is_verified: Whether the annotation has been verified.
        created_at: Timestamp when annotation was created.
        updated_at: Timestamp when annotation was last updated.
        image: Relationship to annotated image.
        dataset: Relationship to parent dataset.
        label_category: Relationship to label category.
    """

    __tablename__ = "annotations"

    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    label_category_id = Column(
        Integer, ForeignKey("label_categories.id"), nullable=False
    )

    # Annotation data (JSON format for flexibility)
    annotation_data = Column(JSON)  # Bounding boxes, polygons, points, etc.
    confidence = Column(Float, default=1.0)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    image = relationship("Image", back_populates="annotations")
    dataset = relationship("Dataset", back_populates="annotations")
    label_category = relationship("LabelCategory", back_populates="annotations")


# Database dependency
def get_db() -> Generator[Session, None, None]:
    """Database dependency generator for FastAPI.

    Yields a database session and ensures it's closed after use.

    Yields:
        Database session object.

    Note:
        This is a FastAPI dependency that should be used with Depends().
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Database initialization
def create_tables() -> None:
    """Create all database tables.

    Initializes the database schema by creating all tables defined in the
    SQLAlchemy models if they don't already exist.
    """
    # Ensure data directory exists
    os.makedirs("../data", exist_ok=True)
    Base.metadata.create_all(bind=engine)


def init_database() -> None:
    """Initialize database with default data.

    Creates all database tables and populates the default project with
    standard label categories (Object, Person, Vehicle, Building, Other).
    """
    create_tables()

    # Create default label categories for the default project
    db = SessionLocal()
    try:
        # Get the default project
        project = db.query(Project).filter(Project.name == "Default Project").first()
        if project:
            # Create default label categories
            default_categories = [
                {"name": "Object", "color": "#FF0000"},
                {"name": "Person", "color": "#00FF00"},
                {"name": "Vehicle", "color": "#0000FF"},
                {"name": "Building", "color": "#FFFF00"},
                {"name": "Other", "color": "#FF00FF"},
            ]

            for cat_data in default_categories:
                existing = (
                    db.query(LabelCategory)
                    .filter(
                        LabelCategory.name == cat_data["name"],
                        LabelCategory.project_id == project.id,
                    )
                    .first()
                )

                if not existing:
                    category = LabelCategory(
                        name=cat_data["name"],
                        color=cat_data["color"],
                        project_id=project.id,
                    )
                    db.add(category)

            db.commit()
            print("✅ Default label categories created")
    finally:
        db.close()
