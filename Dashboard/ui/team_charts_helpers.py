"""
Helper functions for creating team performance charts.
Extracted from create_team_charts() for better organization.
"""
from typing import Dict, Any
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from match_analyzer import MatchAnalyzer
from config import CHART_COLORS
from charts.utils import apply_beautiful_theme, plotly_config


def _create_action_distribution_chart(df: pd.DataFrame) -> None:
    """Create and display action distribution pie chart.
    
    Args:
        df: Match data DataFrame
    """
    action_counts = df['action'].value_counts()
    fig_actions = px.pie(
        values=action_counts.values,
        names=action_counts.index,
        title="Action Distribution",
        color_discrete_sequence=px.colors.qualitative.Set3,
        hole=0.4  # Donut chart
    )
    fig_actions.update_traces(
        textposition='inside',
        textinfo='percent+label',
        hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>',
        marker=dict(line=dict(color='rgba(0,0,0,0.2)', width=1))
    )
    fig_actions = apply_beautiful_theme(fig_actions, "Action Distribution")
    st.plotly_chart(fig_actions, use_container_width=True, config=plotly_config)
    
    # Add note about action distribution
    dominant_action = action_counts.idxmax()
    dominant_pct = (action_counts.max() / action_counts.sum()) * 100
    if dominant_pct > 30:
        st.caption(f"💡 **Note:** {dominant_action.capitalize()} actions represent {dominant_pct:.1f}% of total actions")


def _create_outcome_distribution_chart(df: pd.DataFrame) -> None:
    """Create and display outcome distribution bar chart.
    
    Args:
        df: Match data DataFrame
    """
    outcome_counts = df['outcome'].value_counts()
    # Fix y-axis to show all data with padding
    max_value = outcome_counts.values.max()
    y_max = max_value * 1.15  # Add 15% padding
    
    fig_outcomes = px.bar(
        x=outcome_counts.index,
        y=outcome_counts.values,
        title="Outcome Distribution",
        labels={'x': 'Outcome', 'y': 'Count'},
        color_discrete_sequence=px.colors.qualitative.Set3
    )
    fig_outcomes.update_xaxes(
        title_font=dict(color='#050d76'),
        tickfont=dict(color='#050d76')
    )
    fig_outcomes.update_yaxes(title_font=dict(color='#050d76'))
    fig_outcomes.update_traces(
        marker=dict(line=dict(color='rgba(0,0,0,0.2)', width=1)),
        hovertemplate='<b>%{x}</b><br>Count: %{y}<extra></extra>'
    )
    fig_outcomes = apply_beautiful_theme(fig_outcomes, "Outcome Distribution", height=400)
    fig_outcomes.update_layout(
        showlegend=False,
        yaxis=dict(range=[0, y_max])
    )
    st.plotly_chart(fig_outcomes, use_container_width=True, config=plotly_config)


def _calculate_set_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate performance metrics by set.
    
    Args:
        df: Match data DataFrame
        
    Returns:
        DataFrame with set metrics
    """
    set_stats = df.groupby('set_number').agg({
        'action': 'count',
        'outcome': lambda x: (x == 'kill').sum()
    }).rename(columns={'action': 'Total_Actions', 'outcome': 'Kills'})
    
    # Calculate efficiency metrics by set
    set_metrics = []
    for set_num in set_stats.index:
        set_df = df[df['set_number'] == set_num]
        
        # Attack efficiency
        attacks = set_df[set_df['action'] == 'attack']
        attack_kills = len(attacks[attacks['outcome'] == 'kill'])
        attack_errors = len(attacks[attacks['outcome'] == 'error'])
        attack_eff = (attack_kills - attack_errors) / len(attacks) if len(attacks) > 0 else 0
        
        # Service efficiency
        serves = set_df[set_df['action'] == 'serve']
        service_aces = len(serves[serves['outcome'] == 'ace'])
        service_errors = len(serves[serves['outcome'] == 'error'])
        service_eff = (service_aces - service_errors) / len(serves) if len(serves) > 0 else 0
        
        # Errors
        errors = len(set_df[set_df['outcome'] == 'error'])
        
        set_metrics.append({
            'Set': set_num,
            'Total Actions': set_stats.loc[set_num, 'Total_Actions'],
            'Kills': set_stats.loc[set_num, 'Kills'],
            'Attack Efficiency': attack_eff,
            'Service Efficiency': service_eff,
            'Errors': errors
        })
    
    return pd.DataFrame(set_metrics), set_stats


def _create_set_by_set_charts(df: pd.DataFrame, set_metrics_df: pd.DataFrame, set_stats: pd.DataFrame) -> None:
    """Create and display set-by-set performance charts.
    
    Args:
        df: Match data DataFrame
        set_metrics_df: DataFrame with set metrics
        set_stats: DataFrame with set statistics
    """
    st.markdown("### 🎯 Set-by-Set Performance")
    
    fig_set = make_subplots(
        rows=1, cols=3,
        subplot_titles=('Total Actions by Set', 'Attack Efficiency by Set', 'Errors by Set'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Total Actions
    fig_set.add_trace(
        go.Bar(x=set_stats.index, y=set_stats['Total_Actions'], name='Total Actions',
               marker=dict(
                   color=set_stats['Total_Actions'],
                   colorscale=[[0, CHART_COLORS['primary']], [1, CHART_COLORS['secondary']]],
                   line=dict(width=2)
               ),
               showlegend=False),
        row=1, col=1
    )
    
    # Attack Efficiency
    fig_set.add_trace(
        go.Bar(x=set_metrics_df['Set'], y=set_metrics_df['Attack Efficiency'], name='Attack Efficiency',
               marker=dict(
                   color=set_metrics_df['Attack Efficiency'],
                   colorscale=[[0, CHART_COLORS['success']], [1, '#06D6A0']],
                   line=dict(width=2)
               ),
               showlegend=False),
        row=1, col=2
    )
    
    # Errors
    fig_set.add_trace(
        go.Bar(x=set_metrics_df['Set'], y=set_metrics_df['Errors'], name='Errors',
               marker=dict(
                   color=set_metrics_df['Errors'],
                   colorscale=[[0, CHART_COLORS['warning']], [1, CHART_COLORS['danger']]],
                   line=dict(width=2)
               ),
               showlegend=False),
        row=1, col=3
    )
    
    # Update axes with beautiful styling
    fig_set.update_xaxes(
        title_text="Set Number", 
        row=1, col=1, 
        dtick=1,
        gridcolor='rgba(102, 126, 234, 0.1)',
        linecolor='rgba(102, 126, 234, 0.3)',
        title_font=dict(color='#050d76')
    )
    fig_set.update_xaxes(
        title_text="Set Number", 
        row=1, col=2, 
        dtick=1,
        gridcolor='rgba(102, 126, 234, 0.1)',
        linecolor='rgba(102, 126, 234, 0.3)',
        title_font=dict(color='#050d76')
    )
    fig_set.update_xaxes(
        title_text="Set Number", 
        row=1, col=3, 
        dtick=1,
        gridcolor='rgba(102, 126, 234, 0.1)',
        linecolor='rgba(102, 126, 234, 0.3)',
        title_font=dict(color='#050d76')
    )
    
    fig_set.update_yaxes(
        title_text="Total Actions", 
        row=1, col=1,
        gridcolor='rgba(102, 126, 234, 0.1)',
        linecolor='rgba(102, 126, 234, 0.3)',
        title_font=dict(color='#050d76')
    )
    fig_set.update_yaxes(
        title_text="Efficiency", 
        row=1, col=2, 
        tickformat='.1%',
        gridcolor='rgba(102, 126, 234, 0.1)',
        linecolor='rgba(102, 126, 234, 0.3)',
        title_font=dict(color='#050d76')
    )
    fig_set.update_yaxes(
        title_text="Errors", 
        row=1, col=3,
        gridcolor='rgba(102, 126, 234, 0.1)',
        linecolor='rgba(102, 126, 234, 0.3)',
        title_font=dict(color='#050d76')
    )
    
    fig_set.update_layout(
        height=450,
        showlegend=False,
        paper_bgcolor='rgba(255,255,255,0)',
        plot_bgcolor='rgba(255,255,255,0.95)',
        font=dict(family='Inter, sans-serif', size=12, color='#2C3E50'),
        title_font=dict(family='Poppins, sans-serif', size=16, color='#1A1A2E'),
        margin=dict(l=60, r=40, t=80, b=60)
    )
    
    st.plotly_chart(fig_set, use_container_width=True, config=plotly_config)
    
    # Display set metrics table
    st.markdown("#### 📊 Set-by-Set Metrics Summary")
    display_df = set_metrics_df.copy()
    display_df['Attack Efficiency'] = display_df['Attack Efficiency'].apply(lambda x: f"{x:.1%}")
    display_df['Service Efficiency'] = display_df['Service Efficiency'].apply(lambda x: f"{x:.1%}")
    st.dataframe(display_df, use_container_width=True, hide_index=True)


def _create_rotation_heatmap(analyzer: MatchAnalyzer) -> None:
    """Create and display rotation performance heatmap.
    
    Args:
        analyzer: MatchAnalyzer instance
    """
    st.markdown("### 🔄 Rotation Performance Analysis")
    rotation_stats = analyzer.analyze_rotation_performance()
    
    if not rotation_stats:
        st.info("No rotation data available")
        return
    
    # Prepare data for heatmap
    rotations = sorted(rotation_stats.keys())
    metrics = ['attack_efficiency', 'service_efficiency', 'reception_percentage', 'block_efficiency']
    
    heatmap_data = []
    metric_labels = ['Attack Eff', 'Service Eff', 'Reception %', 'Block Eff']
    
    for rotation in rotations:
        row_data = []
        for metric in metrics:
            value = rotation_stats[rotation].get(metric, 0)
            row_data.append(value)
        heatmap_data.append(row_data)
    
    # Create heatmap
    fig_heatmap = go.Figure(data=go.Heatmap(
        z=heatmap_data,
        x=metric_labels,
        y=[f"Rotation {r}" for r in rotations],
        colorscale=[[0, '#FF4444'], [0.5, '#FFD700'], [1, '#00AA00']],  # Red to Yellow to Green
        text=[[f"{val:.1%}" if val != 0 else "" for val in row] for row in heatmap_data],
        texttemplate="%{text}",
        textfont={"size": 11},
        colorbar=dict(title="Efficiency")
    ))
    
    fig_heatmap.update_layout(
        title="Rotation Performance Heatmap",
        xaxis_title="Metric",
        yaxis_title="Rotation",
        height=400,
        font=dict(family='Inter, sans-serif', size=12, color='#050d76'),
        paper_bgcolor='rgba(255,255,255,0)',
        plot_bgcolor='rgba(255,255,255,0.95)'
    )
    
    st.plotly_chart(fig_heatmap, use_container_width=True, config=plotly_config)
    
    # Display rotation summary table
    rotation_summary = []
    for rotation in rotations:
        stats = rotation_stats[rotation]
        rotation_summary.append({
            'Rotation': f"Rotation {rotation}",
            'Attack Eff': f"{stats.get('attack_efficiency', 0):.1%}",
            'Service Eff': f"{stats.get('service_efficiency', 0):.1%}",
            'Reception %': f"{stats.get('reception_percentage', 0):.1%}",
            'Block Eff': f"{stats.get('block_efficiency', 0):.1%}",
            'Total Actions': stats.get('total_actions', 0)
        })
    
    rotation_df = pd.DataFrame(rotation_summary)
    st.dataframe(rotation_df, use_container_width=True, hide_index=True)


def _create_pass_quality_charts(df: pd.DataFrame, team_stats: Dict[str, Any]) -> None:
    """Create and display pass quality analysis charts.
    
    Args:
        df: Match data DataFrame
        team_stats: Team statistics dictionary
    """
    if not team_stats or team_stats.get('perfect_passes', 0) + team_stats.get('good_passes', 0) + team_stats.get('poor_passes', 0) == 0:
        return
    
    st.markdown("### 🎯 Pass Quality Analysis")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Pass Quality Distribution
        pass_data = {
            'Quality': ['Perfect (1)', 'Good (2)', 'Poor (3)'],
            'Count': [
                team_stats.get('perfect_passes', 0),
                team_stats.get('good_passes', 0),
                team_stats.get('poor_passes', 0)
            ]
        }
        pass_df = pd.DataFrame(pass_data)
        total_passes = pass_df['Count'].sum()
        pass_df['Percentage'] = (pass_df['Count'] / total_passes * 100) if total_passes > 0 else 0
        
        fig_pass = px.pie(
            pass_df,
            values='Count',
            names='Quality',
            title="Pass Quality Distribution",
            color='Quality',
            hole=0.4,  # Donut chart
            color_discrete_map={
                'Perfect (1)': '#00AA00',
                'Good (2)': '#FFD700',
                'Poor (3)': '#FF4500'
            }
        )
        fig_pass.update_traces(textposition='inside', textinfo='percent+label+value')
        fig_pass = apply_beautiful_theme(fig_pass, "Pass Quality Distribution")
        st.plotly_chart(fig_pass, use_container_width=True, config=plotly_config)
    
    with col2:
        # Pass Quality to Attack Efficiency Correlation
        if 'pass_quality' in df.columns and team_stats.get('first_ball_efficiency') is not None:
            # Calculate attack efficiency by pass quality
            pass_attack_stats = []
            for quality in [1, 2, 3]:
                quality_label = ['Perfect', 'Good', 'Poor'][quality - 1]
                quality_attacks = df[(df['action'] == 'attack') & (df['pass_quality'] == quality)]
                if len(quality_attacks) > 0:
                    kills = len(quality_attacks[quality_attacks['outcome'] == 'kill'])
                    errors = len(quality_attacks[quality_attacks['outcome'] == 'error'])
                    efficiency = (kills - errors) / len(quality_attacks)
                    pass_attack_stats.append({
                        'Pass Quality': quality_label,
                        'Attack Efficiency': efficiency,
                        'Sample Size': len(quality_attacks)
                    })
            
            if pass_attack_stats:
                pass_eff_df = pd.DataFrame(pass_attack_stats)
                fig_pass_eff = px.bar(
                    pass_eff_df,
                    x='Pass Quality',
                    y='Attack Efficiency',
                    title="Attack Efficiency by Pass Quality",
                    color='Attack Efficiency',
                    color_continuous_scale=['#FF4500', '#FFD700', '#00AA00'],
                    text='Sample Size'
                )
                fig_pass_eff.update_traces(texttemplate='n=%{text}', textposition='outside')
                fig_pass_eff.update_yaxes(tickformat='.1%')
                fig_pass_eff = apply_beautiful_theme(fig_pass_eff, "Attack Efficiency by Pass Quality")
                st.plotly_chart(fig_pass_eff, use_container_width=True, config=plotly_config)

