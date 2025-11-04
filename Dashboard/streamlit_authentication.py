"""
Optional authentication module for Streamlit Cloud deployment.
Add password protection to your dashboard.

To use:
1. In Streamlit Cloud: Settings → Secrets → Add:
   [authentication]
   password = "your-secure-password-here"

2. In streamlit_dashboard.py, add at the top:
   from streamlit_authentication import check_password
   if not check_password():
       st.stop()
"""

import streamlit as st


def check_password():
    """Check if user entered correct password from Streamlit secrets.
    
    Returns:
        bool: True if password is correct, False otherwise
    """
    def password_entered():
        """Check if the password entered by the user is correct."""
        password_from_secrets = st.secrets.get("authentication", {}).get("password", "")
        if st.session_state["password"] == password_from_secrets:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store password
        else:
            st.session_state["password_correct"] = False
    
    # First run: show password input
    if "password_correct" not in st.session_state:
        st.title("🔒 Volleyball Analytics Dashboard")
        st.markdown("### Please enter the password to access the dashboard")
        st.text_input(
            "Password", 
            type="password", 
            on_change=password_entered, 
            key="password",
            help="Enter the password provided by your team administrator"
        )
        return False
    
    # Wrong password: show error
    elif not st.session_state["password_correct"]:
        st.title("🔒 Volleyball Analytics Dashboard")
        st.markdown("### Please enter the password to access the dashboard")
        st.text_input(
            "Password", 
            type="password", 
            on_change=password_entered, 
            key="password"
        )
        st.error("❌ Password incorrect. Please try again.")
        return False
    
    # Correct password: allow access
    else:
        return True

