"""
Export utilities for generating downloadable reports.

Provides functionality to export match analysis reports in various formats.
"""
import io
from typing import Dict, Any, Optional
from datetime import datetime
import streamlit as st
import pandas as pd


def generate_text_report(
    analyzer,
    loader,
    kpis: Optional[Dict[str, Any]] = None,
    include_insights: bool = True
) -> str:
    """Generate a text-based match report.
    
    Args:
        analyzer: MatchAnalyzer instance
        loader: EventTrackerLoader instance
        kpis: Optional pre-computed KPIs
        include_insights: Whether to include coaching insights
        
    Returns:
        Formatted text report string
    """
    lines = []
    
    # Header
    lines.append("=" * 60)
    lines.append("NO BLOCKERS - MATCH ANALYSIS REPORT")
    lines.append("=" * 60)
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append("")
    
    # Match Info
    if loader:
        match_info = getattr(loader, 'match_info', {})
        if match_info:
            lines.append("MATCH INFORMATION")
            lines.append("-" * 40)
            lines.append(f"Opponent: {match_info.get('opponent', 'Unknown')}")
            lines.append(f"Date: {match_info.get('date', 'Unknown')}")
            lines.append(f"Competition: {match_info.get('competition', 'Unknown')}")
            lines.append("")
    
    # Match Result
    if loader and hasattr(loader, 'team_data_by_rotation'):
        from ui.components import _get_match_result_summary
        summary = _get_match_result_summary(loader)
        if summary:
            lines.append("MATCH RESULT")
            lines.append("-" * 40)
            lines.append(f"Result: {summary.get('label', 'Unknown')}")
            lines.append(f"Outcome: {summary.get('outcome', 'Unknown')}")
            lines.append("")
    
    # Team KPIs
    if kpis:
        lines.append("TEAM PERFORMANCE METRICS")
        lines.append("-" * 40)
        
        # Scoring
        lines.append("\n[SCORING]")
        if 'side_out_efficiency' in kpis:
            lines.append(f"  Receiving Point Rate: {kpis['side_out_efficiency']:.1%}")
        if 'break_point_rate' in kpis:
            lines.append(f"  Serving Point Rate: {kpis['break_point_rate']:.1%}")
        if 'attack_kill_pct' in kpis:
            lines.append(f"  Attack Kill %: {kpis['attack_kill_pct']:.1%}")
        
        # Defense
        lines.append("\n[DEFENSE & TRANSITION]")
        if 'reception_quality' in kpis:
            lines.append(f"  Reception Quality: {kpis['reception_quality']:.1%}")
        if 'dig_rate' in kpis:
            lines.append(f"  Dig Rate: {kpis['dig_rate']:.1%}")
        if 'block_kill_pct' in kpis:
            lines.append(f"  Block Kill %: {kpis['block_kill_pct']:.1%}")
        
        # Service
        lines.append("\n[SERVICE]")
        if 'serve_in_rate' in kpis:
            lines.append(f"  Serve In-Rate: {kpis['serve_in_rate']:.1%}")
        if 'totals' in kpis:
            totals = kpis['totals']
            ace_rate = totals.get('service_aces', 0) / max(totals.get('serve_attempts', 1), 1)
            lines.append(f"  Ace Rate: {ace_rate:.1%}")
        lines.append("")
    
    # Player Statistics
    if analyzer:
        player_stats = analyzer.calculate_player_metrics()
        if player_stats:
            lines.append("PLAYER STATISTICS")
            lines.append("-" * 40)
            lines.append(f"{'Player':<20} {'Kills':<8} {'Aces':<8} {'Blocks':<8} {'Total Pts':<10}")
            lines.append("-" * 54)
            
            for player_name, data in sorted(player_stats.items()):
                kills = data.get('attack_kills', 0)
                aces = data.get('service_aces', 0)
                blocks = data.get('block_kills', 0)
                total = kills + aces + blocks
                lines.append(f"{player_name:<20} {kills:<8} {aces:<8} {blocks:<8} {total:<10}")
            lines.append("")
    
    # Insights
    if include_insights:
        lines.append("COACHING INSIGHTS")
        lines.append("-" * 40)
        lines.append("• Review match video focusing on service patterns")
        lines.append("• Analyze rotation performance for optimization")
        lines.append("• Identify player matchups for next game preparation")
        lines.append("")
    
    # Footer
    lines.append("=" * 60)
    lines.append("NO FEAR. NO LIMITS. NO BLOCKERS.")
    lines.append("=" * 60)
    
    return "\n".join(lines)


def generate_csv_player_stats(analyzer) -> str:
    """Generate CSV of player statistics.
    
    Args:
        analyzer: MatchAnalyzer instance
        
    Returns:
        CSV string
    """
    player_stats = analyzer.calculate_player_metrics()
    if not player_stats:
        return ""
    
    rows = []
    for player_name, data in player_stats.items():
        rows.append({
            'Player': player_name,
            'Total Actions': data.get('total_actions', 0),
            'Attack Attempts': data.get('attack_attempts', 0),
            'Attack Kills': data.get('attack_kills', 0),
            'Attack Errors': data.get('attack_errors', 0),
            'Attack Kill %': data.get('attack_kill_pct', 0),
            'Serve Attempts': data.get('service_attempts', 0),
            'Service Aces': data.get('service_aces', 0),
            'Service Errors': data.get('service_errors', 0),
            'Block Attempts': data.get('block_attempts', 0),
            'Block Kills': data.get('block_kills', 0),
            'Reception Attempts': data.get('reception_attempts', 0),
            'Reception Good': data.get('reception_good', 0),
            'Reception %': data.get('reception_percentage', 0),
            'Dig Attempts': data.get('dig_attempts', 0),
            'Dig Good': data.get('dig_good', 0),
            'Set Attempts': data.get('total_sets', 0),
        })
    
    df = pd.DataFrame(rows)
    return df.to_csv(index=False)


def display_export_buttons(analyzer, loader, kpis: Optional[Dict[str, Any]] = None) -> None:
    """Display export buttons in the UI.
    
    Args:
        analyzer: MatchAnalyzer instance
        loader: EventTrackerLoader instance
        kpis: Optional pre-computed KPIs
    """
    st.markdown("### 📤 Export Report")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Text Report Download
        text_report = generate_text_report(analyzer, loader, kpis)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        
        st.download_button(
            label="📄 Download Text Report",
            data=text_report,
            file_name=f"match_report_{timestamp}.txt",
            mime="text/plain",
            help="Download a text-based match analysis report"
        )
    
    with col2:
        # CSV Player Stats Download
        if analyzer:
            csv_data = generate_csv_player_stats(analyzer)
            if csv_data:
                st.download_button(
                    label="📊 Download Player Stats (CSV)",
                    data=csv_data,
                    file_name=f"player_stats_{timestamp}.csv",
                    mime="text/csv",
                    help="Download player statistics in CSV format for further analysis"
                )

