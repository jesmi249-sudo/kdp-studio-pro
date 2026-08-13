import cv2
import numpy as np
from PIL import Image
import os
from reportlab.pdfgen import canvas
from core.logger import get_logger

logger = get_logger(__name__)

class ColoringGenerator:
    """Core logic for converting images to coloring book pages."""
    
    def __init__(self):
        self.original_image = None
        self.processed_image = None
        
        # Default Parameters
        self.brightness = 0
        self.contrast = 1.0
        self.blur_ksize = 5
        self.threshold_block = 11
        self.threshold_c = 2
        self.morph_iters = 1

    def load_image(self, file_path: str) -> bool:
        """Loads an image using OpenCV."""
        try:
            # imread reads as BGR, we store the original
            img = cv2.imread(file_path)
            if img is None:
                logger.error(f"Could not load image: {file_path}")
                return False
            self.original_image = img
            return True
        except Exception as e:
            logger.error(f"Error loading image: {e}")
            return False

    def process_image(self, brightness, contrast, blur_ksize, threshold_block, threshold_c, morph_iters):
        """Applies the OpenCV pipeline to generate a coloring page."""
        if self.original_image is None:
            return None
            
        try:
            img = self.original_image.copy()
            
            # 1. Brightness & Contrast
            img = cv2.convertScaleAbs(img, alpha=contrast, beta=brightness)
            
            # 2. Grayscale
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            
            # 3. Gaussian Blur (noise removal)
            # Ensure blur_ksize is odd and >= 3
            blur_ksize = max(3, blur_ksize)
            if blur_ksize % 2 == 0:
                blur_ksize += 1
            blurred = cv2.GaussianBlur(gray, (blur_ksize, blur_ksize), 0)
            
            # 4. Adaptive Threshold (Line Extraction)
            # Ensure block size is odd and >= 3
            threshold_block = max(3, threshold_block)
            if threshold_block % 2 == 0:
                threshold_block += 1
            thresh = cv2.adaptiveThreshold(
                blurred, 255, 
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                cv2.THRESH_BINARY, 
                threshold_block, 
                threshold_c
            )
            
            # 5. Morphology (Line thickening/refining)
            if morph_iters > 0:
                kernel = np.ones((3,3), np.uint8)
                # Erode the binary image (which means thickening the black lines since white is 255)
                thresh = cv2.erode(thresh, kernel, iterations=morph_iters)
                
            self.processed_image = thresh
            return True
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return False

    def get_processed_pil_image(self):
        """Returns the processed image as a PIL Image."""
        if self.processed_image is None:
            return None
        # Convert grayscale numpy array to PIL Image
        return Image.fromarray(self.processed_image)

    def export(self, path: str, fmt: str, page_size: str = "8.5x11"):
        """Exports the processed image to the given format."""
        if self.processed_image is None:
            return False
            
        try:
            pil_img = self.get_processed_pil_image()
            
            if fmt.lower() in ['png', 'jpg', 'jpeg']:
                pil_img.convert('RGB').save(path)
                return True
                
            elif fmt.lower() == 'pdf':
                return self._export_pdf(path, pil_img, page_size)
                
        except Exception as e:
            logger.error(f"Failed to export image: {e}")
            return False
            
    def _export_pdf(self, path: str, pil_img, page_size: str):
        """Exports to PDF using ReportLab with specific page sizes and margins."""
        # Page size mappings (inches)
        sizes = {
            "8.5 x 11": (8.5, 11.0),
            "A4": (8.27, 11.69),
            "6 x 9": (6.0, 9.0)
        }
        
        # 1 inch = 72 points in reportlab
        w_in, h_in = sizes.get(page_size, (8.5, 11.0))
        w_pt = w_in * 72
        h_pt = h_in * 72
        
        c = canvas.Canvas(path, pagesize=(w_pt, h_pt))
        
        # Calculate margins (0.375" minimum safe margin)
        margin_pt = 0.375 * 72
        
        # Available drawing area
        avail_w = w_pt - (2 * margin_pt)
        avail_h = h_pt - (2 * margin_pt)
        
        # Calculate image aspect ratio to fit within available area
        img_w, img_h = pil_img.size
        aspect = img_w / img_h
        
        draw_w = avail_w
        draw_h = avail_w / aspect
        
        if draw_h > avail_h:
            draw_h = avail_h
            draw_w = avail_h * aspect
            
        # Center on page
        x = (w_pt - draw_w) / 2
        y = (h_pt - draw_h) / 2
        
        # Save temporary image for reportlab to read
        temp_img = "temp_pdf_export_img.png"
        pil_img.save(temp_img)
        
        c.drawImage(temp_img, x, y, width=draw_w, height=draw_h)
        c.showPage()
        c.save()
        
        if os.path.exists(temp_img):
            os.remove(temp_img)
            
        return True
