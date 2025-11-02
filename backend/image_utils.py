"""
Image processing utilities for BOXER Data Labeling Tool
"""

import os
import uuid
from pathlib import Path
from typing import Dict, List, Tuple, Optional

import numpy as np
from PIL import Image as PILImage

try:
    import rasterio
except ImportError:
    rasterio = None

try:
    from sarpy.io.complex.sicd import SICDReader
    from sarpy.visualization.remap import density
except ImportError:
    SICDReader = None
    density = None


def _load_r0_image(file_path: str) -> Optional[PILImage.Image]:
    """Load a .r0 raster file using rasterio and convert to PIL Image.

    Args:
        file_path: Path to the .r0 raster file.

    Returns:
        PIL Image object or None if loading fails.
    """
    if rasterio is None:
        return None

    try:
        with rasterio.open(file_path) as src:
            # Read the first band (or all bands if RGB)
            if src.count == 1:
                data = src.read(1)
                # Convert to uint8 if needed
                if data.dtype != np.uint8:
                    # Normalize to 0-255 range
                    data_min, data_max = data.min(), data.max()
                    if data_max > data_min:
                        data = ((data - data_min) / (data_max - data_min) * 255).astype(
                            np.uint8
                        )
                    else:
                        data = np.zeros_like(data, dtype=np.uint8)
                img = PILImage.fromarray(data, mode="L")
            elif src.count >= 3:
                # Read RGB bands
                r = src.read(1)
                g = src.read(2)
                b = src.read(3)
                # Stack bands and normalize
                if r.dtype != np.uint8:
                    for band in [r, g, b]:
                        band_min, band_max = band.min(), band.max()
                        if band_max > band_min:
                            band[:] = (
                                (band - band_min) / (band_max - band_min) * 255
                            ).astype(np.uint8)
                        else:
                            band[:] = np.zeros_like(band, dtype=np.uint8)
                img = PILImage.fromarray(np.stack([r, g, b], axis=-1), mode="RGB")
            else:
                # For other cases, use first band
                data = src.read(1)
                if data.dtype != np.uint8:
                    data_min, data_max = data.min(), data.max()
                    if data_max > data_min:
                        data = ((data - data_min) / (data_max - data_min) * 255).astype(
                            np.uint8
                        )
                    else:
                        data = np.zeros_like(data, dtype=np.uint8)
                img = PILImage.fromarray(data, mode="L")
            return img
    except Exception as e:
        print(f"Error loading .r0 file with rasterio: {e}")
        return None


def _load_sicd_image(file_path: str) -> Optional[PILImage.Image]:
    """Load a SICD file using Sarpy and convert to PIL Image with density remap.

    Args:
        file_path: Path to the SICD file.

    Returns:
        PIL Image object or None if loading fails.
    """
    if SICDReader is None or density is None:
        return None

    try:
        # Read SICD file
        reader = SICDReader(file_path)

        # Read the full image chip (all pixels)
        # read_chip() reads the entire image, or we can specify bounds
        sicd_data = reader.read_chip()

        # Apply density remap to visualize as real values
        # density() function converts complex SAR data to intensity
        remapped_data = density(sicd_data)

        # Convert to uint8 for PIL Image
        if remapped_data.dtype != np.uint8:
            # Normalize to 0-255 range
            data_min, data_max = remapped_data.min(), remapped_data.max()
            if data_max > data_min:
                remapped_data = (
                    (remapped_data - data_min) / (data_max - data_min) * 255
                ).astype(np.uint8)
            else:
                remapped_data = np.zeros_like(remapped_data, dtype=np.uint8)

        # Handle single band vs multi-band
        if len(remapped_data.shape) == 2:
            img = PILImage.fromarray(remapped_data, mode="L")
        elif len(remapped_data.shape) == 3 and remapped_data.shape[2] >= 3:
            # Take first 3 bands for RGB
            img = PILImage.fromarray(remapped_data[:, :, :3], mode="RGB")
        else:
            # Fallback to grayscale
            img = PILImage.fromarray(remapped_data.squeeze(), mode="L")

        return img
    except Exception as e:
        print(f"Error loading SICD file with Sarpy: {e}")
        return None


def _load_special_image(file_path: str) -> Optional[PILImage.Image]:
    """Load special image formats (.r0, SICD) and convert to PIL Image.

    Args:
        file_path: Path to the image file.

    Returns:
        PIL Image object or None if file type is not supported or loading fails.
    """
    file_ext = os.path.splitext(file_path)[1].lower()

    if file_ext == ".r0":
        return _load_r0_image(file_path)
    elif file_ext in [".sicd", ".nitf", ".ntf", ".nff"]:
        # SICD files can have various extensions: .sicd, .nitf, .ntf, or .nff
        return _load_sicd_image(file_path)

    return None


def _save_as_pil_compatible(file_path: str, output_path: str) -> bool:
    """Convert special image formats to standard format (PNG) for storage.

    Args:
        file_path: Path to the source file.
        output_path: Path where the converted image will be saved.

    Returns:
        True if conversion was successful, False otherwise.
    """
    img = _load_special_image(file_path)
    if img is None:
        return False

    try:
        # Save as PNG (lossless and widely supported)
        img.save(output_path, "PNG")
        return True
    except Exception as e:
        print(f"Error saving converted image: {e}")
        return False


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
        # Try loading as special format first
        file_ext = os.path.splitext(image_path)[1].lower()
        if file_ext in [".r0", ".sicd", ".nitf", ".ntf", ".nff"]:
            img = _load_special_image(image_path)
            if img is not None:
                img.thumbnail(size, PILImage.Resampling.LANCZOS)
                img.save(thumbnail_path, "JPEG", quality=85)
                return True

        # Fallback to standard PIL image loading
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
        # Try loading as special format first
        file_ext = os.path.splitext(image_path)[1].lower()
        if file_ext in [".r0", ".sicd", ".nitf", ".ntf", ".nff"]:
            img = _load_special_image(image_path)
            if img is not None:
                width, height = img.size
                file_size = os.path.getsize(image_path)
                return {
                    "width": width,
                    "height": height,
                    "file_size": file_size,
                    "format": file_ext[1:].upper() if file_ext else "UNKNOWN",
                    "mode": img.mode,
                }

        # Fallback to standard PIL image loading
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
    # Check for special formats first
    file_ext = os.path.splitext(file_path)[1].lower()
    if file_ext == ".r0":
        if rasterio is None:
            return False
        try:
            with rasterio.open(file_path) as src:
                # Just verify we can open it
                _ = src.width, src.height
            return True
        except Exception:
            return False
    elif file_ext in [".sicd", ".nitf", ".ntf", ".nff"]:
        if SICDReader is None:
            return False
        try:
            reader = SICDReader(file_path)
            _ = reader.sicd_meta  # Verify we can read metadata
            return True
        except Exception:
            return False

    # Standard PIL validation
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
    For special formats (.r0, SICD), converts to PNG format for storage.

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

    # Check if this is a special format that needs conversion
    file_ext = os.path.splitext(original_filename)[1].lower()
    needs_conversion = file_ext in [".r0", ".sicd", ".nitf", ".ntf", ".nff"]

    if needs_conversion:
        # Generate unique filename with .png extension for converted files
        base_name = os.path.splitext(original_filename)[0]
        unique_filename = f"{base_name}_{str(uuid.uuid4())[:8]}.png"
        converted_path = os.path.join(
            project_root, "uploads", "images", unique_filename
        )

        # Convert special format to PNG
        if not _save_as_pil_compatible(file_path, converted_path):
            raise ValueError(
                f"Failed to convert {original_filename} to standard image format"
            )

        # Delete original temporary file
        if os.path.exists(file_path):
            os.remove(file_path)

        final_path = converted_path
        stored_original_filename = original_filename  # Keep original name for reference
    else:
        # Generate unique filename
        unique_filename = generate_unique_filename(original_filename)

        # Move to images directory (use absolute paths)
        images_dir = os.path.join(project_root, "uploads", "images")
        final_path = os.path.join(images_dir, unique_filename)

        # Move file
        os.rename(file_path, final_path)
        stored_original_filename = original_filename

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
        "r0": "image/r0",
        "sicd": "image/sicd",
        "nitf": "image/nitf",
        "ntf": "image/nitf",
        "nff": "image/nitf",
    }
    mime_type = mime_type_map.get(
        format_name, "image/png" if needs_conversion else f"image/{format_name}"
    )

    # Return relative paths for storage in database
    return {
        "filename": unique_filename,
        "original_filename": stored_original_filename,
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
    formats = [".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".webp", ".gif"]
    # Add special formats if libraries are available
    if rasterio is not None:
        formats.append(".r0")
    if SICDReader is not None:
        formats.extend([".sicd", ".nitf", ".ntf", ".nff"])
    return formats


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


def convert_yolo_to_annotation(
    yolo_line: str,
    image_width: int,
    image_height: int,
) -> Optional[Dict]:
    """Convert a YOLO format annotation line to internal annotation format.

    Args:
        yolo_line: YOLO format line string (e.g., "0 0.5 0.5 0.3 0.4").
        image_width: Width of the image in pixels.
        image_height: Height of the image in pixels.

    Returns:
        Dictionary with tool and coordinates in internal format, or None if invalid.
    """
    try:
        parts = yolo_line.strip().split()
        if len(parts) < 5:
            return None

        # YOLO format: class_index center_x center_y width height (all normalized)
        class_index = int(parts[0])
        normalized_center_x = float(parts[1])
        normalized_center_y = float(parts[2])
        normalized_width = float(parts[3])
        normalized_height = float(parts[4])

        # Denormalize coordinates
        center_x = normalized_center_x * image_width
        center_y = normalized_center_y * image_height
        width = normalized_width * image_width
        height = normalized_height * image_height

        # Convert center-based to corner-based bbox
        start_x = center_x - (width / 2.0)
        start_y = center_y - (height / 2.0)
        end_x = center_x + (width / 2.0)
        end_y = center_y + (height / 2.0)

        # Ensure coordinates are within image bounds
        start_x = max(0, min(start_x, image_width))
        start_y = max(0, min(start_y, image_height))
        end_x = max(0, min(end_x, image_width))
        end_y = max(0, min(end_y, image_height))

        return {
            "tool": "bbox",
            "coordinates": {
                "startX": start_x,
                "startY": start_y,
                "endX": end_x,
                "endY": end_y,
            },
            "class_index": class_index,
        }
    except (ValueError, IndexError) as e:
        print(f"Error parsing YOLO line: {yolo_line}, error: {e}")
        return None
