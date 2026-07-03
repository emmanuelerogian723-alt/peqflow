"""
Paystack Integration
Handles payment triggers and actions via Paystack API.
"""
import httpx
from typing import Dict, Any
from .base import BaseIntegration, ExecutionResult


class PaystackIntegration(BaseIntegration):
    name = "paystack"
    display_name = "Paystack"
    BASE_URL = "https://api.paystack.co"
    
    def _get_headers(self) -> Dict:
        return {
            "Authorization": f"Bearer {self.credentials.get('secret_key', '')}",
            "Content-Type": "application/json",
        }
    
    def test_connection(self) -> ExecutionResult:
        try:
            resp = httpx.get(f"{self.BASE_URL}/transaction", headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                return ExecutionResult(success=True, data={"connected": True})
            return ExecutionResult(success=False, error=f"Paystack auth failed: {resp.status_code}")
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def execute_action(self, operation: str, parameters: Dict, context: Dict) -> ExecutionResult:
        if operation == "charge.customer":
            return self._charge_customer(parameters, context)
        elif operation == "refund.create":
            return self._create_refund(parameters, context)
        elif operation == "subscriber.list":
            return self._list_subscribers(parameters, context)
        elif operation == "plan.create":
            return self._create_plan(parameters, context)
        return ExecutionResult(success=False, error=f"Unknown operation: {operation}")
    
    def _charge_customer(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            email = params.get("to") or context.get("customer_email", "")
            amount = int(float(params.get("amount", 0)) * 100)  # Convert to kobo
            payload = {"email": email, "amount": amount, "currency": params.get("currency", "NGN")}
            resp = httpx.post(f"{self.BASE_URL}/transaction/initialize", json=payload, headers=self._get_headers(), timeout=15)
            data = resp.json()
            if resp.status_code == 200 and data.get("status"):
                return ExecutionResult(success=True, data=data.get("data", {}))
            return ExecutionResult(success=False, error=data.get("message", "Charge failed"))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _create_refund(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            tx_id = params.get("transaction_id") or context.get("transaction_id", "")
            payload = {"transaction": tx_id}
            if params.get("amount"):
                payload["amount"] = int(float(params["amount"]) * 100)
            resp = httpx.post(f"{self.BASE_URL}/refund", json=payload, headers=self._get_headers(), timeout=15)
            data = resp.json()
            if resp.status_code == 200:
                return ExecutionResult(success=True, data=data.get("data", {}))
            return ExecutionResult(success=False, error=data.get("message", "Refund failed"))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _list_subscribers(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            url = f"{self.BASE_URL}/subscription"
            if params.get("plan"):
                url += f"?plan={params['plan']}"
            resp = httpx.get(url, headers=self._get_headers(), timeout=15)
            data = resp.json()
            if resp.status_code == 200:
                return ExecutionResult(success=True, data=data.get("data", []))
            return ExecutionResult(success=False, error=data.get("message", "List failed"))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _create_plan(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            payload = {
                "name": params.get("name", "Custom Plan"),
                "amount": int(float(params.get("amount", 0)) * 100),
                "interval": params.get("interval", "monthly"),
            }
            resp = httpx.post(f"{self.BASE_URL}/plan", json=payload, headers=self._get_headers(), timeout=15)
            data = resp.json()
            if resp.status_code == 200:
                return ExecutionResult(success=True, data=data.get("data", {}))
            return ExecutionResult(success=False, error=data.get("message", "Plan creation failed"))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
