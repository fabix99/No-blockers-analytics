"""
Data formatting and helper utilities for the dashboard
"""
from typing import Optional, Dict, Any, Tuple
import streamlit as st
import pandas as pd


def get_performance_color(value: float, target_min: float, target_max: float, 
                         target_optimal: Optional[float] = None) -> str:
    """Return color emoji based on performance level.
    
    Args:
        value: The actual performance value
        target_min: Minimum acceptable value
        target_max: Maximum expected value
        target_optimal: Optimal target value (uses midpoint if None)
        
    Returns:
        Color emoji string: "🟢" for meets/exceeds target, "🔴" for below target
    """
    # If optimal target provided, use it; otherwise use midpoint of min/max
    if target_optimal is None:
        target_optimal = (target_min + target_max) / 2
    
    # Only return green or red - no yellow
    if value >= target_optimal:
        return "🟢"  # Meets or exceeds target
    else:
        return "🔴"  # Below target


def get_performance_delta_color(value: float, target_min: float, target_max: float,
                                target_optimal: Optional[float] = None) -> str:
    """Get Streamlit delta color for metric display.
    
    Args:
        value: The actual performance value
        target_min: Minimum acceptable value
        target_max: Maximum expected value
        target_optimal: Optimal target value
        
    Returns:
        Streamlit color string: "normal", "inverse", or "off"
    """
    if target_optimal is None:
        target_optimal = (target_min + target_max) / 2
    
    if value >= target_max:
        return "inverse"  # Green - exceeds expectations
    elif value >= target_optimal:
        return "normal"  # Yellow - meets target
    elif value >= target_min:
        return "normal"  # Yellow - acceptable
    else:
        return "normal"  # Red - below target


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format a float as a percentage string.
    
    Args:
        value: Value to format (0.35 -> "35.0%")
        decimals: Number of decimal places
        
    Returns:
        Formatted percentage string
    """
    if pd.isna(value) or value is None:
        return "N/A"
    return f"{value * 100:.{decimals}f}%"


def format_float(value: float, decimals: int = 2) -> str:
    """Format a float with specified decimals.
    
    Args:
        value: Value to format
        decimals: Number of decimal places
        
    Returns:
        Formatted string or "N/A" if invalid
    """
    if pd.isna(value) or value is None:
        return "N/A"
    return f"{value:.{decimals}f}"

