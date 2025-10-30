"""
Unit tests for YOLO export functionality
"""

import io
import zipfile
from unittest import TestCase

from backend.image_utils import convert_annotation_to_yolo


class TestYOLOExport(TestCase):
    """Test YOLO export conversion functions."""

    def test_convert_bbox_to_yolo(self):
        """Test converting a bounding box annotation to YOLO format."""
        annotation = {
            "tool": "bbox",
            "coordinates": {
                "startX": 100,
                "startY": 150,
                "endX": 300,
                "endY": 250,
            },
            "label_category_id": 1,
        }
        image_width = 800
        image_height = 600
        category_id_to_index = {1: 0}

        result = convert_annotation_to_yolo(
            annotation, image_width, image_height, category_id_to_index
        )

        # Expected: class_index center_x center_y width height (all normalized)
        # center_x = (100 + 300) / 2 = 200, normalized = 200/800 = 0.25
        # center_y = (150 + 250) / 2 = 200, normalized = 200/600 = 0.333...
        # width = 300 - 100 = 200, normalized = 200/800 = 0.25
        # height = 250 - 150 = 100, normalized = 100/600 = 0.166...

        self.assertIsNotNone(result)
        parts = result.split()
        self.assertEqual(len(parts), 5)
        self.assertEqual(int(parts[0]), 0)  # Class index

        # Check center x (should be 0.25)
        self.assertAlmostEqual(float(parts[1]), 0.25, places=5)

        # Check center y (should be 0.333333...)
        self.assertAlmostEqual(float(parts[2]), 0.333333, places=4)

        # Check width (should be 0.25)
        self.assertAlmostEqual(float(parts[3]), 0.25, places=5)

        # Check height (should be 0.166666...)
        self.assertAlmostEqual(float(parts[4]), 0.166666, places=4)

    def test_convert_bbox_topleft_corner(self):
        """Test converting a bounding box at top-left corner."""
        annotation = {
            "tool": "bbox",
            "coordinates": {
                "startX": 0,
                "startY": 0,
                "endX": 100,
                "endY": 100,
            },
            "label_category_id": 2,
        }
        image_width = 640
        image_height = 480
        category_id_to_index = {2: 1}

        result = convert_annotation_to_yolo(
            annotation, image_width, image_height, category_id_to_index
        )

        parts = result.split()
        self.assertEqual(len(parts), 5)
        self.assertEqual(int(parts[0]), 1)  # Class index

        # Center x should be at (0 + 100)/2 = 50, normalized = 50/640
        self.assertAlmostEqual(float(parts[1]), 50 / 640, places=5)

        # Center y should be at (0 + 100)/2 = 50, normalized = 50/480
        self.assertAlmostEqual(float(parts[2]), 50 / 480, places=5)

        # Width should be 100, normalized = 100/640
        self.assertAlmostEqual(float(parts[3]), 100 / 640, places=5)

        # Height should be 100, normalized = 100/480
        self.assertAlmostEqual(float(parts[4]), 100 / 480, places=5)

    def test_convert_bbox_full_image(self):
        """Test converting a bounding box covering full image."""
        annotation = {
            "tool": "bbox",
            "coordinates": {
                "startX": 0,
                "startY": 0,
                "endX": 800,
                "endY": 600,
            },
            "label_category_id": 0,
        }
        image_width = 800
        image_height = 600
        category_id_to_index = {0: 0}

        result = convert_annotation_to_yolo(
            annotation, image_width, image_height, category_id_to_index
        )

        parts = result.split()
        # Center should be at 0.5, 0.5 (middle of image)
        self.assertAlmostEqual(float(parts[1]), 0.5, places=5)
        self.assertAlmostEqual(float(parts[2]), 0.5, places=5)

        # Width and height should both be 1.0 (full image)
        self.assertAlmostEqual(float(parts[3]), 1.0, places=5)
        self.assertAlmostEqual(float(parts[4]), 1.0, places=5)

    def test_convert_point_annotation_skipped(self):
        """Test that point annotations are skipped (not supported in YOLO)."""
        annotation = {
            "tool": "point",
            "coordinates": {
                "startX": 100,
                "startY": 200,
            },
            "label_category_id": 1,
        }
        image_width = 800
        image_height = 600
        category_id_to_index = {1: 0}

        result = convert_annotation_to_yolo(
            annotation, image_width, image_height, category_id_to_index
        )

        self.assertEqual(result, "")  # Point annotations should return empty string

    def test_convert_polygon_annotation_skipped(self):
        """Test that polygon annotations are skipped (not supported in YOLO)."""
        annotation = {
            "tool": "polygon",
            "coordinates": {
                "points": [
                    {"x": 100, "y": 100},
                    {"x": 200, "y": 100},
                    {"x": 200, "y": 200},
                    {"x": 100, "y": 200},
                ],
            },
            "label_category_id": 1,
        }
        image_width = 800
        image_height = 600
        category_id_to_index = {1: 0}

        result = convert_annotation_to_yolo(
            annotation, image_width, image_height, category_id_to_index
        )

        self.assertEqual(result, "")  # Polygon annotations should return empty string

    def test_multiple_categories(self):
        """Test with multiple categories (different class indices)."""
        annotation1 = {
            "tool": "bbox",
            "coordinates": {"startX": 0, "startY": 0, "endX": 100, "endY": 100},
            "label_category_id": 1,
        }
        annotation2 = {
            "tool": "bbox",
            "coordinates": {"startX": 200, "startY": 200, "endX": 300, "endY": 300},
            "label_category_id": 3,
        }

        image_width = 640
        image_height = 480
        category_id_to_index = {1: 0, 2: 1, 3: 2}

        result1 = convert_annotation_to_yolo(
            annotation1, image_width, image_height, category_id_to_index
        )
        result2 = convert_annotation_to_yolo(
            annotation2, image_width, image_height, category_id_to_index
        )

        # First should have class index 0
        parts1 = result1.split()
        self.assertEqual(int(parts1[0]), 0)

        # Second should have class index 2
        parts2 = result2.split()
        self.assertEqual(int(parts2[0]), 2)

    def test_reversed_coordinates(self):
        """Test that coordinates work regardless of start/end order."""
        annotation1 = {
            "tool": "bbox",
            "coordinates": {"startX": 100, "startY": 100, "endX": 200, "endY": 200},
            "label_category_id": 1,
        }
        annotation2 = {
            "tool": "bbox",
            "coordinates": {"startX": 200, "startY": 200, "endX": 100, "endY": 100},
            "label_category_id": 1,
        }

        image_width = 800
        image_height = 600
        category_id_to_index = {1: 0}

        result1 = convert_annotation_to_yolo(
            annotation1, image_width, image_height, category_id_to_index
        )
        result2 = convert_annotation_to_yolo(
            annotation2, image_width, image_height, category_id_to_index
        )

        # Both should produce the same result (abs() used for width/height)
        parts1 = result1.split()
        parts2 = result2.split()

        self.assertAlmostEqual(float(parts1[1]), float(parts2[1]), places=5)  # center_x
        self.assertAlmostEqual(float(parts1[2]), float(parts2[2]), places=5)  # center_y
        self.assertAlmostEqual(float(parts1[3]), float(parts2[3]), places=5)  # width
        self.assertAlmostEqual(float(parts1[4]), float(parts2[4]), places=5)  # height
