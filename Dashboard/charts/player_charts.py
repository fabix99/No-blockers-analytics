"""
Player chart generation module
"""
from typing import Dict, Any, List, Optional
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from match_analyzer import MatchAnalyzer
from config import CHART_COLORS, OUTCOME_COLORS, CHART_HEIGHTS
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
    
    # Get player position
    from utils.helpers import get_player_position
    position = get_player_position(df, player_name)
    
    st.markdown("### 📊 Player Performance Charts")
    
    # Position-specific charts
    if position and (position.startswith('OH') or position == 'OPP' or position.startswith('MB')):
        # Attackers: Show attack-specific charts
        _create_attacker_specific_charts(player_df, analyzer, player_name, loader)
    elif position == 'S' or (position and 'setter' in position.lower()):
        # Setters: Show setting-specific charts
        _create_setter_specific_charts(player_df, analyzer, player_name, loader)
    elif position == 'L':
        # Liberos: Show reception/dig-specific charts
        _create_libero_specific_charts(player_df, analyzer, player_name, loader)
    
    # Generic charts (for all positions)
    col1, col2 = st.columns(2)
    
    with col1:
        _create_action_distribution_chart(player_df)
    
    with col2:
        _create_outcome_distribution_chart(player_df)
    
    # Performance by set (enhanced)
    st.markdown("### 🎯 Performance by Set")
    _create_performance_by_set_charts(player_df, analyzer, player_name, loader)
    
    # Add Attack Outcome Breakdown for attackers
    if position and (position.startswith('OH') or position == 'OPP' or position.startswith('MB')):
        _create_attack_outcome_breakdown(player_df, player_name)
    
    # Add Block Efficiency Trends for blockers (MB, OPP, OH)
    if position and (position.startswith('MB') or position == 'OPP' or position.startswith('OH')):
        _create_block_efficiency_trends(player_df, player_name)
    
    # Add Reception & Dig Performance charts - grouped together for better organization
    # Show for any player with reception/dig data (including setters and liberos)
    receives = player_df[player_df['action'] == 'receive']
    digs = player_df[player_df['action'] == 'dig']
    
    if len(receives) > 0 or len(digs) > 0:
        st.markdown("### 📥 Reception & Defense Performance")
        
        if len(receives) > 0 and len(digs) > 0:
            # Both charts side by side
            col1, col2 = st.columns(2)
            with col1:
                _create_reception_performance_chart(receives, player_name)
            with col2:
                _create_dig_performance_chart(digs, player_name)
        elif len(receives) > 0:
            # Only reception chart
            _create_reception_performance_chart(receives, player_name)
        elif len(digs) > 0:
            # Only dig chart
            _create_dig_performance_chart(digs, player_name)


def _create_attack_outcome_breakdown(player_df: pd.DataFrame, player_name: str) -> None:
    """Create attack outcome breakdown chart showing all outcomes (Kill, Defended, Blocked, Out, Net)."""
    attacks = player_df[player_df['action'] == 'attack']
    
    if len(attacks) == 0:
        return
    
    st.markdown("#### 🏐 Attack Outcome Breakdown")
    
    # Count all outcomes (error removed - all errors covered by out, net, blocked)
    kills = len(attacks[attacks['outcome'] == 'kill'])
    defended = len(attacks[attacks['outcome'] == 'defended'])
    blocked = len(attacks[attacks['outcome'] == 'blocked'])
    out = len(attacks[attacks['outcome'] == 'out'])
    net = len(attacks[attacks['outcome'] == 'net'])
    
    # Group outcomes
    labels = []
    values = []
    colors_list = []
    
    if kills > 0:
        labels.append('Kill')
        values.append(kills)
        colors_list.append(OUTCOME_COLORS.get('kill', '#28A745'))
    if defended > 0:
        labels.append('Defended')
        values.append(defended)
        colors_list.append(OUTCOME_COLORS.get('defended', '#B0E0E6'))
    if blocked > 0:
        labels.append('Blocked')
        values.append(blocked)
        colors_list.append(OUTCOME_COLORS.get('blocked', '#DC3545'))
    if out > 0:
        labels.append('Out')
        values.append(out)
        colors_list.append(OUTCOME_COLORS.get('out', '#DC3545'))
    if net > 0:
        labels.append('Net')
        values.append(net)
        colors_list.append(OUTCOME_COLORS.get('net', '#DC3545'))
    
    if labels:
        fig = go.Figure(data=[go.Bar(
            x=labels,
            y=values,
            marker=dict(color=colors_list),
            text=values,
            textposition='outside',
            textfont=dict(size=12, color='#050d76'),
            hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
        )])
        fig.update_layout(
            title="Attack Outcomes",
            xaxis_title="Outcome",
            yaxis_title="Count",
            height=CHART_HEIGHTS['medium'],
            xaxis=dict(tickfont=dict(color='#050d76')),
            yaxis=dict(tickfont=dict(color='#050d76'))
        )
        fig = apply_beautiful_theme(fig, "Attack Outcomes")
        st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"player_attack_outcomes_{player_name}")


def _create_block_efficiency_trends(player_df: pd.DataFrame, player_name: str) -> None:
    """Create block efficiency trends by set for blockers."""
    blocks = player_df[player_df['action'] == 'block']
    
    if len(blocks) == 0:
        return
    
    st.markdown("#### 🛡️ Block Efficiency Trends")
    
    played_sets = sorted(player_df['set_number'].unique())
    block_kill_pct_by_set = []
    
    for set_num in played_sets:
        set_blocks = blocks[blocks['set_number'] == set_num]
        block_kills = len(set_blocks[set_blocks['outcome'] == 'kill'])
        block_total = len(set_blocks)
        
        if block_total > 0:
            kill_pct = (block_kills / block_total) * 100
            block_kill_pct_by_set.append(kill_pct)
        else:
            block_kill_pct_by_set.append(0)
    
    fig = go.Figure(data=go.Scatter(
        x=[f"Set {s}" for s in played_sets],
        y=block_kill_pct_by_set,
        mode='lines+markers',
        name='Block Kill %',
        line=dict(color=OUTCOME_COLORS.get('block_kill', '#B8E986'), width=3),
        marker=dict(size=10),
        fill='tonexty',
        fillcolor='rgba(184, 233, 134, 0.2)'
    ))
    fig.update_layout(
        title="Block Kill % by Set",
        xaxis_title="Set",
        yaxis_title="Block Kill %",
        height=CHART_HEIGHTS['medium'],
        yaxis=dict(range=[0, 100], tickfont=dict(color='#050d76')),
        xaxis=dict(tickfont=dict(color='#050d76'))
    )
    fig = apply_beautiful_theme(fig, "Block Kill % by Set")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"player_block_trends_{player_name}")


def _create_reception_performance_chart(receives: pd.DataFrame, player_name: str) -> None:
    """Create reception performance donut chart with outcome breakdown."""
    if len(receives) == 0:
        return
    
    st.markdown("#### 📥 Reception Performance")
    
    # Count outcomes
    perfect = len(receives[receives['outcome'] == 'perfect'])
    good = len(receives[receives['outcome'] == 'good'])
    poor = len(receives[receives['outcome'] == 'poor'])
    errors = len(receives[receives['outcome'] == 'error'])
    
    total = len(receives)
    
    # Build labels, values, and colors
    labels = []
    values = []
    colors_list = []
    
    if perfect > 0:
        labels.append('Perfect')
        values.append(perfect)
        colors_list.append(OUTCOME_COLORS.get('perfect', '#28A745'))
    if good > 0:
        labels.append('Good')
        values.append(good)
        colors_list.append(OUTCOME_COLORS.get('good', '#6CBF47'))
    if poor > 0:
        labels.append('Poor')
        values.append(poor)
        colors_list.append(OUTCOME_COLORS.get('poor', '#FFC107'))
    if errors > 0:
        labels.append('Error')
        values.append(errors)
        colors_list.append(OUTCOME_COLORS.get('error', '#DC3545'))
    
    if not labels:
        st.info("No reception data available")
        return
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=colors_list, line=dict(color='white', width=2)),
        textinfo='percent',
        textfont=dict(size=14, color='#050d76', family='Inter, sans-serif'),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
    )])
    
    # Add annotation for total
    annotations = [dict(
        text=f"Total<br>{total}",
        x=0.5, y=0.5,
        font=dict(size=14, color='#050d76', family='Inter, sans-serif', weight='bold'),
        showarrow=False
    )]
    
    fig.update_layout(
        title="Reception Performance",
        height=CHART_HEIGHTS['large'],
        showlegend=True,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        margin=dict(l=0, r=100, t=50, b=0),
        font=dict(family='Inter, sans-serif', size=11, color='#050d76'),
        annotations=annotations
    )
    fig = apply_beautiful_theme(fig, "Reception Performance")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"player_reception_performance_{player_name}")


def _create_dig_performance_chart(digs: pd.DataFrame, player_name: str) -> None:
    """Create dig performance donut chart with outcome breakdown."""
    if len(digs) == 0:
        return
    
    st.markdown("#### 🛡️ Dig Performance")
    
    # Count outcomes
    perfect = len(digs[digs['outcome'] == 'perfect'])
    good = len(digs[digs['outcome'] == 'good'])
    poor = len(digs[digs['outcome'] == 'poor'])
    errors = len(digs[digs['outcome'] == 'error'])
    
    total = len(digs)
    
    # Build labels, values, and colors
    labels = []
    values = []
    colors_list = []
    
    if perfect > 0:
        labels.append('Perfect')
        values.append(perfect)
        colors_list.append(OUTCOME_COLORS.get('perfect', '#28A745'))
    if good > 0:
        labels.append('Good')
        values.append(good)
        colors_list.append(OUTCOME_COLORS.get('good', '#6CBF47'))
    if poor > 0:
        labels.append('Poor')
        values.append(poor)
        colors_list.append(OUTCOME_COLORS.get('poor', '#FFC107'))
    if errors > 0:
        labels.append('Error')
        values.append(errors)
        colors_list.append(OUTCOME_COLORS.get('error', '#DC3545'))
    
    if not labels:
        st.info("No dig data available")
        return
    
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=0.4,
        marker=dict(colors=colors_list, line=dict(color='white', width=2)),
        textinfo='percent',
        textfont=dict(size=14, color='#050d76', family='Inter, sans-serif'),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
    )])
    
    # Add annotation for total
    annotations = [dict(
        text=f"Total<br>{total}",
        x=0.5, y=0.5,
        font=dict(size=14, color='#050d76', family='Inter, sans-serif', weight='bold'),
        showarrow=False
    )]
    
    fig.update_layout(
        title="Dig Performance",
        height=CHART_HEIGHTS['large'],
        showlegend=True,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
        margin=dict(l=0, r=100, t=50, b=0),
        font=dict(family='Inter, sans-serif', size=11, color='#050d76'),
        annotations=annotations
    )
    fig = apply_beautiful_theme(fig, "Dig Performance")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key=f"player_dig_performance_{player_name}")


def _create_action_distribution_chart(player_df: pd.DataFrame) -> None:
    """Create action distribution donut chart with unique colors."""
    action_counts = player_df['action'].value_counts()
    if len(action_counts) == 0:
        return
    
    total_actions = action_counts.sum()
    action_percentages = (action_counts / total_actions) * 100
    
    # Unique color mapping aligned with dashboard palette
    action_color_map = {
        'attack': '#F5A623',        # orange
        'serve': '#00B5AD',         # teal
        'receive': '#7ED321',       # green
        'set': '#4A6CF7',           # blue
        'block': '#9013FE',         # purple
        'dig': '#BD10E0'            # magenta
    }
    colors = [action_color_map.get(action.lower(), '#9B9B9B') for action in action_counts.index]
    
    fig = go.Figure(data=[go.Pie(
        labels=action_counts.index.str.title(),
        values=action_counts.values,
        hole=0.4,
        marker=dict(colors=colors, line=dict(color='white', width=2)),
        textinfo='percent',
        textfont=dict(size=14, color='#050d76', family='Inter, sans-serif'),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
    )])
    fig.update_layout(
        title="Action Distribution",
        height=CHART_HEIGHTS['medium'],
        showlegend=True,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.05),
        margin=dict(l=0, r=100, t=50, b=0),
        font=dict(family='Inter, sans-serif', size=11, color='#050d76'),
        annotations=[dict(
            text=f"Total\n{int(total_actions)}", x=0.5, y=0.5,
            font=dict(size=14, color='#050d76', family='Inter, sans-serif'),
            showarrow=False
        )]
    )
    fig = apply_beautiful_theme(fig, "Action Distribution")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="player_action_distribution")


def _create_outcome_distribution_chart(player_df: pd.DataFrame) -> None:
    """Create outcome distribution donut chart grouped into four buckets."""
    if 'outcome' not in player_df.columns or player_df.empty:
        return
    
    outcome_counts = player_df['outcome'].value_counts()
    total_outcomes = outcome_counts.sum()
    
    category_map = {
        'kill': 'Kills',
        'ace': 'Kills',
        'good': 'Positive',
        'exceptional': 'Positive',
        'perfect': 'Positive',
        'touch': 'Neutral',
        'defended': 'Neutral',
        'poor': 'Neutral',
        'error': 'Errors',
        'blocked': 'Errors',
        'out': 'Errors',
        'net': 'Errors',
        'no_touch': 'No Touch',
        'block_no_kill': 'Block - No Kill'
    }
    
    grouped_counts = {'Kills': 0, 'Positive': 0, 'Neutral': 0, 'Errors': 0}
    for outcome, count in outcome_counts.items():
        bucket = category_map.get(outcome.lower(), 'Neutral')
        grouped_counts[bucket] += count
    
    categories = ['Kills', 'Positive', 'Neutral', 'Errors']
    values = [grouped_counts[c] for c in categories]
    colors = [
        OUTCOME_COLORS.get('kill', '#4CAF50'),
        OUTCOME_COLORS.get('good', '#8BC34A'),
        '#F5A623',
        OUTCOME_COLORS.get('error', '#FF6B6B')
    ]
    
    fig = go.Figure(data=[go.Pie(
        labels=categories,
        values=values,
        hole=0.4,
        marker=dict(colors=colors, line=dict(color='white', width=2)),
        textinfo='percent',
        textfont=dict(size=14, color='#050d76', family='Inter, sans-serif'),
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
    )])
    fig.update_layout(
        title="Outcome Distribution",
        height=CHART_HEIGHTS['medium'],
        showlegend=True,
        legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.05),
        margin=dict(l=0, r=100, t=50, b=0),
        font=dict(family='Inter, sans-serif', size=11, color='#050d76'),
        annotations=[dict(
            text=f"Total\n{int(total_outcomes)}", x=0.5, y=0.5,
            font=dict(size=14, color='#050d76', family='Inter, sans-serif'),
            showarrow=False
        )]
    )
    fig = apply_beautiful_theme(fig, "Outcome Distribution")
    st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="player_outcome_distribution")


def _create_attacker_specific_charts(player_df: pd.DataFrame, analyzer: MatchAnalyzer, 
                                    player_name: str, loader=None) -> None:
    """Create attacker-specific charts (Attack Type Distribution, Attack Type Efficiency)."""
    st.markdown("#### 🏐 Attacking Performance")
    
    attacks = player_df[player_df['action'] == 'attack']
    
    if len(attacks) == 0:
        st.info("No attack data available")
        return
    
    # First row: Attack Type Distribution and Attack Type Efficiency
    col1, col2 = st.columns(2)
    
    with col1:
        # Attack Type Distribution
        if 'attack_type' in attacks.columns:
            attack_types = attacks['attack_type'].value_counts()
            if len(attack_types) > 0:
                from config import ATTACK_TYPE_COLORS
                type_colors = {
                    'normal': ATTACK_TYPE_COLORS.get('normal', '#4A90E2'),
                    'tip': ATTACK_TYPE_COLORS.get('tip', '#F5A623'),
                    # 'after_block' removed - no longer tracking
                }
                colors = [type_colors.get(t.lower(), '#999999') for t in attack_types.index]
                
                fig = go.Figure(data=[go.Pie(
                    labels=attack_types.index.str.title(),
                    values=attack_types.values,
                    hole=0.4,
                    marker=dict(colors=colors, line=dict(color='white', width=2)),
                    textinfo='percent',
                    textfont=dict(size=14, color='#050d76', family='Inter, sans-serif'),
                    hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
                )])
                fig.update_layout(
                    title="Attack Type Distribution",
                    height=CHART_HEIGHTS['medium'],
                    showlegend=True,
                    legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
                    margin=dict(l=0, r=100, t=50, b=0),
                    font=dict(family='Inter, sans-serif', size=11, color='#050d76')
                )
                fig = apply_beautiful_theme(fig, "Attack Type Distribution")
                st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="player_attack_type")
    
    with col2:
        # Attack Type Efficiency
        if 'attack_type' in attacks.columns:
            from config import ATTACK_TYPE_COLORS
            type_efficiency = {}
            type_attempts = {}
            
            for attack_type in attacks['attack_type'].unique():
                type_attacks = attacks[attacks['attack_type'] == attack_type]
                if len(type_attacks) > 0:
                    kills = len(type_attacks[type_attacks['outcome'] == 'kill'])
                    errors = len(type_attacks[type_attacks['outcome'].isin(['blocked', 'out', 'net'])])  # error removed
                    attempts = len(type_attacks)
                    efficiency = ((kills - errors) / attempts * 100) if attempts > 0 else 0
                    type_efficiency[attack_type] = efficiency
                    type_attempts[attack_type] = attempts
            
            if type_efficiency:
                attack_types_list = list(type_efficiency.keys())
                efficiency_values = [type_efficiency[t] for t in attack_types_list]
                attempts_values = [type_attempts[t] for t in attack_types_list]
                colors_list = [ATTACK_TYPE_COLORS.get(t.lower(), '#999999') for t in attack_types_list]
                
                fig = go.Figure(data=[go.Bar(
                    x=[t.title() for t in attack_types_list],
                    y=efficiency_values,
                    marker=dict(color=colors_list),
                    text=[f"{eff:.1f}%<br>({att} att)" for eff, att in zip(efficiency_values, attempts_values)],
                    textposition='outside',
                    textfont=dict(size=11, color='#050d76'),
                    hovertemplate='<b>%{x}</b><br>Efficiency: %{y:.1f}%<br>Attempts: %{customdata}<extra></extra>',
                    customdata=attempts_values
                )])
                fig.update_layout(
                    title="Attack Efficiency by Type",
                    xaxis_title="Attack Type",
                    yaxis_title="Efficiency %",
                    height=CHART_HEIGHTS['medium'],
                    yaxis=dict(tickfont=dict(color='#050d76')),
                    xaxis=dict(tickfont=dict(color='#050d76'))
                )
                fig = apply_beautiful_theme(fig, "Attack Efficiency by Type")
                st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="player_attack_type_efficiency")


def _create_setter_specific_charts(player_df: pd.DataFrame, analyzer: MatchAnalyzer,
                                  player_name: str, loader=None) -> None:
    """Create setter-specific charts (Setting Quality by Set, Set Distribution)."""
    st.markdown("#### 🎯 Setting Performance")
    
    sets = player_df[player_df['action'] == 'set']
    
    if len(sets) == 0:
        st.info("No setting data available")
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Setting Quality by Set
        played_sets = sorted(player_df['set_number'].unique())
        quality_by_set = []
        
        for set_num in played_sets:
            set_sets = sets[sets['set_number'] == set_num]
            good_sets = len(set_sets[set_sets['outcome'].isin(['exceptional', 'good'])])
            total_sets = len(set_sets)
            
            if total_sets > 0:
                quality_by_set.append((good_sets / total_sets) * 100)
            else:
                quality_by_set.append(0)
        
        fig = go.Figure(data=go.Scatter(
            x=[f"Set {s}" for s in played_sets],
            y=quality_by_set,
            mode='lines+markers',
            name='Setting Quality',
            line=dict(color=OUTCOME_COLORS['serving_rate'], width=3),
            marker=dict(size=10),
            fill='tonexty',
            fillcolor='rgba(74, 144, 226, 0.2)'
        ))
        fig.update_layout(
            title="Setting Quality by Set",
            xaxis_title="Set",
            yaxis_title="Quality %",
            height=CHART_HEIGHTS['medium'],
            yaxis=dict(range=[0, 100], tickfont=dict(color='#050d76')),
            xaxis=dict(tickfont=dict(color='#050d76'))
        )
        fig = apply_beautiful_theme(fig, "Setting Quality by Set")
        st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="player_setting_quality")
    
    with col2:
        # Setting Outcome Distribution
        exceptional = len(sets[sets['outcome'] == 'exceptional'])
        good = len(sets[sets['outcome'] == 'good'])
        poor = len(sets[sets['outcome'] == 'poor'])
        errors = len(sets[sets['outcome'] == 'error'])
        
        labels = []
        values = []
        colors_list = []
        
        if exceptional > 0:
            labels.append('Exceptional')
            values.append(exceptional)
            colors_list.append(OUTCOME_COLORS['perfect'])
        if good > 0:
            labels.append('Good')
            values.append(good)
            colors_list.append(OUTCOME_COLORS['good'])
        if poor > 0:
            labels.append('Poor')
            values.append(poor)
            colors_list.append(OUTCOME_COLORS['poor'])
        if errors > 0:
            labels.append('Error')
            values.append(errors)
            colors_list.append(OUTCOME_COLORS['error'])
        
        if labels:
            fig = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.4,
                marker=dict(colors=colors_list),
                textinfo='percent',
                textfont=dict(size=14, color='#050d76'),
                hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
            )])
            fig.update_layout(
                title="Setting Outcome Distribution",
                height=CHART_HEIGHTS['medium'],
                showlegend=True,
                legend=dict(orientation="v", yanchor="top", y=1, xanchor="left", x=1.02),
                margin=dict(l=0, r=100, t=50, b=0),
                font=dict(family='Inter, sans-serif', size=11, color='#050d76')
            )
            fig = apply_beautiful_theme(fig, "Setting Outcome Distribution")
            st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="player_setting_outcomes")


def _create_libero_specific_charts(player_df: pd.DataFrame, analyzer: MatchAnalyzer,
                                  player_name: str, loader=None) -> None:
    """Create libero-specific charts (Reception Quality by Set, Dig Success Rate)."""
    st.markdown("#### 📥 Reception & Defense Performance")
    
    receives = player_df[player_df['action'] == 'receive']
    digs = player_df[player_df['action'] == 'dig']
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Reception Quality by Set
        if len(receives) > 0:
            played_sets = sorted(player_df['set_number'].unique())
            quality_by_set = []
            
            from utils.helpers import filter_good_receptions
            
            for set_num in played_sets:
                set_receives = receives[receives['set_number'] == set_num]
                good_receives = len(filter_good_receptions(set_receives))
                total_receives = len(set_receives)
                
                if total_receives > 0:
                    quality_by_set.append((good_receives / total_receives) * 100)
                else:
                    quality_by_set.append(0)
            
            fig = go.Figure(data=go.Scatter(
                x=[f"Set {s}" for s in played_sets],
                y=quality_by_set,
                mode='lines+markers',
                name='Reception Quality',
                line=dict(color=OUTCOME_COLORS['reception'], width=3),
                marker=dict(size=10),
                fill='tonexty',
                fillcolor='rgba(80, 227, 194, 0.2)'
            ))
            fig.update_layout(
                title="Reception Quality by Set",
                xaxis_title="Set",
                yaxis_title="Quality %",
                height=CHART_HEIGHTS['medium'],
                yaxis=dict(range=[0, 100], tickfont=dict(color='#050d76')),
                xaxis=dict(tickfont=dict(color='#050d76'))
            )
            fig = apply_beautiful_theme(fig, "Reception Quality by Set")
            st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="player_reception_quality")
        else:
            st.info("No reception data available")
    
    with col2:
        # Dig Success Rate by Set
        if len(digs) > 0:
            played_sets = sorted(player_df['set_number'].unique())
            success_by_set = []
            
            from utils.helpers import filter_good_digs
            
            for set_num in played_sets:
                set_digs = digs[digs['set_number'] == set_num]
                good_digs = len(filter_good_digs(set_digs))
                total_digs = len(set_digs)
                
                if total_digs > 0:
                    success_by_set.append((good_digs / total_digs) * 100)
                else:
                    success_by_set.append(0)
            
            fig = go.Figure(data=go.Scatter(
                x=[f"Set {s}" for s in played_sets],
                y=success_by_set,
                mode='lines+markers',
                name='Dig Success Rate',
                line=dict(color=OUTCOME_COLORS['serving_rate'], width=3),
                marker=dict(size=10),
                fill='tonexty',
                fillcolor='rgba(74, 144, 226, 0.2)'
            ))
            fig.update_layout(
                title="Dig Success Rate by Set",
                xaxis_title="Set",
                yaxis_title="Success Rate %",
                height=CHART_HEIGHTS['medium'],
                yaxis=dict(range=[0, 100], tickfont=dict(color='#050d76')),
                xaxis=dict(tickfont=dict(color='#050d76'))
            )
            fig = apply_beautiful_theme(fig, "Dig Success Rate by Set")
            st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="player_dig_success")
        else:
            st.info("No dig data available")


def _create_performance_by_set_charts(player_df: pd.DataFrame, analyzer: MatchAnalyzer,
                                     player_name: str, loader=None) -> None:
    """Create enhanced performance by set charts with quality metrics and team comparison."""
    from utils.helpers import get_player_position
    df = analyzer.match_data
    position = get_player_position(df, player_name)
    
    # Player actions by set (workload)
    set_actions = player_df.groupby('set_number')['action'].count()
    all_sets = sorted(player_df['set_number'].unique())
    
    col1, col2 = st.columns(2)
    
    with col1:
        fig_set = go.Figure(data=go.Bar(
            x=[f"Set {s}" for s in all_sets],
            y=[set_actions.get(s, 0) for s in all_sets],
            marker_color=OUTCOME_COLORS['serving_rate'],
            text=[set_actions.get(s, 0) for s in all_sets],
            textposition='outside',
            textfont=dict(size=11, color='#050d76')
        ))
        fig_set.update_layout(
            title="Actions by Set (Workload)",
            xaxis_title="Set Number",
            yaxis_title="Number of Actions",
            showlegend=False,
            height=CHART_HEIGHTS['medium'],
            xaxis=dict(dtick=1, tickfont=dict(color='#050d76')),
            yaxis=dict(tickfont=dict(color='#050d76'))
        )
        fig_set.update_traces(
            marker=dict(line=dict(color='rgba(255,255,255,0.8)', width=1)),
            hovertemplate='<b>Set %{x}</b><br>Actions: %{y}<extra></extra>'
        )
        fig_set = apply_beautiful_theme(fig_set, "Actions by Set")
        st.plotly_chart(fig_set, use_container_width=True, config=plotly_config, key="player_actions_by_set")
    
    with col2:
        # Position-specific performance metric by set
        if position and (position.startswith('OH') or position == 'OPP' or position.startswith('MB')):
            # Attack Kill % by Set
            attacks = player_df[player_df['action'] == 'attack']
            kill_pct_by_set = []
            team_kill_pct_by_set = []
            
            for set_num in all_sets:
                set_attacks = attacks[attacks['set_number'] == set_num]
                kills = len(set_attacks[set_attacks['outcome'] == 'kill'])
                attempts = len(set_attacks)
                kill_pct = (kills / attempts * 100) if attempts > 0 else 0
                kill_pct_by_set.append(kill_pct)
                
                # Team average
                set_df = df[df['set_number'] == set_num]
                team_attacks = set_df[set_df['action'] == 'attack']
                team_kills = len(team_attacks[team_attacks['outcome'] == 'kill'])
                team_attempts = len(team_attacks)
                team_kill_pct = (team_kills / team_attempts * 100) if team_attempts > 0 else 0
                team_kill_pct_by_set.append(team_kill_pct)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[f"Set {s}" for s in all_sets],
                y=kill_pct_by_set,
                mode='lines+markers',
                name='Player',
                line=dict(color=OUTCOME_COLORS['attack_kill'], width=3),
                marker=dict(size=10)
            ))
            fig.add_trace(go.Scatter(
                x=[f"Set {s}" for s in all_sets],
                y=team_kill_pct_by_set,
                mode='lines+markers',
                name='Team Average',
                line=dict(color='#999999', width=2, dash='dash'),
                marker=dict(size=8)
            ))
            fig.update_layout(
                title="Attack Kill % by Set",
                xaxis_title="Set",
                yaxis_title="Kill %",
                height=CHART_HEIGHTS['medium'],
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis=dict(range=[0, 100], tickfont=dict(color='#050d76')),
                xaxis=dict(tickfont=dict(color='#050d76'))
            )
            fig = apply_beautiful_theme(fig, "Attack Kill % by Set")
            st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="player_kill_pct_by_set")
        
        elif position == 'L':
            # Reception Quality by Set (already shown in libero-specific, but show here too for consistency)
            receives = player_df[player_df['action'] == 'receive']
            from utils.helpers import filter_good_receptions
            
            rec_quality_by_set = []
            team_rec_quality_by_set = []
            
            for set_num in all_sets:
                set_receives = receives[receives['set_number'] == set_num]
                good_receives = len(filter_good_receptions(set_receives))
                attempts = len(set_receives)
                quality = (good_receives / attempts * 100) if attempts > 0 else 0
                rec_quality_by_set.append(quality)
                
                # Team average
                set_df = df[df['set_number'] == set_num]
                team_receives = set_df[set_df['action'] == 'receive']
                team_good = len(filter_good_receptions(team_receives))
                team_attempts = len(team_receives)
                team_quality = (team_good / team_attempts * 100) if team_attempts > 0 else 0
                team_rec_quality_by_set.append(team_quality)
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=[f"Set {s}" for s in all_sets],
                y=rec_quality_by_set,
                mode='lines+markers',
                name='Player',
                line=dict(color=OUTCOME_COLORS['reception'], width=3),
                marker=dict(size=10)
            ))
            fig.add_trace(go.Scatter(
                x=[f"Set {s}" for s in all_sets],
                y=team_rec_quality_by_set,
                mode='lines+markers',
                name='Team Average',
                line=dict(color='#999999', width=2, dash='dash'),
                marker=dict(size=8)
            ))
            fig.update_layout(
                title="Reception Quality by Set",
                xaxis_title="Set",
                yaxis_title="Quality %",
                height=CHART_HEIGHTS['medium'],
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                yaxis=dict(range=[0, 100], tickfont=dict(color='#050d76')),
                xaxis=dict(tickfont=dict(color='#050d76'))
            )
            fig = apply_beautiful_theme(fig, "Reception Quality by Set")
            st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="player_rec_quality_by_set")
        
        else:
            # Generic: Outcomes by Set
            set_kills = player_df[player_df['outcome'] == 'kill'].groupby('set_number').size()
            set_aces = player_df[player_df['outcome'] == 'ace'].groupby('set_number').size()
            set_good = player_df[
                (player_df['outcome'] == 'good') | 
                (player_df['outcome'] == 'defended') | 
                (player_df['outcome'].isin(['perfect', 'good'])) |
                (player_df['outcome'] == 'touch')
            ].groupby('set_number').size()
            set_errors = player_df[player_df['outcome'] == 'error'].groupby('set_number').size()
            
            set_kills_reindexed = set_kills.reindex(all_sets, fill_value=0) if len(set_kills) > 0 else pd.Series(0, index=all_sets)
            set_aces_reindexed = set_aces.reindex(all_sets, fill_value=0) if len(set_aces) > 0 else pd.Series(0, index=all_sets)
            set_kills_combined = set_kills_reindexed + set_aces_reindexed
            set_good_reindexed = set_good.reindex(all_sets, fill_value=0) if len(set_good) > 0 else pd.Series(0, index=all_sets)
            set_errors_reindexed = set_errors.reindex(all_sets, fill_value=0) if len(set_errors) > 0 else pd.Series(0, index=all_sets)
            
            fig_outcomes = go.Figure()
            
            if set_kills_combined.sum() > 0:
                fig_outcomes.add_trace(go.Bar(
                    x=[f"Set {s}" for s in all_sets],
                    y=[set_kills_combined.get(s, 0) for s in all_sets],
                    name='Kills',
                    marker_color=OUTCOME_COLORS['kill']
                ))
            
            if set_good_reindexed.sum() > 0:
                fig_outcomes.add_trace(go.Bar(
                    x=[f"Set {s}" for s in all_sets],
                    y=[set_good_reindexed.get(s, 0) for s in all_sets],
                    name='Good',
                    marker_color=OUTCOME_COLORS['good']
                ))
            
            if set_errors_reindexed.sum() > 0:
                fig_outcomes.add_trace(go.Bar(
                    x=[f"Set {s}" for s in all_sets],
                    y=[set_errors_reindexed.get(s, 0) for s in all_sets],
                    name='Errors',
                    marker_color=OUTCOME_COLORS['error']
                ))
            
            fig_outcomes.update_layout(
                title="Outcomes by Set",
                xaxis_title="Set Number",
                yaxis_title="Count",
                barmode='group',
                height=CHART_HEIGHTS['medium'],
                xaxis=dict(dtick=1, tickfont=dict(color='#050d76')),
                yaxis=dict(tickfont=dict(color='#050d76'))
            )
            fig_outcomes.update_traces(
                marker=dict(line=dict(color='rgba(255,255,255,0.8)', width=1))
            )
            fig_outcomes = apply_beautiful_theme(fig_outcomes, "Outcomes by Set")
            st.plotly_chart(fig_outcomes, use_container_width=True, config=plotly_config, key="player_outcomes_by_set")

