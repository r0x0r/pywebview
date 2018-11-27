# Javascript API

Create an application without a HTTP server. The application uses Javascript API object to communicate between Python and Javascript. 

``` python
import webview
import threading
import time
import sys
import random


html = """
<!DOCTYPE html>
<html>
<head lang="en">
<meta charset="UTF-8">

<style>
    #response-container {
        display: none;
        padding: 3rem;
        margin: 3rem 5rem;
        font-size: 120%;
        border: 5px dashed #ccc;
    }

    label {
        margin-left: 0.3rem;
        margin-right: 0.3rem;
    }
     
    button {
        font-size: 100%;
        padding: 0.5rem;
        margin: 0.3rem;
        text-transform: uppercase;
    }

</style>
</head>
<body>


<h1>JS API Example</h1>
<button onClick="initialize()">Hello Python</button><br/>
<button id="heavy-stuff-btn" onClick="doHeavyStuff()">Perform a heavy operation</button><br/>
<button onClick="getRandomNumber()">Get a random number</button><br/>
<label for="name_input">Say hello to:</label><input id="name_input" placeholder="put a name here">
<button onClick="greet()">Greet</button><br/>

<div id="response-container"></div>
<script>
function showResponse(response) {
    var container = document.getElementById('response-container')

    container.innerText = response.message
    container.style.display = 'block'
}

function initialize() {
    pywebview.api.init().then(showResponse)
}

function doHeavyStuff() {
    var btn = document.getElementById('heavy-stuff-btn')

    pywebview.api.doHeavyStuff().then(function(response) {
        showResponse(response)
        btn.onclick = doHeavyStuff
        btn.innerText = 'Perform a heavy operation'
    })

    showResponse({message: 'Working...'})
    btn.innerText = 'Cancel the heavy operation'
    btn.onclick = cancelHeavyStuff
}

function cancelHeavyStuff() {
    pywebview.api.cancelHeavyStuff()
}

function getRandomNumber() {
    pywebview.api.getRandomNumber().then(showResponse)
}

function greet() {
    var name_input = document.getElementById('name_input').value;
    pywebview.api.sayHelloTo(name_input).then(showResponse)
}

</script>
</body>
</html>
"""


class Api:
    def __init__(self):
        self.cancel_heavy_stuff_flag = False

    def init(self, params):
        response = {
            'message': 'Hello from Python {0}'.format(sys.version)
        }
        return response

    def getRandomNumber(self, params):
        response = {
            'message': 'Here is a random number courtesy of randint: {0}'.format(random.randint(0, 100000000))
        }
        return response

    def doHeavyStuff(self, params):
        time.sleep(0.1)  # sleep to prevent from the ui thread from freezing for a moment
        now = time.time()
        self.cancel_heavy_stuff_flag = False
        for i in range(0, 1000000):
            _ = i * random.randint(0, 1000)
            if self.cancel_heavy_stuff_flag:
                response = {'message': 'Operation cancelled'}
                break
        else:
            then = time.time()
            response = {
                'message': 'Operation took {0:.1f} seconds on the thread {1}'.format((then - now), threading.current_thread())
            }
        return response

    def cancelHeavyStuff(self, params):
        time.sleep(0.1)
        self.cancel_heavy_stuff_flag = True

    def sayHelloTo(self, params):
        response = {
            'message': 'Hello {0}!'.format(params)
        }
        return response


def create_app():
    webview.load_html(html)


if __name__ == '__main__':
    t = threading.Thread(target=create_app)
    t.start()

    api = Api()
    webview.create_window('API example', js_api=api)
```