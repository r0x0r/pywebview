"""
    Custom alert box without the URL in the title bar for Windows
"""

src = """
window.alert = function(message) {
    window.external.alert(message);
};

"""
