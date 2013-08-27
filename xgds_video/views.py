# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

# from django.shortcuts import render_to_response
from django.http import HttpResponse
# from django.http import HttpResponseRedirect, HttpResponseForbidden, Http404
# from django.template import RequestContext
# from django.utils.translation import ugettext, ugettext_lazy as _

from geocamUtil.loader import getModelByName

from xgds_video import settings

VIDEO_TRACK_MODEL = getModelByName(settings.XGDS_VIDEO_TRACK_MODEL)
VIDEO_SEGMENT_MODEL = getModelByName(settings.XGDS_VIDEO_SEGMENT_MODEL)
VIDEO_EPISODE_MODEL = getModelByName(settings.XGDS_VIDEO_EPISODE_MODEL)


######################################################################
# HELPERS
######################################################################


def getZerorpcClient(clientName):
    ports = json.loads(file(settings.ZEROMQ_PORTS, 'r').read())
    rpcPort = ports[clientName]['rpc']
    client = zerorpc.Client(rpcPort)
    return client


def makedirsIfNeeded(path):
    if not os.path.exists(path):
        os.makedirs(path)
        os.chmod(path, settings.XGDS_VIDEO_NEW_DIR_PERMISSIONS)


def stopPyraptordServiceIfRunning(pyraptord, svcName):
    try:
        pyraptord.stop(svcName)
    except zerorpc.RemoteError:
        pass


def getRecordedVideoDir(episodeCode, segmentNumber):
    recordedVideoDir = "%s/%s/Video/Recordings/Segment%s" % \
        (settings.XGDS_VIDEO_RECORDING_DIR_BASE,
         episodeCode,
         segmentNumber)
    return recordedVideoDir


def getRecordedVideoSegment(episode, segIdx=None):
    """
    Helper for getActiveRecordedSegments
    """
    segments = VIDEO_SEGMENT_MODEL.objects.filter(episode=episode)
    if segIdx is None:
        if segments:
            segment = segments[-1]
        else:
            segment = None
    else:
        segment = segments[segIdx]
    return segment


def startRecording(track, episodeCode):
    segmentNumber = 0
    recordedVideoDir = getRecordedVideoDir(episodeCode, segmentNumber)
    logging.debug("Recorded video dir:", recordedVideoDir)
    makedirsIfNeeded(recordedVideoDir)

    episodes = VIDEO_EPISODE_MODEL.objects.filter(episodeCode=episodeCode)
    if episodes.count() == 0:
        episode = VIDEO_EPISODE_MODEL(episodeCode=episodeCode,
                                      startTime=datetime.datetime.now(),
                                      endTime=None,
                                      height=track.height,
                                      width=track.width)
    else:
        episode = episodes[0]
    videoSegment = VIDEO_SEGMENT_MODEL(path="Segment",
                                       startTime=episode.startTime,
                                       endTime=episode.endTime,
                                       segNumber=0,
                                       compressionRate=None,
                                       playbackDataRate=None,
                                       flightVideo=flightVideo,
                                       indexFileName=settings.XGDS_VIDEO_INDEX_FILE_NAME)
    videoSegment.save()

    if settings.PYRAPTORD_SERVICE is True:
	pyraptord = getZerorpcClient('pyraptord')

    trackCode = track.trackCode

    vlcSvc = '%s_vlc' % trackCode
    vlcCmd = ('%s %s %s'
              % (settings.XGDS_VIDEO_VLC_PATH,
                 track.url,
                 settings.XGDS_VIDEO_VLC_PARAMETERS))

    logging.debug(vlcCmd)

    segmenterSvc = '%s_segmenter' % trackCode
    videoDir = getRecordedVideoDir(episodeCode, segmentNumber)
    segmenterCmd = ('%s -b %s/%s/Video/Recordings/Segment%s -f %s -t 5 -S 3 -p -program-duration %s'
                    % (settings.XGDS_VIDEO_MEDIASTREAMSEGMENTER_PATH,
                       videoDir,
                       recordedVideoDir,
                       settings.XGDS_VIDEO_MAX_EPISODE_DURATION_MINUTES))

    logging.debug(segmenterCmd)

    if settings.PYRAPTORD_SERVICE is True:
	stopPyraptordServiceIfRunning(vlcSvc)
	stopPyraptordServiceIfRunning(segmenterSvc)

	pyraptord.updateServiceConfig(vlcSvc,
                                      {'command': vlcCmd})
	pyraptord.updateServiceConfig(segmenterSvc,
                                      {'command': segmenterCmd})

	pyraptord.restart(vlcSvc)
	pyraptord.restart(segmenterSvc)


def stopRecording(trackCode):
    if settings.PYRAPTORD_SERVICE is True:
	pyraptord = getZerorpcClient('pyraptord')
    vlcSvc = '%s_vlc' % trackCode
    segmenterSvc = '%s_segmenter' % trackCode

    if settings.PYRAPTORD_SERVICE is True:
	stopPyraptordServiceIfRunning(pyraptord, vlcSvc)
	stopPyraptordServiceIfRunning(pyraptord, segmenterSvc)


######################################################################
# VIEWS
######################################################################


def index(request):
    return HttpResponse('ok')


def liveVideoFeed(request, trackCode):
    templatePath = 'video_feeds.html'
    if trackCode.lower() == 'all':
        videoTracks = VIDEO_TRACK_MODEL.objects.all()
    else:
        videoTracks = VIDEO_TRACK_MODEL.objects.filter(trackCode=trackCode)
    return render_to_response(templatePath,
                              {'trackCode': trackCode,
                               'videoTracks': videoTracks},
                              context_instance=RequestContext(request))


def getRecordedSegmentsForEpisode(request, episodeCode):
    """
    Returns video segment given flight name
    """
    episode = Episode.objects.get(episodeCode=episodeCode)
    displaySegment = getRecordedVideoSegment(episode)
    currentTime = datetime.datetime.now().strftime("%H:%M")
    testSiteTime = getTestSiteTimeLabel(flight)

    return render_to_response('activeVideoSegments.html',
                              {'displaySegment': displaySegment,
                               'currentTime': currentTime,
                               'testSiteTimeAndZone': testSiteTime},
                              context_instance=RequestContext(request))


def playRecordedVideo(request, episodeCode, segmentNumber=0):
    track = VideoEpisode.objects.get(episodeCode=episodeCode)
    recordedVideoDir = getRecordedVideoDir(episodeCode, segmentNumber)
    indexFileHandle = open('%s/%s' % \
                           (recordedVideoDir, settings.XGDS_VIDEO_INDEX_FILE_NAME),
                           "r")
    indexFileData = indexFileHandle.read()
    indexFileData = "%s%s\n" % (indexFileData, settings.XGDS_VIDEO_INDEX_FILE_END_TAG)

    return HttpResponse(indexFileData, mimetype='application/x-mpegurl')
