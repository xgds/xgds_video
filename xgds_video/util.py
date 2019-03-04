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
from django.utils import timezone
import os
import traceback
import m3u8

from django.conf import settings
from geocamUtil.loader import LazyGetModelByName, getClassByName
from xgds_core.views import getDelay
from xgds_video.recordingUtil import getFudgeForSource

TIME_ZONE = pytz.timezone(settings.XGDS_VIDEO_TIME_ZONE['code'])
SEGMENT_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SEGMENT_MODEL)


def getDelaySeconds(flightName):
    delay = getDelay()
#     the below is already subtracted when we use the delay seconds.
#     delay -= settings.XGDS_VIDEO_BUFFER_FUDGE_FACTOR
    return delay


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
        
        #GET_INDEX_FILE_METHOD = getClassByName(settings.XGDS_VIDEO_INDEX_FILE_METHOD)
        #indexFilePath = GET_INDEX_FILE_METHOD(flightName, source.shortName, segment.segNumber)
        indexFilePath = '%s/%s' % (getSegmentPath(flightName, source.shortName, segment.segNumber), segment.indexFileName)
    
        path = settings.DATA_ROOT + indexFilePath
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
    #TODO use the m3u8 library to get the duration
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


def getIndexFilePath(flightName, sourceShortName, segmentNumber):
    indexFileName = settings.XGDS_VIDEO_INDEX_FILE_NAME
    if '_' in flightName:
        splits = flightName.split('_')
    else:
        splits = [flightName, sourceShortName]

    if sourceShortName:
        if flightName.endswith(sourceShortName):
            episode_shortName = splits[0]
        else:
            episode_shortName = flightName
    else:
        episode_shortName = splits[0]
        sourceShortName = splits[1]

    try:
        segments = SEGMENT_MODEL.get().objects.filter(episode__shortName=episode_shortName,
                                                      segNumber=int(segmentNumber),
                                                      source__shortName=sourceShortName)
        # should only be one
        indexFileName = segments[0].indexFileName
        return os.path.join(getSegmentPath(flightName, sourceShortName, segmentNumber), indexFileName), segments[0]
    except:
        raise Exception('Segments not found for %s: %s: %s' % (episode_shortName, sourceShortName, segmentNumber))



def getNumChunksFromEndForDelay(delayTime, indexPath):
    index = None
    segCount = 0
    totalTime = 0
    valid = False    
    try:
        index = m3u8.load(indexPath)
        segList = index.segments

        for s in reversed(segList):
            totalTime += s.duration
            segCount += 1
            if totalTime >= delayTime:
                break
        valid = True
    except:
        traceback.print_exc()
    return segCount, index, valid


def getSegmentNumber(segmentObj):
    segFileName = os.path.basename(segmentObj.uri)
    name, ext = os.path.splitext(segFileName)
    try:
        baseName, otherNumber, segNum = name.split("_")
    except:
        try:
            baseName, segNum = name.split("-")
        except:
            pattern = '(?:[a-z]*[A-Z]*)*([0-9]*)'
            match = re.search(pattern, name)
            if match:
                return int(match.group(1))
            
    return int(segNum)


def getIndexFileContents(flightName=None, sourceShortName=None, segmentNumber=None):
    """ This is truncating the last n rows from the m3u8 file and reappending the end and the metadata at the top.
    This fakes our delay
    """

    # Look up path to index file
    GET_INDEX_FILE_METHOD = getClassByName(settings.XGDS_VIDEO_INDEX_FILE_METHOD)
    indexFileSuffix, segment = GET_INDEX_FILE_METHOD(flightName, sourceShortName, segmentNumber)

    indexFilePath = os.path.join(settings.DATA_ROOT, indexFileSuffix)
    segmentDirectoryUrl = settings.DATA_URL + os.path.dirname(indexFileSuffix)
    valid = False
    try:
        videoDelayInSecs = getClassByName(settings.XGDS_VIDEO_DELAY_AMOUNT_METHOD)(flightName)
        if videoDelayInSecs > 0:
            calculatedDelay = videoDelayInSecs

            #if the segment is ended then this may want to be different
            if segment.endTime:
                # 1. calculate secondsAgo = nowTime - segment.endTime
                secondsAgo = (timezone.now() - segment.endTime).total_seconds()
                # 2. if secondsAgo < delay, calculatedDelay = videoDelayInSecs - secondsAgo
                calculatedDelay = max(videoDelayInSecs - secondsAgo, 0)
            if calculatedDelay > 0: 
                (videoDelayInChunks, m3u8_index, valid) = getNumChunksFromEndForDelay(calculatedDelay - getFudgeForSource(sourceShortName), indexFilePath)
                if videoDelayInChunks > 0:
                    m3u8_index.is_endlist = False
            else:
                # I *think* we should only get here if we have signal loss during a live feed and are playing out the last
                # bit of playlist in which case we *should* add an end tag.
                try:
                    if segment.endTime:
                        m3u8_index = m3u8.load(indexFilePath)
                    if segment.episode.endTime: 
                        m3u8_index.is_endlist = True
                        valid = True
                    videoDelayInChunks = 0
                    #TODO broadcast segment end, show glitch in progress screen
                except:
                    traceback.print_exc()
        else:
            try: 
                m3u8_index = m3u8.load(indexFilePath)
                videoDelayInChunks = 0
                valid = True
            except:
                traceback.print_exc()
        
        if not valid:
            if m3u8_index:
                 try:
                    m3u8_index.segments = None
                 except:
                    pass
                 return (m3u8_index.dumps(), indexFilePath)
            else:
                 return (None, None)

        m3u8_chunks = m3u8_index.segments
        
        if m3u8_chunks and len(m3u8_chunks) > 0:
            # this was probably to handle vlc badness
#             if segments[0].duration > 100:
#                 del segments[0]

            if videoDelayInChunks > 0: # and len(m3u8_chunks) > videoDelayInChunks:
                del m3u8_chunks[-videoDelayInChunks:]
                del m3u8_chunks[:-settings.XGDS_VIDEO_LIVE_PLAYLIST_SIZE_TO_PLAYER]

        if m3u8_chunks:
            firstSegNum = getSegmentNumber(m3u8_index.segments[0])
        else:
            firstSegNum = 0
        m3u8_index.media_sequence = firstSegNum

        for s in m3u8_chunks:
            s.uri = str(segmentDirectoryUrl) + '/' + s.uri
    
        return (m3u8_index.dumps(), indexFilePath)
        
    except:
        #TODO handle better
        traceback.print_exc()
        traceback.print_stack()
        return (None, None)


def calculate_ts_file(folder_name, seconds_int, index_file_name='prog_index.m3u8'):
    """
    Find the ts file that is s_int seconds into the recording
    :param folder_name: that holds ts files
    :param seconds_int: seconds into the recording
    :param index_file_name: usually prog_index.m3u8
    :return: tsfile name and offset seconds into the file
    """
    # open the prog_index.m3u8
    m3u8_obj = m3u8.load(os.path.join(folder_name, index_file_name))

    acc_time = 0
    num_segs = len(m3u8_obj.segments)
    s_float = float(seconds_int)
    file_number = 0
    for seg_num in range(0, num_segs):
        next_delta = m3u8_obj.segments[seg_num].duration
        if acc_time + next_delta > float(s_float):
            # save file number
            # (if you subtract 1, you're off by one. not sure why.)
            file_number = seg_num
            break
        acc_time = acc_time + next_delta

    if seconds_int > int(acc_time + next_delta):
        msg = "Requested time " + str(seconds_int) + "s is outside range of " + index_file_name + ", " \
              + str(int(acc_time + next_delta)) + 's'
        raise Exception(msg)

    return m3u8_obj.segments[file_number].uri, s_float - acc_time