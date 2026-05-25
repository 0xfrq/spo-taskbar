import asyncio
import datetime
from winsdk.windows.media.control import GlobalSystemMediaTransportControlsSessionManager

async def test():
    manager = await GlobalSystemMediaTransportControlsSessionManager.request_async()
    session = manager.get_current_session()
    if session:
        timeline = session.get_timeline_properties()
        print("Position:", timeline.position.total_seconds())
        print("Last updated:", timeline.last_updated_time)
        now = datetime.datetime.now(datetime.timezone.utc)
        elapsed = now - timeline.last_updated_time
        print("Elapsed since update:", elapsed.total_seconds())
        real_pos = timeline.position.total_seconds() + elapsed.total_seconds()
        print("Real Position:", real_pos)

asyncio.run(test())
