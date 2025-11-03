# 🎨 BOXER - Intelligent Image Labeling Tool

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Status](https://img.shields.io/badge/status-active-success.svg)

**A powerful, web-based image annotation tool designed for creating high-quality training data for computer vision models. Built with a focus on simplicity, performance, and ease of use.**

[Features](#-features) • [Installation](#-installation) • [Usage](#-usage) • [API Reference](#-api-reference) • [Contributing](#-contributing)

</div>

---

## ✨ Features

### 🖼️ **Multi-Format Image Support**
- Support for **PNG, JPG, JPEG, GIF, and TIFF** formats
- Handle **large images** up to **100MB**
- Automatic thumbnail generation for fast loading
- Responsive image viewing with zoom and pan controls

### 📝 **Advanced Annotation Tools**
- **Bounding Boxes**: Draw rectangular annotations with precise coordinate tracking
- **Point Annotations**: Mark specific points of interest
- **Polygon Annotations**: Create complex shapes with multiple vertices
- **Smart Coordinate Clamping**: Automatically restrict annotations to image boundaries

### 🎯 **Multi-Select & Batch Operations**
- **Ctrl+Click** to select multiple annotations
- **Ctrl+A** to select all annotations
- **Drag-to-Move**: Reposition selected annotations together
- **Copy/Paste**: Duplicate annotations within an image or between images
- **Batch Editing**: Edit multiple annotations simultaneously

### 🏷️ **Smart Category Management**
- Create custom label categories with unique colors
- **Import YOLO Classes**: Bulk import from `classes.txt` files
- **Random Color Assignment**: Auto-generate distinct colors for imported classes
- **Delete Categories**: Remove categories with confirmation
- **Visual Indicators**: Color-coded annotation display

### 📊 **YOLO Export & Import**
- **Export to YOLO Format**: Generate standard YOLO dataset with:
  - `classes.txt` file
  - Label files (`.txt`) for each image
  - Organized directory structure
  - Automatic coordinate normalization
- **Import YOLO Classes**: Upload `classes.txt` to create categories
- **Deduplication**: Smart handling of duplicate category names
- **Validation**: Ensures valid annotations before export

### 🔍 **Enhanced User Experience**
- **Auto-Fit Zoom**: Images automatically fit to screen on load
- **Pan Mode**: Pan around large images with dedicated tool
- **Context Menu**: Right-click to edit or delete annotations
- **Keyboard Shortcuts**:
  - `Ctrl+C` / `Cmd+C`: Copy annotations
  - `Ctrl+V` / `Cmd+V`: Paste annotations
  - `Ctrl+A` / `Cmd+A`: Select all
- **Responsive Design**: Adaptive layout that fits any screen size
- **Smart Scrolling**: Only scrollable areas scroll (categories list, images list)

### 💾 **Data Management**
- **SQLite Database**: Lightweight, file-based storage
- **Project Management**: Organize annotations by projects and datasets
- **Data Persistence**: All annotations saved automatically
- **File Management**: Automatic cleanup when images are deleted

---

## 🚀 Installation

### Prerequisites
- Python 3.9 or higher
- pip

### Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/BOXER.git
   cd BOXER
   ```

2. **Create and activate a virtual environment**
   ```bash
   python3.9 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install the package in development mode**
   ```bash
   pip install -e .
   ```

5. **Initialize the database**
   ```bash
   python run.py
   ```

6. **Access the application**
   Open your browser and navigate to `http://localhost:8000`

---

## 💡 Usage

### Getting Started

1. **Create a Project**
   - On first launch, a default project is automatically created
   - You can edit the project name by clicking on it

2. **Add Label Categories**
   - Click "Add Category" in the sidebar
   - Enter a name and choose a color
   - Or import categories from a YOLO `classes.txt` file using "Import Classes"

3. **Upload Images**
   - Click in the upload area or use the "Upload Images" button
   - Select one or multiple images
   - Images will be automatically processed and thumbnails created

4. **Annotate Images**
   - Select an annotation tool: Select, Bounding Box, Point, or Polygon
   - Choose a category from the list
   - Draw annotations directly on the image
   - Use the context menu (right-click) to edit or delete

5. **Manage Annotations**
   - Use Ctrl+Click to select multiple annotations
   - Drag selected annotations to reposition them
   - Copy and paste annotations within or between images
   - Use the context menu to change categories or delete

6. **Export Data**
   - Click "Export YOLO" to download annotations in YOLO format
   - The exported ZIP contains:
     - `classes.txt`: List of all categories
     - `labels/`: Directory with label files
     - `images/`: Directory with original images

### Annotation Tips

- **Zoom Controls**: Use zoom in/out buttons or mouse wheel for precision
- **Pan Tool**: Enable pan mode to move around large images
- **Multi-Select**: Hold Ctrl while clicking to select multiple annotations
- **Keyboard Shortcuts**: Use Ctrl+C/V to copy/paste annotations

---

## 🔌 API Reference

### Authentication
Currently no authentication is implemented. All features are accessible to anyone with access to the server.

### Endpoints

#### Images
- `POST /api/images/upload` - Upload one or more images
- `DELETE /api/images/{image_id}` - Delete an image and its files

#### Annotations
- `POST /api/annotations` - Create a new annotation
- `GET /api/annotations/{image_id}` - Get all annotations for an image
- `PUT /api/annotations/{annotation_id}` - Update an annotation
- `DELETE /api/annotations/{annotation_id}` - Delete an annotation

#### Categories
- `POST /api/label-categories` - Create a label category
- `DELETE /api/label-categories/{category_id}` - Delete a label category

#### Export/Import
- `GET /api/export/yolo` - Export all annotations in YOLO format
- `POST /api/import/yolo-classes` - Import categories from YOLO classes.txt

#### Projects
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create a new project
- `PUT /api/projects/{project_id}` - Update a project

---

## 🏗️ Project Structure

```
BOXER/
├── backend/                   # Backend API code
│   ├── main.py               # FastAPI application
│   ├── database.py           # Database models and setup
│   └── image_utils.py        # Image processing utilities
├── templates/                # HTML templates
│   ├── labeling.html         # Main annotation interface
│   ├── dashboard.html        # Dashboard view
│   └── base.html             # Base template
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   ├── performance/          # Performance tests
│   └── e2e/                  # End-to-end tests
├── uploads/                  # Uploaded images (auto-generated)
│   ├── images/               # Original images
│   └── thumbnails/           # Thumbnail images
├── requirements.txt          # Python dependencies
├── setup.py                  # Package configuration
└── run.py                    # Application entry point
```

---

## 🧪 Development

### Running Tests
```bash
# Run all tests
pytest

# Run specific test suite
pytest tests/unit/
pytest tests/integration/

# Run with coverage
pytest --cov=backend tests/
```

### Code Quality
```bash
# Format code with Black
black backend/ tests/

# Lint with Pylint
pylint backend/

# Type checking with mypy
mypy backend/
```

### Development Server
```bash
# Run development server with auto-reload
python run.py

# Or using uvicorn directly
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Code Style
- Follow PEP 8 style guide
- Use Black for code formatting
- Write comprehensive tests for new features
- Update documentation as needed

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- UI powered by [TailwindCSS](https://tailwindcss.com/)
- Icons from [Font Awesome](https://fontawesome.com/)
- Image processing with [Pillow](https://python-pillow.org/)

---

## 📞 Support

For issues, questions, or suggestions, please open an issue on the [GitHub Issues](https://github.com/yourusername/BOXER/issues) page.

---

<div align="center">

**Made with ❤️ for the computer vision community**

⭐ Star this repo if you find it helpful!

</div>
