"""
Test cleanup utilities for removing test artifacts
"""

import os
from pathlib import Path


def cleanup_test_files():
    """Remove all test files created during testing and their database records"""
    try:
        from backend.database import SessionLocal, Image, Annotation
    except ModuleNotFoundError as e:
        print(f"⚠️  Warning: Cannot import database modules for cleanup: {e}")
        return 0

    project_root = Path(__file__).parent.parent

    # Remove test images and thumbnails
    uploads_images = project_root / "uploads" / "images"
    uploads_thumbnails = project_root / "uploads" / "thumbnails"

    removed_count = 0

    # Get database session to track and delete test images from DB
    db = SessionLocal()
    try:
        # Remove test images from database first
        # IMPORTANT: Only match files that START with these test prefixes and have image extensions
        # This prevents accidentally matching user files that might contain "test" in the name
        test_patterns = [
            "test_",  # Must start with "test_"
            "ui_test_",  # Must start with "ui_test_"
            "concurrent_",  # Must start with "concurrent_"
            "persistence_test_",  # Must start with "persistence_test_"
            "test_workflow_",  # Must start with "test_workflow_"
        ]

        # Build filter conditions for filename and original_filename
        # CRITICAL: Only match if filename STARTS with test pattern AND has an extension
        # This prevents matching partial names or files without extensions
        filters = []
        image_extensions = [".jpg", ".jpeg", ".png", ".bmp"]

        for pattern in test_patterns:
            # Match files that start with the pattern followed by any characters and then an extension
            # Pattern: "test_%" matches anything starting with "test_"
            # But we require it to have one of our extensions at the end
            for ext in image_extensions:
                # Match: test_something.jpg, test_123.jpg, etc.
                # BUT also match test_something_abc123.jpg (the unique ID format)
                pattern_with_ext = f"{pattern}%{ext}"
                filters.append(Image.filename.like(pattern_with_ext))
                filters.append(Image.original_filename.like(pattern_with_ext))

        # Also match exact test filenames (without UUID suffix)
        test_exact_names = ["test.jpg", "ui_test.jpg", "test.png", "ui_test.png"]
        for name in test_exact_names:
            filters.append(Image.filename == name)
            filters.append(Image.original_filename == name)

        from sqlalchemy import or_

        # Safety check: If no filters defined, don't delete anything
        if not filters:
            print("⚠️  WARNING: No test image filters defined - skipping cleanup")
            test_images = []
        else:
            test_images_query = db.query(Image).filter(or_(*filters))
            test_images = test_images_query.all()

        # Safety check: Show all images before deletion for verification
        all_images = db.query(Image).all()
        if all_images:
            print(f"\n📊 Current images in database ({len(all_images)} total):")
            for img in all_images:
                is_test = img in test_images
                status = (
                    "🗑️  TEST (will be deleted)"
                    if is_test
                    else "✅ PRODUCTION (preserved)"
                )
                print(
                    f"  {status}: {img.filename} (original: {img.original_filename}, ID: {img.id})"
                )

        print(f"\n🗑️  Found {len(test_images)} test images to clean up")
        if test_images:
            for img in test_images:
                print(
                    f"  - {img.filename} (original: {img.original_filename}, ID: {img.id})"
                )
        else:
            print("  ✅ No test images found - all images are production")

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
                f"\n✅ Deleted {len(test_images)} test images and {annotation_count} associated annotations"
            )

        # Show remaining production images
        remaining_images = db.query(Image).all()
        if remaining_images:
            print(f"\n✅ Preserved {len(remaining_images)} production image(s):")
            for img in remaining_images:
                print(
                    f"  - {img.filename} (original: {img.original_filename}, ID: {img.id})"
                )
        else:
            print("\nℹ️  No images remain in database")
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
    """Remove test label categories from the database.

    Only removes categories with specific test-related names:
    - "Test Category%" (pattern: matches "Test Category", "Test Category 1", etc.)
    - "Test" (exact match)
    - "test" (exact match)
    - "Class1" (exact match - created by YOLO export tests)
    - "Class2" (exact match - created by YOLO export tests)

    Production categories with other names (e.g., "person", "car", custom names)
    are NOT affected by this cleanup.
    """
    try:
        from backend.database import SessionLocal, LabelCategory, Annotation
    except ModuleNotFoundError as e:
        print(f"⚠️  Warning: Cannot import database modules for cleanup: {e}")
        return 0

    db = SessionLocal()
    try:
        # Define test category names - ONLY these specific names will be deleted
        # This ensures production categories are never accidentally removed
        TEST_CATEGORY_NAMES = [
            "Test Category%",  # Pattern match
            "Test",  # Exact match
            "test",  # Exact match
            "Class1",  # Exact match (YOLO test category)
            "Class2",  # Exact match (YOLO test category)
        ]

        # Find test categories using specific test names only
        filters = []
        for name in TEST_CATEGORY_NAMES:
            if name.endswith("%"):
                # Pattern match
                filters.append(LabelCategory.name.like(name))
            else:
                # Exact match
                filters.append(LabelCategory.name == name)

        from sqlalchemy import or_

        test_categories = db.query(LabelCategory).filter(or_(*filters)).all()

        # Show all categories before cleanup for verification
        all_categories = db.query(LabelCategory).all()
        if all_categories:
            print(f"\n📊 Current categories in database ({len(all_categories)} total):")
            for cat in all_categories:
                is_test = cat in test_categories
                status = (
                    "🗑️  TEST (will be deleted)"
                    if is_test
                    else "✅ PRODUCTION (preserved)"
                )
                print(
                    f"  {status}: {cat.name} (ID: {cat.id}, project: {cat.project_id})"
                )

        if not test_categories:
            print(
                "\n✅ No test categories found to clean up - all categories are production"
            )
            return 0

        print(f"\n🗑️  Found {len(test_categories)} test categories to clean up:")
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
        print(f"\n✅ Deleted {deleted} test categories and associated annotations")

        # Show remaining production categories
        remaining_categories = db.query(LabelCategory).all()
        if remaining_categories:
            print(
                f"\n✅ Preserved {len(remaining_categories)} production category(ies):"
            )
            for cat in remaining_categories:
                print(f"  - {cat.name} (ID: {cat.id}, project: {cat.project_id})")
        else:
            print("\nℹ️  No categories remain in database")

        return deleted
    except Exception as e:
        db.rollback()
        print(f"❌ Error cleaning test categories: {e}")
        import traceback

        traceback.print_exc()
        raise
    finally:
        db.close()


def cleanup_all():
    """Clean up all test artifacts"""
    print("🧹 Cleaning up test artifacts...")

    try:
        files_removed = cleanup_test_files()
        categories_removed = cleanup_test_categories()

        print(f"✅ Removed {files_removed} test files")
        print(f"✅ Removed {categories_removed} test categories")

        return files_removed + categories_removed
    except Exception as e:
        print(f"⚠️  Warning: Cleanup encountered errors: {e}")
        return 0


if __name__ == "__main__":
    cleanup_all()
