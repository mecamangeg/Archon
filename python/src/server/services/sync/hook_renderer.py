"""
Git Hook Template Renderer

Renders git hook templates with project-specific configuration.
Supports placeholder replacement for dynamic hook generation.
"""

import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class HookRenderer:
    """
    Service for rendering git hook templates with project configuration.

    Features:
    - Simple placeholder-based template rendering
    - Template validation
    - Support for multiple hook types
    - Error handling for missing templates
    """

    def __init__(self, templates_dir: Optional[Path] = None):
        """
        Initialize the HookRenderer.

        Args:
            templates_dir: Path to templates directory. If None, uses default location.
        """
        if templates_dir is None:
            # Default to templates directory relative to this file
            self.templates_dir = Path(__file__).parent / "templates"
        else:
            self.templates_dir = Path(templates_dir)

        logger.debug(f"HookRenderer initialized with templates_dir: {self.templates_dir}")

    async def render_post_commit_hook(
        self,
        project_id: str,
        archon_api_url: str
    ) -> str:
        """
        Render the post-commit hook template with project configuration.

        Args:
            project_id: UUID of the project
            archon_api_url: Base URL of the Archon API (e.g., http://localhost:8000)

        Returns:
            Rendered hook content as string

        Raises:
            FileNotFoundError: If template file doesn't exist
            ValueError: If rendering fails
        """
        try:
            # Load template
            template_path = self.templates_dir / "post-commit-hook.template"

            if not template_path.exists():
                raise FileNotFoundError(f"Template not found: {template_path}")

            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()

            # Render template with placeholders
            rendered_content = self._replace_placeholders(
                template_content,
                {
                    "PROJECT_ID": project_id,
                    "ARCHON_API_URL": archon_api_url
                }
            )

            # Validate rendered content
            if not self.validate_template(rendered_content):
                raise ValueError("Template validation failed after rendering")

            logger.info(f"Rendered post-commit hook for project {project_id}")

            return rendered_content

        except Exception as e:
            logger.error(f"Failed to render post-commit hook: {e}")
            raise

    async def validate_template(self, content: str) -> bool:
        """
        Validate that template content is properly rendered.

        Checks:
        - No unreplaced placeholders remain
        - Content is not empty
        - Has Python shebang (for Python hooks)
        - Has required hook structure

        Args:
            content: Rendered template content

        Returns:
            True if valid, False otherwise
        """
        try:
            # Check if empty
            if not content or not content.strip():
                logger.error("Template validation failed: Content is empty")
                return False

            # Check for unreplaced placeholders
            if "{{PROJECT_ID}}" in content:
                logger.error("Template validation failed: PROJECT_ID placeholder not replaced")
                return False

            if "{{ARCHON_API_URL}}" in content:
                logger.error("Template validation failed: ARCHON_API_URL placeholder not replaced")
                return False

            # Check for Python shebang
            if not content.strip().startswith("#!/usr/bin/env python"):
                logger.warning("Template validation: Missing Python shebang")
                # Not a hard failure, just a warning

            # Check for main entry point
            if "if __name__ ==" not in content:
                logger.warning("Template validation: Missing main entry point")

            # Check for essential functions
            required_functions = ["get_changed_files", "trigger_sync", "main"]
            for func in required_functions:
                if f"def {func}" not in content:
                    logger.error(f"Template validation failed: Missing function {func}")
                    return False

            logger.debug("Template validation passed")
            return True

        except Exception as e:
            logger.error(f"Template validation error: {e}")
            return False

    def _replace_placeholders(
        self,
        template: str,
        replacements: Dict[str, str]
    ) -> str:
        """
        Replace placeholders in template with actual values.

        Placeholders format: {{PLACEHOLDER_NAME}}

        Args:
            template: Template content with placeholders
            replacements: Dict mapping placeholder names to values

        Returns:
            Template with placeholders replaced
        """
        result = template

        for placeholder, value in replacements.items():
            # Replace {{PLACEHOLDER}} with value
            result = result.replace(f"{{{{{placeholder}}}}}", value)

        return result

    async def get_available_templates(self) -> Dict[str, Any]:
        """
        Get list of available hook templates.

        Returns:
            Dict with template information
        """
        try:
            if not self.templates_dir.exists():
                logger.warning(f"Templates directory does not exist: {self.templates_dir}")
                return {"templates": []}

            templates = []

            for template_file in self.templates_dir.glob("*.template"):
                # Read first line to get description
                with open(template_file, 'r', encoding='utf-8') as f:
                    first_line = f.readline().strip()
                    description = first_line.lstrip('#').strip() if first_line.startswith('#') else ""

                templates.append({
                    "name": template_file.stem,
                    "file": template_file.name,
                    "path": str(template_file),
                    "description": description,
                    "size_bytes": template_file.stat().st_size
                })

            return {
                "templates_dir": str(self.templates_dir),
                "templates": templates,
                "count": len(templates)
            }

        except Exception as e:
            logger.error(f"Failed to get available templates: {e}")
            return {"templates": [], "error": str(e)}

    async def render_template(
        self,
        template_name: str,
        context: Dict[str, str]
    ) -> str:
        """
        Generic template rendering method.

        Args:
            template_name: Name of the template file (without .template extension)
            context: Dict of placeholder values to replace

        Returns:
            Rendered template content

        Raises:
            FileNotFoundError: If template doesn't exist
            ValueError: If rendering fails
        """
        try:
            template_path = self.templates_dir / f"{template_name}.template"

            if not template_path.exists():
                raise FileNotFoundError(f"Template not found: {template_name}")

            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()

            # Replace all placeholders
            rendered_content = self._replace_placeholders(template_content, context)

            logger.info(f"Rendered template: {template_name}")

            return rendered_content

        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            raise
