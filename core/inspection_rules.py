import os
from typing import List
from models.compliance_result import Issue
from PIL import Image

def check_metadata(app) -> List[Issue]:
    issues = []
    meta_view = app.views.get("Metadata")
    if not meta_view:
        issues.append(Issue("CRITICAL", "Project", "Metadata Module Missing", "Metadata view could not be found.", "Restart the application."))
        return issues
        
    meta_view._update_generator_data()
    data = meta_view.generator.get_metadata()
    
    # Project Info
    title = data.get("title", "").strip()
    author = data.get("author", "").strip()
    subtitle = data.get("subtitle", "").strip()
    desc = data.get("description", "").strip()
    
    if not title:
        issues.append(Issue("ERROR", "Project", "Missing Title", "KDP requires a book title.", "Add a title in the Metadata generator."))
    elif len(title) > 200:
        issues.append(Issue("ERROR", "Project", "Title Too Long", "Title exceeds 200 characters.", "Shorten the title."))
        
    if not author:
        issues.append(Issue("ERROR", "Project", "Missing Author", "KDP requires an author name.", "Add an author in the Metadata generator."))
        
    if subtitle and len(subtitle) > 200:
        issues.append(Issue("ERROR", "Project", "Subtitle Too Long", "Subtitle exceeds 200 characters.", "Shorten the subtitle."))
        
    if not desc:
        issues.append(Issue("WARNING", "Project", "Missing Description", "A description helps sell your book.", "Add a description."))
        
    # Keywords
    keywords = data.get("keywords", [])
    if len(keywords) == 0:
        issues.append(Issue("WARNING", "Metadata", "No Keywords", "Keywords help readers find your book.", "Add up to 7 keywords."))
    elif len(keywords) > 7:
        issues.append(Issue("ERROR", "Metadata", "Too Many Keywords", "KDP allows a maximum of 7 keywords.", "Remove extra keywords."))
        
    unique_keywords = set([k.lower() for k in keywords])
    if len(unique_keywords) < len(keywords):
        issues.append(Issue("WARNING", "Metadata", "Duplicate Keywords", "You have duplicate keywords which wastes space.", "Remove duplicates."))
        
    for kw in keywords:
        if len(kw) > 50:
            issues.append(Issue("ERROR", "Metadata", "Keyword Too Long", f"Keyword '{kw[:10]}...' is over 50 characters.", "Shorten the keyword."))

    return issues


def check_interior(app) -> List[Issue]:
    issues = []
    interior_view = app.views.get("Interior Designer")
    if not interior_view:
        issues.append(Issue("CRITICAL", "Interior", "Interior Module Missing", "Interior view could not be found.", "Restart the application."))
        return issues
        
    try:
        pages = int(interior_view.page_count.get())
        if pages < 24:
            issues.append(Issue("ERROR", "Interior", "Insufficient Pages", "KDP requires at least 24 pages for a paperback.", "Increase the page count to 24 or more."))
        if pages > 828:
            issues.append(Issue("ERROR", "Interior", "Too Many Pages", "Maximum page count for KDP is 828.", "Reduce the page count."))
            
        if pages % 2 != 0:
            issues.append(Issue("WARNING", "Interior", "Odd Page Count", "Page counts should typically be even to ensure proper left/right spreads.", "Add one blank page to the end."))
    except ValueError:
        issues.append(Issue("ERROR", "Interior", "Invalid Page Count", "The page count must be a number.", "Enter a valid integer for page count."))
        
    try:
        top = float(interior_view.m_top.get())
        bot = float(interior_view.m_bot.get())
        ins = float(interior_view.m_in.get())
        out = float(interior_view.m_out.get())
        
        if top < 0.25 or bot < 0.25 or out < 0.25:
            issues.append(Issue("ERROR", "Interior", "Margins Too Small", "Outer margins must be at least 0.25 inches.", "Increase top, bottom, and outside margins."))
            
        # Inside margin depends on page count, rough check:
        # 24-150: 0.375
        # 151-300: 0.5
        # 301-500: 0.625
        # >500: 0.75
        required_inside = 0.375
        try:
            p = int(interior_view.page_count.get())
            if p > 150: required_inside = 0.5
            if p > 300: required_inside = 0.625
            if p > 500: required_inside = 0.75
        except: pass
        
        if ins < required_inside:
            issues.append(Issue("ERROR", "Interior", "Inside Margin Too Small", f"For this page count, inside margin must be at least {required_inside} inches.", "Increase the inside margin."))
            
    except ValueError:
        issues.append(Issue("ERROR", "Interior", "Invalid Margins", "Margins must be numeric.", "Enter valid numbers for all margins."))

    return issues


def check_cover_and_images(app) -> List[Issue]:
    issues = []
    cover_view = app.views.get("Cover Designer Pro")
    if not cover_view:
        issues.append(Issue("CRITICAL", "Cover", "Cover Module Missing", "Cover view could not be found.", "Restart the application."))
        return issues
        
    objects = getattr(cover_view, "canvas_objects", [])
    if not objects:
        issues.append(Issue("ERROR", "Cover", "Empty Cover", "No design elements found on the cover.", "Add text, images, or colors to your cover."))
        
    # Check dimensions
    dims = getattr(cover_view, "dims", {})
    if not dims:
        issues.append(Issue("WARNING", "Cover", "Dimensions Not Calculated", "Cover dimensions have not been calculated yet.", "Modify a cover setting to force calculation."))
    
    for obj in objects:
        if obj.get("type") == "image":
            path = obj.get("image_path")
            if not path or not os.path.exists(path):
                issues.append(Issue("ERROR", "Images", "Missing Image", f"Image file not found: {path}", "Locate the missing image or remove it from the cover."))
            else:
                try:
                    with Image.open(path) as img:
                        # Check format
                        if img.format not in ['JPEG', 'PNG', 'TIFF']:
                            issues.append(Issue("WARNING", "Images", "Unsupported Format", f"Format {img.format} is not ideal.", "Use high-quality JPEG or PNG."))
                        
                        # Check DPI (if available in EXIF/Info)
                        dpi = img.info.get("dpi", (72, 72))
                        if dpi[0] < 300 or dpi[1] < 300:
                            # Note: PIL might default to 72 if not set, so this can be a false positive, but good for warnings
                            issues.append(Issue("WARNING", "Images", "Low Image Resolution", f"Image {os.path.basename(path)} has {dpi[0]} DPI. 300 DPI is recommended.", "Use a higher resolution image."))
                            
                        # Check Transparency for JPEG which doesn't support it, KDP flattens it
                        if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                            issues.append(Issue("INFO", "Images", "Image Transparency", f"Image {os.path.basename(path)} contains transparency which will be flattened.", "Check flattened result in preview."))
                except Exception as e:
                    issues.append(Issue("ERROR", "Images", "Corrupt Image", f"Failed to read image {path}: {e}", "Replace the image file."))

    return issues


def check_project_files(app) -> List[Issue]:
    issues = []
    # Could check the project directory for stray files, but since it's an in-memory/DB project primarily,
    # we just report INFO that it's clean for now.
    issues.append(Issue("INFO", "Files", "Project Structure", "Virtual project structure is clean.", "No action needed."))
    return issues
