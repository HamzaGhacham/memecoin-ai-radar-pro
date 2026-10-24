"""Owner-only, opt-in informational Telegram reporting; no trading or financial signals."""
import os
from .transport import JsonTransport, SourceError


def notify_owner(text: str, *, transport=None) -> bool:
    token=os.getenv('TELEGRAM_BOT_TOKEN','')
    owner=os.getenv('TELEGRAM_OWNER_ID','')
    if not token or not owner or not owner.isdecimal():
        return False
    transport=transport or JsonTransport(timeout_seconds=10)
    try:
        response=transport.request('https://api.telegram.org/bot'+token+'/sendMessage',payload={
            'chat_id':owner,'text':text[:3500],'disable_web_page_preview':True})
        return isinstance(response,dict) and response.get('ok') is True
    except (SourceError, ValueError, TypeError):
        return False


def format_research_report(result: dict) -> str:
    if result.get('mode') not in ('demo','live'):
        return 'Radar: unavailable. No signals issued.'
    return (f"MemeCoin AI Radar Pro — {result['mode'].upper()} research scan\n"
            f"Unique tokens: {result['scanned']}\n"
            f"Preselected: {result['preselected']}\n"
            f"Inspected: {result['selected']}\n"
            f"Opportunity signals: 0 (strict security incomplete)\n"
            f"Safety status: HOLD / UNKNOWN\n"
            f"This is research data, not a buy recommendation.")
