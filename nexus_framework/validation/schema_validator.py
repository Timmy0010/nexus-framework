# nexus_framework/validation/schema_validator.py
import jsonschema
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class SchemaValidationError(Exception):
    """Custom exception for schema validation errors."""
    def __init__(self, message: str, errors: List[str]):
        super().__init__(message)
        self.errors = errors

    def __str__(self):
        return f"{super().__str__()} Errors: {'; '.join(self.errors)}"

class SchemaValidator:
    def __init__(self, base_schema: Dict[str, Any], payload_schema_registry: Dict[str, Dict[str, Any]]):
        """
        Initializes the SchemaValidator.

        Args:
            base_schema: The JSON schema for the base message structure.
            payload_schema_registry: A dictionary where keys are message_type names,
                                     and values are dictionaries mapping schema_version strings
                                     to their respective payload JSON schemas.
                                     e.g., {"text_message": {"1.0": {...payload_schema...}}}
        """
        try:
            jsonschema.Draft7Validator.check_schema(base_schema)
            self.base_validator = jsonschema.Draft7Validator(base_schema)
        except jsonschema.SchemaError as e:
            logger.error(f"Invalid base schema provided: {e}")
            raise

        self.payload_schema_registry = payload_schema_registry
        self.payload_validators_cache: Dict[Tuple[str, str], jsonschema.Draft7Validator] = {}

        # Pre-compile and check payload schemas
        for msg_type, versions in payload_schema_registry.items():
            for version, schema_def in versions.items():
                try:
                    jsonschema.Draft7Validator.check_schema(schema_def)
                except jsonschema.SchemaError as e:
                    logger.error(f"Invalid payload schema for {msg_type} v{version}: {e}")
                    raise

    def _get_payload_validator(self, message_type: str, schema_version: str) -> Optional[jsonschema.Draft7Validator]:
        """
        Retrieves or creates and caches a validator for a specific message type and payload schema version.
        """
        cache_key = (message_type, schema_version)
        if cache_key in self.payload_validators_cache:
            return self.payload_validators_cache[cache_key]

        type_schemas = self.payload_schema_registry.get(message_type)
        if not type_schemas:
            logger.warning(f"No schema definitions found for message_type '{message_type}'.")
            return None
        
        payload_schema = type_schemas.get(schema_version)
        if not payload_schema:
            logger.warning(f"No schema definition found for message_type '{message_type}' version '{schema_version}'.")
            return None
        
        validator = jsonschema.Draft7Validator(payload_schema)
        self.payload_validators_cache[cache_key] = validator
        return validator

    def validate_message(self, message_instance: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates a message instance against the base schema and its specific payload schema.

        Args:
            message_instance: The message dictionary to validate.

        Returns:
            A tuple (is_valid, errors_list).
            is_valid is True if the message is valid, False otherwise.
            errors_list contains string descriptions of validation errors.
        """
        all_errors: List[str] = []

        base_errors = sorted(self.base_validator.iter_errors(message_instance), key=lambda e: e.path)
        for error in base_errors:
            all_errors.append(f"Base schema error: {error.message} (path: {'/'.join(map(str, error.path))})")
        
        if all_errors:
            return False, all_errors

        message_type = message_instance["message_type"] # Known to exist due to base validation
        schema_version = message_instance["schema_version"] # Known to exist
        payload = message_instance["payload"] # Known to exist
            
        payload_validator = self._get_payload_validator(message_type, schema_version)
        if not payload_validator:
            all_errors.append(f"Payload schema error: No schema validator available for message_type '{message_type}' version '{schema_version}'.")
            return False, all_errors

        payload_validation_errors = sorted(payload_validator.iter_errors(payload), key=lambda e: e.path)
        for error in payload_validation_errors:
            all_errors.append(f"Payload schema error for '{message_type}' v{schema_version}: {error.message} (path: payload/{'/'.join(map(str, error.path))})")

        return not bool(all_errors), all_errors

    def validate_and_raise(self, message_instance: Dict[str, Any]) -> None:
        """
        Validates a message and raises SchemaValidationError if invalid.
        """
        is_valid, errors = self.validate_message(message_instance)
        if not is_valid:
            message_id = message_instance.get('message_id', 'N/A')
            raise SchemaValidationError(f"Message validation failed for ID '{message_id}'", errors)