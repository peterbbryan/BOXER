"""
VibeCortex Backend - Multi-User Data Labeling Tool
"""

import os
from datetime import datetime
from typing import Any, Dict, Optional

import uvicorn
from fastapi import Depends, FastAPI, Form, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session

# Import our modules
from backend.database import (
    Annotation,
    Dataset,
    Image,
    LabelCategory,
    Project,
    get_db,
    init_database,
)
from backend.image_utils import process_uploaded_image, validate_image

# Create FastAPI app
app = FastAPI(
    title="VibeCortex Data Labeling Tool",
    description="Multi-user data labeling tool with real-time collaboration",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    # Configure for large file uploads (50MB default)
    max_request_size=100 * 1024 * 1024,  # 100MB
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
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
templates = Jinja2Templates(directory=os.path.join(project_root, "templates"))

# Only mount static and uploads if directories exist
static_dir = os.path.join(project_root, "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

uploads_dir = os.path.join(project_root, "uploads")
if os.path.exists(uploads_dir):
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")


# Pydantic models
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    is_public: bool = False


class ProjectUpdate(BaseModel):
    name: str


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


class AnnotationUpdate(BaseModel):
    annotation_data: Optional[dict] = None
    confidence: Optional[float] = None
    is_verified: Optional[bool] = None


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request) -> HTMLResponse:
    """Serve the main labeling interface.

    Args:
        request: FastAPI request object.

    Returns:
        HTMLResponse: Rendered labeling interface template with project,
        dataset, images, and label categories data.
    """
    # Get or create a default project and dataset
    db = next(get_db())
    try:
        # Get the most recent project or create a default one
        project = db.query(Project).order_by(Project.updated_at.desc()).first()
        if not project:
            project = Project(
                name="Default Project",
                description="Default project for image labeling",
                is_public=True,
            )
            db.add(project)
            db.commit()
            db.refresh(project)

        # Get or create default dataset
        dataset = (
            db.query(Dataset)
            .filter(Dataset.name == "Default Dataset", Dataset.project_id == project.id)
            .first()
        )
        if not dataset:
            dataset = Dataset(
                name="Default Dataset",
                description="Default dataset for image labeling",
                project_id=project.id,
            )
            db.add(dataset)
            db.commit()
            db.refresh(dataset)

        # Get images for labeling
        images = db.query(Image).filter(Image.dataset_id == dataset.id).all()

        # Get label categories
        label_categories = (
            db.query(LabelCategory).filter(LabelCategory.project_id == project.id).all()
        )

        # Convert to dictionaries for JSON serialization
        images_data = []
        for img in images:
            images_data.append(
                {
                    "id": img.id,
                    "filename": img.filename,
                    "original_filename": img.original_filename,
                    "file_path": img.file_path,
                    "thumbnail_path": img.thumbnail_path,
                    "width": img.width,
                    "height": img.height,
                    "file_size": img.file_size,
                    "mime_type": img.mime_type,
                    "uploaded_at": (
                        img.uploaded_at.isoformat() if img.uploaded_at else None
                    ),
                }
            )
        label_categories_data = []
        for cat in label_categories:
            label_categories_data.append(
                {
                    "id": cat.id,
                    "name": cat.name,
                    "color": cat.color,
                    "created_at": (
                        cat.created_at.isoformat() if cat.created_at else None
                    ),
                }
            )
        return templates.TemplateResponse(
            "labeling.html",
            {
                "request": request,
                "title": "VibeCortex - Image Labeling Tool",
                "project": project,
                "dataset": dataset,
                "images": images_data,
                "label_categories": label_categories_data,
            },
        )
    finally:
        db.close()


# API Endpoints
@app.get("/api/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint.

    Returns:
        Dict containing status and message indicating the API is running.
    """
    return {"status": "healthy", "message": "VibeCortex Data Labeling Tool is running!"}


# Project endpoints
@app.post("/api/projects")
async def create_project(
    project_data: ProjectCreate, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Create a new project.

    Args:
        project_data: Project creation data including name and description.
        db: Database session dependency.

    Returns:
        Dict containing success message and project_id of the created project.
    """
    project = Project(
        name=project_data.name,
        description=project_data.description,
        is_public=project_data.is_public,
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return {"message": "Project created successfully", "project_id": project.id}


@app.get("/api/projects")
async def get_projects(db: Session = Depends(get_db)):
    """Get all projects.

    Args:
        db: Database session dependency.

    Returns:
        Dict containing list of all projects.
    """
    projects = db.query(Project).all()
    return {"projects": projects}


@app.put("/api/projects/{project_id}")
async def update_project(
    project_id: int, project_data: ProjectUpdate, db: Session = Depends(get_db)
):
    """Update a project name.

    Args:
        project_id: ID of the project to update.
        project_data: Project update data containing new name.
        db: Database session dependency.

    Returns:
        Dict containing success message and updated project data.

    Raises:
        HTTPException: If project with given ID is not found.
    """
    # Find the project
    project = db.query(Project).filter(Project.id == project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Update project name
    project.name = project_data.name
    project.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(project)

    return {"message": "Project updated successfully", "project": project}


# Dataset endpoints
@app.post("/api/datasets")
async def create_dataset(dataset_data: DatasetCreate, db: Session = Depends(get_db)):
    """Create a new dataset.

    Args:
        dataset_data: Dataset creation data including name and project_id.
        db: Database session dependency.

    Returns:
        Dict containing success message and dataset_id of the created dataset.

    Raises:
        HTTPException: If parent project is not found.
    """
    # Verify project exists
    project = db.query(Project).filter(Project.id == dataset_data.project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    dataset = Dataset(
        name=dataset_data.name,
        description=dataset_data.description,
        project_id=dataset_data.project_id,
    )

    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return {"message": "Dataset created successfully", "dataset_id": dataset.id}


# Image upload endpoint
@app.post("/api/images/upload")
async def upload_image(
    file: UploadFile = File(...),  # 100MB max file size (handled below)
    dataset_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """Upload an image to a dataset.

    Supports large images up to 100MB. The system automatically:
    - Validates the image
    - Creates a thumbnail for faster loading
    - Stores the image with unique filename
    - Records metadata in the database

    Args:
        file: Uploaded image file (max 100MB).
        dataset_id: ID of the dataset to upload to.
        db: Database session dependency.

    Returns:
        Dict containing success message and image_id of the uploaded image.

    Raises:
        HTTPException: If dataset not found, file too large, or file validation fails.
    """
    # Verify dataset exists
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    # Check file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    # Check file size (max 100MB)
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        max_size_mb = MAX_FILE_SIZE / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {max_size_mb:.0f}MB",
        )

    # Save file temporarily
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(content)

    try:
        # Additional validation using image_utils
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
            dataset_id=dataset_id,
        )

        db.add(image)
        db.commit()
        db.refresh(image)

        return {"message": "Image uploaded successfully", "image_id": image.id}

    except Exception as e:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(
            status_code=500, detail=f"Error processing image: {str(e)}"
        ) from e


# Image delete endpoint
@app.delete("/api/images/{image_id}")
async def delete_image(image_id: int, db: Session = Depends(get_db)):
    """Delete an image and its associated files.

    Args:
        image_id: ID of the image to delete.
        db: Database session dependency.

    Returns:
        Dict containing success message and image_id.

    Raises:
        HTTPException: If image not found or deletion fails.
    """
    # Find the image
    image = db.query(Image).filter(Image.id == image_id).first()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    try:
        # Delete associated annotations first (due to foreign key constraints)
        db.query(Annotation).filter(Annotation.image_id == image_id).delete()

        # Delete the image record
        db.delete(image)
        db.commit()

        # Delete the actual files

        # Get absolute paths
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        proj_root = os.path.dirname(backend_dir)

        # Delete main image file
        main_image_path = os.path.join(proj_root, image.file_path)
        if os.path.exists(main_image_path):
            os.remove(main_image_path)

        # Delete thumbnail file
        thumbnail_path = os.path.join(proj_root, image.thumbnail_path)
        if os.path.exists(thumbnail_path):
            os.remove(thumbnail_path)

        return {"message": "Image deleted successfully", "image_id": image_id}

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error deleting image: {str(e)}"
        ) from e


# Label category endpoints
@app.post("/api/label-categories")
async def create_label_category(
    category_data: LabelCategoryCreate, db: Session = Depends(get_db)
):
    """Create a new label category.

    Args:
        category_data: Category creation data including name, color, and project_id.
        db: Database session dependency.

    Returns:
        Dict containing success message and category_id of the created category.

    Raises:
        HTTPException: If parent project is not found.
    """
    # Verify project exists
    project = db.query(Project).filter(Project.id == category_data.project_id).first()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    category = LabelCategory(
        name=category_data.name,
        color=category_data.color,
        project_id=category_data.project_id,
    )

    db.add(category)
    db.commit()
    db.refresh(category)

    return {
        "message": "Label category created successfully",
        "category_id": category.id,
    }


# Annotation endpoints
@app.post("/api/annotations")
async def create_annotation(
    annotation_data: AnnotationCreate, db: Session = Depends(get_db)
):
    """Create a new annotation.

    Args:
        annotation_data: Annotation creation data including image_id,
            label_category_id, annotation_data, and confidence.
        db: Database session dependency.

    Returns:
        Dict containing success message and annotation_id of the created annotation.

    Raises:
        HTTPException: If image not found.
    """
    # Verify image exists
    image = db.query(Image).filter(Image.id == annotation_data.image_id).first()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    annotation = Annotation(
        image_id=annotation_data.image_id,
        dataset_id=image.dataset_id,
        label_category_id=annotation_data.label_category_id,
        annotation_data=annotation_data.annotation_data,
        confidence=annotation_data.confidence,
    )

    db.add(annotation)
    db.commit()
    db.refresh(annotation)

    return {
        "message": "Annotation created successfully",
        "annotation_id": annotation.id,
    }


@app.get("/api/annotations/{image_id}")
async def get_annotations(image_id: int, db: Session = Depends(get_db)):
    """Get annotations for an image.

    Args:
        image_id: ID of the image to get annotations for.
        db: Database session dependency.

    Returns:
        Dict containing list of annotations for the image. Returns empty list
        if image doesn't exist.
    """
    # Return empty list for non-existent images to match test expectations
    image = db.query(Image).filter(Image.id == image_id).first()

    if not image:
        return {"annotations": []}

    annotations = db.query(Annotation).filter(Annotation.image_id == image_id).all()

    # Serialize annotations
    annotations_data = []
    for ann in annotations:
        annotation_dict = {
            "id": ann.id,
            "image_id": ann.image_id,
            "dataset_id": ann.dataset_id,
            "label_category_id": ann.label_category_id,
            "annotation_data": ann.annotation_data,
            "confidence": ann.confidence,
            "is_verified": ann.is_verified,
            "created_at": ann.created_at.isoformat() if ann.created_at else None,
            "updated_at": ann.updated_at.isoformat() if ann.updated_at else None,
        }
        # Extract tool from annotation_data if it exists
        if ann.annotation_data and isinstance(ann.annotation_data, dict):
            annotation_dict["tool"] = ann.annotation_data.get("tool")
            annotation_dict["coordinates"] = ann.annotation_data.get("coordinates")
        annotations_data.append(annotation_dict)

    return {"annotations": annotations_data}


@app.delete("/api/annotations/{annotation_id}")
async def delete_annotation(annotation_id: int, db: Session = Depends(get_db)):
    """Delete an annotation.

    Args:
        annotation_id: ID of the annotation to delete.
        db: Database session dependency.

    Returns:
        Dict containing success message.

    Raises:
        HTTPException: If annotation not found.
    """
    # Find the annotation
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()

    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    # Delete the annotation
    db.delete(annotation)
    db.commit()

    return {"message": "Annotation deleted successfully"}


@app.put("/api/annotations/{annotation_id}")
async def update_annotation(
    annotation_id: int, update_data: AnnotationUpdate, db: Session = Depends(get_db)
):
    """Update an annotation.

    Args:
        annotation_id: ID of the annotation to update.
        update_data: Annotation update data.
        db: Database session dependency.

    Returns:
        Dict containing success message and updated annotation data.

    Raises:
        HTTPException: If annotation not found.
    """
    # Find the annotation
    annotation = db.query(Annotation).filter(Annotation.id == annotation_id).first()

    if not annotation:
        raise HTTPException(status_code=404, detail="Annotation not found")

    # Update annotation fields
    if update_data.annotation_data is not None:
        annotation.annotation_data = update_data.annotation_data
    if update_data.confidence is not None:
        annotation.confidence = update_data.confidence
    if update_data.is_verified is not None:
        annotation.is_verified = update_data.is_verified

    # Commit changes
    db.commit()
    db.refresh(annotation)

    # Build response
    response_data = {
        "message": "Annotation updated successfully",
        "annotation_id": annotation.id,
    }

    # Add updated annotation data
    if annotation.annotation_data and isinstance(annotation.annotation_data, dict):
        response_data["tool"] = annotation.annotation_data.get("tool")
        response_data["coordinates"] = annotation.annotation_data.get("coordinates")

    return response_data


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True, log_level="info")
