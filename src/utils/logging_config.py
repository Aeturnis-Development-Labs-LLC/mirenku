"""Logging configuration for Anime Tracker"""

import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
import sys


def setup_logging(log_dir: Path = None, log_level: str = "INFO", config=None):
    """Set up application logging
    
    Args:
        log_dir: Directory for log files (None for default)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        config: Config instance to get data directory from
    """
    # Create log directory if needed
    if log_dir is None:
        if config:
            # Use config's data directory
            log_dir = config.get_data_directory() / "logs"
        elif getattr(sys, 'frozen', False):
            # Running as executable
            log_dir = Path(sys.executable).parent / "logs"
        else:
            # Running as script - use same pattern as config
            import os
            if os.name == 'nt':  # Windows
                app_data = os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')
                log_dir = Path(app_data) / "AnimeTracker" / "logs"
            else:  # Unix-like
                log_dir = Path.home() / ".config" / "animetracker" / "logs"
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(levelname)s - %(message)s'
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper()))
    
    # Remove existing handlers
    root_logger.handlers.clear()
    
    # File handler - rotating log
    log_file = log_dir / f"anime_tracker_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,  # 5MB
        backupCount=3,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    root_logger.addHandler(file_handler)
    
    # Console handler - only for errors in production
    console_handler = logging.StreamHandler(sys.stdout)
    if getattr(sys, 'frozen', False):
        # In executable, only show errors
        console_handler.setLevel(logging.ERROR)
    else:
        # In development, show info and above
        console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    root_logger.addHandler(console_handler)
    
    # Log startup
    logging.info("=" * 50)
    logging.info("Anime Tracker started")
    logging.info(f"Log level: {log_level}")
    logging.info(f"Log directory: {log_dir}")
    logging.info("=" * 50)
    
    return log_dir


def get_log_files(log_dir: Path = None) -> list:
    """Get list of log files
    
    Args:
        log_dir: Log directory (None for default)
        
    Returns:
        list: List of log file paths
    """
    if log_dir is None:
        import os
        if getattr(sys, 'frozen', False):
            log_dir = Path(sys.executable).parent / "logs"
        elif os.name == 'nt':  # Windows
            app_data = os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local')
            log_dir = Path(app_data) / "AnimeTracker" / "logs"
        else:  # Unix-like
            log_dir = Path.home() / ".config" / "animetracker" / "logs"
    
    if not log_dir.exists():
        return []
    
    return sorted(log_dir.glob("anime_tracker_*.log"), reverse=True)


def clean_old_logs(log_dir: Path = None, days_to_keep: int = 7):
    """Clean old log files
    
    Args:
        log_dir: Log directory (None for default)
        days_to_keep: Number of days to keep logs
    """
    from datetime import timedelta
    
    log_files = get_log_files(log_dir)
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    for log_file in log_files:
        # Parse date from filename
        try:
            date_str = log_file.stem.split('_')[-1]
            file_date = datetime.strptime(date_str, '%Y%m%d')
            
            if file_date < cutoff_date:
                log_file.unlink()
                logging.info(f"Deleted old log file: {log_file.name}")
        except:
            # Skip files with unexpected names
            continue