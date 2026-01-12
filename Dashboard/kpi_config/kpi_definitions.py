"""
KPI Definitions and Help Text.

Provides detailed explanations for each KPI metric used in the dashboard.
This enables tooltips, help text, and consistent descriptions across the UI.
"""
from typing import Dict, Any

# KPI Definitions with full explanations
KPI_DEFINITIONS: Dict[str, Dict[str, Any]] = {
    # Scoring KPIs
    'side_out_efficiency': {
        'name': 'Receiving Point Rate',
        'short_name': 'Side-Out %',
        'formula': 'Points won on reception / Total reception rallies',
        'description': 'Percentage of points won when receiving serve. A key indicator of offensive efficiency on reception.',
        'why_important': 'Higher side-out efficiency means you convert more receiving opportunities into points, reducing pressure on your serve.',
        'target_optimal': 0.60,
        'target_min': 0.50,
        'target_max': 0.70,
        'benchmark_amateur': 0.45,
        'benchmark_pro': 0.65,
        'category': 'scoring'
    },
    'break_point_rate': {
        'name': 'Serving Point Rate',
        'short_name': 'Break %',
        'formula': 'Points won on serve / Total serving rallies',
        'description': 'Percentage of points won when serving. Shows ability to break opponent\'s reception.',
        'why_important': 'Breaking the opponent\'s serve puts pressure on them and can swing momentum in your favor.',
        'target_optimal': 0.45,
        'target_min': 0.35,
        'target_max': 0.55,
        'benchmark_amateur': 0.30,
        'benchmark_pro': 0.50,
        'category': 'scoring'
    },
    'attack_kill_pct': {
        'name': 'Attack Kill %',
        'short_name': 'Kill %',
        'formula': 'Kills / Total attacks',
        'description': 'Percentage of attacks that result in a direct point (kill).',
        'why_important': 'High kill percentage indicates efficient attacking that puts away points when you have the opportunity.',
        'target_optimal': 0.45,
        'target_min': 0.35,
        'target_max': 0.55,
        'benchmark_amateur': 0.30,
        'benchmark_pro': 0.50,
        'category': 'scoring'
    },
    
    # Defense & Transition KPIs
    'reception_quality': {
        'name': 'Reception Quality',
        'short_name': 'Rec %',
        'formula': 'Good receptions / Total receptions',
        'description': 'Percentage of receptions that allow for a full offensive attack (3-option play).',
        'why_important': 'Good reception is the foundation of your offense. Poor reception limits your attacking options.',
        'target_optimal': 0.75,
        'target_min': 0.60,
        'target_max': 0.85,
        'benchmark_amateur': 0.55,
        'benchmark_pro': 0.80,
        'category': 'defense'
    },
    'dig_rate': {
        'name': 'Dig Rate',
        'short_name': 'Dig %',
        'formula': 'Successful digs / Total dig attempts',
        'description': 'Percentage of opponent attacks that are successfully dug, keeping the ball in play.',
        'why_important': 'Strong digging extends rallies and gives your team more opportunities to score.',
        'target_optimal': 0.50,
        'target_min': 0.35,
        'target_max': 0.65,
        'benchmark_amateur': 0.30,
        'benchmark_pro': 0.55,
        'category': 'defense'
    },
    'block_kill_pct': {
        'name': 'Block Kill %',
        'short_name': 'Block %',
        'formula': 'Block kills / Total block attempts',
        'description': 'Percentage of blocks that result in a direct point.',
        'why_important': 'Effective blocking not only scores points but also intimidates attackers and forces errors.',
        'target_optimal': 0.15,
        'target_min': 0.08,
        'target_max': 0.25,
        'benchmark_amateur': 0.05,
        'benchmark_pro': 0.20,
        'category': 'defense'
    },
    
    # Service KPIs
    'serve_in_rate': {
        'name': 'Serve In-Rate',
        'short_name': 'In %',
        'formula': '(Aces + Good serves) / Total serves',
        'description': 'Percentage of serves that land in play (not errors).',
        'why_important': 'Serve errors give free points to the opponent. Consistency is key.',
        'target_optimal': 0.90,
        'target_min': 0.85,
        'target_max': 0.95,
        'benchmark_amateur': 0.80,
        'benchmark_pro': 0.92,
        'category': 'service'
    },
    'ace_rate': {
        'name': 'Ace Rate',
        'short_name': 'Ace %',
        'formula': 'Aces / Total serves',
        'description': 'Percentage of serves that result in a direct point (ace).',
        'why_important': 'Aces are "free" points that require no rally. Aggressive serving can disrupt opponent rhythm.',
        'target_optimal': 0.08,
        'target_min': 0.03,
        'target_max': 0.15,
        'benchmark_amateur': 0.03,
        'benchmark_pro': 0.10,
        'category': 'service'
    },
    'serve_error_rate': {
        'name': 'Service Error Rate',
        'short_name': 'Err %',
        'formula': 'Serve errors / Total serves',
        'description': 'Percentage of serves that result in an error (out, net, foot fault).',
        'why_important': 'Lower is better. High error rate gives away easy points.',
        'target_optimal': 0.10,
        'target_min': 0.05,
        'target_max': 0.15,
        'benchmark_amateur': 0.15,
        'benchmark_pro': 0.08,
        'category': 'service',
        'lower_is_better': True
    },
    
    # Efficiency KPIs
    'attack_efficiency': {
        'name': 'Attack Efficiency',
        'short_name': 'Eff %',
        'formula': '(Kills - Errors - Blocked) / Total attacks',
        'description': 'Net efficiency of attacks, accounting for errors and blocks.',
        'why_important': 'A comprehensive measure of attacking effectiveness that penalizes mistakes.',
        'target_optimal': 0.25,
        'target_min': 0.15,
        'target_max': 0.40,
        'benchmark_amateur': 0.10,
        'benchmark_pro': 0.30,
        'category': 'efficiency'
    },
    'set_conversion': {
        'name': 'Set Conversion',
        'short_name': 'Set %',
        'formula': 'Kills from sets / Total sets',
        'description': 'Percentage of sets that result in a kill.',
        'why_important': 'Measures how well the setter-hitter connection converts opportunities.',
        'target_optimal': 0.40,
        'target_min': 0.30,
        'target_max': 0.50,
        'benchmark_amateur': 0.25,
        'benchmark_pro': 0.45,
        'category': 'efficiency'
    }
}


def get_kpi_help_text(kpi_key: str) -> str:
    """Get formatted help text for a KPI.
    
    Args:
        kpi_key: The KPI identifier
        
    Returns:
        Formatted help text string
    """
    kpi = KPI_DEFINITIONS.get(kpi_key)
    if not kpi:
        return ""
    
    return f"""
**{kpi['name']}**

📊 **Formula:** {kpi['formula']}

📝 **What it measures:** {kpi['description']}

💡 **Why it matters:** {kpi['why_important']}

🎯 **Targets:**
- Minimum: {kpi['target_min']:.0%}
- Optimal: {kpi['target_optimal']:.0%}
- Excellent: {kpi['target_max']:.0%}
""".strip()


def get_kpi_tooltip(kpi_key: str) -> str:
    """Get a short tooltip for a KPI.
    
    Args:
        kpi_key: The KPI identifier
        
    Returns:
        Short tooltip string
    """
    kpi = KPI_DEFINITIONS.get(kpi_key)
    if not kpi:
        return ""
    
    return f"{kpi['formula']}\n\n{kpi['description']}\n\nTarget: {kpi['target_optimal']:.0%}"


def get_kpi_category(kpi_key: str) -> str:
    """Get the category for a KPI.
    
    Args:
        kpi_key: The KPI identifier
        
    Returns:
        Category string ('scoring', 'defense', 'service', 'efficiency')
    """
    kpi = KPI_DEFINITIONS.get(kpi_key)
    return kpi.get('category', 'other') if kpi else 'other'

