using Microsoft.UI.Xaml;
using System;
using System.Threading.Tasks;

namespace CamTouchUI
{
    public sealed partial class MainWindow : Window
    {
        private CoreClient _client;
        private TrayIcon? _trayIcon;
        private SettingsPage? _settingsPage;

        public MainWindow()
        {
            InitializeComponent();
            _client = new CoreClient();
            _client.StatusReceived += OnStatusReceived;
            _ = ConnectToCoreAsync();

            // 初始化托盘图标
            _trayIcon = new TrayIcon(this);
            _trayIcon.Show();
        }

        private async Task ConnectToCoreAsync()
        {
            try
            {
                await _client.ConnectAsync();
                StatusText.Text = "已连接";
                UpdateButtons(true);
            }
            catch (Exception)
            {
                StatusText.Text = "连接失败";
                UpdateButtons(false);
                TryStartCoreProcess();
            }
        }

        private void TryStartCoreProcess()
        {
            // 尝试启动 camtouch-core.exe（假设与 UI 在同一目录）
            string corePath = System.IO.Path.Combine(AppContext.BaseDirectory, "camtouch-core.exe");
            if (System.IO.File.Exists(corePath))
            {
                System.Diagnostics.Process.Start(corePath);
                _ = Task.Delay(2000).ContinueWith(_ => _ = ConnectToCoreAsync());
            }
        }

        private void OnStatusReceived(CoreStatus status)
        {
            DispatcherQueue.TryEnqueue(() =>
            {
                FpsText.Text = status.Fps.ToString("0.0");
                StatusText.Text = status.Status == "running" ? "运行中" : "已暂停";
                HandsText.Text = status.Hands.ToString();
                CameraStatusText.Text = status.Hands >= 0 ? "已连接" : "未连接";
            });
        }

        private void UpdateButtons(bool connected)
        {
            StartButton.IsEnabled = connected;
            StopButton.IsEnabled = connected;
            CalibrateButton.IsEnabled = connected;
            SettingsButton.IsEnabled = connected;
        }

        private async void StartButton_Click(object sender, RoutedEventArgs e)
        {
            await _client.SendCommandAsync(new { action = "start" });
        }

        private async void StopButton_Click(object sender, RoutedEventArgs e)
        {
            await _client.SendCommandAsync(new { action = "stop" });
        }

        private async void CalibrateButton_Click(object sender, RoutedEventArgs e)
        {
            var calibWindow = new CalibrationWindow(_client);
            calibWindow.Activate();
        }

        private void SettingsButton_Click(object sender, RoutedEventArgs e)
        {
            if (_settingsPage == null)
                _settingsPage = new SettingsPage(_client);
            _settingsPage.Activate();
        }
    }
}