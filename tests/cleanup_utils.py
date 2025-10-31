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
        # Match test patterns: test_*, ui_test_*, concurrent_*, persistence_test_*, test_workflow_*
        test_patterns = [
            "test_%",  # Matches test_*.jpg, test_workflow_*.jpg, etc.
            "ui_test_%",
            "concurrent_%",
            "persistence_test_%",
            "test_workflow_%",
        ]

        # Build filter conditions for filename and original_filename
        filters = []
        for pattern in test_patterns:
            # Match all common image extensions
            for ext in ["", ".jpg", ".jpeg", ".png", ".bmp"]:
                filters.append(Image.filename.like(pattern + ext))
                filters.append(Image.original_filename.like(pattern + ext))

        # Also match exact test filenames
        test_exact_names = ["test.jpg", "ui_test.jpg", "test.png", "ui_test.png"]
        for name in test_exact_names:
            filters.append(Image.filename == name)
            filters.append(Image.original_filename == name)

        from sqlalchemy import or_

        test_images_query = db.query(Image).filter(or_(*filters))

        test_images = test_images_query.all()

        print(f"Found {len(test_images)} test images to clean up")
        for img in test_images:
            print(f"  - {img.filename} (original: {img.original_filename})")

        # Delete annotations for these test images
        if test_images:
            image_ids = [img.id for img in test_images]
            annotation_count = (
                db.query(Annotation).filter(Annotation.image_id.in_(image_ids)).count()
            )
            db.query(Annotation).filter(Annotation.image_id.in_(image_ids)).delete()

            # Delete the images from database
            for img in test_images:
                db.delete(img)

        db.commit()
        removed_count += len(test_images)
        if test_images:
            print(
                f"Deleted {len(test_images)} test images and {annotation_count} associated annotations"
            )
    except Exception as e:
        db.rollback()
        print(f"Error cleaning test images from database: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()

    # Remove test images from filesystem (match all extensions)
    # This also removes orphaned files that aren't in the database
    directories_to_clean = [
        (uploads_images, uploads_thumbnails),
        (
            project_root / "backend" / "uploads" / "images",
            project_root / "backend" / "uploads" / "thumbnails",
        ),
    ]

    for images_dir, thumbnails_dir in directories_to_clean:
        for ext in [".jpg", ".jpeg", ".png", ".bmp"]:
            # Clean main images - match all test patterns
            if images_dir.exists():
                test_patterns = [
                    f"test_*{ext}",
                    f"ui_test_*{ext}",
                    f"concurrent_*{ext}",
                    f"persistence_test_*{ext}",
                    f"test_workflow_*{ext}",
                ]
                test_files = []
                for pattern in test_patterns:
                    test_files.extend(list(images_dir.glob(pattern)))

                for test_file in test_files:
                    try:
                        print(f"Removing filesystem test file: {test_file}")
                        os.remove(test_file)
                        removed_count += 1
                    except OSError as e:
                        print(f"Warning: Could not remove {test_file}: {e}")

            # Clean thumbnails - match all test patterns
            if thumbnails_dir.exists():
                test_thumbnail_patterns = [
                    f"thumb_test_*{ext}",
                    f"thumb_ui_test_*{ext}",
                    f"thumb_concurrent_*{ext}",
                    f"thumb_persistence_test_*{ext}",
                    f"thumb_test_workflow_*{ext}",
                ]
                test_thumbnails = []
                for pattern in test_thumbnail_patterns:
                    test_thumbnails.extend(list(thumbnails_dir.glob(pattern)))

                for test_file in test_thumbnails:
                    try:
                        print(f"Removing filesystem test thumbnail: {test_file}")
                        os.remove(test_file)
                        removed_count += 1
                    except OSError as e:
                        print(f"Warning: Could not remove {test_file}: {e}")

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
                | (LabelCategory.name == "Class1")
                | (LabelCategory.name == "Class2")
            )
            .all()
        )

        if not test_categories:
            print("No test categories found to clean up")
            return 0

        print(f"Found {len(test_categories)} test categories to clean up")
        for cat in test_categories:
            print(f"  - {cat.name} (ID: {cat.id}, project: {cat.project_id})")

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
        print(f"Deleted {deleted} test categories")
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
