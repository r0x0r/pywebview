
(function() {
    var platform = window.pywebview.platform;
    var disableText = '%(text_select)s' === 'False';
    var disableTextCss = 'body {-webkit-user-select: none; -khtml-user-select: none; -ms-user-select: none; user-select: none; cursor: default;}'

    if (platform == 'mshtml') {
        window.alert = function(msg) {
            window.external.alert(msg);
        }
    } else if (platform == 'edgechromium') {
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
            window.pywebview._QWebChannel.objects.external.call('_pywebviewAlert', pywebview.stringify(message), 'alert');
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

        // Extract coordinates from mouse or touch event
        function getEventCoords(ev) {
            if (ev.type.startsWith('touch')) {
                var touch = ev.touches[0] || ev.changedTouches[0];
                return {
                    clientX: touch.clientX,
                    clientY: touch.clientY,
                    screenX: touch.screenX,
                    screenY: touch.screenY
                };
            }
            return {
                clientX: ev.clientX,
                clientY: ev.clientY,
                screenX: ev.screenX,
                screenY: ev.screenY
            };
        }

        function onMove(ev) {
            var coords = getEventCoords(ev);
            var x = coords.screenX - initialX;
            var y = coords.screenY - initialY;
            window.pywebview._jsApiCallback('pywebviewMoveWindow', [x, y], 'move');

            if (ev.type.startsWith('touch')) {
                ev.preventDefault();
            }
        }

        function onEnd() {
            window.removeEventListener('mousemove', onMove);
            window.removeEventListener('mouseup', onEnd);
            window.removeEventListener('touchmove', onMove);
            window.removeEventListener('touchend', onEnd);
        }

        function onStart(ev) {
            if (
                '%(drag_region_direct_target_only)s' === 'True' &&
                !ev.target.matches('%(drag_selector)s')
            ) {
                return
            }

            // Only handle single-touch events
            if (ev.type.startsWith('touch') && ev.touches.length !== 1) {
                return;
            }

            var coords = getEventCoords(ev);
            initialX = coords.clientX;
            initialY = coords.clientY;

            window.addEventListener('mouseup', onEnd);
            window.addEventListener('mousemove', onMove);
            window.addEventListener('touchend', onEnd);
            window.addEventListener('touchmove', onMove, {passive: false});
        }

        // Unified body handler for drag selector
        function onBodyStart(event) {
            var target = event.target;
            var dragSelectorElements = document.querySelectorAll('%(drag_selector)s');

            while (target && target !== document.body && target !== document.documentElement) {
                if (target.nodeType === 1) {
                    // Check if target matches the drag selector
                    for (var i = 0; i < dragSelectorElements.length; i++) {
                        if (dragSelectorElements[i] === target) {
                            onStart(event);
                            return;
                        }
                    }
                }

                // If it doesn't match, continue up the DOM tree
                target = target.parentNode;
            }
        }

        document.body.addEventListener('mousedown', onBodyStart);
        document.body.addEventListener('touchstart', onBodyStart);

        // easy drag for edge chromium
        if ('%(easy_drag)s' === 'True') {
            window.addEventListener('mousedown', onStart);
            window.addEventListener('touchstart', onStart);
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
