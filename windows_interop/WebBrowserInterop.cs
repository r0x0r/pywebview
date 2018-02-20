using System;
using System.Runtime.InteropServices;
using System.Windows.Forms;


namespace WebBrowserInterop
{
    public interface IWebBrowserInterop
    {
        object call(string message, object param);

        void alert(string message);
    }
}