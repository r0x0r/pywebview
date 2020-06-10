import webview

'''
This example demonstrates a user-provided "drag region" to move a frameless window
around, whilst maintaining normal mouse down/move events elsewhere. This roughly
replicates `-webkit-drag-region`.
'''

html = '''
<head>
    <style type="text/css">
        .pywebview-drag-region {
            width: 50px;
            height: 50px;
            margin-top: 50px;
            margin-left: 50px;
            background: orange;
        }
    </style>
</head>
<body>
    <div class="pywebview-drag-region">Drag me!</div>
</body>
'''


if __name__ == '__main__':
    window = webview.create_window(
        'API example',
        html=html,
        frameless=True,
        easy_drag=False,
    )
    webview.start(debug=True)
