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
import datetime
#import time
import logging
import os
import stat
import traceback
import time
import json

from django.utils import timezone
from django.conf import settings
from django.contrib import messages 
from django.shortcuts import redirect
from django.core.urlresolvers import reverse

from django.db.models.aggregates import Max

from geocamPycroraptor2.views import getPyraptordClient, stopPyraptordServiceIfRunning
from geocamUtil.datetimeJsonEncoder import DatetimeJsonEncoder

from geocamUtil.loader import LazyGetModelByName, getClassByName

from django.core.cache import caches  
_cache = caches['default']

# if settings.XGDS_CORE_REDIS:
#     from xgds_core.redisUtil import publishRedisSSE


SETTINGS_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SETTINGS_MODEL)
SEGMENT_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SEGMENT_MODEL)
EPISODE_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_EPISODE_MODEL)
VIDEO_SOURCE_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SOURCE_MODEL)

SSE_TYPE = "video"

def makedirsIfNeeded(path):
    """
    Helper for displayEpisodeRecordedVideo
    """
    if not os.path.exists(path):
        currentUmask = os.umask(0)  # Save current umask and set to 0 so we can control permissions
        os.makedirs(path, stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH)
        os.umask(currentUmask)  # Restore process umask
#        os.chmod(path, (stat.S_IRWXO | stat.S_IRWXG | stat.S_IRWXU))


def emptySegmentDir(recordedVideoDir):
    ''' check if this segment directory is empty
    '''
    try:
        if not os.listdir(recordedVideoDir):
            return True
    except:
        return True
    return False


def getVideoSource(sourceName):
    videoSource = VIDEO_SOURCE_MODEL.get().objects.get(shortName=sourceName)
    return videoSource

def splitFlightName(flightName):
    #this assumes flight name of episodeName_sourceName - source cannot have underscores in name.
    splits = flightName.rsplit("_", 1)
    episodeName = splits[0]
    sourceName = splits[1]
    return (episodeName, sourceName)

def startFlightRecording(flightName):
    (episodeName, sourceName) = splitFlightName(flightName)
    startTime=timezone.now()   #TODO: This is not true - we should lookup timecode from Wowza playlist
    try:
        videoEpisode = EPISODE_MODEL.get().objects.get(shortName=episodeName)
        if videoEpisode.endTime:
            videoEpisode.endTime = None
            videoEpisode.save()
            print '*** startFlightRecording(): Cleared end time for episode ' + episodeName
    except:
        videoEpisode = EPISODE_MODEL.get()(shortName=episodeName, startTime=startTime)
        videoEpisode.save()
        print '*** startFlightRecording(): Created video episode ' + episodeName

    videoEpisode.broadcast('start')

    recordingDir = getRecordedVideoDir(flightName)
    recordingUrl = getRecordedVideoUrl(flightName)
    videoSource = getVideoSource(sourceName)
    commands = startRecording(videoSource, recordingDir,
                              recordingUrl, startTime,
                              episode=videoEpisode)
#    messages.info(request, commands)
    return True


def stopFlightRecording(flightName, endEpisode = False):
    (episodeName, sourceName) = splitFlightName(flightName)
    stopTime = timezone.now()
    commands = stopRecording(getVideoSource(sourceName), stopTime)

    if endEpisode:
        videoEpisode = EPISODE_MODEL.get().objects.get(shortName=episodeName)
        videoEpisode.endTime = stopTime
        videoEpisode.save()
        videoEpisode.broadcast('end')
        commands = commands + ' & set episode end time ' + str(stopTime)
#    messages.info(request, commands)
    return True


def makeNewSegment(source, recordingDir, recordingUrl, startTime, episode):
    if not source.videofeed_set.all():
        logging.info("video feeds set is empty")
        return
    videoFeed = source.videofeed_set.all()[0]
    
    # figure out next segment number for this source and episode
    try:
        maxSegmentNumber = SEGMENT_MODEL.get().objects.filter(episode=episode, source=source).aggregate(Max('segNumber'))
        segmentNumber = maxSegmentNumber['segNumber__max']
        if not segmentNumber:
            segmentNumber = 0
        recordedVideoDir = os.path.join(recordingDir, 'Segment%03d' % segmentNumber)
        if not emptySegmentDir(recordedVideoDir):
            segmentNumber = segmentNumber + 1
            recordedVideoDir = os.path.join(recordingDir, 'Segment%03d' % segmentNumber)

        # adjust start and end times for all prio segments
        existingSegments = SEGMENT_MODEL.get().objects.filter(source=source,episode=episode)
#         for segment in existingSegments:
#             segment.adjustSegmentTimes()
    except:
        traceback.print_exc()
        segmentNumber = 0
        recordedVideoDir = os.path.join(recordingDir, 'Segment%03d' % segmentNumber)
    
    makedirsIfNeeded(recordedVideoDir)
    try:
        videoSettingses = SETTINGS_MODEL.get().objects.filter(width=videoFeed.settings.width,
                                                              height=videoFeed.settings.height)
        videoSettings = videoSettingses.first()
    except:
        # make a new one
        videoSettings = SETTINGS_MODEL.get()()
        videoSettings.width = videoFeed.settings.width
        videoSettings.height = videoFeed.settings.height
        videoSettings.save()

    videoSegment, created = SEGMENT_MODEL.get().objects.get_or_create(directoryName="Segment",
                                                                      segNumber=segmentNumber,
                                                                      indexFileName=settings.XGDS_VIDEO_INDEX_FILE_NAME, 
                                                                      endTime=None,
                                                                      settings=videoSettings,
                                                                      source=source,
                                                                      episode=episode)
    videoSegment.startTime = startTime
    videoSegment.save()
    videoSegment.broadcast('start')
    
    return {'videoFeed': videoFeed,
            'recordedVideoDir': recordedVideoDir,
            'segmentObj': videoSegment}


def invokeMakeNewSegment(sourcePK, recordingDir, recordingUrl, startTime, episodePK):
    ''' call makeNewSegment after we look up the source and episode '''
    source = VIDEO_SOURCE_MODEL.get().objects.get(pk=sourcePK)
    episode = EPISODE_MODEL.get().objects.get(pk=episodePK)
    return makeNewSegment(source, recordingDir, recordingUrl, startTime, episode)


def getCurrentSegmentForSource(sourcePK, episodePK):
    ''' Look for latest segment for given source and episode '''
    source = VIDEO_SOURCE_MODEL.get().objects.get(pk=sourcePK)
    episode = EPISODE_MODEL.get().objects.get(pk=episodePK)
    open_segments = source.videosegment_set.filter(episode=episode).filter(endTime=None)
    if open_segments.count() != 1:
        print "*** WARNING: there should be exactly one unfinished segment during recording! Found %d for source %s" % (open_segments.count(), source.shortName)
    return open_segments[0]


def startRecording(source, recordingDir, recordingUrl, startTime, episode):
    segmentInfo = makeNewSegment(source, recordingDir, recordingUrl, startTime, episode)

    if settings.PYRAPTORD_SERVICE is True:
        pyraptord = getPyraptordClient()

    assetName = source.shortName
    recorderService = '%s_recorder' % assetName
    recorderCommand = ''
    if settings.XGDS_VIDEO_RECORDING_METHOD == 'VLC':
        recorderCommand = ("%s %s --sout='#duplicate{dst=std{access=livehttp{seglen=6,splitanywhere=false,delsegs=false,numsegs=0,index=prog_index.m3u8,index-url=prog_index-#####.ts},mux=ts,dst=prog_index-#####.ts}}'"
                           % (settings.XGDS_VIDEO_VLC_PATH,
                              segmentInfo['videoFeed'].url))
    elif settings.XGDS_VIDEO_RECORDING_METHOD == 'HLS':
        scriptPath = os.path.join(settings.PROJ_ROOT, 'apps', 'xgds_video', 'scripts', 'recordHLS2.py')
        recorderCommand = ('%s --sourceUrl=%s --outputDir=%s --recorderId=%s --episodePK=%d --sourcePK=%d' % (scriptPath, segmentInfo['videoFeed'].url, segmentInfo['recordedVideoDir'], assetName, episode.pk, source.pk))
    
    print recorderCommand
    if settings.PYRAPTORD_SERVICE is True:
        #(pyraptord, recorderService)
        #stopPyraptordServiceIfRunning(pyraptord, recorderService)
        # the old process will suicide so let us look to see if it is done
        running = True
        count = 0
        while running and count < 10:
            oldStatus = pyraptord.getStatus(recorderService)
            if 'procStatus' not in oldStatus or oldStatus['procStatus'] != 'running':
                running = False
            time.sleep(0.5)

        pyraptord.updateServiceConfig(recorderService,
                                      {'command': recorderCommand,
                                       'cwd': segmentInfo['recordedVideoDir']})
        pyraptord.restart(recorderService)
        return recorderCommand
    return 'NO PYRAPTORD: ' + recorderCommand


def endSegment(segment, endTime):
    segment.endTime = endTime
    segment.save()
    segment.broadcast('end')


def stopRecording(source, endTime):
    assetName = source.shortName
    recorderService = '%s_recorder' % assetName

    if settings.XGDS_VIDEO_RECORDING_METHOD == 'HLS':
        # set the persistent flag to stop.
        #TODO make this better
        _cache.set("recordHLS:%s:stopRecording" % assetName, True)
        return 'SET MEMCACHE TO STOP HLS RECORDING FOR %s' % (assetName)

    else:
        # we need to set the endtime
        unended_segments = source.videosegment_set.filter(endTime=None)
        for segment in unended_segments:
            endSegment(segment, endTime)
    
        if settings.PYRAPTORD_SERVICE is True:
            pyraptord = getPyraptordClient('pyraptord')
            stopPyraptordServiceIfRunning(pyraptord, recorderService)
            return 'STOPPED PYCRORAPTOR SERVICES: ' + recorderService
    return 'NO PYRAPTORD: ' + recorderService

def stopRecordingAndCleanSegments(source, videoChunks):
    # call method to clear out giant file and kill recorder if needed
    stopRecording(source, timezone.now())
    for chunk in videoChunks:
        os.remove(chunk)

def getRecordedVideoDir(name):
    recordedVideoDir = ("%s/%s/Video/Recordings/" %
                        (settings.RECORDED_VIDEO_DIR_BASE,
                         name))
    return recordedVideoDir


def getRecordedVideoUrl(name):
    recordedVideoUrl = "%s%s/Video/Recordings/" % \
        (settings.RECORDED_VIDEO_URL_BASE,
         name)
    return recordedVideoUrl


def endActiveEpisode(end_time):
    episode = getClassByName(settings.XGDS_VIDEO_GET_ACTIVE_EPISODE)()
    if episode:
        episode.endTime = end_time
        episode.save()
        episode.broadcast('end')


# def publishSSE(channel, status, data):
#     if settings.XGDS_SSE and settings.XGDS_CORE_REDIS:
#         result = {'status': status,
#                   'data': data}
#         json_string = json.dumps(result, cls=DatetimeJsonEncoder)
#         publishRedisSSE(channel, SSE_TYPE, json_string)
#         return json_string

def setFudgeForSource(sourceName, seconds):
    key = 'VIDEO_FUDGE_' + sourceName;
    _cache.set(key, seconds)

    
def getFudgeForSource(sourceName):
    # use memcache to retrieve the frational seconds fudge factor for this video source
    key = 'VIDEO_FUDGE_' + sourceName;
    fudge = _cache.get(key)
    if not fudge:
        fudge = settings.XGDS_VIDEO_BUFFER_FUDGE_FACTOR
    return fudge
