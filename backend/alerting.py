# alerting.py
# Envoi direct d'alertes Telegram et Email depuis le backend.
# Remplace les workflows n8n (webhook → n8n → Telegram/Email).

import logging
import smtplib
from email.message import EmailMessage
from typing import List

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


STATUS_LABELS = {'OK': 'OK', 'ALERTE': 'ALERTE', 'CRITIQUE': 'CRITIQUE', 'ERREUR': 'ERREUR'}
POSITION_LABELS = {1: 'Gauche', 2: 'Centre', 3: 'Droite'}


def _format_mold_line(m: dict) -> str:
    mid = m.get('mold_id', '?')
    pos = POSITION_LABELS.get(mid, '?')
    temp = m.get('temperature')
    temp_str = f"{temp:.1f} °C" if temp is not None else "-- °C"
    status = m.get('status', 'ERREUR')
    return f"   Moule {mid} ({pos}) : {temp_str} [{status}]"


def send_alert(
    severity: str,
    affected_molds: List[int],
    mold_readings: List[dict],
) -> None:
    ts = __import__("datetime").datetime.now().strftime("%d/%m/%Y %H:%M")

    header = f"{'🔴 *ALERTE CRITIQUE*' if severity == 'CRITICAL' else '⚠️ *Alerte Température*'}"
    molds_str = ', '.join(str(m) for m in affected_molds) if affected_molds else '-'

    temps_lines = '\n'.join(_format_mold_line(m) for m in mold_readings)

    message = (
        f"{header}\n\n"
        f"🕐 {ts}\n"
        f"🔸 Moules affectés : {molds_str}\n"
        + (f"\n🔸 Températures :\n{temps_lines}" if temps_lines else "")
    )

    if severity == "WARNING":
        send_telegram(config.TELEGRAM_OPERATORS_ID, message)
    elif severity == "CRITICAL":
        send_telegram(config.TELEGRAM_OPERATORS_ID, message)
        send_telegram(config.TELEGRAM_CHEF_ID, message)
        email_body = (
            f"Alerte Critique - Supervision Thermique\n\n"
            f"Date : {ts}\n"
            f"Moules affectés : {molds_str}\n"
            + (f"\nTempératures :\n{temps_lines}" if temps_lines else "")
        )
        send_email(f"ALERTE - Supervision Thermique - {ts}", email_body)
