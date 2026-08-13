# KDP Compliance Checker

The KDP Compliance Checker is a professional pre-flight inspection tool for KDP Studio Pro. It analyzes the entire project state (Metadata, Interior, Cover, and Assets) and ensures everything meets Amazon KDP's strict publishing guidelines before export.

## Architecture Overview

The module uses a clear separation of concerns:

- **`models/compliance_result.py`**: Defines `Issue` and `ComplianceResult` dataclasses. The result holds the health score and aggregated list of issues.
- **`core/inspection_rules.py`**: Contains modular rules (`check_metadata`, `check_interior`, `check_cover_and_images`, `check_project_files`). Each function queries the relevant UI module for its state and yields `Issue` instances.
- **`core/compliance_checker.py`**: The orchestrator that coordinates all checks, handles unexpected errors, and manages the final health score tally.
- **`core/report_generator.py`**: Handles exporting the `ComplianceResult` to PDF (using ReportLab), HTML, and JSON.
- **`ui/views/compliance_view.py`**: The user interface featuring an interactive progress bar, filterable issue list with color-coded severity, and export controls.

## Health Score & Severity

Every project starts at `100/100`. Deductions are made based on the severity of the issues found:
- **CRITICAL** (-30 points): e.g., Module completely missing, severe architecture failure.
- **ERROR** (-15 points): e.g., Missing Book Title, Page count < 24. Prevents publishing.
- **WARNING** (-5 points): e.g., Low DPI Image, Missing Description. Should be addressed but might still publish.
- **INFO** (0 points): General information or good practices.

## Inspection Rules Included

### Project & Metadata
- **Missing Title/Author**: Validates required fields exist.
- **Character Limits**: Ensures Title/Subtitle are under 200 characters.
- **Keywords**: Ensures between 1 and 7 keywords, checks for duplicates, and validates length (<50 chars).
- **Description**: Warns if the description is blank.

### Interior
- **Page Count Limits**: Validates pages are >= 24 and <= 828.
- **Even/Odd Pages**: Warns if the page count is odd (best practice for KDP is even spreads).
- **Margin Validation**: Ensures outer margins are >= 0.25 inches. Dynamically scales required inside margin requirements based on total page count (0.375" up to 0.75").

### Cover & Images
- **Empty Cover**: Triggers an error if the canvas contains no items.
- **Image Integrity**: Checks that all images referenced on the cover actually exist on the user's disk.
- **Image Formatting**: Warns if the image is an unsupported format, has transparency, or if the DPI is < 300.
- **Corrupt Image Detection**: Catches image parsing errors.

## Testing Guide

To validate changes to this module:
1. Run `python -m unittest tests/test_compliance.py`.
2. The tests use mock objects that replicate the UI state, allowing fast headless testing of business logic rules without loading CustomTkinter.

## Future Enhancements
- **Deep PDF Analysis**: Implement PyPDF2/pdfplumber to scan existing external interior PDFs rather than just checking generator parameters.
- **Text Safe Zone Analysis**: Compute exact intersections of text objects and the cover safe zone bounding box.
- **CMYK vs RGB Checks**: Advanced image color space profiling.
