"""
BOXER Backend - Multi-User Data Labeling Tool
"""

import io
import os
import random
import shutil
import tempfile
import zipfile
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from PIL import Image as PILImage
from fastapi import Depends, FastAPI, Form, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
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
from backend.image_utils import (
    process_uploaded_image,
    validate_image,
    convert_annotation_to_yolo,
    convert_yolo_to_annotation,
)

# Create FastAPI app
# Configure for large file uploads (SAR data can be 500MB+)
app = FastAPI(
    title="BOXER Data Labeling Tool",
    description="Multi-user data labeling tool with real-time collaboration",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)
# Set default maximum upload size for Starlette
app.router.default_max_size = 500 * 1024 * 1024  # 500MB


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
    label_category_id: Optional[int] = None
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
                "title": "BOXER - Image Labeling Tool",
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
    return {"status": "healthy", "message": "BOXER Data Labeling Tool is running!"}


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
    file: UploadFile = File(...),  # 500MB max file size (handled below)
    dataset_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """Upload an image to a dataset.

    Supports large images including SAR data up to 500MB. The system automatically:
    - Validates the image
    - Creates a thumbnail for faster loading
    - Stores the image with unique filename
    - Records metadata in the database
    - Converts special formats (SICD, NITF, R0) to standard images

    Args:
        file: Uploaded image file (max 500MB).
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

    # Check file type - accept image/* and special formats
    file_ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    special_formats = [".r0", ".sicd", ".nitf", ".ntf", ".nff"]

    if (
        not (file.content_type and file.content_type.startswith("image/"))
        and file_ext not in special_formats
    ):
        raise HTTPException(
            status_code=400,
            detail="File must be an image or supported raster/SAR format",
        )

    # Check file size (max 500MB for SAR data)
    MAX_FILE_SIZE = 500 * 1024 * 1024  # 500MB
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
        if image.file_path:
            # Handle both absolute and relative paths
            if os.path.isabs(image.file_path):
                main_image_path = image.file_path
            elif image.file_path.startswith("../"):
                # Handle ../uploads format
                main_image_path = os.path.normpath(
                    os.path.join(proj_root, image.file_path)
                )
            else:
                main_image_path = os.path.join(proj_root, image.file_path)

            if os.path.exists(main_image_path):
                os.remove(main_image_path)
                print(f"Deleted main image: {main_image_path}")

        # Delete thumbnail file
        if image.thumbnail_path:
            # Handle both absolute and relative paths
            if os.path.isabs(image.thumbnail_path):
                thumbnail_path = image.thumbnail_path
            elif image.thumbnail_path.startswith("../"):
                # Handle ../uploads format
                thumbnail_path = os.path.normpath(
                    os.path.join(proj_root, image.thumbnail_path)
                )
            else:
                thumbnail_path = os.path.join(proj_root, image.thumbnail_path)

            if os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
                print(f"Deleted thumbnail: {thumbnail_path}")

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


class LabelCategoryUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None


@app.put("/api/label-categories/{category_id}")
async def update_label_category(
    category_id: int, update: LabelCategoryUpdate, db: Session = Depends(get_db)
):
    """Update a label category's name and/or color.

    Args:
        category_id: ID of the category to update.
        update: Fields to update (name/color).
        db: Database session dependency.

    Returns:
        Dict with success message and updated fields.
    """
    category = db.query(LabelCategory).filter(LabelCategory.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    # Apply updates if provided
    if update.name is not None:
        # Ensure no duplicate within the same project
        exists = (
            db.query(LabelCategory)
            .filter(
                LabelCategory.project_id == category.project_id,
                LabelCategory.name == update.name,
                LabelCategory.id != category_id,
            )
            .first()
        )
        if exists:
            raise HTTPException(status_code=400, detail="Category name already exists")
        category.name = update.name

    if update.color is not None:
        category.color = update.color

    db.commit()
    db.refresh(category)

    return {
        "message": "Label category updated successfully",
        "category_id": category.id,
        "name": category.name,
        "color": category.color,
    }


@app.delete("/api/label-categories/{category_id}")
async def delete_label_category(category_id: int, db: Session = Depends(get_db)):
    """Delete a label category.

    Args:
        category_id: ID of the category to delete.
        db: Database session dependency.

    Returns:
        Dict containing success message and category_id of the deleted category.

    Raises:
        HTTPException: If category not found or deletion fails.
    """
    # Find the category
    category = db.query(LabelCategory).filter(LabelCategory.id == category_id).first()

    if not category:
        raise HTTPException(status_code=404, detail="Category not found")

    try:
        # First, delete all annotations that reference this category
        annotation_count = (
            db.query(Annotation)
            .filter(Annotation.label_category_id == category_id)
            .delete()
        )

        # Delete the category
        db.delete(category)
        db.commit()

        msg = (
            f"Label category deleted successfully "
            f"(removed {annotation_count} associated annotation(s))"
        )
        return {
            "message": msg,
            "category_id": category_id,
            "deleted_annotations": annotation_count,
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error deleting category: {str(e)}"
        ) from e


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
    if update_data.label_category_id is not None:
        annotation.label_category_id = update_data.label_category_id
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


@app.get("/api/export/yolo")
async def export_to_yolo(  # pylint: disable=too-many-locals
    db: Session = Depends(get_db),
) -> Response:
    """Export all annotations to YOLO format.

    Args:
        db: Database session dependency.

    Returns:
        ZIP file containing YOLO format annotations and images.
    """
    # Get all annotations
    all_annotations = db.query(Annotation).all()

    # Filter out annotations without valid annotation_data
    annotations = [ann for ann in all_annotations if ann.annotation_data is not None]

    if not annotations:
        raise HTTPException(status_code=404, detail="No annotations found to export")

    # Get all label categories used in annotations
    annotation_category_ids = {ann.label_category_id for ann in annotations}
    categories = (
        db.query(LabelCategory)
        .filter(LabelCategory.id.in_(annotation_category_ids))
        .all()
    )

    # Deduplicate categories by name (keep first occurrence)
    seen_names = {}
    unique_categories = []
    category_id_to_index = {}

    for cat in categories:
        if cat.name not in seen_names:
            seen_names[cat.name] = len(unique_categories)
            unique_categories.append(cat)
            category_id_to_index[cat.id] = len(unique_categories) - 1
        else:
            # Map duplicate category ID to the same index as the first occurrence
            category_id_to_index[cat.id] = seen_names[cat.name]

    categories = unique_categories

    # Create a ZIP file in memory
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        # Write classes.txt
        classes_content = "\n".join([cat.name for cat in categories])
        zip_file.writestr("classes.txt", classes_content)

        # Group annotations by image
        image_annotations = {}
        for ann in annotations:
            if ann.image_id not in image_annotations:
                image_annotations[ann.image_id] = []
            image_annotations[ann.image_id].append(ann)

        # Process each image
        for image_id, anns in image_annotations.items():
            image = db.query(Image).filter(Image.id == image_id).first()
            if not image:
                continue

            # Read the image to get dimensions
            backend_dir = os.path.dirname(os.path.abspath(__file__))
            proj_root = os.path.dirname(backend_dir)
            image_path = os.path.join(proj_root, image.file_path)

            if not os.path.exists(image_path):
                continue

            with PILImage.open(image_path) as img:
                image_width, image_height = img.size

            # Convert annotations to YOLO format
            yolo_lines = []
            for ann in anns:
                # Convert annotation data structure
                annotation_dict = {
                    "tool": ann.annotation_data.get("tool")
                    if isinstance(ann.annotation_data, dict)
                    else "bbox",
                    "coordinates": ann.annotation_data.get("coordinates")
                    if isinstance(ann.annotation_data, dict)
                    else ann.annotation_data,
                    "label_category_id": ann.label_category_id,
                }

                yolo_line = convert_annotation_to_yolo(
                    annotation_dict, image_width, image_height, category_id_to_index
                )
                if yolo_line:
                    yolo_lines.append(yolo_line)

            # Write annotation file
            if yolo_lines:
                # Use image filename without extension for .txt file
                image_basename = os.path.splitext(image.filename)[0]
                zip_file.writestr(f"labels/{image_basename}.txt", "\n".join(yolo_lines))

                # Copy image to ZIP
                with open(image_path, "rb") as f:
                    zip_file.writestr(f"images/{image.filename}", f.read())

    zip_buffer.seek(0)

    return Response(
        content=zip_buffer.read(),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=yolo_export.zip"},
    )


def generate_random_color() -> str:
    """Generate a random hex color code with high saturation and brightness.

    Returns:
        A random hex color code (e.g., '#FF5733').
    """
    # Generate colors with high saturation and brightness for better visibility
    # Use HSL-like approach to ensure vibrant colors
    hue = random.random()  # 0.0 to 1.0

    # Convert HSL to RGB for better color distribution
    # Using golden ratio to ensure colors are well-distributed
    h = int(hue * 360)
    s = random.randint(60, 100)  # High saturation
    l = random.randint(40, 60)  # Medium-light brightness

    # Simple HSL to RGB conversion
    c = (1 - abs(2 * l / 100 - 1)) * s / 100
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l / 100 - c / 2

    if h < 60:
        r, g, b = c, x, 0
    elif h < 120:
        r, g, b = x, c, 0
    elif h < 180:
        r, g, b = 0, c, x
    elif h < 240:
        r, g, b = 0, x, c
    elif h < 300:
        r, g, b = x, 0, c
    else:
        r, g, b = c, 0, x

    r = int((r + m) * 255)
    g = int((g + m) * 255)
    b = int((b + m) * 255)

    # Ensure values are in valid range
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))

    return f"#{r:02X}{g:02X}{b:02X}"


@app.post("/api/import/yolo-classes")
async def import_yolo_classes(
    file: UploadFile = File(...),
    project_id: int = Form(...),
    db: Session = Depends(get_db),
):
    """Import YOLO classes from a classes.txt file.

    Args:
        file: The classes.txt file containing class names (one per line).
        project_id: The project ID to associate the classes with.
        db: Database session dependency.

    Returns:
        Success message with number of classes imported.
    """
    # Validate file type
    if not file.filename or not file.filename.endswith(".txt"):
        raise HTTPException(status_code=400, detail="File must be a .txt file")

    # Read file content
    content = await file.read()
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(
            status_code=400, detail="File must be valid UTF-8 text"
        ) from exc

    # Parse class names (one per line, strip whitespace)
    class_names = [line.strip() for line in text_content.splitlines() if line.strip()]

    if not class_names:
        raise HTTPException(
            status_code=400, detail="No valid class names found in file"
        )

    # Check if project exists
    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Create label categories for each class
    created_categories = []
    for class_name in class_names:
        # Check if category already exists for this project
        existing_category = (
            db.query(LabelCategory)
            .filter(
                LabelCategory.name == class_name, LabelCategory.project_id == project_id
            )
            .first()
        )

        if not existing_category:
            # Generate a random color for each imported category
            random_color = generate_random_color()
            category = LabelCategory(
                name=class_name, project_id=project_id, color=random_color
            )
            db.add(category)
            db.flush()  # Flush to get the ID
            created_categories.append(category)

    db.commit()

    # Refresh categories to ensure they're committed
    for cat in created_categories:
        db.refresh(cat)

    return {
        "message": f"Successfully imported {len(created_categories)} classes",
        "classes": [cat.name for cat in created_categories],
        "total_classes": len(class_names),
    }


def _get_or_create_dataset(
    db: Session, project_id: int, dataset_id: Optional[int]
) -> Dataset:
    """Get or create dataset for YOLO import.

    Args:
        db: Database session.
        project_id: Project ID.
        dataset_id: Optional dataset ID.

    Returns:
        Dataset object.

    Raises:
        HTTPException: If dataset not found.
    """
    if dataset_id:
        dataset = db.query(Dataset).filter(Dataset.id == dataset_id).first()
        if not dataset:
            raise HTTPException(status_code=404, detail="Dataset not found")
        return dataset

    dataset = (
        db.query(Dataset)
        .filter(Dataset.name == "Default Dataset", Dataset.project_id == project_id)
        .first()
    )
    if not dataset:
        dataset = Dataset(
            name="Default Dataset",
            description="Default dataset",
            project_id=project_id,
        )
        db.add(dataset)
        db.commit()
        db.refresh(dataset)
    return dataset


def _read_classes_from_zip(temp_dir: str) -> list:
    """Read class names from classes.txt in ZIP extraction directory.

    Args:
        temp_dir: Temporary directory where ZIP was extracted.

    Returns:
        List of class names.

    Raises:
        HTTPException: If classes.txt not found or empty.
    """
    classes_file = os.path.join(temp_dir, "classes.txt")
    if not os.path.exists(classes_file):
        raise HTTPException(status_code=400, detail="ZIP file must contain classes.txt")

    with open(classes_file, "r", encoding="utf-8") as f:
        class_names = [line.strip() for line in f.readlines() if line.strip()]

    if not class_names:
        raise HTTPException(
            status_code=400, detail="No valid class names found in classes.txt"
        )
    return class_names


def _create_label_categories(
    db: Session, class_names: list, project_id: int
) -> Dict[int, int]:
    """Create or get label categories for class names.

    Args:
        db: Database session.
        class_names: List of class names.
        project_id: Project ID.

    Returns:
        Dictionary mapping class index to category ID.
    """
    class_index_to_category_id = {}
    for index, class_name in enumerate(class_names):
        existing_category = (
            db.query(LabelCategory)
            .filter(
                LabelCategory.name == class_name,
                LabelCategory.project_id == project_id,
            )
            .first()
        )
        if existing_category:
            class_index_to_category_id[index] = existing_category.id
        else:
            random_color = generate_random_color()
            category = LabelCategory(
                name=class_name, project_id=project_id, color=random_color
            )
            db.add(category)
            db.flush()
            class_index_to_category_id[index] = category.id
    db.commit()
    return class_index_to_category_id


def _create_image_from_info(image_info: Dict[str, Any], dataset_id: int) -> Image:
    """Create Image database object from image info.

    Args:
        image_info: Dictionary with image metadata.
        dataset_id: Dataset ID.

    Returns:
        Image database object.
    """
    return Image(
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


def _process_annotations_from_file(
    label_path: str,
    image_info: Dict[str, Any],
    class_index_to_category_id: Dict[int, int],
    db: Session,
) -> int:
    """Process annotations from YOLO label file.

    Args:
        label_path: Path to label file.
        image_info: Dictionary with image metadata including id, width, height.
        class_index_to_category_id: Mapping from class index to category ID.
        db: Database session.

    Returns:
        Number of annotations created.
    """
    if not os.path.exists(label_path):
        return 0

    annotation_count = 0
    with open(label_path, "r", encoding="utf-8") as f:
        yolo_lines = [line.strip() for line in f.readlines() if line.strip()]

    for yolo_line in yolo_lines:
        annotation_data = convert_yolo_to_annotation(
            yolo_line, image_info["width"], image_info["height"]
        )

        if annotation_data:
            class_index = annotation_data.pop("class_index")
            label_category_id = class_index_to_category_id.get(class_index)

            if label_category_id:
                annotation = Annotation(
                    image_id=image_info["id"],
                    dataset_id=image_info["dataset_id"],
                    label_category_id=label_category_id,
                    annotation_data=annotation_data,
                    confidence=1.0,
                )
                db.add(annotation)
                annotation_count += 1

    return annotation_count


def _process_yolo_image(
    image_file: str,
    import_config: Dict[str, Any],
    db: Session,
) -> Tuple[int, int]:
    """Process a single image file from YOLO import.

    Args:
        image_file: Name of image file.
        import_config: Dictionary with keys: images_dir, labels_dir, dataset,
            class_index_to_category_id.
        db: Database session.

    Returns:
        Tuple of (imported_images_count, imported_annotations_count).
    """
    image_path = os.path.join(import_config["images_dir"], image_file)
    label_path = os.path.join(
        import_config["labels_dir"], os.path.splitext(image_file)[0] + ".txt"
    )

    if not validate_image(image_path):
        return 0, 0

    try:
        image_info = process_uploaded_image(image_path, image_file)
        image = _create_image_from_info(image_info, import_config["dataset"].id)
        db.add(image)
        db.flush()

        full_image_info = {
            **image_info,
            "id": image.id,
            "dataset_id": import_config["dataset"].id,
        }
        annotation_count = _process_annotations_from_file(
            label_path,
            full_image_info,
            import_config["class_index_to_category_id"],
            db,
        )

        return 1, annotation_count
    except (OSError, IOError, ValueError, KeyError) as e:
        print(f"Error importing image {image_file}: {e}")
        return 0, 0


def _setup_import_directories() -> None:
    """Ensure upload directories exist for YOLO import."""
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    proj_root = os.path.dirname(backend_dir)
    for upload_dir in ["uploads/images", "uploads/thumbnails"]:
        os.makedirs(os.path.join(proj_root, upload_dir), exist_ok=True)


def _get_image_files(images_dir: str) -> list:
    """Get list of image files from directory.

    Args:
        images_dir: Directory containing images.

    Returns:
        List of image filenames.
    """
    return [
        f
        for f in os.listdir(images_dir)
        if f.lower().endswith(
            (".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".gif")
        )
    ]


def _validate_zip_structure(temp_dir: str) -> Tuple[str, str]:
    """Validate ZIP structure and return directory paths.

    Args:
        temp_dir: Temporary directory where ZIP was extracted.

    Returns:
        Tuple of (images_dir, labels_dir).

    Raises:
        HTTPException: If required directories are missing.
    """
    images_dir = os.path.join(temp_dir, "images")
    labels_dir = os.path.join(temp_dir, "labels")

    if not os.path.exists(images_dir):
        raise HTTPException(
            status_code=400, detail="ZIP file must contain images/ directory"
        )
    if not os.path.exists(labels_dir):
        raise HTTPException(
            status_code=400, detail="ZIP file must contain labels/ directory"
        )
    return images_dir, labels_dir


def _process_all_images(
    image_files: list,
    import_config: Dict[str, Any],
    db: Session,
) -> Dict[str, int]:
    """Process all images and return statistics.

    Args:
        image_files: List of image filenames.
        import_config: Import configuration dictionary.
        db: Database session.

    Returns:
        Dictionary with statistics.
    """
    stats = {"imported_images": 0, "imported_annotations": 0, "skipped_images": 0}

    for image_file in image_files:
        img_count, ann_count = _process_yolo_image(image_file, import_config, db)
        stats["imported_images"] += img_count
        stats["imported_annotations"] += ann_count
        if img_count == 0:
            stats["skipped_images"] += 1

    return stats


def _extract_yolo_zip(zip_buffer: io.BytesIO) -> str:
    """Extract YOLO ZIP file to temporary directory.

    Args:
        zip_buffer: BytesIO buffer containing ZIP file.

    Returns:
        Path to temporary extraction directory.
    """
    temp_dir = tempfile.mkdtemp()
    with zipfile.ZipFile(zip_buffer, "r") as zip_file:
        zip_file.extractall(temp_dir)
    return temp_dir


@app.post("/api/import/yolo")
async def import_yolo(
    file: UploadFile = File(...),
    project_id: int = Form(...),
    dataset_id: Optional[int] = Form(None),
    db: Session = Depends(get_db),
):
    """Import a complete YOLO dataset from a ZIP file.

    The ZIP file should contain:
    - classes.txt: Class names (one per line)
    - images/: Directory with image files
    - labels/: Directory with annotation files (.txt in YOLO format)

    Args:
        file: The YOLO export ZIP file.
        project_id: The project ID to import into.
        dataset_id: Optional dataset ID. If not provided, uses the default dataset.
        db: Database session dependency.

    Returns:
        Success message with import statistics.
    """
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="File must be a .zip file")

    if not db.query(Project).filter(Project.id == project_id).first():
        raise HTTPException(status_code=404, detail="Project not found")

    dataset = _get_or_create_dataset(db, project_id, dataset_id)
    temp_dir = _extract_yolo_zip(io.BytesIO(await file.read()))

    try:
        class_names = _read_classes_from_zip(temp_dir)
        class_index_to_category_id = _create_label_categories(
            db, class_names, project_id
        )

        images_dir, labels_dir = _validate_zip_structure(temp_dir)
        _setup_import_directories()

        import_config = {
            "images_dir": images_dir,
            "labels_dir": labels_dir,
            "dataset": dataset,
            "class_index_to_category_id": class_index_to_category_id,
        }

        stats = _process_all_images(_get_image_files(images_dir), import_config, db)

        db.commit()

        return {
            "message": "YOLO dataset imported successfully",
            "statistics": {
                "images_imported": stats["imported_images"],
                "annotations_imported": stats["imported_annotations"],
                "classes_imported": len(class_names),
                "images_skipped": stats["skipped_images"],
            },
        }

    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="Invalid ZIP file format") from exc
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error importing YOLO dataset: {str(e)}"
        ) from e
    finally:
        # Clean up temporary directory
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)


class ModelRunRequest(BaseModel):
    """Request model for running YOLO models.

    Attributes:
        image_id: ID of the image to run the model on.
        model_name: Name of the YOLO model to run (e.g., 'yolov8n.pt').
    """

    image_id: int
    model_name: str


@app.post("/api/run-model")
async def run_model(  # pylint: disable=too-many-locals
    request: ModelRunRequest, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Run a pretrained YOLO model on an image to generate annotations.

    Args:
        request: Request containing image_id and model_name.
        db: Database session dependency.

    Returns:
        Dict containing success message and detection count.

    Raises:
        HTTPException: If image not found, model doesn't exist, or execution fails.
    """
    # Verify image exists
    image = db.query(Image).filter(Image.id == request.image_id).first()
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Check if ultralytics is available
    try:
        from ultralytics import YOLO  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail="Ultralytics package not installed. Run: pip install ultralytics",
        ) from exc

    try:
        # Load the model
        model = YOLO(request.model_name)

        # Get the image path
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        proj_root = os.path.dirname(backend_dir)
        image_path = os.path.join(proj_root, image.file_path)

        if not os.path.exists(image_path):
            raise HTTPException(status_code=404, detail="Image file not found")

        # Run inference
        results = model(image_path)

        # Parse results and create annotations
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # Get coordinates in xyxy format (absolute pixels)
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
                # Convert to Python floats to avoid JSON serialization issues
                x1 = float(x1)
                y1 = float(y1)
                x2 = float(x2)
                y2 = float(y2)
                # Get class name
                class_id = int(box.cls[0].cpu().numpy())
                class_name = model.names[class_id]
                confidence = float(box.conf[0].cpu().numpy())

                # Find or create label category
                category = (
                    db.query(LabelCategory)
                    .filter(
                        LabelCategory.name == class_name,
                        LabelCategory.project_id == image.dataset.project_id,
                    )
                    .first()
                )

                if not category:
                    # Create new category with random color
                    category = LabelCategory(
                        name=class_name,
                        color=generate_random_color(),
                        project_id=image.dataset.project_id,
                    )
                    db.add(category)
                    db.commit()
                    db.refresh(category)

                # Create annotation
                annotation = Annotation(
                    image_id=request.image_id,
                    dataset_id=image.dataset_id,
                    label_category_id=category.id,
                    annotation_data={
                        "tool": "bbox",
                        "coordinates": {
                            "startX": x1,
                            "startY": y1,
                            "endX": x2,
                            "endY": y2,
                        },
                    },
                    confidence=confidence,
                )
                db.add(annotation)
                detections.append(
                    {
                        "class": class_name,
                        "confidence": confidence,
                        "bbox": [x1, y1, x2, y2],
                    }
                )

        db.commit()

        return {
            "message": f"Model {request.model_name} processed successfully",
            "detections": detections,
            "count": len(detections),
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error running model: {str(e)}"
        ) from e


@app.post("/api/advanced/clear-all")  # pylint: disable=too-many-locals
async def clear_all_data(  # pylint: disable=too-many-locals
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Clear all data from the system.

    This deletes:
    - All images and thumbnails from uploads directory
    - All database records (projects, datasets, images, annotations, categories)

    Args:
        db: Database session dependency.

    Returns:
        Dict containing success message and counts of deleted records.

    Warning:
        This is a destructive operation that cannot be undone.
    """
    try:
        # Count records before deletion
        project_count = db.query(Project).count()
        dataset_count = db.query(Dataset).count()
        image_count = db.query(Image).count()
        annotation_count = db.query(Annotation).count()
        category_count = db.query(LabelCategory).count()

        # Delete all records from database (order matters due to foreign keys)
        db.query(Annotation).delete()
        db.query(Image).delete()
        db.query(LabelCategory).delete()
        db.query(Dataset).delete()
        db.query(Project).delete()

        db.commit()

        # Delete all files from uploads directory
        backend_dir = os.path.dirname(os.path.abspath(__file__))
        proj_root = os.path.dirname(backend_dir)
        uploads_path = os.path.join(proj_root, "uploads")
        thumbnails_dir = os.path.join(uploads_path, "thumbnails")
        images_dir = os.path.join(uploads_path, "images")

        deleted_files = 0
        for directory in [images_dir, thumbnails_dir]:
            if os.path.exists(directory):
                for filename in os.listdir(directory):
                    file_path = os.path.join(directory, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.remove(file_path)
                            deleted_files += 1
                    except OSError as file_error:
                        print(f"Error deleting file {file_path}: {file_error}")

        return {
            "message": "All data cleared successfully",
            "deleted": {
                "projects": project_count,
                "datasets": dataset_count,
                "images": image_count,
                "annotations": annotation_count,
                "categories": category_count,
                "files": deleted_files,
            },
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, detail=f"Error clearing data: {str(e)}"
        ) from e
