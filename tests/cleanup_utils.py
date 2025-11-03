"""
Test cleanup utilities for removing test artifacts

This module ensures that only test-generated images and annotations are cleaned up,
while protecting all production data including YOLO-imported images and model-generated annotations.
"""

import os
from pathlib import Path


def cleanup_test_files():
    """Remove all test files created during testing and their database records

    CRITICAL SAFETY: This function will NEVER delete images from "Default Dataset" or
    any dataset that doesn't explicitly match test dataset patterns.
    """
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
    test_images = (
        []
    )  # Initialize to empty list - will be populated if we find test images to delete

    # Get database session to track and delete test images from DB
    db = SessionLocal()
    try:
        # CRITICAL SAFETY: Only delete images that are in test datasets
        # This prevents deleting production images even if they match filename patterns
        from backend.database import Dataset
        from sqlalchemy import and_, or_

        # Identify test datasets - ONLY match datasets that are clearly test datasets
        # CRITICAL: Be very strict to avoid matching production datasets
        # EXCLUDE "Default Dataset" and "YOLO Dataset" - these are production dataset names
        # Only match:
        # 1. Exact name "Test Dataset" (the standard test dataset name)
        # 2. Datasets that start with "Test Dataset" (e.g., "Test Dataset 1")
        # 3. Exact name "test" (lowercase, as used in some tests)
        test_datasets = (
            db.query(Dataset)
            .filter(
                and_(
                    Dataset.name != "Default Dataset",  # NEVER match production dataset
                    Dataset.name != "YOLO Dataset",  # NEVER match YOLO import datasets
                    ~Dataset.name.like(
                        "YOLO Dataset%"
                    ),  # NEVER match YOLO import datasets
                    or_(
                        Dataset.name == "Test Dataset",  # Exact match
                        Dataset.name.like(
                            "Test Dataset%"
                        ),  # Starts with "Test Dataset"
                        Dataset.name == "test",  # Exact lowercase match
                    ),
                )
            )
            .all()
        )

        if not test_datasets:
            print(
                "⚠️  No test datasets found - skipping image cleanup to protect production data"
            )
            return 0

        test_dataset_ids = [ds.id for ds in test_datasets]
        print(
            f"📋 Found {len(test_datasets)} test dataset(s): {[ds.name for ds in test_datasets]}"
        )

        # GLOBAL SAFETY CHECK FIRST: Check ALL images in production datasets BEFORE querying
        # If ANY production images match test patterns, abort entirely - don't even query
        all_production_datasets = (
            db.query(Dataset)
            .filter(
                or_(
                    Dataset.name == "Default Dataset",
                    Dataset.name == "YOLO Dataset",
                    Dataset.name.like("YOLO Dataset%"),
                )
            )
            .all()
        )

        if all_production_datasets:
            production_dataset_ids = [ds.id for ds in all_production_datasets]
            production_images = (
                db.query(Image)
                .filter(Image.dataset_id.in_(production_dataset_ids))
                .all()
            )

            # Define test patterns for checking
            test_patterns_for_check = [
                "test_",
                "ui_test_",
                "concurrent_",
                "persistence_test_",
                "test_workflow_",
            ]
            test_exact_names = ["test.jpg", "ui_test.jpg", "test.png", "ui_test.png"]

            # Check if any production images match test filename patterns
            production_test_matches = []
            for img in production_images:
                matches_pattern = False
                # Check if filename starts with test pattern
                for pattern in test_patterns_for_check:
                    if img.filename.startswith(
                        pattern
                    ) or img.original_filename.startswith(pattern):
                        matches_pattern = True
                        break

                # Check exact test names
                if not matches_pattern:
                    if (
                        img.filename in test_exact_names
                        or img.original_filename in test_exact_names
                    ):
                        matches_pattern = True

                if matches_pattern:
                    dataset = (
                        db.query(Dataset).filter(Dataset.id == img.dataset_id).first()
                    )
                    production_test_matches.append(
                        (img, dataset.name if dataset else "unknown")
                    )

            if production_test_matches:
                print(
                    f"\n❌ CRITICAL: Found {len(production_test_matches)} production image(s) matching test patterns:"
                )
                for img, ds_name in production_test_matches:
                    print(
                        f"  - {img.filename} (original: {img.original_filename}) in '{ds_name}'"
                    )
                print("\n🛡️  ABORTING DELETION to protect production data")
                print("   No images will be deleted")
                return 0

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

        image_extensions = [".jpg", ".jpeg", ".png", ".bmp"]

        # Build filters that require:
        # 1. Image is in a test dataset (CRITICAL SAFETY CHECK)
        # 2. BOTH filename AND original_filename indicate test images
        # An image is a test image if:
        # - It's in a test dataset AND
        # - (filename matches test pattern AND original_filename matches test pattern, OR
        #    filename matches test pattern AND original_filename is exact test name, OR
        #    both filename and original_filename are exact test names)
        filters = []

        # Pattern-based matches (e.g., test_abc123.jpg with test_xyz.jpg)
        for pattern in test_patterns:
            for ext in image_extensions:
                pattern_with_ext = f"{pattern}%{ext}"
                # Both filename and original_filename match the pattern AND image is in test dataset
                filters.append(
                    and_(
                        Image.dataset_id.in_(
                            test_dataset_ids
                        ),  # CRITICAL: Must be in test dataset
                        Image.filename.like(pattern_with_ext),
                        Image.original_filename.like(pattern_with_ext),
                    )
                )

        # Handle cases where filename has UUID but original_filename is exact test name
        # (e.g., filename="test_abc123.jpg", original_filename="test.jpg")
        test_exact_names = ["test.jpg", "ui_test.jpg", "test.png", "ui_test.png"]
        for pattern in test_patterns:
            for ext in image_extensions:
                pattern_with_ext = f"{pattern}%{ext}"
                for exact_name in test_exact_names:
                    # filename matches pattern AND original_filename is exact test name AND in test dataset
                    filters.append(
                        and_(
                            Image.dataset_id.in_(
                                test_dataset_ids
                            ),  # CRITICAL: Must be in test dataset
                            Image.filename.like(pattern_with_ext),
                            Image.original_filename == exact_name,
                        )
                    )

        # Also match exact test filenames (require BOTH to match exactly AND be in test dataset)
        for name in test_exact_names:
            filters.append(
                and_(
                    Image.dataset_id.in_(
                        test_dataset_ids
                    ),  # CRITICAL: Must be in test dataset
                    Image.filename == name,
                    Image.original_filename == name,
                )
            )

        # Safety check: If no filters defined, don't delete anything
        if not filters:
            print("⚠️  WARNING: No test image filters defined - skipping cleanup")
            test_images = []
        else:
            # Match if ANY of the filters match (but each filter requires BOTH fields)
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

        # CRITICAL FINAL CHECK: Before deletion, verify EVERY image is actually in a test dataset
        # This is the absolute last line of defense - filter out any images not in test datasets
        final_test_images = []
        for img in test_images:
            dataset = db.query(Dataset).filter(Dataset.id == img.dataset_id).first()
            if not dataset:
                print(f"  ⚠️  Image {img.id} has no dataset - skipping")
                continue

            # Only include if dataset is actually in our test datasets list
            if dataset.id in test_dataset_ids:
                final_test_images.append(img)
            else:
                print(
                    f"  🛡️  PROTECTING: {img.filename} (dataset '{dataset.name}' not in test datasets)"
                )

        test_images = final_test_images

        # ABSOLUTE SAFETY CHECK: NEVER delete images from "Default Dataset" or "YOLO Dataset"
        # This protects YOLO imports and any other production images
        protected_images = []

        for img in test_images:
            dataset = db.query(Dataset).filter(Dataset.id == img.dataset_id).first()
            if dataset:
                # ABSOLUTE PROTECTION: Never delete from "Default Dataset" or "YOLO Dataset"
                if (
                    dataset.name == "Default Dataset"
                    or dataset.name == "YOLO Dataset"
                    or dataset.name.startswith("YOLO Dataset")
                ):
                    protected_images.append(img)
                    print(
                        f"  🛡️  PROTECTING production image: {img.filename} (in '{dataset.name}')"
                    )
                # Also protect images that are NOT in test datasets
                elif img.dataset_id not in test_dataset_ids:
                    protected_images.append(img)
                    print(
                        f"  🛡️  PROTECTING production image: {img.filename} (in '{dataset.name}', not in test dataset)"
                    )

        # If ANY images were protected, abort deletion to be safe
        if protected_images:
            print(
                f"\n❌ ABORTING DELETION: Found {len(protected_images)} production image(s) that matched test patterns"
            )
            print("   This prevents accidental deletion of production data")
            print("   No images will be deleted")
            return 0

        # Remove protected images from deletion list (should be empty now due to abort above)
        test_images = [img for img in test_images if img not in protected_images]

        # Show what will be deleted
        print(
            f"\n🗑️  Found {len(test_images)} test images in test datasets to clean up"
        )
        if test_images:
            for img in test_images:
                dataset = db.query(Dataset).filter(Dataset.id == img.dataset_id).first()
                dataset_name = dataset.name if dataset else "unknown"
                print(
                    f"  - {img.filename} (original: {img.original_filename}, dataset: '{dataset_name}', ID: {img.id})"
                )
        else:
            print("  ✅ No test images found - all images are production")

        # FINAL FINAL CHECK: Verify each image one more time before deletion
        # Only delete images that are DEFINITELY in test datasets
        images_to_delete = []
        for img in test_images:
            dataset = db.query(Dataset).filter(Dataset.id == img.dataset_id).first()
            if not dataset:
                print(f"  ⚠️  Skipping image {img.id} - no dataset found")
                continue

            # ONLY delete if dataset name is EXACTLY "Test Dataset" or starts with "Test Dataset" or is exactly "test"
            is_test_dataset = (
                dataset.name == "Test Dataset"
                or dataset.name.startswith("Test Dataset")
                or dataset.name == "test"
            )

            # NEVER delete from production datasets
            is_production_dataset = (
                dataset.name == "Default Dataset"
                or dataset.name == "YOLO Dataset"
                or dataset.name.startswith("YOLO Dataset")
            )

            if is_production_dataset:
                print(
                    f"  🛡️  FINAL PROTECTION: {img.filename} in '{dataset.name}' - NOT DELETING"
                )
                continue

            if is_test_dataset:
                images_to_delete.append(img)
            else:
                print(
                    f"  🛡️  PROTECTING: {img.filename} in '{dataset.name}' - not a test dataset"
                )

        test_images = images_to_delete

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

    # Remove test images from filesystem
    # CRITICAL: Only delete files that belong to test images in the database
    # This prevents deleting production files even if they match filename patterns
    db = SessionLocal()
    try:
        from backend.database import Dataset

        # Get list of test image filenames that were actually deleted from database
        # Only delete filesystem files that belong to these test images
        test_image_filenames = set()
        if test_images:
            test_image_filenames = {img.filename for img in test_images}

        # Also check for orphaned test files (not in database) but ONLY if they match test patterns
        # AND we're sure they're not production files
        directories_to_clean = [
            (uploads_images, uploads_thumbnails),
            (
                project_root / "backend" / "uploads" / "images",
                project_root / "backend" / "uploads" / "thumbnails",
            ),
        ]

        for images_dir, thumbnails_dir in directories_to_clean:
            for ext in [".jpg", ".jpeg", ".png", ".bmp"]:
                # Clean main images - ONLY delete files that are in test_image_filenames
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
                        filename = test_file.name
                        # CRITICAL: Only delete if this file belongs to a test image we deleted
                        # OR if it's an orphaned file (not in database) that matches test patterns
                        # BUT first check if it exists in database - if so, protect it
                        existing_image = (
                            db.query(Image).filter(Image.filename == filename).first()
                        )

                        if existing_image:
                            # File exists in database - check if it's a test image
                            dataset = (
                                db.query(Dataset)
                                .filter(Dataset.id == existing_image.dataset_id)
                                .first()
                            )
                            if dataset:
                                # Only delete if it's in a test dataset
                                is_test_dataset = (
                                    dataset.name == "Test Dataset"
                                    or dataset.name.startswith("Test Dataset")
                                    or dataset.name == "test"
                                )
                                is_production_dataset = (
                                    dataset.name == "Default Dataset"
                                    or dataset.name == "YOLO Dataset"
                                    or dataset.name.startswith("YOLO Dataset")
                                )

                                if is_production_dataset:
                                    print(
                                        f"  🛡️  PROTECTING filesystem file: {filename} (in production dataset '{dataset.name}')"
                                    )
                                    continue
                                elif not is_test_dataset:
                                    print(
                                        f"  🛡️  PROTECTING filesystem file: {filename} (in dataset '{dataset.name}', not test dataset)"
                                    )
                                    continue

                        # Safe to delete: either it's a test image we deleted, or it's an orphaned test file
                        if filename in test_image_filenames or not existing_image:
                            try:
                                print(f"Removing filesystem test file: {test_file}")
                                os.remove(test_file)
                                removed_count += 1
                            except OSError as e:
                                print(f"Warning: Could not remove {test_file}: {e}")

                # Clean thumbnails - match test patterns but verify in database first
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
                        filename = test_file.name
                        # Extract the original image filename from thumbnail name
                        # thumb_test_abc123.jpg -> test_abc123.jpg
                        original_filename = filename.replace("thumb_", "")
                        existing_image = (
                            db.query(Image)
                            .filter(Image.filename == original_filename)
                            .first()
                        )

                        if existing_image:
                            dataset = (
                                db.query(Dataset)
                                .filter(Dataset.id == existing_image.dataset_id)
                                .first()
                            )
                            if dataset:
                                is_test_dataset = (
                                    dataset.name == "Test Dataset"
                                    or dataset.name.startswith("Test Dataset")
                                    or dataset.name == "test"
                                )
                                is_production_dataset = (
                                    dataset.name == "Default Dataset"
                                    or dataset.name == "YOLO Dataset"
                                    or dataset.name.startswith("YOLO Dataset")
                                )

                                if is_production_dataset:
                                    print(
                                        f"  🛡️  PROTECTING filesystem thumbnail: {filename} (image in production dataset '{dataset.name}')"
                                    )
                                    continue
                                elif not is_test_dataset:
                                    print(
                                        f"  🛡️  PROTECTING filesystem thumbnail: {filename} (image in dataset '{dataset.name}', not test dataset)"
                                    )
                                    continue

                        # Safe to delete: either it's a test thumbnail we deleted, or it's orphaned
                        if (
                            original_filename in test_image_filenames
                            or not existing_image
                        ):
                            try:
                                print(
                                    f"Removing filesystem test thumbnail: {test_file}"
                                )
                                os.remove(test_file)
                                removed_count += 1
                            except OSError as e:
                                print(f"Warning: Could not remove {test_file}: {e}")
    except Exception as e:
        print(f"⚠️  Warning: Error during filesystem cleanup: {e}")
        import traceback

        traceback.print_exc()
    finally:
        db.close()

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
        from backend.database import SessionLocal, LabelCategory, Annotation, Image
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

        # CRITICAL: Only delete annotations that are on test images AND use test categories
        # We need to identify test images first to avoid deleting production annotations
        from sqlalchemy import and_

        # Get test image IDs using the same logic as cleanup_test_files
        test_image_ids = []
        test_patterns_for_categories = [
            "test_",
            "ui_test_",
            "concurrent_",
            "persistence_test_",
            "test_workflow_",
        ]
        test_exact_names = ["test.jpg", "ui_test.jpg", "test.png", "ui_test.png"]

        image_extensions = [".jpg", ".jpeg", ".png", ".bmp"]
        image_filters = []

        # Build the same filters as cleanup_test_files to identify test images
        for pattern in test_patterns_for_categories:
            for ext in image_extensions:
                pattern_with_ext = f"{pattern}%{ext}"
                image_filters.append(
                    and_(
                        Image.filename.like(pattern_with_ext),
                        Image.original_filename.like(pattern_with_ext),
                    )
                )

        for pattern in test_patterns_for_categories:
            for ext in image_extensions:
                pattern_with_ext = f"{pattern}%{ext}"
                for exact_name in test_exact_names:
                    image_filters.append(
                        and_(
                            Image.filename.like(pattern_with_ext),
                            Image.original_filename == exact_name,
                        )
                    )

        for name in test_exact_names:
            image_filters.append(
                and_(Image.filename == name, Image.original_filename == name)
            )

        if image_filters:
            test_images_for_categories = (
                db.query(Image.id).filter(or_(*image_filters)).all()
            )
            test_image_ids = [img_id[0] for img_id in test_images_for_categories]

        # Only delete annotations that:
        # 1. Use test categories AND
        # 2. Are on test images (not production images)
        if test_image_ids and category_ids:
            annotations_to_delete = (
                db.query(Annotation)
                .filter(
                    and_(
                        Annotation.label_category_id.in_(category_ids),
                        Annotation.image_id.in_(test_image_ids),
                    )
                )
                .all()
            )
            annotation_count = len(annotations_to_delete)
            for ann in annotations_to_delete:
                db.delete(ann)
            print(
                f"  Deleted {annotation_count} annotations on test images using test categories"
            )
        elif category_ids:
            # If no test images found, don't delete any annotations
            print(
                "  ⚠️  No test images found - skipping annotation deletion to protect production data"
            )

        # Delete the categories
        deleted = (
            db.query(LabelCategory).filter(LabelCategory.id.in_(category_ids)).delete()
        )

        db.commit()
        print(f"\n✅ Deleted {deleted} test categories")

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


def cleanup_test_projects():
    """Remove test projects from the database.

    Only removes projects with specific test-related names:
    - "YOLO Test Project" (exact match)
    - "Test Project" (exact match)
    - "Performance Test Project" (exact match)
    - Any project name containing "Test" that was created during tests

    Production projects (e.g., "Default Project", user-created projects)
    are NOT affected by this cleanup.
    """
    try:
        from backend.database import SessionLocal, Project
    except ModuleNotFoundError as e:
        print(f"⚠️  Warning: Cannot import database modules for cleanup: {e}")
        return 0

    db = SessionLocal()
    try:
        # Define test project names - ONLY these specific names will be deleted
        # This ensures production projects are never accidentally removed
        TEST_PROJECT_NAMES = [
            "YOLO Test Project",  # Exact match
            "Test Project",  # Exact match
            "Performance Test Project",  # Exact match
        ]

        # Find test projects using specific test names only
        from sqlalchemy import or_

        filters = [Project.name == name for name in TEST_PROJECT_NAMES]
        test_projects = db.query(Project).filter(or_(*filters)).all()

        # Show all projects before cleanup for verification
        all_projects = db.query(Project).all()
        if all_projects:
            print(f"\n📊 Current projects in database ({len(all_projects)} total):")
            for proj in all_projects:
                is_test = proj in test_projects
                status = (
                    "🗑️  TEST (will be deleted)"
                    if is_test
                    else "✅ PRODUCTION (preserved)"
                )
                print(
                    f"  {status}: {proj.name} (ID: {proj.id}, updated: {proj.updated_at})"
                )

        if not test_projects:
            print(
                "\n✅ No test projects found to clean up - all projects are production"
            )
            return 0

        print(f"\n🗑️  Found {len(test_projects)} test project(s) to clean up:")
        for proj in test_projects:
            print(f"  - {proj.name} (ID: {proj.id})")

        # Get project IDs
        project_ids = [proj.id for proj in test_projects]

        # Delete the projects (cascading deletes will handle datasets, images, etc.)
        deleted = (
            db.query(Project)
            .filter(Project.id.in_(project_ids))
            .delete(synchronize_session=False)
        )

        db.commit()
        print(f"\n✅ Deleted {deleted} test project(s)")

        # Show remaining production projects
        remaining_projects = db.query(Project).all()
        if remaining_projects:
            print(f"\n✅ Preserved {len(remaining_projects)} production project(s):")
            for proj in remaining_projects:
                print(f"  - {proj.name} (ID: {proj.id})")
        else:
            print("\nℹ️  No projects remain in database")

        return deleted
    except Exception as e:
        db.rollback()
        print(f"❌ Error cleaning test projects: {e}")
        import traceback

        traceback.print_exc()
        raise
    finally:
        db.close()


def cleanup_all():
    """Clean up all test artifacts.

    Only deletes images where BOTH filename AND original_filename match test patterns.
    This ensures production images are never accidentally deleted.
    """
    print("🧹 Cleaning up test artifacts...")

    try:
        files_removed = cleanup_test_files()
        categories_removed = cleanup_test_categories()
        projects_removed = cleanup_test_projects()

        print(f"✅ Removed {files_removed} test files")
        print(f"✅ Removed {categories_removed} test categories")
        print(f"✅ Removed {projects_removed} test projects")

        return files_removed + categories_removed + projects_removed
    except Exception as e:
        print(f"⚠️  Warning: Cleanup encountered errors: {e}")
        return 0


if __name__ == "__main__":
    cleanup_all()
