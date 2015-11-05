# -*- coding: utf-8 -*-
"""Copyright (C) 2013 COLDWELL AG

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

import webbrowser
#from gevent.lock import Semaphore
from AppKit import NSObject


current = None

class CocoaInput():
    def sethtml(self, html):
        pass
        #app.browserwindow.sethtml(html, self.address, True)
        
    def hide(self):
        pass
        #app.browserwindow.hide()

class BrowserDelegate(NSObject):
    def windowShouldClose_(self, noti):
        print "close event", current, current.input.close_aborts
        ret = None
        """
        if current.input.close_aborts:
            ret = app.browserwindow.javascript("return closing_window();")
        if not ret:
            app.browserwindow.hide()
        if current:
            current.close()
        """
        return False
        
    def webView_runJavaScriptAlertPanelWithMessage_initiatedByFrame_(self, webview, message, frame):
        # dirty message passing over alert()
        cmd, arg = message.split(" ", 1)
        if cmd == "tab":
            webbrowser.open_new_tab(arg)
        else:
            print "unknown cmd/arg", cmd, arg

lock = None # Semaphore()

#@event.register('input:done')
def _(*_):
    if current:
        current.close()
    #else:
    #    app.browserwindow.hide()

#@event.register('input:uirequest')
def input(e, input):
    global current
    #if ui.browser_has_focus():
    #    return
    with lock:
        l = CocoaInput(input)
        current = l
        l.greenserver.join()
        """
        if l.end == 'OK':
            interface.call('input', 'answer', id=input.id, answer=l.serialized)
        elif l.end == 'CANCEL':
            interface.call('input', 'abort', id=input.id)
        """

