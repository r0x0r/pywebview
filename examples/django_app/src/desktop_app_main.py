import os
import socket
import urllib

# This code is heavily based on https://moosystems.com/articles/14-distribute-django-app-as-native-desktop-app-01.html

os.environ["DJANGO_APP_MODE"] = "desktop_app"

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

import cherrypy
from django.core.wsgi import get_wsgi_application
import webview
import subprocess
import sys
import threading
import logging.handlers


# Django standalone application for DjangoExampleApp
class DjangoApplication(object):
    def __init__(self):
        self.servers = []
        self.domains = {}

    def add_server(self, netloc, path, config):
        """Add a new CherryPy Application for a Virtual Host.
        Creates a new CherryPy WSGI Server instance if the host resolves
        to a different IP address or port.
        """

        from cherrypy._cpwsgi_server import CPWSGIServer
        from cherrypy.process.servers import ServerAdapter

        host, port = urllib.splitnport(netloc, 80)
        host = socket.gethostbyname(host)
        bind_addr = (host, port)
        if bind_addr not in self.servers:
            self.servers.append(bind_addr)
            server = CPWSGIServer()
            server.bind_addr = bind_addr
            adapter = ServerAdapter(cherrypy.engine, server, server.bind_addr)
            adapter.subscribe()
        self.domains[netloc] = cherrypy.Application(root=None,
            config={path.rstrip('/') or '/': config})

    def cfg_assets(self, url, root):
        """Configure hosting of static and media asset directories.
        Can either mount to a specific path or add a Virtual Host. Sets
        Expires header to 1 year.
        """
        url_parts = urlparse.urlsplit(url)
        path = url_parts.path.rstrip('/')
        config = {
            'tools.staticdir.on': True,
            'tools.staticdir.dir': root,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 365, # 1 year
            'tools.gzip.on': True,
            'tools.gzip.mime_types': [
                'text/*',
                'application/javascript',
                'application/x-javascript',
            ],
        }
        if url_parts.netloc:
            self.add_server(url_parts.netloc, path, config)
        elif path:
            cherrypy.tree.mount(None, path, {'/': config})

    def cfg_favicon(self, root):
        """Configure a default favicon.

        Expects it to be in STATIC_ROOT.

        """
        favicon = os.path.join(root, 'favicon.ico')
        config = {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': favicon,
            'tools.expires.on': True,
            'tools.expires.secs': 60 * 60 * 24 * 365, # 1 year
        }
        cherrypy.tree.mount(None, '/favicon.ico', {'/': config})

    def run(self, netloc='0.0.0.0:9090', reload=True, log=True):
        """Run the CherryPy server."""
        from django.conf import settings
        from django.core.handlers.wsgi import WSGIHandler
        from paste.translogger import TransLogger

        url_parts = urlparse.urlsplit(netloc)
        host = "0.0.0.0"
        port = 9090
        cherrypy.config.update({
            'server.socket_host': host,
            'server.socket_port': port,
            'log.screen': False,
            'engine.autoreload.on': reload,
            'log.access_file': cherry_access_log,
            'log.error_file': cherry_error_log,
        })
        self.cfg_assets(settings.MEDIA_URL, settings.MEDIA_ROOT)
        self.cfg_assets(settings.STATIC_URL, settings.STATIC_ROOT)
        self.cfg_favicon(settings.STATIC_ROOT)
        app = WSGIHandler()
        app = TransLogger(app, logger_name='cherrypy.access',
                          setup_console_handler=False)
        if self.domains:
            app = cherrypy.wsgi.VirtualHost(app, self.domains)
        cherrypy.tree.graft(app)
        cherrypy.engine.start()


def main(**kwargs):
    app = DjangoApplication()
    app.run(**kwargs)


if __name__ == '__main__':

    # check if we are running as py2app bundle or as a script
    if getattr(sys, 'frozen', None):
        base_dir = os.path.realpath(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        run_as_binary = True
    else:
        base_dir = os.path.realpath(os.path.dirname(__file__))
        run_as_binary = False

    # set up logging and app_name
    if run_as_binary is True:
        log_file = os.path.join(base_dir, "../logs/", "DjangoApp.log")
        cherry_access_log = os.path.join(base_dir, "../logs/", "access.log")
        cherry_error_log = os.path.join(base_dir, "../logs/", "error.log")
        app_name = "DjangoApp"
    else:
        log_file = os.path.join(base_dir, "logs/DjangoApp.log")
        cherry_access_log = os.path.join(base_dir, "logs/access.log")
        cherry_error_log = os.path.join(base_dir, "logs/error.log")
        app_name = "DjangoApp"

    log = logging.getLogger("DjangoApp")
    log.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler(log_file,
                                                   maxBytes=30000000,
                                                   backupCount=10)
    handler.setLevel(logging.DEBUG)
    fmt = logging.Formatter('%(asctime)s - %(message)s')
    handler.setFormatter(fmt)
    log.addHandler(handler)

    # Django settings
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangoapp.settings')
    application = get_wsgi_application()

    # make app show up as frontmost app
    system_feedback = subprocess.Popen([
        "/usr/bin/osascript",
        "-e",
        'tell app \"Finder\" to set frontmost of process \"%s\" to true' % app_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        close_fds=True).communicate()[0].rstrip().decode("utf-8")

    # let web app run as background thread
    t = threading.Thread(target=main(netloc="0.0.0.0:9090",
                                     reload=True,
                                     log='log'))
    t.daemon = True
    t.start()

    # Create a resizable webview window with 800x600 dimensions
    webview.create_window("DjangoApp", "http://localhost:9090/",
                          width=800, height=600, resizable=True,
                          fullscreen=False)

    # stop django when user closes UI
    cherrypy.engine.stop()
    cherrypy.engine.exit()
