"""
Team chart generation module
"""
from typing import Dict, Any, List, Optional
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from match_analyzer import MatchAnalyzer
from config import OUTCOME_COLORS, CHART_HEIGHTS
from config import CHART_COLORS
from config import ATTACK_TYPE_COLORS
from charts.utils import apply_beautiful_theme, plotly_config
from utils.helpers import filter_good_receptions, filter_good_digs, filter_block_touches


def get_played_sets(df: pd.DataFrame, loader=None) -> List[int]:
    """
    Detect which sets were actually played (have data).
    
    A set is considered "played" if:
    - It has actions/events in the dataframe (non-zero rows)
    - OR it has rally data in loader with non-zero values
    
    Args:
        df: Match dataframe
        loader: Optional ExcelMatchLoader instance
        
    Returns:
        List of set numbers that were actually played
    """
    played_sets = set()
    
    # Check dataframe for sets with actions
    if 'set_number' in df.columns and len(df) > 0:
        sets_with_data = df[df['set_number'].notna()]['set_number'].unique()
        for set_num in sets_with_data:
            set_df = df[df['set_number'] == set_num]
            # Set is played if it has any rows
            if len(set_df) > 0:
                played_sets.add(int(set_num))
    
    # Check loader for sets with rally data
    if loader is not None and hasattr(loader, 'team_data_by_rotation'):
        if loader.team_data_by_rotation is not None:
            for set_num in loader.team_data_by_rotation.keys():
                set_data = loader.team_data_by_rotation[set_num]
                # Check if this set has any rotations with non-zero rallies
                has_data = False
                for rotation_data in set_data.values():
                    serving_rallies = float(rotation_data.get('serving_rallies', 0) or 0)
                    receiving_rallies = float(rotation_data.get('receiving_rallies', 0) or 0)
                    if serving_rallies > 0 or receiving_rallies > 0:
                        has_data = True
                        break
                if has_data:
                    played_sets.add(int(set_num))
    
    return sorted(list(played_sets))


def create_match_flow_charts(analyzer: MatchAnalyzer, loader=None) -> None:
    """Create charts for Section 3: Match Flow & Momentum.
    
    Includes:
    - Point-by-Point Score Progression (3 side-by-side charts)
    - Rotation Performance Heatmap
    
    Args:
        analyzer: MatchAnalyzer instance with loaded match data
        loader: Optional ExcelMatchLoader instance for team rally data
    """
    df = analyzer.match_data
    
    # Point-by-Point Score Progression
    _create_point_by_point_progression_chart(df, loader)
    
    # Rotation Performance Heatmap
    try:
        rotation_stats = analyzer.analyze_rotation_performance()
        if rotation_stats:
            _create_rotation_heatmap(rotation_stats, analyzer, df, loader)
    except AttributeError:
        # Method might not exist, skip rotation analysis
        pass
    

def create_skill_performance_charts(analyzer: MatchAnalyzer, loader=None) -> None:
    """Create charts for Section 4: Skill Performance Analysis.
    
    Organized by skill:
    - Tactical Distribution (Attack & Reception by Position)
    - Attacking Performance
    - Reception Performance
    - Serving Performance
    - Blocking Performance
    
    Args:
        analyzer: MatchAnalyzer instance with loaded match data
        loader: Optional ExcelMatchLoader instance for team rally data
    """
    df = analyzer.match_data
    
    # Tactical Distribution: Attack & Reception by Position
    st.markdown("### 📍 Tactical Distribution")
    col1, col2 = st.columns(2)
    with col1:
        _create_attack_distribution_chart(df)
    with col2:
        _create_reception_distribution_chart(df)
    
    # Attacking Performance
    st.markdown("### 🎯 Attacking Performance")
    from charts.attack_charts import create_attacking_performance_charts
    create_attacking_performance_charts(df, loader)
    
    # Serve and Reception Performance
    st.markdown("### 🎾 Serve and Reception Performance")
    from charts.serve_reception_charts import create_serve_reception_performance_charts
    create_serve_reception_performance_charts(df, loader)
    
    # Blocking Performance
    st.markdown("### 🛡️ Blocking Performance")
    from charts.blocking_charts import create_blocking_performance_charts
    create_blocking_performance_charts(df, loader)


def create_team_charts(analyzer: MatchAnalyzer, loader=None) -> None:
    """Legacy function - kept for backward compatibility.
    
    This function is deprecated. Use create_match_flow_charts() and 
    create_skill_performance_charts() instead.
    """
    create_match_flow_charts(analyzer, loader)
    create_skill_performance_charts(analyzer, loader)


def _create_action_distribution_chart(df: pd.DataFrame) -> None:
    """Create action distribution donut chart."""
    action_counts = df['action'].value_counts()
    
    # Check if receive includes digs - if so, separate them
    # Since 'dig' and 'receive' are separate actions in VALID_ACTIONS, they should already be separate
    # But let's ensure we show them separately if both exist
    if 'receive' in action_counts.index and 'dig' in action_counts.index:
        # They're already separate, keep as is
        pass
    
    fig_actions = px.pie(
        values=action_counts.values,
        names=action_counts.index,
        title="Action Distribution",
        color_discrete_sequence=['#B8E6B8', '#B8D4E6', '#E6D4B8', '#E6B8D4', '#D4B8E6', '#B8E6D4', '#E6E6B8'],  # Soft pastels
        hole=0.4  # Creates donut chart (40% hole)
    )
    fig_actions.update_traces(
        textposition='inside',
        textinfo='percent',
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>',
        marker=dict(line=dict(color='white', width=2))
    )
    fig_actions = apply_beautiful_theme(fig_actions, "Action Distribution")
    st.plotly_chart(fig_actions, use_container_width=True, config=plotly_config, key="action_distribution")
    
    # Add note about action distribution
    dominant_action = action_counts.idxmax()
    dominant_pct = (action_counts.max() / action_counts.sum()) * 100
    if dominant_pct > 30:
        st.caption(f"💡 **Note:** {dominant_action.capitalize()} actions represent {dominant_pct:.1f}% of total actions")


def _create_outcome_distribution_chart(df: pd.DataFrame) -> None:
    """Create outcome distribution bar chart sorted by: Kill (with ace), Good, Error."""
    outcome_counts = df['outcome'].value_counts()
    
    # Combine ace with kill
    kill_count = outcome_counts.get('kill', 0)
    ace_count = outcome_counts.get('ace', 0)
    combined_kill = kill_count + ace_count
    
    # Create ordered outcome counts
    ordered_outcomes = {}
    if combined_kill > 0:
        ordered_outcomes['Kill'] = combined_kill
    if 'good' in outcome_counts.index:
        ordered_outcomes['Good'] = outcome_counts['good']
    if 'error' in outcome_counts.index:
        ordered_outcomes['Error'] = outcome_counts['error']
    
    # Add any other outcomes that aren't kill, ace, good, or error
    for outcome in outcome_counts.index:
        if outcome not in ['kill', 'ace', 'good', 'error']:
            ordered_outcomes[outcome.capitalize()] = outcome_counts[outcome]
    
    # Convert to series for plotting
    ordered_series = pd.Series(ordered_outcomes)
    
    # Color mapping: Kill=Green, Good=Yellow/Gold, Error=Red (softened pastels)
    color_map = {
        'Kill': '#90EE90',  # Soft green
        'Good': '#FFE4B5',  # Soft yellow/cream
        'Error': '#FFB6C1'  # Soft pink/red
    }
    colors = [color_map.get(outcome, CHART_COLORS['primary']) for outcome in ordered_series.index]
    
    fig_outcomes = go.Figure(data=go.Bar(
        x=ordered_series.index,
        y=ordered_series.values,
        marker_color=colors,
        text=ordered_series.values,
        textposition='outside',
        textfont=dict(size=11, color='#050d76')
    ))
    
    fig_outcomes.update_layout(
        title="Outcome Distribution",
        xaxis_title="Outcome",
        yaxis_title="Count",
        height=CHART_HEIGHTS['medium'],
        showlegend=False
    )
    fig_outcomes.update_xaxes(
        title_font=dict(color='#050d76'),
        tickfont=dict(color='#050d76')
    )
    fig_outcomes.update_yaxes(
        title_font=dict(color='#050d76'),
        tickfont=dict(color='#050d76')
    )
    fig_outcomes.update_traces(
        hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
    )
    fig_outcomes = apply_beautiful_theme(fig_outcomes, "Outcome Distribution")
    st.plotly_chart(fig_outcomes, use_container_width=True, config=plotly_config, key="outcome_distribution")


def _create_attack_distribution_chart(df: pd.DataFrame) -> None:
    """Create attack distribution by position group with volleyball court visualization."""
    # Filter only attack actions
    attacks = df[df['action'] == 'attack'].copy()
    
    if len(attacks) == 0:
        st.info("No attack data available")
        return
    
    # Map positions to position groups
    # First check if position column exists in dataframe
    if 'position' in attacks.columns:
        # Use position directly from dataframe
        def map_position_group(pos):
            if pd.isna(pos) or pos is None:
                return 'Unknown'
            pos_str = str(pos).upper()
            if pos_str.startswith('MB'):
                return 'Middle Blocker'
            elif pos_str == 'OPP':
                return 'Opposite'
            elif pos_str.startswith('OH'):
                return 'Outside'
            else:
                return 'Other'
        attacks['position_group'] = attacks['position'].apply(map_position_group)
    else:
        # Fallback: get position from player using helper function
        from utils.helpers import get_player_position
        position_groups = {}
        for player in attacks['player'].unique():
            position = get_player_position(df, player)
            if position:
                if position.startswith('MB'):
                    position_groups[player] = 'Middle Blocker'
                elif position == 'OPP':
                    position_groups[player] = 'Opposite'
                elif position.startswith('OH'):
                    position_groups[player] = 'Outside'
                else:
                    position_groups[player] = 'Other'
            else:
                position_groups[player] = 'Unknown'
        attacks['position_group'] = attacks['player'].map(position_groups)
    
    # Count attacks by position group
    attack_counts = attacks['position_group'].value_counts()
    
    # Create volleyball court diagram
    fig = go.Figure()
    
    # Court dimensions (simplified top-down view, rotated 90 degrees)
    court_width = 9  # meters (attack zone length - now horizontal)
    court_length = 18  # meters (court width - now vertical)
    
    # Outer container rectangle with net effect
    # Define container boundaries
    container_y_bottom = 0.5  # Bottom of container
    container_y_top = 8.5  # Top of container
    container_y_midpoint = (container_y_bottom + container_y_top) / 2  # Net line
    container_x_left = -court_length * 0.55
    container_x_right = court_length * 0.55
    
    # Calculate top half height for 25% border positioning
    top_half_height = container_y_top - container_y_midpoint
    border_length = top_half_height * 0.25  # 25% of top half height
    
    # Solid bottom half (court area) - BELOW the net
    fig.add_shape(
        type="rect",
        x0=container_x_left,
        y0=container_y_bottom,
        x1=container_x_right,
        y1=container_y_midpoint,
        fillcolor="rgba(235, 245, 255, 0.75)",  # Slightly deeper blue for court contrast
        line=dict(color="#050d76", width=2),
        layer="below"
    )
    
    # New transparent rectangle below court area (pole area)
    pole_area_height = court_width * 0.3  # Height of pole area
    pole_area_y_bottom = container_y_bottom - pole_area_height
    
    fig.add_shape(
        type="rect",
        x0=container_x_left,
        y0=pole_area_y_bottom,
        x1=container_x_right,
        y1=container_y_bottom,
        fillcolor="rgba(255,255,255,0)",  # Fully transparent
        line=dict(color="rgba(0,0,0,0)", width=0),  # No border on rectangle itself
        layer="below"
    )
    
    # Add left and right borders for pole area (mimicking net poles) - same color as net
    # Left pole border
    fig.add_shape(
        type="line",
        x0=container_x_left,
        y0=pole_area_y_bottom,
        x1=container_x_left,
        y1=container_y_bottom,
        line=dict(color="#050d76", width=2),  # Same color as net
        layer="below"
    )
    
    # Right pole border
    fig.add_shape(
        type="line",
        x0=container_x_right,
        y0=pole_area_y_bottom,
        x1=container_x_right,
        y1=container_y_bottom,
        line=dict(color="#050d76", width=2),  # Same color as net
        layer="below"
    )
    
    # Transparent top half (net area) - ABOVE the net
    # Slightly more visible to simulate net texture without obscuring bubbles
    fig.add_shape(
        type="rect",
        x0=container_x_left,
        y0=container_y_midpoint,
        x1=container_x_right,
        y1=container_y_top,
        fillcolor="rgba(240, 248, 255, 0.12)",  # Subtle net texture - more visible than before
        line=dict(color="rgba(0,0,0,0)", width=0),  # No border on rectangle itself
        layer="below"
    )
    
    # Add red left and right borders for top rectangle (only 25% of top half height)
    # Left border - starts at net line, goes up 25% of top half height
    fig.add_shape(
        type="line",
        x0=container_x_left,
        y0=container_y_midpoint,
        x1=container_x_left,
        y1=container_y_midpoint + border_length,
        line=dict(color="#E63946", width=2),  # Red border
        layer="below"
    )
    
    # Right border - starts at net line, goes up 25% of top half height
    fig.add_shape(
        type="line",
        x0=container_x_right,
        y0=container_y_midpoint,
        x1=container_x_right,
        y1=container_y_midpoint + border_length,
        line=dict(color="#E63946", width=2),  # Red border
        layer="below"
    )
    
    # Net line dividing the two halves (more prominent dashed line)
    fig.add_shape(
        type="line",
        x0=container_x_left,
        y0=container_y_midpoint,
        x1=container_x_right,
        y1=container_y_midpoint,
        line=dict(color="#050d76", width=3, dash="dash"),  # Thicker, clearer dash pattern
        layer="below"
    )
    
    # Attack zone positions (x, y coordinates on court)
    # Outside attacks: left side of court (negative x)
    # Middle Blocker: center (x near 0)
    # Opposite: right side (positive x)
    
    position_coords = {
        'Outside': (-court_length * 0.35, 0),
        'Middle Blocker': (0, 0),
        'Opposite': (court_length * 0.35, 0),
    }
    
    # Position colors matching team branding
    position_colors = {
        'Outside': '#4A90E2',      # Blue
        'Middle Blocker': '#50C878',  # Green
        'Opposite': '#E63946',     # Red
        'Other': '#FFB347',        # Orange
        'Unknown': '#808080'       # Gray
    }
    
    # Calculate max count for scaling bubble sizes
    max_count = attack_counts.max() if len(attack_counts) > 0 else 1
    total_attacks = attack_counts.sum()
    
    # Create circles/bubbles for each position group (ABOVE net in transparent area)
    for position_group, count in attack_counts.items():
        if position_group in position_coords:
            x, base_y = position_coords[position_group]
            # Scale bubble size based on count (min 40, max 120)
            size = max(40, min(120, (count / max_count) * 90))
            percentage = (count / total_attacks * 100) if total_attacks > 0 else 0
            
            # Bubble positioned in the transparent top half (ABOVE the net)
            # Use relative positioning for better responsiveness
            bubble_y = container_y_midpoint + court_width * 0.15  # Well above the net line
            
            fig.add_trace(go.Scatter(
                x=[x],
                y=[bubble_y],
                mode='markers+text',
                marker=dict(
                    size=size,
                    color=position_colors.get(position_group, '#808080'),
                    line=dict(color='#050d76', width=3),  # Thicker border for better visibility
                    opacity=0.85  # Higher opacity for better contrast against transparent background
                ),
                text=[f"{count}<br>{percentage:.1f}%"],
                textposition="middle center",
                textfont=dict(size=11, color='#FFFFFF', family='Arial Black'),
                name=position_group,
                showlegend=False,
                hovertemplate=f'<b>{position_group}</b><br>Attacks: {count}<br>Percentage: {percentage:.1f}%<extra></extra>'
            ))
    
    # Add position labels with background boxes (BELOW net in solid area)
    label_positions = [
        (-court_length * 0.35, "Outside"),
        (0, "Middle"),
        (court_length * 0.35, "Opposite"),
    ]
    
    for x, label in label_positions:
        # Label positioned in the solid bottom half (BELOW the net)
        # Use relative positioning for better responsiveness
        label_y = container_y_midpoint - court_width * 0.10  # Well below the net line
        
        fig.add_annotation(
            x=x,
            y=label_y,
            text=label,
            showarrow=False,
            font=dict(size=13, color='#050d76', family='Poppins'),
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor="#050d76",
            borderwidth=2,
            borderpad=4
        )
    
    # Update layout (rotated 90 degrees)
    fig.update_layout(
        title=dict(
            text="Attack Distribution by Position",
            font=dict(size=18, color='#050d76', family='Poppins'),
            x=0.5
        ),
        xaxis=dict(
            range=[container_x_left * 1.1, container_x_right * 1.1],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            title=""
        ),
        yaxis=dict(
            range=[pole_area_y_bottom - 0.5, container_y_top + 0.5],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            title="",
            scaleanchor="x",
            scaleratio=1
        ),
        height=CHART_HEIGHTS['large'],
        showlegend=False,
        paper_bgcolor='rgba(255,255,255,0)',
        plot_bgcolor='rgba(255,255,255,0.98)',
        margin=dict(l=40, r=40, t=80, b=40)
    )
    
    fig = apply_beautiful_theme(fig, "Attack Distribution by Position")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="attack_distribution_position")


def _create_reception_distribution_chart(df: pd.DataFrame) -> None:
    """Create reception distribution by position group."""
    # Filter only receive actions (reception)
    receptions = df[df['action'] == 'receive'].copy()
    
    if len(receptions) == 0:
        st.info("No reception data available")
        return
    
    # Map positions to position groups
    # First check if position column exists in dataframe
    if 'position' in receptions.columns:
        # Use position directly from dataframe
        def map_position_group(pos):
            if pd.isna(pos) or pos is None:
                return 'Unknown'
            pos_str = str(pos).upper()
            if pos_str.startswith('MB'):
                return 'Middle Blocker'
            elif pos_str == 'OPP':
                return 'Opposite'
            elif pos_str.startswith('OH'):
                return 'Outside'
            elif pos_str == 'L':
                return 'Libero'
            else:
                return 'Other'
        receptions['position_group'] = receptions['position'].apply(map_position_group)
    else:
        # Fallback: get position from player using helper function
        from utils.helpers import get_player_position
        position_groups = {}
        for player in receptions['player'].unique():
            position = get_player_position(df, player)
            if position:
                if position.startswith('MB'):
                    position_groups[player] = 'Middle Blocker'
                elif position == 'OPP':
                    position_groups[player] = 'Opposite'
                elif position.startswith('OH'):
                    position_groups[player] = 'Outside'
                elif position == 'L':
                    position_groups[player] = 'Libero'
                else:
                    position_groups[player] = 'Other'
            else:
                position_groups[player] = 'Unknown'
        receptions['position_group'] = receptions['player'].map(position_groups)
    
    # Count receptions by position group
    reception_counts = receptions['position_group'].value_counts()
    
    # Create volleyball court diagram (trapezoid - half court seen from behind)
    fig = go.Figure()
    
    # Court dimensions for trapezoid (half court view from behind)
    # Top line (net) is shorter, bottom line (back line) is wider
    court_top_width = 9  # Width at net (shorter)
    court_bottom_width = 12  # Width at back line (wider)
    court_depth = 9  # Depth of court
    
    # Center coordinates
    center_x = 0
    court_top_y = court_depth  # Top of court (net line)
    court_bottom_y = 0  # Bottom of court (back line)
    
    # Trapezoid vertices (counter-clockwise from top-left)
    # Top left, top right, bottom right, bottom left
    trapezoid_x = [
        center_x - court_top_width / 2,  # Top left
        center_x + court_top_width / 2,  # Top right
        center_x + court_bottom_width / 2,  # Bottom right
        center_x - court_bottom_width / 2,  # Bottom left
        center_x - court_top_width / 2  # Close the shape
    ]
    trapezoid_y = [
        court_top_y,  # Top left
        court_top_y,  # Top right
        court_bottom_y,  # Bottom right
        court_bottom_y,  # Bottom left
        court_top_y  # Close the shape
    ]
    
    # Draw trapezoid court background
    fig.add_trace(go.Scatter(
        x=trapezoid_x,
        y=trapezoid_y,
        fill='toself',
        fillcolor='rgba(240, 248, 255, 0.5)',
        line=dict(color='#050d76', width=2),
        mode='lines',
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Net line at top
    fig.add_shape(
        type="line",
        x0=center_x - court_top_width / 2,
        y0=court_top_y,
        x1=center_x + court_top_width / 2,
        y1=court_top_y,
        line=dict(color='#050d76', width=2, dash="dash"),
        layer="below"
    )
    
    # Position colors
    position_colors = {
        'Outside': '#4A90E2',      # Blue
        'Middle Blocker': '#50C878',  # Green
        'Opposite': '#E63946',     # Red
        'Libero': '#FFB347',       # Orange
        'Other': '#808080',        # Gray
        'Unknown': '#808080'       # Gray
    }
    
    # Calculate max count for scaling bubble sizes
    max_count = reception_counts.max() if len(reception_counts) > 0 else 1
    total_receptions = reception_counts.sum()
    
    # Position coordinates on court
    # Outside: left side
    # Libero: center
    # Middle Blocker: at the net (top)
    # Opposite: right side
    
    position_coords = {
        'Outside': [(center_x - court_bottom_width * 0.35, court_bottom_y + court_depth * 0.3)],  # Left side
        'Libero': [(center_x, court_bottom_y + court_depth * 0.5)],  # Center
        'Middle Blocker': [(center_x, court_top_y - court_depth * 0.1)],  # At net (top)
        'Opposite': [(center_x + court_bottom_width * 0.35, court_bottom_y + court_depth * 0.3)]  # Right side
    }
    
    # Create circles for each position group
    for position_group, count in reception_counts.items():
        if position_group in position_coords:
            coords = position_coords[position_group]
            color = position_colors.get(position_group, '#808080')
            
            # Scale bubble size based on count (min 40, max 100)
            size = max(40, min(100, (count / max_count) * 75))
            percentage = (count / total_receptions * 100) if total_receptions > 0 else 0
            
            # Single position circle
            x, y = coords[0]
            fig.add_trace(go.Scatter(
                x=[x],
                y=[y],
                mode='markers+text',
                marker=dict(
                    size=size,
                    color=color,
                    line=dict(color='#050d76', width=2.5),
                    opacity=0.8
                ),
                text=[f"{count}<br>{percentage:.1f}%"],
                textposition="middle center",
                textfont=dict(size=10, color='#FFFFFF', family='Arial Black'),
                name=position_group,
                showlegend=False,
                hovertemplate=f'<b>{position_group}</b><br>Receptions: {count}<br>Percentage: {percentage:.1f}%<extra></extra>'
            ))
    
    # Add position labels
    label_positions = {
        'Outside': [(center_x - court_bottom_width * 0.35, court_bottom_y + court_depth * 0.15, "Outside")],
        'Libero': [(center_x, court_bottom_y + court_depth * 0.35, "Libero")],
        'Middle Blocker': [(center_x, court_top_y + court_depth * 0.05, "Middle<br>Blocker")],
        'Opposite': [(center_x + court_bottom_width * 0.35, court_bottom_y + court_depth * 0.15, "Opposite")]
    }
    
    for position_group, labels in label_positions.items():
        for x, y, label_text in labels:
            fig.add_annotation(
                x=x,
                y=y,
                text=label_text,
                showarrow=False,
                font=dict(size=11, color='#050d76', family='Poppins'),
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor="#050d76",
                borderwidth=1.5,
                borderpad=3
            )
    
    # Update layout
    fig.update_layout(
        title=dict(
            text="Reception Distribution by Position",
            font=dict(size=18, color='#050d76', family='Poppins'),
            x=0.5
        ),
        xaxis=dict(
            range=[center_x - court_bottom_width * 0.65, center_x + court_bottom_width * 0.65],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            title=""
        ),
        yaxis=dict(
            range=[court_bottom_y - court_depth * 0.2, court_top_y + court_depth * 0.2],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            title="",
            scaleanchor="x",
            scaleratio=1
        ),
        height=CHART_HEIGHTS['large'],
        showlegend=False,
        paper_bgcolor='rgba(255,255,255,0)',
        plot_bgcolor='rgba(255,255,255,0.98)',
        margin=dict(l=40, r=40, t=80, b=40)
    )
    
    fig = apply_beautiful_theme(fig, "Reception Distribution by Position")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="reception_distribution_position")


def _create_quality_by_action_chart(df: pd.DataFrame, loader=None) -> None:
    """Create stacked bar chart showing quality distribution (Kill, Good, Error) for each action type."""
    # Define action types to analyze
    action_types = ['attack', 'serve', 'block', 'receive', 'dig']
    
    quality_data = []
    
    for action in action_types:
        # Initialize counts
        kills = 0
        good = 0
        errors = 0
        has_data = False
        
        # For reception, use aggregated reception data first
        if action == 'receive' and loader and hasattr(loader, 'reception_data_by_rotation'):
            total_good = 0.0
            total_total = 0.0
            for set_num in loader.reception_data_by_rotation.keys():
                for rot_num in loader.reception_data_by_rotation[set_num].keys():
                    rot_data = loader.reception_data_by_rotation[set_num][rot_num]
                    total_good += float(rot_data.get('good', 0) or 0)
                    total_total += float(rot_data.get('total', 0) or 0)
            if total_total > 0:
                good = int(total_good)
                errors = int(total_total - total_good)
                kills = 0  # Receptions don't have kills
                has_data = True
        
        # For other actions, try aggregated data first (more accurate)
        elif loader and hasattr(loader, 'player_data_by_set'):
            total_kills = 0.0
            total_good = 0.0
            total_total = 0.0
            
            for set_num in loader.player_data_by_set.keys():
                for player in loader.player_data_by_set[set_num].keys():
                    stats = loader.player_data_by_set[set_num][player].get('stats', {})
                    
                    if action == 'attack':
                        total_kills += float(stats.get('Attack_Kills', 0) or 0)
                        total_good += float(stats.get('Attack_Good', 0) or 0)
                        total_total += float(stats.get('Attack_Total', 0) or 0)
                    elif action == 'serve':
                        total_kills += float(stats.get('Service_Aces', 0) or 0)
                        total_good += float(stats.get('Service_Good', 0) or 0)
                        total_total += float(stats.get('Service_Total', 0) or 0)
                    elif action == 'block':
                        total_kills += float(stats.get('Block_Kills', 0) or 0)
                        total_good += float(stats.get('Block_Touches', 0) or 0)
                        total_total += float(stats.get('Block_Total', 0) or 0)
                    elif action == 'dig':
                        total_good += float(stats.get('Dig_Good', 0) or 0)
                        total_total += float(stats.get('Dig_Total', 0) or 0)
            
            # Calculate errors after accumulating all totals
            if total_total > 0:
                total_errors = total_total - total_kills - total_good
                kills = int(total_kills)
                good = int(total_good)
                errors = int(max(0, total_errors))  # Ensure non-negative
                has_data = True
            elif total_kills > 0 or total_good > 0:
                # If we have kills/good but no total, assume no errors
                kills = int(total_kills)
                good = int(total_good)
                errors = 0
                has_data = True
        
        # Fallback to action rows if no aggregated data
        if not has_data:
            action_df = df[df['action'] == action]
            if len(action_df) == 0:
                continue
            
            # Count outcomes from action rows
            if action == 'serve':
                # For serves, combine ace with kill
                kills = len(action_df[action_df['outcome'].isin(['kill', 'ace'])])
                good = len(action_df[action_df['outcome'] == 'good'])
                errors = len(action_df[action_df['outcome'] == 'error'])
            elif action == 'block':
                # For blocks, kills are kills, touches are touches
                kills = len(action_df[action_df['outcome'] == 'kill'])
                good = len(filter_block_touches(action_df))
                errors = len(action_df[action_df['outcome'] == 'error'])
            elif action == 'receive':
                # For receptions, use new outcomes (perfect_0, good_1)
                kills = len(action_df[action_df['outcome'] == 'kill'])
                good = len(filter_good_receptions(action_df))
                errors = len(action_df[action_df['outcome'] == 'error'])
            elif action == 'dig':
                # For digs, use new outcomes (perfect_0, good_1)
                kills = len(action_df[action_df['outcome'] == 'kill'])
                good = len(filter_good_digs(action_df))
                errors = len(action_df[action_df['outcome'] == 'error'])
            else:
                # For other actions (attack, set)
                kills = len(action_df[action_df['outcome'] == 'kill'])
                # For attacks, 'defended' is good; for sets, 'good' is good
                if action == 'attack':
                    good = len(action_df[action_df['outcome'] == 'defended'])
                    # Attack errors: blocked, out, net (error removed - all errors covered)
                    errors = len(action_df[action_df['outcome'].isin(['blocked', 'out', 'net'])])
                else:
                    good = len(action_df[action_df['outcome'] == 'good'])
                    errors = len(action_df[action_df['outcome'] == 'error'])
        
        # Only add if we have data
        if kills + good + errors > 0:
            quality_data.append({
                'Action': action.capitalize(),
                'Kill': kills,
                'Good': good,
                'Error': errors
            })
    
    if not quality_data:
        st.info("No quality data available to display.")
        return
    
    quality_df = pd.DataFrame(quality_data)
    
    # Create stacked bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=quality_df['Action'],
        y=quality_df['Kill'],
        name='Kill',
        marker_color=OUTCOME_COLORS['kill'],
        text=quality_df['Kill'],
        textposition='inside',
        textfont=dict(size=10, color='#FFFFFF')
    ))
    
    fig.add_trace(go.Bar(
        x=quality_df['Action'],
        y=quality_df['Good'],
        name='Good',
        marker_color=OUTCOME_COLORS['good'],
        text=quality_df['Good'],
        textposition='inside',
        textfont=dict(size=10, color='#050d76')
    ))
    
    fig.add_trace(go.Bar(
        x=quality_df['Action'],
        y=quality_df['Error'],
        name='Error',
        marker_color=OUTCOME_COLORS['error'],
        text=quality_df['Error'],
        textposition='inside',
        textfont=dict(size=10, color='#FFFFFF')
    ))
    
    fig.update_layout(
        title="Quality Distribution by Action Type",
        xaxis_title="Action Type",
        yaxis_title="Count",
        barmode='stack',
        height=CHART_HEIGHTS['medium'],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    fig = apply_beautiful_theme(fig, "Quality Distribution by Action Type")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="quality_by_action")
    
    # Add summary statistics
    col1, col2, col3 = st.columns(3)
    total_kills = quality_df['Kill'].sum()
    total_good = quality_df['Good'].sum()
    total_errors = quality_df['Error'].sum()
    total_actions = total_kills + total_good + total_errors
    
    with col1:
        st.metric("Total Kills", f"{total_kills}")
    with col2:
        st.metric("Total Good", f"{total_good}")
    with col3:
        st.metric("Total Errors", f"{total_errors}")


def _create_set_by_set_charts(df: pd.DataFrame, analyzer: MatchAnalyzer, loader=None) -> None:
    """Create set-by-set performance charts with new KPIs and quality distributions."""
    from config import KPI_TARGETS
    
    # Filter to only played sets
    played_sets = get_played_sets(df, loader)
    if not played_sets:
        st.info("No set data available to display.")
        return
    
    # Calculate set-level metrics using aggregated data
    set_metrics_data = []
    
    for set_num in played_sets:
        metrics = {}
        
        # 1. Serving Point Rate (from team_data)
        if loader and hasattr(loader, 'team_data') and set_num in loader.team_data:
            serving_rallies = float(loader.team_data[set_num].get('serving_rallies', 0) or 0)
            serving_points_won = float(loader.team_data[set_num].get('serving_points_won', 0) or 0)
            metrics['serving_point_rate'] = (serving_points_won / serving_rallies) if serving_rallies > 0 else 0.0
        else:
            metrics['serving_point_rate'] = 0.0
        
        # 2. Receiving Point Rate (from team_data)
        if loader and hasattr(loader, 'team_data') and set_num in loader.team_data:
            receiving_rallies = float(loader.team_data[set_num].get('receiving_rallies', 0) or 0)
            receiving_points_won = float(loader.team_data[set_num].get('receiving_points_won', 0) or 0)
            metrics['receiving_point_rate'] = (receiving_points_won / receiving_rallies) if receiving_rallies > 0 else 0.0
        else:
            metrics['receiving_point_rate'] = 0.0
        
        # 3. Attack Kill % (from aggregated player stats)
        if loader and hasattr(loader, 'player_data_by_set') and set_num in loader.player_data_by_set:
            attack_kills = 0.0
            attack_total = 0.0
            for player in loader.player_data_by_set[set_num].keys():
                stats = loader.player_data_by_set[set_num][player].get('stats', {})
                attack_kills += float(stats.get('Attack_Kills', 0) or 0)
                attack_total += float(stats.get('Attack_Total', 0) or 0)
            metrics['attack_kill_pct'] = (attack_kills / attack_total) if attack_total > 0 else 0.0
        else:
            # Fallback to action rows
            set_df = df[df['set_number'] == set_num]
            attacks = set_df[set_df['action'] == 'attack']
            attack_kills = len(attacks[attacks['outcome'] == 'kill'])
            attack_total = len(attacks)
            metrics['attack_kill_pct'] = (attack_kills / attack_total) if attack_total > 0 else 0.0
        
        # 4. Reception Quality (from aggregated reception data)
        if loader and hasattr(loader, 'reception_data_by_rotation') and set_num in loader.reception_data_by_rotation:
            rec_good = 0.0
            rec_total = 0.0
            for rot_num in loader.reception_data_by_rotation[set_num].keys():
                rot_data = loader.reception_data_by_rotation[set_num][rot_num]
                rec_good += float(rot_data.get('good', 0) or 0)
                rec_total += float(rot_data.get('total', 0) or 0)
            metrics['reception_quality'] = (rec_good / rec_total) if rec_total > 0 else 0.0
        else:
            # Fallback to action rows
            set_df = df[df['set_number'] == set_num]
            receives = set_df[set_df['action'] == 'receive']
            rec_good = len(filter_good_receptions(receives))
            rec_total = len(receives)
            metrics['reception_quality'] = (rec_good / rec_total) if rec_total > 0 else 0.0
        
        # 5. Attack Quality Distribution (Kills, Good, Errors)
        if loader and hasattr(loader, 'player_data_by_set') and set_num in loader.player_data_by_set:
            attack_kills = 0.0
            attack_good = 0.0
            attack_errors = 0.0
            attack_total = 0.0
            for player in loader.player_data_by_set[set_num].keys():
                stats = loader.player_data_by_set[set_num][player].get('stats', {})
                attack_kills += float(stats.get('Attack_Kills', 0) or 0)
                attack_good += float(stats.get('Attack_Good', 0) or 0)
                attack_total += float(stats.get('Attack_Total', 0) or 0)
            attack_errors = attack_total - attack_kills - attack_good
            metrics['attack_kills'] = attack_kills
            metrics['attack_good'] = attack_good
            metrics['attack_errors'] = attack_errors
        else:
            set_df = df[df['set_number'] == set_num]
            attacks = set_df[set_df['action'] == 'attack']
            metrics['attack_kills'] = len(attacks[attacks['outcome'] == 'kill'])
            # Attack 'defended' is considered good (kept in play)
            metrics['attack_good'] = len(attacks[attacks['outcome'] == 'defended'])
            # Attack errors: blocked, out, net (error removed - all errors covered)
            metrics['attack_errors'] = len(attacks[attacks['outcome'].isin(['blocked', 'out', 'net'])])
        
        # 6. Service Quality Distribution (Aces, Good, Errors)
        if loader and hasattr(loader, 'player_data_by_set') and set_num in loader.player_data_by_set:
            service_aces = 0.0
            service_good = 0.0
            service_total = 0.0
            for player in loader.player_data_by_set[set_num].keys():
                stats = loader.player_data_by_set[set_num][player].get('stats', {})
                service_aces += float(stats.get('Service_Aces', 0) or 0)
                service_good += float(stats.get('Service_Good', 0) or 0)
                service_total += float(stats.get('Service_Total', 0) or 0)
            service_errors = service_total - service_aces - service_good
            metrics['service_aces'] = service_aces
            metrics['service_good'] = service_good
            metrics['service_errors'] = service_errors
            metrics['service_in_rate'] = ((service_aces + service_good) / service_total) if service_total > 0 else 0.0
        else:
            set_df = df[df['set_number'] == set_num]
            serves = set_df[set_df['action'] == 'serve']
            metrics['service_aces'] = len(serves[serves['outcome'] == 'ace'])
            metrics['service_good'] = len(serves[serves['outcome'] == 'good'])
            metrics['service_errors'] = len(serves[serves['outcome'] == 'error'])
            service_total = len(serves)
            metrics['service_in_rate'] = ((metrics['service_aces'] + metrics['service_good']) / service_total) if service_total > 0 else 0.0
        
        # 7. Block Quality Distribution (Kills, Touches, Errors)
        if loader and hasattr(loader, 'player_data_by_set') and set_num in loader.player_data_by_set:
            block_kills = 0.0
            block_touches = 0.0
            block_total = 0.0
            for player in loader.player_data_by_set[set_num].keys():
                stats = loader.player_data_by_set[set_num][player].get('stats', {})
                block_kills += float(stats.get('Block_Kills', 0) or 0)
                block_touches += float(stats.get('Block_Touches', 0) or 0)
                block_total += float(stats.get('Block_Total', 0) or 0)
            block_errors = block_total - block_kills - block_touches
            metrics['block_kills'] = block_kills
            metrics['block_touches'] = block_touches
            metrics['block_errors'] = block_errors
            metrics['block_kill_pct'] = (block_kills / block_total) if block_total > 0 else 0.0
        else:
            set_df = df[df['set_number'] == set_num]
            blocks = set_df[set_df['action'] == 'block']
            metrics['block_kills'] = len(blocks[blocks['outcome'] == 'kill'])
            metrics['block_touches'] = len(filter_block_touches(blocks))
            metrics['block_errors'] = len(blocks[blocks['outcome'] == 'error'])
            block_total = len(blocks)
            metrics['block_kill_pct'] = (metrics['block_kills'] / block_total) if block_total > 0 else 0.0
        
        # 8. Reception Quality Distribution (Good, Errors)
        if loader and hasattr(loader, 'reception_data_by_rotation') and set_num in loader.reception_data_by_rotation:
            rec_good = 0.0
            rec_total = 0.0
            for rot_num in loader.reception_data_by_rotation[set_num].keys():
                rot_data = loader.reception_data_by_rotation[set_num][rot_num]
                rec_good += float(rot_data.get('good', 0) or 0)
                rec_total += float(rot_data.get('total', 0) or 0)
            metrics['reception_good'] = rec_good
            metrics['reception_errors'] = rec_total - rec_good
        else:
            set_df = df[df['set_number'] == set_num]
            receives = set_df[set_df['action'] == 'receive']
            metrics['reception_good'] = len(filter_good_receptions(receives))
            metrics['reception_errors'] = len(receives[receives['outcome'] == 'error'])
        
        # 9. Dig Rate (from aggregated data)
        if loader and hasattr(loader, 'player_data_by_set') and set_num in loader.player_data_by_set:
            dig_good = 0.0
            dig_total = 0.0
            for player in loader.player_data_by_set[set_num].keys():
                stats = loader.player_data_by_set[set_num][player].get('stats', {})
                dig_good += float(stats.get('Dig_Good', 0) or 0)
                dig_total += float(stats.get('Dig_Total', 0) or 0)
            metrics['dig_rate'] = (dig_good / dig_total) if dig_total > 0 else 0.0
        else:
            set_df = df[df['set_number'] == set_num]
            digs = set_df[set_df['action'] == 'dig']
            dig_good = len(filter_good_digs(digs))
            dig_total = len(digs)
            metrics['dig_rate'] = (dig_good / dig_total) if dig_total > 0 else 0.0
        
        # 10. Error Rate (total errors / total actions)
        if loader and hasattr(loader, 'player_data_by_set') and set_num in loader.player_data_by_set:
            total_errors = 0.0
            total_actions = 0.0
            for player in loader.player_data_by_set[set_num].keys():
                stats = loader.player_data_by_set[set_num][player].get('stats', {})
                total_errors += (float(stats.get('Attack_Errors', 0) or 0) + 
                                float(stats.get('Service_Errors', 0) or 0) +
                                float(stats.get('Block_Errors', 0) or 0) +
                                float(stats.get('Sets_Errors', 0) or 0))
                total_actions += (float(stats.get('Attack_Total', 0) or 0) +
                                 float(stats.get('Service_Total', 0) or 0) +
                                 float(stats.get('Block_Total', 0) or 0) +
                                 float(stats.get('Sets_Total', 0) or 0))
            # Add reception errors (calculated from reception data)
            if set_num in loader.reception_data_by_rotation:
                rec_total = 0.0
                rec_good = 0.0
                for rot_num in loader.reception_data_by_rotation[set_num].keys():
                    rot_data = loader.reception_data_by_rotation[set_num][rot_num]
                    rec_total += float(rot_data.get('total', 0) or 0)
                    rec_good += float(rot_data.get('good', 0) or 0)
                total_errors += (rec_total - rec_good)
                total_actions += rec_total
            metrics['error_rate'] = (total_errors / total_actions) if total_actions > 0 else 0.0
        else:
            set_df = df[df['set_number'] == set_num]
            total_errors = len(set_df[set_df['outcome'] == 'error'])
            total_actions = len(set_df)
            metrics['error_rate'] = (total_errors / total_actions) if total_actions > 0 else 0.0
        
        # 11. Points per Rally
        if loader and hasattr(loader, 'team_data') and set_num in loader.team_data:
            serving_rallies = float(loader.team_data[set_num].get('serving_rallies', 0) or 0)
            receiving_rallies = float(loader.team_data[set_num].get('receiving_rallies', 0) or 0)
            total_rallies = serving_rallies + receiving_rallies
            serving_points_won = float(loader.team_data[set_num].get('serving_points_won', 0) or 0)
            receiving_points_won = float(loader.team_data[set_num].get('receiving_points_won', 0) or 0)
            total_points_won = serving_points_won + receiving_points_won
            metrics['points_per_rally'] = (total_points_won / total_rallies) if total_rallies > 0 else 0.0
        else:
            metrics['points_per_rally'] = 0.0
        
        metrics['set'] = set_num
        set_metrics_data.append(metrics)
    
    set_metrics_df = pd.DataFrame(set_metrics_data)
    
    # === LINE CHART: Performance Trends ===
    st.markdown("#### 📈 Performance Trends Across Sets")
    fig_trends = go.Figure()
    
    fig_trends.add_trace(go.Scatter(
        x=set_metrics_df['set'],
        y=set_metrics_df['serving_point_rate'],
        name='Serving Point Rate',
        mode='lines+markers',
        line=dict(color='#B8D4E6', width=3),  # Soft blue
        marker=dict(size=10)
    ))
    
    fig_trends.add_trace(go.Scatter(
        x=set_metrics_df['set'],
        y=set_metrics_df['receiving_point_rate'],
        name='Receiving Point Rate',
        mode='lines+markers',
        line=dict(color='#90EE90', width=3),  # Soft green
        marker=dict(size=10)
    ))
    
    fig_trends.add_trace(go.Scatter(
        x=set_metrics_df['set'],
        y=set_metrics_df['attack_kill_pct'],
        name='Attack Kill %',
        mode='lines+markers',
        line=dict(color='#FFE4B5', width=3),  # Soft yellow
        marker=dict(size=10)
    ))
    
    fig_trends.add_trace(go.Scatter(
        x=set_metrics_df['set'],
        y=set_metrics_df['reception_quality'],
        name='Reception Quality',
        mode='lines+markers',
        line=dict(color='#FFB6C1', width=3),  # Soft pink/red
        marker=dict(size=10)
    ))
    
    fig_trends.update_layout(
        title="Performance Trends Across Sets",
        xaxis_title="Set Number",
        yaxis_title="Performance Rate",
        yaxis=dict(tickformat='.0%', tickfont=dict(color='#050d76')),
        xaxis=dict(dtick=1, tickfont=dict(color='#050d76')),
        height=CHART_HEIGHTS['medium'],
        hovermode='x unified',
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="right", x=1.02)
    )
    fig_trends = apply_beautiful_theme(fig_trends, "Performance Trends Across Sets")
    st.plotly_chart(fig_trends, use_container_width=True, config=plotly_config, key="performance_trends_sets")
    
    # === STACKED BAR CHARTS: Quality Distributions ===
    st.markdown("#### 🎯 Quality Distribution by Set")
    
    # Row 2: Attack Type Distribution and Attack Quality Distribution side-by-side
    col_attack_type, col_attack_quality = st.columns(2)
    
    with col_attack_type:
        _create_attack_type_distribution_chart(df, loader)
    
    with col_attack_quality:
        # Attack Quality Distribution by Set
        st.markdown("#### 🎯 Attack Quality Distribution by Set")
        attack_details_by_set = {}
        played_sets = get_played_sets(df, loader)
        for set_num in played_sets:
            set_df = df[df['set_number'] == set_num]
            attacks = set_df[set_df['action'] == 'attack']
            attack_details_by_set[set_num] = {
                'kill': len(attacks[attacks['outcome'] == 'kill']),
                'defended': len(attacks[attacks['outcome'] == 'defended']),
                'blocked': len(attacks[attacks['outcome'] == 'blocked']),
                'out': len(attacks[attacks['outcome'] == 'out']),
                'net': len(attacks[attacks['outcome'] == 'net'])
                # 'error' removed from attack outcomes - all errors covered by 'blocked', 'out', 'net'
            }
        
    fig_attack = go.Figure()
    fig_attack.add_trace(go.Bar(
            x=[f"Set {s}" for s in played_sets],
            y=[attack_details_by_set.get(s, {}).get('kill', 0) for s in played_sets],
        name='Kills',
            marker_color=OUTCOME_COLORS['kill'],
            text=[attack_details_by_set.get(s, {}).get('kill', 0) for s in played_sets],
            textposition='inside',
            textfont=dict(size=9, color='#FFFFFF')
    ))
    fig_attack.add_trace(go.Bar(
            x=[f"Set {s}" for s in played_sets],
            y=[attack_details_by_set.get(s, {}).get('defended', 0) for s in played_sets],
            name='Good (Defended)',
            marker_color=OUTCOME_COLORS['defended'],
            text=[attack_details_by_set.get(s, {}).get('defended', 0) for s in played_sets],
            textposition='inside',
            textfont=dict(size=9, color='#FFFFFF')
    ))
    fig_attack.add_trace(go.Bar(
            x=[f"Set {s}" for s in played_sets],
            y=[(attack_details_by_set.get(s, {}).get('blocked', 0) + 
                attack_details_by_set.get(s, {}).get('out', 0) + 
                attack_details_by_set.get(s, {}).get('net', 0) + 
                attack_details_by_set.get(s, {}).get('error', 0)) for s in played_sets],
        name='Errors',
            marker_color=OUTCOME_COLORS['error'],
            text=[(attack_details_by_set.get(s, {}).get('blocked', 0) + 
                   attack_details_by_set.get(s, {}).get('out', 0) + 
                   attack_details_by_set.get(s, {}).get('net', 0) + 
                   attack_details_by_set.get(s, {}).get('error', 0)) for s in played_sets],
            textposition='inside',
            textfont=dict(size=9, color='#FFFFFF')
        ))
        
    total_attack_attempts = sum(sum(attack_details_by_set.get(s, {}).values()) for s in played_sets)
    fig_attack.update_layout(
        title=f"Attack Quality Distribution (n={total_attack_attempts} attacks)",
        xaxis_title="Set Number",
        yaxis_title="Count",
        barmode='stack',
        xaxis=dict(dtick=1, tickfont=dict(color='#050d76')),
        yaxis=dict(tickfont=dict(color='#050d76')),
        height=CHART_HEIGHTS['medium'],
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="right", x=1.02)
    )
    fig_attack = apply_beautiful_theme(fig_attack, "Attack Quality Distribution")
    st.plotly_chart(fig_attack, use_container_width=True, config=plotly_config, key="attack_quality_distribution_set")
    
    # Service Quality Distribution
    col1, col2 = st.columns(2)
    
    with col1:
        fig_service = go.Figure()
        fig_service.add_trace(go.Bar(
            x=set_metrics_df['set'],
            y=set_metrics_df['service_aces'],
            name='Aces',
            marker_color=OUTCOME_COLORS['ace'],
            text=set_metrics_df['service_aces'].astype(int),
            textposition='inside'
        ))
        fig_service.add_trace(go.Bar(
            x=set_metrics_df['set'],
            y=set_metrics_df['service_good'],
            name='Good',
            marker_color=OUTCOME_COLORS['good'],
            text=set_metrics_df['service_good'].astype(int),
            textposition='inside'
        ))
        fig_service.add_trace(go.Bar(
            x=set_metrics_df['set'],
            y=set_metrics_df['service_errors'],
            name='Errors',
            marker_color=OUTCOME_COLORS['error'],
            text=set_metrics_df['service_errors'].astype(int),
            textposition='inside'
        ))
        
        fig_service.update_layout(
            title="Service Quality Distribution",
            xaxis_title="Set Number",
            yaxis_title="Count",
            barmode='stack',
            xaxis=dict(dtick=1, tickfont=dict(color='#050d76')),
            yaxis=dict(tickfont=dict(color='#050d76')),
            height=CHART_HEIGHTS['medium'],
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig_service = apply_beautiful_theme(fig_service, "Service Quality Distribution")
        st.plotly_chart(fig_service, use_container_width=True, config=plotly_config, key="service_quality_set")
    
    with col2:
        fig_block = go.Figure()
        fig_block.add_trace(go.Bar(
            x=set_metrics_df['set'],
            y=set_metrics_df['block_kills'],
            name='Kills',
            marker_color=OUTCOME_COLORS['kill'],
            text=set_metrics_df['block_kills'].astype(int),
            textposition='inside'
        ))
        fig_block.add_trace(go.Bar(
            x=set_metrics_df['set'],
            y=set_metrics_df['block_touches'],
            name='Touches',
            marker_color=OUTCOME_COLORS['touch'],
            text=set_metrics_df['block_touches'].astype(int),
            textposition='inside'
        ))
        fig_block.add_trace(go.Bar(
            x=set_metrics_df['set'],
            y=set_metrics_df['block_errors'],
            name='Errors',
            marker_color=OUTCOME_COLORS['error'],
            text=set_metrics_df['block_errors'].astype(int),
            textposition='inside'
        ))
        
        fig_block.update_layout(
            title="Block Quality Distribution",
            xaxis_title="Set Number",
            yaxis_title="Count",
            barmode='stack',
            xaxis=dict(dtick=1, tickfont=dict(color='#050d76')),
            yaxis=dict(tickfont=dict(color='#050d76')),
            height=CHART_HEIGHTS['medium'],
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig_block = apply_beautiful_theme(fig_block, "Block Quality Distribution")
        st.plotly_chart(fig_block, use_container_width=True, config=plotly_config, key="block_quality_set")
    
    # Reception Quality Distribution - Enhanced with granularity
    # Get detailed reception outcomes from dataframe
    reception_details_by_set = {}
    for set_num in played_sets:
        set_df = df[df['set_number'] == set_num]
        receives = set_df[set_df['action'] == 'receive']
        reception_details_by_set[set_num] = {
            'perfect': len(receives[receives['outcome'] == 'perfect']),
            'good': len(receives[receives['outcome'] == 'good']),
            'poor': len(receives[receives['outcome'] == 'poor']),
            'error': len(receives[receives['outcome'] == 'error'])
        }
    
    fig_reception = go.Figure()
    
    # Separate perfect and good (don't combine)
    fig_reception.add_trace(go.Bar(
        x=[f"Set {s}" for s in played_sets],
        y=[reception_details_by_set.get(s, {}).get('perfect', 0) for s in played_sets],
        name='Perfect',
        marker_color=OUTCOME_COLORS['perfect'],
        text=[reception_details_by_set.get(s, {}).get('perfect', 0) for s in played_sets],
        textposition='inside',
        textfont=dict(size=9, color='#FFFFFF')
    ))
    fig_reception.add_trace(go.Bar(
        x=[f"Set {s}" for s in played_sets],
        y=[reception_details_by_set.get(s, {}).get('good', 0) for s in played_sets],
        name='Good',
        marker_color=OUTCOME_COLORS['good'],
        text=[reception_details_by_set.get(s, {}).get('good', 0) for s in played_sets],
        textposition='inside',
        textfont=dict(size=9, color='#FFFFFF')
    ))
    fig_reception.add_trace(go.Bar(
        x=[f"Set {s}" for s in played_sets],
        y=[reception_details_by_set.get(s, {}).get('poor', 0) for s in played_sets],
        name='Poor',
        marker_color=OUTCOME_COLORS['poor'],
        text=[reception_details_by_set.get(s, {}).get('poor', 0) for s in played_sets],
        textposition='inside',
        textfont=dict(size=9, color='#FFFFFF')
    ))
    fig_reception.add_trace(go.Bar(
        x=[f"Set {s}" for s in played_sets],
        y=[reception_details_by_set.get(s, {}).get('error', 0) for s in played_sets],
        name='Errors',
        marker_color=OUTCOME_COLORS['error'],
        text=[reception_details_by_set.get(s, {}).get('error', 0) for s in played_sets],
        textposition='inside',
        textfont=dict(size=9, color='#FFFFFF')
    ))
    
    # Calculate total reception attempts for sample size
    total_reception_attempts = sum(sum(reception_details_by_set.get(s, {}).values()) for s in played_sets)
    
    fig_reception.update_layout(
        title=f"Reception Quality Distribution (Granular) (n={total_reception_attempts} receptions)",
        xaxis_title="Set Number",
        yaxis_title="Count",
        barmode='stack',
        xaxis=dict(dtick=1, tickfont=dict(color='#050d76')),
        yaxis=dict(tickfont=dict(color='#050d76')),
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="right", x=1.02)
    )
    fig_reception = apply_beautiful_theme(fig_reception, "Reception Quality Distribution", height=CHART_HEIGHTS['medium'])
    st.plotly_chart(fig_reception, use_container_width=True, config=plotly_config, key="reception_quality_set")


def _create_attack_type_distribution_chart(df: pd.DataFrame, loader=None) -> None:
    """Create chart showing attack breakdown by attack type (normal, tip)."""
    from utils.breakdown_helpers import get_attack_breakdown_by_type
    
    st.markdown("#### 🎯 Attack Type Distribution")
    
    attack_breakdown = get_attack_breakdown_by_type(df, loader)
    
    # Prepare data for stacked bar chart by set
    played_sets = get_played_sets(df, loader)
    
    attack_type_data_by_set = {}
    for set_num in played_sets:
        set_df = df[df['set_number'] == set_num]
        set_breakdown = get_attack_breakdown_by_type(set_df, loader)
        attack_type_data_by_set[set_num] = set_breakdown
    
    # Create stacked bar chart
    fig = go.Figure()
    
    attack_types = ['normal', 'tip']
    # Use standardized colors from config
    colors = ATTACK_TYPE_COLORS
    
    for attack_type in attack_types:
        values = []
        for set_num in played_sets:
            set_data = attack_type_data_by_set.get(set_num, {})
            type_data = set_data.get(attack_type, {})
            values.append(type_data.get('total', 0))
        
        fig.add_trace(go.Bar(
            x=[f"Set {s}" for s in played_sets],
            y=values,
            name=attack_type.capitalize().replace('_', ' '),
            marker_color=colors.get(attack_type, '#808080'),
            text=values,
            textposition='inside',
            textfont=dict(size=10, color='#FFFFFF')
        ))
    
    # Calculate total attacks for sample size
    total_attacks = sum(attack_breakdown.get(at, {}).get('total', 0) if isinstance(attack_breakdown.get(at), dict) else 0 for at in attack_types)
    
    fig.update_layout(
        title=f"Attack Type Distribution by Set (n={total_attacks} total attacks)",
        xaxis_title="Set Number",
        yaxis_title="Count",
        barmode='stack',
        height=CHART_HEIGHTS['medium'],
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(tickfont=dict(color='#050d76')),
        yaxis=dict(tickfont=dict(color='#050d76'))
    )
    fig = apply_beautiful_theme(fig, "Attack Type Distribution")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="attack_type_distribution_main")
    
    # Add detailed breakdown as donut charts per set
    st.markdown("#### 📊 Detailed Attack Type Breakdown by Set")
    played_sets = get_played_sets(df, loader)
    
    if played_sets:
        cols = st.columns(len(played_sets))
        for idx, set_num in enumerate(played_sets):
            with cols[idx]:
                set_df = df[df['set_number'] == set_num]
                set_breakdown = get_attack_breakdown_by_type(set_df, loader)
                
                # Prepare data for donut chart - ensure consistent order
                donut_data = []
                donut_labels = []
                donut_values = []
                
                # Process in consistent order: normal, tip
                attack_type_order = ['normal', 'tip']
                label_mapping = {
                    'normal': 'Normal',
                    'tip': 'Tip'
                }
                
                for attack_type in attack_type_order:
                    type_data = set_breakdown.get(attack_type, {})
                    total = type_data.get('total', 0)
                    if total > 0:
                        donut_labels.append(label_mapping[attack_type])
                        donut_values.append(total)
                
                if donut_values:
                    # Map labels to colors explicitly to ensure consistency (use standardized colors)
                    label_to_color = {
                        'Normal': ATTACK_TYPE_COLORS.get('normal', '#4A90E2'),      # Blue
                        'Tip': ATTACK_TYPE_COLORS.get('tip', '#F5A623')             # Orange
                    }
                    
                    # Create explicit color list matching the order of labels
                    donut_colors = [label_to_color.get(label, '#808080') for label in donut_labels]
                    
                    fig_donut = go.Figure(data=[go.Pie(
                        labels=donut_labels,
                        values=donut_values,
                        hole=0.4,
                        marker=dict(colors=donut_colors, line=dict(color='white', width=2)),
                        textinfo='percent',
                        textfont=dict(size=14, color='#050d76', family='Inter, sans-serif'),
                        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
                    )])
                    
                    fig_donut.update_layout(
                        title=f"Set {set_num}",
                        height=CHART_HEIGHTS['small'],
                        showlegend=False,
                        margin=dict(l=20, r=20, t=40, b=20)
                    )
                    fig_donut = apply_beautiful_theme(fig_donut, f"Set {set_num} Attack Types")
                    st.plotly_chart(fig_donut, use_container_width=True, config=plotly_config, key=f"attack_type_donut_set_{set_num}")
                else:
                    st.info(f"No attack data for Set {set_num}")


def _create_rally_length_distribution_chart(df: pd.DataFrame, loader=None) -> None:
    """Create chart showing distribution of rally lengths (MEDIUM PRIORITY 30)."""
    st.markdown("#### 📏 Rally Length Distribution")
    
    # Calculate rally lengths from point_id groupings
    rally_lengths = []
    
    if 'point_id' in df.columns:
        # Group by point_id to get rally length (number of actions per rally)
        for point_id, group in df.groupby('point_id'):
            rally_lengths.append(len(group))
    elif 'point' in df.columns and 'set_number' in df.columns:
        # Fallback: group by set and point
        for (set_num, point), group in df.groupby(['set_number', 'point']):
            rally_lengths.append(len(group))
    else:
        st.info("Cannot calculate rally lengths: missing point_id or point column")
        return
    
    if not rally_lengths:
        st.info("No rally length data available")
        return
    
    # Create distribution histogram
    fig = go.Figure()
    
    # Create bins for rally lengths
    max_length = max(rally_lengths) if rally_lengths else 10
    bins = list(range(1, min(max_length + 2, 21)))  # Up to 20 actions per rally
    
    # Count rallies in each bin
    hist, bin_edges = pd.cut(rally_lengths, bins=bins, right=False, retbins=True)
    bin_counts = hist.value_counts().sort_index()
    
    # Create bar chart
    fig.add_trace(go.Bar(
        x=[f"{int(bin_edges[i])}-{int(bin_edges[i+1])-1}" for i in range(len(bin_counts))],
        y=bin_counts.values,
        marker_color=OUTCOME_COLORS['serving_rate'],
        text=bin_counts.values,
        textposition='outside',
        textfont=dict(size=10, color='#050d76'),
        hovertemplate='Rally Length: %{x} actions<br>Count: %{y}<extra></extra>'
    ))
    
    # Calculate statistics
    avg_rally_length = sum(rally_lengths) / len(rally_lengths) if rally_lengths else 0
    median_rally_length = sorted(rally_lengths)[len(rally_lengths) // 2] if rally_lengths else 0
    
    fig.update_layout(
        title=f"Rally Length Distribution (n={len(rally_lengths)} rallies, avg={avg_rally_length:.1f} actions)",
        xaxis_title="Rally Length (actions per rally)",
        yaxis_title="Number of Rallies",
        height=CHART_HEIGHTS['medium'],
        xaxis=dict(tickfont=dict(color='#050d76')),
        yaxis=dict(tickfont=dict(color='#050d76')),
        showlegend=False
    )
    fig = apply_beautiful_theme(fig, "Rally Length Distribution")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="rally_length_distribution")
    
    # Show statistics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Average Rally Length", f"{avg_rally_length:.1f} actions")
    with col2:
        st.metric("Median Rally Length", f"{median_rally_length:.0f} actions")
    with col3:
        st.metric("Total Rallies", f"{len(rally_lengths)}")


def _create_point_by_point_progression_chart(df: pd.DataFrame, loader=None) -> None:
    """Create chart showing point-by-point score progression - charts arranged side by side."""
    st.markdown("#### 📈 Point-by-Point Score Progression")
    
    if loader is None or not hasattr(loader, 'team_events'):
        st.info("Point-by-point progression requires team events data")
        return
    
    # Get score progression from team events
    try:
        team_events = loader.team_events
        
        # Check for score columns
        if 'Our_Score' not in team_events.columns and 'Opponent_Score' not in team_events.columns:
            st.info("Score progression data not available in team events")
            return
        
        # Group by set and point to get score progression
        sets = sorted(team_events['Set'].unique())
        
        BRAND_BLUE = '#040C7B'  # Team color
        OPPONENT_COLOR = '#E63946'  # Consistent red for opponent
        
        # Determine layout based on number of sets
        num_sets = len(sets)
        if num_sets == 0:
            return
        
        # Layout logic: 3 sets -> 3 columns, 4 sets -> 2 rows of 2, 5 sets -> 3 then 2
        if num_sets <= 3:
            # All sets in one row
            cols = st.columns(num_sets)
            rows = [sets]  # Single row
        elif num_sets == 4:
            # 2 rows of 2
            cols = st.columns(2)
            rows = [sets[:2], sets[2:]]
        else:  # 5 or more sets
            # 3 in first row, rest in second row
            cols = st.columns(3)
            rows = [sets[:3], sets[3:]]
        
        # Create charts for each set
        charts_data = []
        for set_num in sets:
            set_data = team_events[team_events['Set'] == set_num].sort_values('Point')
            
            if 'Our_Score' in set_data.columns and 'Opponent_Score' in set_data.columns:
                our_scores = set_data['Our_Score'].fillna(0).astype(int).tolist()
                opp_scores = set_data['Opponent_Score'].fillna(0).astype(int).tolist()
                points = list(range(1, len(our_scores) + 1))
                
                # Calculate set outcome
                final_our = our_scores[-1] if our_scores else 0
                final_opp = opp_scores[-1] if opp_scores else 0
                
                charts_data.append({
                    'set_num': set_num,
                    'points': points,
                    'our_scores': our_scores,
                    'opp_scores': opp_scores,
                    'final_our': final_our,
                    'final_opp': final_opp
                })
        
        # Add shared legend above all charts (only once)
        st.markdown("""
        <div style="display: flex; justify-content: center; align-items: center; 
                    gap: 20px; margin: 0 0 5px 0; padding: 0;">
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 12px; height: 12px; background-color: #040C7B; border-radius: 50%;"></div>
                <span style="font-size: 13px; color: #050d76; font-weight: 500;">Us</span>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <div style="width: 12px; height: 12px; background-color: #E63946; border-radius: 2px;"></div>
                <span style="font-size: 13px; color: #050d76; font-weight: 500;">Opponent</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        # Display charts in rows
        for row_idx, row_sets in enumerate(rows):
            if row_idx > 0:
                # Add spacing between rows
                st.markdown("<br>", unsafe_allow_html=True)
            
            row_cols = st.columns(len(row_sets)) if len(row_sets) <= 3 else st.columns(3)
            
            for col_idx, set_num in enumerate(row_sets):
                chart_info = next((c for c in charts_data if c['set_num'] == set_num), None)
                if chart_info is None:
                    continue
                
                with row_cols[col_idx if len(row_sets) <= 3 else col_idx % 3]:
                    # Wrap in container to shift left
                    st.markdown('<div style="margin-left: -15px;">', unsafe_allow_html=True)
                    
                    # Calculate set outcome
                    set_outcome = "Won" if chart_info['final_our'] > chart_info['final_opp'] else "Lost"
                    outcome_color = "#28A745" if chart_info['final_our'] > chart_info['final_opp'] else "#DC3545"
                    
                    # Show set header with larger score
                    st.markdown(f"""
                    <div style="display: flex; justify-content: space-between; align-items: center; 
                                padding: 8px 12px; background: #f8f9fa; border-radius: 8px; margin-bottom: 10px;">
                        <span style="font-size: 16px; font-weight: 700; color: #040C7B;">
                            Set {set_num}
                        </span>
                        <span style="font-size: 20px; color: {outcome_color}; font-weight: 700;">
                            {chart_info['final_our']}-{chart_info['final_opp']}
                        </span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    fig = go.Figure()
                    
                    # Add our score trace
                    fig.add_trace(go.Scatter(
                        x=chart_info['points'],
                        y=chart_info['our_scores'],
                        mode='lines+markers',
                        name='Us',
                        line=dict(color=BRAND_BLUE, width=2.5),
                        marker=dict(size=4, color=BRAND_BLUE),
                        hovertemplate='<b>Us</b><br>Rally %{x}<br>Score: %{y}<extra></extra>',
                        showlegend=False
                    ))
                    
                    # Add opponent score trace (continuous line)
                    fig.add_trace(go.Scatter(
                        x=chart_info['points'],
                        y=chart_info['opp_scores'],
                        mode='lines+markers',
                        name='Opponent',
                        line=dict(color=OPPONENT_COLOR, width=2.5),
                        marker=dict(size=4, color=OPPONENT_COLOR, symbol='square'),
                        hovertemplate='<b>Opponent</b><br>Rally %{x}<br>Score: %{y}<extra></extra>',
                        showlegend=False
                    ))
                    
                    fig.update_layout(
                        xaxis_title="Rally",
                        yaxis_title="Score",
                        height=350,
                        showlegend=False,
                        hovermode='x unified',
                        margin=dict(l=30, r=15, t=10, b=20),
                        xaxis=dict(tickfont=dict(color='#050d76', size=10)),
                        yaxis=dict(tickfont=dict(color='#050d76', size=10))
                    )
                    fig = apply_beautiful_theme(fig)
                    # Override margins after theme to ensure they fit in narrow columns
                    fig.update_layout(margin=dict(l=30, r=15, t=10, b=20), autosize=True)
                    # Create custom config with responsive sizing
                    responsive_config = {**plotly_config, 'responsive': True}
                    st.plotly_chart(fig, use_container_width=True, config=responsive_config, 
                                   key=f"score_progression_set_{set_num}")
                    
                    # Close wrapper div
                    st.markdown('</div>', unsafe_allow_html=True)
        
    except Exception as e:
        st.info(f"Score progression chart not available: {str(e)}")


def _create_rotation_heatmap(rotation_stats: Dict[int, Dict[str, float]], 
                             analyzer: MatchAnalyzer, df: pd.DataFrame, loader=None) -> None:
    """Create rotation performance heatmap with new metrics."""
    from config import KPI_TARGETS
    
    st.markdown("### 🔄 Rotation Performance Analysis")
    
    # Add set filter dropdown
    has_loader_available = (loader is not None and 
                           hasattr(loader, 'team_data_by_rotation') and 
                           loader.team_data_by_rotation is not None and
                           len(loader.team_data_by_rotation) > 0)
    
    # Get available sets for filter (only played sets)
    available_sets = get_played_sets(df, loader)
    
    # Always show dropdown if we have sets available
    if available_sets:
        set_options = ['All Sets'] + [f'Set {s}' for s in available_sets]
        selected_set_filter = st.selectbox(
            "Filter by Set:",
            options=set_options,
            index=0,
            key="rotation_set_filter"
        )
        # Extract set number if not "All Sets"
        selected_set_num = None if selected_set_filter == 'All Sets' else int(selected_set_filter.split()[-1])
    else:
        # No sets available, default to all (but still show a disabled dropdown)
        selected_set_filter = st.selectbox(
            "Filter by Set:",
            options=['All Sets'],
            index=0,
            key="rotation_set_filter",
            disabled=True
        )
        selected_set_num = None
    
    # Get played sets for filtering
    played_sets = get_played_sets(df, loader)
    
    # Get rotations from loader if available, otherwise from rotation_stats
    if loader and hasattr(loader, 'team_data_by_rotation') and loader.team_data_by_rotation:
        # Get all unique rotations from loader data (filtered by selected set and played sets)
        loader_rotations = set()
        # Filter to only played sets, then apply selected set filter if applicable
        available_sets_for_rotations = [s for s in played_sets if s in loader.team_data_by_rotation.keys()]
        sets_to_use = [selected_set_num] if selected_set_num is not None else available_sets_for_rotations
        for set_num in sets_to_use:
            if set_num in loader.team_data_by_rotation:
                loader_rotations.update(loader.team_data_by_rotation[set_num].keys())
        rotations = sorted(list(loader_rotations)) if loader_rotations else sorted(rotation_stats.keys())
    else:
        rotations = sorted(rotation_stats.keys())
    
    # Calculate enhanced metrics for each rotation using rally data from loader
    enhanced_stats = {}
    
    # Filter dataframe by set if a specific set is selected, and to only played sets
    if selected_set_num is None:
        filtered_df = df[df['set_number'].isin(played_sets)] if played_sets else df
    else:
        filtered_df = df[df['set_number'] == selected_set_num]
    
    # Calculate total points across all rotations for usage frequency (filtered by selected set if applicable)
    total_points_all_rotations = 0.0
    
    if has_loader_available:
        # Filter to only played sets, then apply selected set filter if applicable
        available_sets_for_points = [s for s in played_sets if s in loader.team_data_by_rotation.keys()]
        sets_to_use = [selected_set_num] if selected_set_num is not None else available_sets_for_points
        for set_num in sets_to_use:
            if set_num in loader.team_data_by_rotation:
                for rot in loader.team_data_by_rotation[set_num].keys():
                    rot_data = loader.team_data_by_rotation[set_num][rot]
                    total_points_all_rotations += float(rot_data.get('serving_rallies', 0) or 0) + float(rot_data.get('receiving_rallies', 0) or 0)
    else:
        # Fallback: count points from dataframe
        if selected_set_num is None:
            points_df = df[df['set_number'].isin(played_sets)] if played_sets else df
        else:
            points_df = df[df['set_number'] == selected_set_num]
        # Count unique point_id values (each point_id represents one rally/point)
        if 'point_id' in points_df.columns:
            total_points_all_rotations = float(points_df['point_id'].nunique())
        else:
            # Fallback: count by set and point
            total_points_all_rotations = float(len(points_df.groupby(['set_number', 'point_id']).size()) if 'point_id' in points_df.columns else len(points_df.groupby(['set_number', 'point']).size()))
    
    for rotation in rotations:
        rotation_data = filtered_df[filtered_df['rotation'] == rotation]
        
        # Serving Point Rate: Use rotation-level team rally data directly
        serving_rallies_total = 0.0
        serving_points_won_total = 0.0
        
        # Receiving Point Rate: Use rotation-level team rally data directly
        receiving_rallies_total = 0.0
        receiving_points_won_total = 0.0
        
        # Points for this rotation (for usage frequency)
        rotation_points = 0.0
        
        # If loader has rotation-level team_data, use it directly
        # Ensure rotation is treated as integer for matching
        rotation_int = int(rotation) if isinstance(rotation, (int, float)) else rotation
        
        # Check if loader and team_data_by_rotation exist and have data
        has_loader_data = (loader is not None and 
                          hasattr(loader, 'team_data_by_rotation') and 
                          loader.team_data_by_rotation is not None and
                          len(loader.team_data_by_rotation) > 0)
        
        if has_loader_data:
            # Filter sets to use based on selected filter and played sets
            available_sets_for_rotation = [s for s in played_sets if s in loader.team_data_by_rotation.keys()]
            sets_to_use = [selected_set_num] if selected_set_num is not None else available_sets_for_rotation
            
            for set_num in sets_to_use:
                if set_num in loader.team_data_by_rotation:
                    # Check if this rotation exists in this set
                    if rotation_int in loader.team_data_by_rotation[set_num]:
                        rot_stats = loader.team_data_by_rotation[set_num][rotation_int]
                        
                        # Get serving data for this rotation in this set
                        set_serving_rallies = float(rot_stats.get('serving_rallies', 0) or 0)
                        set_serving_points_won = float(rot_stats.get('serving_points_won', 0) or 0)
                        serving_rallies_total += set_serving_rallies
                        serving_points_won_total += set_serving_points_won
                        
                        # Get receiving data for this rotation in this set
                        set_receiving_rallies = float(rot_stats.get('receiving_rallies', 0) or 0)
                        set_receiving_points_won = float(rot_stats.get('receiving_points_won', 0) or 0)
                        receiving_rallies_total += set_receiving_rallies
                        receiving_points_won_total += set_receiving_points_won
                        
                        # Add to rotation points total
                        rotation_points += set_serving_rallies + set_receiving_rallies
        else:
            # Fallback: count points from dataframe for this rotation
            rotation_data = filtered_df[filtered_df['rotation'] == rotation]
            if 'point_id' in rotation_data.columns:
                rotation_points = float(rotation_data['point_id'].nunique())
            else:
                # Fallback: count by set and point
                rotation_points = float(len(rotation_data.groupby(['set_number', 'point_id']).size()) if 'point_id' in rotation_data.columns else len(rotation_data.groupby(['set_number', 'point']).size()))
        
        # Calculate rates - avoid division by zero
        # Track whether we have data for each metric
        has_serving_data = serving_rallies_total > 0
        has_receiving_data = receiving_rallies_total > 0
        
        # Use centralized calculation methods
        from services.kpi_calculator import KPICalculator
        serving_point_rate = KPICalculator.calculate_break_point_rate_from_totals(
            int(serving_points_won_total), int(serving_rallies_total)
        ) if has_serving_data else None
        receiving_point_rate = KPICalculator.calculate_side_out_efficiency_from_totals(
            int(receiving_points_won_total), int(receiving_rallies_total)
        ) if has_receiving_data else None
        
        # Kill Percentage: Attack kills / total attacks (from filtered dataframe)
        attacks = rotation_data[rotation_data['action'] == 'attack']
        attack_kills = len(attacks[attacks['outcome'] == 'kill'])
        attack_attempts = len(attacks)
        has_attack_data = attack_attempts > 0
        kill_percentage = KPICalculator.calculate_attack_kill_pct_from_totals(
            attack_kills, attack_attempts
        ) if has_attack_data else None
        
        # Reception Quality: Use aggregated reception data from Excel sheets (more accurate)
        # The Excel sheets have Reception_Good and Reception_Total columns per rotation
        reception_good_total = 0.0
        reception_total = 0.0
        
        if loader is not None:
            # Try to read from Excel file first (if it exists and is accessible)
            import os
            excel_file_path = None
            if hasattr(loader, 'excel_file') and loader.excel_file:
                excel_file_path = os.path.abspath(loader.excel_file) if loader.excel_file else None
                if not (excel_file_path and os.path.exists(excel_file_path)):
                    excel_file_path = None  # File doesn't exist, will use fallback
            
            sets_to_check = [selected_set_num] if selected_set_num is not None else played_sets
            
            # Try reading from Excel file if accessible
            if excel_file_path:
                for set_num in sets_to_check:
                    try:
                        sheet_name = f'Set{set_num}-Rot{rotation_int}'
                        df_rot = None
                        
                        try:
                            df_rot = pd.read_excel(excel_file_path, sheet_name=sheet_name)
                        except Exception:
                            xl_file = pd.ExcelFile(excel_file_path)
                            matching_sheets = [s for s in xl_file.sheet_names 
                                             if s.startswith(f'Set{set_num}-Rot{rotation_int}')]
                            if matching_sheets:
                                df_rot = pd.read_excel(excel_file_path, sheet_name=matching_sheets[0])
                        
                        if df_rot is not None and 'Reception_Good' in df_rot.columns and 'Reception_Total' in df_rot.columns:
                            set_reception_good = df_rot['Reception_Good'].sum()
                            set_reception_total = df_rot['Reception_Total'].sum()
                            reception_good_total += float(set_reception_good)
                            reception_total += float(set_reception_total)
                    except Exception:
                        continue
            
            # If Excel file not accessible, try using reception_data_by_rotation if available
            if reception_total == 0 and hasattr(loader, 'reception_data_by_rotation'):
                for set_num in sets_to_check:
                    if set_num in loader.reception_data_by_rotation:
                        if rotation_int in loader.reception_data_by_rotation[set_num]:
                            rot_rec_data = loader.reception_data_by_rotation[set_num][rotation_int]
                            reception_good_total += float(rot_rec_data.get('good', 0) or 0)
                            reception_total += float(rot_rec_data.get('total', 0) or 0)
        
        # Use aggregated Excel data if available, otherwise fallback to action rows
        has_reception_data = False
        if reception_total > 0:
            # Use aggregated Excel data (accurate)
            reception_quality = (reception_good_total / reception_total)
            has_reception_data = True
        else:
            # Fallback: Count from action rows (less accurate due to distribution)
            receives = rotation_data[rotation_data['action'] == 'receive']
            good_receives = len(filter_good_receptions(receives))
            total_receives = len(receives)
            has_reception_data = total_receives > 0
            reception_quality = (good_receives / total_receives) if has_reception_data else None
        
        # Debug: Log if we're using Excel data vs fallback
        if reception_total > 0:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Rotation {rotation} Reception Quality: Using Excel data - {reception_good_total}/{reception_total} = {reception_quality:.2%}")
        
        # Usage Frequency: Points played in this rotation / total points across all rotations
        has_usage_data = total_points_all_rotations > 0 and rotation_points > 0
        usage_frequency = (rotation_points / total_points_all_rotations) if has_usage_data else None
        
        enhanced_stats[rotation] = {
            'serving_point_rate': serving_point_rate,
            'receiving_point_rate': receiving_point_rate,
            'kill_percentage': kill_percentage,
            'reception_quality': reception_quality,
            'usage_frequency': usage_frequency,
            # Track which metrics have data
            '_has_serving_data': has_serving_data,
            '_has_receiving_data': has_receiving_data,
            '_has_attack_data': has_attack_data,
            '_has_reception_data': has_reception_data,
            '_has_usage_data': has_usage_data
        }
    
    # Prepare heatmap data (including usage frequency as a column)
    metrics = ['serving_point_rate', 'receiving_point_rate', 'kill_percentage', 'reception_quality', 'usage_frequency']
    metric_labels = ['Serving Point Rate', 'Receiving Point Rate', 'Kill %', 'Reception Quality', 'Usage Frequency']
    
    # Prepare heatmap data with proper handling of None values (no data)
    # Note: Usage Frequency (index 4) should NOT be color-coded - values are always 15-25%
    # We'll use actual percentage values (0-100%) with a unified color scale
    # that makes sense for volleyball performance metrics
    heatmap_data = []
    heatmap_text = []
    
    for rotation in rotations:
        row_data = []
        row_text = []
        for metric_idx, metric in enumerate(metrics):
            value = enhanced_stats[rotation].get(metric)
            if value is None:
                # No data available - use NaN for heatmap (will show as gray/empty)
                row_data.append(float('nan'))
                row_text.append("N/A")
            else:
                # Store as percentage (0-100) for consistent color scale
                row_data.append(value * 100)  # Convert to percentage
                # Format as percentage for display
                row_text.append(f"{value:.1%}")
        heatmap_data.append(row_data)
        heatmap_text.append(row_text)
    
    # Create heatmap with unified color scale based on actual percentage values
    # Color thresholds for volleyball performance:
    # 0-30%: Red (poor performance)
    # 30-50%: Orange/Yellow (below average)
    # 50-70%: Light Green (good performance)
    # 70-100%: Green (excellent performance)
    # Usage Frequency column (index 4) will remain uncolored (NaN)
    
    # Set Usage Frequency values to NaN so they don't get colored
    for row_idx in range(len(heatmap_data)):
        if len(heatmap_data[row_idx]) > 4:
            heatmap_data[row_idx][4] = float('nan')  # Usage Frequency - no color coding
    
    # Helper function to get players in a rotation
    def get_players_in_rotation(rotation: int, loader, set_num: Optional[int] = None) -> str:
        """Get players in a rotation based on starting formation.
        
        Rotation 1 mapping (standard):
        - Position 1: Setter (S)
        - Position 2: Outside Hitter 1 (OH1)
        - Position 3: Middle Blocker 1 (MB1)
        - Position 4: Opposite (OPP)
        - Position 5: Outside Hitter 2 (OH2)
        - Position 6: Middle Blocker 2 (MB2)
        
        As rotation changes, players rotate counter-clockwise.
        Libero replaces MB in back row (positions 1, 5, 6).
        """
        if loader is None or not hasattr(loader, 'player_data_by_set'):
            return "N/A"
        
        # Get starting formation from first set or specified set
        sets_to_check = [set_num] if set_num else list(loader.player_data_by_set.keys())
        if not sets_to_check:
            return "N/A"
        
        first_set = sets_to_check[0]
        if first_set not in loader.player_data_by_set:
            return "N/A"
        
        # Build position to player mapping from player_data_by_set
        # Position codes: S, OH1, OH2, MB1, MB2, OPP, L
        position_to_player = {}
        libero_name = None
        
        for player_name, player_info in loader.player_data_by_set[first_set].items():
            position = player_info.get('position', '')
            if position == 'L':
                libero_name = player_name
            else:
                position_to_player[position] = player_name
        
        # Rotation 1 mapping (standard starting formation)
        rotation_1_mapping = {
            1: 'S',    # Setter
            2: 'OH1',  # Outside Hitter 1
            3: 'MB1',  # Middle Blocker 1
            4: 'OPP',  # Opposite
            5: 'OH2',  # Outside Hitter 2
            6: 'MB2',  # Middle Blocker 2
        }
        
        # Calculate which positions are in each court position for this rotation
        # Rotation number = setter's position
        # Players rotate counter-clockwise as rotation increases
        players_on_court = []
        
        for court_pos in range(1, 7):
            # Calculate offset from rotation 1
            # Rotation 1: setter at pos 1, offset = 0
            # Rotation 2: setter at pos 2, offset = 1 (one CCW)
            # Rotation 6: setter at pos 6, offset = 5 (five CCW)
            offset = (rotation - 1) % 6
            
            # Calculate which base position is at this court position
            # Formula: base_pos = ((court_pos - 1 - offset + 6) % 6) + 1
            base_pos = ((court_pos - rotation + 6) % 6) + 1
            position_code = rotation_1_mapping.get(base_pos)
            
            if position_code:
                # Check if this is a back row position where libero might play
                is_back_row = court_pos in [1, 5, 6]
                is_serving_pos = court_pos == 1
                
                # Libero replaces MB in back row (except when serving at pos 1)
                if (position_code in ['MB1', 'MB2'] and is_back_row and 
                    libero_name and not is_serving_pos):
                    player_name = libero_name
                else:
                    player_name = position_to_player.get(position_code, '')
                
                if player_name:
                    # Format: "Pos X: Player Name"
                    pos_label = f"Pos {court_pos}"
                    players_on_court.append(f"{pos_label}: {player_name}")
        
        if players_on_court:
            return "<br>".join(players_on_court)
        return "N/A"
    
    # Build hover templates with player information (no court visualization in hover)
    # Create a mapping of rotation to players for hover display
    rotation_players_map = {}
    for rotation in rotations:
        players_info = get_players_in_rotation(rotation, loader, selected_set_num)
        rotation_players_map[rotation] = players_info
    
    # Build custom hover data - 2D array of formatted strings matching heatmap dimensions
    hover_customdata = []
    for rot_idx, rotation in enumerate(rotations):
        row_data = []
        players_info = rotation_players_map.get(rotation, "N/A")
        for metric_idx, metric_label in enumerate(metric_labels):
            if metric_idx < len(heatmap_text[rot_idx]):
                value_text = heatmap_text[rot_idx][metric_idx]
                # Format hover text with player information (simple text only)
                hover_text = f'<b>Rotation {rotation}</b><br>{metric_label}: {value_text}'
                if players_info != "N/A":
                    hover_text += f'<br><br><b>Players:</b><br>{players_info}'
                hover_text += '<extra></extra>'
                row_data.append(hover_text)
            else:
                row_data.append('')
        hover_customdata.append(row_data)
    
    # Create heatmap with improved color scale (diverging: red → white → green centered on targets)
    # Target-based colorscale: 
    # - Below 50%: Red shades
    # - Around 50%: White/light
    # - Above 50%: Green shades
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=heatmap_data,
        x=metric_labels,
        y=[f"Rotation {r}" for r in rotations],
        colorscale=[
            [0.0, '#DC3545'],    # Red (0%)
            [0.3, '#FF6B6B'],    # Light red (30%)
            [0.45, '#FFE66D'],   # Yellow (45%)
            [0.5, '#FFFFFF'],    # White (50% - target center)
            [0.55, '#C8E6C9'],   # Light green (55%)
            [0.7, '#81C784'],    # Green (70%)
            [1.0, '#4CAF50']     # Dark green (100%)
        ],
        text=heatmap_text,
        texttemplate="%{text}",
        textfont={"size": 14, "color": "#2C3E50", "family": "Arial, sans-serif"},
        colorbar=dict(
            title="Performance Rate (%)",
            tickmode='linear',
            tick0=0,
            dtick=20,
            tickformat='.0f'
        ),
        hovertemplate='%{customdata}',
        customdata=hover_customdata,
        showscale=True,
        zmin=0,   # Minimum value (0%)
        zmax=100, # Maximum value (100%)
        zmid=50,  # Center the color scale at 50% (target)
        # Add borders for cell separation
        xgap=2,
        ygap=2
    ))
    
    # Update title based on filter
    heatmap_title = "Rotation Performance Heatmap"
    if selected_set_num is not None:
        heatmap_title += f" - Set {selected_set_num}"
    
    # Calculate height to roughly match court visualization (350px) + buttons + title
    # Court visualization is ~350px, buttons + title ~100px, total ~450px
    # Adjust heatmap to be similar height
    target_height = 450  # Match court visualization area
    heatmap_height = max(target_height, len(rotations) * 60)  # Minimum per rotation but cap if too tall
    
    fig_heatmap.update_layout(
        title=heatmap_title,
        xaxis_title="Metric",
        yaxis_title="Rotation",
        height=heatmap_height,
        font=dict(family='Inter, sans-serif', size=12, color='#050d76'),
        paper_bgcolor='rgba(255,255,255,0)',
        plot_bgcolor='rgba(255,255,255,0.95)',
        xaxis=dict(tickfont=dict(color='#050d76', size=13)),
        yaxis=dict(tickfont=dict(color='#050d76', size=13)),
        # Increase margins for better spacing
        margin=dict(l=80, r=120, t=60, b=60)
    )
    
    fig_heatmap = apply_beautiful_theme(fig_heatmap, heatmap_title)
    
    # Initialize session state for selected rotation (before columns)
    rotation_key = f"selected_rotation_{selected_set_num if selected_set_num else 'all'}"
    if rotation_key not in st.session_state:
        st.session_state[rotation_key] = rotations[0] if rotations else 1
    
    selected_rotation = st.session_state[rotation_key]
    
    # CSS for beautiful radio buttons and perfectly aligned columns
    st.markdown("""
    <style>
    /* Remove gap between "Select Rotation:" text and radio buttons */
    div[data-testid="stMarkdownContainer"]:has(+ div[data-testid="stRadio"]) {
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
    }
    div[data-testid="stMarkdownContainer"]:has(+ div[data-testid="stRadio"]) p {
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
    }
    /* Remove spacing from radio button container and its wrappers */
    div[data-testid="stRadio"],
    div[data-testid="stRadio"] .element-container,
    div[data-testid="stRadio"] .row-widget {
        margin-top: 0 !important;
        padding-top: 0 !important;
        margin-bottom: 0 !important;
        padding-bottom: 0 !important;
    }
    /* AGGRESSIVELY hide the label wrapper that creates the empty box - target everything */
    div[data-testid="stRadio"] > div:first-child,
    div[data-testid="stRadio"] > div:first-of-type,
    div[data-testid="stRadio"] .element-container > div:first-child,
    div[data-testid="stRadio"] .element-container > div:first-of-type,
    div[data-testid="stRadio"] .row-widget > div:first-child:not(:has(input[type="radio"])),
    div[data-testid="stRadio"] .row-widget > div:first-of-type:not(:has(input[type="radio"])),
    div[data-testid="stRadio"] .stRadio > div:first-child:not(:has(input)),
    /* Hide any div that only contains labels (not radio inputs) */
    div[data-testid="stRadio"] > div:has(> label:not(:has(input))),
    div[data-testid="stRadio"] .element-container > div:has(> label:not(:has(input))) {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        max-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }
    /* Hide empty collapsed label FIRST - only target empty labels, not the actual radio buttons */
    div[data-testid="stRadio"] > div:first-child label,
    div[data-testid="stRadio"] .element-container > div:first-child label,
    div[data-testid="stRadio"] .row-widget > div:first-child label,
    div[data-testid="stRadio"] label:empty,
    div[data-testid="stRadio"] [data-baseweb="typo-label"]:empty {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        max-height: 0 !important;
        visibility: hidden !important;
        opacity: 0 !important;
        line-height: 0 !important;
        font-size: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }
    /* Hide wrapper divs that contain collapsed labels - more aggressive targeting */
    div[data-testid="stRadio"] > div:has(> label:empty),
    div[data-testid="stRadio"] > div:has(> label[data-baseweb="typo-label"]:empty),
    div[data-testid="stRadio"] .element-container > div:first-child:has(label:empty),
    div[data-testid="stRadio"] .element-container > div:first-child:has(label[data-baseweb="typo-label"]:empty),
    div[data-testid="stRadio"] .row-widget > div:first-child:has(label:empty),
    div[data-testid="stRadio"] .stRadio > div:first-child:not(:has(input)),
    div[data-testid="stRadio"] .stRadio > div:first-child:has(label:empty) {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        max-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }
    /* Target any first-child elements that might be empty containers */
    div[data-testid="stRadio"] .element-container > div:first-child,
    div[data-testid="stRadio"] .row-widget > div:first-child {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
        padding-top: 0 !important;
        padding-bottom: 0 !important;
    }
    /* If first child only contains empty/hidden label, hide the whole container */
    div[data-testid="stRadio"] .element-container > div:first-child:has(> label:empty):only-child {
        display: none !important;
        height: 0 !important;
    }
    /* Radio button labels - ONLY style labels that are siblings of radio inputs (not the empty collapsed label) */
    div[data-testid="stRadio"] input[type="radio"] + label,
    div[data-testid="stRadio"] label:has(+ input[type="radio"]),
    div[data-testid="stRadio"] .row-widget label:has(~ input),
    div[data-testid="stRadio"] .stRadio label:has(~ input[type="radio"]) {
        margin: 0 !important;
        padding: 0.5rem 1rem !important;
        font-size: 0.9rem !important;
        min-height: 2.2rem !important;
        height: auto !important;
        line-height: 1.2 !important;
        border: 2px solid #e5e7eb !important;
        background: linear-gradient(to bottom, #ffffff, #f9fafb) !important;
        border-radius: 10px !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        cursor: pointer !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        font-weight: 600 !important;
        color: #374151 !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08) !important;
        min-width: 2.8rem !important;
    }
    div[data-testid="stRadio"] label:hover {
        border-color: #050d76 !important;
        background: linear-gradient(to bottom, #ffffff, #f3f4f6) !important;
        box-shadow: 0 4px 8px rgba(5, 13, 118, 0.15) !important;
        transform: translateY(-2px) scale(1.02) !important;
    }
    div[data-testid="stRadio"] input[type="radio"]:checked + label {
        border: 2.5px solid #050d76 !important;
        color: #050d76 !important;
        font-weight: 700 !important;
        background: linear-gradient(to bottom, #eff6ff, #dbeafe) !important;
        box-shadow: 0 4px 12px rgba(5, 13, 118, 0.3) !important;
        transform: translateY(-2px) scale(1.05) !important;
    }
    /* Hide radio button circles completely */
    div[data-testid="stRadio"] input[type="radio"] {
        position: absolute !important;
        opacity: 0 !important;
        width: 0 !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    /* Column alignment - simplified */
    div[data-testid="column"]:first-child {
        align-items: flex-start !important;
    }
    /* Center court visualization - simplified approach */
    div[data-testid="column"]:nth-child(2) {
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    /* Let Plotly handle its own sizing, just ensure it's centered */
    div[data-testid="column"]:nth-child(2) .js-plotly-plot {
        margin: 0 auto !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
    }
    /* Center the SVG container within the plotly plot */
    div[data-testid="column"]:nth-child(2) .js-plotly-plot > div.plot-container {
        margin: 0 auto !important;
        display: flex !important;
        justify-content: center !important;
        align-items: center !important;
        width: 100% !important;
    }
    div[data-testid="column"]:nth-child(2) .svg-container {
        margin: 0 auto !important;
        position: relative !important;
        left: 0 !important;
        transform: translateX(0) !important;
        text-align: left !important;
    }
    /* Shift the entire plotly chart container slightly left to center it */
    div[data-testid="column"]:nth-child(2) div[data-testid="stPlotlyChart"] {
        margin-left: -15px !important;
        padding-left: 0 !important;
    }
    /* Ensure plot container uses full width and centers content */
    div[data-testid="column"]:nth-child(2) .plot-container {
        width: 100% !important;
        display: flex !important;
        justify-content: center !important;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Rotation selector above both columns - using compact radio buttons
    st.markdown("**Select Rotation:**")
    
    # Use horizontal radio buttons styled as compact buttons
    # Filter to only show available rotations, or show all if needed
    rotation_options = [str(r) for r in range(1, 7)]
    # Find the index of the selected rotation in the options
    try:
        selected_index = rotation_options.index(str(selected_rotation))
    except ValueError:
        selected_index = 0
    
    selected = st.radio(
        "",
        options=rotation_options,
        index=selected_index,
        key=f"rotation_radio_{selected_set_num if selected_set_num else 'all'}",
        horizontal=True,
        label_visibility="collapsed"
    )
    
    if selected and int(selected) != selected_rotation:
        st.session_state[rotation_key] = int(selected)
        st.rerun()
    
    # Create two columns: heatmap on left, court visualization on right
    col_heatmap, col_right = st.columns([2, 1])
    
    with col_heatmap:
        st.plotly_chart(fig_heatmap, use_container_width=True, config=plotly_config, key=f"rotation_heatmap_{selected_set_num if selected_set_num else 'all'}")
    
    with col_right:
        # Render court visualization for selected rotation with matching height
        # The CSS above handles centering and alignment
        selected_rotation_for_court = st.session_state[rotation_key]
        if selected_rotation_for_court in rotations:
            _render_rotation_court(selected_rotation_for_court, loader, selected_set_num, height=heatmap_height)
        else:
            st.info("Select a rotation to view court layout")
    
    # Rotation Usage Frequency removed - now integrated into heatmap above


def _render_rotation_court(rotation: int, loader, set_num: Optional[int] = None, height: Optional[int] = None) -> None:
    """Render a small volleyball court visualization for a specific rotation.
    
    Args:
        rotation: Rotation number to visualize
        loader: EventTrackerLoader instance
        set_num: Optional set number to filter by
        height: Optional height to match with heatmap
    """
    if loader is None or not hasattr(loader, 'player_data_by_set'):
        st.info("Court visualization not available")
        return
    
    # Get starting formation from first set or specified set
    sets_to_check = [set_num] if set_num else list(loader.player_data_by_set.keys())
    if not sets_to_check:
        st.info("No set data available")
        return
    
    first_set = sets_to_check[0]
    if first_set not in loader.player_data_by_set:
        st.info("No set data available")
        return
    
    # Build position to player mapping
    position_to_player = {}
    libero_name = None
    
    for player_name, player_info in loader.player_data_by_set[first_set].items():
        position = player_info.get('position', '')
        if position == 'L':
            libero_name = player_name
        else:
            position_to_player[position] = player_name
    
    # Rotation 1 mapping (standard starting formation)
    rotation_1_mapping = {
        1: 'S',    # Setter
        2: 'OH1',  # Outside Hitter 1
        3: 'MB1',  # Middle Blocker 1
        4: 'OPP',  # Opposite
        5: 'OH2',  # Outside Hitter 2
        6: 'MB2',  # Middle Blocker 2
    }
    
    # Create Plotly figure
    fig = go.Figure()
    
    # Court dimensions for trapezoid (half court view from behind)
    court_top_width = 9  # Width at net (shorter)
    court_bottom_width = 12  # Width at back line (wider)
    court_depth = 9  # Depth of court
    
    # Center coordinates
    center_x = 0
    court_top_y = court_depth  # Top of court (net line)
    court_bottom_y = 0  # Bottom of court (back line)
    
    # Trapezoid vertices (counter-clockwise from top-left)
    trapezoid_x = [
        center_x - court_top_width / 2,  # Top left
        center_x + court_top_width / 2,  # Top right
        center_x + court_bottom_width / 2,  # Bottom right
        center_x - court_bottom_width / 2,  # Bottom left
        center_x - court_top_width / 2  # Close the shape
    ]
    trapezoid_y = [
        court_top_y,  # Top left
        court_top_y,  # Top right
        court_bottom_y,  # Bottom right
        court_bottom_y,  # Bottom left
        court_top_y  # Close the shape
    ]
    
    # Draw trapezoid court background
    fig.add_trace(go.Scatter(
        x=trapezoid_x,
        y=trapezoid_y,
        fill='toself',
        fillcolor='rgba(219, 231, 255, 0.5)',  # Light blue background
        line=dict(color='#050d76', width=2),
        mode='lines',
        showlegend=False,
        hoverinfo='skip'
    ))
    
    # Net line at top
    fig.add_shape(
        type="line",
        x0=center_x - court_top_width / 2,
        y0=court_top_y,
        x1=center_x + court_top_width / 2,
        y1=court_top_y,
        line=dict(color='#050d76', width=2, dash="dash"),
        layer="below"
    )
    
    # Position coordinates on trapezoidal court
    # Positions arranged: 4-3-2 (front), 5-6-1 (back)
    position_coords = {
        1: {'x': center_x + court_bottom_width / 2 - 1.2, 'y': court_bottom_y + 1.2, 'label': '1'},  # Back right
        2: {'x': center_x + court_top_width / 2 - 1.2, 'y': court_top_y - 1.2, 'label': '2'},  # Front right
        3: {'x': center_x, 'y': court_top_y - 1.2, 'label': '3'},  # Front center
        4: {'x': center_x - court_top_width / 2 + 1.2, 'y': court_top_y - 1.2, 'label': '4'},  # Front left
        5: {'x': center_x - court_bottom_width / 2 + 1.2, 'y': court_bottom_y + 1.2, 'label': '5'},  # Back left
        6: {'x': center_x, 'y': court_bottom_y + 1.2, 'label': '6'},  # Back center
    }
    
    # Calculate players for each court position in this rotation
    for court_pos in range(1, 7):
        pos_data = position_coords[court_pos]
        x = pos_data['x']
        y = pos_data['y']
        
        # Calculate which base position is at this court position
        base_pos = ((court_pos - rotation + 6) % 6) + 1
        position_code = rotation_1_mapping.get(base_pos)
        
        if position_code:
            # Check if this is a back row position where libero might play
            is_back_row = court_pos in [1, 5, 6]
            is_serving_pos = court_pos == 1
            
            # Libero replaces MB in back row (except when serving at pos 1)
            if (position_code in ['MB1', 'MB2'] and is_back_row and 
                libero_name and not is_serving_pos):
                player_name = libero_name
            else:
                player_name = position_to_player.get(position_code, '')
            
            # Check if this is the setter position
            is_setter = (position_code == 'S')
            
            # Truncate player name if too long
            display_name = player_name if player_name else f"Pos {court_pos}"
            if len(display_name) > 10:
                display_name = display_name[:8] + ".."
            
            # Color and size based on setter position
            if is_setter:
                circle_color = "#e21b39"  # Brand red for setter
                circle_size = 45
            else:
                circle_color = "#050d76"  # Brand dark blue for other players
                circle_size = 40
            
            # Add circle
            fig.add_trace(go.Scatter(
                x=[x],
                y=[y],
                mode='markers+text',
                marker=dict(
                    size=circle_size,
                    color=circle_color,
                    line=dict(width=2, color='white'),
                    opacity=0.9
                ),
                text=[pos_data['label']],
                textposition="middle center",
                textfont=dict(size=14, color='white', family='Arial Black'),
                name=f"Position {court_pos}",
                hovertext=f"Position {court_pos}<br>{display_name}",
                hoverinfo='text',
                showlegend=False
            ))
            
            # Add player name below position number
            if player_name:
                fig.add_annotation(
                    x=x,
                    y=y - 0.7,
                    text=display_name,
                    showarrow=False,
                    font=dict(size=9, color='white', family='Arial'),
                    bgcolor=circle_color,
                    bordercolor='white',
                    borderwidth=1,
                    borderpad=2,
                    xref="x",
                    yref="y"
                )
            
            # Highlight setter position with ring
            if is_setter:
                fig.add_shape(
                    type="circle",
                    xref="x",
                    yref="y",
                    x0=x - 0.5,
                    y0=y - 0.5,
                    x1=x + 0.5,
                    y1=y + 0.5,
                    line=dict(color="#dbe7ff", width=2, dash="dash"),
                    layer="above"
                )
    
    # Update layout with proper margins and centering
    fig.update_layout(
        title=dict(
            text=f"Rotation {rotation}",
            font=dict(size=14, color='#050d76', family='Arial'),
            x=0.5,
            xanchor='center'
        ),
        xaxis=dict(
            range=[center_x - court_bottom_width * 0.65, center_x + court_bottom_width * 0.65],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            title="",
            fixedrange=True
        ),
        yaxis=dict(
            range=[court_bottom_y - court_depth * 0.2, court_top_y + court_depth * 0.2],
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            title="",
            scaleanchor="x",
            scaleratio=1,
            fixedrange=True
        ),
        height=height if height else 350,
        showlegend=False,
        paper_bgcolor='rgba(255,255,255,0)',
        plot_bgcolor='rgba(255,255,255,0.98)',
        margin=dict(l=5, r=5, t=50, b=10),
        autosize=True
    )
    
    # Apply beautiful theme but override margins to keep them small and centered
    fig = apply_beautiful_theme(fig)
    fig.update_layout(margin=dict(l=5, r=5, t=50, b=10), autosize=True)
    
    # Display the chart centered and constrained
    st.plotly_chart(fig, use_container_width=True, config={
        'displayModeBar': False,
        'responsive': True,
        'autosizable': True
    })


def _create_attacking_performance_charts(df: pd.DataFrame, analyzer: MatchAnalyzer, loader=None) -> None:
    """Create all attacking performance charts for Section 4.
    
    Includes:
    - Attack Type Distribution (4 donut charts: All Sets + one per set)
    - Attack Quality Distribution by Set (4 donut charts: All Sets + one per set)
    """
    # 1. Attack Type Distribution - 4 donut charts (All Sets + one per set)
    st.markdown("#### Attack Type Distribution")
    played_sets = get_played_sets(df, loader)
    from utils.breakdown_helpers import get_attack_breakdown_by_type
    
    # Create 4 columns: All Sets + one for each set
    all_sets_option = ['All Sets'] + [f'Set {s}' for s in played_sets]
    cols = st.columns(4)
    
    # Fixed order for consistent legend: Normal, Tip
    attack_type_order = ['Normal', 'Tip']
    attack_type_color_map = {
        'Normal': ATTACK_TYPE_COLORS['normal'],
        'Tip': ATTACK_TYPE_COLORS['tip']
    }
    
    for idx, set_option in enumerate(all_sets_option[:4]):  # Limit to 4 columns
        with cols[idx]:
            if set_option == 'All Sets':
                filtered_df = df
                title = "All Sets"
            else:
                set_num = int(set_option.split()[-1])
                filtered_df = df[df['set_number'] == set_num]
                title = set_option
            
            breakdown = get_attack_breakdown_by_type(filtered_df, loader)
            
            if breakdown:
                normal_total = breakdown['normal']['total']
                tip_total = breakdown['tip']['total']
                total_attacks = normal_total + tip_total
                
                if total_attacks > 0:
                    # Build labels/values/colors in fixed order for consistent legend
                    labels = []
                    values = []
                    colors = []
                    
                    type_data = {
                        'Normal': normal_total,
                        'Tip': tip_total
                    }
                    
                    for attack_type in attack_type_order:
                        count = type_data[attack_type]
                        if count > 0:
                            labels.append(attack_type)
                            values.append(count)
                            colors.append(attack_type_color_map[attack_type])
                    
                    if labels:
                        fig = go.Figure(data=[go.Pie(
                            labels=labels,
                            values=values,
                            hole=0.4,
                            marker=dict(colors=colors, line=dict(color='white', width=2)),
                            textinfo='percent',  # Only show percentage, not label names
                            textfont=dict(size=14, color='#050d76', family='Inter, sans-serif'),  # Larger font for percentages
                            hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
                        )])
                        fig.update_layout(
                            title=f"{title} (n={total_attacks})",
                            height=CHART_HEIGHTS['large'],  # Larger chart
                            showlegend=True,
                            legend=dict(
                                orientation="v",
                                yanchor="top",
                                y=1,
                                xanchor="left",
                                x=1.02,
                                itemsizing='constant'  # Consistent legend item sizing
                            ),
                            margin=dict(l=0, r=100, t=50, b=0),  # Reduce margins for bigger chart
                            font=dict(family='Inter, sans-serif', size=11, color='#050d76')
                        )
                        fig = apply_beautiful_theme(fig, f"{title} Attack Types")
                        st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"attack_type_donut_{set_option.replace(' ', '_')}")
    
    # 2. Attack Quality Distribution by Set - 4 donut charts (All Sets + one per set)
    st.markdown("#### Attack Quality Distribution by Set")
    
    # Fixed order for consistent legend: Kills, Good (Defended), Errors
    quality_order = ['Kills', 'Good (Defended)', 'Errors']
    quality_color_map = {
        'Kills': OUTCOME_COLORS['kill'],
        'Good (Defended)': OUTCOME_COLORS['good'],
        'Errors': OUTCOME_COLORS['error']
    }
    
    # Prepare data for all sets combined
    all_attacks = df[df['action'] == 'attack']
    all_kills = len(all_attacks[all_attacks['outcome'] == 'kill'])
    all_defended = len(all_attacks[all_attacks['outcome'] == 'defended'])
    all_errors = (
        len(all_attacks[all_attacks['outcome'] == 'blocked']) +
        len(all_attacks[all_attacks['outcome'] == 'out']) +
        len(all_attacks[all_attacks['outcome'] == 'net'])
        # 'error' removed - all errors covered by 'blocked', 'out', 'net'
    )
    all_total = all_kills + all_defended + all_errors
    
    # Create 4 columns: All Sets + one for each set
    cols = st.columns(4)
    
    # All Sets donut chart
    with cols[0]:
        if all_total > 0:
            labels = []
            values = []
            colors = []
            
            quality_data = {
                'Kills': all_kills,
                'Good (Defended)': all_defended,
                'Errors': all_errors
            }
            
            for quality_type in quality_order:
                count = quality_data[quality_type]
                if count > 0:
                    labels.append(quality_type)
                    values.append(count)
                    colors.append(quality_color_map[quality_type])
            
            if labels:
                fig = go.Figure(data=[go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.4,
                    marker=dict(colors=colors, line=dict(color='white', width=2)),
                    textinfo='percent',  # Only show percentage, not label names
                    textfont=dict(size=14, color='#050d76', family='Inter, sans-serif'),  # Larger font for percentages
                    hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
                )])
                fig.update_layout(
                    title=f"All Sets (n={all_total})",
                    height=CHART_HEIGHTS['large'],  # Larger chart
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=1,
                        xanchor="left",
                        x=1.02,
                        itemsizing='constant'  # Consistent legend item sizing
                    ),
                    margin=dict(l=0, r=100, t=50, b=0),  # Reduce margins for bigger chart
                    font=dict(family='Inter, sans-serif', size=11, color='#050d76')
                )
                fig = apply_beautiful_theme(fig, "All Sets Attack Quality")
                st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="attack_quality_donut_all")
    
    # Individual set donut charts
    for idx, set_num in enumerate(played_sets[:3], start=1):  # Limit to 3 sets (plus "All Sets" = 4 total)
        if idx >= len(cols):
            break
        with cols[idx]:
            set_df = df[df['set_number'] == set_num]
            attacks = set_df[set_df['action'] == 'attack']
            
            kills = len(attacks[attacks['outcome'] == 'kill'])
            defended = len(attacks[attacks['outcome'] == 'defended'])
            errors = (
                len(attacks[attacks['outcome'] == 'blocked']) +
                len(attacks[attacks['outcome'] == 'out']) +
                len(attacks[attacks['outcome'] == 'net']) +
                len(attacks[attacks['outcome'] == 'error'])
            )
            total = kills + defended + errors
            
            if total > 0:
                labels = []
                values = []
                colors = []
                
                quality_data = {
                    'Kills': kills,
                    'Good (Defended)': defended,
                    'Errors': errors
                }
                
                for quality_type in quality_order:
                    count = quality_data[quality_type]
                    if count > 0:
                        labels.append(quality_type)
                        values.append(count)
                        colors.append(quality_color_map[quality_type])
                
                if labels:
                    fig = go.Figure(data=[go.Pie(
                        labels=labels,
                        values=values,
                        hole=0.4,
                        marker=dict(colors=colors, line=dict(color='white', width=2)),
                        textinfo='percent',  # Only show percentage, not label names
                        textfont=dict(size=14, color='#050d76', family='Inter, sans-serif'),  # Larger font for percentages
                        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
                    )])
                    fig.update_layout(
                        title=f"Set {set_num} (n={total})",
                        height=CHART_HEIGHTS['large'],  # Larger chart
                        showlegend=True,
                        legend=dict(
                            orientation="v",
                            yanchor="top",
                            y=1,
                            xanchor="left",
                            x=1.02,
                            itemsizing='constant'  # Consistent legend item sizing
                        ),
                        margin=dict(l=0, r=100, t=50, b=0),  # Reduce margins for bigger chart
                        font=dict(family='Inter, sans-serif', size=11, color='#050d76')
                    )
                    fig = apply_beautiful_theme(fig, f"Set {set_num} Attack Quality")
                    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"attack_quality_donut_set_{set_num}")


def _create_reception_performance_charts(df: pd.DataFrame, loader=None) -> None:
    """Create all reception performance charts for Section 4.
    
    Includes:
    - Reception Performance by Set (4 donut charts: All Sets + one per set)
    """
    # Reception Performance by Set - 4 donut charts (All Sets + one per set)
    st.markdown("#### Reception Performance by Set")
    played_sets = get_played_sets(df, loader)
    
    # Fixed order for consistent legend: Perfect, Good, Poor, Error
    reception_order = ['Perfect', 'Good', 'Poor', 'Error']
    reception_color_map = {
        'Perfect': OUTCOME_COLORS['perfect'],
        'Good': OUTCOME_COLORS['good'],
        'Poor': OUTCOME_COLORS['poor'],
        'Error': OUTCOME_COLORS['error']
    }
    
    # Prepare data for all sets combined
    all_receives = df[df['action'] == 'receive']
    all_perfect = len(all_receives[all_receives['outcome'] == 'perfect'])
    all_good = len(all_receives[all_receives['outcome'] == 'good'])
    all_poor = len(all_receives[all_receives['outcome'] == 'poor'])
    all_error = len(all_receives[all_receives['outcome'] == 'error'])
    all_total = all_perfect + all_good + all_poor + all_error
    
    # Create 4 columns: All Sets + one for each set
    cols = st.columns(4)
    
    # All Sets donut chart
    with cols[0]:
        if all_total > 0:
            labels = []
            values = []
            colors = []
            
            reception_data = {
                'Perfect': all_perfect,
                'Good': all_good,
                'Poor': all_poor,
                'Error': all_error
            }
            
            for rec_type in reception_order:
                count = reception_data[rec_type]
                if count > 0:
                    labels.append(rec_type)
                    values.append(count)
                    colors.append(reception_color_map[rec_type])
            
            if labels:
                fig = go.Figure(data=[go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.4,
                    marker=dict(colors=colors, line=dict(color='white', width=2)),
                    textinfo='percent',  # Only show percentage, not label names
                    textfont=dict(size=14, color='#050d76', family='Inter, sans-serif'),  # Larger font for percentages
                    hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
                )])
                fig.update_layout(
                    title=f"All Sets (n={all_total})",
                    height=CHART_HEIGHTS['large'],  # Larger chart
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=1,
                        xanchor="left",
                        x=1.02,
                        itemsizing='constant'  # Consistent legend item sizing
                    ),
                    margin=dict(l=0, r=100, t=50, b=0),  # Reduce margins for bigger chart
                    font=dict(family='Inter, sans-serif', size=11, color='#050d76')
                )
                fig = apply_beautiful_theme(fig, "All Sets Reception")
                st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="reception_donut_all")
    
    # Individual set donut charts
    for idx, set_num in enumerate(played_sets[:3], start=1):  # Limit to 3 sets (plus "All Sets" = 4 total)
        if idx >= len(cols):
            break
        with cols[idx]:
            set_df = df[df['set_number'] == set_num]
            receives = set_df[set_df['action'] == 'receive']
            
            perfect = len(receives[receives['outcome'] == 'perfect'])
            good = len(receives[receives['outcome'] == 'good'])
            poor = len(receives[receives['outcome'] == 'poor'])
            error = len(receives[receives['outcome'] == 'error'])
            total = perfect + good + poor + error
            
            if total > 0:
                labels = []
                values = []
                colors = []
                
                reception_data = {
                    'Perfect': perfect,
                    'Good': good,
                    'Poor': poor,
                    'Error': error
                }
                
                for rec_type in reception_order:
                    count = reception_data[rec_type]
                    if count > 0:
                        labels.append(rec_type)
                        values.append(count)
                        colors.append(reception_color_map[rec_type])
                
                if labels:
                    fig = go.Figure(data=[go.Pie(
                        labels=labels,
                        values=values,
                        hole=0.4,
                        marker=dict(colors=colors, line=dict(color='white', width=2)),
                        textinfo='percent',  # Only show percentage, not label names
                        textfont=dict(size=14, color='#050d76', family='Inter, sans-serif'),  # Larger font for percentages
                        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
                    )])
                    fig.update_layout(
                        title=f"Set {set_num} (n={total})",
                        height=CHART_HEIGHTS['large'],  # Larger chart
                        showlegend=True,
                        legend=dict(
                            orientation="v",
                            yanchor="top",
                            y=1,
                            xanchor="left",
                            x=1.02,
                            itemsizing='constant'  # Consistent legend item sizing
                        ),
                        margin=dict(l=0, r=100, t=50, b=0),  # Reduce margins for bigger chart
                        font=dict(family='Inter, sans-serif', size=11, color='#050d76')
                    )
                    fig = apply_beautiful_theme(fig, f"Set {set_num} Reception")
                    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"reception_donut_set_{set_num}")


def _create_serving_performance_charts(df: pd.DataFrame, loader=None) -> None:
    """Create all serving performance charts for Section 4.
    
    Includes:
    - Serve Performance by Set (4 donut charts: All Sets + one per set)
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
    
    # Prepare data for all sets combined
    all_serves = df[df['action'] == 'serve']
    all_aces = len(all_serves[all_serves['outcome'] == 'ace'])
    all_good = len(all_serves[all_serves['outcome'] == 'good'])
    all_errors = len(all_serves[all_serves['outcome'] == 'error'])
    all_total = all_aces + all_good + all_errors
    
    # Create 4 columns: All Sets + one for each set
    cols = st.columns(4)
    
    # All Sets donut chart
    with cols[0]:
        if all_total > 0:
            labels = []
            values = []
            colors = []
            
            serve_data = {
                'Aces': all_aces,
                'Good': all_good,
                'Errors': all_errors
            }
            
            for serve_type in serve_order:
                count = serve_data[serve_type]
                if count > 0:
                    labels.append(serve_type)
                    values.append(count)
                    colors.append(serve_color_map[serve_type])
            
            if labels:
                fig = go.Figure(data=[go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.4,
                    marker=dict(colors=colors, line=dict(color='white', width=2)),
                    textinfo='percent',  # Only show percentage, not label names
                    textfont=dict(size=14, color='#050d76', family='Inter, sans-serif'),  # Larger font for percentages
                    hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
                )])
                fig.update_layout(
                    title=f"All Sets (n={all_total})",
                    height=CHART_HEIGHTS['large'],  # Larger chart
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=1,
                        xanchor="left",
                        x=1.02,
                        itemsizing='constant'  # Consistent legend item sizing
                    ),
                    margin=dict(l=0, r=100, t=50, b=0),  # Reduce margins for bigger chart
                    font=dict(family='Inter, sans-serif', size=11, color='#050d76')
                )
                fig = apply_beautiful_theme(fig, "All Sets Serve Performance")
                st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="serve_donut_all")
    
    # Individual set donut charts
    for idx, set_num in enumerate(played_sets[:3], start=1):  # Limit to 3 sets (plus "All Sets" = 4 total)
        if idx >= len(cols):
            break
        with cols[idx]:
            set_df = df[df['set_number'] == set_num]
            serves_set = set_df[set_df['action'] == 'serve']
            
            aces = len(serves_set[serves_set['outcome'] == 'ace'])
            good = len(serves_set[serves_set['outcome'] == 'good'])
            errors = len(serves_set[serves_set['outcome'] == 'error'])
            total = aces + good + errors
            
            if total > 0:
                labels = []
                values = []
                colors = []
                
                serve_data = {
                    'Aces': aces,
                    'Good': good,
                    'Errors': errors
                }
                
                for serve_type in serve_order:
                    count = serve_data[serve_type]
                    if count > 0:
                        labels.append(serve_type)
                        values.append(count)
                        colors.append(serve_color_map[serve_type])
                
                if labels:
                    fig = go.Figure(data=[go.Pie(
                        labels=labels,
                        values=values,
                        hole=0.4,
                        marker=dict(colors=colors, line=dict(color='white', width=2)),
                        textinfo='percent',  # Only show percentage, not label names
                        textfont=dict(size=14, color='#050d76', family='Inter, sans-serif'),  # Larger font for percentages
                        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
                    )])
                    fig.update_layout(
                        title=f"Set {set_num} (n={total})",
                        height=CHART_HEIGHTS['large'],  # Larger chart
                        showlegend=True,
                        legend=dict(
                            orientation="v",
                            yanchor="top",
                            y=1,
                            xanchor="left",
                            x=1.02,
                            itemsizing='constant'  # Consistent legend item sizing
                        ),
                        margin=dict(l=0, r=100, t=50, b=0),  # Reduce margins for bigger chart
                        font=dict(family='Inter, sans-serif', size=11, color='#050d76')
                    )
                    fig = apply_beautiful_theme(fig, f"Set {set_num} Serve Performance")
                    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"serve_donut_set_{set_num}")


def _create_blocking_performance_charts(df: pd.DataFrame, loader=None) -> None:
    """Create all blocking performance charts for Section 4.
    
    Includes:
    - Block Performance by Set (4 donut charts: All Sets + one per set)
    """
    st.markdown("#### Block Performance by Set")
    played_sets = get_played_sets(df, loader)
    
    # Fixed order for consistent legend: Kills, Touches, Block - No Kill, No Touch, Errors
    block_order = ['Kills', 'Touches', 'Block - No Kill', 'No Touch', 'Errors']
    block_color_map = {
        'Kills': OUTCOME_COLORS['kill'],
        'Touches': OUTCOME_COLORS['touch'],
        'Block - No Kill': OUTCOME_COLORS['block_no_kill'],
        'No Touch': OUTCOME_COLORS['no_touch'],
        'Errors': OUTCOME_COLORS['error']
    }
    
    # Prepare data for all sets combined
    all_blocks = df[df['action'] == 'block']
    all_kills = len(all_blocks[all_blocks['outcome'] == 'kill'])
    all_touches = len(all_blocks[all_blocks['outcome'] == 'touch'])
    all_block_no_kill = len(all_blocks[all_blocks['outcome'] == 'block_no_kill'])
    all_no_touch = len(all_blocks[all_blocks['outcome'] == 'no_touch'])
    all_errors = len(all_blocks[all_blocks['outcome'] == 'error'])
    all_total = all_kills + all_touches + all_block_no_kill + all_no_touch + all_errors
    
    # Create 4 columns: All Sets + one for each set
    cols = st.columns(4)
    
    # All Sets donut chart
    with cols[0]:
        if all_total > 0:
            labels = []
            values = []
            colors = []
            
            block_data = {
                'Kills': all_kills,
                'Touches': all_touches,
                'Block - No Kill': all_block_no_kill,
                'No Touch': all_no_touch,
                'Errors': all_errors
            }
            
            for block_type in block_order:
                count = block_data[block_type]
                if count > 0:
                    labels.append(block_type)
                    values.append(count)
                    colors.append(block_color_map[block_type])
            
            if labels:
                fig = go.Figure(data=[go.Pie(
                    labels=labels,
                    values=values,
                    hole=0.4,
                    marker=dict(colors=colors, line=dict(color='white', width=2)),
                    textinfo='percent',  # Only show percentage, not label names
                    textfont=dict(size=14, color='#050d76', family='Inter, sans-serif'),  # Larger font for percentages
                    hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
                )])
                fig.update_layout(
                    title=f"All Sets (n={all_total})",
                    height=CHART_HEIGHTS['large'],  # Larger chart
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        yanchor="top",
                        y=1,
                        xanchor="left",
                        x=1.02,
                        itemsizing='constant'  # Consistent legend item sizing
                    ),
                    margin=dict(l=0, r=100, t=50, b=0),  # Reduce margins for bigger chart
                    font=dict(family='Inter, sans-serif', size=11, color='#050d76')
                )
                fig = apply_beautiful_theme(fig, "All Sets Block Performance")
                st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="block_donut_all")
    
    # Individual set donut charts
    for idx, set_num in enumerate(played_sets[:3], start=1):  # Limit to 3 sets (plus "All Sets" = 4 total)
        if idx >= len(cols):
            break
        with cols[idx]:
            set_df = df[df['set_number'] == set_num]
            blocks_set = set_df[set_df['action'] == 'block']
            
            kills = len(blocks_set[blocks_set['outcome'] == 'kill'])
            touches = len(blocks_set[blocks_set['outcome'] == 'touch'])
            block_no_kill = len(blocks_set[blocks_set['outcome'] == 'block_no_kill'])
            no_touch = len(blocks_set[blocks_set['outcome'] == 'no_touch'])
            errors = len(blocks_set[blocks_set['outcome'] == 'error'])
            total = kills + touches + block_no_kill + no_touch + errors
            
            if total > 0:
                labels = []
                values = []
                colors = []
                
                block_data = {
                    'Kills': kills,
                    'Touches': touches,
                    'Block - No Kill': block_no_kill,
                    'No Touch': no_touch,
                    'Errors': errors
                }
                
                for block_type in block_order:
                    count = block_data[block_type]
                    if count > 0:
                        labels.append(block_type)
                        values.append(count)
                        colors.append(block_color_map[block_type])
                
                if labels:
                    fig = go.Figure(data=[go.Pie(
                        labels=labels,
                        values=values,
                        hole=0.4,
                        marker=dict(colors=colors, line=dict(color='white', width=2)),
                        textinfo='percent',  # Only show percentage, not label names
                        textfont=dict(size=14, color='#050d76', family='Inter, sans-serif'),  # Larger font for percentages
                        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
                    )])
                    fig.update_layout(
                        title=f"Set {set_num} (n={total})",
                        height=CHART_HEIGHTS['large'],  # Larger chart
                        showlegend=True,
                        legend=dict(
                            orientation="v",
                            yanchor="top",
                            y=1,
                            xanchor="left",
                            x=1.02,
                            itemsizing='constant'  # Consistent legend item sizing
                        ),
                        margin=dict(l=0, r=100, t=50, b=0),  # Reduce margins for bigger chart
                        font=dict(family='Inter, sans-serif', size=11, color='#050d76')
                    )
                    fig = apply_beautiful_theme(fig, f"Set {set_num} Block Performance")
                    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"block_donut_set_{set_num}")

