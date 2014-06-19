import pytz
import re
import datetime
import os

from xgds_video import settings
# from plrpExplorer.views import getVideoDelay # FIX-ME: should be abstracted better from video

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


def processLine(videoDirUrl, line):
    # line = 'prog_index0.ts\n'
    # videoDirUrl = '/data/20140327A_OUT/Video/Recordings/Segment000'
    line = line.rstrip("\n")
    if line.startswith("prog_index"):
        return videoDirUrl + "/" + line
    else:
        return line


"""
If both the episode endtime and segments' endtimes are not available, 
OR if the flight is active (episode endtime is none and flight is active)
set the segment end time as endTime value inferred from the index file
Given dictionary of segments (key = source, value = segment).
"""
def setSegmentEndTimes(sourceSegmentsDict, episode):
    groupflight = None
    flight = None 
    active = False
    
    for sourceShortName, segments in sourceSegmentsDict.iteritems():
#        try:
#            groupflight = GroupFlight.objects.filter(episode_id=episode.id)[0]
#        except:
#            print "Cannot find group flight from episode!"
#        if groupflight:
#            try:
#                flight = NewFlight.objects.filter(group=groupflight, source=sourceShortName)[0]
#            except:
#                print "Cannot find flight from group flight and source name"
#            
#            if flight:
#                active = ActiveFlight.objects.get(flight_id=flight.uuid)
        flightName = episode.shortName + '_' + sourceShortName
        segments = sorted(segments,key = lambda segment: segment.segNumber)
        # if last segment has no endTime OR if flight is active
        if True: #if (segments[-1].endTime == None) or active:
            segment = segments[-1] # last segment
            suffix = getIndexFileSuffix(flightName,
                                        segment.segNumber)
            path = settings.DATA_ROOT + suffix
            segmentDuration = getTotalDuration(path)
            segment.endTime = segment.startTime + datetime.timedelta(seconds=segmentDuration)
            segment.save()
        else:
            print "Flight was not located so no end times were set"
                

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


def getIndexFileSuffix(flightAndSource, segmentNumber):
    path = "DW_Data/" + \
        flightAndSource + "/Video/Recordings/Segment" + \
        padNum(segmentNumber, 3) + '/prog_index.m3u8'
    return path


"""
search and replace in file
pattern: regex pattern for searching
subst: string you want to replace with.
"""
def updateIndexFilePrefix(indexFileSuffix, subst):
#     foundEndMarker = False
    # open the file
    indexFilePath = settings.DATA_ROOT + indexFileSuffix
    segmentDirectoryUrl = settings.DATA_URL + os.path.dirname(indexFileSuffix)
    baseFile = open(indexFilePath)
    videoDelayInSecs = 0 # getVideoDelay() - settings.XGDS_VIDEO_DELAY_MINIMUM_SEC
    if videoDelayInSecs < 0:
        videoDelayInSecs = 0
    videoDelayInSegments = int(round(videoDelayInSecs / settings.XGDS_VIDEO_SEGMENT_SEC))
    videoDelayInLines = 2*videoDelayInSegments + 1
#    print "Video delay in seconds:", videoDelayInSecs
#    print "Video delay in segments:", videoDelayInSegments

    #edit the index file
    clips = baseFile.read().split('#EXTINF:')
    header = clips.pop(0)
    badFirstClip = clips.pop(0)
    processedClips = '#EXTINF:'.join([header] + clips)
    lineList = processedClips.split("\n")
    maxLineNum = len(lineList) - videoDelayInLines
    processedIndex = []
    for idx, line in enumerate(lineList):
        if (idx < maxLineNum):
            processedIndex.append(processLine(segmentDirectoryUrl, line))

#    processedIndex = [processLine(segmentDirectoryUrl, line)
#                      for line in processedClips.split("\n")]
    baseFile.close()

    if videoDelayInSecs == 0:
        if not any([findEndMarker(item) for item in processedIndex]):
            processedIndex.append("#EXT-X-ENDLIST")
    else:
        print "Video delay non-zero - NOT adding any extra end tag"
    return "\n".join(processedIndex) + "\n"
