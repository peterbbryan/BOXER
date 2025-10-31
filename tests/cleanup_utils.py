"""
Test cleanup utilities for removing test artifacts
"""

import os
import glob
from pathlib import Path


def cleanup_test_files():
    """Remove all test files created during testing and their database records"""
    from backend.database import SessionLocal, Image, Annotation

    project_root = Path(__file__).parent.parent

    # Remove test images and thumbnails
    uploads_images = project_root / "uploads" / "images"
    uploads_thumbnails = project_root / "uploads" / "thumbnails"

    removed_count = 0

    # Get database session to track and delete test images from DB
    db = SessionLocal()
    try:
        # Remove test images from database first
        test_images_query = db.query(Image).filter(
            (Image.filename.like("test_%.jpg"))
            | (Image.filename.like("ui_test_%.jpg"))
            | (Image.original_filename.like("test_%.jpg"))
            | (Image.original_filename.like("ui_test_%.jpg"))
            | (Image.filename.like("test_%.png"))
            | (Image.filename.like("ui_test_%.png"))
            | (Image.original_filename.like("test_%.png"))
            | (Image.original_filename.like("ui_test_%.png"))
        )

        test_images = test_images_query.all()

        # Delete annotations for these test images
        if test_images:
            image_ids = [img.id for img in test_images]
            db.query(Annotation).filter(Annotation.image_id.in_(image_ids)).delete()

            # Delete the images from database
            for img in test_images:
                db.delete(img)

        db.commit()
        removed_count += len(test_images)
    except Exception as e:
        db.rollback()
        print(f"Error cleaning test images from database: {e}")
    finally:
        db.close()

    # Remove test images from filesystem (match all extensions)
    for ext in [".jpg", ".jpeg", ".png", ".bmp"]:
        if uploads_images.exists():
            test_files = list(uploads_images.glob(f"test_*{ext}")) + list(
                uploads_images.glob(f"ui_test_*{ext}")
            )
            for test_file in test_files:
                try:
                    os.remove(test_file)
                    removed_count += 1
                except OSError:
                    pass

        # Remove test thumbnails
        if uploads_thumbnails.exists():
            test_thumbnails = list(
                uploads_thumbnails.glob(f"thumb_test_*{ext}")
            ) + list(uploads_thumbnails.glob(f"thumb_ui_test_*{ext}"))
            for test_file in test_thumbnails:
                try:
                    os.remove(test_file)
                    removed_count += 1
                except OSError:
                    pass

    # Clean up backend/uploads if it exists
    backend_uploads_images = project_root / "backend" / "uploads" / "images"
    backend_uploads_thumbnails = project_root / "backend" / "uploads" / "thumbnails"

    for ext in [".jpg", ".jpeg", ".png", ".bmp"]:
        if backend_uploads_images.exists():
            test_files = list(backend_uploads_images.glob(f"test_*{ext}")) + list(
                backend_uploads_images.glob(f"ui_test_*{ext}")
            )
            for test_file in test_files:
                try:
                    os.remove(test_file)
                    removed_count += 1
                except OSError:
                    pass

        if backend_uploads_thumbnails.exists():
            test_thumbnails = list(
                backend_uploads_thumbnails.glob(f"thumb_test_*{ext}")
            ) + list(backend_uploads_thumbnails.glob(f"thumb_ui_test_*{ext}"))
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
