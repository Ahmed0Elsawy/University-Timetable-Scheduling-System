"""
ui/sidebar.py
Sidebar widgets: course selection, capacity settings, GA parameters.
"""

from __future__ import annotations

import math
import random

import streamlit as st
from collections import defaultdict

from utils.helpers import safe_str, to_int_safe, max_capacity, is_special_course, course_key, course_label
from utils.constants import DAYS


# ---------------------------------------------------------------------------
# Sidebar configuration panel
# ---------------------------------------------------------------------------

def render_sidebar(courses: list[dict], halls: list[dict], labs: list[dict]):
    """
    Render the sidebar and return all user-configured values.

    Returns
    -------
    sel_levels, max_per_level, hall_capacity_override, lab_capacity_override,
    use_hybrid, ga_generations, ga_pop, ga_elite, cp_timeout
    """
    with st.sidebar:
        st.markdown("### 🎯 Course Selection")

        all_levels = sorted({
            to_int_safe(safe_str(c.get("level")))
            for c in courses if safe_str(c.get("level")) != ""
        })

        sel_levels = st.multiselect(
            "**Levels (years)**",
            all_levels,
            default=all_levels,
            help="Select academic levels to include",
        )

        st.markdown("---")
        st.markdown("### ⚙️ Configuration")

        max_per_level = st.number_input(
            "**Max courses per level**", min_value=1, max_value=30, value=4, step=1,
            help="Limit courses per academic level",
        )
        hall_capacity_override = st.number_input(
            "**Default Hall capacity**", min_value=1, value=max_capacity(halls), step=1,
            help="Fallback capacity for lecture halls",
        )
        lab_capacity_override = st.number_input(
            "**Default Lab capacity**", min_value=1, value=max_capacity(labs), step=1,
            help="Fallback capacity for labs",
        )

        st.markdown("---")
        st.markdown("### 🔧 Optimization Settings")

        use_hybrid = st.checkbox(
            "**Enable Hybrid Optimization**", value=True,
            help="Combine Genetic Algorithm with OR-Tools for better results",
        )

        col1, col2 = st.columns(2)
        with col1:
            ga_generations = st.number_input("**GA Generations**", min_value=3, max_value=200, value=15, step=1)
            ga_pop = st.number_input("**GA Population**", min_value=4, max_value=80, value=12, step=1)
        with col2:
            ga_elite = st.number_input("**GA Elite**", min_value=1, max_value=10, value=3, step=1)
            cp_timeout = st.number_input("**CP Timeout (s)**", min_value=5, max_value=300, value=20, step=1)

    return sel_levels, max_per_level, hall_capacity_override, lab_capacity_override, \
           use_hybrid, ga_generations, ga_pop, ga_elite, cp_timeout


# ---------------------------------------------------------------------------
# Course selection panel
# ---------------------------------------------------------------------------

def render_course_selection(
    courses: list[dict],
    sel_levels: list[int],
    max_per_level: int,
):
    """
    Render course add/remove UI and return the final list of selected courses.
    """
    st.markdown("### 📚 Course Selection")

    options_map = {course_label(c): c for c in courses}
    course_labels_all = list(options_map.keys())

    base_level_courses = [
        c for c in courses if to_int_safe(safe_str(c.get("level"))) in sel_levels
    ]

    level_buckets: dict[int, list] = defaultdict(list)
    for c in base_level_courses:
        level_buckets[to_int_safe(safe_str(c.get("level")))].append(c)

    base_limited: list[dict] = []
    for lst in level_buckets.values():
        base_limited.extend(lst[:max_per_level])

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 📋 Available Courses")
        add_labels = st.multiselect(
            "**Add specific courses**", course_labels_all, default=[],
            help="Manually add additional courses",
        )
        manual_add = [options_map[lbl] for lbl in add_labels if lbl in options_map]

    with col2:
        st.markdown("#### 🗑️ Remove Courses")
        all_selected = base_limited + manual_add
        remove_set: set[str] = set()
        if all_selected:
            remove_labels = st.multiselect(
                "**Remove from selection**",
                [course_label(c) for c in all_selected],
                default=[],
                help="Remove courses from current selection",
            )
            for lbl in remove_labels:
                c = options_map.get(lbl)
                if c is not None:
                    remove_set.add(course_key(c))

    # Deduplicate and apply removals
    selected_dict: dict[str, dict] = {}
    for c in base_limited + manual_add:
        k = course_key(c)
        if k and k not in remove_set:
            selected_dict[k] = c

    selected_courses = list(selected_dict.values())

    if selected_courses:
        st.success(f"✅ {len(selected_courses)} courses selected for scheduling")
    else:
        st.warning("⚠️ No courses selected. Please add courses from the selection above.")

    return selected_courses


# ---------------------------------------------------------------------------
# Per-course configuration panel
# ---------------------------------------------------------------------------

def render_per_course_config(
    selected_courses: list[dict],
    doctors: list[dict],
    assistants: list[dict],
    hall_capacity_override: int,
    lab_capacity_override: int,
):
    """
    Render per-course student count and instructor assignment widgets.

    Returns
    -------
    course_students, course_doctors, course_assistants : dict
    """
    if not selected_courses:
        return {}, {}, {}

    st.markdown("### ⚙️ Per-Course Configuration")

    doc_choices = {
        f"D:{d.get('id', '')}": safe_str(d.get("name"))
        for d in doctors if safe_str(d.get("name"))
    }
    asst_choices = {
        f"A:{a.get('id', '')}": safe_str(a.get("name"))
        for a in assistants if safe_str(a.get("name"))
    }

    course_students: dict[str, int] = {}
    course_doctors: dict[str, list] = {}
    course_assistants: dict[str, list] = {}

    tab1, tab2 = st.tabs(["📝 Course Settings", "👨‍🏫 Instructor Assignment"])

    with tab1:
        for idx, c in enumerate(selected_courses):
            code = safe_str(c.get("course_code") or c.get("id"))
            name = safe_str(c.get("course_name") or c.get("name"))
            lvl = to_int_safe(safe_str(c.get("level")))
            title = f"{'🎓 ' if 'project' in name.lower() else '🧰 ' if is_special_course(c) else ''}{code} — {name}"

            with st.expander(f"{title} (Level {lvl or 'N/A'})", expanded=False):
                ca, cb = st.columns(2)
                with ca:
                    st.markdown("**👥 Student Enrollment**")
                    n = st.number_input(
                        f"Students for {code}",
                        min_value=0, value=60, step=5,
                        key=f"stu_{code}_{idx}",
                    )
                    course_students[code] = int(n)
                    st.caption(
                        f"Estimated: {math.ceil(n / hall_capacity_override)} lecture groups, "
                        f"{math.ceil(n / lab_capacity_override)} lab groups"
                    )
                with cb:
                    st.markdown("**📊 Course Information**")
                    st.info(
                        f"**Level:** {lvl or 'N/A'}\n"
                        f"**Department:** {safe_str(c.get('department', ''))}\n"
                        f"**Type:** {'Special' if is_special_course(c) else 'Regular'}"
                    )

    with tab2:
        for idx, c in enumerate(selected_courses):
            code = safe_str(c.get("course_code") or c.get("id"))
            name = safe_str(c.get("course_name") or c.get("name"))

            with st.expander(f"{code} — {name} — Instructor Assignment", expanded=False):
                ca, cb = st.columns(2)

                with ca:
                    st.markdown("**👨‍⚕️ Doctor Assignment**")
                    sel_doc = st.multiselect(
                        "Doctor(s)",
                        options=list(doc_choices.keys()),
                        format_func=lambda x: doc_choices.get(x, ""),
                        key=f"doc_{code}_{idx}",
                    )
                    if not sel_doc and doc_choices:
                        sel_doc = random.sample(list(doc_choices.keys()), k=min(1, len(doc_choices)))
                    course_doctors[code] = [{"id": d, "name": doc_choices.get(d, "")} for d in sel_doc]
                    if sel_doc:
                        st.success(f"Assigned {len(sel_doc)} doctor(s)")
                    else:
                        st.warning("No doctor assigned")

                with cb:
                    st.markdown("**👨‍🏫 Assistant Assignment**")
                    if is_special_course(c):
                        combined = {**asst_choices, **doc_choices}
                        opts = list(combined.keys())
                        fmt = lambda x: ("👨‍⚕️ " + doc_choices[x] if x in doc_choices else "👨‍🏫 " + asst_choices.get(x, ""))
                    else:
                        combined = asst_choices
                        opts = list(asst_choices.keys())
                        fmt = lambda x: asst_choices.get(x, "")

                    sel_asst = st.multiselect(
                        "Assistant(s)", options=opts, format_func=fmt,
                        key=f"asst_{code}_{idx}",
                    )
                    course_assistants[code] = [{"id": a, "name": combined.get(a, "")} for a in sel_asst]
                    if sel_asst:
                        st.success(f"Assigned {len(sel_asst)} assistant(s)")
                    elif not is_special_course(c):
                        st.info("No assistants — no lab sessions will be scheduled")

    return course_students, course_doctors, course_assistants
