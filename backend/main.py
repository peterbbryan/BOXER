"""
VibeCortex Backend - Multi-User Data Labeling Tool
"""

from fastapi import FastAPI, Request, Form, HTTPException, Depends, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from typing import Optional, List
import uvicorn
from pathlib import Path
import json
import os
from datetime import datetime
from sqlalchemy.orm import Session

# Import our modules
from database import get_db, init_database, Project, Dataset, Image, Annotation, LabelCategory
from image_utils import process_uploaded_image, get_supported_formats

# Create FastAPI app
app = FastAPI(
    title="VibeCortex Data Labeling Tool",
    description="Multi-user data labeling tool with real-time collaboration",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# Initialize database on startup
@app.on_event("startup")
async def startup_event():
    init_database()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates and static files
templates = Jinja2Templates(directory="../templates")
app.mount("/static", StaticFiles(directory="../static"), name="static")

# Mount uploads directory to serve uploaded images and thumbnails
uploads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads")
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")

# Pydantic models
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False

class DatasetCreate(BaseModel):
    name: str
    description: Optional[str] = None
    project_id: int

class LabelCategoryCreate(BaseModel):
    name: str
    color: str = "#3B82F6"
    project_id: int

class AnnotationCreate(BaseModel):
    image_id: int
    label_category_id: int
    annotation_data: dict
    confidence: float = 1.0

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    """Serve the main labeling interface"""
    # Get or create a default project and dataset
    db = next(get_db())
    try:
        # Get or create default project
        project = db.query(Project).filter(Project.name == "Default Project").first()
        if not project:
            project = Project(
                name="Default Project",
                description="Default project for image labeling",
                is_public=True
            )
            db.add(project)
            db.commit()
            db.refresh(project)
        
        # Get or create default dataset
        dataset = db.query(Dataset).filter(Dataset.name == "Default Dataset", Dataset.project_id == project.id).first()
        if not dataset:
            dataset = Dataset(
                name="Default Dataset",
                description="Default dataset for image labeling",
                project_id=project.id
            )
            db.add(dataset)
            db.commit()
            db.refresh(dataset)
        
        # Get images for labeling
        images = db.query(Image).filter(Image.dataset_id == dataset.id).all()
        
        # Get label categories
        label_categories = db.query(LabelCategory).filter(
            LabelCategory.project_id == project.id
        ).all()
        
        # Convert to dictionaries for JSON serialization
        images_data = []
        for img in images:
            images_data.append({
                "id": img.id,
                "filename": img.filename,
                "original_filename": img.original_filename,
                "file_path": img.file_path,
                "thumbnail_path": img.thumbnail_path,
                "width": img.width,
                "height": img.height,
                "file_size": img.file_size,
                "mime_type": img.mime_type,
                "uploaded_at": img.uploaded_at.isoformat() if img.uploaded_at else None
            })
        
        label_categories_data = []
        for cat in label_categories:
            label_categories_data.append({
                "id": cat.id,
                "name": cat.name,
                "color": cat.color,
                "created_at": cat.created_at.isoformat() if cat.created_at else None
            })
        
        return templates.TemplateResponse("labeling.html", {
            "request": request,
            "title": "VibeCortex - Image Labeling Tool",
            "project": project,
            "dataset": dataset,
            "images": images_data,
            "label_categories": label_categories_data
        })
    finally:
        db.close()


# API Endpoints
@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "VibeCortex Data Labeling Tool is running!"}


# Project endpoints
@app.post("/api/projects")
async def create_project(
    project_data: ProjectCreate, 
    db: Session = Depends(get_db)
):
    """Create a new project"""
    project = Project(
        name=project_data.name,
        description=project_data.description,
        is_public=project_data.is_public
    )
    
    db.add(project)
    db.commit()
    db.refresh(project)
    
    return {"message": "Project created successfully", "project_id": project.id}

@app.get("/api/projects")
async def get_projects(db: Session = Depends(get_db)):
    """Get all projects"""
    projects = db.query(Project).all()
    return {"projects": projects}

# Dataset endpoints
@app.post("/api/datasets")
async def create_dataset(
    dataset_data: DatasetCreate,
    db: Session = Depends(get_db)
):
    """Create a new dataset"""
    # Verify project exists
    project = db.query(Project).filter(Project.id == dataset_data.project_id).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    dataset = Dataset(
        name=dataset_data.name,
        description=dataset_data.description,
        project_id=dataset_data.project_id
    )
    
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    
    return {"message": "Dataset created successfully", "dataset_id": dataset.id}

# Image upload endpoint
@app.post("/api/images/upload")
async def upload_image(
    file: UploadFile = File(...),
    dataset_id: int = Form(...),
    db: Session = Depends(get_db)
):
    """Upload an image to a dataset"""
    # Verify dataset exists
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
    
    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")
    
    # Check file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Save file temporarily
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    
    try:
        # Additional validation using image_utils
        from image_utils import validate_image
        if not validate_image(temp_path):
            raise HTTPException(status_code=400, detail="Invalid image file")
        
        # Process image
        image_info = process_uploaded_image(temp_path, file.filename)
        
        # Save to database
        image = Image(
            filename=image_info["filename"],
            original_filename=image_info["original_filename"],
            file_path=image_info["file_path"],
            thumbnail_path=image_info["thumbnail_path"],
            width=image_info["width"],
            height=image_info["height"],
            file_size=image_info["file_size"],
            mime_type=image_info["mime_type"],
            dataset_id=dataset_id
        )
        
        db.add(image)
        db.commit()
        db.refresh(image)
        
        return {"message": "Image uploaded successfully", "image_id": image.id}
    
    except Exception as e:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")

# Label category endpoints
@app.post("/api/label-categories")
async def create_label_category(
    category_data: LabelCategoryCreate,
    db: Session = Depends(get_db)
):
    """Create a new label category"""
    # Verify project exists
    project = db.query(Project).filter(Project.id == category_data.project_id).first()
    
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    category = LabelCategory(
        name=category_data.name,
        color=category_data.color,
        project_id=category_data.project_id
    )
    
    db.add(category)
    db.commit()
    db.refresh(category)
    
    return {"message": "Label category created successfully", "category_id": category.id}

# Annotation endpoints
@app.post("/api/annotations")
async def create_annotation(
    annotation_data: AnnotationCreate,
    db: Session = Depends(get_db)
):
    """Create a new annotation"""
    # Verify image exists
    image = db.query(Image).filter(Image.id == annotation_data.image_id).first()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    annotation = Annotation(
        image_id=annotation_data.image_id,
        dataset_id=image.dataset_id,
        label_category_id=annotation_data.label_category_id,
        annotation_data=annotation_data.annotation_data,
        confidence=annotation_data.confidence
    )
    
    db.add(annotation)
    db.commit()
    db.refresh(annotation)
    
    return {"message": "Annotation created successfully", "annotation_id": annotation.id}

@app.get("/api/annotations/{image_id}")
async def get_annotations(
    image_id: int,
    db: Session = Depends(get_db)
):
    """Get annotations for an image"""
    # Verify image exists
    image = db.query(Image).filter(Image.id == image_id).first()
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    annotations = db.query(Annotation).filter(Annotation.image_id == image_id).all()
    return {"annotations": annotations}

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
