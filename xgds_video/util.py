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


def processLine(subst, line):
    return line.rstrip('\n') % {"prefix": subst}  


def findEndMarker(item):
    if re.match("#EXT-X-ENDLIST", item):
        return True


'''
search and replace in file
pattern: regex pattern for searching
subst: string you want to replace with.
'''
def updateIndexFilePrefix(indexFilePath, subst):
    foundEndMarker = False
    baseFile = open(indexFilePath)
    processedIndex = [processLine(subst, line) for line in baseFile]
    baseFile.close()
    
    if not any([findEndMarker(item) for item in processedIndex]):
        processedIndex.append("#EXT-X-ENDLIST")
    return "\n".join(processedIndex) + "\n"
