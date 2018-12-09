
src = """
window.pywebview._checkEvalResult = function(uid) {
    var interval = setInterval(function () {
        if (pywebview._evalResults.hasOwnProperty(uid)) {
            try {
                var result = pywebview._evalResults[uid];
                window.external.return_result(result, uid);
                delete result;
                clearInterval(interval);
            } catch (err) {
                clearInterval(interval);
                alert(err);
            }
        }
    }, 100)
}
"""