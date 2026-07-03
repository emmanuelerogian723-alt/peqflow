"""
FlowMind Runtime Engine
Executes workflows step by step, passing context between steps.
Handles delays, conditions, error retries, and logging.
"""
import asyncio
import time
import json
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import asdict

from .parser import Workflow, WorkflowStep, validate_workflow
from ..integrations import get_integration, ExecutionResult
from ..core.config import settings


class RuntimeEngine:
    """Executes workflows and manages their lifecycle."""
    
    def __init__(self, db_path: str = "flowmind.db"):
        self.db_path = db_path
        self.active_workflows: Dict[str, Workflow] = {}
        self._init_db()
    
    def _init_db(self):
        """Initialize SQLite database for workflow persistence."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS workflows (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                data TEXT NOT NULL,
                status TEXT DEFAULT 'draft',
                created_by TEXT,
                created_date TEXT,
                updated_date TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS execution_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workflow_id TEXT NOT NULL,
                step_id TEXT,
                step_name TEXT,
                status TEXT,
                data TEXT,
                error TEXT,
                timestamp TEXT
            )
        """)
        conn.commit()
        conn.close()
    
    def save_workflow(self, workflow: Workflow) -> bool:
        """Save a workflow to the database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        now = datetime.utcnow().isoformat()
        data = json.dumps(workflow.to_dict())
        c.execute("""
            INSERT OR REPLACE INTO workflows (id, name, description, data, status, created_by, created_date, updated_date)
            VALUES (?, ?, ?, ?, ?, ?, COALESCE((SELECT created_date FROM workflows WHERE id=?), ?), ?)
        """, (workflow.id, workflow.name, workflow.description, data, workflow.status,
              workflow.created_by, workflow.id, now, now))
        conn.commit()
        conn.close()
        return True
    
    def get_workflow(self, workflow_id: str) -> Optional[Workflow]:
        """Load a workflow from the database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("SELECT data FROM workflows WHERE id=?", (workflow_id,))
        row = c.fetchone()
        conn.close()
        if row:
            data = json.loads(row[0])
            steps = [WorkflowStep(**s) for s in data.get("steps", [])]
            return Workflow(
                id=data["id"], name=data["name"], description=data["description"],
                steps=steps, status=data.get("status", "draft"),
                created_by=data.get("created_by", ""), tags=data.get("tags", [])
            )
        return None
    
    def list_workflows(self, user_id: str = "") -> List[Dict]:
        """List all workflows."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        if user_id:
            c.execute("SELECT id, name, description, status, created_date FROM workflows WHERE created_by=? ORDER BY updated_date DESC", (user_id,))
        else:
            c.execute("SELECT id, name, description, status, created_date FROM workflows ORDER BY updated_date DESC")
        rows = c.fetchall()
        conn.close()
        return [{"id": r[0], "name": r[1], "description": r[2], "status": r[3], "created_date": r[4]} for r in rows]
    
    def delete_workflow(self, workflow_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("DELETE FROM workflows WHERE id=?", (workflow_id,))
        conn.commit()
        conn.close()
        return True
    
    def update_status(self, workflow_id: str, status: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("UPDATE workflows SET status=?, updated_date=? WHERE id=?",
                  (status, datetime.utcnow().isoformat(), workflow_id))
        conn.commit()
        conn.close()
        return True
    
    def _log_execution(self, workflow_id: str, step: WorkflowStep, result: ExecutionResult):
        """Log an execution step to the database."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            INSERT INTO execution_logs (workflow_id, step_id, step_name, status, data, error, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (workflow_id, step.id, step.name,
              "success" if result.success else "failed",
              json.dumps(result.data or {}),
              result.error,
              datetime.utcnow().isoformat()))
        conn.commit()
        conn.close()
    
    def get_execution_history(self, workflow_id: str, limit: int = 50) -> List[Dict]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute("""
            SELECT id, step_id, step_name, status, data, error, timestamp
            FROM execution_logs WHERE workflow_id=? ORDER BY id DESC LIMIT ?
        """, (workflow_id, limit))
        rows = c.fetchall()
        conn.close()
        return [{"id": r[0], "step_id": r[1], "step_name": r[2], "status": r[3],
                 "data": json.loads(r[4]) if r[4] else {}, "error": r[5], "timestamp": r[6]} for r in rows]
    
    def _get_credentials(self, integration: str) -> Dict[str, str]:
        """Get API credentials for an integration from environment variables."""
        cred_map = {
            "paystack": {"secret_key": os.getenv("PAYSTACK_SECRET_KEY", "")},
            "whatsapp": {"token": os.getenv("WHATSAPP_TOKEN", ""), "phone_id": os.getenv("WHATSAPP_PHONE_ID", "")},
            "gmail": {
                "client_id": os.getenv("GMAIL_CLIENT_ID", ""),
                "client_secret": os.getenv("GMAIL_CLIENT_SECRET", ""),
                "refresh_token": os.getenv("GMAIL_REFRESH_TOKEN", ""),
            },
            "google_sheets": {"credentials": os.getenv("GOOGLE_SHEETS_CREDENTIALS", "")},
            "slack": {"bot_token": os.getenv("SLACK_BOT_TOKEN", "")},
            "notion": {"token": os.getenv("NOTION_TOKEN", "")},
            "telegram": {"bot_token": os.getenv("TELEGRAM_BOT_TOKEN", "")},
        }
        return cred_map.get(integration, {})
    
    async def execute_step(self, step: WorkflowStep, context: Dict) -> ExecutionResult:
        """Execute a single workflow step."""
        # Handle internal steps
        if step.integration == "internal":
            if step.operation == "delay":
                delay = step.parameters
                duration = delay.get("duration", 1)
                unit = delay.get("unit", "days")
                if unit == "minutes":
                    wait = duration * 60
                elif unit == "hours":
                    wait = duration * 3600
                elif unit == "days":
                    wait = duration * 86400
                elif unit == "weeks":
                    wait = duration * 604800
                else:
                    wait = duration * 86400
                # For demo/testing, cap at 60 seconds
                if os.getenv("ENVIRONMENT") == "development":
                    wait = min(wait, 10)
                    print(f"  [DEV] Delay shortened to {wait}s")
                await asyncio.sleep(wait)
                return ExecutionResult(success=True, data={"delayed": f"{duration} {unit}"})
            
            elif step.operation == "notify.user":
                return ExecutionResult(success=True, data={"notification": step.parameters})
            
            elif step.operation == "http.request":
                import httpx
                try:
                    method = step.parameters.get("method", "GET").upper()
                    url = step.parameters.get("url", "")
                    headers = step.parameters.get("headers", {})
                    body = step.parameters.get("body", {})
                    async with httpx.AsyncClient() as client:
                        if method == "GET":
                            resp = await client.get(url, headers=headers, timeout=15)
                        elif method == "POST":
                            resp = await client.post(url, json=body, headers=headers, timeout=15)
                        else:
                            resp = await client.request(method, url, json=body, headers=headers, timeout=15)
                    return ExecutionResult(success=True, data={"status_code": resp.status_code, "body": resp.text[:500]})
                except Exception as e:
                    return ExecutionResult(success=False, error=str(e))
            
            elif step.operation == "ai.generate":
                return ExecutionResult(success=True, data={"generated": "AI generation placeholder"})
            
            elif step.operation == "condition":
                # Evaluate condition against context
                field = step.parameters.get("field", "")
                operator = step.parameters.get("operator", "equals")
                value = step.parameters.get("value", "")
                actual = context.get(field, "")
                passed = False
                if operator == "equals":
                    passed = str(actual) == str(value)
                elif operator == "not_equals":
                    passed = str(actual) != str(value)
                elif operator == "gt":
                    try:
                        passed = float(actual) > float(value)
                    except:
                        passed = False
                elif operator == "lt":
                    try:
                        passed = float(actual) < float(value)
                    except:
                        passed = False
                elif operator == "contains":
                    passed = str(value) in str(actual)
                return ExecutionResult(success=passed, data={"condition_met": passed})
            
            return ExecutionResult(success=True, data={"internal": True})
        
        # Handle external integrations
        credentials = self._get_credentials(step.integration)
        if not any(credentials.values()):
            return ExecutionResult(success=False, error=f"No credentials configured for {step.integration}")
        
        integration = get_integration(step.integration, credentials)
        if not integration:
            return ExecutionResult(success=False, error=f"Integration {step.integration} not found")
        
        # Execute the action
        result = integration.execute_action(step.operation, step.parameters, context)
        return result
    
    async def execute_workflow(self, workflow: Workflow, trigger_context: Dict = None) -> Dict:
        """Execute a complete workflow with the given trigger context."""
        validation = validate_workflow(workflow)
        if not validation["valid"]:
            return {"success": False, "error": "Invalid workflow", "issues": validation["issues"]}
        
        context = trigger_context or {}
        results = []
        
        # Find the trigger step
        trigger_step = None
        for step in workflow.steps:
            if step.step_type == "trigger":
                trigger_step = step
                break
        
        # Start from trigger or first step
        current_step = trigger_step or (workflow.steps[0] if workflow.steps else None)
        
        while current_step:
            print(f"  Executing: [{current_step.step_type}] {current_step.integration}.{current_step.operation} - {current_step.name}")
            
            result = await self.execute_step(current_step, context)
            self._log_execution(workflow.id, current_step, result)
            results.append({
                "step_id": current_step.id,
                "step_name": current_step.name,
                "integration": current_step.integration,
                "operation": current_step.operation,
                "success": result.success,
                "data": result.data,
                "error": result.error,
            })
            
            if not result.success:
                # Check if it's a condition that failed (which is OK, just stop)
                if current_step.operation == "condition":
                    print(f"  Condition not met, stopping workflow")
                    break
                # For real failures, log and continue to next step
                print(f"  Step failed: {result.error}")
            
            # Merge result data into context for next steps
            if result.data:
                context.update(result.data)
            
            # Find next step
            if current_step.next_step_id:
                current_step = next((s for s in workflow.steps if s.id == current_step.next_step_id), None)
            else:
                # Find the next step in the list after current
                idx = workflow.steps.index(current_step)
                current_step = workflow.steps[idx + 1] if idx + 1 < len(workflow.steps) else None
        
        all_success = all(r["success"] for r in results if r["operation"] != "condition")
        return {
            "success": all_success,
            "workflow_id": workflow.id,
            "steps_executed": len(results),
            "results": results,
            "context": context,
        }
    
    def activate_workflow(self, workflow_id: str) -> bool:
        """Activate a workflow so it starts listening for triggers."""
        wf = self.get_workflow(workflow_id)
        if wf:
            self.update_status(workflow_id, "active")
            self.active_workflows[workflow_id] = wf
            return True
        return False
    
    def pause_workflow(self, workflow_id: str) -> bool:
        self.update_status(workflow_id, "paused")
        if workflow_id in self.active_workflows:
            del self.active_workflows[workflow_id]
        return True


# Global engine instance
engine = RuntimeEngine(os.getenv("FLOWMIND_DB_PATH", "flowmind.db"))
