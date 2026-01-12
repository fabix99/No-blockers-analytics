"""
Serving performance chart generation module.

Provides charts for serve analysis including:
- Serve Performance by Set (donut charts)
- Ace Rate distribution
- Serve error analysis
"""
from typing import List, Optional
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from config import OUTCOME_COLORS, CHART_HEIGHTS
from charts.utils import apply_beautiful_theme, plotly_config


def get_played_sets(df: pd.DataFrame, loader=None) -> List[int]:
    """Get list of sets that were actually played."""
    from charts.team_charts import get_played_sets as _get_played_sets
    return _get_played_sets(df, loader)


def create_serving_performance_charts(df: pd.DataFrame, loader=None) -> None:
    """Create all serving performance charts.
    
    Includes:
    - Serve Performance by Set (4 donut charts: All Sets + one per set)
    
    Args:
        df: Match dataframe
        loader: Optional loader instance
    """
    st.markdown("#### Serve Performance by Set")
    played_sets = get_played_sets(df, loader)
    
    # Fixed order for consistent legend: Aces, Good, Errors
    serve_order = ['Aces', 'Good', 'Errors']
    serve_color_map = {
        'Aces': OUTCOME_COLORS['ace'],
        'Good': OUTCOME_COLORS['good'],
        'Errors': OUTCOME_COLORS['error']
    }
    
    # Create set selector
    set_options = ['All Sets'] + [f'Set {s}' for s in played_sets]
    selected_set = st.selectbox("Select Set", set_options, key="serving_set_selector")
    
    # Determine which data to show
    if selected_set == 'All Sets':
        filtered_df = df
        title = "All Sets"
        key_suffix = "all"
    else:
        set_num = int(selected_set.split()[-1])
        filtered_df = df[df['set_number'] == set_num]
        title = f"Set {set_num}"
        key_suffix = f"set_{set_num}"
    
    # Calculate serving data
    serves = filtered_df[filtered_df['action'] == 'serve']
    aces = len(serves[serves['outcome'] == 'ace'])
    good = len(serves[serves['outcome'] == 'good'])
    errors = len(serves[serves['outcome'] == 'error'])
    total = aces + good + errors
    
    # Display the chart
    if total > 0:
        _create_serve_donut_chart(
            {'Aces': aces, 'Good': good, 'Errors': errors},
            serve_order, serve_color_map, title, total, 
            f"serve_donut_{key_suffix}"
        )
    else:
        st.info("No serve data available")


def _create_serve_donut_chart(serve_data: dict, serve_order: list, 
                               color_map: dict, title: str, total: int, key: str) -> None:
    """Create a single serve donut chart.
    
    Args:
        serve_data: Dict with serve counts by type
        serve_order: Order of serve types for legend
        color_map: Color mapping for serve types
        title: Chart title
        total: Total number of serves
        key: Unique Streamlit key
    """
    if total == 0:
        st.info("No serve data available")
        return
    
    labels = []
    values = []
    colors = []
    
    for serve_type in serve_order:
        count = serve_data.get(serve_type, 0)
        if count > 0:
            labels.append(serve_type)
            values.append(count)
            colors.append(color_map[serve_type])
    
    if not labels:
        st.info("No serve data available")
        return
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=colors, line=dict(color='white', width=2)),
        textinfo='percent+label',
        textfont=dict(size=16, color='#050d76', family='Inter, sans-serif'),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
    )])
    
    fig.update_layout(
        title=dict(text=f"{title} (n={total})", font=dict(size=18)),
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=-0.15,
            xanchor="center",
            x=0.5,
            font=dict(size=14)
        ),
        margin=dict(l=20, r=20, t=60, b=60),
        font=dict(family='Inter, sans-serif', size=14, color='#050d76')
    )
    
    fig = apply_beautiful_theme(fig, f"{title} Serve Performance")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=key)

