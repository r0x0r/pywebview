from cefpython3 import cefpython as cef

browser = None

def init():
    settings = {'multi_threaded_message_loop': True}
    cef.Initialize(settings=settings)


def create_browser(handle, url=None):
    def _create():
        global browser
        browser = cef.CreateBrowserSync(window_info=window_info,  url=url)

    window_info = cef.WindowInfo()
    window_info.SetAsChild(handle)
    cef.PostTask(cef.TID_UI, _create)
