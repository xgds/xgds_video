# __BEGIN_LICENSE__
#Copyright (c) 2015, United States Government, as represented by the 
#Administrator of the National Aeronautics and Space Administration. 
#All rights reserved.
#
#The xGDS platform is licensed under the Apache License, Version 2.0 
#(the "License"); you may not use this file except in compliance with the License. 
#You may obtain a copy of the License at 
#http://www.apache.org/licenses/LICENSE-2.0.
#
#Unless required by applicable law or agreed to in writing, software distributed 
#under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR 
#CONDITIONS OF ANY KIND, either express or implied. See the License for the 
#specific language governing permissions and limitations under the License.
# __END_LICENSE__

from __future__ import division
import json
import stat
import logging
import os
import datetime
import calendar
import re
import m3u8
import zmq

try:
    import zerorpc
except ImportError:
    pass  # zerorpc not needed for most views

from django.shortcuts import render_to_response
from django.shortcuts import redirect
from django.template import RequestContext
# from django.views.generic.list_detail import object_list
from django.contrib import messages

from geocamUtil import dateparse
from geocamUtil.datetimeJsonEncoder import DatetimeJsonEncoder

from xgds_notes.forms import NoteForm

from geocamUtil.loader import LazyGetModelByName, getClassByName
from django.conf import settings
from xgds_video import util
from xgds_video.models import *  # pylint: disable=W0401
from django.http import HttpResponse
from django.core.urlresolvers import reverse
from geocamPycroraptor2.views import getPyraptordClient, stopPyraptordServiceIfRunning

SOURCE_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SOURCE_MODEL)
SETTINGS_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SETTINGS_MODEL)
FEED_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_FEED_MODEL)
SEGMENT_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SEGMENT_MODEL)
EPISODE_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_EPISODE_MODEL)

logging.basicConfig(level=logging.INFO)


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
                               'sources': sources,
                               'INCLUDE_NOTE_INPUT': settings.XGDS_VIDEO_INCLUDE_NOTE_INPUT},
                              context_instance=RequestContext(request))


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
                               'currentEpisodes': currentEpisodes,
                               'INCLUDE_NOTE_INPUT': settings.XGDS_VIDEO_INCLUDE_NOTE_INPUT},
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


def recordedVideoError(request, message):
    # you are doomed.
    messages.add_message(request, messages.ERROR, message)
    ctx = {'episode': None}
    return render_to_response('xgds_video/video_recorded_playbacks.html',
                              ctx,
                              context_instance=RequestContext(request))


def captureStillImage(flightName, timestamp):
    stillLocationFxn = getClassByName(settings.XGDS_VIDEO_GPS_LOCATION_METHOD)
    locationInfo = stillLocationFxn(flightName, timestamp)
    (chunkPath, offsetInChunk) = getChunkfilePathAndOffsetForTime(flightName,
                                                                  timestamp)
    captureParams = {'frameCaptureOffset': offsetInChunk,
                     'imageSubject': flightName,
                     'collectionTimeZoneName': settings.TIME_ZONE,
                     'outputDir': settings.IMAGE_CAPTURE_DIR,
                     'chunkFilePath': chunkPath,
                     'thumbnailSize': {'width': 100, 'height': 56.25},
                     'contactInfo': 'http://www.pavilionlake.com',
                     'wallClockTime': calendar.timegm(timestamp.utctimetuple()),
                     'createThumbnail': True}
    if locationInfo:
        captureParams['locationInfo'] = {'latitude': locationInfo.latitude,
                                         'longitude': locationInfo.longitude,
                                         'altitude': locationInfo.depthMeters}
    #
    # Now, send request for still frame capture
    #
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect(settings.XGDS_VIDEO_STILL_GRAB_SERVICE)
    if chunkPath:  # did we really find a video chunk?  If so, grab frame
        socket.send(json.dumps(captureParams))
        resp = json.loads(socket.recv())
    else:
        resp = {'captureSuccess':False, 'imageUuid':None}

    if resp['captureSuccess']:
        logging.info("Image capture OK for %s at %s" % (flightName, timestamp))
    else:
        logging.info("Image capture failed for %s at %s" %
                     (flightName, timestamp))


def displayVideoStillThumb(request, flightName=None, time=None):
    return displayVideoStill(request, flightName, time, thumbnail=True)


def displayVideoStill(request, flightName=None, time=None, thumbnail=False, isDownload=0):
    """
    Returns a video still for a given flight at the requested time.  If the still already exists for that time, it is just displayed,
    otherwise a new one is created.
    """
    requestedTime = datetime.datetime.strptime(time, "%Y-%m-%d_%H-%M-%S")
    thumbnailPath = "%s/%s_%s.thumbnail.jpg" % (settings.IMAGE_CAPTURE_DIR, flightName, time)
    fullSizePath = "%s/%s_%s.jpg" % (settings.IMAGE_CAPTURE_DIR, flightName, time)
    noImagePath = "%s/xgds_video/images/NoImage.png" % settings.STATIC_ROOT
    noImageThumbnailPath = "%s/xgds_video/images/NoImage.thumbnail.png" % \
                           settings.STATIC_ROOT

    # We generate full image and thumbnail together, so one check for 
    # existence should be OK.  If we don't find it, we generate one and cache it
    if not os.path.isfile(fullSizePath):
        captureStillImage(flightName, requestedTime)

    # The image should now be there, but just in case, we catch exceptions
    if thumbnail:
        try:
            f = open(thumbnailPath, "r")
            mimeType = "image/jpeg"
        except IOError:
            f = open(noImageThumbnailPath, "r")
            mimeType = "image/jpeg"
    else:
        try:
            f = open(fullSizePath, "r")
            mimeType = "image/jpeg"
        except IOError:
            f = open(noImagePath, "r")
            mimeType = "image/png"

    imageBits = f.read()
    f.close()
    response = HttpResponse(imageBits, content_type=mimeType)
    if isDownload:
        response['Content-disposition'] = 'attachment; filename=%s' % os.path.basename(fullSizePath)
    return response


def showStillViewerWindow(request, flightName=None, time=None):
    if flightName is None:
        return HttpResponse(json.dumps({'error': {'code': -32199,
                                                  'message': 'You must provide params in URL, cheater.'}
                                        }),
                            content_type='application/json')

    timestamp = datetime.datetime.strptime(time, "%Y-%m-%d_%H-%M-%S")
    event_timestring = timestamp.strftime("%Y-%m-%d %H:%M:%S")
    formattedTime = timestamp.strftime('%H:%M:%S')

    # build up the form
    try:
        flightGroup, videoSource = flightName.split("_")
    except:
        return recordedVideoError(request, "This flight cannot be made into modern stills " + flightName)
    GET_EPISODE_FROM_NAME_METHOD = getClassByName(settings.XGDS_VIDEO_GET_EPISODE_FROM_NAME)
    episode = GET_EPISODE_FROM_NAME_METHOD(flightName)
    source = SOURCE_MODEL.get().objects.get(shortName=videoSource)
    form = NoteForm()
    form.index = 0
    form.fields["index"] = 0
    form.source = source
    form.fields["source"] = source
    form.fields["extras"].initial = callGetNoteExtras([episode], form.source, request)

    stillLocationFxn = getClassByName(settings.XGDS_VIDEO_GPS_LOCATION_METHOD)
    locationInfo = stillLocationFxn(flightName, timestamp)

    return render_to_response('xgds_video/video_still_viewer.html',
                              {'form': form,
                               'flightName': flightName,
                               'source': source,
                               'position': locationInfo,
                               'formattedTime': formattedTime,
                               'timeKey': time,
                               'event_timestring': event_timestring,
                               'INCLUDE_NOTE_INPUT': settings.XGDS_VIDEO_INCLUDE_NOTE_INPUT},
                              context_instance=RequestContext(request))


def getChunkfilePathAndOffsetForTime(flightName, time):
    # First locate video segment
    try:
        s = getSegmentForTime(flightName, time)
    except VideoSegment.DoesNotExist:
        logging.warning("No segment found for %s at %s" % (flightName, time))
        s = None
    except VideoSegment.MultipleObjectsReturned:
        logging.warning("More than one segment for %s at %s" %
                        (flightName, time))
        s = None
    if s is None:
        return (None, 0.0)  # Bail out if we didn't get exactly one segement

    # Calculate time offset in segment
    segmentOffset = (time - s.startTime).total_seconds()
    # Build path to m3u8 file
    # e.g. ~/xgds_plrp/data/20140623A_OUT/Video/Recordings
    chunkIndexPath = "%s/%s/Video/Recordings/Segment%03d/%s" % (
        settings.RECORDED_VIDEO_DIR_BASE,
        flightName, s.segNumber, settings.INDEX_FILE_NAME)
    try:
        chunkList = m3u8.load(chunkIndexPath).segments
    except IOError:
        logging.warning("Could not open M3U8 index for %s at %s" %
                        (flightName, time))
        return (None, 0.0)
    totalDuration = chunkList[0].duration
    chunkCounter = 0
    while (segmentOffset > totalDuration):
        chunkCounter += 1
        totalDuration += chunkList[chunkCounter].duration

    chunkOffset = segmentOffset - (totalDuration - chunkList[chunkCounter].duration)
    chunkFilePath = "%s/%s" % (chunkList[chunkCounter].base_uri, chunkList[chunkCounter].uri)
    return (chunkFilePath, chunkOffset)


def getSegmentForTime(flightName, time):
    try:
        flightGroup, videoSource = flightName.split("_")
        source = SOURCE_MODEL.get().objects.get(shortName=videoSource)
    except:
        return None
    GET_EPISODE_FROM_NAME_METHOD = getClassByName(settings.XGDS_VIDEO_GET_EPISODE_FROM_NAME)
    episode = GET_EPISODE_FROM_NAME_METHOD(flightName)
    if episode.endTime:
        segment = VideoSegment.objects.get(episode=episode, startTime__lte=time,
                                           endTime__gte=time, source=source)
        return segment
    else:
        try:
            segment = VideoSegment.objects.get(episode=episode, startTime__lte=time, endTime__gte=time, source=source)
        except:
            segment = VideoSegment.objects.get(episode=episode, startTime__lte=time, endTime=None, source=source)
        return segment


def getTimezoneFromFlightName(flightName):
    return 'America/Los_Angeles'


def displayRecordedVideo(request, flightName=None, sourceShortName=None, time=None):
    """ TODO flightName is actually groupName """
    """
    Returns first segment of all sources that are part of a given episode.
    Used for both playing back videos from active episode and also
    for playing videos associated with each note.
    """
    requestedTime = ""
    active = False
    episode = {}
    if time is not None:
        # TODO: this is a duplicate path for playing back video at a certain time, it is legacy from PLRP
        # and was not fully working there; merge these 2 ways of playing back from a time.
        # time is passed as string (yy-mm-dd hh:mm:ss)
        try:
            requestedTime = datetime.datetime.strptime(time, "%Y-%m-%d %H:%M:%S")
        except:
            requestedTime = dateparse.parse_datetime(time)
        requestedTime = util.pythonDatetimeToJSON(requestedTime)  # util.convertUtcToLocal(requestedTime))

    GET_ACTIVE_EPISODE_METHOD = getClassByName(settings.XGDS_VIDEO_GET_ACTIVE_EPISODE)
    activeepisode = GET_ACTIVE_EPISODE_METHOD()

    # this happens when user clicks on a flight name to view video
    if flightName:
        GET_EPISODE_FROM_NAME_METHOD = getClassByName(settings.XGDS_VIDEO_GET_EPISODE_FROM_NAME)
        episode = GET_EPISODE_FROM_NAME_METHOD(flightName)
        if (episode == activeepisode):
            active = True

    # this happens when user looks for live recorded
    if not episode:
        episode = activeepisode
        active = True
    if not episode:
        return redirect("xgds_video_flights")

    if episode:
        # print 'FOUND EPISODE %s' % episode.shortName
        if not flightName:
            flightName = episode.shortName

    # get the segments
    segments = episode.videosegment_set.all()
    if not segments:
        print 'NO SEGMENTS for %s ' %  flightName
        msg = 'Video segments not found '
        if flightName:
            msg = msg + flightName
            return recordedVideoError(request, msg)

    sourceShortName = str(sourceShortName)
    if sourceShortName:
        try:
            source = SOURCE_MODEL.get().objects.get(shortName=sourceShortName)
            segments = segments.filter(source=source)
        except:
            pass

    sources = []
    segmentsDict = {}  # dictionary of segments (in JSON) within given episode
    sourceVehicle = {}
    index = 0
    distinctSources = segments.values('source').distinct()
    for sourceDict in distinctSources:
        source = SOURCE_MODEL.get().objects.get(id=sourceDict['source'])
        sources.append(source)
        sourceVehicle[source.shortName] = source.vehicleName
        sourceSegments = segments.filter(source=source)
#         util.setSegmentEndTimes(segments.all(), episode, source)  # this passes back segments for this source.
        segmentsDict[source.shortName] = [seg.getDict() for seg in sourceSegments]
        form = NoteForm()
        form.index = index
        form.fields["index"] = index
        form.source = source
        form.fields["source"] = source
        form.fields["extras"].initial = callGetNoteExtras([episode], form.source, request)
        source.form = form
        index = index + 1

    if flightName:
        fullFlightName = flightName + "_" + sources[0].shortName
        GET_TIMEZONE_FROM_NAME_METHOD = getClassByName(settings.XGDS_VIDEO_GET_TIMEZONE_FROM_NAME)
        flightTimezone = GET_TIMEZONE_FROM_NAME_METHOD(str(fullFlightName))
    else:
        flightTimezone = GET_TIMEZONE_FROM_NAME_METHOD(None)

    if not segmentsDict:
        return recordedVideoError(request, "No video segments found " + flightName)
    segmentsJson = json.dumps(segmentsDict, sort_keys=True, indent=4, cls=DatetimeJsonEncoder)
    episodeJson = json.dumps(episode.getDict())

    ctx = {
        'segmentsJson': segmentsJson,
        'baseUrl': settings.RECORDED_VIDEO_URL_BASE,
        'episode': episode,
        'episodeJson': episodeJson,
        'noteTimeStamp': requestedTime,  # in string format yy-mm-dd hh:mm:ss (in utc. converted to local time in js)
        'sources': sources,
        'flightName': flightName,
        'flightTZ': flightTimezone,
        'sourceVehicle': json.dumps(sourceVehicle),
        'SSE': settings.XGDS_SSE,
        'INCLUDE_NOTE_INPUT': settings.XGDS_VIDEO_INCLUDE_NOTE_INPUT
    }

    if settings.XGDS_VIDEO_EXTRA_VIDEO_CONTEXT:
        extraVideoContextFn = getClassByName(settings.XGDS_VIDEO_EXTRA_VIDEO_CONTEXT)
        extraVideoContextFn(ctx)

    theTemplate = 'xgds_video/video_recorded_playbacks.html'
    if active:
        theTemplate = 'xgds_video/video_active_playbacks.html'

    return render_to_response(theTemplate,
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


def startRecording(source, recordingDir, recordingUrl, startTime, maxFlightDuration, episode):
    if not source.videofeed_set.all():
        logging.info("video feeds set is empty")
        return
    videoFeed = source.videofeed_set.all()[0]
    recordedVideoDir = None
    segmentNumber = None
    for i in xrange(1000):
        trySegDir = os.path.join(recordingDir, 'Segment%03d' % i)
        if not os.path.exists(trySegDir) or not os.listdir(trySegDir):
            recordedVideoDir = trySegDir
            segmentNumber = i
            break
    assert segmentNumber is not None

    makedirsIfNeeded(recordedVideoDir)
    try:
        videoSettingses = SETTINGS_MODEL.get().objects.filter(width=videoFeed.settings.width,
                                                              height=videoFeed.settings.height,
                                                              compressionRate=None,
                                                              playbackDataRate=None)
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


def videoIndexFile(request, flightName=None, sourceShortName=None, segmentNumber=None):
    """
    modifies index file of recorded video to the correct host.
    """
    # Look up path to index file
    GET_INDEX_FILE_METHOD = getClassByName(settings.XGDS_VIDEO_INDEX_FILE_METHOD)
    suffix = GET_INDEX_FILE_METHOD(flightName, sourceShortName, segmentNumber)

    # use regex substitution to replace hostname, etc.
    newIndex = util.updateIndexFilePrefix(suffix, settings.SCRIPT_NAME, flightName)
    # return modified file in next line
    response = HttpResponse(newIndex, content_type="application/x-mpegurl")
    response['Content-Disposition'] = 'filename = "prog_index.m3u8"'
    return response
