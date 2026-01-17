"""
Player Analysis UI Module
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
from utils.helpers import get_player_position, filter_good_receptions, filter_good_digs, filter_block_touches
from utils.formatters import format_percentage, get_performance_color
from charts.player_charts import create_player_charts
from charts.utils import apply_beautiful_theme, plotly_config


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
    players = list(player_stats.keys())
    
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
    
    Args:
        analyzer: MatchAnalyzer instance
        player_name: Name of the player
        player_stats: Dictionary of all player statistics
        loader: Optional ExcelMatchLoader instance for team data
    """
    player_data = player_stats[player_name]
    df = analyzer.match_data
    player_df = df[df['player'] == player_name]
    position = get_player_position(df, player_name)
    
    # Display player image and info in sidebar
    display_player_image_and_info(player_name, position, image_size=78, use_sidebar=True)
    
    # Check if setter
    total_sets = player_data.get('total_sets', 0)
    is_setter = total_sets > 0 and total_sets >= player_data['total_actions'] * SETTER_THRESHOLD
    
    # Player header with key stats
    _display_player_header(player_name, position, player_data)
    
    # Use tabs for organized content
    tab_overview, tab_stats, tab_charts, tab_insights = st.tabs([
        "📊 Overview", 
        "📈 Detailed Stats", 
        "📉 Performance Charts",
        "💡 Insights & Training"
    ])
    
    with tab_overview:
        try:
            _display_player_summary_card(analyzer, player_name, player_data, position, loader)
        except Exception as e:
            st.warning(f"⚠️ Could not display player summary: {str(e)}")
    
    with tab_stats:
        try:
            _display_detailed_stats(player_name, player_data, is_setter, position, analyzer)
        except Exception as e:
            st.warning(f"⚠️ Could not display detailed stats: {str(e)}")
    
    with tab_charts:
        try:
            create_player_charts(analyzer, player_name, loader)
        except Exception as e:
            st.warning(f"⚠️ Could not display player charts: {str(e)}")
    
    with tab_insights:
        try:
            _display_player_insights(analyzer, player_name, player_data, position, is_setter, loader)
        except Exception as e:
            st.info(f"ℹ️ Player insights not available: {str(e)}")


def _display_player_header(player_name: str, position: Optional[str], player_data: Dict[str, Any]) -> None:
    """Display a compact player header with key stats.
    
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
    
    # Compact header with player name and key stats
    st.markdown(f"""
    <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
                padding: 16px 20px; border-radius: 10px; margin-bottom: 16px;
                border-left: 5px solid #040C7B;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
            <div>
                <span style="font-size: 24px; font-weight: 700; color: #040C7B;">
                    {position_emoji} {player_name}
                </span>
                <span style="font-size: 16px; color: #666; margin-left: 12px;">
                    {position_full}
                </span>
            </div>
            <div style="display: flex; gap: 24px; margin-top: 8px;">
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #040C7B;">{total_points}</div>
                    <div style="font-size: 12px; color: #666;">Total Points</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #28a745;">{attack_kills}</div>
                    <div style="font-size: 12px; color: #666;">Kills</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #6C63FF;">{service_aces}</div>
                    <div style="font-size: 12px; color: #666;">Aces</div>
                </div>
                <div style="text-align: center;">
                    <div style="font-size: 24px; font-weight: 700; color: #FFD700;">{block_kills}</div>
                    <div style="font-size: 12px; color: #666;">Blocks</div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def _display_player_summary_card(analyzer: MatchAnalyzer, player_name: str, player_data: Dict[str, Any],
                                position: Optional[str], loader=None) -> None:
    """Display player summary card with match participation, highlights, and performance overview."""
    df = analyzer.match_data
    player_df = df[df['player'] == player_name]
    
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
    
    # Player Performance Overview - integrated into summary with better grouping
    st.markdown("#### 📊 Player Performance Overview")
    _display_player_overview_metrics(analyzer, player_name, player_data, position, is_setter, loader)


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


def _display_player_overview_metrics(analyzer: MatchAnalyzer, player_name: str, player_data: Dict[str, Any], 
                            position: Optional[str], is_setter: bool, loader=None) -> None:
    """Display player overview metrics with position-specific KPIs (part of summary card)."""
    df = analyzer.match_data
    player_df = df[df['player'] == player_name]
    
    # Calculate position-specific metrics
    metrics = _calculate_player_kpis(analyzer, player_name, player_data, position, is_setter, loader)
    
    # Display metrics based on position - improved grouping
    if is_setter or position == 'S':
        # Setter: Group percentage metrics together, then count metrics
        st.markdown("##### Performance Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            setting_quality = metrics.get('setting_quality', 0.0)
            _display_player_metric_card(
                "Setting Quality",
                setting_quality,
                {'min': 0.70, 'max': 0.90, 'optimal': 0.80},
                "Good Sets / Total Sets",
                f"{player_data.get('good_sets', 0)}/{player_data.get('total_sets', 0)}"
            )
        
        with col2:
            serve_in_rate = metrics.get('serve_in_rate', 0.0)
            service_aces_count = player_data.get('service_aces', 0)
            service_good_count = len(player_df[(player_df['action'] == 'serve') & (player_df['outcome'] == 'good')])
            service_attempts_count = player_data.get('service_attempts', 0)
            _display_player_metric_card(
                "Serve In-Rate",
                serve_in_rate,
                KPI_TARGETS['serve_in_rate'],
                "(Aces + Good Serves) / Total Serve Attempts",
                f"{service_aces_count + service_good_count}/{service_attempts_count}"
            )
        
        with col3:
            if metrics.get('attack_kill_pct', 0.0) > 0:
                attack_kill_pct = metrics['attack_kill_pct']
                _display_player_metric_card(
                    "Attack Kill %",
                    attack_kill_pct,
                    KPI_TARGETS['kill_percentage'],
                    "Attack Kills / Total Attack Attempts",
                    f"{player_data['attack_kills']}/{player_data.get('attack_attempts', 0)}"
                )
            else:
                st.info("No attack data")
        
        # Count metrics in separate row
        st.markdown("##### Activity Metrics")
        col1_count, col2_count, col3_count = st.columns(3)
        
        with col1_count:
            st.metric("Total Sets", f"{player_data.get('total_sets', 0)}")
        
        with col2_count:
            st.metric("Total Actions", f"{player_data.get('total_actions', 0)}")
        
        with col3_count:
            # Empty or additional metric
            pass
    
    elif position and position.startswith('OH'):
        # Outside Hitter: Premium metric cards matching setter quality
        st.markdown("##### Performance Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Attack Kill %
            attack_kill_pct = metrics.get('attack_kill_pct', 0.0)
            attack_kills = player_data.get('attack_kills', 0)
            attack_attempts = player_data.get('attack_attempts', 0)
            if attack_attempts > 0:
                _display_player_metric_card(
                    "Attack Kill %",
                    attack_kill_pct,
                    KPI_TARGETS['kill_percentage'],
                    "Attack Kills / Total Attack Attempts",
                    f"{attack_kills}/{attack_attempts}"
                )
            else:
                st.info("No attack data")
        
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
                    f"{reception_good}/{reception_total}"
                )
            else:
                st.info("No reception data")
        
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
                    f"{block_kills}/{block_attempts}"
                )
            else:
                st.info("No block data")
    
    elif position and position.startswith('MB'):
        # Middle Blocker: Premium metric cards matching setter quality
        st.markdown("##### Performance Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Attack Kill %
            attack_kill_pct = metrics.get('attack_kill_pct', 0.0)
            attack_kills = player_data.get('attack_kills', 0)
            attack_attempts = player_data.get('attack_attempts', 0)
            if attack_attempts > 0:
                _display_player_metric_card(
                    "Attack Kill %",
                    attack_kill_pct,
                    KPI_TARGETS['kill_percentage'],
                    "Attack Kills / Total Attack Attempts",
                    f"{attack_kills}/{attack_attempts}"
                )
            else:
                st.info("No attack data")
        
        with col2:
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
                    f"{block_kills}/{block_attempts}"
                )
            else:
                st.info("No block data")
        
        with col3:
            # Serve In-Rate
            serve_in_rate = metrics.get('serve_in_rate', 0.0)
            service_aces_count = player_data.get('service_aces', 0)
            service_good_count = len(player_df[(player_df['action'] == 'serve') & (player_df['outcome'] == 'good')])
            service_attempts_count = player_data.get('service_attempts', 0)
            if service_attempts_count > 0:
                _display_player_metric_card(
                    "Serve In-Rate",
                    serve_in_rate,
                    KPI_TARGETS['serve_in_rate'],
                    "(Aces + Good Serves) / Total Serve Attempts",
                    f"{service_aces_count + service_good_count}/{service_attempts_count}"
                )
            else:
                st.info("No serve data")
    
    elif position == 'OPP':
        # Opposite: Premium metric cards matching setter quality
        st.markdown("##### Performance Metrics")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Attack Kill %
            attack_kill_pct = metrics.get('attack_kill_pct', 0.0)
            attack_kills = player_data.get('attack_kills', 0)
            attack_attempts = player_data.get('attack_attempts', 0)
            if attack_attempts > 0:
                _display_player_metric_card(
                    "Attack Kill %",
                    attack_kill_pct,
                    KPI_TARGETS['kill_percentage'],
                    "Attack Kills / Total Attack Attempts",
                    f"{attack_kills}/{attack_attempts}"
                )
            else:
                st.info("No attack data")
        
        with col2:
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
                    f"{block_kills}/{block_attempts}"
                )
            else:
                st.info("No block data")
        
        with col3:
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
                    f"{reception_good}/{reception_total}"
                )
            else:
                st.info("No reception data")
    
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
                    f"{reception_good}/{reception_total}"
                )
            else:
                st.info("No reception data")
        
        with col2:
            # Dig Rate
            dig_rate = metrics.get('dig_rate', 0.0)
            dig_total = player_data.get('dig_total', 0)
            dig_good = player_data.get('dig_good', 0)
            if dig_total > 0:
                _display_player_metric_card(
                    "Dig Rate",
                    dig_rate,
                    KPI_TARGETS['dig_rate'],
                    "Good Digs / Total Digs",
                    f"{dig_good}/{dig_total}"
                )
            else:
                st.info("No dig data")
        
        with col3:
            # Serve In-Rate
            serve_in_rate = metrics.get('serve_in_rate', 0.0)
            service_aces_count = player_data.get('service_aces', 0)
            service_good_count = len(player_df[(player_df['action'] == 'serve') & (player_df['outcome'] == 'good')])
            service_attempts_count = player_data.get('service_attempts', 0)
            if service_attempts_count > 0:
                _display_player_metric_card(
                    "Serve In-Rate",
                    serve_in_rate,
                    KPI_TARGETS['serve_in_rate'],
                    "(Aces + Good Serves) / Total Serve Attempts",
                    f"{service_aces_count + service_good_count}/{service_attempts_count}"
                )
            else:
                st.info("No serve data")
    
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
                    f"{attack_kills}/{attack_attempts}"
                )
            else:
                st.info("No attack data")
        
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
                    f"{reception_good}/{reception_total}"
                )
            else:
                st.info("No reception data")
        
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
                    f"{block_kills}/{block_attempts}"
                )
            else:
                st.info("No block data")


def _display_player_metric_card(label: str, value: float, targets: Dict[str, float],
                                formula: str, delta_label: str) -> None:
    """Display a player metric card with target comparison (consistent with Team Overview style)."""
    # Handle case where targets might be empty or all zeros (like Setting Quality)
    has_valid_targets = not (targets.get('min', 0) == 0 and targets.get('max', 0) == 0 and targets.get('optimal', 0) == 0)
    
    if not has_valid_targets:
        # No target - display as raw number (not percentage)
        # For count metrics, display as integer
        if value >= 0:
            display_value = f"{int(value)}" if value.is_integer() else f"{value:.1f}"
        else:
            display_value = "N/A"
        st.markdown(f'**{label}**', unsafe_allow_html=True)
        st.metric(
            label="",
            value=display_value,
            delta=None,
            help=f"{formula}\n\n{delta_label}"
        )
    else:
        # Has targets - display as percentage with comparison
        target_optimal = targets.get('optimal', (targets.get('min', 0) + targets.get('max', 0)) / 2)
        color = get_performance_color(value, targets['min'], targets['max'], target_optimal)
        # Calculate delta
        delta_vs_target = value - target_optimal
        delta_color = "normal" if value >= target_optimal else "inverse"
        delta_text = f"{delta_vs_target:+.1%} vs target ({target_optimal:.0%})"
        
        st.markdown(f'**{label} {color}**', unsafe_allow_html=True)
        st.metric(
            label="",
            value=format_percentage(value) if value >= 0 else "N/A",
            delta=delta_text,
            delta_color=delta_color,
            help=f"{formula}\n\n{delta_label}"
        )


def _calculate_player_kpis(analyzer: MatchAnalyzer, player_name: str, player_data: Dict[str, Any],
                          position: Optional[str], is_setter: bool, loader=None) -> Dict[str, float]:
    """Calculate player KPIs consistent with Team Overview metrics."""
    df = analyzer.match_data
    player_df = df[df['player'] == player_name]
    
    metrics = {}
    
    # Attack Kill % (consistent with Team Overview)
    # Try to get from loader aggregated stats first (more accurate), otherwise use player_data
    attack_attempts = 0
    attack_kills = 0
    if loader and hasattr(loader, 'player_data_by_set'):
        for set_num in loader.player_data_by_set.keys():
            if player_name in loader.player_data_by_set[set_num]:
                stats = loader.player_data_by_set[set_num][player_name].get('stats', {})
                attack_attempts += float(stats.get('Attack_Total', 0) or 0)
                attack_kills += float(stats.get('Attack_Kills', 0) or 0)
    
    if attack_attempts == 0:
        # Fallback: use player_data from MatchAnalyzer
        attack_attempts = player_data.get('attack_attempts', 0)
        attack_kills = player_data.get('attack_kills', 0)
    
    if attack_attempts > 0:
        metrics['attack_kill_pct'] = attack_kills / attack_attempts
    else:
        metrics['attack_kill_pct'] = 0.0
    
    # Serve In-Rate (consistent with Team Overview)
    # Try to get from loader aggregated stats first (more accurate), otherwise use player_data
    service_attempts = 0
    service_aces = 0
    service_good = 0
    if loader and hasattr(loader, 'player_data_by_set'):
        for set_num in loader.player_data_by_set.keys():
            if player_name in loader.player_data_by_set[set_num]:
                stats = loader.player_data_by_set[set_num][player_name].get('stats', {})
                service_attempts += float(stats.get('Service_Total', 0) or 0)
                service_aces += float(stats.get('Service_Aces', 0) or 0)
                service_good += float(stats.get('Service_Good', 0) or 0)
    
    if service_attempts == 0:
        # Fallback: use player_data from MatchAnalyzer
        service_attempts = player_data.get('service_attempts', 0)
        service_aces = player_data.get('service_aces', 0)
        # Calculate good serves from action rows
        serves = player_df[player_df['action'] == 'serve']
        service_good = len(serves[serves['outcome'] == 'good'])
    
    if service_attempts > 0:
        metrics['serve_in_rate'] = (service_aces + service_good) / service_attempts
    else:
        metrics['serve_in_rate'] = 0.0
    
    # Reception Quality (consistent with Team Overview)
    # Try to get from loader aggregated data first (more accurate)
    if loader and hasattr(loader, 'player_data_by_set'):
        total_rec_good = 0.0
        total_rec_total = 0.0
        for set_num in loader.player_data_by_set.keys():
            if player_name in loader.player_data_by_set[set_num]:
                stats = loader.player_data_by_set[set_num][player_name].get('stats', {})
                total_rec_good += float(stats.get('Reception_Good', 0) or 0)
                total_rec_total += float(stats.get('Reception_Total', 0) or 0)
        if total_rec_total > 0:
            metrics['reception_quality'] = total_rec_good / total_rec_total
        else:
            # Fallback to action rows
            receives = player_df[player_df['action'] == 'receive']
            total_receives = len(receives)
            if total_receives > 0:
                good_receives = len(filter_good_receptions(receives))
                metrics['reception_quality'] = good_receives / total_receives
            else:
                metrics['reception_quality'] = 0.0
    else:
        # Fallback to action rows
        receives = player_df[player_df['action'] == 'receive']
        total_receives = len(receives)
        if total_receives > 0:
            good_receives = len(filter_good_receptions(receives))
            metrics['reception_quality'] = good_receives / total_receives
        else:
            metrics['reception_quality'] = 0.0
    
    # Dig Rate (consistent with Team Overview)
    dig_total = player_data.get('dig_total', 0)
    if dig_total > 0:
        dig_good = player_data.get('dig_good', 0)
        metrics['dig_rate'] = dig_good / dig_total
    else:
        # Try to get from loader aggregated data
        if loader and hasattr(loader, 'player_data_by_set'):
            total_dig_good = 0.0
            total_dig_total = 0.0
            for set_num in loader.player_data_by_set.keys():
                if player_name in loader.player_data_by_set[set_num]:
                    stats = loader.player_data_by_set[set_num][player_name].get('stats', {})
                    total_dig_good += float(stats.get('Dig_Good', 0) or 0)
                    total_dig_total += float(stats.get('Dig_Total', 0) or 0)
            if total_dig_total > 0:
                metrics['dig_rate'] = total_dig_good / total_dig_total
            else:
                metrics['dig_rate'] = 0.0
        else:
            metrics['dig_rate'] = 0.0
    
    # Block Kill % (consistent with Team Overview)
    # Try to get from loader aggregated stats first (more accurate), otherwise use player_data
    block_attempts = 0
    block_kills = 0
    if loader and hasattr(loader, 'player_data_by_set'):
        for set_num in loader.player_data_by_set.keys():
            if player_name in loader.player_data_by_set[set_num]:
                stats = loader.player_data_by_set[set_num][player_name].get('stats', {})
                block_attempts += float(stats.get('Block_Total', 0) or 0)
                block_kills += float(stats.get('Block_Kills', 0) or 0)
    
    if block_attempts == 0:
        # Fallback: use player_data from MatchAnalyzer
        block_attempts = player_data.get('block_attempts', 0)
        block_kills = player_data.get('block_kills', 0)
    
    if block_attempts > 0:
        metrics['block_kill_pct'] = block_kills / block_attempts
    else:
        metrics['block_kill_pct'] = 0.0
    
    # Setting Quality (for setters and all players)
    # Check from action rows first (more accurate)
    sets = player_df[player_df['action'] == 'set']
    total_sets_count = len(sets)
    if total_sets_count > 0:
        # Good sets = exceptional + good (both count as good)
        good_sets_count = len(sets[sets['outcome'].isin(['exceptional', 'good'])])
        metrics['setting_quality'] = good_sets_count / total_sets_count
    else:
        # Fallback to player_data if available
        total_sets = player_data.get('total_sets', 0)
        if total_sets > 0:
            # Calculate from aggregated stats if available
            if loader and hasattr(loader, 'player_data_by_set'):
                total_exceptional = 0
                total_good = 0
                for set_num in loader.player_data_by_set.keys():
                    if player_name in loader.player_data_by_set[set_num]:
                        stats = loader.player_data_by_set[set_num][player_name].get('stats', {})
                        total_exceptional += float(stats.get('Sets_Exceptional', 0) or 0)
                        total_good += float(stats.get('Sets_Good', 0) or 0)
                good_sets = total_exceptional + total_good
                metrics['setting_quality'] = good_sets / total_sets if total_sets > 0 else 0.0
            else:
                good_sets = player_data.get('good_sets', 0)
                metrics['setting_quality'] = good_sets / total_sets
        else:
            metrics['setting_quality'] = 0.0
    
    return metrics


def _display_detailed_stats(player_name: str, player_data: Dict[str, Any], is_setter: bool, 
                          position: Optional[str] = None, analyzer: MatchAnalyzer = None) -> None:
    """Display detailed statistics table."""
    st.markdown(f"### 📊 Detailed Statistics for {player_name}")
    
    df = analyzer.match_data if analyzer else None
    player_df = df[df['player'] == player_name] if df is not None else pd.DataFrame()
    
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
            good_total = perfect_receives + good_receives
            reception_quality = (good_total / total_receives * 100) if total_receives > 0 else 0
            
            reception_data = {
                'Metric': ['Total', 'Perfect', 'Good', 'Poor', 'Errors', 'Quality %'],
                'Value': [
                    int(total_receives),
                    int(perfect_receives),
                    int(good_receives),
                    int(poor_receives),
                    int(error_receives),
                    f"{reception_quality:.1f}%"
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
            good_total = perfect_digs + good_digs
            dig_rate = (good_total / total_digs * 100) if total_digs > 0 else 0
            
            dig_data = {
                'Metric': ['Total', 'Perfect', 'Good', 'Poor', 'Errors', 'Success %'],
                'Value': [
                    int(total_digs),
                    int(perfect_digs),
                    int(good_digs),
                    int(poor_digs),
                    int(error_digs),
                    f"{dig_rate:.1f}%"
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
            good_total = exceptional_sets + good_sets
            setting_quality = (good_total / total_sets * 100) if total_sets > 0 else 0
            
            setting_data = {
                'Metric': ['Total', 'Exceptional', 'Good', 'Poor', 'Errors', 'Quality %'],
                'Value': [
                    int(total_sets),
                    int(exceptional_sets),
                    int(good_sets),
                    int(poor_sets),
                    int(error_sets),
                    f"{setting_quality:.1f}%"
                ]
            }
            setting_df = pd.DataFrame(setting_data)
            st.dataframe(setting_df, use_container_width=True, hide_index=True)
    
    elif is_setter:
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("#### 🎯 Setting Statistics")
            # Calculate setting stats from dataframe for accuracy (matches libero approach)
            sets = player_df[player_df['action'] == 'set'] if not player_df.empty else pd.DataFrame()
            total_sets_count = len(sets)
            exceptional_sets = len(sets[sets['outcome'] == 'exceptional']) if len(sets) > 0 else 0
            good_sets_count = len(sets[sets['outcome'] == 'good']) if len(sets) > 0 else 0
            poor_sets = len(sets[sets['outcome'] == 'poor']) if len(sets) > 0 else 0
            error_sets = len(sets[sets['outcome'] == 'error']) if len(sets) > 0 else 0
            good_total = exceptional_sets + good_sets_count
            setting_percentage = (good_total / total_sets_count) if total_sets_count > 0 else player_data.get('setting_percentage', 0)
            
            setting_data = {
                'Metric': ['Total Sets', 'Good Sets', 'Error Sets', 'Setting %'],
                'Value': [
                    int(total_sets_count if total_sets_count > 0 else player_data.get('total_sets', 0)),
                    int(good_total if total_sets_count > 0 else player_data.get('good_sets', 0)),
                    int(error_sets),
                    f"{setting_percentage:.1%}"
                ]
            }
            setting_df = pd.DataFrame(setting_data)
            st.dataframe(setting_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### 🏐 Attack Statistics")
            attack_data = {
                'Metric': ['Attempts', 'Kills', 'Errors', 'Efficiency'],
                'Value': [
                    int(player_data.get('attack_attempts', 0)),
                    int(player_data.get('attack_kills', 0)),
                    int(player_data.get('attack_errors', 0)),
                    f"{player_data.get('attack_efficiency', 0):.1%}"
                ]
            }
            attack_df = pd.DataFrame(attack_data)
            st.dataframe(attack_df, use_container_width=True, hide_index=True)
        
        with col3:
            st.markdown("#### 🎯 Service Statistics")
            service_data = {
                'Metric': ['Attempts', 'Aces', 'Errors', 'Efficiency'],
                'Value': [
                    int(player_data.get('service_attempts', 0)),
                    int(player_data.get('service_aces', 0)),
                    int(player_data.get('service_errors', 0)),
                    f"{player_data.get('service_efficiency', 0):.1%}"
                ]
            }
            service_df = pd.DataFrame(service_data)
            st.dataframe(service_df, use_container_width=True, hide_index=True)
        
        with col4:
            st.markdown("#### 🛡️ Block Statistics")
            block_data = {
                'Metric': ['Attempts', 'Kills', 'Errors', 'Efficiency'],
                'Value': [
                    int(player_data.get('block_attempts', 0)),
                    int(player_data.get('block_kills', 0)),
                    int(player_data.get('block_errors', 0)),
                    f"{player_data.get('block_efficiency', 0):.1%}"
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
                    int(player_data.get('attack_attempts', 0)),
                    int(player_data.get('attack_kills', 0)),
                    int(player_data.get('attack_errors', 0)),
                    f"{player_data.get('attack_efficiency', 0):.1%}"
                ]
            }
            attack_df = pd.DataFrame(attack_data)
            st.dataframe(attack_df, use_container_width=True, hide_index=True)
        
        with col2:
            st.markdown("#### 🎯 Service Statistics")
            service_data = {
                'Metric': ['Attempts', 'Aces', 'Errors', 'Efficiency'],
                'Value': [
                    int(player_data.get('service_attempts', 0)),
                    int(player_data.get('service_aces', 0)),
                    int(player_data.get('service_errors', 0)),
                    f"{player_data.get('service_efficiency', 0):.1%}"
                ]
            }
            service_df = pd.DataFrame(service_data)
            st.dataframe(service_df, use_container_width=True, hide_index=True)
        
        with col3:
            st.markdown("#### 🛡️ Block Statistics")
            block_data = {
                'Metric': ['Attempts', 'Kills', 'Errors', 'Efficiency'],
                'Value': [
                    int(player_data.get('block_attempts', 0)),
                    int(player_data.get('block_kills', 0)),
                    int(player_data.get('block_errors', 0)),
                    f"{player_data.get('block_efficiency', 0):.1%}"
                ]
            }
            block_df = pd.DataFrame(block_data)
            st.dataframe(block_df, use_container_width=True, hide_index=True)


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

