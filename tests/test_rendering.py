import unittest
import os
import time
import shutil
import threading
from unittest.mock import MagicMock
from uuid import uuid4
from PIL import Image

from book_builder.models.page import Page
from book_builder.models.book import BookProject
from book_builder.rendering.engine import RenderContext, PageRenderer, RenderingEngine
from book_builder.rendering.cache import PreviewCache, get_page_content_hash
from book_builder.rendering.thumbnail import PageThumbnailGenerator, PAGE_THUMBNAIL_CACHE_DIR
from book_builder.rendering.service import PreviewService
from book_builder.rendering.job import RenderJob
from book_builder.rendering.queue import RenderQueue
from book_builder.events.bus import EventBus
from book_builder.events.event import Event
from book_builder.jobs.queue import TaskQueue
from book_builder.jobs.base import ProgressEvent, CancellationToken


class TestRenderingSubsystem(unittest.TestCase):
    
    def setUp(self) -> None:
        RenderQueue._reset_singleton()
        self.event_bus = EventBus()
        # Clean subscribers to avoid side effects
        self.event_bus._subscribers.clear()
        
        # Setup a sample generic page
        self.page = Page(
            page_number=1,
            width_pt=200.0,
            height_pt=300.0,
        )
        self.page.vector_objects = [
            {
                "shape_type": "rectangle",
                "geometry": {"x": 10.0, "y": 10.0, "width": 50.0, "height": 50.0},
                "properties": {"fill_color": "blue", "stroke_color": "black", "stroke_width": 2.0}
            }
        ]
        self.page.text_blocks = [
            {
                "text": "Hello World",
                "geometry": {"x": 10.0, "y": 100.0, "width": 100.0, "height": 20.0},
                "properties": {"font_size": 12.0, "color": "red"}
            }
        ]
        self.page.images = []

    def tearDown(self) -> None:
        # Cleanup disk caches if any
        if os.path.exists(PAGE_THUMBNAIL_CACHE_DIR):
            try:
                shutil.rmtree(PAGE_THUMBNAIL_CACHE_DIR)
            except Exception:
                pass
        
        # Ensure EventBus is cleared
        self.event_bus._subscribers.clear()
        RenderQueue._reset_singleton()

    # --- 1. RenderContext Tests ---
    def test_render_context_initialization_and_scaling(self):
        # 72 points = 1 inch. DPI = 300 means scale is 300 / 72 = 4.1667 pixels/point
        ctx = RenderContext(width_pt=72.0, height_pt=144.0, dpi=300)
        self.assertEqual(ctx.scale, 300 / 72.0)
        self.assertEqual(ctx.width_px, 300)
        self.assertEqual(ctx.height_px, 600)
        
        self.assertEqual(ctx.pt_to_px(72.0), 300)
        
        # Coordinate map_y test: bottom-left (y=0, h=72)
        # Inverted bottom-left to top-left mapping: height_px - scale*(y + h)
        # y + h = 72 pt -> 300 px. map_y should return 600 - 300 = 300 px
        self.assertEqual(ctx.map_y(0.0, 72.0), 300)

    # --- 2. RenderingEngine and PageRenderer Tests ---
    def test_rendering_engine_produces_image(self):
        engine = RenderingEngine()
        img = engine.render(self.page, dpi=72)
        
        self.assertIsInstance(img, Image.Image)
        # Width: 200 pt * (72 / 72) = 200 px
        # Height: 300 pt * (72 / 72) = 300 px
        self.assertEqual(img.size, (200, 300))
        
    def test_page_renderer_draws_elements(self):
        # Verify page renderer processes vector objects and text blocks without crashing
        renderer = PageRenderer()
        ctx = RenderContext(width_pt=200.0, height_pt=300.0, dpi=72)
        
        # Adding a mock image check
        self.page.images = [{"file_path": "non_existent_file.png", "geometry": {"x": 0.0, "y": 0.0, "width": 50.0, "height": 50.0}}]
        
        # Should execute without throwing exception and draw placeholders for missing image
        renderer.render_page(self.page, ctx)
        
        # Verify it has standard interface
        self.assertTrue(renderer.render_document(BookProject(), "dummy.pdf"))

    # --- 3. PreviewCache Tests ---
    def test_preview_cache_set_and_get(self):
        cache = PreviewCache(max_size=3)
        img = Image.new("RGBA", (10, 10))
        
        cache.set(self.page, 1.0, img)
        cached_img = cache.get(self.page, 1.0)
        
        self.assertIsNotNone(cached_img)
        self.assertEqual(cached_img, img)

    def test_preview_cache_invalidation_on_content_change(self):
        cache = PreviewCache(max_size=3)
        img = Image.new("RGBA", (10, 10))
        
        cache.set(self.page, 1.0, img)
        
        # Modify the page content
        self.page.vector_objects.append({
            "shape_type": "ellipse",
            "geometry": {"x": 5, "y": 5, "width": 10, "height": 10},
            "properties": {}
        })
        
        # Cache lookup should now miss/invalidate because content hash changed
        cached_img = cache.get(self.page, 1.0)
        self.assertIsNone(cached_img)

    def test_preview_cache_eviction_policy(self):
        # Set max_size to 2
        cache = PreviewCache(max_size=2)
        img1 = Image.new("RGBA", (10, 10))
        img2 = Image.new("RGBA", (10, 10))
        img3 = Image.new("RGBA", (10, 10))
        
        p1 = Page(id=uuid4())
        p2 = Page(id=uuid4())
        p3 = Page(id=uuid4())
        
        cache.set(p1, 1.0, img1)
        cache.set(p2, 1.0, img2)
        
        # Access p1 to make it most recently used
        cache.get(p1, 1.0)
        
        # Set p3, should evict p2 (since p1 was just read and is newer in LRU)
        cache.set(p3, 1.0, img3)
        
        self.assertIsNotNone(cache.get(p1, 1.0))
        self.assertIsNone(cache.get(p2, 1.0))
        self.assertIsNotNone(cache.get(p3, 1.0))

    def test_preview_cache_remove_and_clear(self):
        cache = PreviewCache(max_size=5)
        img = Image.new("RGBA", (10, 10))
        
        cache.set(self.page, 1.0, img)
        cache.set(self.page, 2.0, img)
        
        self.assertEqual(len(cache), 2)
        
        cache.remove(self.page.id)
        self.assertEqual(len(cache), 0)
        
        cache.set(self.page, 1.0, img)
        cache.clear()
        self.assertEqual(len(cache), 0)

    # --- 4. ThumbnailGenerator Tests ---
    def test_thumbnail_generator_disk_caching(self):
        generator = PageThumbnailGenerator()
        
        # Generate thumbnail
        path1 = generator.get_thumbnail_path(self.page, size=(80, 80))
        self.assertTrue(os.path.exists(path1))
        self.assertTrue(path1.endswith(".png"))
        
        # Generate again, should hit cache (return same path and not re-render)
        path2 = generator.get_thumbnail_path(self.page, size=(80, 80))
        self.assertEqual(path1, path2)
        
        # Modify page
        self.page.text_blocks[0]["text"] = "Changed Text"
        path3 = generator.get_thumbnail_path(self.page, size=(80, 80))
        
        # Path should change due to new content hash
        self.assertNotEqual(path1, path3)
        self.assertTrue(os.path.exists(path3))

    def test_thumbnail_generator_error_fallback(self):
        # Inject a failing rendering engine to test placeholder generation
        broken_engine = MagicMock()
        broken_engine.render.side_effect = RuntimeError("Simulated render failure")
        
        generator = PageThumbnailGenerator(rendering_engine=broken_engine)
        path = generator.get_thumbnail_path(self.page, size=(50, 50))
        
        # Should fallback to generating a placeholder and still return a valid cached path
        self.assertTrue(os.path.exists(path))

    # --- 5. PreviewService Tests ---
    def test_preview_service_zoom_scaling_and_caching(self):
        rendering_engine = RenderingEngine()
        cache = PreviewCache()
        service = PreviewService(rendering_engine, cache)
        
        # Generate at 1.0 zoom (72 DPI)
        img1 = service.generate_preview(self.page, 1.0)
        self.assertEqual(img1.size, (200, 300))
        
        # Retrieve from cache
        img1_cached = service.generate_preview(self.page, 1.0)
        self.assertIs(img1, img1_cached)
        
        # Generate at 2.0 zoom (144 DPI)
        img2 = service.generate_preview(self.page, 2.0)
        self.assertEqual(img2.size, (400, 600))
        
        # Out-of-bounds zoom constraints (8.0 limit check)
        img_huge = service.generate_preview(self.page, 20.0) # Requested 20x, should limit to 8x
        self.assertEqual(img_huge.size, (1600, 2400)) # 200 pt * 8.0 * (72/72) = 1600 px

    # --- 6. RenderJob and EventBus Integration Tests ---
    def test_render_job_events_success(self):
        service = PreviewService()
        job = RenderJob(self.page, 1.0, service)
        
        events_fired = []
        def handler(event: Event):
            events_fired.append(event)
            
        self.event_bus.subscribe("PAGE_RENDER_STARTED", handler)
        self.event_bus.subscribe("PAGE_RENDER_COMPLETED", handler)
        
        progress_events = []
        def progress_cb(event: ProgressEvent):
            progress_events.append(event)
            
        token = CancellationToken()
        img = job.execute(progress_cb, token)
        
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(len(events_fired), 2)
        self.assertEqual(events_fired[0].event_type, "PAGE_RENDER_STARTED")
        self.assertEqual(events_fired[0].payload["page_id"], str(self.page.id))
        self.assertEqual(events_fired[1].event_type, "PAGE_RENDER_COMPLETED")
        self.assertEqual(events_fired[1].payload["page_id"], str(self.page.id))
        
        self.assertTrue(len(progress_events) > 0)
        self.assertEqual(progress_events[-1].progress, 1.0)

    def test_render_job_cancellation(self):
        service = PreviewService()
        job = RenderJob(self.page, 1.0, service)
        
        events_fired = []
        def handler(event: Event):
            events_fired.append(event)
            
        self.event_bus.subscribe("PAGE_RENDER_STARTED", handler)
        self.event_bus.subscribe("PAGE_RENDER_CANCELLED", handler)
        
        token = CancellationToken()
        token.cancel() # Pre-cancelled
        
        progress_events = []
        def progress_cb(event: ProgressEvent):
            progress_events.append(event)
            
        res = job.execute(progress_cb, token)
        
        self.assertIsNone(res)
        self.assertEqual(len(events_fired), 2)
        self.assertEqual(events_fired[0].event_type, "PAGE_RENDER_STARTED")
        self.assertEqual(events_fired[1].event_type, "PAGE_RENDER_CANCELLED")
        self.assertEqual(progress_events[-1].message, "Cancelled")

    def test_render_job_failure_events(self):
        # Inject failing service
        broken_service = MagicMock()
        broken_service.generate_preview.side_effect = ValueError("Format failure")
        
        job = RenderJob(self.page, 1.0, broken_service)
        
        events_fired = []
        def handler(event: Event):
            events_fired.append(event)
            
        self.event_bus.subscribe("PAGE_RENDER_STARTED", handler)
        self.event_bus.subscribe("PAGE_RENDER_FAILED", handler)
        
        token = CancellationToken()
        
        with self.assertRaises(ValueError):
            job.execute(lambda x: None, token)
            
        self.assertEqual(len(events_fired), 2)
        self.assertEqual(events_fired[0].event_type, "PAGE_RENDER_STARTED")
        self.assertEqual(events_fired[1].event_type, "PAGE_RENDER_FAILED")
        self.assertEqual(events_fired[1].payload["error"], "Format failure")

    # --- 7. RenderQueue Tests ---
    def test_render_queue_submission_and_flow(self):
        # Create a single worker task queue
        task_queue = TaskQueue(num_workers=1)
        render_queue = RenderQueue(task_queue=task_queue)
        
        completed_event = threading.Event()
        events_received = []
        
        def handle_complete(event: Event):
            if event.payload.get("page_id") == str(self.page.id):
                events_received.append(event)
                completed_event.set()
                
        self.event_bus.subscribe("PAGE_RENDER_COMPLETED", handle_complete)
        
        # Submit task
        task_id, token = render_queue.submit(self.page, 1.0)
        self.assertIsNotNone(task_id)
        self.assertFalse(token.is_cancelled())
        
        # Wait for worker thread to process and trigger completion event
        success = completed_event.wait(timeout=5.0)
        self.assertTrue(success, "RenderQueue did not complete page render within timeout")
        self.assertEqual(len(events_received), 1)
        self.assertEqual(events_received[0].event_type, "PAGE_RENDER_COMPLETED")
        
        # Verify clean up of tokens
        self.assertEqual(len(render_queue._active_tokens), 0)
        
        render_queue.shutdown()

    def test_render_queue_cancellation_flow(self):
        task_queue = TaskQueue(num_workers=1)
        render_queue = RenderQueue(task_queue=task_queue)
        
        # We will pause the worker or submit a long running check,
        # but enqueuing many tasks is a simpler way to test queue cancellation
        cancelled_event = threading.Event()
        
        def handle_cancel(event: Event):
            if event.payload.get("page_id") == str(self.page.id):
                cancelled_event.set()
                
        self.event_bus.subscribe("PAGE_RENDER_CANCELLED", handle_cancel)
        
        # Submit and cancel immediately
        task_id, token = render_queue.submit(self.page, 1.0)
        render_queue.cancel(task_id)
        
        self.assertTrue(token.is_cancelled())
        # Wait for cancellation event
        cancelled_event.wait(timeout=2.0)
        
        render_queue.shutdown()


if __name__ == '__main__':
    unittest.main()
