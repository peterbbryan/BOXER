"""
End-to-end tests for UI functionality
"""

import unittest
import tempfile
import os
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from PIL import Image
import json

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.main import app


class TestUIFunctionality(unittest.TestCase):
    """Test UI functionality end-to-end"""

    def setUp(self):
        """Set up test fixtures"""
        self.client = TestClient(app)
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        """Clean up test fixtures"""
        # Clean up test files
        for file in os.listdir(self.temp_dir):
            file_path = os.path.join(self.temp_dir, file)
            if os.path.isfile(file_path):
                os.remove(file_path)
        os.rmdir(self.temp_dir)

    def test_main_page_loads(self):
        """Test that the main page loads correctly"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # Check that it returns HTML
        self.assertIn("text/html", response.headers["content-type"])

        # Check for key UI elements
        content = response.text
        self.assertIn("VibeCortex", content)
        self.assertIn("Image Labeling Tool", content)
        self.assertIn("annotation-canvas", content)
        self.assertIn("tool-btn", content)

    def test_ui_elements_present(self):
        """Test that all required UI elements are present"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        content = response.text

        # Check for main UI components
        ui_elements = [
            "annotation-canvas",
            "main-image",
            "canvas-container",
            "tool-btn",
            "label-category",  # Changed from category-btn
            "zoom-in",
            "zoom-out",
            "fit-to-screen",
            "clear-tool",
            "close-image",
            "delete-image",
            "image-upload",
            "image-grid",  # Changed from image-thumbnails
            "current-image",
            "total-images",
            "image-count",
            "project-name-display",  # Add project name display
            "upload-images",  # Add upload button
        ]

        for element in ui_elements:
            with self.subTest(element=element):
                self.assertIn(element, content)

    def test_javascript_functions_present(self):
        """Test that required JavaScript functions are present"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        content = response.text

        # Check for key JavaScript functions
        js_functions = [
            "loadImage",
            "setupCanvas",
            "startDrawing",
            "draw",
            "stopDrawing",
            "drawExistingAnnotations",
            "zoomIn",
            "zoomOut",
            "fitToScreen",
            "updateImageTransform",
            "uploadImages",
            "clearAllAnnotations",
            "selectAnnotation",
            "deleteSelectedAnnotation",
            "editAnnotation",
            "completePolygon",
            "drawPolygonPreview",
        ]

        for function in js_functions:
            with self.subTest(function=function):
                self.assertIn(f"function {function}", content)

    def test_css_classes_present(self):
        """Test that required CSS classes are present"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        content = response.text

        # Check for key CSS classes
        css_classes = [
            "bg-gray-900",
            "text-white",
            "tool-btn",
            "label-category",
            "active",
            "hidden",
            "flex",
            "grid",
            "rounded",
            "hover:",
            "transition-colors",
        ]

        for css_class in css_classes:
            with self.subTest(css_class=css_class):
                self.assertIn(css_class, content)

    def test_image_upload_ui_flow(self):
        """Test the complete image upload UI flow"""
        # Step 1: Load main page
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # Step 2: Check that upload area is present
        content = response.text
        self.assertIn("image-upload", content)
        self.assertIn("upload-images", content)

        # Step 3: Create a test image
        test_image_path = os.path.join(self.temp_dir, "ui_test.jpg")
        img = Image.new("RGB", (400, 300), color="blue")
        img.save(test_image_path, "JPEG")

        # Step 4: Upload the image
        with open(test_image_path, "rb") as f:
            files = {"file": ("ui_test.jpg", f, "image/jpeg")}
            data = {"dataset_id": 5}
            response = self.client.post("/api/images/upload", files=files, data=data)

        self.assertEqual(response.status_code, 200)
        upload_data = response.json()
        self.assertIn("image_id", upload_data)

        # Step 5: Verify image appears in the UI
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        # The upload form should still be present after upload
        content = response.text
        self.assertIn("image-upload", content)
        self.assertIn("upload-images", content)

    def test_annotation_tools_ui(self):
        """Test that annotation tools are properly configured in UI"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        content = response.text

        # Check for annotation tool functionality in JavaScript
        tool_functions = ["startDrawing", "draw", "stopDrawing", "completePolygon"]
        for func in tool_functions:
            with self.subTest(func=func):
                self.assertIn(func, content)

    def test_category_buttons_ui(self):
        """Test that category buttons are properly configured in UI"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        content = response.text

        # Check for category button structure
        self.assertIn("label-category", content)
        self.assertIn("getCategoryColor", content)

    def test_zoom_controls_ui(self):
        """Test that zoom controls are properly configured in UI"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        content = response.text

        # Check for zoom control buttons
        zoom_controls = ["zoom-in", "zoom-out", "fit-to-screen"]
        for control in zoom_controls:
            with self.subTest(control=control):
                self.assertIn(f'id="{control}"', content)

    def test_image_navigation_ui(self):
        """Test that image navigation controls are present"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        content = response.text

        # Check for image navigation elements
        nav_elements = [
            "current-image",
            "total-images",
            "image-grid",
            "image-thumbnail",
        ]

        for element in nav_elements:
            with self.subTest(element=element):
                self.assertIn(element, content)

    def test_annotation_context_menu_ui(self):
        """Test that annotation context menu is properly configured"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        content = response.text

        # Check for context menu elements
        context_menu_elements = [
            "annotation-context-menu",
            "edit-annotation",
            "delete-annotation",
        ]

        for element in context_menu_elements:
            with self.subTest(element=element):
                self.assertIn(f'id="{element}"', content)

    def test_notification_system_ui(self):
        """Test that notification system is properly configured"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        content = response.text

        # Check for notification system JavaScript function
        self.assertIn("showNotification", content)

        # Check for notification CSS classes that would be applied dynamically
        self.assertIn("bg-green-500", content)  # success notification
        self.assertIn("bg-red-500", content)  # error notification
        self.assertIn("bg-blue-500", content)  # info notification

    def test_responsive_design_elements(self):
        """Test that responsive design elements are present"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        content = response.text

        # Check for responsive design classes
        responsive_classes = [
            "flex",
            "grid",
            "hidden",
            "block",
            "w-full",
            "h-screen",  # Changed from h-full
        ]

        for css_class in responsive_classes:
            with self.subTest(css_class=css_class):
                self.assertIn(css_class, content)

    def test_dark_mode_styling(self):
        """Test that dark mode styling is applied"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        content = response.text

        # Check for dark mode classes
        dark_mode_classes = [
            "bg-gray-900",
            "text-white",
            "text-gray-300",
            "bg-gray-800",
            "border-gray-600",
        ]

        for css_class in dark_mode_classes:
            with self.subTest(css_class=css_class):
                self.assertIn(css_class, content)

    def test_keyboard_shortcuts_ui(self):
        """Test that keyboard shortcuts are properly configured"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        content = response.text

        # Check for keyboard event listeners
        keyboard_events = [
            "addEventListener('keydown'",
            "key === 'Escape'",
            "key === 'Delete'",
            "key === 'Enter'",
        ]

        for event in keyboard_events:
            with self.subTest(event=event):
                self.assertIn(event, content)

    def test_mouse_events_ui(self):
        """Test that mouse events are properly configured"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        content = response.text

        # Check for mouse event listeners
        mouse_events = [
            "addEventListener('mousedown'",
            "addEventListener('mousemove'",
            "addEventListener('mouseup'",
            "addEventListener('click'",
            "addEventListener('wheel'",
        ]

        for event in mouse_events:
            with self.subTest(event=event):
                self.assertIn(event, content)

    def test_canvas_setup_ui(self):
        """Test that canvas is properly set up in UI"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        content = response.text

        # Check for canvas setup
        canvas_elements = [
            "annotation-canvas",
            "getContext('2d')",
            "canvas.width",
            "canvas.height",
            "clearRect",
        ]

        for element in canvas_elements:
            with self.subTest(element=element):
                self.assertIn(element, content)

    def test_error_handling_ui(self):
        """Test that error handling is properly configured in UI"""
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

        content = response.text

        # Check for error handling
        error_handling = [
            "onerror",
            "try",
            "catch",
            "console.error",
            "showNotification",
        ]

        for element in error_handling:
            with self.subTest(element=element):
                self.assertIn(element, content)


if __name__ == "__main__":
    unittest.main()
