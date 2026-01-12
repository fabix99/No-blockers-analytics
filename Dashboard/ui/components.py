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
        images_dir: Directory containing player images (relative to project root)
        
    Returns:
        PIL Image object or None if not found
    """
    from pathlib import Path
    
    # Resolve path relative to Dashboard directory (go up one level to project root)
    # This file is in Dashboard/ui/, so parent.parent gets us to Dashboard/, then parent gets project root
    current_file = Path(__file__)
    dashboard_dir = current_file.parent.parent  # Go from ui/ to Dashboard/
    project_root = dashboard_dir.parent  # Go from Dashboard/ to project root
    images_path = project_root / images_dir
    
    for ext in ['.jpeg', '.jpg', '.png', '.webp']:
        image_path = images_path / f"{player_name}{ext}"
        if image_path.exists():
            try:
                return Image.open(image_path)
            except Exception as e:
                st.warning(f"Could not load image for {player_name}: {e}")
                return None
    return None


@st.cache_resource
def load_logo_cached(logo_filename: str = "IMG_1377.JPG", images_dir: str = "assets/images"):
    """Load team logo with caching.
    
    Args:
        logo_filename: Name of the logo file (default: IMG_1377.JPG)
        images_dir: Directory containing logo (relative to project root)
        
    Returns:
        PIL Image object or None if not found
    """
    from pathlib import Path
    
    # Resolve path relative to Dashboard directory (go up one level to project root)
    # This file is in Dashboard/ui/, so parent.parent gets us to Dashboard/, then parent gets project root
    current_file = Path(__file__)
    dashboard_dir = current_file.parent.parent  # Go from ui/ to Dashboard/
    project_root = dashboard_dir.parent  # Go from Dashboard/ to project root
    images_path = project_root / images_dir
    
    # Try different case variations
    logo_variants = [
        logo_filename,
        logo_filename.replace('.JPG', '.jpg'),
        logo_filename.replace('.jpg', '.JPG'),
        logo_filename.lower(),
        logo_filename.upper(),
    ]
    
    for variant in logo_variants:
        logo_path = images_path / variant
        if logo_path.exists():
            try:
                return Image.open(logo_path)
            except Exception as e:
                return None
    
    # Also try common extensions
    base_name = logo_filename.rsplit('.', 1)[0] if '.' in logo_filename else logo_filename
    for ext in ['.jpeg', '.jpg', '.JPG', '.JPEG', '.png', '.PNG']:
        logo_path = images_path / f"{base_name}{ext}"
        if logo_path.exists():
            try:
                return Image.open(logo_path)
            except Exception as e:
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


def _get_match_result_summary(loader) -> Optional[Dict[str, Any]]:
    """Extract match result summary from loader.
    
    Args:
        loader: ExcelMatchLoader instance
        
    Returns:
        Dictionary with 'outcome', 'label', 'sets_won', 'sets_lost' or None
    """
    import performance_tracker as pt
    
    if loader is None:
        return None
    
    # Check for team data
    has_team_data = (hasattr(loader, 'team_data') and loader.team_data) or \
                   (hasattr(loader, 'team_data_by_set') and loader.team_data_by_set)
    if not has_team_data:
        return None
    
    try:
        set_results = pt.compute_set_results_from_loader(loader) if hasattr(pt, 'compute_set_results_from_loader') else []
        summary = pt.get_match_summary(set_results) if hasattr(pt, 'get_match_summary') else {'label': 'No sets', 'outcome': 'N/A'}
        
        # Count sets won/lost - get_match_summary already provides this
        sets_won = summary.get('sets_us', 0)
        sets_lost = summary.get('sets_them', 0)
        
        summary['sets_won'] = sets_won
        summary['sets_lost'] = sets_lost
        
        return summary
    except Exception:
        return None


def display_match_banner(loader, opponent_name: Optional[str] = None) -> None:
    """Display match result banner with executive summary.
    
    Args:
        loader: ExcelMatchLoader instance with team data
        opponent_name: Name of opponent (not displayed, kept for compatibility)
    """
    import performance_tracker as pt
    
    if loader is None or not hasattr(loader, 'team_data') or not loader.team_data:
        return
    
    set_results = pt.compute_set_results_from_loader(loader) if hasattr(pt, 'compute_set_results_from_loader') else []
    summary = pt.get_match_summary(set_results) if hasattr(pt, 'get_match_summary') else {'label': 'No sets', 'outcome': 'N/A'}
    
    # Get KPIs for executive summary
    kpis = None
    if hasattr(pt, 'compute_team_kpis_from_loader'):
        try:
            kpis = pt.compute_team_kpis_from_loader(loader)
        except Exception:
            pass
    
    banner_color = "#e6ffed" if summary['outcome'] == 'Win' else ("#ffecec" if summary['outcome'] == 'Loss' else "#f5f5f5")
    outcome_icon = "🏆" if summary['outcome'] == 'Win' else ("📉" if summary['outcome'] == 'Loss' else "🤝")
    
    st.markdown(f"""
    <div style="padding:20px 24px;border:2px solid #040C7B;border-radius:12px;background:{banner_color};margin-bottom:16px;">
        <div style="font-size:32px;font-weight:700;color:#040C7B;">{outcome_icon} {summary['label']}</div>
    </div>
    """, unsafe_allow_html=True)


def display_executive_summary(loader, kpis: Optional[Dict[str, Any]] = None) -> None:
    """Display executive summary with key takeaways.
    
    Shows 3-4 bullet points summarizing the match:
    - Strengths (what went well)
    - Focus areas (what needs work)
    - Key stat highlights
    
    Args:
        loader: ExcelMatchLoader instance with team data
        kpis: Optional pre-computed KPIs dictionary
    """
    import performance_tracker as pt
    from config import KPI_TARGETS
    
    if loader is None:
        return
    
    # Get KPIs if not provided
    if kpis is None and hasattr(pt, 'compute_team_kpis_from_loader'):
        try:
            kpis = pt.compute_team_kpis_from_loader(loader)
        except Exception:
            pass
    
    if kpis is None:
        return
    
    # Analyze performance vs targets
    strengths = []
    focus_areas = []
    
    # Check each KPI
    metrics_to_check = [
        ('side_out_efficiency', 'Receiving Point Rate', KPI_TARGETS.get('side_out_percentage', {}).get('optimal', 0.70)),
        ('break_point_rate', 'Serving Point Rate', KPI_TARGETS.get('break_point_rate', {}).get('optimal', 0.55)),
        ('attack_kill_pct', 'Attack Kill %', KPI_TARGETS.get('kill_percentage', {}).get('optimal', 0.45)),
        ('reception_quality', 'Reception Quality', KPI_TARGETS.get('reception_quality', {}).get('optimal', 0.75)),
        ('serve_in_rate', 'Serve In-Rate', KPI_TARGETS.get('serve_in_rate', {}).get('optimal', 0.90)),
    ]
    
    for kpi_key, display_name, target in metrics_to_check:
        value = kpis.get(kpi_key, 0)
        if value >= target:
            strengths.append((display_name, value, target))
        elif value < target * 0.85:  # Significantly below target
            focus_areas.append((display_name, value, target))
    
    # Build summary bullets as HTML
    summary_html_items = []
    
    if strengths:
        top_strength = max(strengths, key=lambda x: x[1] - x[2])  # Best vs target
        summary_html_items.append(
            f'<div style="font-size: 15px; margin-bottom: 8px; color: #155724;">'
            f'🌟 <strong>Strength:</strong> {top_strength[0]} at {top_strength[1]:.0%} (target: {top_strength[2]:.0%})'
            f'</div>'
        )
    
    if focus_areas:
        worst_gap = min(focus_areas, key=lambda x: x[1] - x[2])  # Worst vs target
        summary_html_items.append(
            f'<div style="font-size: 15px; margin-bottom: 8px; color: #856404;">'
            f'🎯 <strong>Focus Area:</strong> {worst_gap[0]} at {worst_gap[1]:.0%} (target: {worst_gap[2]:.0%})'
            f'</div>'
        )
    
    # Add context about scoring
    side_out = kpis.get('side_out_efficiency', 0)
    break_point = kpis.get('break_point_rate', 0)
    
    if side_out > break_point + 0.10:
        summary_html_items.append(
            '<div style="font-size: 15px; margin-bottom: 8px; color: #0c5460;">'
            '📊 <strong>Pattern:</strong> Stronger on reception than serve - focus on serve pressure'
            '</div>'
        )
    elif break_point > side_out + 0.10:
        summary_html_items.append(
            '<div style="font-size: 15px; margin-bottom: 8px; color: #0c5460;">'
            '📊 <strong>Pattern:</strong> Stronger on serve than reception - protect serve advantage'
            '</div>'
        )
    
    # Render summary as single HTML block
    if summary_html_items:
        items_html = ''.join(summary_html_items)
        html_block = f'<div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 16px 20px; border-radius: 10px; margin-bottom: 16px; border-left: 5px solid #040C7B; box-shadow: 0 2px 8px rgba(0,0,0,0.08);"><div style="font-size: 16px; font-weight: 700; color: #040C7B; margin-bottom: 12px; letter-spacing: 0.5px;">📋 EXECUTIVE SUMMARY</div>{items_html}</div>'
        st.markdown(html_block, unsafe_allow_html=True)


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


def display_player_image_and_info(player_name: str, position: Optional[str], 
                                   image_size: int = 180, use_sidebar: bool = False) -> None:
    """Display player image and basic info in sidebar or main area.
    
    Args:
        player_name: Name of the player
        position: Player position abbreviation (OH1, MB1, etc.)
        image_size: Size of the image in pixels
        use_sidebar: If True, display in sidebar; otherwise in main area
    """
    if use_sidebar:
        # Display in sidebar
        st.sidebar.markdown("<br>", unsafe_allow_html=True)
        
        # Load and display player image
        player_image = load_player_image_cached(player_name)
        if player_image:
            # Create a copy and resize with high quality, preserving aspect ratio
            img_copy = player_image.copy()
            aspect_ratio = img_copy.width / img_copy.height
            if aspect_ratio > 1:
                new_width = image_size
                new_height = int(image_size / aspect_ratio)
            else:
                new_height = image_size
                new_width = int(image_size * aspect_ratio)
            # Use resize() with LANCZOS for better quality
            img_copy = img_copy.resize((new_width, new_height), Image.Resampling.LANCZOS)
            # Center the image using columns
            col1, col2, col3 = st.sidebar.columns([0.5, 1, 0.5])
            with col1:
                st.write("")
            with col2:
                st.image(img_copy, width=image_size, use_container_width=False)
            with col3:
                st.write("")
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
        
        # Display player name and position - both white like Navigation title
        position_full = get_position_full_name(position) if position else 'Unknown'
        st.sidebar.markdown(f"""
        <div style="padding: 10px 0; text-align: center;">
            <h3 style="margin: 0 0 8px 0; color: #FFFFFF !important; font-size: 1.2rem; font-weight: 600;">{player_name}</h3>
            <h4 style="margin: 0; color: #FFFFFF !important; font-size: 1rem; font-weight: 500; text-transform: uppercase; letter-spacing: 0.5px;">
                {position_full}
            </h4>
        </div>
        """, unsafe_allow_html=True)
        
        st.sidebar.markdown("---")
    else:
        # Display in main area
        col1, col2 = st.columns([1, 3])
        
        with col1:
            player_image = load_player_image_cached(player_name)
            if player_image:
                img_copy = player_image.copy()
                aspect_ratio = img_copy.width / img_copy.height
                if aspect_ratio > 1:
                    new_width = image_size
                    new_height = int(image_size / aspect_ratio)
                else:
                    new_height = image_size
                    new_width = int(image_size * aspect_ratio)
                img_copy = img_copy.resize((new_width, new_height), Image.Resampling.LANCZOS)
                st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
                st.markdown("<div style='display: flex; justify-content: center; width: 100%;'>", unsafe_allow_html=True)
                st.image(img_copy, width=image_size, use_container_width=False)
                st.markdown("</div>", unsafe_allow_html=True)
            else:
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
            position_emoji = get_position_emoji(position) if position else '👤'
            position_full = get_position_full_name(position) if position else 'Unknown'
            st.markdown(f"""
            <div style="padding: 10px 0; text-align: left;">
                <h3 style="margin: 0; color: #050d76; font-size: 1.5rem;">{player_name}</h3>
                <p style="margin: 5px 0; font-size: 18px; color: #666;">
                    {position_emoji} {position_full}
                </p>
            </div>
            """, unsafe_allow_html=True)

