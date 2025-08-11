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
        'devops': {
            'format': '{asctime} [{levelname}] DevOps - {module}.{funcName}:{lineno} - {message}',
            'style': '{',
        },
        'collaboration': {
            'format': '{asctime} [{levelname}] Collaboration - {module}.{funcName}:{lineno} - {message}',
            'style': '{',
        },
        'auth': {
            'format': '{asctime} [{levelname}] Auth - {module}.{funcName}:{lineno} - {message}',
            'style': '{',
        },
        'system': {
            'format': '{asctime} [{levelname}] System - {module}.{funcName}:{lineno} - {message}',
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
        'devops_file': {
            'level': 'DEBUG',
            'formatter': 'devops',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, "devops.log"),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'encoding': 'utf-8',
        },
        'devops_actions_file': {
            'level': 'INFO',
            'formatter': 'devops',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, "devops_actions.log"),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'encoding': 'utf-8',
        },
        'collaboration_file': {
            'level': 'DEBUG',
            'formatter': 'collaboration',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, "collaboration.log"),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'encoding': 'utf-8',
        },
        'collaboration_actions_file': {
            'level': 'INFO',
            'formatter': 'collaboration',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, "collaboration_actions.log"),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'encoding': 'utf-8',
        },
        'auth_file': {
            'level': 'DEBUG',
            'formatter': 'auth',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, "auth.log"),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'encoding': 'utf-8',
        },
        'auth_actions_file': {
            'level': 'INFO',
            'formatter': 'auth',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, "auth_actions.log"),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'encoding': 'utf-8',
        },
        'system_file': {
            'level': 'DEBUG',
            'formatter': 'system',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, "system.log"),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'encoding': 'utf-8',
        },
        'system_actions_file': {
            'level': 'INFO',
            'formatter': 'system',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': os.path.join(LOGS_DIR, "system_actions.log"),
            'maxBytes': 10 * 1024 * 1024,  # 10 MB
            'backupCount': 10,
            'encoding': 'utf-8',
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
        'devops': {  # Added logger for DevOps app
            'handlers': ['console', 'devops_file', 'devops_actions_file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG').upper(),
            'propagate': False,
        },
        'collaboration': {  # Added logger for Collaboration app
            'handlers': ['console', 'collaboration_file', 'collaboration_actions_file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG').upper(),
            'propagate': False,
        },
        'auth': {  # Added logger for Auth app
            'handlers': ['console', 'auth_file', 'auth_actions_file'],
            'level': os.getenv('DJANGO_LOG_LEVEL', 'DEBUG').upper(),
            'propagate': False,
        },
        'system': {  # Added logger for System app
            'handlers': ['console', 'system_file', 'system_actions_file'],
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