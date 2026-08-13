from abc import ABC, abstractmethod
from typing import Any, List, Dict, Tuple, Optional

class IRenderer(ABC):
    """Interface for page canvas compilation."""
    
    @abstractmethod
    def render_page(self, page: Any, canvas_context: Any) -> None:
        """Renders vector and text elements onto a print-sheet canvas."""
        pass

    @abstractmethod
    def render_document(self, book_project: Any, output_path: str) -> bool:
        """Compiles the entire book aggregate into a print-ready document file."""
        pass


class IPreviewService(ABC):
    """Interface for rendering fast low-resolution canvas previews."""
    
    @abstractmethod
    def generate_preview(self, page: Any, zoom_level: float) -> Any:
        """Generates a low-resolution raster graphic of a page."""
        pass

    @abstractmethod
    def clear_cache(self) -> None:
        """Disposes of cached preview images to release memory."""
        pass


class IExportService(ABC):
    """Interface for packaging print PDFs and distribution archives."""
    
    @abstractmethod
    def compile_pdf(self, book_project: Any, profile: Any) -> str:
        """Generates an interior print PDF matching KDP formatting requirements."""
        pass

    @abstractmethod
    def compile_cover(self, book_project: Any, profile: Any) -> str:
        """Calculates spine dimensions and compiles a print-ready cover PDF."""
        pass

    @abstractmethod
    def build_zip_package(self, book_project: Any, profile: Any, output_dir: str) -> str:
        """Bundles cover, interior, and metadata package into a distribution archive."""
        pass


class IComplianceService(ABC):
    """Interface for KDP pre-flight validation checks."""
    
    @abstractmethod
    def audit_margins(self, page: Any, is_bleed: bool) -> List[Any]:
        """Validates element coordinates against KDP safety margins."""
        pass

    @abstractmethod
    def audit_page_count(self, book_project: Any) -> List[Any]:
        """Checks page count against print format guidelines."""
        pass

    @abstractmethod
    def audit_image_dpi(self, asset: Any) -> Optional[Any]:
        """Validates image asset resolutions."""
        pass


class IAssetService(ABC):
    """Interface for tracking file dependencies, resolutions, and scaling."""
    
    @abstractmethod
    def import_asset(self, source_path: str, category: str) -> Any:
        """Imports asset file and extracts metadata."""
        pass

    @abstractmethod
    def get_asset_metadata(self, asset_id: str) -> Dict[str, Any]:
        """Retrieves file size, DPI, and format metadata."""
        pass


class IProjectService(ABC):
    """Interface for database writes, lock manager, and backups."""
    
    @abstractmethod
    def save_project_state(self, project: Any) -> bool:
        """Writes project state to database records."""
        pass

    @abstractmethod
    def create_backup(self, project: Any) -> str:
        """Generates an autosave recovery backup file."""
        pass


class IPlugin(ABC):
    """Interface for dynamic third-party extension modules."""
    
    @abstractmethod
    def get_manifest(self) -> Dict[str, Any]:
        """Returns the plugin registry manifest dictionary."""
        pass

    @abstractmethod
    def execute_command(self, cmd_name: str, *args: Any, **kwargs: Any) -> Any:
        """Invokes a plugin command."""
        pass


class IBackgroundTask(ABC):
    """Interface for asynchronous priority-based job operations."""
    
    @abstractmethod
    def execute(self, progress_callback: Any, token: Any) -> Any:
        """Starts task execution loop checking for cancellation tokens."""
        pass
