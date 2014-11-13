from __future__ import division
import stat
import logging
import os
import datetime
import re

try:
    import zerorpc
except ImportError:
    pass  # zerorpc not needed for most views

from django.shortcuts import render_to_response
from django.template import RequestContext
# from django.views.generic.list_detail import object_list
from django.contrib import messages

from geocamUtil import anyjson as json

from xgds_notes.forms import NoteForm

from geocamUtil.loader import LazyGetModelByName, getClassByName
from xgds_video import settings
from xgds_video import util
from xgds_video.models import *  # pylint: disable=W0401
from django.http import HttpResponse
from django.core.urlresolvers import reverse

SOURCE_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SOURCE_MODEL)
SETTINGS_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SETTINGS_MODEL)
FEED_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_FEED_MODEL)
SEGMENT_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SEGMENT_MODEL)
EPISODE_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_EPISODE_MODEL)


def test(request):
    return render_to_response("xgds_video/test.html",
                              {},
                              context_instance=RequestContext(request))


def liveImageStream(request):
    # note forms
    currentEpisodes = EPISODE_MODEL.get().objects.filter(endTime=None)
    sources = SOURCE_MODEL.get().objects.all()
    for source in sources:
        form = NoteForm()
        form.index = 0
        form.fields["index"] = 0
        form.source = source
        form.fields["source"] = source
        if form.fields["source"]:
            form.fields["extras"].initial = callGetNoteExtras(currentEpisodes, form.source, request)
        source.form = form
    socketUrl = settings.XGDS_ZMQ_WEB_SOCKET_URL
    if request.META['wsgi.url_scheme'] == 'https':
        # must use secure WebSockets if web site is secure
        socketUrl = re.sub(r'^ws:', 'wss:', socketUrl)

    return render_to_response("xgds_video/LiveImageStream.html",
                              {'zmqURL': json.dumps(socketUrl),
                               'sources': sources},
                              context_instance=RequestContext(request))


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
# activeEpisode = EPISODE_MODEL.get().objects.filter(endTime=none)
# can find the groupflight that points to that episode
# and then find the flight in the group flight that has the same source.
def getNoteExtras(episodes=None, source=None, request=None):
    # print "RETURNING NONE FROM BASE GET NOTE EXTRAS CLASS"
    return None


def callGetNoteExtras(episodes, source, request):
    if settings.XGDS_VIDEO_NOTE_EXTRAS_FUNCTION:
        noteExtrasFn = getClassByName(settings.XGDS_VIDEO_NOTE_EXTRAS_FUNCTION)
        return noteExtrasFn(episodes, source, request)
    else:
        return None


def liveVideoFeed(request, feedName):
    feedData = []
    # get the active episodes
    currentEpisodes = EPISODE_MODEL.get().objects.filter(endTime=None)
    if feedName.lower() != 'all':
        videofeeds = FEED_MODEL.get().objects.filter(shortName=feedName).select_related('source')
        if videofeeds:
            form = NoteForm()
            form.index = 0
            form.fields["index"] = 0
            form.source = videofeeds[0].source
            form.fields["source"] = videofeeds[0].source
            if form.fields["source"]:
                form.fields["extras"].initial = callGetNoteExtras(currentEpisodes, form.source, request)
        feedData.append((videofeeds[0], form))
    else:
        videofeeds = FEED_MODEL.get().objects.filter(active=True)
        index = 0
        for feed in videofeeds:
            form = NoteForm()
            form.index = index
            form.fields["index"] = index
            form.source = feed.source
            form.fields["source"] = feed.source
            if form.fields["source"]:
                form.fields["extras"].initial = callGetNoteExtras(currentEpisodes, form.source, request)
            index += 1
            feedData.append((feed, form))

    return render_to_response("xgds_video/video_feeds.html",
                              {'videoFeedData': feedData,
                               'currentEpisodes': currentEpisodes},
                              context_instance=RequestContext(request))


def getSegments(source=None, episode=None):
    """
    Point to site settings to see real implementation of this function
    GET_SEGMENTS_METHOD
    """
    return None


def makedirsIfNeeded(path):
    """
    Helper for displayEpisodeRecordedVideo
    """
    if not os.path.exists(path):
        os.makedirs(path)
        os.chmod(path, (stat.S_IRWXO | stat.S_IRWXG | stat.S_IRWXU))


def getEpisodeFromName(flightName):
    """
    Point to site settings to see real implementation of this function
    GET_EPISODE_FROM_NAME_METHOD
    """
    return None


def getActiveEpisode(flightName):
    """
    Point to site settings to see real implementation of this function
    GET_ACTIVE_EPISODE
    """
    return None


def getSourcesFromVehicle(vehicleName):
    """
    Point to site settings to see real implementation of this function
    GET_SOURCES_FROM_VEHICLE
    """
    pass


def displayRecordedVideo(request, flightName=None, sourceShortName=None, time=None):
    """
    Returns first segment of all sources that are part of a given episode.
    Used for both playing back videos from active episode and also
    for playing videos associated with each note.
    """
    noteTime = ""
    episode = {}
    sources = []
    if time is not None:
        # TODO: this is a duplicate path for playing back video at a certain time, it is legacy from PLRP
        # and was not fully working there; merge these 2 ways of playing back from a time.
        # probably not calling it noteTime is clearer
        # time is passed as string (yy-mm-dd hh:mm:ss)
        noteTime = datetime.datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
        noteTime = util.pythonDatetimeToJSON(util.convertUtcToLocal(noteTime))
    # this happens when user clicks on a flight name to view video
    if flightName:
        GET_EPISODE_FROM_NAME_METHOD = getClassByName(settings.XGDS_VIDEO_GET_EPISODE_FROM_NAME)
        episode = GET_EPISODE_FROM_NAME_METHOD(flightName)
    # this happens when user looks for live recorded
    if not episode:
        GET_ACTIVE_EPISODE_METHOD = getClassByName(settings.XGDS_VIDEO_GET_ACTIVE_EPISODE)
        episode = GET_ACTIVE_EPISODE_METHOD()
    # get the sources associated with the episode
    if episode and episode.sourceGroup:
        if sourceShortName:
            source = SOURCE_MODEL.get().objects.filter(shortName=sourceShortName)[0]
            sources.append(source)
        else:
            entries = episode.sourceGroup.sources
            for entry in entries.all():
                sources.append(entry.source)
    else:
        # you are doomed.
        messages.add_message(request, messages.ERROR, 'Either Episode is not set for Group Flight of flight or episode source group has no sources.')
        ctx = {'episode': None}
        return render_to_response('xgds_video/video_recorded_playbacks.html',
                                  ctx,
                                  context_instance=RequestContext(request))
    if sources and (len(sources) != 0):
        segmentsDict = {}  # dictionary of segments (in JSON) within given episode
        index = 0
        sourcesWithNoSegments = []
        for source in sources:
            # trim the white spaces in source shortName
            cleanName = source.shortName.rstrip()
            if cleanName != source.shortName:
                source.shortName = cleanName
                source.save()
            if episode.endTime:
                segments = SEGMENT_MODEL.get().objects.filter(source=source, startTime__gte=episode.startTime, endTime__lte=episode.endTime).order_by("startTime")
            else:
                segments = SEGMENT_MODEL.get().objects.filter(source=source, startTime__gte=episode.startTime).order_by("startTime")
            if segments:
                util.setSegmentEndTimes(segments, episode, source)  # this passes back segments for this source.
                segmentsDict[source.shortName] = [seg.getDict() for seg in segments]
                form = NoteForm()
                form.index = index
                form.fields["index"] = index
                form.source = source
                form.fields["source"] = source
                form.fields["extras"].initial = callGetNoteExtras([episode], form.source, request)
                source.form = form
                index = index + 1
            else:  # if there are no segments, delete the source from 'sources' list.
                sourcesWithNoSegments.append(source)
        # remove from sources list.
        for source in sourcesWithNoSegments:
            sources.remove(source)
        segmentsJson = {}
        episodeJson = {}
        if segmentsDict:
            segmentsJson = json.dumps(segmentsDict, sort_keys=True, indent=4)
            episodeJson = json.dumps(episode.getDict())
            sourceVehicle = {}
            for source in sources:
                sourceVehicle[source.shortName] = source.vehicleName
            ctx = {
                'segmentsJson': segmentsJson,
                'baseUrl': settings.RECORDED_VIDEO_URL_BASE,
                'episode': episode,
                'episodeJson': episodeJson,
                'noteTimeStamp': noteTime,  # in string format yy-mm-dd hh:mm:ss (in utc. converted to local time in js)
                'sources': sources,
                'flightName': flightName,
                'sourceVehicle': json.dumps(sourceVehicle)
            }
        else:
            messages.add_message(request, messages.ERROR, 'No Video Segments Exist')
            ctx = {
                'episode': episode,
                'episodeJson': episodeJson
            }
    else:
        messages.add_message(request, messages.ERROR, 'No Valid Video Sources Exist')
        ctx = {'episode': None,
               'sources': None}

    if settings.XGDS_VIDEO_EXTRA_VIDEO_CONTEXT:
        extraVideoContextFn = getClassByName(settings.XGDS_VIDEO_EXTRA_VIDEO_CONTEXT)
        extraVideoContextFn(ctx)

    return render_to_response('xgds_video/video_recorded_playbacks.html',
                              ctx,
                              context_instance=RequestContext(request))


def extraVideoContext(ctx):
    '''
    Add extra things to your context outside of xgds_video, like this:
#     mvpAppUrl = reverse('mvpApp_images_show_image', kwargs={'imageId': 'dummy'})
#     ctx['mvpAppUrl'] = mvpAppUrl
    and then make sure to update your settings.py to define where to find this method
    '''
    pass


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
    videoSettingsModel = SETTINGS_MODEL.get()(width=videoFeed.settings.width,
                                              height=videoFeed.settings.height,
                                              compressionRate=None,
                                              playbackDataRate=None)
    videoSettingsModel.save()
    videoSegment = SEGMENT_MODEL.get()(directoryName="Segment",
                                       segNumber=segmentNumber,
                                       indexFileName="prog_index.m3u8",
                                       startTime=startTime,
                                       endTime=None,
                                       settings=videoSettingsModel,
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


def videoIndexFile(request, flightName=None, sourceShortName=None, segmentNumber=None):
    """
    modifies index file of recorded video to the correct host.
    """
    # Look up path to index file
    suffix = util.getIndexFileSuffix(flightName, sourceShortName, segmentNumber)
    # use regex substitution to replace hostname, etc.
    newIndex = util.updateIndexFilePrefix(suffix, settings.SCRIPT_NAME)
    # return modified file in next line
    response = HttpResponse(newIndex, content_type="application/x-mpegurl")
    response['Content-Disposition'] = 'filename = "prog_index.m3u8"'
    return response
