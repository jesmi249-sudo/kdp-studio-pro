"""
Test script to verify the PDF engine and all core modules work correctly.
Creates a dummy image and generates a full coloring book PDF.
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from pathlib import Path
from PIL import Image, ImageDraw

# Test 1: Import core modules
print("=" * 60)
print("TEST 1: Importing core modules...")
try:
    from core.logger import get_logger
    from core.pdf_engine import PDFEngine, TRIM_SIZES
    from core.project_io import ProjectIO
    print("  ✓ All core modules imported successfully")
except ImportError as e:
    print(f"  ✗ Import failed: {e}")
    sys.exit(1)

# Test 2: Logger
print("\nTEST 2: Testing logger...")
logger = get_logger("test")
logger.info("Test log message")
print("  ✓ Logger working")

# Test 3: Create dummy test images
print("\nTEST 3: Creating test images...")
test_dir = Path(__file__).parent / "data" / "test_images"
test_dir.mkdir(parents=True, exist_ok=True)

test_images = []
for i in range(5):
    img = Image.new("RGB", (800, 1000), "white")
    draw = ImageDraw.Draw(img)
    # Draw some shapes to simulate line art
    draw.rectangle([50, 50, 750, 950], outline="black", width=3)
    draw.ellipse([100, 100, 700, 700], outline="black", width=2)
    draw.line([100, 500, 700, 500], fill="black", width=2)
    draw.text((300, 450), f"Page {i+1}", fill="black")
    
    img_path = test_dir / f"test_page_{i+1}.png"
    img.save(str(img_path))
    test_images.append(str(img_path))

print(f"  ✓ Created {len(test_images)} test images")

# Test 4: Generate PDF with all page types
print("\nTEST 4: Generating PDF with PDFEngine...")
output_path = Path(__file__).parent / "data" / "test_output.pdf"

progress_log = []

def progress_callback(current, total, message):
    progress_log.append((current, total, message))
    pct = int(current / total * 100) if total > 0 else 0
    print(f"  [{pct:3d}%] {message}")

engine = PDFEngine(
    output_path=str(output_path),
    title="My Amazing Coloring Book",
    subtitle="A Fun Activity Book for Kids",
    author="Test Author",
    trim_size="8.5 x 11 inches (Letter)",
    use_bleed=True,
    images=test_images,
    num_pages=None,
    progress_callback=progress_callback,
)

result = engine.generate()
print(f"\n  ✓ PDF generated: {result}")
print(f"  ✓ File size: {output_path.stat().st_size / 1024:.1f} KB")
print(f"  ✓ Progress callbacks received: {len(progress_log)}")

# Test 5: Verify PDF structure
print("\nTEST 5: Verifying PDF...")
try:
    from PyPDF2 import PdfReader
    reader = PdfReader(str(output_path))
    num_pdf_pages = len(reader.pages)
    expected_pages = 5 + 4  # 5 coloring + title + copyright + belongs_to + thank_you
    print(f"  ✓ PDF has {num_pdf_pages} pages (expected {expected_pages})")
    assert num_pdf_pages == expected_pages, f"Expected {expected_pages} pages, got {num_pdf_pages}"
except ImportError:
    print("  ⚠ PyPDF2 not installed, skipping page count verification")
    print(f"  ✓ PDF file exists and is non-empty ({output_path.stat().st_size} bytes)")

# Test 6: Test ProjectIO
print("\nTEST 6: Testing ProjectIO...")
data_dir = Path(__file__).parent / "data"
pio = ProjectIO(data_dir)

project = ProjectIO.build_project_dict(
    name="Test Project",
    generator_data=ProjectIO.build_generator_data(
        title="Test Book",
        subtitle="Test Subtitle",
        author="Test Author",
        theme="Animals",
        images=test_images,
    ),
    description="A test project",
)

projects = pio.load_all_projects()
projects = pio.save_project(project, projects)
print(f"  ✓ Project saved (total: {len(projects)})")

# Verify we can find it
found = pio.get_project_by_id(project["id"], projects)
assert found is not None, "Project not found after save"
print(f"  ✓ Project retrieved by ID: {found['name']}")

# Test 7: Test all trim sizes
print("\nTEST 7: Testing all trim sizes...")
for size_name in TRIM_SIZES:
    small_output = data_dir / f"test_{size_name.replace(' ', '_').replace('.', '')}.pdf"
    eng = PDFEngine(
        output_path=str(small_output),
        title="Size Test",
        trim_size=size_name,
        use_bleed=True,
        images=test_images[:1],
    )
    eng.generate()
    assert small_output.exists() and small_output.stat().st_size > 0
    small_output.unlink()  # Clean up
print(f"  ✓ All {len(TRIM_SIZES)} trim sizes generate valid PDFs")

# Cleanup
print("\n" + "=" * 60)
print("ALL TESTS PASSED ✓")
print("=" * 60)
