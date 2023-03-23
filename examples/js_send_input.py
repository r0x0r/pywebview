import webview

# Define the HTML content
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>PyWebview Input Value Example</title>
</head>
<body>
    <h1>Enter a value:</h1>
    <input type="text" id="inputValue">
    <button onclick="sendValue()">Send Value</button>

    <script>
        function sendValue() {
            // Get the input element by ID
            var element = document.getElementById('inputValue');
            var value = element.value;

            // Call the PyWebview function to send the value to Python
            window.pywebview.api.send_value(value);
        }
    </script>
</body>
</html>
"""

# Create the PyWebview window

# Function to receive input value from HTML and Javascript
class InputValueReceiver:
    def send_value(self, value):
        # Call a Python function to handle the input value
        handle_input_value(value)
api = InputValueReceiver()
window = webview.create_window("PyWebview Input Value Example", html=html_content, js_api=api)


def handle_input_value(value):
    # Print the input value to the console
    print(f"Received input value: {value}")

# Run the PyWebview event loop
webview.start(debug=True)
