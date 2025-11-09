"""
Player Comparison UI Module
"""
from typing import Dict, Any, Optional, Tuple, List
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from match_analyzer import MatchAnalyzer
from config import KPI_TARGETS, OUTCOME_COLORS, CHART_HEIGHTS
from utils.helpers import get_player_position, filter_good_receptions, filter_good_digs, filter_block_touches
from ui.components import get_position_full_name
from charts.utils import apply_beautiful_theme, plotly_config
from utils.statistical_helpers import (
    calculate_confidence_interval, get_reliability_indicator, 
    is_sample_size_sufficient, format_ci_display, get_statistical_significance_indicator
)


def display_player_comparison(analyzer: MatchAnalyzer, loader=None) -> None:
    """Display player comparison with ratings and KPIs.
    
    Args:
        analyzer: MatchAnalyzer instance with loaded match data
        loader: Optional EventTrackerLoader instance for aggregated data
    """
    # MEDIUM PRIORITY 15: Error handling
    try:
        st.markdown('<h2 class="main-header">🏆 Player Comparison</h2>', unsafe_allow_html=True)
        
        player_stats = analyzer.calculate_player_metrics()
        
        if player_stats is None:
            st.error("No player statistics available")
            return
    except Exception as e:
        st.error(f"❌ Error displaying player comparison: {str(e)}")
        st.info("💡 Please try refreshing the page or re-uploading your data file.")
        import logging
        logging.error(f"Error in display_player_comparison: {e}", exc_info=True)
        return
    
    df = analyzer.match_data
    
    # Create comparison dataframe with new KPIs and ratings
    comparison_data = []
    for player, stats in player_stats.items():
        position = get_player_position(df, player) or 'Unknown'
        is_setter = stats.get('total_sets', 0) > 0 and stats.get('total_sets', 0) >= stats['total_actions'] * 0.2
        
        # Calculate player KPIs (consistent with Team Overview)
        kpis = _calculate_player_kpis_for_comparison(analyzer, player, stats, position, is_setter, loader)
        
        # Calculate position-specific rating
        rating, rating_breakdown = _calculate_player_rating_new(stats, position, is_setter, kpis, loader, player)
        
        # Calculate total actions including all types (from loader aggregated data if available)
        total_actions = stats['total_actions']  # Base count from action rows
        if loader and hasattr(loader, 'player_data_by_set'):
            # Add digs and receptions from aggregated data if not in action rows
            total_digs = 0
            total_receptions = 0
            for set_num in loader.player_data_by_set.keys():
                if player in loader.player_data_by_set[set_num]:
                    stats_agg = loader.player_data_by_set[set_num][player].get('stats', {})
                    total_digs += float(stats_agg.get('Dig_Total', 0) or 0)
                    total_receptions += float(stats_agg.get('Reception_Total', 0) or 0)
            # Only add if not already counted in action rows
            # Check if digs/receptions are in action rows
            player_df = df[df['player'] == player]
            if len(player_df[player_df['action'] == 'dig']) == 0:
                total_actions += int(total_digs)
            if len(player_df[player_df['action'] == 'receive']) < total_receptions:
                total_actions += int(total_receptions - len(player_df[player_df['action'] == 'receive']))
        
        comparison_data.append({
            'Player': player,
            'Position': get_position_full_name(position),
            'Rating': rating,
            'Attack Rating': rating_breakdown.get('attack', 0),
            'Reception Rating': rating_breakdown.get('reception', 0),
            'Serve Rating': rating_breakdown.get('serve', 0),
            'Block Rating': rating_breakdown.get('block', 0),
            'Defense Rating': rating_breakdown.get('defense', 0),
            'Setting Rating': rating_breakdown.get('setting', 0),
            # New KPIs
            'Attack Kill %': kpis.get('attack_kill_pct', 0),
            'Serve In-Rate': kpis.get('serve_in_rate', 0),
            'Reception Quality': kpis.get('reception_quality', 0),
            'Block Kill %': kpis.get('block_kill_pct', 0),
            'Dig Rate': kpis.get('dig_rate', 0),
            'Setting Quality': kpis.get('setting_quality', 0),
            # Volume metrics
            'Attack Attempts': stats.get('attack_attempts', 0),
            'Attack Kills': stats.get('attack_kills', 0),
            'Attack Good': kpis.get('attack_good', 0),  # For weighted scoring
            'Service Attempts': stats.get('service_attempts', 0),
            'Block Attempts': stats.get('block_attempts', 0),
            'Block Kills': stats.get('block_kills', 0),
            'Block Touches': kpis.get('block_touches', 0),  # For weighted scoring
            'Reception Attempts': stats.get('total_receives', 0),
            'Total Sets': stats.get('total_sets', 0),
            'Total Actions': total_actions
        })
    
    comparison_df = pd.DataFrame(comparison_data)
    
    # Consolidated top performers - visual card-based layout
    _display_top_performers_visual(comparison_df)
    
    # Player-level breakdowns as charts (not tables)
    _display_player_breakdowns_charts(analyzer, loader, comparison_df)


def _display_player_breakdowns_charts(analyzer: MatchAnalyzer, loader=None, comparison_df: pd.DataFrame = None) -> None:
    """Display player-level breakdowns as visual charts (not tables)."""
    from utils.breakdown_helpers import get_kpi_by_player
    
    st.markdown("### 👥 Player Performance Breakdowns")
    
    # Get all players from comparison_df or all players
    if comparison_df is not None and len(comparison_df) > 0:
        players_to_show = comparison_df['Player'].tolist()
    else:
        players_to_show = None
    
    # Create tabs for different KPIs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Attack Kill %", "Serve In-Rate", "Reception Quality", "Block Kill %", "Dig Rate"
    ])
    
    with tab1:
        player_attack = get_kpi_by_player(loader, 'attack_kill_pct', return_totals=True) if loader else None
        if player_attack:
            # Filter to selected players if applicable
            if players_to_show:
                player_attack = {p: v for p, v in player_attack.items() if p in players_to_show}
            
            if player_attack:
                # Sort by value descending
                sorted_players = sorted(player_attack.items(), key=lambda x: x[1]['value'], reverse=True)
                players = [p[0] for p in sorted_players]
                values = [p[1]['value'] for p in sorted_players]
                color = OUTCOME_COLORS.get('kill', '#28A745')
                
                fig = go.Figure(data=go.Bar(
                    x=values,
                    y=players,
                    orientation='h',
                    marker=dict(
                        color=color,
                        line=dict(color='rgba(255,255,255,0.8)', width=1.5)
                    ),
                    text=[f"{v:.1%}" for v in values],
                    textposition='outside',
                    textfont=dict(size=12, color='#050d76', family='Arial')
                ))
                fig.update_layout(
                    title=dict(
                        text="Attack Kill % by Player",
                        font=dict(size=16, color='#050d76', family='Arial'),
                        x=0.5,
                        xanchor='center'
                    ),
                    xaxis=dict(
                        title=dict(text="Attack Kill %", font=dict(size=13, color='#050d76')),
                        tickformat='.0%',
                        tickfont=dict(size=11, color='#050d76'),
                        showgrid=True,
                        gridcolor='rgba(0,0,0,0.05)'
                    ),
                    yaxis=dict(
                        title=dict(text="Player", font=dict(size=13, color='#050d76')),
                        tickfont=dict(size=11, color='#050d76'),
                        autorange='reversed',
                        showgrid=False
                    ),
                    height=max(400, len(players) * 45),
                    showlegend=False,
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    margin=dict(l=80, r=80, t=60, b=40)
                )
                fig = apply_beautiful_theme(fig, "Attack Kill % by Player")
                st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="breakdown_attack")
            else:
                st.info("No attack data available for selected players")
        else:
            st.info("No attack data available")
    
    with tab2:
        player_serve = get_kpi_by_player(loader, 'serve_in_rate', return_totals=True) if loader else None
        if player_serve:
            if players_to_show:
                player_serve = {p: v for p, v in player_serve.items() if p in players_to_show}
            
            if player_serve:
                sorted_players = sorted(player_serve.items(), key=lambda x: x[1]['value'], reverse=True)
                players = [p[0] for p in sorted_players]
                values = [p[1]['value'] for p in sorted_players]
                color = OUTCOME_COLORS.get('serving_rate', '#4A90E2')
                
                fig = go.Figure(data=go.Bar(
                    x=values,
                    y=players,
                    orientation='h',
                    marker=dict(
                        color=color,
                        line=dict(color='rgba(255,255,255,0.8)', width=1.5)
                    ),
                    text=[f"{v:.1%}" for v in values],
                    textposition='outside',
                    textfont=dict(size=12, color='#050d76', family='Arial')
                ))
                fig.update_layout(
                    title=dict(
                        text="Serve In-Rate by Player",
                        font=dict(size=16, color='#050d76', family='Arial'),
                        x=0.5,
                        xanchor='center'
                    ),
                    xaxis=dict(
                        title=dict(text="Serve In-Rate", font=dict(size=13, color='#050d76')),
                        tickformat='.0%',
                        tickfont=dict(size=11, color='#050d76'),
                        showgrid=True,
                        gridcolor='rgba(0,0,0,0.05)'
                    ),
                    yaxis=dict(
                        title=dict(text="Player", font=dict(size=13, color='#050d76')),
                        tickfont=dict(size=11, color='#050d76'),
                        autorange='reversed',
                        showgrid=False
                    ),
                    height=max(400, len(players) * 45),
                    showlegend=False,
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    margin=dict(l=80, r=80, t=60, b=40)
                )
                fig = apply_beautiful_theme(fig, "Serve In-Rate by Player")
                st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="breakdown_serve")
            else:
                st.info("No service data available for selected players")
        else:
            st.info("No service data available")
    
    with tab3:
        player_rec = get_kpi_by_player(loader, 'reception_quality', return_totals=True) if loader else None
        if player_rec:
            if players_to_show:
                player_rec = {p: v for p, v in player_rec.items() if p in players_to_show}
            
            if player_rec:
                sorted_players = sorted(player_rec.items(), key=lambda x: x[1]['value'], reverse=True)
                players = [p[0] for p in sorted_players]
                values = [p[1]['value'] for p in sorted_players]
                color = OUTCOME_COLORS.get('reception', '#50E3C2')
                
                fig = go.Figure(data=go.Bar(
                    x=values,
                    y=players,
                    orientation='h',
                    marker=dict(
                        color=color,
                        line=dict(color='rgba(255,255,255,0.8)', width=1.5)
                    ),
                    text=[f"{v:.1%}" for v in values],
                    textposition='outside',
                    textfont=dict(size=12, color='#050d76', family='Arial')
                ))
                fig.update_layout(
                    title=dict(
                        text="Reception Quality by Player",
                        font=dict(size=16, color='#050d76', family='Arial'),
                        x=0.5,
                        xanchor='center'
                    ),
                    xaxis=dict(
                        title=dict(text="Reception Quality", font=dict(size=13, color='#050d76')),
                        tickformat='.0%',
                        tickfont=dict(size=11, color='#050d76'),
                        showgrid=True,
                        gridcolor='rgba(0,0,0,0.05)'
                    ),
                    yaxis=dict(
                        title=dict(text="Player", font=dict(size=13, color='#050d76')),
                        tickfont=dict(size=11, color='#050d76'),
                        autorange='reversed',
                        showgrid=False
                    ),
                    height=max(400, len(players) * 45),
                    showlegend=False,
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    margin=dict(l=80, r=80, t=60, b=40)
                )
                fig = apply_beautiful_theme(fig, "Reception Quality by Player")
                st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="breakdown_reception")
            else:
                st.info("No reception data available for selected players")
        else:
            st.info("No reception data available")
    
    with tab4:
        player_block = get_kpi_by_player(loader, 'block_kill_pct', return_totals=True) if loader else None
        if player_block:
            if players_to_show:
                player_block = {p: v for p, v in player_block.items() if p in players_to_show}
            
            if player_block:
                sorted_players = sorted(player_block.items(), key=lambda x: x[1]['value'], reverse=True)
                players = [p[0] for p in sorted_players]
                values = [p[1]['value'] for p in sorted_players]
                color = OUTCOME_COLORS.get('block_kill', '#B8E986')
                
                fig = go.Figure(data=go.Bar(
                    x=values,
                    y=players,
                    orientation='h',
                    marker=dict(
                        color=color,
                        line=dict(color='rgba(255,255,255,0.8)', width=1.5)
                    ),
                    text=[f"{v:.1%}" for v in values],
                    textposition='outside',
                    textfont=dict(size=12, color='#050d76', family='Arial')
                ))
                fig.update_layout(
                    title=dict(
                        text="Block Kill % by Player",
                        font=dict(size=16, color='#050d76', family='Arial'),
                        x=0.5,
                        xanchor='center'
                    ),
                    xaxis=dict(
                        title=dict(text="Block Kill %", font=dict(size=13, color='#050d76')),
                        tickformat='.0%',
                        tickfont=dict(size=11, color='#050d76'),
                        showgrid=True,
                        gridcolor='rgba(0,0,0,0.05)'
                    ),
                    yaxis=dict(
                        title=dict(text="Player", font=dict(size=13, color='#050d76')),
                        tickfont=dict(size=11, color='#050d76'),
                        autorange='reversed',
                        showgrid=False
                    ),
                    height=max(400, len(players) * 45),
                    showlegend=False,
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    margin=dict(l=80, r=80, t=60, b=40)
                )
                fig = apply_beautiful_theme(fig, "Block Kill % by Player")
                st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="breakdown_block")
            else:
                st.info("No block data available for selected players")
        else:
            st.info("No block data available")
    
    with tab5:
        player_dig = get_kpi_by_player(loader, 'dig_rate', return_totals=True) if loader else None
        if player_dig:
            if players_to_show:
                player_dig = {p: v for p, v in player_dig.items() if p in players_to_show}
            
            if player_dig:
                sorted_players = sorted(player_dig.items(), key=lambda x: x[1]['value'], reverse=True)
                players = [p[0] for p in sorted_players]
                values = [p[1]['value'] for p in sorted_players]
                color = OUTCOME_COLORS.get('dig_rate', '#BD10E0')
                
                fig = go.Figure(data=go.Bar(
                    x=values,
                    y=players,
                    orientation='h',
                    marker=dict(
                        color=color,
                        line=dict(color='rgba(255,255,255,0.8)', width=1.5)
                    ),
                    text=[f"{v:.1%}" for v in values],
                    textposition='outside',
                    textfont=dict(size=12, color='#050d76', family='Arial')
                ))
                fig.update_layout(
                    title=dict(
                        text="Dig Rate by Player",
                        font=dict(size=16, color='#050d76', family='Arial'),
                        x=0.5,
                        xanchor='center'
                    ),
                    xaxis=dict(
                        title=dict(text="Dig Rate", font=dict(size=13, color='#050d76')),
                        tickformat='.0%',
                        tickfont=dict(size=11, color='#050d76'),
                        showgrid=True,
                        gridcolor='rgba(0,0,0,0.05)'
                    ),
                    yaxis=dict(
                        title=dict(text="Player", font=dict(size=13, color='#050d76')),
                        tickfont=dict(size=11, color='#050d76'),
                        autorange='reversed',
                        showgrid=False
                    ),
                    height=max(400, len(players) * 45),
                    showlegend=False,
                    plot_bgcolor='white',
                    paper_bgcolor='white',
                    margin=dict(l=80, r=80, t=60, b=40)
                )
                fig = apply_beautiful_theme(fig, "Dig Rate by Player")
                st.plotly_chart(fig, use_container_width=True, config=plotly_config, key="breakdown_dig")
            else:
                st.info("No dig data available for selected players")
        else:
            st.info("No dig data available")


def _display_top_performers_visual(comparison_df: pd.DataFrame) -> None:
    """Display top performers with visual card-based leaderboard layout."""
    st.markdown("### 🏆 Top Performers")
    
    # Top Attackers
    st.markdown("#### 🎯 Top Attackers")
    attackers_df = comparison_df[comparison_df['Attack Attempts'] > 0].copy()
    if len(attackers_df) > 0:
        attackers_df = attackers_df.nlargest(5, 'Attack Kill %').sort_values('Attack Kill %', ascending=False)
        
        for rank, (_, row) in enumerate(attackers_df.iterrows(), 1):
            value = row['Attack Kill %']
            player = row['Player']
            color = OUTCOME_COLORS.get('kill', '#28A745')
            
            # Create card with rank badge and progress bar
            col1, col2, col3 = st.columns([0.1, 0.3, 0.6])
            with col1:
                st.markdown(f"<div style='text-align: center; padding-top: 8px;'><span style='background-color: {color}; color: white; border-radius: 50%; width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px;'>{rank}</span></div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div style='padding-top: 8px; font-weight: 600; font-size: 15px; color: #050d76;'>{player}</div>", unsafe_allow_html=True)
            with col3:
                # Progress bar style
                st.markdown(f"""
                <div style='padding-top: 4px;'>
                    <div style='background-color: #E0E0E0; border-radius: 10px; height: 24px; position: relative; overflow: hidden;'>
                        <div style='background-color: {color}; width: {value*100}%; height: 100%; border-radius: 10px; transition: width 0.3s;'></div>
                        <div style='position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-weight: 600; font-size: 13px; color: #050d76;'>{value:.1%}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No attack data available")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Top Servers
    st.markdown("#### 🎾 Top Servers")
    servers_df = comparison_df[comparison_df['Service Attempts'] > 0].nlargest(5, 'Serve In-Rate').sort_values('Serve In-Rate', ascending=False)
    if len(servers_df) > 0:
        for rank, (_, row) in enumerate(servers_df.iterrows(), 1):
            value = row['Serve In-Rate']
            player = row['Player']
            color = OUTCOME_COLORS.get('serving_rate', '#4A90E2')
            
            col1, col2, col3 = st.columns([0.1, 0.3, 0.6])
            with col1:
                st.markdown(f"<div style='text-align: center; padding-top: 8px;'><span style='background-color: {color}; color: white; border-radius: 50%; width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px;'>{rank}</span></div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div style='padding-top: 8px; font-weight: 600; font-size: 15px; color: #050d76;'>{player}</div>", unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div style='padding-top: 4px;'>
                    <div style='background-color: #E0E0E0; border-radius: 10px; height: 24px; position: relative; overflow: hidden;'>
                        <div style='background-color: {color}; width: {value*100}%; height: 100%; border-radius: 10px; transition: width 0.3s;'></div>
                        <div style='position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-weight: 600; font-size: 13px; color: #050d76;'>{value:.1%}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No service data available")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Top Blockers
    st.markdown("#### 🛡️ Top Blockers")
    blockers_df = comparison_df[comparison_df['Block Attempts'] > 0].nlargest(5, 'Block Kill %').sort_values('Block Kill %', ascending=False)
    if len(blockers_df) > 0:
        for rank, (_, row) in enumerate(blockers_df.iterrows(), 1):
            value = row['Block Kill %']
            player = row['Player']
            color = OUTCOME_COLORS.get('block_kill', '#B8E986')
            
            col1, col2, col3 = st.columns([0.1, 0.3, 0.6])
            with col1:
                st.markdown(f"<div style='text-align: center; padding-top: 8px;'><span style='background-color: {color}; color: white; border-radius: 50%; width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px;'>{rank}</span></div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div style='padding-top: 8px; font-weight: 600; font-size: 15px; color: #050d76;'>{player}</div>", unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div style='padding-top: 4px;'>
                    <div style='background-color: #E0E0E0; border-radius: 10px; height: 24px; position: relative; overflow: hidden;'>
                        <div style='background-color: {color}; width: {max(value*100, 5)}%; height: 100%; border-radius: 10px; transition: width 0.3s;'></div>
                        <div style='position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-weight: 600; font-size: 13px; color: #050d76;'>{value:.1%}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No block data available")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Top Receivers
    st.markdown("#### ✋ Top Receivers")
    receivers_df = comparison_df[comparison_df['Reception Attempts'] > 0].nlargest(5, 'Reception Quality').sort_values('Reception Quality', ascending=False)
    if len(receivers_df) > 0:
        for rank, (_, row) in enumerate(receivers_df.iterrows(), 1):
            value = row['Reception Quality']
            player = row['Player']
            color = OUTCOME_COLORS.get('reception', '#50E3C2')
            
            col1, col2, col3 = st.columns([0.1, 0.3, 0.6])
            with col1:
                st.markdown(f"<div style='text-align: center; padding-top: 8px;'><span style='background-color: {color}; color: white; border-radius: 50%; width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center; font-weight: bold; font-size: 14px;'>{rank}</span></div>", unsafe_allow_html=True)
            with col2:
                st.markdown(f"<div style='padding-top: 8px; font-weight: 600; font-size: 15px; color: #050d76;'>{player}</div>", unsafe_allow_html=True)
            with col3:
                st.markdown(f"""
                <div style='padding-top: 4px;'>
                    <div style='background-color: #E0E0E0; border-radius: 10px; height: 24px; position: relative; overflow: hidden;'>
                        <div style='background-color: {color}; width: {value*100}%; height: 100%; border-radius: 10px; transition: width 0.3s;'></div>
                        <div style='position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%); font-weight: 600; font-size: 13px; color: #050d76;'>{value:.1%}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No reception data available")


def _calculate_player_kpis_for_comparison(analyzer: MatchAnalyzer, player_name: str, 
                                          player_data: Dict[str, Any], position: Optional[str],
                                          is_setter: bool, loader=None) -> Dict[str, float]:
    """Calculate player KPIs consistent with Team Overview metrics."""
    df = analyzer.match_data
    player_df = df[df['player'] == player_name]
    
    metrics = {}
    
    # Attack Kill % (consistent with Team Overview)
    # Calculate for all players - will be used if they have attempts
    # Try to get from loader aggregated stats first (more accurate), otherwise use player_data
    attack_attempts = 0
    attack_kills = 0
    if loader and hasattr(loader, 'player_data_by_set'):
        for set_num in loader.player_data_by_set.keys():
            if player_name in loader.player_data_by_set[set_num]:
                stats = loader.player_data_by_set[set_num][player_name].get('stats', {})
                attack_attempts += float(stats.get('Attack_Total', 0) or 0)
                attack_kills += float(stats.get('Attack_Kills', 0) or 0)
    
    if attack_attempts == 0:
        # Fallback: use player_data from MatchAnalyzer
        attack_attempts = player_data.get('attack_attempts', 0)
        attack_kills = player_data.get('attack_kills', 0)
    
    if attack_attempts > 0:
        metrics['attack_kill_pct'] = attack_kills / attack_attempts
        # Also get attack good for weighted scoring
        attacks = player_df[player_df['action'] == 'attack']
        # Attack 'defended' is considered good (kept in play)
        metrics['attack_good'] = len(attacks[attacks['outcome'] == 'defended'])
    else:
        metrics['attack_kill_pct'] = 0.0
        metrics['attack_good'] = 0
    
    # Serve In-Rate (consistent with Team Overview)
    # Liberos don't serve - exclude for position 'L'
    if position == 'L':
        metrics['serve_in_rate'] = 0.0
    else:
        # Try to get from loader aggregated stats first (more accurate), otherwise use player_data
        service_attempts = 0
        service_aces = 0
        service_good = 0
        if loader and hasattr(loader, 'player_data_by_set'):
            for set_num in loader.player_data_by_set.keys():
                if player_name in loader.player_data_by_set[set_num]:
                    stats = loader.player_data_by_set[set_num][player_name].get('stats', {})
                    service_attempts += float(stats.get('Service_Total', 0) or 0)
                    service_aces += float(stats.get('Service_Aces', 0) or 0)
                    service_good += float(stats.get('Service_Good', 0) or 0)
        
        if service_attempts == 0:
            # Fallback: use player_data from MatchAnalyzer
            service_attempts = player_data.get('service_attempts', 0)
            service_aces = player_data.get('service_aces', 0)
            serves = player_df[player_df['action'] == 'serve']
            service_good = len(serves[serves['outcome'] == 'good'])
        
        if service_attempts > 0:
            metrics['serve_in_rate'] = (service_aces + service_good) / service_attempts
        else:
            metrics['serve_in_rate'] = 0.0
    
    # Reception Quality (consistent with Team Overview)
    if loader and hasattr(loader, 'player_data_by_set'):
        total_rec_good = 0.0
        total_rec_total = 0.0
        for set_num in loader.player_data_by_set.keys():
            if player_name in loader.player_data_by_set[set_num]:
                stats = loader.player_data_by_set[set_num][player_name].get('stats', {})
                total_rec_good += float(stats.get('Reception_Good', 0) or 0)
                total_rec_total += float(stats.get('Reception_Total', 0) or 0)
        if total_rec_total > 0:
            metrics['reception_quality'] = total_rec_good / total_rec_total
        else:
            receives = player_df[player_df['action'] == 'receive']
            total_receives = len(receives)
            if total_receives > 0:
                good_receives = len(filter_good_receptions(receives))
                metrics['reception_quality'] = good_receives / total_receives
            else:
                metrics['reception_quality'] = 0.0
    else:
        receives = player_df[player_df['action'] == 'receive']
        total_receives = len(receives)
        if total_receives > 0:
            good_receives = len(filter_good_receptions(receives))
            metrics['reception_quality'] = good_receives / total_receives
        else:
            metrics['reception_quality'] = 0.0
    
    # Dig Rate (consistent with Team Overview)
    if loader and hasattr(loader, 'player_data_by_set'):
        total_dig_good = 0.0
        total_dig_total = 0.0
        for set_num in loader.player_data_by_set.keys():
            if player_name in loader.player_data_by_set[set_num]:
                stats = loader.player_data_by_set[set_num][player_name].get('stats', {})
                total_dig_good += float(stats.get('Dig_Good', 0) or 0)
                total_dig_total += float(stats.get('Dig_Total', 0) or 0)
        if total_dig_total > 0:
            metrics['dig_rate'] = total_dig_good / total_dig_total
        else:
            metrics['dig_rate'] = 0.0
    else:
        metrics['dig_rate'] = 0.0
    
    # Block Kill % (consistent with Team Overview)
    # Calculate for all players - will be used if they have attempts
    # Try to get from loader aggregated stats first (more accurate), otherwise use player_data
    block_attempts = 0
    block_kills = 0
    if loader and hasattr(loader, 'player_data_by_set'):
        for set_num in loader.player_data_by_set.keys():
            if player_name in loader.player_data_by_set[set_num]:
                stats = loader.player_data_by_set[set_num][player_name].get('stats', {})
                block_attempts += float(stats.get('Block_Total', 0) or 0)
                block_kills += float(stats.get('Block_Kills', 0) or 0)
    
    if block_attempts == 0:
        # Fallback: use player_data from MatchAnalyzer
        block_attempts = player_data.get('block_attempts', 0)
        block_kills = player_data.get('block_kills', 0)
    
    if block_attempts > 0:
        metrics['block_kill_pct'] = block_kills / block_attempts
        # Also get block touches for weighted scoring
        blocks = player_df[player_df['action'] == 'block']
        metrics['block_touches'] = len(filter_block_touches(blocks))
    else:
        metrics['block_kill_pct'] = 0.0
        metrics['block_touches'] = 0
    
    # Setting Quality - check from action rows first (more accurate for all players)
    # Calculate for all players - will be used as bonus if they set well
    sets = player_df[player_df['action'] == 'set']
    total_sets_count = len(sets)
    if total_sets_count > 0:
        # Good sets = exceptional + good (both count as good)
        good_sets_count = len(sets[sets['outcome'].isin(['exceptional', 'good'])])
        metrics['setting_quality'] = good_sets_count / total_sets_count
    else:
        # Fallback to player_data if available
        total_sets = player_data.get('total_sets', 0)
        if total_sets > 0:
            good_sets = player_data.get('good_sets', 0)
            metrics['setting_quality'] = good_sets / total_sets
        else:
            metrics['setting_quality'] = 0.0
    
    return metrics


def _normalize_kpi_to_rating(value: float, target_min: float, target_optimal: float, 
                             target_max: float) -> float:
    """
    Normalize a KPI value to a rating on a 6=average scale (more generous).
    - 6.0 = at target_min (average performance)
    - 7.0 = at target_optimal (good performance)
    - 8.0 = at target_max (great performance)
    - 9-10 = exceptional (above target_max)
    - 5.5+ = below target_min but still decent (more generous floor)
    - 5.0-5.5 = below average
    """
    if value >= target_max * 1.12:  # 12% above max = exceptional (slightly more generous)
        return 10.0
    elif value >= target_max * 1.06:  # 6% above max = outstanding
        return 9.0
    elif value >= target_max:
        # Great to Outstanding: 8.0 to 9.0 scale
        return min(9.0, 8.0 + ((value - target_max) / (target_max * 0.06)) * 1.0)
    elif value >= target_optimal:
        # Good to Great: 7.0 to 8.0 scale
        return 7.0 + ((value - target_optimal) / (target_max - target_optimal)) * 1.0
    elif value >= target_min:
        # Average to Good: 6.0 to 7.0 scale
        return 6.0 + ((value - target_min) / (target_optimal - target_min)) * 1.0
    elif value > target_min * 0.7:  # More generous: 70% of target_min still gets 5.5+
        # Below Average but decent: 5.5 to 6.0 scale
        return max(5.5, 5.5 + ((value - target_min * 0.7) / (target_min * 0.3)) * 0.5)
    elif value > 0:
        # Below Average: 5.0 to 5.5 scale
        return max(5.0, 5.0 + (value / (target_min * 0.7)) * 0.5)
    else:
        # Poor: 5.0 (more generous floor, no data or zero performance)
        return 5.0


def _calculate_player_rating_new(player_data: Dict[str, Any], position: Optional[str],
                                 is_setter: bool, kpis: Dict[str, float], 
                                 loader=None, player_name: str = "") -> Tuple[float, Dict[str, float]]:
    """
    Calculate position-specific rating on normalized 6=average scale.
    Uses expected actions (90% weight) + bonus actions (up to 10%).
    Expected actions have consistent weights across positions for fairness.
    Returns: (overall_rating, breakdown_dict)
    """
    breakdown = {}
    
    # Standard weights for expected actions (same across all positions)
    WEIGHT_ATTACK = 0.30  # 30%
    WEIGHT_BLOCK = 0.25   # 25%
    WEIGHT_RECEPTION = 0.25  # 25%
    WEIGHT_SERVE = 0.15   # 15%
    WEIGHT_DIG = 0.20     # 20%
    WEIGHT_SETTING = 0.40  # 40% (for setters)
    
    # Bonus threshold: only add bonus if rating ≥ 7.0 (good performance)
    BONUS_THRESHOLD = 7.0
    MAX_BONUS = 0.10  # Maximum 10% bonus
    
    # Check position first (liberos can set but are still liberos)
    if position == 'L':
        # LIBERO: Expected = Reception (45%) + Dig (45%) = 90%
        # Bonus: Setting (up to 10%)
        # Liberos CANNOT serve (hard rule) - no attack, block, serve
        reception_q = kpis.get('reception_quality', 0)
        dig_rate = kpis.get('dig_rate', 0)
        setting_q = kpis.get('setting_quality', 0)
        
        breakdown['reception'] = _normalize_kpi_to_rating(reception_q,
                                                         KPI_TARGETS['reception_quality']['min'],
                                                         KPI_TARGETS['reception_quality']['optimal'],
                                                         KPI_TARGETS['reception_quality']['max'])
        breakdown['defense'] = _normalize_kpi_to_rating(dig_rate,
                                                        KPI_TARGETS['dig_rate']['min'],
                                                        KPI_TARGETS['dig_rate']['optimal'],
                                                        KPI_TARGETS['dig_rate']['max'])
        
        # Liberos don't serve, attack, or block - set to 0
        breakdown['serve'] = 0.0
        breakdown['attack'] = 0.0
        breakdown['block'] = 0.0
        
        # Calculate base rating from expected actions (90%)
        base_rating = (breakdown['reception'] * 0.45 + 
                      breakdown['defense'] * 0.45)
        
        # Calculate bonuses (up to 10%)
        bonus = 0.0
        if setting_q > 0 or player_data.get('total_sets', 0) > 0:
            targets_setting = {'min': 0.70, 'optimal': 0.80, 'max': 0.90}
            breakdown['setting'] = _normalize_kpi_to_rating(setting_q, targets_setting['min'], 
                                                           targets_setting['optimal'], targets_setting['max'])
            if breakdown['setting'] >= BONUS_THRESHOLD:
                bonus += 0.10  # 10% bonus
        else:
            breakdown['setting'] = 0.0
        
        rating = base_rating + min(bonus, MAX_BONUS)
        
        # Ensure liberos never have serve, attack, or block ratings (double-check)
        breakdown['serve'] = 0.0
        breakdown['attack'] = 0.0
        breakdown['block'] = 0.0
    
    elif is_setter or position == 'S':
        # SETTER: Expected = Setting (40%) + Attack (30%) + Serve (15%) + Block (5%) = 90%
        # Bonus: Dig, Reception (up to 10%)
        setting_q = kpis.get('setting_quality', 0)
        attack_kill = kpis.get('attack_kill_pct', 0)
        serve_in = kpis.get('serve_in_rate', 0)
        block_kill = kpis.get('block_kill_pct', 0)
        dig_rate = kpis.get('dig_rate', 0)
        reception_q = kpis.get('reception_quality', 0)
        
        targets_setting = {'min': 0.70, 'optimal': 0.80, 'max': 0.90}
        breakdown['setting'] = _normalize_kpi_to_rating(setting_q, targets_setting['min'], 
                                                         targets_setting['optimal'], targets_setting['max'])
        breakdown['attack'] = _normalize_kpi_to_rating(attack_kill,
                                                       KPI_TARGETS['kill_percentage']['min'],
                                                       KPI_TARGETS['kill_percentage']['optimal'],
                                                       KPI_TARGETS['kill_percentage']['max']) if (attack_kill > 0 or player_data.get('attack_attempts', 0) > 0) else 6.0
        breakdown['serve'] = _normalize_kpi_to_rating(serve_in, 
                                                      KPI_TARGETS['serve_in_rate']['min'],
                                                      KPI_TARGETS['serve_in_rate']['optimal'],
                                                      KPI_TARGETS['serve_in_rate']['max'])
        breakdown['block'] = _normalize_kpi_to_rating(block_kill,
                                                      KPI_TARGETS['block_kill_percentage']['min'],
                                                      KPI_TARGETS['block_kill_percentage']['optimal'],
                                                      KPI_TARGETS['block_kill_percentage']['max']) if (block_kill > 0 or player_data.get('block_attempts', 0) > 0) else 6.0
        
        # Calculate base rating from expected actions (90%)
        base_rating = (breakdown['setting'] * WEIGHT_SETTING + 
                      breakdown['attack'] * WEIGHT_ATTACK + 
                      breakdown['serve'] * WEIGHT_SERVE + 
                      breakdown['block'] * 0.05)  # 5% for block
        
        # Calculate bonuses (up to 10%)
        bonus = 0.0
        if dig_rate > 0 or (loader and hasattr(loader, 'player_data_by_set')):
            has_digs = False
            if loader and hasattr(loader, 'player_data_by_set'):
                for set_num in loader.player_data_by_set.keys():
                    if player_name in loader.player_data_by_set[set_num]:
                        stats = loader.player_data_by_set[set_num][player_name].get('stats', {})
                        if float(stats.get('Dig_Total', 0) or 0) > 0:
                            has_digs = True
                            break
            if has_digs or dig_rate > 0:
                breakdown['defense'] = _normalize_kpi_to_rating(dig_rate,
                                                                KPI_TARGETS['dig_rate']['min'],
                                                                KPI_TARGETS['dig_rate']['optimal'],
                                                                KPI_TARGETS['dig_rate']['max'])
                if breakdown['defense'] >= BONUS_THRESHOLD:
                    bonus += 0.05  # 5% bonus
            else:
                breakdown['defense'] = 0.0
        else:
            breakdown['defense'] = 0.0
        
        if reception_q > 0 or player_data.get('total_receives', 0) > 0:
            breakdown['reception'] = _normalize_kpi_to_rating(reception_q,
                                                             KPI_TARGETS['reception_quality']['min'],
                                                             KPI_TARGETS['reception_quality']['optimal'],
                                                             KPI_TARGETS['reception_quality']['max'])
            if breakdown['reception'] >= BONUS_THRESHOLD:
                bonus += 0.05  # 5% bonus
        else:
            breakdown['reception'] = 0.0
        
        rating = base_rating + min(bonus, MAX_BONUS)
        
    elif position and position.startswith('OH'):
        # OUTSIDE HITTER: Expected = Attack (30%) + Reception (25%) + Block (25%) + Serve (10%) = 90%
        # Bonus: Dig, Setting (up to 10%)
        attack_kill = kpis.get('attack_kill_pct', 0)
        reception_q = kpis.get('reception_quality', 0)
        block_kill = kpis.get('block_kill_pct', 0)
        serve_in = kpis.get('serve_in_rate', 0)
        dig_rate = kpis.get('dig_rate', 0)
        setting_q = kpis.get('setting_quality', 0)
        
        breakdown['attack'] = _normalize_kpi_to_rating(attack_kill,
                                                       KPI_TARGETS['kill_percentage']['min'],
                                                       KPI_TARGETS['kill_percentage']['optimal'],
                                                       KPI_TARGETS['kill_percentage']['max'])
        breakdown['reception'] = _normalize_kpi_to_rating(reception_q,
                                                          KPI_TARGETS['reception_quality']['min'],
                                                          KPI_TARGETS['reception_quality']['optimal'],
                                                          KPI_TARGETS['reception_quality']['max'])
        breakdown['block'] = _normalize_kpi_to_rating(block_kill,
                                                      KPI_TARGETS['block_kill_percentage']['min'],
                                                      KPI_TARGETS['block_kill_percentage']['optimal'],
                                                      KPI_TARGETS['block_kill_percentage']['max'])
        breakdown['serve'] = _normalize_kpi_to_rating(serve_in,
                                                      KPI_TARGETS['serve_in_rate']['min'],
                                                      KPI_TARGETS['serve_in_rate']['optimal'],
                                                      KPI_TARGETS['serve_in_rate']['max'])
        
        # Calculate base rating from expected actions (90%)
        base_rating = (breakdown['attack'] * WEIGHT_ATTACK + 
                      breakdown['reception'] * WEIGHT_RECEPTION + 
                      breakdown['block'] * WEIGHT_BLOCK + 
                      breakdown['serve'] * 0.10)  # 10% for serve (not 15%)
        
        # Calculate bonuses (up to 10%)
        bonus = 0.0
        if dig_rate > 0 or (loader and hasattr(loader, 'player_data_by_set')):
            has_digs = any(player_name in loader.player_data_by_set.get(set_num, {}) and 
                          float(loader.player_data_by_set[set_num][player_name].get('stats', {}).get('Dig_Total', 0) or 0) > 0
                          for set_num in loader.player_data_by_set.keys()) if loader and hasattr(loader, 'player_data_by_set') else False
            if has_digs or dig_rate > 0:
                breakdown['defense'] = _normalize_kpi_to_rating(dig_rate,
                                                                KPI_TARGETS['dig_rate']['min'],
                                                                KPI_TARGETS['dig_rate']['optimal'],
                                                                KPI_TARGETS['dig_rate']['max'])
                if breakdown['defense'] >= BONUS_THRESHOLD:
                    bonus += 0.05  # 5% bonus
            else:
                breakdown['defense'] = 0.0
        else:
            breakdown['defense'] = 0.0
        
        if setting_q > 0 or player_data.get('total_sets', 0) > 0:
            targets_setting = {'min': 0.70, 'optimal': 0.80, 'max': 0.90}
            breakdown['setting'] = _normalize_kpi_to_rating(setting_q, targets_setting['min'], 
                                                           targets_setting['optimal'], targets_setting['max'])
            if breakdown['setting'] >= BONUS_THRESHOLD:
                bonus += 0.05  # 5% bonus
        else:
            breakdown['setting'] = 0.0
        
        rating = base_rating + min(bonus, MAX_BONUS)
        
    elif position and position.startswith('MB'):
        # MIDDLE BLOCKER: Expected = Attack (30%) + Block (25%) + Serve (15%) + Dig (20%) = 90%
        # Bonus: Reception, Setting (up to 10%)
        attack_kill = kpis.get('attack_kill_pct', 0)
        block_kill = kpis.get('block_kill_pct', 0)
        serve_in = kpis.get('serve_in_rate', 0)
        dig_rate = kpis.get('dig_rate', 0)
        reception_q = kpis.get('reception_quality', 0)
        setting_q = kpis.get('setting_quality', 0)
        
        breakdown['attack'] = _normalize_kpi_to_rating(attack_kill,
                                                      KPI_TARGETS['kill_percentage']['min'],
                                                      KPI_TARGETS['kill_percentage']['optimal'],
                                                      KPI_TARGETS['kill_percentage']['max'])
        breakdown['block'] = _normalize_kpi_to_rating(block_kill,
                                                      KPI_TARGETS['block_kill_percentage']['min'],
                                                      KPI_TARGETS['block_kill_percentage']['optimal'],
                                                      KPI_TARGETS['block_kill_percentage']['max'])
        breakdown['serve'] = _normalize_kpi_to_rating(serve_in,
                                                      KPI_TARGETS['serve_in_rate']['min'],
                                                      KPI_TARGETS['serve_in_rate']['optimal'],
                                                      KPI_TARGETS['serve_in_rate']['max'])
        breakdown['defense'] = _normalize_kpi_to_rating(dig_rate,
                                                        KPI_TARGETS['dig_rate']['min'],
                                                        KPI_TARGETS['dig_rate']['optimal'],
                                                        KPI_TARGETS['dig_rate']['max'])
        
        # Calculate base rating from expected actions (90%)
        base_rating = (breakdown['attack'] * WEIGHT_ATTACK + 
                      breakdown['block'] * WEIGHT_BLOCK + 
                      breakdown['serve'] * WEIGHT_SERVE + 
                      breakdown['defense'] * WEIGHT_DIG)
        
        # Calculate bonuses (up to 10%)
        bonus = 0.0
        if reception_q > 0 or player_data.get('total_receives', 0) > 0:
            breakdown['reception'] = _normalize_kpi_to_rating(reception_q,
                                                             KPI_TARGETS['reception_quality']['min'],
                                                             KPI_TARGETS['reception_quality']['optimal'],
                                                             KPI_TARGETS['reception_quality']['max'])
            if breakdown['reception'] >= BONUS_THRESHOLD:
                bonus += 0.05  # 5% bonus
        else:
            breakdown['reception'] = 0.0
        
        if setting_q > 0 or player_data.get('total_sets', 0) > 0:
            targets_setting = {'min': 0.70, 'optimal': 0.80, 'max': 0.90}
            breakdown['setting'] = _normalize_kpi_to_rating(setting_q, targets_setting['min'], 
                                                           targets_setting['optimal'], targets_setting['max'])
            if breakdown['setting'] >= BONUS_THRESHOLD:
                bonus += 0.05  # 5% bonus
        else:
            breakdown['setting'] = 0.0
        
        rating = base_rating + min(bonus, MAX_BONUS)
        
    elif position == 'OPP':
        # OPPOSITE: Expected = Attack (30%) + Block (25%) + Serve (15%) + Dig (20%) = 90%
        # Bonus: Reception, Setting (up to 10%)
        attack_kill = kpis.get('attack_kill_pct', 0)
        block_kill = kpis.get('block_kill_pct', 0)
        serve_in = kpis.get('serve_in_rate', 0)
        dig_rate = kpis.get('dig_rate', 0)
        reception_q = kpis.get('reception_quality', 0)
        setting_q = kpis.get('setting_quality', 0)
        
        breakdown['attack'] = _normalize_kpi_to_rating(attack_kill,
                                                       KPI_TARGETS['kill_percentage']['min'],
                                                       KPI_TARGETS['kill_percentage']['optimal'],
                                                       KPI_TARGETS['kill_percentage']['max'])
        breakdown['block'] = _normalize_kpi_to_rating(block_kill,
                                                       KPI_TARGETS['block_kill_percentage']['min'],
                                                       KPI_TARGETS['block_kill_percentage']['optimal'],
                                                       KPI_TARGETS['block_kill_percentage']['max'])
        breakdown['serve'] = _normalize_kpi_to_rating(serve_in,
                                                      KPI_TARGETS['serve_in_rate']['min'],
                                                      KPI_TARGETS['serve_in_rate']['optimal'],
                                                      KPI_TARGETS['serve_in_rate']['max'])
        breakdown['defense'] = _normalize_kpi_to_rating(dig_rate,
                                                        KPI_TARGETS['dig_rate']['min'],
                                                        KPI_TARGETS['dig_rate']['optimal'],
                                                        KPI_TARGETS['dig_rate']['max'])
        
        # Calculate base rating from expected actions (90%)
        base_rating = (breakdown['attack'] * WEIGHT_ATTACK + 
                      breakdown['block'] * WEIGHT_BLOCK + 
                      breakdown['serve'] * WEIGHT_SERVE + 
                      breakdown['defense'] * WEIGHT_DIG)
        
        # Calculate bonuses (up to 10%)
        bonus = 0.0
        if reception_q > 0 or player_data.get('total_receives', 0) > 0:
            breakdown['reception'] = _normalize_kpi_to_rating(reception_q,
                                                             KPI_TARGETS['reception_quality']['min'],
                                                             KPI_TARGETS['reception_quality']['optimal'],
                                                             KPI_TARGETS['reception_quality']['max'])
            if breakdown['reception'] >= BONUS_THRESHOLD:
                bonus += 0.05  # 5% bonus
        else:
            breakdown['reception'] = 0.0
        
        if setting_q > 0 or player_data.get('total_sets', 0) > 0:
            targets_setting = {'min': 0.70, 'optimal': 0.80, 'max': 0.90}
            breakdown['setting'] = _normalize_kpi_to_rating(setting_q, targets_setting['min'], 
                                                           targets_setting['optimal'], targets_setting['max'])
            if breakdown['setting'] >= BONUS_THRESHOLD:
                bonus += 0.05  # 5% bonus
        else:
            breakdown['setting'] = 0.0
        
        rating = base_rating + min(bonus, MAX_BONUS)
        
    elif position == 'L':
        # LIBERO: Expected = Reception (45%) + Dig (45%) = 90%
        # Bonus: Setting (up to 10%)
        # Liberos CANNOT serve (hard rule) - no attack, block, serve
        reception_q = kpis.get('reception_quality', 0)
        dig_rate = kpis.get('dig_rate', 0)
        setting_q = kpis.get('setting_quality', 0)
        
        breakdown['reception'] = _normalize_kpi_to_rating(reception_q,
                                                         KPI_TARGETS['reception_quality']['min'],
                                                         KPI_TARGETS['reception_quality']['optimal'],
                                                         KPI_TARGETS['reception_quality']['max'])
        breakdown['defense'] = _normalize_kpi_to_rating(dig_rate,
                                                        KPI_TARGETS['dig_rate']['min'],
                                                        KPI_TARGETS['dig_rate']['optimal'],
                                                        KPI_TARGETS['dig_rate']['max'])
        
        # Liberos don't serve, attack, or block - set to 0
        breakdown['serve'] = 0.0
        breakdown['attack'] = 0.0
        breakdown['block'] = 0.0
        
        # Calculate base rating from expected actions (90%)
        base_rating = (breakdown['reception'] * 0.45 + 
                      breakdown['defense'] * 0.45)
        
        # Calculate bonuses (up to 10%)
        bonus = 0.0
        if setting_q > 0 or player_data.get('total_sets', 0) > 0:
            targets_setting = {'min': 0.70, 'optimal': 0.80, 'max': 0.90}
            breakdown['setting'] = _normalize_kpi_to_rating(setting_q, targets_setting['min'], 
                                                           targets_setting['optimal'], targets_setting['max'])
            if breakdown['setting'] >= BONUS_THRESHOLD:
                bonus += 0.10  # 10% bonus
        else:
            breakdown['setting'] = 0.0
        
        rating = base_rating + min(bonus, MAX_BONUS)
        
        # Ensure liberos never have serve, attack, or block ratings (double-check)
        breakdown['serve'] = 0.0
        breakdown['attack'] = 0.0
        breakdown['block'] = 0.0
        
    else:
        # Unknown/Other: General rating
        attack_kill = kpis.get('attack_kill_pct', 0)
        serve_in = kpis.get('serve_in_rate', 0)
        
        breakdown['attack'] = _normalize_kpi_to_rating(attack_kill,
                                                       KPI_TARGETS['kill_percentage']['min'],
                                                       KPI_TARGETS['kill_percentage']['optimal'],
                                                       KPI_TARGETS['kill_percentage']['max']) if attack_kill > 0 else 6.0
        breakdown['serve'] = _normalize_kpi_to_rating(serve_in,
                                                      KPI_TARGETS['serve_in_rate']['min'],
                                                      KPI_TARGETS['serve_in_rate']['optimal'],
                                                      KPI_TARGETS['serve_in_rate']['max']) if serve_in > 0 else 6.0
        
        rating = (breakdown['attack'] * 0.5 + breakdown['serve'] * 0.5) if (attack_kill > 0 or serve_in > 0) else 6.0
    
    # Round to 1 decimal place
    rating = round(rating, 1)
    for key in breakdown:
        breakdown[key] = round(breakdown[key], 1)
    
    return rating, breakdown






def _display_navigation_ctas() -> None:
    """HIGH PRIORITY 6: Display navigation CTAs in Player Comparison."""
    st.markdown("---")
    st.markdown("### 🔗 Navigate to Other Views")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📊 View Team Overview", key="nav_comp_to_team", use_container_width=True):
            st.session_state['navigation_target'] = 'Team Overview'
            st.rerun()
    
    with col2:
        if st.button("👥 View Player Analysis", key="nav_comp_to_player", use_container_width=True):
            st.session_state['navigation_target'] = 'Player Analysis'
            st.rerun()
    
    st.markdown("---")


def _display_export_options(comparison_df: pd.DataFrame, analyzer: MatchAnalyzer, loader=None) -> None:
    """MEDIUM PRIORITY 14: Display export options for Player Comparison."""
    st.markdown("### 📥 Export Player Comparison")
    
    from datetime import datetime
    import io
    excel_output = io.BytesIO()
    with pd.ExcelWriter(excel_output, engine='openpyxl') as writer:
        comparison_df.to_excel(writer, sheet_name='Player Comparison', index=False)
    excel_data = excel_output.getvalue()
    st.download_button(
        label="📊 Export to Excel",
        data=excel_data,
        file_name=f"player_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
        help="Export player comparison table to Excel"
    )
    
    st.markdown("---")


