"""
Unit tests for image utilities
"""

import unittest
from unittest.mock import patch, mock_open
import tempfile
import os
from PIL import Image

from backend.image_utils import (
    generate_unique_filename,
    create_thumbnail,
    get_image_info,
    validate_image,
    process_uploaded_image,
)


class TestImageUtils(unittest.TestCase):
    """Test image utility functions"""

    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up any test files
        for file in os.listdir(self.temp_dir):
            file_path = os.path.join(self.temp_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir(self.temp_dir)

    def test_generate_unique_filename(self):
        """Test unique filename generation"""
        original_filename = "test_image.jpg"
        generated = generate_unique_filename(original_filename)

        # Should be different from original
        self.assertNotEqual(generated, original_filename)

        # Should preserve extension
        self.assertTrue(generated.endswith(".jpg"))

        # Should be reasonable length
        self.assertLess(len(generated), 100)

    def test_generate_unique_filename_different_inputs(self):
        """Test unique filename generation with different inputs"""
        test_cases = [
            "image.png",
            "photo.jpeg",
            "picture.tiff",
            "document.pdf",
            "file_with_underscores.jpg",
            "file-with-dashes.png",
            "file with spaces.gif",
        ]

        for original in test_cases:
            with self.subTest(original=original):
                generated = generate_unique_filename(original)
                self.assertNotEqual(generated, original)
                self.assertTrue(generated.endswith(os.path.splitext(original)[1]))

    def test_create_thumbnail(self):
        """Test thumbnail creation"""
        # Create a test image
        test_image_path = os.path.join(self.temp_dir, "test.jpg")
        img = Image.new("RGB", (800, 600), color="red")
        img.save(test_image_path, "JPEG")

        # Create thumbnail
        thumbnail_path = os.path.join(self.temp_dir, "thumb_test.jpg")
        result = create_thumbnail(test_image_path, thumbnail_path)

        self.assertTrue(result)
        self.assertTrue(os.path.exists(thumbnail_path))

        # Check thumbnail dimensions (default size is 300x300)
        with Image.open(thumbnail_path) as thumb:
            self.assertLessEqual(thumb.width, 300)
            self.assertLessEqual(thumb.height, 300)

    def test_create_thumbnail_small_image(self):
        """Test thumbnail creation with small image"""
        # Create a small test image
        test_image_path = os.path.join(self.temp_dir, "small.jpg")
        img = Image.new("RGB", (50, 50), color="blue")
        img.save(test_image_path, "JPEG")

        # Create thumbnail
        thumbnail_path = os.path.join(self.temp_dir, "thumb_small.jpg")
        result = create_thumbnail(test_image_path, thumbnail_path)

        self.assertTrue(result)
        self.assertTrue(os.path.exists(thumbnail_path))

    def test_create_thumbnail_nonexistent_file(self):
        """Test thumbnail creation with non-existent file"""
        thumbnail_path = os.path.join(self.temp_dir, "thumb_nonexistent.jpg")
        result = create_thumbnail("nonexistent.jpg", thumbnail_path)

        self.assertFalse(result)
        self.assertFalse(os.path.exists(thumbnail_path))

    def test_get_image_info(self):
        """Test getting image information"""
        # Create a test image
        test_image_path = os.path.join(self.temp_dir, "test.jpg")
        img = Image.new("RGB", (800, 600), color="red")
        img.save(test_image_path, "JPEG")

        info = get_image_info(test_image_path)

        self.assertEqual(info["width"], 800)
        self.assertEqual(info["height"], 600)
        self.assertEqual(info["format"], "JPEG")
        self.assertGreater(info["file_size"], 0)

    def test_get_image_info_nonexistent_file(self):
        """Test getting image info for non-existent file"""
        info = get_image_info("nonexistent.jpg")

        self.assertEqual(info, {})

    def test_validate_image(self):
        """Test image validation"""
        # Create a valid test image
        test_image_path = os.path.join(self.temp_dir, "valid.jpg")
        img = Image.new("RGB", (100, 100), color="red")
        img.save(test_image_path, "JPEG")

        self.assertTrue(validate_image(test_image_path))

    def test_validate_image_invalid_file(self):
        """Test image validation with invalid file"""
        # Create a text file (not an image)
        test_file_path = os.path.join(self.temp_dir, "not_image.txt")
        with open(test_file_path, "w") as f:
            f.write("This is not an image")

        self.assertFalse(validate_image(test_file_path))

    def test_validate_image_nonexistent_file(self):
        """Test image validation with non-existent file"""
        self.assertFalse(validate_image("nonexistent.jpg"))

    def test_get_image_info_mime_type(self):
        """Test MIME type detection through get_image_info"""
        # Create a test image
        test_image_path = os.path.join(self.temp_dir, "test.jpg")
        img = Image.new("RGB", (100, 100), color="red")
        img.save(test_image_path, "JPEG")

        info = get_image_info(test_image_path)
        self.assertIn("format", info)
        self.assertEqual(info["format"], "JPEG")

    def test_process_uploaded_image(self):
        """Test processing uploaded image"""
        # Create a test image
        test_image_path = os.path.join(self.temp_dir, "test.jpg")
        img = Image.new("RGB", (800, 600), color="red")
        img.save(test_image_path, "JPEG")

        # Test the actual function
        result = process_uploaded_image(test_image_path, "test.jpg")

        self.assertIsNotNone(result)
        self.assertEqual(result["width"], 800)
        self.assertEqual(result["height"], 600)
        self.assertEqual(result["mime_type"], "image/jpeg")
        self.assertGreater(result["file_size"], 0)
        self.assertIn("filename", result)
        self.assertIn("file_path", result)
        self.assertIn("thumbnail_path", result)
        self.assertIn("original_filename", result)

    def test_process_uploaded_image_invalid(self):
        """Test processing invalid image"""
        # This will raise an exception since the file doesn't exist
        with self.assertRaises(OSError):
            process_uploaded_image("nonexistent.jpg", "test.jpg")

    def test_image_file_operations(self):
        """Test basic image file operations"""
        # Create test files
        image_path = os.path.join(self.temp_dir, "test.jpg")
        thumbnail_path = os.path.join(self.temp_dir, "thumb_test.jpg")

        with open(image_path, "w") as f:
            f.write("fake image")
        with open(thumbnail_path, "w") as f:
            f.write("fake thumbnail")

        # Test that files exist
        self.assertTrue(os.path.exists(image_path))
        self.assertTrue(os.path.exists(thumbnail_path))

        # Test manual deletion
        os.remove(image_path)
        os.remove(thumbnail_path)

        self.assertFalse(os.path.exists(image_path))
        self.assertFalse(os.path.exists(thumbnail_path))

    def test_image_formats_support(self):
        """Test support for different image formats"""
        formats_to_test = [
            ("JPEG", "image/jpeg"),
            ("PNG", "image/png"),
            ("BMP", "image/bmp"),
            ("TIFF", "image/tiff"),
        ]

        for format_name, expected_mime in formats_to_test:
            with self.subTest(format=format_name):
                # Create test image
                test_image_path = os.path.join(
                    self.temp_dir, f"test.{format_name.lower()}"
                )
                img = Image.new("RGB", (100, 100), color="blue")
                img.save(test_image_path, format_name)

                # Test validation
                self.assertTrue(validate_image(test_image_path))

                # Test info extraction
                info = get_image_info(test_image_path)
                self.assertIsNotNone(info)
                self.assertEqual(info["format"], format_name)

    def test_thumbnail_preserves_aspect_ratio(self):
        """Test that thumbnail creation preserves aspect ratio"""
        # Create a rectangular test image
        test_image_path = os.path.join(self.temp_dir, "rect.jpg")
        img = Image.new("RGB", (400, 200), color="green")  # 2:1 aspect ratio
        img.save(test_image_path, "JPEG")

        # Create thumbnail
        thumbnail_path = os.path.join(self.temp_dir, "thumb_rect.jpg")
        result = create_thumbnail(test_image_path, thumbnail_path)

        self.assertTrue(result)

        # Check that aspect ratio is preserved
        with Image.open(thumbnail_path) as thumb:
            aspect_ratio = thumb.width / thumb.height
            expected_ratio = 400 / 200  # 2:1
            self.assertAlmostEqual(aspect_ratio, expected_ratio, places=2)


if __name__ == "__main__":
    unittest.main()
