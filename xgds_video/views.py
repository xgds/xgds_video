from __future__ import division
import stat
import logging
import os

try:
    import zerorpc
except ImportError:
    pass  # zerorpc not needed for most views

from django.shortcuts import render_to_response
from django.template import RequestContext
#from django.views.generic.list_detail import object_list
from django.contrib import messages

from geocamUtil import anyjson as json

from xgds_notes.forms import  NoteForm

from geocamUtil.loader import getModelByName, getClassByName
from xgds_video import settings


SOURCE_MODEL = getModelByName(settings.XGDS_VIDEO_SOURCE_MODEL)
SETTINGS_MODEL = getModelByName(settings.XGDS_VIDEO_SETTINGS_MODEL)
FEED_MODEL = getModelByName(settings.XGDS_VIDEO_FEED_MODEL)
SEGMENT_MODEL = getModelByName(settings.XGDS_VIDEO_SEGMENT_MODEL)
EPISODE_MODEL = getModelByName(settings.XGDS_VIDEO_EPISODE_MODEL)


def getZerorpcClient(clientName):
    ports = json.loads(file(settings.ZEROMQ_PORTS, 'r').read())
    rpcPort = ports[clientName]['rpc']
    client = zerorpc.Client(rpcPort)
    return client


def stopPyraptordServiceIfRunning(pyraptord, svcName):
    try:
        pyraptord.stop(svcName)
    except zerorpc.RemoteError:
        pass


# put a setting for the name of the function to call to generate extra text to insert in the form
# and then add the name of the plrpExplorer.views.getFlightFromFeed (context function)  extraNoteFormDataFunction
# feed has a source, look up active episode, (find episode with endtime of none) -- or use a known episode
# activeEpisode = EPISODE_MODEL.objects.filter(endTime=none)
# can find the groupflight that points to that episode
# and then find the flight in the group flight that has the same source.
def getNoteExtras(episodes=None, source=None):
#     print "RETURNING NONE FROM BASE GET NOTE EXTRAS CLASS"
    return None

def callGetNoteExtras(episodes, source):
    if settings.XGDS_VIDEO_NOTE_EXTRAS_FUNCTION:
        noteExtrasFn = getClassByName(settings.XGDS_VIDEO_NOTE_EXTRAS_FUNCTION)
        return noteExtrasFn(episodes, source)
    else:
        return None


def liveVideoFeed(request, feedName):
    feedData = []

    #get the active episodes
    currentEpisodes = EPISODE_MODEL.objects.filter(endTime=None)
    if feedName.lower() != 'all':
        videofeeds = FEED_MODEL.objects.filter(shortName=feedName).select_related('source')
        if videofeeds:
            form = NoteForm()
            form.index = 0
            form.fields["index"] = 0
            form.source = videofeeds[0].source
            form.fields["source"] = videofeeds[0].source
            if form.fields["source"]:
                form.fields["extras"].initial = callGetNoteExtras(currentEpisodes, form.source)
                #form.extras = callGetNoteExtras(currentEpisodes, form.source)
                #it returned a dictionary which should match the form

        feedData.append((videofeeds[0], form))
    else:
        videofeeds = FEED_MODEL.objects.filter(active=True)
        index = 0
        for feed in videofeeds:
            form = NoteForm()
            form.index = index
            form.fields["index"] = index
            form.source = feed.source
            form.fields["source"] = feed.source
            if form.fields["source"]:
                form.fields["extras"].initial = callGetNoteExtras(currentEpisodes, form.source)
            index += 1
            feedData.append((feed, form))

    return render_to_response("xgds_video/video_feeds.html",
                              {'videoFeedData': feedData,
                               'currentEpisodes': currentEpisodes},
                              context_instance=RequestContext(request))


def getSegments(source, episode):
    """
    Helper for getting segments given source and episode.
    """
    if episode.endTime:
        segments = SEGMENT_MODEL.objects.filter(source=source, startTime__gte=episode.startTime,
                                                endTime__lte=episode.endTime)
    else:  # endTime of segment might be null if flight has not been stopped.
        segments = SEGMENT_MODEL.objects.filter(source=source, startTime__gte=episode.startTime)
    return segments


def makedirsIfNeeded(path):
    """
    Helper for displayEpisodeRecordedVideo
    """
    if not os.path.exists(path):
        os.makedirs(path)
        os.chmod(path, (stat.S_IRWXO | stat.S_IRWXG | stat.S_IRWXU))


def displayEpisodeRecordedVideo(request):
    """
    Returns first segment of all sources that are part of a given episode.
    """
    #XXX use jwplayer playlist to sequence multiple segments
    #http://www.longtailvideo.com/support/forums/jw-player/using-playlists/21104/playlist-to-chain-sequence-of-mp3s/

    episodeName = request.GET.get("episode")
    sourceName = request.GET.get("source")

    if not episodeName:
        searchCriteria = 'episodes'
        episodes = EPISODE_MODEL.objects.filter(endTime=None)[:1]
        if episodes:
            episode = episodes[0]
        else:
            episode = None
    else:
        searchCriteria = 'episodes named "%s"' % episodeName
        try:
            episode = EPISODE_MODEL.objects.get(shortName=episodeName)
        except EPISODE_MODEL.DoesNotExist:
            episode = None

    if sourceName is None:
        sources = SOURCE_MODEL.objects.all()
    else:
        sources = [SOURCE_MODEL.objects.get(shortName=sourceName)]

    if episode:
        segmentsDict = {}  # dictionary of segments in JSON
        for source in sources:
            found  = getSegments(source, episode)
            if found:
                segmentsDict[source.shortName] = [seg.getDict() for seg in found]

        segmentsJson = "null"
        episodeJson = "null"
        if segmentsDict:
            segmentsJson = json.dumps(segmentsDict, sort_keys=True, indent=4)
            episodeJson = json.dumps(episode.getDict())

            ctx = {
                'segmentsJson': segmentsJson,
                'baseUrl': settings.RECORDED_VIDEO_URL_BASE,
                'episode': episode,
                'episodeJson': episodeJson,
                'sources': sources,
            }
        else:
            messages.add_message(request, messages.ERROR, 'No Video Segments Exist')
            ctx = {
                'episode': episode,
                'episodeJson': episodeJson
            }
    else:
        messages.add_message(request, messages.ERROR, 'No Valid Episodes Exist')
        ctx = {'episode': None,
               'searchCriteria': searchCriteria}
    return render_to_response('xgds_video/activeVideoSegments.html',
                              ctx,
                              context_instance=RequestContext(request))


def startRecording(source, recordingDir, recordingUrl, startTime, maxFlightDuration):
    if not source.videofeed_set.all():
        logging.info("video feeds set is empty")
        return

    videoFeed = source.videofeed_set.all()[0]

    recordedVideoDir = None
    segmentNumber = None
    for i in xrange(1000):
        trySegDir = os.path.join(recordingDir, 'Segment%03d' % i)
        if not os.path.exists(trySegDir):
            recordedVideoDir = trySegDir
            segmentNumber = i
            break
    assert segmentNumber is not None

    print "Recorded video dir:", recordedVideoDir
    makedirsIfNeeded(recordedVideoDir)

    videoSettings = SETTINGS_MODEL(width=videoFeed.settings.width,
                                   height=videoFeed.settings.height,
                                   compressionRate=None,
                                   playbackDataRate=None)
    videoSettings.save()

    videoSegment = SEGMENT_MODEL(directoryName="Segment",
                                 segNumber=segmentNumber,
                                 indexFileName="prog_index.m3u8",
                                 startTime=startTime,
                                 endTime=None,
                                 settings=videoSettings,
                                 source=source)
    videoSegment.save()

    if settings.PYRAPTORD_SERVICE is True:
        pyraptord = getZerorpcClient('pyraptord')

    assetName = source.shortName  # flight.assetRole.name

    vlcSvc = '%s_vlc' % assetName
    vlcCmd = ('%s %s %s'
              % (settings.XGDS_VIDEO_VLC_PATH,
                 videoFeed.url,
                 settings.XGDS_VIDEO_VLC_PARAMETERS))

    segmenterSvc = '%s_segmenter' % assetName

    segmenterCmd = ('%s -b %sSegment%s -f %s -t 5 -S 3 -p -program-duration %s'
                    % (settings.XGDS_VIDEO_MEDIASTREAMSEGMENTER_PATH,
                       recordingUrl,
                       segmentNumber,
                       recordedVideoDir,
                       maxFlightDuration))

    print vlcCmd + "|" + segmenterCmd

    if settings.PYRAPTORD_SERVICE is True:
        stopPyraptordServiceIfRunning(pyraptord, vlcSvc)
        stopPyraptordServiceIfRunning(pyraptord, segmenterSvc)
        pyraptord.updateServiceConfig(vlcSvc,
                                      {'command': vlcCmd})
        pyraptord.updateServiceConfig(segmenterSvc,
                                      {'command': segmenterCmd})
        pyraptord.restart(vlcSvc)
        pyraptord.restart(segmenterSvc)


def stopRecording(source, endTime):
    if settings.PYRAPTORD_SERVICE is True:
        pyraptord = getZerorpcClient('pyraptord')
    assetName = source.shortName  # flight.assetRole.name
    vlcSvc = '%s_vlc' % assetName
    segmenterSvc = '%s_segmenter' % assetName

    #we need to set the endtime
    if source.videosegment_set.all().count() != 0:
        videoSegment = source.videosegment_set.all()[0]
        videoSegment.endTime = endTime
        videoSegment.save()

    if settings.PYRAPTORD_SERVICE is True:
        stopPyraptordServiceIfRunning(pyraptord, vlcSvc)
        stopPyraptordServiceIfRunning(pyraptord, segmenterSvc)
