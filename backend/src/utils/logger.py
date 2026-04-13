"""
Logger Configuration

Sets up JSON-formatted logging for the IBDDS EPHR system.
All security events, access attempts, and system operations are logged.
"""

import logging
import json
import os
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """Custom formatter that outputs log records as JSON."""

    def format(self, record):
        log_entry = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        if hasattr(record, 'extra_data'):
            log_entry['data'] = record.extra_data

        if record.exc_info:
            log_entry['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logger(name='ibdds', level=logging.INFO, log_file=None):
    """
    Configure and return a JSON-formatted logger.
    
    Args:
        name: Logger name
        level: Logging level
        log_file: Optional file path for log output
    """
    logger = logging.getLogger(name)
    
    if logger.handlers:
        return logger
    
    logger.setLevel(level)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_dir = os.path.dirname(log_file)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    return logger


# Create default logger instance
logger = setup_logger()


def log_security_event(action, actor_id=None, patient_id=None, resource_id=None, 
                       status='success', details=None):
    """
    Log a security-relevant event (for audit purposes).
    
    Args:
        action: Type of action (e.g., 'login', 'access_record', 'grant_access')
        actor_id: Who performed the action
        patient_id: Whose record was affected
        resource_id: Specific resource ID involved
        status: 'success' or 'denied'
        details: Additional context
    """
    event = {
        'action': action,
        'actor_id': actor_id,
        'patient_id': patient_id,
        'resource_id': resource_id,
        'status': status,
        'details': details,
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    logger.info(f"SECURITY_EVENT: {action}", extra={'extra_data': event})
