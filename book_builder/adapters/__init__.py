from .base import IBookTypeAdapter
from .storybook_adapter import StorybookAdapter
from .coloring_adapter import ColoringAdapter

def get_adapter(book_type: str) -> IBookTypeAdapter:
    """
    Factory method to retrieve the correct BookType adapter for processing AI BookSpecifications.
    """
    book_type = book_type.lower()
    if book_type == "storybook":
        return StorybookAdapter()
    elif book_type == "coloring book" or book_type == "coloring":
        return ColoringAdapter()
    elif book_type == "custom":
        return StorybookAdapter()
    else:
        raise ValueError(f"Book type '{book_type}' is not currently supported by AI generators.")
