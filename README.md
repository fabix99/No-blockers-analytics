# 🏐 Volleyball Team Analytics System

A comprehensive data analysis system for volleyball team performance tracking and tactical analysis.

## 📁 Project Structure

```
volleyball_analytics_v2/
├── Dashboard/                    # Main dashboard application
│   ├── streamlit_dashboard.py   # Main Streamlit application
│   ├── match_analyzer.py         # Match analysis engine
│   ├── performance_tracker.py    # Performance tracking
│   ├── config.py                 # Configuration settings
│   ├── excel_data_loader.py      # Excel data loading
│   ├── event_tracker_loader.py   # Event tracking
│   ├── logging_config.py         # Logging setup
│   ├── streamlit_authentication.py  # Authentication
│   ├── charts/                   # Chart generation modules
│   │   ├── player_charts.py
│   │   ├── team_charts.py
│   │   └── utils.py
│   ├── ui/                       # UI components
│   │   ├── components.py
│   │   ├── insights.py
│   │   ├── player_analysis.py
│   │   ├── player_comparison.py
│   │   └── team_overview.py
│   ├── utils/                    # Utility functions
│   │   ├── formatters.py
│   │   ├── helpers.py
│   │   └── insights.py
│   └── tests/                    # Test suite
│       └── test_basic.py
├── templates/                    # Excel templates
│   ├── Match_Template.xlsx
│   └── match_tracking_template.xlsx
├── assets/                       # Static assets
│   └── images/                   # Images
│       ├── IMG_1377.JPG
│       └── team/                 # Player photos
└── requirements.txt              # Python dependencies
```

## 🚀 Quick Start

### Installation

```bash
pip install -r requirements.txt
```

### Launch Dashboard

Run the dashboard directly with Streamlit:

```bash
streamlit run Dashboard/streamlit_dashboard.py
```

Or from the project root:

```bash
cd Dashboard
streamlit run streamlit_dashboard.py
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

The dashboard is organized as a Python package. All modules are located in the `Dashboard/` directory:

- **Main Application**: `Dashboard/streamlit_dashboard.py`
- **Analysis Tools**: `Dashboard/match_analyzer.py`, `Dashboard/performance_tracker.py`
- **UI Components**: `Dashboard/ui/`
- **Charts**: `Dashboard/charts/`
- **Utilities**: `Dashboard/utils/`

## 📚 Documentation

For detailed documentation, see the README files in the project.

## 🏐 For Coaches

This system helps you:
- Track team performance over time
- Identify individual player strengths and weaknesses
- Make data-driven coaching decisions
- Monitor improvement areas
- Share insights with players and staff




