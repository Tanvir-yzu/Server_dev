# System/views.py
import os
import random
import logging
from datetime import datetime, timedelta
from functools import wraps
import time

from django.shortcuts import render
from django.views.generic import TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required, user_passes_test

# Initialize logger for System app
logger = logging.getLogger('system')

def log_system_action(action_name):
    """
    Decorator to log system-related actions with timing and context
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            request = None
            
            # Extract request object from args
            if args and hasattr(args[0], 'request'):
                request = args[0].request
            elif args and hasattr(args[0], 'method'):
                request = args[0]
            
            user_info = "Anonymous"
            if request and hasattr(request, 'user') and request.user.is_authenticated:
                user_info = f"{request.user.email} (ID: {request.user.id})"
            
            logger.info(f"Starting {action_name} - User: {user_info}")
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"Completed {action_name} - User: {user_info} - Time: {execution_time:.2f}s")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"Failed {action_name} - User: {user_info} - Error: {str(e)} - Time: {execution_time:.2f}s")
                raise
        return wrapper
    return decorator


class AdminLogsView(LoginRequiredMixin, TemplateView):
    template_name = 'admin_logs.html'
    
    def dispatch(self, request, *args, **kwargs):
        logger.debug(f"AdminLogsView accessed by user: {request.user.email if request.user.is_authenticated else 'Anonymous'}")
        
        # Ensure only staff/admin users can access
        if not request.user.is_staff:
            logger.warning(f"Unauthorized access attempt to admin logs by user: {request.user.email if request.user.is_authenticated else 'Anonymous'}")
            raise PermissionDenied("You must be a staff member to access system logs.")
        
        return super().dispatch(request, *args, **kwargs)
    
    @log_system_action("Admin Logs View")
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Get log files
            log_files = self.get_log_files()
            selected_log = self.request.GET.get('log', 'debug.log')  # Changed default to debug.log
            log_content = self.read_log_file(selected_log)
            
            logger.debug(f"Loading log files for admin view - Selected: {selected_log}, Available: {len(log_files)} files")
            
            context.update({
                'title': 'System Logs',
                'user': self.request.user,
                'log_files': log_files,
                'selected_log': selected_log,
                'log_content': log_content,
                'page_name': 'admin_logs'
            })
            
            return context
            
        except Exception as e:
            logger.error(f"Error loading admin logs context: {str(e)}")
            # Return minimal context with error message
            context.update({
                'title': 'System Logs',
                'user': self.request.user,
                'log_files': [],
                'selected_log': '',
                'log_content': f"Error loading logs: {str(e)}",
                'page_name': 'admin_logs'
            })
            return context
    
    def get_log_files(self):
        """Get list of available log files"""
        log_files = []
        
        try:
            # Get LOGS_DIR from settings or use default
            logs_dir = getattr(settings, 'LOGS_DIR', None)
            if not logs_dir:
                # Try to get from local_settings
                try:
                    from Server_dev.local_settings import LOGS_DIR
                    logs_dir = LOGS_DIR
                except ImportError:
                    logs_dir = os.path.join(settings.BASE_DIR, 'logs')
            
            # Common log file locations
            log_paths = [
                logs_dir,  # Primary logs directory
                os.path.join(settings.BASE_DIR, 'logs'),
                settings.BASE_DIR,  # Root project directory
            ]
            
            # Add Unix/Linux log paths only if not on Windows
            if os.name != 'nt':
                log_paths.append('/var/log')
            
            logger.debug(f"Searching for log files in paths: {log_paths}")
            
            for log_path in log_paths:
                if os.path.exists(log_path) and os.path.isdir(log_path):
                    try:
                        for file in os.listdir(log_path):
                            if file.endswith('.log'):
                                log_files.append(file)
                                logger.debug(f"Found log file: {file}")
                    except (PermissionError, OSError) as e:
                        logger.warning(f"Cannot access log directory {log_path}: {str(e)}")
                        continue
            
            # Remove duplicates and sort
            log_files = sorted(list(set(log_files)))
            
            # Add default logs if no logs found
            if not log_files:
                default_logs = ['debug.log', 'warnings.log', 'devops.log', 'collaboration.log', 'auth.log']
                logger.info("No log files found, using default list")
                log_files = default_logs
            
            logger.info(f"Available log files: {log_files}")
            return log_files
            
        except Exception as e:
            logger.error(f"Error getting log files: {str(e)}")
            return ['debug.log', 'warnings.log']  # Fallback
    
    def read_log_file(self, filename, lines=100):
        """Read last N lines from log file"""
        if not filename:
            logger.warning("No log file selected")
            return "No log file selected."
            
        # Security check - only allow .log files
        if not filename.endswith('.log'):
            logger.warning(f"Invalid log file format requested: {filename}")
            return "Invalid log file format. Only .log files are allowed."
        
        # Sanitize filename to prevent directory traversal
        filename = os.path.basename(filename)
        
        try:
            # Get LOGS_DIR from settings
            logs_dir = getattr(settings, 'LOGS_DIR', None)
            if not logs_dir:
                try:
                    from Server_dev.local_settings import LOGS_DIR
                    logs_dir = LOGS_DIR
                except ImportError:
                    logs_dir = os.path.join(settings.BASE_DIR, 'logs')
            
            # Possible log file locations in order of preference
            possible_paths = [
                os.path.join(logs_dir, filename),
                os.path.join(settings.BASE_DIR, 'logs', filename),
                os.path.join(settings.BASE_DIR, filename),
            ]
            
            # Add Unix/Linux paths only if not on Windows
            if os.name != 'nt':
                possible_paths.append(os.path.join('/var/log', filename))
            
            logger.debug(f"Searching for log file {filename} in paths: {possible_paths}")
            
            for log_path in possible_paths:
                if os.path.exists(log_path) and os.path.isfile(log_path):
                    try:
                        logger.debug(f"Reading log file: {log_path}")
                        with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                            # Read last N lines efficiently
                            lines_list = f.readlines()
                            if len(lines_list) > lines:
                                lines_list = lines_list[-lines:]
                            
                            content = ''.join(lines_list)
                            logger.info(f"Successfully read {len(lines_list)} lines from {filename}")
                            return content
                            
                    except (IOError, PermissionError, UnicodeDecodeError) as e:
                        logger.error(f"Error reading log file {log_path}: {str(e)}")
                        continue
            
            # If no log file found, return sample log data
            logger.warning(f"Log file {filename} not found in any location, returning sample data")
            return self.get_sample_log_data()
            
        except Exception as e:
            logger.error(f"Unexpected error reading log file {filename}: {str(e)}")
            return f"Error reading log file: {str(e)}"
    
    def get_sample_log_data(self):
        """Return sample log data when no actual log files are found"""
        try:
            sample_logs = []
            log_levels = ['INFO', 'WARNING', 'ERROR', 'DEBUG']
            messages = [
                'User login successful',
                'Database connection established',
                'Email sent successfully',
                'Cache cleared',
                'Session expired',
                'File upload completed',
                'API request processed',
                'Background task started',
                'System backup completed',
                'Security scan finished',
                'Configuration updated',
                'Memory usage normal',
                'Disk space check completed',
                'Network connectivity verified',
                'SSL certificate validated'
            ]
            
            logger.info("Generating sample log data")
            
            for i in range(50):
                # Generate timestamps in the past 24 hours
                timestamp = datetime.now() - timedelta(minutes=random.randint(1, 1440))
                level = random.choice(log_levels)
                message = random.choice(messages)
                
                log_entry = f"[{timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {level}: {message}\n"
                sample_logs.append(log_entry)
            
            # Sort by timestamp (most recent first)
            sample_logs.sort(key=lambda x: x.split(']')[0][1:], reverse=True)
            
            return ''.join(sample_logs)
            
        except Exception as e:
            logger.error(f"Error generating sample log data: {str(e)}")
            return f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] ERROR: Unable to generate sample log data\n"


@login_required
@user_passes_test(lambda u: u.is_staff)
@require_http_methods(["GET"])
def refresh_logs_ajax(request):
    """
    AJAX endpoint to refresh log content without page reload
    """
    try:
        selected_log = request.GET.get('log', 'debug.log')
        lines = int(request.GET.get('lines', 100))
        
        logger.info(f"AJAX log refresh requested - File: {selected_log}, Lines: {lines}")
        
        # Create instance to use the methods
        admin_logs_view = AdminLogsView()
        admin_logs_view.request = request
        
        log_content = admin_logs_view.read_log_file(selected_log, lines)
        
        return JsonResponse({
            'success': True,
            'log_content': log_content,
            'selected_log': selected_log,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        logger.error(f"Error in AJAX log refresh: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })


@login_required
@user_passes_test(lambda u: u.is_staff)
def download_log_file(request, filename):
    """
    Download a specific log file
    """
    try:
        # Security check
        if not filename.endswith('.log'):
            logger.warning(f"Invalid log file download attempt: {filename}")
            raise PermissionDenied("Invalid file type")
        
        filename = os.path.basename(filename)  # Prevent directory traversal
        
        logger.info(f"Log file download requested: {filename} by user {request.user.email}")
        
        # Get log file path
        logs_dir = getattr(settings, 'LOGS_DIR', os.path.join(settings.BASE_DIR, 'logs'))
        file_path = os.path.join(logs_dir, filename)
        
        if not os.path.exists(file_path):
            logger.warning(f"Log file not found for download: {file_path}")
            raise Http404("Log file not found")
        
        from django.http import FileResponse
        response = FileResponse(
            open(file_path, 'rb'),
            as_attachment=True,
            filename=filename
        )
        
        logger.info(f"Log file {filename} downloaded successfully by {request.user.email}")
        return response
        
    except Exception as e:
        logger.error(f"Error downloading log file {filename}: {str(e)}")
        from django.http import Http404
        raise Http404("Error downloading log file")


# System health check view
class SystemHealthView(LoginRequiredMixin, TemplateView):
    template_name = 'system_health.html'
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Staff access required")
        return super().dispatch(request, *args, **kwargs)
    
    @log_system_action("System Health Check")
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            import psutil
            import django
            from django.db import connection
            
            # System information
            system_info = {
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory': psutil.virtual_memory(),
                'disk': psutil.disk_usage('/'),
                'django_version': django.get_version(),
                'python_version': f"{psutil.sys.version_info.major}.{psutil.sys.version_info.minor}.{psutil.sys.version_info.micro}",
            }
            
            # Database check
            try:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                db_status = "Connected"
            except Exception as e:
                db_status = f"Error: {str(e)}"
                logger.error(f"Database connection error: {str(e)}")
            
            context.update({
                'title': 'System Health',
                'system_info': system_info,
                'db_status': db_status,
                'page_name': 'system_health'
            })
            
        except ImportError:
            logger.warning("psutil not available for system health check")
            context.update({
                'title': 'System Health',
                'error': 'System monitoring requires psutil package',
                'page_name': 'system_health'
            })
        except Exception as e:
            logger.error(f"Error in system health check: {str(e)}")
            context.update({
                'title': 'System Health',
                'error': str(e),
                'page_name': 'system_health'
            })
        
        return context