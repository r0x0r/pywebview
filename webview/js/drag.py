src = """
(function() {
    var initialX = 0;
    var initialY = 0;

    function onMouseMove(ev) {
        var x = ev.screenX - initialX;
        var y = ev.screenY - initialY;
        window.pywebview._bridge.call('moveWindow', [x, y], 'move');
    }

    function onMouseUp() {
        window.removeEventListener('mousemove', onMouseMove);
    }

    function onMouseDown(ev) {
        initialX = ev.clientX;
        initialY = ev.clientY;
        window.addEventListener('mouseup', onMouseUp);
        window.addEventListener('mousemove', onMouseMove);
    }

    var dragBlocks = document.querySelectorAll('%s');
    for(var i=0; i < dragBlocks.length; i++) {
        dragBlocks[i].addEventListener('mousedown', onMouseDown);
    }
})();
"""
