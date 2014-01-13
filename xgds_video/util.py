import pytz

from xgds_video import settings

TIME_ZONE = pytz.timezone(settings.XGDS_VIDEO_TIME_ZONE['code'])


def getShortTimeString(dateTime):
    return dateTime.strftime("%H:%M:%S")


def convertUtcToLocal(time):
    if time:
        time = time.replace(tzinfo=pytz.UTC)
        return time.astimezone(TIME_ZONE) 
    else:
        return ""

def pythonDatetimeToJSON(pyDateTime):
    if pyDateTime:
        return {"year":pyDateTime.year, "month":pyDateTime.month, "day":pyDateTime.day, 
                "hour":pyDateTime.hour, "min":pyDateTime.minute, "seconds":pyDateTime.second}
    else:
        return ""

