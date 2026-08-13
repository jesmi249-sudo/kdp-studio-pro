import os
from typing import Dict, Any
from PIL import Image, ImageEnhance
from core.logger import get_logger
from models.asset import Asset
from core.asset_manager import AssetManager

logger = get_logger(__name__)

class ImageProcessingService:
    """
    Handles KDP-specific Image Quality Checks and lightweight line-art processing.
    """
    
    @staticmethod
    def check_quality(asset: Asset) -> Dict[str, Any]:
        """
        Inspects an asset to ensure it meets KDP coloring book quality standards.
        Returns a dictionary: {"status": "READY" | "WARNING" | "ERROR", "messages": [str]}
        """
        result = {"status": "READY", "messages": []}
        
        if not asset:
            return {"status": "ERROR", "messages": ["Asset object is null."]}
            
        if not os.path.exists(asset.file_path):
            return {"status": "ERROR", "messages": ["Artwork file not found on disk."]}
            
        ext = os.path.splitext(asset.file_path)[1].lower()
        if ext not in ['.png', '.jpg', '.jpeg']:
            result["status"] = "ERROR"
            result["messages"].append(f"Unsupported format '{ext}'. Must be PNG or JPG.")
            return result
            
        try:
            with Image.open(asset.file_path) as img:
                w, h = img.size
                mode = img.mode
                
                # Check resolution bounds roughly (e.g. at least 1500px on one side for decent print)
                if w < 1500 and h < 1500:
                    result["status"] = "WARNING"
                    result["messages"].append(f"Low resolution ({w}x{h}). Artwork may appear pixelated when printed.")
                    
                # Outline check
                gray = img.convert("L")
                hist = gray.histogram()
                total_pixels = max(sum(hist), 1)
                avg_lum = sum(i * count for i, count in enumerate(hist)) / total_pixels
                
                dark_pixels = sum(hist[:60])
                dark_ratio = dark_pixels / total_pixels
                
                if avg_lum < 160:
                    result["status"] = "WARNING"
                    result["messages"].append(f"Average brightness is low ({avg_lum:.1f}). Ensure background is solid white.")
                elif dark_ratio < 0.005:
                    result["status"] = "WARNING"
                    result["messages"].append("Too few dark line pixels detected. Outlines may be faint.")
                elif dark_ratio > 0.35:
                    result["status"] = "WARNING"
                    result["messages"].append("High ratio of dark pixels. May contain too much solid black ink.")
                    
        except Exception as e:
            logger.error(f"Failed to read image quality for {asset.file_path}: {e}")
            result["status"] = "ERROR"
            result["messages"].append("Could not read image data. File may be corrupted.")
            
        return result

    @staticmethod
    def prepare_line_art(asset: Asset, asset_manager: AssetManager) -> Asset:
        """
        Non-destructively processes the original artwork into a high-contrast line-art image.
        Returns the newly imported Asset.
        """
        if not os.path.exists(asset.file_path):
            raise FileNotFoundError(f"Artwork file not found: {asset.file_path}")
            
        # Prepare output path
        base, ext = os.path.splitext(asset.file_path)
        processed_path = f"{base}_processed{ext}"
        
        try:
            with Image.open(asset.file_path) as img:
                # 1. Convert to grayscale
                img = img.convert("L")
                
                # 2. Increase Contrast heavily to push grays to white/black
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(2.0)
                
                # 3. Simple thresholding to enforce pure white and black
                # Map pixels: > 180 becomes white, else black
                # Using point mapping is fast
                img = img.point(lambda p: 255 if p > 180 else 0)
                
                # 4. Save
                img.save(processed_path)
                
            # Import as a new asset
            new_name = f"{asset.name} (Processed)"
            new_asset = asset_manager.import_asset(
                source_path=processed_path,
                category=asset.category,
                name=new_name,
                character=asset.character,
                pose=asset.pose,
                expression=asset.expression,
                outfit=asset.outfit,
                scene=asset.scene
            )
            
            return new_asset
            
        except Exception as e:
            logger.error(f"Failed to prepare line art for {asset.file_path}: {e}")
            raise e
