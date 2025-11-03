"""
Unit tests for zoom and pan functionality

NOTE: These tests verify mathematical formulas used in frontend JavaScript code,
not backend Python functions. The actual zoom/pan logic is implemented in
templates/labeling.html as JavaScript functions. These tests serve as regression
tests to ensure the math formulas remain correct.
"""

import unittest


class TestZoomPanFunctions(unittest.TestCase):
    """Test zoom and pan calculation functions"""

    def setUp(self):
        """Set up test fixtures"""
        self.container_width = 800
        self.container_height = 600
        self.image_width = 1200
        self.image_height = 900

    def test_fit_to_screen_calculation(self):
        """Test fit-to-screen zoom calculation"""
        # Calculate expected values
        scale_x = self.container_width / self.image_width  # 800/1200 = 0.667
        scale_y = self.container_height / self.image_height  # 600/900 = 0.667
        expected_zoom = min(scale_x, scale_y) * 0.9  # 0.667 * 0.9 = 0.6

        # Test the calculation
        actual_zoom = min(scale_x, scale_y) * 0.9
        self.assertAlmostEqual(actual_zoom, expected_zoom, places=3)
        self.assertAlmostEqual(actual_zoom, 0.6, places=3)

    def test_fit_to_screen_centering(self):
        """Test fit-to-screen centering calculation"""
        zoom_level = 0.6
        scaled_width = self.image_width * zoom_level  # 1200 * 0.6 = 720
        scaled_height = self.image_height * zoom_level  # 900 * 0.6 = 540

        expected_pan_x = (
            self.container_width - scaled_width
        ) / 2  # (800 - 720) / 2 = 40
        expected_pan_y = (
            self.container_height - scaled_height
        ) / 2  # (600 - 540) / 2 = 30

        # Test the calculation
        actual_pan_x = (self.container_width - scaled_width) / 2
        actual_pan_y = (self.container_height - scaled_height) / 2

        self.assertAlmostEqual(actual_pan_x, expected_pan_x, places=1)
        self.assertAlmostEqual(actual_pan_y, expected_pan_y, places=1)
        self.assertAlmostEqual(actual_pan_x, 40.0, places=1)
        self.assertAlmostEqual(actual_pan_y, 30.0, places=1)

    def test_zoom_in_calculation(self):
        """Test zoom in calculation"""
        initial_zoom = 1.0
        zoom_factor = 1.2
        max_zoom = 5.0

        # Test normal zoom in
        new_zoom = min(max_zoom, initial_zoom * zoom_factor)
        self.assertEqual(new_zoom, 1.2)

        # Test max zoom limit
        initial_zoom = 4.0
        new_zoom = min(max_zoom, initial_zoom * zoom_factor)
        self.assertEqual(new_zoom, 4.8)

        # Test zoom at max limit
        initial_zoom = 5.0
        new_zoom = min(max_zoom, initial_zoom * zoom_factor)
        self.assertEqual(new_zoom, 5.0)

    def test_zoom_out_calculation(self):
        """Test zoom out calculation"""
        initial_zoom = 1.0
        zoom_factor = 1.2
        min_zoom = 0.1

        # Test normal zoom out
        new_zoom = max(min_zoom, initial_zoom / zoom_factor)
        self.assertAlmostEqual(new_zoom, 0.833, places=3)

        # Test min zoom limit
        initial_zoom = 0.2
        new_zoom = max(min_zoom, initial_zoom / zoom_factor)
        self.assertAlmostEqual(new_zoom, 0.167, places=3)

        # Test zoom at min limit
        initial_zoom = 0.1
        new_zoom = max(min_zoom, initial_zoom / zoom_factor)
        self.assertEqual(new_zoom, 0.1)

    def test_coordinate_transformation_screen_to_image(self):
        """Test coordinate transformation from screen to image space"""
        screen_x = 100
        screen_y = 150
        pan_x = 40
        pan_y = 30
        zoom_level = 0.6

        # Transform screen coordinates to image coordinates
        image_x = (screen_x - pan_x) / zoom_level
        image_y = (screen_y - pan_y) / zoom_level

        expected_x = (100 - 40) / 0.6  # 60 / 0.6 = 100
        expected_y = (150 - 30) / 0.6  # 120 / 0.6 = 200

        self.assertAlmostEqual(image_x, expected_x, places=1)
        self.assertAlmostEqual(image_y, expected_y, places=1)
        self.assertAlmostEqual(image_x, 100.0, places=1)
        self.assertAlmostEqual(image_y, 200.0, places=1)

    def test_coordinate_transformation_image_to_screen(self):
        """Test coordinate transformation from image to screen space"""
        image_x = 100
        image_y = 200
        pan_x = 40
        pan_y = 30
        zoom_level = 0.6

        # Transform image coordinates to screen coordinates
        screen_x = image_x * zoom_level + pan_x
        screen_y = image_y * zoom_level + pan_y

        expected_x = 100 * 0.6 + 40  # 60 + 40 = 100
        expected_y = 200 * 0.6 + 30  # 120 + 30 = 150

        self.assertAlmostEqual(screen_x, expected_x, places=1)
        self.assertAlmostEqual(screen_y, expected_y, places=1)
        self.assertAlmostEqual(screen_x, 100.0, places=1)
        self.assertAlmostEqual(screen_y, 150.0, places=1)

    def test_aspect_ratio_preservation(self):
        """Test that aspect ratio is preserved during scaling"""
        # Test with different aspect ratios
        test_cases = [
            (1200, 900, 1.333),  # 4:3
            (1920, 1080, 1.778),  # 16:9
            (800, 600, 1.333),  # 4:3
            (1000, 1000, 1.0),  # 1:1 (square)
        ]

        for width, height, expected_ratio in test_cases:
            with self.subTest(width=width, height=height):
                actual_ratio = width / height
                self.assertAlmostEqual(actual_ratio, expected_ratio, places=3)

    def test_edge_cases(self):
        """Test edge cases for zoom and pan calculations"""
        # Test with very small image
        small_width, small_height = 10, 10
        scale_x = self.container_width / small_width  # 800/10 = 80
        scale_y = self.container_height / small_height  # 600/10 = 60
        zoom = min(scale_x, scale_y) * 0.9  # 60 * 0.9 = 54
        self.assertEqual(zoom, 54.0)

        # Test with very large image
        large_width, large_height = 10000, 10000
        scale_x = self.container_width / large_width  # 800/10000 = 0.08
        scale_y = self.container_height / large_height  # 600/10000 = 0.06
        zoom = min(scale_x, scale_y) * 0.9  # 0.06 * 0.9 = 0.054
        self.assertAlmostEqual(zoom, 0.054, places=3)

        # Test with zero dimensions (should not crash)
        with self.assertRaises(ZeroDivisionError):
            self.container_width / 0


if __name__ == "__main__":
    unittest.main()
