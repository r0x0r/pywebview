
(function() {
    var platform = window.pywebview.platform;
    var disableText = '%(text_select)s' === 'False';
    var disableTextCss = 'body {-webkit-user-select: none; -khtml-user-select: none; -ms-user-select: none; user-select: none; cursor: default;}'

    if (platform == 'mshtml') {
        window.alert = function(msg) {
            window.external.alert(msg);
        }
    } else if (platform == 'edgechromium' || platform == 'winui3') {
        window.alert = function (message) {
            window.chrome.webview.postMessage(['_pywebviewAlert', pywebview.stringify(message), 'alert']);
        }
    } else if (platform == 'gtkwebkit2') {
        window.alert = function (message) {
            window.webkit.messageHandlers.jsBridge.postMessage(pywebview.stringify({funcName: '_pywebviewAlert', params: message, id: 'alert'}));
        }
    } else if (platform == 'cocoa') {
        window.print = function() {
            window.webkit.messageHandlers.browserDelegate.postMessage('print');
        }
    } else if (platform === 'qtwebengine') {
        window.alert = function (message) {
            window.pywebview._QWebChannel.objects.external.call('_pywebviewAlert', pywebview.stringify(message), 'alert', window.pywebview.token);
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
            window.pywebview._jsApiCallback('pywebviewMoveWindow', [x, y], 'move');
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
                window.pywebview._jsApiCallback('pywebviewStartDrag', [], 'drag');
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

    function setupResizeHandles() {
        if ('%(resize_handles)s' !== 'True') {
            return;
        }

        // A frameless window cannot hit-test its own edges: the points over the page
        // reach the webview child window first. Transparent strips along the viewport
        // edges ask the backend to start the native sizing loop instead, and carry the
        // resize cursor with them.
        var handles = [
            { code: 10, cursor: 'ew-resize', css: 'left:0;top:8px;bottom:8px;width:8px' },
            { code: 11, cursor: 'ew-resize', css: 'right:0;top:8px;bottom:8px;width:8px' },
            { code: 12, cursor: 'ns-resize', css: 'top:0;left:8px;right:8px;height:8px' },
            { code: 15, cursor: 'ns-resize', css: 'bottom:0;left:8px;right:8px;height:8px' },
            { code: 13, cursor: 'nwse-resize', css: 'top:0;left:0;width:8px;height:8px' },
            { code: 14, cursor: 'nesw-resize', css: 'top:0;right:0;width:8px;height:8px' },
            { code: 16, cursor: 'nesw-resize', css: 'bottom:0;left:0;width:8px;height:8px' },
            { code: 17, cursor: 'nwse-resize', css: 'bottom:0;right:0;width:8px;height:8px' }
        ];

        handles.forEach(function (handle) {
            var element = document.createElement('div');
            element.style.cssText = 'position:fixed;z-index:2147483647;'
                + handle.css + ';cursor:' + handle.cursor;

            element.addEventListener('mousedown', function (event) {
                if (event.button !== 0) {
                    return;
                }
                event.preventDefault();

                // A drag region that reaches the window edge would otherwise be
                // resized rather than moved from its first few pixels.
                var underneath = document.elementsFromPoint(event.clientX, event.clientY);
                for (var i = 0; i < underneath.length; i++) {
                    var candidate = underneath[i];
                    if (candidate === element || !candidate.closest) {
                        continue;
                    }
                    if (candidate.closest('%(drag_selector)s')) {
                        window.pywebview._jsApiCallback('pywebviewStartDrag', [], 'drag');
                        return;
                    }
                }

                window.pywebview._jsApiCallback('pywebviewStartResize', [handle.code], 'resize');
            });

            document.body.appendChild(element);
        });
    }

    disableTouchEvents();
    setupResizeHandles();
  })();
