# nexus_framework/agents/verification/rules/content_rule.py
from typing import Dict, Any, List
import logging
import re

from nexus_framework.core.message import Message
from nexus_framework.agents.verification.verification_agent import VerificationRule

logger = logging.getLogger(__name__)

class ContentVerificationRule(VerificationRule):
    """
    Verification rule that checks message content for potentially malicious patterns.
    """
    
    def __init__(self):
        """Initialize the content verification rule."""
        # Define patterns to check for
        self.patterns = {
            # Command injection
            "command_injection": [
                r";\s*rm\s+", r";\s*del\s+", r";\s*whoami",
                r";\s*chmod\s+", r";\s*sudo\s+", r"&&\s*[a-z]+\s*",
                r"\|\s*[a-z]+\s*", r"`[^`]+`", r"\$\([^)]+\)"
            ],
            
            # SQL injection
            "sql_injection": [
                r"'\s*OR\s+'1'='1", r";\s*DROP\s+TABLE", r";\s*DELETE\s+FROM",
                r"UNION\s+SELECT", r"--\s*", r"/\*.*\*/"
            ],
            
            # XSS
            "xss": [
                r"<script>", r"javascript:", r"onerror=", r"onload=",
                r"eval\(", r"document\.cookie"
            ],
            
            # Path traversal
            "path_traversal": [
                r"\.\./", r"%2e%2e%2f", r"\.\.\\", r"%2e%2e%5c"
            ]
        }
        
        # Compile regex patterns for efficiency
        self.compiled_patterns = {}
        for category, patterns in self.patterns.items():
            self.compiled_patterns[category] = [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    
    def _check_string_content(self, content: str) -> List[Dict[str, Any]]:
        """
        Check a string for potentially malicious patterns.
        
        Args:
            content: The string content to check
            
        Returns:
            List of detected issues, each a dict with category, pattern, and match
        """
        issues = []
        
        for category, patterns in self.compiled_patterns.items():
            for i, pattern in enumerate(patterns):
                matches = pattern.findall(content)
                if matches:
                    issues.append({
                        "category": category,
                        "pattern": self.patterns[category][i],
                        "matches": matches
                    })
        
        return issues
    
    def _check_dict_recursively(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Recursively check a dictionary for potentially malicious patterns.
        
        Args:
            data: The dictionary to check
            
        Returns:
            List of detected issues
        """
        issues = []
        
        for key, value in data.items():
            # Check the key if it's a string
            if isinstance(key, str):
                key_issues = self._check_string_content(key)
                if key_issues:
                    issues.extend(key_issues)
            
            # Check the value based on its type
            if isinstance(value, str):
                value_issues = self._check_string_content(value)
                if value_issues:
                    issues.extend(value_issues)
            elif isinstance(value, dict):
                # Recursive check for nested dictionaries
                dict_issues = self._check_dict_recursively(value)
                if dict_issues:
                    issues.extend(dict_issues)
            elif isinstance(value, list):
                # Check each item in the list
                for item in value:
                    if isinstance(item, str):
                        item_issues = self._check_string_content(item)
                        if item_issues:
                            issues.extend(item_issues)
                    elif isinstance(item, dict):
                        dict_issues = self._check_dict_recursively(item)
                        if dict_issues:
                            issues.extend(dict_issues)
        
        return issues
    
    def verify(self, message: Message) -> Dict[str, Any]:
        """
        Verify a message for potentially malicious content.
        
        Args:
            message: The message to verify
            
        Returns:
            Dict with verification results
        """
        try:
            all_issues = []
            
            # Check message content if it's a string
            if hasattr(message, 'content') and isinstance(message.content, str):
                content_issues = self._check_string_content(message.content)
                if content_issues:
                    all_issues.extend(content_issues)
            
            # Check message payload if it's a dictionary
            if hasattr(message, 'payload') and isinstance(message.payload, dict):
                payload_issues = self._check_dict_recursively(message.payload)
                if payload_issues:
                    all_issues.extend(payload_issues)
            
            # Check message metadata if it exists
            if hasattr(message, 'metadata') and isinstance(message.metadata, dict):
                metadata_issues = self._check_dict_recursively(message.metadata)
                if metadata_issues:
                    all_issues.extend(metadata_issues)
            
            # Determine result based on issues found
            if not all_issues:
                return {
                    "passed": True,
                    "reason": "No malicious patterns detected",
                    "risk_level": "none"
                }
            else:
                # Determine risk level based on categories and number of issues
                risk_level = "low"
                
                # Count issues by category
                category_counts = {}
                for issue in all_issues:
                    category = issue["category"]
                    category_counts[category] = category_counts.get(category, 0) + 1
                
                # Adjust risk level based on categories and counts
                if "command_injection" in category_counts or "sql_injection" in category_counts:
                    risk_level = "critical"
                elif "xss" in category_counts:
                    risk_level = "high"
                elif "path_traversal" in category_counts:
                    risk_level = "high"
                elif sum(category_counts.values()) > 3:
                    risk_level = "medium"
                
                # Create failure message
                categories = ", ".join(category_counts.keys())
                issue_count = sum(category_counts.values())
                
                return {
                    "passed": False,
                    "reason": f"Detected {issue_count} potential security {issue_count > 1 and 'issues' or 'issue'} in categories: {categories}",
                    "risk_level": risk_level,
                    "issues": all_issues
                }
        
        except Exception as e:
            logger.error(f"Error during content verification: {str(e)}")
            return {
                "passed": False,
                "reason": f"Content verification error: {str(e)}",
                "risk_level": "medium"
            }
