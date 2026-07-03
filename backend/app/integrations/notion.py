"""
Notion Integration
Creates pages and queries databases via Notion API.
"""
import httpx
from typing import Dict, Any
from .base import BaseIntegration, ExecutionResult


class NotionIntegration(BaseIntegration):
    name = "notion"
    display_name = "Notion"
    BASE_URL = "https://api.notion.com/v1"
    
    def _get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.credentials.get('token', '')}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
    
    def test_connection(self) -> ExecutionResult:
        try:
            resp = httpx.get(f"{self.BASE_URL}/users/me", headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                return ExecutionResult(success=True, data={"connected": True})
            return ExecutionResult(success=False, error="Notion auth failed")
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def execute_action(self, operation: str, parameters: Dict, context: Dict) -> ExecutionResult:
        if operation == "page.create":
            return self._create_page(parameters, context)
        elif operation == "page.update":
            return self._update_page(parameters, context)
        elif operation == "database.query":
            return self._query_database(parameters, context)
        return ExecutionResult(success=False, error=f"Unknown operation: {operation}")
    
    def _create_page(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            database_id = params.get("database_id", "")
            # Build properties from context + params
            properties = params.get("properties", {})
            if not properties:
                # Auto-build from context
                title = context.get("customer_name", context.get("event_type", "New FlowMind Entry"))
                properties = {
                    "Name": {"title": [{"text": {"content": title}}]}
                }
                if context.get("customer_email"):
                    properties["Email"] = {"rich_text": [{"text": {"content": context["customer_email"]}}]}
                if context.get("amount"):
                    properties["Amount"] = {"rich_text": [{"text": {"content": str(context["amount"])}}]}
            
            payload = {"parent": {"database_id": database_id}, "properties": properties}
            resp = httpx.post(f"{self.BASE_URL}/pages", json=payload, headers=self._get_headers(), timeout=15)
            data = resp.json()
            if resp.status_code == 200:
                return ExecutionResult(success=True, data={"page_id": data.get("id", ""), "url": data.get("url", "")})
            return ExecutionResult(success=False, error=str(data))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _update_page(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            page_id = params.get("page_id", "")
            properties = params.get("properties", {})
            resp = httpx.patch(f"{self.BASE_URL}/pages/{page_id}", json={"properties": properties}, headers=self._get_headers(), timeout=15)
            if resp.status_code == 200:
                return ExecutionResult(success=True, data={"updated": True})
            return ExecutionResult(success=False, error="Update failed")
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _query_database(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            database_id = params.get("database_id", "")
            filter_query = params.get("filter", {})
            payload = {}
            if filter_query:
                payload["filter"] = filter_query
            resp = httpx.post(f"{self.BASE_URL}/databases/{database_id}/query", json=payload, headers=self._get_headers(), timeout=15)
            data = resp.json()
            if resp.status_code == 200:
                return ExecutionResult(success=True, data={"results": data.get("results", [])})
            return ExecutionResult(success=False, error=str(data))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
