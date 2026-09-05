using Microsoft.UI.Xaml;
using System;

namespace CamTouchUI
{
    public sealed partial class CalibrationWindow : Window
    {
        private CoreClient _client;

        public CalibrationWindow(CoreClient client)
        {
            InitializeComponent();
            _client = client;
        }

        private async void StartCalibration_Click(object sender, RoutedEventArgs e)
        {
            await _client.SendCommandAsync(new { action = "calibrate" });
            Close();
        }

        private void Cancel_Click(object sender, RoutedEventArgs e)
        {
            Close();
        }
    }
}