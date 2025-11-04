# 🏐 Volleyball Team Analytics System

A comprehensive data analysis system for volleyball team performance tracking and tactical analysis.

## 📁 Project Structure

```
volleyball_analytics/
├── src/                          # Source code
│   ├── dashboard/                # Dashboard application
│   │   ├── streamlit_dashboard.py
│   │   └── launch_dashboard.py
│   ├── analysis/                 # Analysis tools
│   │   ├── match_analyzer.py
│   │   └── performance_tracker.py
│   ├── data/                     # Data handling
│   │   ├── collectors/           # Data collection
│   │   │   └── match_data_collector.py
│   │   └── loaders/              # Data loading
│   │       └── excel_data_loader.py
│   └── utils/                    # Utilities
│       ├── generate_dummy_data.py
│       └── create_match_template.py
├── templates/                    # Excel templates
│   ├── Match_Template.xlsx
│   └── match_tracking_template.xlsx
├── data/                         # Data files
│   ├── examples/                 # Example match data
│   └── replays/                  # Video replays
├── assets/                       # Static assets
│   └── images/                   # Images
│       ├── IMG_1377.JPG
│       └── team/                 # Player photos
├── docs/                         # Documentation
│   ├── README.md                 # Detailed docs (moved from root)
│   ├── DASHBOARD_README.md
│   ├── KPI_SUMMARY.md
│   └── KPI_IMPLEMENTATION_STATUS.md
├── scripts/                      # Utility scripts
│   └── demo.py
└── requirements.txt              # Python dependencies
```

## 🚀 Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Launch Dashboard

```bash
python src/dashboard/launch_dashboard.py
```

Or directly with Streamlit:

```bash
streamlit run src/dashboard/streamlit_dashboard.py
```

### Run Demo

```bash
python scripts/demo.py
```

## 📊 Features

### Phase 1: Foundation
- **Match Data Collection**: Excel templates for real-time tracking
- **Data Processing**: Python scripts for analysis and trend tracking
- **Basic Analytics**: Performance metrics and rotation efficiency

### Phase 2: Advanced Analytics
- **Visualization Dashboards**: Interactive Streamlit dashboard
- **Team & Player Analysis**: Comprehensive performance breakdowns
- **Comparison Tools**: Player and team comparison charts

## 📝 Usage

1. **Data Collection**: Use the match tracking template (`templates/Match_Template.xlsx`) during games
2. **Analysis**: Upload your match data to the dashboard
3. **Visualization**: Explore team and player performance metrics
4. **Insights**: Use the automated insights to improve team tactics

## 🔧 Development

### Generate Match Template

```bash
python src/utils/create_match_template.py
```

### Generate Sample Data

```python
from src.utils.generate_dummy_data import generate_sample_analysis
filename, match_df = generate_sample_analysis()
```

## 📚 Documentation

- **Main Documentation**: See `docs/README.md`
- **Dashboard Guide**: See `docs/DASHBOARD_README.md`
- **KPI Reference**: See `docs/KPI_SUMMARY.md`

## 🏐 For Coaches

This system helps you:
- Track team performance over time
- Identify individual player strengths and weaknesses
- Make data-driven coaching decisions
- Monitor improvement areas
- Share insights with players and staff




