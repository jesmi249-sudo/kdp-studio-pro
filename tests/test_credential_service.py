import unittest
from book_builder.services.credential_service import MockCredentialService

class TestCredentialService(unittest.TestCase):
    def setUp(self):
        self.service = MockCredentialService()

    def test_set_and_get_credential(self):
        success = self.service.set_credential("test_service", "test_user", "secret123")
        self.assertTrue(success)
        
        val = self.service.get_credential("test_service", "test_user")
        self.assertEqual(val, "secret123")

    def test_get_nonexistent_credential(self):
        val = self.service.get_credential("test_service", "unknown_user")
        self.assertIsNone(val)

    def test_delete_credential(self):
        self.service.set_credential("test_service", "test_user", "secret123")
        
        success = self.service.delete_credential("test_service", "test_user")
        self.assertTrue(success)
        
        val = self.service.get_credential("test_service", "test_user")
        self.assertIsNone(val)
        
    def test_delete_nonexistent_credential(self):
        success = self.service.delete_credential("test_service", "unknown_user")
        self.assertFalse(success)

if __name__ == "__main__":
    unittest.main()
