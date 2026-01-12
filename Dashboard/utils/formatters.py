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


def format_percentage_with_sample_size(value: float, numerator: int, denominator: int, decimals: int = 1) -> str:
    """Format a percentage with sample size indicator.
    
    Args:
        value: Percentage value (0.35)
        numerator: Count of successes (21)
        denominator: Total count (50)
        decimals: Number of decimal places for percentage
        
    Returns:
        Formatted string with HTML: "35.0% <small>(21/50)</small>" or "N/A" if invalid
    """
    if pd.isna(value) or value is None or denominator == 0:
        return "N/A"
    # Use HTML to make parenthetical text smaller
    return f"{value * 100:.{decimals}f}% <small style='font-size: 0.7em; opacity: 0.8;'>({numerator}/{denominator})</small>"


def get_sample_size_warning(denominator: int) -> Optional[str]:
    """Get warning message for small sample sizes.
    
    Args:
        denominator: Total count/sample size
        
    Returns:
        Warning message string or None if sample size is sufficient
    """
    if denominator < 5:
        return "⚠️ Very low sample size - results may be unreliable"
    elif denominator < 10:
        return "⚠️ Low sample size - results should be interpreted with caution"
    return None


def should_hide_metric(denominator: int, min_threshold: int = 5) -> bool:
    """Determine if a metric should be hidden due to insufficient sample size.
    
    Args:
        denominator: Total count/sample size
        min_threshold: Minimum sample size threshold (default: 5)
        
    Returns:
        True if metric should be hidden, False otherwise
    """
    return denominator < min_threshold


def calculate_confidence_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """Calculate confidence interval for a proportion using normal approximation.
    
    Args:
        successes: Number of successes
        total: Total number of trials
        confidence: Confidence level (default: 0.95 for 95% CI)
        
    Returns:
        Tuple of (lower_bound, upper_bound) as proportions (0-1)
    """
    if total == 0:
        return (0.0, 0.0)
    
    try:
        from scipy import stats
        import numpy as np
        
        p = successes / total
        z = stats.norm.ppf((1 + confidence) / 2)
        se = np.sqrt(p * (1 - p) / total)
        
        lower = max(0.0, p - z * se)
        upper = min(1.0, p + z * se)
        
        return (lower, upper)
    except ImportError:
        # Fallback to simple approximation if scipy not available
        import math
        p = successes / total
        # Use 1.96 for 95% CI (z-score for 0.95 confidence)
        z = 1.96 if confidence == 0.95 else 1.645  # 1.645 for 90% CI
        se = math.sqrt(p * (1 - p) / total)
        
        lower = max(0.0, p - z * se)
        upper = min(1.0, p + z * se)
        
        return (lower, upper)


def get_data_quality_badge(sample_size: int) -> str:
    """Get a data quality badge based on sample size.
    
    Args:
        sample_size: Number of data points
        
    Returns:
        HTML badge string
    """
    if sample_size >= 50:
        color = "#28a745"  # Green
        label = "HIGH"
        icon = "✓"
    elif sample_size >= 20:
        color = "#ffc107"  # Yellow
        label = "MEDIUM"
        icon = "○"
    elif sample_size >= 10:
        color = "#fd7e14"  # Orange
        label = "LOW"
        icon = "△"
    else:
        color = "#dc3545"  # Red
        label = "VERY LOW"
        icon = "⚠"
    
    return f"""
    <span style="
        background: {color}; 
        color: white; 
        padding: 2px 8px; 
        border-radius: 4px; 
        font-size: 11px; 
        font-weight: 600;
        margin-left: 8px;
    ">{icon} n={sample_size}</span>
    """


def get_data_quality_indicator(sample_size: int) -> Tuple[str, str, str]:
    """Get data quality indicator components.
    
    Args:
        sample_size: Number of data points
        
    Returns:
        Tuple of (emoji, label, description)
    """
    if sample_size >= 50:
        return ("🟢", "High Confidence", "Large sample size provides reliable insights")
    elif sample_size >= 20:
        return ("🟡", "Medium Confidence", "Moderate sample size - results are reasonably reliable")
    elif sample_size >= 10:
        return ("🟠", "Low Confidence", "Small sample size - interpret with caution")
    else:
        return ("🔴", "Very Low Confidence", "Very small sample - results may not be representative")


def format_stat_with_quality(value: float, sample_size: int, is_percentage: bool = True) -> str:
    """Format a statistic with quality indicator.
    
    Args:
        value: The statistic value
        sample_size: Number of data points
        is_percentage: Whether to format as percentage
        
    Returns:
        Formatted string with quality badge
    """
    if pd.isna(value) or value is None:
        return "N/A"
    
    if is_percentage:
        formatted = f"{value * 100:.1f}%"
    else:
        formatted = f"{value:.2f}"
    
    quality_emoji, _, _ = get_data_quality_indicator(sample_size)
    
    return f"{formatted} {quality_emoji} (n={sample_size})"

