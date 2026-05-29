"""
utils/data_loader.py
Functions for loading, normalizing, and validating Excel data sheets.
"""

import pandas as pd
from utils.helpers import norm_id


# ---------------------------------------------------------------------------
# Sheet reading
# ---------------------------------------------------------------------------

def read_sheet_flexible(xls: pd.ExcelFile, candidates: list) -> pd.DataFrame:
    """Try reading the first matching sheet name from *candidates*."""
    for name in candidates:
        try:
            return pd.read_excel(xls, sheet_name=name)
        except Exception:
            continue
    raise ValueError(f"Missing required sheet. Tried: {candidates}")


def try_read_sheet_flexible(xls: pd.ExcelFile, candidates: list):
    """Same as *read_sheet_flexible* but returns None instead of raising."""
    for name in candidates:
        try:
            return pd.read_excel(xls, sheet_name=name)
        except Exception:
            continue
    return None


# ---------------------------------------------------------------------------
# Column normalisation
# ---------------------------------------------------------------------------

def normalize_columns(df: pd.DataFrame, mapping: dict) -> pd.DataFrame:
    """
    Rename columns to canonical names using *mapping*.

    mapping = { canonical_name: [alias1, alias2, ...], ... }
    After renaming, all column names are lowercased and stripped.
    """
    cols = {c.lower().strip(): c for c in df.columns}
    rename = {}
    for canonical, candidates in mapping.items():
        for cand in candidates:
            if cand.lower().strip() in cols:
                rename[cols[cand.lower().strip()]] = canonical
                break
    if rename:
        df = df.rename(columns=rename)
    df.columns = [c.lower().strip() for c in df.columns]
    return df


def ensure_cols(df: pd.DataFrame, needed: list) -> pd.DataFrame:
    """Add missing columns (empty string default)."""
    for col in needed:
        if col not in df.columns:
            df[col] = ""
    return df


# ---------------------------------------------------------------------------
# High-level loader
# ---------------------------------------------------------------------------

COURSES_MAP = {
    "course_code": ["course_code", "code", "course id", "course_id", "id"],
    "course_name": ["course_name", "name", "title"],
    "level": ["level", "lvl", "year"],
    "department": ["department", "dept", "program", "section"],
    "id": ["id", "course_id"],
}

DOCTORS_MAP = {
    "id": ["id", "doctor_id"],
    "name": ["name", "doctor_name"],
    "department": ["department", "dept", "program", "section"],
    "days_off": ["days_off", "days off"],
}

ASSISTANTS_MAP = {
    "id": ["id", "assistant_id"],
    "name": ["name", "assistant_name"],
    "department": ["department", "dept", "program", "section"],
    "days_off": ["days_off", "days off"],
}

HALLS_MAP = {
    "id": ["id", "hall_id", "venue_id"],
    "name": ["name", "hall_name", "venue_name"],
    "capacity": ["capacity", "max", "size"],
    "building": ["building", "bld", "block"],
}

LABS_MAP = {
    "id": ["id", "lab_id", "venue_id"],
    "name": ["name", "lab_name", "venue_name"],
    "capacity": ["capacity", "max", "size"],
    "building": ["building", "bld", "block"],
}

LEVEL_TEMPLATE_MAP = {
    "level": ["level", "lvl", "year"],
    "day": ["day", "weekday"],
    "period": ["period", "slot", "time"],
}


def load_all_data(xls: pd.ExcelFile):
    """
    Load and normalise all required sheets from *xls*.

    Returns
    -------
    courses, doctors, assistants, halls, labs : list[dict]
        Records ready for scheduling.
    level_template_df : pd.DataFrame | None
        Optional level-template sheet (may be None).
    """
    courses_df = normalize_columns(
        read_sheet_flexible(xls, ["Courses", "courses"]),
        COURSES_MAP,
    )
    doctors_df = normalize_columns(
        read_sheet_flexible(xls, ["Doctors", "doctors"]),
        DOCTORS_MAP,
    )
    assistants_df = normalize_columns(
        read_sheet_flexible(xls, ["Assistants", "assistants"]),
        ASSISTANTS_MAP,
    )
    halls_df = normalize_columns(
        read_sheet_flexible(xls, ["halls", "Halls", "HALLS"]),
        HALLS_MAP,
    )
    labs_df = normalize_columns(
        read_sheet_flexible(xls, ["Labs", "labs", "LABS"]),
        LABS_MAP,
    )

    # Ensure required columns exist
    courses_df = ensure_cols(courses_df, list(COURSES_MAP.keys()))
    doctors_df = ensure_cols(doctors_df, list(DOCTORS_MAP.keys()))
    assistants_df = ensure_cols(assistants_df, list(ASSISTANTS_MAP.keys()))
    halls_df = ensure_cols(halls_df, list(HALLS_MAP.keys()))
    labs_df = ensure_cols(labs_df, list(LABS_MAP.keys()))

    # Optional level-schedule template
    level_template_df = try_read_sheet_flexible(
        xls,
        ["LevelSchedule", "level_schedule", "LevelsSchedule", "LEVELSCHEDULE", "Level_Schedule"],
    )
    if (
        level_template_df is not None
        and isinstance(level_template_df, pd.DataFrame)
        and not level_template_df.empty
    ):
        level_template_df = normalize_columns(level_template_df, LEVEL_TEMPLATE_MAP)

    # Convert DataFrames to lists of dicts
    courses = courses_df.to_dict(orient="records")
    doctors = doctors_df.to_dict(orient="records")
    assistants = assistants_df.to_dict(orient="records")
    halls = halls_df.to_dict(orient="records")
    labs = labs_df.to_dict(orient="records")

    # Normalise IDs to strings
    for lst in (doctors, assistants, halls, labs):
        for v in lst:
            v["id"] = norm_id(v.get("id"))

    return courses, doctors, assistants, halls, labs, level_template_df
