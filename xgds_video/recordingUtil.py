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
import time
import logging
import os
import stat

from django.utils import timezone
from django.conf import settings
from django.contrib import messages 
from django.shortcuts import redirect
from django.core.urlresolvers import reverse

from django.db.models.aggregates import Max

from geocamPycroraptor2.views import getPyraptordClient, stopPyraptordServiceIfRunning

from geocamUtil.loader import LazyGetModelByName, getClassByName
from scipy.stats.morestats import fligner


SETTINGS_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SETTINGS_MODEL)
SEGMENT_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SEGMENT_MODEL)
EPISODE_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_EPISODE_MODEL)
VIDEO_SOURCE_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SOURCE_MODEL)

def makedirsIfNeeded(path):
    """
    Helper for displayEpisodeRecordedVideo
    """
    if not os.path.exists(path):
        os.makedirs(path)
        os.chmod(path, (stat.S_IRWXO | stat.S_IRWXG | stat.S_IRWXU))


def emptySegmentDir(recordedVideoDir):
    if not os.listdir(recordedVideoDir):
        return True
    return False

def getVideoSource(sourceName):
    videoSource = VIDEO_SOURCE_MODEL.get().objects.get(shortName=sourceName)
    return videoSource

def splitFlightName(flightName):
    #this assumes flight name of episodeName_sourceName
    splits = flightName.split('_')
    episodeName = splits[0]
    sourceName = splits[1]
    return (episodeName, sourceName)

def startFlightRecording(request, flightName):
    (episodeName, sourceName) = splitFlightName(flightName)
    startTime=timezone.now()
    try:
        videoEpisode = EPISODE_MODEL.get().objects.get(shortName=episodeName)
        if videoEpisode.endTime:
            videoEpisode.endTime = None
            videoEpisode.save()
            messages.info(request, 'Cleared end time for episode ' + episodeName)
    except:
        videoEpisode = EPISODE_MODEL.get()(shortName=episodeName, startTime=startTime)
        videoEpisode.save()
        messages.info(request, 'Created video episode ' + episodeName)

    recordingDir = getRecordedVideoDir(flightName)
    recordingUrl = getRecordedVideoUrl(flightName)
    videoSource = getVideoSource(sourceName)
    commands = startRecording(videoSource, recordingDir,
                              recordingUrl, startTime,
                              settings.XGDS_VIDEO_MAX_EPISODE_DURATION_MINUTES,
                              episode=videoEpisode)
    messages.info(request, commands)
    return redirect(reverse('error'))

def stopFlightRecording(request, flightName):
    (episodeName, sourceName) = splitFlightName(flightName)
    stopTime = timezone.now()
    commands = stopRecording(getVideoSource(sourceName), stopTime)
    videoEpisode = EPISODE_MODEL.get().objects.get(shortName=episodeName)

    done = True
    #TODO this only will work if videosegment is the model
    for segment in videoEpisode.videosegment_set.all():
        if not segment.endTime:
            done = False
            break
    if done:
        videoEpisode.endTime = stopTime
        videoEpisode.save()
        commands = commands + ' & set episode end time ' + str(stopTime)
    messages.info(request, commands)
    return redirect(reverse('error'))
            
def startRecording(source, recordingDir, recordingUrl, startTime, maxFlightDuration, episode):
    if not source.videofeed_set.all():
        logging.info("video feeds set is empty")
        return
    videoFeed = source.videofeed_set.all()[0]
    
    # figure out next segment number for this source and episode
    try:
        maxSegmentNumber = SEGMENT_MODEL.get().objects.filter(episode=episode, source=source).aggregate(Max('segNumber'))
        segmentNumber = maxSegmentNumber['segNumber__max']
        recordedVideoDir = os.path.join(recordingDir, 'Segment%03d' % segmentNumber)
        if not emptySegmentDir(recordedVideoDir):
            segmentNumber = segmentNumber + 1
            recordedVideoDir = os.path.join(recordingDir, 'Segment%03d' % segmentNumber)
    except:
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

    # adjust start and end times for all prio segments
    existingSegments = SEGMENT_MODEL.get().objects.filter(source=source,episode=episode)
    for segment in existingSegments:
        segment.adjustSegmentTimes()
    videoSegment, created = SEGMENT_MODEL.get().objects.get_or_create(directoryName="Segment",
                                                                      segNumber=segmentNumber,
                                                                      indexFileName="prog_index.m3u8",
                                                                      endTime=None,
                                                                      settings=videoSettings,
                                                                      source=source,
                                                                      episode=episode)
    videoSegment.startTime = startTime
    videoSegment.save()

    if settings.PYRAPTORD_SERVICE is True:
        pyraptord = getPyraptordClient()

    assetName = source.shortName
    vlcSvc = '%s_vlc' % assetName
    vlcCmd = ("%s %s --sout='#duplicate{dst=std{access=livehttp{seglen=6,splitanywhere=false,delsegs=false,numsegs=0,index=prog_index.m3u8,index-url=prog_index-#####.ts},mux=ts,dst=prog_index-#####.ts}}'"
              % (settings.XGDS_VIDEO_VLC_PATH,
                 videoFeed.url))
#     print vlcCmd
    if settings.PYRAPTORD_SERVICE is True:
        (pyraptord, vlcSvc)
        stopPyraptordServiceIfRunning(pyraptord, vlcSvc)
        time.sleep(2)
        pyraptord.updateServiceConfig(vlcSvc,
                                      {'command': vlcCmd,
                                       'cwd': recordedVideoDir})
        pyraptord.restart(vlcSvc)
        return vlcCmd
    return 'NO PYRAPTORD: ' + vlcCmd

def stopRecording(source, endTime):
    if settings.PYRAPTORD_SERVICE is True:
        pyraptord = getPyraptordClient('pyraptord')
    assetName = source.shortName
    vlcSvc = '%s_vlc' % assetName

    # we need to set the endtime
    unended_segments = source.videosegment_set.filter(endTime=None)
    for segment in unended_segments:
        segment.endTime = endTime
        segment.save()
    
    if settings.PYRAPTORD_SERVICE is True:
        stopPyraptordServiceIfRunning(pyraptord, vlcSvc)
        return 'STOPPED PYCRORAPTOR SERVICES: ' + vlcSvc
    return 'NO PYRAPTORD: ' + vlcSvc


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
