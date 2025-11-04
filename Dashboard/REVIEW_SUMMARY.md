# Dashboard Code Review - Quick Summary

## Critical Issues Found

### 1. ⚠️ BLOCKING UI ISSUE - `time.sleep()` in Streamlit
**Location:** `speech_capture_app.py:594-595`
```python
if st.session_state.is_recording:
    time.sleep(1)  # Refresh every second to show status updates
    st.rerun()
```

**Problem:** `time.sleep()` blocks the entire Streamlit UI thread, making the app unresponsive.

**Fix:**
```python
if st.session_state.is_recording:
    # Use st.empty() container and auto-refresh
    status_container = st.empty()
    status_container.info("🎤 Recording...")
    time.sleep(0.1)  # Minimal delay, or better: use st.rerun() with a counter
    st.rerun()
```

**Better Solution:** Use Streamlit's built-in auto-refresh or `st.empty()` containers.

---

### 2. 🔒 SECURITY - File Upload Without Validation
**Location:** `streamlit_dashboard.py:976-977`
```python
with open("temp_match_data.xlsx", "wb") as f:
    f.write(uploaded_file.getbuffer())
```

**Problems:**
- No file size validation
- No file type validation (only checks extension)
- Files written to current directory (potential security issue)
- No cleanup of temporary files

**Fix:**
```python
import tempfile
import os
from pathlib import Path

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB

def save_uploaded_file(uploaded_file):
    if uploaded_file.size > MAX_FILE_SIZE:
        raise ValueError("File too large (max 10MB)")
    
    # Use tempfile for secure temporary file handling
    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, f"match_data_{uuid.uuid4()}.xlsx")
    
    with open(temp_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return temp_path
```

---

### 3. 🔒 SECURITY - Path Traversal Vulnerability
**Location:** `speech_capture_app.py:690`
```python
template_path = st.text_input("Template", value="../templates/Match_Template.xlsx")
```

**Problem:** User input used directly in file paths without sanitization.

**Fix:**
```python
from pathlib import Path

def sanitize_template_path(user_input):
    """Sanitize and validate template path"""
    base_dir = Path(__file__).parent.parent / "templates"
    user_path = Path(user_input)
    
    # Resolve relative paths
    if not user_path.is_absolute():
        resolved = (base_dir / user_path).resolve()
    else:
        resolved = Path(user_path).resolve()
    
    # Ensure path is within allowed directory
    if not str(resolved).startswith(str(base_dir.resolve())):
        raise ValueError("Invalid template path")
    
    return resolved
```

---

### 4. ❌ ERROR HANDLING - Silent Failures
**Location:** `excel_data_loader.py:85, 99, 129`
```python
except:
    pass  # Silent failure!
```

**Problem:** Errors are silently swallowed, making debugging difficult.

**Fix:**
```python
import logging

logger = logging.getLogger(__name__)

try:
    # operation
except ValueError as e:
    logger.warning(f"Invalid value: {e}")
    # Handle appropriately
except Exception as e:
    logger.error(f"Unexpected error: {e}", exc_info=True)
    raise  # Or handle appropriately
```

---

### 5. 🐌 PERFORMANCE - No Caching
**Location:** Multiple locations in `streamlit_dashboard.py`

**Problem:** Expensive calculations repeated on every rerun.

**Fix:**
```python
@st.cache_data
def calculate_team_metrics_cached(analyzer):
    """Cache team metrics calculation"""
    return analyzer.calculate_team_metrics()

@st.cache_data
def load_player_image_cached(player_name, images_dir):
    """Cache player image loading"""
    return load_player_image(player_name, images_dir)
```

---

### 6. 📁 CODE ORGANIZATION - Massive File
**Location:** `streamlit_dashboard.py` (3,976 lines)

**Problem:** Single file contains UI, data processing, validation, and chart generation.

**Recommendation:** Split into:
- `ui/team_overview.py` (~300 lines)
- `ui/player_analysis.py` (~300 lines)
- `charts/team_charts.py` (~400 lines)
- `utils/validators.py` (~100 lines)
- `config/constants.py` (~100 lines)
- `streamlit_dashboard.py` (~200 lines - main entry point only)

---

### 7. 🔧 BUG - Incorrect Rotation Distribution
**Location:** `excel_data_loader.py:157-192`

**Problem:** Actions distributed across rotations using modulo (`i % 6 + 1`), which doesn't reflect actual match rotations.

**Current Code:**
```python
for i, _ in enumerate(range(attack_kills)):
    rotation = (i % 6) + 1  # This is arbitrary!
    data.append({...})
```

**Issue:** This creates artificial rotation assignments that may not match actual match data.

**Recommendation:** If rotation data isn't available, either:
1. Store rotation as None/NaN
2. Document that rotations are estimated
3. Provide UI to manually assign rotations

---

### 8. ⚠️ MEMORY LEAK - Session State Accumulation
**Location:** Multiple files

**Problem:** Session state accumulates data without cleanup, potentially causing memory issues.

**Fix:**
```python
def clear_session_state():
    """Clear session state when loading new match"""
    keys_to_keep = ['match_loaded', 'analyzer', 'loader']
    keys_to_remove = [k for k in st.session_state.keys() if k not in keys_to_keep]
    for key in keys_to_remove:
        del st.session_state[key]
```

---

## High-Priority Fixes (Do These First)

1. ✅ Fix `time.sleep()` blocking issue
2. ✅ Add file size validation
3. ✅ Implement path sanitization
4. ✅ Replace silent exceptions with proper error handling
5. ✅ Add caching for expensive operations

## Medium-Priority Fixes (Next Sprint)

1. ✅ Refactor large functions
2. ✅ Extract configuration to separate file
3. ✅ Add type hints
4. ✅ Implement proper logging
5. ✅ Add session state cleanup

## Code Quality Metrics

- **Lines of Code:** ~8,000+ across all files
- **Largest File:** 3,976 lines (`streamlit_dashboard.py`)
- **Function Complexity:** Several functions > 200 lines
- **Test Coverage:** 0% (no tests found)
- **Type Hints:** ~10% coverage
- **Docstring Coverage:** ~60% coverage

## Positive Aspects

✅ Well-structured data analysis classes  
✅ Beautiful UI/UX design  
✅ Comprehensive feature set  
✅ Good separation of concerns between data loading and analysis  
✅ Professional visualizations  

## Next Steps

1. Review this document with the team
2. Prioritize fixes based on production impact
3. Create tickets for each issue
4. Start with critical security fixes
5. Plan refactoring sprint for code organization

