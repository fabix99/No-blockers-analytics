"""
Reusable UI components for the dashboard
"""
from typing import Optional, Dict, Any
import streamlit as st
from PIL import Image
from config import CHART_COLORS, DEFAULT_IMAGES_DIR
from utils.formatters import format_percentage, get_performance_delta_color


@st.cache_resource
def load_player_image_cached(player_name: str, images_dir: str = DEFAULT_IMAGES_DIR):
    """Load player image with caching.
    
    Args:
        player_name: Name of the player
        images_dir: Directory containing player images
        
    Returns:
        PIL Image object or None if not found
    """
    from pathlib import Path
    
    images_path = Path(images_dir)
    for ext in ['.jpeg', '.jpg', '.png', '.webp']:
        image_path = images_path / f"{player_name}{ext}"
        if image_path.exists():
            try:
                return Image.open(image_path)
            except Exception as e:
                st.warning(f"Could not load image for {player_name}: {e}")
                return None
    return None


def display_kpi_card(kpi_name: str, value: float, target_min: float, 
                     target_max: float, target_optimal: Optional[float] = None,
                     delta_label: Optional[str] = None) -> None:
    """Display a single KPI metric card with color coding.
    
    Args:
        kpi_name: Name of the KPI
        value: Current value
        target_min: Minimum acceptable value
        target_max: Maximum expected value
        target_optimal: Optimal target value
        delta_label: Optional label for delta display
    """
    color = get_performance_delta_color(value, target_min, target_max, target_optimal)
    
    delta_value = None
    if delta_label:
        delta_value = delta_label
    elif target_optimal is not None:
        delta_value = f"Target: {format_percentage(target_optimal)}"
    
    st.metric(
        label=kpi_name,
        value=format_percentage(value),
        delta=delta_value,
        delta_color=color
    )


def display_match_banner(loader, opponent_name: Optional[str] = None) -> None:
    """Display match result banner.
    
    Args:
        loader: ExcelMatchLoader instance with team data
        opponent_name: Name of opponent (not displayed, kept for compatibility)
    """
    import performance_tracker as pt
    
    if loader is None or not hasattr(loader, 'team_data') or not loader.team_data:
        return
    
    set_results = pt.compute_set_results_from_loader(loader) if hasattr(pt, 'compute_set_results_from_loader') else []
    summary = pt.get_match_summary(set_results) if hasattr(pt, 'get_match_summary') else {'label': 'No sets', 'outcome': 'N/A'}
    
    banner_color = "#e6ffed" if summary['outcome'] == 'Win' else ("#ffecec" if summary['outcome'] == 'Loss' else "#f5f5f5")
    
    st.markdown(f"""
    <div style="padding:20px 24px;border:2px solid #040C7B;border-radius:12px;background:{banner_color};margin-bottom:16px;">
        <div style="font-size:36px;font-weight:700;color:#040C7B;">{summary['label']}</div>
    </div>
    """, unsafe_allow_html=True)


def get_position_full_name(position: str) -> str:
    """Convert position abbreviation to full name.
    
    Args:
        position: Position abbreviation (OH1, MB1, etc.)
        
    Returns:
        Full position name
    """
    position_names = {
        'OH1': 'Outside Hitter',
        'OH2': 'Outside Hitter',
        'MB1': 'Middle Blocker',
        'MB2': 'Middle Blocker',
        'OPP': 'Opposite',
        'S': 'Setter',
        'L': 'Libero'
    }
    return position_names.get(position, position)


def get_position_emoji(position: str) -> str:
    """Get emoji for player position.
    
    Args:
        position: Position abbreviation
        
    Returns:
        Emoji string
    """
    position_emojis = {
        'OH1': '🏐', 'OH2': '🏐',
        'MB1': '🛡️', 'MB2': '🛡️',
        'OPP': '⚡',
        'S': '🎯',
        'L': '🕸️'
    }
    return position_emojis.get(position, '👤')

