"""LLM client for AI-powered code analysis."""

import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from config import Config
from config.exceptions import ConfigurationError
from utils.logging.logger_factory import LoggerFactory


class LLMProvider(Enum):
    """Supported LLM providers."""
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"
    OLLAMA = "ollama"
    LOCAL = "local"
    # NBCU Kong Gateway Providers
    KONG_AWS = "kong_aws"
    KONG_AZURE = "kong_azure"
    KONG_GCP = "kong_gcp"


@dataclass
class LLMResponse:
    """Response from LLM API call."""
    success: bool
    content: str
    error_message: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            "success": self.success,
            "content": self.content,
            "error_message": self.error_message,
            "usage": self.usage,
            "metadata": self.metadata
        }


class LLMClient:
    """
    Client for interacting with Large Language Models for code analysis.
    
    Supports multiple providers:
    - OpenAI GPT models
    - Azure OpenAI
    - Anthropic Claude
    - Local Ollama models
    """
    
    def __init__(self) -> None:
        """Initialize LLM client using Config."""
        try:
            config = Config.get_instance()
        except ConfigurationError as e:
            raise ConfigurationError(f"LLMClient initialization failed: {e}") from e
            
        self.config = config
        self.logger = LoggerFactory.get_logger(__name__)
        
        # Check if LLM configuration exists
        if not hasattr(config, 'llm') or config.llm is None:
            raise ConfigurationError("LLM configuration not found in config")
        
        # Access LLM configuration from the dataclass structure
        self.provider = LLMProvider(config.llm.provider)
        self.model = getattr(config.llm, 'model', 'gpt-3.5-turbo')
        self.api_key = getattr(config.llm, 'api_key', None)
        self.base_url = getattr(config.llm, 'base_url', None)
        self.max_tokens = config.llm.max_tokens
        self.temperature = config.llm.temperature
        
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize the LLM client based on provider."""
        try:
            if self.provider == LLMProvider.OPENAI:
                # Initialize OpenAI client
                # import openai
                # self.client = openai.OpenAI(api_key=self.api_key)
                pass
            
            elif self.provider == LLMProvider.AZURE_OPENAI:
                # Initialize Azure OpenAI client
                # import openai
                # self.client = openai.AzureOpenAI(
                #     api_key=self.api_key,
                #     azure_endpoint=self.base_url,
                #     api_version="2024-02-01"
                # )
                pass
            
            elif self.provider == LLMProvider.ANTHROPIC:
                # Initialize Anthropic client
                # import anthropic
                # self.client = anthropic.Anthropic(api_key=self.api_key)
                pass
            
            elif self.provider == LLMProvider.OLLAMA:
                # Initialize Ollama client
                # import ollama
                # self.client = ollama.Client(host=self.base_url or "http://localhost:11434")
                pass
            
            self.logger.info("LLM client initialized for provider: %s", self.provider.value)
            
        except (ImportError, ConnectionError, ValueError, RuntimeError) as e:
            self.logger.error("Failed to initialize LLM client: %s", e)
    
    def analyze_code_structure(self, code: str, language: str = "java") -> LLMResponse:
        """
        Analyze code structure using LLM.
        
        Args:
            code: Source code to analyze
            language: Programming language
            
        Returns:
            LLMResponse with analysis results
        """
        prompt = f"""
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
            "key_methods": [{"name": "string", "purpose": "string"}],
            "issues": ["string"],
            "improvements": ["string"],
            "dependencies": ["string"]
        }}
        """
        
        return self._make_request(prompt)
    
    def identify_components(self, file_content: str, file_path: str) -> LLMResponse:
        """
        Identify components in a file using LLM.
        
        Args:
            file_content: Content of the file
            file_path: Path to the file
            
        Returns:
            LLMResponse with identified components
        """
        prompt = f"""
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
        """
        
        return self._make_request(prompt)
    
    def suggest_modernization(self, component_analysis: Dict[str, Any]) -> LLMResponse:
        """
        Suggest modernization approaches for legacy components.
        
        Args:
            component_analysis: Analysis results for components
            
        Returns:
            LLMResponse with modernization suggestions
        """
        analysis_text = json.dumps(component_analysis, indent=2)
        
        prompt = f"""
        Based on the following component analysis, suggest modernization approaches:
        
        {analysis_text}
        
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
        """
        
        return self._make_request(prompt)
    
    def analyze_architecture(self, project_structure: Dict[str, Any]) -> LLMResponse:
        """
        Analyze overall project architecture.
        
        Args:
            project_structure: Project structure information
            
        Returns:
            LLMResponse with architecture analysis
        """
        structure_text = json.dumps(project_structure, indent=2)
        
        prompt = f"""
        Analyze the following project structure and provide architectural insights:
        
        {structure_text}
        
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
        """
        
        return self._make_request(prompt)
    
    def generate_migration_plan(self, analysis_results: Dict[str, Any]) -> LLMResponse:
        """
        Generate a comprehensive migration plan.
        
        Args:
            analysis_results: Combined analysis results
            
        Returns:
            LLMResponse with migration plan
        """
        results_text = json.dumps(analysis_results, indent=2)
        
        prompt = f"""
        Based on the comprehensive analysis results, generate a detailed migration plan:
        
        {results_text}
        
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
        """
        
        return self._make_request(prompt)
    
    def extract_business_logic(self, code: str) -> LLMResponse:
        """
        Extract business logic from code using LLM.
        
        Args:
            code: Source code to analyze
            
        Returns:
            LLMResponse with business logic extraction
        """
        prompt = f"""
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
        """
        
        return self._make_request(prompt)
    
    def _make_request(self, prompt: str, system_message: Optional[str] = None) -> LLMResponse:
        """
        Make a request to the LLM API.
        
        Args:
            prompt: User prompt
            system_message: Optional system message
            
        Returns:
            LLMResponse with the result
        """
        try:
            # Placeholder implementation
            # This would make actual API calls to the configured LLM provider
            
            if self.provider == LLMProvider.OPENAI:
                return self._call_openai(prompt, system_message)
            elif self.provider == LLMProvider.AZURE_OPENAI:
                return self._call_azure_openai(prompt, system_message)
            elif self.provider == LLMProvider.ANTHROPIC:
                return self._call_anthropic(prompt, system_message)
            elif self.provider == LLMProvider.OLLAMA:
                return self._call_ollama(prompt, system_message)
            else:
                return LLMResponse(
                    success=False,
                    content="",
                    error_message=f"Unsupported provider: {self.provider.value}"
                )
                
        except (ConnectionError, ValueError, RuntimeError, ImportError) as e:
            self.logger.error("Failed to make LLM request: %s", e)
            return LLMResponse(
                success=False,
                content="",
                error_message=str(e)
            )
    
    def _call_openai(self, prompt: str, system_message: Optional[str] = None) -> LLMResponse:
        """Call OpenAI API."""
        # Placeholder implementation
        return LLMResponse(
            success=True,
            content='{"component_type": "class", "design_patterns": ["singleton"], "framework_dependencies": ["spring"]}',
            usage={"total_tokens": 150}
        )
    
    def _call_azure_openai(self, prompt: str, system_message: Optional[str] = None) -> LLMResponse:
        """Call Azure OpenAI API."""
        # Placeholder implementation
        return LLMResponse(
            success=True,
            content='{"component_type": "service", "design_patterns": ["repository"], "framework_dependencies": ["spring-boot"]}',
            usage={"total_tokens": 180}
        )
    
    def _call_anthropic(self, prompt: str, system_message: Optional[str] = None) -> LLMResponse:
        """Call Anthropic API."""
        # Placeholder implementation
        return LLMResponse(
            success=True,
            content='{"component_type": "controller", "design_patterns": ["mvc"], "framework_dependencies": ["spring-mvc"]}',
            usage={"total_tokens": 160}
        )
    
    def _call_ollama(self, prompt: str, system_message: Optional[str] = None) -> LLMResponse:
        """Call Ollama local API."""
        # Placeholder implementation
        return LLMResponse(
            success=True,
            content='{"component_type": "entity", "design_patterns": ["jpa"], "framework_dependencies": ["hibernate"]}',
            metadata={"model": self.model}
        )
    
    def test_connection(self) -> bool:
        """Test connection to the LLM provider."""
        try:
            response = self._make_request("Hello, please respond with 'OK'")
            return response.success and "OK" in response.content
        except (ConnectionError, ValueError, RuntimeError) as e:
            self.logger.error("Connection test failed: %s", e)
            return False
