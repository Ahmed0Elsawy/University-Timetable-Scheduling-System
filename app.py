"""
app.py
Entry point — Timetable Smart Dashboard (Hybrid OR-Tools + GA).

Run with:
    streamlit run app.py
"""

import os
from io import BytesIO

import streamlit as st
from ortools.sat.python import cp_model

# ── Project modules ──────────────────────────────────────────────────────────
from utils.data_loader import load_all_data
from utils.constants import DAYS, PERIODS_UI
from ui.styles import GLOBAL_CSS
from ui.sidebar import render_sidebar, render_course_selection, render_per_course_config
from ui.components import create_visual_timetable, create_visual_summary
from scheduler.cp_solver import run_greedy_plus_cp
from scheduler.ga_hybrid import ga_hybrid_run
from export.excel_export import df_to_excel_bytes, export_full_workbook_bytes

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(page_title="Timetable Smart Dashboard", layout="wide")
st.title("🗓️ Timetable Scheduling — Hybrid (OR-Tools + GA)")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ── Banner ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <div class="main-header">
        <h1>University Timetable Scheduling</h1>
        <p>Hybrid Optimization System (OR-Tools + Genetic Algorithm)</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── File upload ───────────────────────────────────────────────────────────────
with st.container():
    col1, col2 = st.columns([2, 1])
    with col1:
        uploaded = st.file_uploader(
            "📁 Upload Excel File", type=["xlsx", "xls"],
            help="Upload your university data file (Courses, Doctors, Assistants, Halls, Labs sheets)",
        )
    with col2:
        st.markdown("### ⚙️ Quick Setup")
        st.info("Upload your data file to begin scheduling")

# Fall back to a local file path during development
DEFAULT_LOCAL = r"C:\Users\Mega Store\Downloads\FINAL TIME (1)\FINAL TIME\DATA.xlsx"

if uploaded is not None:
    try:
        import pandas as pd
        xls = pd.ExcelFile(BytesIO(uploaded.read()))
        st.success("✅ File uploaded successfully!")
    except Exception as e:
        st.error(f"❌ Error reading uploaded file: {e}")
        st.stop()
elif os.path.exists(DEFAULT_LOCAL):
    import pandas as pd
    st.info(f"📂 Using local file: {DEFAULT_LOCAL}")
    xls = pd.ExcelFile(DEFAULT_LOCAL)
else:
    st.warning("📤 Please upload an Excel file to proceed.")
    st.stop()

# ── Load data ─────────────────────────────────────────────────────────────────
try:
    with st.spinner("📊 Loading data…"):
        courses, doctors, assistants, halls, labs, level_template_df = load_all_data(xls)
    st.success("✅ Data loaded successfully!")
except Exception as e:
    st.error(f"❌ Error reading sheets: {e}")
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────────────────
(
    sel_levels,
    max_per_level,
    hall_capacity_override,
    lab_capacity_override,
    use_hybrid,
    ga_generations,
    ga_pop,
    ga_elite,
    cp_timeout,
) = render_sidebar(courses, halls, labs)

# ── Course selection ──────────────────────────────────────────────────────────
selected_courses = render_course_selection(courses, sel_levels, max_per_level)

# ── Per-course configuration ──────────────────────────────────────────────────
course_students, course_doctors, course_assistants = render_per_course_config(
    selected_courses, doctors, assistants, hall_capacity_override, lab_capacity_override,
)

# ── Run button ────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("### 🚀 Generate Schedule")

_, col_btn, _ = st.columns([1, 2, 1])
with col_btn:
    run_clicked = st.button(
        "🎯 Run Scheduling Optimization",
        use_container_width=True,
        type="primary",
        help="Generate optimised timetable using OR-Tools and Genetic Algorithm",
    )

if "last_result" not in st.session_state:
    st.session_state.last_result = None

if run_clicked:
    if not selected_courses:
        st.error("❌ Please select at least one course before running the scheduler.")
        st.stop()

    with st.spinner("🧠 Running optimisation…"):
        progress = st.progress(0)

        if use_hybrid:
            st.info("⚙️ Starting Hybrid Optimisation (GA + OR-Tools)…")
            progress.progress(20)

            schedule_df, summary_df, conflicts_df, status, best_fit = ga_hybrid_run(
                selected_courses=selected_courses,
                course_students=course_students,
                course_doctors=course_doctors,
                course_assistants=course_assistants,
                halls=halls,
                labs=labs,
                doctors=doctors,
                assistants=assistants,
                days=DAYS,
                periods_ui=PERIODS_UI,
                hall_capacity_override=int(hall_capacity_override),
                lab_capacity_override=int(lab_capacity_override),
                level_template_df=level_template_df,
                generations=int(ga_generations),
                pop_size=int(ga_pop),
                elite_k=int(ga_elite),
                cp_timeout=int(cp_timeout),
            )
            progress.progress(100)
            st.success("✅ Hybrid Optimisation Complete!")
            st.caption(f"🎯 Optimisation Score: {best_fit:.2f}")

        else:
            st.info("⚙️ Running OR-Tools Optimisation…")
            progress.progress(50)

            schedule_df, summary_df, conflicts_df, status = run_greedy_plus_cp(
                selected_courses=selected_courses,
                course_students=course_students,
                course_doctors=course_doctors,
                course_assistants=course_assistants,
                halls=halls,
                labs=labs,
                doctors=doctors,
                assistants=assistants,
                days=DAYS,
                periods_ui=PERIODS_UI,
                hall_capacity=int(hall_capacity_override),
                lab_capacity=int(lab_capacity_override),
                level_template_df=level_template_df,
                cp_timeout=int(cp_timeout),
            )
            progress.progress(100)
            best_fit = 0.0
            st.success("✅ OR-Tools Optimisation Complete!")

        st.session_state.last_result = {
            "schedule_df": schedule_df,
            "summary_df": summary_df,
            "conflicts_df": conflicts_df,
            "status": status,
            "hybrid": bool(use_hybrid),
        }

    st.balloons()
    st.success("✨ Schedule generated! View results in the tabs below.")

# ── Results ───────────────────────────────────────────────────────────────────
res = st.session_state.last_result
if res is not None:
    schedule_df = res["schedule_df"]
    summary_df  = res["summary_df"]
    conflicts_df = res["conflicts_df"]
    status = res["status"]

    tab1, tab2, tab3 = st.tabs(["📅 Timetable View", "📊 Schedule Summary", "💾 Export Data"])

    with tab1:
        create_visual_timetable(schedule_df)

    with tab2:
        create_visual_summary(summary_df, conflicts_df)

        # Solver status badge
        if status == cp_model.OPTIMAL:
            badge_text, badge_class = "OPTIMAL SOLUTION", "status-optimal"
        elif status == cp_model.FEASIBLE:
            badge_text, badge_class = "FEASIBLE SOLUTION", "status-feasible"
        else:
            badge_text, badge_class = "NO SOLUTION FOUND", "status-unsolved"

        st.markdown("---")
        c1, c2 = st.columns([1, 3])
        with c1:
            st.markdown(f"<div class='status-badge {badge_class}'>{badge_text}</div>", unsafe_allow_html=True)
        with c2:
            st.caption(f"Solver status: {badge_text}")

    with tab3:
        st.markdown("### 📤 Export Schedule")

        col1, col2 = st.columns(2)
        with col1:
            st.download_button(
                "📥 Download Excel (Complete)",
                data=export_full_workbook_bytes(schedule_df, summary_df, conflicts_df),
                file_name="University_Timetable_Complete.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                help="Includes styled grid view, per-doctor sheets, and raw data",
            )
        with col2:
            st.download_button(
                "📄 Download Excel (Simple)",
                data=df_to_excel_bytes({
                    "Schedule": schedule_df,
                    "Summary": summary_df,
                    "Conflicts": conflicts_df,
                }),
                file_name="University_Timetable_Simple.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                help="Basic Excel with raw data tables",
            )

        st.markdown("---")
        st.markdown("### 📊 Export Details")
        if schedule_df is not None and not schedule_df.empty:
            total_sessions = len(schedule_df)
            lectures = len(schedule_df[schedule_df["Type"] == "Lecture"])
            labs_count = len(schedule_df[schedule_df["Type"] == "Lab"])
            c1, c2, c3 = st.columns(3)
            c1.metric("Total Sessions", total_sessions)
            c2.metric("Lectures", lectures)
            c3.metric("Labs", labs_count)

        col3, col4 = st.columns(2)
        with col3:
            if st.button("🖨️ Print Timetable", use_container_width=True):
                st.info("Use your browser's print function (Ctrl+P) to print the timetable.")
        with col4:
            if st.button("🎉 Celebrate!", use_container_width=True):
                st.balloons()

else:
    st.info(
        "👈 Configure your courses and settings in the sidebar, then click "
        "'Run Scheduling Optimization' to generate your timetable."
    )
