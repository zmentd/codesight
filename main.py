#!/usr/bin/env python3
"""
CodeSight Pipeline Entry Point

Main entry point for the CodeSight AI-powered reverse engineering pipeline.
Uses PocketFlow for orchestration and automatic validation.
"""

import argparse
import sys
from pathlib import Path

# Add src directory to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))


from config import Config
from config.exceptions import ConfigurationError
from core.codesight_flow import run_codesight_analysis, run_codesight_selected_steps
from utils.logging.logger_factory import LoggerFactory


def setup_logging(config_path: str) -> None:
    """Initialize logging configuration."""
    LoggerFactory.initialize(config_path)


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="CodeSight AI-powered reverse engineering pipeline"
    )
    
    parser.add_argument(
        "project_name",
        help="Name of the project to analyze (e.g., 'storm')"
    )
    
    parser.add_argument(
        "--config-path",
        default="config/config.yaml",
        help="Path to main configuration file"
    )
    
    parser.add_argument(
        "--source-path",
        help="Path to source code (overrides config)"
    )
    
    parser.add_argument(
        "--output-path",
        help="Path to output directory (overrides config)"
    )
    
    parser.add_argument(
        "--steps",
        help="Comma-separated steps to run (e.g., step04 or step03,step04). If provided, only these steps run using existing outputs."
    )
    
    return parser.parse_args()


def validate_project_structure(project_name: str) -> bool:
    """Validate that required project directories exist."""
    # Projects are in the codesight root directory
    project_dir = Path(f"../projects/{project_name}")
    required_dirs = ["input", "output", "embeddings"]
    
    for dir_name in required_dirs:
        dir_path = project_dir / dir_name
        if not dir_path.exists():
            dir_path.mkdir(parents=True, exist_ok=True)
    
    return True


def main() -> int:
    """Main application entry point."""
    try:
        args = parse_arguments()

        # Initialize configuration with project name
        # This will load the base config and project-specific overrides
        try:
            Config.initialize(project_name=args.project_name)
            config = Config.get_instance()
        except ConfigurationError as e:
            print(f"Error: Failed to initialize configuration for project '{args.project_name}': {e}")
            return 1
        
        # Setup logging
        try:
            setup_logging("config/logging.yaml")
            logger = LoggerFactory.get_logger("codesight")
        except Exception as e:  # pylint: disable=broad-except
            print(f"Failed to initialize logging: {e}")
            # Continue with basic logging
            import logging
            logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            logger = logging.getLogger("codesight")
        
        logger.info("Starting CodeSight pipeline for project: %s", args.project_name)
        
        # Validate project structure
        if not validate_project_structure(args.project_name):
            logger.error("Failed to validate project structure for: %s", args.project_name)
            return 1
        
        # Determine project path
        if args.source_path:
            project_path = args.source_path
        else:
            # Use the configured source path or default location
            project_path = config.project.source_path

        # If steps specified, run only those steps (assumes prior outputs exist)
        if args.steps:
            steps = [s.strip() for s in args.steps.split(",") if s.strip()]
            logger.info("Running selected steps only: %s", ", ".join(steps))
            result = run_codesight_selected_steps(project_path, args.project_name, steps)
            if result.get("success"):
                logger.info("Selected steps completed successfully")
                logger.info("Execution time: %.2f seconds", result.get('execution_time', 0.0))
                return 0
            logger.error("Selected steps failed: %s", result.get('error_message'))
            return 1
        
        # Run CodeSight analysis using PocketFlow (all steps)
        logger.info("Analyzing project at: %s", project_path)
        result = run_codesight_analysis(project_path, args.project_name)
        
        if result["success"]:
            logger.info("Pipeline execution completed successfully")
            logger.info("Execution time: %.2f seconds", result['execution_time'])
            return 0
        else:
            logger.error("Pipeline execution failed: %s", result['error_message'])
            return 1
            
    except KeyboardInterrupt:
        print("\nPipeline execution interrupted by user")
        return 130
    except Exception as e:  # pylint: disable=broad-except
        print(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
