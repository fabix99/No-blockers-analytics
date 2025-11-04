"""
Team Overview UI Module

Displays team performance overview with KPIs, insights, and charts
"""
from typing import Optional, Dict, Any, List
import streamlit as st
from match_analyzer import MatchAnalyzer
import performance_tracker as pt
from config import KPI_TARGETS
from ui.components import display_match_banner
from utils.formatters import format_percentage, get_performance_delta_color, get_performance_color


def display_team_overview(analyzer: MatchAnalyzer, loader=None) -> None:
    """Display team performance overview with KPIs and insights.
    
    Args:
        analyzer: MatchAnalyzer instance with loaded match data
        loader: Optional ExcelMatchLoader instance for team data
    """
    # Display match banner if loader available
    display_match_banner(loader)
    
    st.markdown('<h2 class="main-header">🏆 Team Performance Overview</h2>', unsafe_allow_html=True)
    
    # Calculate team metrics
    team_stats = analyzer.calculate_team_metrics()
    
    if team_stats is None:
        st.error("No team statistics available")
        return
    
    # Prepare targets
    targets = KPI_TARGETS.copy()
    for key in targets:
        targets[key]['label'] = f"Target: {targets[key]['optimal']:.0%}+"
    
    # Get KPIs from loader if available
    kpis = _get_kpis(loader, analyzer, team_stats)
    
    # Display CSS styling
    _display_metric_styling()
    
    # Display KPI metrics
    _display_kpi_metrics(analyzer, team_stats, kpis, targets, loader)
    
    # Detailed Team Analysis section with charts
    st.markdown('<h2 class="main-header">📊 Detailed Team Analysis</h2>', unsafe_allow_html=True)
    from charts.team_charts import create_team_charts
    create_team_charts(analyzer, loader)
    
    # Display insights section (moved to bottom)
    _display_insights_section(analyzer, team_stats, targets, loader)


def _get_kpis(loader, analyzer: MatchAnalyzer, team_stats: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get KPIs from loader if available, otherwise return None."""
    if loader is not None and hasattr(loader, 'team_data') and loader.team_data:
        if hasattr(pt, 'compute_team_kpis_from_loader'):
            try:
                return pt.compute_team_kpis_from_loader(loader)
            except Exception:
                pass
    return None


def _display_metric_styling() -> None:
    """Display CSS styling for metrics."""
    st.markdown(
        """
        <style>
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
        div[data-testid="stMetricContainer"] {
            padding: 0.25rem 0.5rem !important;
        }
        div[data-testid="stMetricLabel"],
        div[data-testid="stMetricValue"],
        div[data-testid="stMetricDelta"] {
            padding: 0 !important;
        }
        div[data-testid="column"] {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            padding-top: 0.25rem !important;
            padding-bottom: 0.25rem !important;
            min-height: auto !important;
            height: auto !important;
        }
        div[data-testid="column"] > div {
            min-height: auto !important;
            height: auto !important;
        }
        .element-container {
            padding: 0 !important;
            min-height: auto !important;
            height: auto !important;
        }
        div[data-testid="stMarkdownContainer"],
        div[data-testid="stMetricContainer"] {
            min-height: auto !important;
            height: auto !important;
        }
        h4, h3 {
            font-size: 1.15rem !important;
        }
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
        div[data-testid="stMarkdownContainer"] {
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
            margin-top: 0 !important;
        }
        .element-container {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        div[data-testid="column"] > .element-container:has(div[data-testid="column"]) + .element-container {
            margin-top: 0.5rem !important;
        }
        div[data-testid="stMarkdownContainer"],
        div[data-testid="stMetricContainer"] {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
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


def _display_kpi_metrics(analyzer: MatchAnalyzer, team_stats: Dict[str, Any], 
                        kpis: Optional[Dict[str, Any]], targets: Dict[str, Any], loader=None) -> None:
    """Display KPI metrics in grid layout."""
    # Row 1: 4 metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        serving_rate = kpis['break_point_rate'] if kpis else team_stats.get('serve_point_percentage', 0.0)
        _display_metric_card(
            "Serving Point Rate",
            serving_rate,
            targets['break_point_rate'],
            "Points Won When Serving / Total Serving Rallies",
            "info_serving_point"
        )
    
    with col2:
        service_value = _calculate_serve_in_rate(analyzer, kpis)
        _display_metric_card(
            "Serve In-Rate",
            service_value,
            targets['serve_in_rate'],
            "(Aces + Good Serves) / Total Serve Attempts",
            "info_service"
        )
    
    with col3:
        attack_value = kpis['attack_kill_pct'] if kpis else team_stats.get('kill_percentage', 0.0)
        if attack_value is None:
            attack_value = _calculate_attack_kill_pct(analyzer)
        _display_metric_card(
            "Attack Kill %",
            attack_value,
            targets['kill_percentage'],
            "Attack Kills / Total Attack Attempts",
            "info_attack"
        )
    
    with col4:
        dig_rate = kpis['dig_rate'] if kpis else _calculate_dig_rate(analyzer, loader)
        _display_metric_card(
            "Dig Rate",
            dig_rate,
            targets['dig_rate'],
            "Good Digs / Total Dig Attempts",
            "info_dig"
        )
    
    # Row 2: 4 metrics
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        receiving_rate = kpis['side_out_efficiency'] if kpis else team_stats['side_out_percentage']
        _display_metric_card(
            "Receiving Point Rate",
            receiving_rate,
            targets['side_out_percentage'],
            "Points Won When Receiving / Total Receiving Rallies",
            "info_receiving_point"
        )
    
    with col6:
        reception_quality = kpis['reception_quality'] if kpis else _calculate_reception_quality(analyzer, loader)
        _display_metric_card(
            "Reception Quality",
            reception_quality,
            targets['reception_quality'],
            "Good Receptions / Total Reception Attempts",
            "info_reception"
        )
    
    with col7:
        block_kill_pct = kpis['block_kill_pct'] if kpis else _calculate_block_kill_pct(analyzer)
        _display_metric_card(
            "Block Kill %",
            block_kill_pct,
            targets['block_kill_percentage'],
            "Block Kills / Total Block Attempts",
            "info_block_kill"
        )
    
    with col8:
        avg_actions = kpis.get('avg_actions_per_point', 0.0) if kpis else _calculate_avg_actions(analyzer, loader)
        _display_metric_card(
            "Avg Actions/Point",
            avg_actions,
            {'min': 0.0, 'max': 0.0, 'optimal': 0.0},
            "Total Actions / Total Points",
            "info_avg_actions",
            is_percentage=False
        )


def _display_metric_card(label: str, value: float, targets: Dict[str, float],
                         formula: str, info_key: str, is_percentage: bool = True) -> None:
    """Display a single metric card with info button."""
    target_optimal = targets.get('optimal', (targets.get('min', 0) + targets.get('max', 0)) / 2)
    color = get_performance_color(value, targets['min'], targets['max'], target_optimal)
    
    # Create label with inline info icon
    label_col, icon_col, _ = st.columns([12, 1, 0.1], gap="small")
    with label_col:
        st.markdown(f'**{label} {color}**', unsafe_allow_html=True)
    with icon_col:
        if st.button("ℹ️", key=f"{info_key}_btn", help="Show definition", 
                    use_container_width=False, type="secondary"):
            st.session_state[f'show_{info_key}'] = not st.session_state.get(f'show_{info_key}', False)
    
    # Calculate delta
    delta_vs_target = value - target_optimal
    delta_color = "normal" if value >= target_optimal else "inverse"
    delta_label = f"{delta_vs_target:+.1%} vs target ({target_optimal:.0%})" if is_percentage else f"{delta_vs_target:+.1f} vs target ({target_optimal:.1f})"
    
    display_value = format_percentage(value) if is_percentage else f"{value:.1f}"
    
    st.metric(
        label="",
        value=display_value,
        delta=delta_label,
        delta_color=delta_color,
        help=formula
    )
    
    # Info popup
    if st.session_state.get(f'show_{info_key}', False):
        st.info(f"**{label}**\n\n**Formula:** {formula}\n\n**Current Calculation:** {display_value}")


def _calculate_serve_in_rate(analyzer: MatchAnalyzer, kpis: Optional[Dict[str, Any]]) -> float:
    """Calculate serve in rate."""
    if kpis:
        return kpis.get('serve_in_rate', 0.0)
    serves = analyzer.match_data[analyzer.match_data['action'] == 'serve']
    in_play = len(serves[serves['outcome'].isin(['ace', 'good'])])
    attempts = len(serves)
    return (in_play / attempts) if attempts > 0 else 0.0


def _calculate_attack_kill_pct(analyzer: MatchAnalyzer) -> float:
    """Calculate attack kill percentage."""
    attacks = analyzer.match_data[analyzer.match_data['action'] == 'attack']
    kills = len(attacks[attacks['outcome'] == 'kill'])
    total = len(attacks)
    return (kills / total) if total > 0 else 0.0


def _calculate_dig_rate(analyzer: MatchAnalyzer, loader=None) -> float:
    """Calculate dig rate from aggregated data (digs are not distributed as action rows)."""
    # Digs are not created as individual action rows in the dataframe
    # Must use aggregated data from loader if available
    if loader is not None and hasattr(loader, 'player_data_by_set'):
        total_dig_good = 0.0
        total_dig_total = 0.0
        for set_num in loader.player_data_by_set.keys():
            for player in loader.player_data_by_set[set_num].keys():
                stats = loader.player_data_by_set[set_num][player].get('stats', {})
                total_dig_good += float(stats.get('Dig_Good', 0) or 0)
                total_dig_total += float(stats.get('Dig_Total', 0) or 0)
        return (total_dig_good / total_dig_total) if total_dig_total > 0 else 0.0
    
    # Fallback: try action rows (but this will be 0 since digs aren't created)
    digs = analyzer.match_data[analyzer.match_data['action'] == 'dig']
    good = len(digs[digs['outcome'] == 'good'])
    total = len(digs)
    return (good / total) if total > 0 else 0.0


def _calculate_reception_quality(analyzer: MatchAnalyzer, loader=None) -> float:
    """Calculate reception quality from aggregated data (more accurate)."""
    # Use aggregated data from loader if available (more accurate)
    if loader is not None and hasattr(loader, 'reception_data_by_rotation'):
        total_rec_good = 0.0
        total_rec_total = 0.0
        for set_num in loader.reception_data_by_rotation.keys():
            for rot_num in loader.reception_data_by_rotation[set_num].keys():
                rot_data = loader.reception_data_by_rotation[set_num][rot_num]
                total_rec_good += float(rot_data.get('good', 0) or 0)
                total_rec_total += float(rot_data.get('total', 0) or 0)
        return (total_rec_good / total_rec_total) if total_rec_total > 0 else 0.0
    
    # Fallback: count from action rows (less accurate due to distribution)
    receives = analyzer.match_data[analyzer.match_data['action'] == 'receive']
    good = len(receives[receives['outcome'] == 'good'])
    total = len(receives)
    return (good / total) if total > 0 else 0.0


def _calculate_block_kill_pct(analyzer: MatchAnalyzer) -> float:
    """Calculate block kill percentage."""
    blocks = analyzer.match_data[analyzer.match_data['action'] == 'block']
    kills = len(blocks[blocks['outcome'] == 'kill'])
    total = len(blocks)
    return (kills / total) if total > 0 else 0.0


def _calculate_avg_actions(analyzer: MatchAnalyzer, loader=None) -> float:
    """Calculate average actions per point."""
    from utils.helpers import calculate_total_points_from_loader
    
    # Calculate total points (reusable helper function)
    total_points = calculate_total_points_from_loader(loader)
    
    if total_points > 0:
        # Count total actions from aggregated data if available
        total_actions = 0.0
        if loader is not None and hasattr(loader, 'player_data_by_set'):
            for set_num in loader.player_data_by_set.keys():
                for player in loader.player_data_by_set[set_num].keys():
                    stats = loader.player_data_by_set[set_num][player].get('stats', {})
                    total_actions += (
                        float(stats.get('Attack_Total', 0) or 0) +
                        float(stats.get('Service_Total', 0) or 0) +
                        float(stats.get('Block_Total', 0) or 0) +
                        float(stats.get('Sets_Total', 0) or 0) +
                        float(stats.get('Dig_Total', 0) or 0)
                    )
            # Add reception actions
            if hasattr(loader, 'reception_data_by_rotation'):
                for set_num in loader.reception_data_by_rotation.keys():
                    for rot_num in loader.reception_data_by_rotation[set_num].keys():
                        rot_data = loader.reception_data_by_rotation[set_num][rot_num]
                        total_actions += float(rot_data.get('total', 0) or 0)
        
        if total_actions > 0:
            return total_actions / total_points
    
    # Fallback: use action rows
    df = analyzer.match_data
    total_actions = len(df)
    if total_actions == 0:
        return 0.0
    
    # Recalculate total_points for fallback (in case loader didn't have data)
    if total_points == 0:
        total_points = calculate_total_points_from_loader(loader)
    
    if total_points > 0:
        return total_actions / total_points
    
    # Final fallback: rough estimate
    total_points = df['set_number'].nunique() * 25  # Rough estimate
    return (total_actions / total_points) if total_points > 0 else 0.0


def _display_insights_section(analyzer: MatchAnalyzer, team_stats: Dict[str, Any], 
                              targets: Dict[str, Any], loader=None) -> None:
    """Display insights and recommendations section."""
    from ui.insights import generate_coach_insights, display_coach_insights_section
    insights = generate_coach_insights(analyzer, team_stats, targets, loader)
    display_coach_insights_section(insights, team_stats, targets, loader)

