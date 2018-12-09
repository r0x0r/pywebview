

import clr

clr.AddReference('System.Windows.Forms')
clr.AddReference('System.Threading')

import System.Windows.Forms as WinForms
from System import IntPtr, Int32, Func, Type, Environment, EventHandler
from System.Threading import Thread, ThreadStart, ApartmentState
from System.Drawing import Size, Point, Icon, Color, ColorTranslator, SizeF


from cefpython3 import cefpython as cef


class BrowserForm(WinForms.Form):
    def __init__(self):
        self.Text = "Test"
        self.ClientSize = Size(800, 600)

        #self.Shown += self.on_shown
        cef.PostTask(cef.TID_UI, self.create_cef)

    def create_cef(self):
        self.window_info = cef.WindowInfo()
        self.window_info.SetAsChild(self.Handle.ToInt32())
        self.cef_browser = cef.CreateBrowserSync(window_info=self.window_info,
                                                 url='https://pywebview.flowrl.com/hello')

    def on_shown(self, sender, args):
        cef.PostTask(cef.TID_UI, self.create_cef)


def create_window():
    def create():
        window = BrowserForm()
        window.Show()

        app = WinForms.Application
        app.Run()

    settings = {
        "multi_threaded_message_loop": True,
    }
    cef.Initialize(settings=settings)
    thread = Thread(ThreadStart(create))
    thread.SetApartmentState(ApartmentState.STA)
    thread.Start()
    thread.Join()


if __name__ == '__main__':
    create_window()