"""
Peq API Routes
All REST endpoints for workflow management, execution, and integration testing.
"""
import json
import os
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime

from ..engine.parser import parse_natural_language, validate_workflow, get_all_capabilities
from ..engine.runner import engine
from ..core.config import settings, AVAILABLE_INTEGRATIONS, get_enabled_integrations


router = APIRouter()


# ============ MODELS ============

class ParseRequest(BaseModel):
    description: str
    user_id: str = ""

class WorkflowActionRequest(BaseModel):
    workflow_id: str

class ExecuteRequest(BaseModel):
    workflow_id: str
    trigger_context: Dict[str, Any] = {}

class TestIntegrationRequest(BaseModel):
    integration: str


# ============ ROUTES ============

@router.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "timestamp": datetime.utcnow().isoformat(),
    }


@router.get("/health")
async def health():
    enabled = get_enabled_integrations()
    return {
        "status": "ok",
        "version": settings.APP_VERSION,
        "enabled_integrations": enabled,
        "environment": settings.ENVIRONMENT,
    }


# ----- WORKFLOW MANAGEMENT -----

@router.post("/workflows/parse")
async def parse_workflow(req: ParseRequest):
    """Parse a natural language description into a structured workflow."""
    try:
        workflow = parse_natural_language(req.description, req.user_id)
        validation = validate_workflow(workflow)
        return {
            "success": True,
            "workflow": workflow.to_dict(),
            "validation": validation,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/workflows/create")
async def create_workflow(req: ParseRequest):
    """Parse and save a workflow from natural language."""
    try:
        workflow = parse_natural_language(req.description, req.user_id)
        validation = validate_workflow(workflow)
        if not validation["valid"]:
            return {"success": False, "validation": validation, "workflow": workflow.to_dict()}
        
        engine.save_workflow(workflow)
        return {
            "success": True,
            "workflow_id": workflow.id,
            "workflow": workflow.to_dict(),
            "validation": validation,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/workflows")
async def list_workflows(user_id: str = ""):
    """List all saved workflows."""
    workflows = engine.list_workflows(user_id)
    return {"success": True, "workflows": workflows, "count": len(workflows)}


@router.get("/workflows/{workflow_id}")
async def get_workflow(workflow_id: str):
    """Get a specific workflow by ID."""
    wf = engine.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"success": True, "workflow": wf.to_dict()}


@router.delete("/workflows/{workflow_id}")
async def delete_workflow(workflow_id: str):
    """Delete a workflow."""
    success = engine.delete_workflow(workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"success": True, "deleted": workflow_id}


@router.post("/workflows/activate")
async def activate_workflow(req: WorkflowActionRequest):
    """Activate a workflow so it starts listening for triggers."""
    success = engine.activate_workflow(req.workflow_id)
    if not success:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"success": True, "status": "active", "workflow_id": req.workflow_id}


@router.post("/workflows/pause")
async def pause_workflow(req: WorkflowActionRequest):
    """Pause a workflow."""
    success = engine.pause_workflow(req.workflow_id)
    return {"success": True, "status": "paused", "workflow_id": req.workflow_id}


# ----- EXECUTION -----

@router.post("/workflows/execute")
async def execute_workflow(req: ExecuteRequest, background_tasks: BackgroundTasks):
    """Execute a workflow with the given trigger context."""
    wf = engine.get_workflow(req.workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    result = await engine.execute_workflow(wf, req.trigger_context)
    return result


@router.get("/workflows/{workflow_id}/history")
async def get_history(workflow_id: str, limit: int = 50):
    """Get execution history for a workflow."""
    history = engine.get_execution_history(workflow_id, limit)
    return {"success": True, "history": history, "count": len(history)}


# ----- INTEGRATIONS -----

@router.get("/integrations")
async def list_integrations():
    """List all available integrations and their status."""
    enabled = get_enabled_integrations()
    result = []
    for key, config in AVAILABLE_INTEGRATIONS.items():
        result.append({
            "name": key,
            "display_name": config.display_name,
            "icon": config.icon,
            "enabled": key in enabled,
            "required_env_vars": config.required_env_vars,
        })
    return {"success": True, "integrations": result}


@router.get("/integrations/capabilities")
async def get_capabilities():
    """Get the full capability registry showing what each integration can do."""
    caps = get_all_capabilities()
    return {"success": True, "capabilities": caps}


@router.post("/integrations/test")
async def test_integration(req: TestIntegrationRequest):
    """Test if an integration's credentials are configured and valid."""
    from ..integrations import get_integration
    from ..core.config import settings
    
    cred_map = {
        "paystack": {"secret_key": settings.PAYSTACK_SECRET_KEY},
        "whatsapp": {"token": settings.WHATSAPP_TOKEN, "phone_id": settings.WHATSAPP_PHONE_ID},
        "gmail": {"client_id": settings.GMAIL_CLIENT_ID, "client_secret": settings.GMAIL_CLIENT_SECRET, "refresh_token": settings.GMAIL_REFRESH_TOKEN},
        "google_sheets": {"credentials": settings.GOOGLE_SHEETS_CREDENTIALS},
        "slack": {"bot_token": settings.SLACK_BOT_TOKEN},
        "notion": {"token": settings.NOTION_TOKEN},
        "telegram": {"bot_token": settings.TELEGRAM_BOT_TOKEN},
    }
    
    if req.integration not in cred_map:
        raise HTTPException(status_code=404, detail="Unknown integration")
    
    creds = cred_map[req.integration]
    if not any(creds.values()):
        return {"success": False, "error": "Credentials not configured", "integration": req.integration}
    
    integration = get_integration(req.integration, creds)
    if not integration:
        return {"success": False, "error": "Integration not implemented"}
    
    result = integration.test_connection()
    return {"success": result.success, "data": result.data, "error": result.error, "integration": req.integration}


# ----- WEBHOOKS (for triggers) -----

@router.post("/webhooks/paystack")
async def paystack_webhook(background_tasks: BackgroundTasks, payload: Dict = None):
    """Handle Paystack webhook events."""
    event = payload.get("event", "")
    data = payload.get("data", {})
    
    if event == "charge.success":
        context = {
            "event_type": "payment.received",
            "customer_name": data.get("customer", {}).get("first_name", ""),
            "customer_email": data.get("customer", {}).get("email", ""),
            "amount": data.get("amount", 0) / 100,  # Convert from kobo
            "reference": data.get("reference", ""),
            "transaction_id": data.get("id", ""),
        }
        
        # Find workflows with paystack payment.received trigger
        for wf_id, wf in engine.active_workflows.items():
            for step in wf.steps:
                if step.step_type == "trigger" and step.integration == "paystack" and step.operation == "payment.received":
                    background_tasks.add_task(engine.execute_workflow, wf, context)
                    break
        
        return {"status": "ok", "triggered": True}
    
    return {"status": "ok", "event": event}


@router.post("/webhooks/whatsapp")
async def whatsapp_webhook(background_tasks: BackgroundTasks, payload: Dict = None):
    """Handle WhatsApp webhook events."""
    # Parse incoming WhatsApp message
    entry = payload.get("entry", [{}])[0] if payload.get("entry") else {}
    changes = entry.get("changes", [{}])[0] if entry.get("changes") else {}
    value = changes.get("value", {})
    messages = value.get("messages", [])
    
    if messages:
        msg = messages[0]
        context = {
            "event_type": "message.received",
            "customer_phone": msg.get("from", ""),
            "message_text": msg.get("text", {}).get("body", ""),
            "message_id": msg.get("id", ""),
        }
        
        for wf_id, wf in engine.active_workflows.items():
            for step in wf.steps:
                if step.step_type == "trigger" and step.integration == "whatsapp" and step.operation == "message.received":
                    background_tasks.add_task(engine.execute_workflow, wf, context)
                    break
        
        return {"status": "ok", "triggered": True}
    
    return {"status": "ok"}


@router.get("/webhooks/whatsapp")
async def whatsapp_verify(hub_mode: str = "", hub_challenge: str = "", hub_verify_token: str = ""):
    """Verify WhatsApp webhook setup."""
    if hub_mode == "subscribe" and hub_verify_token == settings.WHATSAPP_VERIFY_TOKEN:
        return int(hub_challenge)
    raise HTTPException(status_code=403, detail="Verification failed")
