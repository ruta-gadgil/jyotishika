"""
Centralized Logging Configuration

Provides structured logging with JSON formatting for production
and human-readable formatting for development.
"""

import os
import sys
import logging
import json
from datetime import datetime
from typing import Any, Dict
from flask import Flask, has_request_context, request, g


class JsonFormatter(logging.Formatter):
    """
    JSON formatter for structured logging in production.
    
    Outputs logs as JSON for easy parsing by log aggregators like
    CloudWatch, Datadog, or ELK stack.
    """
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add request context if available
        if has_request_context():
            log_data["request"] = {
                "method": request.method,
                "path": request.path,
                "remote_addr": request.remote_addr,
            }
            
            # Add user_id if available
            if hasattr(g, 'current_user') and g.current_user:
                log_data["user_id"] = str(g.current_user.id)
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields from record
        if hasattr(record, 'extra_data'):
            log_data["extra"] = record.extra_data
        
        # Add source location for errors
        if record.levelno >= logging.ERROR:
            log_data["source"] = {
                "file": record.pathname,
                "line": record.lineno,
                "function": record.funcName,
            }
        
        return json.dumps(log_data, ensure_ascii=False)


class ColoredFormatter(logging.Formatter):
    """
    Human-readable formatter with colors for development.
    
    Adds color coding based on log level for easier reading
    during development.
    """
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with colors."""
        # Get color for log level
        color = self.COLORS.get(record.levelname, '')
        
        # Format timestamp
        timestamp = datetime.utcnow().strftime('%H:%M:%S')
        
        # Build log message
        log_parts = [
            f"{color}{record.levelname:8s}{self.RESET}",
            f"{timestamp}",
            f"{record.name:20s}",
            record.getMessage(),
        ]
        
        # Add request context if available
        if has_request_context():
            log_parts.append(f"[{request.method} {request.path}]")
        
        message = " | ".join(log_parts)
        
        # Add exception if present
        if record.exc_info:
            message += "\n" + self.formatException(record.exc_info)
        
        return message


def configure_logging(app: Flask) -> None:
    """
    Configure logging for the Flask application.
    
    Args:
        app: Flask application instance
        
    Sets up:
    - JSON logging for production (FLASK_ENV=production)
    - Colored logging for development
    - Appropriate log levels
    - Log handlers for stdout
    """
    # Get configuration from environment
    env = os.environ.get('FLASK_ENV', 'development')
    log_level_str = os.environ.get('LOG_LEVEL', 'INFO').upper()
    
    # Parse log level
    log_level = getattr(logging, log_level_str, logging.INFO)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # Choose formatter based on environment
    if env == 'production':
        formatter = JsonFormatter()
    else:
        formatter = ColoredFormatter()
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Configure Flask app logger
    app.logger.setLevel(log_level)
    
    # Configure third-party loggers
    # Reduce noise from verbose libraries
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
    
    # Log configuration
    app.logger.info(f"Logging configured - Environment: {env}, Level: {log_level_str}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
        
    Example:
        logger = get_logger(__name__)
        logger.info("Operation successful")
    """
    return logging.getLogger(name)


class LoggerAdapter(logging.LoggerAdapter):
    """
    Logger adapter that adds context to log messages.
    
    Useful for adding request-specific context to all logs
    within a request handler.
    """
    
    def process(self, msg: str, kwargs: Dict[str, Any]) -> tuple:
        """Add extra context to log record."""
        # Add extra data to record
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        # Add context from adapter
        if self.extra:
            kwargs['extra']['extra_data'] = self.extra
        
        return msg, kwargs


def create_logger_with_context(**context) -> LoggerAdapter:
    """
    Create a logger with additional context.
    
    Args:
        **context: Key-value pairs to add to all log messages
        
    Returns:
        Logger adapter with context
        
    Example:
        logger = create_logger_with_context(user_id="123", request_id="abc")
        logger.info("Processing request")
    """
    logger = logging.getLogger()
    return LoggerAdapter(logger, context)
