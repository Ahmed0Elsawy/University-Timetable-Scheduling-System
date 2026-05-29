"""
ui/components.py
Streamlit display components: visual timetable grid and summary cards.
"""

from __future__ import annotations

import streamlit as st

from utils.constants import DAYS, PERIOD_KEYS, PERIOD_TIMES
from ui.styles import TIMETABLE_CSS


# ---------------------------------------------------------------------------
# Timetable grid
# ---------------------------------------------------------------------------

def create_visual_timetable(schedule_df) -> None:
    """Render a full HTML timetable grid from *schedule_df*."""
    if schedule_df is None or schedule_df.empty:
        st.warning("No schedule data to display.")
        return

    days_order = DAYS
    periods_order = PERIOD_KEYS

    # Fill grid structure
    timetable = {day: {period: [] for period in periods_order} for day in days_order}
    for _, row in schedule_df.iterrows():
        day = row["Day"]
        period = row["Period"]
        if day in timetable and period in timetable[day]:
            timetable[day][period].append({
                "course_code": row["Course Code"],
                "course_name": row["Course Name"],
                "type": row["Type"],
                "room": row["Room"],
                "instructor": row["Instructor"],
                "group": row.get("Group", ""),
            })

    st.markdown(TIMETABLE_CSS, unsafe_allow_html=True)
    st.markdown('<div class="modern-timetable">', unsafe_allow_html=True)
    st.markdown(
        """
        <div class="modern-header">
            <h2>University Course Timetable</h2>
            <div class="subtitle">Generated Schedule — Academic Year</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Build table HTML
    html = ['<table class="modern-table"><thead><tr><th class="time-header">Day / Period</th>']
    for p in periods_order:
        html.append(f'<th>Period {p[1:]}<br><span class="period-time">{PERIOD_TIMES[p]}</span></th>')
    html.append("</tr></thead><tbody>")

    for day in days_order:
        html.append(f'<tr><th class="day-header">{day}</th>')
        for period in periods_order:
            html.append("<td>")
            items = timetable[day][period]
            if items:
                for item in items:
                    css_class = (
                        "lecture-modern" if item["type"] == "Lecture"
                        else "lab-modern" if item["type"] == "Lab"
                        else "section-modern"
                    )
                    g = item.get("group", "")
                    badge = f'<span class="group-badge">G{g}</span>' if str(g).strip() else ""
                    html.append(
                        f'<div class="modern-item {css_class}">'
                        f'<span class="item-type">{item["type"].upper()}</span>'
                        f'<span class="course-name">{item["course_name"]}</span>'
                        f'{badge}'
                        f'<span class="instructor">{item["instructor"]}</span>'
                        f'<span class="room-info">{item["room"]}</span>'
                        f"</div>"
                    )
            else:
                html.append('<div class="empty-slot-modern">Free Period</div>')
            html.append("</td>")
        html.append("</tr>")

    html.append("</tbody></table>")
    html.append("""
    <div class="legend-modern">
        <div class="legend-item-modern">
            <div class="legend-color-modern legend-lecture-modern"></div>
            <span>Lecture (Doctor — Hall)</span>
        </div>
        <div class="legend-item-modern">
            <div class="legend-color-modern legend-lab-modern"></div>
            <span>Lab (Assistant — Lab Room)</span>
        </div>
        <div class="legend-item-modern">
            <div class="legend-color-modern" style="background: linear-gradient(135deg,#9b59b6,#8e44ad);"></div>
            <span>Section / Tutorial</span>
        </div>
    </div>
    """)

    st.markdown("".join(html), unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Summary cards + course details
# ---------------------------------------------------------------------------

def create_visual_summary(summary_df, conflicts_df) -> None:
    """Render scheduling summary metrics and per-course details."""
    if summary_df is None or summary_df.empty:
        st.warning("No summary data yet.")
        return

    total_courses = len(summary_df)
    total_students = int(summary_df["Students"].sum())
    total_assigned_lec = int(summary_df["Assigned Lectures"].sum())
    total_needed_lec = int(summary_df["Needed Lectures"].sum())
    total_unassigned_lec = int(summary_df["Unassigned Lectures"].sum())
    total_assigned_lab = int(summary_df["Assigned Labs"].sum())
    total_needed_lab = int(summary_df["Needed Labs"].sum())
    total_unassigned_lab = int(summary_df["Unassigned Labs"].sum())
    lec_pct = (100.0 * total_assigned_lec / total_needed_lec) if total_needed_lec else 0.0
    lab_pct = (100.0 * total_assigned_lab / total_needed_lab) if total_needed_lab else 0.0

    st.markdown("### 📊 Schedule Summary")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Total Courses</div>'
            f'<div class="metric-value">{total_courses}</div>'
            f'<div style="font-size:0.85em;color:#7f8c8d;margin-top:8px;">Scheduled</div></div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div class="metric-card"><div class="metric-label">Total Students</div>'
            f'<div class="metric-value">{total_students:,}</div>'
            f'<div style="font-size:0.85em;color:#7f8c8d;margin-top:8px;">Enrolled</div></div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f'<div class="metric-card lecture"><div class="metric-label">Lectures</div>'
            f'<div class="metric-value">{total_assigned_lec}/{total_needed_lec}</div>'
            f'<div style="font-size:0.85em;color:#7f8c8d;margin-top:8px;">'
            f'{lec_pct:.1f}% • {total_unassigned_lec} unassigned</div></div>',
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f'<div class="metric-card lab"><div class="metric-label">Labs</div>'
            f'<div class="metric-value">{total_assigned_lab}/{total_needed_lab}</div>'
            f'<div style="font-size:0.85em;color:#7f8c8d;margin-top:8px;">'
            f'{lab_pct:.1f}% • {total_unassigned_lab} unassigned</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown("---")
    st.markdown("### 📋 Course Details")

    for _, r in summary_df.sort_values("Course Code").iterrows():
        code = str(r["Course Code"])
        students = int(r["Students"])
        need_lec = int(r["Needed Lectures"])
        ass_lec = int(r["Assigned Lectures"])
        un_lec = int(r["Unassigned Lectures"])
        need_lab = int(r["Needed Labs"])
        ass_lab = int(r["Assigned Labs"])
        un_lab = int(r["Unassigned Labs"])
        remaining = int(r.get("Remaining Students (est.)", 0))

        if un_lec > 0 or un_lab > 0:
            icon = "⚠️"
        elif ass_lec == 0 and ass_lab == 0:
            icon = "⏳"
        else:
            icon = "✅"

        with st.expander(f"{icon} {code} — {students:,} students", expanded=False):
            ca, cb, cc, cd = st.columns(4)
            with ca:
                st.metric("Students", f"{students:,}")
            with cb:
                st.metric("Lectures", f"{ass_lec}/{need_lec}",
                          f"{un_lec} unassigned" if un_lec else "Complete")
                st.progress(ass_lec / max(1, need_lec))
            with cc:
                st.metric("Labs", f"{ass_lab}/{need_lab}",
                          f"{un_lab} unassigned" if un_lab else "Complete")
                st.progress(ass_lab / max(1, need_lab))
            with cd:
                st.metric("Remaining", f"{remaining:,}")
            if un_lec > 0 or un_lab > 0:
                st.warning(f"⚠️ {un_lec} unassigned lectures and {un_lab} unassigned labs.")

    # Conflicts
    st.markdown("---")
    st.markdown("### ⚠️ Scheduling Conflicts")

    if conflicts_df is not None and not conflicts_df.empty:
        st.markdown(
            f'<div class="warning-box"><strong>Attention:</strong> '
            f'Found {len(conflicts_df)} courses with scheduling conflicts.</div>',
            unsafe_allow_html=True,
        )
        st.dataframe(
            conflicts_df,
            use_container_width=True,
            column_config={
                "Course Code": st.column_config.TextColumn("Code", width="small"),
                "Students": st.column_config.NumberColumn("Students", width="small", format="%d"),
                "Unassigned Lectures": st.column_config.NumberColumn("Unassigned Lec", width="small"),
                "Unassigned Labs": st.column_config.NumberColumn("Unassigned Lab", width="small"),
                "Remaining Students (est.)": st.column_config.NumberColumn("Remaining", width="small"),
            },
        )
    else:
        st.markdown(
            '<div class="success-box"><strong>Great!</strong> All courses scheduled without conflicts.</div>',
            unsafe_allow_html=True,
        )
