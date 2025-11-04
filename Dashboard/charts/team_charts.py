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
from config import CHART_COLORS
from charts.utils import apply_beautiful_theme, plotly_config


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


def create_team_charts(analyzer: MatchAnalyzer, loader=None) -> None:
    """Create all team performance charts.
    
    Args:
        analyzer: MatchAnalyzer instance with loaded match data
        loader: Optional ExcelMatchLoader instance for team rally data
    """
    df = analyzer.match_data
    
    # Row 1: Action distribution and Outcome distribution
    col1, col2 = st.columns(2)
    
    with col1:
        _create_action_distribution_chart(df)
    
    with col2:
        _create_outcome_distribution_chart(df)
    
    # Row 2: Attack distribution and Reception distribution
    col3, col4 = st.columns(2)
    
    with col3:
        _create_attack_distribution_chart(df)
    
    with col4:
        _create_reception_distribution_chart(df)
    
    # Rotation Performance Analysis (before set-by-set)
    try:
        rotation_stats = analyzer.analyze_rotation_performance()
        if rotation_stats:
            _create_rotation_heatmap(rotation_stats, analyzer, df, loader)
    except AttributeError:
        # Method might not exist, skip rotation analysis
        pass
    
    # Set-by-set performance
    st.markdown("### 🎯 Set-by-Set Performance")
    _create_set_by_set_charts(df, analyzer, loader)


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
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>',
        marker=dict(line=dict(color='rgba(255,255,255,0.8)', width=1))
    )
    fig_actions = apply_beautiful_theme(fig_actions, "Action Distribution")
    st.plotly_chart(fig_actions, use_container_width=True, config=plotly_config)
    
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
        textfont=dict(size=11, color='#040C7B')
    ))
    
    fig_outcomes.update_layout(
        title="Outcome Distribution",
        xaxis_title="Outcome",
        yaxis_title="Count",
        height=400,
        showlegend=False
    )
    fig_outcomes.update_xaxes(
        title_font=dict(color='#040C7B'),
        tickfont=dict(color='#040C7B')
    )
    fig_outcomes.update_yaxes(
        title_font=dict(color='#040C7B'),
        tickfont=dict(color='#040C7B')
    )
    fig_outcomes.update_traces(
        hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
    )
    fig_outcomes = apply_beautiful_theme(fig_outcomes, "Outcome Distribution")
    st.plotly_chart(fig_outcomes, use_container_width=True, config=plotly_config)


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
        line=dict(color="#040C7B", width=2),
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
        line=dict(color="#040C7B", width=2),  # Same color as net
        layer="below"
    )
    
    # Right pole border
    fig.add_shape(
        type="line",
        x0=container_x_right,
        y0=pole_area_y_bottom,
        x1=container_x_right,
        y1=container_y_bottom,
        line=dict(color="#040C7B", width=2),  # Same color as net
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
        line=dict(color="#040C7B", width=3, dash="dash"),  # Thicker, clearer dash pattern
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
                    line=dict(color='#040C7B', width=3),  # Thicker border for better visibility
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
            font=dict(size=13, color='#040C7B', family='Poppins'),
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor="#040C7B",
            borderwidth=2,
            borderpad=4
        )
    
    # Update layout (rotated 90 degrees)
    fig.update_layout(
        title=dict(
            text="Attack Distribution by Position",
            font=dict(size=18, color='#040C7B', family='Poppins'),
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
        height=450,
        showlegend=False,
        paper_bgcolor='rgba(255,255,255,0)',
        plot_bgcolor='rgba(255,255,255,0.98)',
        margin=dict(l=40, r=40, t=80, b=40)
    )
    
    fig = apply_beautiful_theme(fig, "Attack Distribution by Position")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config)


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
        line=dict(color='#040C7B', width=2),
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
        line=dict(color='#040C7B', width=2, dash="dash"),
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
                    line=dict(color='#040C7B', width=2.5),
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
                font=dict(size=11, color='#040C7B', family='Poppins'),
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor="#040C7B",
                borderwidth=1.5,
                borderpad=3
            )
    
    # Update layout
    fig.update_layout(
        title=dict(
            text="Reception Distribution by Position",
            font=dict(size=18, color='#040C7B', family='Poppins'),
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
        height=450,
        showlegend=False,
        paper_bgcolor='rgba(255,255,255,0)',
        plot_bgcolor='rgba(255,255,255,0.98)',
        margin=dict(l=40, r=40, t=80, b=40)
    )
    
    fig = apply_beautiful_theme(fig, "Reception Distribution by Position")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config)


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
                # For blocks, kills are kills, good are touches
                kills = len(action_df[action_df['outcome'] == 'kill'])
                good = len(action_df[action_df['outcome'] == 'good'])
                errors = len(action_df[action_df['outcome'] == 'error'])
            else:
                # For other actions (attack, receive, dig)
                kills = len(action_df[action_df['outcome'] == 'kill'])
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
        marker_color='#90EE90',  # Soft green
        text=quality_df['Kill'],
        textposition='inside',
        textfont=dict(size=10, color='#FFFFFF')
    ))
    
    fig.add_trace(go.Bar(
        x=quality_df['Action'],
        y=quality_df['Good'],
        name='Good',
        marker_color='#FFE4B5',  # Soft yellow/cream
        text=quality_df['Good'],
        textposition='inside',
        textfont=dict(size=10, color='#040C7B')
    ))
    
    fig.add_trace(go.Bar(
        x=quality_df['Action'],
        y=quality_df['Error'],
        name='Error',
        marker_color='#FFB6C1',  # Soft pink/red
        text=quality_df['Error'],
        textposition='inside',
        textfont=dict(size=10, color='#FFFFFF')
    ))
    
    fig.update_layout(
        title="Quality Distribution by Action Type",
        xaxis_title="Action Type",
        yaxis_title="Count",
        barmode='stack',
        height=400,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    fig = apply_beautiful_theme(fig, "Quality Distribution by Action Type")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config)
    
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
            rec_good = len(receives[receives['outcome'] == 'good'])
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
            metrics['attack_good'] = len(attacks[attacks['outcome'] == 'good'])
            metrics['attack_errors'] = len(attacks[attacks['outcome'] == 'error'])
        
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
            metrics['block_touches'] = len(blocks[blocks['outcome'] == 'good'])
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
            metrics['reception_good'] = len(receives[receives['outcome'] == 'good'])
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
            dig_good = len(digs[digs['outcome'] == 'good'])
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
        yaxis=dict(tickformat='.0%', tickfont=dict(color='#040C7B')),
        xaxis=dict(dtick=1, tickfont=dict(color='#040C7B')),
        height=400,
        hovermode='x unified',
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig_trends = apply_beautiful_theme(fig_trends, "Performance Trends Across Sets")
    st.plotly_chart(fig_trends, use_container_width=True, config=plotly_config)
    
    # === STACKED BAR CHARTS: Quality Distributions ===
    st.markdown("#### 🎯 Quality Distribution by Set")
    
    # Attack Quality Distribution
    fig_attack = go.Figure()
    fig_attack.add_trace(go.Bar(
        x=set_metrics_df['set'],
        y=set_metrics_df['attack_kills'],
        name='Kills',
        marker_color='#90EE90',  # Soft green
        text=set_metrics_df['attack_kills'].astype(int),
        textposition='inside'
    ))
    fig_attack.add_trace(go.Bar(
        x=set_metrics_df['set'],
        y=set_metrics_df['attack_good'],
        name='Good',
        marker_color='#FFE4B5',  # Soft yellow/cream
        text=set_metrics_df['attack_good'].astype(int),
        textposition='inside'
    ))
    fig_attack.add_trace(go.Bar(
        x=set_metrics_df['set'],
        y=set_metrics_df['attack_errors'],
        name='Errors',
        marker_color='#FFB6C1',  # Soft pink/red
        text=set_metrics_df['attack_errors'].astype(int),
        textposition='inside'
    ))
    
    fig_attack.update_layout(
        title="Attack Quality Distribution",
        xaxis_title="Set Number",
        yaxis_title="Count",
        barmode='stack',
        xaxis=dict(dtick=1, tickfont=dict(color='#040C7B')),
        yaxis=dict(tickfont=dict(color='#040C7B')),
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig_attack = apply_beautiful_theme(fig_attack, "Attack Quality Distribution")
    st.plotly_chart(fig_attack, use_container_width=True, config=plotly_config)
    
    # Service Quality Distribution
    col1, col2 = st.columns(2)
    
    with col1:
        fig_service = go.Figure()
        fig_service.add_trace(go.Bar(
            x=set_metrics_df['set'],
            y=set_metrics_df['service_aces'],
            name='Aces',
            marker_color='#90EE90',  # Soft green
            text=set_metrics_df['service_aces'].astype(int),
            textposition='inside'
        ))
        fig_service.add_trace(go.Bar(
            x=set_metrics_df['set'],
            y=set_metrics_df['service_good'],
            name='Good',
            marker_color='#FFE4B5',  # Soft yellow/cream
            text=set_metrics_df['service_good'].astype(int),
            textposition='inside'
        ))
        fig_service.add_trace(go.Bar(
            x=set_metrics_df['set'],
            y=set_metrics_df['service_errors'],
            name='Errors',
            marker_color='#FFB6C1',  # Soft pink/red
            text=set_metrics_df['service_errors'].astype(int),
            textposition='inside'
        ))
        
        fig_service.update_layout(
            title="Service Quality Distribution",
            xaxis_title="Set Number",
            yaxis_title="Count",
            barmode='stack',
            xaxis=dict(dtick=1, tickfont=dict(color='#040C7B')),
            yaxis=dict(tickfont=dict(color='#040C7B')),
            height=350,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig_service = apply_beautiful_theme(fig_service, "Service Quality Distribution")
        st.plotly_chart(fig_service, use_container_width=True, config=plotly_config)
    
    with col2:
        fig_block = go.Figure()
        fig_block.add_trace(go.Bar(
            x=set_metrics_df['set'],
            y=set_metrics_df['block_kills'],
            name='Kills',
            marker_color='#90EE90',  # Soft green
            text=set_metrics_df['block_kills'].astype(int),
            textposition='inside'
        ))
        fig_block.add_trace(go.Bar(
            x=set_metrics_df['set'],
            y=set_metrics_df['block_touches'],
            name='Touches',
            marker_color='#FFE4B5',  # Soft yellow/cream
            text=set_metrics_df['block_touches'].astype(int),
            textposition='inside'
        ))
        fig_block.add_trace(go.Bar(
            x=set_metrics_df['set'],
            y=set_metrics_df['block_errors'],
            name='Errors',
            marker_color='#FFB6C1',  # Soft pink/red
            text=set_metrics_df['block_errors'].astype(int),
            textposition='inside'
        ))
        
        fig_block.update_layout(
            title="Block Quality Distribution",
            xaxis_title="Set Number",
            yaxis_title="Count",
            barmode='stack',
            xaxis=dict(dtick=1, tickfont=dict(color='#040C7B')),
            yaxis=dict(tickfont=dict(color='#040C7B')),
            height=350,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        fig_block = apply_beautiful_theme(fig_block, "Block Quality Distribution")
        st.plotly_chart(fig_block, use_container_width=True, config=plotly_config)
    
    # Reception Quality Distribution
    fig_reception = go.Figure()
    fig_reception.add_trace(go.Bar(
        x=set_metrics_df['set'],
        y=set_metrics_df['reception_good'],
        name='Good',
        marker_color='#90EE90',  # Soft green
        text=set_metrics_df['reception_good'].astype(int),
        textposition='inside'
    ))
    fig_reception.add_trace(go.Bar(
        x=set_metrics_df['set'],
        y=set_metrics_df['reception_errors'],
        name='Errors',
        marker_color='#FFB6C1',  # Soft pink/red
        text=set_metrics_df['reception_errors'].astype(int),
        textposition='inside'
    ))
    
    fig_reception.update_layout(
        title="Reception Quality Distribution",
        xaxis_title="Set Number",
        yaxis_title="Count",
        barmode='stack',
        xaxis=dict(dtick=1, tickfont=dict(color='#040C7B')),
        yaxis=dict(tickfont=dict(color='#040C7B')),
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig_reception = apply_beautiful_theme(fig_reception, "Reception Quality Distribution")
    st.plotly_chart(fig_reception, use_container_width=True, config=plotly_config)


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
        
        # Calculate rates - avoid division by zero
        serving_point_rate = (serving_points_won_total / serving_rallies_total) if serving_rallies_total > 0 else 0.0
        receiving_point_rate = (receiving_points_won_total / receiving_rallies_total) if receiving_rallies_total > 0 else 0.0
        
        # Kill Percentage: Attack kills / total attacks (from filtered dataframe)
        attacks = rotation_data[rotation_data['action'] == 'attack']
        attack_kills = len(attacks[attacks['outcome'] == 'kill'])
        attack_attempts = len(attacks)
        kill_percentage = (attack_kills / attack_attempts) if attack_attempts > 0 else 0.0
        
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
        if reception_total > 0:
            # Use aggregated Excel data (accurate)
            reception_quality = (reception_good_total / reception_total)
        else:
            # Fallback: Count from action rows (less accurate due to distribution)
            receives = rotation_data[rotation_data['action'] == 'receive']
            good_receives = len(receives[receives['outcome'] == 'good'])
            total_receives = len(receives)
            reception_quality = (good_receives / total_receives) if total_receives > 0 else 0.0
        
        # Debug: Log if we're using Excel data vs fallback
        if reception_total > 0:
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Rotation {rotation} Reception Quality: Using Excel data - {reception_good_total}/{reception_total} = {reception_quality:.2%}")
        
        # Usage Frequency: Points played in this rotation / total points across all rotations
        usage_frequency = (rotation_points / total_points_all_rotations) if total_points_all_rotations > 0 else 0.0
        
        enhanced_stats[rotation] = {
            'serving_point_rate': serving_point_rate,
            'receiving_point_rate': receiving_point_rate,
            'kill_percentage': kill_percentage,
            'reception_quality': reception_quality,
            'usage_frequency': usage_frequency
        }
    
    # Prepare heatmap data (excluding usage frequency for color scale)
    metrics = ['serving_point_rate', 'receiving_point_rate', 'kill_percentage', 'reception_quality']
    metric_labels = ['Serving Point Rate', 'Receiving Point Rate', 'Kill %', 'Reception Quality']
    
    heatmap_data = []
    for rotation in rotations:
        row_data = []
        for metric in metrics:
            value = enhanced_stats[rotation].get(metric, 0)
            row_data.append(value)
        heatmap_data.append(row_data)
    
    # Create heatmap with improved color scale
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=heatmap_data,
        x=metric_labels,
        y=[f"Rotation {r}" for r in rotations],
        colorscale=[[0, '#FFB3BA'], [0.4, '#FFDFBA'], [0.6, '#FFFFBA'], [0.8, '#BAFFC9'], [1, '#90EE90']],  # Softer pastel gradient ending in soft green
        text=[[f"{val:.1%}" if val >= 0.001 else "0.0%" for val in row] for row in heatmap_data],
        texttemplate="%{text}",
        textfont={"size": 11, "color": "#2C3E50"},
        colorbar=dict(title="Performance Rate"),
        hovertemplate='<b>%{y}</b><br>%{x}: %{z:.1%}<extra></extra>'
    ))
    
    # Update title based on filter
    heatmap_title = "Rotation Performance Heatmap"
    if selected_set_num is not None:
        heatmap_title += f" - Set {selected_set_num}"
    
    fig_heatmap.update_layout(
        title=heatmap_title,
        xaxis_title="Metric",
        yaxis_title="Rotation",
        height=400,
        font=dict(family='Inter, sans-serif', size=12, color='#040C7B'),
        paper_bgcolor='rgba(255,255,255,0)',
        plot_bgcolor='rgba(255,255,255,0.95)',
        xaxis=dict(tickfont=dict(color='#040C7B')),
        yaxis=dict(tickfont=dict(color='#040C7B'))
    )
    
    fig_heatmap = apply_beautiful_theme(fig_heatmap, heatmap_title)
    st.plotly_chart(fig_heatmap, use_container_width=True, config=plotly_config)
    
    # Usage frequency bar chart
    usage_title = "Rotation Usage Frequency"
    if selected_set_num is not None:
        usage_title += f" - Set {selected_set_num}"
    
    usage_values = [enhanced_stats[r]['usage_frequency'] for r in rotations]
    fig_usage = go.Figure(data=go.Bar(
        x=[f"Rotation {r}" for r in rotations],
        y=usage_values,
        marker=dict(color='#040C7B', opacity=0.7),
        text=[f"{val:.1%}" for val in usage_values],
        textposition='outside',
        textfont=dict(size=11, color='#040C7B')
    ))
    
    fig_usage.update_layout(
        title=usage_title,
        xaxis_title="Rotation",
        yaxis_title="Percentage of Total Points",
        yaxis=dict(tickformat='.0%', tickfont=dict(color='#040C7B')),
        xaxis=dict(tickfont=dict(color='#040C7B')),
        height=300,
        showlegend=False
    )
    
    fig_usage = apply_beautiful_theme(fig_usage, usage_title)
    st.plotly_chart(fig_usage, use_container_width=True, config=plotly_config)

