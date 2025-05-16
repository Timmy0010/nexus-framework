"""
MCP connector for the Nexus framework.

This module provides integration with the Model Context Protocol (MCP)
via mcp-desktop-commander, allowing agents to access external tools and resources.
"""

import logging
import json
import subprocess
from typing import Dict, List, Any, Optional, Union
import os
import uuid
import sys
import threading
import queue

# Set up logging
logger = logging.getLogger(__name__)

class MCPConnector:
    """
    Handles communication with mcp-desktop-commander for MCP tool interactions.
    
    This class encapsulates the communication with mcp-desktop-commander,
    allowing agents to discover and use tools exposed via MCP.
    """
    
    def __init__(
        self, 
        mcp_commander_path: Optional[str] = None, 
        timeout: int = 30
    ):
        """
        Initialize a new MCP connector.
        
        Args:
            mcp_commander_path: Optional path to the mcp-desktop-commander executable.
                                If not provided, it will be looked up in PATH.
            timeout: Timeout in seconds for MCP command execution.
        """
        self.mcp_commander_path = mcp_commander_path or "mcp-desktop-commander"
        self.timeout = timeout
        self._validate_commander()
        
        # Store discovered tools to avoid repeated calls
        self._tools_cache: Optional[List[Dict[str, Any]]] = None
        
        # Counter for request IDs
        self._request_id = 0
    
    def _validate_commander(self) -> None:
        """
        Validate that mcp-desktop-commander is accessible.
        
        Raises:
            RuntimeError: If mcp-desktop-commander cannot be found or executed.
        """
        try:
            # Just check if the executable exists and is callable
            if self.mcp_commander_path == "mcp-desktop-commander":
                # It's supposed to be in PATH, check if it's runnable
                result = subprocess.run(
                    ["mcp-desktop-commander", "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5
                )
                if result.returncode != 0:
                    logger.warning(f"mcp-desktop-commander returned non-zero exit code: {result.returncode}")
                    logger.warning(f"stderr: {result.stderr.decode('utf-8')}")
            else:
                # It's a specific path, check if the file exists
                if not os.path.isfile(self.mcp_commander_path):
                    raise FileNotFoundError(f"mcp-desktop-commander not found at: {self.mcp_commander_path}")
                
                # Check if it's executable
                result = subprocess.run(
                    [self.mcp_commander_path, "--version"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=5
                )
                if result.returncode != 0:
                    logger.warning(f"mcp-desktop-commander returned non-zero exit code: {result.returncode}")
                    logger.warning(f"stderr: {result.stderr.decode('utf-8')}")
            
            logger.info(f"mcp-desktop-commander validated at {self.mcp_commander_path}")
        except FileNotFoundError:
            logger.error(f"mcp-desktop-commander not found at: {self.mcp_commander_path}")
            raise RuntimeError(f"Cannot find mcp-desktop-commander. Please ensure it is installed "
                               f"and accessible at: {self.mcp_commander_path}")
        except subprocess.TimeoutExpired:
            logger.error("Timeout while validating mcp-desktop-commander")
            raise RuntimeError("Timeout while validating mcp-desktop-commander")
        except Exception as e:
            logger.error(f"Error validating mcp-desktop-commander: {str(e)}")
            raise RuntimeError(f"Error validating mcp-desktop-commander: {str(e)}")
    
    def _get_next_request_id(self) -> str:
        """Get a unique ID for the next JSON-RPC request."""
        self._request_id += 1
        return str(self._request_id)
    
    def _execute_mcp_command(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute an MCP command via mcp-desktop-commander.
        
        Args:
            method: The JSON-RPC method to call (e.g., "tools/list", "tools/call").
            params: Optional parameters for the method call.
            
        Returns:
            The parsed JSON response.
            
        Raises:
            RuntimeError: If the command fails or returns an error.
        """
        # Construct the JSON-RPC request
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": self._get_next_request_id()
        }
        
        if params:
            request["params"] = params
        
        request_json = json.dumps(request)
        logger.debug(f"Sending MCP command: {request_json}")
        
        try:
            # Execute the command
            result = subprocess.run(
                [self.mcp_commander_path],
                input=request_json.encode('utf-8'),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=self.timeout
            )
            
            if result.returncode != 0:
                stderr = result.stderr.decode('utf-8')
                logger.error(f"mcp-desktop-commander returned non-zero exit code: {result.returncode}")
                logger.error(f"stderr: {stderr}")
                raise RuntimeError(f"MCP command failed: {stderr}")
            
            stdout = result.stdout.decode('utf-8')
            logger.debug(f"MCP command response: {stdout}")
            
            # Parse the JSON response
            try:
                response = json.loads(stdout)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse MCP response: {e}")
                logger.error(f"Response was: {stdout}")
                raise RuntimeError(f"Invalid JSON response from MCP: {e}")
            
            # Check for JSON-RPC errors
            if "error" in response:
                error = response["error"]
                logger.error(f"MCP error: {error}")
                raise RuntimeError(f"MCP error: {error.get('message', 'Unknown error')}")
            
            return response.get("result", {})
        
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout while executing MCP command: {method}")
            raise RuntimeError(f"Timeout while executing MCP command: {method}")
        
        except Exception as e:
            logger.error(f"Error executing MCP command: {str(e)}")
            raise RuntimeError(f"Error executing MCP command: {str(e)}")
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """
        Query mcp-desktop-commander for the list of available MCP tools.
        
        Returns:
            A list of tool definitions (dictionaries).
        """
        # Use cache if available
        if self._tools_cache is not None:
            return self._tools_cache
        
        logger.info("Querying available MCP tools")
        tools = self._execute_mcp_command("tools/list")
        
        # Cache the result
        self._tools_cache = tools
        
        logger.info(f"Found {len(tools)} MCP tools")
        return tools
    
    def invoke_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a specific MCP tool.
        
        Args:
            tool_name: The name of the tool to execute.
            parameters: A dictionary of parameters for the tool.
            
        Returns:
            The result provided by the tool.
            
        Raises:
            RuntimeError: If the tool invocation fails.
        """
        logger.info(f"Invoking MCP tool: {tool_name}")
        logger.debug(f"Tool parameters: {parameters}")
        
        # Check if we have the tool list and if this tool exists
        if self._tools_cache is not None:
            tool_exists = any(tool.get("name") == tool_name for tool in self._tools_cache)
            if not tool_exists:
                logger.warning(f"Tool '{tool_name}' not found in cached tool list")
        
        # Prepare parameters for tools/call
        params = {
            "tool_name": tool_name,
            "parameters": parameters
        }
        
        # TODO: Add parameter validation against tool schema before sending
        
        # Execute the tool
        result = self._execute_mcp_command("tools/call", params)
        
        logger.info(f"MCP tool {tool_name} executed successfully")
        logger.debug(f"Tool result: {result}")
        
        return result
    
    def clear_cache(self) -> None:
        """Clear the tools cache, forcing a refresh on the next list_tools call."""
        logger.info("Clearing MCP tools cache")
        self._tools_cache = None
