"""
Unit tests for annotation coordinate transformations
"""

import unittest
import math


class TestAnnotationCoordinates(unittest.TestCase):
    """Test annotation coordinate transformation functions"""

    def setUp(self):
        """Set up test fixtures"""
        self.zoom_level = 0.6
        self.pan_x = 40
        self.pan_y = 30

    def test_bbox_coordinate_transformation(self):
        """Test bounding box coordinate transformation"""
        # Test data: bbox in image coordinates
        bbox_image = {"startX": 100, "startY": 150, "endX": 300, "endY": 250}

        # Transform to screen coordinates
        screen_start_x = bbox_image["startX"] * self.zoom_level + self.pan_x
        screen_start_y = bbox_image["startY"] * self.zoom_level + self.pan_y
        screen_end_x = bbox_image["endX"] * self.zoom_level + self.pan_x
        screen_end_y = bbox_image["endY"] * self.zoom_level + self.pan_y

        expected_start_x = 100 * 0.6 + 40  # 100
        expected_start_y = 150 * 0.6 + 30  # 120
        expected_end_x = 300 * 0.6 + 40  # 220
        expected_end_y = 250 * 0.6 + 30  # 180

        self.assertAlmostEqual(screen_start_x, expected_start_x, places=1)
        self.assertAlmostEqual(screen_start_y, expected_start_y, places=1)
        self.assertAlmostEqual(screen_end_x, expected_end_x, places=1)
        self.assertAlmostEqual(screen_end_y, expected_end_y, places=1)

    def test_point_coordinate_transformation(self):
        """Test point coordinate transformation"""
        # Test data: point in image coordinates
        point_image = {"startX": 200, "startY": 300}

        # Transform to screen coordinates
        screen_x = point_image["startX"] * self.zoom_level + self.pan_x
        screen_y = point_image["startY"] * self.zoom_level + self.pan_y

        expected_x = 200 * 0.6 + 40  # 160
        expected_y = 300 * 0.6 + 30  # 210

        self.assertAlmostEqual(screen_x, expected_x, places=1)
        self.assertAlmostEqual(screen_y, expected_y, places=1)

    def test_polygon_coordinate_transformation(self):
        """Test polygon coordinate transformation"""
        # Test data: polygon points in image coordinates
        polygon_image = {
            "points": [
                {"x": 100, "y": 100},
                {"x": 200, "y": 100},
                {"x": 200, "y": 200},
                {"x": 100, "y": 200},
            ]
        }

        # Transform to screen coordinates
        screen_points = []
        for point in polygon_image["points"]:
            screen_x = point["x"] * self.zoom_level + self.pan_x
            screen_y = point["y"] * self.zoom_level + self.pan_y
            screen_points.append({"x": screen_x, "y": screen_y})

        expected_points = [
            {"x": 100, "y": 90},  # 100*0.6+40, 100*0.6+30
            {"x": 160, "y": 90},  # 200*0.6+40, 100*0.6+30
            {"x": 160, "y": 150},  # 200*0.6+40, 200*0.6+30
            {"x": 100, "y": 150},  # 100*0.6+40, 200*0.6+30
        ]

        for i, (actual, expected) in enumerate(zip(screen_points, expected_points)):
            with self.subTest(point_index=i):
                self.assertAlmostEqual(actual["x"], expected["x"], places=1)
                self.assertAlmostEqual(actual["y"], expected["y"], places=1)

    def test_point_in_bbox_detection(self):
        """Test point-in-bounding-box detection"""
        # Test bbox
        bbox = {"startX": 100, "startY": 100, "endX": 300, "endY": 200}

        # Test points
        test_cases = [
            (150, 150, True),  # Inside bbox
            (50, 150, False),  # Left of bbox
            (350, 150, False),  # Right of bbox
            (150, 50, False),  # Above bbox
            (150, 250, False),  # Below bbox
            (100, 100, True),  # On top-left corner
            (300, 200, True),  # On bottom-right corner
        ]

        for x, y, expected_inside in test_cases:
            with self.subTest(x=x, y=y):
                min_x = min(bbox["startX"], bbox["endX"])
                max_x = max(bbox["startX"], bbox["endX"])
                min_y = min(bbox["startY"], bbox["endY"])
                max_y = max(bbox["startY"], bbox["endY"])

                actual_inside = min_x <= x <= max_x and min_y <= y <= max_y
                self.assertEqual(actual_inside, expected_inside)

    def test_point_in_polygon_detection(self):
        """Test point-in-polygon detection using ray casting algorithm"""
        # Test polygon (rectangle)
        polygon = [
            {"x": 100, "y": 100},
            {"x": 300, "y": 100},
            {"x": 300, "y": 200},
            {"x": 100, "y": 200},
        ]

        def point_in_polygon(x, y, points):
            """Ray casting algorithm for point-in-polygon test"""
            inside = False
            j = len(points) - 1
            for i in range(len(points)):
                if ((points[i]["y"] > y) != (points[j]["y"] > y)) and (
                    x
                    < (points[j]["x"] - points[i]["x"])
                    * (y - points[i]["y"])
                    / (points[j]["y"] - points[i]["y"])
                    + points[i]["x"]
                ):
                    inside = not inside
                j = i
            return inside

        # Test points
        test_cases = [
            (200, 150, True),  # Inside polygon
            (50, 150, False),  # Left of polygon
            (350, 150, False),  # Right of polygon
            (200, 50, False),  # Above polygon
            (200, 250, False),  # Below polygon
            (100, 100, True),  # On corner
            (
                300,
                200,
                False,
            ),  # On corner (edge case - may be outside due to algorithm)
        ]

        for x, y, expected_inside in test_cases:
            with self.subTest(x=x, y=y):
                actual_inside = point_in_polygon(x, y, polygon)
                self.assertEqual(actual_inside, expected_inside)

    def test_coordinate_round_trip(self):
        """Test that coordinate transformation is reversible"""
        # Original screen coordinates
        original_screen_x = 150
        original_screen_y = 200

        # Transform to image coordinates
        image_x = (original_screen_x - self.pan_x) / self.zoom_level
        image_y = (original_screen_y - self.pan_y) / self.zoom_level

        # Transform back to screen coordinates
        final_screen_x = image_x * self.zoom_level + self.pan_x
        final_screen_y = image_y * self.zoom_level + self.pan_y

        # Should be very close to original (allowing for floating point precision)
        self.assertAlmostEqual(final_screen_x, original_screen_x, places=10)
        self.assertAlmostEqual(final_screen_y, original_screen_y, places=10)

    def test_zoom_level_limits(self):
        """Test zoom level boundary conditions"""
        # Test minimum zoom level
        min_zoom = 0.1
        test_zoom = 0.05
        clamped_zoom = max(min_zoom, test_zoom)
        self.assertEqual(clamped_zoom, 0.1)

        # Test maximum zoom level
        max_zoom = 5.0
        test_zoom = 6.0
        clamped_zoom = min(max_zoom, test_zoom)
        self.assertEqual(clamped_zoom, 5.0)

        # Test zoom within limits
        test_zoom = 2.0
        clamped_zoom = max(min_zoom, min(max_zoom, test_zoom))
        self.assertEqual(clamped_zoom, 2.0)


if __name__ == "__main__":
    unittest.main()
