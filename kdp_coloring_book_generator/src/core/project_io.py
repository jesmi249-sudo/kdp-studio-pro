"""
Project I/O module for KDP Coloring Book Generator.
Handles saving, loading, and updating project state as JSON.
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from typing import Optional
import uuid

from .logger import get_logger

logger = get_logger("project_io")


class ProjectIO:
    """
    Manages project persistence: save, load, update, and export.
    
    Projects are stored as entries in a central projects.json file.
    Each project contains all form metadata and image paths.
    """

    def __init__(self, data_dir: Path):
        """
        Initialize ProjectIO with the data directory path.
        
        Args:
            data_dir: Path to the data directory (contains projects.json).
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True)
        self.projects_file = self.data_dir / "projects.json"

    def load_all_projects(self) -> list:
        """Load all projects from the JSON file."""
        if not self.projects_file.exists():
            return []
        try:
            with open(self.projects_file, "r", encoding="utf-8") as f:
                projects = json.load(f)
            logger.debug(f"Loaded {len(projects)} projects from {self.projects_file}")
            return projects
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Failed to load projects: {e}")
            return []

    def save_all_projects(self, projects: list):
        """Save the full projects list to JSON."""
        try:
            with open(self.projects_file, "w", encoding="utf-8") as f:
                json.dump(projects, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(projects)} projects to {self.projects_file}")
        except IOError as e:
            logger.error(f"Failed to save projects: {e}")
            raise

    def save_project(self, project_data: dict, projects: list) -> list:
        """
        Save or update a project in the projects list.
        
        If project_data has an 'id' that matches an existing project, update it.
        Otherwise, create a new project with a new ID.
        
        Args:
            project_data: The project dictionary to save.
            projects: The current list of all projects.
            
        Returns:
            Updated projects list.
        """
        project_id = project_data.get("id")
        now = datetime.now().isoformat()

        if project_id:
            # Try to find and update existing project
            for i, p in enumerate(projects):
                if p.get("id") == project_id:
                    project_data["modified_at"] = now
                    projects[i] = project_data
                    logger.info(f"Updated project: {project_data.get('name')} ({project_id})")
                    self.save_all_projects(projects)
                    return projects

        # Create new project
        if not project_id:
            project_data["id"] = str(uuid.uuid4())
        project_data["created_at"] = project_data.get("created_at", now)
        project_data["modified_at"] = now
        projects.append(project_data)
        logger.info(f"Created new project: {project_data.get('name')} ({project_data['id']})")
        self.save_all_projects(projects)
        return projects

    def delete_project(self, project_id: str, projects: list) -> list:
        """
        Delete a project by ID.
        
        Args:
            project_id: The project ID to delete.
            projects: Current projects list.
            
        Returns:
            Updated projects list.
        """
        projects = [p for p in projects if p.get("id") != project_id]
        self.save_all_projects(projects)
        logger.info(f"Deleted project: {project_id}")
        return projects

    def get_project_by_id(self, project_id: str, projects: list) -> Optional[dict]:
        """Find a project by its ID."""
        for p in projects:
            if p.get("id") == project_id:
                return p
        return None

    @staticmethod
    def build_generator_data(
        title: str,
        subtitle: str = "",
        author: str = "",
        theme: str = "",
        age_group: str = "Kids (4-8)",
        num_pages: str = "",
        trim_size: str = "8.5 x 11 inches (Letter)",
        bleed: str = "Yes",
        images: Optional[list] = None,
    ) -> dict:
        """
        Build a generator_data dictionary from form fields.
        
        Args:
            All form field values.
            
        Returns:
            Dictionary suitable for storing in project['generator_data'].
        """
        return {
            "title": title,
            "subtitle": subtitle,
            "author": author,
            "theme": theme,
            "age_group": age_group,
            "num_pages": num_pages,
            "trim_size": trim_size,
            "bleed": bleed,
            "images": images or [],
        }

    @staticmethod
    def build_project_dict(
        name: str,
        generator_data: dict,
        project_id: Optional[str] = None,
        description: str = "",
        status: str = "draft",
    ) -> dict:
        """
        Build a complete project dictionary.
        
        Args:
            name: Project name.
            generator_data: The generator state data.
            project_id: Existing ID (for updates) or None (for new).
            description: Project description.
            status: Project status.
            
        Returns:
            Complete project dictionary.
        """
        now = datetime.now().isoformat()
        images = generator_data.get("images", [])

        return {
            "id": project_id or str(uuid.uuid4()),
            "name": name,
            "description": description,
            "page_size": generator_data.get("trim_size", "8.5 x 11 inches (Letter)"),
            "author": generator_data.get("author", ""),
            "page_count": len(images),
            "status": status,
            "created_at": now,
            "modified_at": now,
            "generator_data": generator_data,
            "pages": [],
        }

    def export_project_bundle(self, project: dict, export_dir: str) -> str:
        """
        Export a project as a portable bundle (JSON + copies of images).
        
        Args:
            project: The project dictionary.
            export_dir: Directory to export to.
            
        Returns:
            Path to the exported bundle directory.
        """
        export_path = Path(export_dir)
        project_name = project.get("name", "untitled").replace(" ", "_")
        bundle_dir = export_path / f"{project_name}_bundle"
        bundle_dir.mkdir(parents=True, exist_ok=True)

        # Copy images
        images_dir = bundle_dir / "images"
        images_dir.mkdir(exist_ok=True)

        gen_data = project.get("generator_data", {})
        images = gen_data.get("images", [])
        new_image_paths = []

        for img_path in images:
            src = Path(img_path)
            if src.exists():
                dst = images_dir / src.name
                shutil.copy2(str(src), str(dst))
                new_image_paths.append(str(dst))
            else:
                logger.warning(f"Image not found during export: {img_path}")

        # Save project JSON with relative paths
        export_project = project.copy()
        export_gen_data = gen_data.copy()
        export_gen_data["images"] = [
            str(Path("images") / Path(p).name) for p in new_image_paths
        ]
        export_project["generator_data"] = export_gen_data

        json_path = bundle_dir / "project.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(export_project, f, indent=2, ensure_ascii=False)

        logger.info(f"Exported project bundle to: {bundle_dir}")
        return str(bundle_dir)
