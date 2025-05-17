# nexus_framework/validation/schema_registry.py
from typing import Dict, Any, Optional, List, Tuple
import logging
import json
import os
import glob
from pathlib import Path

from nexus_framework.core.schemas import BASE_MESSAGE_SCHEMA_V1, TEXT_MESSAGE_PAYLOAD_SCHEMA_V1

logger = logging.getLogger(__name__)

class SchemaRegistry:
    """Manages schemas for message validation with versioning support."""
    
    def __init__(self, schema_directory: Optional[str] = None):
        """
        Initialize the schema registry.
        
        Args:
            schema_directory: Optional directory to load schema definitions from.
                             If provided, JSON schema files will be loaded from this directory.
        """
        # Base schema versions
        self.base_schemas = {
            "1.0": BASE_MESSAGE_SCHEMA_V1
        }
        
        # Initialize with known payload schemas
        self.payload_schemas: Dict[str, Dict[str, Any]] = {
            "text_message": {
                "1.0": TEXT_MESSAGE_PAYLOAD_SCHEMA_V1
            }
        }
        
        # Load schemas from directory if provided
        if schema_directory:
            self._load_schemas_from_directory(schema_directory)
    
    def _load_schemas_from_directory(self, directory: str) -> None:
        """Load schema definitions from JSON files in the provided directory."""
        schema_path = Path(directory)
        if not schema_path.exists() or not schema_path.is_dir():
            logger.warning(f"Schema directory '{directory}' does not exist or is not a directory.")
            return
        
        # Look for schema files matching pattern: message_type.schema_version.json
        # Example: command_message.1.0.json
        schema_files = glob.glob(str(schema_path / "*.json"))
        
        for schema_file in schema_files:
            try:
                file_name = Path(schema_file).stem  # Get filename without extension
                if "base." in file_name:
                    # Handle base schema file (e.g., base.1.0.json)
                    parts = file_name.split(".")
                    if len(parts) >= 2:
                        version = parts[1]
                        with open(schema_file, 'r') as f:
                            schema_def = json.load(f)
                        self.register_base_schema(version, schema_def)
                else:
                    # Handle payload schema file (e.g., text_message.1.0.json)
                    parts = file_name.split(".")
                    if len(parts) >= 2:
                        message_type = parts[0]
                        version = parts[1]
                        with open(schema_file, 'r') as f:
                            schema_def = json.load(f)
                        self.register_payload_schema(message_type, version, schema_def)
            except Exception as e:
                logger.error(f"Error loading schema from {schema_file}: {str(e)}")
    
    def register_base_schema(self, version: str, schema: Dict[str, Any]) -> None:
        """Register a new base message schema version."""
        self.base_schemas[version] = schema
        logger.info(f"Registered base schema version {version}")
    
    def register_payload_schema(self, message_type: str, version: str, schema: Dict[str, Any]) -> None:
        """Register a payload schema for a specific message type and version."""
        if message_type not in self.payload_schemas:
            self.payload_schemas[message_type] = {}
        
        self.payload_schemas[message_type][version] = schema
        logger.info(f"Registered payload schema for {message_type} version {version}")
    
    def get_base_schema(self, version: str = "1.0") -> Optional[Dict[str, Any]]:
        """Get the base schema for a specific version."""
        return self.base_schemas.get(version)
    
    def get_payload_schema(self, message_type: str, version: str) -> Optional[Dict[str, Any]]:
        """Get the payload schema for a specific message type and version."""
        message_schemas = self.payload_schemas.get(message_type)
        if not message_schemas:
            return None
        return message_schemas.get(version)
    
    def get_all_payload_schemas(self) -> Dict[str, Dict[str, Any]]:
        """Get all registered payload schemas."""
        return self.payload_schemas
    
    def save_schemas_to_directory(self, directory: str) -> None:
        """Save all schemas to JSON files in the specified directory."""
        schema_path = Path(directory)
        schema_path.mkdir(parents=True, exist_ok=True)
        
        # Save base schemas
        for version, schema in self.base_schemas.items():
            file_path = schema_path / f"base.{version}.json"
            with open(file_path, 'w') as f:
                json.dump(schema, f, indent=2)
        
        # Save payload schemas
        for message_type, versions in self.payload_schemas.items():
            for version, schema in versions.items():
                file_path = schema_path / f"{message_type}.{version}.json"
                with open(file_path, 'w') as f:
                    json.dump(schema, f, indent=2)
        
        logger.info(f"Saved all schemas to directory: {directory}")
    
    def list_message_types(self) -> List[str]:
        """List all registered message types."""
        return list(self.payload_schemas.keys())
    
    def list_schema_versions(self, message_type: str) -> List[str]:
        """List all versions available for a specific message type."""
        if message_type not in self.payload_schemas:
            return []
        return list(self.payload_schemas[message_type].keys())
    
    def is_compatible(self, message_type: str, old_version: str, new_version: str) -> Tuple[bool, List[str]]:
        """
        Check if a newer schema version is backward compatible with an older version.
        
        Returns:
            A tuple (is_compatible, incompatibilities) where incompatibilities is a list
            of string descriptions of compatibility issues.
        """
        # This is a simplified compatibility check
        # A more robust implementation would need deeper schema analysis
        old_schema = self.get_payload_schema(message_type, old_version)
        new_schema = self.get_payload_schema(message_type, new_version)
        
        if not old_schema or not new_schema:
            return False, ["One or both schema versions not found"]
        
        incompatibilities = []
        
        # Check if all required fields in old schema are still required in new schema
        old_required = old_schema.get("required", [])
        new_required = new_schema.get("required", [])
        
        for field in old_required:
            if field not in new_required:
                incompatibilities.append(f"Field '{field}' was required in {old_version} but not in {new_version}")
        
        # Check if all properties in old schema still exist in new schema
        old_props = old_schema.get("properties", {})
        new_props = new_schema.get("properties", {})
        
        for field_name in old_props:
            if field_name not in new_props:
                incompatibilities.append(f"Field '{field_name}' existed in {old_version} but not in {new_version}")
        
        return len(incompatibilities) == 0, incompatibilities
