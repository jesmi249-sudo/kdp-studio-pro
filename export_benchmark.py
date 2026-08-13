import os
import time
import tracemalloc
import sys
from uuid import uuid4

# Import codebase models and exporters
from book_builder.models.book import BookProject
from book_builder.models.page import Page
from book_builder.models.export import ExportProfile
from exporters.export_engine import ExportEngine

def run_benchmark():
    print("====================================================")
    print("      KDP STUDIO PRO - EXPORT ENGINE BENCHMARK      ")
    print("====================================================")
    
    # 1. Initialize memory tracer
    tracemalloc.start()
    
    # 2. Setup mock 500-page notebook project
    print("\n[1/4] Constructing mock 500-page book project...")
    start_setup = time.time()
    
    project = BookProject(
        name="Benchmark Large Notebook",
        book_type="Notebook",
        trim_width_in=6.0,
        trim_height_in=9.0,
        has_bleed=True
    )
    
    # 6"x9" + bleed -> 6.125" x 9.25" -> 441.0 pt x 666.0 pt
    w_pt = 441.0
    h_pt = 666.0
    
    # Populate with 500 pages containing ruled lines (5 shapes per page)
    for p_num in range(1, 501):
        page = Page(
            page_number=p_num,
            width_pt=w_pt,
            height_pt=h_pt,
            margin_top_pt=36.0,
            margin_bottom_pt=36.0,
            margin_inside_pt=54.0,
            margin_outside_pt=36.0
        )
        # Add 5 ruled lines to simulate rendering load
        for i in range(5):
            y_pos = 100.0 + (i * 100.0)
            page.vector_objects.append({
                "shape_type": "line",
                "geometry": {"x": 54.0, "y": y_pos, "width": 351.0, "height": 0.0},
                "properties": {"stroke_color": "#D3D3D3", "stroke_width": 0.75}
            })
        project.pages.append(page)
        
    duration_setup = time.time() - start_setup
    print(f"[*] Setup completed in {duration_setup:.3f} seconds.")
    
    # 3. Setup export profile (DPI 150 to keep execution times reasonable for benchmark)
    output_dir = "benchmark_output"
    os.makedirs(output_dir, exist_ok=True)
    
    profile = ExportProfile(
        profile_name="Benchmark High Quality",
        export_format="KDP_PDF",
        color_space="RGB",
        dpi=150,
        compression_level=0.75,
        custom_options={
            "output_folder": output_dir,
            "naming_template": "benchmark_large_interior"
        }
    )
    
    engine = ExportEngine()
    
    # 4. Measure PDF generation time
    print("\n[2/4] Executing PDF Compilation (500 pages @ 150 DPI)...")
    start_pdf = time.time()
    
    pdf_path = engine.compile_pdf(project, profile)
    
    duration_pdf = time.time() - start_pdf
    pdf_size_mb = os.path.getsize(pdf_path) / (1024 * 1024)
    
    print("[*] PDF Compilation Complete.")
    print(f"  - Target file: {pdf_path}")
    print(f"  - Output size: {pdf_size_mb:.2f} MB")
    print(f"  - Elapsed time: {duration_pdf:.2f} seconds")
    print(f"  - Compilation speed: {500.0 / duration_pdf:.2f} pages/sec")
    
    # 5. Measure Image rendering throughput (on a subset of 50 pages)
    print("\n[3/4] Measuring Image Rendering Throughput (50 pages @ 300 DPI)...")
    profile.export_format = "PNG"
    profile.dpi = 300
    profile.custom_options["naming_template"] = "benchmark_page"
    
    # Slice first 50 pages
    subset_project = BookProject(name="Subset", book_type="Notebook")
    subset_project.pages = project.pages[:50]
    
    start_img = time.time()
    img_files = engine.export_pages_to_images(subset_project, profile)
    duration_img = time.time() - start_img
    
    print("[*] Image Rendering Complete.")
    print(f"  - Rendered pages: {len(img_files)} files")
    print(f"  - Elapsed time: {duration_img:.2f} seconds")
    print(f"  - Rendering throughput: {50.0 / duration_img:.2f} pages/sec")
    
    # 6. Read peak memory allocation
    current_mem, peak_mem = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    
    print("\n[4/4] Analyzing Memory Footprint & Resource Usage...")
    print(f"  - Current memory: {current_mem / (1024 * 1024):.2f} MB")
    print(f"  - Peak memory usage: {peak_mem / (1024 * 1024):.2f} MB")
    
    # Clean up output files
    print("\nCleaning up benchmark temporary output files...")
    if os.path.exists(output_dir):
        import shutil
        shutil.rmtree(output_dir)
    print("[*] Cleanup completed.")
    
    print("\n====================================================")
    print("                  BENCHMARK PASSED                  ")
    print("====================================================")

if __name__ == "__main__":
    run_benchmark()
