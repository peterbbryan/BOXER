"""
Pytest configuration and fixtures for VibeCortex tests
"""

import pytest
import tempfile
import os
from PIL import Image


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    for file in os.listdir(temp_dir):
        os.remove(os.path.join(temp_dir, file))
    os.rmdir(temp_dir)


@pytest.fixture
def test_image_800x600(temp_dir):
    """Create a test image 800x600 pixels"""
    image_path = os.path.join(temp_dir, "test_800x600.jpg")
    img = Image.new("RGB", (800, 600), color="red")
    img.save(image_path, "JPEG")
    return image_path


@pytest.fixture
def test_image_1920x1080(temp_dir):
    """Create a test image 1920x1080 pixels"""
    image_path = os.path.join(temp_dir, "test_1920x1080.jpg")
    img = Image.new("RGB", (1920, 1080), color="blue")
    img.save(image_path, "JPEG")
    return image_path


@pytest.fixture
def test_image_square(temp_dir):
    """Create a square test image 1000x1000 pixels"""
    image_path = os.path.join(temp_dir, "test_square.jpg")
    img = Image.new("RGB", (1000, 1000), color="green")
    img.save(image_path, "JPEG")
    return image_path


@pytest.fixture
def mock_annotations():
    """Mock annotation data for testing"""
    return [
        {
            "id": 1,
            "image_id": 1,
            "label_category_id": 1,
            "tool": "bbox",
            "coordinates": {"startX": 100, "startY": 100, "endX": 300, "endY": 200},
        },
        {
            "id": 2,
            "image_id": 1,
            "label_category_id": 2,
            "tool": "point",
            "coordinates": {"startX": 150, "startY": 150},
        },
        {
            "id": 3,
            "image_id": 1,
            "label_category_id": 3,
            "tool": "polygon",
            "coordinates": {
                "points": [
                    {"x": 200, "y": 200},
                    {"x": 400, "y": 200},
                    {"x": 400, "y": 300},
                    {"x": 200, "y": 300},
                ]
            },
        },
    ]


@pytest.fixture
def mock_container_dimensions():
    """Mock container dimensions for testing"""
    return {"width": 1000, "height": 800}


@pytest.fixture
def mock_zoom_pan_state():
    """Mock zoom and pan state for testing"""
    return {"zoom_level": 0.6, "pan_x": 40, "pan_y": 30}
