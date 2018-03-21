src = """
(function() {
    var css = document.createElement("style");
    css.type = "text/css";
    css.innerHTML = "%s";
    document.head.appendChild(css);
})()
"""

disable_text_select = src % 'body {-webkit-user-select: none; -khtml-user-select: none; -ms-user-select: none; user-select: none; cursor: default;}'