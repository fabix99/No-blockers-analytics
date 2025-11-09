"""
Statistical helper functions for calculating confidence intervals, 
significance tests, and statistical indicators
"""
from typing import Tuple, Optional
import math


def calculate_confidence_interval(successes: int, total: int, confidence: float = 0.95) -> Tuple[float, float]:
    """
    Calculate confidence interval for a proportion using normal approximation.
    
    Args:
        successes: Number of successful events
        total: Total number of events
        confidence: Confidence level (default 0.95 for 95% CI)
        
    Returns:
        Tuple of (lower_bound, upper_bound) as proportions
    """
    if total == 0:
        return (0.0, 0.0)
    
    p = successes / total
    z = 1.96 if confidence == 0.95 else 2.58 if confidence == 0.99 else 1.645
    
    # Normal approximation: CI = p ± z * sqrt(p*(1-p)/n)
    margin_of_error = z * math.sqrt(p * (1 - p) / total)
    
    lower = max(0.0, p - margin_of_error)
    upper = min(1.0, p + margin_of_error)
    
    return (lower, upper)


def calculate_margin_of_error(successes: int, total: int, confidence: float = 0.95) -> float:
    """
    Calculate margin of error for a proportion.
    
    Args:
        successes: Number of successful events
        total: Total number of events
        confidence: Confidence level
        
    Returns:
        Margin of error as proportion
    """
    if total == 0:
        return 0.0
    
    p = successes / total
    z = 1.96 if confidence == 0.95 else 2.58 if confidence == 0.99 else 1.645
    
    margin_of_error = z * math.sqrt(p * (1 - p) / total)
    return margin_of_error


def is_sample_size_sufficient(total: int, min_sample: int = 30) -> bool:
    """
    Check if sample size is sufficient for statistical significance.
    
    Args:
        total: Total number of observations
        min_sample: Minimum sample size (default 30)
        
    Returns:
        True if sample size is sufficient
    """
    return total >= min_sample


def get_reliability_indicator(total: int) -> str:
    """
    Get reliability indicator based on sample size.
    
    Args:
        total: Total number of observations
        
    Returns:
        'High', 'Medium', or 'Low'
    """
    if total >= 50:
        return 'High'
    elif total >= 20:
        return 'Medium'
    else:
        return 'Low'


def calculate_percentage_with_ci(successes: int, total: int, 
                                  confidence: float = 0.95) -> Tuple[float, float, float]:
    """
    Calculate percentage with confidence interval.
    
    Args:
        successes: Number of successful events
        total: Total number of events
        confidence: Confidence level
        
    Returns:
        Tuple of (percentage, lower_bound, upper_bound)
    """
    if total == 0:
        return (0.0, 0.0, 0.0)
    
    p = successes / total
    lower, upper = calculate_confidence_interval(successes, total, confidence)
    
    return (p, lower, upper)


def format_ci_display(percentage: float, lower: float, upper: float, 
                      format_as_percent: bool = True) -> str:
    """
    Format confidence interval for display.
    
    Args:
        percentage: Point estimate
        lower: Lower bound
        upper: Upper bound
        format_as_percent: Whether to format as percentage
        
    Returns:
        Formatted string like "42.0% (95% CI: 38.5% - 45.5%)"
    """
    if format_as_percent:
        p_str = f"{percentage:.1%}"
        lower_str = f"{lower:.1%}"
        upper_str = f"{upper:.1%}"
    else:
        p_str = f"{percentage:.2f}"
        lower_str = f"{lower:.2f}"
        upper_str = f"{upper:.2f}"
    
    return f"{p_str} (95% CI: {lower_str} - {upper_str})"


def get_statistical_significance_indicator(successes1: int, total1: int,
                                           successes2: int, total2: int,
                                           alpha: float = 0.05) -> Optional[str]:
    """
    Determine if difference between two proportions is statistically significant.
    Uses two-proportion z-test.
    
    Args:
        successes1: Successes in group 1
        total1: Total in group 1
        successes2: Successes in group 2
        total2: Total in group 2
        alpha: Significance level (default 0.05)
        
    Returns:
        '★' if significant, None otherwise
    """
    if total1 == 0 or total2 == 0:
        return None
    
    p1 = successes1 / total1
    p2 = successes2 / total2
    
    # Pooled proportion
    p_pooled = (successes1 + successes2) / (total1 + total2)
    
    # Standard error
    se = math.sqrt(p_pooled * (1 - p_pooled) * (1/total1 + 1/total2))
    
    if se == 0:
        return None
    
    # Z-score
    z = (p1 - p2) / se
    
    # Critical z-value (two-tailed)
    z_critical = 1.96 if alpha == 0.05 else 2.58 if alpha == 0.01 else 1.645
    
    if abs(z) > z_critical:
        return '★'
    
    return None


