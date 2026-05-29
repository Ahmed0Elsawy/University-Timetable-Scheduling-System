"""
utils/helpers.py
General-purpose helper functions used across the application.
"""

import pandas as pd


# ---------------------------------------------------------------------------
# Type-safe conversions
# ---------------------------------------------------------------------------

def safe_str(x) -> str:
    """Return stripped string or empty string for NaN/None values."""
    return str(x).strip() if pd.notna(x) else ""


def to_int_safe(x, default: int = 0) -> int:
    """Parse x to int; return *default* on failure."""
    try:
        return int(x)
    except Exception:
        try:
            return int(float(x))
        except Exception:
            return default


def norm_id(x) -> str:
    """Normalize an ID value to a clean string (drops trailing .0 from floats)."""
    if pd.isna(x):
        return ""
    try:
        fx = float(x)
        if fx.is_integer():
            return str(int(fx))
    except Exception:
        pass
    return str(x).strip()


# ---------------------------------------------------------------------------
# Venue capacity helpers
# ---------------------------------------------------------------------------

def venue_capacity(v: dict, default: int = 60) -> int:
    """Extract capacity from a venue dict, trying several key names."""
    for k in ("capacity", "max", "size"):
        val = v.get(k)
        if val not in (None, "", 0):
            try:
                return int(float(val))
            except Exception:
                pass
    return default


def max_capacity(venues: list, default: int = 60) -> int:
    """Return the maximum capacity across a list of venue dicts."""
    caps = []
    for v in venues:
        for k in ("capacity", "max", "size"):
            val = v.get(k)
            if val not in (None, "", 0):
                try:
                    caps.append(int(float(val)))
                except Exception:
                    pass
    return max(caps) if caps else default


# ---------------------------------------------------------------------------
# Course type helpers
# ---------------------------------------------------------------------------

def is_work_based_course(c: dict) -> bool:
    name = safe_str(c.get("course_name") or c.get("course_code") or c.get("name") or "")
    n = name.lower()
    return ("work" in n and "based" in n) or "work-based" in n


def is_project_course(c: dict) -> bool:
    name = safe_str(c.get("course_name") or c.get("course_code") or c.get("name") or "")
    return "project" in name.lower()


def is_special_course(c: dict) -> bool:
    return is_project_course(c) or is_work_based_course(c)


def course_key(c: dict) -> str:
    return safe_str(c.get("course_code") or c.get("id"))


def course_label(c: dict) -> str:
    code = safe_str(c.get("course_code") or c.get("id"))
    name = safe_str(c.get("course_name") or c.get("name") or "")
    if "project" in name.lower():
        return f"🎓 {code} — {name}"
    if "work" in name.lower() and "based" in name.lower():
        return f"🧰 {code} — {name}"
    return f"{code} — {name}"
