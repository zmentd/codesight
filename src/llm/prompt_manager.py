"""Prompt management system for LLM interactions."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from utils.logging.logger_factory import LoggerFactory


@dataclass
class PromptTemplate:
    """Template for LLM prompts."""
    
    name: str
    description: str
    template: str
    variables: List[str]
    system_message: Optional[str] = None
    examples: Optional[List[Dict[str, str]]] = None
    
    def format(self, **kwargs: Any) -> str:
        """Format the template with provided variables."""
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise ValueError(f"Missing required variable: {e}") from e
    
    def validate_variables(self, variables: Dict[str, Any]) -> List[str]:
        """Validate that all required variables are provided."""
        missing = []
        for var in self.variables:
            if var not in variables:
                missing.append(var)
        return missing


class PromptManager:
    """
    Manager for LLM prompt templates and prompt engineering.
    
    Handles:
    - Loading prompt templates from files
    - Template variable substitution
    - Prompt optimization
    - Context management
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.logger = LoggerFactory.get_logger(__name__)
        self.templates: Dict[str, PromptTemplate] = {}
        self.templates_dir = config.get("templates_dir", "prompts")
        
        self._load_templates()
    
    def _load_templates(self) -> None:
        """Load prompt templates from files."""
        try:
            templates_path = Path(self.templates_dir)
            
            if not templates_path.exists():
                self.logger.warning("Templates directory not found: %s", templates_path)
                self._create_default_templates()
                return
            
            # Load YAML template files
            for template_file in templates_path.glob("*.yml"):
                self._load_template_file(template_file)
            
            for template_file in templates_path.glob("*.yaml"):
                self._load_template_file(template_file)
            
            self.logger.info("Loaded %d prompt templates", len(self.templates))
            
        except (OSError, IOError, ValueError) as e:
            self.logger.error("Failed to load templates: %s", e)
            self._create_default_templates()
    
    def _load_template_file(self, file_path: Path) -> None:
        """Load a single template file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                template_data = yaml.safe_load(f)
            
            template = PromptTemplate(
                name=template_data.get("name", file_path.stem),
                description=template_data.get("description", ""),
                template=template_data.get("template", ""),
                variables=template_data.get("variables", []),
                system_message=template_data.get("system_message"),
                examples=template_data.get("examples", [])
            )
            
            self.templates[template.name] = template
            
        except (OSError, IOError, ValueError, KeyError) as e:
            self.logger.error("Failed to load template file %s: %s", file_path, e)
    
    def _create_default_templates(self) -> None:
        """Create default templates if none are found."""
        default_templates = {
            "code_analysis": PromptTemplate(
                name="code_analysis",
                description="Analyze code structure and patterns",
                template="""
Analyze the following {language} code and provide a structured analysis:

```{language}
{code}
```

Please provide:
1. Component type (class, interface, enum, etc.)
2. Design patterns used
3. Framework dependencies
4. Key methods and their purposes
5. Potential issues or improvements
6. Dependencies on other components

Return the analysis as JSON with the following structure:
{{
    "component_type": "string",
    "design_patterns": ["string"],
    "framework_dependencies": ["string"],
    "key_methods": [{{"name": "string", "purpose": "string"}}],
    "issues": ["string"],
    "improvements": ["string"],
    "dependencies": ["string"]
}}
                """.strip(),
                variables=["language", "code"],
                system_message="You are an expert software architect analyzing code for modernization."
            ),
            
            "component_identification": PromptTemplate(
                name="component_identification",
                description="Identify software components in files",
                template="""
Analyze the following file and identify all software components:

File: {file_path}

```
{file_content}
```

Please identify:
1. All classes, interfaces, enums
2. Component types (Controller, Service, Repository, Entity, etc.)
3. Framework annotations
4. Configuration components
5. Dependencies between components

Return as JSON:
{{
    "components": [
        {{
            "name": "string",
            "type": "string",
            "framework_type": "string",
            "annotations": ["string"],
            "methods": ["string"],
            "dependencies": ["string"]
        }}
    ]
}}
                """.strip(),
                variables=["file_path", "file_content"],
                system_message="You are an expert in enterprise software architecture."
            ),
            
            "modernization_suggestions": PromptTemplate(
                name="modernization_suggestions",
                description="Suggest modernization approaches",
                template="""
Based on the following component analysis, suggest modernization approaches:

{analysis}

Please provide:
1. Legacy patterns identified
2. Modern alternatives
3. Migration strategies
4. Risk assessment
5. Priority recommendations

Return as JSON:
{{
    "legacy_patterns": ["string"],
    "modern_alternatives": [
        {{
            "pattern": "string",
            "replacement": "string",
            "benefits": ["string"]
        }}
    ],
    "migration_strategies": ["string"],
    "risks": ["string"],
    "priorities": [
        {{
            "item": "string",
            "priority": "high|medium|low",
            "effort": "string"
        }}
    ]
}}
                """.strip(),
                variables=["analysis"],
                system_message="You are a modernization specialist with expertise in legacy system migration."
            ),
            
            "architecture_analysis": PromptTemplate(
                name="architecture_analysis",
                description="Analyze overall project architecture",
                template="""
Analyze the following project structure and provide architectural insights:

{project_structure}

Please analyze:
1. Architectural patterns used
2. Layer separation
3. Component organization
4. Technology stack assessment
5. Scalability considerations
6. Maintainability factors

Return as JSON:
{{
    "architectural_patterns": ["string"],
    "layer_analysis": {{
        "presentation": "string",
        "business": "string",
        "data": "string"
    }},
    "technology_assessment": {{
        "current_stack": ["string"],
        "strengths": ["string"],
        "weaknesses": ["string"]
    }},
    "scalability": {{
        "current_level": "string",
        "bottlenecks": ["string"],
        "recommendations": ["string"]
    }},
    "maintainability": {{
        "score": "number",
        "factors": ["string"],
        "improvements": ["string"]
    }}
}}
                """.strip(),
                variables=["project_structure"],
                system_message="You are a senior software architect with expertise in enterprise systems."
            ),
            
            "business_logic_extraction": PromptTemplate(
                name="business_logic_extraction",
                description="Extract business logic from code",
                template="""
Extract and describe the business logic from the following code:

```
{code}
```

Please identify:
1. Business rules and constraints
2. Domain concepts
3. Workflow processes
4. Data validation logic
5. Integration points

Return as JSON:
{{
    "business_rules": ["string"],
    "domain_concepts": ["string"],
    "workflows": [
        {{
            "name": "string",
            "steps": ["string"],
            "inputs": ["string"],
            "outputs": ["string"]
        }}
    ],
    "validations": ["string"],
    "integrations": ["string"]
}}
                """.strip(),
                variables=["code"],
                system_message="You are a business analyst with deep technical knowledge."
            ),
            
            "migration_plan": PromptTemplate(
                name="migration_plan",
                description="Generate comprehensive migration plan",
                template="""
Based on the comprehensive analysis results, generate a detailed migration plan:

{analysis_results}

Please create:
1. Migration phases with timelines
2. Risk mitigation strategies
3. Resource requirements
4. Success criteria
5. Rollback plans

Return as JSON:
{{
    "phases": [
        {{
            "name": "string",
            "description": "string",
            "duration": "string",
            "activities": ["string"],
            "deliverables": ["string"],
            "dependencies": ["string"]
        }}
    ],
    "risks": [
        {{
            "risk": "string",
            "impact": "high|medium|low",
            "probability": "high|medium|low",
            "mitigation": "string"
        }}
    ],
    "resources": {{
        "team_size": "number",
        "skills_required": ["string"],
        "external_support": ["string"]
    }},
    "success_criteria": ["string"],
    "rollback_plans": ["string"]
}}
                """.strip(),
                variables=["analysis_results"],
                system_message="You are a project manager and technical lead specializing in legacy system modernization."
            )
        }
        
        self.templates.update(default_templates)
        self.logger.info("Created default prompt templates")
    
    def get_template(self, name: str) -> Optional[PromptTemplate]:
        """Get a template by name."""
        return self.templates.get(name)
    
    def list_templates(self) -> List[str]:
        """List all available template names."""
        return list(self.templates.keys())
    
    def format_prompt(self, template_name: str, **kwargs: Any) -> Dict[str, Any]:
        """
        Format a prompt template with variables.
        
        Args:
            template_name: Name of the template
            **kwargs: Variables to substitute
            
        Returns:
            Dictionary with formatted prompt and system message
        """
        template = self.get_template(template_name)
        if not template:
            raise ValueError(f"Template not found: {template_name}")
        
        # Validate variables
        missing_vars = template.validate_variables(kwargs)
        if missing_vars:
            raise ValueError(f"Missing required variables: {missing_vars}")
        
        # Format the template
        formatted_prompt = template.format(**kwargs)
        
        return {
            "prompt": formatted_prompt,
            "system_message": template.system_message
        }
    
    def add_template(self, template: PromptTemplate) -> None:
        """Add a new template."""
        self.templates[template.name] = template
        self.logger.info("Added template: %s", template.name)
    
    def remove_template(self, name: str) -> bool:
        """Remove a template."""
        if name in self.templates:
            del self.templates[name]
            self.logger.info("Removed template: %s", name)
            return True
        return False
    
    def save_template(self, template: PromptTemplate, file_path: Optional[str] = None) -> None:
        """Save a template to file."""
        if not file_path:
            templates_dir = Path(self.templates_dir)
            templates_dir.mkdir(exist_ok=True)
            actual_file_path = templates_dir / f"{template.name}.yml"
        else:
            actual_file_path = Path(file_path)
        
        template_data = {
            "name": template.name,
            "description": template.description,
            "template": template.template,
            "variables": template.variables,
            "system_message": template.system_message,
            "examples": template.examples or []
        }
        
        try:
            with open(actual_file_path, 'w', encoding='utf-8') as f:
                yaml.dump(template_data, f, default_flow_style=False, allow_unicode=True)
            
            self.logger.info("Saved template to: %s", actual_file_path)
            
        except (OSError, IOError, ValueError) as e:
            self.logger.error("Failed to save template: %s", e)
    
    def optimize_prompt(self, template_name: str, feedback: Dict[str, Any]) -> None:
        """
        Optimize a prompt template based on feedback.
        
        Args:
            template_name: Name of the template to optimize
            feedback: Feedback data for optimization
        """
        # Placeholder for prompt optimization logic
        # This could use techniques like:
        # - A/B testing of different prompt variations
        # - Analyzing success rates of different prompt formats
        # - Automatic prompt tuning based on model responses
        
        self.logger.info("Optimizing template: %s", template_name)
    
    def create_context_aware_prompt(
        self, 
        base_template: str, 
        context: Dict[str, Any]
    ) -> str:
        """
        Create a context-aware prompt by injecting relevant context.
        
        Args:
            base_template: Base template name
            context: Context information to inject
            
        Returns:
            Enhanced prompt with context
        """
        template = self.get_template(base_template)
        if not template:
            raise ValueError(f"Template not found: {base_template}")
        
        # Add context to the template variables
        enhanced_context = {}
        
        # Add project context if available
        if "project_info" in context:
            project_info = context["project_info"]
            enhanced_context["project_context"] = f"""
Project Information:
- Name: {project_info.get('name', 'Unknown')}
- Type: {project_info.get('type', 'Unknown')}
- Technologies: {', '.join(project_info.get('technologies', []))}
- Frameworks: {', '.join(project_info.get('frameworks', []))}
            """.strip()
        
        # Add file context if available
        if "file_context" in context:
            file_context = context["file_context"]
            enhanced_context["file_info"] = f"""
File Context:
- Path: {file_context.get('path', 'Unknown')}
- Type: {file_context.get('type', 'Unknown')}
- Size: {file_context.get('size', 0)} lines
            """.strip()
        
        # Add component context if available
        if "component_context" in context:
            comp_context = context["component_context"]
            enhanced_context["component_info"] = f"""
Component Context:
- Related components: {len(comp_context.get('related', []))}
- Dependencies: {len(comp_context.get('dependencies', []))}
- Framework type: {comp_context.get('framework_type', 'Unknown')}
            """.strip()
        
        # Merge with original context
        final_context = {**context, **enhanced_context}
        
        return template.format(**final_context)
    
    def get_prompt_statistics(self) -> Dict[str, Any]:
        """Get statistics about prompt usage and performance."""
        return {
            "total_templates": len(self.templates),
            "template_names": list(self.templates.keys()),
            "templates_with_examples": len([t for t in self.templates.values() if t.examples]),
            "average_variables_per_template": sum(len(t.variables) for t in self.templates.values()) / len(self.templates) if self.templates else 0
        }
