using System;
using System.ComponentModel;
using System.Runtime.InteropServices;
using System.Security.Permissions;
using System.Windows.Forms;



namespace WebBrowserInterop
{
    public interface IWebBrowserInterop
    {
        object call(string message, object param, string valueId);

        void alert(string message);

        void console(string message);
    }

    [ComImport, TypeLibType(TypeLibTypeFlags.FHidden),
    InterfaceType(ComInterfaceType.InterfaceIsIDispatch),
    Guid("34A715A0-6587-11D0-924A-0020AFC7AC4D")]
    public interface DWebBrowserEvents2
    {
        /// <summary>
        ///
        /// </summary>
        /// <param name="ppDisp">
        /// An interface pointer that, optionally, receives the IDispatch interface
        /// pointer of a new WebBrowser object or an InternetExplorer object.
        /// </param>
        /// <param name="Cancel">
        /// value that determines whether the current navigation should be canceled
        /// </param>
        /// <param name="dwFlags">
        /// The flags from the NWMF enumeration that pertain to the new window
        /// See http://msdn.microsoft.com/en-us/library/bb762518(VS.85).aspx.
        /// </param>
        /// <param name="bstrUrlContext">
        /// The URL of the page that is opening the new window.
        /// </param>
        /// <param name="bstrUrl">The URL that is opened in the new window.</param>
        [DispId(0x111)]
        void NewWindow3(
            [In, Out, MarshalAs(UnmanagedType.IDispatch)] ref object ppDisp,
            [In, Out] ref bool Cancel,
            [In] uint dwFlags,
            [In, MarshalAs(UnmanagedType.BStr)] string bstrUrlContext,
            [In, MarshalAs(UnmanagedType.BStr)] string bstrUrl);

        [DispId(0x68)]
        void DownloadComplete();
    }

    public partial class WebBrowserEx : WebBrowser
    {
        AxHost.ConnectionPointCookie cookie;
        DWebBrowserEvent2Helper helper;
        [Browsable(true)]
        public event EventHandler DownloadComplete;
        public event EventHandler<WebBrowserNewWindowEventArgs> NewWindow3;
        public const int WM_NCLBUTTONDOWN = 161;
        public const int HT_CAPTION = 2;

        [PermissionSetAttribute(SecurityAction.LinkDemand, Name = "FullTrust")]
        public WebBrowserEx()
        {
        }

        [DllImport("user32.dll")]
        public static extern int SendMessage(IntPtr hWnd, int Msg, int wParam, int lParam);

        [DllImport("user32.dll")]
        public static extern bool ReleaseCapture();

        [DllImport("urlmon.dll", CharSet = CharSet.Ansi)]
        private static extern int UrlMkSetSessionOption(int dwOption, string pBuffer, int dwBufferLength, int dwReserved);
        const int URLMON_OPTION_USERAGENT = 0x10000001;

        public void ChangeUserAgent(string Agent)
        {
            UrlMkSetSessionOption(URLMON_OPTION_USERAGENT, Agent, Agent.Length, 0);
        }

        /// <summary>
        /// Associates the underlying ActiveX control with a client that can
        /// handle control events including NewWindow3 event.
        /// </summary>
        [PermissionSetAttribute(SecurityAction.LinkDemand, Name = "FullTrust")]
        protected override void CreateSink()
        {
            base.CreateSink();

            helper = new DWebBrowserEvent2Helper(this);
            cookie = new AxHost.ConnectionPointCookie(
                this.ActiveXInstance, helper, typeof(DWebBrowserEvents2));
        }
        /// <summary>
        /// Releases the event-handling client attached in the CreateSink method
        /// from the underlying ActiveX control
        /// </summary>
        [PermissionSetAttribute(SecurityAction.LinkDemand, Name = "FullTrust")]
        protected override void DetachSink()
        {
            if (cookie != null)
            {
                cookie.Disconnect();
                cookie = null;
            }
            base.DetachSink();
        }
        /// <summary>
        ///  Raises the NewWindow3 event.
        /// </summary>
        protected virtual void OnNewWindow3(WebBrowserNewWindowEventArgs e)
        {
            if (this.NewWindow3 != null)
            {
                this.NewWindow3(this, e);
            }
        }

        protected virtual void OnDownloadComplete()
        {
            if (this.DownloadComplete != null)
            {
                this.DownloadComplete(this, null);
            }
        }

        private class DWebBrowserEvent2Helper : StandardOleMarshalObject, DWebBrowserEvents2
        {
            private WebBrowserEx parent;
            public DWebBrowserEvent2Helper(WebBrowserEx parent)
            {
                this.parent = parent;
            }
            /// <summary>
            /// Raise the NewWindow3 event.
            /// If an instance of WebBrowser2EventHelper is associated with the underlying
            /// ActiveX control, this method will be called When the NewWindow3 event was
            /// fired in the ActiveX control.
            /// </summary>
            public void NewWindow3(ref object ppDisp, ref bool Cancel, uint dwFlags,
                string bstrUrlContext, string bstrUrl)
            {
                var e = new WebBrowserNewWindowEventArgs(bstrUrl, Cancel);
                this.parent.OnNewWindow3(e);
                Cancel = e.Cancel;
            }

            public void DownloadComplete()
            {
                this.parent.OnDownloadComplete();
            }
        }
    }
    public class WebBrowserNewWindowEventArgs : EventArgs
    {
        public String Url { get; set; }
        public Boolean Cancel { get; set; }
        public WebBrowserNewWindowEventArgs(String url, Boolean cancel)
        {
            this.Url = url;
            this.Cancel = cancel;
        }
    }
}
