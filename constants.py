"""
utils/constants.py
Application-wide constants: days, periods, time mappings.
"""

DAYS: list[str] = [
    "Saturday",
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
]

PERIOD_KEYS: list[str] = ["P1", "P2", "P3", "P4", "P5"]

PERIOD_TIMES: dict[str, str] = {
    "P1": "8:45-10:15",
    "P2": "10:15-11:45",
    "P3": "11:45-13:15",
    "P4": "13:15-14:45",
    "P5": "14:45-16:15",
}

# Human-readable period labels (used in UI dropdowns)
PERIODS_UI: list[str] = [PERIOD_TIMES[k] for k in PERIOD_KEYS]

# Bidirectional mappings
UI_PERIOD_TO_KEY: dict[str, str] = dict(zip(PERIODS_UI, PERIOD_KEYS))
KEY_TO_UI_PERIOD: dict[str, str] = dict(zip(PERIOD_KEYS, PERIODS_UI))
