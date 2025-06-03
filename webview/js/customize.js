
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

    // store mouse state for moving and resizing
    var mouseState = {
        isResizing: false,
        isMoving: false,
        resizingDirection: "",
        initialX: 0,
        initialY: 0,
        initialWidth: 0,
        initialHeight: 0
    }

    // easy drag for edge chromium
    var easyDrag = '%(easy_drag)s' === 'True';
    var easyResize = '%(easy_resize)s' === 'True';

    // calculate possible resizing direction
    function possibleResizingDirection(ev) {
        var resizeRegionSize = 5;
        var nearLeft = ev.clientX < resizeRegionSize;
        var nearRight = window.innerWidth - ev.clientX < resizeRegionSize;
        var nearTop = ev.clientY < resizeRegionSize;
        var nearBottom = window.innerHeight - ev.clientY < resizeRegionSize;

        if (nearLeft && nearTop)
            return 'nw';
        if (nearLeft && nearBottom)
            return 'sw';
        if (nearRight && nearTop)
            return 'ne';
        if (nearRight && nearBottom)
            return 'se';
        if (nearLeft)
            return 'w';
        if (nearRight)
            return 'e';
        if (nearTop)
            return 'n';
        if (nearBottom)
            return 's';
        return '';
    }

    // override cursor style to indicate resizable region
    function overrideCursorStyle(direction) {
        var cursorStyle = document.getElementById('cursor-style');
        if (direction === "") {
            if (cursorStyle !== null) {
                cursorStyle.remove();
            }
        } else {
            if (cursorStyle === null) {
                cursorStyle = document.createElement('style');
                cursorStyle.id = 'cursor-style';
                document.head.appendChild(cursorStyle);
            }
            cursorStyle.innerHTML = '*{cursor: ' + direction + '-resize !important;}';
        }
    }

    function onMouseMove(ev) {
        // handle resizing
        if (easyResize && mouseState.isResizing) {
            var w = mouseState.initialWidth;
            var h = mouseState.initialHeight;
            var fixPoint = 0;

            switch (mouseState.resizingDirection) {
                case "nw":
                    w += mouseState.initialX - ev.screenX;
                    h += mouseState.initialY - ev.screenY;
                    fixPoint = 12;
                    break
                case "sw":
                    w += mouseState.initialX - ev.screenX;
                    h += ev.screenY - mouseState.initialY;
                    fixPoint = 5;
                    break
                case "ne":
                    w += ev.screenX - mouseState.initialX;
                    h += mouseState.initialY - ev.screenY;
                    fixPoint = 10;
                    break
                case "se":
                    w += ev.screenX - mouseState.initialX;
                    h += ev.screenY - mouseState.initialY;
                    fixPoint = 3;
                    break
                case "w":
                    w += mouseState.initialX - ev.screenX;
                    fixPoint = 13;
                    break
                case "e":
                    w += ev.screenX - mouseState.initialX;
                    fixPoint = 11;
                    break
                case "n":
                    h += mouseState.initialY - ev.screenY;
                    fixPoint = 14;
                    break
                case "s":
                    h += ev.screenY - mouseState.initialY;
                    fixPoint = 7;
                    break
            }

            window.pywebview._jsApiCallback('pywebviewResizeWindow', [w, h, fixPoint], 'resize');
        }

        // handle moving
        if (mouseState.isMoving) {
            window.pywebview._jsApiCallback('pywebviewMoveWindow', [ev.screenX - mouseState.initialX, ev.screenY - mouseState.initialY], 'move');
        }

        // change cursor style to indicate resizable region
        if (easyResize && !(mouseState.isResizing || mouseState.isMoving)) {
            overrideCursorStyle(possibleResizingDirection(ev))
        }
    }

    // reset resizing and moving state
    function onMouseUp() {
        mouseState.isResizing = false;
        mouseState.isMoving = false;
        window.removeEventListener('mouseup', onMouseUp);
    }

    function startMovingWindow(ev) {
        mouseState.isMoving = true;
        mouseState.initialX = ev.clientX;
        mouseState.initialY = ev.clientY;
        window.addEventListener('mouseup', onMouseUp);
    }

    function startResizingWindow(ev, direction) {
        mouseState.isResizing = true;
        mouseState.resizingDirection = direction;
        mouseState.initialX = ev.screenX;
        mouseState.initialY = ev.screenY;
        mouseState.initialWidth = window.innerWidth;
        mouseState.initialHeight = window.innerHeight;
        overrideCursorStyle(direction);
        window.addEventListener('mouseup', onMouseUp);
    }

    function onMouseDown(ev) {
        if (easyResize) {
            var direction = possibleResizingDirection(ev);
            if (direction !== "") {
                startResizingWindow(ev, direction);
                return;
            }
        }

        if (easyDrag) {
            startMovingWindow(ev);
        }
    }

    var dragBlocks = document.querySelectorAll('%(drag_selector)s');
    for (var i=0; i < dragBlocks.length; i++) {
        dragBlocks[i].addEventListener('mousedown', startMovingWindow);
    }

    // listen mousedown event for trigger moving and resizing
    if (easyDrag || easyResize) {
        window.addEventListener('mousedown', onMouseDown);
    }

    // listen mousemove event for moving and resizing
    window.addEventListener('mousemove', onMouseMove);

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
        Array.prototype.slice.call(document.querySelectorAll("img")).forEach(function(img) {
            img.setAttribute("draggable", false);
        })

        Array.prototype.slice.call(document.querySelectorAll("a")).forEach(function(a) {
            a.setAttribute("draggable", false);
        })
    }
})();

