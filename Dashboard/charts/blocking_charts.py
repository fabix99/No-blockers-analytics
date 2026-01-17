"""
Blocking performance chart generation module.

Provides charts for block analysis including:
- Block Performance by Set (donut charts)
- Block kill/touch distribution
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


def create_blocking_performance_charts(df: pd.DataFrame, loader=None) -> None:
    """Create all blocking performance charts.
    
    Includes:
    - Block Performance Distribution (donut chart)
    - Block Kill % by Set (trend chart)
    Both displayed side-by-side with a shared set selector.
    
    Args:
        df: Match dataframe
        loader: Optional loader instance
    """
    played_sets = get_played_sets(df, loader)
    
    # Fixed order for consistent legend: Kills, Touches, Block - No Kill, No Touch, Errors
    block_order = ['Kills', 'Touches', 'Block - No Kill', 'No Touch', 'Errors']
    block_color_map = {
        'Kills': OUTCOME_COLORS['kill'],
        'Touches': OUTCOME_COLORS.get('touch', '#FFC107'),
        'Block - No Kill': OUTCOME_COLORS.get('block_no_kill', '#FF9800'),
        'No Touch': OUTCOME_COLORS.get('no_touch', '#999999'),
        'Errors': OUTCOME_COLORS['error']
    }
    
    # Shared set selector
    set_options = ['All Sets'] + [f'Set {s}' for s in played_sets]
    selected_set = st.selectbox("Select Set", set_options, key="blocking_set_selector")
    
    # Display both charts side by side
    col1, col2 = st.columns(2)
    
    with col1:
        _create_block_distribution_chart(df, played_sets, loader, selected_set, block_order, block_color_map)
    
    with col2:
        _create_block_kill_trend_chart(df, played_sets, loader, selected_set)


def _create_block_distribution_chart(df: pd.DataFrame, played_sets: List[int], loader=None, 
                                     selected_set: str = None, block_order: List[str] = None,
                                     block_color_map: dict = None) -> None:
    """Create block performance distribution chart with set selector."""
    
    # Determine which data to show
    if selected_set == 'All Sets':
        filtered_df = df
        key_suffix = "all"
    else:
        set_num = int(selected_set.split()[-1])
        filtered_df = df[df['set_number'] == set_num]
        key_suffix = f"set_{set_num}"
    
    # Calculate blocking data
    blocks = filtered_df[filtered_df['action'] == 'block']
    kills = len(blocks[blocks['outcome'] == 'kill'])
    touches = len(blocks[blocks['outcome'] == 'touch'])
    block_no_kill = len(blocks[blocks['outcome'] == 'block_no_kill'])
    no_touch = len(blocks[blocks['outcome'] == 'no_touch'])
    errors = len(blocks[blocks['outcome'] == 'error'])
    total = kills + touches + block_no_kill + no_touch + errors
    
    # Display the chart
    if total > 0:
        _create_block_donut_chart(
            {'Kills': kills, 'Touches': touches, 'Block - No Kill': block_no_kill, 'No Touch': no_touch, 'Errors': errors},
            block_order, block_color_map, total, 
            f"block_donut_{key_suffix}"
        )
    else:
        st.info("No block data available")


def _create_block_kill_trend_chart(df: pd.DataFrame, played_sets: List[int], loader=None, 
                                    selected_set: str = None) -> None:
    """Create block kill % trend chart across sets with improved styling."""
    
    # Get block kill % by set
    if loader and hasattr(loader, 'player_data_by_set'):
        from utils.breakdown_helpers import get_kpi_by_set
        block_kill_by_set = get_kpi_by_set(loader, 'block_kill_pct')
    else:
        # Fallback: calculate from dataframe
        block_kill_by_set = {}
        for set_num in played_sets:
            set_blocks = df[df['action'] == 'block']
            set_blocks = set_blocks[set_blocks['set_number'] == set_num]
            block_kills = len(set_blocks[set_blocks['outcome'] == 'kill'])
            block_total = len(set_blocks)
            if block_total > 0:
                block_kill_by_set[set_num] = block_kills / block_total
            else:
                block_kill_by_set[set_num] = 0.0
    
    if not block_kill_by_set:
        st.info("No block data available")
        return
    
    # Show all sets in trend
    sets_to_show = sorted(block_kill_by_set.keys())
    
    if not sets_to_show:
        st.info("No block data available")
        return
    
    # Create line chart with improved styling
    fig = go.Figure()
    
    # Use brand blue color for consistency
    block_color = OUTCOME_COLORS.get('kill', '#00C853')  # Green for block kills
    
    fig.add_trace(go.Scatter(
        x=[f"Set {s}" for s in sets_to_show],
        y=[block_kill_by_set[s] * 100 for s in sets_to_show],
        mode='lines+markers',
        name='Block Kill %',
        line=dict(color=block_color, width=3.5, shape='spline'),
        marker=dict(size=12, color=block_color, line=dict(width=2, color='white')),
        fill='tozeroy',
        fillcolor=f'rgba(0, 200, 83, 0.12)',
        hovertemplate='<b>Set %{x}</b><br>Block Kill %: %{y:.1f}%<extra></extra>'
    ))
    
    fig = apply_beautiful_theme(fig, "", legend_position='bottom')
    
    fig.update_layout(
        title=dict(text="Block Kill % by Set", font=dict(size=14, color='#050d76'), x=0.5, xanchor='center'),
        xaxis_title="",
        yaxis_title="",
        height=350,
        margin=dict(l=20, r=20, t=50, b=40),
        yaxis=dict(
            range=[0, max(100, max([block_kill_by_set[s] * 100 for s in sets_to_show]) * 1.1)],
            tickfont=dict(size=12, color='#666'),
            tickformat='.0f',
            gridcolor='rgba(0,0,0,0.05)',
            gridwidth=1,
            showline=False,
            zeroline=False
        ),
        xaxis=dict(
            tickfont=dict(size=12, color='#666'),
            showline=False,
            gridcolor='rgba(0,0,0,0.05)',
            gridwidth=1
        ),
        showlegend=False,
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)'
    )
    
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"block_kill_trend_{selected_set}")


def _create_block_donut_chart(block_data: dict, block_order: list, 
                               color_map: dict, total: int, key: str) -> None:
    """Create a single block donut chart."""
    labels = []
    values = []
    colors = []
    
    for block_type in block_order:
        count = block_data.get(block_type, 0)
        if count > 0:
            labels.append(block_type)
            values.append(count)
            colors.append(color_map[block_type])
    
    if not labels:
        st.info("No block data available")
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
        title=dict(text="Block Performance Distribution", font=dict(size=14, color='#050d76'), x=0.5, xanchor='center'),
        height=350,
        showlegend=False,
        margin=dict(l=0, r=0, t=50, b=40)
    )
    
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=key)

