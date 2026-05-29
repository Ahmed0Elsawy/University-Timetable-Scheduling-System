"""
scheduler/cp_solver.py
Greedy-first + CP-SAT (OR-Tools) scheduling engine.
"""

from __future__ import annotations

import math
from collections import defaultdict

import pandas as pd
from ortools.sat.python import cp_model

from utils.helpers import safe_str, max_capacity, is_special_course
from utils.constants import DAYS, PERIOD_KEYS, UI_PERIOD_TO_KEY


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _parse_days_off(val) -> list[str]:
    """Parse a comma-separated days-off string into a list of day names."""
    if val is None or pd.isna(val):
        return []
    s = str(val).strip()
    if s == "" or s.lower() in ("none", "no", "0", "nan", "null"):
        return []
    return [
        x.strip()
        for x in s.split(",")
        if x.strip() and x.strip().lower() not in ("none", "no", "0", "nan", "null")
    ]


def _allowed_labs_for_course(c: dict, labs: list[dict]) -> list[str]:
    """Return lab IDs that are permitted for a given course type."""
    name = safe_str(
        c.get("course_name") or c.get("name") or c.get("course_code") or ""
    ).lower()

    if "work" in name and "based" in name:
        return [
            lab["id"]
            for lab in labs
            if "work" in safe_str(lab.get("name", "")).lower()
            and "based" in safe_str(lab.get("name", "")).lower()
        ]

    if "project" in name or "graduation" in name:
        return [
            lab["id"]
            for lab in labs
            if "project" in safe_str(lab.get("name", "")).lower()
            or "graduation" in safe_str(lab.get("name", "")).lower()
        ]

    # Regular courses: exclude work-based / project labs
    return [
        lab["id"]
        for lab in labs
        if "work" not in safe_str(lab.get("name", "")).lower()
        and "project" not in safe_str(lab.get("name", "")).lower()
        and "graduation" not in safe_str(lab.get("name", "")).lower()
    ]


# ---------------------------------------------------------------------------
# Public solver
# ---------------------------------------------------------------------------

def run_greedy_plus_cp(
    selected_courses: list[dict],
    course_students: dict,
    course_doctors: dict,
    course_assistants: dict,
    halls: list[dict],
    labs: list[dict],
    doctors: list[dict],
    assistants: list[dict],
    days: list[str] = DAYS,
    periods_ui: list[str] | None = None,
    hall_capacity: int = 0,
    lab_capacity: int = 0,
    level_template_df: pd.DataFrame | None = None,
    cp_timeout: int = 20,
):
    """
    Schedule *selected_courses* using a greedy pass followed by CP-SAT for
    any remaining unscheduled groups.

    Returns
    -------
    schedule_df, summary_df, conflicts_df : pd.DataFrame
    status : int   (cp_model.OPTIMAL / FEASIBLE / INFEASIBLE …)
    """
    period_keys = PERIOD_KEYS

    # Slots: "Saturday_P1", "Saturday_P2", …
    period_order_map = {k: i for i, k in enumerate(period_keys)}
    slots = [f"{d}_{p}" for d in days for p in period_keys]
    slots_sorted = sorted(
        slots,
        key=lambda s: (period_order_map[s.split("_")[1]], days.index(s.split("_")[0])),
    )
    slot_index = {s: i for i, s in enumerate(slots)}
    slot_count = len(slots)

    # UI period → key mapping
    if periods_ui:
        ui_to_key = {p: k for p, k in zip(periods_ui, period_keys)}
    else:
        ui_to_key = UI_PERIOD_TO_KEY

    # Venue index maps
    hall_index = {h["id"]: i for i, h in enumerate(halls)}
    lab_index = {lab["id"]: i for i, lab in enumerate(labs)}

    # Build people registry
    people_name: dict[str, str] = {}
    people_days_off: dict[str, list[str]] = {}
    for d in doctors:
        pid = f"D:{d['id']}"
        people_name[pid] = safe_str(d.get("name"))
        people_days_off[pid] = _parse_days_off(d.get("days_off", ""))
    for a in assistants:
        pid = f"A:{a['id']}"
        people_name[pid] = safe_str(a.get("name"))
        people_days_off[pid] = _parse_days_off(a.get("days_off", ""))

    people_occupied: dict[str, list[bool]] = {
        pid: [False] * slot_count for pid in people_name
    }

    # Capacity defaults
    avg_hall_cap = hall_capacity or max_capacity(halls)
    avg_lab_cap = lab_capacity or max_capacity(labs)

    # Course session counts
    course_lectures_count: dict[str, int] = {}
    course_labs_count: dict[str, int] = {}
    for c in selected_courses:
        code = safe_str(c.get("course_code") or c.get("id"))
        students = int(course_students.get(code, 0))
        course_lectures_count[code] = max(1, math.ceil(students / max(1, avg_hall_cap)))
        if not course_assistants.get(code):
            course_labs_count[code] = 0
        else:
            course_labs_count[code] = max(1, math.ceil(students / max(1, avg_lab_cap)))

    # Department doctor fallback pool
    dept_doctors: dict[str, list[str]] = {}
    for d in doctors:
        dept = safe_str(d.get("department") or "general").strip().lower()
        dept_doctors.setdefault(dept, []).append(f"D:{d['id']}")
    dept_counters: dict[str, int] = {}

    # Level → allowed slots (from template or heuristic)
    levels = sorted(
        {safe_str(c.get("level") or "0") for c in selected_courses
         if safe_str(c.get("level") or "0") != ""},
    )
    level_allowed_days: dict[str, list[str]] = {}
    n_days = len(days)
    for i, lvl in enumerate(levels):
        start = i % n_days
        level_allowed_days[lvl] = [days[(start + k) % n_days] for k in range(4)]
    level_allowed_days["0"] = days

    allowed_slots_by_level: dict[str, set[str]] = {}
    template_slots_by_level: dict[str, set[str]] = defaultdict(set)

    if (
        level_template_df is not None
        and isinstance(level_template_df, pd.DataFrame)
        and not level_template_df.empty
        and all(col in level_template_df.columns for col in ["level", "day", "period"])
    ):
        for _, r in level_template_df.iterrows():
            lvl = safe_str(r.get("level"))
            day_name = safe_str(r.get("day"))
            per = safe_str(r.get("period"))
            if per in ui_to_key:
                per = ui_to_key[per]
            if day_name in days and per in period_keys and lvl:
                template_slots_by_level[lvl].add(f"{day_name}_{per}")

        if template_slots_by_level:
            base_lvl = sorted(template_slots_by_level.keys(), key=lambda x: int(x) if x.isdigit() else 999)[0]
            base_slots = template_slots_by_level[base_lvl]
            allowed_slots_by_level[base_lvl] = set(base_slots)

            base_day_idx = {d: i for i, d in enumerate(days)}
            for i, lvl in enumerate(levels):
                if lvl == base_lvl:
                    continue
                rot = i % max(1, len(days))
                allowed_slots_by_level[lvl] = {
                    f"{days[(base_day_idx[s.split('_')[0]] + rot) % len(days)]}_{s.split('_')[1]}"
                    for s in base_slots
                }

            base_days = [d for d in days if any(s.startswith(d + "_") for s in base_slots)]
            if base_days:
                for i, lvl in enumerate(levels):
                    rot = i % max(1, len(base_days))
                    rotated = base_days[rot:] + base_days[:rot]
                    level_allowed_days[lvl] = rotated[:4] if len(rotated) >= 4 else rotated

    def slot_allowed_for_level(lvl: str, slot_str: str) -> bool:
        if lvl in allowed_slots_by_level and allowed_slots_by_level[lvl]:
            return slot_str in allowed_slots_by_level[lvl]
        return slot_str.split("_")[0] in level_allowed_days.get(lvl, days)

    # Occupancy matrices
    hall_occupied = [[False] * slot_count for _ in halls]
    lab_occupied = [[False] * slot_count for _ in labs]

    course_assigned_lectures: dict[str, list] = defaultdict(list)
    course_assigned_labs: dict[str, list] = defaultdict(list)

    # Build instructor plans
    lecture_instructor_plan: dict[str, list[str]] = {}
    lab_instructor_plan: dict[str, list[str]] = {}

    for c in selected_courses:
        code = safe_str(c.get("course_code") or c.get("id"))
        needed_lecs = course_lectures_count.get(code, 0)
        needed_labs = course_labs_count.get(code, 0)

        selected_docs = [x["id"] for x in (course_doctors.get(code) or []) if safe_str(x.get("id"))]
        if not selected_docs:
            dept = safe_str(c.get("department") or "general").lower()
            pool = dept_doctors.get(dept, [])
            if pool:
                idx = dept_counters.get(dept, 0) % len(pool)
                selected_docs = [pool[idx]]
                dept_counters[dept] = idx + 1
            elif doctors:
                selected_docs = [f"D:{doctors[0]['id']}"]

        lecture_instructor_plan[code] = [
            selected_docs[i % len(selected_docs)] for i in range(needed_lecs)
        ] if selected_docs else []

        selected_assts = [x["id"] for x in (course_assistants.get(code) or []) if safe_str(x.get("id"))]
        lab_instructor_plan[code] = [
            selected_assts[i % len(selected_assts)] for i in range(needed_labs)
        ] if selected_assts and needed_labs > 0 else []

    def get_lec_pid(code: str, gi: int) -> str:
        plan = lecture_instructor_plan.get(code, [])
        return plan[gi] if gi < len(plan) else (plan[0] if plan else "")

    def get_lab_pid(code: str, gi: int) -> str:
        plan = lab_instructor_plan.get(code, [])
        return plan[gi] if gi < len(plan) else (plan[0] if plan else "")

    # -----------------------------------------------------------------------
    # GREEDY PASS
    # -----------------------------------------------------------------------
    level_priority = {lvl: i for i, lvl in enumerate(levels)}
    courses_sorted = sorted(
        selected_courses,
        key=lambda x: (
            level_priority.get(safe_str(x.get("level") or "0"), 999),
            -int(course_students.get(safe_str(x.get("course_code") or x.get("id")), 0)),
        ),
    )

    for c in courses_sorted:
        code = safe_str(c.get("course_code") or c.get("id"))
        lvl = safe_str(c.get("level") or "0")
        needed_lecs = course_lectures_count.get(code, 0)
        needed_labs = course_labs_count.get(code, 0)

        # Lectures
        for gi in range(needed_lecs):
            if gi < len(course_assigned_lectures[code]):
                continue
            instr_pid = get_lec_pid(code, gi)
            placed = False
            for slot_str in slots_sorted:
                if not slot_allowed_for_level(lvl, slot_str):
                    continue
                s_idx = slot_index[slot_str]
                day_name = slot_str.split("_")[0]
                if instr_pid and (
                    day_name in people_days_off.get(instr_pid, [])
                    or people_occupied[instr_pid][s_idx]
                ):
                    continue
                if any(s_idx == lab_s for (_, _ip, lab_s, _g) in course_assigned_labs[code]):
                    continue
                for h in halls:
                    hidx = hall_index.get(h["id"])
                    if hidx is None or hall_occupied[hidx][s_idx]:
                        continue
                    hall_occupied[hidx][s_idx] = True
                    if instr_pid:
                        people_occupied[instr_pid][s_idx] = True
                    course_assigned_lectures[code].append((h["id"], s_idx, instr_pid, gi))
                    placed = True
                    break
                if placed:
                    break

        # Labs
        for gi in range(needed_labs):
            if gi < len(course_assigned_labs[code]):
                continue
            instr_pid = get_lab_pid(code, gi)
            placed = False
            allowed_lab_ids = _allowed_labs_for_course(c, labs)
            for slot_str in slots_sorted:
                if not slot_allowed_for_level(lvl, slot_str):
                    continue
                s_idx = slot_index[slot_str]
                day_name = slot_str.split("_")[0]
                if any(s_idx == lec_s for (_, lec_s, _ip, _g) in course_assigned_lectures[code]):
                    continue
                if instr_pid and (
                    day_name in people_days_off.get(instr_pid, [])
                    or people_occupied[instr_pid][s_idx]
                ):
                    continue
                for lab in labs:
                    if lab["id"] not in allowed_lab_ids:
                        continue
                    lidx = lab_index.get(lab["id"])
                    if lidx is None or lab_occupied[lidx][s_idx]:
                        continue
                    lab_occupied[lidx][s_idx] = True
                    if instr_pid:
                        people_occupied[instr_pid][s_idx] = True
                    course_assigned_labs[code].append((lab["id"], instr_pid, s_idx, gi))
                    placed = True
                    break
                if placed:
                    break

    # -----------------------------------------------------------------------
    # CP-SAT PASS for remaining unscheduled groups
    # -----------------------------------------------------------------------
    remaining_lec_groups: dict[str, list[int]] = {}
    remaining_lab_groups: dict[str, list[int]] = {}
    for c in selected_courses:
        code = safe_str(c.get("course_code") or c.get("id"))
        remaining_lec_groups[code] = list(range(len(course_assigned_lectures[code]), course_lectures_count.get(code, 0)))
        remaining_lab_groups[code] = list(range(len(course_assigned_labs[code]), course_labs_count.get(code, 0)))

    model = cp_model.CpModel()
    x_lecture: dict = {}
    x_lab: dict = {}

    for c in selected_courses:
        code = safe_str(c.get("course_code") or c.get("id"))
        lvl = safe_str(c.get("level") or "0")
        for gi in remaining_lec_groups.get(code, []):
            instr_pid = get_lec_pid(code, gi)
            for h in halls:
                hidx = hall_index.get(h["id"])
                if hidx is None:
                    continue
                for s_idx in range(slot_count):
                    slot_str = slots[s_idx]
                    if not slot_allowed_for_level(lvl, slot_str):
                        continue
                    day_name = slot_str.split("_")[0]
                    if hall_occupied[hidx][s_idx]:
                        continue
                    if instr_pid and (
                        day_name in people_days_off.get(instr_pid, [])
                        or people_occupied[instr_pid][s_idx]
                    ):
                        continue
                    if any(s_idx == lab_s for (_, _ip, lab_s, _g) in course_assigned_labs[code]):
                        continue
                    x_lecture[(code, gi, h["id"], s_idx)] = model.NewBoolVar(
                        f"lec_c{code}_g{gi}_h{h['id']}_s{s_idx}"
                    )

    for c in selected_courses:
        code = safe_str(c.get("course_code") or c.get("id"))
        lvl = safe_str(c.get("level") or "0")
        allowed_lab_ids = _allowed_labs_for_course(c, labs)
        for gi in remaining_lab_groups.get(code, []):
            instr_pid = get_lab_pid(code, gi)
            for lab in labs:
                if lab["id"] not in allowed_lab_ids:
                    continue
                lidx = lab_index.get(lab["id"])
                if lidx is None:
                    continue
                for s_idx in range(slot_count):
                    slot_str = slots[s_idx]
                    if not slot_allowed_for_level(lvl, slot_str):
                        continue
                    day_name = slot_str.split("_")[0]
                    if lab_occupied[lidx][s_idx]:
                        continue
                    if instr_pid and (
                        day_name in people_days_off.get(instr_pid, [])
                        or people_occupied[instr_pid][s_idx]
                    ):
                        continue
                    if any(s_idx == lec_s for (_, lec_s, _ip, _g) in course_assigned_lectures[code]):
                        continue
                    x_lab[(code, gi, lab["id"], instr_pid, s_idx)] = model.NewBoolVar(
                        f"lab_c{code}_g{gi}_l{lab['id']}_i{instr_pid}_s{s_idx}"
                    )

    # Shortfall variables
    shortfall_lec: dict = {}
    shortfall_lab: dict = {}
    for c in selected_courses:
        code = safe_str(c.get("course_code") or c.get("id"))
        for gi in remaining_lec_groups.get(code, []):
            vars_here = [v for (cc, g2, _hid, _si), v in x_lecture.items() if cc == code and g2 == gi]
            sv = model.NewIntVar(0, 1, f"short_lec_{code}_g{gi}")
            model.Add((sum(vars_here) + sv == 1) if vars_here else (sv == 1))
            shortfall_lec[(code, gi)] = sv

        for gi in remaining_lab_groups.get(code, []):
            vars_here = [v for (cc, g2, _lid, _ipid, _si), v in x_lab.items() if cc == code and g2 == gi]
            sv = model.NewIntVar(0, 1, f"short_lab_{code}_g{gi}")
            model.Add((sum(vars_here) + sv == 1) if vars_here else (sv == 1))
            shortfall_lab[(code, gi)] = sv

    # No-double-book constraints
    for h in halls:
        hidx = hall_index.get(h["id"])
        if hidx is None:
            continue
        for s_idx in range(slot_count):
            used = 1 if hall_occupied[hidx][s_idx] else 0
            vars_here = [v for (cc, gi, hid, si), v in x_lecture.items() if hid == h["id"] and si == s_idx]
            if vars_here:
                model.Add(sum(vars_here) + used <= 1)

    for lab in labs:
        lidx = lab_index.get(lab["id"])
        if lidx is None:
            continue
        for s_idx in range(slot_count):
            used = 1 if lab_occupied[lidx][s_idx] else 0
            vars_here = [v for (cc, gi, lid, ipid, si), v in x_lab.items() if lid == lab["id"] and si == s_idx]
            if vars_here:
                model.Add(sum(vars_here) + used <= 1)

    for pid in people_occupied:
        for s_idx in range(slot_count):
            used = 1 if people_occupied[pid][s_idx] else 0
            lec_here = [v for (cc, gi, hid, si), v in x_lecture.items() if si == s_idx and get_lec_pid(cc, gi) == pid]
            lab_here = [v for (cc, gi, lid, ipid, si), v in x_lab.items() if si == s_idx and ipid == pid]
            if lec_here or lab_here:
                model.Add(sum(lec_here) + sum(lab_here) + used <= 1)

    for c in selected_courses:
        code = safe_str(c.get("course_code") or c.get("id"))
        for s_idx in range(slot_count):
            lec_vars = [v for (cc, gi, hid, si), v in x_lecture.items() if cc == code and si == s_idx]
            lab_vars = [v for (cc, gi, lid, ipid, si), v in x_lab.items() if cc == code and si == s_idx]
            if lec_vars and lab_vars:
                model.Add(sum(lec_vars) + sum(lab_vars) <= 1)
            if lab_vars:
                model.Add(sum(lab_vars) <= 1)

    # Soft objective: minimise shortfall, prefer early periods
    early_bonus = [
        v for (code, gi, hid, s_idx), v in x_lecture.items()
        if slots[s_idx].split("_")[1] in ("P1", "P2")
    ]
    total_short = list(shortfall_lec.values()) + list(shortfall_lab.values())
    if total_short:
        model.Minimize(sum(total_short) * 1000 - (sum(early_bonus) * 5 if early_bonus else 0))
    elif early_bonus:
        model.Minimize(-sum(early_bonus) * 5)

    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    solver.parameters.max_time_in_seconds = float(cp_timeout)
    solver.parameters.random_seed = 0
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for (code, gi, hid, s_idx), var in x_lecture.items():
            if solver.BooleanValue(var):
                course_assigned_lectures[code].append((hid, s_idx, get_lec_pid(code, gi), gi))
        for (code, gi, lid, instr_pid, s_idx), var in x_lab.items():
            if solver.BooleanValue(var):
                course_assigned_labs[code].append((lid, instr_pid, s_idx, gi))

    # -----------------------------------------------------------------------
    # Build output DataFrames
    # -----------------------------------------------------------------------
    final_rows = []
    for c in selected_courses:
        code = safe_str(c.get("course_code") or c.get("id"))
        cname = safe_str(c.get("course_name") or c.get("name") or "")
        level = safe_str(c.get("level") or "")
        dept = safe_str(c.get("department") or "")

        doctors_all = ", ".join(
            x.get("name", "") for x in (course_doctors.get(code) or []) if safe_str(x.get("name"))
        )
        assts_all = ", ".join(
            x.get("name", "") for x in (course_assistants.get(code) or []) if safe_str(x.get("name"))
        )

        for hid, s_idx, instr_pid, gi in course_assigned_lectures[code]:
            hname = next((safe_str(h.get("name")) for h in halls if h["id"] == hid), "")
            day_name, period_key = slots[s_idx].split("_")
            instr_name = people_name.get(instr_pid, "")
            instr_role = (
                "Doctor" if str(instr_pid).startswith("D:")
                else "Assistant" if str(instr_pid).startswith("A:")
                else "Person"
            )
            final_rows.append({
                "Course Code": code, "Course Name": cname, "Type": "Lecture",
                "Day": day_name, "Period": period_key, "Room": hname,
                "Instructor": instr_name, "Instructor ID": instr_pid,
                "Instructor Role": instr_role, "Group": gi + 1,
                "Doctors": doctors_all if is_special_course(c) else "",
                "Assistants": assts_all if is_special_course(c) else "",
                "Level": level, "Department": dept,
            })

        for lid, instr_pid, s_idx, gi in course_assigned_labs[code]:
            lname = next((safe_str(lab.get("name")) for lab in labs if lab["id"] == lid), "")
            day_name, period_key = slots[s_idx].split("_")
            instr_name = people_name.get(instr_pid, "")
            instr_role = (
                "Doctor" if str(instr_pid).startswith("D:")
                else "Assistant" if str(instr_pid).startswith("A:")
                else "Person"
            )
            final_rows.append({
                "Course Code": code, "Course Name": cname, "Type": "Lab",
                "Day": day_name, "Period": period_key, "Room": lname,
                "Instructor": instr_name, "Instructor ID": instr_pid,
                "Instructor Role": instr_role, "Group": gi + 1,
                "Doctors": doctors_all if is_special_course(c) else "",
                "Assistants": assts_all if is_special_course(c) else "",
                "Level": level, "Department": dept,
            })

    schedule_df = pd.DataFrame(final_rows)

    summary_rows = []
    for code in course_lectures_count:
        students = int(course_students.get(code, 0))
        needed_lecs = course_lectures_count[code]
        assigned_lecs = len(course_assigned_lectures.get(code, []))
        needed_labs = course_labs_count.get(code, 0)
        assigned_labs = len(course_assigned_labs.get(code, []))

        rem_lec = max(0, needed_lecs - assigned_lecs)
        rem_lab = max(0, needed_labs - assigned_labs)
        rem_students = max(
            max(0, students - assigned_lecs * max(1, avg_hall_cap)),
            max(0, students - assigned_labs * max(1, avg_lab_cap)),
        )
        summary_rows.append({
            "Course Code": code, "Students": students,
            "Needed Lectures": needed_lecs, "Assigned Lectures": assigned_lecs, "Unassigned Lectures": rem_lec,
            "Needed Labs": needed_labs, "Assigned Labs": assigned_labs, "Unassigned Labs": rem_lab,
            "Remaining Students (est.)": rem_students,
        })

    summary_df = pd.DataFrame(summary_rows)
    conflicts_df = summary_df[
        (summary_df["Unassigned Lectures"] > 0) | (summary_df["Unassigned Labs"] > 0)
    ]

    return schedule_df, summary_df, conflicts_df, status
