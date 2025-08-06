# PYTHON IMPORTS
import os
import logging.handlers
from pathlib import Path

# PROJECT IMPORTS
from Server_dev.local_settings import LOGS_DIR

# Ensure logs directory exists
Path(LOGS_DIR).mkdir(parents=True, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{asctime} {levelname} {module} {process:d} {thread:d} '
                      '{message}',
            'style': '{',
        },
        'simple': {
            'format': '{asctime} {levelname} {message}',
            'style': '{',
        },
    },  # formatters
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'DEBUG',
            'formatter': 'verbose',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, "debug.log"),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'encoding': 'utf-8',  # Added encoding for better compatibility
        },
        'warnings_file': {
            'level': 'WARNING',
            'formatter': 'verbose',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, "warnings.log"),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'encoding': 'utf-8',  # Added encoding for better compatibility
        },
    },  # handlers
    'loggers': {
        '': {  # root logger
            'handlers': ['console', 'file', 'warnings_file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'INFO').upper(),
        },
        'customauth': {
            'handlers': ['console', 'file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG').upper(),
            'propagate': False,  # required to eliminate duplication on root
        },
        'dashboard': {
            'handlers': ['console', 'file', 'warnings_file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG').upper(),
            'propagate': False,
        },
        'software': {  # Added logger for software app
            'handlers': ['console', 'file', 'warnings_file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG').upper(),
            'propagate': False,
        },
        # 'app_name': {
        #     'handlers': ['console', 'file'],
        #     'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG').upper(),
        #     'propagate': False,  # required to eliminate duplication on root
        # },
    },  # loggers
}  # logging