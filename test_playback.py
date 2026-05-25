import asyncio
import datetime
from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager, GlobalSystemMediaTransportControlsSessionPlaybackStatus

async def test():
    manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
    session = manager.get_current_session()
    if session:
        playback = session.get_playback_info()
        print("Playback status:", playback.playback_status)
        print("Is playing?", playback.playback_status == GlobalSystemMediaTransportControlsSessionPlaybackStatus.PLAYING)

asyncio.run(test())
