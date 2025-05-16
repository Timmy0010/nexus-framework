# nexus_framework/core/schemas.py

# Base Message Schema (v1.0)
# This defines common fields for all Nexus messages.
BASE_MESSAGE_SCHEMA_V1 = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "NexusBaseMessage",
    "description": "Base schema for all Nexus Framework messages, version 1.0",
    "type": "object",
    "properties": {
        "message_id": {
            "type": "string",
            "format": "uuid",
            "description": "Unique identifier for the message."
        },
        "saga_id": {
            "type": ["string", "null"], # Can be null if not part of a saga
            "format": "uuid",
            "description": "Identifier for the saga this message belongs to, if any."
        },
        "correlation_id": {
            "type": ["string", "null"], # Can be null
            "format": "uuid",
            "description": "Identifier to correlate related messages or requests."
        },
        "timestamp": {
            "type": "string",
            "format": "date-time",
            "description": "Timestamp of when the message was created (ISO 8601)."
        },
        "sender_id": {
            "type": "string",
            "description": "Identifier of the sending agent or component."
        },
        "recipient_id": {
            "type": "string",
            "description": "Identifier of the intended recipient agent or component."
        },
        "message_type": {
            "type": "string",
            "description": "Type of the message, used for routing and schema validation (e.g., 'text_message', 'command_message')."
        },
        "schema_version": {
            "type": "string",
            "pattern": "^\\d+\\.\\d+$",  # e.g., "1.0", "2.1"
            "description": "Version of the payload schema this message's payload conforms to."
        },
        "payload": {
            "type": "object",
            "description": "The actual content/data of the message. Its structure is defined by message_type and schema_version."
        },
        "metadata": {
            "type": "object",
            "description": "Additional metadata about the message.",
            "properties": {
                "priority": {"type": "integer", "minimum": 0, "maximum": 10},
                "ttl": {"type": "integer", "description": "Time-to-live in seconds for the message."}
            },
            "additionalProperties": True # Allow other metadata fields
        }
    },
    "required": [
        "message_id",
        "timestamp",
        "sender_id",
        "recipient_id",
        "message_type",
        "schema_version",
        "payload"
    ],
    "additionalProperties": False # Disallow extra top-level properties not defined in the base schema
}

# Text Message Payload Schema (v1.0)
# Specific payload for a 'text_message' type.
TEXT_MESSAGE_PAYLOAD_SCHEMA_V1 = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "title": "NexusTextMessagePayload",
    "description": "Schema for the payload of a text message, version 1.0",
    "type": "object",
    "properties": {
        "text": {
            "type": "string",
            "description": "The text content of the message."
        },
        "language": {
            "type": "string",
            "default": "en",
            "description": "Language code of the text (e.g., 'en', 'es')."
        }
    },
    "required": ["text"],
    "additionalProperties": False
}

# This is where a schema registry would typically be defined or loaded.
# For the SchemaValidator, it will be passed in during initialization.
# Example:
# PAYLOAD_SCHEMA_REGISTRY = {
#     "text_message": {
#         "1.0": TEXT_MESSAGE_PAYLOAD_SCHEMA_V1
#     },
#     # ... other message types and their versions
# }