"""
Shared flask-sock Sock instance (CTCOAMSHM-7).

Created without an app so routes can be registered via @sock.route(...) before
app.py calls sock.init_app(app). All deferred routes are registered at that point.
"""
from flask_sock import Sock

sock = Sock()
