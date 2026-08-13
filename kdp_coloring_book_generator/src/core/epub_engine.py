"""
EPUB Generation Engine for KDP Coloring Book Generator.
Builds Kindle-compliant EPUB files offline using EbookLib.
Supports Text eBook Mode and Image eBook Mode.
"""

import os
import uuid
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Optional
import shutil

try:
    from ebooklib import epub
    EBOOKLIB_AVAILABLE = True
except ImportError:
    EBOOKLIB_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import cairosvg
    SVG_AVAILABLE = True
except ImportError:
    SVG_AVAILABLE = False

from .logger import get_logger

logger = get_logger("epub_engine")


class EpubEngine:
    def __init__(self, metadata: Dict[str, Any], items: List[Dict[str, Any]], output_path: str, mode: str = "text"):
        """
        metadata: title, subtitle, author, language, publisher, copyright, description, isbn
        items: list of chapters/pages.
          For text mode: {"title": "Chap 1", "content": "<p>html...</p>"}
          For image mode: {"title": "Optional", "description": "Optional", "image_path": "path"}
        mode: "text" or "image"
        """
        self.metadata = metadata
        self.items = items
        self.output_path = output_path
        self.mode = mode
        
        if EBOOKLIB_AVAILABLE:
            self.book = epub.EpubBook()
        self._temp_files = []

    def _cleanup(self):
        for f in self._temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except Exception:
                pass

    def _optimize_image(self, original_path: str, max_size: int = 1600) -> str:
        """Compress and resize image for EPUB. Returns path to new optimized image."""
        if not PIL_AVAILABLE:
            return original_path

        ext = Path(original_path).suffix.lower()
        if ext == ".svg":
            if not SVG_AVAILABLE:
                logger.warning("SVG provided but cairosvg not available.")
                return original_path
            png_path = os.path.join(tempfile.gettempdir(), f"opt_{uuid.uuid4().hex}.png")
            self._temp_files.append(png_path)
            try:
                cairosvg.svg2png(url=original_path, write_to=png_path, output_width=max_size)
                return png_path
            except Exception as e:
                logger.error(f"Failed to rasterize SVG: {e}")
                return original_path

        try:
            img = Image.open(original_path)
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            
            # Auto resize if too large
            if img.width > max_size or img.height > max_size:
                img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
            
            # Save as optimized JPG (convert RGBA to RGB for JPEG)
            if img.mode == "RGBA":
                bg = Image.new("RGB", img.size, (255, 255, 255))
                bg.paste(img, mask=img.split()[3])
                img = bg
            
            opt_path = os.path.join(tempfile.gettempdir(), f"opt_{uuid.uuid4().hex}.jpg")
            self._temp_files.append(opt_path)
            img.save(opt_path, "JPEG", quality=85, optimize=True)
            return opt_path
        except Exception as e:
            logger.error(f"Failed to optimize image {original_path}: {e}")
            return original_path

    def _add_metadata(self):
        self.book.set_identifier(self.metadata.get("isbn") or str(uuid.uuid4()))
        self.book.set_title(self.metadata.get("title", "Untitled"))
        self.book.set_language(self.metadata.get("language", "en"))
        if self.metadata.get("author"):
            self.book.add_author(self.metadata.get("author"))
        if self.metadata.get("description"):
            self.book.add_metadata("DC", "description", self.metadata.get("description"))
        if self.metadata.get("publisher"):
            self.book.add_metadata("DC", "publisher", self.metadata.get("publisher"))

    def _create_css(self):
        style = '''
            body { font-family: sans-serif; margin: 0; padding: 0; }
            .title-page { text-align: center; margin-top: 20%; }
            .title { font-size: 2em; font-weight: bold; margin-bottom: 0.5em; }
            .subtitle { font-size: 1.5em; color: #555; margin-bottom: 2em; }
            .author { font-size: 1.2em; }
            .copyright-page { font-size: 0.9em; text-align: center; margin-top: 10%; }
            .chapter-title { font-size: 1.5em; font-weight: bold; margin-bottom: 1em; text-align: center; }
            .image-container { text-align: center; margin: 1em 0; width: 100%; height: auto; }
            .image-container img { max-width: 100%; height: auto; page-break-inside: avoid; }
            .image-caption { text-align: center; font-style: italic; margin-top: 0.5em; }
            p { line-height: 1.5; margin-bottom: 1em; }
        '''
        css = epub.EpubItem(uid="style_nav", file_name="style/nav.css", media_type="text/css", content=style)
        self.book.add_item(css)
        return css

    def _create_front_matter(self, css_item):
        front_matter = []
        
        # Title Page
        title_html = f'''
        <div class="title-page">
            <div class="title">{self.metadata.get("title", "")}</div>
            <div class="subtitle">{self.metadata.get("subtitle", "")}</div>
            <div class="author">{self.metadata.get("author", "")}</div>
        </div>
        '''
        title_page = epub.EpubHtml(title="Title Page", file_name="title.xhtml")
        title_page.set_content(title_html)
        title_page.add_item(css_item)
        self.book.add_item(title_page)
        front_matter.append(title_page)

        # Copyright Page
        if self.metadata.get("copyright"):
            copy_html = f'''
            <div class="copyright-page">
                <h3>Copyright</h3>
                <p>{self.metadata.get("copyright", "")}</p>
                <p>Publisher: {self.metadata.get("publisher", "")}</p>
                <p>ISBN: {self.metadata.get("isbn", "")}</p>
            </div>
            '''
            copy_page = epub.EpubHtml(title="Copyright", file_name="copyright.xhtml")
            copy_page.set_content(copy_html)
            copy_page.add_item(css_item)
            self.book.add_item(copy_page)
            front_matter.append(copy_page)
            
        return front_matter

    def _create_back_matter(self, css_item):
        back_matter = []
        
        # About the Author
        about = self.metadata.get("about_author", "")
        if about:
            html = f'''
            <div>
                <h2 class="chapter-title">About the Author</h2>
                <p>{about.replace(chr(10), "<br/>")}</p>
            </div>
            '''
            page = epub.EpubHtml(title="About the Author", file_name="about.xhtml")
            page.set_content(html)
            page.add_item(css_item)
            self.book.add_item(page)
            back_matter.append(page)

        # Thank You
        thanks = self.metadata.get("thank_you", "")
        if thanks:
            html = f'''
            <div class="title-page">
                <h2 class="chapter-title">Thank You</h2>
                <p>{thanks.replace(chr(10), "<br/>")}</p>
            </div>
            '''
            page = epub.EpubHtml(title="Thank You", file_name="thanks.xhtml")
            page.set_content(html)
            page.add_item(css_item)
            self.book.add_item(page)
            back_matter.append(page)
            
        return back_matter

    def build(self) -> bool:
        if not EBOOKLIB_AVAILABLE:
            raise RuntimeError("EbookLib is required to generate EPUB files.")

        try:
            self._add_metadata()
            css_item = self._create_css()
            
            spine = ['nav']
            toc = []
            
            # Front matter
            front_matter = self._create_front_matter(css_item)
            for page in front_matter:
                spine.append(page)
            
            # Content
            chapters = []
            for idx, item in enumerate(self.items):
                file_name = f"chapter_{idx+1}.xhtml"
                title = item.get("title", f"Chapter {idx+1}")
                
                html_content = ""
                
                if self.mode == "text":
                    html_content = f'<h2 class="chapter-title">{title}</h2>'
                    content_text = item.get("content", "")
                    # Convert newlines to paragraphs if raw text
                    if "<p>" not in content_text and "<div" not in content_text:
                        paras = [f"<p>{p.strip()}</p>" for p in content_text.split(chr(10)) if p.strip()]
                        html_content += "".join(paras)
                    else:
                        html_content += content_text
                        
                elif self.mode == "image":
                    html_content = ""
                    if title and title.lower() != "untitled":
                        html_content += f'<h2 class="chapter-title">{title}</h2>'
                        
                    img_path = item.get("image_path")
                    if img_path and os.path.exists(img_path):
                        opt_img = self._optimize_image(img_path)
                        img_name = f"img_{idx+1}{Path(opt_img).suffix}"
                        with open(opt_img, "rb") as f:
                            epub_img = epub.EpubItem(
                                uid=f"image_{idx+1}",
                                file_name=f"images/{img_name}",
                                media_type="image/jpeg" if opt_img.endswith(".jpg") else "image/png",
                                content=f.read()
                            )
                            self.book.add_item(epub_img)
                        html_content += f'<div class="image-container"><img src="images/{img_name}" alt="{title}"/></div>'
                    
                    desc = item.get("description", "")
                    if desc:
                        html_content += f'<div class="image-caption">{desc}</div>'
                
                chap = epub.EpubHtml(title=title, file_name=file_name)
                chap.set_content(f"<div>{html_content}</div>")
                chap.add_item(css_item)
                self.book.add_item(chap)
                chapters.append(chap)
                spine.append(chap)
                toc.append(chap)

            # Back matter
            back_matter = self._create_back_matter(css_item)
            for page in back_matter:
                spine.append(page)
                toc.append(page)

            # Assemble
            self.book.toc = tuple(toc)
            self.book.add_item(epub.EpubNcx())
            self.book.add_item(epub.EpubNav())
            self.book.spine = spine

            # Validate and write
            epub.write_epub(self.output_path, self.book, {})
            return True
            
        except Exception as e:
            logger.error(f"EPUB generation failed: {e}", exc_info=True)
            raise e
        finally:
            self._cleanup()
