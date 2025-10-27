"""
Database configuration and models for VibeCortex Data Labeling Tool
"""

from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Float, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os

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
    __tablename__ = "label_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    color = Column(String(7), default="#3B82F6")  # Hex color
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    project = relationship("Project", back_populates="label_categories")
    annotations = relationship("Annotation", back_populates="label_category")

class Annotation(Base):
    __tablename__ = "annotations"
    
    id = Column(Integer, primary_key=True, index=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    label_category_id = Column(Integer, ForeignKey("label_categories.id"), nullable=False)
    
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
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Database initialization
def create_tables():
    """Create all database tables"""
    # Ensure data directory exists
    os.makedirs("../data", exist_ok=True)
    Base.metadata.create_all(bind=engine)

def init_database():
    """Initialize database with default data"""
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
                {"name": "Other", "color": "#FF00FF"}
            ]
            
            for cat_data in default_categories:
                existing = db.query(LabelCategory).filter(
                    LabelCategory.name == cat_data["name"],
                    LabelCategory.project_id == project.id
                ).first()
                
                if not existing:
                    category = LabelCategory(
                        name=cat_data["name"],
                        color=cat_data["color"],
                        project_id=project.id
                    )
                    db.add(category)
            
            db.commit()
            print("✅ Default label categories created")
    finally:
        db.close()