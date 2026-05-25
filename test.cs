using System;
using System.Threading;
using System.Threading.Tasks;
using Windows.Media.Control;

class Program
{
    static async Task Main()
    {
        var manager = await GlobalSystemMediaTransportControlsSessionManager.RequestAsync();
        var session = manager.GetCurrentSession();
        if (session != null)
        {
            var props = await session.TryGetMediaPropertiesAsync();
            Console.WriteLine(props.Title);
        }
    }
}
