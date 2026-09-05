using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using System;
using System.Diagnostics;
using System.IO;
using System.Threading.Tasks;
using Windows.Devices.Enumeration;

namespace CamTouchUI
{
    public sealed partial class SetupWizardWindow : Window
    {
        private int _currentStep = 0;
        private CoreClient _client;
        private bool _driverInstalled = false;
        private bool _cameraInstalled = false;

        public SetupWizardWindow(CoreClient client)
        {
            InitializeComponent();
            _client = client;
            UpdateNavigation();
        }

        private void UpdateNavigation()
        {
            // 显示当前步骤
            WelcomePage.Visibility = _currentStep == 0 ? Visibility.Visible : Visibility.Collapsed;
            DriverPage.Visibility = _currentStep == 1 ? Visibility.Visible : Visibility.Collapsed;
            CameraPage.Visibility = _currentStep == 2 ? Visibility.Visible : Visibility.Collapsed;
            ScreenPage.Visibility = _currentStep == 3 ? Visibility.Visible : Visibility.Collapsed;
            CalibrationPage.Visibility = _currentStep == 4 ? Visibility.Visible : Visibility.Collapsed;
            CompletePage.Visibility = _currentStep == 5 ? Visibility.Visible : Visibility.Collapsed;

            // 更新按钮状态
            BackButton.IsEnabled = _currentStep > 0 && _currentStep < 5;
            NextButton.IsEnabled = _currentStep < 5;
            SkipButton.Visibility = _currentStep < 5 ? Visibility.Visible : Visibility.Collapsed;

            if (_currentStep == 0)
            {
                NextButton.Content = "开始设置";
                NextButton.IsEnabled = AgreeCheckBox.IsChecked == true;
            }
            else if (_currentStep == 5)
            {
                NextButton.Content = "完成";
                SkipButton.Visibility = Visibility.Collapsed;
            }
            else
            {
                NextButton.Content = "下一步";
            }

            // 执行当前步骤的检查
            if (_currentStep == 1)
            {
                CheckDriver();
            }
            else if (_currentStep == 2)
            {
                CheckCamera();
            }
        }

        private void AgreeCheckBox_Changed(object sender, RoutedEventArgs e)
        {
            if (_currentStep == 0)
            {
                NextButton.IsEnabled = AgreeCheckBox.IsChecked == true;
            }
        }

        private async void CheckDriver()
        {
            DriverProgressBar.IsIndeterminate = true;
            DriverStatusText.Text = "正在检测 VMulti 驱动...";
            
            await Task.Delay(1000); // 模拟检测过程
            
            _driverInstalled = IsDriverInstalled();
            DriverProgressBar.IsIndeterminate = false;
            
            if (_driverInstalled)
            {
                DriverStatusText.Text = "✅ VMulti 驱动已安装";
                DriverStatusText.Foreground = new SolidColorBrush(Microsoft.UI.Colors.Green);
                DriverActionPanel.Visibility = Visibility.Collapsed;
                NextButton.IsEnabled = true;
            }
            else
            {
                DriverStatusText.Text = "❌ 未检测到 VMulti 驱动";
                DriverStatusText.Foreground = new SolidColorBrush(Microsoft.UI.Colors.Red);
                DriverActionPanel.Visibility = Visibility.Visible;
                NextButton.IsEnabled = false;
            }
        }

        private async void CheckCamera()
        {
            CameraProgressBar.IsIndeterminate = true;
            CameraStatusText.Text = "正在检测摄像头...";
            
            await Task.Delay(1000); // 模拟检测过程
            
            _cameraInstalled = await IsCameraAvailable();
            CameraProgressBar.IsIndeterminate = false;
            
            if (_cameraInstalled)
            {
                CameraStatusText.Text = "✅ 摄像头已连接";
                CameraStatusText.Foreground = new SolidColorBrush(Microsoft.UI.Colors.Green);
                CameraPreviewPanel.Visibility = Visibility.Visible;
                NextButton.IsEnabled = true;
            }
            else
            {
                CameraStatusText.Text = "❌ 未检测到摄像头";
                CameraStatusText.Foreground = new SolidColorBrush(Microsoft.UI.Colors.Red);
                NextButton.IsEnabled = false;
            }
        }

        private bool IsDriverInstalled()
        {
            string dllPath = Path.Combine(AppContext.BaseDirectory, "vmulticlient.dll");
            if (File.Exists(dllPath))
            {
                return true;
            }

            try
            {
                var process = new Process
                {
                    StartInfo = new ProcessStartInfo
                    {
                        FileName = "pnputil",
                        Arguments = "/enum-devices",
                        UseShellExecute = false,
                        RedirectStandardOutput = true,
     