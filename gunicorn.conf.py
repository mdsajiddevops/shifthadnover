# Gunicorn configuration — edit this file to tune server parameters.
# REQ-002: Application shall be served by Gunicorn; default worker count is 1.
# Do NOT set daemon = True; containers must run in the foreground.

workers = 1
# gthread allows multiple concurrent WebSocket connections per worker (one thread per WS conn).
worker_class = "gthread"
threads = 8
bind = "0.0.0.0:5000"
timeout = 120
loglevel = "info"
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
