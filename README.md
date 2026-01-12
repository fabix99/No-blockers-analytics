# 🏐 Volleyball Team Analytics System

A comprehensive data analysis system for volleyball team performance tracking, tactical analysis, and live event tracking.

## 📁 Project Structure

```
volleyball_analytics_v2/
├── Dashboard/                    # Main dashboard application
│   ├── streamlit_dashboard.py   # Main Streamlit application
│   ├── live_event_tracker.py    # Live match event tracking
│   ├── match_analyzer.py        # Match analysis engine
│   ├── performance_tracker.py   # Performance tracking
│   ├── config.py                # Configuration settings
│   ├── event_tracker_loader.py  # Event data loading
│   ├── streamlit_authentication.py  # Password protection module
│   ├── charts/                  # Chart generation modules
│   │   ├── player_charts.py
│   │   ├── team_charts.py
│   │   └── utils.py
│   ├── ui/                      # UI components
│   │   ├── components.py
│   │   ├── insights.py
│   │   ├── player_analysis.py
│   │   ├── player_comparison.py
│   │   ├── team_overview.py
│   │   └── theme.py            # Centralized styling
│   ├── services/                # Business logic layer
│   │   ├── analytics_service.py
│   │   └── session_manager.py
│   ├── utils/                   # Utility functions
│   │   ├── formatters.py
│   │   ├── helpers.py
│   │   └── export_utils.py
│   └── tests/                   # Test suite
│       └── test_basic.py
├── templates/                   # Excel templates
│   ├── Match_Template.xlsx
│   ├── match_tracking_template.xlsx
│   └── Event_Tracker_Template.xlsx
├── data/                        # Data files
│   └── examples/                # Example match data
├── assets/                      # Static assets
│   └── images/                  # Player photos & logos
├── docs/                        # Documentation
│   ├── DEPLOYMENT_GUIDE.md     # Streamlit Cloud deployment
│   └── GITHUB_SETUP.md         # GitHub & Git setup
└── requirements.txt             # Python dependencies
```

## 🚀 Quick Start

### Installation

```bash
cd volleyball_analytics_v2
pip install -r requirements.txt
```

### Launch Dashboard

```bash
streamlit run Dashboard/streamlit_dashboard.py
```

### Launch Live Event Tracker

```bash
streamlit run Dashboard/live_event_tracker.py
```

## 📊 Features

### Core Analytics Dashboard
- **Team Overview**: Match-level performance metrics and KPIs
- **Player Analysis**: Individual player statistics and trends
- **Player Comparison**: Head-to-head comparisons between players
- **Performance Insights**: AI-generated tactical recommendations

### Live Event Tracker 🆕
- **Real-time Tracking**: Record events during live matches
- **Court Visualization**: Visual representation of player positions
- **Rotation Management**: Automatic rotation tracking
- **Libero Substitutions**: Track libero in/out swaps
- **Set-by-Set Scoring**: Live score management
- **Export to Excel**: Download match data for later analysis

### Advanced Features
- **Service Layer**: Clean separation of business logic
- **Session Management**: Persistent state across interactions
- **Centralized Theming**: Consistent brand styling (No Blockers blue)
- **Password Protection**: Optional authentication for deployments

## 📝 Usage

### Match Data Collection

1. **Using Templates**: Download templates from `templates/` folder
2. **Live Tracking**: Use the Live Event Tracker during matches
3. **Upload Data**: Import Excel files into the dashboard

### Analysis Workflow

1. **Upload Match Data**: Excel file with match events
2. **View Team Overview**: Overall performance metrics
3. **Analyze Players**: Individual performance breakdowns
4. **Compare Players**: Side-by-side comparisons
5. **Get Insights**: Automated recommendations

## 🎨 Brand Colors

The dashboard uses the official No Blockers team colors:
- **Primary Blue**: `#050d76`
- **Light Blue**: `#dbe7ff`
- **Red Accent**: `#e21b39`
- **Light Gray**: `#e9e9e9`

## 🔒 Authentication

For password-protected deployments, see `Dashboard/streamlit_authentication.py`.

## 🚀 Deployment

See `docs/DEPLOYMENT_GUIDE.md` for complete Streamlit Cloud deployment instructions.

### Quick Deploy

1. Push to GitHub (private repository)
2. Connect to Streamlit Cloud
3. Set main file: `Dashboard/streamlit_dashboard.py`
4. Deploy!

## 🧪 Running Tests

```bash
cd Dashboard
pytest tests/ -v
```

## 🏐 For Coaches

This system helps you:
- Track team performance over time
- Identify individual player strengths and weaknesses
- Make data-driven coaching decisions
- Monitor improvement areas
- Share insights with players and staff
- Track events live during matches

## 📚 Documentation

- **Deployment**: See `docs/DEPLOYMENT_GUIDE.md`
- **GitHub Setup**: See `docs/GITHUB_SETUP.md`
- **Rotation Logic**: See `Dashboard/ROTATION_SYSTEM_DETAILED.md`
- **Point Outcomes**: See `Dashboard/POINT_OUTCOME_LOGIC.md`

## 🔧 Development

### Code Organization
- **UI Components**: `Dashboard/ui/`
- **Chart Generation**: `Dashboard/charts/`
- **Business Logic**: `Dashboard/services/`
- **Utilities**: `Dashboard/utils/`

### Key Patterns
- Service layer for analytics (`AnalyticsService`)
- Session state management (`SessionStateManager`)
- Centralized styling (`ui/theme.py`)
- Helper function extraction for maintainability

## 📦 Dependencies

Core dependencies (see `requirements.txt`):
- `streamlit>=1.28.0` - Dashboard framework
- `pandas>=1.5.0` - Data manipulation
- `plotly>=5.0.0` - Interactive charts
- `openpyxl>=3.0.0` - Excel file handling
- `pillow>=8.0.0` - Image processing

## 📞 Support

- [Streamlit Documentation](https://docs.streamlit.io/)
- [Plotly Documentation](https://plotly.com/python/)

---

**Version:** 2.0  
**Last Updated:** January 2025
