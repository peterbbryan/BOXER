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
    """Create a thumbnail of an image"""
    try:
        with PILImage.open(image_path) as img:
            img.thumbnail(size, PILImage.Resampling.LANCZOS)
            img.save(thumbnail_path, "JPEG", quality=85)
        return True
    except (OSError, IOError) as e:
        print(f"Error creating thumbnail: {e}")
        return False


def get_image_info(image_path: str) -> Dict[str, any]:
    """Get image information (dimensions, size, etc.)"""
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
    """Validate if file is a valid image"""
    try:
        with PILImage.open(file_path) as img:
            img.verify()
        return True
    except (OSError, IOError):
        return False


def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename while preserving extension"""
    name, ext = os.path.splitext(original_filename)
    unique_id = str(uuid.uuid4())[:8]
    return f"{name}_{unique_id}{ext}"


def ensure_upload_directories() -> None:
    """Ensure upload directories exist"""
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
    """Process an uploaded image and create thumbnail"""
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


def resize_image_for_display(
    image_path: str, max_width: int = 1200, max_height: int = 800
) -> str:
    """Resize image for display while maintaining aspect ratio"""
    try:
        with PILImage.open(image_path) as img:
            # Calculate new size maintaining aspect ratio
            ratio = min(max_width / img.width, max_height / img.height)
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)

            # Resize image
            resized_img = img.resize(
                (new_width, new_height), PILImage.Resampling.LANCZOS
            )

            # Save resized image
            resized_path = image_path.replace("uploads/images", "uploads/display")
            os.makedirs(os.path.dirname(resized_path), exist_ok=True)
            resized_img.save(resized_path, "JPEG", quality=90)

            return resized_path
    except (OSError, IOError) as e:
        print(f"Error resizing image: {e}")
        return image_path


def get_supported_formats() -> List[str]:
    """Get list of supported image formats"""
    return [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".gif"]
