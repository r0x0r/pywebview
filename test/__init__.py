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

import subprocess

from . import app

has_ui = True

def init():
    app.init()
    
def main_loop():
    pass

# http://stackoverflow.com/questions/480866/get-the-title-of-the-current-active-window-document-in-mac-os-x
# seems to work fine with safari, chrome and firefox.
def browser_has_focus():
    try:
        title = subprocess.check_output(["osascript", "-e",
"""
tell application "System Events"
set frontApp to name of first application process whose frontmost is true
end tell
tell application frontApp
if the (count of windows) is not 0 then
    set window_name to name of front window
end if
end tell
"""
        ])
    except subprocess.CalledProcessError:
        return False
    #print title
    if "ownload.am" in title:
        return True
    else:
        return False
