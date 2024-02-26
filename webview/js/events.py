
src = """

(function() {
    var initialX = 0;
    var initialY = 0;

    function onMouseMove(ev) {
        var x = ev.screenX - initialX;
        var y = ev.screenY - initialY;
        window.pywebview._bridge.call('pywebviewMoveWindow', [x, y], 'move');
    }

    function onMouseUp() {
        window.removeEventListener('mousemove', onMouseMove);
        window.removeEventListener('mouseup', onMouseUp);
    }

    function onMouseDown(ev) {
        initialX = ev.clientX;
        initialY = ev.clientY;
        window.addEventListener('mouseup', onMouseUp);
        window.addEventListener('mousemove', onMouseMove);
    }

    var dragBlocks = document.querySelectorAll('%(drag_selector)s');
    for (var i=0; i < dragBlocks.length; i++) {
        dragBlocks[i].addEventListener('mousedown', onMouseDown);
    }
        // easy drag for edge chromium
    if (%(easy_drag)s) {
        window.addEventListener('mousedown', onMouseDown);
    }

})();

// zoomable
if (!%(zoomable)s) {
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
if (!%(draggable)s) {
    document.querySelectorAll("img").forEach(function(img) {
        img.setAttribute("draggable", false);
    })

    document.querySelectorAll("a").forEach(function(a) {
        a.setAttribute("draggable", false);
    })
}

"""
