import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_tests():
    print("Testing Interior Generator...")
    from generators.interior_generator import InteriorGenerator
    
    gen = InteriorGenerator()
    
    pdf_path = "test_notebook.pdf"
    margins = {'top': 0.5, 'bottom': 0.5, 'inside': 0.5, 'outside': 0.5}
    
    # Generate 10-page College Ruled notebook
    success = gen.generate_pdf(
        output_path=pdf_path,
        size="6 x 9",
        orientation="Portrait",
        margins=margins,
        bleed=True,
        page_numbers="Bottom Center",
        template="College Ruled",
        page_count=10
    )
    
    if not success or not os.path.exists(pdf_path):
        print("FAILED: PDF Generation")
        sys.exit(1)
        
    print("PASS: PDF Generation")
    os.remove(pdf_path)
    
    # Test importing the UI
    try:
        from ui.views.interior_view import InteriorView
        print("PASS: UI Imports")
    except Exception as e:
        print(f"FAILED: UI Imports ({e})")
        sys.exit(1)
        
    print("ALL TESTS PASSED!")

if __name__ == "__main__":
    run_tests()
