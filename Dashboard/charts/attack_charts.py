"""
Attack performance chart generation module.

Provides charts for attack analysis including:
- Attack Type Distribution (Normal, Tip, After Block)
- Attack Quality Distribution by Set
"""
from typing import List, Dict, Any, Optional
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from config import OUTCOME_COLORS, CHART_HEIGHTS, ATTACK_TYPE_COLORS
from charts.utils import apply_beautiful_theme, plotly_config


def get_played_sets(df: pd.DataFrame, loader=None) -> List[int]:
    """Get list of sets that were actually played."""
    from charts.team_charts import get_played_sets as _get_played_sets
    return _get_played_sets(df, loader)


def create_attacking_performance_charts(df: pd.DataFrame, loader=None) -> None:
    """Create all attacking performance charts.
    
    Includes:
    - Attack Type Distribution (Normal, Tip, After Block)
    - Attack Quality Distribution by Set (Kills, Defended, Errors)
    
    Args:
        df: Match dataframe
        loader: Optional loader instance
    """
    played_sets = get_played_sets(df, loader)
    
    # Shared set selector
    set_options = ['All Sets'] + [f'Set {s}' for s in played_sets]
    selected_set = st.selectbox("Select Set", set_options, key="attack_charts_set_selector")
    
    # Display both charts side by side
    col1, col2 = st.columns(2)
    
    with col1:
        _create_attack_type_charts(df, played_sets, loader, selected_set)
    
    with col2:
        _create_attack_quality_charts(df, played_sets, loader, selected_set)


def _create_attack_type_charts(df: pd.DataFrame, played_sets: List[int], loader=None, selected_set: str = None) -> None:
    """Create attack type distribution charts with set selector."""
    from utils.breakdown_helpers import get_attack_breakdown_by_type
    
    # Fixed order for consistent legend
    attack_type_order = ['Normal', 'Tip']
    attack_type_color_map = {
        'Normal': ATTACK_TYPE_COLORS['normal'],
        'Tip': ATTACK_TYPE_COLORS['tip']
    }
    
    # Use provided selected_set or default to 'All Sets'
    if selected_set is None:
        set_options = ['All Sets'] + [f'Set {s}' for s in played_sets]
        selected_set = st.selectbox("Select Set", set_options, key="attack_type_set_selector")
    
    # Determine which data to show
    if selected_set == 'All Sets':
        breakdown = get_attack_breakdown_by_type(df, loader)
        title = "All Sets"
        key_suffix = "all"
    else:
        set_num = int(selected_set.split()[-1])
        filtered_df = df[df['set_number'] == set_num]
        breakdown = get_attack_breakdown_by_type(filtered_df, loader)
        title = f"Set {set_num}"
        key_suffix = f"set_{set_num}"
    
    # Display the chart
    if breakdown:
        normal_total = breakdown['normal']['total']
        tip_total = breakdown['tip']['total']
        total_attacks = normal_total + tip_total
        
        if total_attacks > 0:
            _create_attack_type_donut(
                {'Normal': normal_total, 'Tip': tip_total},
                attack_type_order, attack_type_color_map, title, total_attacks,
                f"attack_type_donut_{key_suffix}"
            )
        else:
            st.info("No attack data available")
    else:
        st.info("No attack data available")


def _create_attack_quality_charts(df: pd.DataFrame, played_sets: List[int], loader=None, selected_set: str = None) -> None:
    """Create attack quality distribution charts with set selector."""
    
    # Fixed order for consistent legend
    quality_order = ['Kills', 'Defended', 'Errors']
    quality_color_map = {
        'Kills': OUTCOME_COLORS['kill'],  # Green for kills
        'Defended': '#4A90E2',  # Blue for defended (better contrast than light blue)
        'Errors': OUTCOME_COLORS['error']  # Red for errors
    }
    
    # Use provided selected_set or default to 'All Sets'
    if selected_set is None:
        set_options = ['All Sets'] + [f'Set {s}' for s in played_sets]
        selected_set = st.selectbox("Select Set", set_options, key="attack_quality_set_selector")
    
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
    
    # Calculate attack quality data
    attacks = filtered_df[filtered_df['action'] == 'attack']
    kills = len(attacks[attacks['outcome'] == 'kill'])
    defended = len(attacks[attacks['outcome'].isin(['defended', 'good'])])
    errors = len(attacks[attacks['outcome'].isin(['blocked', 'out', 'net'])])  # error removed
    total = kills + defended + errors
    
    # Display the chart
    if total > 0:
        _create_attack_quality_donut(
            {'Kills': kills, 'Defended': defended, 'Errors': errors},
            quality_order, quality_color_map, title, total,
            f"attack_quality_donut_{key_suffix}"
        )
    else:
        st.info("No attack data available")


def _create_attack_type_donut(attack_data: dict, order: list, color_map: dict, 
                               title: str, total: int, key: str) -> None:
    """Create attack type donut chart."""
    labels = []
    values = []
    colors = []
    
    for attack_type in order:
        count = attack_data.get(attack_type, 0)
        if count > 0:
            labels.append(attack_type)
            values.append(count)
            colors.append(color_map[attack_type])
    
    if not labels:
        st.info("No data available")
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
        title=dict(text="Attack Type Distribution", font=dict(size=14, color='#050d76'), x=0.5, xanchor='center'),
        height=350,
        showlegend=False,
        margin=dict(l=0, r=0, t=50, b=40)
    )
    
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=key)


def _create_attack_quality_donut(quality_data: dict, order: list, color_map: dict, 
                                  title: str, total: int, key: str) -> None:
    """Create attack quality donut chart with matching size to attack type chart."""
    labels = []
    values = []
    colors = []
    
    for quality_type in order:
        count = quality_data.get(quality_type, 0)
        if count > 0:
            labels.append(quality_type)
            values.append(count)
            colors.append(color_map[quality_type])
    
    if not labels:
        st.info("No data available")
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
        title=dict(text="Attack Quality Distribution", font=dict(size=14, color='#050d76'), x=0.5, xanchor='center'),
        height=350,
        showlegend=False,
        margin=dict(l=0, r=0, t=50, b=40)
    )
    
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=key)

