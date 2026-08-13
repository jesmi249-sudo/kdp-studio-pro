import os
import sys
import glob
import re

def test_pdf_final_verification():
    print("Phase 8G.1: Final PDF Verification & Production Handoff")
    
    export_pkg_dir = os.path.join(os.path.dirname(__file__), "test_real_24_page", "export_pkg")
    
    if not os.path.exists(export_pkg_dir):
        print("ERROR: export_pkg directory not found. Please run Phase 8G test first.")
        sys.exit(1)
        
    # Find the most recently generated package
    packages = sorted(glob.glob(os.path.join(export_pkg_dir, "KDP_Package_*")))
    if not packages:
        print("ERROR: No KDP packages found in export_pkg.")
        sys.exit(1)
        
    latest_package = packages[-1]
    print(f"Inspecting package: {os.path.basename(latest_package)}")
    
    interior_pdf_path = None
    interior_dir = os.path.join(latest_package, "Interior")
    if os.path.exists(interior_dir):
        pdfs = glob.glob(os.path.join(interior_dir, "*.pdf"))
        if pdfs:
            interior_pdf_path = pdfs[0]
            
    if not interior_pdf_path:
        print("ERROR: Interior PDF not found in the package.")
        sys.exit(1)
        
    print(f"Found Interior PDF: {os.path.basename(interior_pdf_path)}")
    
    # 1. Verify exists, size > 0, readable
    assert os.path.exists(interior_pdf_path), "PDF does not exist"
    size_bytes = os.path.getsize(interior_pdf_path)
    assert size_bytes > 0, "PDF is empty"
    print(f"PASS: PDF exists and is readable (Size: {size_bytes / (1024*1024):.2f} MB)")
    
    # 2. Verify Page Count
    page_count = -1
    
    try:
        import pypdf
        with open(interior_pdf_path, "rb") as f:
            reader = pypdf.PdfReader(f)
            page_count = len(reader.pages)
        print(f"Method: Used 'pypdf' library to count pages.")
    except ImportError:
        try:
            import PyPDF2
            with open(interior_pdf_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                page_count = len(reader.pages)
            print(f"Method: Used 'PyPDF2' library to count pages.")
        except ImportError:
            # Fallback for PIL-generated PDFs (they typically use uncompressed objects for /Type /Page)
            print("Method: No external PDF library found. Using binary regex fallback.")
            with open(interior_pdf_path, "rb") as f:
                content = f.read()
                # PIL typically formats page dictionaries with /Type /Page
                matches = re.findall(b"/Type\\s*/Page[^s]", content)
                page_count = len(matches)
                
    if page_count == -1:
        print("FAILED: Could not determine page count.")
        sys.exit(1)
        
    print(f"Result: PDF Page Count is {page_count}")
    
    if page_count != 24:
        print(f"FAILED: Expected exactly 24 pages, found {page_count}.")
        sys.exit(1)
        
    print("PASS: PDF Page count is exactly 24.")
    
    # 3. Verify Manifest and Validation Report
    manifest_path = os.path.join(latest_package, "Metadata", "manifest.json")
    assert os.path.exists(manifest_path), "manifest.json is missing."
    print("PASS: manifest.json verified.")
    
    report_path = os.path.join(latest_package, "Reports", "Validation_Report.txt")
    assert os.path.exists(report_path), "Validation_Report.txt is missing."
    print("PASS: Validation_Report.txt verified.")
    
    print("\nALL PHASE 8G.1 PDF VERIFICATION TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_pdf_final_verification()
