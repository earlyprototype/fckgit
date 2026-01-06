"""
Logging configuration for fckgit MCP server.

Provides structured logging without interfering with MCP stdio protocol.
"""

import logging
import sys
from typing import Optional


def setup_logging(level: str = "INFO", enable_debug: bool = False) -> None:
    """
    Configure logging for MCP server.
    
    IMPORTANT: Logs go to stderr to avoid interfering with MCP stdio protocol
    which uses stdout for communication.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_debug: Enable debug logging for development
    """
    # Use stderr to not interfere with stdio protocol
    log_level = logging.DEBUG if enable_debug else getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter with timestamp and context
    formatter = logging.Formatter(
        fmt='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add stderr handler
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(log_level)
    stderr_handler.setFormatter(formatter)
    root_logger.addHandler(stderr_handler)
    
    # Configure specific loggers
    configure_module_loggers(log_level)


def configure_module_loggers(level: int) -> None:
    """
    Configure loggers for specific modules.
    
    Args:
        level: Logging level as integer
    """
    # fckgit modules
    logging.getLogger('mcp_server').setLevel(level)
    logging.getLogger('mcp_server.workspace').setLevel(level)
    logging.getLogger('mcp_server.git_utils').setLevel(level)
    logging.getLogger('mcp_server.platform_utils').setLevel(level)
    
    # Reduce noise from external libraries
    logging.getLogger('google').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific module.
    
    Args:
        name: Module name (typically __name__)
        
    Returns:
        Configured logger
    """
    return logging.getLogger(name)


class StructuredLogger:
    """
    Structured logger with context support.
    
    Provides convenience methods for logging with additional context.
    """
    
    def __init__(self, name: str):
        """
        Initialize structured logger.
        
        Args:
            name: Logger name (typically __name__)
        """
        self.logger = logging.getLogger(name)
    
    def debug(self, msg: str, **kwargs) -> None:
        """Log debug message with context."""
        self._log(logging.DEBUG, msg, kwargs)
    
    def info(self, msg: str, **kwargs) -> None:
        """Log info message with context."""
        self._log(logging.INFO, msg, kwargs)
    
    def warning(self, msg: str, **kwargs) -> None:
        """Log warning message with context."""
        self._log(logging.WARNING, msg, kwargs)
    
    def error(self, msg: str, **kwargs) -> None:
        """Log error message with context."""
        self._log(logging.ERROR, msg, kwargs)
    
    def critical(self, msg: str, **kwargs) -> None:
        """Log critical message with context."""
        self._log(logging.CRITICAL, msg, kwargs)
    
    def _log(self, level: int, msg: str, context: dict) -> None:
        """
        Internal log method with context.
        
        Args:
            level: Log level
            msg: Message
            context: Additional context as key-value pairs
        """
        if context:
            # Format context as key=value pairs
            context_str = ' '.join(f'{k}={v}' for k, v in context.items())
            full_msg = f'{msg} [{context_str}]'
        else:
            full_msg = msg
        
        self.logger.log(level, full_msg)


# Global logger instance
_logger: Optional[StructuredLogger] = None


def init_logger(name: str = 'mcp_server') -> StructuredLogger:
    """
    Initialize and get the global logger.
    
    Args:
        name: Logger name
        
    Returns:
        StructuredLogger instance
    """
    global _logger
    if _logger is None:
        _logger = StructuredLogger(name)
    return _logger
