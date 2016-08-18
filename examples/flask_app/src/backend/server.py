import os
from flask import Flask, url_for, render_template, jsonify, request, make_response
import webview

import app

gui_dir = os.path.join(os.getcwd(), "gui")  # development path
if not os.path.exists(gui_dir):  # frozen executable path
    gui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui")

server = Flask(__name__, static_folder=gui_dir, template_folder=gui_dir)
server.config["SEND_FILE_MAX_AGE_DEFAULT"] = 1  # disable caching


@server.after_request
def add_header(response):
    response.headers['Cache-Control'] = 'no-store'
    return response


@server.route("/")
def landing():
    """
    Render index.html. Initialization is performed asynchronously in initialize() function
    """
    return render_template("index.html")


@server.route("/init")
def initialize():
    """
    Perform heavy-lifting initialization asynchronously.
    :return:
    """
    can_start = app.initialize()

    if can_start:
        response = {
            "status": "ok",
        }
    else:
        response = {
            "status": "error"
        }

    return jsonify(response)


@server.route("/choose/path")
def choose_path():
    """
    Invoke a folder selection dialog here
    :return:
    """
    dirs = webview.create_file_dialog(webview.FOLDER_DIALOG)
    if dirs and len(dirs) > 0:
        directory = dirs[0]
        if isinstance(directory, bytes):
            directory = directory.decode("utf-8")

        response = {"status": "ok", "directory": directory}
    else:
        response = {"status": "cancel"}

    return jsonify(response)


@server.route("/do/stuff", methods=["POST"])
def search():
    options = request.form["options"]
    status = app.do_stuff(options)

    if status:
        response = {"status": "ok"}
    else:
        response = {"status": "error"}

    return jsonify(response)


def run_server():
    server.run(host="127.0.0.1", port=41357, threaded=True)


if __name__ == "__main__":
    run_server()
