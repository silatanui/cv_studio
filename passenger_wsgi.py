import os
import sys

# Ensure current application directory is in Python path
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Native Synchronous WSGI Application
# Directly compatible with cPanel / CloudLinux / Phusion Passenger / LiteSpeed
from wsgi_app import app as application
