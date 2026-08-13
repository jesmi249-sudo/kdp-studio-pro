import unittest
import time
from uuid import uuid4, UUID
from typing import Dict, Any, List

from book_builder.interfaces.core import IBookBuilder, IStudio
from book_builder.interfaces.services import IExportService
from book_builder.interfaces.base import BaseStudio, BaseCommand
from book_builder.models.book import BookProject
from book_builder.models.page import Page
from book_builder.events.event import Event
from book_builder.events.bus import EventBus
from book_builder.commands.manager import CommandManager
from book_builder.jobs.base import Task, ProgressEvent, CancellationToken
from book_builder.jobs.queue import TaskQueue
from book_builder.container import Container

class MockStudio(BaseStudio):
    """Subclass of BaseStudio implementing mandatory abstract methods for testing."""
    def save_project(self) -> Any:
        return None
    def generate_pages(self, options: Dict[str, Any]) -> None:
        pass
    def validate(self) -> Any:
        return None
    def preview(self, page_number: int) -> Any:
        return None


class MockCommand(BaseCommand):
    """Subclass of BaseCommand for history stack testing."""
    def __init__(self, desc: str = "Mock Operation") -> None:
        self.desc = desc
        self.executed = False
        self.undone = False

    def execute(self) -> bool:
        self.executed = True
        return True

    def undo(self) -> bool:
        self.undone = True
        return True

    def redo(self) -> bool:
        self.executed = True
        return True

    def get_description(self) -> str:
        return self.desc


class MockTask(Task):
    """Subclass of Task for progress and cancellation testing."""
    def __init__(self, steps: int = 10, priority: int = 1) -> None:
        super().__init__(priority)
        self.steps = steps
        self.completed = False

    def execute(self, progress_callback: Any, token: CancellationToken) -> None:
        for i in range(self.steps):
            if token.is_cancelled():
                return
            progress_callback(ProgressEvent(self.id, (i + 1) / self.steps, f"Processing step {i+1}"))
            time.sleep(0.01) # Yield thread briefly
        self.completed = True


class TestScaffolding(unittest.TestCase):
    """Comprehensive test suite validating the v8.0 scaffolding foundation."""
    
    def test_interfaces_and_abc_constraints(self):
        """Verifies abstract base classes raise errors if abstract lifecycle methods are not implemented."""
        with self.assertRaises(TypeError):
            # BaseStudio cannot be directly instantiated (unimplemented abstract methods)
            BaseStudio(None)
            
        studio = MockStudio(None)
        self.assertIsInstance(studio, IStudio)
        
    def test_domain_model_properties(self):
        """Verifies domain models instantiate with correct property defaults."""
        project = BookProject(name="Scaffolding Book")
        self.assertEqual(project.name, "Scaffolding Book")
        self.assertEqual(project.trim_width_in, 8.5)
        
        page = Page(page_number=5)
        self.assertEqual(page.page_number, 5)
        self.assertEqual(page.page_type, "Body")

    def test_dependency_injection_container(self):
        """Verifies Container service registry registrations and lookup resolution rules."""
        container = Container()
        container.clear()
        
        # Resolution lookup before registration must raise error
        with self.assertRaises(ValueError):
            container.resolve(IExportService)
            
        mock_exporter = object()
        container.register(IExportService, mock_exporter)
        
        resolved = container.resolve(IExportService)
        self.assertIs(resolved, mock_exporter)
        
        container.clear()

    def test_event_bus_publishing(self):
        """Verifies subscriber callback registration, event routing, and unsubscribing."""
        bus = EventBus()
        received_events: List[Event] = []
        
        def handler(event: Event) -> None:
            received_events.append(event)
            
        bus.subscribe("TEST_EVENT", handler)
        
        event = Event("TEST_EVENT", "TestSender", {"val": 123})
        bus.publish(event)
        
        self.assertEqual(len(received_events), 1)
        self.assertEqual(received_events[0].event_type, "TEST_EVENT")
        self.assertEqual(received_events[0].payload["val"], 123)
        
        bus.unsubscribe("TEST_EVENT", handler)
        bus.publish(event)
        
        # Should not receive events after unsubscribe
        self.assertEqual(len(received_events), 1)

    def test_command_manager_undo_redo(self):
        """Verifies CommandManager executes command history and performs undo/redo loops."""
        mgr = CommandManager(max_depth=10)
        cmd = MockCommand("Add Blank Page")
        
        self.assertTrue(mgr.execute(cmd))
        self.assertTrue(cmd.executed)
        self.assertFalse(cmd.undone)
        self.assertEqual(mgr.undo_stack.size(), 1)
        
        self.assertTrue(mgr.undo())
        self.assertTrue(cmd.undone)
        self.assertEqual(mgr.undo_stack.size(), 0)
        self.assertEqual(mgr.redo_stack.size(), 1)
        
        self.assertTrue(mgr.redo())
        self.assertEqual(mgr.undo_stack.size(), 1)
        self.assertEqual(mgr.redo_stack.size(), 0)

    def test_background_task_cancellation_flow(self):
        """Verifies TaskQueue handles queue scheduling, progress callbacks, and cancellation signals."""
        queue = TaskQueue(num_workers=1)
        task = MockTask(steps=100, priority=1)
        
        progress_events = []
        def progress_cb(event: ProgressEvent) -> None:
            progress_events.append(event)
            
        token = queue.enqueue(task, progress_cb)
        self.assertFalse(token.is_cancelled())
        
        # Trigger immediate cancellation
        queue.cancel(task.id)
        self.assertTrue(token.is_cancelled())
        
        time.sleep(0.1) # Wait briefly for loop yields
        
        self.assertFalse(task.completed) # Task should have halted on cancel
        queue.shutdown()

if __name__ == "__main__":
    unittest.main()
