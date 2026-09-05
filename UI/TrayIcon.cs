using H.NotifyIcon;
using Microsoft.UI.Xaml;
using System;

namespace CamTouchUI
{
    public class TrayIcon
    {
        private TaskbarIcon _icon;
        private MainWindow _window;

        public TrayIcon(MainWindow window)
        {
            _window = window;
            _icon = new TaskbarIcon
            {
                Icon = System.Drawing.SystemIcons.Application,
                ToolTipText = "电视触屏",
                ContextMenu = new System.Windows.Forms.ContextMenuStrip()
            };
            var menu = _icon.ContextMenu.Items;
            menu.Add("校准", null, (s, e) => _window.CalibrateButton_Click(null, null));
            menu.Add("暂停/恢复", null, (s, e) => _window.StopButton_Click(null, null));
            menu.Add("退出", null, (s, e) => _window.Close());
        }

        public void Show()
        {
            _icon.Visible = true;
        }

        public void Hide()
        {
            _icon.Visible = false;
        }
    }
}