"""
ui/styles.py
All CSS/HTML style strings injected via st.markdown().
"""

GLOBAL_CSS = """
<style>
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.15);
    }
    .main-header h1 {
        font-size: 2.5rem; font-weight: 800; margin: 0;
        background: linear-gradient(135deg, #ffffff 0%, #e6e6e6 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    }
    .main-header p { font-size: 1.1rem; opacity: 0.9; margin-top: 0.5rem; }

    .metric-card {
        background: white; border-radius: 15px; padding: 1.5rem;
        box-shadow: 0 6px 20px rgba(0,0,0,0.08);
        border-left: 5px solid #667eea;
        transition: transform 0.3s ease; height: 100%;
    }
    .metric-card:hover { transform: translateY(-5px); box-shadow: 0 12px 25px rgba(0,0,0,0.12); }
    .metric-card.lecture  { border-left-color: #3498db; }
    .metric-card.lab      { border-left-color: #2ecc71; }
    .metric-card.conflict { border-left-color: #e74c3c; }
    .metric-card.success  { border-left-color: #27ae60; }
    .metric-value { font-size: 2.5rem; font-weight: 800; color: #2c3e50; line-height: 1; margin: 0.5rem 0; }
    .metric-label { font-size: 0.9rem; color: #7f8c8d; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }

    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white; border: none; padding: 0.75rem 2rem;
        border-radius: 25px; font-weight: 600; transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4); }

    .stProgress > div > div > div { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }

    .stTabs [data-baseweb="tab-list"] { gap: 8px; background: transparent; }
    .stTabs [data-baseweb="tab"] {
        background: white; border-radius: 8px 8px 0 0; padding: 12px 24px;
        font-weight: 600; border: 1px solid #e0e0e0; border-bottom: none; transition: all 0.3s ease;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important; border-color: #667eea !important;
    }

    .status-badge { display: inline-block; padding: 8px 16px; border-radius: 20px; font-weight: 600; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.5px; }
    .status-optimal  { background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%); color: white; }
    .status-feasible { background: linear-gradient(135deg, #f39c12 0%, #e67e22 100%); color: white; }
    .status-unsolved { background: linear-gradient(135deg, #e74c3c 0%, #c0392b 100%); color: white; }

    .info-box    { background: linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%); border-left: 5px solid #2196f3; padding: 1rem 1.5rem; border-radius: 10px; margin: 1rem 0; }
    .warning-box { background: linear-gradient(135deg, #fff3e0 0%, #ffe0b2 100%); border-left: 5px solid #ff9800; padding: 1rem 1.5rem; border-radius: 10px; margin: 1rem 0; }
    .success-box { background: linear-gradient(135deg, #e8f5e9 0%, #c8e6c9 100%); border-left: 5px solid #4caf50; padding: 1rem 1.5rem; border-radius: 10px; margin: 1rem 0; }
</style>
"""

TIMETABLE_CSS = """
<style>
.modern-timetable { background: linear-gradient(135deg, #ffffff 0%, #f8f9fa 100%); border-radius: 16px; padding: 30px; box-shadow: 0 15px 35px rgba(0,0,0,0.1); margin-bottom: 30px; }
.modern-header h2 { font-size: 2.2rem; font-weight: 800; margin: 0; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.modern-header .subtitle { font-size: 1rem; color: #6c757d; margin-top: 10px; font-weight: 500; }
.modern-table { width: 100%; border-collapse: separate; border-spacing: 0; border-radius: 12px; overflow: hidden; box-shadow: 0 8px 25px rgba(0,0,0,0.08); }
.modern-table th, .modern-table td { border: 1px solid #e9ecef; padding: 12px 10px; text-align: center; vertical-align: top; font-size: 0.9em; }
.modern-table th { background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%); color: white; font-weight: 700; padding: 16px 12px; text-transform: uppercase; letter-spacing: 0.5px; }
.time-header { background: linear-gradient(135deg, #34495e 0%, #2c3e50 100%) !important; }
.day-header  { background: linear-gradient(135deg, #243B53 0%, #1F2D3D 100%) !important; color: white; font-weight: 700; }
.modern-item { margin: 6px 0; padding: 12px 10px; border-radius: 8px; text-align: left; font-size: 0.85em; border-left: 4px solid; box-shadow: 0 3px 10px rgba(0,0,0,0.08); }
.lecture-modern { background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); color: white; border-left-color: #1c6ea4; }
.lab-modern     { background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%); color: white; border-left-color: #1e8449; }
.section-modern { background: linear-gradient(135deg, #9b59b6 0%, #8e44ad 100%); color: white; border-left-color: #6c3483; }
.item-type  { font-weight: bold; font-size: 0.85em; display: block; margin-bottom: 4px; text-transform: uppercase; }
.course-name { font-weight: 700; display: block; margin-bottom: 3px; font-size: 0.95em; }
.instructor  { font-size: 0.82em; opacity: 0.95; display: block; margin-top: 4px; }
.room-info   { font-size: 0.8em; opacity: 0.9; font-style: italic; margin-top: 2px; }
.group-badge { font-size: 0.75em; background: rgba(255,255,255,0.25); padding: 2px 8px; border-radius: 12px; float: right; font-weight: bold; }
.empty-slot-modern { color: #95a5a6; font-style: italic; padding: 25px 0; font-size: 0.9em; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 8px; border: 2px dashed #dee2e6; }
.period-time { font-size: 0.75em; color: rgba(255,255,255,0.9); display: block; margin-top: 4px; }
.legend-modern { display: flex; justify-content: center; gap: 30px; flex-wrap: wrap; padding: 20px; background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 12px; margin-top: 30px; border: 1px solid #dee2e6; }
.legend-item-modern { display: flex; align-items: center; gap: 12px; font-size: 0.95em; color: #2c3e50; font-weight: 500; }
.legend-color-modern { width: 24px; height: 24px; border-radius: 6px; box-shadow: 0 3px 6px rgba(0,0,0,0.1); }
.legend-lecture-modern { background: linear-gradient(135deg, #3498db 0%, #2980b9 100%); }
.legend-lab-modern     { background: linear-gradient(135deg, #2ecc71 0%, #27ae60 100%); }
</style>
"""
