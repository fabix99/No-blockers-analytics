"""
Comprehensive help guide and tutorial utilities
"""
import streamlit as st
from typing import Dict, Any


def display_help_guide() -> None:
    """MEDIUM PRIORITY 11: Display comprehensive help guide."""
    st.markdown("# 📚 Dashboard Help Guide")
    
    # Table of contents
    st.markdown("## 📋 Table of Contents")
    toc_items = [
        ("Getting Started", "getting_started"),
        ("Understanding KPIs", "understanding_kpis"),
        ("Navigation", "navigation"),
        ("Exporting Data", "exporting"),
        ("FAQ", "faq")
    ]
    
    for item, anchor in toc_items:
        st.markdown(f"- [{item}](#{anchor})")
    
    st.markdown("---")
    
    # Getting Started
    st.markdown("## 🚀 Getting Started {#getting_started}")
    st.markdown("""
    ### Uploading Match Data
    1. Click on the file uploader at the bottom of the page
    2. Select your match data Excel file (must be in event tracker format)
    3. Wait for the data to load (you'll see a progress indicator)
    4. Once loaded, navigate between views using the sidebar
    
    ### Required File Format
    - Your Excel file must contain two sheets:
      - **Individual Events**: Event-by-event tracking of player actions
      - **Team Events**: Point-by-point team statistics
    - See the template file for exact column requirements
    """)
    
    # Understanding KPIs
    st.markdown("## 📊 Understanding KPIs {#understanding_kpis}")
    st.markdown("""
    ### Key Performance Indicators Explained
    
    **Attack Kill %**: Percentage of attack attempts that result in kills
    - Formula: Attack Kills / Total Attack Attempts
    - Target: 35-50% (optimal: 42%)
    
    **Serve In-Rate**: Percentage of serves that are in play (ace or good serve)
    - Formula: (Service Aces + Good Serves) / Total Serve Attempts
    - Target: 85-95% (optimal: 90%)
    
    **Reception Quality**: Percentage of receptions that are good quality
    - Formula: Good Receptions / Total Reception Attempts
    - Good receptions include: perfect, good, and 0.5 credit for poor
    - Target: 70-85% (optimal: 75%)
    
    **Block Kill %**: Percentage of block attempts that result in kills
    - Formula: Block Kills / Total Block Attempts
    - Target: 5-15% (optimal: 10%)
    
    **Dig Rate**: Percentage of dig attempts that are successful
    - Formula: Good Digs / Total Dig Attempts
    - Target: 65-80% (optimal: 70%)
    
    **Attack Efficiency**: Net attack performance accounting for errors
    - Formula: (Attack Kills - Attack Errors) / Total Attack Attempts
    - Target: 25-35% (optimal: 30%)
    """)
    
    # Navigation
    st.markdown("## 🧭 Navigation {#navigation}")
    st.markdown("""
    ### Three Main Views
    
    1. **Team Overview**: High-level team performance metrics and insights
       - View overall KPIs
       - See breakdowns by position, set, and rotation
       - Get tactical recommendations
    
    2. **Player Analysis**: Detailed individual player performance
       - Select a player from the dropdown
       - View position-specific KPIs
       - See player-specific recommendations
       - Analyze performance trends by set
    
    3. **Player Comparison**: Compare players side-by-side
       - Filter by position
       - Sort by any metric
       - See statistical significance indicators
       - View complementarity analysis
    
    ### Quick Navigation
    - Use the sidebar dropdown to switch between views
    - Click navigation buttons at the bottom of each view
    """)
    
    # Exporting
    st.markdown("## 📥 Exporting Data {#exporting}")
    st.markdown("""
    ### Export Options
    - **Excel**: Export to Excel format with multiple sheets
    
    ### Where to Find Export
    - Team Overview: Export section at the bottom
    - Player Analysis: Export section after player insights
    - Player Comparison: Export section at the bottom
    - Sidebar: Quick export button for general match data
    """)
    
    # FAQ
    st.markdown("## ❓ Frequently Asked Questions {#faq}")
    
    with st.expander("Why is my data completeness showing as less than 100%?"):
        st.markdown("""
        Data completeness measures how many events in your file are valid. 
        Common reasons for low completeness:
        - Missing 'Point Won' values in Team Events
        - Invalid outcome values for actions
        - Missing required columns
        - Invalid action types
        
        Check the detailed breakdown for specific issues.
        """)
    
    with st.expander("What do the confidence intervals mean?"):
        st.markdown("""
        Confidence intervals (95% CI) show the range where the true value likely falls.
        For example, if Attack Kill % shows 42.0% (95% CI: 38.5% - 45.5%), 
        this means we're 95% confident the true value is between 38.5% and 45.5%.
        
        Smaller sample sizes result in wider confidence intervals.
        """)
    
    with st.expander("How do I interpret the reliability indicator?"):
        st.markdown("""
        Reliability indicates how confident we can be in the metric:
        - **High**: 50+ observations - very reliable
        - **Medium**: 20-49 observations - reasonably reliable
        - **Low**: <20 observations - use with caution
        
        Metrics with low reliability may not be statistically significant.
        """)
    
    with st.expander("What is complementarity analysis?"):
        st.markdown("""
        Complementarity analysis identifies which position combinations work well together.
        It's based on balancing strengths and weaknesses between positions.
        
        Higher complementarity scores indicate better position pairings.
        Use this to make lineup decisions.
        """)
    
    with st.expander("How do I filter players in the comparison view?"):
        st.markdown("""
        Use the filters at the top of the Player Comparison view:
        - **Position Filter**: Select a specific position or "All"
        - **Sort By**: Choose which metric to sort by
        - **Order**: Select ascending or descending
        - **Min Actions**: Filter by minimum playing time
        
        You can also use the multi-select to choose specific players.
        """)
    
    st.markdown("---")
    st.info("💡 **Need more help?** Check the validation errors section for specific issues with your data file.")


def display_tutorial_modal() -> None:
    """Display interactive tutorial modal."""
    st.markdown("""
    <div id="tutorial-modal" style="display: none;">
        <h2>Welcome to Volleyball Analytics Dashboard!</h2>
        <p>This interactive tutorial will guide you through the dashboard features.</p>
        <button onclick="startTutorial()">Start Tutorial</button>
    </div>
    <script>
    function startTutorial() {
        alert("Tutorial will be implemented in future version");
    }
    </script>
    """, unsafe_allow_html=True)

