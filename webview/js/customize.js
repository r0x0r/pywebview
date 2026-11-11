
(function() {
    // Pages without the JS API get this script alone, with a sender that needs no token
    var pywebview = '%(ui_only)s' === 'True' ? {
        platform: '%(platform)s',
        _jsApiCallback: function (funcName, params, id) {
            var message = JSON.stringify(params);
            switch (this.platform) {
                case 'edgechromium':
                case 'winui3':
                    return window.chrome.webview.postMessage([funcName, message, id, '']);
                case 'cocoa':
                case 'gtkwebkit2':
                    return window.webkit.messageHandlers.jsBridge.postMessage(
                        JSON.stringify({funcName: funcName, params: params, id: id, token: ''})
                    );
                case 'qtwebengine':
                    if (window.qt && typeof QWebChannel !== 'undefined') {
                        new QWebChannel(qt.webChannelTransport, function (channel) {
                            channel.objects.external.call(funcName, message, id, '');
                        });
                    }
                    return;
                case 'cef':
                case 'qtwebkit':
                case 'android-webkit':
                    return window.external.call(funcName, message, id, '');
            }
        }
    } : window.pywebview;
    var platform = pywebview.platform;
    var disableText = '%(text_select)s' === 'False';
    var disableTextCss = 'body {-webkit-user-select: none; -khtml-user-select: none; -ms-user-select: none; user-select: none; cursor: default;}'

    if (platform == 'edgechromium' || platform == 'winui3' || platform == 'gtkwebkit2' || platform === 'qtwebengine') {
        window.alert = function (message) {
            var text = arguments.length ? message : '';
            pywebview._jsApiCallback('_pywebviewAlert', text == null ? String(text) : text, 'alert');
        }
    } else if (platform == 'cocoa') {
        window.print = function() {
            window.webkit.messageHandlers.browserDelegate.postMessage('print');
        }
    } else if (platform === 'qtwebkit') {
        window.alert = function (message) {
            window.external.invoke(JSON.stringify(['_pywebviewAlert', message, 'alert']));
        }
    }

    if (disableText) {
        var css = document.createElement("style");
        css.type = "text/css";
        css.innerHTML = disableTextCss;
        document.head.appendChild(css);
    }

    function disableTouchEvents() {
        var initialX = 0;
        var initialY = 0;

        function onMouseMove(ev) {
            var x = ev.screenX - initialX;
            var y = ev.screenY - initialY;
            pywebview._jsApiCallback('pywebviewMoveWindow', [x, y], 'move');
        }

        function onMouseUp() {
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);
        }

        function onMouseDown(ev) {
            if (
                '%(drag_region_direct_target_only)s' === 'True' &&
                !ev.target.matches('%(drag_selector)s')
            ) {
                return
            }

            if (platform === 'edgechromium' || platform === 'winui3') {
                pywebview._jsApiCallback('pywebviewStartDrag', [], 'drag');
                return;
            }

            initialX = ev.clientX;
            initialY = ev.clientY;
            window.addEventListener('mouseup', onMouseUp);
            window.addEventListener('mousemove', onMouseMove);
        }

        function onBodyMouseDown(event) {
            var target = event.target;
            var dragSelectorElements = document.querySelectorAll('%(drag_selector)s');

            while (target && target !== document.body && target !== document.documentElement) {
                if (target.nodeType === 1) {
                    // Check if target matches the drag selector
                    for (var i = 0; i < dragSelectorElements.length; i++) {
                        if (dragSelectorElements[i] === target) {
                            onMouseDown(event);
                            return;
                        }
                    }
                }

                // If it doesn't match, continue up the DOM tree
                target = target.parentNode;
            }
        }

        document.body.addEventListener('mousedown', onBodyMouseDown);

            // easy drag for edge chromium
        if ('%(easy_drag)s' === 'True') {
            window.addEventListener('mousedown', onMouseDown);
        }

        if ('%(zoomable)s' === 'False') {
            document.body.addEventListener('touchstart', function(e) {
                if ((e.touches.length > 1) || e.targetTouches.length > 1) {
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                }
            }, {passive: false});

            window.addEventListener('wheel', function (e) {
                if (e.ctrlKey) {
                    e.preventDefault();
                }
            }, {passive: false});
        }

        // draggable
        if ('%(draggable)s' === 'False') {
            document.addEventListener('dragstart', function(e) {
                if (e.target.tagName === 'IMG' || e.target.tagName === 'A') {
                    e.preventDefault();
                }
            });
        }
    }

    disableTouchEvents();
  })();
