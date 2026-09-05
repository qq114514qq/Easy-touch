using System;
using System.IO;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace CamTouchUI
{
    public class CoreStatus
    {
        public double Fps { get; set; }
        public string Status { get; set; } = "";
        public int Hands { get; set; }
    }

    public class CoreClient : IDisposable
    {
        private TcpClient? _client;
        private NetworkStream? _stream;
        private CancellationTokenSource? _cts;
        public event Action<CoreStatus>? StatusReceived;

        public bool IsConnected => _client?.Connected ?? false;

        public async Task ConnectAsync()
        {
            _client = new TcpClient();
            await _client.ConnectAsync("127.0.0.1", 8765);
            _stream = _client.GetStream();
            _cts = new CancellationTokenSource();
            _ = Task.Run(() => ReadLoop(_cts.Token));
        }

        private async Task ReadLoop(CancellationToken token)
        {
            var buffer = new byte[1024];
            var sb = new StringBuilder();
            while (!token.IsCancellationRequested)
            {
                int bytesRead = await _stream!.ReadAsync(buffer, 0, buffer.Length, token);
                if (bytesRead == 0) break;
                sb.Append(Encoding.UTF8.GetString(buffer, 0, bytesRead));
                string data = sb.ToString();
                int newlineIndex;
                while ((newlineIndex = data.IndexOf('\n')) >= 0)
                {
                    string line = data.Substring(0, newlineIndex);
                    data = data.Substring(newlineIndex + 1);
                    try
                    {
                        var status = JsonSerializer.Deserialize<CoreStatus>(line);
                        if (status != null)
                            StatusReceived?.Invoke(status);
                    }
                    catch { /* 忽略非状态消息 */ }
                }
                sb.Clear();
                sb.Append(data);
            }
        }

        public async Task SendCommandAsync(object command)
        {
            if (_stream == null) return;
            string json = JsonSerializer.Serialize(command) + "\n";
            byte[] bytes = Encoding.UTF8.GetBytes(json);
            await _stream.WriteAsync(bytes, 0, bytes.Length);
        }

        public void Dispose()
        {
            _cts?.Cancel();
            _client?.Close();
        }
    }
}