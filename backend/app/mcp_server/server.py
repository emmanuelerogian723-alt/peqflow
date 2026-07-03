"""
Peq MCP Server
Exposes Peq's automation capabilities via the Model Context Protocol.
This allows Claude (and any MCP-compatible AI assistant) to:
1. Create automations from natural language
2. List and manage existing workflows
3. Execute workflows on demand
4. Test integrations
5. Get capabilities of all connected tools

The MCP server uses JSON-RPC over stdio (standard MCP transport).
"""
import json
import sys
import os
import asyncio
from typing import Dict, Any, List

# Add parent to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from app.engine.parser import parse_natural_language, validate_workflow, get_all_capabilities
from app.engine.runner import engine
from app.core.config import AVAILABLE_INTEGRATIONS, get_enabled_integrations


class PeqMCPServer:
    """MCP server that exposes Peq automation tools."""
    
    def __init__(self):
        self.tools = self._define_tools()
        self.resources = self._define_resources()
    
    def _define_tools(self) -> List[Dict]:
        """Define all MCP tools that Peq exposes."""
        return [
            {
                "name": "create_automation",
                "description": "Create an automation workflow from a natural language description. The workflow will be saved and can be activated to run automatically. Example: 'When someone pays on Paystack, send them a WhatsApp receipt and add them to Google Sheets'",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Natural language description of the automation. Start with 'When...' for the trigger, then list actions separated by commas or 'and'."
                        },
                        "user_id": {
                            "type": "string",
                            "description": "Optional user ID for the workflow owner.",
                            "default": ""
                        }
                    },
                    "required": ["description"]
                }
            },
            {
                "name": "parse_automation",
                "description": "Parse a natural language description into a structured workflow without saving it. Returns the parsed steps for review.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "description": {
                            "type": "string",
                            "description": "Natural language description of the automation."
                        }
                    },
                    "required": ["description"]
                }
            },
            {
                "name": "list_automations",
                "description": "List all saved automation workflows with their status (active, paused, draft).",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "user_id": {
                            "type": "string",
                            "description": "Optional filter by user ID.",
                            "default": ""
                        }
                    }
                }
            },
            {
                "name": "get_automation",
                "description": "Get details of a specific automation workflow by ID, including all steps.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The workflow ID to retrieve."
                        }
                    },
                    "required": ["workflow_id"]
                }
            },
            {
                "name": "activate_automation",
                "description": "Activate a workflow so it starts listening for triggers and running automatically.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The workflow ID to activate."
                        }
                    },
                    "required": ["workflow_id"]
                }
            },
            {
                "name": "pause_automation",
                "description": "Pause a workflow so it stops running.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The workflow ID to pause."
                        }
                    },
                    "required": ["workflow_id"]
                }
            },
            {
                "name": "delete_automation",
                "description": "Delete a workflow permanently.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The workflow ID to delete."
                        }
                    },
                    "required": ["workflow_id"]
                }
            },
            {
                "name": "execute_automation",
                "description": "Execute a workflow manually with a trigger context. Useful for testing or running on-demand.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The workflow ID to execute."
                        },
                        "trigger_context": {
                            "type": "object",
                            "description": "Context data for the trigger (e.g., customer_name, amount, customer_email, customer_phone).",
                            "default": {}
                        }
                    },
                    "required": ["workflow_id"]
                }
            },
            {
                "name": "list_integrations",
                "description": "List all available integrations and whether they are configured/enabled.",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "get_integration_capabilities",
                "description": "Get the full capability registry showing what each integration can do (triggers and actions).",
                "inputSchema": {
                    "type": "object",
                    "properties": {}
                }
            },
            {
                "name": "test_integration",
                "description": "Test if an integration's credentials are configured and valid.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "integration": {
                            "type": "string",
                            "description": "Integration name (paystack, whatsapp, gmail, google_sheets, slack, notion, telegram)."
                        }
                    },
                    "required": ["integration"]
                }
            },
            {
                "name": "get_execution_history",
                "description": "Get execution history for a workflow, showing each step's success/failure.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "workflow_id": {
                            "type": "string",
                            "description": "The workflow ID."
                        },
                        "limit": {
                            "type": "integer",
                            "description": "Maximum number of history entries to return.",
                            "default": 50
                        }
                    },
                    "required": ["workflow_id"]
                }
            }
        ]
    
    def _define_resources(self) -> List[Dict]:
        """Define MCP resources."""
        return [
            {
                "uri": "peq://integrations",
                "name": "Available Integrations",
                "description": "List of all integrations Peq can connect to",
                "mimeType": "application/json"
            },
            {
                "uri": "peq://capabilities",
                "name": "Integration Capabilities",
                "description": "Full registry of what each integration can do",
                "mimeType": "application/json"
            }
        ]
    
    async def handle_tool_call(self, tool_name: str, arguments: Dict) -> Any:
        """Handle a tool call and return the result."""
        
        if tool_name == "create_automation":
            wf = parse_natural_language(arguments["description"], arguments.get("user_id", ""))
            validation = validate_workflow(wf)
            if validation["valid"]:
                engine.save_workflow(wf)
            return {
                "success": validation["valid"],
                "workflow_id": wf.id,
                "name": wf.name,
                "steps": [{"type": s.step_type, "integration": s.integration, "operation": s.operation, "name": s.name} for s in wf.steps],
                "validation": validation
            }
        
        elif tool_name == "parse_automation":
            wf = parse_natural_language(arguments["description"])
            validation = validate_workflow(wf)
            return {
                "success": True,
                "steps": [{"type": s.step_type, "integration": s.integration, "operation": s.operation, "name": s.name, "description": s.description} for s in wf.steps],
                "validation": validation
            }
        
        elif tool_name == "list_automations":
            wfs = engine.list_workflows(arguments.get("user_id", ""))
            return {"workflows": wfs, "count": len(wfs)}
        
        elif tool_name == "get_automation":
            wf = engine.get_workflow(arguments["workflow_id"])
            if not wf:
                return {"error": "Workflow not found"}
            return wf.to_dict()
        
        elif tool_name == "activate_automation":
            success = engine.activate_workflow(arguments["workflow_id"])
            return {"success": success, "status": "active" if success else "failed"}
        
        elif tool_name == "pause_automation":
            success = engine.pause_workflow(arguments["workflow_id"])
            return {"success": success, "status": "paused" if success else "failed"}
        
        elif tool_name == "delete_automation":
            success = engine.delete_workflow(arguments["workflow_id"])
            return {"success": success}
        
        elif tool_name == "execute_automation":
            wf = engine.get_workflow(arguments["workflow_id"])
            if not wf:
                return {"error": "Workflow not found"}
            result = await engine.execute_workflow(wf, arguments.get("trigger_context", {}))
            return result
        
        elif tool_name == "list_integrations":
            enabled = get_enabled_integrations()
            return {
                "integrations": [
                    {"name": k, "display_name": v.display_name, "enabled": k in enabled}
                    for k, v in AVAILABLE_INTEGRATIONS.items()
                ]
            }
        
        elif tool_name == "get_integration_capabilities":
            return get_all_capabilities()
        
        elif tool_name == "test_integration":
            from app.integrations import get_integration
            from app.core.config import settings
            cred_map = {
                "paystack": {"secret_key": settings.PAYSTACK_SECRET_KEY},
                "whatsapp": {"token": settings.WHATSAPP_TOKEN, "phone_id": settings.WHATSAPP_PHONE_ID},
                "gmail": {"client_id": settings.GMAIL_CLIENT_ID, "client_secret": settings.GMAIL_CLIENT_SECRET, "refresh_token": settings.GMAIL_REFRESH_TOKEN},
                "google_sheets": {"credentials": settings.GOOGLE_SHEETS_CREDENTIALS},
                "slack": {"bot_token": settings.SLACK_BOT_TOKEN},
                "notion": {"token": settings.NOTION_TOKEN},
                "telegram": {"bot_token": settings.TELEGRAM_BOT_TOKEN},
            }
            integration_name = arguments["integration"]
            if integration_name not in cred_map:
                return {"error": f"Unknown integration: {integration_name}"}
            creds = cred_map[integration_name]
            if not any(creds.values()):
                return {"error": "Credentials not configured", "integration": integration_name}
            integration = get_integration(integration_name, creds)
            if not integration:
                return {"error": "Integration not implemented"}
            result = integration.test_connection()
            return {"success": result.success, "data": result.data, "error": result.error}
        
        elif tool_name == "get_execution_history":
            history = engine.get_execution_history(arguments["workflow_id"], arguments.get("limit", 50))
            return {"history": history, "count": len(history)}
        
        return {"error": f"Unknown tool: {tool_name}"}
    
    async def handle_resource_read(self, uri: str) -> str:
        """Handle a resource read request."""
        if uri == "peq://integrations":
            enabled = get_enabled_integrations()
            return json.dumps({
                "integrations": [
                    {"name": k, "display_name": v.display_name, "enabled": k in enabled}
                    for k, v in AVAILABLE_INTEGRATIONS.items()
                ]
            }, indent=2)
        elif uri == "peq://capabilities":
            return json.dumps(get_all_capabilities(), indent=2)
        return json.dumps({"error": "Unknown resource"})
    
    def handle_request(self, request: Dict) -> Dict:
        """Handle a JSON-RPC request (MCP protocol)."""
        method = request.get("method", "")
        req_id = request.get("id")
        params = request.get("params", {})
        
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False}
                    },
                    "serverInfo": {
                        "name": "peq",
                        "version": "1.0.0",
                    }
                }
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": self.tools}
            }
        
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            try:
                result = asyncio.run(self.handle_tool_call(tool_name, arguments))
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": json.dumps(result, indent=2, default=str)}]
                    }
                }
            except Exception as e:
                return {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": str(e)}
                }
        
        elif method == "resources/list":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"resources": self.resources}
            }
        
        elif method == "resources/read":
            uri = params.get("uri", "")
            content = asyncio.run(self.handle_resource_read(uri))
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "contents": [{"type": "text", "text": content}]
                }
            }
        
        elif method == "notifications/initialized":
            return None  # No response for notifications
        
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32601, "message": f"Method not found: {method}"}
        }
    
    def run(self):
        """Run the MCP server, reading from stdin and writing to stdout."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
                response = self.handle_request(request)
                if response is not None:
                    sys.stdout.write(json.dumps(response) + "\n")
                    sys.stdout.flush()
            except json.JSONDecodeError:
                continue
            except Exception as e:
                sys.stderr.write(f"Error: {str(e)}\n")
                sys.stderr.flush()


if __name__ == "__main__":
    server = PeqMCPServer()
    server.run()
