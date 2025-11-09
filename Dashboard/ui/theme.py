"""
Theme and styling configuration for the Streamlit Dashboard.
Extracted from streamlit_dashboard.py for better maintainability.
"""
import streamlit as st
from typing import Dict, Any

# Brand colors
BRAND_COLORS = {
    'primary': '#050d76',  # Dark blue
    'primary_dark': '#050d76',  # Dark blue (same as primary)
    'primary_light': '#dbe7ff',  # Light blue
    'red': '#e21b39',  # Red
    'light_gray': '#e9e9e9',  # Light gray
    'black': '#000000',  # Black
    'white': '#ffffff',  # White
    'text': '#2C3E50',  # Text color (kept for readability)
    'success': '#06A77D',  # Success green (kept)
    'warning': '#F18F01',  # Warning orange (kept)
    'error': '#e21b39',  # Error red (using brand red)
    'info': '#dbe7ff',  # Info light blue (using brand light blue)
    'background': '#FAFAFA',  # Background (kept)
}

# CSS styling
DASHBOARD_CSS = """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=Poppins:wght@300;400;500;600;700;800;900&display=swap');
    
    /* Main App Background - Very Light Gray (easier on eyes) */
    .stApp {
        background: #FAFAFA;
        background-attachment: fixed;
    }
    
    /* Main Content Area - Clean White */
    .main .block-container {
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.98) 0%, rgba(250, 250, 255, 0.98) 100%);
        border-radius: 16px;
        padding: 3rem 2rem;
        box-shadow: 0 20px 60px rgba(5, 13, 118, 0.3), inset 0 0 100px rgba(5, 13, 118, 0.05);
        border: 2px solid rgba(5, 13, 118, 0.3);
        margin-top: 2rem;
        margin-bottom: 2rem;
    }
    
    /* Headers - No Blockers Deep Blue - Enhanced Layout */
    .main-header {
        text-align: left;
        margin-bottom: 0;
        font-family: 'Poppins', sans-serif;
        line-height: 1.1;
        padding: 0;
    }
    
    .main-header .brand-name {
        display: block;
        font-size: 4rem;
        font-weight: 900;
        background: linear-gradient(135deg, #050d76 0%, #050d76 50%, #dbe7ff 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: -2px;
        margin-bottom: 0.2rem;
        animation: headerGlow 3s ease-in-out infinite;
    }
    
    .main-header .subtitle {
        display: block;
        font-size: 1.8rem;
        font-weight: 600;
        background: linear-gradient(135deg, #050d76 0%, #050d76 80%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        letter-spacing: 1px;
        margin-top: 0;
        opacity: 0.9;
    }
    
    .tagline-header {
        text-align: right;
        font-size: 1rem;
        font-weight: 600;
        color: #050d76;
        font-family: 'Poppins', sans-serif;
        letter-spacing: 3px;
        text-transform: uppercase;
        line-height: 1.6;
        opacity: 0.85;
        padding-top: 1rem;
    }
    
    /* Player image centering */
    div[data-testid="column"]:nth-of-type(1) img {
        display: block;
        margin: 10px auto;
    }
    
    div[data-testid="column"]:nth-of-type(1) {
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    /* Center images in player cards */
    div[style*="border: 2px solid #050d76"] div[data-testid="stImage"],
    div[style*="border: 2px solid #050d76"] div[data-testid="stImage"] img {
        display: block !important;
        margin: 0 auto 15px auto !important;
        text-align: center !important;
    }
    
    div[style*="border: 2px solid #050d76"] div[data-testid="stImage"] {
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
    }
    
    @keyframes headerGlow {
        0%, 100% { filter: brightness(1); }
        50% { filter: brightness(1.15); }
    }
    
    /* Team Photo Container */
    .team-photo-container {
        text-align: center;
        margin: 2rem 0;
        padding: 1rem;
        border-radius: 16px;
        background: rgba(5, 13, 118, 0.1);
        border: 2px solid rgba(5, 13, 118, 0.3);
    }
    
    .team-photo-container img {
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(5, 13, 118, 0.4);
        max-width: 100%;
        height: auto;
        border: 3px solid rgba(5, 13, 118, 0.5);
    }
    
    h2.main-header {
        font-size: 2.5rem;
        font-weight: 800;
    }
    
    h3 {
        font-family: 'Poppins', sans-serif;
        font-weight: 700;
        color: #050d76;
        margin-top: 2rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid;
        border-image: linear-gradient(90deg, #050d76, #050d76) 1;
    }
    
    /* Metric cards - No Blockers dark theme */
    [data-testid="stMetricValue"] {
        font-family: 'Poppins', sans-serif;
        font-weight: 700;
        font-size: 2.5rem;
        background: linear-gradient(135deg, #050d76 0%, #050d76 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    [data-testid="metric-container"] {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 8px 32px rgba(5, 13, 118, 0.15);
        border: 2px solid rgba(5, 13, 118, 0.2);
        transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
        backdrop-filter: blur(10px);
        position: relative;
        overflow: hidden;
    }
    
    [data-testid="metric-container"]::before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 100%;
        height: 100%;
        background: linear-gradient(90deg, transparent, rgba(5, 13, 118, 0.15), transparent);
        transition: left 0.5s;
    }
    
    [data-testid="metric-container"]:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 16px 48px rgba(5, 13, 118, 0.4);
        border-color: rgba(5, 13, 118, 0.7);
    }
    
    [data-testid="metric-container"]:hover::before {
        left: 100%;
    }
    
    [data-testid="metric-container"] label {
        font-family: 'Inter', sans-serif;
        font-weight: 600;
        color: #2C3E50 !important;
        font-size: 0.95rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    /* DataFrames - No Blockers dark theme */
    .stDataFrame {
        background: #FFFFFF;
        border-radius: 12px;
        border: 1px solid rgba(5, 13, 118, 0.15);
        box-shadow: 0 2px 6px rgba(5, 13, 118, 0.08);
    }
    
    .stDataFrame table {
        color: #2C3E50;
        font-family: 'Inter', sans-serif;
        background: #FFFFFF;
    }
    
    .stDataFrame th {
        background: linear-gradient(135deg, #050d76 0%, #050d76 100%) !important;
        color: white !important;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        font-size: 0.85rem;
        padding: 1rem !important;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .stDataFrame td {
        color: #2C3E50;
        padding: 0.75rem !important;
        border-bottom: 1px solid rgba(5, 13, 118, 0.1);
        background: #FFFFFF;
    }
    
    .stDataFrame tbody tr:hover {
        background: rgba(5, 13, 118, 0.1) !important;
        transform: scale(1.01);
        transition: all 0.2s;
    }
    
    /* Selectbox and inputs - No Blockers theme */
    .stSelectbox > div > div {
        background: #FFFFFF;
        border-radius: 8px;
        border: 1px solid rgba(5, 13, 118, 0.2);
        transition: all 0.3s;
        color: #2C3E50;
    }
    
    .stSelectbox > div > div:hover {
        border-color: rgba(5, 13, 118, 0.6);
        box-shadow: 0 4px 16px rgba(5, 13, 118, 0.3);
    }
    
    .stFileUploader {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 1.5rem;
        border: 2px dashed rgba(5, 13, 118, 0.25);
        transition: all 0.3s;
    }
    
    .stFileUploader:hover {
        border-color: rgba(5, 13, 118, 0.4);
        background: #FFFFFF;
        box-shadow: 0 2px 8px rgba(5, 13, 118, 0.1);
    }
    
    /* Sidebar - Blue theme with readable text */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(5, 13, 118, 0.95) 0%, rgba(5, 13, 118, 0.95) 100%);
        backdrop-filter: blur(20px);
        border-right: 2px solid rgba(5, 13, 118, 0.5);
    }
    
    section[data-testid="stSidebar"] .stMarkdown h1 {
        color: #FFFFFF;
        font-family: 'Poppins', sans-serif;
        font-weight: 800;
        text-shadow: 0 2px 10px rgba(0,0,0,0.3);
    }
    
    section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] div,
    section[data-testid="stSidebar"] label {
        color: #FFFFFF;
    }
    
    section[data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.3);
        background: rgba(255, 255, 255, 0.3);
    }
    
    /* Sidebar selectbox and inputs - white background with blue text */
    section[data-testid="stSidebar"] .stSelectbox > div > div {
        background: #FFFFFF;
        border: 2px solid rgba(255, 255, 255, 0.3);
        color: #050d76 !important;
        border-radius: 8px;
    }
    
    /* Selected value text in closed selectbox */
    section[data-testid="stSidebar"] .stSelectbox > div > div > div,
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:first-child,
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select-value"],
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select-value"] > div,
    section[data-testid="stSidebar"] .stSelectbox [role="combobox"] {
        color: #050d76 !important;
    }
    
    section[data-testid="stSidebar"] .stSelectbox label {
        color: #FFFFFF !important;
    }
    
    /* Ensure all text elements inside selectbox are blue */
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] {
        color: #050d76 !important;
    }
    
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] * {
        color: #050d76 !important;
    }
    
    /* More aggressive targeting for the displayed value */
    section[data-testid="stSidebar"] .stSelectbox button,
    section[data-testid="stSidebar"] .stSelectbox button > div,
    section[data-testid="stSidebar"] .stSelectbox button > div > div,
    section[data-testid="stSidebar"] [data-baseweb="select"] button,
    section[data-testid="stSidebar"] [data-baseweb="select"] button > div,
    section[data-testid="stSidebar"] [data-baseweb="select"] button > div > div,
    section[data-testid="stSidebar"] [data-baseweb="select"] [data-baseweb="select-value"],
    section[data-testid="stSidebar"] [data-baseweb="select"] [data-baseweb="select-value"] > div,
    section[data-testid="stSidebar"] [data-baseweb="select"] [data-baseweb="select-value"] > div > div {
        color: #050d76 !important;
    }
    
    /* Override any white text color */
    section[data-testid="stSidebar"] .stSelectbox *[style*="color: white"],
    section[data-testid="stSidebar"] .stSelectbox *[style*="color: #FFFFFF"],
    section[data-testid="stSidebar"] .stSelectbox *[style*="color: rgb(255"] {
        color: #050d76 !important;
    }
    
    section[data-testid="stSidebar"] .stSelectbox > div > div:hover {
        border-color: rgba(255, 255, 255, 0.6);
        box-shadow: 0 2px 8px rgba(255, 255, 255, 0.2);
    }
    
    /* Selectbox dropdown options - white background with dark text */
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] {
        color: #050d76 !important;
    }
    
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {
        color: #050d76 !important;
    }
    
    /* Dropdown menu styling - force white background and dark text */
    div[data-baseweb="popover"],
    div[data-baseweb="popover"] > div,
    div[data-baseweb="popover"] ul,
    div[data-baseweb="popover"] ul > li {
        background: #FFFFFF !important;
        color: #2C3E50 !important;
    }
    
    div[data-baseweb="popover"] li {
        background: #FFFFFF !important;
        color: #2C3E50 !important;
    }
    
    div[data-baseweb="popover"] li:hover {
        background: rgba(5, 13, 118, 0.1) !important;
        color: #050d76 !important;
    }
    
    div[data-baseweb="popover"] li[aria-selected="true"],
    div[data-baseweb="popover"] li[aria-selected="true"] > div {
        background: rgba(5, 13, 118, 0.15) !important;
        color: #050d76 !important;
    }
    
    /* Target the actual option text - more aggressive */
    div[data-baseweb="popover"] li div,
    div[data-baseweb="popover"] li span,
    div[data-baseweb="popover"] li button,
    div[data-baseweb="popover"] li a {
        color: #2C3E50 !important;
        background: #FFFFFF !important;
    }
    
    div[data-baseweb="popover"] li:hover div,
    div[data-baseweb="popover"] li:hover span,
    div[data-baseweb="popover"] li:hover button {
        color: #050d76 !important;
        background: rgba(5, 13, 118, 0.1) !important;
    }
    
    /* Override BaseWeb default grey styles */
    div[data-baseweb="popover"] [class*="List"] {
        background: #FFFFFF !important;
    }
    
    div[data-baseweb="popover"] [class*="ListItem"] {
        background: #FFFFFF !important;
        color: #2C3E50 !important;
    }
    
    div[data-baseweb="popover"] [class*="ListItem"]:hover {
        background: rgba(5, 13, 118, 0.1) !important;
        color: #050d76 !important;
    }
    
    /* Force override any grey backgrounds - but be more selective */
    div[data-baseweb="popover"] li:not([aria-selected="true"]):not(:hover) * {
        background-color: #FFFFFF !important;
    }
    
    div[data-baseweb="popover"] li[aria-selected="true"] * {
        background-color: rgba(5, 13, 118, 0.15) !important;
        color: #050d76 !important;
    }
    
    div[data-baseweb="popover"] li:hover * {
        background-color: rgba(5, 13, 118, 0.1) !important;
        color: #050d76 !important;
    }
    
    /* But allow text color to show through */
    div[data-baseweb="popover"] li {
        color: #2C3E50 !important;
    }
    
    div[data-baseweb="popover"] li[aria-selected="true"] {
        color: #050d76 !important;
    }
    
    /* Sidebar image caption - white text on blue */
    section[data-testid="stSidebar"] .stImage {
        color: #FFFFFF;
    }
    
    section[data-testid="stSidebar"] .stImage caption {
        color: #FFFFFF;
        font-weight: 500;
        text-shadow: 0 1px 3px rgba(0,0,0,0.3);
    }
    
    /* Chart containers - No Blockers theme */
    .js-plotly-plot {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 1rem;
        box-shadow: 0 2px 6px rgba(5, 13, 118, 0.08);
        border: 1px solid rgba(5, 13, 118, 0.1);
        transition: all 0.3s;
    }
    
    .js-plotly-plot:hover {
        box-shadow: 0 4px 12px rgba(5, 13, 118, 0.12);
        transform: translateY(-4px);
    }
    
    /* Alert boxes - Enhanced */
    .stSuccess {
        background: linear-gradient(135deg, rgba(6, 167, 125, 0.15) 0%, rgba(6, 167, 125, 0.05) 100%);
        border-left: 4px solid #06A77D;
        border-radius: 12px;
        color: #155724;
        font-weight: 500;
        box-shadow: 0 4px 16px rgba(6, 167, 125, 0.2);
    }
    
    .stWarning {
        background: linear-gradient(135deg, rgba(241, 143, 1, 0.15) 0%, rgba(241, 143, 1, 0.05) 100%);
        border-left: 4px solid #F18F01;
        border-radius: 12px;
        color: #856404;
        font-weight: 500;
        box-shadow: 0 4px 16px rgba(241, 143, 1, 0.2);
    }
    
    .stError {
        background: linear-gradient(135deg, rgba(199, 62, 29, 0.15) 0%, rgba(199, 62, 29, 0.05) 100%);
        border-left: 4px solid #C73E1D;
        border-radius: 12px;
        color: #721c24;
        font-weight: 500;
        box-shadow: 0 4px 16px rgba(199, 62, 29, 0.2);
    }
    
    .stInfo {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.15) 0%, rgba(118, 75, 162, 0.05) 100%);
        border-left: 4px solid #667eea;
        border-radius: 12px;
        color: #0c5460;
        font-weight: 500;
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.2);
    }
    
    /* Buttons */
    button[kind="header"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 12px;
        border: none;
        color: white;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    button[kind="header"]:hover {
        transform: scale(1.05);
        box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
    }
    
    /* Info buttons for KPIs - Light blue/white theme */
    div[data-testid="column"] button {
        background: rgba(5, 13, 118, 0.1) !important;
        border: 1px solid rgba(5, 13, 118, 0.3) !important;
        border-radius: 8px !important;
        color: #050d76 !important;
        font-size: 1rem !important;
        padding: 0.25rem 0.5rem !important;
        min-height: auto !important;
        height: auto !important;
        transition: all 0.2s ease !important;
    }
    
    div[data-testid="column"] button:hover {
        background: rgba(5, 13, 118, 0.2) !important;
        border-color: rgba(5, 13, 118, 0.5) !important;
        transform: scale(1.05);
        box-shadow: 0 2px 8px rgba(5, 13, 118, 0.3);
    }
    
    /* Specifically target info buttons (ones with ℹ️) */
    button[data-testid*="button"]:has-text("ℹ️"),
    button:contains("ℹ️") {
        background: rgba(5, 13, 118, 0.1) !important;
        border: 1px solid rgba(5, 13, 118, 0.3) !important;
        color: #050d76 !important;
    }
    
    /* More specific targeting for metric column buttons - Improved styling */
    div[data-testid="column"]:nth-child(2) button,
    div[data-testid="column"]:last-child button {
        background: rgba(5, 13, 118, 0.15) !important;
        border: 1.5px solid rgba(5, 13, 118, 0.4) !important;
        border-radius: 6px !important;
        color: #050d76 !important;
        padding: 0.25rem 0.4rem !important;
        min-height: 32px !important;
        height: 32px !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
    }
    
    div[data-testid="column"]:nth-child(2) button:hover,
    div[data-testid="column"]:last-child button:hover {
        background: rgba(5, 13, 118, 0.25) !important;
        border-color: rgba(5, 13, 118, 0.6) !important;
        transform: scale(1.08);
        box-shadow: 0 2px 8px rgba(5, 13, 118, 0.4);
    }
    
    /* Scrollbar styling */
    ::-webkit-scrollbar {
        width: 10px;
    }
    
    ::-webkit-scrollbar-track {
        background: rgba(102, 126, 234, 0.1);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 10px;
    }
    
    ::-webkit-scrollbar-thumb:hover {
        background: linear-gradient(135deg, #764ba2 0%, #667eea 100%);
    }
    
    /* Text colors - Dark text on light background */
    .stMarkdown, .stApp {
        color: #2C3E50;
        font-family: 'Inter', sans-serif;
    }
    
    /* Regular text should be dark, blue for accents only */
    p, span, div {
        color: #2C3E50;
    }
    
    /* Top header bar - No Blockers blue */
    header[data-testid="stHeader"],
    div[data-testid="stHeader"],
    #MainMenu {
        background: #050d76 !important;
    }
    
    header[data-testid="stHeader"] button,
    header[data-testid="stHeader"] a,
    header[data-testid="stHeader"] div,
    header[data-testid="stHeader"] svg,
    #MainMenu button,
    #MainMenu a {
        color: #FFFFFF !important;
        fill: #FFFFFF !important;
    }
    
    /* Streamlit top bar menu */
    section[data-testid="stHeader"] {
        background: #050d76 !important;
    }
    
    /* Section dividers - No Blockers blue */
    hr {
        border: none;
        height: 3px;
        background: linear-gradient(90deg, transparent, #050d76, transparent);
        margin: 2rem 0;
    }
    
    /* Clean info icon buttons - completely transparent, no background box */
    /* Target all buttons in the last column of horizontal blocks (metric rows) */
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child button,
    div[data-testid="column"]:last-child button {
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        border-width: 0 !important;
        color: #050d76 !important;
        font-size: 1.4rem !important;
        padding: 0 !important;
        margin: 0 !important;
        min-height: auto !important;
        height: auto !important;
        width: auto !important;
        box-shadow: none !important;
        opacity: 0.65 !important;
        transition: opacity 0.2s ease, transform 0.2s ease !important;
    }
    
    div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:last-child button:hover,
    div[data-testid="column"]:last-child button:hover {
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
        opacity: 1 !important;
        transform: scale(1.25) !important;
        color: #050d76 !important;
        box-shadow: none !important;
    }
    
    /* Override BaseWeb button styles aggressively */
    button[data-baseweb="button"][kind="secondary"],
    button[kind="secondary"] {
        background: transparent !important;
        background-color: transparent !important;
        border: none !important;
    }
    
    /* Inline info icons in metric labels - positioned next to the title */
    .inline-info-icon {
        color: #050d76;
        font-size: 1rem;
        cursor: pointer;
        opacity: 0.65;
        margin-left: 0.5rem;
        display: inline-block;
        vertical-align: middle;
        transition: all 0.2s ease;
        user-select: none;
    }
    
    .inline-info-icon:hover {
        opacity: 1;
        color: #050d76;
        transform: scale(1.2);
    }
    
    /* Hide the checkbox used for toggle */
    div[data-testid="stCheckbox"] input[type="checkbox"][key*="info-"],
    div[data-testid="stCheckbox"] input[type="checkbox"][key*="toggle"] {
        display: none;
    }
    
    /* HIGH PRIORITY 7: Accessibility improvements */
    /* Focus indicators for keyboard navigation */
    button:focus, select:focus, input:focus, textarea:focus {
        outline: 3px solid #050d76 !important;
        outline-offset: 2px !important;
    }
    
    /* ARIA labels support */
    [aria-label] {
        cursor: help;
    }
    
    /* High contrast mode support */
    @media (prefers-contrast: high) {
        .main-header {
            color: #000000 !important;
        }
    }
    
    /* Customizable dashboard layout */
    .main .block-container {
        max-width: 100%;
        padding-left: 2rem;
        padding-right: 2rem;
    }
    
    /* Remove background colors from delta metrics, only show colored arrows */
    div[data-testid="stMetricDelta"] {
        background-color: transparent !important;
        padding: 0 !important;
    }
    
    div[data-testid="stMetricDelta"] svg {
        color: inherit !important;
    }
    
    div[data-testid="stMetricDelta"] > div {
        background-color: transparent !important;
    }
    
    div[data-testid="stMetricValue"] {
        font-size: 2.5rem !important;
        font-weight: 700 !important;
    }
    
    div[data-testid="stMetricLabel"] {
        font-size: 1.1rem !important;
        font-weight: 600 !important;
    }
    
    div[data-testid="stMetricDelta"] {
        font-size: 1rem !important;
    }
    
    button[key^="info_"] {
        font-size: 1.3rem !important;
        width: 32px !important;
        height: 32px !important;
        padding: 0 !important;
        opacity: 0.75 !important;
    }
    
    button[key^="info_"]:hover {
        opacity: 1 !important;
        transform: scale(1.15);
    }
</style>
"""


def apply_dashboard_theme() -> None:
    """Apply the dashboard CSS theme to Streamlit."""
    st.markdown(DASHBOARD_CSS, unsafe_allow_html=True)

