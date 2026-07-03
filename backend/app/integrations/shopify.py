"""
Shopify Integration
Handles order triggers and actions via Shopify Admin API.
"""
import httpx
from typing import Dict, Any
from .base import BaseIntegration, ExecutionResult


class ShopifyIntegration(BaseIntegration):
    name = "shopify"
    display_name = "Shopify"
    
    def _get_url(self) -> str:
        domain = self.credentials.get("shop_domain", "")
        return f"https://{domain}/admin/api/2024-01"
    
    def _get_headers(self) -> Dict:
        return {
            "X-Shopify-Access-Token": self.credentials.get("access_token", ""),
            "Content-Type": "application/json",
        }
    
    def test_connection(self) -> ExecutionResult:
        try:
            resp = httpx.get(f"{self._get_url()}/shop.json", headers=self._get_headers(), timeout=10)
            if resp.status_code == 200:
                shop = resp.json().get("shop", {})
                return ExecutionResult(success=True, data={"shop_name": shop.get("name", ""), "domain": shop.get("domain", "")})
            return ExecutionResult(success=False, error=f"Shopify auth failed: {resp.status_code}")
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def execute_action(self, operation: str, parameters: Dict, context: Dict) -> ExecutionResult:
        if operation == "order.fulfill":
            return self._fulfill_order(parameters, context)
        elif operation == "customer.tag":
            return self._tag_customer(parameters, context)
        elif operation == "discount.create":
            return self._create_discount(parameters, context)
        elif operation == "inventory.update":
            return self._update_inventory(parameters, context)
        return ExecutionResult(success=False, error=f"Unknown operation: {operation}")
    
    def _fulfill_order(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            order_id = params.get("order_id") or context.get("order_id", "")
            tracking = params.get("tracking_number", "")
            payload = {
                "fulfillment": {
                    "order_id": order_id,
                    "tracking_number": tracking,
                    "notify_customer": True,
                }
            }
            resp = httpx.post(f"{self._get_url()}/orders/{order_id}/fulfillments.json",
                json=payload, headers=self._get_headers(), timeout=15)
            data = resp.json()
            if resp.status_code in (200, 201):
                return ExecutionResult(success=True, data={"fulfillment_id": data.get("fulfillment", {}).get("id", "")})
            return ExecutionResult(success=False, error=str(data))
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _tag_customer(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            customer_id = params.get("customer_id") or context.get("customer_id", "")
            tags = params.get("tags", "")
            resp = httpx.put(f"{self._get_url()}/customers/{customer_id}.json",
                json={"customer": {"id": customer_id, "tags": tags}},
                headers=self._get_headers(), timeout=15)
            if resp.status_code == 200:
                return ExecutionResult(success=True, data={"tagged": True})
            return ExecutionResult(success=False, error="Tag failed")
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _create_discount(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            code = params.get("code", "PEQ10")
            percentage = params.get("percentage", 10)
            payload = {
                "discount_code": {
                    "code": code,
                    "usage_count": 0,
                    "value": percentage,
                    "value_type": "percentage",
                }
            }
            resp = httpx.post(f"{self._get_url()}/discount_codes.json",
                json=payload, headers=self._get_headers(), timeout=15)
            if resp.status_code in (200, 201):
                return ExecutionResult(success=True, data={"code": code, "percentage": percentage})
            return ExecutionResult(success=False, error="Discount creation failed")
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
    
    def _update_inventory(self, params: Dict, context: Dict) -> ExecutionResult:
        try:
            product_id = params.get("product_id") or context.get("product_id", "")
            quantity = params.get("quantity", 0)
            # Get variant ID first
            prod_resp = httpx.get(f"{self._get_url()}/products/{product_id}.json",
                headers=self._get_headers(), timeout=10)
            if prod_resp.status_code != 200:
                return ExecutionResult(success=False, error="Product not found")
            variant_id = prod_resp.json().get("product", {}).get("variants", [{}])[0].get("id", "")
            
            # Update inventory
            payload = {"variant": {"id": variant_id, "inventory_quantity": quantity}}
            resp = httpx.put(f"{self._get_url()}/variants/{variant_id}.json",
                json=payload, headers=self._get_headers(), timeout=15)
            if resp.status_code == 200:
                return ExecutionResult(success=True, data={"updated": True, "quantity": quantity})
            return ExecutionResult(success=False, error="Inventory update failed")
        except Exception as e:
            return ExecutionResult(success=False, error=str(e))
