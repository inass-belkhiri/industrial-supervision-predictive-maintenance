# alerting.py
# Envoi direct d'alertes Telegram et Email depuis le backend.
# Remplace les workflows n8n (webhook → n8n → Telegram/Email).

import logging
import smtplib
from email.message import EmailMessage
from typing import List, Optional

import requests

import config

log = logging.getLogger(__name__)

TELEGRAM_API = f"https://api.telegram.org/bot{config.TELEGRAM_BOT_TOKEN}/sendMessage"


def send_telegram(chat_id: str, message: str) -> bool:
    try:
        resp = requests.post(
            TELEGRAM_API,
            json={
                "chat_id": chat_id,
                "text": message,
                "parse_mode": "Markdown",
            },
            timeout=10,
        )
        if resp.status_code != 200:
            log.warning("Telegram API error (%d): %s", resp.status_code, resp.text)
            return False
        return True
    except Exception as exc:
        log.warning("Telegram send failed: %s", exc)
        return False


def send_email(subject: str, body: str) -> bool:
    try:
        msg = EmailMessage()
        msg.set_content(body)
        msg["Subject"] = subject
        msg["From"] = config.EMAIL_FROM
        msg["To"] = config.EMAIL_TO

        with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(config.SMTP_USER, config.SMTP_PASSWORD)
            server.send_message(msg)
        return True
    except Exception as exc:
        log.warning("Email send failed: %s", exc)
        return False


def send_alert(
    severity: str,
    cause: Optional[str],
    confidence: Optional[float],
    actions: List[str],
    amdec_criticite: Optional[float],
    amdec_priorite: Optional[int],
    affected_molds: List[int],
) -> None:
    ts = __import__("datetime").datetime.now().strftime("%d/%m/%Y %H:%M")

    header = f"{'🔴 *ALERTE CRITIQUE*' if severity == 'CRITICAL' else '⚠️ *Alerte Température*'}"
    causes_text = cause or "Cause inconnue"

    message = (
        f"{header}\n\n"
        f"🕐 {ts}\n"
        f"🔸 Cause : {causes_text}\n"
        + (f"🔸 Confiance ML : {confidence:.0f}%\n" if confidence is not None else "")
        + (f"🔸 Priorité AMDEC : #{amdec_priorite}\n" if amdec_priorite else "")
        + (f"🔸 Moules affectés : {', '.join(str(m) for m in affected_molds)}\n" if affected_molds else "")
        + f"\n📋 Actions :\n"
    )  # fmt: skip
    for a in actions:
        message += f"  • {a}\n"

    if severity == "WARNING":
        send_telegram(config.TELEGRAM_OPERATORS_ID, message)
    elif severity == "CRITICAL":
        send_telegram(config.TELEGRAM_OPERATORS_ID, message)
        send_telegram(config.TELEGRAM_CHEF_ID, message)
        email_body = (
            f"Alerte Critique - Supervision Thermique\n\n"
            f"Cause : {causes_text}\n"
            + (f"Confiance ML : {confidence:.0f}%\n" if confidence is not None else "")
            + (f"Criticité AMDEC : {amdec_criticite}\n" if amdec_criticite else "")
            + (f"Priorité : #{amdec_priorite}\n" if amdec_priorite else "")
            + (f"Moules affectés : {', '.join(str(m) for m in affected_molds)}\n" if affected_molds else "")
            + f"\nActions :\n"
        )  # fmt: skip
        for a in actions:
            email_body += f"- {a}\n"
        send_email(f"🔴 ALERTE CRITIQUE - Supervision Thermique - {ts}", email_body)
