"""
Utility modules for the dashboard
"""
# Import security and file handling utilities (moved from utils.py)
import tempfile
import os
import uuid
from pathlib import Path
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Import file upload limits from config to avoid duplication
from config import MAX_FILE_SIZE, ALLOWED_EXTENSIONS
ALLOWED_MIME_TYPES = [
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-excel'
]


def validate_uploaded_file(uploaded_file) -> Tuple[bool, Optional[str]]:
    """
    Validate uploaded file for size, type, and security.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if uploaded_file is None:
        return False, "No file provided"
    
    # Check file size
    if uploaded_file.size > MAX_FILE_SIZE:
        return False, f"File too large. Maximum size is {MAX_FILE_SIZE / (1024*1024):.1f}MB"
    
    if uploaded_file.size == 0:
        return False, "File is empty"
    
    # Check file extension
    filename = uploaded_file.name.lower()
    if not any(filename.endswith(ext) for ext in ALLOWED_EXTENSIONS):
        return False, f"Invalid file type. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
    
    # Check MIME type if available
    if hasattr(uploaded_file, 'type') and uploaded_file.type:
        if uploaded_file.type not in ALLOWED_MIME_TYPES:
            logger.warning(f"Unusual MIME type: {uploaded_file.type} for file {uploaded_file.name}")
            # Don't reject based on MIME type alone, but log it
    
    return True, None


def save_uploaded_file_securely(uploaded_file) -> Optional[str]:
    """
    Save uploaded file to a secure temporary location.
    
    Args:
        uploaded_file: Streamlit UploadedFile object
        
    Returns:
        Path to saved temporary file, or None if error
    """
    # Validate file first
    is_valid, error_msg = validate_uploaded_file(uploaded_file)
    if not is_valid:
        raise ValueError(error_msg)
    
    try:
        # Use tempfile for secure temporary file handling
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, f"match_data_{uuid.uuid4().hex}.xlsx")
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        logger.info(f"Saved uploaded file to temporary location: {temp_path}")
        return temp_path
    except Exception as e:
        logger.error(f"Error saving uploaded file: {e}", exc_info=True)
        raise


def sanitize_template_path(user_input: str, base_dir: Optional[Path] = None) -> Path:
    """
    Sanitize and validate template path to prevent path traversal attacks.
    
    Args:
        user_input: User-provided path string
        base_dir: Base directory to resolve relative paths from
        
    Returns:
        Resolved and validated Path object
        
    Raises:
        ValueError: If path is invalid or outside allowed directory
    """
    if base_dir is None:
        # Default to templates directory relative to Dashboard folder
        base_dir = Path(__file__).parent.parent / "templates"
    else:
        base_dir = Path(base_dir)
    
    user_path = Path(user_input)
    
    # Resolve relative paths
    if not user_path.is_absolute():
        resolved = (base_dir / user_path).resolve()
    else:
        resolved = Path(user_path).resolve()
    
    # Ensure path is within allowed directory
    base_resolved = base_dir.resolve()
    try:
        resolved.relative_to(base_resolved)
    except ValueError:
        raise ValueError(f"Template path must be within {base_resolved}")
    
    # Check if file exists
    if not resolved.exists():
        raise FileNotFoundError(f"Template file not found: {resolved}")
    
    return resolved


def cleanup_temp_file(file_path: str) -> None:
    """
    Safely remove a temporary file.
    
    Args:
        file_path: Path to file to remove
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.warning(f"Could not clean up temporary file {file_path}: {e}")


# Import formatters for convenience
from .formatters import (
    format_percentage,
    format_float,
    get_performance_color,
    get_performance_delta_color
)

# Import helpers for convenience
from .helpers import (
    get_player_position,
    calculate_total_points_from_loader,
    extract_date_from_filename
)

__all__ = [
    'validate_uploaded_file',
    'save_uploaded_file_securely',
    'sanitize_template_path',
    'cleanup_temp_file',
    'format_percentage',
    'format_float',
    'get_performance_color',
    'get_performance_delta_color',
    'get_player_position',
    'calculate_total_points_from_loader',
    'extract_date_from_filename',
    'MAX_FILE_SIZE',
    'ALLOWED_EXTENSIONS',
    'ALLOWED_MIME_TYPES',
]
