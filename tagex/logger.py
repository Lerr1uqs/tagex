"""
Logger module for the tagex project.

This module provides a configurable logger that:
1. Filters logs by level to stdout based on the specified minimum level
2. Saves all logs (regardless of level) to local log files
3. Includes the log level in the output format
4. Uses RichHandler for colorful, formatted output to terminal
"""

import sys
from typing import Any
from loguru import logger as loguru_logger
from rich.logging import RichHandler
from pathlib import Path


# Global variable to hold the configured logger
logger = None


def setup_logger(level: str = "INFO", log_file_path: str | Path | None = None) -> Any:
    """
    Setup and configure the logger.

    Args:
        level (str): Minimum log level to display in terminal (default: 'INFO')
        log_file_path (str): Path for log file (default: logs/app_{date}.log)

    Returns:
        Logger: Configured logger instance
    """
    global logger

    # Remove all existing handlers
    loguru_logger.remove()

    # Convert string level to loguru level number
    try:
        level_number = loguru_logger.level(level).no
    except ValueError:
        raise ValueError(f"Invalid log level: {level}")
    
    # Level filter for stdout
    def level_filter(record: dict) -> bool:
        return record["level"].no >= level_number  # type: ignore[no-any-return]
    
    # Add Rich handler for stdout with level filter
    # show_time 和 show_path 都设置为 False 可以避免(loguru和rich的)重复输出
    loguru_logger.configure(
        handlers=[{  # type: ignore[misc, list-item]
            "sink": RichHandler(
                markup=True,
                show_time=False,
                show_path=False,
                omit_repeated_times=False
            ),
            "format": "{time:YYYY-MM-DD HH:mm:ss} | {file}:{line} | {message}",
            "filter": level_filter,
            "level": "TRACE"  # Set to TRACE so filter handles the actual level control
        }]
    )
    
    # Create logs directory if it doesn't exist
    logs_dir = Path("logs")
    logs_dir.mkdir(exist_ok=True)
    
    # Set default log file path if not provided
    if log_file_path is None:
        log_file_path = logs_dir / "tagex_{time:YYYY-MM-DD}.log"
    
    # Add file handler - no filter, captures all levels
    loguru_logger.add(
        log_file_path,
        rotation="00:00",  # Rotate at midnight
        retention="7 days",  # Keep logs for 7 days
        level="TRACE",  # Log everything to file
        colorize=False,  # No need for colors in file
        compression=None,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level:<8} | {file}:{line} | {message}",
        enqueue=True  # Thread-safe logging
    )

    logger = loguru_logger  # Assign the configured logger to the global variable
    return logger


def init_default_logger() -> None:
    """
    Initialize the logger with default settings.
    This is useful when importing the module without explicitly configuring.
    """
    global logger
    if logger is None:
        setup_logger("INFO")


# Initialize logger with default settings on import
init_default_logger()