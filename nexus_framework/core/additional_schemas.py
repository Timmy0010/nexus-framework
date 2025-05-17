# nexus_framework/core/additional_schemas.py
"""
Additional schema definitions for Nexus Framework message types.
"""

# Command Message Payload Schema (v1.0)
COMMAND_MESSAGE_PAYLOAD_SCHEMA_V1 = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "NexusCommandMessagePayload",
    "description": "Schema for the payload of a command message, version 1.0",
    "type": "object",
    "properties": {
        "command": {
            "type": "string",
            "description": "The command to execute."
        },
        "parameters": {
            "type": "object",
            "description": "Parameters for the command.",
            "additionalProperties": True
        },
        "context": {
            "type": "object",
            "description": "Additional context for command execution.",
            "additionalProperties": True
        }
    },
    "required": ["command"],
    "additionalProperties": False
}

# Event Message Payload Schema (v1.0)
EVENT_MESSAGE_PAYLOAD_SCHEMA_V1 = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "NexusEventMessagePayload",
    "description": "Schema for the payload of an event message, version 1.0",
    "type": "object",
    "properties": {
        "event_type": {
            "type": "string",
            "description": "The type of event that occurred."
        },
        "event_data": {
            "type": "object",
            "description": "Data associated with the event.",
            "additionalProperties": True
        },
        "event_time": {
            "type": "string",
            "format": "date-time",
            "description": "Timestamp when the event occurred (ISO 8601)."
        },
        "source": {
            "type": "string",
            "description": "The source of the event."
        },
        "tags": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Optional tags for categorizing the event."
        }
    },
    "required": ["event_type", "event_data", "event_time", "source"],
    "additionalProperties": False
}

# Error Message Payload Schema (v1.0)
ERROR_MESSAGE_PAYLOAD_SCHEMA_V1 = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "NexusErrorMessagePayload",
    "description": "Schema for the payload of an error message, version 1.0",
    "type": "object",
    "properties": {
        "error_code": {
            "type": "string",
            "description": "Error code identifier."
        },
        "error_message": {
            "type": "string",
            "description": "Human-readable error message."
        },
        "error_details": {
            "type": "object",
            "description": "Additional error details.",
            "additionalProperties": True
        },
        "related_message_id": {
            "type": "string",
            "description": "ID of the message that triggered this error, if applicable."
        },
        "stacktrace": {
            "type": "string",
            "description": "Optional stacktrace for debugging."
        },
        "severity": {
            "type": "string",
            "enum": ["info", "warning", "error", "critical"],
            "description": "Severity level of the error."
        }
    },
    "required": ["error_code", "error_message", "severity"],
    "additionalProperties": False
}

# Data Message Payload Schema (v1.0)
DATA_MESSAGE_PAYLOAD_SCHEMA_V1 = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "NexusDataMessagePayload",
    "description": "Schema for the payload of a data message, version 1.0",
    "type": "object",
    "properties": {
        "data_type": {
            "type": "string",
            "description": "Type of data being transferred."
        },
        "content": {
            "type": "object",
            "description": "The actual data content.",
            "additionalProperties": True
        },
        "format": {
            "type": "string",
            "description": "Format of the data (e.g., 'json', 'xml', 'binary')."
        },
        "schema_url": {
            "type": "string",
            "format": "uri",
            "description": "Optional URL to the schema for the data content."
        },
        "encoding": {
            "type": "string",
            "description": "Encoding method if applicable."
        },
        "metadata": {
            "type": "object",
            "description": "Additional metadata about the data.",
            "additionalProperties": True
        }
    },
    "required": ["data_type", "content"],
    "additionalProperties": False
}

# Status Message Payload Schema (v1.0)
STATUS_MESSAGE_PAYLOAD_SCHEMA_V1 = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "NexusStatusMessagePayload",
    "description": "Schema for the payload of a status message, version 1.0",
    "type": "object",
    "properties": {
        "status_code": {
            "type": "string",
            "description": "Status code identifier."
        },
        "status_message": {
            "type": "string",
            "description": "Human-readable status message."
        },
        "component": {
            "type": "string",
            "description": "The component providing the status."
        },
        "state": {
            "type": "string",
            "enum": ["starting", "running", "degraded", "stopping", "stopped", "error"],
            "description": "Current state of the component."
        },
        "metrics": {
            "type": "object",
            "description": "Optional performance metrics.",
            "additionalProperties": True
        },
        "timestamp": {
            "type": "string",
            "format": "date-time",
            "description": "Timestamp of the status report (ISO 8601)."
        }
    },
    "required": ["status_code", "status_message", "component", "state", "timestamp"],
    "additionalProperties": False
}

# VerificationResult Message Payload Schema (v1.0)
VERIFICATION_RESULT_PAYLOAD_SCHEMA_V1 = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "NexusVerificationResultPayload",
    "description": "Schema for the payload of a verification result message, version 1.0",
    "type": "object",
    "properties": {
        "verified": {
            "type": "boolean",
            "description": "Whether the verification passed."
        },
        "original_message_id": {
            "type": "string",
            "description": "ID of the message that was verified."
        },
        "checks_performed": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "check_name": {"type": "string"},
                    "passed": {"type": "boolean"},
                    "details": {"type": "string"}
                },
                "required": ["check_name", "passed"]
            },
            "description": "List of verification checks performed."
        },
        "risk_level": {
            "type": "string",
            "enum": ["none", "low", "medium", "high", "critical"],
            "description": "Assessed risk level of the message."
        },
        "actions_taken": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Actions taken as a result of verification."
        },
        "verification_timestamp": {
            "type": "string",
            "format": "date-time",
            "description": "Timestamp of verification (ISO 8601)."
        }
    },
    "required": ["verified", "original_message_id", "checks_performed", "verification_timestamp"],
    "additionalProperties": False
}

# Registry mapping message types to their schema versions
PAYLOAD_SCHEMA_REGISTRY = {
    "text_message": {
        "1.0": "TEXT_MESSAGE_PAYLOAD_SCHEMA_V1"
    },
    "command_message": {
        "1.0": "COMMAND_MESSAGE_PAYLOAD_SCHEMA_V1"
    },
    "event_message": {
        "1.0": "EVENT_MESSAGE_PAYLOAD_SCHEMA_V1"
    },
    "error_message": {
        "1.0": "ERROR_MESSAGE_PAYLOAD_SCHEMA_V1"
    },
    "data_message": {
        "1.0": "DATA_MESSAGE_PAYLOAD_SCHEMA_V1"
    },
    "status_message": {
        "1.0": "STATUS_MESSAGE_PAYLOAD_SCHEMA_V1"
    },
    "verification_result": {
        "1.0": "VERIFICATION_RESULT_PAYLOAD_SCHEMA_V1"
    }
}
