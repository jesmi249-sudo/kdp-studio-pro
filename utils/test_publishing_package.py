import os
import sys
import shutil

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

class DummyExportEngine:
    def compile_pdf(self, project, profile):
        out = os.path.join(profile.custom_options["output_folder"], "interior.pdf")
        with open(out, "w") as f:
            f.write("DUMMY INTERIOR PDF")
        return out
        
    def compile_cover(self, project, profile):
        out = os.path.join(profile.custom_options["output_folder"], "cover.pdf")
        with open(out, "w") as f:
            f.write("DUMMY COVER PDF")
        return out

def test_publishing_package():
    print("Testing Phase 7J: KDP Publishing Package Workflow...")
    
    from book_builder.models.book import BookProject
    from book_builder.models.page import Page
    from book_builder.models.export import ExportProfile
    from core.publishing_package_service import PublishingPackageService
    
    # 1. Setup Service with Dummy Exporter
    dummy_exporter = DummyExportEngine()
    package_service = PublishingPackageService(export_engine=dummy_exporter)
    
    # 2. Setup a valid mock project (24 pages, matching dimensions)
    project = BookProject(name="Test Book", trim_width_in=8.5, trim_height_in=11.0)
    for i in range(24):
        p = Page(page_number=i+1, width_pt=8.5*72, height_pt=11.0*72)
        p.text_blocks.append({"text": "dummy content", "geometry": {"x": 100, "y": 100, "width": 100, "height": 100}})
        project.pages.append(p)
        
    # Mock some metadata
    project.metadata.title = "My Coloring Book"
    project.metadata.author = "Jane Doe"
        
    # 3. Test Readiness Status (Should be READY)
    readiness = package_service.check_package_readiness(project)
    if readiness["status"] != "READY":
        print(f"FAILED: Expected READY, got {readiness['status']}. Errors: {readiness['errors_count']}")
        sys.exit(1)
    print("PASS: Valid project returns READY status.")
    
    # 4. Test BLOCKED Status (simulate an error by giving odd page count < 24)
    project_err = BookProject(name="Bad Book", trim_width_in=8.5, trim_height_in=11.0)
    project_err.pages.append(Page(page_number=1, width_pt=100, height_pt=100))
    readiness_err = package_service.check_package_readiness(project_err)
    if readiness_err["status"] != "BLOCKED":
        print(f"FAILED: Expected BLOCKED, got {readiness_err['status']}")
        sys.exit(1)
    print("PASS: Invalid project returns BLOCKED status.")
    
    # 5. Build Publishing Package
    profile = ExportProfile(profile_name="KDP Package Profile", export_format="KDP_PDF", color_space="CMYK", dpi=300)
    test_output_dir = os.path.join(os.path.dirname(__file__), "test_kdp_export")
    if not os.path.exists(test_output_dir):
        os.makedirs(test_output_dir)
        
    try:
        package_path = package_service.build_publishing_package(project, profile, test_output_dir)
        
        # 6. Verify Directory Structure
        expected_dirs = ["Interior", "Cover", "Metadata", "Reports"]
        for d in expected_dirs:
            if not os.path.exists(os.path.join(package_path, d)):
                print(f"FAILED: Missing directory {d} in package.")
                sys.exit(1)
        print("PASS: Package directory structure generated correctly.")
        
        # 7. Verify Manifest
        manifest_file = os.path.join(package_path, "Metadata", "manifest.json")
        if not os.path.exists(manifest_file):
            print("FAILED: manifest.json not found.")
            sys.exit(1)
            
        import json
        with open(manifest_file, "r") as f:
            manifest = json.load(f)
            if manifest["book_title"] != "My Coloring Book":
                print("FAILED: Manifest title mismatch.")
                sys.exit(1)
        print("PASS: Manifest generated with correct metadata.")
        
        # 8. Verify Validation Report
        report_file = os.path.join(package_path, "Reports", "Validation_Report.txt")
        if not os.path.exists(report_file):
            print("FAILED: Validation_Report.txt not found.")
            sys.exit(1)
            
        with open(report_file, "r") as f:
            report_text = f.read()
            if "PASS: No issues detected" not in report_text:
                print("FAILED: Report does not reflect PASS state.")
                sys.exit(1)
        print("PASS: Validation Report generated correctly.")
        
        # 9. Verify interior and cover PDFs were "exported"
        if not os.path.exists(os.path.join(package_path, "Interior", "interior.pdf")):
            print("FAILED: Interior PDF not found.")
            sys.exit(1)
        if not os.path.exists(os.path.join(package_path, "Cover", "cover.pdf")):
            print("FAILED: Cover PDF not found.")
            sys.exit(1)
            
        print("PASS: Dummy PDF generation succeeded without destructive overwrites.")
        
    finally:
        # Cleanup
        if os.path.exists(test_output_dir):
            shutil.rmtree(test_output_dir)

    print("\nALL PHASE 7J TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    test_publishing_package()
