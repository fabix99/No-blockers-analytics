"""
Player Analysis UI Module
"""
from typing import Dict, Any, Optional
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from match_analyzer import MatchAnalyzer
from config import SETTER_THRESHOLD, CHART_COLORS, KPI_TARGETS
from ui.components import get_position_full_name, get_position_emoji, load_player_image_cached
from utils.helpers import get_player_position
from utils.formatters import format_percentage, get_performance_color
from streamlit_dashboard import display_player_image_and_info
from charts.player_charts import create_player_charts
from charts.utils import apply_beautiful_theme, plotly_config


def display_player_analysis(analyzer: MatchAnalyzer, loader=None) -> None:
    """Display detailed player analysis.
    
    Args:
        analyzer: MatchAnalyzer instance with loaded match data
        loader: Optional ExcelMatchLoader instance for team data
    """
    st.markdown('<h2 class="main-header">👥 Player Analysis</h2>', unsafe_allow_html=True)
    
    # Calculate player metrics
    player_stats = analyzer.calculate_player_metrics()
    
    if player_stats is None:
        st.error("No player statistics available")
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
    
    # Display overview metrics (position-specific KPIs)
    _display_player_overview(analyzer, player_name, player_data, position, is_setter, loader)
    
    # Setter-specific analysis
    if is_setter:
        _display_setter_analysis(player_name, player_df, df)
    
    # Display detailed stats
    _display_detailed_stats(player_name, player_data, is_setter)
    
    # Display charts
    create_player_charts(analyzer, player_name, loader)


def _display_player_overview(analyzer: MatchAnalyzer, player_name: str, player_data: Dict[str, Any], 
                            position: Optional[str], is_setter: bool, loader=None) -> None:
    """Display player overview metrics with position-specific KPIs aligned with Team Overview."""
    st.markdown("### 📊 Player Performance Overview")
    
    df = analyzer.match_data
    player_df = df[df['player'] == player_name]
    
    # Calculate position-specific metrics
    metrics = _calculate_player_kpis(analyzer, player_name, player_data, position, is_setter, loader)
    
    # Display metrics based on position
    if is_setter or position == 'S':
        # Setter: Setting Quality, Serve In-Rate, Attack Kill % (if they attack)
        col1, col2, col3, col4 = st.columns(4)
        
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
                st.metric("Attack Kill %", "N/A", help="No attack attempts")
        
        with col4:
            st.metric("Total Sets", player_data.get('total_sets', 0))
    
    elif position and position.startswith('OH'):
        # Outside Hitter: Attack Kill %, Serve In-Rate, Reception Quality, Dig Rate
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            attack_kill_pct = metrics.get('attack_kill_pct', 0.0)
            _display_player_metric_card(
                "Attack Kill %",
                attack_kill_pct,
                KPI_TARGETS['kill_percentage'],
                "Attack Kills / Total Attack Attempts",
                f"{player_data['attack_kills']}/{player_data.get('attack_attempts', 0)}"
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
            reception_quality = metrics.get('reception_quality', 0.0)
            receives = player_df[player_df['action'] == 'receive']
            rec_good_count = len(receives[receives['outcome'] == 'good'])
            rec_total_count = len(receives)
            rec_display = f"{rec_good_count}/{rec_total_count}" if rec_total_count > 0 else "N/A"
            _display_player_metric_card(
                "Reception Quality",
                reception_quality,
                KPI_TARGETS['reception_quality'],
                "Good Receptions / Total Reception Attempts",
                rec_display
            )
        
        with col4:
            dig_rate = metrics.get('dig_rate', 0.0)
            _display_player_metric_card(
                "Dig Rate",
                dig_rate,
                KPI_TARGETS['dig_rate'],
                "Good Digs / Total Dig Attempts",
                f"{player_data.get('dig_good', 0)}/{player_data.get('dig_total', 0)}" if player_data.get('dig_total', 0) > 0 else "N/A"
            )
    
    elif position and position.startswith('MB'):
        # Middle Blocker: Attack Kill %, Block Kill %, Serve In-Rate
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            attack_kill_pct = metrics.get('attack_kill_pct', 0.0)
            _display_player_metric_card(
                "Attack Kill %",
                attack_kill_pct,
                KPI_TARGETS['kill_percentage'],
                "Attack Kills / Total Attack Attempts",
                f"{player_data['attack_kills']}/{player_data.get('attack_attempts', 0)}"
            )
        
        with col2:
            block_kill_pct = metrics.get('block_kill_pct', 0.0)
            _display_player_metric_card(
                "Block Kill %",
                block_kill_pct,
                KPI_TARGETS['block_kill_percentage'],
                "Block Kills / Total Block Attempts",
                f"{player_data['block_kills']}/{player_data.get('block_attempts', 0)}"
            )
        
        with col3:
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
        
        with col4:
            st.metric("Total Actions", player_data['total_actions'])
    
    elif position == 'OPP':
        # Opposite: Attack Kill %, Block Kill %, Serve In-Rate
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            attack_kill_pct = metrics.get('attack_kill_pct', 0.0)
            _display_player_metric_card(
                "Attack Kill %",
                attack_kill_pct,
                KPI_TARGETS['kill_percentage'],
                "Attack Kills / Total Attack Attempts",
                f"{player_data['attack_kills']}/{player_data.get('attack_attempts', 0)}"
            )
        
        with col2:
            block_kill_pct = metrics.get('block_kill_pct', 0.0)
            _display_player_metric_card(
                "Block Kill %",
                block_kill_pct,
                KPI_TARGETS['block_kill_percentage'],
                "Block Kills / Total Block Attempts",
                f"{player_data['block_kills']}/{player_data.get('block_attempts', 0)}"
            )
        
        with col3:
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
        
        with col4:
            st.metric("Total Actions", player_data['total_actions'])
    
    elif position == 'L':
        # Libero: Reception Quality, Dig Rate, Serve In-Rate (if they serve)
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            reception_quality = metrics.get('reception_quality', 0.0)
            receives = player_df[player_df['action'] == 'receive']
            rec_good_count = len(receives[receives['outcome'] == 'good'])
            rec_total_count = len(receives)
            rec_display = f"{rec_good_count}/{rec_total_count}" if rec_total_count > 0 else "N/A"
            _display_player_metric_card(
                "Reception Quality",
                reception_quality,
                KPI_TARGETS['reception_quality'],
                "Good Receptions / Total Reception Attempts",
                rec_display
            )
        
        with col2:
            dig_rate = metrics.get('dig_rate', 0.0)
            _display_player_metric_card(
                "Dig Rate",
                dig_rate,
                KPI_TARGETS['dig_rate'],
                "Good Digs / Total Dig Attempts",
                f"{player_data.get('dig_good', 0)}/{player_data.get('dig_total', 0)}" if player_data.get('dig_total', 0) > 0 else "N/A"
            )
        
        with col3:
            if player_data.get('service_attempts', 0) > 0:
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
            else:
                st.metric("Serve In-Rate", "N/A", help="No service attempts")
        
        with col4:
            st.metric("Total Actions", player_data['total_actions'])
    
    else:
        # Unknown/Other position: Show general metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            attack_kill_pct = metrics.get('attack_kill_pct', 0.0)
            if attack_kill_pct > 0:
                _display_player_metric_card(
                    "Attack Kill %",
                    attack_kill_pct,
                    KPI_TARGETS['kill_percentage'],
                    "Attack Kills / Total Attack Attempts",
                    f"{player_data['attack_kills']}/{player_data.get('attack_attempts', 0)}"
                )
            else:
                st.metric("Attack Kill %", "N/A")
        
        with col2:
            serve_in_rate = metrics.get('serve_in_rate', 0.0)
            if serve_in_rate > 0:
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
            else:
                st.metric("Serve In-Rate", "N/A")
        
        with col3:
            st.metric("Total Actions", player_data['total_actions'])
        
        with col4:
            st.metric("Block Efficiency", f"{player_data['block_efficiency']:.1%}")


def _display_player_metric_card(label: str, value: float, targets: Dict[str, float],
                                formula: str, delta_label: str) -> None:
    """Display a player metric card with target comparison (consistent with Team Overview style)."""
    # Handle case where targets might be empty or all zeros (like Setting Quality)
    if targets.get('min', 0) == 0 and targets.get('max', 0) == 0 and targets.get('optimal', 0) == 0:
        # No target, just display the value
        target_optimal = 0.0
        color = "🟢"  # Default green
        delta_vs_target = 0.0
        delta_color = "normal"
        delta_text = ""
    else:
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
        delta=delta_text if delta_text else None,
        delta_color=delta_color if delta_text else None,
        help=f"{formula}\n\n{delta_label}"
    )


def _calculate_player_kpis(analyzer: MatchAnalyzer, player_name: str, player_data: Dict[str, Any],
                          position: Optional[str], is_setter: bool, loader=None) -> Dict[str, float]:
    """Calculate player KPIs consistent with Team Overview metrics."""
    df = analyzer.match_data
    player_df = df[df['player'] == player_name]
    
    metrics = {}
    
    # Attack Kill % (consistent with Team Overview)
    attack_attempts = player_data.get('attack_attempts', 0)
    if attack_attempts > 0:
        metrics['attack_kill_pct'] = player_data['attack_kills'] / attack_attempts
    else:
        metrics['attack_kill_pct'] = 0.0
    
    # Serve In-Rate (consistent with Team Overview)
    service_attempts = player_data.get('service_attempts', 0)
    if service_attempts > 0:
        service_aces = player_data.get('service_aces', 0)
        # Calculate good serves from action rows (not stored in player_data)
        serves = player_df[player_df['action'] == 'serve']
        service_good = len(serves[serves['outcome'] == 'good'])
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
                good_receives = len(receives[receives['outcome'] == 'good'])
                metrics['reception_quality'] = good_receives / total_receives
            else:
                metrics['reception_quality'] = 0.0
    else:
        # Fallback to action rows
        receives = player_df[player_df['action'] == 'receive']
        total_receives = len(receives)
        if total_receives > 0:
            good_receives = len(receives[receives['outcome'] == 'good'])
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
    block_attempts = player_data.get('block_attempts', 0)
    if block_attempts > 0:
        metrics['block_kill_pct'] = player_data['block_kills'] / block_attempts
    else:
        metrics['block_kill_pct'] = 0.0
    
    # Setting Quality (for setters)
    if is_setter:
        total_sets = player_data.get('total_sets', 0)
        if total_sets > 0:
            good_sets = player_data.get('good_sets', 0)
            metrics['setting_quality'] = good_sets / total_sets
        else:
            metrics['setting_quality'] = 0.0
    
    return metrics


def _display_setter_analysis(player_name: str, player_df: pd.DataFrame, df: pd.DataFrame) -> None:
    """Display setter-specific analysis."""
    st.markdown(f"### 🎯 Setter-Specific Analysis for {player_name}")
    
    sets = player_df[player_df['action'] == 'set']
    if len(sets) > 0:
        col1, col2 = st.columns(2)
        
        with col1:
            _display_setting_distribution(sets)
        
        with col2:
            _display_setting_by_set(sets, df)


def _display_setting_distribution(sets: pd.DataFrame) -> None:
    """Display setting quality distribution."""
    st.markdown("#### 📊 Setting Distribution")
    
    good_sets = len(sets[sets['outcome'] == 'good'])
    error_sets = len(sets[sets['outcome'] == 'error'])
    total = len(sets)
    
    import plotly.express as px
    import plotly.graph_objects as go
    # Use softer pastel colors for distribution
    fig = px.pie(
        values=[good_sets, error_sets],
        names=['Good Sets', 'Error Sets'],
        title="Setting Quality Distribution",
        color_discrete_sequence=['#90EE90', '#FFB6C1']  # Soft green, soft pink
    )
    fig.update_traces(
        textposition='inside',
        textinfo='percent+label',
        marker=dict(line=dict(color='rgba(255,255,255,0.8)', width=1.5))
    )
    fig = apply_beautiful_theme(fig, "Setting Quality Distribution")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config)


def _display_setting_by_set(sets: pd.DataFrame, df: pd.DataFrame) -> None:
    """Display setting performance by set."""
    st.markdown("#### 📈 Setting Performance by Set")
    
    sets_by_set = sets.groupby('set_number').size()
    
    # Single soft color for trend/performance chart
    fig = go.Figure(data=go.Bar(
        x=sets_by_set.index,
        y=sets_by_set.values,
        marker_color='#B8D4E6',  # Soft blue - single color
        text=sets_by_set.values,
        textposition='outside',
        textfont=dict(size=11, color='#040C7B')
    ))
    fig.update_layout(
        title="Sets per Set (Workload)",
        xaxis_title="Set Number",
        yaxis_title="Number of Sets",
        showlegend=False,
        xaxis=dict(dtick=1, tickfont=dict(color='#040C7B')),
        yaxis=dict(tickfont=dict(color='#040C7B'))
    )
    fig.update_traces(
        marker=dict(line=dict(color='rgba(255,255,255,0.8)', width=1)),
        hovertemplate='<b>Set %{x}</b><br>Sets: %{y}<extra></extra>'
    )
    fig = apply_beautiful_theme(fig, "Sets per Set (Workload)")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config)


def _display_detailed_stats(player_name: str, player_data: Dict[str, Any], is_setter: bool) -> None:
    """Display detailed statistics table."""
    st.markdown(f"### 📊 Detailed Statistics for {player_name}")
    
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
                    int(player_data.get('attack_attempts', 0)),
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
                    int(player_data.get('service_attempts', 0)),
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
                    int(player_data.get('block_attempts', 0)),
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
                    int(player_data.get('attack_attempts', 0)),
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
                    int(player_data.get('service_attempts', 0)),
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
                    int(player_data.get('block_attempts', 0)),
                    int(player_data['block_kills']),
                    int(player_data['block_errors']),
                    f"{player_data['block_efficiency']:.1%}"
                ]
            }
            block_df = pd.DataFrame(block_data)
            st.dataframe(block_df, use_container_width=True, hide_index=True)

