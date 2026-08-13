import unittest
import os
import shutil
import time
from uuid import uuid4
from PIL import Image

from book_builder.models.book import BookProject, BookMetadata
from book_builder.models.page import Page
from book_builder.models.export import ExportProfile
from book_builder.models.asset import Asset
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from book_builder.jobs.queue import TaskQueue
from book_builder.jobs.base import CancellationToken, ProgressEvent

from exporters.validation import KDPValidator
from exporters.export_engine import ExportEngine
from exporters.job import ExportJob
from exporters.svg_exporter import SVGExporter

class TestKDPValidator(unittest.TestCase):
    """
    Verifies that KDPValidator correctly flags page counts, bleed layouts,
    margins, asset resolutions, and cover sizes.
    """
    
    def setUp(self) -> None:
        self.validator = KDPValidator()
        self.project = BookProject(
            name="Test Book",
            book_type="Coloring Book",
            trim_width_in=8.5,
            trim_height_in=11.0,
            has_bleed=False
        )
        # Populate pages
        for i in range(24): # 24 pages minimum
            self.project.pages.append(Page(page_number=i+1, width_pt=612.0, height_pt=792.0))

    def test_page_count_validation(self) -> None:
        # 1. Standard 24 pages - valid
        issues = self.validator.audit_page_count(self.project)
        errors = [i for i in issues if i.severity == "ERROR"]
        self.assertEqual(len(errors), 0)
        
        # 2. Too few pages - invalid
        short_project = BookProject(name="Short")
        short_project.pages = [Page(page_number=1)]
        issues = self.validator.audit_page_count(short_project)
        errors = [i for i in issues if i.severity == "ERROR"]
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("at least 24 pages" in e.explanation for e in errors))

    def test_bleed_validation(self) -> None:
        # 1. has_bleed is True but page size doesn't contain bleed
        self.project.has_bleed = True
        issues = self.validator.validate_bleed(self.project)
        errors = [i for i in issues if i.severity == "ERROR"]
        self.assertGreater(len(errors), 0)
        
        # 2. Correct page size for bleed (8.5x11 + 0.125w + 0.25h) -> 8.625 x 11.25 -> 621.0 x 810.0 pts
        for p in self.project.pages:
            p.width_pt = 621.0
            p.height_pt = 810.0
        issues = self.validator.validate_bleed(self.project)
        errors = [i for i in issues if i.severity == "ERROR"]
        self.assertEqual(len(errors), 0)

    def test_safe_margins_validation(self) -> None:
        # 1. Text block inside margin limits - valid
        page = self.project.pages[0]
        # margins default to 36.0 pt (0.5"). Width 612, Height 792.
        # Safe bounds: X [36, 576] and Y [36, 756]
        page.text_blocks.append({
            "text": "Hello KDP",
            "geometry": {"x": 50.0, "y": 50.0, "width": 100.0, "height": 20.0}
        })
        issues = self.validator.audit_margins(page, False)
        self.assertEqual(len(issues), 0)
        
        # 2. Text block violating inside margin (X < 36)
        page.text_blocks.append({
            "text": "Bad Coordinate",
            "geometry": {"x": 10.0, "y": 50.0, "width": 100.0, "height": 20.0}
        })
        issues = self.validator.audit_margins(page, False)
        errors = [i for i in issues if i.severity == "ERROR"]
        self.assertGreater(len(errors), 0)
        self.assertTrue(any("extends into the KDP safe margin" in e.explanation for e in errors))

    def test_asset_dpi_validation(self) -> None:
        # Create temp file
        temp_img_path = "temp_validation_test.png"
        with Image.new("RGB", (100, 100)) as img:
            img.save(temp_img_path)
            
        asset = Asset(
            id=uuid4(),
            name="Test Image",
            file_path=temp_img_path,
            dpi=72 # Too low
        )
        
        issue = self.validator.audit_image_dpi(asset)
        self.assertIsNotNone(issue)
        self.assertEqual(issue.severity, "WARNING")
        self.assertTrue("Low Image Resolution" in issue.rule_name)
        
        if os.path.exists(temp_img_path):
            os.remove(temp_img_path)


class TestExportEngine(unittest.TestCase):
    """
    Verifies export outputs (PDF, PNG, SVG, ZIP).
    """
    
    def setUp(self) -> None:
        self.export_engine = ExportEngine()
        self.project = BookProject(
            name="Pipeline Test Book",
            book_type="Ruled Notebook",
            trim_width_in=6.0,
            trim_height_in=9.0,
            has_bleed=False
        )
        
        # Add 2 pages with vector lines
        p1 = Page(page_number=1, width_pt=432.0, height_pt=648.0)
        p1.vector_objects.append({
            "shape_type": "line",
            "geometry": {"x": 36.0, "y": 100.0, "width": 360.0, "height": 0.0},
            "properties": {"stroke_color": "#000000", "stroke_width": 1.0}
        })
        p2 = Page(page_number=2, width_pt=432.0, height_pt=648.0)
        p2.text_blocks.append({
            "text": "Notebook Title",
            "geometry": {"x": 100.0, "y": 500.0, "width": 200.0, "height": 20.0},
            "properties": {"font_size": 12.0, "color": "black"}
        })
        
        self.project.pages = [p1, p2]
        
        self.profile = ExportProfile(
            profile_name="Standard Print preset",
            export_format="KDP_PDF",
            color_space="RGB",
            dpi=150, # low DPI for faster test rendering
            compression_level=0.7,
            custom_options={
                "output_folder": "test_output",
                "naming_template": "{project_name}_test_export"
            }
        )
        os.makedirs("test_output", exist_ok=True)

    def tearDown(self) -> None:
        if os.path.exists("test_output"):
            shutil.rmtree("test_output")

    def test_pdf_generation(self) -> None:
        pdf_file = self.export_engine.compile_pdf(self.project, self.profile)
        self.assertTrue(os.path.exists(pdf_file))
        self.assertTrue(pdf_file.endswith(".pdf"))

    def test_image_generation(self) -> None:
        self.profile.export_format = "PNG"
        img_files = self.export_engine.export_pages_to_images(self.project, self.profile)
        self.assertEqual(len(img_files), 2)
        for f in img_files:
            self.assertTrue(os.path.exists(f))
            self.assertTrue(f.endswith(".png"))

    def test_svg_generation(self) -> None:
        self.profile.export_format = "SVG"
        svg_files = self.export_engine.export_pages_to_svg(self.project, self.profile)
        self.assertEqual(len(svg_files), 2)
        for f in svg_files:
            self.assertTrue(os.path.exists(f))
            self.assertTrue(f.endswith(".svg"))
            
            # Verify file contents are valid SVG
            with open(f, "r") as r:
                content = r.read()
                self.assertTrue("<svg" in content)
                self.assertTrue("xmlns=" in content)


class TestExportJobAndQueue(unittest.TestCase):
    """
    Tests validation rules matching, EventBus signaling, and background worker task pools.
    """
    
    def setUp(self) -> None:
        self.project = BookProject(name="Async Test Book", book_type="Notebook")
        # 24 pages minimum
        for i in range(24):
            self.project.pages.append(Page(page_number=i+1, width_pt=612.0, height_pt=792.0))
            
        self.profile = ExportProfile(
            profile_name="Async Preset",
            export_format="KDP_PDF",
            color_space="RGB",
            dpi=72, # lowest resolution to keep benchmarks fast
            custom_options={
                "output_folder": "test_output",
                "naming_template": "async_export_test"
            }
        )
        
        self.event_bus = EventBus()
        self.events_received = []
        self.event_bus.subscribe("*", self._on_event)
        
        os.makedirs("test_output", exist_ok=True)

    def tearDown(self) -> None:
        self.event_bus.unsubscribe("*", self._on_event)
        if os.path.exists("test_output"):
            shutil.rmtree("test_output")

    def _on_event(self, event: Event) -> None:
        self.events_received.append(event)

    def test_background_job_success(self) -> None:
        job = ExportJob(self.project, self.profile)
        queue = TaskQueue(num_workers=1)
        
        done_flag = [False]
        def progress_callback(event: ProgressEvent) -> None:
            if event.progress >= 1.0 or "Error" in event.message:
                done_flag[0] = True
                
        # Enqueue and block until done
        token = queue.enqueue(job, progress_callback)
        
        # Wait up to 5 seconds
        start = time.time()
        while not done_flag[0] and (time.time() - start) < 5.0:
            time.sleep(0.1)
            
        queue.shutdown()
        
        # Verify events
        event_types = [e.event_type for e in self.events_received]
        self.assertTrue("EXPORT_STARTED" in event_types)
        self.assertTrue("EXPORT_PROGRESS" in event_types)
        self.assertTrue("EXPORT_COMPLETED" in event_types)
        
    def test_background_job_validation_failure(self) -> None:
        # Invalid project due to insufficient page count (1 page)
        fail_project = BookProject(name="Fail Book", book_type="Notebook")
        fail_project.pages = [Page(page_number=1)]
        
        job = ExportJob(fail_project, self.profile)
        queue = TaskQueue(num_workers=1)
        
        done_flag = [False]
        def progress_callback(event: ProgressEvent) -> None:
            if event.progress >= 1.0 or "Error" in event.message:
                done_flag[0] = True
                
        queue.enqueue(job, progress_callback)
        
        start = time.time()
        while not done_flag[0] and (time.time() - start) < 5.0:
            time.sleep(0.1)
            
        queue.shutdown()
        
        event_types = [e.event_type for e in self.events_received]
        self.assertTrue("EXPORT_STARTED" in event_types)
        self.assertTrue("EXPORT_VALIDATION_FAILED" in event_types)
        self.assertTrue("EXPORT_FAILED" in event_types)
