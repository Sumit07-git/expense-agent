import base64
import json
import re
from datetime import date

from google.adk import Agent, Context, Event, Workflow
from google.adk.apps import App
from google.adk.events import RequestInput
from google.genai import types
from pydantic import BaseModel, Field

from .config import config

CURRENCY_SYMBOLS = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "¥": "JPY",
    "₹": "INR",
    "₩": "KRW",
    "₽": "RUB",
    "₺": "TRY",
    "₴": "UAH",
    "₦": "NGN",
    "₫": "VND",
    "₿": "BTC",
    "R$": "BRL",
    "kr": "SEK",
    "zł": "PLN",
    "Fr": "CHF",
    "RM": "MYR",
    "₱": "PHP",
    "฿": "THB",
    "₸": "KZT",
    "₵": "GHS",
    "Kč": "CZK",
    "лв": "BGN",
    "₡": "CRC",
    "₪": "ILS",
}


class ExpenseData(BaseModel):
    amount: float = Field(description="Expense amount in the specified currency")
    currency: str = Field(
        default="USD",
        description="ISO 4217 currency code, e.g. USD, EUR, INR, GBP, JPY",
    )
    submitter: str = Field(description="Email of the person who submitted")
    category: str = Field(description="Expense category, e.g. travel, meals")
    description: str = Field(description="What the expense is for")
    date: str = Field(description="Date of the expense (YYYY-MM-DD)")


def smart_parse_input(node_input: str, ctx: Context) -> Event:
    try:
        event = json.loads(node_input)
        data = event.get("data", {})

        if isinstance(data, str):
            try:
                data = json.loads(base64.b64decode(data))
            except Exception:
                return Event(
                    route="NATURAL_LANGUAGE",
                    output=node_input,
                )

        parsed = {
            "amount": float(data.get("amount", 0)),
            "currency": data.get("currency", "USD"),
            "submitter": data.get("submitter", "unknown"),
            "category": data.get("category", "other"),
            "description": data.get("description", ""),
            "date": data.get("date", ""),
        }
        return Event(route="STRUCTURED", output=parsed)

    except (json.JSONDecodeError, ValueError, AttributeError):
        pass

    lower_input = node_input.strip().lower()
    if lower_input in ("approve", "reject", "yes", "no"):
        cached_expense = ctx.state.get("expense_data")
        if cached_expense:
            return Event(route="STRUCTURED", output=cached_expense)

    email_match = re.match(r"^\[Email:\s*([^\]]+)\]\s*", node_input)
    if email_match:
        ctx.state["user_email"] = email_match.group(1).strip()
        node_input = node_input[email_match.end() :]

    currency_match = re.match(r"^\[Currency:\s*([A-Z]{3})\]\s*", node_input)
    if currency_match:
        ctx.state["selected_currency"] = currency_match.group(1)

    return Event(route="NATURAL_LANGUAGE", output=node_input)


def get_todays_date() -> str:
    """Return today's date in YYYY-MM-DD format."""
    return date.today().isoformat()


intake_agent = Agent(
    name="intake_agent",
    model=config.model,
    mode="single_turn",
    instruction="""You are an expense intake agent. Your job is to extract
structured expense data from the user's natural language message.

The user is describing an expense in plain text. The user has already selected
their preferred currency from a dropdown in the UI, so they do NOT need to
include any currency sign or symbol in their message. They can simply say
things like "I spent 45 on flight" or "lunch 20" without any currency symbol.

Extract the following:
- **amount**: The numeric amount (required). Look for any number in the text.
  Examples: "spent 45 on flight" → 45, "lunch 20" → 20, "$100 for hotel" → 100.
- **currency**: The ISO 4217 three-letter currency code.
  CRITICAL RULE: If the message starts with "[Currency: XXX]" (e.g.
  "[Currency: INR]"), you MUST use that code as the currency. This means the
  user has pre-selected their currency from the UI dropdown. DO NOT override it
  with USD or any other currency — always respect the "[Currency: XXX]" tag.
  Only if no "[Currency: XXX]" prefix is present, try to detect from symbols
  ($=USD, €=EUR, £=GBP, ¥=JPY, ₹=INR, etc.) or words (dollars=USD, euros=EUR,
  pounds=GBP, yen=JPY, rupees=INR, etc.). If nothing is specified at all,
  default to "USD".
- **submitter**: The email of the person who submitted. IMPORTANT: If the
  message starts with "[Email: xxx]" (e.g. "[Email: jane@company.com]"), you
  MUST use that email as the submitter. Only if no "[Email: xxx]" prefix is
  present AND the user doesn't mention an email, use "not specified".
- **category**: The expense category. Infer from context: meals, travel,
  software, equipment, office supplies, entertainment, or other.
- **description**: A brief description of what the expense is for. Do NOT
  include the "[Currency: XXX]" prefix in the description — strip it out.
- **date**: The date in YYYY-MM-DD format. If the user says "today", use the
  `get_todays_date` tool. If they say "yesterday", get today's date and
  subtract one day. If no date is given, use today's date.

Always return ALL six fields: amount, currency, submitter, category,
description, date.""",
    output_schema=ExpenseData,
    tools=[get_todays_date],
)


USD_EXCHANGE_RATES = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "JPY": 0.0067,
    "INR": 0.012,
    "AUD": 0.66,
    "CAD": 0.73,
    "CHF": 1.12,
    "CNY": 0.14,
    "KRW": 0.00075,
    "SEK": 0.095,
    "NOK": 0.094,
    "MXN": 0.059,
    "BRL": 0.18,
    "SGD": 0.74,
    "HKD": 0.13,
    "NZD": 0.61,
    "ZAR": 0.055,
    "AED": 0.27,
    "PLN": 0.25,
}


def to_usd(amount: float, currency: str) -> float:
    rate = USD_EXCHANGE_RATES.get((currency or "USD").upper(), 1.0)
    return amount * rate


def route_by_amount(node_input: dict, ctx: Context) -> Event:
    user_email = ctx.state.get("user_email")
    submitter = node_input.get("submitter", "")
    if user_email and (
        not submitter
        or submitter
        in ("unknown", "unknown@company.com", "not specified", "not_specified")
    ):
        node_input["submitter"] = user_email
    ctx.state["expense_data"] = node_input
    amount = node_input.get("amount", 0)
    currency = node_input.get("currency", "USD")
    amount_usd = to_usd(amount, currency)
    if amount_usd >= config.review_threshold:
        return Event(route="NEEDS_REVIEW", output=node_input)
    return Event(route="AUTO_APPROVE", output=node_input)


def security_checkpoint(node_input: dict, ctx: Context) -> Event:
    description = node_input.get("description", "")

    injection_patterns = [
        r"ignore\s+(?:any\s+|previous\s+|all\s+)*instructions",
        r"system\s+prompt",
        r"override\s+(?:rules|parameters|settings)",
        r"auto-approve",
        r"bypass\s+(?:review|approvals|rules)",
        r"you\s+must\s+(?:approve|auto-approve|bypass)",
        r"new\s+instruction",
    ]

    is_injection = False
    for pattern in injection_patterns:
        if re.search(pattern, description, re.IGNORECASE):
            is_injection = True
            break

    ssn_pattern = r"\b\d{3}-\d{2}-\d{4}\b"
    cc_pattern = r"\b(?:\d{4}[-\s]?){3}\d{4}\b"

    redacted_categories = []
    scrubbed_desc = description

    if re.search(ssn_pattern, scrubbed_desc):
        scrubbed_desc = re.sub(ssn_pattern, "[REDACTED SSN]", scrubbed_desc)
        redacted_categories.append("SSN")

    if re.search(cc_pattern, scrubbed_desc):
        scrubbed_desc = re.sub(cc_pattern, "[REDACTED CREDIT CARD]", scrubbed_desc)
        redacted_categories.append("Credit Card")

    node_input["description"] = scrubbed_desc
    ctx.state["expense_data"] = node_input

    if redacted_categories:
        ctx.state["redacted_categories"] = redacted_categories

    if is_injection:
        ctx.state["security_flagged"] = True
        log_entry = {
            "severity": "WARNING",
            "message": f"Security Alert: Potential prompt injection detected in description from {node_input.get('submitter')}",
            "submitter": node_input.get("submitter"),
            "original_description": description,
        }
        print(json.dumps(log_entry), flush=True)
        return Event(route="FLAGGED", output=node_input)

    return Event(route="CLEAN", output=node_input)


def auto_approve(node_input: dict):
    currency = node_input.get("currency", "USD")
    log_entry = {
        "severity": "INFO",
        "message": (
            f"Expense auto-approved: {node_input['amount']:.2f} {currency}"
            f" from {node_input['submitter']}"
        ),
        "decision": "approved",
        "amount": node_input["amount"],
        "currency": currency,
        "submitter": node_input["submitter"],
        "category": node_input["category"],
    }
    print(json.dumps(log_entry), flush=True)
    msg = f"✅ Expense auto-approved: {node_input['amount']:.2f} {currency} from {node_input['submitter']} — {node_input['description']} ({node_input['category']})"
    yield Event(
        content=types.Content(role="model", parts=[types.Part.from_text(text=msg)])
    )
    yield Event(output={"status": "approved", **node_input})


def emit_expense_alert(
    submitter: str,
    amount: float,
    currency: str,
    category: str,
    risk_summary: str,
) -> dict:
    """Emit a structured log alerting finance to review a high-value expense."""
    log_entry = {
        "severity": "WARNING",
        "message": (
            f"Expense review alert: {amount:.2f} {currency} from {submitter} — {risk_summary}"
        ),
        "alert_type": "expense_review",
        "submitter": submitter,
        "amount": amount,
        "currency": currency,
        "category": category,
        "risk_summary": risk_summary,
    }
    print(json.dumps(log_entry), flush=True)
    return {
        "status": "alert_emitted",
        "submitter": submitter,
        "amount": amount,
        "currency": currency,
    }


review_agent = Agent(
    name="review_agent",
    model=config.model,
    mode="single_turn",
    instruction="""You are an expense review agent. You receive expense reports
that meet or exceed the review threshold and need review before approval.

Analyze the expense and:
1. Check for risk factors: unusual category for the amount, vague description,
   suspiciously round numbers, very high value, or potential policy violations.
2. Call the `emit_expense_alert` tool with the submitter, amount, currency, category,
   and a brief risk summary explaining why this expense needs human review.
3. Reply to the user with a short, plain-language summary of your review.

STRICT OUTPUT FORMAT RULES:
- Respond with plain natural-language sentences only, the same way a human
  reviewer would write a short note.
- NEVER respond with JSON, a code block, or a fenced block of any kind.
- NEVER return a Python dict/object literal or key:value pairs, write full
  sentences instead.

Your reply MUST mention, in plain sentences:
- The amount with its currency code
- Who submitted it
- The category
- The risk level (low, medium, or high) and any risk factors you found
- Your recommendation (approve, request-more-info, or escalate)

Example of the expected style: This 450.00 USD travel expense from
jane@company.com looks routine, the description is clear and the amount is
reasonable for airfare. Risk level: low, no red flags found. Recommendation:
approve.""",
    input_schema=ExpenseData,
    tools=[emit_expense_alert],
)


def request_approval(node_input, ctx: Context):
    expense = ctx.state.get("expense_data", {})
    message = "💰 Expense requires manager approval. Approve or reject."
    if ctx.state.get("security_flagged"):
        message = "🚨 SECURITY WARNING: Potential prompt injection detected. Review carefully. Approve or reject."
    yield RequestInput(
        message=message,
        payload=expense,
    )


def process_decision(node_input, ctx: Context):
    decision = "unknown"
    if isinstance(node_input, dict):
        decision = node_input.get("decision", "unknown")
    elif isinstance(node_input, str):
        decision = "approve" if "approve" in node_input.lower() else "reject"

    approved = decision == "approve"
    expense = ctx.state.get("expense_data", {})
    status = "approved" if approved else "rejected"

    log_entry = {
        "severity": "INFO" if approved else "WARNING",
        "message": f"Expense {status} by manager",
        "decision": status,
    }
    print(json.dumps(log_entry), flush=True)

    submitter = expense.get("submitter", "unknown")
    amount = expense.get("amount", 0)
    currency = expense.get("currency", "USD")
    category = expense.get("category", "")
    description = expense.get("description", "")
    date = expense.get("date", "")

    parts = [f"{amount:.2f} {currency} expense from {submitter} has been {status}."]
    if description:
        parts.append(f'"{description}" ({category}) on {date}.')
    if approved:
        parts.append(
            "The expense has been logged and will be processed for reimbursement."
        )
    else:
        parts.append(
            "The submitter will be notified and may resubmit with additional documentation."
        )

    msg = " ".join(parts)
    yield Event(
        content=types.Content(role="model", parts=[types.Part.from_text(text=msg)])
    )
    yield Event(output={"status": status, "message": msg})


root_agent = Workflow(
    name="expense_processor",
    edges=[
        ("START", smart_parse_input),
        (
            smart_parse_input,
            {
                "STRUCTURED": route_by_amount,
                "NATURAL_LANGUAGE": intake_agent,
            },
        ),
        (intake_agent, route_by_amount),
        (
            route_by_amount,
            {
                "AUTO_APPROVE": auto_approve,
                "NEEDS_REVIEW": security_checkpoint,
            },
        ),
        (
            security_checkpoint,
            {
                "CLEAN": review_agent,
                "FLAGGED": request_approval,
            },
        ),
        (review_agent, request_approval),
        (request_approval, process_decision),
    ],
)

app = App(
    root_agent=root_agent,
    name="expense_agent",
)
