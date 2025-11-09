"""
Chart utilities and theme configuration
"""
import plotly.graph_objects as go

# Professional Plotly template
BEAUTIFUL_TEMPLATE = {
    'layout': {
        'font': {
            'family': 'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
            'size': 13,
            'color': '#050d76'
        },
        'title': {
            'font': {
                'size': 18,
                'color': '#050d76',
                'family': 'Poppins, sans-serif'
            },
            'x': 0.5,
            'xanchor': 'center'
        },
        'paper_bgcolor': 'rgba(255,255,255,0)',
        'plot_bgcolor': '#FFFFFF',
        'hovermode': 'closest',
        'hoverlabel': {
            'bgcolor': '#F5F5F5',
            'font_size': 12,
            'font_family': 'Inter, sans-serif',
            'font_color': '#050d76',
            'bordercolor': '#050d76'
        },
        'xaxis': {
            'gridcolor': '#E8F4F8',
            'gridwidth': 1,
            'linecolor': '#BDC3C7',
            'linewidth': 1,
            'showgrid': True,
            'zeroline': False
        },
        'yaxis': {
            'gridcolor': '#E8F4F8',
            'gridwidth': 1,
            'linecolor': '#BDC3C7',
            'linewidth': 1,
            'showgrid': True,
            'zeroline': False
        },
        'legend': {
            'bgcolor': 'rgba(255,255,255,0.9)',
            'bordercolor': '#E8F4F8',
            'borderwidth': 1,
            'font': {'size': 11, 'color': '#050d76'}
        },
        'margin': {'l': 60, 'r': 40, 't': 60, 'b': 60}
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


def apply_beautiful_theme(fig, title=None, height=None):
    """Apply beautiful styling to any Plotly figure.
    
    Args:
        fig: Plotly figure object
        title: Optional title text
        height: Optional height in pixels
        
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
    
    # Update layout with beautiful template
    layout_update = {
        'template': 'plotly_white',
        'font': BEAUTIFUL_TEMPLATE['layout']['font'],
        'paper_bgcolor': 'rgba(255,255,255,0)',
        'plot_bgcolor': '#FFFFFF',
        'hovermode': 'closest',
        'hoverlabel': {
            'bgcolor': '#F5F5F5',
            'font_size': 12,
            'font_color': '#050d76',
            'bordercolor': '#050d76',
            'font_family': 'Inter, sans-serif'
        },
        'xaxis': {
            'gridcolor': '#E8F4F8',
            'gridwidth': 1,
            'linecolor': '#BDC3C7',
            'linewidth': 1,
            'showgrid': True,
            'zeroline': False,
            'title_font': {'size': 12, 'color': '#050d76'},
            'tickfont': {'color': '#050d76'}
        },
        'yaxis': {
            'gridcolor': '#E8F4F8',
            'gridwidth': 1,
            'linecolor': '#BDC3C7',
            'linewidth': 1,
            'showgrid': True,
            'zeroline': False,
            'title_font': {'size': 12, 'color': '#050d76'},
            'tickfont': {'color': '#050d76'}
        },
        'legend': {
            'bgcolor': 'rgba(255,255,255,0.9)',
            'bordercolor': '#E8F4F8',
            'borderwidth': 1,
            'font': {'size': 11, 'color': '#050d76'},
            'x': 1.02,
            'y': 1,
            'xanchor': 'left',
            'yanchor': 'top'
        },
        'margin': {'l': 60, 'r': 40, 't': 60, 'b': 60},
        'height': height or 450
    }
    
    # Add title only if we have valid title text
    if title_text:
        layout_update['title'] = {
            'text': title_text,
            'font': {
                'size': 18,
                'color': '#050d76',
                'family': 'Poppins, sans-serif'
            },
            'x': 0.5,
            'xanchor': 'center'
        }
    
    fig.update_layout(**layout_update)
    
    return fig

