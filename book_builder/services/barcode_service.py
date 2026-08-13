from abc import ABC, abstractmethod
from typing import Optional
from PIL import Image
import barcode
from barcode.writer import ImageWriter
import io
import re

class IBarcodeService(ABC):
    @abstractmethod
    def is_valid_isbn13(self, isbn: str) -> bool:
        pass

    @abstractmethod
    def generate_ean13(self, isbn: str) -> Optional[Image.Image]:
        pass


class PythonBarcodeService(IBarcodeService):
    def is_valid_isbn13(self, isbn: str) -> bool:
        """
        Validates if the provided string is a valid ISBN-13 format.
        Strips hyphens and whitespace, checks length and checksum.
        """
        if not isbn:
            return False
            
        clean_isbn = re.sub(r'[-\s]', '', isbn)
        if len(clean_isbn) != 13 or not clean_isbn.isdigit():
            return False
            
        # Checksum calculation for ISBN-13/EAN-13
        total = 0
        for i in range(12):
            digit = int(clean_isbn[i])
            total += digit if i % 2 == 0 else digit * 3
            
        checksum = (10 - (total % 10)) % 10
        return checksum == int(clean_isbn[12])

    def generate_ean13(self, isbn: str) -> Optional[Image.Image]:
        """
        Generates an EAN-13 barcode image (PIL) from a valid ISBN-13.
        Returns None if invalid.
        """
        if not self.is_valid_isbn13(isbn):
            return None
            
        clean_isbn = re.sub(r'[-\s]', '', isbn)
        
        # python-barcode EAN13 generation
        # We must write to a BytesIO object to load into PIL
        try:
            ean = barcode.get('ean13', clean_isbn, writer=ImageWriter())
            # Configure writer options for high-res print quality
            options = {
                'module_width': 0.4,
                'module_height': 15.0,
                'font_size': 10,
                'text_distance': 5.0,
                'quiet_zone': 6.5,
                'dpi': 300,
                'background': 'white',
                'foreground': 'black'
            }
            
            output = io.BytesIO()
            ean.write(output, options=options)
            output.seek(0)
            
            # Load into PIL
            img = Image.open(output)
            img.load() # Force load so we can close the BytesIO safely if needed
            return img
        except Exception as e:
            from core.logger import get_logger
            get_logger(__name__).error(f"Failed to generate barcode for {isbn}: {e}")
            return None

from book_builder.container import Container
Container().register(IBarcodeService, PythonBarcodeService())
