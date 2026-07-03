"""
FlowMind Automation Parser
Converts natural language descriptions into structured automation workflows.

User says: "When someone pays on Paystack, send them a WhatsApp receipt and add to Google Sheets"
Parser outputs: structured workflow with triggers, conditions, and actions.
"""
import json
import re
import uuid
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional
from enum import Enum


class StepType(Enum):
    TRIGGER = "trigger"
    CONDITION = "condition"
    ACTION = "action"
    DELAY = "delay"


class WorkflowStatus(Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


@dataclass
class WorkflowStep:
    id: str
    step_type: str
    integration: str
    operation: str
    name: str
    description: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    next_step_id: Optional[str] = None


@dataclass
class Workflow:
    id: str
    name: str
    description: str
    steps: List[WorkflowStep]
    status: str = "draft"
    created_by: str = ""
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "steps": [asdict(s) for s in self.steps],
            "tags": self.tags,
            "created_by": self.created_by,
        }


# Integration capability registry
INTEGRATION_CAPABILITIES: Dict[str, Dict] = {
    "paystack": {
        "triggers": [
            {"operation": "payment.received", "name": "Payment Received", "description": "When a customer pays via Paystack", "params": ["amount_min", "amount_max", "currency"]},
            {"operation": "payment.failed", "name": "Payment Failed", "description": "When a payment attempt fails", "params": []},
            {"operation": "refund.processed", "name": "Refund Processed", "description": "When a refund is completed", "params": []},
            {"operation": "subscription.activated", "name": "Subscription Activated", "description": "When a customer starts a subscription", "params": ["plan"]},
            {"operation": "subscription.cancelled", "name": "Subscription Cancelled", "description": "When a customer cancels", "params": []},
        ],
        "actions": [
            {"operation": "charge.customer", "name": "Charge Customer", "description": "Charge a customer's saved card", "params": ["email", "amount", "currency"]},
            {"operation": "refund.create", "name": "Create Refund", "description": "Refund a transaction", "params": ["transaction_id", "amount"]},
            {"operation": "subscriber.list", "name": "List Subscribers", "description": "Get all subscribers", "params": ["plan"]},
            {"operation": "plan.create", "name": "Create Plan", "description": "Create a subscription plan", "params": ["name", "amount", "interval"]},
        ],
    },
    "whatsapp": {
        "triggers": [
            {"operation": "message.received", "name": "Message Received", "description": "When a WhatsApp message is received", "params": ["from_number", "keyword"]},
            {"operation": "order.received", "name": "Order Received", "description": "When a WhatsApp order comes in", "params": []},
        ],
        "actions": [
            {"operation": "message.send", "name": "Send Message", "description": "Send a WhatsApp message to a number", "params": ["to", "message", "template"]},
            {"operation": "message.send_template", "name": "Send Template Message", "description": "Send a pre-approved template message", "params": ["to", "template_name", "variables"]},
            {"operation": "image.send", "name": "Send Image", "description": "Send an image via WhatsApp", "params": ["to", "image_url", "caption"]},
            {"operation": "document.send", "name": "Send Document", "description": "Send a PDF/document via WhatsApp", "params": ["to", "document_url", "filename"]},
        ],
    },
    "gmail": {
        "triggers": [
            {"operation": "email.received", "name": "Email Received", "description": "When an email arrives in inbox", "params": ["from", "subject_contains", "has_attachment"]},
        ],
        "actions": [
            {"operation": "email.send", "name": "Send Email", "description": "Send an email to someone", "params": ["to", "subject", "body", "attachments"]},
            {"operation": "email.reply", "name": "Reply to Email", "description": "Reply to a specific email thread", "params": ["thread_id", "body"]},
            {"operation": "label.add", "name": "Add Label", "description": "Add a Gmail label to an email", "params": ["email_id", "label"]},
            {"operation": "draft.create", "name": "Create Draft", "description": "Create a draft email for review", "params": ["to", "subject", "body"]},
        ],
    },
    "google_sheets": {
        "triggers": [
            {"operation": "row.added", "name": "Row Added", "description": "When a new row is added to a sheet", "params": ["spreadsheet_id", "sheet_name"]},
            {"operation": "row.updated", "name": "Row Updated", "description": "When a row is updated", "params": ["spreadsheet_id", "sheet_name", "column"]},
        ],
        "actions": [
            {"operation": "row.append", "name": "Add Row", "description": "Add a new row with data", "params": ["spreadsheet_id", "sheet_name", "values"]},
            {"operation": "row.update", "name": "Update Row", "description": "Update an existing row", "params": ["spreadsheet_id", "sheet_name", "row_number", "values"]},
            {"operation": "row.read", "name": "Read Rows", "description": "Read data from a sheet", "params": ["spreadsheet_id", "sheet_name", "range"]},
            {"operation": "sheet.create", "name": "Create Sheet", "description": "Create a new spreadsheet", "params": ["title"]},
        ],
    },
    "slack": {
        "triggers": [
            {"operation": "message.received", "name": "Message in Channel", "description": "When a message is posted in a channel", "params": ["channel", "keyword"]},
            {"operation": "mention.received", "name": "Bot Mentioned", "description": "When the bot is @mentioned", "params": ["channel"]},
        ],
        "actions": [
            {"operation": "message.send", "name": "Send Message", "description": "Post a message to a channel", "params": ["channel", "message"]},
            {"operation": "dm.send", "name": "Send DM", "description": "Send a direct message to a user", "params": ["user", "message"]},
            {"operation": "channel.create", "name": "Create Channel", "description": "Create a new Slack channel", "params": ["name"]},
        ],
    },
    "notion": {
        "triggers": [
            {"operation": "page.created", "name": "Page Created", "description": "When a new page is created in a database", "params": ["database_id"]},
        ],
        "actions": [
            {"operation": "page.create", "name": "Create Page", "description": "Create a new page in a database", "params": ["database_id", "properties"]},
            {"operation": "page.update", "name": "Update Page", "description": "Update an existing page", "params": ["page_id", "properties"]},
            {"operation": "database.query", "name": "Query Database", "description": "Search pages in a database", "params": ["database_id", "filter"]},
        ],
    },
    "telegram": {
        "triggers": [
            {"operation": "message.received", "name": "Message Received", "description": "When a Telegram message is received", "params": ["from_user", "keyword"]},
            {"operation": "command.received", "name": "Command Received", "description": "When a bot command is used", "params": ["command"]},
        ],
        "actions": [
            {"operation": "message.send", "name": "Send Message", "description": "Send a Telegram message", "params": ["chat_id", "message"]},
            {"operation": "photo.send", "name": "Send Photo", "description": "Send a photo", "params": ["chat_id", "photo_url", "caption"]},
            {"operation": "document.send", "name": "Send Document", "description": "Send a file", "params": ["chat_id", "document_url"]},
        ],
    },
    "shopify": {
        "triggers": [
            {"operation": "order.created", "name": "Order Created", "description": "When a new order is placed", "params": ["amount_min"]},
            {"operation": "order.paid", "name": "Order Paid", "description": "When an order is paid", "params": []},
            {"operation": "order.fulfilled", "name": "Order Fulfilled", "description": "When an order is shipped", "params": []},
            {"operation": "customer.created", "name": "New Customer", "description": "When a new customer signs up", "params": []},
        ],
        "actions": [
            {"operation": "order.fulfill", "name": "Fulfill Order", "description": "Mark an order as fulfilled", "params": ["order_id", "tracking_number"]},
            {"operation": "customer.tag", "name": "Tag Customer", "description": "Add tags to a customer", "params": ["customer_id", "tags"]},
            {"operation": "discount.create", "name": "Create Discount", "description": "Create a discount code", "params": ["code", "percentage"]},
            {"operation": "inventory.update", "name": "Update Inventory", "description": "Update product stock levels", "params": ["product_id", "quantity"]},
        ],
    },
    "internal": {
        "actions": [
            {"operation": "delay", "name": "Wait/Delay", "description": "Wait for a specified duration", "params": ["duration", "unit"]},
            {"operation": "condition", "name": "Condition Check", "description": "Check a condition and branch", "params": ["field", "operator", "value"]},
            {"operation": "http.request", "name": "HTTP Request", "description": "Make a custom HTTP request to any API", "params": ["method", "url", "headers", "body"]},
            {"operation": "ai.generate", "name": "AI Generate", "description": "Generate text using AI", "params": ["prompt", "model"]},
            {"operation": "data.transform", "name": "Transform Data", "description": "Transform data between steps", "params": ["source_field", "transform"]},
            {"operation": "notify.user", "name": "Notify User", "description": "Send a push notification to the user", "params": ["title", "message"]},
        ],
    },
}

# Keyword mappings for NL detection
INTEGRATION_KEYWORDS = {
    "paystack": ["paystack", "payment", "paid", "charge", "subscription", "pay "],
    "whatsapp": ["whatsapp", "wa ", "chat", "message someone", "text them"],
    "gmail": ["gmail", "email", "mail", "inbox"],
    "google_sheets": ["google sheet", "spreadsheet", "google sheets", "sheet"],
    "slack": ["slack", "channel", "team chat"],
    "notion": ["notion", "page", "database", "task", "project"],
    "telegram": ["telegram", "tg "],
    "shopify": ["shopify", "store", "order", "product"],
}

OPERATION_KEYWORDS = {
    "paystack": {
        "payment.received": ["pays", "payment received", "payment successful", "someone pays", "customer pays", "payment comes in", "pays on paystack", "pays via paystack"],
        "payment.failed": ["payment fails", "payment failed", "declined"],
        "subscription.activated": ["subscribes", "starts subscription", "signs up for plan"],
        "subscription.cancelled": ["cancels", "unsubscribes", "cancels subscription"],
        "charge.customer": ["charge", "charge customer", "bill customer"],
        "refund.create": ["refund", "return money"],
    },
    "whatsapp": {
        "message.send": ["send whatsapp", "send message", "whatsapp receipt", "whatsapp message", "notify on whatsapp", "send them a message", "whatsapp follow", "follow-up", "follow up"],
        "message.send_template": ["send template", "template message"],
        "image.send": ["send image", "send picture", "send photo"],
        "document.send": ["send document", "send pdf", "send receipt", "send invoice"],
        "message.received": ["receives whatsapp", "whatsapp message received", "someone messages", "message received"],
    },
    "gmail": {
        "email.send": ["send email", "email them", "send an email", "email receipt", "notify by email", "email notification"],
        "email.received": ["email received", "get email", "email arrives", "new email", "get an email", "email from"],
        "email.reply": ["reply to email", "respond to email"],
    },
    "google_sheets": {
        "row.append": ["add to sheet", "add to google sheet", "log in spreadsheet", "add row", "record in sheet", "add to spreadsheet", "add them to"],
        "row.read": ["read sheet", "get from sheet", "lookup in sheet"],
        "row.updated": ["row updated", "sheet updated"],
        "row.added": ["row added", "new row", "sheet entry"],
    },
    "slack": {
        "message.send": ["send slack", "notify slack", "slack message", "post to channel", "send to team", "notify team", "slack notification", "notification to my team"],
        "dm.send": ["dm someone", "direct message", "slack dm"],
        "message.received": ["slack message received", "message in channel"],
    },
    "notion": {
        "page.create": ["create notion page", "add to notion", "create task", "add task", "create project", "notion page", "task in notion"],
        "page.update": ["update notion", "update page"],
        "database.query": ["search notion", "query notion"],
    },
    "telegram": {
        "message.send": ["send telegram", "telegram message", "notify on telegram"],
        "message.received": ["telegram message received", "telegram message"],
    },
    "shopify": {
        "order.created": ["new order", "order placed", "order created", "customer orders", "order comes in"],
        "order.paid": ["order paid", "payment for order"],
        "order.fulfilled": ["order fulfilled", "order shipped"],
        "customer.created": ["new customer", "customer signs up"],
        "order.fulfill": ["fulfill order", "ship order", "mark as shipped"],
    },
}

DELAY_PATTERNS = [
    (r"(\d+)\s*(minute|min|minutes)", "minutes"),
    (r"(\d+)\s*(hour|hr|hours)", "hours"),
    (r"(\d+)\s*(day|days)", "days"),
    (r"(\d+)\s*(week|weeks)", "weeks"),
    (r"(\d+)\s*(month|months)", "months"),
]

# Action verbs that indicate a new step in the workflow
ACTION_VERBS = [
    "send", "add", "create", "notify", "email", "post", "update",
    "wait", "log", "trigger", "charge", "refund", "message", "reply",
    "schedule", "call", "make", "generate", "check", "alert", "dm",
    "text", "record", "save", "store", "forward", "if", "when"
]

TRIGGER_STARTERS = ["when", "if", "after", "once", "whenever", "every time", "on "]


def detect_integration(text: str) -> Optional[str]:
    text_lower = text.lower()
    for integration, keywords in INTEGRATION_KEYWORDS.items():
        for kw in keywords:
            if kw in text_lower:
                return integration
    return None


def detect_operation(integration: str, text: str) -> Optional[str]:
    text_lower = text.lower()
    if integration in OPERATION_KEYWORDS:
        for op, keywords in OPERATION_KEYWORDS[integration].items():
            for kw in keywords:
                if kw in text_lower:
                    return op
    return None


def detect_delay(text: str) -> Optional[Dict]:
    text_lower = text.lower()
    if "wait" not in text_lower and "later" not in text_lower and "after" not in text_lower and "delay" not in text_lower:
        return None
    for pattern, unit in DELAY_PATTERNS:
        match = re.search(pattern, text_lower)
        if match:
            return {"duration": int(match.group(1)), "unit": unit}
    if "later" in text_lower or ("after" in text_lower and not any(kw in text_lower for kw in ["pays", "payment", "email", "order", "message"])):
        return {"duration": 1, "unit": "days"}
    return None


def extract_parameters(text: str, operation: str, integration: str) -> Dict[str, Any]:
    params = {}
    text_lower = text.lower()
    
    if operation in ("email.send", "email.reply"):
        email_match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
        if email_match:
            params["to"] = email_match.group(0)
    
    if operation in ("message.send", "message.send_template", "image.send", "document.send"):
        phone_match = re.search(r'\+?\d{10,15}', text)
        if phone_match:
            params["to"] = phone_match.group(0)
    
    if operation == "message.send":
        if "receipt" in text_lower:
            params["template"] = "receipt"
        elif "follow" in text_lower:
            params["template"] = "follow_up"
    
    if operation == "message.send" and integration == "slack":
        channel_match = re.search(r'#([\w-]+)', text)
        if channel_match:
            params["channel"] = channel_match.group(1)
        else:
            params["channel"] = "general"
    
    if "amount" in text_lower or "naira" in text_lower or "dollar" in text_lower:
        amount_match = re.search(r'[\$₦]?\s*(\d+(?:,\d{3})*(?:\.\d{2})?)', text)
        if amount_match:
            params["amount"] = amount_match.group(1).replace(",", "")
    
    return params


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into logical workflow steps.
    Handles: commas, 'and', 'then', semicolons, periods before action verbs.
    """
    text = text.strip()
    if not text:
        return []
    
    # Build a regex that splits before action verbs
    # We want to split at: ", send", " and add", " then create", "; notify", ". wait"
    action_pattern = '|'.join(ACTION_VERBS)
    
    # Pattern: (comma|and|then|semicolon|period) + optional spaces + action verb
    split_re = re.compile(
        r'(?:,\s*|\s+and\s+|\s+then\s+|;\s*|\.\s+)'
        r'(?=(' + action_pattern + r')\b)',
        re.IGNORECASE
    )
    
    # Find all split points
    split_positions = []
    for m in split_re.finditer(text):
        # The split position is at the start of the lookahead (the action verb)
        split_pos = m.start()
        # Back up past any comma/space/period/semicolon
        while split_pos > 0 and text[split_pos - 1] in ',;. ':
            split_pos -= 1
        split_positions.append(split_pos)
    
    if not split_positions:
        return [text]
    
    # Build segments
    segments = []
    last_start = 0
    for pos in split_positions:
        if pos > last_start:
            segments.append(text[last_start:pos].strip())
        last_start = pos
        # Skip leading separators
        while last_start < len(text) and text[last_start] in ',;. ':
            last_start += 1
    
    if last_start < len(text):
        segments.append(text[last_start:].strip())
    
    return [s for s in segments if s]


def generate_workflow_id() -> str:
    return f"wf_{uuid.uuid4().hex[:12]}"


def generate_step_id() -> str:
    return f"step_{uuid.uuid4().hex[:8]}"


def parse_natural_language(description: str, user_id: str = "") -> Workflow:
    """
    Main entry point: parse a natural language description into a Workflow.
    """
    description = description.strip()
    words = description.split()
    name = " ".join(words[:6]) + ("..." if len(words) > 6 else "")
    
    segments = split_into_sentences(description)
    if not segments:
        segments = [description]
    
    steps = []
    prev_step_id = None
    
    for i, segment in enumerate(segments):
        segment_lower = segment.lower()
        
        # Is this a trigger?
        is_trigger = i == 0 and any(segment_lower.startswith(kw) or segment_lower.startswith("when ") or segment_lower.startswith("if ") or segment_lower.startswith("after ") or segment_lower.startswith("once ") for kw in TRIGGER_STARTERS)
        
        # Check for delay
        delay = detect_delay(segment)
        if delay and ("wait" in segment_lower or ("after" in segment_lower and i > 0)):
            step_id = generate_step_id()
            step = WorkflowStep(
                id=step_id,
                step_type="delay",
                integration="internal",
                operation="delay",
                name=f"Wait {delay['duration']} {delay['unit']}",
                description=segment,
                parameters=delay,
            )
            if prev_step_id:
                for s in steps:
                    if s.id == prev_step_id:
                        s.next_step_id = step_id
                        break
            steps.append(step)
            prev_step_id = step_id
            continue
        
        # Detect integration
        integration = detect_integration(segment)
        if not integration:
            if "notify" in segment_lower or "alert" in segment_lower:
                integration = "internal"
            elif "http" in segment_lower or "api" in segment_lower or "webhook" in segment_lower:
                integration = "internal"
            elif "wait" in segment_lower:
                integration = "internal"
            else:
                integration = "internal"
        
        # Detect operation
        operation = detect_operation(integration, segment)
        if not operation:
            if is_trigger:
                if integration == "paystack":
                    operation = "payment.received"
                elif integration == "gmail":
                    operation = "email.received"
                elif integration == "whatsapp":
                    operation = "message.received"
                elif integration == "shopify":
                    operation = "order.created"
                elif integration == "slack":
                    operation = "message.received"
                elif integration == "telegram":
                    operation = "message.received"
                elif integration == "notion":
                    operation = "page.created"
                elif integration == "google_sheets":
                    operation = "row.added"
                else:
                    operation = "event.received"
            elif integration == "internal":
                if "notify" in segment_lower or "alert" in segment_lower:
                    operation = "notify.user"
                elif "http" in segment_lower or "api" in segment_lower:
                    operation = "http.request"
                elif "generate" in segment_lower or "ai" in segment_lower:
                    operation = "ai.generate"
                else:
                    operation = "data.transform"
            else:
                # Default to most common action for this integration
                cap = INTEGRATION_CAPABILITIES.get(integration, {})
                actions = cap.get("actions", [])
                if actions:
                    operation = actions[0]["operation"]
                else:
                    operation = "action.execute"
        
        # Extract parameters
        params = extract_parameters(segment, operation, integration)
        
        # Determine step type
        step_type = "trigger" if is_trigger else "action"
        
        # Get operation display name
        op_name = operation
        cap_info = INTEGRATION_CAPABILITIES.get(integration, {})
        op_list = cap_info.get("triggers" if is_trigger else "actions", [])
        for op in op_list:
            if op["operation"] == operation:
                op_name = op["name"]
                break
        
        step_id = generate_step_id()
        step = WorkflowStep(
            id=step_id,
            step_type=step_type,
            integration=integration,
            operation=operation,
            name=op_name,
            description=segment,
            parameters=params,
        )
        
        if prev_step_id:
            for s in steps:
                if s.id == prev_step_id:
                    s.next_step_id = step_id
                    break
        
        steps.append(step)
        prev_step_id = step_id
    
    # Ensure at least one trigger
    if not any(s.step_type == "trigger" for s in steps) and steps:
        steps[0].step_type = "trigger"
    
    workflow = Workflow(
        id=generate_workflow_id(),
        name=name,
        description=description,
        steps=steps,
        status="draft",
        created_by=user_id,
    )
    
    return workflow


def get_all_capabilities() -> Dict:
    return INTEGRATION_CAPABILITIES


def validate_workflow(workflow: Workflow) -> Dict[str, Any]:
    issues = []
    if not workflow.steps:
        issues.append("Workflow has no steps")
        return {"valid": False, "issues": issues}
    triggers = [s for s in workflow.steps if s.step_type == "trigger"]
    if not triggers:
        issues.append("Workflow needs at least one trigger")
    actions = [s for s in workflow.steps if s.step_type == "action"]
    if not actions:
        issues.append("Workflow needs at least one action")
    for step in workflow.steps:
        if step.integration != "internal":
            if step.integration not in INTEGRATION_CAPABILITIES:
                issues.append(f"Unknown integration: {step.integration}")
    return {"valid": len(issues) == 0, "issues": issues}
