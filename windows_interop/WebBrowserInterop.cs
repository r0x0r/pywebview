using System;
using System.Runtime.InteropServices;
using System.Windows.Forms;
using MsHtmHstInterop;


namespace WebBrowserInterop
{
    public interface IWebBrowserInterop
    {
        object call(string message, object param);

        void alert(string message);
    }

    public class WebBrowserHelper : IDocHostUIHandler
    {

        public WebBrowserHelper(HtmlDocument doc)
        {
            ICustomDoc iDoc = (ICustomDoc)doc.DomDocument;
            iDoc.SetUIHandler((IDocHostUIHandler)this);
        }

        void IDocHostUIHandler.EnableModeless(int fEnable)
        {

        }

        void IDocHostUIHandler.FilterDataObject(MsHtmHstInterop.IDataObject pDO, out MsHtmHstInterop.IDataObject ppDORet)
        {
            ppDORet = null;
        }

        void IDocHostUIHandler.GetDropTarget(MsHtmHstInterop.IDropTarget pDropTarget, out MsHtmHstInterop.IDropTarget ppDropTarget)
        {
            ppDropTarget = null;
        }

        void IDocHostUIHandler.GetExternal(out object ppDispatch)
        {
            ppDispatch = null;
        }

        void IDocHostUIHandler.GetHostInfo(ref _DOCHOSTUIINFO pInfo)
        {
            pInfo.dwFlags = 0x5a74012;
            pInfo.dwFlags |= 0x40000000;
            MessageBox.Show("w00t");
        }

        void IDocHostUIHandler.GetOptionKeyPath(out string pchKey, uint dw)
        {
            pchKey = null;
        }

        void IDocHostUIHandler.HideUI()
        {

        }

        void IDocHostUIHandler.OnDocWindowActivate(int fActivate)
        {

        }

        void IDocHostUIHandler.OnFrameWindowActivate(int fActivate)
        {

        }

        void IDocHostUIHandler.ResizeBorder(ref MsHtmHstInterop.tagRECT prcBorder, IOleInPlaceUIWindow pUIWindow, int fRameWindow)
        {

        }

        void IDocHostUIHandler.ShowContextMenu(uint dwID, ref MsHtmHstInterop.tagPOINT ppt, object pcmdtReserved, object pdispReserved)
        {

        }

        void IDocHostUIHandler.ShowUI(uint dwID, IOleInPlaceActiveObject pActiveObject, IOleCommandTarget pCommandTarget, IOleInPlaceFrame pFrame, IOleInPlaceUIWindow pDoc)
        {

        }

        void IDocHostUIHandler.TranslateAccelerator(ref tagMSG lpmsg, ref Guid pguidCmdGroup, uint nCmdID)
        {

        }

        void IDocHostUIHandler.TranslateUrl(uint dwTranslate, ref ushort pchURLIn, IntPtr ppchURLOut)
        {

        }

        void IDocHostUIHandler.UpdateUI()
        {

        }
    }
}