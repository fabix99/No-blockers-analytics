"""
Player Analysis UI Module

Displays detailed player performance analysis with KPIs, insights, and charts.
Features premium visual components matching Team Overview quality standards.
"""
from typing import Dict, Any, Optional
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from match_analyzer import MatchAnalyzer
from config import SETTER_THRESHOLD, CHART_COLORS, KPI_TARGETS, OUTCOME_COLORS, CHART_HEIGHTS
from ui.components import (
    get_position_full_name, get_position_emoji, load_player_image_cached,
    display_player_image_and_info
)
from ui.premium_components import display_premium_section_header
from ui.team_overview_helpers import _display_metric_styling
from utils.helpers import get_player_position, get_player_df, filter_good_receptions, filter_good_digs, filter_block_touches
from utils.formatters import (
    format_percentage, get_performance_color,
    format_percentage_with_sample_size, get_sample_size_warning, should_hide_metric
)
from charts.player_charts import create_player_charts
from charts.utils import apply_beautiful_theme, plotly_config
from services.kpi_calculator import KPICalculator


def display_player_analysis(analyzer: MatchAnalyzer, loader=None) -> None:
    """Display detailed player analysis.
    
    Args:
        analyzer: MatchAnalyzer instance with loaded match data
        loader: Optional ExcelMatchLoader instance for team data
    """
    # MEDIUM PRIORITY 15: Error handling
    try:
        st.markdown('<h2 class="main-header">👥 Player Analysis</h2>', unsafe_allow_html=True)
        
        # Calculate player metrics
        player_stats = analyzer.calculate_player_metrics()
        
        if player_stats is None:
            st.error("No player statistics available")
            return
    except Exception as e:
        st.error(f"❌ Error displaying player analysis: {str(e)}")
        st.info("💡 Please try refreshing the page or re-uploading your data file.")
        import logging
        logging.error(f"Error in display_player_analysis: {e}", exc_info=True)
        return
    
    # Player selection
    selected_player = _select_player(analyzer, player_stats)
    
    if selected_player:
        _display_player_details(analyzer, selected_player, player_stats, loader)


def _select_player(analyzer: MatchAnalyzer, player_stats: Dict[str, Any]) -> Optional[str]:
    """Display player selection interface with dropdown, ordered by position then alphabetically.
    
    Returns:
        Selected player name or None
    """
    df = analyzer.match_data
    players = [p for p in player_stats.keys() if p.upper() != 'OUR_TEAM']
    
    st.markdown("### 👥 Player Selection")
    
    # Position priority order (S, OH, MB, OPP, L, then Unknown)
    position_priority = {
        'S': 1, 'OH1': 2, 'OH2': 2, 'OH': 2,
        'MB1': 3, 'MB2': 3, 'MB': 3,
        'OPP': 4,
        'L': 5
    }
    
    # Create list of (priority, position, player_name) for sorting
    player_list = []
    for player in players:
        position = get_player_position(df, player) or 'Unknown'
        # Get position group for sorting (OH1/OH2 -> OH, MB1/MB2 -> MB)
        position_group = position
        if position.startswith('OH'):
            position_group = 'OH'
        elif position.startswith('MB'):
            position_group = 'MB'
        
        priority = position_priority.get(position_group, 99)
        player_list.append((priority, position_group, player, position))
    
    # Sort by priority, then position, then player name (alphabetical)
    player_list.sort(key=lambda x: (x[0], x[1], x[2]))
    
    # Create options for dropdown
    player_options = []
    player_dict = {}  # Map display name to actual player name
    
    for priority, position_group, player_name, position in player_list:
        position_emoji = get_position_emoji(position)
        position_full = get_position_full_name(position)
        display_name = f"{position_emoji} {player_name} ({position_full})"
        player_options.append(display_name)
        player_dict[display_name] = player_name
    
    # Use selectbox (dropdown) instead of radio
    selected_display = st.selectbox(
        "Choose a player for detailed analysis:",
        options=player_options,
        help="Select a player to see their detailed performance statistics",
        label_visibility="visible"
    )
    
    return player_dict.get(selected_display) if selected_display else None


def _display_player_details(analyzer: MatchAnalyzer, player_name: str, 
                           player_stats: Dict[str, Any], loader=None) -> None:
    """Display detailed statistics for a player.
    
    Restructured into 4 logical sections:
    1. Player Profile & Match Participation
    2. Core Performance Metrics
    3. Detailed Statistics
    4. Performance Charts & Trends
    
    Args:
        analyzer: MatchAnalyzer instance
        player_name: Name of the player
        player_stats: Dictionary of all player statistics
        loader: Optional ExcelMatchLoader instance for team data
    """
    player_data = player_stats[player_name]
    df = analyzer.match_data
    player_df = get_player_df(df, player_name)
    position = get_player_position(df, player_name)
    
    # Display player image and info in sidebar
    display_player_image_and_info(player_name, position, image_size=78, use_sidebar=True)
    
    # Check if setter
    total_sets = player_data.get('total_sets', 0)
    is_setter = total_sets > 0 and total_sets >= player_data['total_actions'] * SETTER_THRESHOLD
    
    # Display CSS styling for consistent appearance
    _display_metric_styling()
    
    # ============================================================
    # SECTION 1: Player Profile & Match Participation
    # ============================================================
    display_premium_section_header("Player Profile & Match Participation", "👤", "Player overview and match involvement")
    
    # Enhanced player header with key stats
    _display_player_header(player_name, position, player_data)
    
    # Match participation metrics
    try:
        _display_player_participation(analyzer, player_name, player_data, df)
    except Exception as e:
        st.warning(f"⚠️ Could not display match participation: {str(e)}")
    
    # ============================================================
    # SECTION 2: Core Performance Metrics
    # ============================================================
    display_premium_section_header("Core Performance Metrics", "📊", "Key performance indicators by skill area")
    
    try:
        _display_core_performance_metrics(analyzer, player_name, player_data, position, is_setter, loader, df)
    except Exception as e:
        st.warning(f"⚠️ Could not display core performance metrics: {str(e)}")
    
    # ============================================================
    # SECTION 3: Detailed Statistics
    # ============================================================
    display_premium_section_header("Detailed Statistics", "📋", "Comprehensive breakdown by skill")
    
    try:
        _display_detailed_stats(player_name, player_data, is_setter, position, analyzer, loader)
    except Exception as e:
        st.warning(f"⚠️ Could not display detailed stats: {str(e)}")
    
    # ============================================================
    # SECTION 4: Performance Charts & Trends
    # ============================================================
    display_premium_section_header("Performance Charts & Trends", "📈", "Visual analysis of player performance")
    
    try:
        create_player_charts(analyzer, player_name, loader)
    except Exception as e:
        st.warning(f"⚠️ Could not display player charts: {str(e)}")


def _display_player_header(player_name: str, position: Optional[str], player_data: Dict[str, Any]) -> None:
    """Display a premium player header with key stats.
    
    Enhanced with premium styling matching Team Overview quality.
    
    Args:
        player_name: Player's name
        position: Player's position code
        player_data: Player's statistics dictionary
    """
    position_emoji = get_position_emoji(position)
    position_full = get_position_full_name(position)
    
    # Calculate key stats
    attack_kills = player_data.get('attack_kills', 0)
    service_aces = player_data.get('service_aces', 0)
    block_kills = player_data.get('block_kills', 0)
    total_points = attack_kills + service_aces + block_kills
    
    # Premium header with enhanced styling
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #ffffff 0%, #f5f7ff 100%);
                padding: 20px 24px; border-radius: 12px; margin-bottom: 20px;
                border: 2px solid rgba(4, 12, 123, 0.1);
                box-shadow: 0 4px 12px rgba(4, 12, 123, 0.08);">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 16px;">
            <div>
                <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 4px;">
                    <span style="font-size: 32px;">{position_emoji}</span>
                    <span style="font-size: 28px; font-weight: 700; color: #040C7B;">
                        {player_name}
                    </span>
                </div>
                <div style="font-size: 16px; color: #666; font-weight: 500; margin-left: 44px;">
                    {position_full}
                </div>
            </div>
            <div style="display: flex; gap: 32px; margin-top: 8px; flex-wrap: wrap;">
                <div style="text-align: center; min-width: 80px;">
                    <div style="font-size: 28px; font-weight: 700; color: #040C7B;">{total_points}</div>
                    <div style="font-size: 13px; color: #666; font-weight: 500;">Total Points</div>
                </div>
                <div style="text-align: center; min-width: 80px;">
                    <div style="font-size: 28px; font-weight: 700; color: #28a745;">{attack_kills}</div>
                    <div style="font-size: 13px; color: #666; font-weight: 500;">Kills</div>
                </div>
                <div style="text-align: center; min-width: 80px;">
                    <div style="font-size: 28px; font-weight: 700; color: #6C63FF;">{service_aces}</div>
                    <div style="font-size: 13px; color: #666; font-weight: 500;">Aces</div>
                </div>
                <div style="text-align: center; min-width: 80px;">
                    <div style="font-size: 28px; font-weight: 700; color: #FFD700;">{block_kills}</div>
                    <div style="font-size: 13px; color: #666; font-weight: 500;">Blocks</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _display_player_participation(analyzer: MatchAnalyzer, player_name: str, 
                                  player_data: Dict[str, Any], df: pd.DataFrame) -> None:
    """Display match participation metrics.
    
    Args:
        analyzer: MatchAnalyzer instance
        player_name: Player's name
        player_data: Player's statistics dictionary
        df: Match data DataFrame
    """
    player_df = get_player_df(df, player_name)
    
    # Calculate match participation
    played_sets = sorted(player_df['set_number'].unique())
    total_sets_in_match = sorted(df['set_number'].unique())
    sets_played = len(played_sets)
    total_sets = len(total_sets_in_match)
    
    # Calculate total actions and participation rate
    total_actions = player_data.get('total_actions', 0)
    team_total_actions = len(df)
    participation_rate = (total_actions / team_total_actions * 100) if team_total_actions > 0 else 0
    
    col1_part, col2_part, col3_part = st.columns(3)
    
    with col1_part:
        st.metric("Sets Played", f"{sets_played}/{total_sets}")
    
    with col2_part:
        st.metric("Total Actions", f"{total_actions}")
    
    with col3_part:
        st.metric("Participation", f"{participation_rate:.1f}%")


def _display_player_summary_card(analyzer: MatchAnalyzer, player_name: str, player_data: Dict[str, Any],
                                position: Optional[str], loader=None) -> None:
    """Display player summary card with match participation, highlights, and performance overview."""
    df = analyzer.match_data
    player_df = get_player_df(df, player_name)
    
    # Check if setter
    total_sets = player_data.get('total_sets', 0)
    is_setter = total_sets > 0 and total_sets >= player_data['total_actions'] * SETTER_THRESHOLD
    
    # Calculate match participation
    played_sets = sorted(player_df['set_number'].unique())
    total_sets_in_match = sorted(df['set_number'].unique())
    sets_played = len(played_sets)
    total_sets = len(total_sets_in_match)
    
    # Calculate total actions and participation rate
    total_actions = player_data.get('total_actions', 0)
    team_total_actions = len(df)
    participation_rate = (total_actions / team_total_actions * 100) if team_total_actions > 0 else 0
    
    # Calculate player KPIs for highlights
    kpis = _calculate_player_kpis(analyzer, player_name, player_data, position, is_setter, loader)
    
    # Find best metric
    best_metric = None
    best_value = 0
    best_metric_name = ""
    
    if kpis.get('attack_kill_pct', 0) > best_value:
        best_value = kpis['attack_kill_pct']
        best_metric = 'attack_kill_pct'
        best_metric_name = "Attack Kill %"
    if kpis.get('reception_quality', 0) > best_value:
        best_value = kpis['reception_quality']
        best_metric = 'reception_quality'
        best_metric_name = "Reception Quality"
    if kpis.get('block_kill_pct', 0) > best_value:
        best_value = kpis['block_kill_pct']
        best_metric = 'block_kill_pct'
        best_metric_name = "Block Kill %"
    if kpis.get('serve_in_rate', 0) > best_value:
        best_value = kpis['serve_in_rate']
        best_metric = 'serve_in_rate'
        best_metric_name = "Serve In-Rate"
    if kpis.get('setting_quality', 0) > best_value:
        best_value = kpis['setting_quality']
        best_metric = 'setting_quality'
        best_metric_name = "Setting Quality"
    
    # Calculate total points contributed
    attack_kills = player_data.get('attack_kills', 0)
    service_aces = player_data.get('service_aces', 0)
    block_kills = player_data.get('block_kills', 0)
    total_points = attack_kills + service_aces + block_kills
    
    # Create summary card
    st.markdown("### 📋 Player Summary")
    
    # Top section: Match Participation in 1 row with 3 columns
    st.markdown("#### 🎮 Match Participation")
    col1_part, col2_part, col3_part = st.columns(3)
    
    with col1_part:
        st.metric("Sets Played", f"{sets_played}/{total_sets}")
    
    with col2_part:
        st.metric("Total Actions", f"{total_actions}")
    
    with col3_part:
        st.metric("Participation", f"{participation_rate:.1f}%")
    


def _create_mini_attack_kill_chart(player_df: pd.DataFrame, player_data: Dict[str, Any], player_name: str = "") -> None:
    """Create a mini attack kill percentage donut chart."""
    attacks = player_df[player_df['action'] == 'attack']
    
    attack_kills = len(attacks[attacks['outcome'] == 'kill']) if len(attacks) > 0 else 0
    attack_attempts = player_data.get('attack_attempts', len(attacks)) if len(attacks) > 0 else 0
    
    labels = []
    values = []
    colors_list = []
    
    if attack_attempts == 0:
        # Show empty state
        labels = ['No Data']
        values = [1]
        colors_list = ['#E0E0E0']
    else:
        attack_errors = len(attacks[attacks['outcome'].isin(['blocked', 'out', 'net'])]) if len(attacks) > 0 else 0  # error removed
        attack_good = attack_attempts - attack_kills - attack_errors
        
        if attack_kills > 0:
            labels.append('Kills')
            values.append(attack_kills)
            colors_list.append(OUTCOME_COLORS.get('kill', '#28A745'))
        if attack_good > 0:
            labels.append('Good')
            values.append(attack_good)
            colors_list.append(OUTCOME_COLORS.get('good', '#6CBF47'))
        if attack_errors > 0:
            labels.append('Errors')
            values.append(attack_errors)
            colors_list.append(OUTCOME_COLORS.get('error', '#FF6B6B'))
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(colors=colors_list, line=dict(color='white', width=2)),
        textinfo='percent' if attack_attempts > 0 else 'none',
        textfont=dict(size=13, color='#050d76', family='Inter, sans-serif'),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>' if attack_attempts > 0 else '<b>No attack data</b><extra></extra>'
    )])
    
    # Add annotation for empty state or kill percentage
    annotations = []
    if attack_attempts == 0:
        annotations.append(dict(
            text='No Data',
            x=0.5, y=0.5,
            font=dict(size=12, color='#999999', family='Inter, sans-serif'),
            showarrow=False
        ))
    elif attack_kills > 0:
        kill_pct = (attack_kills / attack_attempts) * 100
        annotations.append(dict(
            text=f'{kill_pct:.1f}%',
            x=0.5, y=0.5,
            font=dict(size=16, color='#050d76', family='Inter, sans-serif', weight='bold'),
            showarrow=False
        ))
    
    fig.update_layout(
        title=dict(text="Attack Kill %", font=dict(size=14, color='#050d76', family='Inter, sans-serif')),
        height=220,
        showlegend=attack_attempts > 0,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=10)),
        margin=dict(l=10, r=10, t=50, b=50),
        font=dict(family='Inter, sans-serif', size=10, color='#050d76'),
        paper_bgcolor='white',
        plot_bgcolor='white',
        annotations=annotations
    )
    fig = apply_beautiful_theme(fig, "Attack Kill %")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"mini_attack_kill_{player_name}")


def _create_mini_serve_rate_chart(player_df: pd.DataFrame, player_data: Dict[str, Any], player_name: str = "") -> None:
    """Create a mini serve in-rate donut chart."""
    serves = player_df[player_df['action'] == 'serve']
    service_attempts = player_data.get('service_attempts', len(serves)) if len(serves) > 0 else 0
    
    labels = []
    values = []
    colors_list = []
    
    if service_attempts == 0:
        # Show empty state
        labels = ['No Data']
        values = [1]
        colors_list = ['#E0E0E0']
    else:
        service_aces = player_data.get('service_aces', 0)
        service_good = len(serves[serves['outcome'] == 'good']) if len(serves) > 0 else 0
        service_errors = len(serves[serves['outcome'] == 'error']) if len(serves) > 0 else 0
        
        if service_aces + service_good > 0:
            labels.append('In')
            values.append(service_aces + service_good)
            colors_list.append(OUTCOME_COLORS.get('good', '#6CBF47'))
        if service_errors > 0:
            labels.append('Errors')
            values.append(service_errors)
            colors_list.append(OUTCOME_COLORS.get('error', '#FF6B6B'))
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(colors=colors_list, line=dict(color='white', width=2)),
        textinfo='percent' if service_attempts > 0 else 'none',
        textfont=dict(size=13, color='#050d76', family='Inter, sans-serif'),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>' if service_attempts > 0 else '<b>No serve data</b><extra></extra>'
    )])
    
    # Add annotation for empty state or in-rate percentage
    annotations = []
    if service_attempts == 0:
        annotations.append(dict(
            text='No Data',
            x=0.5, y=0.5,
            font=dict(size=12, color='#999999', family='Inter, sans-serif'),
            showarrow=False
        ))
    elif service_attempts > 0:
        service_aces = player_data.get('service_aces', 0)
        service_good = len(serves[serves['outcome'] == 'good']) if len(serves) > 0 else 0
        in_rate = ((service_aces + service_good) / service_attempts) * 100
        annotations.append(dict(
            text=f'{in_rate:.1f}%',
            x=0.5, y=0.5,
            font=dict(size=16, color='#050d76', family='Inter, sans-serif', weight='bold'),
            showarrow=False
        ))
    
    fig.update_layout(
        title=dict(text="Serve In-Rate", font=dict(size=14, color='#050d76', family='Inter, sans-serif')),
        height=220,
        showlegend=service_attempts > 0,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=10)),
        margin=dict(l=10, r=10, t=50, b=50),
        font=dict(family='Inter, sans-serif', size=10, color='#050d76'),
        paper_bgcolor='white',
        plot_bgcolor='white',
        annotations=annotations
    )
    fig = apply_beautiful_theme(fig, "Serve In-Rate")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"mini_serve_rate_{player_name}")


def _create_mini_reception_chart(player_df: pd.DataFrame, player_name: str = "") -> None:
    """Create a mini reception quality donut chart with Perfect/Good/Poor breakdown."""
    receives = player_df[player_df['action'] == 'receive']
    
    # Count by granular outcomes
    perfect_receives = len(receives[receives['outcome'] == 'perfect']) if len(receives) > 0 else 0
    good_receives = len(receives[receives['outcome'] == 'good']) if len(receives) > 0 else 0
    poor_receives = len(receives[receives['outcome'] == 'poor']) if len(receives) > 0 else 0
    error_receives = len(receives[receives['outcome'] == 'error']) if len(receives) > 0 else 0
    total_receives = len(receives)
    
    # Group poor and error together as "Poor"
    poor_total = poor_receives + error_receives
    
    labels = []
    values = []
    colors_list = []
    
    if total_receives == 0:
        # Show empty state
        labels = ['No Data']
        values = [1]
        colors_list = ['#E0E0E0']
    else:
        if perfect_receives > 0:
            labels.append('Perfect')
            values.append(perfect_receives)
            colors_list.append(OUTCOME_COLORS.get('perfect', '#28A745'))
        if good_receives > 0:
            labels.append('Good')
            values.append(good_receives)
            colors_list.append(OUTCOME_COLORS.get('good', '#6CBF47'))
        if poor_total > 0:
            labels.append('Poor')
            values.append(poor_total)
            colors_list.append(OUTCOME_COLORS.get('error', '#FF6B6B'))
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(colors=colors_list, line=dict(color='white', width=2)),
        textinfo='percent' if total_receives > 0 else 'none',
        textfont=dict(size=13, color='#050d76', family='Inter, sans-serif'),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>' if total_receives > 0 else '<b>No reception data</b><extra></extra>'
    )])
    
    # Add annotation for empty state
    annotations = []
    if total_receives == 0:
        annotations.append(dict(
            text='No Data',
            x=0.5, y=0.5,
            font=dict(size=12, color='#999999', family='Inter, sans-serif'),
            showarrow=False
        ))
    
    fig.update_layout(
        title=dict(text="Reception Quality", font=dict(size=14, color='#050d76', family='Inter, sans-serif')),
        height=220,
        showlegend=total_receives > 0,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=10)),
        margin=dict(l=10, r=10, t=50, b=50),
        font=dict(family='Inter, sans-serif', size=10, color='#050d76'),
        paper_bgcolor='white',
        plot_bgcolor='white',
        annotations=annotations
    )
    fig = apply_beautiful_theme(fig, "Reception Quality")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"mini_reception_{player_name}")


def _create_mini_block_chart(player_df: pd.DataFrame, player_name: str = "") -> None:
    """Create a mini block outcomes donut chart."""
    blocks = player_df[player_df['action'] == 'block']
    
    block_kills = len(blocks[blocks['outcome'] == 'kill']) if len(blocks) > 0 else 0
    block_touches = len(blocks[blocks['outcome'] == 'touch']) if len(blocks) > 0 else 0
    block_errors = len(blocks[blocks['outcome'].isin(['error', 'blocked', 'out', 'net'])]) if len(blocks) > 0 else 0
    block_missed = len(blocks[blocks['outcome'] == 'missed']) if len(blocks) > 0 else 0
    total_blocks = len(blocks)
    
    labels = []
    values = []
    colors_list = []
    
    if total_blocks == 0:
        # Show empty state
        labels = ['No Data']
        values = [1]
        colors_list = ['#E0E0E0']
    else:
        if block_kills > 0:
            labels.append('Kills')
            values.append(block_kills)
            colors_list.append(OUTCOME_COLORS.get('kill', '#4CAF50'))
        if block_touches > 0:
            labels.append('Touches')
            values.append(block_touches)
            colors_list.append(OUTCOME_COLORS.get('good', '#8BC34A'))
        if block_missed > 0:
            labels.append('Missed')
            values.append(block_missed)
            colors_list.append('#F5A623')
        if block_errors > 0:
            labels.append('Errors')
            values.append(block_errors)
            colors_list.append(OUTCOME_COLORS.get('error', '#FF6B6B'))
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(colors=colors_list, line=dict(color='white', width=2)),
        textinfo='percent' if total_blocks > 0 else 'none',
        textfont=dict(size=13, color='#050d76', family='Inter, sans-serif'),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>' if total_blocks > 0 else '<b>No block data</b><extra></extra>'
    )])
    
    # Add annotation for empty state
    annotations = []
    if total_blocks == 0:
        annotations.append(dict(
            text='No Data',
            x=0.5, y=0.5,
            font=dict(size=12, color='#999999', family='Inter, sans-serif'),
            showarrow=False
        ))
    
    fig.update_layout(
        title=dict(text="Block Outcomes", font=dict(size=14, color='#050d76', family='Inter, sans-serif')),
        height=220,
        showlegend=total_blocks > 0,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=10)),
        margin=dict(l=10, r=10, t=50, b=50),
        font=dict(family='Inter, sans-serif', size=10, color='#050d76'),
        paper_bgcolor='white',
        plot_bgcolor='white',
        annotations=annotations
    )
    fig = apply_beautiful_theme(fig, "Block Outcomes")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"mini_block_{player_name}")


def _create_mini_dig_chart(player_df: pd.DataFrame, player_name: str = "") -> None:
    """Create a mini dig outcomes donut chart."""
    digs = player_df[player_df['action'] == 'dig']
    
    from utils.helpers import filter_good_digs
    good_digs = len(filter_good_digs(digs)) if len(digs) > 0 else 0
    total_digs = len(digs)
    poor_digs = total_digs - good_digs
    
    labels = []
    values = []
    colors_list = []
    
    if total_digs == 0:
        # Show empty state
        labels = ['No Data']
        values = [1]
        colors_list = ['#E0E0E0']
    else:
        labels = ['Good', 'Poor']
        values = [good_digs, poor_digs]
        colors_list = [OUTCOME_COLORS.get('good', '#8BC34A'), OUTCOME_COLORS.get('error', '#FF6B6B')]
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.6,
        marker=dict(colors=colors_list, line=dict(color='white', width=2)),
        textinfo='percent' if total_digs > 0 else 'none',
        textfont=dict(size=13, color='#050d76', family='Inter, sans-serif'),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>' if total_digs > 0 else '<b>No dig data</b><extra></extra>'
    )])
    
    # Add annotation for empty state
    annotations = []
    if total_digs == 0:
        annotations.append(dict(
            text='No Data',
            x=0.5, y=0.5,
            font=dict(size=12, color='#999999', family='Inter, sans-serif'),
            showarrow=False
        ))
    
    fig.update_layout(
        title=dict(text="Dig Rate", font=dict(size=14, color='#050d76', family='Inter, sans-serif')),
        height=220,
        showlegend=total_digs > 0,
        legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5, font=dict(size=10)),
        margin=dict(l=10, r=10, t=50, b=50),
        font=dict(family='Inter, sans-serif', size=10, color='#050d76'),
        paper_bgcolor='white',
        plot_bgcolor='white',
        annotations=annotations
    )
    fig = apply_beautiful_theme(fig, "Dig Rate")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"mini_dig_{player_name}")


def _display_core_performance_metrics(analyzer: MatchAnalyzer, player_name: str, player_data: Dict[str, Any],
                                     position: Optional[str], is_setter: bool, loader=None, df: pd.DataFrame = None) -> None:
    """Display core performance metrics grouped by skill area (matching Team Overview structure).
    
    Args:
        analyzer: MatchAnalyzer instance
        player_name: Player's name
        player_data: Player's statistics dictionary
        position: Player's position
        is_setter: Whether player is a setter
        loader: Optional loader instance
        df: Match data DataFrame
    """
    if df is None:
        df = analyzer.match_data
    player_df = get_player_df(df, player_name)
    
    # Initialize KPI Calculator for all calculations
    kpi_calc = KPICalculator(analyzer=analyzer, loader=loader)
    
    # Calculate position-specific metrics
    metrics = _calculate_player_kpis(analyzer, player_name, player_data, position, is_setter, loader)
    
    # Display metrics based on position - improved grouping
    if is_setter or position == 'S':
        # Setter: 5 core metrics in specific order
        # 1. Setting Quality, 2. Serve In-Rate, 3. Dig Percentage, 4. Attack Kill %, 5. Block %
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            setting_quality = metrics.get('setting_quality', 0.0)
            good_sets = player_data.get('good_sets', 0)
            total_sets_count = player_data.get('total_sets', 0)
            _display_player_metric_card(
                "Setting Quality",
                setting_quality,
                {'min': 0.70, 'max': 0.90, 'optimal': 0.80},
                "Good Sets / Total Sets",
                "setting_quality",
                numerator=good_sets,
                denominator=total_sets_count,
                min_threshold=0  # Always show for setters, even with small sample size
            )
        
        with col2:
            # Serve In-Rate - use centralized KPICalculator
            serve_result = kpi_calc.calculate_player_serve_in_rate(player_name, return_totals=True)
            serve_in_rate = serve_result['value']
            service_in_count = serve_result['numerator']
            service_attempts_count = serve_result['denominator']
            _display_player_metric_card(
                "Serve In-Rate",
                serve_in_rate,
                KPI_TARGETS['serve_in_rate'],
                "(Aces + Good Serves) / Total Serve Attempts",
                "serve_in_rate",
                numerator=service_in_count,
                denominator=service_attempts_count,
                min_threshold=0  # Always show for setters, even with small sample size
            )
        
        with col3:
            # Dig Rate - use centralized KPICalculator
            dig_result = kpi_calc.calculate_player_dig_rate(player_name, return_totals=True)
            dig_rate = dig_result['value']
            dig_good = dig_result['numerator']
            dig_total = dig_result['denominator']
            
            if dig_total > 0:
                _display_player_metric_card(
                    "Dig Rate",
                    dig_rate,
                    KPI_TARGETS['dig_rate'],
                    "Good and perfect digs / total",
                    "dig_rate",
                    numerator=dig_good,
                    denominator=dig_total,
                    min_threshold=0  # Always show for setters, even with small sample size
                )
            else:
                _display_player_metric_card(
                    "Dig Rate",
                    0.0,
                    KPI_TARGETS['dig_rate'],
                    "Good and perfect digs / total",
                    "dig_rate",
                    no_data_action="dig"
                )
        
        with col4:
            # Attack Kill % - use centralized KPICalculator
            attack_result = kpi_calc.calculate_player_attack_kill_pct(player_name, return_totals=True)
            attack_kill_pct_value = attack_result['value']
            attack_kills_count = attack_result['numerator']
            attack_attempts_count = attack_result['denominator']
            
            if attack_attempts_count > 0:
                _display_player_metric_card(
                    "Attack Kill %",
                    attack_kill_pct_value,
                    KPI_TARGETS['kill_percentage'],
                    "Attack kills / attempts",
                    "attack_kill_pct",
                    numerator=attack_kills_count,
                    denominator=attack_attempts_count,
                    min_threshold=0  # Always show for setters, even with small sample size
                )
            else:
                _display_player_metric_card(
                    "Attack Kill %",
                    0.0,
                    KPI_TARGETS['kill_percentage'],
                    "Attack kills / attempts",
                    "attack_kill_pct",
                    no_data_action="attack"
                )
        
        with col5:
            # Block % - use centralized KPICalculator
            block_result = kpi_calc.calculate_player_block_pct(player_name, return_totals=True)
            block_pct_value = block_result['value']
            block_total_count = block_result['numerator']
            block_attempts_count = block_result['denominator']
            
            if block_attempts_count > 0:
                _display_player_metric_card(
                    "Block %",
                    block_pct_value,
                    KPI_TARGETS['block_percentage'],
                    "(Block kills + Block no kill) / total attempts",
                    "block_pct",
                    numerator=block_total_count,
                    denominator=block_attempts_count,
                    min_threshold=0  # Always show for setters, even with small sample size
                )
            else:
                _display_player_metric_card(
                    "Block %",
                    0.0,
                    KPI_TARGETS['block_percentage'],
                    "(Block kills + Block no kill) / total attempts",
                    "block_pct",
                    no_data_action="block"
                )
    
    elif position and position.startswith('OH'):
        # Outside Hitter: Premium metric cards matching setter quality
        st.markdown("##### Performance Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Attack Kill % - use centralized KPICalculator
            attack_result = kpi_calc.calculate_player_attack_kill_pct(player_name, return_totals=True)
            attack_kill_pct_value = attack_result['value']
            attack_kills_count = attack_result['numerator']
            attack_attempts_count = attack_result['denominator']
            if attack_attempts_count > 0:
                _display_player_metric_card(
                    "Attack Kill %",
                    attack_kill_pct_value,
                    KPI_TARGETS['kill_percentage'],
                    "Attack Kills / Total Attack Attempts",
                    "attack_kill_pct",
                    numerator=attack_kills_count,
                    denominator=attack_attempts_count,
                    min_threshold=0  # Always show for outside hitters, even with small sample size
                )
            else:
                _display_player_metric_card(
                    "Attack Kill %",
                    0.0,
                    KPI_TARGETS['kill_percentage'],
                    "Attack Kills / Total Attack Attempts",
                    "attack_kill_pct",
                    no_data_action="attack"
                )
        
        with col2:
            # Reception Quality - use centralized KPICalculator
            reception_result = kpi_calc.calculate_player_reception_quality(player_name, return_totals=True)
            reception_quality_value = reception_result['value']
            reception_good_count = reception_result['numerator']
            reception_total_count = reception_result['denominator']
            if reception_total_count > 0:
                _display_player_metric_card(
                    "Reception Quality",
                    reception_quality_value,
                    KPI_TARGETS['reception_quality'],
                    "Good Receptions / Total Receptions",
                    "reception_quality",
                    numerator=reception_good_count,
                    denominator=reception_total_count,
                    min_threshold=0  # Always show for outside hitters, even with small sample size
                )
            else:
                _display_player_metric_card(
                    "Reception Quality",
                    0.0,
                    KPI_TARGETS['reception_quality'],
                    "Good Receptions / Total Receptions",
                    "reception_quality",
                    no_data_action="reception"
                )
        
        with col3:
            # Block Kill % - use centralized KPICalculator
            block_kill_result = kpi_calc.calculate_player_block_kill_pct(player_name, return_totals=True)
            block_kill_pct_value = block_kill_result['value']
            block_kills_count = block_kill_result['numerator']
            block_attempts_count = block_kill_result['denominator']
            if block_attempts_count > 0:
                _display_player_metric_card(
                    "Block Kill %",
                    block_kill_pct_value,
                    KPI_TARGETS['block_kill_percentage'],
                    "Block Kills / Total Block Attempts",
                    "block_kill_pct",
                    numerator=block_kills_count,
                    denominator=block_attempts_count,
                    min_threshold=0  # Always show for outside hitters, even with small sample size
                )
            else:
                _display_player_metric_card(
                    "Block Kill %",
                    0.0,
                    KPI_TARGETS['block_kill_percentage'],
                    "Block Kills / Total Block Attempts",
                    "block_kill_pct",
                    no_data_action="block"
                )
    
    elif position and position.startswith('MB'):
        # Middle Blocker: Premium metric cards matching outside hitter quality
        st.markdown("##### Performance Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Attack Kill % - use centralized KPICalculator
            attack_result = kpi_calc.calculate_player_attack_kill_pct(player_name, return_totals=True)
            attack_kill_pct_value = attack_result['value']
            attack_kills_count = attack_result['numerator']
            attack_attempts_count = attack_result['denominator']
            if attack_attempts_count > 0:
                _display_player_metric_card(
                    "Attack Kill %",
                    attack_kill_pct_value,
                    KPI_TARGETS['kill_percentage'],
                    "Attack Kills / Total Attack Attempts",
                    "attack_kill_pct",
                    numerator=attack_kills_count,
                    denominator=attack_attempts_count,
                    min_threshold=0  # Always show for middle blockers, even with small sample size
                )
            else:
                _display_player_metric_card(
                    "Attack Kill %",
                    0.0,
                    KPI_TARGETS['kill_percentage'],
                    "Attack Kills / Total Attack Attempts",
                    "attack_kill_pct",
                    no_data_action="attack"
                )
        
        with col2:
            # Block Kill % - use centralized KPICalculator
            block_kill_result = kpi_calc.calculate_player_block_kill_pct(player_name, return_totals=True)
            block_kill_pct_value = block_kill_result['value']
            block_kills_count = block_kill_result['numerator']
            block_attempts_count = block_kill_result['denominator']
            if block_attempts_count > 0:
                _display_player_metric_card(
                    "Block Kill %",
                    block_kill_pct_value,
                    KPI_TARGETS['block_kill_percentage'],
                    "Block Kills / Total Block Attempts",
                    "block_kill_pct",
                    numerator=block_kills_count,
                    denominator=block_attempts_count,
                    min_threshold=0  # Always show for middle blockers, even with small sample size
                )
            else:
                _display_player_metric_card(
                    "Block Kill %",
                    0.0,
                    KPI_TARGETS['block_kill_percentage'],
                    "Block Kills / Total Block Attempts",
                    "block_kill_pct",
                    no_data_action="block"
                )
        
        with col3:
            # Serve In-Rate - use centralized KPICalculator
            serve_result = kpi_calc.calculate_player_serve_in_rate(player_name, return_totals=True)
            serve_in_rate_value = serve_result['value']
            service_in_count = serve_result['numerator']
            service_attempts_count = serve_result['denominator']
            if service_attempts_count > 0:
                _display_player_metric_card(
                    "Serve In-Rate",
                    serve_in_rate_value,
                    KPI_TARGETS['serve_in_rate'],
                    "(Aces + Good Serves) / Total Serve Attempts",
                    "serve_in_rate",
                    numerator=service_in_count,
                    denominator=service_attempts_count,
                    min_threshold=0  # Always show for middle blockers, even with small sample size
                )
            else:
                _display_player_metric_card(
                    "Serve In-Rate",
                    0.0,
                    KPI_TARGETS['serve_in_rate'],
                    "(Aces + Good Serves) / Total Serve Attempts",
                    "serve_in_rate",
                    no_data_action="serve"
                )
    
    elif position == 'OPP':
        # Opposite: Premium metric cards matching outside hitter quality
        st.markdown("##### Performance Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Attack Kill % - use centralized KPICalculator
            attack_result = kpi_calc.calculate_player_attack_kill_pct(player_name, return_totals=True)
            attack_kill_pct_value = attack_result['value']
            attack_kills_count = attack_result['numerator']
            attack_attempts_count = attack_result['denominator']
            if attack_attempts_count > 0:
                _display_player_metric_card(
                    "Attack Kill %",
                    attack_kill_pct_value,
                    KPI_TARGETS['kill_percentage'],
                    "Attack Kills / Total Attack Attempts",
                    "attack_kill_pct",
                    numerator=attack_kills_count,
                    denominator=attack_attempts_count,
                    min_threshold=0  # Always show for opposite, even with small sample size
                )
            else:
                _display_player_metric_card(
                    "Attack Kill %",
                    0.0,
                    KPI_TARGETS['kill_percentage'],
                    "Attack Kills / Total Attack Attempts",
                    "attack_kill_pct",
                    no_data_action="attack"
                )
        
        with col2:
            # Block Kill % - use centralized KPICalculator
            block_kill_result = kpi_calc.calculate_player_block_kill_pct(player_name, return_totals=True)
            block_kill_pct_value = block_kill_result['value']
            block_kills_count = block_kill_result['numerator']
            block_attempts_count = block_kill_result['denominator']
            if block_attempts_count > 0:
                _display_player_metric_card(
                    "Block Kill %",
                    block_kill_pct_value,
                    KPI_TARGETS['block_kill_percentage'],
                    "Block Kills / Total Block Attempts",
                    "block_kill_pct",
                    numerator=block_kills_count,
                    denominator=block_attempts_count,
                    min_threshold=0  # Always show for opposite, even with small sample size
                )
            else:
                _display_player_metric_card(
                    "Block Kill %",
                    0.0,
                    KPI_TARGETS['block_kill_percentage'],
                    "Block Kills / Total Block Attempts",
                    "block_kill_pct",
                    no_data_action="block"
                )
        
        with col3:
            # Reception Quality - use centralized KPICalculator
            reception_result = kpi_calc.calculate_player_reception_quality(player_name, return_totals=True)
            reception_quality_value = reception_result['value']
            reception_good_count = reception_result['numerator']
            reception_total_count = reception_result['denominator']
            if reception_total_count > 0:
                _display_player_metric_card(
                    "Reception Quality",
                    reception_quality_value,
                    KPI_TARGETS['reception_quality'],
                    "Good Receptions / Total Receptions",
                    "reception_quality",
                    numerator=reception_good_count,
                    denominator=reception_total_count,
                    min_threshold=0  # Always show for opposite, even with small sample size
                )
            else:
                _display_player_metric_card(
                    "Reception Quality",
                    0.0,
                    KPI_TARGETS['reception_quality'],
                    "Good Receptions / Total Receptions",
                    "reception_quality",
                    no_data_action="reception"
                )
    
    elif position == 'L':
        # Libero: Premium metric cards matching setter quality
        st.markdown("##### Performance Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Reception Quality
            reception_quality = metrics.get('reception_quality', 0.0)
            receives = player_df[player_df['action'] == 'receive']
            reception_good = len(filter_good_receptions(receives))
            reception_total = len(receives)
            if reception_total > 0:
                _display_player_metric_card(
                    "Reception Quality",
                    reception_quality,
                    KPI_TARGETS['reception_quality'],
                    "Good Receptions / Total Receptions",
                    "reception_quality",
                    numerator=reception_good,
                    denominator=reception_total,
                    min_threshold=0  # Always show for liberos, even with small sample size
                )
            else:
                _display_player_metric_card(
                    "Reception Quality",
                    0.0,
                    KPI_TARGETS['reception_quality'],
                    "Good Receptions / Total Receptions",
                    "reception_quality",
                    no_data_action="reception"
                )
        
        with col2:
            # Dig Rate - use centralized KPICalculator
            dig_result = kpi_calc.calculate_player_dig_rate(player_name, return_totals=True)
            dig_rate = dig_result['value']
            dig_good = dig_result['numerator']
            dig_total = dig_result['denominator']
            if dig_total > 0:
                _display_player_metric_card(
                    "Dig Rate",
                    dig_rate,
                    KPI_TARGETS['dig_rate'],
                    "Good and perfect digs / total",
                    "dig_rate",
                    numerator=dig_good,
                    denominator=dig_total,
                    min_threshold=0  # Always show for liberos, even with small sample size
                )
            else:
                _display_player_metric_card(
                    "Dig Rate",
                    0.0,
                    KPI_TARGETS['dig_rate'],
                    "Good and perfect digs / total",
                    "dig_rate",
                    no_data_action="dig"
                )
        
        with col3:
            # Setting Quality - same as setters
            setting_quality = metrics.get('setting_quality', 0.0)
            good_sets = player_data.get('good_sets', 0)
            total_sets_count = player_data.get('total_sets', 0)
            _display_player_metric_card(
                "Setting Quality",
                setting_quality,
                {'min': 0.70, 'max': 0.90, 'optimal': 0.80},
                "Good Sets / Total Sets",
                "setting_quality",
                numerator=good_sets,
                denominator=total_sets_count,
                min_threshold=0  # Always show for liberos, even with small sample size
            )
    
    else:
        # Unknown/Other position: Premium metric cards matching setter quality
        st.markdown("##### Performance Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            attack_kill_pct = metrics.get('attack_kill_pct', 0.0)
            attack_kills = player_data.get('attack_kills', 0)
            attack_attempts = player_data.get('attack_attempts', 0)
            if attack_attempts > 0:
                _display_player_metric_card(
                    "Attack Kill %",
                    attack_kill_pct,
                    KPI_TARGETS['kill_percentage'],
                    "Attack Kills / Total Attack Attempts",
                    "attack_kill_pct",
                    numerator=attack_kills,
                    denominator=attack_attempts,
                    min_threshold=0  # Always show for unknown/other positions, even with small sample size
                )
            else:
                _display_player_metric_card(
                    "Attack Kill %",
                    0.0,
                    KPI_TARGETS['kill_percentage'],
                    "Attack Kills / Total Attack Attempts",
                    "attack_kill_pct",
                    no_data_action="attack"
                )
        
        with col2:
            # Reception Quality
            reception_quality = metrics.get('reception_quality', 0.0)
            receives = player_df[player_df['action'] == 'receive']
            reception_good = len(filter_good_receptions(receives))
            reception_total = len(receives)
            if reception_total > 0:
                _display_player_metric_card(
                    "Reception Quality",
                    reception_quality,
                    KPI_TARGETS['reception_quality'],
                    "Good Receptions / Total Receptions",
                    "reception_quality",
                    numerator=reception_good,
                    denominator=reception_total,
                    min_threshold=0  # Always show for unknown/other positions, even with small sample size
                )
            else:
                _display_player_metric_card(
                    "Reception Quality",
                    0.0,
                    KPI_TARGETS['reception_quality'],
                    "Good Receptions / Total Receptions",
                    "reception_quality",
                    no_data_action="reception"
                )
        
        with col3:
            # Block Kill %
            block_kill_pct = metrics.get('block_kill_pct', 0.0)
            block_kills = player_data.get('block_kills', 0)
            block_attempts = player_data.get('block_attempts', 0)
            if block_attempts > 0:
                _display_player_metric_card(
                    "Block Kill %",
                    block_kill_pct,
                    KPI_TARGETS['block_kill_percentage'],
                    "Block Kills / Total Block Attempts",
                    "block_kill_pct",
                    numerator=block_kills,
                    denominator=block_attempts,
                    min_threshold=0  # Always show for unknown/other positions, even with small sample size
                )
            else:
                st.info("No block data")


def _display_player_metric_card(label: str, value: float, targets: Dict[str, float],
                                formula: str, info_key: str, is_percentage: bool = True,
                                numerator: Optional[int] = None, denominator: Optional[int] = None,
                                lower_is_better: bool = False, min_threshold: Optional[int] = 5,
                                no_data_action: Optional[str] = None) -> None:
    """Display a premium player metric card matching Team Overview quality.
    
    Features:
    - Info button with collapsible formula
    - Sample size display (numerator/denominator)
    - Sample size warnings
    - Target comparison with delta
    - Hides metrics with insufficient data (n<5)
    
    Args:
        label: Metric label
        value: Metric value (0-1 for percentages, or raw number)
        targets: Target dictionary with 'min', 'max', 'optimal'
        formula: Formula description
        info_key: Unique key for info button
        is_percentage: Whether value is a percentage (0-1)
        numerator: Count of successes (for sample size display)
        denominator: Total count (for sample size display)
        lower_is_better: If True, lower values are better
    """
    from utils.formatters import format_percentage_with_sample_size, get_sample_size_warning, should_hide_metric
    
    # Handle "no data" case - show label and "No [action] registered" message
    if no_data_action is not None:
        # Create label with info button
        label_col, info_col = st.columns([11, 1])
        with label_col:
            st.markdown(f'**{label}**', unsafe_allow_html=True)
        with info_col:
            if st.button("ℹ️", key=f"info_btn_{info_key}", help="Click to show/hide formula", use_container_width=False, type="secondary"):
                st.session_state[f'show_formula_{info_key}'] = not st.session_state.get(f'show_formula_{info_key}', False)
        
        # Display formula if toggled on
        if st.session_state.get(f'show_formula_{info_key}', False):
            st.caption(f"📊 {formula}")
        
        # Display "No [action] registered" in the same large, bold style as the metric value
        st.markdown(f'<div style="font-size: 2rem; font-weight: bold; line-height: 1.1; margin-bottom: 0.05rem; color: #050d76;">No {no_data_action} registered</div>', unsafe_allow_html=True)
        return
    
    # Check if we should hide metric due to small sample size
    # Use custom threshold if provided, otherwise default to 5
    threshold = min_threshold if min_threshold is not None else 5
    if denominator is not None and should_hide_metric(denominator, min_threshold=threshold):
        st.markdown(f'**{label}**')
        st.metric(
            label="",
            value="N/A",
            delta=None,
            help=f"{formula}\n\n⚠️ Insufficient data (n={denominator})"
        )
        return
    
    # Handle case where targets might be empty or all zeros (like Setting Quality)
    has_valid_targets = not (targets.get('min', 0) == 0 and targets.get('max', 0) == 0 and targets.get('optimal', 0) == 0)
    
    if not has_valid_targets:
        # No target - display as raw number (not percentage)
        if value >= 0:
            display_value = f"{int(value)}" if value.is_integer() else f"{value:.1f}"
        else:
            display_value = "N/A"
        
        # Create label with info button
        label_col, info_col = st.columns([11, 1])
        with label_col:
            st.markdown(f'**{label}**', unsafe_allow_html=True)
        with info_col:
            if st.button("ℹ️", key=f"info_btn_{info_key}", help="Click to show/hide formula", use_container_width=False, type="secondary"):
                st.session_state[f'show_formula_{info_key}'] = not st.session_state.get(f'show_formula_{info_key}', False)
        
        if st.session_state.get(f'show_formula_{info_key}', False):
            st.caption(f"📊 {formula}")
        
        st.metric(
            label="",
            value=display_value,
            delta=None,
            help=formula
        )
        return
    
    # Has targets - display as percentage with comparison
    target_optimal = targets.get('optimal', (targets.get('min', 0) + targets.get('max', 0)) / 2)
    
    # Create label with info button for formula (using columns for layout)
    label_col, info_col = st.columns([11, 1])
    with label_col:
        st.markdown(f'**{label}**', unsafe_allow_html=True)
    with info_col:
        if st.button("ℹ️", key=f"info_btn_{info_key}", help="Click to show/hide formula", use_container_width=False, type="secondary"):
            st.session_state[f'show_formula_{info_key}'] = not st.session_state.get(f'show_formula_{info_key}', False)
    
    # Display formula if toggled on
    if st.session_state.get(f'show_formula_{info_key}', False):
        st.caption(f"📊 {formula}")
    
    # Calculate delta
    delta_vs_target = value - target_optimal
    if lower_is_better:
        delta_color = "normal" if value <= target_optimal else "inverse"
    else:
        delta_color = "normal" if value >= target_optimal else "inverse"
    
    delta_label = f"{delta_vs_target:+.1%} vs target ({target_optimal:.0%})" if is_percentage else f"{delta_vs_target:+.1f} vs target ({target_optimal:.1f})"
    
    # Format display value with sample size if available
    if numerator is not None and denominator is not None:
        display_value = format_percentage_with_sample_size(value, numerator, denominator) if is_percentage else f"{value:.1f} <small style='font-size: 0.7em; opacity: 0.8;'>(n={denominator})</small>"
        # Add warning for small sample sizes
        warning = get_sample_size_warning(denominator)
        help_text = f"{formula}\n\nSample size: {numerator}/{denominator}"
        if warning:
            help_text += f"\n\n{warning}"
    else:
        display_value = format_percentage(value) if is_percentage else f"{value:.1f}"
        help_text = formula
    
    if lower_is_better:
        help_text += "\n\n(Lower is better - more efficient scoring)"
    
    # Use markdown to display value with HTML formatting (for smaller parenthetical text)
    st.markdown(f'<div style="font-size: 2rem; font-weight: bold; line-height: 1.1; margin-bottom: 0.05rem;">{display_value}</div>', unsafe_allow_html=True)
    
    # Display delta using a custom container
    delta_html = f'<div style="font-size: 0.9rem; color: {"#28A745" if delta_color == "normal" and value >= target_optimal else "#DC3545" if delta_color == "inverse" else "#6C757D"}; margin-top: 0.05rem; margin-bottom: 0.05rem;">{delta_label}</div>'
    st.markdown(delta_html, unsafe_allow_html=True)


def _calculate_player_kpis(analyzer: MatchAnalyzer, player_name: str, player_data: Dict[str, Any],
                          position: Optional[str], is_setter: bool, loader=None) -> Dict[str, float]:
    """Calculate player KPIs using centralized KPICalculator.
    
    All calculations are now delegated to KPICalculator to ensure consistency.
    """
    kpi_calc = KPICalculator(analyzer=analyzer, loader=loader)
    
    # Use centralized calculation methods
    metrics = {
        'attack_kill_pct': kpi_calc.calculate_player_attack_kill_pct(player_name),
        'serve_in_rate': kpi_calc.calculate_player_serve_in_rate(player_name),
        'reception_quality': kpi_calc.calculate_player_reception_quality(player_name),
        'dig_rate': kpi_calc.calculate_player_dig_rate(player_name),
        'block_kill_pct': kpi_calc.calculate_player_block_kill_pct(player_name),
        'block_pct': kpi_calc.calculate_player_block_pct(player_name),
        'setting_quality': kpi_calc.calculate_player_setting_quality(player_name),
    }
    
    return metrics


def _display_detailed_stats(player_name: str, player_data: Dict[str, Any], is_setter: bool, 
                          position: Optional[str] = None, analyzer: MatchAnalyzer = None, loader=None) -> None:
    """Display detailed statistics table."""
    st.markdown(f"### 📊 Detailed Statistics for {player_name}")
    
    from utils.helpers import get_player_df
    df = analyzer.match_data if analyzer else None
    player_df = get_player_df(df, player_name) if df is not None else pd.DataFrame()
    
    # Libero: Focus on Reception, Dig, and Set
    if position == 'L':
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### 📥 Reception Statistics")
            receives = player_df[player_df['action'] == 'receive'] if not player_df.empty else pd.DataFrame()
            total_receives = len(receives)
            perfect_receives = len(receives[receives['outcome'] == 'perfect']) if len(receives) > 0 else 0
            good_receives = len(receives[receives['outcome'] == 'good']) if len(receives) > 0 else 0
            poor_receives = len(receives[receives['outcome'] == 'poor']) if len(receives) > 0 else 0
            error_receives = len(receives[receives['outcome'] == 'error']) if len(receives) > 0 else 0
            
            # Also try to get from aggregated data if available (receptions are often aggregated)
            if total_receives == 0 and loader and hasattr(loader, 'player_data_by_set'):
                total_rec_total = 0
                reception_good_from_loader = 0
                player_name_normalized = player_name.strip().lower()
                for set_num in loader.player_data_by_set.keys():
                    for loader_player_name in loader.player_data_by_set[set_num].keys():
                        if loader_player_name.strip().lower() == player_name_normalized:
                            stats = loader.player_data_by_set[set_num][loader_player_name].get('stats', {})
                            total_rec_total += float(stats.get('Reception_Total', 0) or 0)
                            reception_good_from_loader += float(stats.get('Reception_Good', 0) or 0)
                            break
                if total_rec_total > 0:
                    total_receives = int(total_rec_total)
                    # Approximate: if we have aggregated good, distribute between perfect and good
                    if reception_good_from_loader > 0:
                        good_receives = int(reception_good_from_loader * 0.7)  # Estimate 70% as "good"
                        perfect_receives = int(reception_good_from_loader * 0.3)  # Estimate 30% as "perfect"
            
            good_total = perfect_receives + good_receives
            reception_quality = (good_total / total_receives * 100) if total_receives > 0 else 0
            
            reception_data = {
                'Metric': ['Total', 'Perfect', 'Good', 'Poor', 'Errors', 'Quality %'],
                'Count': [
                    int(total_receives if total_receives > 0 else player_data.get('reception_total', 0)),
                    int(perfect_receives),
                    int(good_receives),
                    int(poor_receives),
                    int(error_receives),
                    f"{reception_quality:.1f}%"
                ],
                '%': [
                    "-",
                    f"{(perfect_receives / total_receives * 100):.1f}%" if total_receives > 0 else "N/A",
                    f"{(good_receives / total_receives * 100):.1f}%" if total_receives > 0 else "N/A",
                    f"{(poor_receives / total_receives * 100):.1f}%" if total_receives > 0 else "N/A",
                    f"{(error_receives / total_receives * 100):.1f}%" if total_receives > 0 else "N/A",
                    "-"  # Quality % already includes the percentage
                ]
            }
            reception_df = pd.DataFrame(reception_data)
            st.dataframe(reception_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### 🛡️ Dig Statistics")
            digs = player_df[player_df['action'] == 'dig'] if not player_df.empty else pd.DataFrame()
            total_digs = len(digs)
            perfect_digs = len(digs[digs['outcome'] == 'perfect']) if len(digs) > 0 else 0
            good_digs = len(digs[digs['outcome'] == 'good']) if len(digs) > 0 else 0
            poor_digs = len(digs[digs['outcome'] == 'poor']) if len(digs) > 0 else 0
            error_digs = len(digs[digs['outcome'] == 'error']) if len(digs) > 0 else 0
            
            # Also try to get from aggregated data if available (digs are often aggregated)
            if total_digs == 0 and loader and hasattr(loader, 'player_data_by_set'):
                total_dig_total = 0
                for set_num in loader.player_data_by_set.keys():
                    player_name_normalized = player_name.strip().lower()
                    for loader_player_name in loader.player_data_by_set[set_num].keys():
                        if loader_player_name.strip().lower() == player_name_normalized:
                            stats = loader.player_data_by_set[set_num][loader_player_name].get('stats', {})
                            total_dig_total += float(stats.get('Dig_Total', 0) or 0)
                            # If we have aggregated data, we can't get individual outcomes from it
                            # So we'll use 0 for individual outcomes but show the total
                if total_dig_total > 0:
                    total_digs = int(total_dig_total)
            
            good_total = perfect_digs + good_digs
            dig_rate = (good_total / total_digs * 100) if total_digs > 0 else 0
            
            dig_data = {
                'Metric': ['Total', 'Perfect', 'Good', 'Poor', 'Errors', 'Success %'],
                'Count': [
                    int(total_digs if total_digs > 0 else player_data.get('dig_total', 0)),
                    int(perfect_digs),
                    int(good_digs),
                    int(poor_digs),
                    int(error_digs),
                    f"{dig_rate:.1f}%"
                ],
                '%': [
                    "-",
                    f"{(perfect_digs / total_digs * 100):.1f}%" if total_digs > 0 else "N/A",
                    f"{(good_digs / total_digs * 100):.1f}%" if total_digs > 0 else "N/A",
                    f"{(poor_digs / total_digs * 100):.1f}%" if total_digs > 0 else "N/A",
                    f"{(error_digs / total_digs * 100):.1f}%" if total_digs > 0 else "N/A",
                    "-"  # Success % already includes the percentage
                ]
            }
            dig_df = pd.DataFrame(dig_data)
            st.dataframe(dig_df, use_container_width=True, hide_index=True)
        
        with col3:
            st.markdown("#### 🎯 Setting Statistics")
            sets = player_df[player_df['action'] == 'set'] if not player_df.empty else pd.DataFrame()
            total_sets = len(sets)
            exceptional_sets = len(sets[sets['outcome'] == 'exceptional']) if len(sets) > 0 else 0
            good_sets = len(sets[sets['outcome'] == 'good']) if len(sets) > 0 else 0
            poor_sets = len(sets[sets['outcome'] == 'poor']) if len(sets) > 0 else 0
            error_sets = len(sets[sets['outcome'] == 'error']) if len(sets) > 0 else 0
            
            # Also try to get from aggregated data if available
            if total_sets == 0 and loader and hasattr(loader, 'player_data_by_set'):
                total_set_total = 0
                player_name_normalized = player_name.strip().lower()
                for set_num in loader.player_data_by_set.keys():
                    for loader_player_name in loader.player_data_by_set[set_num].keys():
                        if loader_player_name.strip().lower() == player_name_normalized:
                            stats = loader.player_data_by_set[set_num][loader_player_name].get('stats', {})
                            total_set_total += float(stats.get('Set_Total', 0) or 0)
                if total_set_total > 0:
                    total_sets = int(total_set_total)
            
            good_total = exceptional_sets + good_sets
            setting_quality = (good_total / total_sets * 100) if total_sets > 0 else 0
            
            setting_data = {
                'Metric': ['Total', 'Exceptional', 'Good', 'Poor', 'Errors', 'Quality %'],
                'Count': [
                    int(total_sets if total_sets > 0 else player_data.get('total_sets', 0)),
                    int(exceptional_sets),
                    int(good_sets),
                    int(poor_sets),
                    int(error_sets),
                    f"{setting_quality:.1f}%"
                ],
                '%': [
                    "-",
                    f"{(exceptional_sets / total_sets * 100):.1f}%" if total_sets > 0 else "N/A",
                    f"{(good_sets / total_sets * 100):.1f}%" if total_sets > 0 else "N/A",
                    f"{(poor_sets / total_sets * 100):.1f}%" if total_sets > 0 else "N/A",
                    f"{(error_sets / total_sets * 100):.1f}%" if total_sets > 0 else "N/A",
                    "-"  # Quality % already includes the percentage
                ]
            }
            setting_df = pd.DataFrame(setting_data)
            st.dataframe(setting_df, use_container_width=True, hide_index=True)
    
    elif is_setter:
        # Setter: All outcomes in order: Setting, Serve, Dig, Attack, Block
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown("#### 🎯 Setting Statistics")
            sets = player_df[player_df['action'] == 'set'] if not player_df.empty else pd.DataFrame()
            total_sets = len(sets)
            exceptional_sets = len(sets[sets['outcome'] == 'exceptional']) if len(sets) > 0 else 0
            good_sets = len(sets[sets['outcome'] == 'good']) if len(sets) > 0 else 0
            poor_sets = len(sets[sets['outcome'] == 'poor']) if len(sets) > 0 else 0
            error_sets = len(sets[sets['outcome'] == 'error']) if len(sets) > 0 else 0
            
            total_sets_final = int(total_sets if total_sets > 0 else player_data.get('total_sets', 0))
            setting_data = {
                'Outcome': ['Total', 'Exceptional', 'Good', 'Poor', 'Error'],
                'Count': [
                    total_sets_final,
                    int(exceptional_sets),
                    int(good_sets),
                    int(poor_sets),
                    int(error_sets)
                ],
                '%': [
                    "-",
                    f"{(exceptional_sets / total_sets_final * 100):.1f}%" if total_sets_final > 0 else "N/A",
                    f"{(good_sets / total_sets_final * 100):.1f}%" if total_sets_final > 0 else "N/A",
                    f"{(poor_sets / total_sets_final * 100):.1f}%" if total_sets_final > 0 else "N/A",
                    f"{(error_sets / total_sets_final * 100):.1f}%" if total_sets_final > 0 else "N/A"
                ]
            }
            setting_df = pd.DataFrame(setting_data)
            st.dataframe(setting_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### 🎾 Service Statistics")
            serves = player_df[player_df['action'] == 'serve'] if not player_df.empty else pd.DataFrame()
            total_serves = len(serves)
            service_aces = len(serves[serves['outcome'] == 'ace']) if len(serves) > 0 else 0
            service_good = len(serves[serves['outcome'] == 'good']) if len(serves) > 0 else 0
            service_errors = len(serves[serves['outcome'] == 'error']) if len(serves) > 0 else 0
            
            total_serves_final = int(total_serves if total_serves > 0 else player_data.get('service_attempts', 0))
            service_aces_final = int(service_aces if service_aces > 0 else player_data.get('service_aces', 0))
            service_errors_final = int(service_errors if service_errors > 0 else player_data.get('service_errors', 0))
            service_data = {
                'Outcome': ['Total', 'Ace', 'Good', 'Error'],
                'Count': [
                    total_serves_final,
                    service_aces_final,
                    int(service_good),
                    service_errors_final
                ],
                '%': [
                    "-",
                    f"{(service_aces_final / total_serves_final * 100):.1f}%" if total_serves_final > 0 else "N/A",
                    f"{(service_good / total_serves_final * 100):.1f}%" if total_serves_final > 0 else "N/A",
                    f"{(service_errors_final / total_serves_final * 100):.1f}%" if total_serves_final > 0 else "N/A"
                ]
            }
            service_df = pd.DataFrame(service_data)
            st.dataframe(service_df, use_container_width=True, hide_index=True)
        
        with col3:
            st.markdown("#### 🛡️ Dig Statistics")
            digs = player_df[player_df['action'] == 'dig'] if not player_df.empty else pd.DataFrame()
            total_digs = len(digs)
            perfect_digs = len(digs[digs['outcome'] == 'perfect']) if len(digs) > 0 else 0
            good_digs = len(digs[digs['outcome'] == 'good']) if len(digs) > 0 else 0
            poor_digs = len(digs[digs['outcome'] == 'poor']) if len(digs) > 0 else 0
            error_digs = len(digs[digs['outcome'] == 'error']) if len(digs) > 0 else 0
            
            # Also try to get from aggregated data if available
            if total_digs == 0 and loader and hasattr(loader, 'player_data_by_set'):
                total_dig_total = 0
                player_name_normalized = player_name.strip().lower()
                for set_num in loader.player_data_by_set.keys():
                    for loader_player_name in loader.player_data_by_set[set_num].keys():
                        if loader_player_name.strip().lower() == player_name_normalized:
                            stats = loader.player_data_by_set[set_num][loader_player_name].get('stats', {})
                            total_dig_total += float(stats.get('Dig_Total', 0) or 0)
                            break
                if total_dig_total > 0:
                    total_digs = int(total_dig_total)
            
            total_digs_final = int(total_digs if total_digs > 0 else player_data.get('dig_total', 0))
            dig_data = {
                'Outcome': ['Total', 'Perfect', 'Good', 'Poor', 'Error'],
                'Count': [
                    total_digs_final,
                    int(perfect_digs),
                    int(good_digs),
                    int(poor_digs),
                    int(error_digs)
                ],
                '%': [
                    "-",
                    f"{(perfect_digs / total_digs_final * 100):.1f}%" if total_digs_final > 0 else "N/A",
                    f"{(good_digs / total_digs_final * 100):.1f}%" if total_digs_final > 0 else "N/A",
                    f"{(poor_digs / total_digs_final * 100):.1f}%" if total_digs_final > 0 else "N/A",
                    f"{(error_digs / total_digs_final * 100):.1f}%" if total_digs_final > 0 else "N/A"
                ]
            }
            dig_df = pd.DataFrame(dig_data)
            st.dataframe(dig_df, use_container_width=True, hide_index=True)
        
        with col4:
            st.markdown("#### 🏐 Attack Statistics")
            attacks = player_df[player_df['action'] == 'attack'] if not player_df.empty else pd.DataFrame()
            total_attacks = len(attacks)
            attack_kills = len(attacks[attacks['outcome'] == 'kill']) if len(attacks) > 0 else 0
            attack_defended = len(attacks[attacks['outcome'] == 'defended']) if len(attacks) > 0 else 0
            attack_blocked = len(attacks[attacks['outcome'] == 'blocked']) if len(attacks) > 0 else 0
            attack_out = len(attacks[attacks['outcome'] == 'out']) if len(attacks) > 0 else 0
            attack_net = len(attacks[attacks['outcome'] == 'net']) if len(attacks) > 0 else 0
            
            total_attacks_final = int(total_attacks if total_attacks > 0 else player_data.get('attack_attempts', 0))
            attack_kills_final = int(attack_kills if attack_kills > 0 else player_data.get('attack_kills', 0))
            attack_data = {
                'Outcome': ['Total', 'Kill', 'Defended', 'Blocked', 'Out', 'Net'],
                'Count': [
                    total_attacks_final,
                    attack_kills_final,
                    int(attack_defended),
                    int(attack_blocked),
                    int(attack_out),
                    int(attack_net)
                ],
                '%': [
                    "-",
                    f"{(attack_kills_final / total_attacks_final * 100):.1f}%" if total_attacks_final > 0 else "N/A",
                    f"{(attack_defended / total_attacks_final * 100):.1f}%" if total_attacks_final > 0 else "N/A",
                    f"{(attack_blocked / total_attacks_final * 100):.1f}%" if total_attacks_final > 0 else "N/A",
                    f"{(attack_out / total_attacks_final * 100):.1f}%" if total_attacks_final > 0 else "N/A",
                    f"{(attack_net / total_attacks_final * 100):.1f}%" if total_attacks_final > 0 else "N/A"
                ]
            }
            attack_df = pd.DataFrame(attack_data)
            st.dataframe(attack_df, use_container_width=True, hide_index=True)
        
        with col5:
            st.markdown("#### 🧱 Block Statistics")
            blocks = player_df[player_df['action'] == 'block'] if not player_df.empty else pd.DataFrame()
            total_blocks = len(blocks)
            block_kills = len(blocks[blocks['outcome'] == 'kill']) if len(blocks) > 0 else 0
            block_no_kill = len(blocks[blocks['outcome'] == 'block_no_kill']) if len(blocks) > 0 else 0
            block_touch = len(blocks[blocks['outcome'] == 'touch']) if len(blocks) > 0 else 0
            block_no_touch = len(blocks[blocks['outcome'] == 'no_touch']) if len(blocks) > 0 else 0
            block_errors = len(blocks[blocks['outcome'] == 'error']) if len(blocks) > 0 else 0
            
            total_blocks_final = int(total_blocks if total_blocks > 0 else player_data.get('block_attempts', 0))
            block_kills_final = int(block_kills if block_kills > 0 else player_data.get('block_kills', 0))
            block_errors_final = int(block_errors if block_errors > 0 else player_data.get('block_errors', 0))
            block_data = {
                'Outcome': ['Total', 'Kill', 'Block No Kill', 'Touch', 'No Touch', 'Error'],
                'Count': [
                    total_blocks_final,
                    block_kills_final,
                    int(block_no_kill),
                    int(block_touch),
                    int(block_no_touch),
                    block_errors_final
                ],
                '%': [
                    "-",
                    f"{(block_kills_final / total_blocks_final * 100):.1f}%" if total_blocks_final > 0 else "N/A",
                    f"{(block_no_kill / total_blocks_final * 100):.1f}%" if total_blocks_final > 0 else "N/A",
                    f"{(block_touch / total_blocks_final * 100):.1f}%" if total_blocks_final > 0 else "N/A",
                    f"{(block_no_touch / total_blocks_final * 100):.1f}%" if total_blocks_final > 0 else "N/A",
                    f"{(block_errors_final / total_blocks_final * 100):.1f}%" if total_blocks_final > 0 else "N/A"
                ]
            }
            block_df = pd.DataFrame(block_data)
            st.dataframe(block_df, use_container_width=True, hide_index=True)
    else:
        # Other positions (OH, MB, OPP): Show Attack, Service, Block, Reception, Dig
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.markdown("#### 🏐 Attack Statistics")
            attacks = player_df[player_df['action'] == 'attack'] if not player_df.empty else pd.DataFrame()
            total_attacks = len(attacks)
            attack_kills = len(attacks[attacks['outcome'] == 'kill']) if len(attacks) > 0 else 0
            attack_defended = len(attacks[attacks['outcome'] == 'defended']) if len(attacks) > 0 else 0
            attack_blocked = len(attacks[attacks['outcome'] == 'blocked']) if len(attacks) > 0 else 0
            attack_out = len(attacks[attacks['outcome'] == 'out']) if len(attacks) > 0 else 0
            attack_net = len(attacks[attacks['outcome'] == 'net']) if len(attacks) > 0 else 0
            
            total_attacks_final = int(total_attacks if total_attacks > 0 else player_data.get('attack_attempts', 0))
            attack_kills_final = int(attack_kills if attack_kills > 0 else player_data.get('attack_kills', 0))
            attack_data = {
                'Outcome': ['Total', 'Kill', 'Defended', 'Blocked', 'Out', 'Net'],
                'Count': [
                    total_attacks_final,
                    attack_kills_final,
                    int(attack_defended),
                    int(attack_blocked),
                    int(attack_out),
                    int(attack_net)
                ],
                '%': [
                    "-",
                    f"{(attack_kills_final / total_attacks_final * 100):.1f}%" if total_attacks_final > 0 else "N/A",
                    f"{(attack_defended / total_attacks_final * 100):.1f}%" if total_attacks_final > 0 else "N/A",
                    f"{(attack_blocked / total_attacks_final * 100):.1f}%" if total_attacks_final > 0 else "N/A",
                    f"{(attack_out / total_attacks_final * 100):.1f}%" if total_attacks_final > 0 else "N/A",
                    f"{(attack_net / total_attacks_final * 100):.1f}%" if total_attacks_final > 0 else "N/A"
                ]
            }
            attack_df = pd.DataFrame(attack_data)
            st.dataframe(attack_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### 🎾 Service Statistics")
            serves = player_df[player_df['action'] == 'serve'] if not player_df.empty else pd.DataFrame()
            total_serves = len(serves)
            service_aces = len(serves[serves['outcome'] == 'ace']) if len(serves) > 0 else 0
            service_good = len(serves[serves['outcome'] == 'good']) if len(serves) > 0 else 0
            service_errors = len(serves[serves['outcome'] == 'error']) if len(serves) > 0 else 0
            
            total_serves_final = int(total_serves if total_serves > 0 else player_data.get('service_attempts', 0))
            service_aces_final = int(service_aces if service_aces > 0 else player_data.get('service_aces', 0))
            service_errors_final = int(service_errors if service_errors > 0 else player_data.get('service_errors', 0))
            service_data = {
                'Outcome': ['Total', 'Ace', 'Good', 'Error'],
                'Count': [
                    total_serves_final,
                    service_aces_final,
                    int(service_good),
                    service_errors_final
                ],
                '%': [
                    "-",
                    f"{(service_aces_final / total_serves_final * 100):.1f}%" if total_serves_final > 0 else "N/A",
                    f"{(service_good / total_serves_final * 100):.1f}%" if total_serves_final > 0 else "N/A",
                    f"{(service_errors_final / total_serves_final * 100):.1f}%" if total_serves_final > 0 else "N/A"
                ]
            }
            service_df = pd.DataFrame(service_data)
            st.dataframe(service_df, use_container_width=True, hide_index=True)
        
        with col3:
            st.markdown("#### 🧱 Block Statistics")
            blocks = player_df[player_df['action'] == 'block'] if not player_df.empty else pd.DataFrame()
            total_blocks = len(blocks)
            block_kills = len(blocks[blocks['outcome'] == 'kill']) if len(blocks) > 0 else 0
            block_no_kill = len(blocks[blocks['outcome'] == 'block_no_kill']) if len(blocks) > 0 else 0
            block_touch = len(blocks[blocks['outcome'] == 'touch']) if len(blocks) > 0 else 0
            block_no_touch = len(blocks[blocks['outcome'] == 'no_touch']) if len(blocks) > 0 else 0
            block_errors = len(blocks[blocks['outcome'] == 'error']) if len(blocks) > 0 else 0
            
            total_blocks_final = int(total_blocks if total_blocks > 0 else player_data.get('block_attempts', 0))
            block_kills_final = int(block_kills if block_kills > 0 else player_data.get('block_kills', 0))
            block_errors_final = int(block_errors if block_errors > 0 else player_data.get('block_errors', 0))
            block_data = {
                'Outcome': ['Total', 'Kill', 'Block No Kill', 'Touch', 'No Touch', 'Error'],
                'Count': [
                    total_blocks_final,
                    block_kills_final,
                    int(block_no_kill),
                    int(block_touch),
                    int(block_no_touch),
                    block_errors_final
                ],
                '%': [
                    "-",
                    f"{(block_kills_final / total_blocks_final * 100):.1f}%" if total_blocks_final > 0 else "N/A",
                    f"{(block_no_kill / total_blocks_final * 100):.1f}%" if total_blocks_final > 0 else "N/A",
                    f"{(block_touch / total_blocks_final * 100):.1f}%" if total_blocks_final > 0 else "N/A",
                    f"{(block_no_touch / total_blocks_final * 100):.1f}%" if total_blocks_final > 0 else "N/A",
                    f"{(block_errors_final / total_blocks_final * 100):.1f}%" if total_blocks_final > 0 else "N/A"
                ]
            }
            block_df = pd.DataFrame(block_data)
            st.dataframe(block_df, use_container_width=True, hide_index=True)
        
        with col4:
            st.markdown("#### 📥 Reception Statistics")
            receives = player_df[player_df['action'] == 'receive'] if not player_df.empty else pd.DataFrame()
            total_receives = len(receives)
            perfect_receives = len(receives[receives['outcome'] == 'perfect']) if len(receives) > 0 else 0
            good_receives = len(receives[receives['outcome'] == 'good']) if len(receives) > 0 else 0
            poor_receives = len(receives[receives['outcome'] == 'poor']) if len(receives) > 0 else 0
            error_receives = len(receives[receives['outcome'] == 'error']) if len(receives) > 0 else 0
            
            reception_data = {
                'Outcome': ['Total', 'Perfect', 'Good', 'Poor', 'Error'],
                'Count': [
                    int(total_receives),
                    int(perfect_receives),
                    int(good_receives),
                    int(poor_receives),
                    int(error_receives)
                ],
                '%': [
                    "-",
                    f"{(perfect_receives / total_receives * 100):.1f}%" if total_receives > 0 else "N/A",
                    f"{(good_receives / total_receives * 100):.1f}%" if total_receives > 0 else "N/A",
                    f"{(poor_receives / total_receives * 100):.1f}%" if total_receives > 0 else "N/A",
                    f"{(error_receives / total_receives * 100):.1f}%" if total_receives > 0 else "N/A"
                ]
            }
            reception_df = pd.DataFrame(reception_data)
            st.dataframe(reception_df, use_container_width=True, hide_index=True)
        
        with col5:
            st.markdown("#### 🛡️ Dig Statistics")
            digs = player_df[player_df['action'] == 'dig'] if not player_df.empty else pd.DataFrame()
            total_digs = len(digs)
            perfect_digs = len(digs[digs['outcome'] == 'perfect']) if len(digs) > 0 else 0
            good_digs = len(digs[digs['outcome'] == 'good']) if len(digs) > 0 else 0
            poor_digs = len(digs[digs['outcome'] == 'poor']) if len(digs) > 0 else 0
            error_digs = len(digs[digs['outcome'] == 'error']) if len(digs) > 0 else 0
            
            total_digs_final = int(total_digs if total_digs > 0 else player_data.get('dig_total', 0))
            dig_data = {
                'Outcome': ['Total', 'Perfect', 'Good', 'Poor', 'Error'],
                'Count': [
                    total_digs_final,
                    int(perfect_digs),
                    int(good_digs),
                    int(poor_digs),
                    int(error_digs)
                ],
                '%': [
                    "-",
                    f"{(perfect_digs / total_digs_final * 100):.1f}%" if total_digs_final > 0 else "N/A",
                    f"{(good_digs / total_digs_final * 100):.1f}%" if total_digs_final > 0 else "N/A",
                    f"{(poor_digs / total_digs_final * 100):.1f}%" if total_digs_final > 0 else "N/A",
                    f"{(error_digs / total_digs_final * 100):.1f}%" if total_digs_final > 0 else "N/A"
                ]
            }
            dig_df = pd.DataFrame(dig_data)
            st.dataframe(dig_df, use_container_width=True, hide_index=True)


def _display_player_insights(analyzer: MatchAnalyzer, player_name: str, player_data: Dict[str, Any],
                             position: Optional[str], is_setter: bool, loader=None) -> None:
    """HIGH PRIORITY 4: Display player-specific insights and recommendations."""
    from ui.insights import generate_player_insights
    import performance_tracker as pt
    
    st.markdown("### 💡 Player-Specific Insights & Recommendations")
    
    # Calculate player KPIs
    kpis = _calculate_player_kpis(analyzer, player_name, player_data, position, is_setter, loader)
    
    # Calculate team average KPIs for comparison
    team_avg_kpis = {}
    if loader:
        try:
            team_kpis = pt.compute_team_kpis_from_loader(loader)
            team_avg_kpis = {
                'attack_kill_pct': team_kpis.get('attack_kill_pct', 0),
                'serve_in_rate': team_kpis.get('serve_in_rate', 0),
                'reception_quality': team_kpis.get('reception_quality', 0),
                'block_kill_pct': team_kpis.get('block_kill_pct', 0),
                'dig_rate': team_kpis.get('dig_rate', 0),
                'setting_quality': 0.75  # Default target
            }
        except (KeyError, TypeError, ZeroDivisionError):
            pass
    
    # Generate insights
    insights = generate_player_insights(player_name, player_data, position, kpis, team_avg_kpis)
    
    # Display strengths
    if insights['strengths']:
        st.markdown("#### ✅ Strengths")
        for strength in insights['strengths']:
            metric_name = strength.get('metric_display', strength['metric'].replace('_', ' ').title())
            player_val = strength['value']
            team_avg = strength.get('team_avg', 0)
            diff_pct = strength.get('diff_pct', 0)
            
            if team_avg > 0:
                st.success(f"**{metric_name}**: {player_val:.1%} (Team avg: {team_avg:.1%}, +{diff_pct:.1f}%)")
            else:
                st.success(f"**{metric_name}**: {player_val:.1%}")
    
    # Display weaknesses
    if insights['weaknesses']:
        st.markdown("#### ⚠️ Areas for Improvement")
        for weakness in insights['weaknesses']:
            metric_name = weakness.get('metric_display', weakness['metric'].replace('_', ' ').title())
            player_val = weakness['value']
            team_avg = weakness.get('team_avg', 0)
            target = weakness.get('target', 0)
            diff_pct = weakness.get('diff_pct', 0)
            
            comparison_text = ""
            if team_avg > 0:
                comparison_text = f" (Team avg: {team_avg:.1%}, -{diff_pct:.1f}%)"
            elif target > 0:
                comparison_text = f" (Target: {target:.0%})"
            
            st.warning(f"**{metric_name}**: {player_val:.1%}{comparison_text}")
    
    # Display recommendations with specific targets
    if insights['recommendations']:
        st.markdown("#### 🎯 Recommendations")
        # Sort by priority (high first)
        sorted_recs = sorted(insights['recommendations'], key=lambda x: 0 if x['priority'] == 'high' else 1)
        
        for rec in sorted_recs:
            priority_icon = "🔴" if rec['priority'] == 'high' else "🟡"
            current = rec.get('current_value', 'N/A')
            target = rec.get('specific_target', 'N/A')
            
            st.markdown(f"{priority_icon} **{rec['action']}**")
            if current != 'N/A' and target != 'N/A':
                st.markdown(f"   Current: {current} → Target: {target}")
            st.markdown(f"   {rec['details']}")
            st.markdown("")
    
    # Display training focus areas
    if insights.get('training_focus'):
        st.markdown("#### 🏋️ Training Focus Areas")
        for focus in insights['training_focus']:
            st.info(f"**{focus['area']}**: {focus['focus']}")

