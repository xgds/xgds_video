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
from geocamUtil.loader import getClassByName
# from plrpExplorer.views import getVideoDelay # FIX-ME: should be abstracted better from video
from django.conf import settings

TIME_ZONE = pytz.timezone(settings.XGDS_VIDEO_TIME_ZONE['code'])


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


def pythonDatetimeToJSON(pyDateTime):
    if pyDateTime:
        return {"year": pyDateTime.year, "month": pyDateTime.month, "day": pyDateTime.day,
                "hour": pyDateTime.hour, "min": pyDateTime.minute, "seconds": pyDateTime.second}
    else:
        return ""


def processLine(videoDirUrl, line):
    line = line.rstrip("\n")
    if line.endswith(".ts"):
        return videoDirUrl + "/" + line
    else:
        return line


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


def getIndexFileSuffix(flightName, sourceShortName, segmentNumber):
    return '%s/Video/Recordings/Segment%03d/prog_index.m3u8' % (flightName, sourceShortName, int(segmentNumber))


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
    return segCount


def updateIndexFilePrefix(indexFileSuffix, subst, flightName):
    """ This is truncating the last n rows from the m3u8 file and reappending the end and the metadata at the top.
    This fakes our delay
    """
    """ TODO flightName is really groupName"""
    """
    search and replace in file
    pattern: regex pattern for searching
    subst: string you want to replace with.
    """
    # foundEndMarker = False
    # open the file
    indexFilePath = settings.DATA_ROOT + indexFileSuffix
    segmentDirectoryUrl = settings.DATA_URL + os.path.dirname(indexFileSuffix)
    try:
        baseFile = open(indexFilePath)
        DELAY_METHOD = getClassByName(settings.XGDS_VIDEO_DELAY_AMOUNT_METHOD)
        videoDelayInSecs = DELAY_METHOD(indexFileSuffix.split('/')[0])
        if videoDelayInSecs < 0:
            videoDelayInSecs = 0
#        videoDelayInSegments = int(round(videoDelayInSecs / settings.XGDS_VIDEO_SEGMENT_SEC))
        if videoDelayInSecs > 0:
            videoDelayInSegments = getSegmentsFromEndForDelay(videoDelayInSecs-30,
                                                              indexFilePath)
        else:
            videoDelayInSegments = 0
        videoDelayInLines = 2 * videoDelayInSegments + 1

        #  edit the index file
        clips = baseFile.read().split('#EXTINF:')
        baseFile.close()
        header = clips.pop(0)
#        clips.pop(0)  # badFirstClip
        processedClips = '#EXTINF:'.join([header] + clips)
        lineList = processedClips.split("\n")
        maxLineNum = len(lineList) - videoDelayInLines
        processedIndex = []
        if maxLineNum <= 0:
            processedIndex.append(header)
        else:
            for idx, line in enumerate(lineList):
                if idx < maxLineNum:
                    processedIndex.append(processLine(segmentDirectoryUrl, line))
        if False:
            if not any([findEndMarker(item) for item in processedIndex]):
                processedIndex.append("#EXT-X-ENDLIST")
        else:
            print "Video delay %d - NOT adding any extra end tag" % videoDelayInSecs
        return "\n".join(processedIndex) + "\n"
    except:
        traceback.print_exc()
        traceback.print_stack()
        return segmentDirectoryUrl
