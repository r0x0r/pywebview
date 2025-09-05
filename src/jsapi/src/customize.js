
export function initCustomizations() {
    const platform = window.pywebview.platform;
    const disableText = '%(text_select)s' === 'False';
    const disableTextCss = 'body {-webkit-user-select: none; -khtml-user-select: none; -ms-user-select: none; user-select: none; cursor: default;}';

    if (platform == 'mshtml') {
        window.alert = (msg) => {
            window.external.alert(msg);
        };
    } else if (platform == 'edgechromium') {
        window.alert = (message) => {
            window.chrome.webview.postMessage(['_pywebviewAlert', pywebview.stringify(message), 'alert']);
        };
    } else if (platform == 'gtkwebkit2') {
        window.alert = (message) => {
            window.webkit.messageHandlers.jsBridge.postMessage(pywebview.stringify({funcName: '_pywebviewAlert', params: message, id: 'alert'}));
        };
    } else if (platform == 'cocoa') {
        window.print = () => {
            window.webkit.messageHandlers.browserDelegate.postMessage('print');
        };
    } else if (platform === 'qtwebengine') {
        window.alert = (message) => {
            window.pywebview._QWebChannel.objects.external.call('_pywebviewAlert', pywebview.stringify(message), 'alert');
        };
    } else if (platform === 'qtwebkit') {
        window.alert = (message) => {
            window.external.invoke(JSON.stringify(['_pywebviewAlert', message, 'alert']));
        };
    }

    if (disableText) {
        const css = document.createElement("style");
        css.type = "text/css";
        css.innerHTML = disableTextCss;
        document.head.appendChild(css);
    }

    const disableTouchEvents = () => {
        let initialX = 0;
        let initialY = 0;

        const onMouseMove = (ev) => {
            const x = ev.screenX - initialX;
            const y = ev.screenY - initialY;
            window.pywebview._jsApiCallback('pywebviewMoveWindow', [x, y], 'move');
        };

        const onMouseUp = () => {
            window.removeEventListener('mousemove', onMouseMove);
            window.removeEventListener('mouseup', onMouseUp);
        };

        const onMouseDown = (ev) => {
            if (
                '%(drag_region_direct_target_only)s' === 'True' &&
                !ev.target.matches('%(drag_selector)s')
            ) {
                return;
            }

            initialX = ev.clientX;
            initialY = ev.clientY;
            window.addEventListener('mouseup', onMouseUp);
            window.addEventListener('mousemove', onMouseMove);
        };

        const onBodyMouseDown = (event) => {
            let target = event.target;
            const dragSelectorElements = document.querySelectorAll('%(drag_selector)s');

            while (target && target !== document.body && target !== document.documentElement) {
                if (target.nodeType === 1) {
                    // Check if target matches the drag selector
                    for (let i = 0; i < dragSelectorElements.length; i++) {
                        if (dragSelectorElements[i] === target) {
                            onMouseDown(event);
                            return;
                        }
                    }
                }

                // If it doesn't match, continue up the DOM tree
                target = target.parentNode;
            }
        };

        document.body.addEventListener('mousedown', onBodyMouseDown);

        // easy drag for edge chromium
        if ('%(easy_drag)s' === 'True') {
            window.addEventListener('mousedown', onMouseDown);
        }

        if ('%(zoomable)s' === 'False') {
            document.body.addEventListener('touchstart', (e) => {
                if ((e.touches.length > 1) || e.targetTouches.length > 1) {
                    e.preventDefault();
                    e.stopPropagation();
                    e.stopImmediatePropagation();
                }
            }, {passive: false});

            window.addEventListener('wheel', (e) => {
                if (e.ctrlKey) {
                    e.preventDefault();
                }
            }, {passive: false});
        }

        // draggable
        if ('%(draggable)s' === 'False') {
            document.addEventListener('dragstart', (e) => {
                if (e.target.tagName === 'IMG' || e.target.tagName === 'A') {
                    e.preventDefault();
                }
            });
        }
    };

    disableTouchEvents();
};

