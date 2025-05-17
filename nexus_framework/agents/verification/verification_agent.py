# nexus_framework/agents/verification/verification_agent.py
from typing import Dict, Any, List, Optional, Type, Tuple
import logging
import importlib
import os
import yaml
from abc import ABC, abstractmethod
import json
import uuid

from nexus_framework.core.message import Message
from nexus_framework.agents.specialized import BaseAgent

logger = logging.getLogger(__name__)

class VerificationRule(ABC):
    """Abstract base class for verification rules."""
    
    @abstractmethod
    def verify(self, message: Message) -> Dict[str, Any]:
        """
        Verify a message against this rule.
        
        Args:
            message: The message to verify
            
        Returns:
            A dict containing at least:
            {
                "passed": bool,  # Whether the rule passed
                "reason": str,   # Reason for pass/fail
                "risk_level": str  # Risk level assessment (none/low/medium/high/critical)
            }
        """
        pass

class MessageSanitizer(ABC):
    """Abstract base class for message sanitizers."""
    
    @abstractmethod
    def sanitize(self, message: Message) -> Message:
        """
        Sanitize a message.
        
        Args:
            message: The message to sanitize
            
        Returns:
            The sanitized message
        """
        pass

class VerificationAgent(BaseAgent):
    """
    Agent responsible for verifying and sanitizing messages in the Nexus Framework.
    
    The VerificationAgent applies a pipeline of verification rules to messages
    and can sanitize content that fails verification but is deemed safe to modify.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the VerificationAgent.
        
        Args:
            config_path: Path to the verification configuration directory.
                        If not provided, default rules will be loaded.
        """
        super().__init__(agent_name="VerificationAgent", role="security")
        
        # Load rules and sanitizers
        self.rules: Dict[str, VerificationRule] = {}
        self.sanitizers: Dict[str, MessageSanitizer] = {}
        self.rule_config: Dict[str, Dict[str, Any]] = {}
        
        # Configure from file or use default configuration
        if config_path:
            self._load_configuration(config_path)
        else:
            self._load_default_configuration()
            
        logger.info(f"VerificationAgent initialized with {len(self.rules)} rules and {len(self.sanitizers)} sanitizers")
    
    def _load_configuration(self, config_path: str) -> None:
        """Load configuration from the specified directory."""
        try:
            # Load rule configuration
            rule_config_file = os.path.join(config_path, "rules.yaml")
            if os.path.exists(rule_config_file):
                with open(rule_config_file, 'r') as f:
                    self.rule_config = yaml.safe_load(f)
            else:
                logger.warning(f"Rule configuration file not found: {rule_config_file}")
                self.rule_config = {}
            
            # Load rules from Python modules
            rules_dir = os.path.join(config_path, "rules")
            if os.path.exists(rules_dir) and os.path.isdir(rules_dir):
                self._load_rules_from_directory(rules_dir)
            else:
                logger.warning(f"Rules directory not found: {rules_dir}")
            
            # Load sanitizers from Python modules
            sanitizers_dir = os.path.join(config_path, "sanitizers")
            if os.path.exists(sanitizers_dir) and os.path.isdir(sanitizers_dir):
                self._load_sanitizers_from_directory(sanitizers_dir)
            else:
                logger.warning(f"Sanitizers directory not found: {sanitizers_dir}")
        
        except Exception as e:
            logger.error(f"Error loading VerificationAgent configuration: {str(e)}")
            # Load defaults as fallback
            self._load_default_configuration()
    
    def _load_default_configuration(self) -> None:
        """Load default rules and sanitizers."""
        # Load built-in rules
        from nexus_framework.agents.verification.rules.schema_rule import SchemaVerificationRule
        from nexus_framework.agents.verification.rules.content_rule import ContentVerificationRule
        from nexus_framework.agents.verification.rules.size_rule import SizeVerificationRule
        
        # Load built-in sanitizers
        from nexus_framework.agents.verification.sanitizers.content_sanitizer import ContentSanitizer
        
        # Register default rules
        self.rules["schema"] = SchemaVerificationRule()
        self.rules["content"] = ContentVerificationRule()
        self.rules["size"] = SizeVerificationRule()
        
        # Register default sanitizers
        self.sanitizers["content"] = ContentSanitizer()
        
        # Default rule configuration
        self.rule_config = {
            "schema": {"enabled": True, "priority": 100},
            "content": {"enabled": True, "priority": 200},
            "size": {"enabled": True, "priority": 300, "max_size_bytes": 1048576}  # 1MB default limit
        }
    
    def _load_rules_from_directory(self, rules_dir: str) -> None:
        """
        Load verification rules from Python modules in the specified directory.
        
        Each module should define a class that inherits from VerificationRule.
        """
        for file_name in os.listdir(rules_dir):
            if file_name.endswith(".py") and not file_name.startswith("__"):
                try:
                    module_name = file_name[:-3]  # Remove .py extension
                    module_path = os.path.join(rules_dir, file_name)
                    
                    # Load module
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # Find and instantiate rule classes
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if (isinstance(attr, type) and 
                                issubclass(attr, VerificationRule) and 
                                attr != VerificationRule):
                                rule_instance = attr()
                                self.rules[module_name] = rule_instance
                                logger.info(f"Loaded verification rule: {module_name}")
                
                except Exception as e:
                    logger.error(f"Error loading verification rule from {file_name}: {str(e)}")
    
    def _load_sanitizers_from_directory(self, sanitizers_dir: str) -> None:
        """
        Load message sanitizers from Python modules in the specified directory.
        
        Each module should define a class that inherits from MessageSanitizer.
        """
        for file_name in os.listdir(sanitizers_dir):
            if file_name.endswith(".py") and not file_name.startswith("__"):
                try:
                    module_name = file_name[:-3]  # Remove .py extension
                    module_path = os.path.join(sanitizers_dir, file_name)
                    
                    # Load module
                    spec = importlib.util.spec_from_file_location(module_name, module_path)
                    if spec and spec.loader:
                        module = importlib.util.module_from_spec(spec)
                        spec.loader.exec_module(module)
                        
                        # Find and instantiate sanitizer classes
                        for attr_name in dir(module):
                            attr = getattr(module, attr_name)
                            if (isinstance(attr, type) and 
                                issubclass(attr, MessageSanitizer) and 
                                attr != MessageSanitizer):
                                sanitizer_instance = attr()
                                self.sanitizers[module_name] = sanitizer_instance
                                logger.info(f"Loaded message sanitizer: {module_name}")
                
                except Exception as e:
                    logger.error(f"Error loading message sanitizer from {file_name}: {str(e)}")
    
    def verify_message(self, message: Message) -> Tuple[bool, Dict[str, Any]]:
        """
        Apply all verification rules to a message.
        
        Args:
            message: The message to verify
            
        Returns:
            A tuple (passed, results):
            - passed: Boolean indicating if all rules passed
            - results: Dict with detailed results for each rule
        """
        # Get enabled rules sorted by priority
        enabled_rules = []
        for rule_name, rule in self.rules.items():
            rule_config = self.rule_config.get(rule_name, {"enabled": False, "priority": 999})
            if rule_config.get("enabled", False):
                enabled_rules.append((rule_name, rule, rule_config.get("priority", 999)))
        
        # Sort rules by priority (lower values run first)
        enabled_rules.sort(key=lambda x: x[2])
        
        overall_passed = True
        verification_results = {}
        highest_risk = "none"
        risk_levels = ["none", "low", "medium", "high", "critical"]
        
        # Apply each rule
        for rule_name, rule, _ in enabled_rules:
            try:
                rule_result = rule.verify(message)
                verification_results[rule_name] = rule_result
                
                # Update overall pass/fail and risk assessment
                if not rule_result.get("passed", False):
                    overall_passed = False
                
                # Update highest risk level
                rule_risk = rule_result.get("risk_level", "none")
                if risk_levels.index(rule_risk) > risk_levels.index(highest_risk):
                    highest_risk = rule_risk
            
            except Exception as e:
                logger.error(f"Error applying rule {rule_name}: {str(e)}")
                verification_results[rule_name] = {
                    "passed": False,
                    "reason": f"Rule execution error: {str(e)}",
                    "risk_level": "medium"  # Default to medium risk for rule failures
                }
                overall_passed = False
                if risk_levels.index("medium") > risk_levels.index(highest_risk):
                    highest_risk = "medium"
        
        # Compile detailed results
        summary = {
            "passed": overall_passed,
            "risk_level": highest_risk,
            "rule_results": verification_results,
            "verification_timestamp": None  # Will be filled in by process_message
        }
        
        return overall_passed, summary
    
    def sanitize_message(self, message: Message, verification_results: Dict[str, Any]) -> Tuple[Message, bool]:
        """
        Attempt to sanitize a message that failed verification.
        
        Args:
            message: The message to sanitize
            verification_results: Results from verification
            
        Returns:
            A tuple (sanitized_message, success):
            - sanitized_message: The sanitized message (or original if sanitization failed)
            - success: Boolean indicating if sanitization was successful
        """
        # Don't sanitize if risk is too high
        if verification_results.get("risk_level") == "critical":
            logger.warning(f"Message {message.message_id} has critical risk, skipping sanitization")
            return message, False
        
        # Apply sanitizers
        sanitized_message = message
        sanitized = False
        
        for sanitizer_name, sanitizer in self.sanitizers.items():
            try:
                # Apply sanitizer if the related rule failed
                if sanitizer_name in verification_results.get("rule_results", {}) and \
                   not verification_results["rule_results"][sanitizer_name].get("passed", True):
                    
                    # Apply sanitization
                    sanitized_message = sanitizer.sanitize(sanitized_message)
                    sanitized = True
                    logger.info(f"Applied sanitizer {sanitizer_name} to message {message.message_id}")
            
            except Exception as e:
                logger.error(f"Error applying sanitizer {sanitizer_name}: {str(e)}")
        
        return sanitized_message, sanitized
    
    def process_message(self, message: Message) -> Optional[Message]:
        """
        Process a message through verification and optional sanitization.
        
        This is the main entry point for message processing in the VerificationAgent.
        
        Args:
            message: The message to process
            
        Returns:
            The processed message if it passed verification or was successfully sanitized,
            or None if the message should be rejected.
        """
        logger.info(f"Processing message {message.message_id} from {message.sender_id}")
        
        # Apply verification rules
        passed, verification_results = self.verify_message(message)
        
        # Add timestamp to results
        import datetime
        verification_results["verification_timestamp"] = datetime.datetime.utcnow().isoformat()
        
        if passed:
            logger.info(f"Message {message.message_id} passed verification")
            return message
        
        # Message failed verification, try to sanitize
        logger.warning(f"Message {message.message_id} failed verification with risk level {verification_results['risk_level']}")
        
        sanitized_message, sanitized = self.sanitize_message(message, verification_results)
        
        if sanitized:
            # Verify sanitized message
            sanitized_passed, _ = self.verify_message(sanitized_message)
            
            if sanitized_passed:
                logger.info(f"Message {message.message_id} was successfully sanitized and now passes verification")
                return sanitized_message
            else:
                logger.warning(f"Message {message.message_id} failed verification even after sanitization")
        
        # Message failed verification and could not be sanitized
        # Create a verification result message
        verification_message = self._create_verification_result_message(message, verification_results)
        
        logger.warning(f"Rejecting message {message.message_id} due to verification failure")
        return verification_message
    
    def _create_verification_result_message(self, original_message: Message, verification_results: Dict[str, Any]) -> Message:
        """
        Create a verification result message in response to a failed verification.
        
        Args:
            original_message: The message that failed verification
            verification_results: The verification results
            
        Returns:
            A new message containing verification results
        """
        # Extract checks performed
        checks_performed = []
        for rule_name, result in verification_results.get("rule_results", {}).items():
            checks_performed.append({
                "check_name": rule_name,
                "passed": result.get("passed", False),
                "details": result.get("reason", "No details provided")
            })
        
        # Create verification result payload
        verification_payload = {
            "verified": False,
            "original_message_id": original_message.message_id,
            "checks_performed": checks_performed,
            "risk_level": verification_results.get("risk_level", "high"),
            "actions_taken": ["message_rejected"],
            "verification_timestamp": verification_results.get("verification_timestamp")
        }
        
        # Create verification result message
        return Message(
            message_id=str(uuid.uuid4()),
            content="Message verification failed",
            sender_id=self.agent_id,
            recipient_id=original_message.sender_id,
            message_type="verification_result",
            metadata={
                "original_message_id": original_message.message_id,
                "verification_summary": verification_results
            },
            payload=verification_payload
        )
