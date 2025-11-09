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
import time
from typing import Optional, Dict, Any, List, Tuple

# Suppress Plotly deprecation warnings
warnings.filterwarnings('ignore', message='.*keyword arguments have been deprecated.*')

# Add the Dashboard directory to the path for imports
# This ensures imports work when running from parent directory
dashboard_dir = Path(__file__).parent
if str(dashboard_dir) not in sys.path:
    sys.path.insert(0, str(dashboard_dir))

from match_analyzer import MatchAnalyzer
import performance_tracker as pt
from utils import validate_uploaded_file, save_uploaded_file_securely, cleanup_temp_file
from event_tracker_loader import EventTrackerLoader
from ui.components import load_logo_cached
from services.session_manager import SessionStateManager
from services.analytics_service import AnalyticsService
from ui.insights_helpers import (
    _generate_attack_efficiency_insights,
    _generate_set_by_set_insights,
    _generate_rotation_insights,
    _generate_service_insights,
    _generate_block_insights,
    _generate_reception_insights,
    _generate_position_specific_insights,
    _generate_action_distribution_insights,
    _generate_service_reception_battle_insights
)
from ui.team_overview_helpers import (
    _display_metric_styling,
    _display_kpi_metrics_row_1,
    _display_kpi_metrics_row_2,
    _display_match_banner,
    _display_rotation_analysis,
    _display_pass_quality_analysis
)
from ui.data_loading_helpers import (
    _extract_opponent_name,
    _create_progress_tracker,
    _display_validation_errors,
    _load_event_tracker_format
)
from utils.helpers import (
    filter_good_receptions, filter_good_digs, filter_block_touches,
    count_good_outcomes, is_good_reception, is_good_dig, is_good_block,
    get_player_position
)
from ui.components import (
    get_position_full_name,
    get_position_emoji,
    load_player_image_cached
)
import logging_config  # Initialize logging
import logging

logger = logging.getLogger(__name__)

# Import configuration
from config import (
    CHART_COLORS, CHART_COLOR_GRADIENTS, SETTER_THRESHOLD,
    KPI_TARGETS, VALID_ACTIONS, VALID_OUTCOMES,
    MAX_FILE_SIZE, ALLOWED_EXTENSIONS, DEFAULT_TEMPLATE_PATH, DEFAULT_IMAGES_DIR
)

# Import chart utilities from charts.utils
from charts.utils import apply_beautiful_theme, plotly_config

# Page configuration
st.set_page_config(
    page_title="Volleyball Team Analytics",
    page_icon="🏐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import theme module
from ui.theme import apply_dashboard_theme

# Apply dashboard theme
apply_dashboard_theme()

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

def clear_session_state() -> None:
    """Clear session state when loading new match, keeping only essential keys."""
    SessionStateManager.clear_match_data()

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
    with st.spinner("📁 Validating file..."):
        is_valid, error_msg = validate_uploaded_file(uploaded_file)
        if not is_valid:
            st.error(f"❌ File validation failed: {error_msg}")
            return False
    
    # Extract opponent name and date from filename
    filename = uploaded_file.name
    opponent_name = _extract_opponent_name(filename)
    
    # Extract date from filename
    import re
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    match_date = None
    if date_match:
        try:
            match_date = datetime.strptime(date_match.group(1), '%Y-%m-%d').date()
        except:
            pass
    
    # Store in session state for use in header
    SessionStateManager.set_opponent_name(opponent_name)
    SessionStateManager.set_match_filename(filename)
    if match_date:
        st.session_state['match_date'] = match_date
    
    temp_file_path = None
    temp_converted_path = None
    
    try:
        # Save uploaded file securely to temporary location
        temp_file_path = save_uploaded_file_securely(uploaded_file)
        
        # Check which format the file uses by examining sheet names
        xl_file = pd.ExcelFile(temp_file_path)
        sheet_names = xl_file.sheet_names
        
        # Try Event Tracker format first (newest format)
        if 'Individual Events' in sheet_names and 'Team Events' in sheet_names:
            progress_bar, status_text = _create_progress_tracker()
            
            try:
                analyzer, loader, temp_converted_path = _load_event_tracker_format(
                    temp_file_path, progress_bar, status_text
                )
                
                if analyzer is None:
                    return False
                
                # Additional validation after loading
                is_valid, errors, warnings = validate_match_data(analyzer.match_data)
                if not is_valid:
                    progress_bar.empty()
                    status_text.empty()
                    _display_validation_errors(errors, "Data validation")
                    return False
                
                if warnings:
                    for warning in warnings:
                        st.warning(f"⚠️ {warning}")
                
                # Store in session state
                SessionStateManager.set_analyzer(analyzer)
                SessionStateManager.set_loader(loader)
                SessionStateManager.set_match_loaded(True)
                
                # Store data load timestamp
                st.session_state['data_last_loaded'] = datetime.now()
                
                num_players = len(set(loader.individual_events['Player'].unique())) if loader.individual_events is not None else 0
                num_sets = len(loader.sets) if loader.sets else 0
                
                # Clear loading indicators
                progress_bar.empty()
                status_text.empty()
                
                st.success(f"✅ Event tracker data loaded successfully! Found {num_players} players across {num_sets} sets.")
                return True
            except Exception as e:
                logger.warning(f"Event tracker loader failed: {e}, trying other formats...")
                progress_bar.empty()
                status_text.empty()
                raise
        
        # Only event-based format is supported now
        raise Exception("Could not identify file format. Expected sheets: 'Individual Events' + 'Team Events' (event tracker format). Only event-based format is supported.")
        
    except ValueError as e:
        # Validation errors - user-friendly message
        st.error(f"❌ {str(e)}")
        return False
    except Exception as e:
        st.error(f"❌ Error loading file: {str(e)}")
        st.info("💡 Make sure your Excel file follows the correct format (Match_Template.xlsx)")
        # Log full traceback for debugging, but don't show to user
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
                background: linear-gradient(135deg, #050d76, #1A1F9E); 
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
                    background: linear-gradient(135deg, #050d76, #1A1F9E); 
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
                <h3 style="margin: 0; color: #050d76; font-size: 1.5rem;">{player_name}</h3>
                <p style="margin: 5px 0; font-size: 18px; color: #666;">
                    {position_emoji} {position_full}
                </p>
            </div>
            """, unsafe_allow_html=True)

def generate_insights(analyzer: MatchAnalyzer, team_stats: Dict[str, Any], 
                     TARGETS: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate actionable insights and recommendations from match data.
    
    Args:
        analyzer: MatchAnalyzer instance with loaded match data
        team_stats: Team statistics dictionary
        TARGETS: KPI targets dictionary
        
    Returns:
        List of insight dictionaries sorted by priority
    """
    insights = []
    
    df = analyzer.match_data
    player_stats = analyzer.calculate_player_metrics()
    
    # Calculate set statistics
    set_stats = df.groupby('set_number').agg({
        'action': 'count',
        'outcome': lambda x: (x == 'kill').sum()
    }).rename(columns={'action': 'Total_Actions', 'outcome': 'Kills'})
    
    # Calculate rotation statistics
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
    
    # Generate insights using helper functions
    insights.extend(_generate_attack_efficiency_insights(team_stats, TARGETS))
    insights.extend(_generate_set_by_set_insights(df, set_stats))
    insights.extend(_generate_rotation_insights(df, rotation_stats))
    insights.extend(_generate_service_insights(team_stats, TARGETS))
    insights.extend(_generate_block_insights(team_stats, df, TARGETS))
    insights.extend(_generate_reception_insights(team_stats, TARGETS))
    insights.extend(_generate_position_specific_insights(df, player_stats))
    insights.extend(_generate_action_distribution_insights(df, team_stats))
    insights.extend(_generate_service_reception_battle_insights(team_stats))
    
    # Attack Distribution - Are we balanced?
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

def main():
    """Main Streamlit app"""
    
    # Header with No Blockers branding - Enhanced Layout
    col_header1, col_header2 = st.columns([3, 2])
    
    with col_header1:
        opponent = SessionStateManager.get_opponent_name()
        match_date = st.session_state.get('match_date')
        
        # Format the subtitle
        if opponent:
            # Try to extract date from filename if match_date not available
            if not match_date:
                filename = SessionStateManager.get_match_filename() or ''
                import re
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
                if date_match:
                    try:
                        match_date = datetime.strptime(date_match.group(1), '%Y-%m-%d').date()
                    except:
                        pass
            
            # Format date as "24th of October 2025"
            if match_date:
                # Convert string to date if needed
                if isinstance(match_date, str):
                    try:
                        match_date = datetime.strptime(match_date, '%Y-%m-%d').date()
                    except:
                        match_date = None
                
                # Convert datetime to date if needed
                if match_date and hasattr(match_date, 'date'):
                    try:
                        match_date = match_date.date()
                    except:
                        pass
                
                if match_date and hasattr(match_date, 'day'):
                    # Format day with ordinal suffix (1st, 2nd, 3rd, 4th, etc.)
                    day = match_date.day
                    if 10 <= day % 100 <= 20:
                        suffix = 'th'
                    else:
                        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(day % 10, 'th')
                    
                    # Format month name
                    month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                                 'July', 'August', 'September', 'October', 'November', 'December']
                    month_name = month_names[match_date.month - 1]
                    
                    formatted_date = f"{day}{suffix} of {month_name} {match_date.year}"
                    opponent_text = f" vs {opponent} on {formatted_date}"
                else:
                    opponent_text = f" vs {opponent}"
            else:
                opponent_text = f" vs {opponent}"
        else:
            opponent_text = ""
        
        st.markdown(f"""
        <div class="main-header">
            <span class="brand-name">⚫ NO BLOCKERS</span>
            <span class="subtitle">Match Analysis{opponent_text}</span>
        </div>
        """, unsafe_allow_html=True)
    
    with col_header2:
        # Show data load timestamp if available
        data_loaded_time = st.session_state.get('data_last_loaded')
        if data_loaded_time:
            if isinstance(data_loaded_time, datetime):
                loaded_str = data_loaded_time.strftime('%H:%M:%S')
            else:
                loaded_str = str(data_loaded_time)
            st.markdown(f"""
            <div style="text-align: right; padding-top: 10px;">
                <small style="color: #666;">📅 Data loaded: {loaded_str}</small>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="tagline-header">
                NO FEAR. NO LIMITS.<br>NO BLOCKERS.
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)  # Add spacing
    
    # Sidebar
    # Display team photo in sidebar (top left)
    logo_image = load_logo_cached("IMG_1377.JPG", "assets/images")
    if logo_image:
        try:
            st.sidebar.image(logo_image, width=150, caption="No Blockers Team")
            st.sidebar.markdown("---")
        except Exception as e:
            # Silently fail if image can't be loaded
            pass
    
    st.sidebar.title("📊 Navigation")
    
    # HIGH PRIORITY 6: Handle navigation from CTAs
    nav_target = st.session_state.get('navigation_target')
    if nav_target:
        # Set the page to the target
        page_options = ["Team Overview", "Player Analysis", "Player Comparison"]
        if nav_target in page_options:
            page_index = page_options.index(nav_target)
            page = st.sidebar.selectbox(
                "Choose Analysis Type:",
                page_options,
                index=page_index
            )
            # Clear the navigation target after using it
            del st.session_state['navigation_target']
        else:
            page = st.sidebar.selectbox(
                "Choose Analysis Type:",
                ["Team Overview", "Player Analysis", "Player Comparison"]
            )
    else:
        page = st.sidebar.selectbox(
            "Choose Analysis Type:",
            ["Team Overview", "Player Analysis", "Player Comparison"]
        )
    
    st.sidebar.markdown("---")
    
    # MEDIUM PRIORITY 11: Help guide button
    if st.sidebar.button("📚 Help Guide", use_container_width=True):
        SessionStateManager.set_show_help_guide(True)
    
    # Display help guide if requested
    if SessionStateManager.should_show_help_guide():
        from utils.help_guide import display_help_guide
        if st.sidebar.button("❌ Close Help", use_container_width=True):
            SessionStateManager.set_show_help_guide(False)
            st.rerun()
        display_help_guide()
        st.stop()
    
    # Initialize session state for match data
    if not SessionStateManager.is_match_loaded():
        SessionStateManager.set_match_loaded(False)
    
    # Check for initial file upload (if no data loaded yet)
    if not SessionStateManager.is_match_loaded():
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
    
    # Get data from session state for page display
    analyzer = SessionStateManager.get_analyzer()
    loader = SessionStateManager.get_loader()
    
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
