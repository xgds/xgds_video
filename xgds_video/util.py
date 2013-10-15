import pytz

from xgds_video import settings

TIME_ZONE = pytz.timezone(settings.XGDS_VIDEO_TIME_ZONE['code'])


def getShortTimeString(dateTime):
    return dateTime.strftime("%H:%M:%S")


def convertUtcToLocal(time):
    time = time.replace(tzinfo=pytz.UTC)
    return getShortTimeString(time.astimezone(TIME_ZONE))  # strftime("%H:%M:%S")
