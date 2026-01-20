import os

# Server socket
bind = "0.0.0.0:8080"

# Worker processes
workers = int(os.environ.get("GUNICORN_WORKERS", "2"))
threads = int(os.environ.get("GUNICORN_THREADS", "4"))
worker_class = "gthread"
worker_tmp_dir = "/dev/shm"  # Use memory for worker heartbeats (faster)

# Timeouts
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
graceful_timeout = 30
keepalive = 5

# Process naming
proc_name = "jyotishika-api"

# Server mechanics
daemon = False
pidfile = None
umask = 0
user = None
group = None
tmp_upload_dir = None
preload_app = True

# Logging
accesslog = "-"  # Log to stdout
errorlog = "-"   # Log to stderr
loglevel = os.environ.get("LOG_LEVEL", "info").lower()

# Access log format
# h: remote address, l: '-', u: user name, t: date/time, r: request line
# s: status code, b: response size, f: referer, a: user agent, D: time in microseconds
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Don't log health checks (reduce noise)
def is_health_check(request):
    """Check if request is a health check."""
    return request.path == "/healthz"

def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting Gunicorn server")

def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading Gunicorn server")

def when_ready(server):
    """Called just after the server is started."""
    server.log.info(f"Gunicorn server ready - Workers: {workers}, Threads: {threads}")

def worker_int(worker):
    """Called when a worker receives the INT or QUIT signal."""
    worker.log.info(f"Worker {worker.pid} received INT/QUIT signal")

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.error(f"Worker {worker.pid} aborted")

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    pass

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info(f"Worker {worker.pid} spawned")

def post_worker_init(worker):
    """Called just after a worker has initialized the application."""
    worker.log.info(f"Worker {worker.pid} initialized")

def worker_exit(server, worker):
    """Called just after a worker has been exited."""
    server.log.info(f"Worker {worker.pid} exited")

def nworkers_changed(server, new_value, old_value):
    """Called when the number of workers changes."""
    server.log.info(f"Number of workers changed from {old_value} to {new_value}")

def pre_exec(server):
    """Called just before a new master process is forked."""
    server.log.info("Pre-execution: Forking new master process")

def pre_request(worker, req):
    """Called before each request."""
    # Don't log health checks
    if is_health_check(req):
        return
    worker.log.debug(f"{req.method} {req.path}")

def post_request(worker, req, environ, resp):
    """Called after each request."""
    # Don't log health checks
    if is_health_check(req):
        return

def child_exit(server, worker):
    """Called when a worker exits."""
    server.log.info(f"Worker child {worker.pid} exited")

def worker_abort(worker):
    """Called when a worker times out."""
    worker.log.error(f"Worker {worker.pid} timed out")

def on_exit(server):
    """Called just before exiting Gunicorn."""
    server.log.info("Shutting down Gunicorn server")
