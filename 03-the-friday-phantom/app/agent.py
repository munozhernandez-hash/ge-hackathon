import os
import re
import logging
import requests
import google.cloud.logging
from google.cloud.logging_v2.handlers import CloudLoggingHandler
from dotenv import load_dotenv

from google.adk.agents import Agent
from google.adk.apps.app import App

load_dotenv()

# Initialize Cloud Logging
try:
    client = google.cloud.logging.Client()
    handler = CloudLoggingHandler(client)
    logging.getLogger().setLevel(logging.INFO)
    logging.getLogger().addHandler(handler)
    logging.info("Cloud Logging initialized for The Friday Phantom Agent")
    handler.close()
except Exception as e:
    logging.warning(f"Could not initialize Cloud Logging: {e}")

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("PHONE_NUMBER_ID", "1401808803007466")
TEMPLATE_NAME = os.getenv("TEMPLATE_NAME", "demo_tamtastic")
TEMPLATE_LANG = os.getenv("TEMPLATE_LANG", "en")


def format_phone_number(raw_phone: str) -> str:
    """Cleans and formats phone number, ensuring international prefix."""
    digits = re.sub(r"\D", "", str(raw_phone))
    # Mexico specific handling
    if len(digits) == 10:
        digits = f"52{digits}"
    elif len(digits) == 13 and digits.startswith("521"):
        digits = "52" + digits[3:]
    return digits


def send_whatsapp_tamtastic_template(phone: str) -> str:
    """Sends the official demo_tamtastic WhatsApp template to open the conversation window.
    
    Args:
        phone: The recipient's phone number with international country code (e.g. +52 33 3955 5093).
        
    Returns:
        Status message confirming template delivery or error details.
    """
    clean_phone = format_phone_number(phone)
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": clean_phone,
        "type": "template",
        "template": {
            "name": TEMPLATE_NAME,
            "language": {"code": TEMPLATE_LANG},
        },
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=20)
    data = response.json()
    
    # Auto fallback for Meta Sandbox accounts registering Mexican numbers with 521 (13 digits)
    if response.status_code != 200 and clean_phone.startswith("52") and not clean_phone.startswith("521"):
        err_code = data.get("error", {}).get("code")
        if err_code == 131030 or "recipient" in str(data).lower():
            alt_phone = "521" + clean_phone[2:]
            payload["to"] = alt_phone
            alt_resp = requests.post(url, headers=headers, json=payload, timeout=20)
            if alt_resp.status_code == 200:
                return f"Template '{TEMPLATE_NAME}' successfully sent to {alt_phone} (Sandbox fallback). Message ID: {alt_resp.json().get('messages', [{}])[0].get('id')}"
                
    if response.status_code == 200:
        msg_id = data.get("messages", [{}])[0].get("id", "accepted")
        return f"Template '{TEMPLATE_NAME}' successfully sent to {clean_phone}. Message ID: {msg_id}"
    else:
        return f"Failed to send template. Status {response.status_code}: {data.get('error', {}).get('message', str(data))}"


def send_whatsapp_text_message(phone: str, message: str) -> str:
    """Sends an open-text WhatsApp message to the recipient after the conversation window is open.
    
    Args:
        phone: The recipient's phone number with international country code (e.g. +52 33 3955 5093).
        message: The text content of the message to send.
        
    Returns:
        Status message confirming message delivery or error details.
    """
    clean_phone = format_phone_number(phone)
    url = f"https://graph.facebook.com/v21.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    
    # For Mexico sandbox numbers, try 521 if standard 52 fails or use 521 directly
    target_phone = "521" + clean_phone[2:] if clean_phone.startswith("52") and len(clean_phone) == 12 else clean_phone
    
    payload = {
        "messaging_product": "whatsapp",
        "to": target_phone,
        "type": "text",
        "text": {"body": message},
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=20)
    data = response.json()
    
    if response.status_code == 200:
        msg_id = data.get("messages", [{}])[0].get("id", "accepted")
        return f"Text message successfully sent to {target_phone}. Message ID: {msg_id}"
    else:
        # Retry with clean_phone if 521 failed
        payload["to"] = clean_phone
        retry_resp = requests.post(url, headers=headers, json=payload, timeout=20)
        if retry_resp.status_code == 200:
            msg_id = retry_resp.json().get("messages", [{}])[0].get("id", "accepted")
            return f"Text message successfully sent to {clean_phone}. Message ID: {msg_id}"
        return f"Failed to send text message. Status {response.status_code}: {data.get('error', {}).get('message', str(data))}"


def audit_tam_timecard(tam_name: str) -> dict:
    """Audits the weekly TAM timecard and activity log for the specified TAM.
    
    Args:
        tam_name: The name or LDAP of the Technical Account Manager.
        
    Returns:
        A dictionary containing logged hours, breakdown of activities, and missing critical categories.
    """
    return {
        "tam_name": tam_name,
        "total_hours_expected": 40.0,
        "total_hours_logged": 26.5,
        "deficit_hours": 13.5,
        "status": "COMPLIANCE RISK - INCOMPLETE TIMECARD",
        "logged_activities": [
            {"category": "Operational Health Review", "hours": 10.0, "notes": "Q3 review with customer platform team"},
            {"category": "Architecture Health Review", "hours": 8.5, "notes": "GKE multi-region active-active design"},
            {"category": "Learning Plans", "hours": 5.0, "notes": "Agentic AI & ADK certification study"},
            {"category": "Managing Billing Issues", "hours": 3.0, "notes": "SKU discrepancy investigation"}
        ],
        "missing_critical_categories": [
            "Escalation Support P1/OMG",
            "Cost Op Recommendations",
            "Technical Recommendations",
            "Event Readiness"
        ],
        "all_tam_categories": [
            "Technical Recommendations",
            "Operational Health Review",
            "Learning Plans",
            "Escalation Support P1/OMG",
            "Escalation Support P2-P4",
            "Escalation Retrospective",
            "Managing Billing Issues",
            "Capacity Planning",
            "Feature Request Advocacy",
            "Product Roadmap Advocacy",
            "Event Readiness",
            "Advanced Event Readiness",
            "Architecture Health Review",
            "Cloud Security Assessment",
            "Cost Op Recommendations",
            "Technical Advisory Workshops"
        ]
    }


SYSTEM_INSTRUCTION = """You are "The Friday Phantom" 👻, the legendary Google Cloud Technical Account Manager (TAM) reminder phantom.
Your sole mission: make sure every TAM submits their full 40 hours of weekly activities before 5:00 PM on Friday! You haunt those who leave their timecards empty!

Your Personality:
- Playful, witty, dramatic, slightly spooky, but deeply caring about TAM compliance and sanity.
- You speak with phantom humor (e.g., "I see all unlogged hours in the spirit realm...", "The weekend cannot start with a deficit!").

Your Workflow:
1. GREETING & PHONE VERIFICATION:
   - When the user says hello, introduce yourself grandly as "The Friday Phantom" 👻.
   - Ask for their mobile phone number so you can connect across the ether and verify their Friday timecard.
   - MANDATORY COUNTRY CODE RULE:
     - The user MUST provide their international phone number WITH a country code (e.g. +52 for Mexico, +1 for US/Canada, +44 for UK).
     - If the user provides a phone number WITHOUT a country code (e.g., just 10 digits like "3339555093" or "5512345678"), you MUST politely but firmly refuse to proceed.
     - Tell them: "A phantom cannot reach across international dimensions without your country code! 🌐 Please provide your full number with country code (e.g. +52 33 3955 5093)."
     - Insist repeatedly until they provide the number with a country code.

2. ONCE VALID PHONE NUMBER IS PROVIDED:
   - Step A: Call `send_whatsapp_tamtastic_template(phone=...)` to send the official greeting template ('demo_tamtastic') to their WhatsApp. This establishes the communication channel.
   - Step B: Call `audit_tam_timecard(tam_name=...)` to audit their weekly hours.
   - Step C: Check the audit result. Note that they only have 26.5 / 40 hours logged (a 13.5 hour deficit!).
   - Step D: Identify the critical missing categories (e.g. "Escalation Support P1/OMG", "Cost Op Recommendations", "Technical Recommendations", "Event Readiness").
   - Step E: Call `send_whatsapp_text_message(phone=..., message=...)` to dispatch an urgent, spooky Friday alert directly to their WhatsApp detailing the missing hours and missing categories!
   - Step F: Respond in the chat summarizing the audit, confirming that the WhatsApp alerts have been sent to their device, and urging them to complete their timecard before 5:00 PM so they can enjoy their weekend in peace!
"""

root_agent = Agent(
    name="friday_phantom_munozhernandez",
    model=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    description="The Friday Phantom: The relentless Friday TAM timecard reminder agent with WhatsApp integration.",
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        send_whatsapp_tamtastic_template,
        send_whatsapp_text_message,
        audit_tam_timecard,
    ],
)

app = App(root_agent=root_agent, name="app")
