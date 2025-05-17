"""
Policy definitions and management for the Nexus Framework's access control system.

This module provides classes for defining and managing access control policies,
which determine how permissions are evaluated in different contexts.
"""

import enum
import json
import logging
import time
from typing import Dict, Set, List, Optional, Any, Tuple, FrozenSet, Callable

from .permissions import Permission, PermissionSet, PermissionError, ResourceType, ResourceAction
from .roles import Role, RoleManager, RoleError

logger = logging.getLogger(__name__)

class PolicyError(Exception):
    """Exception raised for policy-related errors."""
    pass

class EffectType(enum.Enum):
    """Types of effects a policy can have."""
    ALLOW = "allow"
    DENY = "deny"
    UNDETERMINED = "undetermined"

class PolicyContext:
    """
    Context information for policy evaluation.
    
    This class encapsulates all the contextual information that might be
    relevant for evaluating policies, such as the entity making the request,
    the resource being accessed, environment variables, etc.
    """
    
    def __init__(self, 
                entity_id: str = "",
                resource_type: str = "",
                resource_id: str = "",
                action: str = "",
                environment: Optional[Dict[str, Any]] = None,
                timestamp: Optional[float] = None,
                message_metadata: Optional[Dict[str, Any]] = None,
                additional_context: Optional[Dict[str, Any]] = None):
        """
        Initialize a policy context.
        
        Args:
            entity_id: ID of the entity making the request.
            resource_type: Type of resource being accessed.
            resource_id: ID of the resource being accessed.
            action: Action being performed on the resource.
            environment: Environment variables.
            timestamp: Time of the request. If None, current time is used.
            message_metadata: Metadata from the message, if applicable.
            additional_context: Any additional context information.
        """
        self.entity_id = entity_id
        self.resource_type = resource_type
        self.resource_id = resource_id
        self.action = action
        self.environment = environment or {}
        self.timestamp = timestamp or time.time()
        self.message_metadata = message_metadata or {}
        self.additional_context = additional_context or {}
    
    def get_value(self, path: str, default: Any = None) -> Any:
        """
        Get a value from the context using a dotted path.
        
        Args:
            path: Dotted path to the value (e.g., "environment.debug").
            default: Default value to return if path is not found.
            
        Returns:
            The value at the path, or the default value if not found.
        """
        parts = path.split('.')
        value: Any = self
        
        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            elif isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default
                
        return value
    
    def matches(self, conditions: Dict[str, Any]) -> bool:
        """
        Check if this context matches a set of conditions.
        
        Args:
            conditions: Dictionary of conditions, where keys are paths
                      and values are the expected values.
            
        Returns:
            True if all conditions match, False otherwise.
        """
        for path, expected in conditions.items():
            actual = self.get_value(path)
            
            # Handle wildcards in expected values
            if expected == "*":
                if actual is None:
                    return False
                continue
            
            # Handle list/set membership
            if isinstance(expected, list):
                if actual not in expected:
                    return False
                continue
            
            # Handle regular equality
            if actual != expected:
                return False
                
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the context to a dictionary.
        
        Returns:
            Dictionary representation of the context.
        """
        return {
            "entity_id": self.entity_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "action": self.action,
            "environment": self.environment,
            "timestamp": self.timestamp,
            "message_metadata": self.message_metadata,
            "additional_context": self.additional_context
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PolicyContext':
        """
        Create a context from a dictionary.
        
        Args:
            data: Dictionary representation of a context.
            
        Returns:
            A new policy context.
        """
        return cls(
            entity_id=data.get("entity_id", ""),
            resource_type=data.get("resource_type", ""),
            resource_id=data.get("resource_id", ""),
            action=data.get("action", ""),
            environment=data.get("environment", {}),
            timestamp=data.get("timestamp"),
            message_metadata=data.get("message_metadata", {}),
            additional_context=data.get("additional_context", {})
        )
    
    def __str__(self) -> str:
        return f"PolicyContext({self.entity_id}, {self.resource_type}, {self.action})"

class Policy:
    """
    Represents an access control policy.
    
    A policy defines a set of conditions and the effect (allow/deny) that
    should be applied when those conditions are met.
    """
    
    def __init__(self, 
                name: str,
                description: str = "",
                effect: EffectType = EffectType.ALLOW,
                conditions: Optional[Dict[str, Any]] = None,
                resource_patterns: Optional[List[str]] = None,
                action_patterns: Optional[List[str]] = None,
                entity_patterns: Optional[List[str]] = None,
                priority: int = 0):
        """
        Initialize a policy.
        
        Args:
            name: Unique policy name.
            description: Policy description.
            effect: Effect of the policy (allow or deny).
            conditions: Additional conditions for the policy to apply.
            resource_patterns: Patterns of resources this policy applies to.
            action_patterns: Patterns of actions this policy applies to.
            entity_patterns: Patterns of entities this policy applies to.
            priority: Priority of the policy (higher numbers take precedence).
        """
        self.name = name
        self.description = description
        self.effect = effect
        self.conditions = conditions or {}
        self.resource_patterns = resource_patterns or ["*"]
        self.action_patterns = action_patterns or ["*"]
        self.entity_patterns = entity_patterns or ["*"]
        self.priority = priority
    
    def matches(self, context: PolicyContext) -> bool:
        """
        Check if this policy applies to a given context.
        
        Args:
            context: The policy evaluation context.
            
        Returns:
            True if the policy applies to the context, False otherwise.
        """
        # Check entity patterns
        if not self._matches_pattern(context.entity_id, self.entity_patterns):
            return False
        
        # Check resource patterns
        resource_id = f"{context.resource_type}:{context.resource_id}"
        if not self._matches_pattern(resource_id, self.resource_patterns):
            return False
        
        # Check action patterns
        if not self._matches_pattern(context.action, self.action_patterns):
            return False
        
        # Check additional conditions
        return context.matches(self.conditions)
    
    def _matches_pattern(self, value: str, patterns: List[str]) -> bool:
        """
        Check if a value matches any of the given patterns.
        
        Patterns can use '*' as a wildcard.
        
        Args:
            value: Value to check.
            patterns: List of patterns to match against.
            
        Returns:
            True if the value matches any pattern, False otherwise.
        """
        for pattern in patterns:
            # Exact match
            if pattern == value:
                return True
            
            # Wildcard match
            if pattern == "*":
                return True
            
            # Prefix match with wildcard
            if pattern.endswith("*") and value.startswith(pattern[:-1]):
                return True
            
            # Suffix match with wildcard
            if pattern.startswith("*") and value.endswith(pattern[1:]):
                return True
            
            # Contains match with wildcards
            if pattern.startswith("*") and pattern.endswith("*") and pattern[1:-1] in value:
                return True
                
        return False
    
    def evaluate(self, context: PolicyContext) -> EffectType:
        """
        Evaluate the policy for a given context.
        
        Args:
            context: The policy evaluation context.
            
        Returns:
            The effect of the policy (ALLOW, DENY, or UNDETERMINED).
        """
        if self.matches(context):
            return self.effect
        else:
            return EffectType.UNDETERMINED
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the policy to a dictionary.
        
        Returns:
            Dictionary representation of the policy.
        """
        return {
            "name": self.name,
            "description": self.description,
            "effect": self.effect.value,
            "conditions": self.conditions,
            "resource_patterns": self.resource_patterns,
            "action_patterns": self.action_patterns,
            "entity_patterns": self.entity_patterns,
            "priority": self.priority
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Policy':
        """
        Create a policy from a dictionary.
        
        Args:
            data: Dictionary representation of a policy.
            
        Returns:
            A new policy.
        """
        effect = EffectType(data.get("effect", EffectType.ALLOW.value))
        
        return cls(
            name=data["name"],
            description=data.get("description", ""),
            effect=effect,
            conditions=data.get("conditions", {}),
            resource_patterns=data.get("resource_patterns", ["*"]),
            action_patterns=data.get("action_patterns", ["*"]),
            entity_patterns=data.get("entity_patterns", ["*"]),
            priority=data.get("priority", 0)
        )
    
    def __str__(self) -> str:
        return f"Policy({self.name}, {self.effect.value})"

class PolicySet:
    """
    A set of policies with combined evaluation logic.
    
    This class provides operations for working with groups of policies
    and evaluating them as a unit.
    """
    
    def __init__(self, policies: Optional[List[Policy]] = None):
        """
        Initialize a policy set.
        
        Args:
            policies: Initial list of policies.
        """
        self.policies = policies or []
    
    def add_policy(self, policy: Policy) -> None:
        """
        Add a policy to the set.
        
        Args:
            policy: The policy to add.
        """
        self.policies.append(policy)
        
        # Sort policies by priority (descending)
        self.policies.sort(key=lambda p: p.priority, reverse=True)
    
    def remove_policy(self, policy_name: str) -> None:
        """
        Remove a policy from the set.
        
        Args:
            policy_name: Name of the policy to remove.
            
        Raises:
            PolicyError: If the policy is not found.
        """
        for i, policy in enumerate(self.policies):
            if policy.name == policy_name:
                del self.policies[i]
                return
                
        raise PolicyError(f"Policy '{policy_name}' not found")
    
    def get_policy(self, policy_name: str) -> Policy:
        """
        Get a policy by name.
        
        Args:
            policy_name: Name of the policy to get.
            
        Returns:
            The policy.
            
        Raises:
            PolicyError: If the policy is not found.
        """
        for policy in self.policies:
            if policy.name == policy_name:
                return policy
                
        raise PolicyError(f"Policy '{policy_name}' not found")
    
    def evaluate(self, context: PolicyContext) -> EffectType:
        """
        Evaluate all policies in the set for a given context.
        
        Policies are evaluated in order of priority (highest first).
        The first definitive effect (ALLOW or DENY) is returned.
        If no policy applies, UNDETERMINED is returned.
        
        Args:
            context: The policy evaluation context.
            
        Returns:
            The combined effect of all applicable policies.
        """
        # Default to undetermined if no policies apply
        result = EffectType.UNDETERMINED
        
        for policy in self.policies:
            effect = policy.evaluate(context)
            
            # If we get a definitive effect, return it
            if effect != EffectType.UNDETERMINED:
                logger.debug(f"Policy '{policy.name}' matched with effect {effect.value}")
                return effect
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the policy set to a dictionary.
        
        Returns:
            Dictionary representation of the policy set.
        """
        return {
            "policies": [p.to_dict() for p in self.policies]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PolicySet':
        """
        Create a policy set from a dictionary.
        
        Args:
            data: Dictionary representation of a policy set.
            
        Returns:
            A new policy set.
        """
        policies = [Policy.from_dict(p) for p in data.get("policies", [])]
        return cls(policies)
    
    def __len__(self) -> int:
        return len(self.policies)
    
    def __iter__(self):
        return iter(self.policies)
    
    def __str__(self) -> str:
        return f"PolicySet({len(self.policies)} policies)"

class PolicyEngine:
    """
    Engine for evaluating policies against requests.
    
    This class provides a central point for policy evaluation,
    combining multiple policy sets with different evaluation strategies.
    """
    
    def __init__(self):
        """Initialize the policy engine with empty policy sets."""
        # Default policy set
        self.default_policies = PolicySet()
        
        # Resource-specific policy sets
        self.resource_policies: Dict[str, PolicySet] = {}
        
        # Action-specific policy sets
        self.action_policies: Dict[str, PolicySet] = {}
        
        # Entity-specific policy sets
        self.entity_policies: Dict[str, PolicySet] = {}
    
    def add_policy(self, policy: Policy, policy_set: str = "default") -> None:
        """
        Add a policy to a specific policy set.
        
        Args:
            policy: The policy to add.
            policy_set: The policy set to add to ("default" or "resource:TYPE"
                       or "action:TYPE" or "entity:TYPE").
        """
        if policy_set == "default":
            self.default_policies.add_policy(policy)
        elif policy_set.startswith("resource:"):
            resource_type = policy_set[9:]
            if resource_type not in self.resource_policies:
                self.resource_policies[resource_type] = PolicySet()
            self.resource_policies[resource_type].add_policy(policy)
        elif policy_set.startswith("action:"):
            action_type = policy_set[7:]
            if action_type not in self.action_policies:
                self.action_policies[action_type] = PolicySet()
            self.action_policies[action_type].add_policy(policy)
        elif policy_set.startswith("entity:"):
            entity_type = policy_set[7:]
            if entity_type not in self.entity_policies:
                self.entity_policies[entity_type] = PolicySet()
            self.entity_policies[entity_type].add_policy(policy)
        else:
            raise PolicyError(f"Unknown policy set: {policy_set}")
    
    def evaluate(self, context: PolicyContext) -> Tuple[EffectType, Optional[str]]:
        """
        Evaluate policies for a given context.
        
        Args:
            context: The policy evaluation context.
            
        Returns:
            Tuple of (effect, reason). If no policy applies, the effect is
            UNDETERMINED and reason is None.
        """
        # Check entity-specific policies
        if context.entity_id:
            if context.entity_id in self.entity_policies:
                effect = self.entity_policies[context.entity_id].evaluate(context)
                if effect != EffectType.UNDETERMINED:
                    return effect, f"Entity-specific policy for {context.entity_id}"
        
        # Check resource-specific policies
        if context.resource_type:
            if context.resource_type in self.resource_policies:
                effect = self.resource_policies[context.resource_type].evaluate(context)
                if effect != EffectType.UNDETERMINED:
                    return effect, f"Resource-specific policy for {context.resource_type}"
        
        # Check action-specific policies
        if context.action:
            if context.action in self.action_policies:
                effect = self.action_policies[context.action].evaluate(context)
                if effect != EffectType.UNDETERMINED:
                    return effect, f"Action-specific policy for {context.action}"
        
        # Check default policies
        effect = self.default_policies.evaluate(context)
        if effect != EffectType.UNDETERMINED:
            return effect, "Default policy"
        
        # No policy applied
        return EffectType.UNDETERMINED, None
    
    def is_allowed(self, context: PolicyContext) -> bool:
        """
        Check if an action is allowed in a given context.
        
        Args:
            context: The policy evaluation context.
            
        Returns:
            True if the action is allowed, False otherwise.
        """
        effect, _ = self.evaluate(context)
        return effect == EffectType.ALLOW
    
    def why(self, context: PolicyContext) -> str:
        """
        Get the reason for an access control decision.
        
        Args:
            context: The policy evaluation context.
            
        Returns:
            A human-readable explanation of the decision.
        """
        effect, reason = self.evaluate(context)
        
        if effect == EffectType.ALLOW:
            return f"Access allowed: {reason}"
        elif effect == EffectType.DENY:
            return f"Access denied: {reason}"
        else:
            return "No applicable policy found. Access is denied by default."
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the policy engine to a dictionary.
        
        Returns:
            Dictionary representation of the policy engine.
        """
        return {
            "default_policies": self.default_policies.to_dict(),
            "resource_policies": {k: v.to_dict() for k, v in self.resource_policies.items()},
            "action_policies": {k: v.to_dict() for k, v in self.action_policies.items()},
            "entity_policies": {k: v.to_dict() for k, v in self.entity_policies.items()}
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PolicyEngine':
        """
        Create a policy engine from a dictionary.
        
        Args:
            data: Dictionary representation of a policy engine.
            
        Returns:
            A new policy engine.
        """
        engine = cls()
        
        # Load default policies
        if "default_policies" in data:
            engine.default_policies = PolicySet.from_dict(data["default_policies"])
        
        # Load resource policies
        for resource_type, policy_data in data.get("resource_policies", {}).items():
            engine.resource_policies[resource_type] = PolicySet.from_dict(policy_data)
        
        # Load action policies
        for action_type, policy_data in data.get("action_policies", {}).items():
            engine.action_policies[action_type] = PolicySet.from_dict(policy_data)
        
        # Load entity policies
        for entity_type, policy_data in data.get("entity_policies", {}).items():
            engine.entity_policies[entity_type] = PolicySet.from_dict(policy_data)
        
        return engine

class PolicyManager:
    """
    Manager for loading, saving, and applying policies.
    
    This class provides functionality for managing policies in the system,
    including loading from configuration files and integrating with the
    role manager.
    """
    
    def __init__(self, role_manager: Optional[RoleManager] = None):
        """
        Initialize the policy manager.
        
        Args:
            role_manager: Optional role manager for role-based access control.
        """
        self.engine = PolicyEngine()
        self.role_manager = role_manager or RoleManager()
    
    def add_policy(self, policy: Policy, policy_set: str = "default") -> None:
        """
        Add a policy to the engine.
        
        Args:
            policy: The policy to add.
            policy_set: The policy set to add to.
        """
        self.engine.add_policy(policy, policy_set)
    
    def load_from_file(self, file_path: str) -> None:
        """
        Load policies from a JSON file.
        
        Args:
            file_path: Path to the JSON file.
            
        Raises:
            PolicyError: If the file cannot be loaded.
        """
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            # Load engine data
            if "engine" in data:
                self.engine = PolicyEngine.from_dict(data["engine"])
                
            # Load individual policies
            for policy_data in data.get("policies", []):
                policy = Policy.from_dict(policy_data)
                policy_set = policy_data.get("policy_set", "default")
                self.add_policy(policy, policy_set)
                
        except Exception as e:
            raise PolicyError(f"Failed to load policies from {file_path}: {e}")
    
    def save_to_file(self, file_path: str) -> None:
        """
        Save policies to a JSON file.
        
        Args:
            file_path: Path to the JSON file.
            
        Raises:
            PolicyError: If the file cannot be saved.
        """
        try:
            data = {
                "engine": self.engine.to_dict(),
                "policies": [] # Individual policies are already in the engine
            }
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception as e:
            raise PolicyError(f"Failed to save policies to {file_path}: {e}")
    
    def is_allowed(self, entity_id: str, resource_type: str, 
                  resource_id: str, action: str,
                  context_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if an action is allowed.
        
        This method first checks role-based permissions, then evaluates policies.
        
        Args:
            entity_id: ID of the entity performing the action.
            resource_type: Type of resource being accessed.
            resource_id: ID of the resource being accessed.
            action: Action being performed.
            context_data: Additional context data.
            
        Returns:
            True if the action is allowed, False otherwise.
        """
        # Check role-based permissions
        if self.role_manager:
            try:
                # Create a permission object for the request
                # Convert resource_type and action to appropriate enum values
                try:
                    res_type = ResourceType.from_string(resource_type)
                    act = ResourceAction.from_string(action)
                    
                    permission = Permission(res_type, act, resource_id)
                    
                    # Check if entity has this permission
                    if self.role_manager.has_permission(entity_id, permission):
                        logger.debug(f"Access allowed by role-based permission for {entity_id}")
                        return True
                        
                except Exception as e:
                    logger.warning(f"Error checking role-based permission: {e}")
            except Exception as e:
                logger.warning(f"Error in role-based permission check: {e}")
        
        # Check policy-based permissions
        context = PolicyContext(
            entity_id=entity_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            additional_context=context_data or {}
        )
        
        return self.engine.is_allowed(context)
    
    def why(self, entity_id: str, resource_type: str, 
           resource_id: str, action: str,
           context_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Get the reason for an access control decision.
        
        Args:
            entity_id: ID of the entity performing the action.
            resource_type: Type of resource being accessed.
            resource_id: ID of the resource being accessed.
            action: Action being performed.
            context_data: Additional context data.
            
        Returns:
            A human-readable explanation of the decision.
        """
        # Check role-based permissions first
        if self.role_manager:
            try:
                res_type = ResourceType.from_string(resource_type)
                act = ResourceAction.from_string(action)
                
                permission = Permission(res_type, act, resource_id)
                
                if self.role_manager.has_permission(entity_id, permission):
                    roles = self.role_manager.get_entity_roles(entity_id)
                    return f"Access allowed by role-based permissions. Entity {entity_id} has roles: {', '.join(roles)}"
            except Exception as e:
                logger.warning(f"Error checking role-based permission: {e}")
        
        # Check policy-based permissions
        context = PolicyContext(
            entity_id=entity_id,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            additional_context=context_data or {}
        )
        
        return self.engine.why(context)
    
    def create_basic_policies(self) -> None:
        """
        Create some basic default policies.
        
        This method sets up some common policies that are generally useful.
        """
        # Policy 1: Admins can do anything
        admin_policy = Policy(
            name="admin_full_access",
            description="Administrators have full access to all resources",
            effect=EffectType.ALLOW,
            entity_patterns=["admin*"],
            resource_patterns=["*"],
            action_patterns=["*"],
            priority=1000  # Very high priority
        )
        self.add_policy(admin_policy)
        
        # Policy 2: System services have high access
        system_policy = Policy(
            name="system_service_access",
            description="System services have high access to core resources",
            effect=EffectType.ALLOW,
            entity_patterns=["system*", "service*"],
            resource_patterns=["system:*", "service:*"],
            action_patterns=["read", "execute"],
            priority=900
        )
        self.add_policy(system_policy)
        
        # Policy 3: Default deny for sensitive operations
        sensitive_deny = Policy(
            name="sensitive_operations_deny",
            description="Deny sensitive operations by default",
            effect=EffectType.DENY,
            resource_patterns=["config:*", "security:*"],
            action_patterns=["update", "delete", "manage"],
            priority=500
        )
        self.add_policy(sensitive_deny)
        
        # Policy 4: Default allow for basic read operations
        read_allow = Policy(
            name="basic_read_allow",
            description="Allow basic read operations by default",
            effect=EffectType.ALLOW,
            action_patterns=["read", "list"],
            priority=100
        )
        self.add_policy(read_allow)
        
        # Policy 5: Default deny for everything else
        default_deny = Policy(
            name="default_deny",
            description="Deny everything by default",
            effect=EffectType.DENY,
            resource_patterns=["*"],
            action_patterns=["*"],
            priority=1  # Lowest priority
        )
        self.add_policy(default_deny)
        
        logger.info("Created basic policies")
