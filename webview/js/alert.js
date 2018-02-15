// Custom alert box without the URL in the title bar for Windows

window.alert = function(message) {
    window.external.alert(message);
}
