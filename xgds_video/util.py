import pytz
import re
import datetime

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


"""
If both the episode endtime and segments' endtimes are not available, 
set the segment end time as endTime value inferred from the index file
Given dictionary of segments (key = source, value = segment).
"""
def setSegmentEndTimes(sourceSegmentsDict, episode):
    if episode:
        if episode.endTime == None:
            for sourceShortName, segments in sourceSegmentsDict.iteritems():
                flightAndSource = episode.shortName + '_' + sourceShortName
                for segment in segments:
                    if segment.endTime == None:
                        path = getPathToIndexFile(flightAndSource, segment.segNumber)
                        segmentDuration = getTotalDuration(path)
                        segment.endTime = segment.startTime + datetime.timedelta(seconds=segmentDuration)
                        segment.save()


"""
Helper that finds the substring between first and last strings.
"""
def find_between( s, first, last ):
    try:
        start = s.index( first ) + len( first )
        end = s.index( last, start )
        return s[start:end]
    except ValueError:
        return ""

"""
Given path to the index file of a segment, returns the total duration of the 
segment
"""
def getTotalDuration(path):
    indexFile = open(path)

    totalDuration = 0
    for line in indexFile:
        if line.startswith("#EXTINF"):
            timeValue = find_between(line, ":", ",")
            totalDuration += int(float(timeValue))

    indexFile.close()
    return totalDuration



def findEndMarker(item):
    if re.match("#EXT-X-ENDLIST", item):
        return True


def padNum(num, size):
    s = str(num);
    while (len(s) < size): 
        s = '0' + s
    return s


def getPathToIndexFile(flightAndSource, segmentNumber):
    path = settings.PROJ_ROOT + "data/DW_Data/" + \
        flightAndSource + "/Video/Recordings/Segment" + \
        padNum(segmentNumber, 3) + '/prog_index.m3u8'
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
