"""
Export utilities for PDF and Excel export functionality
"""
from typing import Dict, Any, Optional
import pandas as pd
import io
from pathlib import Path
import base64


def export_to_excel(analyzer, kpis: Optional[Dict[str, Any]], loader=None) -> bytes:
    """Export match data to Excel format.
    
    Returns:
        Excel file as bytes
    """
    try:
        output = io.BytesIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet 1: Summary KPIs
            if kpis:
                kpi_data = []
                for key, value in kpis.items():
                    if key != 'totals' and isinstance(value, (int, float)):
                        kpi_data.append({
                            'KPI': key.replace('_', ' ').title(),
                            'Value': f"{value:.1%}" if value <= 1 else f"{value:.2f}"
                        })
                
                if kpi_data:
                    kpi_df = pd.DataFrame(kpi_data)
                    kpi_df.to_excel(writer, sheet_name='KPIs', index=False)
            
            # Sheet 2: Player Statistics
            if loader and hasattr(loader, 'player_data_by_set'):
                player_data = []
                for set_num in loader.player_data_by_set.keys():
                    for player in loader.player_data_by_set[set_num].keys():
                        stats = loader.player_data_by_set[set_num][player].get('stats', {})
                        player_data.append({
                            'Set': set_num,
                            'Player': player,
                            'Attack_Kills': stats.get('Attack_Kills', 0),
                            'Attack_Total': stats.get('Attack_Total', 0),
                            'Service_Aces': stats.get('Service_Aces', 0),
                            'Service_Total': stats.get('Service_Total', 0),
                            'Block_Kills': stats.get('Block_Kills', 0),
                            'Block_Total': stats.get('Block_Total', 0),
                            'Reception_Good': stats.get('Reception_Good', 0),
                            'Reception_Total': stats.get('Reception_Total', 0)
                        })
                
                if player_data:
                    player_df = pd.DataFrame(player_data)
                    player_df.to_excel(writer, sheet_name='Player Stats', index=False)
            
            # Sheet 3: Team Events
            if loader and hasattr(loader, 'team_events'):
                loader.team_events.to_excel(writer, sheet_name='Team Events', index=False)
            
            # Sheet 4: Individual Events
            if loader and hasattr(loader, 'individual_events'):
                loader.individual_events.to_excel(writer, sheet_name='Individual Events', index=False)
        
        output.seek(0)
        return output.read()
    except Exception as e:
        # Return empty bytes if export fails
        return b''


# export_to_pdf, export_to_csv, and export_to_json functions removed per user request

