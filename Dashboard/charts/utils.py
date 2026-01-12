"""
Chart utilities and theme configuration.

Provides consistent styling for all Plotly charts in the dashboard.
"""
import plotly.graph_objects as go
from typing import Optional, Dict, Any

# Brand colors
BRAND_PRIMARY = '#040C7B'
BRAND_SECONDARY = '#6C63FF'
BRAND_ACCENT = '#FFD700'

# Professional Plotly template with larger fonts for readability
BEAUTIFUL_TEMPLATE = {
    'layout': {
        'font': {
            'family': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            'size': 14,  # Increased from 13
            'color': BRAND_PRIMARY
        },
        'title': {
            'font': {
                'size': 20,  # Increased from 18
                'color': BRAND_PRIMARY,
                'family': 'Poppins, sans-serif'
            },
            'x': 0.5,
            'xanchor': 'center'
        },
        'paper_bgcolor': 'rgba(255,255,255,0)',
        'plot_bgcolor': '#FFFFFF',
        'hovermode': 'x unified',  # Better hover for line charts
        'hoverlabel': {
            'bgcolor': '#FFFFFF',
            'font_size': 13,
            'font_family': 'Inter, sans-serif',
            'font_color': BRAND_PRIMARY,
            'bordercolor': BRAND_PRIMARY
        },
        'xaxis': {
            'gridcolor': '#E8F4F8',
            'gridwidth': 1,
            'linecolor': '#BDC3C7',
            'linewidth': 1,
            'showgrid': True,
            'zeroline': False,
            'tickfont': {'size': 12},
            'title_font': {'size': 14, 'color': BRAND_PRIMARY}
        },
        'yaxis': {
            'gridcolor': '#E8F4F8',
            'gridwidth': 1,
            'linecolor': '#BDC3C7',
            'linewidth': 1,
            'showgrid': True,
            'zeroline': False,
            'tickfont': {'size': 12},
            'title_font': {'size': 14, 'color': BRAND_PRIMARY}
        },
        'legend': {
            'bgcolor': 'rgba(255,255,255,0.95)',
            'bordercolor': '#E8F4F8',
            'borderwidth': 1,
            'font': {'size': 13, 'color': BRAND_PRIMARY},  # Increased from 11
            'itemsizing': 'constant'
        },
        'margin': {'l': 60, 'r': 40, 't': 70, 'b': 60}
    }
}

plotly_config = {
    'displayModeBar': True,
    'displaylogo': False,
    'modeBarButtonsToRemove': ['lasso2d', 'select2d'],
    'toImageButtonOptions': {
        'format': 'png',
        'filename': 'chart',
        'height': 600,
        'width': 1200,
        'scale': 2
    }
}


def apply_beautiful_theme(
    fig: go.Figure, 
    title: Optional[str] = None, 
    height: Optional[int] = None,
    legend_position: str = 'right',
    show_grid: bool = True,
    x_title: Optional[str] = None,
    y_title: Optional[str] = None
) -> go.Figure:
    """Apply beautiful styling to any Plotly figure.
    
    Args:
        fig: Plotly figure object
        title: Optional title text
        height: Optional height in pixels
        legend_position: 'right', 'bottom', 'top', or 'none'
        show_grid: Whether to show grid lines
        x_title: Optional X-axis title
        y_title: Optional Y-axis title
        
    Returns:
        Styled Plotly figure
    """
    # Determine title text - avoid "undefined"
    if title:
        title_text = title
    elif hasattr(fig.layout, 'title') and hasattr(fig.layout.title, 'text'):
        existing_title = fig.layout.title.text
        title_text = existing_title if existing_title and existing_title != 'undefined' else ''
    else:
        title_text = ''
    
    # Legend positioning
    legend_config = {
        'bgcolor': 'rgba(255,255,255,0.95)',
        'bordercolor': '#E8F4F8',
        'borderwidth': 1,
        'font': {'size': 13, 'color': BRAND_PRIMARY},
        'itemsizing': 'constant'
    }
    
    if legend_position == 'right':
        legend_config.update({'x': 1.02, 'y': 1, 'xanchor': 'left', 'yanchor': 'top'})
    elif legend_position == 'bottom':
        legend_config.update({'x': 0.5, 'y': -0.15, 'xanchor': 'center', 'yanchor': 'top', 'orientation': 'h'})
    elif legend_position == 'top':
        legend_config.update({'x': 0.5, 'y': 1.1, 'xanchor': 'center', 'yanchor': 'bottom', 'orientation': 'h'})
    
    # Update layout with beautiful template
    layout_update = {
        'template': 'plotly_white',
        'font': BEAUTIFUL_TEMPLATE['layout']['font'],
        'paper_bgcolor': 'rgba(255,255,255,0)',
        'plot_bgcolor': '#FFFFFF',
        'hovermode': 'x unified',
        'hoverlabel': {
            'bgcolor': '#FFFFFF',
            'font_size': 13,
            'font_color': BRAND_PRIMARY,
            'bordercolor': BRAND_PRIMARY,
            'font_family': 'Inter, sans-serif'
        },
        'xaxis': {
            'gridcolor': '#E8F4F8' if show_grid else 'rgba(0,0,0,0)',
            'gridwidth': 1,
            'linecolor': '#BDC3C7',
            'linewidth': 1,
            'showgrid': show_grid,
            'zeroline': False,
            'title_font': {'size': 14, 'color': BRAND_PRIMARY},
            'tickfont': {'size': 12, 'color': BRAND_PRIMARY}
        },
        'yaxis': {
            'gridcolor': '#E8F4F8' if show_grid else 'rgba(0,0,0,0)',
            'gridwidth': 1,
            'linecolor': '#BDC3C7',
            'linewidth': 1,
            'showgrid': show_grid,
            'zeroline': False,
            'title_font': {'size': 14, 'color': BRAND_PRIMARY},
            'tickfont': {'size': 12, 'color': BRAND_PRIMARY}
        },
        'margin': {'l': 60, 'r': 40, 't': 70, 'b': 60},
        'height': height or 450
    }
    
    # Add legend unless hidden
    if legend_position != 'none':
        layout_update['legend'] = legend_config
        layout_update['showlegend'] = True
    else:
        layout_update['showlegend'] = False
    
    # Add axis titles if provided
    if x_title:
        layout_update['xaxis']['title'] = {'text': x_title, 'font': {'size': 14, 'color': BRAND_PRIMARY}}
    if y_title:
        layout_update['yaxis']['title'] = {'text': y_title, 'font': {'size': 14, 'color': BRAND_PRIMARY}}
    
    # Add title only if we have valid title text
    if title_text:
        layout_update['title'] = {
            'text': title_text,
            'font': {
                'size': 20,
                'color': BRAND_PRIMARY,
                'family': 'Poppins, sans-serif'
            },
            'x': 0.5,
            'xanchor': 'center'
        }
    
    fig.update_layout(**layout_update)
    
    return fig


def format_percentage_axis(fig: go.Figure, axis: str = 'y') -> go.Figure:
    """Format axis to display percentages properly.
    
    Args:
        fig: Plotly figure
        axis: 'x' or 'y' axis
        
    Returns:
        Updated figure
    """
    axis_config = {
        'tickformat': '.0%',
        'range': [0, 1]
    }
    
    if axis == 'y':
        fig.update_yaxes(**axis_config)
    else:
        fig.update_xaxes(**axis_config)
    
    return fig


def add_target_line(
    fig: go.Figure, 
    target_value: float, 
    label: str = "Target",
    color: str = "#FF6B6B",
    dash: str = "dash"
) -> go.Figure:
    """Add a horizontal target line to a chart.
    
    Args:
        fig: Plotly figure
        target_value: Y-value for the target line
        label: Label for the target line
        color: Line color
        dash: Line style ('solid', 'dash', 'dot', 'dashdot')
        
    Returns:
        Updated figure
    """
    fig.add_hline(
        y=target_value,
        line_dash=dash,
        line_color=color,
        line_width=2,
        annotation_text=f"{label}: {target_value:.0%}",
        annotation_position="top right",
        annotation_font_size=12,
        annotation_font_color=color
    )
    return fig

