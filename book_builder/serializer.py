import json
from datetime import datetime
from typing import Dict, Any, List
from uuid import UUID
from book_builder.models.book import BookProject, BookMetadata
from book_builder.models.page import Page
from book_builder.models.asset import Asset
from book_builder.models.export import ExportProfile
from book_builder.models.compliance import ComplianceResult, ComplianceIssue
from book_builder.models.state import ValidationResult, ValidationError

class ProjectSerializer:
    """Utility class to serialize and deserialize Book Builder domain models to and from dicts."""

    @staticmethod
    def serialize_metadata(metadata: BookMetadata) -> Dict[str, Any]:
        """Converts BookMetadata to a dictionary."""
        return {
            "title": metadata.title,
            "subtitle": metadata.subtitle,
            "author": metadata.author,
            "publisher": metadata.publisher,
            "description": metadata.description,
            "language": metadata.language,
            "keywords": metadata.keywords,
            "categories": metadata.categories,
            "isbn": metadata.isbn,
            "imprint": metadata.imprint,
            "series_name": metadata.series_name,
            "series_number": metadata.series_number,
            "age_range_min": metadata.age_range_min,
            "age_range_max": metadata.age_range_max
        }

    @staticmethod
    def deserialize_metadata(data: Dict[str, Any]) -> BookMetadata:
        """Converts a dictionary back to a BookMetadata object."""
        return BookMetadata(
            title=data.get("title", ""),
            subtitle=data.get("subtitle", ""),
            author=data.get("author", ""),
            publisher=data.get("publisher", ""),
            description=data.get("description", ""),
            language=data.get("language", "en"),
            keywords=data.get("keywords", []),
            categories=data.get("categories", []),
            isbn=data.get("isbn"),
            imprint=data.get("imprint"),
            series_name=data.get("series_name"),
            series_number=data.get("series_number"),
            age_range_min=data.get("age_range_min"),
            age_range_max=data.get("age_range_max")
        )

    @staticmethod
    def serialize_page(page: Page) -> Dict[str, Any]:
        """Converts Page to a dictionary."""
        return {
            "id": str(page.id),
            "page_number": page.page_number,
            "page_type": page.page_type,
            "width_pt": page.width_pt,
            "height_pt": page.height_pt,
            "margin_top_pt": page.margin_top_pt,
            "margin_bottom_pt": page.margin_bottom_pt,
            "margin_inside_pt": page.margin_inside_pt,
            "margin_outside_pt": page.margin_outside_pt,
            "has_bleed": page.has_bleed,
            "rotation_deg": page.rotation_deg,
            "background_asset_id": str(page.background_asset_id) if page.background_asset_id else None,
            "layers": page.layers,
            "images": page.images,
            "text_blocks": page.text_blocks,
            "vector_objects": page.vector_objects,
            "guides": page.guides,
            "bookmarks": page.bookmarks,
            "template_id": str(page.template_id) if page.template_id else None,
            "rendering_state": page.rendering_state,
            "validation_state": page.validation_state
        }

    @staticmethod
    def deserialize_page(data: Dict[str, Any]) -> Page:
        """Converts a dictionary back to a Page object."""
        bg_id = data.get("background_asset_id")
        temp_id = data.get("template_id")
        return Page(
            id=UUID(data["id"]) if "id" in data else UUID(int=0),
            page_number=data.get("page_number", 1),
            page_type=data.get("page_type", "Body"),
            width_pt=data.get("width_pt", 612.0),
            height_pt=data.get("height_pt", 792.0),
            margin_top_pt=data.get("margin_top_pt", 36.0),
            margin_bottom_pt=data.get("margin_bottom_pt", 36.0),
            margin_inside_pt=data.get("margin_inside_pt", 36.0),
            margin_outside_pt=data.get("margin_outside_pt", 36.0),
            has_bleed=data.get("has_bleed", False),
            rotation_deg=data.get("rotation_deg", 0.0),
            background_asset_id=UUID(bg_id) if bg_id else None,
            layers=data.get("layers", []),
            images=data.get("images", []),
            text_blocks=data.get("text_blocks", []),
            vector_objects=data.get("vector_objects", []),
            guides=data.get("guides", []),
            bookmarks=data.get("bookmarks", []),
            template_id=UUID(temp_id) if temp_id else None,
            rendering_state=data.get("rendering_state", {}),
            validation_state=data.get("validation_state", {})
        )

    @staticmethod
    def serialize_asset(asset: Asset) -> Dict[str, Any]:
        """Converts Asset to a dictionary."""
        return {
            "id": str(asset.id),
            "name": asset.name,
            "asset_type": asset.asset_type,
            "storage_type": asset.storage_type,
            "file_path": asset.file_path,
            "file_size_bytes": asset.file_size_bytes,
            "dpi": asset.dpi,
            "width_px": asset.width_px,
            "height_px": asset.height_px,
            "is_favorite": asset.is_favorite,
            "tags": asset.tags,
            "created_at": asset.created_at.isoformat(),
            "last_used": asset.last_used.isoformat() if asset.last_used else None,
            "custom_metadata": asset.custom_metadata
        }

    @staticmethod
    def deserialize_asset(data: Dict[str, Any]) -> Asset:
        """Converts a dictionary back to an Asset object."""
        created_str = data.get("created_at")
        last_used_str = data.get("last_used")
        return Asset(
            id=UUID(data["id"]) if "id" in data else UUID(int=0),
            name=data.get("name", ""),
            asset_type=data.get("asset_type", "Image"),
            storage_type=data.get("storage_type", "Linked"),
            file_path=data.get("file_path", ""),
            file_size_bytes=data.get("file_size_bytes", 0),
            dpi=data.get("dpi", 300),
            width_px=data.get("width_px", 0),
            height_px=data.get("height_px", 0),
            is_favorite=data.get("is_favorite", False),
            tags=data.get("tags", ""),
            created_at=datetime.fromisoformat(created_str) if created_str else datetime.utcnow(),
            last_used=datetime.fromisoformat(last_used_str) if last_used_str else None,
            custom_metadata=data.get("custom_metadata", {})
        )

    @staticmethod
    def serialize_export_profile(profile: ExportProfile) -> Dict[str, Any]:
        """Converts ExportProfile to a dictionary."""
        return {
            "profile_name": profile.profile_name,
            "export_format": profile.export_format,
            "color_space": profile.color_space,
            "dpi": profile.dpi,
            "embed_fonts": profile.embed_fonts,
            "include_crop_marks": profile.include_crop_marks,
            "compression_level": profile.compression_level,
            "pdf_x_standard": profile.pdf_x_standard,
            "custom_options": profile.custom_options
        }

    @staticmethod
    def deserialize_export_profile(data: Dict[str, Any]) -> ExportProfile:
        """Converts a dictionary back to an ExportProfile object."""
        return ExportProfile(
            profile_name=data.get("profile_name", "Standard KDP Print"),
            export_format=data.get("export_format", "KDP_PDF"),
            color_space=data.get("color_space", "CMYK"),
            dpi=data.get("dpi", 300),
            embed_fonts=data.get("embed_fonts", True),
            include_crop_marks=data.get("include_crop_marks", False),
            compression_level=data.get("compression_level", 0.8),
            pdf_x_standard=data.get("pdf_x_standard", "PDF/X-1a:2001"),
            custom_options=data.get("custom_options", {})
        )

    @classmethod
    def serialize_project(cls, project: BookProject) -> Dict[str, Any]:
        """Serializes the entire BookProject aggregate root to a dictionary."""
        return {
            "id": str(project.id),
            "name": project.name,
            "book_type": project.book_type,
            "metadata": cls.serialize_metadata(project.metadata),
            "trim_width_in": project.trim_width_in,
            "trim_height_in": project.trim_height_in,
            "has_bleed": project.has_bleed,
            "paper_type": project.paper_type,
            "cover_finish": project.cover_finish,
            "pages": [cls.serialize_page(p) for p in project.pages],
            "assets": [cls.serialize_asset(a) for a in project.assets],
            "export_profiles": [cls.serialize_export_profile(ep) for ep in project.export_profiles],
            "custom_settings": project.custom_settings,
            "created_at": project.created_at.isoformat(),
            "modified_at": project.modified_at.isoformat(),
            "version": project.version,
            "schema_version": project.schema_version
        }

    @classmethod
    def _parse_id(cls, raw_id: Any) -> Any:
        if raw_id is None:
            return UUID(int=0)
        if isinstance(raw_id, int):
            return raw_id
        if isinstance(raw_id, str):
            if raw_id.isdigit():
                return int(raw_id)
            try:
                return UUID(raw_id)
            except ValueError:
                return raw_id
        return raw_id

    @classmethod
    def deserialize_project(cls, data: Dict[str, Any]) -> BookProject:
        """Deserializes a dictionary back into a full BookProject aggregate root."""
        created_str = data.get("created_at")
        modified_str = data.get("modified_at")
        
        # Load sub-components
        metadata_dict = data.get("metadata", {})
        pages_list = data.get("pages", [])
        assets_list = data.get("assets", [])
        export_profiles_list = data.get("export_profiles", [])

        return BookProject(
            id=cls._parse_id(data.get("id")),
            name=data.get("name", "New Project"),
            book_type=data.get("book_type", "Coloring Book"),
            metadata=cls.deserialize_metadata(metadata_dict),
            trim_width_in=data.get("trim_width_in", 8.5),
            trim_height_in=data.get("trim_height_in", 11.0),
            has_bleed=data.get("has_bleed", False),
            paper_type=data.get("paper_type", "White"),
            cover_finish=data.get("cover_finish", "Matte"),
            pages=[cls.deserialize_page(p) for p in pages_list],
            assets=[cls.deserialize_asset(a) for a in assets_list],
            export_profiles=[cls.deserialize_export_profile(ep) for ep in export_profiles_list],
            custom_settings=data.get("custom_settings", {}),
            created_at=datetime.fromisoformat(created_str) if created_str else datetime.utcnow(),
            modified_at=datetime.fromisoformat(modified_str) if modified_str else datetime.utcnow(),
            version=data.get("version", "1.0.0"),
            schema_version=data.get("schema_version", "8.0.0")
        )

