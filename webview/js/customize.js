
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
        var snapOnDrag = '%(snap_on_drag)s' === 'True';
        var snapPreview = snapOnDrag && '%(snap_preview)s' === 'True';
        var lastZone = null;

        function onMouseMove(ev) {
            var x = ev.screenX - initialX;
            var y = ev.screenY - initialY;
            window.pywebview._jsApiCallback('pywebviewMoveWindow', [x, y], 'move');

            if (snapPreview) {
                var zone = snapZoneAt(ev.screenX, ev.screenY);
                if (zone !== lastZone) {
                    lastZone = zone;
                    reportZone(zone);
                }
            }
        }

        // The work area (screen minus taskbar/dock) of the screen the cursor is on. Chromium reports
        // it per screen through avail*, which is exactly what the snap zones are relative to.
        function workArea() {
            var s = window.screen;
            var left = typeof s.availLeft === 'number' ? s.availLeft : 0;
            var top = typeof s.availTop === 'number' ? s.availTop : 0;
            return { l: left, t: top, w: s.availWidth || s.width, h: s.availHeight || s.height };
        }

        // Python turns the zone plus work area into a rectangle: the preview overlay while dragging,
        // and the window geometry on release.
        function reportZone(zone) {
            var a = workArea();
            window.pywebview._jsApiCallback(
                'pywebviewSnapPreview', [zone, {l: a.l, t: a.t, w: a.w, h: a.h}], 'snapPreview'
            );
        }

        function snapZoneAt(x, y) {
            var a = workArea();
            var trigger = Number('%(snap_trigger)s');
            var left = x <= a.l + trigger;
            var right = x >= a.l + a.w - 1 - trigger;
            var top = y <= a.t + trigger;
            var bottom = y >= a.t + a.h - 1 - trigger;

            if (top && left) return 'tl';
            if (top && right) return 'tr';
            if (bottom && left) return 'bl';
            if (bottom && right) return 'br';
            if (top) return 'max';
            if (left) return 'left';
            if (right) return 'right';
            return null;
        }

        function onMouseUp(ev) {
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);

            if (!snapOnDrag || !ev || typeof ev.screenX !== 'number') {
                return;
            }

            var zone = snapZoneAt(ev.screenX, ev.screenY);
            if (zone) {
                var a = workArea();
                window.pywebview._jsApiCallback(
                    'pywebviewSnapWindow', [zone, {l: a.l, t: a.t, w: a.w, h: a.h}], 'snap'
                );
            }
            if (snapPreview) {
                lastZone = null;
                reportZone(null);
            }
        }

        function onMouseDown(ev) {
            if (
                '%(drag_region_direct_target_only)s' === 'True' &&
                !ev.target.matches('%(drag_selector)s')
            ) {
                return
            }

            // With snapping enabled the drag has to stay in JS: the native move loop started by
            // pywebviewStartDrag swallows the mouse, so the page would never see the mouseup that
            // decides the snap zone (and on Windows that loop does not snap by itself either).
            if (!snapOnDrag && (platform === 'edgechromium' || platform === 'winui3')) {
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

    disableTouchEvents();
  })();
