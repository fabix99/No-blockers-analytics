"""
Premium UI Components for Next-Level Dashboard Visualization.

Provides visually stunning, sports-broadcast quality components:
- Gauge charts for KPIs
- Performance scorecards with letter grades
- Animated progress bars
- Premium metric cards
"""
import streamlit as st
import plotly.graph_objects as go
from typing import Dict, Any, Optional, List, Tuple
import math

# Brand Colors - Team Blue as primary
BRAND_BLUE = "#040C7B"
BRAND_BLUE_LIGHT = "#1a237e"
BRAND_BLUE_DARK = "#000051"
ACCENT_GOLD = "#FFD700"
SUCCESS_GREEN = "#00C853"
WARNING_YELLOW = "#FFC107"
DANGER_RED = "#FF5252"
NEUTRAL_GRAY = "#78909C"


def get_letter_grade(value: float, target: float, lower_is_better: bool = False) -> Tuple[str, str]:
    """Calculate letter grade based on performance vs target.
    
    Args:
        value: Actual performance value (0-1 for percentages)
        target: Target value
        lower_is_better: If True, lower values are better
        
    Returns:
        Tuple of (letter_grade, color_hex)
    """
    if lower_is_better:
        ratio = target / value if value > 0 else 1.0
    else:
        ratio = value / target if target > 0 else 1.0
    
    if ratio >= 1.20:
        return ("A+", SUCCESS_GREEN)
    elif ratio >= 1.10:
        return ("A", SUCCESS_GREEN)
    elif ratio >= 1.00:
        return ("A-", "#4CAF50")
    elif ratio >= 0.90:
        return ("B+", "#8BC34A")
    elif ratio >= 0.80:
        return ("B", WARNING_YELLOW)
    elif ratio >= 0.70:
        return ("C+", "#FF9800")
    elif ratio >= 0.60:
        return ("C", "#FF5722")
    elif ratio >= 0.50:
        return ("D", DANGER_RED)
    else:
        return ("F", "#B71C1C")


def create_gauge_chart(
    value: float,
    title: str,
    target: float = 0.5,
    min_val: float = 0.0,
    max_val: float = 1.0,
    is_percentage: bool = True,
    height: int = 200
) -> go.Figure:
    """Create a premium gauge chart for KPI visualization.
    
    Args:
        value: Current value
        title: Chart title
        target: Target value (for color zones)
        min_val: Minimum scale value
        max_val: Maximum scale value
        is_percentage: Format as percentage
        height: Chart height in pixels
        
    Returns:
        Plotly figure
    """
    # Determine color based on value vs target
    if value >= target:
        bar_color = SUCCESS_GREEN
    elif value >= target * 0.85:
        bar_color = WARNING_YELLOW
    else:
        bar_color = DANGER_RED
    
    # Format display value
    if is_percentage:
        display_value = f"{value * 100:.0f}%"
        target_display = f"Target: {target * 100:.0f}%"
    else:
        display_value = f"{value:.1f}"
        target_display = f"Target: {target:.1f}"
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=value * 100 if is_percentage else value,
        number={'suffix': '%' if is_percentage else '', 'font': {'size': 36, 'color': BRAND_BLUE, 'family': 'Inter'}},
        gauge={
            'axis': {
                'range': [min_val * 100 if is_percentage else min_val, 
                          max_val * 100 if is_percentage else max_val],
                'tickwidth': 1,
                'tickcolor': BRAND_BLUE,
                'tickfont': {'size': 10, 'color': '#666'}
            },
            'bar': {'color': bar_color, 'thickness': 0.75},
            'bgcolor': '#E8EAF6',
            'borderwidth': 2,
            'bordercolor': BRAND_BLUE,
            'steps': [
                {'range': [0, target * 85 if is_percentage else target * 0.85], 'color': '#FFEBEE'},
                {'range': [target * 85 if is_percentage else target * 0.85, 
                           target * 100 if is_percentage else target], 'color': '#FFF8E1'},
                {'range': [target * 100 if is_percentage else target, 
                           max_val * 100 if is_percentage else max_val], 'color': '#E8F5E9'}
            ],
            'threshold': {
                'line': {'color': BRAND_BLUE, 'width': 3},
                'thickness': 0.8,
                'value': target * 100 if is_percentage else target
            }
        },
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    
    fig.update_layout(
        height=height,
        margin=dict(l=20, r=20, t=40, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        font={'family': 'Inter, sans-serif'},
        annotations=[
            dict(
                text=target_display,
                x=0.5, y=-0.15,
                showarrow=False,
                font=dict(size=12, color='#666')
            )
        ]
    )
    
    return fig


def display_premium_metric_card(
    label: str,
    value: float,
    target: float,
    formula: str = "",
    numerator: Optional[int] = None,
    denominator: Optional[int] = None,
    lower_is_better: bool = False,
    show_gauge: bool = True
) -> None:
    """Display a premium metric card with gauge visualization.
    
    Args:
        label: Metric label
        value: Current value (0-1 for percentages)
        target: Target value
        formula: Formula description
        numerator: Count of successes
        denominator: Total count
        lower_is_better: If True, lower values are better
        show_gauge: Whether to show gauge chart
    """
    grade, grade_color = get_letter_grade(value, target, lower_is_better)
    
    # Calculate delta
    delta = value - target
    if lower_is_better:
        delta_color = SUCCESS_GREEN if delta <= 0 else DANGER_RED
        delta_sign = "" if delta <= 0 else "+"
    else:
        delta_color = SUCCESS_GREEN if delta >= 0 else DANGER_RED
        delta_sign = "+" if delta >= 0 else ""
    
    # Sample size display
    sample_info = f"({numerator}/{denominator})" if numerator is not None and denominator is not None else ""
    
    # Create the premium card HTML
    card_html = f"""
    <div style="
        background: linear-gradient(135deg, #ffffff 0%, #f5f7ff 100%);
        border-radius: 16px;
        padding: 20px;
        box-shadow: 0 4px 20px rgba(4, 12, 123, 0.1);
        border: 1px solid rgba(4, 12, 123, 0.1);
        margin-bottom: 16px;
        position: relative;
        overflow: hidden;
    ">
        <!-- Accent stripe -->
        <div style="
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, {BRAND_BLUE} 0%, {grade_color} 100%);
        "></div>
        
        <!-- Header with grade badge -->
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px;">
            <div>
                <div style="font-size: 14px; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 0.5px;">
                    {label}
                </div>
                <div style="font-size: 11px; color: #999; margin-top: 2px;">
                    {formula}
                </div>
            </div>
            <div style="
                background: {grade_color};
                color: white;
                font-size: 18px;
                font-weight: 700;
                padding: 8px 14px;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.15);
            ">
                {grade}
            </div>
        </div>
        
        <!-- Value display -->
        <div style="display: flex; align-items: baseline; gap: 8px; margin-bottom: 8px;">
            <span style="font-size: 42px; font-weight: 700; color: {BRAND_BLUE};">
                {value * 100:.0f}%
            </span>
            <span style="font-size: 14px; color: #999;">
                {sample_info}
            </span>
        </div>
        
        <!-- Progress bar -->
        <div style="
            width: 100%;
            height: 8px;
            background: #E8EAF6;
            border-radius: 4px;
            overflow: hidden;
            margin-bottom: 8px;
        ">
            <div style="
                width: {min(value / max(target * 1.2, 0.01) * 100, 100)}%;
                height: 100%;
                background: linear-gradient(90deg, {grade_color} 0%, {BRAND_BLUE} 100%);
                border-radius: 4px;
                transition: width 0.5s ease;
            "></div>
        </div>
        
        <!-- Delta vs target -->
        <div style="display: flex; justify-content: space-between; font-size: 13px;">
            <span style="color: #666;">Target: {target * 100:.0f}%</span>
            <span style="color: {delta_color}; font-weight: 600;">
                {delta_sign}{delta * 100:.1f}% vs target
            </span>
        </div>
    </div>
    """
    
    st.markdown(card_html, unsafe_allow_html=True)


def display_performance_scorecard(kpis: Dict[str, float], targets: Dict[str, Dict[str, float]]) -> None:
    """Display a performance scorecard with letter grades for all skill areas.
    
    Args:
        kpis: Dictionary of KPI values (e.g., {'attack_kill_pct': 0.45})
        targets: Dictionary of target dicts (e.g., {'kill_percentage': {'optimal': 0.42}})
    """
    # Define skill areas with their KPIs and target keys
    skill_areas = [
        ('Attack', 'attack_kill_pct', 'kill_percentage', '⚔️'),
        ('Serve', 'serve_in_rate', 'serve_in_rate', '🎾'),
        ('Reception', 'reception_quality', 'reception_quality', '🛡️'),
        ('Block', 'block_kill_pct', 'block_kill_percentage', '🧱'),
    ]
    
    cards_html = ""
    for skill_name, kpi_key, target_key, emoji in skill_areas:
        value = kpis.get(kpi_key, 0)
        target_dict = targets.get(target_key, {})
        target = target_dict.get('optimal', 0.5) if isinstance(target_dict, dict) else target_dict
        grade, grade_color = get_letter_grade(value, target)
        
        delta = value - target
        delta_sign = "+" if delta >= 0 else ""
        delta_color = SUCCESS_GREEN if delta >= 0 else DANGER_RED
        
        cards_html += f'<div style="flex: 1; min-width: 140px; background: linear-gradient(180deg, #ffffff 0%, #f8f9ff 100%); border-radius: 12px; padding: 16px; text-align: center; box-shadow: 0 2px 12px rgba(4, 12, 123, 0.08); border: 1px solid rgba(4, 12, 123, 0.08);"><div style="font-size: 24px; margin-bottom: 4px;">{emoji}</div><div style="font-size: 12px; font-weight: 600; color: #666; text-transform: uppercase; letter-spacing: 0.5px;">{skill_name}</div><div style="font-size: 36px; font-weight: 700; color: {grade_color}; margin: 8px 0; text-shadow: 0 2px 4px rgba(0,0,0,0.1);">{grade}</div><div style="font-size: 18px; font-weight: 600; color: {BRAND_BLUE};">{value * 100:.0f}%</div><div style="font-size: 11px; color: {delta_color}; margin-top: 4px;">{delta_sign}{delta * 100:.0f}% vs target</div></div>'
    
    html_content = f'<div style="margin-bottom: 16px;"><div style="font-size: 16px; font-weight: 700; color: {BRAND_BLUE}; margin-bottom: 12px; display: flex; align-items: center; gap: 8px;"><span style="font-size: 20px;">📊</span>PERFORMANCE SCORECARD</div><div style="display: flex; gap: 16px; flex-wrap: wrap;">{cards_html}</div></div>'
    
    st.markdown(html_content, unsafe_allow_html=True)


def display_match_result_premium(
    outcome: str,
    sets_won: int,
    sets_lost: int,
    set_scores: List[Tuple[int, int]],
    opponent: str = ""
) -> None:
    """Display premium match result banner with set scores.
    
    Args:
        outcome: 'Win', 'Loss', or 'Draw'
        sets_won: Number of sets won
        sets_lost: Number of sets lost
        set_scores: List of (our_score, opponent_score) tuples
        opponent: Opponent name
    """
    if outcome == 'Win':
        bg_gradient = f"linear-gradient(135deg, {SUCCESS_GREEN}15 0%, {SUCCESS_GREEN}05 100%)"
        border_color = SUCCESS_GREEN
        icon = "🏆"
        result_text = "VICTORY"
    elif outcome == 'Loss':
        bg_gradient = f"linear-gradient(135deg, {DANGER_RED}15 0%, {DANGER_RED}05 100%)"
        border_color = DANGER_RED
        icon = "📉"
        result_text = "DEFEAT"
    else:
        bg_gradient = f"linear-gradient(135deg, {NEUTRAL_GRAY}15 0%, {NEUTRAL_GRAY}05 100%)"
        border_color = NEUTRAL_GRAY
        icon = "🤝"
        result_text = "DRAW"
    
    # Build set scores display
    set_scores_html = ""
    for i, (our_score, opp_score) in enumerate(set_scores, 1):
        won_set = our_score > opp_score
        set_bg = SUCCESS_GREEN if won_set else DANGER_RED
        set_scores_html += f'<div style="background: {set_bg}20; border: 2px solid {set_bg}; border-radius: 8px; padding: 8px 16px; text-align: center; min-width: 70px;"><div style="font-size: 10px; color: #666; font-weight: 600;">SET {i}</div><div style="font-size: 20px; font-weight: 700; color: {BRAND_BLUE};">{our_score}-{opp_score}</div></div>'
    
    opponent_text = f"vs {opponent}" if opponent else ""
    
    html_content = f'<div style="background: {bg_gradient}; border: 3px solid {border_color}; border-radius: 16px; padding: 20px; margin-bottom: 16px; box-shadow: 0 4px 24px rgba(0,0,0,0.08);"><div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 20px;"><div style="display: flex; align-items: center; gap: 16px;"><span style="font-size: 48px;">{icon}</span><div><div style="font-size: 14px; color: #666; text-transform: uppercase; letter-spacing: 1px;">{result_text}</div><div style="font-size: 42px; font-weight: 800; color: {BRAND_BLUE};">{sets_won} - {sets_lost}</div><div style="font-size: 14px; color: #666;">{opponent_text}</div></div></div><div style="display: flex; gap: 12px; flex-wrap: wrap;">{set_scores_html}</div></div></div>'
    
    st.markdown(html_content, unsafe_allow_html=True)


def create_player_radar_chart(
    player_name: str,
    stats: Dict[str, float],
    team_avg: Optional[Dict[str, float]] = None,
    height: int = 350
) -> go.Figure:
    """Create a radar chart for player multi-dimensional assessment.
    
    Args:
        player_name: Player's name
        stats: Dict of stat_name -> value (0-1 scale)
        team_avg: Optional team average for comparison
        height: Chart height
        
    Returns:
        Plotly figure
    """
    categories = list(stats.keys())
    values = list(stats.values())
    
    # Close the polygon
    categories = categories + [categories[0]]
    values = values + [values[0]]
    
    fig = go.Figure()
    
    # Add team average if provided
    if team_avg:
        avg_values = [team_avg.get(k, 0) for k in stats.keys()]
        avg_values = avg_values + [avg_values[0]]
        
        fig.add_trace(go.Scatterpolar(
            r=[v * 100 for v in avg_values],
            theta=categories,
            fill='toself',
            fillcolor=f'rgba(120, 144, 156, 0.2)',
            line=dict(color=NEUTRAL_GRAY, width=1, dash='dash'),
            name='Team Average'
        ))
    
    # Add player stats
    fig.add_trace(go.Scatterpolar(
        r=[v * 100 for v in values],
        theta=categories,
        fill='toself',
        fillcolor=f'rgba(4, 12, 123, 0.3)',
        line=dict(color=BRAND_BLUE, width=3),
        name=player_name
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickfont=dict(size=10, color='#666'),
                gridcolor='#E8EAF6'
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color=BRAND_BLUE, family='Inter'),
                gridcolor='#E8EAF6'
            ),
            bgcolor='rgba(0,0,0,0)'
        ),
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=-0.15,
            xanchor='center',
            x=0.5,
            font=dict(size=12)
        ),
        height=height,
        margin=dict(l=60, r=60, t=40, b=60),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(family='Inter, sans-serif')
    )
    
    return fig


def display_premium_section_header(title: str, icon: str = "📊", subtitle: str = "") -> None:
    """Display a premium section header with icon and optional subtitle.
    
    Args:
        title: Section title text
        icon: Icon emoji or text
        subtitle: Optional subtitle text
    """
    subtitle_html = f'<div style="font-size: 14px; color: #666; margin-top: 4px; font-weight: 400;">{subtitle}</div>' if subtitle else ''
    
    html_content = f'<div style="margin-top: 4px; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 2px solid rgba(4, 12, 123, 0.1);"><div style="display: flex; align-items: center; gap: 12px;"><span style="font-size: 28px;">{icon}</span><div><div style="font-size: 24px; font-weight: 700; color: {BRAND_BLUE};">{title}</div>{subtitle_html}</div></div></div>'
    
    st.markdown(html_content, unsafe_allow_html=True)

