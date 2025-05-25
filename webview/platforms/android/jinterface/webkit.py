from jnius import PythonJavaClass, java_method


class ValueCallback(PythonJavaClass):
    __javacontext__ = 'app'
    __javainterfaces__ = ['android/webkit/ValueCallback']

    def __init__(self, on_receive_value):
        self.on_receive_value = on_receive_value

    @java_method('(Ljava/lang/Object;)V')
    def onReceiveValue(self, value):
        self.on_receive_value(value)
