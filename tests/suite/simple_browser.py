import unittest
import threading
import webview

#from '../cocoa_util' import mousemove

class DestroyWindowTestCase(unittest.TestCase):
    def setUp(self):
        def stop():
            import time
            time.sleep(10)
            print ('destrory')
            webview.destroy_window()

        t = threading.Thread(target=lambda: webview.destroy_window())
        t.start()
        print ('start')


class TestSimpleBrowser(DestroyWindowTestCase):
    def runTest(self):
        try:
            webview.create_window('Simple browser', 'https://www.google.com')
        except Exception as e:
            self.fail('Exception occured: \n{0}'.format(e))

def run():
    print ("w00t")
    unittest.main()

if __name__ == '__main__':
    run()
