"""
Gunicorn configuration for production
"""
import multiprocessing

# Server socket
bind = "127.0.0.1:8001"
backlog = 2048

# Worker processes
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 30
keepalive = 2

# Restart workers after this many requests, to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
errorlog = "/var/log/inspice/gunicorn_error.log"
accesslog = "/var/log/inspice/gunicorn_access.log"
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'

# Process naming
proc_name = "inspice_gunicorn"

# Daemon mode
daemon = False

# User and group
user = "www-data"
group = "www-data"

# Preload application
preload_app = True

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Environment
raw_env = [
    "DJANGO_SETTINGS_MODULE=inspice_seo_tool.settings",
]