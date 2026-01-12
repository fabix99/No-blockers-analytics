"""
Reception performance chart generation module.

Provides charts for reception analysis including:
- Reception Quality Distribution by Set
- Reception by Rotation
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


def create_reception_performance_charts(df: pd.DataFrame, loader=None) -> None:
    """Create all reception performance charts.
    
    Includes:
    - Reception Quality Distribution by Set (donut charts)
    
    Args:
        df: Match dataframe
        loader: Optional loader instance
    """
    st.markdown("#### Reception Quality by Set")
    played_sets = get_played_sets(df, loader)
    
    # Fixed order for consistent legend: Good, Average, Poor
    reception_order = ['Good', 'Average', 'Poor']
    reception_color_map = {
        'Good': OUTCOME_COLORS['good'],
        'Average': OUTCOME_COLORS.get('average', '#FFC107'),
        'Poor': OUTCOME_COLORS['error']
    }
    
    # Create set selector
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
    
    # Calculate reception data
    receptions = filtered_df[filtered_df['action'] == 'receive']
    good = len(receptions[receptions['outcome'].isin(['good', 'perfect'])])
    average = len(receptions[receptions['outcome'].isin(['average', 'ok'])])
    poor = len(receptions[receptions['outcome'].isin(['poor', 'error', 'ace'])])
    total = good + average + poor
    
    # Display the chart
    if total > 0:
        _create_reception_donut_chart(
            {'Good': good, 'Average': average, 'Poor': poor},
            reception_order, reception_color_map, title, total, 
            f"reception_donut_{key_suffix}"
        )
    else:
        st.info("No reception data available")


def _create_reception_donut_chart(reception_data: dict, reception_order: list, 
                                   color_map: dict, title: str, total: int, key: str) -> None:
    """Create a single reception donut chart.
    
    Args:
        reception_data: Dict with reception counts by quality
        reception_order: Order of reception qualities for legend
        color_map: Color mapping for reception qualities
        title: Chart title
        total: Total number of receptions
        key: Unique Streamlit key
    """
    if total == 0:
        st.info("No reception data available")
        return
    
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
    
    fig = apply_beautiful_theme(fig, f"{title} Reception Quality")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=key)

