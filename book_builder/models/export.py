from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class ExportProfile:
    """Value object holding export configuration mappings for output generation."""
    profile_name: str = "Standard KDP Print"
    export_format: str = "KDP_PDF" # KDP_PDF, EPUB, ZIP, PNG, JPEG
    color_space: str = "CMYK" # CMYK, RGB, Grayscale
    dpi: int = 300
    embed_fonts: bool = True
    include_crop_marks: bool = False
    compression_level: float = 0.8
    pdf_x_standard: str = "PDF/X-1a:2001"
    custom_options: Dict[str, Any] = field(default_factory=dict)
