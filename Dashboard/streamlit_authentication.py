"""
Optional authentication module for Streamlit Cloud deployment.
Add password protection to your dashboard.

SETUP INSTRUCTIONS:
==================

1. In Streamlit Cloud: Settings → Secrets → Add:
   
   [authentication]
   password = "your-secure-password-here"

2. In streamlit_dashboard.py, add these lines after the imports:
   
   from streamlit_authentication import check_password
   if not check_password():
       st.stop()

3. Deploy to Streamlit Cloud - your dashboard will now be password protected!

LOCAL TESTING:
=============
For local testing, create a file at .streamlit/secrets.toml:
   
   [authentication]
   password = "test-password"

"""

import streamlit as st
from typing import Optional


def check_password() -> bool:
    """Check if user entered correct password from Streamlit secrets.
    
    Returns:
        bool: True if password is correct or no password is configured,
              False if password is incorrect or not yet entered
    """
    # Check if authentication is configured
    password_from_secrets = _get_password_from_secrets()
    
    if not password_from_secrets:
        # No password configured, allow access
        return True
    
    def password_entered():
        """Callback when password is submitted."""
        if st.session_state.get("password") == password_from_secrets:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False
    
    # First run or no correct password yet
    if "password_correct" not in st.session_state:
        _show_login_page(password_entered)
        return False
    
    # Wrong password entered
    if not st.session_state["password_correct"]:
        _show_login_page(password_entered, show_error=True)
        return False
    
    # Correct password
    return True


def _get_password_from_secrets() -> Optional[str]:
    """Get password from Streamlit secrets.
    
    Returns:
        Password string if configured, None otherwise
    """
    try:
        return st.secrets.get("authentication", {}).get("password", "")
    except Exception:
        return None


def _show_login_page(on_submit_callback, show_error: bool = False):
    """Display the login page.
    
    Args:
        on_submit_callback: Function to call when password is submitted
        show_error: Whether to show an error message
    """
    # Custom styling for login page
    st.markdown("""
    <style>
        .login-container {
            max-width: 400px;
            margin: 100px auto;
            padding: 40px;
            background: linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%);
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(5, 13, 118, 0.15);
            border: 2px solid rgba(5, 13, 118, 0.1);
        }
        .login-title {
            color: #050d76;
            font-size: 2rem;
            font-weight: 700;
            text-align: center;
            margin-bottom: 10px;
        }
        .login-subtitle {
            color: #666;
            text-align: center;
            margin-bottom: 30px;
        }
    </style>
    """, unsafe_allow_html=True)
    
    # Center content
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("# 🏐 Volleyball Analytics")
        st.markdown("### Please enter the password to access the dashboard")
        
        st.text_input(
            "Password", 
            type="password", 
            on_change=on_submit_callback, 
            key="password",
            help="Enter the password provided by your team administrator"
        )
        
        if show_error:
            st.error("❌ Password incorrect. Please try again.")
        
        st.markdown("---")
        st.markdown(
            "<small style='color: #888;'>Contact your team administrator if you don't have the password.</small>",
            unsafe_allow_html=True
        )


def logout():
    """Log the user out by clearing the session state."""
    if "password_correct" in st.session_state:
        del st.session_state["password_correct"]
    st.rerun()


# Add a logout button helper for use in the dashboard
def add_logout_button(sidebar: bool = True):
    """Add a logout button to the dashboard.
    
    Args:
        sidebar: If True, adds button to sidebar. Otherwise, adds to main area.
    """
    container = st.sidebar if sidebar else st
    
    if container.button("🚪 Logout", help="Sign out of the dashboard"):
        logout()

