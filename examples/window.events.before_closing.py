import webview

def on_closing():
    # The on_closing event is executed when the window attempts to close, even if before_closing is running
    if (not window.before_closing_active): # This filter prevents that from happening
        print("on_closing")

def before_closing_function(arg1, arg2):
    print("before closing", arg1, arg2)

    result = window.evaluate_js('confirm("Are you very sure you want to close the window?");')
    
    if result:
        # If user confirms, show final message and close
        window.evaluate_js("""document.body.innerHTML += "Don't leave :("; alert("The window will now close");""")
    else:
        return False # Cancel closing the window

if __name__ == "__main__":
    window = webview.create_window("Mi App", html="<html><head><body></body></head></html>")
    
    window.events.closing += on_closing
    window.events.before_closing = lambda: before_closing_function("value1", "value2") # It is necessary to use "=" (No "+="). "lambda:" it is necessary if arguments are passed, otherwise use "= before_closing_function"
    
    webview.start()