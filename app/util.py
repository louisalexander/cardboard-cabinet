import time

def bucketize_minutes(minutes: int) -> str:
    if minutes is None:
        return "Unknown"
    if minutes <= 30: return "≤30 min"
    if minutes <= 60: return "31–60 min"
    if minutes <= 90: return "61–90 min"
    if minutes <= 120: return "91–120 min"
    return "120+ min"

def rate_limit_sleep(seconds: float = 1.0):
    time.sleep(seconds)
