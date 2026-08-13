from models.compliance_result import ComplianceResult
from core.inspection_rules import check_metadata, check_interior, check_cover_and_images, check_project_files
from core.logger import get_logger

logger = get_logger(__name__)

class ComplianceChecker:
    def __init__(self, app):
        self.app = app

    def run_inspection(self) -> ComplianceResult:
        logger.info("Starting KDP Compliance Inspection...")
        result = ComplianceResult()
        
        try:
            # 1. Metadata Checks
            meta_issues = check_metadata(self.app)
            for issue in meta_issues:
                result.add_issue(issue)
                
            # 2. Interior Checks
            interior_issues = check_interior(self.app)
            for issue in interior_issues:
                result.add_issue(issue)
                
            # 3. Cover & Images Checks
            cover_issues = check_cover_and_images(self.app)
            for issue in cover_issues:
                result.add_issue(issue)
                
            # 4. Project Files Checks
            file_issues = check_project_files(self.app)
            for issue in file_issues:
                result.add_issue(issue)
                
        except Exception as e:
            logger.error(f"Error during compliance inspection: {e}")
            from models.compliance_result import Issue
            result.add_issue(Issue("CRITICAL", "Project", "Inspection Failed", f"An unexpected error occurred: {e}", "Check application logs."))

        logger.info(f"Inspection complete. Health Score: {result.health_score}")
        return result
