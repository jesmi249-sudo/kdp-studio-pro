from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any, Literal

# Supported Enums / Literals
BookType = Literal["storybook", "coloring", "activity", "planner", "notebook"]
PageType = Literal["title", "copyright", "body", "end"]
LayoutType = Literal["image_top", "text_bottom", "full_bleed_image", "text_only", "image_only", "split", "activity"]
ActivityType = Literal["maze", "word_search", "sudoku", "crossword", "dot_to_dot", "tracing", "matching", "none"]

class PageSpecification(BaseModel):
    page_number: int = Field(..., description="The sequential page number, 1-indexed.")
    page_type: PageType = Field(..., description="The type of the page.")
    layout_type: LayoutType = Field(..., description="The layout configuration for this page.")
    text_content: Optional[str] = Field(None, description="The primary text content to appear on the page.")
    image_prompt: Optional[str] = Field(None, description="A detailed visual description for future AI image generation.")
    activity_type: ActivityType = Field("none", description="The type of activity if this is an activity page.")
    activity_metadata: Optional[Dict[str, Any]] = Field(None, description="Specific parameters for the activity (e.g. difficulty, word list).")
    instructions: Optional[str] = Field(None, description="Instructions to be printed on the page for the activity/coloring.")

    @field_validator("page_number")
    @classmethod
    def validate_page_number(cls, v: int) -> int:
        if v < 1:
            raise ValueError("Page number must be >= 1")
        return v


class BookSpecification(BaseModel):
    title: str = Field(..., description="The title of the book.")
    subtitle: Optional[str] = Field(None, description="The subtitle of the book.")
    book_type: BookType = Field(..., description="The category of the book.")
    target_audience: str = Field(..., description="The intended audience or age range, e.g., 'Children 5-7'.")
    trim_width_in: float = Field(..., description="The trim width in inches (e.g., 8.5).")
    trim_height_in: float = Field(..., description="The trim height in inches (e.g., 11.0).")
    page_count: int = Field(..., description="Total number of pages in the book.")
    global_style_instructions: str = Field(..., description="High-level aesthetic and style guidelines for the book's assets.")
    pages: List[PageSpecification] = Field(..., description="The page-by-page specification.")

    @field_validator("page_count")
    @classmethod
    def validate_page_count(cls, v: int) -> int:
        if v < 24:
            raise ValueError("KDP requires a minimum of 24 pages.")
        if v > 828:
            raise ValueError("KDP supports a maximum of 828 pages.")
        return v

    @field_validator("trim_width_in", "trim_height_in")
    @classmethod
    def validate_trim_sizes(cls, v: float) -> float:
        if v < 4.0 or v > 11.69:
            raise ValueError("Trim dimensions must be within valid standard KDP ranges (4.0 to 11.69 inches).")
        return v

    @field_validator("pages")
    @classmethod
    def validate_pages_length(cls, v: List[PageSpecification], info) -> List[PageSpecification]:
        expected = info.data.get("page_count")
        if expected is not None and len(v) != expected:
            raise ValueError(f"Number of page specifications ({len(v)}) does not match expected page_count ({expected}).")
        
        # Verify page numbers are sequential
        expected_nums = list(range(1, len(v) + 1))
        actual_nums = [p.page_number for p in v]
        if expected_nums != actual_nums:
            raise ValueError("Page numbers must be strictly sequential starting from 1.")
            
        return v
