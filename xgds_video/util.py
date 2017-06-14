#__BEGIN_LICENSE__
# Copyright (c) 2015, United States Government, as represented by the
# Administrator of the National Aeronautics and Space Administration.
# All rights reserved.
#
# The xGDS platform is licensed under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# http://www.apache.org/licenses/LICENSE-2.0.
#
# Unless required by applicable law or agreed to in writing, software distributed
# under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
# CONDITIONS OF ANY KIND, either express or implied. See the License for the
# specific language governing permissions and limitations under the License.
#__END_LICENSE__
import pytz
import re
import datetime
import os
import traceback
import m3u8

from django.conf import settings
from geocamUtil.loader import LazyGetModelByName, getClassByName


TIME_ZONE = pytz.timezone(settings.XGDS_VIDEO_TIME_ZONE['code'])
SEGMENT_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SEGMENT_MODEL)

def getDelaySeconds(flightName):
    return settings.XGDS_VIDEO_DELAY_SECONDS


def getShortTimeString(dateTime):
    return dateTime.strftime("%H:%M:%S")


def convertUtcToLocal(time):
    if time:
        time = time.replace(tzinfo=pytz.utc)
        return time.astimezone(TIME_ZONE)
    else:
        return ""


# def pythonDatetimeToJSON(pyDateTime):
#     if pyDateTime:
#         return {"year": pyDateTime.year, "month": pyDateTime.month, "day": pyDateTime.day,
#                 "hour": pyDateTime.hour, "min": pyDateTime.minute, "seconds": pyDateTime.second}
#     else:
#         return ""


def setSegmentEndTimes(segments, episode, source):
    """
    If both the episode endtime and segments' endtimes are not available (we are live),
    set the segment end time as endTime value inferred from the index file
    Given dictionary of segments (key = source, value = segment).
    """
    if not episode:
        print "CANNOT set segment end times for empty episode" + str(episode)
        return

#     for sourceShortName, segments in sourceSegmentsDict.iteritems():
    flightName = episode.shortName + '_' + source.shortName
#     segments = sourceSegmentsDict[source.shortName]
    segments = sorted(segments, key=lambda segment: segment.segNumber)
    # if last segment has no endTime 
    if (segments[-1].endTime is None) and (episode.endTime is None):
        segment = segments[-1]  # last segment
        GET_INDEX_FILE_METHOD = getClassByName(settings.XGDS_VIDEO_INDEX_FILE_METHOD)
        suffix = GET_INDEX_FILE_METHOD(flightName, source.shortName, segment.segNumber)
        path = settings.DATA_ROOT + suffix
        segmentDuration = getTotalDuration(path)
        segment.endTime = segment.startTime + datetime.timedelta(seconds=segmentDuration)
        segment.save()


def find_between(s, first, last):
    """
    Helper that finds the substring between first and last strings.
    """
    try:
        start = s.index(first) + len(first)
        end = s.index(last, start)
        return s[start:end]
    except ValueError:
        return ""


def getTotalDuration(path):
    """
    Given path to the index file of a segment, returns the total duration of the
    segment
    """
    try:
        indexFile = open(path)
    except IOError:
        print "path not found for segments " + path
        return 0

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

def getSegmentPath(flightName, sourceName, number):
    if sourceName:
        return '%s_%s/Video/Recordings/Segment%03d/' % (flightName, sourceName, int(number))
    else:
        return '%s/Video/Recordings/Segment%03d/' % (flightName, int(number))

def getIndexFileSuffix(flightName, sourceShortName, segmentNumber):
    indexFileName = settings.XGDS_VIDEO_INDEX_FILE_NAME
    splits = flightName.split('_')
    try:
        if sourceShortName:
            if flightName.endswith(sourceShortName):
                flightName = splits[0]
            segments = SEGMENT_MODEL.get().objects.filter(episode__shortName=flightName,segNumber=segmentNumber,source__name=sourceShortName)
        else:
            # flight name encodes both, split it
            segments = SEGMENT_MODEL.get().objects.filter(episode__shortName=splits[0],segNumber=segmentNumber,source__name=splits[1])
            
        # should only be one
        indexFileName = segments[0].indexFileName
    except:
        pass
    
    return '%s/%s' % (getSegmentPath(flightName, sourceShortName, segmentNumber), indexFileName)


def getSegmentsFromEndForDelay(delayTime, indexPath):
    index = m3u8.load(indexPath)
    segList = index.segments
    segCount = 0
    totalTime = 0
    for s in reversed(segList):
        totalTime += s.duration
        segCount += 1
        if totalTime >= delayTime:
            break
    return segCount, index


def updateIndexFilePrefix(indexFileSuffix, subst, flightName):
    """ This is truncating the last n rows from the m3u8 file and reappending the end and the metadata at the top.
    This fakes our delay
    """
    indexFilePath = settings.DATA_ROOT + indexFileSuffix
    segmentDirectoryUrl = settings.DATA_URL + os.path.dirname(indexFileSuffix)
    try:
        videoDelayInSecs = getClassByName(settings.XGDS_VIDEO_DELAY_AMOUNT_METHOD)(flightName)
        if videoDelayInSecs > 0:
            (videoDelayInSegments, m3u8_index) = getSegmentsFromEndForDelay(videoDelayInSecs-30,
                                                              indexFilePath)
        else:
            m3u8_index = m3u8.load(indexFilePath)
            videoDelayInSegments = 0
        
        segments = m3u8_index.segments
        if len(segments) > 0:
            if segments[0].duration > 100:
                del segments[0]
            if videoDelayInSegments > 0 and len(segments) > videoDelayInSegments:
                del segments[-videoDelayInSegments:]
        
        for s in segments:
            s.uri = str(segmentDirectoryUrl) + '/' + s.uri
        return m3u8_index.dumps()
        
    except:
        traceback.print_exc()
        traceback.print_stack()
        return segmentDirectoryUrl
