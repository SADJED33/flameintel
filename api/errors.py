"""Turn errors raised by chat.py into friendly JSON (never leak keys)."""
def describe(exc, scrub):
    name = type(exc).__name__
    msg = scrub(str(exc))
    if name == "QuotaError":
        wait = getattr(exc, "retry_after", None)
        daily = getattr(exc, "daily", False)
        friendly = ("The free language-model quota is used up for today. " if daily else
                    "The language model is rate-limited right now. ")
        friendly += (f"Try again in about {int(wait)} s." if wait else "Please try again later.")
        return 429, {"type": "quota", "message": friendly, "retry_after": wait, "daily": daily}
    if name == "StallError":
        return 504, {"type": "stall", "message": "The language model did not reply in time. It may be overloaded; please try again in a minute."}
    if "Every model failed" in msg:
        return 502, {"type": "all_models_failed", "message": "Every configured language model failed (rate-limited or stalled). Please try again later."}
    if "Put your key in the .env" in msg or "LLM_MODEL is required" in msg:
        return 500, {"type": "config", "message": "The server's language-model settings are incomplete. Check the .env file on the server."}
    return 500, {"type": "internal", "message": "Something went wrong while answering. " + msg[:200]}
