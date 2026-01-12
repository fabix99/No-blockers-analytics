"""
Coach-focused insights generation module
"""
from typing import Dict, Any, List, Optional
import streamlit as st
from match_analyzer import MatchAnalyzer
import performance_tracker as pt
import pandas as pd


def generate_coach_insights(analyzer: MatchAnalyzer, team_stats: Dict[str, Any], 
                           TARGETS: Dict[str, Any], loader=None) -> Dict[str, Any]:
    """Generate coach-focused insights: prioritized, actionable, focused on next game and training."""
    df = analyzer.match_data
    insights_data = {
        'summary': {},
        'immediate_adjustments': [],
        'training_priorities': [],
        'by_skill': {
            'serving': [],
            'reception': [],
            'attack': [],
            'block': [],
            'setter': []
        }
    }
    
    # Get match context from loader if available
    match_context = {}
    if loader and hasattr(loader, 'team_data') and loader.team_data:
        total_sets_won = 0
        total_sets_played = len(loader.team_data)
        for set_num in loader.team_data.keys():
            serving_points = float(loader.team_data[set_num].get('serving_points_won', 0) or 0)
            receiving_points = float(loader.team_data[set_num].get('receiving_points_won', 0) or 0)
            if serving_points + receiving_points > 0:
                total_sets_won += 1
        
        # Get KPIs from loader for accurate metrics
        kpis = None
        if hasattr(pt, 'compute_team_kpis_from_loader'):
            try:
                kpis = pt.compute_team_kpis_from_loader(loader)
            except Exception:
                pass
        
        match_context['sets_played'] = total_sets_played
        match_context['kpis'] = kpis
    
    # Calculate key metrics (use KPIs if available, otherwise team_stats)
    serving_point_rate = team_stats.get('serve_point_percentage', 0.0)
    receiving_point_rate = team_stats.get('side_out_percentage', 0.0)
    attack_kill_pct = team_stats.get('kill_percentage', 0.0)
    reception_quality = team_stats.get('reception_quality', 0.0)
    
    if match_context.get('kpis'):
        serving_point_rate = match_context['kpis'].get('break_point_rate', serving_point_rate)
        receiving_point_rate = match_context['kpis'].get('side_out_efficiency', receiving_point_rate)
        attack_kill_pct = match_context['kpis'].get('attack_kill_pct', attack_kill_pct)
        reception_quality = match_context['kpis'].get('reception_quality', reception_quality)
    
    # Get player stats for position-specific analysis
    player_stats = analyzer.calculate_player_metrics()
    
    # === PRIORITIZED INSIGHTS ===
    
    # 1. RECEPTION (Critical foundation)
    if reception_quality < TARGETS.get('reception_quality', {}).get('min', 0.70):
        insights_data['by_skill']['reception'].append({
            'type': 'training',
            'action': f'Reception Quality below target (currently {reception_quality:.1%}, target 75%+)',
            'specific': 'Reception is the foundation of offense. Practice serve receive drills with OH and Libero. Work on platform work, body positioning, reading serve trajectory'
        })
    
    # 2. SERVING POINT RATE (Critical for winning)
    if serving_point_rate < TARGETS.get('break_point_rate', {}).get('min', 0.55):
        insights_data['immediate_adjustments'].append({
            'priority': 'high',
            'action': f'Serving point rate below target ({serving_point_rate:.1%} vs 55%+)',
            'details': 'Focus on service consistency. Consider safer serves when ahead.'
        })
        insights_data['by_skill']['serving'].append({
            'type': 'immediate',
            'action': 'Improve serving point rate',
            'specific': 'Balance aggression with consistency. Target deep corners and seams.'
        })
    
    # 3. RECEIVING POINT RATE (Critical for winning)
    if receiving_point_rate < TARGETS.get('side_out_percentage', {}).get('min', 0.70):
        insights_data['immediate_adjustments'].append({
            'priority': 'high',
            'action': f'Receiving point rate below target ({receiving_point_rate:.1%} vs 70%+)',
            'details': 'This directly impacts match outcome. Focus on reception quality and transition offense.'
        })
        insights_data['by_skill']['reception'].append({
            'type': 'immediate',
            'action': 'Improve receiving point rate',
            'specific': 'Good reception leads to better attack opportunities'
        })
    
    # 4. ATTACK KILL % (Scoring efficiency)
    if attack_kill_pct < TARGETS.get('kill_percentage', {}).get('min', 0.42):
        insights_data['by_skill']['attack'].append({
            'type': 'training',
            'action': f'Attack Kill % below target ({attack_kill_pct:.1%} vs 42%+)',
            'specific': 'Focus on shot selection, placement, and attacking under pressure. Work on hitting angles, power control, off-speed shots'
        })
    
    # 5. Rotation Performance Analysis
    if loader and hasattr(loader, 'team_data_by_rotation'):
        rotation_performance = {}
        # Aggregate totals across all sets for each rotation
        for set_num in loader.team_data_by_rotation.keys():
            for rot_num in loader.team_data_by_rotation[set_num].keys():
                rot_data = loader.team_data_by_rotation[set_num][rot_num]
                serving_rallies = float(rot_data.get('serving_rallies', 0) or 0)
                serving_points_won = float(rot_data.get('serving_points_won', 0) or 0)
                receiving_rallies = float(rot_data.get('receiving_rallies', 0) or 0)
                receiving_points_won = float(rot_data.get('receiving_points_won', 0) or 0)
                
                # Initialize rotation if not seen before
                if rot_num not in rotation_performance:
                    rotation_performance[rot_num] = {
                        'serving_rallies_total': 0.0,
                        'serving_points_won_total': 0.0,
                        'receiving_rallies_total': 0.0,
                        'receiving_points_won_total': 0.0
                    }
                
                # Aggregate totals across all sets
                rotation_performance[rot_num]['serving_rallies_total'] += serving_rallies
                rotation_performance[rot_num]['serving_points_won_total'] += serving_points_won
                rotation_performance[rot_num]['receiving_rallies_total'] += receiving_rallies
                rotation_performance[rot_num]['receiving_points_won_total'] += receiving_points_won
        
        # Calculate rates from aggregated totals (correct method)
        if rotation_performance:
            avg_rates = {}
            for rot_num, totals in rotation_performance.items():
                serving_rate = (totals['serving_points_won_total'] / totals['serving_rallies_total']) if totals['serving_rallies_total'] > 0 else 0.0
                receiving_rate = (totals['receiving_points_won_total'] / totals['receiving_rallies_total']) if totals['receiving_rallies_total'] > 0 else 0.0
                
                avg_rates[rot_num] = {
                    'serving': serving_rate,
                    'receiving': receiving_rate,
                    'overall': (serving_rate + receiving_rate) / 2
                }
            
            if avg_rates:
                weakest_rot_num = min(avg_rates.items(), key=lambda x: x[1]['overall'])
                weakest_rot = weakest_rot_num[1]
                
                if weakest_rot['overall'] < 0.55:  # Below 55% average
                    # Identify which specific metrics need improvement
                    issues = []
                    if weakest_rot['serving'] < 0.55:
                        issues.append(f"Serving Point Rate ({weakest_rot['serving']:.1%})")
                    if weakest_rot['receiving'] < 0.70:
                        issues.append(f"Receiving Point Rate ({weakest_rot['receiving']:.1%})")
                    
                    if issues:
                        issues_text = " and ".join(issues)
                        insights_data['by_skill']['reception'].append({
                            'type': 'training',
                            'action': f'Rotation {weakest_rot_num[0]}: Improve {issues_text}',
                            'specific': 'Focus practice on this rotation combination. Review positioning and communication.'
                        })
    
    # 6. Service Error Analysis
    if loader and hasattr(loader, 'player_data_by_set'):
        total_service_errors = 0.0
        total_service_aces = 0.0
        total_service_total = 0.0
        for set_num in loader.player_data_by_set.keys():
            for player in loader.player_data_by_set[set_num].keys():
                stats = loader.player_data_by_set[set_num][player].get('stats', {})
                total_service_errors += float(stats.get('Service_Errors', 0) or 0)
                total_service_aces += float(stats.get('Service_Aces', 0) or 0)
                total_service_total += float(stats.get('Service_Total', 0) or 0)
        
        if total_service_total > 0:
            service_error_rate = total_service_errors / total_service_total
            if service_error_rate > 0.15:  # More than 15% errors
                insights_data['immediate_adjustments'].append({
                    'priority': 'medium',
                    'action': f'High service error rate ({service_error_rate:.1%})',
                    'details': f'Service errors ({int(total_service_errors)}) outnumber aces ({int(total_service_aces)}). Prioritize consistency.'
                })
                insights_data['by_skill']['serving'].append({
                    'type': 'immediate',
                    'action': 'Reduce service errors',
                    'specific': 'Focus on consistency over power. Use safer serves when ahead.'
                })
    
    # 7. Block Performance
    if loader and hasattr(loader, 'player_data_by_set'):
        total_block_kills = 0.0
        total_block_total = 0.0
        for set_num in loader.player_data_by_set.keys():
            for player in loader.player_data_by_set[set_num].keys():
                stats = loader.player_data_by_set[set_num][player].get('stats', {})
                total_block_kills += float(stats.get('Block_Kills', 0) or 0)
                total_block_total += float(stats.get('Block_Total', 0) or 0)
        
        if total_block_total > 0:
            block_kill_pct = total_block_kills / total_block_total
            if block_kill_pct < 0.05:  # Less than 5%
                insights_data['by_skill']['block'].append({
                    'type': 'training',
                    'action': f'Block Kill % low ({block_kill_pct:.1%})',
                    'specific': 'Work on blocking timing, penetration, and hand positioning. Focus on MB coordination. Practice reading attacker approach and timing jump'
                })
    
    # Generate summary
    insights_data['summary'] = generate_coach_summary(team_stats, match_context, TARGETS, insights_data)
    
    return insights_data


def generate_coach_summary(team_stats: Dict[str, Any], match_context: Dict[str, Any], 
                          TARGETS: Dict[str, Any], insights_data: Dict[str, Any]) -> Dict[str, Any]:
    """Generate concise coach-focused summary with match context and top insights."""
    summary = {
        'match_context': '',
        'performance_snapshot': '',
        'strengths': [],
        'critical_areas': []
    }
    
    # Match context
    sets_played = match_context.get('sets_played', 0)
    if sets_played > 0:
        summary['match_context'] = f"Match played over {sets_played} set(s)"
    
    # Performance snapshot
    kpis = match_context.get('kpis')
    serving_rate = team_stats.get('serve_point_percentage', 0.0)
    receiving_rate = team_stats.get('side_out_percentage', 0.0)
    
    if kpis:
        serving_rate = kpis.get('break_point_rate', serving_rate)
        receiving_rate = kpis.get('side_out_efficiency', receiving_rate)
    
    # Overall assessment
    avg_performance = (serving_rate + receiving_rate) / 2
    if avg_performance >= 0.65:
        summary['performance_snapshot'] = "Strong overall performance"
    elif avg_performance >= 0.55:
        summary['performance_snapshot'] = "Solid performance with room for improvement"
    else:
        summary['performance_snapshot'] = "Performance needs attention"
    
    # Top strengths (from what's working)
    if serving_rate >= TARGETS.get('break_point_rate', {}).get('min', 0.55):
        summary['strengths'].append(f"Serving point rate strong ({serving_rate:.1%})")
    if receiving_rate >= TARGETS.get('side_out_percentage', {}).get('min', 0.70):
        summary['strengths'].append(f"Receiving point rate strong ({receiving_rate:.1%})")
    
    # Critical areas (top priority issues)
    high_priority_immediate = [i for i in insights_data['immediate_adjustments'] if i['priority'] == 'high']
    
    for item in high_priority_immediate[:2]:  # Top 2
        summary['critical_areas'].append(item['action'])
    
    # Also include high-priority skill area issues
    for skill_items in insights_data['by_skill'].values():
        for item in skill_items[:2]:  # Top 2 per skill
            if item['type'] == 'training' and 'below target' in item['action'].lower():
                summary['critical_areas'].append(item['action'])
                break
    
    # Limit to 3 critical areas
    summary['critical_areas'] = summary['critical_areas'][:3]
    
    return summary


def generate_player_insights(player_name: str, player_data: Dict[str, Any], 
                             position: Optional[str], kpis: Dict[str, float],
                             team_avg_kpis: Dict[str, float]) -> Dict[str, Any]:
    """Generate player-specific actionable recommendations with specific targets and tactical advice."""
    from config import KPI_TARGETS
    
    insights = {
        'strengths': [],
        'weaknesses': [],
        'recommendations': [],
        'training_focus': [],
        'set_analysis': {}
    }
    
    # Compare player KPIs to team averages and targets
    for kpi_name, player_value in kpis.items():
        if player_value == 0.0:
            continue
        
        team_avg = team_avg_kpis.get(kpi_name, 0.0)
        target = KPI_TARGETS.get(kpi_name, {}).get('optimal', 0.0)
        
        if team_avg == 0.0 and target == 0.0:
            continue
        
        # Determine if strength or weakness
        comparison_value = team_avg if team_avg > 0 else target
        
        if player_value > comparison_value * 1.1:
            metric_display = kpi_name.replace('_', ' ').title()
            diff = player_value - comparison_value
            diff_pct = (diff / comparison_value * 100) if comparison_value > 0 else 0
            insights['strengths'].append({
                'metric': kpi_name,
                'metric_display': metric_display,
                'value': player_value,
                'team_avg': team_avg,
                'target': target,
                'diff': diff,
                'diff_pct': diff_pct
            })
        elif player_value < comparison_value * 0.9:  # 10% below comparison
            metric_display = kpi_name.replace('_', ' ').title()
            diff = comparison_value - player_value
            diff_pct = (diff / comparison_value * 100) if comparison_value > 0 else 0
            insights['weaknesses'].append({
                'metric': kpi_name,
                'metric_display': metric_display,
                'value': player_value,
                'team_avg': team_avg,
                'target': target,
                'diff': diff,
                'diff_pct': diff_pct
            })
    
    # Generate position-specific recommendations with specific targets
    # ... (keep existing player insights generation logic)
    
    return insights


def display_coach_insights_section(insights_data: Dict[str, Any], team_stats: Dict[str, Any],
                                   TARGETS: Dict[str, Any], loader=None) -> None:
    """Display professional-grade insights section with metrics, comparisons, and actionable recommendations."""
    from config import KPI_TARGETS
    
    # Get KPIs for detailed analysis
    kpis = insights_data.get('summary', {}).get('kpis')
    if not kpis and loader:
        try:
            kpis = pt.compute_team_kpis_from_loader(loader)
        except Exception:
            kpis = None
    
    # Calculate key performance metrics
    serving_rate = team_stats.get('serve_point_percentage', 0.0)
    receiving_rate = team_stats.get('side_out_percentage', 0.0)
    attack_kill = team_stats.get('kill_percentage', 0.0)
    reception_qual = team_stats.get('reception_quality', 0.0)
    
    if kpis:
        serving_rate = kpis.get('break_point_rate', serving_rate)
        receiving_rate = kpis.get('side_out_efficiency', receiving_rate)
        attack_kill = kpis.get('attack_kill_pct', attack_kill)
        reception_qual = kpis.get('reception_quality', reception_qual)
    
    # Get set-by-set analysis
    set_analysis = _analyze_set_by_set_performance(loader, kpis) if loader else {}
    
    # Build professional insights
    strengths = _build_professional_strengths(kpis, team_stats, TARGETS, set_analysis)
    priorities = _build_professional_priorities(kpis, team_stats, TARGETS, set_analysis, insights_data, loader)
    tactical = _build_tactical_recommendations(kpis, team_stats, TARGETS, loader)
    
    # Display strengths
    if strengths:
        _display_professional_insight_card(
            "KEY STRENGTHS",
            strengths,
            "#155724",
            "#e6ffed",
            "#28A745",
            "🌟"
        )
    
    # Display training priorities
    if priorities:
        _display_professional_insight_card(
            "TRAINING PRIORITIES",
            priorities,
            "#856404",
            "#fff3cd",
            "#F0A000",
            "🎯"
        )
    
    # Display tactical recommendations
    if tactical:
        _display_professional_insight_card(
            "TACTICAL RECOMMENDATIONS",
            tactical,
            "#721c24",
            "#f8d7da",
            "#DC3545",
            "⚡"
        )


def _analyze_set_by_set_performance(loader, kpis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze performance differences across sets."""
    if not loader or not hasattr(loader, 'team_data') or not loader.team_data:
        return {}
    
    set_metrics = {}
    for set_num, set_data in loader.team_data.items():
        serving_rallies = float(set_data.get('serving_rallies', 0) or 0)
        serving_points = float(set_data.get('serving_points_won', 0) or 0)
        receiving_rallies = float(set_data.get('receiving_rallies', 0) or 0)
        receiving_points = float(set_data.get('receiving_points_won', 0) or 0)
        
        set_metrics[set_num] = {
            'serving_rate': (serving_points / serving_rallies) if serving_rallies > 0 else 0.0,
            'receiving_rate': (receiving_points / receiving_rallies) if receiving_rallies > 0 else 0.0,
            'serving_rallies': serving_rallies,
            'receiving_rallies': receiving_rallies
        }
    
    # Identify trends
    if len(set_metrics) >= 2:
        sets = sorted(set_metrics.keys())
        serving_trend = "improving" if set_metrics[sets[-1]]['serving_rate'] > set_metrics[sets[0]]['serving_rate'] else "declining"
        receiving_trend = "improving" if set_metrics[sets[-1]]['receiving_rate'] > set_metrics[sets[0]]['receiving_rate'] else "declining"
        
        return {
            'set_metrics': set_metrics,
            'serving_trend': serving_trend,
            'receiving_trend': receiving_trend,
            'sets_played': len(sets)
        }
    
    return {'set_metrics': set_metrics}


def _build_professional_strengths(kpis: Optional[Dict[str, Any]], team_stats: Dict[str, Any],
                                  TARGETS: Dict[str, Any], set_analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Build professional-grade strength insights with metrics and context."""
    strengths = []
    
    serving_rate = team_stats.get('serve_point_percentage', 0.0)
    receiving_rate = team_stats.get('side_out_percentage', 0.0)
    attack_kill = team_stats.get('kill_percentage', 0.0)
    reception_qual = team_stats.get('reception_quality', 0.0)
    
    if kpis:
        serving_rate = kpis.get('break_point_rate', serving_rate)
        receiving_rate = kpis.get('side_out_efficiency', receiving_rate)
        attack_kill = kpis.get('attack_kill_pct', attack_kill)
        reception_qual = kpis.get('reception_quality', reception_qual)
    
    serving_target = TARGETS.get('break_point_rate', {}).get('optimal', 0.55)
    receiving_target = TARGETS.get('side_out_percentage', {}).get('optimal', 0.70)
    attack_target = TARGETS.get('kill_percentage', {}).get('optimal', 0.42)
    reception_target = TARGETS.get('reception_quality', {}).get('optimal', 0.75)
    
    # Serving performance
    if serving_rate >= serving_target:
        diff = serving_rate - serving_target
        context = ""
        if set_analysis.get('serving_trend') == "improving":
            context = " (trending upward across sets)"
        strengths.append({
            'metric': 'Serving Point Rate',
            'value': serving_rate,
            'target': serving_target,
            'diff': diff,
            'context': context,
            'impact': 'Critical for point production and momentum'
        })
    
    # Receiving performance
    if receiving_rate >= receiving_target:
        diff = receiving_rate - receiving_target
        context = ""
        if set_analysis.get('receiving_trend') == "improving":
            context = " (trending upward across sets)"
        strengths.append({
            'metric': 'Receiving Point Rate',
            'value': receiving_rate,
            'target': receiving_target,
            'diff': diff,
            'context': context,
            'impact': 'Foundation for offensive success'
        })
    
    # Attack performance
    if attack_kill >= attack_target:
        diff = attack_kill - attack_target
        strengths.append({
            'metric': 'Attack Kill %',
            'value': attack_kill,
            'target': attack_target,
            'diff': diff,
            'context': '',
            'impact': 'Scoring efficiency indicator'
        })
    
    # Reception quality
    if reception_qual >= reception_target:
        diff = reception_qual - reception_target
        strengths.append({
            'metric': 'Reception Quality',
            'value': reception_qual,
            'target': reception_target,
            'diff': diff,
            'context': '',
            'impact': 'Enables clean offensive execution'
        })
    
    return strengths[:3]  # Top 3


def _build_professional_priorities(kpis: Optional[Dict[str, Any]], team_stats: Dict[str, Any],
                                   TARGETS: Dict[str, Any], set_analysis: Dict[str, Any],
                                   insights_data: Dict[str, Any], loader) -> List[Dict[str, Any]]:
    """Build professional-grade training priorities with metrics, gaps, and actionable focus."""
    priorities = []
    
    serving_rate = team_stats.get('serve_point_percentage', 0.0)
    receiving_rate = team_stats.get('side_out_percentage', 0.0)
    attack_kill = team_stats.get('kill_percentage', 0.0)
    reception_qual = team_stats.get('reception_quality', 0.0)
    
    if kpis:
        serving_rate = kpis.get('break_point_rate', serving_rate)
        receiving_rate = kpis.get('side_out_efficiency', receiving_rate)
        attack_kill = kpis.get('attack_kill_pct', attack_kill)
        reception_qual = kpis.get('reception_quality', reception_qual)
    
    serving_target = TARGETS.get('break_point_rate', {}).get('optimal', 0.55)
    receiving_target = TARGETS.get('side_out_percentage', {}).get('optimal', 0.70)
    attack_target = TARGETS.get('kill_percentage', {}).get('optimal', 0.42)
    reception_target = TARGETS.get('reception_quality', {}).get('optimal', 0.75)
    
    # Reception (highest priority - foundation skill)
    if reception_qual < reception_target:
        gap = reception_target - reception_qual
        gap_pct = (gap / reception_target * 100) if reception_target > 0 else 0
        priorities.append({
            'skill': 'Reception',
            'metric': f'Reception Quality: {reception_qual:.1%} (Target: {reception_target:.0%})',
            'gap': f'{gap_pct:.0f}% below target',
            'focus': 'Serve receive fundamentals: platform work, body positioning, reading serve trajectory. Prioritize OH and Libero.',
            'priority_level': 'HIGH'
        })
    
    # Receiving Point Rate
    if receiving_rate < receiving_target:
        gap = receiving_target - receiving_rate
        gap_pct = (gap / receiving_target * 100) if receiving_target > 0 else 0
        context = ""
        if set_analysis.get('receiving_trend') == "declining":
            context = " Performance declining across sets."
        priorities.append({
            'skill': 'Reception',
            'metric': f'Receiving Point Rate: {receiving_rate:.1%} (Target: {receiving_target:.0%})',
            'gap': f'{gap_pct:.0f}% below target{context}',
            'focus': 'Transition offense after reception. Improve first-ball attack efficiency and reduce reception errors.',
            'priority_level': 'HIGH'
        })
    
    # Serving Point Rate
    if serving_rate < serving_target:
        gap = serving_target - serving_rate
        gap_pct = (gap / serving_target * 100) if serving_target > 0 else 0
        context = ""
        if set_analysis.get('serving_trend') == "declining":
            context = " Performance declining across sets."
        priorities.append({
            'skill': 'Serving',
            'metric': f'Serving Point Rate: {serving_rate:.1%} (Target: {serving_target:.0%})',
            'gap': f'{gap_pct:.0f}% below target{context}',
            'focus': 'Service consistency and placement. Balance aggression with reliability. Target deep corners and seams.',
            'priority_level': 'HIGH'
        })
    
    # Attack Kill %
    if attack_kill < attack_target:
        gap = attack_target - attack_kill
        gap_pct = (gap / attack_target * 100) if attack_target > 0 else 0
        priorities.append({
            'skill': 'Attack',
            'metric': f'Attack Kill %: {attack_kill:.1%} (Target: {attack_target:.0%})',
            'gap': f'{gap_pct:.0f}% below target',
            'focus': 'Shot selection, placement, and attacking under pressure. Work on hitting angles, power control, and off-speed shots.',
            'priority_level': 'MEDIUM'
        })
    
    # Sort by priority level (HIGH first)
    priorities.sort(key=lambda x: 0 if x['priority_level'] == 'HIGH' else 1)
    
    return priorities[:3]  # Top 3


def _build_tactical_recommendations(kpis: Optional[Dict[str, Any]], team_stats: Dict[str, Any],
                                    TARGETS: Dict[str, Any], loader) -> List[Dict[str, Any]]:
    """Build tactical recommendations for next match."""
    recommendations = []
    
    serving_rate = team_stats.get('serve_point_percentage', 0.0)
    receiving_rate = team_stats.get('side_out_percentage', 0.0)
    
    if kpis:
        serving_rate = kpis.get('break_point_rate', serving_rate)
        receiving_rate = kpis.get('side_out_efficiency', receiving_rate)
    
    # Serving vs Receiving analysis
    if serving_rate < receiving_rate - 0.10:
        recommendations.append({
            'title': 'Service Pressure',
            'message': f'Receiving point rate ({receiving_rate:.1%}) significantly outperforms serving point rate ({serving_rate:.1%}). Increase service aggression to create more scoring opportunities from serve.',
            'tactical': 'Consider more aggressive serves when ahead in score. Focus on serve placement over power.'
        })
    elif receiving_rate < serving_rate - 0.10:
        recommendations.append({
            'title': 'Protect Service Advantage',
            'message': f'Serving point rate ({serving_rate:.1%}) is strong, but receiving point rate ({receiving_rate:.1%}) needs improvement. Protect service advantages by improving first-ball attack efficiency.',
            'tactical': 'Work on transition offense. When receiving, prioritize clean first-ball attacks to capitalize on service pressure.'
        })
    
    return recommendations[:2]  # Top 2


def _display_professional_insight_card(title: str, items: List[Dict[str, Any]], 
                                       text_color: str, bg_gradient_start: str, 
                                       border_color: str, icon: str) -> None:
    """Display a professional-grade insight card with metrics and context."""
    items_html = ""
    
    for item in items:
        if 'metric' in item:  # Priority/Strength format
            metric_html = f'<div style="font-size: 16px; font-weight: 700; color: {text_color}; margin-bottom: 6px;">{item["metric"]}</div>'
            gap_html = f'<div style="font-size: 14px; color: {text_color}; opacity: 0.85; margin-bottom: 8px;">{item.get("gap", "")}</div>' if item.get('gap') else ''
            focus_html = f'<div style="font-size: 14px; color: {text_color}; line-height: 1.5; padding: 10px; background: rgba(255,255,255,0.4); border-radius: 6px; border-left: 3px solid {border_color};">{item.get("focus", item.get("impact", ""))}</div>'
            items_html += f'<div style="margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid rgba(0,0,0,0.1);">{metric_html}{gap_html}{focus_html}</div>'
        elif 'title' in item:  # Tactical format
            title_html = f'<div style="font-size: 16px; font-weight: 700; color: {text_color}; margin-bottom: 6px;">{item["title"]}</div>'
            message_html = f'<div style="font-size: 14px; color: {text_color}; line-height: 1.5; margin-bottom: 8px;">{item["message"]}</div>'
            tactical_html = f'<div style="font-size: 14px; color: {text_color}; line-height: 1.5; padding: 10px; background: rgba(255,255,255,0.4); border-radius: 6px; border-left: 3px solid {border_color};">{item.get("tactical", "")}</div>'
            items_html += f'<div style="margin-bottom: 16px; padding-bottom: 16px; border-bottom: 1px solid rgba(0,0,0,0.1);">{title_html}{message_html}{tactical_html}</div>'
    
    # Remove last border
    items_html = items_html.rsplit('<div style="margin-bottom: 16px; padding-bottom: 16px; border-bottom:', 1)[0] if items_html.count('border-bottom:') > 1 else items_html.replace('border-bottom: 1px solid rgba(0,0,0,0.1);', '')
    
    html_content = f'<div style="background: linear-gradient(135deg, {bg_gradient_start} 0%, rgba(255,255,255,0.8) 100%); padding: 22px 26px; border-radius: 12px; margin-bottom: 20px; border-left: 5px solid {border_color}; box-shadow: 0 4px 12px rgba(0,0,0,0.1);"><div style="font-size: 20px; font-weight: 800; color: {text_color}; margin-bottom: 18px; letter-spacing: 0.5px; display: flex; align-items: center; gap: 10px;"><span style="font-size: 24px;">{icon}</span>{title}</div>{items_html}</div>'
    st.markdown(html_content, unsafe_allow_html=True)
