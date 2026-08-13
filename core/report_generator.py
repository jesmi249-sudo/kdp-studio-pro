import json
import os
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from models.compliance_result import ComplianceResult
from core.logger import get_logger

logger = get_logger(__name__)

class ReportGenerator:
    @staticmethod
    def export_json(result: ComplianceResult, output_path: str) -> bool:
        try:
            data = {
                "health_score": result.health_score,
                "status": result.status_message,
                "issues": [
                    {
                        "severity": i.severity,
                        "category": i.category,
                        "rule": i.rule_name,
                        "explanation": i.explanation,
                        "suggested_fix": i.suggested_fix
                    } for i in result.issues
                ]
            }
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4)
            return True
        except Exception as e:
            logger.error(f"Failed to export JSON report: {e}")
            return False

    @staticmethod
    def export_html(result: ComplianceResult, output_path: str) -> bool:
        try:
            html = f"""
            <html>
            <head>
                <title>KDP Compliance Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    h1 {{ color: #333; }}
                    .score {{ font-size: 24px; font-weight: bold; margin-bottom: 20px; }}
                    .issue {{ border: 1px solid #ccc; padding: 15px; margin-bottom: 10px; border-radius: 5px; }}
                    .INFO {{ border-left: 5px solid #2196F3; }}
                    .WARNING {{ border-left: 5px solid #FFC107; }}
                    .ERROR {{ border-left: 5px solid #F44336; }}
                    .CRITICAL {{ border-left: 5px solid #9C27B0; }}
                    .title {{ font-weight: bold; font-size: 18px; }}
                    .severity {{ font-weight: bold; padding-right: 10px; }}
                </style>
            </head>
            <body>
                <h1>KDP Compliance Report</h1>
                <div class="score">Health Score: {result.health_score}/100 - {result.status_message}</div>
            """
            
            for i in result.issues:
                html += f"""
                <div class="issue {i.severity}">
                    <span class="severity">{i.severity}</span>
                    <span class="title">[{i.category}] {i.rule_name}</span>
                    <p><strong>Explanation:</strong> {i.explanation}</p>
                    <p><strong>Suggested Fix:</strong> {i.suggested_fix}</p>
                </div>
                """
                
            html += "</body></html>"
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            return True
        except Exception as e:
            logger.error(f"Failed to export HTML report: {e}")
            return False

    @staticmethod
    def export_pdf(result: ComplianceResult, output_path: str) -> bool:
        try:
            c = canvas.Canvas(output_path, pagesize=letter)
            width, height = letter
            y = height - 50
            
            c.setFont("Helvetica-Bold", 20)
            c.drawString(50, y, "KDP Compliance Report")
            y -= 30
            
            c.setFont("Helvetica", 14)
            c.drawString(50, y, f"Health Score: {result.health_score}/100 - {result.status_message}")
            y -= 40
            
            c.setFont("Helvetica", 10)
            for i in result.issues:
                if y < 100:
                    c.showPage()
                    y = height - 50
                    c.setFont("Helvetica", 10)
                    
                c.setFont("Helvetica-Bold", 10)
                c.drawString(50, y, f"[{i.severity}] {i.category}: {i.rule_name}")
                y -= 15
                
                c.setFont("Helvetica", 10)
                c.drawString(70, y, f"Explanation: {i.explanation}")
                y -= 15
                c.drawString(70, y, f"Fix: {i.suggested_fix}")
                y -= 25
                
            c.save()
            return True
        except Exception as e:
            logger.error(f"Failed to export PDF report: {e}")
            return False
