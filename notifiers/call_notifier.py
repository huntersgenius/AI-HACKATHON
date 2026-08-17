"""SmartCall (callmaster.uz) voice-call channel.

Thin wrapper around https://smartcall.uz/web/api/v1 — create a call, check
its status, cancel a queued one. Nothing here decides *when* to call; that
lives in `services/call_service.py` and `hooks/call_hooks.py`. Like every
other network-dependent piece in this codebase (see llm_analyzer.py), a
missing key, a timeout or a bad response never raises — callers get back a
plain dict with `ok: False` and act on that.
"""

import requests

from config import Config
from notifiers.base import register

ERROR_MESSAGES_UZ = {
    "invalid_api_key": "SmartCall API kaliti notoʻgʻri yoki muddati oʻtgan.",
    "invalid_group": "SmartCall guruh ID topilmadi.",
    "no_shared_number": "Ulashilgan faol raqam topilmadi.",
    "invalid_phone": "Telefon raqam formati notoʻgʻri.",
    "duplicate_call": "Bu raqamga yaqinda qoʻngʻiroq qilingan. Biroz kuting.",
    "limit_exceeded": "Qoʻngʻiroq limiti tugagan.",
    "call_not_found": "Qoʻngʻiroq topilmadi.",
    "rate_limit_exceeded": "Soʻrovlar limiti oshib ketdi.",
    "method_not_allowed": "Notoʻgʻri soʻrov usuli.",
    "not_configured": "SmartCall sozlanmagan (API kalit yoki guruh ID yoʻq).",
    "network_error": "SmartCall bilan aloqa yoʻq.",
}


def message_for(error_code):
    return ERROR_MESSAGES_UZ.get(error_code, "Qoʻngʻiroqda xatolik yuz berdi.")


def _configured():
    return bool(Config.SMARTCALL_API_KEY and Config.SMARTCALL_GROUP_ID)


def _post(payload):
    """POST to the single SmartCall endpoint; normalise every outcome."""
    if not Config.SMARTCALL_API_KEY:
        return {"ok": False, "error_code": "not_configured"}

    body = {"apiKey": Config.SMARTCALL_API_KEY}
    body.update(payload)

    try:
        response = requests.post(
            Config.SMARTCALL_API_URL,
            data=body,
            timeout=Config.SMARTCALL_TIMEOUT_SECONDS,
        )
        data = response.json()
    except (requests.RequestException, ValueError):
        return {"ok": False, "error_code": "network_error"}

    if data.get("status") == "success" or "call_id" in data:
        return {"ok": True, "raw": data}
    if "deleteStatus" in data:
        return {"ok": data.get("deleteStatus") is True, "raw": data}
    if data.get("status") in ("pending", "sended"):
        return {"ok": True, "raw": data}

    error_code = data.get("error") or data.get("message") or "unknown_error"
    return {"ok": False, "error_code": error_code, "raw": data}


def place_call(phone, verify_code=None, random_number=None):
    """Queue a new call. `phone` must be in the seller's expected format."""
    if not _configured():
        return {"ok": False, "error_code": "not_configured"}

    payload = {"groupID": Config.SMARTCALL_GROUP_ID, "phone": phone}
    if verify_code:
        payload["verifyCode"] = verify_code
    if random_number:
        payload["randomNumber"] = 1

    result = _post(payload)
    if result["ok"]:
        result["call_id"] = result["raw"].get("call_id")
    return result


def check_status(external_call_id):
    return _post({"call_id": external_call_id})


def cancel_call(external_call_id):
    return _post({"call_id": external_call_id, "del": 1})


class CallNotifier:
    key = "call"

    def send(self, to, title, body):
        return place_call(to)


register(CallNotifier())
