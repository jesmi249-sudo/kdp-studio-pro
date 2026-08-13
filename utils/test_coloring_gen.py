import os
import sys
from PIL import Image

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_tests():
    print("Testing ColoringGenerator core logic...")
    from generators.coloring_generator import ColoringGenerator
    
    gen = ColoringGenerator()
    
    # Create a dummy image using PIL
    test_img_path = "test_input.jpg"
    img = Image.new('RGB', (800, 600), color=(150, 150, 150))
    img.save(test_img_path)
    
    # 1. Test Load
    if not gen.load_image(test_img_path):
        print("FAILED: Image load")
        sys.exit(1)
    print("PASS: Image load")
        
    # 2. Test Processing Pipeline
    success = gen.process_image(
        brightness=10, 
        contrast=1.2, 
        blur_ksize=5, 
        threshold_block=15, 
        threshold_c=2, 
        morph_iters=1
    )
    if not success:
        print("FAILED: Image processing")
        sys.exit(1)
    print("PASS: Image processing")
        
    # 3. Test Export (PNG)
    png_path = "test_output.png"
    if not gen.export(png_path, "PNG"):
        print("FAILED: PNG Export")
        sys.exit(1)
    print("PASS: PNG Export")
        
    # 4. Test Export (PDF)
    pdf_path = "test_output.pdf"
    if not gen.export(pdf_path, "PDF", "8.5 x 11"):
        print("FAILED: PDF Export")
        sys.exit(1)
    print("PASS: PDF Export")
    
    # Cleanup
    for f in [test_img_path, png_path, pdf_path]:
        if os.path.exists(f):
            os.remove(f)
            
    print("ALL TESTS PASSED!")

if __name__ == "__main__":
    run_tests()
