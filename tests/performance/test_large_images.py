"""
Performance tests for large image handling
"""

import unittest
import os
import tempfile
import time
from PIL import Image
import math


class TestLargeImagePerformance(unittest.TestCase):
    """Test performance with large images and many annotations"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up any test files
        for file in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file))
        os.rmdir(self.temp_dir)

    def test_large_image_loading_performance(self):
        """Test performance of loading very large images"""
        # Test with different image sizes
        test_sizes = [
            (2000, 1500),  # 3MP
            (4000, 3000),  # 12MP
            (8000, 6000),  # 48MP
        ]

        for width, height in test_sizes:
            with self.subTest(size=(width, height)):
                # Create large test image
                test_path = os.path.join(self.temp_dir, f"test_{width}x{height}.jpg")

                start_time = time.time()
                img = Image.new("RGB", (width, height), color="red")
                img.save(test_path, "JPEG", quality=85)
                creation_time = time.time() - start_time

                # Test loading time
                start_time = time.time()
                with Image.open(test_path) as loaded_img:
                    loaded_width, loaded_height = loaded_img.size
                loading_time = time.time() - start_time

                # Verify dimensions
                self.assertEqual(loaded_width, width)
                self.assertEqual(loaded_height, height)

                # Performance assertions (should complete within reasonable time)
                self.assertLess(
                    creation_time, 10.0
                )  # Should create in under 10 seconds
                self.assertLess(loading_time, 5.0)  # Should load in under 5 seconds

                # Clean up
                os.remove(test_path)

    def test_zoom_calculation_performance(self):
        """Test performance of zoom calculations with large images"""
        # Test with very large image dimensions
        large_width = 10000
        large_height = 8000
        container_width = 1000
        container_height = 800

        # Measure calculation time
        start_time = time.time()

        # Perform multiple calculations
        for _ in range(1000):
            scale_x = container_width / large_width
            scale_y = container_height / large_height
            zoom_level = min(scale_x, scale_y) * 0.9

            scaled_width = large_width * zoom_level
            scaled_height = large_height * zoom_level
            pan_x = (container_width - scaled_width) / 2
            pan_y = (container_height - scaled_height) / 2

        calculation_time = time.time() - start_time

        # Should complete 1000 calculations in under 1 second
        self.assertLess(calculation_time, 1.0)

    def test_coordinate_transformation_performance(self):
        """Test performance of coordinate transformations"""
        # Test with many annotations
        num_annotations = 1000
        zoom_level = 0.6
        pan_x = 40
        pan_y = 30

        # Generate test annotations
        annotations = []
        for i in range(num_annotations):
            annotation = {
                "id": i,
                "tool": "bbox",
                "coordinates": {
                    "startX": i * 10,
                    "startY": i * 10,
                    "endX": i * 10 + 100,
                    "endY": i * 10 + 100,
                },
            }
            annotations.append(annotation)

        # Measure transformation time
        start_time = time.time()

        for annotation in annotations:
            coords = annotation["coordinates"]
            # Transform to screen coordinates
            screen_start_x = coords["startX"] * zoom_level + pan_x
            screen_start_y = coords["startY"] * zoom_level + pan_y
            screen_end_x = coords["endX"] * zoom_level + pan_x
            screen_end_y = coords["endY"] * zoom_level + pan_y

        transformation_time = time.time() - start_time

        # Should transform 1000 annotations in under 0.1 seconds
        self.assertLess(transformation_time, 0.1)

    def test_polygon_point_in_polygon_performance(self):
        """Test performance of point-in-polygon calculations"""
        # Create complex polygon with many points
        num_points = 1000
        polygon = []
        for i in range(num_points):
            angle = 2 * math.pi * i / num_points
            radius = 500 + 100 * math.sin(10 * angle)  # Complex shape
            x = 1000 + radius * math.cos(angle)
            y = 1000 + radius * math.sin(angle)
            polygon.append({"x": x, "y": y})

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

        # Test multiple points
        test_points = [(1000, 1000), (1500, 1500), (500, 500), (2000, 2000)]

        start_time = time.time()

        for x, y in test_points:
            point_in_polygon(x, y, polygon)

        calculation_time = time.time() - start_time

        # Should complete point-in-polygon tests in under 1 second
        self.assertLess(calculation_time, 1.0)

    def test_memory_usage_with_large_images(self):
        """Test memory usage with large images"""
        # This is more of a smoke test - we can't easily measure memory usage
        # in a unit test, but we can ensure operations complete without errors

        # Create a moderately large image
        width, height = 4000, 3000
        test_path = os.path.join(self.temp_dir, "large_test.jpg")

        try:
            # Create and save large image
            img = Image.new("RGB", (width, height), color="blue")
            img.save(test_path, "JPEG", quality=85)

            # Perform multiple operations that might consume memory
            for _ in range(10):
                with Image.open(test_path) as loaded_img:
                    # Simulate zoom calculations
                    container_width = 1000
                    container_height = 800
                    img_w, img_h = loaded_img.size

                    scale_x = container_width / img_w
                    scale_y = container_height / img_h
                    zoom_level = min(scale_x, scale_y) * 0.9

                    scaled_w = img_w * zoom_level
                    scaled_h = img_h * zoom_level
                    pan_x = (container_width - scaled_w) / 2
                    pan_y = (container_height - scaled_h) / 2

                    # Verify calculations are reasonable
                    self.assertGreater(zoom_level, 0)
                    self.assertLessEqual(scaled_w, container_width)
                    self.assertLessEqual(scaled_h, container_height)

        finally:
            if os.path.exists(test_path):
                os.remove(test_path)

    def test_annotation_rendering_performance(self):
        """Test performance of rendering many annotations"""
        # Simulate rendering 500 annotations
        num_annotations = 500
        zoom_level = 0.6
        pan_x = 40
        pan_y = 30

        # Generate test annotations with different tools
        annotations = []
        for i in range(num_annotations):
            tool = ["bbox", "point", "polygon"][i % 3]

            if tool == "bbox":
                coords = {
                    "startX": i * 5,
                    "startY": i * 5,
                    "endX": i * 5 + 50,
                    "endY": i * 5 + 50,
                }
            elif tool == "point":
                coords = {"startX": i * 5, "startY": i * 5}
            else:  # polygon
                coords = {
                    "points": [
                        {"x": i * 5, "y": i * 5},
                        {"x": i * 5 + 50, "y": i * 5},
                        {"x": i * 5 + 50, "y": i * 5 + 50},
                        {"x": i * 5, "y": i * 5 + 50},
                    ]
                }

            annotation = {"id": i, "tool": tool, "coordinates": coords}
            annotations.append(annotation)

        # Measure rendering simulation time
        start_time = time.time()

        for annotation in annotations:
            # Simulate coordinate transformation for rendering
            if annotation["tool"] == "bbox":
                coords = annotation["coordinates"]
                screen_start_x = coords["startX"] * zoom_level + pan_x
                screen_start_y = coords["startY"] * zoom_level + pan_y
                screen_end_x = coords["endX"] * zoom_level + pan_x
                screen_end_y = coords["endY"] * zoom_level + pan_y

            elif annotation["tool"] == "point":
                coords = annotation["coordinates"]
                screen_x = coords["startX"] * zoom_level + pan_x
                screen_y = coords["startY"] * zoom_level + pan_y

            else:  # polygon
                coords = annotation["coordinates"]
                for point in coords["points"]:
                    screen_x = point["x"] * zoom_level + pan_x
                    screen_y = point["y"] * zoom_level + pan_y

        rendering_time = time.time() - start_time

        # Should render 500 annotations in under 0.5 seconds
        self.assertLess(rendering_time, 0.5)


if __name__ == "__main__":
    unittest.main()
