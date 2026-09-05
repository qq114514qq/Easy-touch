using Microsoft.UI.Xaml;
using System;
using Microsoft.Win32;

namespace CamTouchUI
{
    public sealed partial class SettingsPage : Window
    {
        private CoreClient _client;

        public SettingsPage(CoreClient client)
        {
            InitializeComponent();
            _client = client;
            FpsSlider.ValueChanged += (s, e) => FpsValueText.Text = ((int)FpsSlider.Value).ToString();
            LoadSettings();
        }

        private void LoadSettings()
        {
            // 从注册表或配置文件读取现有设置（简化）
            ResolutionCombo.SelectedIndex = 0;
            FpsSlider.Value = 30;
            PalmEraseSwitch.IsOn = true;
            AutoStartSwitch.IsOn = IsAutoStartEnabled();
        }

        private bool IsAutoStartEnabled()
        {
            using var key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run");
            return key?.GetValue("CamTouchUI") != null;
        }

        private async void SaveButton_Click(object sender, RoutedEventArgs e)
        {
            // 发送设置命令给后端
            await _client.SendCommandAsync(new { action = "set", key = "fps", value = (int)FpsSlider.Value });
            await _client.SendCommandAsync(new { action = "set", key = "palm_erase", value = PalmEraseSwitch.IsOn });

            // 处理开机自启
            if (AutoStartSwitch.IsOn)
            {
                using var key = Registry.CurrentUser.CreateSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run");
                key.SetValue("CamTouchUI", System.Diagnostics.Process.GetCurrentProcess().MainModule.FileName);
            }
            else
            {
                using var key = Registry.CurrentUser.OpenSubKey(@"Software\Microsoft\Windows\CurrentVersion\Run", true);
                key?.DeleteValue("CamTouchUI", false);
            }

            Close();
        }
    }
}