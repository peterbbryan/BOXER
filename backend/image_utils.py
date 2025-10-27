"""
Image processing utilities for VibeCortex Data Labeling Tool
"""

import os
from PIL import Image as PILImage
import cv2
import numpy as np
from typing import Tuple, Optional
import uuid
from pathlib import Path

def create_thumbnail(image_path: str, thumbnail_path: str, size: Tuple[int, int] = (300, 300)) -> bool:
    """Create a thumbnail of an image"""
    try:
        with PILImage.open(image_path) as img:
            img.thumbnail(size, PILImage.Resampling.LANCZOS)
            img.save(thumbnail_path, "JPEG", quality=85)
        return True
    except Exception as e:
        print(f"Error creating thumbnail: {e}")
        return False

def get_image_info(image_path: str) -> dict:
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
                "mode": img.mode
            }
    except Exception as e:
        print(f"Error getting image info: {e}")
        return {}

def validate_image(file_path: str) -> bool:
    """Validate if file is a valid image"""
    try:
        with PILImage.open(file_path) as img:
            img.verify()
        return True
    except Exception:
        return False

def generate_unique_filename(original_filename: str) -> str:
    """Generate a unique filename while preserving extension"""
    name, ext = os.path.splitext(original_filename)
    unique_id = str(uuid.uuid4())[:8]
    return f"{name}_{unique_id}{ext}"

def ensure_upload_directories():
    """Ensure upload directories exist"""
    directories = [
        "uploads/images",
        "uploads/thumbnails",
        "data"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

def process_uploaded_image(file_path: str, original_filename: str) -> dict:
    """Process an uploaded image and create thumbnail"""
    ensure_upload_directories()
    
    # Generate unique filename
    unique_filename = generate_unique_filename(original_filename)
    
    # Move to images directory
    images_dir = "uploads/images"
    final_path = os.path.join(images_dir, unique_filename)
    
    # Move file
    os.rename(file_path, final_path)
    
    # Create thumbnail
    thumbnail_dir = "uploads/thumbnails"
    thumbnail_filename = f"thumb_{unique_filename}"
    thumbnail_path = os.path.join(thumbnail_dir, thumbnail_filename)
    
    create_thumbnail(final_path, thumbnail_path)
    
    # Get image info
    image_info = get_image_info(final_path)
    
    return {
        "filename": unique_filename,
        "original_filename": original_filename,
        "file_path": final_path,
        "thumbnail_path": thumbnail_path,
        "width": image_info.get("width", 0),
        "height": image_info.get("height", 0),
        "file_size": image_info.get("file_size", 0),
        "mime_type": f"image/{image_info.get('format', '').lower()}"
    }

def resize_image_for_display(image_path: str, max_width: int = 1200, max_height: int = 800) -> str:
    """Resize image for display while maintaining aspect ratio"""
    try:
        with PILImage.open(image_path) as img:
            # Calculate new size maintaining aspect ratio
            ratio = min(max_width / img.width, max_height / img.height)
            new_width = int(img.width * ratio)
            new_height = int(img.height * ratio)
            
            # Resize image
            resized_img = img.resize((new_width, new_height), PILImage.Resampling.LANCZOS)
            
            # Save resized image
            resized_path = image_path.replace("uploads/images", "uploads/display")
            os.makedirs(os.path.dirname(resized_path), exist_ok=True)
            resized_img.save(resized_path, "JPEG", quality=90)
            
            return resized_path
    except Exception as e:
        print(f"Error resizing image: {e}")
        return image_path

def get_supported_formats() -> list:
    """Get list of supported image formats"""
    return ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp', '.gif']
