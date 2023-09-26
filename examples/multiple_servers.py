"""
Create multiple windows, some of which have their own servers, both before and after `webview.start()` is called.
"""

import bottle

import webview

# We'll have a global list of our windows so our web app can give us information
# about them
windows = []


# A simple function to format a description of our servers
def serverDescription(server):
    return f"{str(server).replace('<','').replace('>','')}"


# Define a couple of simple web apps using Bottle
app1 = bottle.Bottle()


@app1.route('/')
def hello():
    return '<h1>Second Window</h1><p>This one is a web app and has its own server.</p>'


app2 = bottle.Bottle()


@app2.route('/')
def hello():
    head = """  <head>
                    <style type="text/css">
                        table {
                          font-family: arial, sans-serif;
                          border-collapse: collapse;
                          width: 100%;
                        }

                        td, th {
                          border: 1px solid #dddddd;
                          text-align: center;
                          padding: 8px;
                        }

                        tr:nth-child(even) {
                          background-color: #dddddd;
                        }
                    </style>
                </head>
            """
    body = f""" <body>
                    <h1>Third Window</h1>
                    <p>This one is another web app and has its own server. It was started after webview.start.</p>
                    <p>Server Descriptions: </p>
                    <table>
                        <tr>
                            <th>Window</th>
                            <th>Object</th>
                            <th>IP Address</th>
                        </tr>
                        <tr>
                            <td>Global Server</td>
                            <td>{serverDescription(webview.http.global_server)}</td>
                            <td>{webview.http.global_server.address if not webview.http.global_server is None else 'None'}</td>
                        </tr>
                        <tr>
                            <td>First Window</td>
                            <td>{serverDescription(windows[0]._server)}</td>
                            <td>{windows[0]._server.address if not windows[0]._server is None else 'None'}</td>
                        </tr>
                        <tr>
                            <td>Second Window</td>
                            <td>{serverDescription(windows[1]._server)}</td>
                            <td>{windows[1]._server.address}</td>
                        </tr>
                        <tr>
                            <td>Third Window</td>
                            <td>{serverDescription(windows[2]._server)}</td>
                            <td>{windows[2]._server.address}</td>
                        </tr>
                    </table>
                </body>
            """
    return head + body


def third_window():
    # Create a new window after the loop started
    windows.append(webview.create_window('Window #3', url=app2))


if __name__ == '__main__':
    # Master window
    windows.append(
        webview.create_window(
            'Window #1',
            html='<h1>First window</h1><p>This one is static HTML and just uses the global server for api calls.</p>',
        )
    )
    windows.append(webview.create_window('Window #2', url=app1, http_port=3333))
    webview.start(third_window, debug=True, http_server=True, http_port=3334)
