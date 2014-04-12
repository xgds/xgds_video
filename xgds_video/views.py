from __future__ import division
import stat
import logging
import os
import datetime

try:
    import zerorpc
except ImportError:
    pass  # zerorpc not needed for most views

from django.shortcuts import render_to_response
from django.http import HttpResponse
from django.template import RequestContext
# from django.views.generic.list_detail import object_list
from django.contrib import messages

from geocamUtil import anyjson as json

from xgds_notes.forms import NoteForm

from geocamUtil.loader import getModelByName, getClassByName
from xgds_video import settings
from xgds_video import util

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
    # get the active episodes
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
    segments = SEGMENT_MODEL.objects.filter(source=source, startTime__gte=episode.startTime)
    segmentSources = set([source for source in episode.sourceGroup.sources.all()])
    #if the segment's source group is part of the sourceGroup
    validSegments = []
    for segment in segments:
        if segment.source in segmentSources:
            validSegments.append(segment)
    return validSegments


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

    sourcesWithVideo = []
    
    if episode:
        segmentsDict = {}  # dictionary of segments (in JSON) within given episode
        sourceSegmentsDict = {} # dictionary of source and segments.
        index = 0
        for source in sources:
            # trim the white spaces in source shortName
            source.shortName = source.shortName.rstrip()
            source.save()
            found = getSegments(source, episode)
            if found: 
                sourceSegmentsDict[source.shortName] = found    
        #this command changes the value of segment object (sets end time)
        util.setSegmentEndTimes(sourceSegmentsDict, episode)
        
        for source in sources:
            found = getSegments(source, episode) 
            if found:
                segmentsDict[source.shortName] = [seg.getDict() for seg in found]
                #this is used for getSliderEndTime
                form = NoteForm()
                form.index = index
                form.fields["index"] = index
                form.source = source
                form.fields["source"] = source
                form.fields["extras"].initial = callGetNoteExtras([episode], form.source)
                source.form = form
                sourcesWithVideo.append(source)                
                index = index + 1
        
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
                'sources': sourcesWithVideo
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
    return render_to_response('xgds_video/video_recorded_playbacks.html',
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
        stopPyraptordServiceIfRunning(pyraptord, vlcSvc)
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
        pyraptord = getZerorpcClient('pyraptord')
    assetName = source.shortName  # flight.assetRole.name
    vlcSvc = '%s_vlc' % assetName
    segmenterSvc = '%s_segmenter' % assetName

    # we need to set the endtime
    if source.videosegment_set.all().count() != 0:
        videoSegment = source.videosegment_set.all()[0]
        videoSegment.endTime = endTime
        videoSegment.save()

    if settings.PYRAPTORD_SERVICE is True:
        stopPyraptordServiceIfRunning(pyraptord, vlcSvc)
        stopPyraptordServiceIfRunning(pyraptord, segmenterSvc)


"""
    modifies index file of recorded video to the correct host.
"""
def videoIndexFile(request, flightAndSource=None, segmentNumber=None):
    # Look up path to index file
    suffix = util.getIndexFileSuffix(flightAndSource, segmentNumber)
    
    # use regex substitution to replace hostname, etc.
    newIndex = util.updateIndexFilePrefix(suffix, settings.SCRIPT_NAME)
    #newIndex = util.updateIndexFilePrefix(path)
   
    # return modified file in next line
    response = HttpResponse(newIndex, content_type="application/x-mpegurl")
    response['Content-Disposition'] = 'filename = "prog_index.m3u8"'
    return response
