"""
Image processing utilities for VibeCortex Data Labeling Tool
"""

import os
import uuid
from pathlib import Path
from typing import Dict, List, Tuple

from PIL import Image as PILImage


def create_thumbnail(
    image_path: str, thumbnail_path: str, size: Tuple[int, int] = (300, 300)
) -> bool:
    """Create a thumbnail of an image.

    Args:
        image_path: Path to the source image file.
        thumbnail_path: Path where the thumbnail will be saved.
        size: Maximum size of the thumbnail as (width, height). Defaults to (300, 300).

    Returns:
        True if thumbnail was created successfully, False otherwise.
    """
    try:
        with PILImage.open(image_path) as img:
            img.thumbnail(size, PILImage.Resampling.LANCZOS)
            img.save(thumbnail_path, "JPEG", quality=85)
        return True
    except (OSError, IOError) as e:
        print(f"Error creating thumbnail: {e}")
        return False


def get_image_info(image_path: str) -> Dict[str, any]:
    """Get image information (dimensions, size, etc.).

    Args:
        image_path: Path to the image file.

    Returns:
        Dictionary containing image metadata including width, height, file_size,
        format, and mode. Returns empty dict if file cannot be read.
    """
    try:
        with PILImage.open(image_path) as img:
            width, height = img.size
            file_size = os.path.getsize(image_path)

            return {
                "width": width,
                "height": height,
                "file_size": file_size,
                "format": img.format,
                "mode": img.mode,
            }
    except (OSError, IOError) as e:
        print(f"Error getting image info: {e}")
        return {}


def validate_image(file_path: str) -> bool:
    """Validate if file is a valid image.

    Args:
        file_path: Path to the file to validate.

    Returns:
        True if the file is a valid image, False otherwise.
    """
    try:
        with PILImage.open(file_path) as img:
            img.verify()
        return True
    except (OSError, IOError):
        return False


def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename while preserving extension.

    Args:
        original_filename: The original filename to make unique.

    Returns:
        A new filename with a unique UUID suffix while preserving the
        original extension.
    """
    name, ext = os.path.splitext(original_filename)
    unique_id = str(uuid.uuid4())[:8]
    return f"{name}_{unique_id}{ext}"


def ensure_upload_directories() -> None:
    """Ensure upload directories exist.

    Creates the necessary directories for storing uploaded images and
    thumbnails if they don't already exist.
    """
    # Get absolute paths relative to backend directory
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)

    directories = [
        os.path.join(project_root, "uploads", "images"),
        os.path.join(project_root, "uploads", "thumbnails"),
        os.path.join(project_root, "data"),
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)


def process_uploaded_image(file_path: str, original_filename: str) -> Dict[str, any]:
    """Process an uploaded image and create thumbnail.

    Moves the uploaded image to the images directory, generates a unique
    filename, creates a thumbnail, and gathers image metadata.

    Args:
        file_path: Path to the temporary uploaded file.
        original_filename: The original filename of the uploaded file.

    Returns:
        Dictionary containing image metadata including filename,
        file_path, thumbnail_path, dimensions, file_size, and mime_type.
    """
    ensure_upload_directories()

    # Get absolute paths
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(backend_dir)

    # Generate unique filename
    unique_filename = generate_unique_filename(original_filename)

    # Move to images directory (use absolute paths)
    images_dir = os.path.join(project_root, "uploads", "images")
    final_path = os.path.join(images_dir, unique_filename)

    # Move file
    os.rename(file_path, final_path)

    # Create thumbnail (use absolute paths)
    thumbnail_dir = os.path.join(project_root, "uploads", "thumbnails")
    thumbnail_filename = f"thumb_{unique_filename}"
    thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)

    create_thumbnail(final_path, thumbnail_path)

    # Get image info
    image_info = get_image_info(final_path)

    # Get proper MIME type
    format_name = image_info.get("format", "").lower()
    mime_type_map = {
        "jpeg": "image/jpeg",
        "jpg": "image/jpeg",
        "png": "image/png",
        "gif": "image/gif",
        "bmp": "image/bmp",
        "tiff": "image/tiff",
        "webp": "image/webp",
    }
    mime_type = mime_type_map.get(format_name, f"image/{format_name}")

    # Return relative paths for storage in database
    return {
        "filename": unique_filename,
        "original_filename": original_filename,
        "file_path": os.path.join("uploads", "images", unique_filename),
        "thumbnail_path": os.path.join("uploads", "thumbnails", thumbnail_filename),
        "width": image_info.get("width", 0),
        "height": image_info.get("height", 0),
        "file_size": image_info.get("file_size", 0),
        "mime_type": mime_type,
    }


def get_supported_formats() -> List[str]:
    """Get list of supported image formats.

    Returns:
        List of file extensions for supported image formats.
    """
    return [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".gif"]


def convert_annotation_to_yolo(  # pylint: disable=too-many-locals
    annotation: Dict,
    image_width: int,
    image_height: int,
    category_id_to_index: Dict[int, int],
) -> str:
    """Convert an annotation to YOLO format.

    Args:
        annotation: Annotation dictionary with tool and coordinates.
        image_width: Width of the image.
        image_height: Height of the image.
        category_id_to_index: Dictionary mapping category IDs to YOLO class indices.

    Returns:
        YOLO format line string or empty string if conversion not possible.
    """
    tool = annotation.get("tool", "")
    coordinates = annotation.get("coordinates", {})

    if tool == "bbox":
        # Convert bbox to YOLO format (center_x, center_y, width, height, normalized)
        start_x = coordinates.get("startX", 0)
        start_y = coordinates.get("startY", 0)
        end_x = coordinates.get("endX", 0)
        end_y = coordinates.get("endY", 0)

        # Calculate center and dimensions
        center_x = (start_x + end_x) / 2.0
        center_y = (start_y + end_y) / 2.0
        width = abs(end_x - start_x)
        height = abs(end_y - start_y)

        # Normalize coordinates
        normalized_center_x = center_x / image_width
        normalized_center_y = center_y / image_height
        normalized_width = width / image_width
        normalized_height = height / image_height

        # Get class index
        label_category_id = annotation.get("label_category_id")
        class_index = category_id_to_index.get(label_category_id, 0)

        return (
            f"{class_index} {normalized_center_x:.6f} {normalized_center_y:.6f} "
            f"{normalized_width:.6f} {normalized_height:.6f}"
        )

    return ""
