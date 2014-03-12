import pytz
import re
import sys

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
        return {"year": pyDateTime.year, "month": pyDateTime.month, "day": pyDateTime.day,
                "hour": pyDateTime.hour, "min": pyDateTime.minute, "seconds": pyDateTime.second}
    else:
        return ""

'''
search and replace in file
pattern: regex pattern for searching
subst: string you want to replace with.
'''
def updateIndexFilePrefix(indexFilePath, pattern, subst):
    foundEndMarker = False
    baseFile = open(indexFilePath)
    processedIndex = []
    for line in baseFile:
        processedIndex.append(re.sub(pattern, subst, line.rstrip("\n")))
        if re.match("#EXT-X-ENDLIST", line):
            foundEndMarker = True
    baseFile.close()
    if not foundEndMarker:
        processedIndex.append("#EXT-X-ENDLIST")
    # Append final newline to match original file format
    return "\n".join(processedIndex) + "\n"

