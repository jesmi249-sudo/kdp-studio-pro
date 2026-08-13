import os
from PIL import Image, ImageDraw, ImageFont
from core.logger import get_logger

logger = get_logger(__name__)

class CoverGenerator:
    def __init__(self):
        self.dpi = 300
        # Multipliers to convert inches to pixels at 300 DPI
        self.ppi = 300
        
    def calculate_dimensions(self, trim_width, trim_height, pages, paper_type="White", bleed=0.125):
        """
        Calculates cover dimensions in inches and pixels based on KDP guidelines.
        Paper types: "White", "Cream", "Color"
        """
        # Spine width calculation
        if paper_type == "White":
            spine_width = pages * 0.002252
        elif paper_type == "Cream":
            spine_width = pages * 0.0025
        elif paper_type == "Color":
            spine_width = pages * 0.002347
        else:
            spine_width = pages * 0.002252 # Default white
            
        # Full cover dimensions (in inches)
        # Bleed on 3 sides of each cover (top, bottom, outside). No bleed on spine.
        # Width = Bleed + BackCoverTrim + Spine + FrontCoverTrim + Bleed
        full_width = bleed + trim_width + spine_width + trim_width + bleed
        
        # Height = Bleed + TrimHeight + Bleed
        full_height = bleed + trim_height + bleed
        
        dims = {
            "spine_inches": spine_width,
            "full_width_inches": full_width,
            "full_height_inches": full_height,
            "spine_px": int(spine_width * self.ppi),
            "full_width_px": int(full_width * self.ppi),
            "full_height_px": int(full_height * self.ppi),
            "trim_width_px": int(trim_width * self.ppi),
            "trim_height_px": int(trim_height * self.ppi),
            "bleed_px": int(bleed * self.ppi),
            "safe_zone_px": int(0.25 * self.ppi), # 0.25" safe zone margin from trim
        }
        return dims

    def _hex_to_rgb(self, hex_color):
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return (255, 255, 255) # default white

    def generate_image(self, canvas_objects, dims, background_color="#FFFFFF"):
        """
        Generates a PIL Image object from canvas data.
        canvas_objects is a list of dictionaries with element properties.
        """
        width = dims['full_width_px']
        height = dims['full_height_px']
        
        # Create base image
        bg_rgb = self._hex_to_rgb(background_color)
        img = Image.new('RGB', (width, height), color=bg_rgb)
        draw = ImageDraw.Draw(img)
        
        # Render objects based on their Z-order
        # Assuming canvas_objects is sorted by z-index or we sort it here.
        
        for obj in canvas_objects:
            obj_type = obj.get('type')
            x = int(obj.get('x', 0))
            y = int(obj.get('y', 0))
            
            if obj_type == 'text':
                text = obj.get('text', '')
                font_name = obj.get('font', 'arial.ttf')
                font_size = int(obj.get('size', 40))
                color = self._hex_to_rgb(obj.get('color', '#000000'))
                
                try:
                    # In a real app, you'd map standard font names to absolute paths or use a default
                    # Fallback to default PIL font if custom font loading fails
                    font = ImageFont.truetype(font_name, font_size)
                except IOError:
                    font = ImageFont.load_default()
                
                # Handling rotation (if supported) requires rendering text to a temporary transparent image, rotating it, and pasting it.
                # For simplicity here without a full rotation matrix implementation:
                angle = obj.get('rotation', 0)
                if angle != 0:
                    temp_img = Image.new('RGBA', (font_size * len(text), font_size * 2), (255,255,255,0))
                    temp_draw = ImageDraw.Draw(temp_img)
                    temp_draw.text((0, 0), text, font=font, fill=color + (255,))
                    temp_img = temp_img.rotate(-angle, expand=1)
                    img.paste(temp_img, (x, y), temp_img)
                else:
                    draw.text((x, y), text, font=font, fill=color)
                    
            elif obj_type == 'image':
                img_path = obj.get('image_path')
                if img_path and os.path.exists(img_path):
                    try:
                        elem_img = Image.open(img_path).convert("RGBA")
                        
                        # Resize
                        target_w = int(obj.get('width', elem_img.width))
                        target_h = int(obj.get('height', elem_img.height))
                        elem_img = elem_img.resize((target_w, target_h), Image.Resampling.LANCZOS)
                        
                        # Rotate
                        angle = obj.get('rotation', 0)
                        if angle != 0:
                            elem_img = elem_img.rotate(-angle, expand=True)
                            
                        # Paste with alpha channel as mask
                        img.paste(elem_img, (x, y), elem_img)
                    except Exception as e:
                        logger.error(f"Error rendering image on cover: {e}")
                        
            elif obj_type in ('barcode', 'barcode_placeholder'):
                value = obj.get('value', '')
                w = int(obj.get('width', 2.0 * self.ppi))
                h = int(obj.get('height', 1.2 * self.ppi))
                self._draw_barcode(draw, img, x, y, w, h, value)

        return img

    def _draw_barcode(self, draw, img, x, y, width, height, value):
        from book_builder.container import Container
        from book_builder.services.barcode_service import IBarcodeService
        
        barcode_service = None
        try:
            barcode_service = Container().resolve(IBarcodeService)
        except Exception as e:
            logger.warning(f"BarcodeService not registered: {e}")
            
        if barcode_service and value and barcode_service.is_valid_isbn13(value):
            barcode_img = barcode_service.generate_ean13(value)
            if barcode_img:
                # Resize barcode to fit the target width/height
                barcode_img = barcode_img.resize((width, height), Image.Resampling.LANCZOS)
                # Ensure mode is compatible (convert to RGBA for pasting if needed)
                barcode_img = barcode_img.convert("RGBA")
                img.paste(barcode_img, (x, y), barcode_img)
                return
                
        # Fallback / No ISBN: Draw a blank white rectangle of the exact size
        # This reserves the space for KDP's auto-generated barcode and prevents cover art overlap
        draw.rectangle([x, y, x + width, y + height], fill=(255, 255, 255), outline=(255, 255, 255))

    def export(self, canvas_objects, dims, background_color, path, format="pdf"):
        """
        Exports the cover to the specified path.
        format can be 'pdf', 'png', or 'jpeg'
        """
        try:
            img = self.generate_image(canvas_objects, dims, background_color)
            if format.lower() == 'pdf':
                # Convert to RGB just in case, though it should be
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save(path, "PDF", resolution=self.dpi)
            elif format.lower() == 'png':
                img.save(path, "PNG")
            elif format.lower() in ['jpg', 'jpeg']:
                img = img.convert('RGB')
                img.save(path, "JPEG", quality=95)
            logger.info(f"Successfully exported cover to {path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export cover: {e}")
            return False
