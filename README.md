# 🗓️ University Timetable Smart Dashboard

A Streamlit web application that generates optimized university timetables using a **hybrid Greedy + CP-SAT (OR-Tools) + Genetic Algorithm** approach.

---

## ✨ Features

- **Hybrid Scheduling**: Greedy heuristic → CP-SAT constraint solver → Genetic Algorithm wrapper for best results
- **Smart Conflict Detection**: Instructor availability, hall/lab double-booking, days-off constraints
- **Level Templates**: Optional `LevelSchedule` sheet to enforce per-level time restrictions
- **Special Course Handling**: Work-based and project courses routed to matching lab rooms
- **Rich Export**: Styled Excel workbooks with dashboard grid, per-doctor sheets, and raw tables
- **Modern UI**: Gradient cards, interactive timetable grid, progress indicators

---

## 🚀 Quick Start

### 1. Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/timetable-scheduler.git
cd timetable-scheduler
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Run the app
```bash
streamlit run app.py
```

---

## 📁 Project Structure

```
timetable-scheduler/
│
├── app.py                      # Main Streamlit entry point
│
├── utils/
│   ├── __init__.py
│   ├── helpers.py              # Type-safe conversions, course-type helpers
│   ├── data_loader.py          # Excel sheet loading & column normalisation
│   └── constants.py            # Days, periods, time mappings
│
├── scheduler/
│   ├── __init__.py
│   ├── cp_solver.py            # Greedy + CP-SAT core engine
│   └── ga_hybrid.py            # Genetic Algorithm wrapper
│
├── ui/
│   ├── __init__.py
│   ├── styles.py               # CSS strings (global + timetable)
│   ├── components.py           # Visual timetable grid & summary cards
│   └── sidebar.py              # Sidebar, course selection, per-course config
│
├── export/
│   ├── __init__.py
│   └── excel_export.py         # Styled Excel workbook generation
│
├── requirements.txt
├── .gitignore
└── README.md
```

---

## 📊 Excel Input Format

Upload an `.xlsx` file with the following sheets (column names are flexible — the app normalises them automatically):

| Sheet | Required Columns |
|-------|-----------------|
| `Courses` | `course_code`, `course_name`, `level`, `department` |
| `Doctors` | `id`, `name`, `department`, `days_off` |
| `Assistants` | `id`, `name`, `department`, `days_off` |
| `Halls` | `id`, `name`, `capacity`, `building` |
| `Labs` | `id`, `name`, `capacity`, `building` |
| `LevelSchedule` *(optional)* | `level`, `day`, `period` |

**`days_off`** accepts comma-separated day names, e.g. `Saturday, Friday`.

---

## ⚙️ Configuration

All settings are available in the sidebar:

| Setting | Description |
|---------|-------------|
| Levels | Which academic years to schedule |
| Max courses per level | Cap on auto-selected courses |
| Hall / Lab capacity | Fallback when not in the data |
| Enable Hybrid | GA + OR-Tools (slower but better) or OR-Tools only |
| GA Generations | Evolutionary iterations |
| GA Population | Candidate solutions per generation |
| GA Elite | Top individuals preserved unchanged |
| CP Timeout | Seconds allowed per OR-Tools solve |

---

## 🧠 Algorithm Overview

```
Upload Excel → Load & Normalise Data
        ↓
Course Selection + Instructor Assignment (UI)
        ↓
┌─────────────────────────────────┐
│  Greedy Pass                    │  Fill easiest slots first
│  CP-SAT Pass (OR-Tools)         │  Solve remaining groups with constraints
└─────────────────────────────────┘
        ↓  (if Hybrid enabled)
┌─────────────────────────────────┐
│  Genetic Algorithm              │  Evolve course orderings
│  → evaluate each via CP solver  │
│  → select, crossover, mutate    │
│  → keep best result             │
└─────────────────────────────────┘
        ↓
Export (styled Excel / simple Excel)
```

---

## 📦 Dependencies

- [Streamlit](https://streamlit.io/) — UI framework
- [OR-Tools](https://developers.google.com/optimization) — Constraint programming solver
- [pandas](https://pandas.pydata.org/) — Data manipulation
- [openpyxl](https://openpyxl.readthedocs.io/) — Excel export

---

## 🤝 Contributing

Pull requests are welcome. For major changes, please open an issue first.

---

## 📄 License

MIT
