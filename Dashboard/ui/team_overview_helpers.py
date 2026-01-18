"""
Helper functions for displaying team overview sections.
Extracted from display_team_overview() for better organization.
"""
from typing import Optional, Dict, Any
import streamlit as st
import pandas as pd
import plotly.express as px
from match_analyzer import MatchAnalyzer
from event_tracker_loader import EventTrackerLoader
from services.session_manager import SessionStateManager
from services.kpi_calculator import KPICalculator
from utils.helpers import filter_good_receptions, filter_good_digs
from utils.formatters import get_performance_color
from config import KPI_TARGETS
import performance_tracker as pt


def _display_metric_styling() -> None:
    """Display CSS styling for metrics - optimized and consolidated."""
    st.markdown(
        """
        <style>
        /* Metric components - consolidated */
        div[data-testid="stMetricDelta"] {
            background-color: transparent !important;
            padding: 0 !important;
            font-size: 1rem !important;
        }
        div[data-testid="stMetricDelta"] svg,
        div[data-testid="stMetricDelta"] > div {
            background-color: transparent !important;
            color: inherit !important;
        }
        div[data-testid="stMetricValue"] {
            font-size: 2.5rem !important;
            font-weight: 700 !important;
            padding: 0 !important;
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
        div[data-testid="stMetricLabel"] {
            font-size: 1.1rem !important;
            font-weight: 600 !important;
            padding: 0 !important;
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
        }
        div[data-testid="stMetricContainer"] {
            padding: 0.1rem 0.25rem !important;
            gap: 0 !important;
            margin-top: 0 !important;
            padding-top: 0 !important;
            margin-bottom: 0 !important;
            padding-bottom: 0 !important;
            min-height: auto !important;
            height: auto !important;
        }
        /* Info buttons */
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
        button[key^="info_btn_"] {
            font-size: 0.75rem !important;
            width: 24px !important;
            height: 24px !important;
            opacity: 0.6 !important;
            background: transparent !important;
            border: 1px solid #ddd !important;
            border-radius: 3px !important;
        }
        button[key^="info_btn_"]:hover {
            opacity: 1 !important;
            background: #f0f0f0 !important;
        }
        /* Layout containers - consolidated */
        div[data-testid="column"] {
            padding-left: 0.25rem !important;
            padding-right: 0.5rem !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            min-height: auto !important;
            height: auto !important;
        }
        /* Shift score progression charts to the left */
        div[data-testid="stElementContainer"]:has(div[data-testid="stPlotlyChart"]:has(div[key*="score_progression"])) {
            margin-left: -15px !important;
            padding-left: 0 !important;
        }
        div[data-testid="stElementContainer"]:has(div[data-testid="stPlotlyChart"]:has(div[key*="score_progression"])) > div {
            margin-left: 0 !important;
        }
        div[data-testid="column"] > div {
            min-height: auto !important;
            height: auto !important;
        }
        div[data-testid="column"] + div[data-testid="column"] {
            margin-left: 0 !important;
        }
        div[data-testid="column"] > .element-container:has(div[data-testid="column"]) + .element-container {
            margin-top: 0.5rem !important;
        }
        .element-container {
            padding: 0 !important;
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            min-height: auto !important;
            height: auto !important;
        }
        /* Markdown and text containers - consolidated */
        div[data-testid="stMarkdownContainer"],
        div[data-testid="stMetricContainer"] {
            margin-top: 0 !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
            min-height: auto !important;
            height: auto !important;
        }
        /* Hide specific empty markdown container between match header and Core Performance Metrics */
        div[data-testid="stElementContainer"]:nth-child(2) > div[data-testid="stMarkdownContainer"]:has(> div.st-emotion-cache-ai037n:empty),
        div[data-testid="stElementContainer"]:nth-child(2) > div[data-testid="stMarkdownContainer"]:empty {
            display: none !important;
            height: 0 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        div[data-testid="stMarkdownContainer"] p {
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1 !important;
        }
        div[data-testid="stMarkdownContainer"] p strong {
            font-size: 1.15rem !important;
            line-height: 1 !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        div[data-testid="stCaptionContainer"] {
            margin-top: 0.05rem !important;
            margin-bottom: 0 !important;
            padding-top: 0 !important;
            padding-bottom: 0 !important;
        }
        div[data-testid="stCaptionContainer"] > p {
            margin: 0 !important;
            padding: 0 !important;
            line-height: 1.1 !important;
        }
        /* Headings */
        h4, h3 {
            font-size: 1.15rem !important;
        }
        /* Ensure Plotly charts fit within their containers */
        div[data-testid="stPlotlyChart"] {
            overflow: hidden !important;
            width: 100% !important;
        }
        div[data-testid="stPlotlyChart"] > div {
            max-width: 100% !important;
            width: 100% !important;
            overflow: hidden !important;
        }
        div.plot-container.plotly {
            max-width: 100% !important;
            width: 100% !important;
            overflow: hidden !important;
        }
        div.js-plotly-plot {
            width: 100% !important;
            max-width: 100% !important;
        }
        div.user-select-none.svg-container {
            width: 100% !important;
            max-width: 100% !important;
            overflow: hidden !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )


def _render_single_metric(
    label: str,
    value: float,
    targets: Dict[str, float],
    formula: str,
    info_key: str,
    is_percentage: bool = True
) -> None:
    """Render a single metric card.
    
    Args:
        label: Metric label
        value: Metric value
        targets: Target dictionary
        formula: Formula description
        info_key: Unique key for info button
        is_percentage: Whether value is a percentage
    """
    target_optimal = targets.get('optimal', (targets.get('min', 0) + targets.get('max', 0)) / 2)
    metric_color = get_performance_color(value, targets['min'], targets['max'], target_optimal)
    
    # Create label with inline info icon
    label_col, icon_col, metric_col = st.columns([12, 1, 0.1], gap="small")
    with label_col:
        st.markdown(f'**{label} {metric_color}**', unsafe_allow_html=True)
    with icon_col:
        if st.button("ℹ️", key=f"info_{info_key}_btn", help="Show definition", use_container_width=False, type="secondary"):
            st.session_state[f'show_info_{info_key}'] = not st.session_state.get(f'show_info_{info_key}', False)
    
    # Calculate delta vs target
    delta_vs_target = value - target_optimal
    delta_color = "normal" if value >= target_optimal else "inverse"
    delta_label = f"{delta_vs_target:+.1%} vs target ({target_optimal:.0%})" if is_percentage else f"{delta_vs_target:+.1f} vs target ({target_optimal:.1f})"
    
    # Format display value
    display_value = f"{value:.1%}" if is_percentage else f"{value:.1f}"
    
    st.metric(
        label="",
        value=display_value,
        delta=delta_label,
        delta_color=delta_color,
        help=formula
    )
    
    # CSS for info button positioning
    st.markdown(
        f"""
        <style>
            div[data-testid="column"]:has(button[key="info_{info_key}_btn"]) {{
                position: relative;
                margin-left: -40px;
                margin-top: -36px;
            }}
            button[key="info_{info_key}_btn"] {{
                background: transparent !important;
                border: none !important;
                color: #050d76 !important;
                font-size: 0.95rem !important;
                padding: 0 !important;
                opacity: 0.65;
                margin: 0 !important;
            }}
            button[key="info_{info_key}_btn"]:hover {{
                opacity: 1;
                transform: scale(1.2);
            }}
        </style>
        """,
        unsafe_allow_html=True
    )
    
    # Show info if toggled
    if st.session_state.get(f'show_info_{info_key}', False):
        description = f"**{label}**\n\n**Formula:** {formula}\n\n**Current Calculation:** {display_value}"
        st.info(description)


def _display_kpi_metrics_row_1(
    analyzer: MatchAnalyzer,
    kpis: Optional[Dict[str, Any]],
    team_stats: Dict[str, Any],
    targets: Dict[str, Dict[str, float]],
    loader=None
) -> None:
    """Display first row of KPI metrics (4 metrics).
    
    Args:
        analyzer: MatchAnalyzer instance
        kpis: Optional KPIs dictionary
        team_stats: Team statistics dictionary
        targets: KPI targets dictionary
    """
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Serving Point Rate
        serving_point_rate = (kpis['break_point_rate'] if kpis else team_stats.get('serve_point_percentage', 0.0))
        serving_point_targets = targets.get('break_point_rate', KPI_TARGETS.get('break_point_rate', {'min': 0.50, 'max': 0.60, 'optimal': 0.55}))
        _render_single_metric(
            "Serving Point Rate",
            serving_point_rate,
            serving_point_targets,
            "Points Won When Serving / Total Serving Rallies",
            "serving_point"
        )
    
    with col2:
        # Serve In-Rate
        service_value = (kpis['serve_in_rate'] if kpis else None)
        if service_value is None:
            kpi_calc = KPICalculator(analyzer=analyzer, loader=loader)
            service_value = kpi_calc.calculate_serve_in_rate()
        serve_in_targets = targets.get('serve_in_rate', KPI_TARGETS.get('serve_in_rate', {'min': 0.85, 'max': 0.95, 'optimal': 0.90}))
        _render_single_metric(
            "Serve In-Rate",
            service_value,
            serve_in_targets,
            "(Aces + Good Serves) / Total Serve Attempts",
            "service"
        )
    
    with col3:
        # Attack Kill %
        attack_value = (kpis['attack_kill_pct'] if kpis else team_stats.get('kill_percentage', 0.0))
        if attack_value is None or (kpis is None and 'kill_percentage' not in team_stats):
            kpi_calc = KPICalculator(analyzer=analyzer, loader=loader)
            attack_value = kpi_calc.calculate_attack_kill_pct()
        attack_targets = targets.get('kill_percentage', KPI_TARGETS.get('kill_percentage', {'min': 0.35, 'max': 0.50, 'optimal': 0.42}))
        _render_single_metric(
            "Attack Kill %",
            attack_value,
            attack_targets,
            "Attack Kills / Total Attack Attempts",
            "attack"
        )
    
    with col4:
        # Dig Rate
        dig_rate = (kpis['dig_rate'] if kpis else None)
        if dig_rate is None:
            kpi_calc = KPICalculator(analyzer=analyzer, loader=loader)
            dig_rate = kpi_calc.calculate_dig_rate()
        dig_targets = targets.get('dig_rate', KPI_TARGETS.get('dig_rate', {'min': 0.65, 'max': 0.80, 'optimal': 0.70}))
        _render_single_metric(
            "Dig Rate",
            dig_rate,
            dig_targets,
            "Good Digs / Total Dig Attempts",
            "dig"
        )


def _display_kpi_metrics_row_2(
    analyzer: MatchAnalyzer,
    kpis: Optional[Dict[str, Any]],
    team_stats: Dict[str, Any],
    targets: Dict[str, Dict[str, float]],
    loader: Optional[EventTrackerLoader]
) -> None:
    """Display second row of KPI metrics (4 metrics).
    
    Args:
        analyzer: MatchAnalyzer instance
        kpis: Optional KPIs dictionary
        team_stats: Team statistics dictionary
        targets: KPI targets dictionary
        loader: Optional EventTrackerLoader
    """
    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        # Receiving Point Rate
        receiving_point_rate = (kpis['side_out_efficiency'] if kpis else team_stats['side_out_percentage'])
        receiving_point_targets = targets.get('side_out_percentage', KPI_TARGETS.get('side_out_percentage', {'min': 0.65, 'max': 0.75, 'optimal': 0.70}))
        _render_single_metric(
            "Receiving Point Rate",
            receiving_point_rate,
            receiving_point_targets,
            "Points Won When Receiving / Total Receiving Rallies",
            "receiving_point"
        )
    
    with col6:
        # Reception Quality
        reception_quality = (kpis['reception_quality'] if kpis else None)
        if reception_quality is None:
            kpi_calc = KPICalculator(analyzer=analyzer, loader=loader)
            reception_quality = kpi_calc.calculate_reception_quality()
        reception_targets = targets.get('reception_quality', KPI_TARGETS.get('reception_quality', {'min': 0.70, 'max': 0.85, 'optimal': 0.75}))
        _render_single_metric(
            "Reception Quality",
            reception_quality,
            reception_targets,
            "Good Receptions / Total Reception Attempts",
            "reception"
        )
    
    with col7:
        # Block Kill %
        block_kill_pct = (kpis['block_kill_pct'] if kpis else None)
        if block_kill_pct is None:
            kpi_calc = KPICalculator(analyzer=analyzer, loader=loader)
            block_kill_pct = kpi_calc.calculate_block_kill_pct()
        block_kill_targets = targets.get('block_kill_percentage', KPI_TARGETS.get('block_kill_percentage', {'min': 0.05, 'max': 0.15, 'optimal': 0.10}))
        _render_single_metric(
            "Block Kill %",
            block_kill_pct,
            block_kill_targets,
            "Block Kills / Total Block Attempts",
            "block_kill"
        )
    
    with col8:
        # Avg Actions/Point (no target)
        avg_actions = (kpis['avg_actions_per_point'] if kpis else None)
        if avg_actions is None:
            kpi_calc = KPICalculator(analyzer=analyzer, loader=loader)
            avg_actions = kpi_calc.calculate_avg_actions()
        
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
                    color: #050d76 !important;
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
            st.info(f"**Average Actions per Point**\n\n**Formula:** Total Actions / Total Points Played\n\n**Description:** Average number of actions per point. Higher indicates longer rallies.\n\n**Current Calculation:** {avg_actions:.1f}")


def _display_match_banner(loader: Optional[EventTrackerLoader]) -> None:
    """Display match result banner.
    
    Args:
        loader: Optional EventTrackerLoader instance
    """
    if loader is not None and hasattr(loader, 'team_data') and loader.team_data:
        set_results = pt.compute_set_results_from_loader(loader) if hasattr(pt, 'compute_set_results_from_loader') else []
        summary = pt.get_match_summary(set_results) if hasattr(pt, 'get_match_summary') else {'label': 'No sets', 'outcome': 'N/A'}
        opponent = SessionStateManager.get_opponent_name() or 'Opponent'
        banner_color = "#e6ffed" if summary['outcome'] == 'Win' else ("#ffecec" if summary['outcome'] == 'Loss' else "#f5f5f5")
        st.markdown(f"""
        <div style="padding:14px 18px;border:2px solid #050d76;border-radius:12px;background:{banner_color};margin-bottom:12px;">
            <div style="font-size:20px;font-weight:700;color:#050d76;">Match Result: {summary['label']}</div>
            <div style="color:#050d76;opacity:0.85;margin-top:4px;">vs {opponent}</div>
        </div>
        """, unsafe_allow_html=True)


def _display_rotation_analysis(analyzer: MatchAnalyzer) -> None:
    """Display rotation performance analysis.
    
    Args:
        analyzer: MatchAnalyzer instance
    """
    st.markdown("### 🔄 Rotation Performance Analysis")
    
    rotation_stats = analyzer.analyze_rotation_performance()
    if rotation_stats:
        rotation_summary = []
        for rotation in sorted(rotation_stats.keys()):
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


def _display_pass_quality_analysis(analyzer: MatchAnalyzer, team_stats: Dict[str, Any]) -> None:
    """Display pass quality visualization.
    
    Args:
        analyzer: MatchAnalyzer instance
        team_stats: Team statistics dictionary
    """
    if team_stats and team_stats.get('perfect_passes', 0) + team_stats.get('good_passes', 0) + team_stats.get('poor_passes', 0) > 0:
        st.markdown("### 🎯 Pass Quality Analysis")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Pass Quality Distribution
            pass_data = {
                'Quality': ['Perfect (1)', 'Good (2)', 'Poor (3)'],
                'Count': [
                    team_stats.get('perfect_passes', 0),
                    team_stats.get('good_passes', 0),
                    team_stats.get('poor_passes', 0)
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
                hole=0.4,
                color_discrete_map={
                    'Perfect (1)': '#00AA00',
                    'Good (2)': '#FFD700',
                    'Poor (3)': '#FF4500'
                }
            )
            fig_pass.update_traces(textposition='inside', textinfo='percent+label+value')
            # Import chart utilities from main dashboard
            import sys
            import os
            from charts.utils import apply_beautiful_theme, plotly_config
            fig_pass = apply_beautiful_theme(fig_pass, "Pass Quality Distribution")
            st.plotly_chart(fig_pass, use_container_width=True, config=plotly_config)
        
        with col2:
            # Pass Quality to Attack Efficiency Correlation
            df = analyzer.match_data
            if 'pass_quality' in df.columns and team_stats.get('first_ball_efficiency') is not None:
                pass_attack_stats = []
                for quality in [1, 2, 3]:
                    quality_label = ['Perfect', 'Good', 'Poor'][quality - 1]
                    quality_attacks = df[(df['action'] == 'attack') & (df['pass_quality'] == quality)]
                    if len(quality_attacks) > 0:
                        kills = len(quality_attacks[quality_attacks['outcome'] == 'kill'])
                        errors = len(quality_attacks[quality_attacks['outcome'].isin(['blocked', 'out', 'net'])])  # error removed
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
                    from charts.utils import apply_beautiful_theme, plotly_config
                    fig_pass_eff = apply_beautiful_theme(fig_pass_eff, "Attack Efficiency by Pass Quality")
                    st.plotly_chart(fig_pass_eff, use_container_width=True, config=plotly_config)

