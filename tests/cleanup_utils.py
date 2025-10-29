"""
Test cleanup utilities for removing test artifacts
"""

import os
import glob
from pathlib import Path


def cleanup_test_files():
    """Remove all test files created during testing"""
    project_root = Path(__file__).parent.parent

    # Remove test images and thumbnails
    uploads_images = project_root / "uploads" / "images"
    uploads_thumbnails = project_root / "uploads" / "thumbnails"

    removed_count = 0

    # Remove test images
    if uploads_images.exists():
        test_files = list(uploads_images.glob("test_*.jpg")) + list(
            uploads_images.glob("ui_test_*.jpg")
        )
        for test_file in test_files:
            try:
                os.remove(test_file)
                removed_count += 1
            except OSError:
                pass

    # Remove test thumbnails
    if uploads_thumbnails.exists():
        test_thumbnails = list(uploads_thumbnails.glob("thumb_test_*.jpg")) + list(
            uploads_thumbnails.glob("thumb_ui_test_*.jpg")
        )
        for test_file in test_thumbnails:
            try:
                os.remove(test_file)
                removed_count += 1
            except OSError:
                pass

    # Clean up backend/uploads if it exists
    backend_uploads_images = project_root / "backend" / "uploads" / "images"
    backend_uploads_thumbnails = project_root / "backend" / "uploads" / "thumbnails"

    if backend_uploads_images.exists():
        test_files = list(backend_uploads_images.glob("test_*.jpg")) + list(
            backend_uploads_images.glob("ui_test_*.jpg")
        )
        for test_file in test_files:
            try:
                os.remove(test_file)
                removed_count += 1
            except OSError:
                pass

    if backend_uploads_thumbnails.exists():
        test_thumbnails = list(
            backend_uploads_thumbnails.glob("thumb_test_*.jpg")
        ) + list(backend_uploads_thumbnails.glob("thumb_ui_test_*.jpg"))
        for test_file in test_thumbnails:
            try:
                os.remove(test_file)
                removed_count += 1
            except OSError:
                pass

    return removed_count


def cleanup_test_categories():
    """Remove test label categories from the database"""
    from backend.database import SessionLocal, LabelCategory, Annotation

    db = SessionLocal()
    try:
        # Find test categories
        test_categories = (
            db.query(LabelCategory)
            .filter(
                (LabelCategory.name.like("Test Category%"))
                | (LabelCategory.name == "Test")
                | (LabelCategory.name == "test")
            )
            .all()
        )

        if not test_categories:
            return 0

        # Get category IDs
        category_ids = [cat.id for cat in test_categories]

        # Delete annotations using these categories
        db.query(Annotation).filter(
            Annotation.label_category_id.in_(category_ids)
        ).delete()

        # Delete the categories
        deleted = (
            db.query(LabelCategory).filter(LabelCategory.id.in_(category_ids)).delete()
        )

        db.commit()
        return deleted
    finally:
        db.close()


def cleanup_all():
    """Clean up all test artifacts"""
    print("🧹 Cleaning up test artifacts...")

    files_removed = cleanup_test_files()
    categories_removed = cleanup_test_categories()

    print(f"✅ Removed {files_removed} test files")
    print(f"✅ Removed {categories_removed} test categories")

    return files_removed + categories_removed


if __name__ == "__main__":
    cleanup_all()
