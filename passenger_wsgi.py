import os
import sys
import glob
import traceback

# Ensure current application directory is in Python path
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

# Auto-detect cPanel virtual environment site-packages if not already active
# cPanel standard structure: /home/<user>/virtualenv/<app_path>/<py_version>/lib/python<py_version>/site-packages
home_dir = os.path.expanduser("~")
cpanel_venvs = glob.glob(os.path.join(home_dir, "virtualenv", "*", "*", "lib", "python*", "site-packages"))
for venv_path in cpanel_venvs:
    if venv_path not in sys.path:
        sys.path.insert(0, venv_path)

# Also check for local venv/.venv folders inside the project
for venv_dir in ["venv", ".venv"]:
    local_sp_linux = os.path.join(APP_DIR, venv_dir, "lib", f"python{sys.version_info.major}.{sys.version_info.minor}", "site-packages")
    local_sp_win = os.path.join(APP_DIR, venv_dir, "Lib", "site-packages")
    if os.path.isdir(local_sp_linux) and local_sp_linux not in sys.path:
        sys.path.insert(0, local_sp_linux)
    if os.path.isdir(local_sp_win) and local_sp_win not in sys.path:
        sys.path.insert(0, local_sp_win)

# Attempt to load the application with clear error reporting on failure
try:
    from wsgi_app import app as application
except Exception as e:
    err_tb = traceback.format_exc()

    # Log to a file in the app directory for inspection in cPanel File Manager
    try:
        with open(os.path.join(APP_DIR, "passenger_error.log"), "w", encoding="utf-8") as f:
            f.write(err_tb)
    except Exception:
        pass

    # Provide an informative debug page in the browser instead of opaque 500
    def application(environ, start_response):
        status = '500 Internal Server Error'
        response_headers = [('Content-Type', 'text/html; charset=utf-8')]
        start_response(status, response_headers)
        
        py_version = sys.version
        py_exec = sys.executable
        py_path = "<br>".join(sys.path[:10])

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>CV Studio - Application Startup Error</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; padding: 2rem; margin: 0; }}
        .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 2rem; max-width: 900px; margin: 0 auto; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }}
        h1 {{ color: #ef4444; margin-top: 0; font-size: 1.5rem; }}
        pre {{ background: #0b1120; color: #f87171; padding: 1.25rem; border-radius: 8px; overflow-x: auto; font-size: 0.88rem; line-height: 1.5; }}
        .box {{ background: #0b1120; border: 1px solid #334155; padding: 1rem; border-radius: 8px; font-size: 0.85rem; margin-top: 1rem; color: #94a3b8; }}
        ul {{ padding-left: 1.4rem; color: #cbd5e1; line-height: 1.6; }}
        code {{ background: #334155; color: #38bdf8; padding: 2px 6px; border-radius: 4px; font-family: monospace; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>⚠️ CV Studio - Application Startup Error</h1>
        <p>The application encountered an error while starting up in Phusion Passenger:</p>
        <pre>{err_tb}</pre>
        <h3>Recommended Fixes:</h3>
        <ul>
            <li><strong>Missing Dependencies:</strong> In cPanel &rarr; <em>Setup Python App</em> &rarr; click on your app &rarr; in <strong>Configuration files</strong>, enter <code>requirements.txt</code> and click <strong>Add</strong>, then click <strong>Run Pip Install</strong>.</li>
            <li><strong>Missing .env File:</strong> Make sure a <code>.env</code> file exists in <code>cv_studio/</code> with your <code>OPENAI_API_KEY</code>.</li>
            <li><strong>Python Version:</strong> Ensure Python 3.10 or 3.11 is selected in <em>Setup Python App</em>.</li>
        </ul>
        <div class="box">
            <strong>Runtime Information:</strong><br>
            <strong>Python:</strong> {py_version}<br>
            <strong>Executable:</strong> {py_exec}<br>
            <strong>sys.path (first 10):</strong><br>{py_path}
        </div>
    </div>
</body>
</html>"""
        return [html.encode('utf-8')]
