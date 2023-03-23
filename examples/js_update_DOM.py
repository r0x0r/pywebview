import webview

"""
In this updated template, the update function in the HTML document takes a value parameter that will be used to update the innerHTML of the content element.
"""

# Define the HTML content
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>PyWebview DOM Update Example</title>
</head>
<body>
    <h1>Original content</h1>
    <p id="content">This is the original content of the paragraph.</p>
    <button onclick="update('')">Update content</button>

    <script>
        function update(value) {
            // Get the DOM element by ID
            var element = document.getElementById('content');

            // Update the innerHTML of the element with the passed in value
            element.innerHTML = value;
        }
    </script>
</body>
</html>
"""

# Function to update the DOM element
def update_element():
    new_value = "new_value"
    # Call the Javascript function to update the DOM element
    window.evaluate_js(f"update('{new_value}')")
# Create the PyWebview window
window = webview.create_window("PyWebview DOM Update Example", html=html_content)

# Example usage of update_element function


# Run the PyWebview event loop
webview.start(update_element)

