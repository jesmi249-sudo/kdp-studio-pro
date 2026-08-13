import unittest
from core.compliance_checker import ComplianceChecker
from models.compliance_result import Issue

class MockGenerator:
    def __init__(self, data):
        self.data = data
    def get_metadata(self):
        return self.data
        
class MockMetaView:
    def __init__(self, data):
        self.generator = MockGenerator(data)
    def _update_generator_data(self):
        pass
        
class MockVar:
    def __init__(self, val):
        self.val = val
    def get(self):
        return self.val

class MockInteriorView:
    def __init__(self, pages="100", mt="0.5", mb="0.5", mi="0.5", mo="0.5"):
        self.page_count = MockVar(pages)
        self.m_top = MockVar(mt)
        self.m_bot = MockVar(mb)
        self.m_in = MockVar(mi)
        self.m_out = MockVar(mo)

class MockCoverView:
    def __init__(self, objects, dims):
        self.canvas_objects = objects
        self.dims = dims

class MockApp:
    def __init__(self):
        self.views = {
            "Metadata": MockMetaView({
                "title": "A Valid Title",
                "author": "John Doe",
                "keywords": ["test1", "test2"]
            }),
            "Interior Designer": MockInteriorView(),
            "Cover Designer Pro": MockCoverView([{"type": "text", "text": "Hi"}], {"trim_width_px": 100})
        }

class TestComplianceChecker(unittest.TestCase):
    def test_complete_project_passes(self):
        app = MockApp()
        checker = ComplianceChecker(app)
        res = checker.run_inspection()
        
        # We expect a high score, maybe some warnings (description missing), but no errors
        errors = [i for i in res.issues if i.severity in ("ERROR", "CRITICAL")]
        self.assertEqual(len(errors), 0)
        self.assertGreater(res.health_score, 80)
        
    def test_empty_metadata_fails(self):
        app = MockApp()
        app.views["Metadata"].generator.data = {}
        checker = ComplianceChecker(app)
        res = checker.run_inspection()
        
        errors = [i.rule_name for i in res.issues if i.severity == "ERROR"]
        self.assertIn("Missing Title", errors)
        self.assertIn("Missing Author", errors)
        
    def test_interior_invalid_pages(self):
        app = MockApp()
        app.views["Interior Designer"] = MockInteriorView(pages="10") # < 24
        checker = ComplianceChecker(app)
        res = checker.run_inspection()
        
        errors = [i.rule_name for i in res.issues if i.severity == "ERROR"]
        self.assertIn("Insufficient Pages", errors)

if __name__ == '__main__':
    unittest.main()
