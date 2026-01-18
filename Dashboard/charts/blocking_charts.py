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
    
    # Fixed order for consistent legend: Kills, Block - No Kill, Touches, No Touch, Errors
    # Block - No Kill is better than Touch (ball went back but didn't finish point vs just touched)
    block_order = ['Kills', 'Block - No Kill', 'Touches', 'No Touch', 'Errors']
    block_color_map = {
        'Kills': OUTCOME_COLORS['kill'],
        'Block - No Kill': OUTCOME_COLORS['good'],  # Light green (better outcome)
        'Touches': OUTCOME_COLORS.get('block_no_kill', '#FF9800'),  # Orange
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
    """Create stacked bar chart showing all block outcomes by set with same color scheme as reception chart."""
    
    # Get block outcomes by set - similar to reception quality distribution
    block_details_by_set = {}
    sets_to_process = played_sets
    
    # Filter sets if specific set selected
    if selected_set and selected_set != 'All Sets':
        set_num = int(selected_set.split()[-1])
        sets_to_process = [set_num] if set_num in played_sets else []
    
    for set_num in sets_to_process:
        set_df = df[df['set_number'] == set_num]
        blocks = set_df[set_df['action'] == 'block']
        
        # Map block outcomes - separate all categories like the donut chart
        block_details_by_set[set_num] = {
            'kill': len(blocks[blocks['outcome'] == 'kill']),
            'touch': len(blocks[blocks['outcome'] == 'touch']),
            'block_no_kill': len(blocks[blocks['outcome'] == 'block_no_kill']),
            'no_touch': len(blocks[blocks['outcome'] == 'no_touch']),
            'error': len(blocks[blocks['outcome'] == 'error'])
        }
    
    if not block_details_by_set or not any(sum(v.values()) > 0 for v in block_details_by_set.values()):
        st.info("No block data available")
        return
    
    # Create stacked bar chart
    fig = go.Figure()
    
    # Use same color scheme as donut chart - must match exactly
    # Kill
    fig.add_trace(go.Bar(
        x=[f"Set {s}" for s in sets_to_process],
        y=[block_details_by_set.get(s, {}).get('kill', 0) for s in sets_to_process],
        name='Kills',
        marker_color=OUTCOME_COLORS['kill'],  # Match donut chart
        text=[block_details_by_set.get(s, {}).get('kill', 0) for s in sets_to_process],
        textposition='inside',
        textfont=dict(size=9, color='#FFFFFF')
    ))
    
    # Block - No Kill → Light green (better than Touch - ball went back but didn't finish point)
    fig.add_trace(go.Bar(
        x=[f"Set {s}" for s in sets_to_process],
        y=[block_details_by_set.get(s, {}).get('block_no_kill', 0) for s in sets_to_process],
        name='Block - No Kill',
        marker_color=OUTCOME_COLORS['good'],  # Light green - match donut chart
        text=[block_details_by_set.get(s, {}).get('block_no_kill', 0) for s in sets_to_process],
        textposition='inside',
        textfont=dict(size=9, color='#FFFFFF')
    ))
    
    # Touch → Orange
    fig.add_trace(go.Bar(
        x=[f"Set {s}" for s in sets_to_process],
        y=[block_details_by_set.get(s, {}).get('touch', 0) for s in sets_to_process],
        name='Touches',
        marker_color=OUTCOME_COLORS.get('block_no_kill', '#FF9800'),  # Orange - match donut chart
        text=[block_details_by_set.get(s, {}).get('touch', 0) for s in sets_to_process],
        textposition='inside',
        textfont=dict(size=9, color='#FFFFFF')
    ))
    
    # No Touch → Gray
    fig.add_trace(go.Bar(
        x=[f"Set {s}" for s in sets_to_process],
        y=[block_details_by_set.get(s, {}).get('no_touch', 0) for s in sets_to_process],
        name='No Touch',
        marker_color=OUTCOME_COLORS.get('no_touch', '#999999'),  # Gray - match donut chart
        text=[block_details_by_set.get(s, {}).get('no_touch', 0) for s in sets_to_process],
        textposition='inside',
        textfont=dict(size=9, color='#FFFFFF')
    ))
    
    # Error → Red
    fig.add_trace(go.Bar(
        x=[f"Set {s}" for s in sets_to_process],
        y=[block_details_by_set.get(s, {}).get('error', 0) for s in sets_to_process],
        name='Errors',
        marker_color=OUTCOME_COLORS['error'],  # Red - match donut chart
        text=[block_details_by_set.get(s, {}).get('error', 0) for s in sets_to_process],
        textposition='inside',
        textfont=dict(size=9, color='#FFFFFF')
    ))
    
    # Calculate total block attempts for sample size
    total_block_attempts = sum(sum(block_details_by_set.get(s, {}).values()) for s in sets_to_process)
    
    fig.update_layout(
        title=f"Block Outcomes Distribution (n={total_block_attempts} blocks)",
        xaxis_title="Set Number",
        yaxis_title="Count",
        barmode='stack',
        xaxis=dict(dtick=1, tickfont=dict(color='#050d76')),
        yaxis=dict(tickfont=dict(color='#050d76')),
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="right", x=1.02)
    )
    fig = apply_beautiful_theme(fig, "Block Outcomes Distribution", height=350)
    # Override height and margins after theme to match donut chart height (350px)
    fig.update_layout(height=350, margin=dict(l=40, r=30, t=50, b=40))
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"block_outcomes_{selected_set}")


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
        domain=dict(x=[0, 1], y=[0, 1])
    )])
    
    fig = apply_beautiful_theme(fig, "", legend_position='bottom')
    
    fig.update_layout(
        title=dict(text="Block Performance Distribution", font=dict(size=14, color='#050d76'), x=0.5, xanchor='center'),
        height=350,
        showlegend=False,
        margin=dict(l=20, r=20, t=50, b=40),
        autosize=True
    )
    
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=key)

