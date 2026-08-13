import json
import csv
import os
from typing import Dict, List
from core.logger import get_logger

logger = get_logger(__name__)

class MetadataGenerator:
    """Generates and exports KDP metadata in JSON and CSV formats."""
    
    def __init__(self):
        self.metadata = {
            "title": "",
            "subtitle": "",
            "author": "",
            "description": "",
            "keywords": [],
            "categories": [],
            "series": "",
            "language": "English",
            "publisher": ""
        }

    def set_field(self, field: str, value):
        """Sets a metadata field."""
        if field in self.metadata:
            self.metadata[field] = value
        else:
            logger.warning(f"Attempted to set unknown metadata field: {field}")

    def get_metadata(self) -> Dict:
        """Returns the current metadata dictionary."""
        return self.metadata

    def export_json(self, output_path: str) -> bool:
        """Exports the metadata to a JSON file."""
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=4, ensure_ascii=False)
            logger.info(f"Metadata exported to JSON: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export metadata to JSON: {e}")
            return False

    def export_csv(self, output_path: str) -> bool:
        """Exports the metadata to a CSV file."""
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write headers
                writer.writerow(["Field", "Value"])
                
                # Write data
                for key, value in self.metadata.items():
                    if isinstance(value, list):
                        # Join lists with a semicolon for CSV
                        value = "; ".join(value)
                    writer.writerow([key.capitalize(), str(value)])
                    
            logger.info(f"Metadata exported to CSV: {output_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export metadata to CSV: {e}")
            return False
