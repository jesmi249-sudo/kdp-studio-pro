import unittest
from book_builder.services.barcode_service import PythonBarcodeService
from PIL import Image

class TestBarcodeService(unittest.TestCase):
    def setUp(self):
        self.service = PythonBarcodeService()

    def test_valid_isbn13(self):
        # 978-0-306-40615-7 is a valid ISBN
        self.assertTrue(self.service.is_valid_isbn13("978-0-306-40615-7"))
        self.assertTrue(self.service.is_valid_isbn13("9780306406157"))

    def test_invalid_isbn13_checksum(self):
        # Changed last digit from 7 to 8
        self.assertFalse(self.service.is_valid_isbn13("978-0-306-40615-8"))

    def test_invalid_isbn_length(self):
        self.assertFalse(self.service.is_valid_isbn13("978-0-306-40615"))
        self.assertFalse(self.service.is_valid_isbn13("1234567890"))

    def test_missing_isbn(self):
        self.assertFalse(self.service.is_valid_isbn13(""))
        self.assertFalse(self.service.is_valid_isbn13(None))

    def test_barcode_generation_valid(self):
        img = self.service.generate_ean13("978-0-306-40615-7")
        self.assertIsNotNone(img)
        self.assertIsInstance(img, Image.Image)
        # Verify it has dimensions
        self.assertTrue(img.width > 0)
        self.assertTrue(img.height > 0)

    def test_barcode_generation_invalid(self):
        img = self.service.generate_ean13("978-0-306-40615-8")
        self.assertIsNone(img)

if __name__ == '__main__':
    unittest.main()
