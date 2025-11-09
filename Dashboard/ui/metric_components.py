"""
Reusable UI Components for the Dashboard.
Extracted from streamlit_dashboard.py for better maintainability.
"""
from typing import Optional, Dict, Any
import streamlit as st
from utils.formatters import get_performance_color


def render_metric_card(
    label: str,
    value: float,
    targets: Dict[str, float],
    formula: str,
    info_key: str,
    kpis: Optional[Dict[str, Any]] = None,
    kpi_key: Optional[str] = None,
    team_stats: Optional[Dict[str, Any]] = None,
    fallback_key: Optional[str] = None,
    is_percentage: bool = True,
    lower_is_better: bool = False
) -> None:
    """Render a metric card with label, value, delta, and info button.
    
    Args:
        label: Metric label (e.g., "Serving Point Rate")
        value: Metric value (0-1 for percentages, or raw number)
        targets: Target dictionary with 'min', 'max', 'optimal'
        formula: Formula description for help text
        info_key: Unique key for info button and session state
        kpis: Optional KPIs dictionary from loader
        kpi_key: Optional key to get value from kpis dict
        team_stats: Optional team stats dictionary
        fallback_key: Optional key to get value from team_stats if kpis not available
        is_percentage: Whether value is a percentage (0-1)
        lower_is_better: If True, lower values are better
    """
    # Get value from kpis or team_stats or use provided value
    if kpis and kpi_key and kpi_key in kpis:
        metric_value = kpis[kpi_key]
    elif team_stats and fallback_key and fallback_key in team_stats:
        metric_value = team_stats[fallback_key]
    else:
        metric_value = value
    
    # Handle None values
    if metric_value is None:
        metric_value = value
    
    # Get performance color
    target_optimal = targets.get('optimal', (targets.get('min', 0) + targets.get('max', 0)) / 2)
    metric_color = get_performance_color(metric_value, targets['min'], targets['max'], target_optimal)
    
    # Create label with inline info icon
    label_col, icon_col, metric_col = st.columns([12, 1, 0.1], gap="small")
    with label_col:
        st.markdown(f'**{label} {metric_color}**', unsafe_allow_html=True)
    with icon_col:
        if st.button("ℹ️", key=f"info_{info_key}_btn", help="Show definition", use_container_width=False, type="secondary"):
            st.session_state[f'show_info_{info_key}'] = not st.session_state.get(f'show_info_{info_key}', False)
    
    # Calculate delta vs target
    delta_vs_target = metric_value - target_optimal
    if lower_is_better:
        delta_color = "normal" if metric_value <= target_optimal else "inverse"
    else:
        delta_color = "normal" if metric_value >= target_optimal else "inverse"
    
    delta_label = f"{delta_vs_target:+.1%} vs target ({target_optimal:.0%})" if is_percentage else f"{delta_vs_target:+.1f} vs target ({target_optimal:.1f})"
    
    # Format display value
    display_value = f"{metric_value:.1%}" if is_percentage else f"{metric_value:.1f}"
    
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


def render_match_banner(loader: Optional[Any], opponent: str) -> None:
    """Render match result banner.
    
    Args:
        loader: Optional EventTrackerLoader instance
        opponent: Opponent team name
    """
    if loader is not None and hasattr(loader, 'team_data') and loader.team_data:
        import performance_tracker as pt
        set_results = pt.compute_set_results_from_loader(loader) if hasattr(pt, 'compute_set_results_from_loader') else []
        summary = pt.get_match_summary(set_results) if hasattr(pt, 'get_match_summary') else {'label': 'No sets', 'outcome': 'N/A'}
        
        banner_color = "#e6ffed" if summary['outcome'] == 'Win' else ("#ffecec" if summary['outcome'] == 'Loss' else "#f5f5f5")
        st.markdown(f"""
        <div style="padding:14px 18px;border:2px solid #050d76;border-radius:12px;background:{banner_color};margin-bottom:12px;">
            <div style="font-size:20px;font-weight:700;color:#050d76;">Match Result: {summary['label']}</div>
            <div style="color:#050d76;opacity:0.85;margin-top:4px;">vs {opponent}</div>
        </div>
        """, unsafe_allow_html=True)

