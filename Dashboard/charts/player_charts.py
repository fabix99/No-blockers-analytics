"""
Player chart generation module
"""
from typing import Dict, Any, List, Optional
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from match_analyzer import MatchAnalyzer
from config import CHART_COLORS
from charts.utils import apply_beautiful_theme, plotly_config


def get_played_sets(df: pd.DataFrame, loader=None) -> List[int]:
    """
    Detect which sets were actually played (have data).
    Same function as in team_charts.py - import it to avoid duplication.
    """
    from charts.team_charts import get_played_sets as _get_played_sets
    return _get_played_sets(df, loader)


def create_player_charts(analyzer: MatchAnalyzer, player_name: str, loader=None) -> None:
    """Create all player performance charts.
    
    Args:
        analyzer: MatchAnalyzer instance
        player_name: Name of the player
        loader: Optional ExcelMatchLoader instance for detecting played sets
    """
    df = analyzer.match_data
    player_df = df[df['player'] == player_name]
    
    # Filter player data to only played sets
    played_sets = get_played_sets(df, loader)
    if played_sets:
        player_df = player_df[player_df['set_number'].isin(played_sets)]
    
    st.markdown("### 📊 Player Performance Charts")
    
    col1, col2 = st.columns(2)
    
    with col1:
        _create_action_distribution_chart(player_df)
    
    with col2:
        _create_outcome_distribution_chart(player_df)
    
    # Performance by set
    st.markdown("### 🎯 Performance by Set")
    _create_performance_by_set_charts(player_df)


def _create_action_distribution_chart(player_df: pd.DataFrame) -> None:
    """Create action distribution chart for player."""
    action_counts = player_df['action'].value_counts()
    
    if len(action_counts) > 0:
        # Use softer pastel colors for distribution
        soft_pastels = ['#B8E6B8', '#B8D4E6', '#E6D4B8', '#E6B8D4', '#D4B8E6', '#B8E6D4', '#E6E6B8']
        fig = px.pie(
            values=action_counts.values,
            names=action_counts.index,
            title="Action Distribution",
            color_discrete_sequence=soft_pastels
        )
        fig.update_traces(
            textposition='inside',
            textinfo='percent+label',
            hovertemplate='<b>%{label}</b><br>Count: %{value}<extra></extra>',
            marker=dict(line=dict(color='rgba(255,255,255,0.8)', width=1.5))
        )
        fig = apply_beautiful_theme(fig, "Action Distribution")
        st.plotly_chart(fig, use_container_width=True, config=plotly_config)


def _create_outcome_distribution_chart(player_df: pd.DataFrame) -> None:
    """Create outcome distribution chart for player."""
    outcome_counts = player_df['outcome'].value_counts()
    
    # Combine ace with kill (like team overview)
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
    
    # Add any other outcomes
    for outcome in outcome_counts.index:
        if outcome not in ['kill', 'ace', 'good', 'error']:
            ordered_outcomes[outcome.capitalize()] = outcome_counts[outcome]
    
    if len(ordered_outcomes) > 0:
        ordered_series = pd.Series(ordered_outcomes)
        
        # Use softer pastel colors for distribution (same as team overview)
        color_map = {
            'Kill': '#90EE90',  # Soft green
            'Good': '#FFE4B5',  # Soft yellow/cream
            'Error': '#FFB6C1'  # Soft pink/red
        }
        colors = [color_map.get(outcome, '#B8D4E6') for outcome in ordered_series.index]
        
        fig = go.Figure(data=go.Bar(
            x=ordered_series.index,
            y=ordered_series.values,
            marker_color=colors,
            text=ordered_series.values,
            textposition='outside',
            textfont=dict(size=11, color='#040C7B')
        ))
        
        fig.update_layout(
            title="Outcome Distribution",
            xaxis_title="Outcome",
            yaxis_title="Count",
            showlegend=False
        )
        fig.update_traces(
            marker=dict(line=dict(color='rgba(255,255,255,0.8)', width=1)),
            hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
        )
        fig = apply_beautiful_theme(fig, "Outcome Distribution")
        st.plotly_chart(fig, use_container_width=True, config=plotly_config)


def _create_performance_by_set_charts(player_df: pd.DataFrame) -> None:
    """Create performance by set charts."""
    # Player actions by set - single soft color for trend
    set_actions = player_df.groupby('set_number')['action'].count()
    
    fig_set = go.Figure(data=go.Bar(
        x=set_actions.index,
        y=set_actions.values,
        marker_color='#B8D4E6',  # Soft blue - single color for trend
        text=set_actions.values,
        textposition='outside',
        textfont=dict(size=11, color='#040C7B')
    ))
    fig_set.update_layout(
        title="Actions by Set",
        xaxis_title="Set Number",
        yaxis_title="Number of Actions",
        showlegend=False,
        xaxis=dict(dtick=1, tickfont=dict(color='#040C7B')),
        yaxis=dict(tickfont=dict(color='#040C7B'))
    )
    fig_set.update_traces(
        marker=dict(line=dict(color='rgba(255,255,255,0.8)', width=1)),
        hovertemplate='<b>Set %{x}</b><br>Actions: %{y}<extra></extra>'
    )
    fig_set = apply_beautiful_theme(fig_set, "Actions by Set")
    st.plotly_chart(fig_set, use_container_width=True, config=plotly_config)
    
    # Player outcomes by set - Kills, Good, Errors (three colors for distribution)
    if 'outcome' in player_df.columns:
        # Combine ace with kill (like other charts)
        set_kills = player_df[player_df['outcome'] == 'kill'].groupby('set_number').size()
        set_aces = player_df[player_df['outcome'] == 'ace'].groupby('set_number').size()
        set_good = player_df[player_df['outcome'] == 'good'].groupby('set_number').size()
        set_errors = player_df[player_df['outcome'] == 'error'].groupby('set_number').size()
        
        # Combine kills and aces
        # Get all sets from player data to ensure we show all sets
        all_sets = sorted(player_df['set_number'].unique())
        set_kills_reindexed = set_kills.reindex(all_sets, fill_value=0) if len(set_kills) > 0 else pd.Series(0, index=all_sets)
        set_aces_reindexed = set_aces.reindex(all_sets, fill_value=0) if len(set_aces) > 0 else pd.Series(0, index=all_sets)
        set_kills_combined = set_kills_reindexed + set_aces_reindexed
        set_good_reindexed = set_good.reindex(all_sets, fill_value=0) if len(set_good) > 0 else pd.Series(0, index=all_sets)
        set_errors_reindexed = set_errors.reindex(all_sets, fill_value=0) if len(set_errors) > 0 else pd.Series(0, index=all_sets)
        
        fig_outcomes = go.Figure()
        
        if set_kills_combined.sum() > 0:
            fig_outcomes.add_trace(go.Bar(
                x=set_kills_combined.index,
                y=set_kills_combined.values,
                name='Kills',
                marker_color='#90EE90'  # Soft green
            ))
        
        if set_good_reindexed.sum() > 0:
            fig_outcomes.add_trace(go.Bar(
                x=set_good_reindexed.index,
                y=set_good_reindexed.values,
                name='Good',
                marker_color='#FFE4B5'  # Soft yellow/cream
            ))
        
        if set_errors_reindexed.sum() > 0:
            fig_outcomes.add_trace(go.Bar(
                x=set_errors_reindexed.index,
                y=set_errors_reindexed.values,
                name='Errors',
                marker_color='#FFB6C1'  # Soft pink/red
            ))
        
        fig_outcomes.update_layout(
            title="Outcomes by Set",
            xaxis_title="Set Number",
            yaxis_title="Count",
            barmode='group',
            xaxis=dict(dtick=1, tickfont=dict(color='#040C7B')),
            yaxis=dict(tickfont=dict(color='#040C7B'))
        )
        fig_outcomes.update_traces(
            marker=dict(line=dict(color='rgba(255,255,255,0.8)', width=1))
        )
        fig_outcomes = apply_beautiful_theme(fig_outcomes, "Outcomes by Set")
        st.plotly_chart(fig_outcomes, use_container_width=True, config=plotly_config)

