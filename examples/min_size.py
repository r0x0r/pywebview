import webview

"""
This example demonstrates how to create a webview window with a custom minimum
size.
"""

if __name__ == '__main__':
    # Create a resizable webview window with minimum size constraints
    webview.create_window("Minimum window size",
                          "http://www.flowrl.com",
                          width=800, height=600,
                          resizable=True,
                          min_size=(400, 200))
