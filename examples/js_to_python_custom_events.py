"""pywebview custom events example"""

import webview

def on_custom_event_1(e=None, Text=None):
    print(f"Python event 1 triggered from JS, data: {e['dataText']}, Text: {Text}")
    return False

def on_custom_event_2(e=None, Text=None):
    print(f"Python event 2 triggered from JS, data: {e['dataText']}, Text: {Text}")


if __name__ == '__main__':
    window = webview.create_window(
        'JavaScript to Python Events',
        html="""<!DOCTYPE html>
        <html>
        <body>
            <button onclick="testDispatch('custom_event_1')">custom_event_1</button>
            <button onclick="testDispatch('custom_event_2')">custom_event_2</button>
            
            <div id="output" style="background: #f0f0f0; padding: 10px; margin: 10px 0; min-height: 100px;"></div>
            
            <script>
                function log(message) {
                    document.getElementById('output').innerHTML += message + '<br>';
                    console.log(message);
                }
                
                function testDispatch(eventName) {
                    log(`${eventName}:`);
                    pywebview.dispatch_custom_event(eventName, { "dataText": "Hello from JS!" }, "optional additional parameter")
                        .then(result => {
                            log('Result: ' + JSON.stringify(result));
                        })
                        .catch(error => {
                            log('Error: ' + error);
                        });
                }
            </script>
        </body>
        </html>
        """
    )
    
    window.events.custom_event_1 += on_custom_event_1
    window.events.custom_event_2 += on_custom_event_2

    webview.start()