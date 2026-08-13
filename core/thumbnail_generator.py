import os
import hashlib
from PIL import Image
from core.logger import get_logger

logger = get_logger(__name__)

CACHE_DIR = os.path.join(".cache", "thumbnails")
os.makedirs(CACHE_DIR, exist_ok=True)

try:
    import cairosvg
    HAS_CAIROSVG = True
except Exception as e:
    logger.warning(f"cairosvg not available: {e}")
    HAS_CAIROSVG = False

try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False

class ThumbnailGenerator:
    @staticmethod
    def _get_cache_path(file_path: str, size: tuple) -> str:
        """Generate a unique cache path based on file path and modification time."""
        if not os.path.exists(file_path):
            return ""
        
        mtime = os.path.getmtime(file_path)
        unique_string = f"{file_path}_{mtime}_{size[0]}x{size[1]}"
        hash_str = hashlib.md5(unique_string.encode()).hexdigest()
        
        return os.path.join(CACHE_DIR, f"{hash_str}.png")

    @staticmethod
    def generate(file_path: str, size=(150, 150)) -> str:
        """
        Generates a thumbnail for the given file, utilizing cache.
        Returns the path to the thumbnail PNG.
        """
        if not os.path.exists(file_path):
            return ""

        cache_path = ThumbnailGenerator._get_cache_path(file_path, size)
        if os.path.exists(cache_path):
            return cache_path
            
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp']:
                return ThumbnailGenerator._generate_image(file_path, cache_path, size)
            elif ext == '.svg':
                return ThumbnailGenerator._generate_svg(file_path, cache_path, size)
            elif ext == '.pdf':
                return ThumbnailGenerator._generate_pdf(file_path, cache_path, size)
            else:
                return ThumbnailGenerator._generate_placeholder(ext, cache_path, size)
        except Exception as e:
            logger.error(f"Thumbnail generation failed for {file_path}: {e}")
            return ThumbnailGenerator._generate_placeholder(ext, cache_path, size)

    @staticmethod
    def _generate_image(file_path, cache_path, size):
        with Image.open(file_path) as img:
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(cache_path, format="PNG")
        return cache_path

    @staticmethod
    def _generate_svg(file_path, cache_path, size):
        if HAS_CAIROSVG:
            # Generate a temporary PNG, then resize with Pillow
            temp_png = cache_path + ".tmp.png"
            cairosvg.svg2png(url=file_path, write_to=temp_png, output_width=size[0], output_height=size[1])
            with Image.open(temp_png) as img:
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(cache_path, format="PNG")
            os.remove(temp_png)
            return cache_path
        else:
            return ThumbnailGenerator._generate_placeholder(".svg", cache_path, size)

    @staticmethod
    def _generate_pdf(file_path, cache_path, size):
        if HAS_PYMUPDF:
            doc = fitz.open(file_path)
            page = doc.load_page(0)
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            
            # Save raw image
            temp_img = cache_path + ".tmp.png"
            pix.save(temp_img)
            doc.close()
            
            with Image.open(temp_img) as img:
                img.thumbnail(size, Image.Resampling.LANCZOS)
                img.save(cache_path, format="PNG")
            os.remove(temp_img)
            return cache_path
        else:
            return ThumbnailGenerator._generate_placeholder(".pdf", cache_path, size)

    @staticmethod
    def _generate_placeholder(ext, cache_path, size):
        """Generates a simple colored box with the extension name as a fallback."""
        img = Image.new('RGB', size, color=(200, 200, 200))
        # Basic drawing, no custom fonts needed
        from PIL import ImageDraw
        d = ImageDraw.Draw(img)
        d.text((size[0]/2 - 15, size[1]/2 - 10), ext.upper(), fill=(50, 50, 50))
        img.save(cache_path, format="PNG")
        return cache_path
