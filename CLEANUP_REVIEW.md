# File Cleanup Review for GitHub Upload

## ✅ FILES TO KEEP (Essential for Dashboard)

### Core Application Files
- `Dashboard/streamlit_dashboard.py` - Main dashboard
- `Dashboard/match_analyzer.py` - Match analysis logic
- `Dashboard/performance_tracker.py` - Performance tracking
- `Dashboard/excel_data_loader.py` - Data loading
- `Dashboard/config.py` - Configuration
- `Dashboard/logging_config.py` - Logging setup
- `Dashboard/streamlit_authentication.py` - Optional authentication

### UI Components
- `Dashboard/ui/*.py` - All UI modules
- `Dashboard/charts/*.py` - All chart modules
- `Dashboard/utils/*.py` - All utility modules

### Configuration Files
- `.streamlit/config.toml` - Streamlit config
- `.gitignore` - Git ignore rules
- `requirements.txt` - Python dependencies

### Templates (Users will upload these)
- `templates/Match_Template.xlsx` - Match template
- `templates/match_tracking_template.xlsx` - Tracking template
- `data/replays/Match_Template.xlsx` - Another template

### Assets
- `assets/images/` - Player photos (used by dashboard)

### Documentation
- `README.md` - Main documentation
- `DEPLOYMENT_GUIDE.md` - Deployment instructions

### Tests (Optional but useful)
- `Dashboard/tests/` - Test files

---

## ❌ FILES TO DELETE (Not needed for deployment)

### Temporary Files
- `Dashboard/temp_match_converted.xlsx`
- `Dashboard/temp_match_data.xlsx`
- `temp_match_converted.xlsx` (root)
- `temp_match_data.xlsx` (root)

### Personal/Sensitive Data Files
- `data/examples/Osta Berchem 2.xlsx` - Actual match data (sensitive)
- `data/examples/Osta Berchem 2 Test.xlsx` - Test match data (sensitive)
- `data/examples/Osta Berchem 2.numbers` - Match data (sensitive)
- `data/replays/Osta Berchem 2.mov` - Video file (1.2MB, not needed)

### Development Documentation (Internal only)
- `Dashboard/CODE_QUALITY_ASSESSMENT.md`
- `Dashboard/CODE_REVIEW.md`
- `Dashboard/ENHANCEMENTS_COMPLETE.md`
- `Dashboard/FIXES_COMPLETED.md`
- `Dashboard/IMPLEMENTATION_STATUS.md`
- `Dashboard/MAINTAINABILITY_IMPROVEMENT_PLAN.md`
- `Dashboard/REVIEW_SUMMARY.md`
- `Dashboard/TEAM_OVERVIEW_REVIEW.md`
- `GITHUB_PUSH_COMMANDS.md` - Temporary guide

### Unused Code
- `Dashboard/speech_capture_app.py` - Not imported/used by dashboard

---

## 📊 Summary

**Total files to delete:** ~15 files
**Total size to save:** ~1.3MB (mostly video file)
**Files to keep:** All Python code, configs, templates, assets, main docs

---

## 🎯 Recommendations

1. **Delete all temporary files** - They're regenerated on each run
2. **Delete personal match data** - Users will upload their own data
3. **Delete development docs** - Internal only, not needed for deployment
4. **Delete unused code** - speech_capture_app.py is not used
5. **Keep templates** - Users need these to structure their data
6. **Keep assets** - Player photos are used by the dashboard

