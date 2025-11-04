import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
from datetime import datetime
import sys
import warnings
from pathlib import Path
from PIL import Image
import base64
import tempfile
import uuid
import logging
from typing import Optional, Dict, Any, List, Tuple

# Suppress Plotly deprecation warnings
warnings.filterwarnings('ignore', message='.*keyword arguments have been deprecated.*')

# Add the analysis tools to the path
sys.path.append('analysis_tools')
sys.path.append('data_collection')

from match_analyzer import MatchAnalyzer
import performance_tracker as pt
from utils import validate_uploaded_file, save_uploaded_file_securely, cleanup_temp_file
import logging_config  # Initialize logging
import logging

logger = logging.getLogger(__name__)

# Import configuration
from config import (
    CHART_COLORS, CHART_COLOR_GRADIENTS, SETTER_THRESHOLD,
    KPI_TARGETS, VALID_ACTIONS, VALID_OUTCOMES,
    MAX_FILE_SIZE, ALLOWED_EXTENSIONS, DEFAULT_TEMPLATE_PATH, DEFAULT_IMAGES_DIR
)

# Professional Plotly template
BEAUTIFUL_TEMPLATE = {
    'layout': {
        'font': {
            'family': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            'size': 13,
            'color': '#040C7B'
        },
        'title': {
            'font': {
                'size': 18,
                'family': 'Inter, sans-serif',
                'color': '#040C7B'
            },
            'x': 0.5,
            'xanchor': 'center'
        },
        'paper_bgcolor': 'rgba(255,255,255,0)',  # Transparent
        'plot_bgcolor': '#FFFFFF',
        'hovermode': 'closest',
        'hoverlabel': {
            'bgcolor': '#F5F5F5',
            'font_size': 12,
            'font_family': 'Inter, sans-serif',
            'font_color': '#040C7B',
            'bordercolor': '#040C7B'
        },
        'xaxis': {
            'gridcolor': '#E8F4F8',
            'gridwidth': 1,
            'linecolor': '#BDC3C7',
            'linewidth': 1,
            'showgrid': True,
            'zeroline': False
        },
        'yaxis': {
            'gridcolor': '#E8F4F8',
            'gridwidth': 1,
            'linecolor': '#BDC3C7',
            'linewidth': 1,
            'showgrid': True,
            'zeroline': False
        },
        'legend': {
            'bgcolor': 'rgba(255,255,255,0.9)',
            'bordercolor': '#E8F4F8',
            'borderwidth': 1,
            'font': {'size': 11, 'color': '#040C7B'}
        },
        'margin': {'l': 60, 'r': 40, 't': 60, 'b': 60}
    }
}

def apply_beautiful_theme(fig, title=None, height=None):
    """Apply beautiful styling to any Plotly figure"""
    # Determine title text - avoid "undefined"
    if title:
        title_text = title
    elif hasattr(fig.layout, 'title') and hasattr(fig.layout.title, 'text'):
        existing_title = fig.layout.title.text
        title_text = existing_title if existing_title and existing_title != 'undefined' else ''
    else:
        title_text = ''
    
    # Update layout with beautiful template
    layout_update = {
        'template': 'plotly_white',
        'font': BEAUTIFUL_TEMPLATE['layout']['font'],
        'paper_bgcolor': 'rgba(255,255,255,0)',
        'plot_bgcolor': '#FFFFFF',
        'hovermode': 'closest',
        'hoverlabel': {
            'bgcolor': '#F5F5F5',
            'font_size': 12,
            'font_color': '#040C7B',
            'bordercolor': '#040C7B',
            'font_family': 'Inter, sans-serif'
        },
        'xaxis': {
            'gridcolor': '#E8F4F8',
            'gridwidth': 1,
            'linecolor': '#BDC3C7',
            'linewidth': 1,
            'showgrid': True,
            'zeroline': False,
            'title_font': {'size': 12, 'color': '#040C7B'}
        },
        'yaxis': {
            'gridcolor': '#E8F4F8',
            'gridwidth': 1,
            'linecolor': '#BDC3C7',
            'linewidth': 1,
            'showgrid': True,
            'zeroline': False,
            'title_font': {'size': 12, 'color': '#040C7B'}
        },
        'legend': {
            'bgcolor': 'rgba(255,255,255,0.9)',
            'bordercolor': '#E8F4F8',
            'borderwidth': 1,
            'font': {'size': 11, 'color': '#040C7B'},
            'x': 1.02,
            'y': 1,
            'xanchor': 'left',
            'yanchor': 'top'
        },
        'margin': {'l': 60, 'r': 40, 't': 60, 'b': 60},
        'height': height or 450
    }
    
    # Add title only if we have valid title text
    if title_text:
        layout_update['title'] = {
            'text': title_text,
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#040C7B', 'family': 'Inter, sans-serif'}
        }
    
    fig.update_layout(**layout_update)
    
    # Update traces for better appearance
    for trace in fig.data:
        if hasattr(trace, 'marker'):
            if 'line' not in trace.marker:
                trace.marker.line = {'width': 0.5, 'color': 'rgba(0,0,0,0.1)'}
        if hasattr(trace, 'line'):
            trace.line.width = 2.5
    
    return fig

# Plotly configuration for better UX
plotly_config = {
    'displayModeBar': True,
    'displaylogo': False,
    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
    'toImageButtonOptions': {
        'format': 'png',
        'filename': 'volleyball_chart',
        'height': 600,
        'width': 1000,
        'scale': 2
    }
}

# Page configuration
st.set_page_config(
    page_title="Volleyball Team Analytics",
    page_icon="🏐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Beautiful CSS styling - SUPER CREATIVE & COOL
st.markdown("""
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
        box-shadow: 0 20px 60px rgba(4, 12, 123, 0.3), inset 0 0 100px rgba(4, 12, 123, 0.05);
        border: 2px solid rgba(4, 12, 123, 0.3);
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
        background: linear-gradient(135deg, #040C7B 0%, #050C8C 50%, #060D9E 100%);
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
        background: linear-gradient(135deg, #040C7B 0%, #050C8C 80%);
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
        color: #040C7B;
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
    div[style*="border: 2px solid #040C7B"] div[data-testid="stImage"],
    div[style*="border: 2px solid #040C7B"] div[data-testid="stImage"] img {
        display: block !important;
        margin: 0 auto 15px auto !important;
        text-align: center !important;
    }
    
    div[style*="border: 2px solid #040C7B"] div[data-testid="stImage"] {
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
        background: rgba(4, 12, 123, 0.1);
        border: 2px solid rgba(4, 12, 123, 0.3);
    }
    
    .team-photo-container img {
        border-radius: 12px;
        box-shadow: 0 10px 40px rgba(4, 12, 123, 0.4);
        max-width: 100%;
        height: auto;
        border: 3px solid rgba(4, 12, 123, 0.5);
    }
    
    h2.main-header {
        font-size: 2.5rem;
        font-weight: 800;
    }
    
    h3 {
        font-family: 'Poppins', sans-serif;
        font-weight: 700;
        color: #040C7B;
        margin-top: 2rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid;
        border-image: linear-gradient(90deg, #040C7B, #050C8C) 1;
    }
    
    /* Metric cards - No Blockers dark theme */
    [data-testid="stMetricValue"] {
        font-family: 'Poppins', sans-serif;
        font-weight: 700;
        font-size: 2.5rem;
        background: linear-gradient(135deg, #040C7B 0%, #050C8C 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    
    [data-testid="metric-container"] {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 8px 32px rgba(4, 12, 123, 0.15);
        border: 2px solid rgba(4, 12, 123, 0.2);
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
        background: linear-gradient(90deg, transparent, rgba(4, 12, 123, 0.15), transparent);
        transition: left 0.5s;
    }
    
    [data-testid="metric-container"]:hover {
        transform: translateY(-8px) scale(1.02);
        box-shadow: 0 16px 48px rgba(4, 12, 123, 0.4);
        border-color: rgba(4, 12, 123, 0.7);
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
        border: 1px solid rgba(4, 12, 123, 0.15);
        box-shadow: 0 2px 6px rgba(4, 12, 123, 0.08);
    }
    
    .stDataFrame table {
        color: #2C3E50;
        font-family: 'Inter', sans-serif;
        background: #FFFFFF;
    }
    
    .stDataFrame th {
        background: linear-gradient(135deg, #040C7B 0%, #050C8C 100%) !important;
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
        border-bottom: 1px solid rgba(4, 12, 123, 0.1);
        background: #FFFFFF;
    }
    
    .stDataFrame tbody tr:hover {
        background: rgba(4, 12, 123, 0.1) !important;
        transform: scale(1.01);
        transition: all 0.2s;
    }
    
    /* Selectbox and inputs - No Blockers theme */
    .stSelectbox > div > div {
        background: #FFFFFF;
        border-radius: 8px;
        border: 1px solid rgba(4, 12, 123, 0.2);
        transition: all 0.3s;
        color: #2C3E50;
    }
    
    .stSelectbox > div > div:hover {
        border-color: rgba(4, 12, 123, 0.6);
        box-shadow: 0 4px 16px rgba(4, 12, 123, 0.3);
    }
    
    .stFileUploader {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 1.5rem;
        border: 2px dashed rgba(4, 12, 123, 0.25);
        transition: all 0.3s;
    }
    
    .stFileUploader:hover {
        border-color: rgba(4, 12, 123, 0.4);
        background: #FFFFFF;
        box-shadow: 0 2px 8px rgba(4, 12, 123, 0.1);
    }
    
    /* Sidebar - Blue theme with readable text */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(4, 12, 123, 0.95) 0%, rgba(5, 12, 140, 0.95) 100%);
        backdrop-filter: blur(20px);
        border-right: 2px solid rgba(4, 12, 123, 0.5);
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
        color: #040C7B !important;
        border-radius: 8px;
    }
    
    /* Selected value text in closed selectbox */
    section[data-testid="stSidebar"] .stSelectbox > div > div > div,
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div:first-child,
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select-value"],
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select-value"] > div,
    section[data-testid="stSidebar"] .stSelectbox [role="combobox"] {
        color: #040C7B !important;
    }
    
    section[data-testid="stSidebar"] .stSelectbox label {
        color: #FFFFFF !important;
    }
    
    /* Ensure all text elements inside selectbox are blue */
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] {
        color: #040C7B !important;
    }
    
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] * {
        color: #040C7B !important;
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
        color: #040C7B !important;
    }
    
    /* Override any white text color */
    section[data-testid="stSidebar"] .stSelectbox *[style*="color: white"],
    section[data-testid="stSidebar"] .stSelectbox *[style*="color: #FFFFFF"],
    section[data-testid="stSidebar"] .stSelectbox *[style*="color: rgb(255"] {
        color: #040C7B !important;
    }
    
    section[data-testid="stSidebar"] .stSelectbox > div > div:hover {
        border-color: rgba(255, 255, 255, 0.6);
        box-shadow: 0 2px 8px rgba(255, 255, 255, 0.2);
    }
    
    /* Selectbox dropdown options - white background with dark text */
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] {
        color: #040C7B !important;
    }
    
    section[data-testid="stSidebar"] .stSelectbox [data-baseweb="select"] > div {
        color: #040C7B !important;
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
        background: rgba(4, 12, 123, 0.1) !important;
        color: #040C7B !important;
    }
    
    div[data-baseweb="popover"] li[aria-selected="true"],
    div[data-baseweb="popover"] li[aria-selected="true"] > div {
        background: rgba(4, 12, 123, 0.15) !important;
        color: #040C7B !important;
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
        color: #040C7B !important;
        background: rgba(4, 12, 123, 0.1) !important;
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
        background: rgba(4, 12, 123, 0.1) !important;
        color: #040C7B !important;
    }
    
    /* Force override any grey backgrounds - but be more selective */
    div[data-baseweb="popover"] li:not([aria-selected="true"]):not(:hover) * {
        background-color: #FFFFFF !important;
    }
    
    div[data-baseweb="popover"] li[aria-selected="true"] * {
        background-color: rgba(4, 12, 123, 0.15) !important;
        color: #040C7B !important;
    }
    
    div[data-baseweb="popover"] li:hover * {
        background-color: rgba(4, 12, 123, 0.1) !important;
        color: #040C7B !important;
    }
    
    /* But allow text color to show through */
    div[data-baseweb="popover"] li {
        color: #2C3E50 !important;
    }
    
    div[data-baseweb="popover"] li[aria-selected="true"] {
        color: #040C7B !important;
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
        box-shadow: 0 2px 6px rgba(4, 12, 123, 0.08);
        border: 1px solid rgba(4, 12, 123, 0.1);
        transition: all 0.3s;
    }
    
    .js-plotly-plot:hover {
        box-shadow: 0 4px 12px rgba(4, 12, 123, 0.12);
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
        background: rgba(4, 12, 123, 0.1) !important;
        border: 1px solid rgba(4, 12, 123, 0.3) !important;
        border-radius: 8px !important;
        color: #040C7B !important;
        font-size: 1rem !important;
        padding: 0.25rem 0.5rem !important;
        min-height: auto !important;
        height: auto !important;
        transition: all 0.2s ease !important;
    }
    
    div[data-testid="column"] button:hover {
        background: rgba(4, 12, 123, 0.2) !important;
        border-color: rgba(4, 12, 123, 0.5) !important;
        transform: scale(1.05);
        box-shadow: 0 2px 8px rgba(4, 12, 123, 0.3);
    }
    
    /* Specifically target info buttons (ones with ℹ️) */
    button[data-testid*="button"]:has-text("ℹ️"),
    button:contains("ℹ️") {
        background: rgba(4, 12, 123, 0.1) !important;
        border: 1px solid rgba(4, 12, 123, 0.3) !important;
        color: #040C7B !important;
    }
    
    /* More specific targeting for metric column buttons - Improved styling */
    div[data-testid="column"]:nth-child(2) button,
    div[data-testid="column"]:last-child button {
        background: rgba(4, 12, 123, 0.15) !important;
        border: 1.5px solid rgba(4, 12, 123, 0.4) !important;
        border-radius: 6px !important;
        color: #040C7B !important;
        padding: 0.25rem 0.4rem !important;
        min-height: 32px !important;
        height: 32px !important;
        font-weight: 500 !important;
        font-size: 0.9rem !important;
    }
    
    div[data-testid="column"]:nth-child(2) button:hover,
    div[data-testid="column"]:last-child button:hover {
        background: rgba(4, 12, 123, 0.25) !important;
        border-color: rgba(4, 12, 123, 0.6) !important;
        transform: scale(1.08);
        box-shadow: 0 2px 8px rgba(4, 12, 123, 0.4);
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
        background: #040C7B !important;
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
        background: #040C7B !important;
    }
    
    /* Section dividers - No Blockers blue */
    hr {
        border: none;
        height: 3px;
        background: linear-gradient(90deg, transparent, #040C7B, transparent);
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
        color: #040C7B !important;
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
        color: #050C8C !important;
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
        color: #040C7B;
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
        color: #050C8C;
        transform: scale(1.2);
    }
    
    /* Hide the checkbox used for toggle */
    div[data-testid="stCheckbox"] input[type="checkbox"][key*="info-"],
    div[data-testid="stCheckbox"] input[type="checkbox"][key*="toggle"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

def validate_match_data(df) -> tuple[bool, list[str], list[str]]:
    """
    Comprehensive data validation for match data DataFrame.
    Returns (is_valid, error_messages, warnings)
    """
    errors = []
    warnings = []
    
    if df is None or df.empty:
        errors.append("DataFrame is None or empty")
        return False, errors, warnings
    
    # Check required columns
    REQUIRED_COLS = ['action', 'outcome', 'player', 'set_number', 'rotation']
    missing_cols = [col for col in REQUIRED_COLS if col not in df.columns]
    if missing_cols:
        errors.append(f"Missing required columns: {', '.join(missing_cols)}")
        return False, errors, warnings
    
    # Validate rotation values (should be 1-6)
    if 'rotation' in df.columns:
        invalid_rotations = df[~df['rotation'].isin(range(1, 7))]
        if len(invalid_rotations) > 0:
            unique_invalid = invalid_rotations['rotation'].unique()
            warnings.append(f"Invalid rotation values found: {unique_invalid}. Should be 1-6.")
    
    # Validate action values
    if 'action' in df.columns:
        invalid_actions = df[~df['action'].isin(VALID_ACTIONS)]
        if len(invalid_actions) > 0:
            unique_invalid = invalid_actions['action'].unique()[:5]  # Limit to first 5
            warnings.append(f"Invalid action values found: {unique_invalid}. Valid actions: {', '.join(VALID_ACTIONS)}")
    
    # Validate outcome values
    if 'outcome' in df.columns:
        invalid_outcomes = df[~df['outcome'].isin(VALID_OUTCOMES)]
        if len(invalid_outcomes) > 0:
            unique_invalid = invalid_outcomes['outcome'].unique()[:5]  # Limit to first 5
            warnings.append(f"Invalid outcome values found: {unique_invalid}. Valid outcomes: {', '.join(VALID_OUTCOMES)}")
    
    # Validate set_number (should be positive integer)
    if 'set_number' in df.columns:
        try:
            df['set_number'] = pd.to_numeric(df['set_number'], errors='coerce')
            invalid_sets = df[df['set_number'].isna() | (df['set_number'] <= 0)]
            if len(invalid_sets) > 0:
                warnings.append(f"Invalid set_number values found: {len(invalid_sets)} rows")
        except Exception:
            warnings.append("Could not validate set_number column")
    
    # Check for missing player names
    if 'player' in df.columns:
        missing_players = df[df['player'].isna() | (df['player'] == '')]
        if len(missing_players) > 0:
            warnings.append(f"Rows with missing player names: {len(missing_players)}")
    
    return len(errors) == 0, errors, warnings

def clear_session_state():
    """Clear session state when loading new match, keeping only essential keys"""
    keys_to_keep = {'match_loaded', 'analyzer', 'loader', 'opponent_name', 'match_filename'}
    keys_to_remove = [k for k in st.session_state.keys() if k not in keys_to_keep]
    for key in keys_to_remove:
        try:
            del st.session_state[key]
            logger.debug(f"Cleared session state key: {key}")
        except KeyError:
            pass

def load_match_data(uploaded_file) -> bool:
    """Load match data from uploaded file and store in session state.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        True if successful, False otherwise
    """
    if uploaded_file is None:
        return False
    
    # Validate file before processing
    is_valid, error_msg = validate_uploaded_file(uploaded_file)
    if not is_valid:
        st.error(f"❌ File validation failed: {error_msg}")
        return False
    
    # Extract opponent name from filename (assumes format like "vs Opponent.xlsx" or "Opponent.xlsx")
    filename = uploaded_file.name
    opponent_name = None
    if ' vs ' in filename.lower() or ' vs. ' in filename.lower():
        parts = filename.lower().split(' vs ')
        if len(parts) > 1:
            opponent_name = parts[1].replace('.xlsx', '').replace('.xls', '').strip().title()
    elif filename.startswith('vs '):
        opponent_name = filename.replace('vs ', '').replace('.xlsx', '').replace('.xls', '').strip().title()
    else:
        # Try to extract from filename (remove extension and common prefixes)
        opponent_name = filename.replace('.xlsx', '').replace('.xls', '').replace('Match_', '').replace('match_', '').strip()
    
    # Store in session state for use in header
    st.session_state['opponent_name'] = opponent_name
    st.session_state['match_filename'] = filename
    
    temp_file_path = None
    temp_converted_path = None
    
    try:
        # Save uploaded file securely to temporary location
        temp_file_path = save_uploaded_file_securely(uploaded_file)
        
        # Try loading with new Excel format first
        try:
            from excel_data_loader import ExcelMatchLoader
            loader = ExcelMatchLoader(temp_file_path)
            df = loader.get_match_dataframe()
            
            # Create a temporary Excel file in old format for MatchAnalyzer compatibility
            temp_converted_path = os.path.join(tempfile.gettempdir(), f"match_converted_{uuid.uuid4().hex}.xlsx")
            with pd.ExcelWriter(temp_converted_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Raw_Data', index=False)
            
            analyzer = MatchAnalyzer(temp_converted_path)
            if analyzer.match_data is not None and len(analyzer.match_data) > 0:
                # Validate data
                is_valid, errors, warnings = validate_match_data(analyzer.match_data)
                if not is_valid:
                    error_msg = "❌ Data validation failed:\n" + "\n".join(f"  • {e}" for e in errors)
                    st.error(error_msg)
                    return False
                if warnings:
                    for warning in warnings:
                        st.warning(f"⚠️ {warning}")
                # Store in session state
                st.session_state['analyzer'] = analyzer
                st.session_state['loader'] = loader
                st.session_state['match_loaded'] = True
                st.success(f"✅ Match data loaded successfully! Found {len(loader.player_data)} players across {len(loader.sets)} sets.")
                return True
            else:
                raise Exception("No data found in file after loading")
        except ImportError as e:
            # Fallback to old format
            analyzer = MatchAnalyzer(temp_file_path)
            if analyzer.match_data is not None and len(analyzer.match_data) > 0:
                # Validate even for old format
                is_valid, errors, warnings = validate_match_data(analyzer.match_data)
                if not is_valid:
                    error_msg = "❌ Data validation failed:\n" + "\n".join(f"  • {e}" for e in errors)
                    st.error(error_msg)
                    return False
                if warnings:
                    for warning in warnings:
                        st.warning(f"⚠️ {warning}")
                # Store in session state
                st.session_state['analyzer'] = analyzer
                st.session_state['loader'] = None
                st.session_state['match_loaded'] = True
                st.success("✅ Match data loaded successfully!")
                return True
            else:
                raise Exception(f"Could not load match data from uploaded file. ImportError: {e}")
    except ValueError as e:
        # Validation errors - user-friendly message
        st.error(f"❌ {str(e)}")
        return False
    except Exception as e:
        st.error(f"❌ Error loading file: {str(e)}")
        st.info("💡 Make sure your Excel file follows the correct format (Match_Template.xlsx)")
        # Log full traceback for debugging, but don't show to user
        import logging
        logging.error(f"Error loading match data: {e}", exc_info=True)
        return False
    finally:
        # Cleanup temporary files
        if temp_file_path:
            cleanup_temp_file(temp_file_path)
        if temp_converted_path:
            cleanup_temp_file(temp_converted_path)

def toggle_info_attack() -> None:
    """Toggle attack info display state."""
    st.session_state['show_info_attack'] = not st.session_state.get('show_info_attack', False)

def toggle_info_service() -> None:
    """Toggle service info display state."""
    st.session_state['show_info_service'] = not st.session_state.get('show_info_service', False)

def toggle_info_block() -> None:
    """Toggle block info display state."""
    st.session_state['show_info_block'] = not st.session_state.get('show_info_block', False)

def toggle_info_sideout() -> None:
    """Toggle sideout info display state."""
    st.session_state['show_info_sideout'] = not st.session_state.get('show_info_sideout', False)

def get_player_position(df: pd.DataFrame, player_name: str) -> Optional[str]:
    """Get the primary position of a player"""
    player_data = df[df['player'] == player_name]
    if 'position' in player_data.columns and len(player_data) > 0:
        # Get the most common position for this player
        position_counts = player_data['position'].value_counts()
        if len(position_counts) > 0:
            return position_counts.index[0]
    return None

def load_player_image(player_name: str, images_dir: str = "assets/images/team") -> Optional[Image.Image]:
    """Load player image from the team_images directory"""
    images_path = Path(images_dir)
    
    # Try different file extensions
    for ext in ['.jpeg', '.jpg', '.png', '.webp']:
        image_path = images_path / f"{player_name}{ext}"
        if image_path.exists():
            try:
                # Return original image without resizing to preserve quality
                return Image.open(image_path)
            except Exception as e:
                st.warning(f"Could not load image for {player_name}: {e}")
                return None
    
    return None

@st.cache_resource
def load_player_image_cached(player_name, images_dir="assets/images/team"):
    """Cached version of load_player_image for better performance"""
    return load_player_image(player_name, images_dir)

def get_position_full_name(position: str) -> str:
    """Convert position abbreviation to full name"""
    position_names = {
        'OH1': 'Outside Hitter',
        'OH2': 'Outside Hitter',
        'MB1': 'Middle Blocker',
        'MB2': 'Middle Blocker',
        'OPP': 'Opposite',
        'S': 'Setter',
        'L': 'Libero'
    }
    return position_names.get(position, position or 'Unknown Position')

def get_position_emoji(position: str) -> str:
    """Get emoji for player position"""
    position_emojis = {
        'OH1': '🏐', 'OH2': '🏐',  # Outside Hitters
        'MB1': '🛡️', 'MB2': '🛡️',  # Middle Blockers
        'OPP': '⚡',  # Opposite Hitter
        'S': '🎯',    # Setter
        'L': '🕸️'     # Libero
    }
    return position_emojis.get(position, '👤')

def display_player_image_and_info(player_name, position, image_size=180, use_sidebar=False):
    """Display player image and basic info in sidebar or main area"""
    if use_sidebar:
        # Display in sidebar
        st.sidebar.markdown("<br>", unsafe_allow_html=True)
        
        # Load and display player image
        player_image = load_player_image_cached(player_name)
        if player_image:
            # Create a copy and resize with high quality, preserving aspect ratio
            img_copy = player_image.copy()
            # Calculate aspect ratio to maintain proportions
            aspect_ratio = img_copy.width / img_copy.height
            if aspect_ratio > 1:
                new_width = image_size
                new_height = int(image_size / aspect_ratio)
            else:
                new_height = image_size
                new_width = int(image_size * aspect_ratio)
            # Use resize() with LANCZOS for better quality than thumbnail()
            img_copy = img_copy.resize((new_width, new_height), Image.Resampling.LANCZOS)
            # Center the image using CSS
            st.sidebar.markdown("""
            <style>
            .sidebar .element-container:has(img) {
                display: flex !important;
                justify-content: center !important;
                align-items: center !important;
            }
            </style>
            """, unsafe_allow_html=True)
            st.sidebar.image(img_copy, width=image_size, use_container_width=False)
        else:
            # Fallback: display a placeholder with player initial
            st.sidebar.markdown(f"""
            <div style="
                width: {image_size}px; 
                height: {image_size}px; 
                background: linear-gradient(135deg, #040C7B, #1A1F9E); 
                border-radius: 50%; 
                display: flex; 
                align-items: center; 
                justify-content: center; 
                color: white; 
                font-size: 24px; 
                font-weight: bold;
                margin: 0 auto;
            ">
                {player_name[0].upper()}
            </div>
            """, unsafe_allow_html=True)
        
        # Display player name and position
        position_emoji = get_position_emoji(position)
        position_full = get_position_full_name(position)
        st.sidebar.markdown(f"""
        <div style="padding: 10px 0; text-align: center;">
            <h3 style="margin: 0; color: #FFFFFF; font-size: 1.2rem;">{player_name}</h3>
            <p style="margin: 5px 0; font-size: 16px; color: #FFFFFF;">
                {position_emoji} {position_full}
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        st.sidebar.markdown("---")
    else:
        # Display in main area
        col1, col2 = st.columns([1, 3])
        
        with col1:
            # Load and display player image
            player_image = load_player_image(player_name)
            if player_image:
                # Create a copy and resize with high quality, preserving aspect ratio
                img_copy = player_image.copy()
                # Calculate aspect ratio to maintain proportions
                aspect_ratio = img_copy.width / img_copy.height
                if aspect_ratio > 1:
                    new_width = image_size
                    new_height = int(image_size / aspect_ratio)
                else:
                    new_height = image_size
                    new_width = int(image_size * aspect_ratio)
                # Use resize() with LANCZOS for better quality than thumbnail()
                img_copy = img_copy.resize((new_width, new_height), Image.Resampling.LANCZOS)
                # Add vertical spacing to align image with text (name starts at ~10px padding)
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                # Center horizontally
                st.markdown(f"""
                <div style="display: flex; justify-content: center; width: 100%;">
                """, unsafe_allow_html=True)
                st.image(img_copy, width=image_size, use_container_width=False)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                # Fallback: display a placeholder with player initial
                st.markdown(f"""
                <div style="
                    width: {image_size}px; 
                    height: {image_size}px; 
                    background: linear-gradient(135deg, #040C7B, #1A1F9E); 
                    border-radius: 50%; 
                    display: flex; 
                    align-items: center; 
                    justify-content: center; 
                    color: white; 
                    font-size: 24px; 
                    font-weight: bold;
                    margin: 0 auto;
                ">
                    {player_name[0].upper()}
                </div>
                """, unsafe_allow_html=True)
        
        with col2:
            # Display player name and position
            position_emoji = get_position_emoji(position)
            position_full = get_position_full_name(position)
            st.markdown(f"""
            <div style="padding: 10px 0; text-align: left;">
                <h3 style="margin: 0; color: #040C7B; font-size: 1.5rem;">{player_name}</h3>
                <p style="margin: 5px 0; font-size: 18px; color: #666;">
                    {position_emoji} {position_full}
                </p>
            </div>
            """, unsafe_allow_html=True)

def generate_insights(analyzer: MatchAnalyzer, team_stats: Dict[str, Any], 
                     TARGETS: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate actionable insights and recommendations from match data"""
    insights = []
    recommendations = []
    warnings = []
    
    df = analyzer.match_data
    # Get player stats for position-specific analysis
    player_stats = analyzer.calculate_player_metrics()
    
    # 1. Attack Efficiency Analysis
    attack_eff = team_stats['attack_efficiency']
    if attack_eff < TARGETS['attack_efficiency']['min']:
        insights.append({
            'type': 'warning',
            'priority': 'high',
            'title': 'Attack Efficiency Below Target',
            'message': f"Attack efficiency ({attack_eff:.1%}) is below target ({TARGETS['attack_efficiency']['min']:.1%}). Team has {team_stats['attack_errors']} attack errors vs {team_stats['attack_kills']} kills.",
            'recommendation': 'Focus on attack precision and decision-making. Consider reducing high-risk attacks when ahead.'
        })
    
    # 2. Set-by-Set Performance Trends
    set_stats = df.groupby('set_number').agg({
        'action': 'count',
        'outcome': lambda x: (x == 'kill').sum()
    }).rename(columns={'action': 'Total_Actions', 'outcome': 'Kills'})
    
    if len(set_stats) > 1:
        # Calculate attack efficiency by set
        set_attack_eff = []
        for set_num in set_stats.index:
            set_df = df[df['set_number'] == set_num]
            attacks = set_df[set_df['action'] == 'attack']
            if len(attacks) > 0:
                kills = len(attacks[attacks['outcome'] == 'kill'])
                errors = len(attacks[attacks['outcome'] == 'error'])
                eff = (kills - errors) / len(attacks)
                set_attack_eff.append({'set': set_num, 'efficiency': eff})
        
        if len(set_attack_eff) >= 2:
            first_set_eff = set_attack_eff[0]['efficiency']
            last_set_eff = set_attack_eff[-1]['efficiency']
            change = last_set_eff - first_set_eff
            
            if change < -0.10:  # Drop of 10% or more
                insights.append({
                    'type': 'warning',
                    'priority': 'high',
                    'title': 'Performance Decline in Later Sets',
                    'message': f"Attack efficiency drops from {first_set_eff:.1%} in Set {set_attack_eff[0]['set']} to {last_set_eff:.1%} in Set {set_attack_eff[-1]['set']} ({change:.1%} decrease).",
                    'recommendation': 'Consider strategic substitutions or timeout management to maintain performance. May indicate fatigue or loss of focus.'
                })
            elif change > 0.10:
                insights.append({
                    'type': 'success',
                    'priority': 'medium',
                    'title': 'Improving Performance',
                    'message': f"Attack efficiency improves from {first_set_eff:.1%} to {last_set_eff:.1%} (+{change:.1%}).",
                    'recommendation': 'Team is adapting well. Maintain this momentum.'
                })
    
    # 3. Rotation Efficiency Analysis
    rotation_stats = {}
    for rot in range(1, 7):
        rot_df = df[df['rotation'] == rot]
        if len(rot_df) > 0:
            attacks = rot_df[rot_df['action'] == 'attack']
            if len(attacks) > 0:
                kills = len(attacks[attacks['outcome'] == 'kill'])
                errors = len(attacks[attacks['outcome'] == 'error'])
                eff = (kills - errors) / len(attacks)
                rotation_stats[rot] = eff
    
    if rotation_stats:
        avg_rotation_eff = sum(rotation_stats.values()) / len(rotation_stats)
        weakest_rotation = min(rotation_stats.items(), key=lambda x: x[1])
        strongest_rotation = max(rotation_stats.items(), key=lambda x: x[1])
        
        if weakest_rotation[1] < avg_rotation_eff - 0.10:  # 10% below average
            insights.append({
                'type': 'warning',
                'priority': 'high',
                'title': f'Weak Rotation Identified',
                'message': f"Rotation {weakest_rotation[0]} has attack efficiency {weakest_rotation[1]:.1%}, which is {avg_rotation_eff - weakest_rotation[1]:.1%} below team average ({avg_rotation_eff:.1%}).",
                'recommendation': f'Focus practice on Rotation {weakest_rotation[0]} combinations. Review positioning and communication in this rotation.'
            })
        
        if strongest_rotation[1] > avg_rotation_eff + 0.10:  # 10% above average
            insights.append({
                'type': 'success',
                'priority': 'low',
                'title': f'Strong Rotation',
                'message': f"Rotation {strongest_rotation[0]} performs well with {strongest_rotation[1]:.1%} attack efficiency.",
                'recommendation': f'Use Rotation {strongest_rotation[0]} strategically when you need points. Consider this as your "go-to" rotation.'
            })
    
    # 4. Service Error Analysis
    service_eff = team_stats['service_efficiency']
    service_errors = team_stats['service_errors']
    service_aces = team_stats['service_aces']
    
    if service_errors > service_aces * 2:  # More than 2x errors vs aces
        insights.append({
            'type': 'warning',
            'priority': 'high',
            'title': 'High Service Error Rate',
            'message': f"Service errors ({service_errors}) significantly outnumber aces ({service_aces}). Net service impact: {service_aces - service_errors} points.",
            'recommendation': 'Focus on service consistency over power. Consider safer serves when ahead in score.'
        })
    
    # 5. Block Efficiency
    block_eff = team_stats['block_efficiency']
    if block_eff < TARGETS['block_efficiency']['min']:
        insights.append({
            'type': 'warning',
            'priority': 'medium',
            'title': 'Low Block Efficiency',
            'message': f"Block efficiency ({block_eff:.1%}) is below target. Only {team_stats['block_kills']} block kills.",
            'recommendation': 'Work on timing and positioning. Consider blocking assignments and communication.'
        })
    
    # 6. Error Distribution by Set
    if len(set_stats) > 1:
        set_errors = []
        for set_num in set_stats.index:
            set_df = df[df['set_number'] == set_num]
            errors = len(set_df[set_df['outcome'] == 'error'])
            set_errors.append({'set': set_num, 'errors': errors})
        
        if len(set_errors) >= 2:
            max_errors_set = max(set_errors, key=lambda x: x['errors'])
            min_errors_set = min(set_errors, key=lambda x: x['errors'])
            
            if max_errors_set['errors'] > min_errors_set['errors'] * 1.5:
                insights.append({
                    'type': 'warning',
                    'priority': 'medium',
                    'title': f'Error Concentration in Set {max_errors_set["set"]}',
                    'message': f"Set {max_errors_set['set']} has {max_errors_set['errors']} errors vs {min_errors_set['errors']} in Set {min_errors_set['set']}.",
                    'recommendation': f'Review what happened in Set {max_errors_set["set"]}. Identify error patterns and address root causes.'
                })
    
    # 7. Side-out Percentage
    side_out = team_stats['side_out_percentage']
    if side_out < TARGETS['side_out_percentage']['min']:
        insights.append({
            'type': 'warning',
            'priority': 'high',
            'title': 'Low Side-out Percentage',
            'message': f"Side-out percentage ({side_out:.1%}) is below target. Only {team_stats['good_receives']} good receives out of {team_stats['total_receives']} attempts.",
            'recommendation': 'Focus on reception quality. Good reception is the foundation of effective offense. Practice serve receive drills with OH and Libero players. Work on reading serve trajectory and positioning.'
        })
    elif side_out >= TARGETS['side_out_percentage']['max']:
        insights.append({
            'type': 'success',
            'priority': 'low',
            'title': 'Excellent Side-out Performance',
            'message': f"Side-out percentage ({side_out:.1%}) exceeds target. Strong reception foundation.",
            'recommendation': 'Maintain this reception quality. This strong foundation allows for more aggressive offensive plays.'
        })
    
    # 8. Attack Error Analysis - Too many errors
    attack_errors = team_stats['attack_errors']
    attack_kills = team_stats['attack_kills']
    if attack_errors > attack_kills * 0.5:  # More than half as many errors as kills
        error_rate = attack_errors / team_stats['attack_attempts'] if team_stats['attack_attempts'] > 0 else 0
        insights.append({
            'type': 'warning',
            'priority': 'high',
            'title': 'High Attack Error Rate',
            'message': f"Attack errors ({attack_errors}) are {error_rate:.1%} of all attack attempts. Error-to-kill ratio: {attack_errors/attack_kills:.2f}:1",
            'recommendation': 'Focus on shot selection and placement. Work on hitting angles, reducing out-of-bounds attacks. Consider lowering attack tempo when ahead to reduce errors. Practice attacking under pressure.'
        })
    
    # 9. Service Pressure Analysis
    service_aces = team_stats['service_aces']
    if service_aces > service_errors * 1.5:  # More aces than errors
        insights.append({
            'type': 'success',
            'priority': 'medium',
            'title': 'Effective Service Pressure',
            'message': f"Service aces ({service_aces}) significantly exceed errors ({service_errors}). Good service pressure.",
            'recommendation': 'Continue aggressive serving. Your service game is putting pressure on opponents. Maintain consistency while keeping aggressive approach.'
        })
    
    # 10. Reception Quality Distribution
    total_receives = team_stats['total_receives']
    if total_receives > 0:
        reception_error_rate = (team_stats['total_receives'] - team_stats['good_receives']) / total_receives
        if reception_error_rate > 0.25:  # More than 25% reception errors
            insights.append({
                'type': 'warning',
                'priority': 'high',
                'title': 'Reception Error Rate Too High',
                'message': f"Reception error rate is {reception_error_rate:.1%}. {team_stats['total_receives'] - team_stats['good_receives']} reception errors.",
                'recommendation': 'Focus on reception fundamentals: body positioning, platform angle, reading serve trajectory. Practice with different serve types and speeds. Work on libero and outside hitter reception skills specifically.'
            })
    
    # 11. Set-by-Set Service Analysis
    if len(set_stats) > 1:
        set_service_stats = []
        for set_num in set_stats.index:
            set_df = df[df['set_number'] == set_num]
            serves = set_df[set_df['action'] == 'serve']
            if len(serves) > 0:
                aces = len(serves[serves['outcome'] == 'ace'])
                serv_errors = len(serves[serves['outcome'] == 'error'])
                set_service_stats.append({
                    'set': set_num,
                    'aces': aces,
                    'errors': serv_errors,
                    'net': aces - serv_errors
                })
        
        if len(set_service_stats) >= 2:
            # Find set with most service errors
            worst_service_set = max(set_service_stats, key=lambda x: x['errors'])
            if worst_service_set['errors'] > 5:
                insights.append({
                    'type': 'warning',
                    'priority': 'medium',
                    'title': f'Service Errors Peak in Set {worst_service_set["set"]}',
                    'message': f"Set {worst_service_set['set']} has {worst_service_set['errors']} service errors, highest of all sets.",
                    'recommendation': f'Review service strategy for Set {worst_service_set["set"]}. Consider switching to safer serves when errors accumulate. May indicate fatigue or pressure affecting service consistency.'
                })
    
    # 12. Block Coverage Analysis
    block_attempts = team_stats['block_attempts']
    block_kills = team_stats['block_kills']
    if block_attempts > 0:
        block_kill_rate = block_kills / block_attempts
        if block_kill_rate < 0.05:  # Less than 5% kill rate
            insights.append({
                'type': 'warning',
                'priority': 'medium',
                'title': 'Low Block Kill Rate',
                'message': f"Only {block_kill_rate:.1%} of block attempts result in kills. {block_kills} kills from {block_attempts} attempts.",
                'recommendation': 'Focus on blocking timing and hand positioning. Work on reading attacker approach and timing jump. Practice middle blockers on quick tempo blocks. Improve blocking unit coordination.'
            })
    
    # 13. Position-Specific Analysis
    if player_stats:
        # Outside Hitter Analysis
        oh_players = []
        for player, stats in player_stats.items():
            pos = get_player_position(df, player)
            if pos and pos.startswith('OH'):
                oh_players.append({'player': player, 'position': pos, 'stats': stats})
        
        if oh_players:
            oh_attack_eff = [p['stats']['attack_efficiency'] for p in oh_players if p['stats']['attack_attempts'] > 5]
            oh_reception = [p['stats'].get('reception_percentage', 0) for p in oh_players if p['stats'].get('total_receives', 0) > 0]
            
            if oh_attack_eff:
                avg_oh_attack = sum(oh_attack_eff) / len(oh_attack_eff)
                if avg_oh_attack < 0.20:
                    weak_oh = [p for p in oh_players if p['stats']['attack_efficiency'] < 0.20 and p['stats']['attack_attempts'] > 5]
                    if weak_oh:
                        insights.append({
                            'type': 'warning',
                            'priority': 'high',
                            'title': 'Outside Hitter Attack Efficiency Low',
                            'message': f"Average OH attack efficiency: {avg_oh_attack:.1%}. {', '.join([p['player'] for p in weak_oh[:2]])} performing below target.",
                            'recommendation': 'Focus on OH attack technique: hitting angles, power control, off-speed shots. Work on attacking from various sets. Practice back-row attacks. Improve attacking against double blocks.'
                        })
            
            if oh_reception:
                avg_oh_reception = sum(oh_reception) / len(oh_reception)
                if avg_oh_reception < 0.70:
                    insights.append({
                        'type': 'warning',
                        'priority': 'high',
                        'title': 'Outside Hitter Reception Quality Needs Improvement',
                        'message': f"Average OH reception percentage: {avg_oh_reception:.1%}, below target 70%.",
                        'recommendation': 'Focus OH reception training: platform work, body positioning, reading serve. Practice with different serve types. Work on movement to ball and proper platform angle.'
                    })
        
        # Middle Blocker Analysis
        mb_players = []
        for player, stats in player_stats.items():
            pos = get_player_position(df, player)
            if pos and pos.startswith('MB'):
                mb_players.append({'player': player, 'position': pos, 'stats': stats})
        
        if mb_players:
            mb_block_eff = [p['stats']['block_efficiency'] for p in mb_players if p['stats']['block_attempts'] > 0]
            mb_attack_eff = [p['stats']['attack_efficiency'] for p in mb_players if p['stats']['attack_attempts'] > 0]
            
            if mb_block_eff:
                avg_mb_block = sum(mb_block_eff) / len(mb_block_eff)
                if avg_mb_block < 0.05:
                    insights.append({
                        'type': 'warning',
                        'priority': 'high',
                        'title': 'Middle Blocker Blocking Performance Low',
                        'message': f"Average MB block efficiency: {avg_mb_block:.1%}. Middle blockers not generating enough block kills.",
                        'recommendation': 'Focus MB blocking: timing, penetration, hand positioning. Work on reading setter and hitter. Practice quick tempo blocks. Improve coordination between MBs. Focus on blocking assignments and communication.'
                    })
            
            if mb_attack_eff:
                avg_mb_attack = sum(mb_attack_eff) / len(mb_attack_eff)
                if avg_mb_attack < 0.30:
                    insights.append({
                        'type': 'warning',
                        'priority': 'medium',
                        'title': 'Middle Blocker Attack Efficiency Below Target',
                        'message': f"Average MB attack efficiency: {avg_mb_attack:.1%}. Middle blockers should have high efficiency.",
                        'recommendation': 'MBs need to capitalize on quick sets. Work on quick attack timing, hitting angles, and variety. Practice 1st tempo attacks. Improve connection with setter on quick sets.'
                    })
        
        # Setter Analysis
        setter_players = []
        for player, stats in player_stats.items():
            pos = get_player_position(df, player)
            if pos == 'S':
                setter_players.append({'player': player, 'stats': stats})
            elif stats.get('total_sets', 0) > 20:  # Has many sets even if not marked as S
                setter_players.append({'player': player, 'stats': stats})
        
        if setter_players:
            for setter in setter_players:
                sets_total = setter['stats'].get('total_sets', 0)
                good_sets = setter['stats'].get('good_sets', 0)
                if sets_total > 0:
                    set_quality = good_sets / sets_total
                    if set_quality < 0.80:
                        insights.append({
                            'type': 'warning',
                            'priority': 'high',
                            'title': f'Setter {setter["player"]} - Setting Quality Below Target',
                            'message': f"Setting quality: {set_quality:.1%} ({good_sets}/{sets_total} good sets). Target: 80%+.",
                            'recommendation': f'Focus on setting consistency for {setter["player"]}. Work on hand position, footwork, and reading blockers. Practice setting accuracy to different positions. Improve decision-making on distribution. Setter should prioritize consistency over spectacular sets.'
                        })
        
        # Opposite Hitter Analysis
        opp_players = []
        for player, stats in player_stats.items():
            pos = get_player_position(df, player)
            if pos == 'OPP':
                opp_players.append({'player': player, 'stats': stats})
        
        if opp_players:
            opp_attack_eff = [p['stats']['attack_efficiency'] for p in opp_players if p['stats']['attack_attempts'] > 5]
            if opp_attack_eff:
                avg_opp_attack = sum(opp_attack_eff) / len(opp_attack_eff)
                if avg_opp_attack < 0.25:
                    insights.append({
                        'type': 'warning',
                        'priority': 'high',
                        'title': 'Opposite Hitter Attack Efficiency Low',
                        'message': f"Average OPP attack efficiency: {avg_opp_attack:.1%}. Opposite hitters are key offensive weapons.",
                        'recommendation': 'OPP needs improvement on right-side attacks. Work on attacking angles, avoiding opponent blocks, back-row attacks. Practice attacking from the right side with various sets. Focus on power and placement. Work on hitting around blocks and using the antenna effectively.'
                    })
        
        # Libero Analysis
        libero_players = []
        for player, stats in player_stats.items():
            pos = get_player_position(df, player)
            if pos == 'L':
                libero_players.append({'player': player, 'stats': stats})
        
        if libero_players:
            for libero in libero_players:
                reception = libero['stats'].get('reception_percentage', 0)
                total_rec = libero['stats'].get('total_receives', 0)
                if total_rec > 10 and reception < 0.75:
                    insights.append({
                        'type': 'warning',
                        'priority': 'high',
                        'title': f'Libero {libero["player"]} - Reception Below Standard',
                        'message': f"Reception percentage: {reception:.1%} ({libero['stats'].get('good_receives', 0)}/{total_rec} good). Libero target: 75%+.",
                        'recommendation': f'Focus on reception fundamentals for {libero["player"]}. Libero is primary reception specialist. Work on platform work, reading serves, and positioning. Practice with various serve speeds and types. Improve movement to ball and first contact quality. Focus on consistency and minimizing reception errors.'
                    })
    
    # 14. Action Distribution Analysis
    action_counts = df['action'].value_counts()
    total_actions = len(df)
    if total_actions > 0:
        attack_pct = action_counts.get('attack', 0) / total_actions
        if attack_pct < 0.20:  # Less than 20% attacks
            insights.append({
                'type': 'warning',
                'priority': 'medium',
                'title': 'Low Attack Percentage',
                'message': f"Only {attack_pct:.1%} of actions are attacks. Team may be too passive.",
                'recommendation': 'Increase attack frequency. Good reception should lead to attacks. Work on transition offense. Improve attack opportunities from good receptions.'
            })
        elif attack_pct > 0.35:  # More than 35% attacks
            insights.append({
                'type': 'info',
                'priority': 'low',
                'title': 'High Attack Percentage',
                'message': f"{attack_pct:.1%} of actions are attacks. Team is aggressive offensively.",
                'recommendation': 'Maintain offensive pressure. Ensure high attack efficiency accompanies high frequency.'
            })
    
    # 15. Outcome Distribution Analysis
    outcome_counts = df['outcome'].value_counts()
    total_outcomes = len(df)
    if total_outcomes > 0:
        good_pct = outcome_counts.get('good', 0) / total_outcomes
        kill_pct = outcome_counts.get('kill', 0) / total_outcomes
        error_pct = outcome_counts.get('error', 0) / total_outcomes
        
        if error_pct > 0.15:  # More than 15% errors
            insights.append({
                'type': 'warning',
                'priority': 'high',
                'title': 'High Error Rate Across All Actions',
                'message': f"Errors represent {error_pct:.1%} of all actions ({outcome_counts.get('error', 0)} total errors).",
                'recommendation': 'Focus on reducing unforced errors across all skills. Work on consistency and decision-making. Practice under pressure situations. Review error types and address root causes.'
            })
        
        if kill_pct < 0.08:  # Less than 8% kills
            insights.append({
                'type': 'warning',
                'priority': 'high',
                'title': 'Low Scoring Rate',
                'message': f"Kills represent only {kill_pct:.1%} of all actions. Low scoring efficiency.",
                'recommendation': 'Increase kill rate. Focus on attack placement, power, and decision-making. Work on finishing rallies. Improve attacking against blocks.'
            })
    
    # 16. Rotation-Specific Detailed Analysis
    if rotation_stats:
        for rot, eff in rotation_stats.items():
            rot_df = df[df['rotation'] == rot]
            rot_errors = len(rot_df[rot_df['outcome'] == 'error'])
            rot_total = len(rot_df)
            
            if rot_total > 10:  # Only analyze rotations with significant data
                error_rate = rot_errors / rot_total
                if error_rate > 0.20:  # More than 20% errors in rotation
                    insights.append({
                        'type': 'warning',
                        'priority': 'high',
                        'title': f'Rotation {rot} - High Error Rate',
                        'message': f"Rotation {rot} has {error_rate:.1%} error rate ({rot_errors}/{rot_total} errors).",
                        'recommendation': f'Review Rotation {rot} lineup and positioning. Identify which players in this rotation struggle. Consider lineup adjustments or focused practice for this rotation combination. Work on communication and coordination in this rotation.'
                    })
    
    # 17. Service vs Reception Battle
    if total_receives > 0 and service_aces + service_errors > 0:
        service_pressure = service_aces / (service_aces + service_errors) if (service_aces + service_errors) > 0 else 0
        reception_success = team_stats['good_receives'] / total_receives
        
        if service_pressure < 0.15 and reception_success < 0.70:
            insights.append({
                'type': 'warning',
                'priority': 'high',
                'title': 'Service-Reception Battle Not Favorable',
                'message': f"Low service pressure ({service_pressure:.1%}) and low reception success ({reception_success:.1%}).",
                        'recommendation': 'Improve both serving and receiving. Work on service consistency and power. Simultaneously improve reception quality through focused drills. Both skills need attention for competitive play.'
            })
    
    # 18. Block Touch vs Kill Analysis
    blocks = df[df['action'] == 'block']
    if len(blocks) > 0:
        block_touches = len(blocks[blocks['outcome'] == 'good'])
        block_kills_total = len(blocks[blocks['outcome'] == 'kill'])
        if block_touches > block_kills_total * 5:  # More touches than kills
            insights.append({
                'type': 'info',
                'priority': 'medium',
                'title': 'Blocks Creating Opportunities',
                'message': f"Many block touches ({block_touches}) creating follow-up opportunities. {block_kills_total} direct block kills.",
                'recommendation': 'Blocks are creating opportunities. Work on converting block touches into points through better defense coverage and transition attacks.'
            })
    
    # 19. Set-by-Set Error Trend
    if len(set_stats) > 1:
        error_trend = []
        for set_num in sorted(set_stats.index):
            set_df = df[df['set_number'] == set_num]
            errors = len(set_df[set_df['outcome'] == 'error'])
            error_trend.append({'set': set_num, 'errors': errors})
        
        if len(error_trend) >= 2:
            increasing_errors = all(error_trend[i]['errors'] < error_trend[i+1]['errors'] for i in range(len(error_trend)-1))
            if increasing_errors and error_trend[-1]['errors'] > error_trend[0]['errors'] * 1.3:
                insights.append({
                    'type': 'warning',
                    'priority': 'high',
                    'title': 'Increasing Error Trend Across Sets',
                    'message': f"Errors increase from Set {error_trend[0]['set']} ({error_trend[0]['errors']} errors) to Set {error_trend[-1]['set']} ({error_trend[-1]['errors']} errors).",
                    'recommendation': 'Errors are increasing across sets - may indicate fatigue, loss of focus, or mounting pressure. Consider strategic timeouts, substitutions, or mental reset strategies. Work on maintaining consistency under pressure.'
                })
    
    # 20. Attack Distribution - Are we balanced?
    if player_stats:
        attack_distribution = {}
        for player, stats in player_stats.items():
            if stats['attack_attempts'] > 5:
                attack_distribution[player] = stats['attack_attempts']
        
        if len(attack_distribution) >= 4:
            sorted_attacks = sorted(attack_distribution.items(), key=lambda x: x[1], reverse=True)
            top_attacker_attacks = sorted_attacks[0][1]
            avg_other_attacks = sum(x[1] for x in sorted_attacks[1:]) / (len(sorted_attacks) - 1) if len(sorted_attacks) > 1 else 0
            
            if avg_other_attacks > 0 and top_attacker_attacks > avg_other_attacks * 2.5:
                insights.append({
                    'type': 'info',
                    'priority': 'medium',
                    'title': 'Unbalanced Attack Distribution',
                    'message': f"{sorted_attacks[0][0]} has {top_attacker_attacks} attacks vs average of {avg_other_attacks:.1f} for others.",
                    'recommendation': f'Consider distributing attacks more evenly. While {sorted_attacks[0][0]} is getting many sets, diversifying attack points makes team harder to defend. Work on setter distribution to multiple hitters.'
                })
    
    # Sort insights by priority
    priority_order = {'high': 0, 'medium': 1, 'low': 2}
    insights.sort(key=lambda x: priority_order.get(x['priority'], 3))
    
    return insights


# NOTE: generate_coach_insights, generate_coach_summary, and display_coach_insights_section 
# have been moved to ui/insights.py to avoid circular import issues. 
# They are now imported from ui.insights module. Do not add them back here.


def generate_summary(insights, team_stats, TARGETS):
    """Generate a concise summary with pros, cons, and key sentences"""
    summary = {
        'sentences': [],
        'pros': [],
        'cons': []
    }
    
    # Group insights
    high_priority = [i for i in insights if i['priority'] == 'high']
    warnings = [i for i in insights if i['type'] == 'warning']
    successes = [i for i in insights if i['type'] == 'success']
    
    # Key metrics summary
    attack_eff = team_stats['attack_efficiency']
    service_eff = team_stats['service_efficiency']
    block_eff = team_stats.get('block_efficiency', 0)
    side_out = team_stats.get('side_out_percentage', 0)
    
    # Generate summary sentences
    summary['sentences'].append(f"Team attack efficiency: {attack_eff:.1%} (Target: {TARGETS['attack_efficiency']['min']:.1%}+)")
    summary['sentences'].append(f"Service efficiency: {service_eff:.1%} (Target: {TARGETS['service_efficiency']['min']:.1%}+)")
    
    if len(high_priority) > 0:
        summary['sentences'].append(f"{len(high_priority)} high-priority areas need attention.")
    
    # Generate pros (successes and strengths)
    if attack_eff >= TARGETS['attack_efficiency']['min']:
        summary['pros'].append(f"Attack efficiency ({attack_eff:.1%}) meets target")
    if service_eff >= TARGETS['service_efficiency']['min']:
        summary['pros'].append(f"Service efficiency ({service_eff:.1%}) meets target")
    if side_out >= TARGETS.get('side_out_percentage', {}).get('min', 0.65):
        summary['pros'].append(f"Side-out percentage ({side_out:.1%}) is strong")
    
    for success in successes[:3]:  # Top 3 successes
        summary['pros'].append(success['title'])
    
    # Generate cons (warnings and weaknesses)
    if attack_eff < TARGETS['attack_efficiency']['min']:
        summary['cons'].append(f"Attack efficiency below target ({attack_eff:.1%} vs {TARGETS['attack_efficiency']['min']:.1%})")
    if service_eff < TARGETS['service_efficiency']['min']:
        summary['cons'].append(f"Service efficiency below target ({service_eff:.1%} vs {TARGETS['service_efficiency']['min']:.1%})")
    if block_eff < TARGETS.get('block_efficiency', {}).get('min', 0.05):
        summary['cons'].append(f"Block efficiency below target ({block_eff:.1%} vs {TARGETS.get('block_efficiency', {}).get('min', 0.05):.1%})")
    
    for warning in warnings[:3]:  # Top 3 warnings
        summary['cons'].append(warning['title'])
    
    return summary

def display_insights_section(insights: List[Dict[str, Any]], 
                             team_stats: Optional[Dict[str, Any]] = None, 
                             TARGETS: Optional[Dict[str, Any]] = None) -> None:
    """Display insights and recommendations in an organized way"""
    if not insights:
        st.info("💡 No specific insights available. Overall performance is consistent.")
        return
    
    st.markdown("### 💡 Insights")
    
    # Generate and display summary
    if team_stats and TARGETS:
        summary = generate_summary(insights, team_stats, TARGETS)
        
        st.markdown("#### 📋 Summary")
        
        # Summary sentences
        if summary['sentences']:
            sentences_text = "\n".join([f"• {s}" for s in summary['sentences']])
            st.info(f"**Key Points:**\n\n{sentences_text}")
        
        # Pros and Cons in columns
        col1, col2 = st.columns(2)
        
        with col1:
            if summary['pros']:
                pros_text = "\n".join([f"• {pro}" for pro in summary['pros']])
                st.success(f"**✅ Strengths:**\n\n{pros_text}")
            else:
                st.info("**✅ Strengths:**\n\n• No major strengths identified")
        
        with col2:
            if summary['cons']:
                cons_text = "\n".join([f"• {con}" for con in summary['cons']])
                st.warning(f"**⚠️ Areas for Improvement:**\n\n{cons_text}")
            else:
                st.info("**⚠️ Areas for Improvement:**\n\n• No critical weaknesses")
        
        st.markdown("---")
    
    # Group insights by type
    high_priority = [i for i in insights if i['priority'] == 'high']
    medium_priority = [i for i in insights if i['priority'] == 'medium']
    
    # Display high priority
    if high_priority:
        st.markdown("#### 🔴 High Priority Actions")
        for insight in high_priority:
            if insight['type'] == 'warning':
                st.warning(f"**{insight['title']}**\n\n{insight['message']}")
            elif insight['type'] == 'success':
                st.success(f"**{insight['title']}**\n\n{insight['message']}")
    
    # Display medium priority
    if medium_priority:
        st.markdown("#### 🟡 Medium Priority Actions")
        for insight in medium_priority[:5]:  # Limit to top 5
            if insight['type'] == 'warning':
                st.warning(f"**{insight['title']}**\n\n{insight.get('message', '')}")
            elif insight['type'] == 'success':
                st.info(f"**{insight['title']}**\n\n{insight.get('message', '')}")

def get_performance_color(value: float, target_min: float, target_max: float, 
                         target_optimal: Optional[float] = None) -> str:
    """Return color based on performance level - only green or red"""
    # If optimal target provided, use it; otherwise use midpoint of min/max
    if target_optimal is None:
        target_optimal = (target_min + target_max) / 2
    
    # Only return green or red - no yellow
    if value >= target_optimal:
        return "🟢"  # Meets or exceeds target
    else:
        return "🔴"  # Below target

METRIC_DEFINITIONS = {
    'attack_efficiency': {
        'name': 'Attack Efficiency',
        'formula': '(Kills - Errors) / Total Attack Attempts',
        'description': 'Measures net scoring effectiveness. Positive values indicate more kills than errors.',
        'display_as_percentage': True
    },
    'service_efficiency': {
        'name': 'Service Efficiency',
        'formula': '(Aces - Errors) / Total Service Attempts',
        'description': 'Measures net service impact. Positive values indicate more aces than service errors.',
        'display_as_percentage': True
    },
    'block_efficiency': {
        'name': 'Block Efficiency',
        'formula': '(Block Kills - Block Errors) / Total Block Attempts',
        'description': 'Measures defensive scoring impact. Positive values indicate more block kills than errors.',
        'display_as_percentage': True
    },
    'side_out_percentage': {
        'name': 'Side-out Percentage',
        'formula': 'Points Won When Receiving Serve / Total Rallies When Receiving Serve',
        'description': 'Measures ability to score when receiving serve. Higher indicates better offensive conversion.',
        'display_as_percentage': True
    },
    'reception_percentage': {
        'name': 'Reception Percentage',
        'formula': 'Good Receives / Total Reception Attempts',
        'description': 'Measures reception quality - percentage of successful (good) receptions. Higher indicates better first contact.',
        'display_as_percentage': True
    },
    'serve_point_percentage': {
        'name': 'Serve Point Percentage',
        'formula': 'Points Won When Serving / Total Service Rallies',
        'description': 'Measures ability to score when serving. Higher indicates better service pressure and point conversion.',
        'display_as_percentage': True
    },
    'first_ball_efficiency': {
        'name': 'First Ball Efficiency',
        'formula': 'Attack Kills After Perfect Pass / Total Attacks After Perfect Pass',
        'description': 'Measures attack success rate after perfect reception (pass quality = 1). Higher indicates better offensive execution.',
        'display_as_percentage': True
    }
}

def display_team_overview(analyzer, loader=None):
    """Display team performance overview"""
    # Top: Match result banner (requires loader with team sheets)
    if loader is not None and hasattr(loader, 'team_data') and loader.team_data:
        set_results = pt.compute_set_results_from_loader(loader) if hasattr(pt, 'compute_set_results_from_loader') else []
        summary = pt.get_match_summary(set_results) if hasattr(pt, 'get_match_summary') else {'label': 'No sets', 'outcome': 'N/A'}
        opponent = st.session_state.get('opponent_name') or 'Opponent'
        banner_color = "#e6ffed" if summary['outcome'] == 'Win' else ("#ffecec" if summary['outcome'] == 'Loss' else "#f5f5f5")
        st.markdown(f"""
        <div style="padding:14px 18px;border:2px solid #040C7B;border-radius:12px;background:{banner_color};margin-bottom:12px;">
            <div style="font-size:20px;font-weight:700;color:#040C7B;">Match Result: {summary['label']}</div>
            <div style="color:#040C7B;opacity:0.85;margin-top:4px;">vs {opponent}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown('<h2 class="main-header">🏆 Team Performance Overview</h2>', unsafe_allow_html=True)
    
    # Calculate team metrics
    team_stats = analyzer.calculate_team_metrics()
    
    if team_stats is None:
        st.error("No team statistics available")
        return
    
    # Performance targets (competitive club level) - use constants
    TARGETS = KPI_TARGETS.copy()
    for key in TARGETS:
        TARGETS[key]['label'] = f"Target: {TARGETS[key]['optimal']:.0%}+"
    
    # Prefer loader-derived friendly KPIs if available
    kpis = None
    if loader is not None and hasattr(loader, 'team_data') and loader.team_data and hasattr(pt, 'compute_team_kpis_from_loader'):
        try:
            kpis = pt.compute_team_kpis_from_loader(loader)
        except Exception:
            kpis = None

    # Add global CSS for delta styling - only red/green arrows, no background
    st.markdown(
        """
        <style>
        /* Remove background colors from delta metrics, only show colored arrows */
        div[data-testid="stMetricDelta"] {
            background-color: transparent !important;
            padding: 0 !important;
        }
        div[data-testid="stMetricDelta"] svg {
            /* Ensure only red/green arrows, no yellow */
            color: inherit !important;
        }
        /* Ensure delta text has no background */
        div[data-testid="stMetricDelta"] > div {
            background-color: transparent !important;
        }
        /* Increase metric value font size */
        div[data-testid="stMetricValue"] {
            font-size: 2.5rem !important;
            font-weight: 700 !important;
        }
        /* Increase metric label font size */
        div[data-testid="stMetricLabel"] {
            font-size: 1.1rem !important;
            font-weight: 600 !important;
        }
        /* Increase delta text font size */
        div[data-testid="stMetricDelta"] {
            font-size: 1rem !important;
        }
        /* Make info buttons larger and more prominent */
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
        /* Reduce metric card padding to minimum */
        div[data-testid="stMetricContainer"] {
            padding: 0.25rem 0.5rem !important;
        }
        /* Reduce padding on all metric-related containers */
        div[data-testid="stMetricLabel"],
        div[data-testid="stMetricValue"],
        div[data-testid="stMetricDelta"] {
            padding: 0 !important;
        }
        /* Reduce column padding and height */
        div[data-testid="column"] {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            padding-top: 0.25rem !important;
            padding-bottom: 0.25rem !important;
            min-height: auto !important;
            height: auto !important;
        }
        /* Reduce height of column inner containers */
        div[data-testid="column"] > div {
            min-height: auto !important;
            height: auto !important;
        }
        /* Reduce element container padding and height */
        .element-container {
            padding: 0 !important;
            min-height: auto !important;
            height: auto !important;
        }
        /* Specifically reduce height of markdown and metric containers */
        div[data-testid="stMarkdownContainer"],
        div[data-testid="stMetricContainer"] {
            min-height: auto !important;
            height: auto !important;
        }
        /* Make metric titles larger */
        h4, h3 {
            font-size: 1.15rem !important;
        }
        /* Increase markdown text size for metric labels - tight line height */
        div[data-testid="stMarkdownContainer"] p strong {
            font-size: 1.15rem !important;
            line-height: 1.2 !important;
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
        }
        div[data-testid="stMarkdownContainer"] p {
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
            line-height: 1.2 !important;
        }
        /* Aggressively reduce spacing between metric label and value */
        div[data-testid="stMetricContainer"] {
            gap: 0rem !important;
            padding-top: 0 !important;
            margin-top: 0 !important;
        }
        div[data-testid="stMetricLabel"] {
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
        }
        div[data-testid="stMetricValue"] {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        /* Aggressively reduce spacing in markdown containers for metric titles */
        div[data-testid="stMarkdownContainer"] {
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
            margin-top: 0 !important;
        }
        /* CONTROL SPACING BETWEEN TITLE AND METRIC VALUE - DIRECT APPROACH */
        /* Reset all element-container margins globally first */
        .element-container {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        /* Add 0.5rem spacing between title and metric using adjacent sibling selector */
        /* Target element-container that comes after nested columns */
        div[data-testid="column"] > .element-container:has(div[data-testid="column"]) + .element-container {
            margin-top: 0.5rem !important;
        }
        /* Ensure markdown and metric containers themselves have no margins */
        div[data-testid="stMarkdownContainer"],
        div[data-testid="stMetricContainer"] {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        /* Remove all spacing from paragraph elements */
        div[data-testid="stMarkdownContainer"] p {
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1 !important;
        }
        div[data-testid="stMarkdownContainer"] p strong {
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Create columns for primary metrics - Row 1: 4 metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Serving Point Rate (formerly Break-point Rate): Percentage of serving points won / total serving points
        serving_point_rate = (kpis['break_point_rate'] if kpis else team_stats.get('serve_point_percentage', 0.0))
        serving_point_targets = KPI_TARGETS.get('break_point_rate', {'min': 0.50, 'max': 0.60, 'optimal': 0.55})
        serving_point_color = get_performance_color(serving_point_rate, serving_point_targets['min'], serving_point_targets['max'], serving_point_targets['optimal'])
        
        # Create label with inline info icon
        label_col, icon_col, metric_col = st.columns([12, 1, 0.1], gap="small")
        with label_col:
            st.markdown(f'**Serving Point Rate {serving_point_color}**', unsafe_allow_html=True)
        with icon_col:
            if st.button("ℹ️", key="info_serving_point_btn", help="Show definition", use_container_width=False, type="secondary"):
                st.session_state['show_info_serving_point'] = not st.session_state.get('show_info_serving_point', False)
        
        # Calculate delta vs target
        target_optimal = serving_point_targets['optimal']
        delta_vs_target = serving_point_rate - target_optimal
        delta_color = "normal" if serving_point_rate >= target_optimal else "inverse"
        delta_label = f"{delta_vs_target:+.1%} vs target ({target_optimal:.0%})"
        
        st.metric(
            label="",
            value=f"{serving_point_rate:.1%}",
            delta=delta_label,
            delta_color=delta_color,
            help="Points Won When Serving / Total Serving Rallies"
        )
        
        # CSS to position icon inline with label
        st.markdown(
            """
            <style>
                div[data-testid="column"]:has(button[key="info_serving_point_btn"]) {
                    position: relative;
                    margin-left: -40px;
                    margin-top: -36px;
                }
                button[key="info_serving_point_btn"] {
                    background: transparent !important;
                    border: none !important;
                    color: #040C7B !important;
                    font-size: 0.95rem !important;
                    padding: 0 !important;
                    opacity: 0.65;
                    margin: 0 !important;
                }
                button[key="info_serving_point_btn"]:hover {
                    opacity: 1;
                    transform: scale(1.2);
                }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        if st.session_state.get('show_info_serving_point', False):
            st.info(f"**Serving Point Rate**\n\n**Formula:** Points Won When Serving / Total Serving Rallies\n\n**Description:** Percentage of rallies won when your team is serving. Higher indicates better service pressure and point conversion.\n\n**Current Calculation:** {serving_point_rate:.1%}")
    
    with col2:
        # Serve In Rate: (Aces + Good Serves) / Total Serve Attempts
        service_value = (kpis['serve_in_rate'] if kpis else None)
        if service_value is None:
            serves = analyzer.match_data[analyzer.match_data['action'] == 'serve']
            in_play = len(serves[(serves['outcome'].isin(['ace','good']))])
            attempts = len(serves)
            service_value = (in_play / attempts) if attempts > 0 else 0.0
        serve_in_targets = KPI_TARGETS.get('serve_in_rate', {'min': 0.85, 'max': 0.95, 'optimal': 0.90})
        service_color = get_performance_color(service_value, serve_in_targets['min'], serve_in_targets['max'], serve_in_targets['optimal'])
        
        # Create label with inline info icon positioned next to colored dot
        label_col, icon_col, metric_col = st.columns([12, 1, 0.1], gap="small")
        with label_col:
            st.markdown(f'**Serve In-Rate {service_color}**', unsafe_allow_html=True)
        with icon_col:
            if st.button("ℹ️", key="info_service_btn", help="Show definition", use_container_width=False, type="secondary"):
                st.session_state['show_info_service'] = not st.session_state.get('show_info_service', False)
        
        # Calculate delta vs target
        target_optimal = serve_in_targets['optimal']
        delta_vs_target = service_value - target_optimal
        delta_color = "normal" if service_value >= target_optimal else "inverse"
        delta_label = f"{delta_vs_target:+.1%} vs target ({target_optimal:.0%})"
        
        st.metric(
            label="",  # Empty label since we show it above
            value=f"{service_value:.1%}",
            delta=delta_label,
            delta_color=delta_color,
            help="(Aces + Good Serves) / Total Serve Attempts"
        )
        
        # CSS to position icon inline with label
        st.markdown(
            """
            <style>
                /* Position icon column to overlay on metric label */
                div[data-testid="column"]:has(button[key="info_service_btn"]) {
                    position: relative;
                    margin-left: -40px;
                    margin-top: -36px;
                }
                button[key="info_service_btn"] {
                    background: transparent !important;
                    border: none !important;
                    color: #040C7B !important;
                    font-size: 0.95rem !important;
                    padding: 0 !important;
                    opacity: 0.65;
                    margin: 0 !important;
                }
                button[key="info_service_btn"]:hover {
                    opacity: 1;
                    transform: scale(1.2);
                }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        if st.session_state.get('show_info_service', False):
            st.info(f"**Serve In-Rate**\n\n**Formula:** (Aces + Good Serves) / Total Serve Attempts\n\n**Description:** Percentage of serves that stay in play (ace or good). Higher indicates better serve consistency.\n\n**Current Calculation:** {service_value:.1%}")
    
    with col3:
        # Attack Kill %: Kills / Total Attack Attempts (including kills, good, errors)
        attack_value = (kpis['attack_kill_pct'] if kpis else team_stats.get('kill_percentage', 0.0))
        if attack_value is None or (kpis is None and 'kill_percentage' not in team_stats):
            # Fallback: calculate from match data
            attacks = analyzer.match_data[analyzer.match_data['action'] == 'attack']
            attack_kills = len(attacks[attacks['outcome'] == 'kill'])
            attack_total = len(attacks)
            attack_value = (attack_kills / attack_total) if attack_total > 0 else 0.0
        attack_targets = KPI_TARGETS.get('kill_percentage', {'min': 0.35, 'max': 0.50, 'optimal': 0.42})
        attack_color = get_performance_color(attack_value, attack_targets['min'], attack_targets['max'], attack_targets['optimal'])
        
        # Create label with inline info icon positioned next to colored dot
        label_col, icon_col, metric_col = st.columns([12, 1, 0.1], gap="small")
        with label_col:
            st.markdown(f'**Attack Kill % {attack_color}**', unsafe_allow_html=True)
        with icon_col:
            if st.button("ℹ️", key="info_attack_btn", help="Show definition", use_container_width=False, type="secondary"):
                st.session_state['show_info_attack'] = not st.session_state.get('show_info_attack', False)
        
        # Calculate delta vs target
        target_optimal = attack_targets['optimal']
        delta_vs_target = attack_value - target_optimal
        delta_color = "normal" if attack_value >= target_optimal else "inverse"
        delta_label = f"{delta_vs_target:+.1%} vs target ({target_optimal:.0%})"
        
        st.metric(
            label="",  # Empty label since we show it above
            value=f"{attack_value:.1%}",
            delta=delta_label,
            delta_color=delta_color,
            help="Attack Kills / Total Attack Attempts (Kills + Good + Errors)"
        )
        
        # CSS to position icon inline with label
        st.markdown(
            """
            <style>
                /* Position icon column to overlay on metric label */
                div[data-testid="column"]:has(button[key="info_attack_btn"]) {
                    position: relative;
                    margin-left: -40px;
                    margin-top: -36px;
                }
                button[key="info_attack_btn"] {
                    background: transparent !important;
                    border: none !important;
                    color: #040C7B !important;
                    font-size: 0.95rem !important;
                    padding: 0 !important;
                    opacity: 0.65;
                    margin: 0 !important;
                }
                button[key="info_attack_btn"]:hover {
                    opacity: 1;
                    transform: scale(1.2);
                }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        if st.session_state.get('show_info_attack', False):
            st.info(f"**Attack Kill %**\n\n**Formula:** Attack Kills / Total Attack Attempts (Kills + Good Attacks + Errors)\n\n**Description:** Percentage of attacks resulting in kills. Higher indicates better offensive efficiency.\n\n**Current Calculation:** {attack_value:.1%}")
    
    with col4:
        # Dig Rate: Good digs / total digs
        dig_rate = (kpis['dig_rate'] if kpis else None)
        if dig_rate is None:
            digs = analyzer.match_data[analyzer.match_data['action'] == 'dig']
            dig_good = len(digs[digs['outcome'] == 'good'])
            dig_total = len(digs)
            dig_rate = (dig_good / dig_total) if dig_total > 0 else 0.0
        dig_targets = KPI_TARGETS.get('dig_rate', {'min': 0.65, 'max': 0.80, 'optimal': 0.70})
        dig_color = get_performance_color(dig_rate, dig_targets['min'], dig_targets['max'], dig_targets['optimal'])
        
        # Create label with inline info icon
        label_col, icon_col, metric_col = st.columns([12, 1, 0.1], gap="small")
        with label_col:
            st.markdown(f'**Dig Rate {dig_color}**', unsafe_allow_html=True)
        with icon_col:
            if st.button("ℹ️", key="info_dig_btn", help="Show definition", use_container_width=False, type="secondary"):
                st.session_state['show_info_dig'] = not st.session_state.get('show_info_dig', False)
        
        # Calculate delta vs target
        target_optimal = dig_targets['optimal']
        delta_vs_target = dig_rate - target_optimal
        delta_color = "normal" if dig_rate >= target_optimal else "inverse"
        delta_label = f"{delta_vs_target:+.1%} vs target ({target_optimal:.0%})"
        
        st.metric(
            label="",
            value=f"{dig_rate:.1%}",
            delta=delta_label,
            delta_color=delta_color,
            help="Good Digs / Total Dig Attempts"
        )
        
        # CSS to position icon inline with label
        st.markdown(
            """
            <style>
                div[data-testid="column"]:has(button[key="info_dig_btn"]) {
                    position: relative;
                    margin-left: -40px;
                    margin-top: -36px;
                }
                button[key="info_dig_btn"] {
                    background: transparent !important;
                    border: none !important;
                    color: #040C7B !important;
                    font-size: 0.95rem !important;
                    padding: 0 !important;
                    opacity: 0.65;
                    margin: 0 !important;
                }
                button[key="info_dig_btn"]:hover {
                    opacity: 1;
                    transform: scale(1.2);
                }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        if st.session_state.get('show_info_dig', False):
            st.info(f"**Dig Rate**\n\n**Formula:** Good Digs / Total Dig Attempts\n\n**Description:** Percentage of successful digs. Higher indicates better defensive ball control.\n\n**Current Calculation:** {dig_rate:.1%}")
    
    # Row 2: 4 metrics
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        # Receiving Point Rate (formerly Side-out %): Percentage of receiving points won / total receiving points
        receiving_point_rate = (kpis['side_out_efficiency'] if kpis else team_stats['side_out_percentage'])
        receiving_point_targets = KPI_TARGETS.get('side_out_percentage', {'min': 0.65, 'max': 0.75, 'optimal': 0.70})
        receiving_point_color = get_performance_color(receiving_point_rate, receiving_point_targets['min'], receiving_point_targets['max'], receiving_point_targets['optimal'])
        
        # Create label with inline info icon
        label_col, icon_col, metric_col = st.columns([12, 1, 0.1], gap="small")
        with label_col:
            st.markdown(f'**Receiving Point Rate {receiving_point_color}**', unsafe_allow_html=True)
        with icon_col:
            if st.button("ℹ️", key="info_receiving_point_btn", help="Show definition", use_container_width=False, type="secondary"):
                st.session_state['show_info_receiving_point'] = not st.session_state.get('show_info_receiving_point', False)
        
        target_optimal = receiving_point_targets['optimal']
        delta_vs_target = receiving_point_rate - target_optimal
        delta_color = "normal" if receiving_point_rate >= target_optimal else "inverse"
        delta_label = f"{delta_vs_target:+.1%} vs target ({target_optimal:.0%})"
        st.metric(
            label="",
            value=f"{receiving_point_rate:.1%}",
            delta=delta_label,
            delta_color=delta_color,
            help="Points Won When Receiving / Total Receiving Rallies"
        )
        
        # CSS to position icon inline with label
        st.markdown(
            """
            <style>
                div[data-testid="column"]:has(button[key="info_receiving_point_btn"]) {
                    position: relative;
                    margin-left: -40px;
                    margin-top: -36px;
                }
                button[key="info_receiving_point_btn"] {
                    background: transparent !important;
                    border: none !important;
                    color: #040C7B !important;
                    font-size: 0.95rem !important;
                    padding: 0 !important;
                    opacity: 0.65;
                    margin: 0 !important;
                }
                button[key="info_receiving_point_btn"]:hover {
                    opacity: 1;
                    transform: scale(1.2);
                }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        if st.session_state.get('show_info_receiving_point', False):
            st.info(f"**Receiving Point Rate**\n\n**Formula:** Points Won When Receiving / Total Receiving Rallies\n\n**Description:** Measures ability to score on opponent serve. Higher indicates better offensive conversion when receiving.\n\n**Current Calculation:** {receiving_point_rate:.1%}")
    
    with col6:
        # Reception Quality: Percentage of good receptions / total receptions
        reception_quality = (kpis['reception_quality'] if kpis else None)
        if reception_quality is None:
            receives = analyzer.match_data[analyzer.match_data['action'] == 'receive']
            rec_good = len(receives[receives['outcome'] == 'good'])
            rec_total = len(receives)
            reception_quality = (rec_good / rec_total) if rec_total > 0 else 0.0
        reception_targets = KPI_TARGETS.get('reception_quality', {'min': 0.70, 'max': 0.85, 'optimal': 0.75})
        reception_color = get_performance_color(reception_quality, reception_targets['min'], reception_targets['max'], reception_targets['optimal'])
        
        # Create label with inline info icon
        label_col, icon_col, metric_col = st.columns([12, 1, 0.1], gap="small")
        with label_col:
            st.markdown(f'**Reception Quality {reception_color}**', unsafe_allow_html=True)
        with icon_col:
            if st.button("ℹ️", key="info_reception_btn", help="Show definition", use_container_width=False, type="secondary"):
                st.session_state['show_info_reception'] = not st.session_state.get('show_info_reception', False)
        
        # Calculate delta vs target
        target_optimal = reception_targets['optimal']
        delta_vs_target = reception_quality - target_optimal
        delta_color = "normal" if reception_quality >= target_optimal else "inverse"
        delta_label = f"{delta_vs_target:+.1%} vs target ({target_optimal:.0%})"
        
        st.metric(
            label="",
            value=f"{reception_quality:.1%}",
            delta=delta_label,
            delta_color=delta_color,
            help="Good Receptions / Total Reception Attempts"
        )
        
        # CSS to position icon inline with label
        st.markdown(
            """
            <style>
                div[data-testid="column"]:has(button[key="info_reception_btn"]) {
                    position: relative;
                    margin-left: -40px;
                    margin-top: -36px;
                }
                button[key="info_reception_btn"] {
                    background: transparent !important;
                    border: none !important;
                    color: #040C7B !important;
                    font-size: 0.95rem !important;
                    padding: 0 !important;
                    opacity: 0.65;
                    margin: 0 !important;
                }
                button[key="info_reception_btn"]:hover {
                    opacity: 1;
                    transform: scale(1.2);
                }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        if st.session_state.get('show_info_reception', False):
            st.info(f"**Reception Quality**\n\n**Formula:** Good Receptions / Total Reception Attempts\n\n**Description:** Percentage of successful (good) receptions. Higher indicates better first contact quality.\n\n**Current Calculation:** {reception_quality:.1%}")
    
    with col7:
        # Block Kill Percentage: Block kills / total block attempts
        block_kill_pct = (kpis['block_kill_pct'] if kpis else None)
        if block_kill_pct is None:
            blocks = analyzer.match_data[analyzer.match_data['action'] == 'block']
            block_kills = len(blocks[blocks['outcome'] == 'kill'])
            block_total = len(blocks)
            block_kill_pct = (block_kills / block_total) if block_total > 0 else 0.0
        block_kill_targets = KPI_TARGETS.get('block_kill_percentage', {'min': 0.05, 'max': 0.15, 'optimal': 0.10})
        block_kill_color = get_performance_color(block_kill_pct, block_kill_targets['min'], block_kill_targets['max'], block_kill_targets['optimal'])
        
        # Create label with inline info icon
        label_col, icon_col, metric_col = st.columns([12, 1, 0.1], gap="small")
        with label_col:
            st.markdown(f'**Block Kill % {block_kill_color}**', unsafe_allow_html=True)
        with icon_col:
            if st.button("ℹ️", key="info_block_kill_btn", help="Show definition", use_container_width=False, type="secondary"):
                st.session_state['show_info_block_kill'] = not st.session_state.get('show_info_block_kill', False)
        
        # Calculate delta vs target
        target_optimal = block_kill_targets['optimal']
        delta_vs_target = block_kill_pct - target_optimal
        delta_color = "normal" if block_kill_pct >= target_optimal else "inverse"
        delta_label = f"{delta_vs_target:+.1%} vs target ({target_optimal:.0%})"
        
        st.metric(
            label="",
            value=f"{block_kill_pct:.1%}",
            delta=delta_label,
            delta_color=delta_color,
            help="Block Kills / Total Block Attempts"
        )
        
        # CSS to position icon inline with label
        st.markdown(
            """
            <style>
                div[data-testid="column"]:has(button[key="info_block_kill_btn"]) {
                    position: relative;
                    margin-left: -40px;
                    margin-top: -36px;
                }
                button[key="info_block_kill_btn"] {
                    background: transparent !important;
                    border: none !important;
                    color: #040C7B !important;
                    font-size: 0.95rem !important;
                    padding: 0 !important;
                    opacity: 0.65;
                    margin: 0 !important;
                }
                button[key="info_block_kill_btn"]:hover {
                    opacity: 1;
                    transform: scale(1.2);
                }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        if st.session_state.get('show_info_block_kill', False):
            st.info(f"**Block Kill %**\n\n**Formula:** Block Kills / Total Block Attempts\n\n**Description:** Percentage of blocks resulting directly in points. Higher indicates better defensive scoring.\n\n**Current Calculation:** {block_kill_pct:.1%}")
    
    with col8:
        # Average Actions per Point: Total actions / total points (NO TARGET)
        avg_actions = (kpis['avg_actions_per_point'] if kpis else None)
        if avg_actions is None:
            # Calculate from analyzer data
            total_actions = len(analyzer.match_data)
            # Estimate total points from serves + receives or use team data
            if loader and hasattr(loader, 'team_data') and loader.team_data:
                serving_rallies = sum(int(stats.get('serving_rallies', 0) or 0) for stats in loader.team_data.values())
                receiving_rallies = sum(int(stats.get('receiving_rallies', 0) or 0) for stats in loader.team_data.values())
                total_points = serving_rallies + receiving_rallies
            else:
                # Fallback: estimate from unique point_ids or set/rotation combinations
                if 'point_id' in analyzer.match_data.columns:
                    total_points = analyzer.match_data['point_id'].nunique()
                else:
                    total_points = analyzer.match_data['set_number'].nunique() * 25  # Rough estimate
            avg_actions = (total_actions / total_points) if total_points > 0 else 0.0
        
        # No target for this metric - no colored dot
        # Create label with inline info icon
        label_col, icon_col, metric_col = st.columns([12, 1, 0.1], gap="small")
        with label_col:
            st.markdown(f'**Avg Actions/Point**', unsafe_allow_html=True)
        with icon_col:
            if st.button("ℹ️", key="info_avg_actions_btn", help="Show definition", use_container_width=False, type="secondary"):
                st.session_state['show_info_avg_actions'] = not st.session_state.get('show_info_avg_actions', False)
        
        st.metric(
            label="",
            value=f"{avg_actions:.1f}",
            help="Total Actions / Total Points Played"
        )
        
        # CSS to position icon inline with label
        st.markdown(
            """
            <style>
                div[data-testid="column"]:has(button[key="info_avg_actions_btn"]) {
                    position: relative;
                    margin-left: -40px;
                    margin-top: -36px;
                }
                button[key="info_avg_actions_btn"] {
                    background: transparent !important;
                    border: none !important;
                    color: #040C7B !important;
                    font-size: 0.95rem !important;
                    padding: 0 !important;
                    opacity: 0.65;
                    margin: 0 !important;
                }
                button[key="info_avg_actions_btn"]:hover {
                    opacity: 1;
                    transform: scale(1.2);
                }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        if st.session_state.get('show_info_avg_actions', False):
            st.info(f"**Average Actions per Point**\n\n**Formula:** Total Actions / Total Points Played\n\n**Description:** Average number of actions (attacks, serves, blocks, etc.) per point. Higher indicates longer rallies.\n\n**Current Calculation:** {avg_actions:.1f}")

def create_team_charts(analyzer: MatchAnalyzer) -> None:
    """Create team performance charts"""
    st.markdown("### 📈 Team Performance Charts")
    
    df = analyzer.match_data
    
    # Action distribution chart
    col1, col2 = st.columns(2)
    
    with col1:
        action_counts = df['action'].value_counts()
        fig_actions = px.pie(
            values=action_counts.values,
            names=action_counts.index,
            title="Action Distribution",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_actions.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>',
            marker=dict(line=dict(color='rgba(0,0,0,0.2)', width=1))
        )
        fig_actions = apply_beautiful_theme(fig_actions, "Action Distribution")
        st.plotly_chart(fig_actions, use_container_width=True, config=plotly_config)
        
        # Add note about action distribution
        dominant_action = action_counts.idxmax()
        dominant_pct = (action_counts.max() / action_counts.sum()) * 100
        if dominant_pct > 30:
            st.caption(f"💡 **Note:** {dominant_action.capitalize()} actions represent {dominant_pct:.1f}% of total actions")
    
    with col2:
        outcome_counts = df['outcome'].value_counts()
        # Fix y-axis to show all data with padding
        max_value = outcome_counts.values.max()
        y_max = max_value * 1.15  # Add 15% padding
        
        fig_outcomes = px.bar(
            x=outcome_counts.index,
            y=outcome_counts.values,
            title="Outcome Distribution",
            labels={'x': 'Outcome', 'y': 'Count'},
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_outcomes.update_xaxes(
            title_font=dict(color='#040C7B'),
            tickfont=dict(color='#040C7B')
        )
        fig_outcomes.update_yaxes(title_font=dict(color='#040C7B'))
        fig_outcomes.update_traces(
            marker=dict(line=dict(color='rgba(0,0,0,0.2)', width=1)),
            hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
        )
        fig_outcomes = apply_beautiful_theme(fig_outcomes, "Outcome Distribution", height=400)
        fig_outcomes.update_layout(
            showlegend=False,
            yaxis=dict(range=[0, y_max])
        )
        st.plotly_chart(fig_outcomes, use_container_width=True, config=plotly_config)
    
    # Set-by-set performance - Enhanced with efficiency trends
    st.markdown("### 🎯 Set-by-Set Performance")
    
    set_stats = df.groupby('set_number').agg({
        'action': 'count',
        'outcome': lambda x: (x == 'kill').sum()
    }).rename(columns={'action': 'Total_Actions', 'outcome': 'Kills'})
    
    # Calculate efficiency metrics by set
    set_metrics = []
    for set_num in set_stats.index:
        set_df = df[df['set_number'] == set_num]
        
        # Attack efficiency
        attacks = set_df[set_df['action'] == 'attack']
        attack_kills = len(attacks[attacks['outcome'] == 'kill'])
        attack_errors = len(attacks[attacks['outcome'] == 'error'])
        attack_eff = (attack_kills - attack_errors) / len(attacks) if len(attacks) > 0 else 0
        
        # Service efficiency
        serves = set_df[set_df['action'] == 'serve']
        service_aces = len(serves[serves['outcome'] == 'ace'])
        service_errors = len(serves[serves['outcome'] == 'error'])
        service_eff = (service_aces - service_errors) / len(serves) if len(serves) > 0 else 0
        
        # Errors
        errors = len(set_df[set_df['outcome'] == 'error'])
        
        set_metrics.append({
            'Set': set_num,
            'Total Actions': set_stats.loc[set_num, 'Total_Actions'],
            'Kills': set_stats.loc[set_num, 'Kills'],
            'Attack Efficiency': attack_eff,
            'Service Efficiency': service_eff,
            'Errors': errors
        })
    
    set_metrics_df = pd.DataFrame(set_metrics)
    
    fig_set = make_subplots(
        rows=1, cols=3,
        subplot_titles=('Total Actions by Set', 'Attack Efficiency by Set', 'Errors by Set'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Total Actions
    fig_set.add_trace(
        go.Bar(x=set_stats.index, y=set_stats['Total_Actions'], name='Total Actions',
               marker=dict(
                   color=set_stats['Total_Actions'],
                   colorscale=[[0, CHART_COLORS['primary']], [1, CHART_COLORS['secondary']]],
                   line=dict(width=2)
               ),
               showlegend=False),
        row=1, col=1
    )
    
    # Attack Efficiency
    fig_set.add_trace(
        go.Bar(x=set_metrics_df['Set'], y=set_metrics_df['Attack Efficiency'], name='Attack Efficiency',
               marker=dict(
                   color=set_metrics_df['Attack Efficiency'],
                   colorscale=[[0, CHART_COLORS['success']], [1, '#06D6A0']],
                   line=dict(width=2)
               ),
               showlegend=False),
        row=1, col=2
    )
    
    # Errors
    fig_set.add_trace(
        go.Bar(x=set_metrics_df['Set'], y=set_metrics_df['Errors'], name='Errors',
               marker=dict(
                   color=set_metrics_df['Errors'],
                   colorscale=[[0, CHART_COLORS['warning']], [1, CHART_COLORS['danger']]],
                   line=dict(width=2)
               ),
               showlegend=False),
        row=1, col=3
    )
    
    # Update axes with beautiful styling
    fig_set.update_xaxes(
        title_text="Set Number", 
        row=1, col=1, 
        dtick=1,
        gridcolor='rgba(102, 126, 234, 0.1)',
        linecolor='rgba(102, 126, 234, 0.3)',
        title_font=dict(color='#040C7B')
    )
    fig_set.update_xaxes(
        title_text="Set Number", 
        row=1, col=2, 
        dtick=1,
        gridcolor='rgba(102, 126, 234, 0.1)',
        linecolor='rgba(102, 126, 234, 0.3)',
        title_font=dict(color='#040C7B')
    )
    fig_set.update_xaxes(
        title_text="Set Number", 
        row=1, col=3, 
        dtick=1,
        gridcolor='rgba(102, 126, 234, 0.1)',
        linecolor='rgba(102, 126, 234, 0.3)',
        title_font=dict(color='#040C7B')
    )
    
    fig_set.update_yaxes(
        title_text="Total Actions", 
        row=1, col=1,
        gridcolor='rgba(102, 126, 234, 0.1)',
        linecolor='rgba(102, 126, 234, 0.3)',
        title_font=dict(color='#040C7B')
    )
    fig_set.update_yaxes(
        title_text="Efficiency", 
        row=1, col=2, 
        tickformat='.1%',
        gridcolor='rgba(102, 126, 234, 0.1)',
        linecolor='rgba(102, 126, 234, 0.3)',
        title_font=dict(color='#040C7B')
    )
    fig_set.update_yaxes(
        title_text="Errors", 
        row=1, col=3,
        gridcolor='rgba(102, 126, 234, 0.1)',
        linecolor='rgba(102, 126, 234, 0.3)',
        title_font=dict(color='#040C7B')
    )
    
    fig_set.update_layout(
        height=450,
        showlegend=False,
        paper_bgcolor='rgba(255,255,255,0)',
        plot_bgcolor='rgba(255,255,255,0.95)',
        font=dict(family='Inter, sans-serif', size=12, color='#2C3E50'),
        title_font=dict(family='Poppins, sans-serif', size=16, color='#1A1A2E'),
        margin=dict(l=60, r=40, t=80, b=60)
    )
    
    # Apply beautiful theme
    fig_set = apply_beautiful_theme(fig_set, height=450)
    st.plotly_chart(fig_set, use_container_width=True, config=plotly_config)
    
    # Rotation Efficiency Heatmap
    st.markdown("### 🔄 Rotation Performance Analysis")
    rotation_stats = analyzer.analyze_rotation_performance()
    
    if rotation_stats:
        # Prepare data for heatmap
        rotations = sorted(rotation_stats.keys())
        metrics = ['attack_efficiency', 'service_efficiency', 'reception_percentage', 'block_efficiency']
        
        heatmap_data = []
        metric_labels = ['Attack Eff', 'Service Eff', 'Reception %', 'Block Eff']
        
        for rotation in rotations:
            row_data = []
            for metric in metrics:
                value = rotation_stats[rotation].get(metric, 0)
                row_data.append(value)
            heatmap_data.append(row_data)
        
        # Create heatmap
        fig_heatmap = go.Figure(data=go.Heatmap(
            z=heatmap_data,
            x=metric_labels,
            y=[f"Rotation {r}" for r in rotations],
            colorscale=[[0, '#FF4444'], [0.5, '#FFD700'], [1, '#00AA00']],  # Red to Yellow to Green
            text=[[f"{val:.1%}" if val != 0 else "" for val in row] for row in heatmap_data],
            texttemplate="%{text}",
            textfont={"size": 11},
            colorbar=dict(title="Efficiency")
        ))
        
        fig_heatmap.update_layout(
            title="Rotation Performance Heatmap",
            xaxis_title="Metric",
            yaxis_title="Rotation",
            height=400,
            font=dict(family='Inter, sans-serif', size=12, color='#040C7B'),
            paper_bgcolor='rgba(255,255,255,0)',
            plot_bgcolor='rgba(255,255,255,0.95)'
        )
        
        st.plotly_chart(fig_heatmap, use_container_width=True, config=plotly_config)
        
        # Display rotation summary table
        rotation_summary = []
        for rotation in rotations:
            stats = rotation_stats[rotation]
            rotation_summary.append({
                'Rotation': f"Rotation {rotation}",
                'Attack Eff': f"{stats.get('attack_efficiency', 0):.1%}",
                'Service Eff': f"{stats.get('service_efficiency', 0):.1%}",
                'Reception %': f"{stats.get('reception_percentage', 0):.1%}",
                'Block Eff': f"{stats.get('block_efficiency', 0):.1%}",
                'Total Actions': stats.get('total_actions', 0)
            })
        
        rotation_df = pd.DataFrame(rotation_summary)
        st.dataframe(rotation_df, use_container_width=True, hide_index=True)
    
    # Pass Quality Visualization
    team_stats_temp = analyzer.calculate_team_metrics()
    if team_stats_temp and team_stats_temp.get('perfect_passes', 0) + team_stats_temp.get('good_passes', 0) + team_stats_temp.get('poor_passes', 0) > 0:
        st.markdown("### 🎯 Pass Quality Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Pass Quality Distribution
            pass_data = {
                'Quality': ['Perfect (1)', 'Good (2)', 'Poor (3)'],
                'Count': [
                    team_stats_temp.get('perfect_passes', 0),
                    team_stats_temp.get('good_passes', 0),
                    team_stats_temp.get('poor_passes', 0)
                ]
            }
            pass_df = pd.DataFrame(pass_data)
            total_passes = pass_df['Count'].sum()
            pass_df['Percentage'] = (pass_df['Count'] / total_passes * 100) if total_passes > 0 else 0
            
            fig_pass = px.pie(
                pass_df,
                values='Count',
                names='Quality',
                title="Pass Quality Distribution",
                color='Quality',
                color_discrete_map={
                    'Perfect (1)': '#00AA00',
                    'Good (2)': '#FFD700',
                    'Poor (3)': '#FF4500'
                }
            )
            fig_pass.update_traces(textposition='inside', textinfo='percent+label+value')
            fig_pass = apply_beautiful_theme(fig_pass, "Pass Quality Distribution")
            st.plotly_chart(fig_pass, use_container_width=True, config=plotly_config)
        
        with col2:
            # Pass Quality to Attack Efficiency Correlation
            if 'pass_quality' in df.columns and team_stats_temp.get('first_ball_efficiency') is not None:
                # Calculate attack efficiency by pass quality
                pass_attack_stats = []
                for quality in [1, 2, 3]:
                    quality_label = ['Perfect', 'Good', 'Poor'][quality - 1]
                    quality_attacks = df[(df['action'] == 'attack') & (df['pass_quality'] == quality)]
                    if len(quality_attacks) > 0:
                        kills = len(quality_attacks[quality_attacks['outcome'] == 'kill'])
                        errors = len(quality_attacks[quality_attacks['outcome'] == 'error'])
                        efficiency = (kills - errors) / len(quality_attacks)
                        pass_attack_stats.append({
                            'Pass Quality': quality_label,
                            'Attack Efficiency': efficiency,
                            'Sample Size': len(quality_attacks)
                        })
                
                if pass_attack_stats:
                    pass_eff_df = pd.DataFrame(pass_attack_stats)
                    fig_pass_eff = px.bar(
                        pass_eff_df,
                        x='Pass Quality',
                        y='Attack Efficiency',
                        title="Attack Efficiency by Pass Quality",
                        color='Attack Efficiency',
                        color_continuous_scale=['#FF4500', '#FFD700', '#00AA00'],
                        text='Sample Size'
                    )
                    fig_pass_eff.update_traces(texttemplate='n=%{text}', textposition='outside')
                    fig_pass_eff.update_yaxes(tickformat='.1%')
                    fig_pass_eff = apply_beautiful_theme(fig_pass_eff, "Attack Efficiency by Pass Quality")
                    st.plotly_chart(fig_pass_eff, use_container_width=True, config=plotly_config)
    
    # Generate and display insights & recommendations
    st.markdown("---")
    team_stats = analyzer.calculate_team_metrics()
    
    if team_stats:
        # Use KPI_TARGETS constant
        TARGETS = KPI_TARGETS.copy()
        for key in TARGETS:
            TARGETS[key]['label'] = f"Target: {TARGETS[key]['optimal']:.0%}+"
        
        insights = generate_insights(analyzer, team_stats, TARGETS)
        if insights:
            display_insights_section(insights, team_stats, TARGETS)

def display_player_analysis(analyzer: MatchAnalyzer) -> None:
    """Display detailed player analysis"""
    st.markdown('<h2 class="main-header">👥 Player Analysis</h2>', unsafe_allow_html=True)
    
    # Calculate player metrics
    player_stats = analyzer.calculate_player_metrics()
    
    if player_stats is None:
        st.error("No player statistics available")
        return
    
    # Player selection with enhanced display
    players = list(player_stats.keys())
    
    # Create player selection with images and positions
    st.markdown("### 👥 Player Selection")
    
    # Create a custom player selection interface
    df = analyzer.match_data
    player_options = []
    for player in players:
        position = get_player_position(df, player)
        position_emoji = get_position_emoji(position)
        position_full = get_position_full_name(position)
        display_name = f"{position_emoji} {player} ({position_full})"
        player_options.append((display_name, player))
    
    # Use radio buttons for better visual selection
    selected_display = st.radio(
        "Choose a player for detailed analysis:",
        options=[opt[0] for opt in player_options],
        help="Select a player to see their detailed performance statistics with image and position info"
    )
    
    # Get the actual player name
    selected_player = None
    for display_name, player_name in player_options:
        if display_name == selected_display:
            selected_player = player_name
            break
    
    if selected_player:
        player_data = player_stats[selected_player]
        df = analyzer.match_data
        player_df = df[df['player'] == selected_player]
        
        # Get player position
        position = get_player_position(df, selected_player)
        
        # Display player image and basic info in sidebar
        display_player_image_and_info(selected_player, position, image_size=78, use_sidebar=True)
        
        # Check if player is primarily a setter (has many sets relative to other actions)
        total_sets = player_data.get('total_sets', 0)
        is_setter = total_sets > 0 and total_sets >= player_data['total_actions'] * SETTER_THRESHOLD
        
        # Player overview cards - adjust based on position
        if is_setter:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="Total Sets",
                    value=player_data.get('total_sets', 0)
                )
            
            with col2:
                setting_percentage = player_data.get('setting_percentage', 0)
                st.metric(
                    label="Setting Quality",
                    value=f"{setting_percentage:.1%}",
                    delta=f"{player_data.get('good_sets', 0)} good sets"
                )
            
            with col3:
                st.metric(
                    label="Attack Efficiency",
                    value=f"{player_data['attack_efficiency']:.1%}",
                    delta=f"{player_data['attack_kills']} kills, {player_data['attack_errors']} errors"
                )
            
            with col4:
                st.metric(
                    label="Service Efficiency",
                    value=f"{player_data['service_efficiency']:.1%}",
                    delta=f"{player_data['service_aces']} aces, {player_data['service_errors']} errors"
                )
        else:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    label="Total Actions",
                    value=player_data['total_actions']
                )
            
            with col2:
                st.metric(
                    label="Attack Efficiency",
                    value=f"{player_data['attack_efficiency']:.1%}",
                    delta=f"{player_data['attack_kills']} kills, {player_data['attack_errors']} errors"
                )
            
            with col3:
                st.metric(
                    label="Service Efficiency",
                    value=f"{player_data['service_efficiency']:.1%}",
                    delta=f"{player_data['service_aces']} aces, {player_data['service_errors']} errors"
                )
            
            with col4:
                st.metric(
                    label="Block Efficiency",
                    value=f"{player_data['block_efficiency']:.1%}",
                    delta=f"{player_data['block_kills']} kills, {player_data['block_errors']} errors"
            )
        
        # Setter-specific detailed analysis
        if is_setter:
            st.markdown(f"### 🎯 Setter-Specific Analysis for {selected_player}")
            
            # Calculate setter-specific metrics
            sets = player_df[player_df['action'] == 'set']
            
            if len(sets) > 0:
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 📊 Setting Distribution")
                    
                    # Setting quality breakdown
                    exceptional_sets = 0  # We don't track this separately in current data
                    good_sets = len(sets[sets['outcome'] == 'good'])
                    error_sets = len(sets[sets['outcome'] == 'error'])
                    total_sets_count = len(sets)
                    
                    setting_quality = {
                        'Quality': ['Good Sets', 'Error Sets'],
                        'Count': [good_sets, error_sets],
                        'Percentage': [
                            (good_sets / total_sets_count * 100) if total_sets_count > 0 else 0,
                            (error_sets / total_sets_count * 100) if total_sets_count > 0 else 0
                        ]
                    }
                    
                    fig_set_quality = px.pie(
                        values=[good_sets, error_sets],
                        names=['Good Sets', 'Error Sets'],
                        title="Setting Quality Distribution",
                        color_discrete_sequence=[CHART_COLORS['success'], CHART_COLORS['danger']]
                    )
                    fig_set_quality.update_traces(
                        textposition='inside', 
                        textinfo='percent+label',
                        marker=dict(line=dict(width=2))
                    )
                    fig_set_quality = apply_beautiful_theme(fig_set_quality, "Setting Quality Distribution")
                    st.plotly_chart(fig_set_quality, use_container_width=True, config=plotly_config)
                    
                    # Setting statistics table
                    setting_stats_data = {
                        'Metric': ['Total Sets', 'Good Sets', 'Error Sets', 'Setting %', 'Sets per Set'],
                        'Value': [
                            total_sets_count,
                            good_sets,
                            error_sets,
                            f"{(good_sets / total_sets_count * 100):.1f}%" if total_sets_count > 0 else "0.0%",
                            f"{(total_sets_count / len(df['set_number'].unique()) if len(df['set_number'].unique()) > 0 else 0):.1f}"
                        ]
                    }
                    setting_stats_df = pd.DataFrame(setting_stats_data)
                    st.dataframe(setting_stats_df, use_container_width=True, hide_index=True)
                
                with col2:
                    st.markdown("#### 📈 Setting Performance by Set")
                    
                    # Sets by set
                    sets_by_set = sets.groupby('set_number').size()
                    sets_by_set_df = pd.DataFrame({
                        'Set': sets_by_set.index,
                        'Sets': sets_by_set.values
                    })
                    
                    fig_sets_by_set = px.bar(
                        sets_by_set_df,
                        x='Set',
                        y='Sets',
                        title="Sets per Set (Workload)",
                        color='Sets',
                        color_continuous_scale=[CHART_COLORS['primary'], CHART_COLORS['secondary']]
                    )
                    fig_sets_by_set.update_traces(
                        marker=dict(line=dict(color='rgba(0,0,0,0.2)', width=1)),
                        hovertemplate='<b>Set %{x}</b><br>Sets: %{y}<extra></extra>'
                    )
                    fig_sets_by_set = apply_beautiful_theme(fig_sets_by_set, "Sets per Set (Workload)")
                    fig_sets_by_set.update_layout(showlegend=False)
                    st.plotly_chart(fig_sets_by_set, use_container_width=True, config=plotly_config)
                    
                    # Setting quality by set
                    setting_quality_by_set = []
                    for set_num in sets['set_number'].unique():
                        set_sets = sets[sets['set_number'] == set_num]
                        good = len(set_sets[set_sets['outcome'] == 'good'])
                        errors = len(set_sets[set_sets['outcome'] == 'error'])
                        total = len(set_sets)
                        quality_pct = (good / total * 100) if total > 0 else 0
                        setting_quality_by_set.append({
                            'Set': set_num,
                            'Good %': quality_pct,
                            'Good': good,
                            'Errors': errors,
                            'Total': total
                        })
                    
                    quality_df = pd.DataFrame(setting_quality_by_set)
                    fig_quality_trend = go.Figure()
                    fig_quality_trend.add_trace(go.Scatter(
                        x=quality_df['Set'],
                        y=quality_df['Good %']/100,
                        mode='lines+markers',
                        name='Setting Quality %',
                        line=dict(color=CHART_COLORS['success'], width=4, shape='spline'),
                        marker=dict(size=12, color='#00AA00', line=dict(width=2)),
                        fill='tonexty',
                        fillcolor='rgba(6, 167, 125, 0.1)'
                    ))
                    fig_quality_trend = apply_beautiful_theme(fig_quality_trend, "Setting Quality Trend Across Sets", height=350)
                    fig_quality_trend.update_layout(yaxis_tickformat='.0%', xaxis=dict(dtick=1), hovermode='x unified')
                    st.plotly_chart(fig_quality_trend, use_container_width=True, config=plotly_config)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown("#### 🔄 Setting by Rotation")
                    
                    # Sets by rotation
                    sets_by_rotation = sets.groupby('rotation').size()
                    rotation_list = list(range(1, 7))
                    sets_by_rot_data = []
                    for rot in rotation_list:
                        sets_by_rot_data.append({
                            'Rotation': rot,
                            'Sets': sets_by_rotation.get(rot, 0)
                        })
                    
                    sets_rot_df = pd.DataFrame(sets_by_rot_data)
                    
                    fig_sets_rotation = px.bar(
                        sets_rot_df,
                        x='Rotation',
                        y='Sets',
                        title="Setting Distribution by Rotation",
                        color='Sets',
                        color_continuous_scale=[CHART_COLORS['info'], CHART_COLORS['primary']]
                    )
                    fig_sets_rotation.update_traces(
                        marker=dict(line=dict(color='rgba(0,0,0,0.2)', width=1)),
                        hovertemplate='<b>Rotation %{x}</b><br>Sets: %{y}<extra></extra>'
                    )
                    fig_sets_rotation = apply_beautiful_theme(fig_sets_rotation, "Setting Distribution by Rotation")
                    fig_sets_rotation.update_layout(showlegend=False)
                    fig_sets_rotation.update_xaxes(dtick=1)
                    st.plotly_chart(fig_sets_rotation, use_container_width=True, config=plotly_config)
                
                with col2:
                    st.markdown("#### 🎯 Attack Correlation Analysis")
                    
                    # Analyze if sets lead to kills (attack correlation)
                    # Find attacks that happen after sets from this player
                    # This is simplified - in reality we'd track sequences
                    attacks = df[df['action'] == 'attack']
                    total_attacks = len(attacks)
                    kills_after_set = len(attacks[attacks['outcome'] == 'kill'])
                    
                    # Calculate approximate correlation
                    team_kills = len(df[df['outcome'] == 'kill'])
                    team_attacks = len(df[df['action'] == 'attack'])
                    team_kill_rate = team_kills / team_attacks if team_attacks > 0 else 0
                    
                    st.metric(
                        label="Team Attack Kill Rate",
                        value=f"{team_kill_rate:.1%}",
                        help="Percentage of attacks that result in kills (indirect measure of setting quality)"
                    )
                    
                    st.info(f"💡 **Note:** With {total_sets_count} sets, the setter enables approximately {total_sets_count} attack opportunities. Team kill rate is {team_kill_rate:.1%}.")
        
        # Detailed player stats (for all players)
        st.markdown(f"### 📊 Detailed Statistics for {selected_player}")
        
        if is_setter:
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.markdown("#### 🎯 Setting Statistics")
                setting_data = {
                    'Metric': ['Total Sets', 'Good Sets', 'Error Sets', 'Setting %'],
                    'Value': [
                        int(player_data.get('total_sets', 0)),
                        int(player_data.get('good_sets', 0)),
                        int(player_data.get('total_sets', 0) - player_data.get('good_sets', 0)),
                        f"{player_data.get('setting_percentage', 0):.1%}"
                    ]
                }
                setting_df = pd.DataFrame(setting_data)
                st.dataframe(setting_df, use_container_width=True, hide_index=True)
            
            with col2:
                st.markdown("#### 🏐 Attack Statistics")
                attack_data = {
                    'Metric': ['Attempts', 'Kills', 'Errors', 'Efficiency'],
                    'Value': [
                        int(player_data['attack_attempts']),
                        int(player_data['attack_kills']),
                        int(player_data['attack_errors']),
                        f"{player_data['attack_efficiency']:.1%}"
                    ]
                }
                attack_df = pd.DataFrame(attack_data)
                st.dataframe(attack_df, use_container_width=True, hide_index=True)
            
            with col3:
                st.markdown("#### 🎯 Service Statistics")
                service_data = {
                    'Metric': ['Attempts', 'Aces', 'Errors', 'Efficiency'],
                    'Value': [
                        int(player_data['service_attempts']),
                        int(player_data['service_aces']),
                        int(player_data['service_errors']),
                        f"{player_data['service_efficiency']:.1%}"
                    ]
                }
                service_df = pd.DataFrame(service_data)
                st.dataframe(service_df, use_container_width=True, hide_index=True)
            
            with col4:
                st.markdown("#### 🛡️ Block Statistics")
                block_data = {
                    'Metric': ['Attempts', 'Kills', 'Errors', 'Efficiency'],
                    'Value': [
                        int(player_data['block_attempts']),
                        int(player_data['block_kills']),
                        int(player_data['block_errors']),
                        f"{player_data['block_efficiency']:.1%}"
                    ]
                }
                block_df = pd.DataFrame(block_data)
                st.dataframe(block_df, use_container_width=True, hide_index=True)
        else:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("#### 🏐 Attack Statistics")
                attack_data = {
                    'Metric': ['Attempts', 'Kills', 'Errors', 'Efficiency'],
                    'Value': [
                        int(player_data['attack_attempts']),
                        int(player_data['attack_kills']),
                        int(player_data['attack_errors']),
                        f"{player_data['attack_efficiency']:.1%}"
                    ]
                }
                attack_df = pd.DataFrame(attack_data)
                st.dataframe(attack_df, use_container_width=True, hide_index=True)
            
            with col2:
                st.markdown("#### 🎯 Service Statistics")
                service_data = {
                    'Metric': ['Attempts', 'Aces', 'Errors', 'Efficiency'],
                    'Value': [
                        int(player_data['service_attempts']),
                        int(player_data['service_aces']),
                        int(player_data['service_errors']),
                        f"{player_data['service_efficiency']:.1%}"
                    ]
                }
                service_df = pd.DataFrame(service_data)
                st.dataframe(service_df, use_container_width=True, hide_index=True)
            
            with col3:
                st.markdown("#### 🛡️ Block Statistics")
                block_data = {
                    'Metric': ['Attempts', 'Kills', 'Errors', 'Efficiency'],
                    'Value': [
                        int(player_data['block_attempts']),
                        int(player_data['block_kills']),
                        int(player_data['block_errors']),
                        f"{player_data['block_efficiency']:.1%}"
                    ]
                }
                block_df = pd.DataFrame(block_data)
                st.dataframe(block_df, use_container_width=True, hide_index=True)
        
        # Player performance charts
        create_player_charts(analyzer, selected_player)

def create_player_charts(analyzer: MatchAnalyzer, player_name: str) -> None:
    """Create player-specific performance charts"""
    st.markdown(f"### 📈 Performance Charts for {player_name}")
    
    df = analyzer.match_data
    player_df = df[df['player'] == player_name]
    
    if player_df.empty:
        st.warning(f"No data found for {player_name}")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Player actions by set
        set_actions = player_df.groupby('set_number')['action'].count()
        fig_set = px.bar(
            x=set_actions.index,
            y=set_actions.values,
            title=f"{player_name} - Actions by Set",
            color=set_actions.values,
            color_continuous_scale=[CHART_COLORS['primary'], CHART_COLORS['secondary']]
        )
        fig_set.update_traces(
            marker=dict(line=dict(color='rgba(0,0,0,0.2)', width=1)),
            hovertemplate='<b>Set %{x}</b><br>Actions: %{y}<extra></extra>'
        )
        fig_set = apply_beautiful_theme(fig_set, f"{player_name} - Actions by Set")
        fig_set.update_layout(showlegend=False)
        st.plotly_chart(fig_set, use_container_width=True, config=plotly_config)
    
    with col2:
        # Player action distribution
        action_counts = player_df['action'].value_counts()
        fig_actions = px.pie(
            values=action_counts.values,
            names=action_counts.index,
            title=f"{player_name} - Action Distribution",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_actions.update_traces(
            textposition='inside', 
            textinfo='percent+label',
            marker=dict(line=dict(color='rgba(0,0,0,0.2)', width=1))
        )
        fig_actions = apply_beautiful_theme(fig_actions, f"{player_name} - Action Distribution")
        st.plotly_chart(fig_actions, use_container_width=True, config=plotly_config)
    
    # Player performance over time (by rotation)
    st.markdown("### 🔄 Performance by Rotation")
    
    rotation_stats = player_df.groupby('rotation').agg({
        'action': 'count',
        'outcome': lambda x: (x == 'kill').sum()
    }).rename(columns={'action': 'Total_Actions', 'outcome': 'Kills'})
    
    # Ensure we have all rotations 1-6 (fill missing with 0)
    for rot in range(1, 7):
        if rot not in rotation_stats.index:
            rotation_stats.loc[rot] = {'Total_Actions': 0, 'Kills': 0}
    rotation_stats = rotation_stats.sort_index()
    
    fig_rotation = make_subplots(
        rows=1, cols=2,
        subplot_titles=(f'{player_name} - Actions by Rotation', f'{player_name} - Kills by Rotation'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    fig_rotation.add_trace(
        go.Bar(
            x=rotation_stats.index, 
            y=rotation_stats['Total_Actions'], 
            name='Total Actions',
            marker=dict(
                color=rotation_stats['Total_Actions'],
                colorscale=[[0, CHART_COLORS['primary']], [1, CHART_COLORS['secondary']]],
                line=dict(color='#040C7B', width=2)
            )
        ),
        row=1, col=1
    )
    
    fig_rotation.add_trace(
        go.Bar(
            x=rotation_stats.index, 
            y=rotation_stats['Kills'], 
            name='Kills',
            marker=dict(
                color=rotation_stats['Kills'],
                colorscale=[[0, CHART_COLORS['success']], [1, '#06D6A0']],
                line=dict(color='#040C7B', width=2)
            )
        ),
        row=1, col=2
    )
    
    fig_rotation.update_xaxes(
        title_text="Rotation", 
        row=1, col=1, 
        dtick=1,
        gridcolor='rgba(102, 126, 234, 0.1)',
        linecolor='rgba(102, 126, 234, 0.3)'
    )
    fig_rotation.update_xaxes(
        title_text="Rotation", 
        row=1, col=2, 
        dtick=1,
        gridcolor='rgba(102, 126, 234, 0.1)',
        linecolor='rgba(102, 126, 234, 0.3)'
    )
    fig_rotation.update_yaxes(
        title_text="Total Actions", 
        row=1, col=1,
        gridcolor='rgba(102, 126, 234, 0.1)',
        linecolor='rgba(102, 126, 234, 0.3)'
    )
    fig_rotation.update_yaxes(
        title_text="Kills", 
        row=1, col=2,
        gridcolor='rgba(102, 126, 234, 0.1)',
        linecolor='rgba(102, 126, 234, 0.3)'
    )
    
    fig_rotation = apply_beautiful_theme(fig_rotation, height=450)
    fig_rotation.update_layout(showlegend=False)
    st.plotly_chart(fig_rotation, use_container_width=True, config=plotly_config)

def calculate_player_rating(player_stats_dict: Dict[str, Any], position: str, df: pd.DataFrame) -> float:
    """
    Calculate a position-specific rating out of 10 for a player
    Ratings are based on position-specific key metrics
    """
    stats = player_stats_dict
    rating = 0.0
    
    if position == 'S':  # Setter
        # Primary: Setting quality (40%), Service (20%), Attack (20%), Digs (20%)
        setting_pct = stats.get('setting_percentage', 0) if stats.get('total_sets', 0) > 0 else 0
        service_eff = stats.get('service_efficiency', 0)
        attack_eff = stats.get('attack_efficiency', 0)
        dig_total = stats.get('total_digs', 0)
        
        # Setting: 0.65+ = 10, 0.50 = 5, below 0.30 = 0
        setting_score = min(10, max(0, (setting_pct - 0.30) / 0.35 * 10)) if stats.get('total_sets', 0) > 0 else 5
        service_score = min(10, max(0, (service_eff - (-0.15)) / 0.30 * 10))
        attack_score = min(10, max(0, attack_eff / 0.50 * 10)) if stats.get('attack_attempts', 0) > 0 else 5
        dig_score = min(10, max(0, dig_total / 10 * 10))
        
        rating = setting_score * 0.4 + service_score * 0.2 + attack_score * 0.2 + dig_score * 0.2
        
    elif position in ['OH1', 'OH2', 'OPP']:  # Outside Hitters / Opposite
        # Primary: Attack (35%), Reception (25%), Service (20%), Blocking (10%), Digs (10%)
        attack_eff = stats.get('attack_efficiency', 0)
        reception_pct = stats.get('reception_percentage', 0) if stats.get('total_receives', 0) > 0 else 0
        service_eff = stats.get('service_efficiency', 0)
        block_eff = stats.get('block_efficiency', 0)
        dig_total = stats.get('total_digs', 0)
        
        attack_score = min(10, max(0, (attack_eff - 0.10) / 0.45 * 10)) if stats.get('attack_attempts', 0) > 0 else 0
        reception_score = min(10, max(0, (reception_pct - 0.50) / 0.40 * 10)) if stats.get('total_receives', 0) > 0 else 5
        service_score = min(10, max(0, (service_eff - (-0.15)) / 0.30 * 10))
        block_score = min(10, max(0, (block_eff - (-0.10)) / 0.20 * 10))
        dig_score = min(10, max(0, dig_total / 20 * 10))
        
        rating = attack_score * 0.35 + reception_score * 0.25 + service_score * 0.20 + block_score * 0.10 + dig_score * 0.10
        
    elif position in ['MB1', 'MB2']:  # Middle Blockers
        # Primary: Blocking (40%), Attack Efficiency (30%), Service (20%), Digs (10%)
        block_eff = stats.get('block_efficiency', 0)
        attack_eff = stats.get('attack_efficiency', 0)
        service_eff = stats.get('service_efficiency', 0)
        dig_total = stats.get('total_digs', 0)
        
        block_score = min(10, max(0, (block_eff - (-0.05)) / 0.25 * 10))
        attack_score = min(10, max(0, (attack_eff - 0.20) / 0.50 * 10)) if stats.get('attack_attempts', 0) > 0 else 0
        service_score = min(10, max(0, (service_eff - (-0.15)) / 0.30 * 10))
        dig_score = min(10, max(0, dig_total / 10 * 10))
        
        rating = block_score * 0.4 + attack_score * 0.3 + service_score * 0.2 + dig_score * 0.1
        
    elif position == 'L':  # Libero
        # Primary: Reception (50%), Digs (40%), Service (10% - if applicable)
        reception_pct = stats.get('reception_percentage', 0) if stats.get('total_receives', 0) > 0 else 0
        dig_total = stats.get('total_digs', 0)
        service_eff = stats.get('service_efficiency', 0)
        
        reception_score = min(10, max(0, (reception_pct - 0.60) / 0.30 * 10)) if stats.get('total_receives', 0) > 0 else 5
        dig_score = min(10, max(0, dig_total / 30 * 10))
        service_score = min(10, max(0, (service_eff - (-0.15)) / 0.30 * 10)) if stats.get('service_total', 0) > 0 else 5
        
        rating = reception_score * 0.5 + dig_score * 0.4 + service_score * 0.1
    
    return round(rating, 1)

def display_player_comparison(analyzer: MatchAnalyzer) -> None:
    """Display player comparison with position-specific and cross-position ratings"""
    st.markdown('<h2 class="main-header">🏆 Player Comparison</h2>', unsafe_allow_html=True)
    
    player_stats = analyzer.calculate_player_metrics()
    
    if player_stats is None:
        st.error("No player statistics available")
        return
    
    df = analyzer.match_data
    
    # Create comparison dataframe with positions and ratings
    comparison_data = []
    for player, stats in player_stats.items():
        position = get_player_position(df, player)
        rating = calculate_player_rating(stats, position, df)
        
        comparison_data.append({
            'Player': player,
            'Position': get_position_full_name(position),
            'Rating': rating,
            'Total Actions': stats['total_actions'],
            'Attack Efficiency': stats['attack_efficiency'],
            'Service Efficiency': stats['service_efficiency'],
            'Block Efficiency': stats['block_efficiency'],
            'Reception Percentage': stats.get('reception_percentage', 0),
            'Setting Percentage': stats.get('setting_percentage', 0),
            'Attack Kills': stats['attack_kills'],
            'Service Aces': stats['service_aces'],
            'Block Kills': stats['block_kills'],
            'Total Receives': stats.get('total_receives', 0),
            'Total Sets': stats.get('total_sets', 0),
            'Total Digs': stats.get('total_digs', 0)
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # ===== CROSS-POSITION RATING SYSTEM =====
    st.markdown("## ⭐ Overall Player Ratings (Out of 10)")
    st.info("""
    **Rating System:** Each player is rated out of 10 based on position-specific metrics:
    - **Setters (S):** Setting quality (40%), Service (20%), Attack (20%), Digs (20%)
    - **Outside Hitters/Opposite (OH/OPP):** Attack (35%), Reception (25%), Service (20%), Blocking (10%), Digs (10%)
    - **Middle Blockers (MB):** Blocking (40%), Attack (30%), Service (20%), Digs (10%)
    - **Liberos (L):** Reception (50%), Digs (40%), Service (10%)
    """)
    
    # Sort by rating
    rating_df = comparison_df[['Player', 'Position', 'Rating', 'Total Actions']].copy()
    rating_df = rating_df.sort_values('Rating', ascending=False)
    rating_df['Rating'] = rating_df['Rating'].apply(lambda x: f"{x:.1f}/10")
    
    # Enhanced player comparison with images
    st.markdown("#### 🏅 Player Performance Overview")
    
    # Create visual player cards
    top_players = rating_df.head(6)  # Show top 6 players
    
    # Create columns for player cards
    cols = st.columns(3)
    
    for idx, (_, player_row) in enumerate(top_players.iterrows()):
        player_name = player_row['Player']
        position_full = player_row['Position']  # Already full name from comparison_data
        rating = player_row['Rating']
        actions = player_row['Total Actions']
        
        # Get position abbreviation for emoji
        position_abbrev = get_player_position(df, player_name)
        
        with cols[idx % 3]:
            # Create player card with enhanced styling
            st.markdown(f"""
            <div style="
                border: 2px solid #040C7B; 
                border-radius: 15px; 
                padding: 25px 20px;
                min-height: 300px; 
                margin: 10px 0; 
                text-align: center;
                background: linear-gradient(135deg, #ffffff, #f8f9fa);
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                transition: transform 0.2s ease;
            ">
            """, unsafe_allow_html=True)
            
            # Player image with better styling
            player_image = load_player_image(player_name)
            if player_image:
                # Create a copy and resize with high quality, preserving aspect ratio
                img_copy = player_image.copy()
                # Calculate aspect ratio to maintain proportions
                aspect_ratio = img_copy.width / img_copy.height
                card_size = 120  # Increased from 85 for better quality
                if aspect_ratio > 1:
                    new_width = card_size
                    new_height = int(card_size / aspect_ratio)
                else:
                    new_height = card_size
                    new_width = int(card_size * aspect_ratio)
                # Use resize() with LANCZOS for better quality than thumbnail()
                img_copy = img_copy.resize((new_width, new_height), Image.Resampling.LANCZOS)
                # Wrap image in centered container
                st.markdown('<div style="display: flex; justify-content: center; margin-bottom: 15px;">', unsafe_allow_html=True)
                st.image(img_copy, width=card_size, use_container_width=False)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                # Enhanced fallback placeholder
                st.markdown(f"""
                <div style="
                    width: {card_size}px; 
                    height: {card_size}px; 
                    background: linear-gradient(135deg, #040C7B, #1A1F9E); 
                    border-radius: 50%; 
                    display: flex; 
                    align-items: center; 
                    justify-content: center; 
                    color: white; 
                    font-size: 24px; 
                    font-weight: bold;
                    margin: 0 auto 15px auto;
                    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
                ">
                    {player_name[0].upper()}
                </div>
                """, unsafe_allow_html=True)
            
            # Enhanced player info
            position_emoji = get_position_emoji(position_abbrev)
            st.markdown(f"""
            <div style="text-align: center;">
                <h4 style="margin: 8px 0; color: #040C7B; font-size: 18px;">{player_name}</h4>
                <p style="margin: 5px 0; font-size: 14px; color: #666; font-weight: 500;">
                    {position_emoji} {position_full}
                </p>
                <div style="
                    background: linear-gradient(135deg, #28a745, #20c997); 
                    color: white; 
                    padding: 8px 12px; 
                    border-radius: 20px; 
                    margin: 10px 0;
                    font-weight: bold;
                    font-size: 18px;
                ">
                    {rating}
                </div>
                <p style="margin: 12px 0 0 0; font-size: 14px; color: #777; font-weight: 500;">
                    {actions} actions
                </p>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("</div>", unsafe_allow_html=True)
    
    # Add performance insights
    st.markdown("---")
    st.markdown("#### 📊 Performance Insights")
    
    # Top performers by position
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("**🏆 Top Rated Player**")
        top_player = rating_df.iloc[0]
        st.markdown(f"**{top_player['Player']}** ({top_player['Position']}) - {top_player['Rating']}")
    
    with col2:
        st.markdown("**⚡ Most Active Player**")
        most_active = rating_df.loc[rating_df['Total Actions'].idxmax()]
        st.markdown(f"**{most_active['Player']}** - {most_active['Total Actions']} actions")
    
    with col3:
        st.markdown("**🎯 Position Distribution**")
        position_counts = rating_df['Position'].value_counts()
        top_position = position_counts.index[0]
        st.markdown(f"Most common: **{top_position}** ({position_counts.iloc[0]} players)")
    
    st.markdown("---")
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("#### 📊 Complete Player Ratings Table")
        st.dataframe(rating_df, use_container_width=True, hide_index=True)
    
    with col2:
        st.markdown("#### 🏅 Top Rated Players")
        top_3 = rating_df.head(3).copy()
        medals = ["🥇", "🥈", "🥉"]
        for i, (idx, row) in enumerate(top_3.iterrows()):
            medal = medals[i] if i < len(medals) else "🏅"
            st.markdown(f"**{medal} {row['Player']}** ({row['Position']})")
            st.markdown(f"Rating: **{row['Rating']}**")
            st.markdown("---")
    
    # Rating visualization
    st.markdown("#### 📈 Overall Rating Comparison")
    fig_rating = px.bar(
        comparison_df.sort_values('Rating', ascending=True),
        x='Rating',
        y='Player',
        color='Position',
        orientation='h',
        title="Player Ratings Comparison (Out of 10)",
        color_discrete_sequence=CHART_COLOR_GRADIENTS['gradient']
    )
    fig_rating.update_traces(
        marker=dict(line=dict(color='#040C7B', width=2)),
        hovertemplate='<b>%{y}</b><br>Rating: %{x:.1f}/10<extra></extra>'
    )
    fig_rating = apply_beautiful_theme(fig_rating, "Player Ratings Comparison (Out of 10)", height=450)
    fig_rating.update_layout(xaxis_range=[0, 10])
    st.plotly_chart(fig_rating, use_container_width=True, config=plotly_config)
    
    st.markdown("---")
    
    # ===== POSITION-SPECIFIC COMPARISONS =====
    st.markdown("## 📊 Position-Specific Comparisons")
    st.markdown("Compare players within the same position for direct performance metrics.")
    
    # Group by position
    positions = comparison_df['Position'].unique()
    
    for position in sorted(positions):
        pos_df = comparison_df[comparison_df['Position'] == position].copy()
        if len(pos_df) == 0:
            continue
            
        position_names = {
            'S': '🏐 Setters',
            'OH1': '🎯 Outside Hitters (OH1)',
            'OH2': '🎯 Outside Hitters (OH2)',
            'OPP': '⚡ Opposite Hitters',
            'MB1': '🛡️ Middle Blockers (MB1)',
            'MB2': '🛡️ Middle Blockers (MB2)',
            'L': '🔵 Liberos'
        }
        
        st.markdown(f"### {position_names.get(position, f'{position} Players')}")
        
        if position == 'S':  # Setter comparison
            setter_cols = ['Player', 'Setting Percentage', 'Service Efficiency', 'Attack Efficiency', 'Total Sets', 'Total Digs', 'Rating']
            setter_df = pos_df[setter_cols].copy()
            setter_df['Setting Percentage'] = setter_df['Setting Percentage'].apply(lambda x: f"{x:.1%}" if pd.notna(x) and x > 0 else "N/A")
            setter_df['Service Efficiency'] = setter_df['Service Efficiency'].apply(lambda x: f"{x:.1%}")
            setter_df['Attack Efficiency'] = setter_df['Attack Efficiency'].apply(lambda x: f"{x:.1%}")
            setter_df['Rating'] = setter_df['Rating'].apply(lambda x: f"{x:.1f}/10")
            setter_df = setter_df.sort_values('Rating', ascending=False)
            st.dataframe(setter_df, use_container_width=True, hide_index=True)
            
        elif position == 'L':  # Libero comparison
            libero_cols = ['Player', 'Reception Percentage', 'Service Efficiency', 'Total Receives', 'Total Digs', 'Rating']
            libero_df = pos_df[libero_cols].copy()
            libero_df['Reception Percentage'] = libero_df['Reception Percentage'].apply(lambda x: f"{x:.1%}" if pd.notna(x) and x > 0 else "N/A")
            libero_df['Service Efficiency'] = libero_df['Service Efficiency'].apply(lambda x: f"{x:.1%}")
            libero_df['Rating'] = libero_df['Rating'].apply(lambda x: f"{x:.1f}/10")
            libero_df = libero_df.sort_values('Rating', ascending=False)
            st.dataframe(libero_df, use_container_width=True, hide_index=True)
            
        elif position in ['OH1', 'OH2', 'OPP']:  # Hitter comparison
            hitter_cols = ['Player', 'Attack Efficiency', 'Reception Percentage', 'Service Efficiency', 'Block Efficiency', 'Attack Kills', 'Rating']
            hitter_df = pos_df[hitter_cols].copy()
            hitter_df['Attack Efficiency'] = hitter_df['Attack Efficiency'].apply(lambda x: f"{x:.1%}")
            hitter_df['Reception Percentage'] = hitter_df['Reception Percentage'].apply(lambda x: f"{x:.1%}" if pd.notna(x) and x > 0 else "N/A")
            hitter_df['Service Efficiency'] = hitter_df['Service Efficiency'].apply(lambda x: f"{x:.1%}")
            hitter_df['Block Efficiency'] = hitter_df['Block Efficiency'].apply(lambda x: f"{x:.1%}")
            hitter_df['Rating'] = hitter_df['Rating'].apply(lambda x: f"{x:.1f}/10")
            hitter_df = hitter_df.sort_values('Rating', ascending=False)
            st.dataframe(hitter_df, use_container_width=True, hide_index=True)
            
        elif position in ['MB1', 'MB2']:  # Middle blocker comparison
            mb_cols = ['Player', 'Block Efficiency', 'Attack Efficiency', 'Service Efficiency', 'Block Kills', 'Attack Kills', 'Rating']
            mb_df = pos_df[mb_cols].copy()
            mb_df['Block Efficiency'] = mb_df['Block Efficiency'].apply(lambda x: f"{x:.1%}")
            mb_df['Attack Efficiency'] = mb_df['Attack Efficiency'].apply(lambda x: f"{x:.1%}")
            mb_df['Service Efficiency'] = mb_df['Service Efficiency'].apply(lambda x: f"{x:.1%}")
            mb_df['Rating'] = mb_df['Rating'].apply(lambda x: f"{x:.1f}/10")
            mb_df = mb_df.sort_values('Rating', ascending=False)
            st.dataframe(mb_df, use_container_width=True, hide_index=True)
        
        st.markdown("---")
    
    # ===== TOP PERFORMERS BY METRIC =====
    st.markdown("## 🏅 Top Performers by Category")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("#### 🎯 Top Attackers")
        # Filter to players with meaningful attack attempts
        attackers_df = comparison_df[comparison_df['Attack Kills'] > 0].nlargest(5, 'Attack Efficiency')[['Player', 'Position', 'Attack Efficiency']].copy()
        attackers_df['Attack Efficiency'] = attackers_df['Attack Efficiency'].apply(lambda x: f"{x:.1%}")
        if len(attackers_df) > 0:
            st.dataframe(attackers_df, use_container_width=True, hide_index=True)
        else:
            st.info("No attack data available")
    
    with col2:
        st.markdown("#### 🏐 Top Servers")
        servers_df = comparison_df.nlargest(5, 'Service Efficiency')[['Player', 'Position', 'Service Efficiency']].copy()
        servers_df['Service Efficiency'] = servers_df['Service Efficiency'].apply(lambda x: f"{x:.1%}")
        st.dataframe(servers_df, use_container_width=True, hide_index=True)
    
    with col3:
        st.markdown("#### 🛡️ Top Blockers")
        blockers_df = comparison_df[comparison_df['Block Kills'] > 0].nlargest(5, 'Block Efficiency')[['Player', 'Position', 'Block Efficiency']].copy()
        blockers_df['Block Efficiency'] = blockers_df['Block Efficiency'].apply(lambda x: f"{x:.1%}")
        if len(blockers_df) > 0:
            st.dataframe(blockers_df, use_container_width=True, hide_index=True)
        else:
            st.info("No block data available")
    
    with col4:
        st.markdown("#### ✋ Top Receivers")
        receivers_df = comparison_df[comparison_df['Total Receives'] > 0].nlargest(5, 'Reception Percentage')[['Player', 'Position', 'Reception Percentage']].copy()
        receivers_df['Reception Percentage'] = receivers_df['Reception Percentage'].apply(lambda x: f"{x:.1%}" if pd.notna(x) and x > 0 else "N/A")
        if len(receivers_df) > 0:
            st.dataframe(receivers_df, use_container_width=True, hide_index=True)
        else:
            st.info("No reception data available")

def main():
    """Main Streamlit app"""
    
    # Header with No Blockers branding - Enhanced Layout
    col_header1, col_header2 = st.columns([3, 2])
    
    with col_header1:
        opponent = st.session_state.get('opponent_name', '')
        opponent_text = f" vs {opponent}" if opponent else ""
        st.markdown(f"""
        <div class="main-header">
            <span class="brand-name">⚫ NO BLOCKERS</span>
            <span class="subtitle">Team Analytics{opponent_text}</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col_header2:
        st.markdown("""
        <div class="tagline-header">
            NO FEAR. NO LIMITS.<br>NO BLOCKERS.
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)  # Add spacing
    
    # Sidebar
    # Display team photo in sidebar (top left)
    if os.path.exists("assets/images/IMG_1377.JPG"):
        st.sidebar.image("assets/images/IMG_1377.JPG", width=150, caption="No Blockers Team")
        st.sidebar.markdown("---")
    
    st.sidebar.title("📊 Navigation")
    page = st.sidebar.selectbox(
        "Choose Analysis Type:",
        ["Team Overview", "Player Analysis", "Player Comparison"]
    )
    
    # Initialize session state for match data
    if 'match_loaded' not in st.session_state:
        st.session_state['match_loaded'] = False
    
    # Check for initial file upload (if no data loaded yet)
    if not st.session_state.get('match_loaded', False):
        # Show file uploader at the bottom for initial load
        st.info("👆 Please upload your match data file below to begin analysis.")
        st.markdown("---")
        st.markdown("### 📁 Upload Match Data")
        uploaded_file = st.file_uploader(
            "Upload Match Data (Excel file)", 
            type=['xlsx'],
            help="Please upload your match data Excel file (created from the ../templates/Match_Template.xlsx)",
            key="file_uploader_initial"
        )
        
        if uploaded_file is not None:
            success = load_match_data(uploaded_file)
            if success:
                st.rerun()
        st.stop()
    
    # Get data from session state
    analyzer = st.session_state.get('analyzer')
    loader = st.session_state.get('loader')
    
    if analyzer is None:
        st.error("❌ No match data available. Please upload a file below.")
        st.stop()
    
    # Display selected page
    if page == "Team Overview":
        from ui.team_overview import display_team_overview
        display_team_overview(analyzer, loader)
    
    elif page == "Player Analysis":
        from ui.player_analysis import display_player_analysis
        display_player_analysis(analyzer, loader)
    
    elif page == "Player Comparison":
        from ui.player_comparison import display_player_comparison
        display_player_comparison(analyzer, loader)
    
    # Footer with file uploader at the bottom
    st.markdown("---")
    st.markdown(
        """
        <div style='text-align: center; color: #666;'>
            <p>🏐 Volleyball Team Analytics Dashboard | Built with Streamlit</p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # File uploader at the bottom
    st.markdown("### 📁 Upload New Match Data")
    uploaded_file = st.file_uploader(
        "Upload Match Data (Excel file)", 
        type=['xlsx'],
        help="Upload a new match file to replace the current data",
        key="file_uploader_bottom"
    )
    
    if uploaded_file is not None:
        # Clear existing session state before loading new file
        clear_session_state()
        
        # Load new file
        success = load_match_data(uploaded_file)
        if success:
            st.rerun()

if __name__ == "__main__":
    main()
