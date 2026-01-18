"""
Team Overview UI Module

Displays team performance overview with KPIs, insights, and charts.
Features premium visual components for professional sports analytics.
"""
from typing import Optional, Dict, Any, List
import streamlit as st
import pandas as pd
from match_analyzer import MatchAnalyzer
import performance_tracker as pt
from config import KPI_TARGETS
from ui.components import display_match_banner
from ui.premium_components import (
    display_match_result_premium,
    display_premium_metric_card,
    create_gauge_chart,
    display_premium_section_header
)
from utils.formatters import format_percentage, get_performance_delta_color, get_performance_color
from utils.helpers import filter_good_receptions, filter_good_digs, filter_block_touches
from ui.team_overview_helpers import _display_metric_styling
from services.kpi_calculator import KPICalculator


def display_team_overview(analyzer: MatchAnalyzer, loader=None) -> None:
    """Display team performance overview with KPIs and insights.
    
    Restructured into 5 logical sections:
    1. Match Context & Quick Summary
    2. Core Performance Metrics
    3. Match Flow & Momentum
    4. Skill Performance Analysis
    5. Performance Trends & Consistency
    
    Args:
        analyzer: MatchAnalyzer instance with loaded match data
        loader: Optional ExcelMatchLoader instance for team data
    """
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
    
    # ============================================================
    # SECTION 1: Match Result & Executive Summary
    # ============================================================
    _display_premium_match_header(loader, kpis, targets)
    
    # ============================================================
    # SECTION 2: Core Performance Metrics
    # ============================================================
    display_premium_section_header("Core Performance Metrics", "📊", "Detailed metrics by skill area")
    _display_kpi_metrics(analyzer, team_stats, kpis, targets, loader)
    
    # ============================================================
    # SECTION 3: Match Flow & Momentum
    # ============================================================
    display_premium_section_header("Match Flow & Momentum", "📈", "Score progression and rotation performance")
    from charts.team_charts import create_match_flow_charts
    create_match_flow_charts(analyzer, loader)
    
    # ============================================================
    # SECTION 4: Skill Performance Analysis
    # ============================================================
    display_premium_section_header("Skill Performance Analysis", "🎯", "Detailed breakdown by skill area")
    from charts.team_charts import create_skill_performance_charts
    create_skill_performance_charts(analyzer, loader)
    
    


def _get_kpis(loader, analyzer: MatchAnalyzer, team_stats: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Get KPIs from loader if available, otherwise return None."""
    if loader is not None:
        # Check for both team_data and team_data_by_set (for EventTrackerLoader compatibility)
        has_team_data = (hasattr(loader, 'team_data') and loader.team_data) or \
                       (hasattr(loader, 'team_data_by_set') and loader.team_data_by_set)
        if has_team_data and hasattr(pt, 'compute_team_kpis_from_loader'):
            try:
                return pt.compute_team_kpis_from_loader(loader)
            except Exception as e:
                import logging
                logging.warning(f"Could not compute KPIs from loader: {e}")
                pass
    return None


def _display_premium_match_header(loader, kpis: Optional[Dict[str, Any]], targets: Dict[str, Any]) -> None:
    """Display premium match header with result banner, scorecard, and executive summary.
    
    Args:
        loader: ExcelMatchLoader instance
        kpis: Computed KPIs dictionary
        targets: KPI targets dictionary
    """
    import performance_tracker as pt
    from ui.components import _get_match_result_summary
    
    try:
        # Get match result data using existing helpers
        summary = _get_match_result_summary(loader) if loader else None
        
        if summary:
            # Get set results using existing function
            set_results = []
            if loader and hasattr(loader, 'team_data'):
                try:
                    set_results = pt.compute_set_results_from_loader(loader) if hasattr(pt, 'compute_set_results_from_loader') else []
                except Exception:
                    pass
            
            # Extract set scores from set_results
            set_scores = []
            if set_results:
                for result in sorted(set_results, key=lambda x: x.get('set_number', 0)):
                    our_points = result.get('our_points', 0)
                    opp_points = result.get('opp_points', 0)
                    if our_points > 0 or opp_points > 0:
                        set_scores.append((our_points, opp_points))
            
            # Get opponent name
            opponent = ""
            if loader and hasattr(loader, 'match_info') and loader.match_info:
                opponent = loader.match_info.get('opponent', '')
            
            # Display premium match result
            # Use set_scores if available, otherwise use default placeholders
            if not set_scores:
                # Create default scores based on sets_won/sets_lost
                sets_won = summary.get('sets_won', 0)
                sets_lost = summary.get('sets_lost', 0)
                set_scores = [(25, 20)] * sets_won + [(20, 25)] * sets_lost
            
            display_match_result_premium(
                outcome=summary['outcome'],
                sets_won=summary.get('sets_won', 0),
                sets_lost=summary.get('sets_lost', 0),
                set_scores=set_scores,
                opponent=opponent
            )
        else:
            # Fallback to standard banner
            display_match_banner(loader)
    except Exception as e:
        import logging
        logging.error(f"Error displaying premium match header: {e}", exc_info=True)
        # Fallback to standard banner
        display_match_banner(loader)
    
    # Executive Summary and Performance Scorecard removed per user request


def _display_kpi_metrics(analyzer: MatchAnalyzer, team_stats: Dict[str, Any], 
                        kpis: Optional[Dict[str, Any]], targets: Dict[str, Any], loader=None) -> None:
    """Display KPI metrics in organized groups: Scoring, Service, Defense & Transition, Attack and Net Performance."""
    
    # Initialize KPI Calculator for all calculations
    kpi_calc = KPICalculator(analyzer=analyzer, loader=loader)
    
    # ==========================================
    # SCORING SECTION
    # ==========================================
    st.markdown('<div style="display: flex; align-items: center; margin-top: 2px; margin-bottom: 4px;"><span style="font-size: 20px; font-weight: 700; color: #040C7B;">⚡ Scoring</span><span style="font-size: 13px; color: #666; margin-left: 12px; font-weight: 400;">Point production efficiency</span></div>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        serving_rate = kpis['break_point_rate'] if kpis else team_stats.get('serve_point_percentage', 0.0)
        serving_points_won = kpis['totals']['serving_points_won'] if kpis and 'totals' in kpis else 0
        serving_rallies = kpis['totals']['serving_rallies'] if kpis and 'totals' in kpis else 0
        _display_metric_card(
            "Serving Point Rate",
            serving_rate,
            targets['break_point_rate'],
            "Points won when serving",
            "info_serving_point",
            numerator=serving_points_won,
            denominator=serving_rallies
        )
    
    with col2:
        receiving_rate = kpis['side_out_efficiency'] if kpis else team_stats['side_out_percentage']
        receiving_points_won = kpis['totals']['receiving_points_won'] if kpis and 'totals' in kpis else 0
        receiving_rallies = kpis['totals']['receiving_rallies'] if kpis and 'totals' in kpis else 0
        _display_metric_card(
            "Receiving Point Rate",
            receiving_rate,
            targets['side_out_percentage'],
            "Points won when receiving",
            "info_receiving_point",
            numerator=receiving_points_won,
            denominator=receiving_rallies
        )
    
    with col3:
        # % of total points in the lead (momentum statistic)
        try:
            points_in_lead_pct = kpi_calc.calculate_points_in_lead_pct()
            points_in_lead_count = kpi_calc.calculate_points_in_lead_count()
            total_points = kpi_calc.calculate_total_points_count()
            _display_metric_card(
                "% Points in Lead",
                points_in_lead_pct,
                targets.get('points_in_lead', {'min': 0.40, 'max': 0.60, 'optimal': 0.50}),
                "Points where team was leading / total points",
                "info_points_in_lead",
                numerator=points_in_lead_count,
                denominator=total_points
            )
        except Exception as e:
            import logging
            logging.error(f"Error displaying points in lead metric: {e}", exc_info=True)
            # Fallback display
            st.markdown('**% Points in Lead**')
            st.info("Data not available")
    
    # Add reduced margin after metrics
    st.markdown('<div style="margin-bottom: 8px;"></div>', unsafe_allow_html=True)
    
    # Separator at end of Scoring section
    st.markdown('<hr style="margin: 0.75rem 0; border: none; border-top: 1px solid #E0E0E0;">', unsafe_allow_html=True)
    
    # ==========================================
    # SERVICE SECTION
    # ==========================================
    st.markdown('<div style="display: flex; align-items: center; margin-top: 8px; margin-bottom: 4px;"><span style="font-size: 20px; font-weight: 700; color: #040C7B;">🎾 Service</span><span style="font-size: 13px; color: #666; margin-left: 12px; font-weight: 400;">Serve quality and consistency</span></div>', unsafe_allow_html=True)
    
    col3, col4, col5 = st.columns(3)
    
    with col3:
        service_value = kpis['serve_in_rate'] if kpis else kpi_calc.calculate_serve_in_rate()
        service_aces = kpis['totals']['service_aces'] if kpis and 'totals' in kpis else 0
        service_good = kpis['totals']['service_good'] if kpis and 'totals' in kpis else 0
        serve_attempts = kpis['totals']['serve_attempts'] if kpis and 'totals' in kpis else 0
        service_in = service_aces + service_good
        _display_metric_card(
            "Serve In-Rate",
            service_value,
            targets['serve_in_rate'],
            "(Aces + Good) / total",
            "info_service",
            numerator=service_in,
            denominator=serve_attempts
        )
    
    with col4:
        # Service Error Rate (lower is better)
        service_errors = kpis['totals'].get('service_errors', 0) if kpis and 'totals' in kpis else 0
        error_rate = (service_errors / serve_attempts) if serve_attempts > 0 else 0.0
        _display_metric_card(
            "Service Errors",
            error_rate,
            targets['service_error_rate'],
            "Errors / total serves",
            "info_serve_error",
            numerator=service_errors,
            denominator=serve_attempts,
            lower_is_better=True
        )
    
    with col5:
        # Ace Rate
        ace_rate = (service_aces / serve_attempts) if serve_attempts > 0 else 0.0
        _display_metric_card(
            "Aces",
            ace_rate,
            targets['ace_rate'],
            "Aces / total serves",
            "info_ace_rate",
            numerator=service_aces,
            denominator=serve_attempts
        )
    
    # Separator at end of Service section
    st.markdown('<hr style="margin: 0.75rem 0; border: none; border-top: 1px solid #E0E0E0;">', unsafe_allow_html=True)
    
    # ==========================================
    # DEFENSE & TRANSITION SECTION
    # ==========================================
    st.markdown('<div style="display: flex; align-items: center; margin-top: 8px; margin-bottom: 4px;"><span style="font-size: 20px; font-weight: 700; color: #040C7B;">🛡️ Defense & Transition</span><span style="font-size: 13px; color: #666; margin-left: 12px; font-weight: 400;">Quality of defensive contacts</span></div>', unsafe_allow_html=True)
    
    col6, col7, col8 = st.columns(3)
    
    with col6:
        reception_quality = kpis['reception_quality'] if kpis else kpi_calc.calculate_reception_quality()
        rec_good = kpis['totals']['reception_good'] if kpis and 'totals' in kpis else 0
        rec_total = kpis['totals']['reception_total'] if kpis and 'totals' in kpis else 0
        _display_metric_card(
            "Reception Quality",
            reception_quality,
            targets['reception_quality'],
            "Good and perfect receptions / total",
            "info_reception",
            numerator=rec_good,
            denominator=rec_total
        )
    
    with col7:
        dig_rate = kpis['dig_rate'] if kpis else kpi_calc.calculate_dig_rate()
        dig_good = kpis['totals']['dig_good'] if kpis and 'totals' in kpis else 0
        dig_total = kpis['totals']['dig_total'] if kpis and 'totals' in kpis else 0
        _display_metric_card(
            "Dig Rate %",
            dig_rate,
            targets['dig_rate'],
            "Good and perfect digs / total",
            "info_dig",
            numerator=dig_good,
            denominator=dig_total
        )
    
    with col8:
        # Reception Error % (lower is better)
        reception_error_pct = kpi_calc.calculate_reception_error_pct(kpis=kpis)
        rec_errors = kpis['totals'].get('reception_errors', 0) if kpis and 'totals' in kpis else 0
        rec_total = kpis['totals']['reception_total'] if kpis and 'totals' in kpis else 0
        _display_metric_card(
            "Reception Error %",
            reception_error_pct,
            targets['reception_error_rate'],
            "Reception errors / total receptions",
            "info_reception_error",
            numerator=rec_errors,
            denominator=rec_total,
            lower_is_better=True
        )
    
    # Separator at end of Defense & Transition section
    st.markdown('<hr style="margin: 0.75rem 0; border: none; border-top: 1px solid #E0E0E0;">', unsafe_allow_html=True)
    
    # ==========================================
    # ATTACK AND NET PERFORMANCE SECTION
    # ==========================================
    st.markdown('<div style="display: flex; align-items: center; margin-top: 8px; margin-bottom: 4px;"><span style="font-size: 20px; font-weight: 700; color: #040C7B;">🎯 Attack and Net Performance</span><span style="font-size: 13px; color: #666; margin-left: 12px; font-weight: 400;">Attack efficiency and blocking</span></div>', unsafe_allow_html=True)
    
    col9, col10, col11 = st.columns(3)
    
    with col9:
        attack_value = kpis['attack_kill_pct'] if kpis else team_stats.get('kill_percentage', 0.0)
        if attack_value is None:
            attack_value = kpi_calc.calculate_attack_kill_pct()
        attack_kills = kpis['totals']['attack_kills'] if kpis and 'totals' in kpis else 0
        attack_attempts = kpis['totals']['attack_attempts'] if kpis and 'totals' in kpis else 0
        _display_metric_card(
            "Attack Kill %",
            attack_value,
            targets['kill_percentage'],
            "Attack kills / attempts",
            "info_attack",
            numerator=attack_kills,
            denominator=attack_attempts
        )
    
    with col10:
        # Attack Error % (lower is better) - all error types / all attempts
        attack_error_pct = kpi_calc.calculate_attack_error_pct(kpis=kpis)
        attack_errors = kpis['totals'].get('attack_errors', 0) if kpis and 'totals' in kpis else 0
        attack_attempts = kpis['totals']['attack_attempts'] if kpis and 'totals' in kpis else 0
        _display_metric_card(
            "Attack Error",
            attack_error_pct,
            targets['attack_error_rate'],
            "All attack errors / total attempts",
            "info_attack_error",
            numerator=attack_errors,
            denominator=attack_attempts,
            lower_is_better=True
        )
    
    with col11:
        # Block % - block kill + block no kill / total block attempts
        block_pct = kpi_calc.calculate_block_pct()
        # Count from analyzer for accurate numerator
        blocks = analyzer.match_data[analyzer.match_data['action'] == 'block']
        block_kills = len(blocks[blocks['outcome'] == 'kill'])
        block_no_kill = len(blocks[blocks['outcome'] == 'block_no_kill'])
        block_attempts = len(blocks)
        _display_metric_card(
            "Block %",
            block_pct,
            targets['block_percentage'],
            "(Block kills + Block no kill) / total attempts",
            "info_block_pct",
            numerator=block_kills + block_no_kill,
            denominator=block_attempts
        )
    
    # Separator at end of Attack and Net Performance section
    st.markdown('<hr style="margin: 0.75rem 0; border: none; border-top: 1px solid #E0E0E0;">', unsafe_allow_html=True)


def _display_metric_card(label: str, value: float, targets: Dict[str, float],
                         formula: str, info_key: str, is_percentage: bool = True,
                         numerator: Optional[int] = None, denominator: Optional[int] = None,
                         lower_is_better: bool = False) -> None:
    """Display a single metric card with info button and sample size.
    
    Args:
        label: Metric label
        value: Metric value (0-1 for percentages, or raw number)
        targets: Target dictionary with 'min', 'max', 'optimal'
        formula: Formula description
        info_key: Unique key for info button
        is_percentage: Whether value is a percentage (0-1)
        numerator: Count of successes (for sample size display)
        denominator: Total count (for sample size display)
        lower_is_better: If True, lower values are better (e.g., avg_actions_per_point)
    """
    from utils.formatters import format_percentage_with_sample_size, get_sample_size_warning, should_hide_metric
    
    # Check if we should hide metric due to small sample size
    if denominator is not None and should_hide_metric(denominator, min_threshold=5):
        st.markdown(f'**{label}**')
        st.metric(
            label="",
            value="N/A",
            delta=None,
            help=f"{formula}\n\n⚠️ Insufficient data (n={denominator})"
        )
        return
    
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
        # For lower_is_better: negative delta is good (value is lower than target)
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
    
    # Display formula/definition as collapsible
    if st.session_state.get(f'show_formula_{info_key}', False):
        st.caption(f"📊 {formula}")
    
    # Show warning if small sample size
    if denominator is not None:
        warning = get_sample_size_warning(denominator)
        if warning:
            st.caption(f"⚠️ {warning}")



































def _display_performance_scorecard(kpis: Optional[Dict[str, Any]], loader=None) -> None:
    """Display performance scorecard with match result, overall rating, and key win factor.
    
    Args:
        kpis: Optional dictionary of KPIs
        loader: Optional loader instance for match data
    """
    st.markdown('<h2 class="main-header">📋 Performance Scorecard</h2>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    # Column 1: Match Result & Sets Won
    with col1:
        st.markdown("#### 🏆 Match Result")
        if loader and hasattr(loader, 'team_events') and len(loader.team_events) > 0:
            team_events = loader.team_events
            sets_played = sorted(team_events['Set'].unique())
            sets_won = 0
            sets_lost = 0
            
            for set_num in sets_played:
                set_data = team_events[team_events['Set'] == set_num]
                if len(set_data) > 0:
                    final_row = set_data.iloc[-1]
                    our_score = int(final_row.get('Our_Score', 0))
                    opp_score = int(final_row.get('Opponent_Score', 0))
                    if our_score > opp_score:
                        sets_won += 1
                    else:
                        sets_lost += 1
            
            st.metric("Sets Won", sets_won, delta=f"{sets_lost} sets lost")
            st.metric("Sets Played", len(sets_played))
        else:
            st.info("Match result data not available")
    
    # Column 2: Overall Performance Rating
    with col2:
        st.markdown("#### ⭐ Overall Performance Rating")
        if kpis:
            # Calculate overall rating based on KPI performance vs targets
            kpi_scores = []
            kpi_names = [
                ('break_point_rate', 'Serving Point Rate'),
                ('side_out_efficiency', 'Receiving Point Rate'),
                ('attack_kill_pct', 'Attack Kill %'),
                ('reception_quality', 'Reception Quality'),
                ('serve_in_rate', 'Serve In-Rate'),
                ('block_kill_pct', 'Block Kill %'),
                ('dig_rate', 'Dig Rate')
            ]
            
            for kpi_key, kpi_name in kpi_names:
                if kpi_key in kpis and kpi_key in KPI_TARGETS:
                    kpi_value = kpis[kpi_key]
                    target_optimal = KPI_TARGETS[kpi_key].get('optimal', 0.5)
                    target_min = KPI_TARGETS[kpi_key].get('min', 0.0)
                    target_max = KPI_TARGETS[kpi_key].get('max', 1.0)
                    
                    # Score: 0-100 based on performance vs target
                    if kpi_value >= target_optimal:
                        score = 100
                    elif kpi_value >= target_min:
                        # Linear interpolation between min and optimal
                        score = 50 + 50 * ((kpi_value - target_min) / (target_optimal - target_min))
                    else:
                        # Below minimum
                        score = max(0, 50 * (kpi_value / target_min))
                    
                    kpi_scores.append(score)
            
            if kpi_scores:
                overall_score = sum(kpi_scores) / len(kpi_scores)
                
                # Determine rating
                if overall_score >= 80:
                    rating = "Excellent"
                    rating_emoji = "🟢"
                    rating_color = "#28A745"
                elif overall_score >= 65:
                    rating = "Good"
                    rating_emoji = "🟡"
                    rating_color = "#FFC107"
                elif overall_score >= 50:
                    rating = "Fair"
                    rating_emoji = "🟠"
                    rating_color = "#FF9800"
                else:
                    rating = "Poor"
                    rating_emoji = "🔴"
                    rating_color = "#DC3545"
                
                st.markdown(f'<div style="text-align: center; padding: 1rem; background-color: {rating_color}20; border-radius: 8px; border: 2px solid {rating_color};">'
                           f'<h3 style="margin: 0; color: {rating_color};">{rating_emoji} {rating}</h3>'
                           f'<p style="margin: 0.5rem 0 0 0; font-size: 1.2rem; font-weight: bold; color: {rating_color};">{overall_score:.0f}/100</p>'
                           f'</div>', unsafe_allow_html=True)
            else:
                st.info("Insufficient data for rating")
        else:
            st.info("KPI data not available")
    
    # Column 3: Key Win Factor
    with col3:
        st.markdown("#### 🎯 Key Win Factor")
        if kpis:
            # Identify strongest performing KPI
            kpi_performance = {}
            kpi_labels = {
                'break_point_rate': 'Strong Serving',
                'side_out_efficiency': 'Strong Receiving',
                'attack_kill_pct': 'Efficient Attacking',
                'reception_quality': 'Quality Reception',
                'serve_in_rate': 'Consistent Serving',
                'block_kill_pct': 'Effective Blocking',
                'dig_rate': 'Strong Defense'
            }
            
            for kpi_key, kpi_label in kpi_labels.items():
                if kpi_key in kpis and kpi_key in KPI_TARGETS:
                    kpi_value = kpis[kpi_key]
                    target_optimal = KPI_TARGETS[kpi_key].get('optimal', 0.5)
                    # Performance ratio vs target
                    if target_optimal > 0:
                        performance_ratio = kpi_value / target_optimal
                        kpi_performance[kpi_label] = performance_ratio
            
            if kpi_performance:
                # Find strongest performing KPI
                strongest_kpi = max(kpi_performance.items(), key=lambda x: x[1])
                factor_name = strongest_kpi[0]
                factor_performance = strongest_kpi[1]
                
                st.markdown(f'<div style="text-align: center; padding: 1rem; background-color: #E3F2FD; border-radius: 8px; border: 2px solid #2196F3;">'
                           f'<h4 style="margin: 0; color: #1976D2;">{factor_name}</h4>'
                           f'<p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; color: #424242;">{factor_performance:.0%} of target</p>'
                           f'</div>', unsafe_allow_html=True)
            else:
                st.info("Insufficient data")
        else:
            st.info("KPI data not available")


def _display_player_breakdowns(analyzer: MatchAnalyzer, kpis: Optional[Dict[str, Any]], loader=None) -> None:
    """Display player-level breakdowns for team KPIs (HIGH PRIORITY 9)."""
    from utils.breakdown_helpers import get_kpi_by_player
    from utils.formatters import format_percentage_with_sample_size
    
    st.markdown("### 👥 Player-Level Breakdowns")
    
    # Create tabs for different KPIs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Attack Kill %", "Serve In-Rate", "Reception Quality", "Block Kill %", "Dig Rate"
    ])
    
    with tab1:
        player_attack = get_kpi_by_player(loader, 'attack_kill_pct', return_totals=True)
        if player_attack:
            attack_data = []
            for player, data in sorted(player_attack.items(), key=lambda x: x[1]['value'], reverse=True):
                attack_data.append({
                    'Player': player,
                    'Attack Kill %': format_percentage_with_sample_size(
                        data['value'], data['numerator'], data['denominator']
                    ),
                    'Kills': data['numerator'],
                    'Attempts': data['denominator']
                })
            attack_df = pd.DataFrame(attack_data)
            st.dataframe(attack_df, use_container_width=True, hide_index=True)
        else:
            st.info("No attack data available")
    
    with tab2:
        player_serve = get_kpi_by_player(loader, 'serve_in_rate', return_totals=True)
        if player_serve:
            serve_data = []
            for player, data in sorted(player_serve.items(), key=lambda x: x[1]['value'], reverse=True):
                serve_data.append({
                    'Player': player,
                    'Serve In-Rate': format_percentage_with_sample_size(
                        data['value'], data['numerator'], data['denominator']
                    ),
                    'In': data['numerator'],
                    'Attempts': data['denominator']
                })
            serve_df = pd.DataFrame(serve_data)
            st.dataframe(serve_df, use_container_width=True, hide_index=True)
        else:
            st.info("No service data available")
    
    with tab3:
        player_rec = get_kpi_by_player(loader, 'reception_quality', return_totals=True)
        if player_rec:
            rec_data = []
            for player, data in sorted(player_rec.items(), key=lambda x: x[1]['value'], reverse=True):
                rec_data.append({
                    'Player': player,
                    'Reception Quality': format_percentage_with_sample_size(
                        data['value'], data['numerator'], data['denominator']
                    ),
                    'Good': data['numerator'],
                    'Total': data['denominator']
                })
            rec_df = pd.DataFrame(rec_data)
            st.dataframe(rec_df, use_container_width=True, hide_index=True)
        else:
            st.info("No reception data available")
    
    with tab4:
        player_block = get_kpi_by_player(loader, 'block_kill_pct', return_totals=True)
        if player_block:
            block_data = []
            for player, data in sorted(player_block.items(), key=lambda x: x[1]['value'], reverse=True):
                block_data.append({
                    'Player': player,
                    'Block Kill %': format_percentage_with_sample_size(
                        data['value'], data['numerator'], data['denominator']
                    ),
                    'Kills': data['numerator'],
                    'Attempts': data['denominator']
                })
            block_df = pd.DataFrame(block_data)
            st.dataframe(block_df, use_container_width=True, hide_index=True)
        else:
            st.info("No block data available")
    
    with tab5:
        player_dig = get_kpi_by_player(loader, 'dig_rate', return_totals=True)
        if player_dig:
            dig_data = []
            for player, data in sorted(player_dig.items(), key=lambda x: x[1]['value'], reverse=True):
                dig_data.append({
                    'Player': player,
                    'Dig Rate': format_percentage_with_sample_size(
                        data['value'], data['numerator'], data['denominator']
                    ),
                    'Good': data['numerator'],
                    'Total': data['denominator']
                })
            dig_df = pd.DataFrame(dig_data)
            st.dataframe(dig_df, use_container_width=True, hide_index=True)
        else:
            st.info("No dig data available")


def _display_set_by_set_breakdowns(analyzer: MatchAnalyzer, kpis: Optional[Dict[str, Any]], loader=None) -> None:
    """Display KPI trends across sets for Section 5: Performance Trends & Consistency."""
    from utils.breakdown_helpers import get_kpi_by_set
    import plotly.graph_objects as go
    from charts.utils import apply_beautiful_theme, plotly_config
    from config import OUTCOME_COLORS, CHART_HEIGHTS
    
    st.markdown("### 📈 KPI Trends Across Sets")
    
    # Get set-by-set data for the new KPI list
    set_serve_error = get_kpi_by_set(loader, 'serve_error_rate')
    set_rec = get_kpi_by_set(loader, 'reception_quality')
    set_dig = get_kpi_by_set(loader, 'dig_quality')
    set_attack_kill = get_kpi_by_set(loader, 'attack_kill_pct')
    set_attack_error = get_kpi_by_set(loader, 'attack_error_rate')
    
    # Create summary table
    all_sets = sorted(set(set_serve_error.keys()) | set(set_rec.keys()) | set(set_dig.keys()) | 
                     set(set_attack_kill.keys()) | set(set_attack_error.keys()))
    
    if all_sets:
        # Spider web (radar) charts: One chart per set showing all 5 KPIs
        # Normalize all metrics to 0-100 scale where higher is always better
        # For error metrics, invert them (100 - error%) so higher = better
        
        # Determine layout based on number of sets
        num_sets = len(all_sets)
        if num_sets <= 3:
            cols = st.columns(num_sets)
            rows = [all_sets]
        elif num_sets == 4:
            cols = st.columns(2)
            rows = [all_sets[:2], all_sets[2:]]
        else:  # 5 or more
            cols = st.columns(3)
            rows = [all_sets[:3], all_sets[3:]]
        
        # Create radar chart for each set
        for row_idx, row_sets in enumerate(rows):
            if row_idx > 0:
                st.markdown("<br>", unsafe_allow_html=True)
            
            row_cols = st.columns(len(row_sets)) if len(row_sets) <= 3 else st.columns(3)
            
            for col_idx, set_num in enumerate(row_sets):
                with row_cols[col_idx if len(row_sets) <= 3 else col_idx % 3]:
                    # Get values for this set
                    serve_error_val = set_serve_error.get(set_num, 0.0) * 100
                    rec_val = set_rec.get(set_num, 0.0) * 100
                    dig_val = set_dig.get(set_num, 0.0) * 100
                    attack_kill_val = set_attack_kill.get(set_num, 0.0) * 100
                    attack_error_val = set_attack_error.get(set_num, 0.0) * 100
                    
                    # Normalize: For error metrics, invert so higher = better (100 - error%)
                    # For quality metrics, use as-is
                    normalized_values = [
                        100 - serve_error_val,  # Serve Error % inverted (lower error = higher score)
                        rec_val,                 # Reception Quality (higher = better)
                        dig_val,                 # Dig Quality (higher = better)
                        attack_kill_val,         # Attack Kill % (higher = better)
                        100 - attack_error_val   # Attack Error % inverted (lower error = higher score)
                    ]
                    
                    # KPI labels in order
                    kpi_labels = [
                        'Serve Error %',
                        'Reception Quality',
                        'Dig Quality',
                        'Attack Kill %',
                        'Attack Error %'
                    ]
                    
                    # Create radar chart with actual values for hover
                    actual_values = [
                        serve_error_val,   # Show actual error %
                        rec_val,           # Reception Quality
                        dig_val,           # Dig Quality
                        attack_kill_val,   # Attack Kill %
                        attack_error_val   # Show actual error %
                    ]
                    
                    fig = go.Figure()
                    
                    fig.add_trace(go.Scatterpolar(
                        r=normalized_values,
                        theta=kpi_labels,
                        fill='toself',
                        name=f'Set {set_num}',
                        line=dict(color='#040C7B', width=2.5),
                        marker=dict(size=8, color='#040C7B'),
                        hovertemplate='<b>%{theta}</b><br>Value: %{customdata:.1f}%<extra></extra>',
                        customdata=actual_values
                    ))
                    
                    fig.update_layout(
                        polar=dict(
                            radialaxis=dict(
                                visible=True,
                                range=[0, 100],
                                tickfont=dict(size=10, color='#050d76'),
                                gridcolor='#E8F4F8',
                                linecolor='#BDC3C7',
                                tickmode='linear',
                                tick0=0,
                                dtick=20
                            ),
                            angularaxis=dict(
                                tickfont=dict(size=11, color='#050d76'),
                                linecolor='#BDC3C7'
                            )
                        ),
                        title=dict(
                            text=f"Set {set_num}",
                            font=dict(size=16, color='#040C7B', family='Inter, sans-serif'),
                            x=0.5,
                            xanchor='center'
                        ),
                        height=350,
                        showlegend=False,
                        margin=dict(l=20, r=20, t=50, b=20),
                        paper_bgcolor='rgba(255,255,255,0)',
                        plot_bgcolor='rgba(255,255,255,0.95)'
                    )
                    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"radar_set_{set_num}")
    else:
        st.info("No set-by-set data available")


def _display_position_breakdowns(analyzer: MatchAnalyzer, kpis: Optional[Dict[str, Any]], loader=None) -> None:
    """Display position-level breakdowns for Section 5: Performance Trends & Consistency.
    
    Shows 3 KPIs as horizontal bar charts side-by-side (not donut charts since these don't sum to 100%).
    """
    from utils.breakdown_helpers import get_kpi_by_position
    import plotly.graph_objects as go
    from charts.utils import apply_beautiful_theme, plotly_config
    from config import OUTCOME_COLORS, CHART_HEIGHTS
    
    df = analyzer.match_data
    
    st.markdown("### 👥 Position-Level Breakdowns")
    
    # Get position data for all 3 KPIs
    position_attack = get_kpi_by_position(df, loader, 'attack_kill_pct')
    position_rec = get_kpi_by_position(df, loader, 'reception_quality')
    position_block = get_kpi_by_position(df, loader, 'block_kill_pct')
    
    # Display 3 horizontal bar charts side-by-side
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("#### Attack Kill %")
        if position_attack:
            positions = list(position_attack.keys())
            values = [v * 100 for v in position_attack.values()]
            
            # Sort by value descending
            sorted_data = sorted(zip(positions, values), key=lambda x: x[1], reverse=True)
            positions_sorted, values_sorted = zip(*sorted_data) if sorted_data else ([], [])
            
            # Create horizontal bar chart
            fig = go.Figure(data=go.Bar(
                y=list(positions_sorted),
                x=list(values_sorted),
                orientation='h',
                marker=dict(color=OUTCOME_COLORS['attack_kill']),
                text=[f"{v:.1f}%" for v in values_sorted],
                textposition='outside',
                textfont=dict(size=11, color='#050d76')
            ))
            fig.update_layout(
                height=CHART_HEIGHTS['medium'],
                xaxis_title="Attack Kill %",
                yaxis_title="Position",
                xaxis=dict(tickfont=dict(color='#050d76'), tickformat='.0f', range=[0, max(values_sorted) * 1.15 if values_sorted else 100]),
                yaxis=dict(tickfont=dict(color='#050d76'), autorange='reversed')  # Reverse to show highest at top
            )
            fig = apply_beautiful_theme(fig, "Attack Kill % by Position")
            st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="position_attack_bar")
        else:
            st.info("No attack data by position available")
    
    with col2:
        st.markdown("#### Reception Quality")
        if position_rec:
            positions = list(position_rec.keys())
            values = [v * 100 for v in position_rec.values()]
            
            # Sort by value descending
            sorted_data = sorted(zip(positions, values), key=lambda x: x[1], reverse=True)
            positions_sorted, values_sorted = zip(*sorted_data) if sorted_data else ([], [])
            
            # Create horizontal bar chart
            fig = go.Figure(data=go.Bar(
                y=list(positions_sorted),
                x=list(values_sorted),
                orientation='h',
                marker=dict(color=OUTCOME_COLORS['reception']),
                text=[f"{v:.1f}%" for v in values_sorted],
                textposition='outside',
                textfont=dict(size=11, color='#050d76')
            ))
            fig.update_layout(
                height=CHART_HEIGHTS['medium'],
                xaxis_title="Reception Quality %",
                yaxis_title="Position",
                xaxis=dict(tickfont=dict(color='#050d76'), tickformat='.0f', range=[0, max(values_sorted) * 1.15 if values_sorted else 100]),
                yaxis=dict(tickfont=dict(color='#050d76'), autorange='reversed')  # Reverse to show highest at top
            )
            fig = apply_beautiful_theme(fig, "Reception Quality by Position")
            st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="position_rec_bar")
        else:
            st.info("No reception data by position available")
    
    with col3:
        st.markdown("#### Block Kill %")
        if position_block:
            positions = list(position_block.keys())
            values = [v * 100 for v in position_block.values()]
            
            # Sort by value descending
            sorted_data = sorted(zip(positions, values), key=lambda x: x[1], reverse=True)
            positions_sorted, values_sorted = zip(*sorted_data) if sorted_data else ([], [])
            
            # Create horizontal bar chart
            fig = go.Figure(data=go.Bar(
                y=list(positions_sorted),
                x=list(values_sorted),
                orientation='h',
                marker=dict(color=OUTCOME_COLORS['block_kill']),
                text=[f"{v:.1f}%" for v in values_sorted],
                textposition='outside',
                textfont=dict(size=11, color='#050d76')
            ))
            fig.update_layout(
                height=CHART_HEIGHTS['medium'],
                xaxis_title="Block Kill %",
                yaxis_title="Position",
                xaxis=dict(tickfont=dict(color='#050d76'), tickformat='.0f', range=[0, max(values_sorted) * 1.15 if values_sorted else 100]),
                yaxis=dict(tickfont=dict(color='#050d76'), autorange='reversed')  # Reverse to show highest at top
            )
            fig = apply_beautiful_theme(fig, "Block Kill % by Position")
            st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="position_block_bar")
        else:
            st.info("No block data by position available")


def _display_rotation_breakdowns(analyzer: MatchAnalyzer, kpis: Optional[Dict[str, Any]], loader=None) -> None:
    """Display rotation-level breakdowns for Section 6: Rotation Analysis."""
    import plotly.graph_objects as go
    from charts.utils import apply_beautiful_theme, plotly_config
    from config import OUTCOME_COLORS, CHART_HEIGHTS
    
    if not loader or not hasattr(loader, 'team_data_by_rotation'):
        return
    
    st.markdown("### Rotation Performance Summary")
    
    # Get all sets and rotations
    all_sets = sorted(loader.team_data_by_rotation.keys())
    
    if not all_sets:
        st.info("No rotation-level data available")
        return
    
    # Display rotation data for each set with charts
    for set_num in all_sets:
        st.markdown(f"#### Set {set_num} - Rotation Performance")
        rotations = sorted(loader.team_data_by_rotation[set_num].keys())
        
        serving_rates = []
        receiving_rates = []
        rotation_labels = []
        
        for rotation in rotations:
            rot_data = loader.team_data_by_rotation[set_num][rotation]
            serving_rallies = float(rot_data.get('serving_rallies', 0) or 0)
            serving_points_won = float(rot_data.get('serving_points_won', 0) or 0)
            receiving_rallies = float(rot_data.get('receiving_rallies', 0) or 0)
            receiving_points_won = float(rot_data.get('receiving_points_won', 0) or 0)
            
            serving_rate = (serving_points_won / serving_rallies * 100) if serving_rallies > 0 else 0.0
            receiving_rate = (receiving_points_won / receiving_rallies * 100) if receiving_rallies > 0 else 0.0
            
            rotation_labels.append(f"R{rotation}")
            serving_rates.append(serving_rate)
            receiving_rates.append(receiving_rate)
        
        if rotation_labels:
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=rotation_labels,
                y=serving_rates,
                name='Serving Point Rate',
                marker_color=OUTCOME_COLORS['serving_rate'],
                text=[f"{v:.1f}%" for v in serving_rates],
                textposition='outside',
                textfont=dict(size=10, color='#050d76')
            ))
            fig.add_trace(go.Bar(
                x=rotation_labels,
                y=receiving_rates,
                name='Receiving Point Rate',
                marker_color=OUTCOME_COLORS['receiving_rate'],
                text=[f"{v:.1f}%" for v in receiving_rates],
                textposition='outside',
                textfont=dict(size=10, color='#050d76')
            ))
            fig.update_layout(
                barmode='group',
                height=CHART_HEIGHTS['medium'],
                xaxis_title="Rotation",
                yaxis_title="Point Rate (%)",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(tickfont=dict(color='#050d76')),
                yaxis=dict(tickfont=dict(color='#050d76'), tickformat='.0f')
            )
            fig = apply_beautiful_theme(fig, f"Set {set_num} Rotation Performance")
            st.plotly_chart(fig, use_container_width=True, config=plotly_config)
        else:
            st.info(f"No rotation data for Set {set_num}")


def _display_top_performers_charts(analyzer: MatchAnalyzer, kpis: Optional[Dict[str, Any]], loader=None) -> None:
    """Display top 3 performers charts for each KPI (MEDIUM PRIORITY 25)."""
    from utils.breakdown_helpers import get_kpi_by_player
    import plotly.graph_objects as go
    from charts.utils import apply_beautiful_theme, plotly_config
    
    st.markdown("### 🏆 Top Performers")
    
    # Get top performers for each KPI
    kpi_names = [
        ('attack_kill_pct', 'Attack Kill %', 'Kills'),
        ('serve_in_rate', 'Serve In-Rate', 'In'),
        ('reception_quality', 'Reception Quality', 'Good'),
        ('block_kill_pct', 'Block Kill %', 'Kills'),
        ('dig_rate', 'Dig Rate', 'Good')
    ]
    
    # Create tabs for each KPI
    tabs = st.tabs([name for _, name, _ in kpi_names])
    
    for idx, (kpi_name, display_name, metric_name) in enumerate(kpi_names):
        with tabs[idx]:
            player_data = get_kpi_by_player(loader, kpi_name, return_totals=True)
            
            if not player_data:
                st.info(f"No {display_name} data available")
                continue
            
            # Sort and get top 3
            sorted_players = sorted(player_data.items(), key=lambda x: x[1]['value'], reverse=True)
            top_3 = sorted_players[:3]
            
            if not top_3:
                st.info(f"No {display_name} data available")
                continue
            
            # Create horizontal bar chart
            fig = go.Figure()
            
            players = [p[0] for p in top_3]
            values = [p[1]['value'] * 100 for p in top_3]  # Convert to percentage
            numerators = [p[1]['numerator'] for p in top_3]
            denominators = [p[1]['denominator'] for p in top_3]
            
            # Color bars based on performance (green for top, yellow for middle, blue for bottom)
            colors = ['#90EE90', '#FFD700', '#87CEEB']
            
            fig.add_trace(go.Bar(
                y=players,
                x=values,
                orientation='h',
                marker_color=colors[:len(top_3)],
                text=[f"{v:.1f}% ({n}/{d})" for v, n, d in zip(values, numerators, denominators)],
                textposition='outside',
                textfont=dict(size=11, color='#050d76'),
                hovertemplate='<b>%{y}</b><br>' + 
                             f'{display_name}: %{{x:.1f}}%<br>' +
                             f'{metric_name}: %{{customdata[0]}}/%{{customdata[1]}}<extra></extra>',
                customdata=list(zip(numerators, denominators))
            ))
            
            fig.update_layout(
                title=f"Top 3 Performers: {display_name}",
                xaxis_title=f"{display_name} (%)",
                yaxis_title="Player",
                height=250,
                xaxis=dict(range=[0, max(values) * 1.2 if values else 100], tickfont=dict(color='#050d76')),
                yaxis=dict(tickfont=dict(color='#050d76')),
                showlegend=False,
                margin=dict(l=100, r=20, t=60, b=40)
            )
            fig = apply_beautiful_theme(fig, f"Top Performers: {display_name}")
            st.plotly_chart(fig, use_container_width=True, config=plotly_config)
            
            # Show full table below chart
            with st.expander("📊 All Players", expanded=False):
                all_data = []
                for player, data in sorted_players:
                    all_data.append({
                        'Player': player,
                        display_name: format_percentage_with_sample_size(
                            data['value'], data['numerator'], data['denominator']
                        ),
                        'Rank': sorted_players.index((player, data)) + 1
                    })
                all_df = pd.DataFrame(all_data)
                st.dataframe(all_df, use_container_width=True, hide_index=True)


# Historical comparisons function removed per user request

def _display_advanced_analytics(analyzer: MatchAnalyzer, kpis: Optional[Dict[str, Any]], loader=None) -> None:
    """Display advanced analytics (LOW PRIORITY 37-42)."""
    from utils.advanced_analytics import (
        calculate_win_probability, calculate_momentum_indicators,
        generate_tactical_recommendations, analyze_timeout_effectiveness,
        analyze_substitution_impact
    )
    
    st.markdown("### 🧠 Advanced Analytics")
    
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "Win Probability", "Momentum", "Tactical Recommendations", 
        "Opponent Analysis", "Timeouts", "Substitutions"
    ])
    
    with tab1:
        st.markdown("#### 🎯 Win Probability")
        if kpis and loader:
            # Get current score from team events
            current_set = 1
            our_score = 0
            their_score = 0
            
            try:
                if hasattr(loader, 'team_events') and len(loader.team_events) > 0:
                    latest_event = loader.team_events.iloc[-1]
                    current_set = int(latest_event.get('Set', 1))
                    our_score = int(latest_event.get('Our_Score', 0))
                    their_score = int(latest_event.get('Opponent_Score', 0))
            except (ValueError, TypeError, KeyError):
                pass
            
            serving_rate = kpis.get('break_point_rate', 0.5)
            receiving_rate = kpis.get('side_out_efficiency', 0.5)
            
            win_prob = calculate_win_probability(
                our_score, their_score, serving_rate, receiving_rate, current_set
            )
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Current Score", f"{our_score} - {their_score}")
                st.metric("Set", current_set)
            with col2:
                st.metric("Win Probability", f"{win_prob:.1%}")
                if win_prob > 0.6:
                    st.success("🎉 High probability of winning!")
                elif win_prob < 0.4:
                    st.warning("⚠️ Need to improve performance")
                else:
                    st.info("⚖️ Close match")
        else:
            st.info("Win probability calculation requires current score data")
    
    with tab2:
        st.markdown("#### ⚡ Momentum Indicators")
        momentum = calculate_momentum_indicators(analyzer.match_data, loader)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Longest Winning Streak", momentum.get('longest_winning_streak', 0))
            st.metric("Current Streak", f"{momentum.get('current_streak', 0)} ({momentum.get('current_streak_type', 'N/A')})")
        with col2:
            st.metric("Longest Losing Streak", momentum.get('longest_losing_streak', 0))
            st.metric("Runs of 3+ Points", momentum.get('runs_of_3_plus', 0))
        with col3:
            if momentum.get('longest_winning_streak', 0) >= 5:
                st.success("🔥 Strong momentum!")
            elif momentum.get('longest_losing_streak', 0) >= 5:
                st.warning("⚠️ Struggling with momentum")
            else:
                st.info("📊 Momentum analysis available")
    
    with tab3:
        st.markdown("#### 💡 Tactical Recommendations")
        if kpis:
            recommendations = generate_tactical_recommendations(analyzer, kpis, loader)
            
            if recommendations:
                for rec in recommendations:
                    priority_color = {
                        'high': '🔴',
                        'medium': '🟡',
                        'low': '🟢'
                    }
                    with st.expander(f"{priority_color.get(rec['priority'], '⚪')} {rec['title']}", expanded=True):
                        st.write(rec['message'])
            else:
                st.success("✅ All KPIs are performing well! No major recommendations.")
        else:
            st.info("Tactical recommendations require KPI data")
    
    with tab4:
        st.markdown("#### 🎯 Opponent Analysis")
        st.info("Opponent analysis requires opponent-specific data. This feature will be enhanced when opponent data is available in the event tracker.")
        
        # Placeholder for future opponent analysis
        if kpis:
            st.write("**Current Team Performance:**")
            st.write(f"- Attack Kill %: {format_percentage(kpis.get('attack_kill_pct', 0))}")
            st.write(f"- Serve In-Rate: {format_percentage(kpis.get('serve_in_rate', 0))}")
            st.write(f"- Reception Quality: {format_percentage(kpis.get('reception_quality', 0))}")
    
    with tab5:
        st.markdown("#### ⏱️ Timeout Effectiveness")
        timeout_analysis = analyze_timeout_effectiveness(loader)
        st.info(timeout_analysis.get('message', 'Timeout data not available'))
        # Future: Add timeout tracking in event tracker
    
    with tab6:
        st.markdown("#### 🔄 Substitution Impact")
        sub_analysis = analyze_substitution_impact(loader)
        st.info(sub_analysis.get('message', 'Substitution data not available'))
        # Future: Add substitution tracking in event tracker


def _display_insights_section(analyzer: MatchAnalyzer, team_stats: Dict[str, Any], 
                              targets: Dict[str, Any], loader=None) -> None:
    """Display insights and recommendations section."""
    from ui.insights import generate_coach_insights, display_coach_insights_section
    insights = generate_coach_insights(analyzer, team_stats, targets, loader)
    display_coach_insights_section(insights, team_stats, targets, loader)


def _display_data_completeness(loader) -> None:
    """CRITICAL PRIORITY 3: Display data completeness prominently."""
    if loader is None or not hasattr(loader, 'data_completeness'):
        return
    
    completeness = loader.data_completeness
    
    # Calculate overall completeness
    ind_total = completeness.get('individual_events', {}).get('total', 0)
    ind_valid = completeness.get('individual_events', {}).get('valid', 0)
    team_total = completeness.get('team_events', {}).get('total', 0)
    team_valid = completeness.get('team_events', {}).get('valid', 0)
    
    # Calculate percentages
    ind_pct = (ind_valid / ind_total * 100) if ind_total > 0 else 0.0
    team_pct = (team_valid / team_total * 100) if team_total > 0 else 0.0
    
    overall_pct = ((ind_valid + team_valid) / (ind_total + team_total) * 100) if (ind_total + team_total) > 0 else 0.0
    
    # Determine quality level
    if overall_pct >= 95:
        quality_level = "Good"
        quality_color = "🟢"
    elif overall_pct >= 85:
        quality_level = "Fair"
        quality_color = "🟡"
    else:
        quality_level = "Poor"
        quality_color = "🔴"
    
    # Display completeness banner
    st.markdown("### 📊 Data Quality & Completeness")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Overall Quality", f"{quality_color} {quality_level}", f"{overall_pct:.1f}%")
    
    with col2:
        st.metric("Individual Events", f"{ind_valid}/{ind_total}", f"{ind_pct:.1f}%")
    
    with col3:
        st.metric("Team Events", f"{team_valid}/{team_total}", f"{team_pct:.1f}%")
    
    with col4:
        missing_point_won = completeness.get('team_events', {}).get('missing_point_won', 0)
        invalid_point_won = completeness.get('team_events', {}).get('invalid_point_won', 0)
        total_issues = missing_point_won + invalid_point_won
        if total_issues > 0:
            st.metric("Data Issues", total_issues, f"{missing_point_won} missing, {invalid_point_won} invalid")
        else:
            st.metric("Data Issues", "0", "✅ None")
    
    # Warning banner if completeness is low
    if overall_pct < 95:
        st.warning(f"⚠️ Data completeness is {overall_pct:.1f}%. Some metrics may be less reliable. "
                  f"Please review your data file for missing or invalid entries.")
    
    # Detailed breakdown in expandable section
    with st.expander("📋 Detailed Data Completeness Breakdown"):
        st.markdown("#### Individual Events")
        ind_data = completeness.get('individual_events', {})
        st.write(f"- **Total Events:** {ind_data.get('total', 0)}")
        st.write(f"- **Valid Events:** {ind_data.get('valid', 0)}")
        st.write(f"- **Invalid Events:** {ind_data.get('invalid', 0)}")
        
        st.markdown("#### Team Events")
        team_data = completeness.get('team_events', {})
        st.write(f"- **Total Events:** {team_data.get('total', 0)}")
        st.write(f"- **Valid Events:** {team_data.get('valid', 0)}")
        st.write(f"- **Invalid Events:** {team_data.get('invalid', 0)}")
        st.write(f"- **Missing Point Won:** {team_data.get('missing_point_won', 0)}")
        st.write(f"- **Invalid Point Won:** {team_data.get('invalid_point_won', 0)}")
        
        if loader and hasattr(loader, 'validation_errors') and loader.validation_errors:
            st.markdown("#### Validation Errors")
            for error in loader.validation_errors[:10]:  # Show first 10
                st.error(error)
            if len(loader.validation_errors) > 10:
                st.info(f"... and {len(loader.validation_errors) - 10} more errors")
    
    st.markdown("---")


def _display_navigation_ctas() -> None:
    """HIGH PRIORITY 6: Display navigation CTAs in Team Overview."""
    st.markdown("### 🔗 Navigate to Other Views")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("👥 View Player Analysis", key="nav_to_player_analysis", use_container_width=True):
            st.session_state['navigation_target'] = 'Player Analysis'
            st.rerun()
    
    with col2:
        if st.button("🏆 View Player Comparison", key="nav_to_comparison", use_container_width=True):
            st.session_state['navigation_target'] = 'Player Comparison'
            st.rerun()
    
    st.markdown("---")


def _display_export_options(analyzer, kpis, loader) -> None:
    """MEDIUM PRIORITY 14: Display export options for Team Overview."""
    st.markdown("### 📥 Export Team Overview")
    
    from utils.export_utils import export_to_excel
    from datetime import datetime
    excel_data = export_to_excel(analyzer, kpis, loader)
    st.download_button(
        label="📊 Export to Excel",
        data=excel_data,
        file_name=f"team_overview_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        help="Export team overview data to Excel"
    )
    
    st.markdown("---")

