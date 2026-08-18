import os
from typing import List, Dict, Any, Optional
from uuid import UUID
from PIL import Image

from book_builder.interfaces.services import IComplianceService
from book_builder.models.book import BookProject
from book_builder.models.page import Page
from models.compliance_result import Issue

class KDPValidator(IComplianceService):
    """
    KDP pre-flight validation checker that audits page counts, bleed settings,
    safe zones, standard trim dimensions, image DPI, and fonts.
    """

    # KDP Standard Trim Sizes in inches (Width, Height)
    STANDARD_TRIM_SIZES = {
        (5.0, 8.0), (5.25, 8.0), (5.5, 8.5), (6.0, 9.0),
        (5.06, 7.81), (6.14, 9.21), (6.69, 9.61), (7.0, 10.0),
        (7.44, 9.69), (7.5, 9.25), (8.0, 10.0), (8.5, 8.5),
        (8.25, 6.0), (8.25, 8.25), (8.5, 11.0),
        (8.27, 11.69), # A4
        (5.83, 8.27)   # A5
    }

    def audit_margins(self, page: Page, is_bleed: bool) -> List[Issue]:
        """
        Validates page element coordinates (specifically text blocks) against safety margins.
        """
        issues = []
        w = page.width_pt
        h = page.height_pt
        
        # Resolve left and right margins based on odd/even page numbering
        is_odd = (page.page_number % 2 != 0)
        left_margin = page.margin_inside_pt if is_odd else page.margin_outside_pt
        right_margin = page.margin_outside_pt if is_odd else page.margin_inside_pt
        
        x_min = left_margin
        x_max = w - right_margin
        y_min = page.margin_bottom_pt
        y_max = h - page.margin_top_pt
        
        # Check text blocks
        for i, text_block in enumerate(page.text_blocks):
            text = text_block.get("text", "")
            geom = text_block.get("geometry", {})
            x = geom.get("x", 0.0)
            y = geom.get("y", 0.0)
            width = geom.get("width", 0.0)
            height = geom.get("height", 0.0)
            
            # Allow minor floating-point tolerance (0.01 pt)
            if x < (x_min - 0.01) or (x + width) > (x_max + 0.01) or y < (y_min - 0.01) or (y + height) > (y_max + 0.01):
                issues.append(Issue(
                    severity="ERROR",
                    category="Interior",
                    rule_name="Safe Margin Violation",
                    explanation=f"Page {page.page_number}: Text block '{text[:15]}...' extends into the KDP safe margin zone.",
                    suggested_fix=f"Adjust coordinates to stay inside X: [{x_min:.1f}, {x_max:.1f}] and Y: [{y_min:.1f}, {y_max:.1f}]."
                ))
                
        # Also check custom vector text blocks if any
        for shape in page.vector_objects:
            if shape.get("shape_type") == "text_block":
                text = shape.get("text", "")
                geom = shape.get("geometry", {})
                x = geom.get("x", 0.0)
                y = geom.get("y", 0.0)
                width = geom.get("width", 0.0)
                height = geom.get("height", 0.0)
                if x < (x_min - 0.01) or (x + width) > (x_max + 0.01) or y < (y_min - 0.01) or (y + height) > (y_max + 0.01):
                    issues.append(Issue(
                        severity="ERROR",
                        category="Interior",
                        rule_name="Safe Margin Violation",
                        explanation=f"Page {page.page_number}: Vector text block '{text[:15]}...' violates margins.",
                        suggested_fix="Move the text block further inside the page margins."
                    ))
                    
        return issues

    def audit_page_count(self, book_project: BookProject) -> List[Issue]:
        """
        Validates page counts against KDP paperback specifications.
        """
        issues = []
        page_count = len(book_project.pages)
        
        # Black & white or color minimum / maximum range
        if page_count < 24:
            issues.append(Issue(
                severity="ERROR",
                category="Project",
                rule_name="Insufficient Pages",
                explanation=f"Project contains {page_count} pages. KDP requires at least 24 pages for paperbacks.",
                suggested_fix="Add more pages to the project to reach at least 24."
            ))
        elif page_count > 828:
            issues.append(Issue(
                severity="ERROR",
                category="Project",
                rule_name="Excessive Pages",
                explanation=f"Project contains {page_count} pages. Maximum KDP page count is 828 pages.",
                suggested_fix="Reduce the page count of the project."
            ))
            
        if page_count % 2 != 0:
            issues.append(Issue(
                severity="WARNING",
                category="Project",
                rule_name="Odd Page Count",
                explanation=f"Project has an odd number of pages ({page_count}). KDP will append a blank page, which shifts spreads.",
                suggested_fix="Add a blank page to ensure even page spread layout."
            ))
            
        return issues

    def audit_image_dpi(self, asset: Any) -> Optional[Issue]:
        """
        Validates image asset file resolutions.
        """
        if not hasattr(asset, "file_path") or not os.path.exists(asset.file_path):
            return Issue(
                severity="ERROR",
                category="Images",
                rule_name="Missing Image Asset",
                explanation=f"Asset '{getattr(asset, 'name', 'Unknown')}' has a missing or broken file path.",
                suggested_fix="Re-import the image or fix the reference path."
            )
            
        try:
            dpi = getattr(asset, "dpi", 300)
            if dpi < 300:
                return Issue(
                    severity="WARNING",
                    category="Images",
                    rule_name="Low Image Resolution",
                    explanation=f"Asset '{asset.name}' has a resolution of {dpi} DPI. Amazon recommends at least 300 DPI.",
                    suggested_fix="Replace with a higher resolution image."
                )
        except Exception as e:
            return Issue(
                severity="ERROR",
                category="Images",
                rule_name="Asset Audit Failed",
                explanation=f"Could not read asset '{getattr(asset, 'name', 'Unknown')}': {e}",
                suggested_fix="Re-save or convert the image."
            )
        return None

    def validate_bleed(self, book_project: BookProject) -> List[Issue]:
        """
        Validates page-level dimension compliance based on the global bleed setting.
        For bleed, width must be trim_width + 0.125 inches and height must be trim_height + 0.25 inches.
        """
        issues = []
        has_bleed = book_project.has_bleed
        trim_w = book_project.trim_width_in
        trim_h = book_project.trim_height_in
        
        # Expected width and height in points
        if has_bleed:
            expected_w_pt = (trim_w + 0.125) * 72.0
            expected_h_pt = (trim_h + 0.250) * 72.0
        else:
            expected_w_pt = trim_w * 72.0
            expected_h_pt = trim_h * 72.0
            
        for page in book_project.pages:
            # Allow minor float precision issues (within 0.1 pt)
            if abs(page.width_pt - expected_w_pt) > 0.1 or abs(page.height_pt - expected_h_pt) > 0.1:
                issues.append(Issue(
                    severity="ERROR",
                    category="Interior",
                    rule_name="Dimension Mismatch",
                    explanation=(
                        f"Page {page.page_number} dimensions ({page.width_pt/72.0:.3f}\"x{page.height_pt/72.0:.3f}\") "
                        f"do not match the expected project size ({expected_w_pt/72.0:.3f}\"x{expected_h_pt/72.0:.3f}\") "
                        f"with bleed={has_bleed}."
                    ),
                    suggested_fix="Resize page dimensions to match project configuration."
                ))
        return issues

    def validate_trim_size(self, book_project: BookProject) -> List[Issue]:
        """
        Validates if the project trim size is an official KDP paperback standard size.
        """
        issues = []
        size = (book_project.trim_width_in, book_project.trim_height_in)
        if size not in self.STANDARD_TRIM_SIZES:
            issues.append(Issue(
                severity="WARNING",
                category="Project",
                rule_name="Non-Standard Trim Size",
                explanation=f"Trim size {size[0]} x {size[1]} inches is not standard for KDP paperbacks.",
                suggested_fix="Select a standard KDP trim size from the project configuration."
            ))
        return issues

    def validate_missing_images_and_fonts(self, book_project: BookProject) -> List[Issue]:
        """
        Scans all pages for missing image files or unavailable fonts.
        """
        issues = []
        
        for page in book_project.pages:
            # Check page images
            for img_obj in page.images:
                path = img_obj.get("file_path", "")
                if not path or not os.path.exists(path):
                    issues.append(Issue(
                        severity="ERROR",
                        category="Images",
                        rule_name="Missing Image",
                        explanation=f"Page {page.page_number}: Referenced image file '{os.path.basename(path)}' not found.",
                        suggested_fix=f"Add the image file back to path: {path}"
                    ))
                    
            # Check page text block fonts
            for text in page.text_blocks:
                font_name = text.get("properties", {}).get("font", "")
                if font_name and not self._is_font_available(font_name):
                    issues.append(Issue(
                        severity="WARNING",
                        category="Metadata",
                        rule_name="Unavailable Font",
                        explanation=f"Page {page.page_number}: Font '{font_name}' might not be available at runtime. System default fallback will be used.",
                        suggested_fix="Install the custom font or change text blocks to Arial or Helvetica."
                    ))
                    
        return issues

    def calculate_spine_width(self, pages: int, paper_type: str) -> float:
        """
        Calculates expected KDP cover spine width in inches.
        """
        # Spine factors per page
        factors = {
            "white": 0.002252,
            "cream": 0.0025,
            "color": 0.002347
        }
        factor = factors.get(paper_type.lower(), 0.002252)
        return pages * factor

    def validate_cover_dimensions(self, cover_data: Dict[str, Any], trim_width: float, trim_height: float, pages: int, paper_type: str) -> List[Issue]:
        """
        Validates if cover dimensions match KDP formulas based on interior page count.
        """
        issues = []
        
        # Parse dimensions from cover_data
        full_width_px = cover_data.get("full_width_px")
        full_height_px = cover_data.get("full_height_px")
        
        if not full_width_px or not full_height_px:
            # Try parsing from raw layout coordinates
            dims = cover_data.get("dims", {})
            full_width_px = dims.get("full_width_px")
            full_height_px = dims.get("full_height_px")
            
        if not full_width_px or not full_height_px:
            issues.append(Issue(
                severity="ERROR",
                category="Cover",
                rule_name="Missing Cover Dimensions",
                explanation="Cover layout contains no width/height coordinates for verification.",
                suggested_fix="Re-initialize the cover template to calculate sizes."
            ))
            return issues
            
        # Re-calculate correct spine and cover dimensions (at 300 DPI)
        spine_in = self.calculate_spine_width(pages, paper_type)
        expected_w_in = 0.125 + trim_width + spine_in + trim_width + 0.125
        expected_h_in = 0.125 + trim_height + 0.125
        
        expected_w_px = int(expected_w_in * 300)
        expected_h_px = int(expected_h_in * 300)
        
        # Validate with +/- 5 pixels tolerance
        if abs(full_width_px - expected_w_px) > 5:
            issues.append(Issue(
                severity="ERROR",
                category="Cover",
                rule_name="Cover Width Error",
                explanation=f"Cover width ({full_width_px} px) does not match KDP requirement ({expected_w_px} px at 300 DPI) for {pages} pages.",
                suggested_fix="Update the cover page count setting and regenerate the template."
            ))
            
        if abs(full_height_px - expected_h_px) > 5:
            issues.append(Issue(
                severity="ERROR",
                category="Cover",
                rule_name="Cover Height Error",
                explanation=f"Cover height ({full_height_px} px) does not match KDP requirement ({expected_h_px} px at 300 DPI).",
                suggested_fix="Adjust the cover trim size configurations."
            ))
            
        return issues

    def run_full_preflight_audit(self, project: BookProject, cover_design: Optional[Dict[str, Any]] = None) -> List[Issue]:
        """
        Runs the complete suite of validations against a BookProject.
        """
        issues = []
        
        # 1. Page count audit
        issues.extend(self.audit_page_count(project))
        
        # 2. Bleed validation
        issues.extend(self.validate_bleed(project))
        
        # 3. Trim size standard
        issues.extend(self.validate_trim_size(project))
        
        # 4. Safe margin checks on each page
        for page in project.pages:
            issues.extend(self.audit_margins(page, project.has_bleed))
            
        # 5. Missing images / fonts
        issues.extend(self.validate_missing_images_and_fonts(project))
        
        # 6. Asset DPI audits
        for asset in project.assets:
            img_issue = self.audit_image_dpi(asset)
            if img_issue:
                issues.append(img_issue)
                
        # 7. Cover dimension verification (if cover data is provided)
        if cover_design:
            # We assume cover_design contains a "dims" dict if saved, or directly the dimensions if from profile
            dims = cover_design.get("dims", {})
            cover_data = {
                "full_width_px": dims.get("full_width_px"),
                "full_height_px": dims.get("full_height_px"),
            }
            issues.extend(self.validate_cover_dimensions(
                cover_data, 
                project.trim_width_in, 
                project.trim_height_in, 
                len(project.pages), 
                project.paper_type
            ))
            
        # 8. Blank pages check
        for page in project.pages:
            if len(page.text_blocks) == 0 and len(page.vector_objects) == 0 and len(page.images) == 0:
                issues.append(Issue(
                    severity="WARNING",
                    category="Interior",
                    rule_name="Blank Page Detected",
                    explanation=f"Page {page.page_number} is completely blank (contains no text, shapes, or images).",
                    suggested_fix="Place content on this page or delete it if it is redundant."
                ))

        # 9. Metadata field validation
        meta = project.metadata
        if (not meta.title or not meta.title.strip()) and (not project.name or not project.name.strip()):
            issues.append(Issue(
                severity="ERROR",
                category="Metadata",
                rule_name="Missing Book Title",
                explanation="The project metadata does not specify a book title.",
                suggested_fix="Configure a title under project metadata properties."
            ))
        if not meta.author or not meta.author.strip():
            issues.append(Issue(
                severity="WARNING",
                category="Metadata",
                rule_name="Missing Book Author",
                explanation="The project metadata does not specify an author name.",
                suggested_fix="Set an author name to print correctly on copyright areas."
            ))

        # 10. PDF compatibility and Color Mode validation
        # Print resolution and PDF compatibility checks
        for profile in project.export_profiles:
            if profile.dpi < 300:
                issues.append(Issue(
                    severity="WARNING",
                    category="Project",
                    rule_name="Low Export Resolution Preset",
                    explanation=f"Profile '{profile.profile_name}' uses {profile.dpi} DPI. Standard KDP publications require at least 300 DPI.",
                    suggested_fix="Change resolution to 300 DPI for print quality."
                ))
            if profile.color_space.upper() not in ("CMYK", "GRAYSCALE") and project.book_type in ("Coloring Book", "Activity Book"):
                issues.append(Issue(
                    severity="WARNING",
                    category="Project",
                    rule_name="RGB Color Mode Preset",
                    explanation=f"Profile '{profile.profile_name}' uses RGB. For KDP print validation, CMYK color space is recommended.",
                    suggested_fix="Set target color space to CMYK."
                ))
            
        return issues

    def _is_font_available(self, font_name: str) -> bool:
        # Simplistic check - standard PIL fonts, system fonts check fallback
        font_name_lower = font_name.lower()
        if font_name_lower in ["arial", "helvetica", "times new roman", "courier", "default", "default.ttf", "arial.ttf"]:
            return True
        # Check standard path
        paths_to_check = [
            font_name,
            os.path.join("C:\\Windows\\Fonts", font_name),
            os.path.join("C:\\Windows\\Fonts", font_name + ".ttf"),
            os.path.join("C:\\Windows\\Fonts", font_name + ".otf")
        ]
        return any(os.path.exists(p) for p in paths_to_check)

# Register the validation engine in DI container
from book_builder.container import Container
Container().register(IComplianceService, KDPValidator())
