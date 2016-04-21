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
import logging
import os
import stat

from django.conf import settings

from django.db.models.aggregates import Max

from geocamPycroraptor2.views import getPyraptordClient, stopPyraptordServiceIfRunning

from geocamUtil.loader import LazyGetModelByName

SETTINGS_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SETTINGS_MODEL)
SEGMENT_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SEGMENT_MODEL)


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
    
def startRecording(source, recordingDir, recordingUrl, startTime, maxFlightDuration, episode):
    if not source.videofeed_set.all():
        logging.info("video feeds set is empty")
        return
    videoFeed = source.videofeed_set.all()[0]
    
    # figure out next segment number for this source and episode
    try:
        segmentNumber = SEGMENT_MODEL.get().objects.filter(episode=episode, source=source).aggregate(Max('segNumber'))
        recordedVideoDir = os.path.join(recordingDir, 'Segment%03d' % segmentNumber)
        if not emptySegmentDir(recordedVideoDir):
            segmentNumber = segmentNumber + 1
            recordedVideoDir = os.path.join(recordingDir, 'Segment%03d' % segmentNumber)
    except:
        segmentNumber = 0
    
#     recordedVideoDir = None
#     segmentNumber = None
#     for i in xrange(1000):
#         trySegDir = os.path.join(recordingDir, 'Segment%03d' % i)
#         if not os.path.exists(trySegDir) or not os.listdir(trySegDir):
#             recordedVideoDir = trySegDir
#             segmentNumber = i
#             break
#     assert segmentNumber is not None

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
                                                                      indexFileName="prog_index.m3u8",
                                                                      endTime=None,
                                                                      settings=videoSettings,
                                                                      source=source,
                                                                      episode=episode)
    videoSegment.startTime = startTime
    videoSegment.save()

    if settings.PYRAPTORD_SERVICE is True:
        pyraptord = getPyraptordClient()

    assetName = source.shortName  # flight.assetRole.name
    vlcSvc = '%s_vlc' % assetName
    vlcCmd = ('%s %s %s'
              % (settings.XGDS_VIDEO_VLC_PATH,
                 videoFeed.url,
                 settings.XGDS_VIDEO_VLC_PARAMETERS))
    segmenterSvc = '%s_segmenter' % assetName
    segmenterCmdTemplate = '%s %s' % (settings.XGDS_VIDEO_SEGMENTER_PATH,
                                      settings.XGDS_VIDEO_SEGMENTER_ARGS)

    segmenterCmdCtx = {
        'recordingUrl': recordingUrl,
        'segmentNumber': segmentNumber,
        'recordedVideoDir': recordedVideoDir,
        'maxFlightDuration': maxFlightDuration,
    }
    segmenterCmd = segmenterCmdTemplate % segmenterCmdCtx
    print vlcCmd + "|" + segmenterCmd
    if settings.PYRAPTORD_SERVICE is True:
        (pyraptord, vlcSvc)
        stopPyraptordServiceIfRunning(pyraptord, segmenterSvc)
        pyraptord.updateServiceConfig(vlcSvc,
                                      {'command': vlcCmd})
        pyraptord.updateServiceConfig(segmenterSvc,
                                      {'command': segmenterCmd,
                                       'cwd': recordedVideoDir})
        pyraptord.restart(vlcSvc)
        pyraptord.restart(segmenterSvc)


def stopRecording(source, endTime):
    if settings.PYRAPTORD_SERVICE is True:
        pyraptord = getPyraptordClient('pyraptord')
    assetName = source.shortName  # flight.assetRole.name
    vlcSvc = '%s_vlc' % assetName
    segmenterSvc = '%s_segmenter' % assetName

    # we need to set the endtime
    unended_segments = source.videosegment_set.filter(endTime=None)
    for segment in unended_segments:
        segment.endTime = endTime
        segment.save()

    if settings.PYRAPTORD_SERVICE is True:
        stopPyraptordServiceIfRunning(pyraptord, vlcSvc)
        stopPyraptordServiceIfRunning(pyraptord, segmenterSvc)


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