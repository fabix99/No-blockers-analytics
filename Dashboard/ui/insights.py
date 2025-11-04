"""
Coach-focused insights generation module
"""
from typing import Dict, Any, List
import streamlit as st
from match_analyzer import MatchAnalyzer
import performance_tracker as pt


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


def display_coach_insights_section(insights_data: Dict[str, Any], team_stats: Dict[str, Any],
                                   TARGETS: Dict[str, Any], loader=None) -> None:
    """Display coach-focused insights section with summary and prioritized actions."""
    st.markdown("### 💡 Insights & Recommendations")
    
    # === SUMMARY SECTION ===
    summary = insights_data.get('summary', {})
    st.markdown("#### 📋 Summary")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if summary.get('match_context'):
            st.info(f"**Match Context:** {summary['match_context']}")
        if summary.get('performance_snapshot'):
            st.info(f"**Performance:** {summary['performance_snapshot']}")
    
    with col2:
        if summary.get('strengths'):
            strengths_text = "\n".join([f"• {s}" for s in summary['strengths']])
            st.success(f"**✅ Strengths:**\n\n{strengths_text}")
        else:
            st.info("**✅ Strengths:**\n\n• Review performance data for strengths")
    
    if summary.get('critical_areas'):
        st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
        critical_text = "\n".join([f"• {area}" for area in summary['critical_areas']])
        st.warning(f"**⚠️ Critical Areas:**\n\n{critical_text}")
    
    st.markdown("---")
    
    # === ACTIONS SECTION ===
    st.markdown("#### 🎯 Actions")
    
    # Immediate Adjustments
    immediate = insights_data.get('immediate_adjustments', [])
    if immediate:
        st.markdown("##### ⚡ Immediate Adjustments (Next Game)")
        for item in immediate:
            priority_icon = "🔴" if item['priority'] == 'high' else "🟡"
            st.markdown(f"{priority_icon} **{item['action']}**")
            st.markdown(f"   {item['details']}")
            st.markdown("")
    
    # By Skill Area (combines training priorities and skill-specific insights)
    has_skill_insights = any(insights_data['by_skill'].values())
    training_priorities = insights_data.get('training_priorities', [])
    
    if has_skill_insights or training_priorities:
        st.markdown("---")
        st.markdown("##### 📊 By Skill Area")
        
        skill_labels = {
            'serving': '🎾 Serving',
            'reception': '🤲 Reception',
            'attack': '⚡ Attack',
            'block': '🛡️ Block',
            'setter': '👆 Setter',
            'rotation': '🔄 Rotation'
        }
        
        # Add training priorities to by_skill structure
        for item in training_priorities:
            skill = item.get('skill', 'general')
            if skill not in insights_data['by_skill']:
                insights_data['by_skill'][skill] = []
            insights_data['by_skill'][skill].append({
                'type': 'training',
                'action': item['action'],
                'specific': item.get('details', '')
            })
        
        for skill, items in insights_data['by_skill'].items():
            if items:
                st.markdown(f"**{skill_labels.get(skill, skill.title())}**")
                for item in items:
                    type_label = "⚡ Immediate" if item['type'] == 'immediate' else "🏋️ Training"
                    st.markdown(f"  {type_label}: {item['action']}")
                    if item.get('specific'):
                        st.markdown(f"    → {item['specific']}")
                st.markdown("")
    
    if not immediate and not (has_skill_insights or training_priorities):
        st.info("💡 Overall performance is solid. Continue focusing on fundamentals and consistency.")

