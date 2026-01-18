"""
Serve and Reception performance chart generation module.

Provides combined charts for serve and reception analysis including:
- Reception Quality Distribution by Set
- Serve Performance by Set
"""
from typing import List, Dict, Any, Optional
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from config import OUTCOME_COLORS, CHART_HEIGHTS
from charts.utils import apply_beautiful_theme, plotly_config


def get_played_sets(df: pd.DataFrame, loader=None) -> List[int]:
    """Get list of sets that were actually played."""
    from charts.team_charts import get_played_sets as _get_played_sets
    return _get_played_sets(df, loader)


def create_serve_reception_performance_charts(df: pd.DataFrame, loader=None) -> None:
    """Create all serve and reception performance charts.
    
    Includes:
    - Reception Quality Distribution by Set (donut charts)
    - Serve Performance by Set (donut charts)
    
    Args:
        df: Match dataframe
        loader: Optional loader instance
    """
    played_sets = get_played_sets(df, loader)
    
    # Shared set selector
    set_options = ['All Sets'] + [f'Set {s}' for s in played_sets]
    selected_set = st.selectbox("Select Set", set_options, key="serve_reception_set_selector")
    
    # Display both charts side by side
    col1, col2 = st.columns(2)
    
    with col1:
        _create_reception_charts(df, played_sets, loader, selected_set)
    
    with col2:
        _create_serving_charts(df, played_sets, loader, selected_set)


def _create_reception_charts(df: pd.DataFrame, played_sets: List[int], loader=None, selected_set: str = None) -> None:
    """Create reception quality distribution charts with set selector."""
    
    # Fixed order for consistent legend: Perfect, Good, Poor, Error
    reception_order = ['Perfect', 'Good', 'Poor', 'Error']
    reception_color_map = {
        'Perfect': OUTCOME_COLORS.get('perfect', '#28A745'),
        'Good': OUTCOME_COLORS['good'],
        'Poor': OUTCOME_COLORS.get('poor', '#FFC107'),
        'Error': OUTCOME_COLORS['error']
    }
    
    # Use provided selected_set or default to 'All Sets'
    if selected_set is None:
        set_options = ['All Sets'] + [f'Set {s}' for s in played_sets]
        selected_set = st.selectbox("Select Set", set_options, key="reception_set_selector")
    
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
    
    # Calculate reception data - separate all categories
    receptions = filtered_df[filtered_df['action'] == 'receive']
    perfect = len(receptions[receptions['outcome'] == 'perfect'])
    good = len(receptions[receptions['outcome'] == 'good'])
    poor = len(receptions[receptions['outcome'] == 'poor'])
    error = len(receptions[receptions['outcome'].isin(['error', 'ace'])])
    total = perfect + good + poor + error
    
    # Display the chart
    if total > 0:
        _create_reception_donut_chart(
            {'Perfect': perfect, 'Good': good, 'Poor': poor, 'Error': error},
            reception_order, reception_color_map, title, total, 
            f"reception_donut_{key_suffix}"
        )
    else:
        st.info("No reception data available")


def _create_serving_charts(df: pd.DataFrame, played_sets: List[int], loader=None, selected_set: str = None) -> None:
    """Create serving performance charts with set selector."""
    
    # Fixed order for consistent legend: Aces, Good, Errors
    serve_order = ['Aces', 'Good', 'Errors']
    serve_color_map = {
        'Aces': OUTCOME_COLORS['ace'],
        'Good': OUTCOME_COLORS['good'],
        'Errors': OUTCOME_COLORS['error']
    }
    
    # Use provided selected_set or default to 'All Sets'
    if selected_set is None:
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


def _create_reception_donut_chart(reception_data: dict, reception_order: list, 
                                   color_map: dict, title: str, total: int, key: str) -> None:
    """Create a single reception donut chart."""
    labels = []
    values = []
    colors = []
    
    for rec_type in reception_order:
        count = reception_data.get(rec_type, 0)
        if count > 0:
            labels.append(rec_type)
            values.append(count)
            colors.append(color_map[rec_type])
    
    if not labels:
        st.info("No reception data available")
        return
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=colors, line=dict(color='white', width=2)),
        textinfo='percent+label',
        textfont=dict(size=14, color='#050d76', family='Inter, sans-serif'),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>',
        domain=dict(x=[0, 1], y=[0.15, 0.95])
    )])
    
    fig = apply_beautiful_theme(fig, "", legend_position='bottom')
    
    fig.update_layout(
        title=dict(text="Reception Quality Distribution", font=dict(size=14, color='#050d76'), x=0.5, xanchor='center'),
        height=350,
        showlegend=False,
        margin=dict(l=0, r=0, t=50, b=40)
    )
    
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=key)


def _create_serve_donut_chart(serve_data: dict, serve_order: list, 
                               color_map: dict, title: str, total: int, key: str) -> None:
    """Create a single serve donut chart."""
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
        textfont=dict(size=14, color='#050d76', family='Inter, sans-serif'),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>',
        domain=dict(x=[0, 1], y=[0.15, 0.95])
    )])
    
    fig = apply_beautiful_theme(fig, "", legend_position='bottom')
    
    fig.update_layout(
        title=dict(text="Serve Performance Distribution", font=dict(size=14, color='#050d76'), x=0.5, xanchor='center'),
        height=350,
        showlegend=False,
        margin=dict(l=0, r=0, t=50, b=40)
    )
    
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=key)

