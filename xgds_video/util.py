import pytz
import re
#import pydevd

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
    return line.rstrip('\n') % {"fileSequence": subst}


def getTotalDuration(path):
    indexFile = open(path)

    totalDuration = 0
    for line in indexFile:
        if re.match("#EXTINF:[^\d]",line):
           totalDuration += re.findall(r'[0-9]*\.[0-9]+',line)

    indexFile.close()
    return totalDuration


def findEndMarker(item):
    if re.match("#EXT-X-ENDLIST", item):
        return True


def getPathToIndexFile(flightAndSource, segmentNumber):
    path = settings.PROJ_ROOT + "data/DW_Data/" + \
        str(flightAndSource) + "/Video/Recordings/Segment" + \
        segmentNumber + '/prog_index.m3u8'
    return path


"""
search and replace in file
pattern: regex pattern for searching
subst: string you want to replace with.
"""
def updateIndexFilePrefix(indexFilePath, subst):
#     foundEndMarker = False
    # open the file
    baseFile = open(indexFilePath)

    #edit the index file
    processedIndex = [processLine(subst, line) for line in baseFile]
    baseFile.close()

    if not any([findEndMarker(item) for item in processedIndex]):
        processedIndex.append("#EXT-X-ENDLIST")
    return "\n".join(processedIndex) + "\n"
