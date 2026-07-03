"""
Google Sheets Integration
Appends and reads rows via Google Sheets API.
"""
import httpx
from typing import Dict, Any, List
from .base import BaseIntegration, ExecutionResult


class GoogleSheetsIntegration(BaseIntegration):
    name = "google_sheets"
    display_name = "Google Sheets"
    BASE_URL = "https://sheets.googleapis.com/v4/spreadsheets"
    
    def _get_access_token(self) -> str:
        """Get OAuth2 access token from service account or refresh token."""
        # For service accounts, you'd use JWT. For OAuth, use refresh token.
        creds_json = self.credentials.get("credentials", "")
        if creds_json:
            try:
                import json
                creds = json.loads(creds_json)
                # Simplified — in production use google-auth library
                resp = httpx.post("https://oauth2.googleapis.com/token", data={
                    "client_id": creds.get("client_id", ""),
                    "client_secret": creds.get("client_secret", ""),
                    "refresh_token": creds.get("refresh_token", ""),
                    "grant_type": "refresh_token",
                }, timeout=10)
                return resp.json().get("access_token", "")
            except:
                return ""
        return ""
    
    def _get_headers(self) -> Dict:
        return {"Authorization": f"Bearer {self._get_access_token()}", "Content-Type": "application/json"}
    
    def test_connection(self) -> ExecutionResult:
        token = self._get_access_token()
        if token:
            return ExecutionResult(success=True, data={"connected": True})
        return ExecutionResult(success=False, error="Google Sheets auth failed")
    
    def execute_action(self, operation: str, parameters: Dict, context: Dict) -> ExecutionResult:
        if operation == "row.append":
            return self._append_row(parameters, context)
        elif operation == "row.update":
            return self._update_row(parameters, context)
        elif operation == "row.read":
            return self._read_rows(parameters, context)
        return ExecutionResult(success=False, error=f"Unknown operation: {operation}")
    
    def _append_row(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            spreadsheet_id = params.get("spreadsheet_id", "")
            sheet_name = params.get("sheet_name", "Sheet1")
            values = params.get("values", [])
            if not values:
                # Auto-build from context
                values = [
                    context.get("customer_name", ""),
                    context.get("customer_email", ""),
                    context.get("customer_phone", ""),
                    str(context.get("amount", "")),
                    context.get("reference", ""),
                    context.get("event_type", ""),
                ]
            
            url = f"{self.BASE_URL}/{spreadsheet_id}/values/{sheet_name}!A:A:append?valueInputOption=RAW"
            resp = httpx.post(url, json={"values": [values]}, headers=self._get_headers(), timeout=15)
            data = resp.json()
            if resp.status_code == 200:
                return ExecutionResult(success=True, data={"updated_range": data.get("updates", {}).get("updatedRange", "")})
            return ExecutionResult(success=False, error=str(data))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _update_row(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            spreadsheet_id = params.get("spreadsheet_id", "")
            sheet_name = params.get("sheet_name", "Sheet1")
            row_number = params.get("row_number", 1)
            values = params.get("values", [])
            range_str = f"{sheet_name}!A{row_number}:Z{row_number}"
            url = f"{self.BASE_URL}/{spreadsheet_id}/values/{range_str}?valueInputOption=RAW"
            resp = httpx.put(url, json={"values": [values]}, headers=self._get_headers(), timeout=15)
            if resp.status_code == 200:
                return ExecutionResult(success=True, data={"updated": True})
            return ExecutionResult(success=False, error="Update failed")
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _read_rows(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            spreadsheet_id = params.get("spreadsheet_id", "")
            sheet_name = params.get("sheet_name", "Sheet1")
            range_str = params.get("range", f"{sheet_name}!A:Z")
            url = f"{self.BASE_URL}/{spreadsheet_id}/values/{range_str}"
            resp = httpx.get(url, headers=self._get_headers(), timeout=15)
            data = resp.json()
            if resp.status_code == 200:
                return ExecutionResult(success=True, data={"values": data.get("values", [])})
            return ExecutionResult(success=False, error=str(data))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
