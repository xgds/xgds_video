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
from __future__ import division

import httplib
import json
import logging
import os
import datetime
import calendar
import m3u8
import zmq

from django.shortcuts import render
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth.models import User

from geocamUtil import dateparse
from geocamUtil.datetimeJsonEncoder import DatetimeJsonEncoder

from xgds_notes2.forms import NoteForm

from geocamUtil.loader import LazyGetModelByName, getClassByName
from django.conf import settings
from xgds_core.views import get_handlebars_templates
from xgds_video import util
from xgds_video.models import *  # pylint: disable=W0401
from xgds_map_server.views import getSearchForms
from django.http import HttpResponse, JsonResponse
from django.core.urlresolvers import reverse
from geocamPycroraptor2.views import getPyraptordClient, stopPyraptordServiceIfRunning
from dateutil.parser import parse as dateparser
from frame_grab import grab_frame
from xgds_core.flightUtils import getFlight

# introducting a dependency on xgds_image

SOURCE_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SOURCE_MODEL)
SETTINGS_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SETTINGS_MODEL)
FEED_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_FEED_MODEL)
SEGMENT_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_SEGMENT_MODEL)
EPISODE_MODEL = LazyGetModelByName(settings.XGDS_VIDEO_EPISODE_MODEL)
NOTE_MODEL = LazyGetModelByName(getattr(settings, 'XGDS_NOTES_NOTE_MODEL'))
CAMERA_MODEL = LazyGetModelByName(settings.XGDS_IMAGE_CAMERA_MODEL)
ACTIVE_FLIGHT_MODEL = LazyGetModelByName(settings.XGDS_CORE_ACTIVE_FLIGHT_MODEL)

logging.basicConfig(level=logging.INFO)


def grabFrame(request):
    start = request.POST.get('start_time')
    grab = request.POST.get('grab_time')

    if start is None:
        result_dict = {'status': 'error',
                       'error': 'You must specify video start time.'
                       }
        return JsonResponse(json.dumps(result_dict),
                            status=httplib.NOT_ACCEPTABLE, safe=False)
    if grab is None:
        result_dict = {'status': 'error',
                       'error': 'You must specify video grab time.'
                       }
        return JsonResponse(json.dumps(result_dict),
                            status=httplib.NOT_ACCEPTABLE, safe=False)

    starttime = dateparser(start)
    grabtime = dateparser(grab)
    img_bytes = grab_frame(request.POST.get('path'), starttime, grabtime)
    mimeType = "image/png"
    response = HttpResponse(img_bytes, content_type=mimeType)
    return response


def prepare_grab_frame(episode_name, source_short_name, grab_time):
    """
    Prepare to grab a frame returning a dictionary of useful info
    :param episode_name:
    :param source_short_name:
    :param grab_time:
    :return:
    """
    found_segment = getSegmentForTimeFromSource(episode_name, source_short_name, grab_time)
    if found_segment:
        index_file_path, seg = util.getIndexFilePath(episode_name, source_short_name, found_segment.segNumber)
        file_path = os.path.join(settings.DATA_ROOT, os.path.dirname(index_file_path))
        return {'segment': found_segment,
                'file_path': file_path}

    return None


def grab_frame_from_time(grab_time, vehicle, author=None, prefix=settings.XGDS_IMAGE_FRAME_GRAB_FILENAME_PREFIX):
    """
    Direct method to grab the frame given a time, without requests
    :param grab_time: the grab time datetime
    :param vehicle: the vehicle model
    :return: the ImageSet that was created
    """

    flight = getFlight(grab_time, vehicle)
    if not flight:
        raise Exception("No flight for time %s" % str(grab_time))

    # TODO we currently name episodes after group flights this may change.
    # Ideally have a link
    source = SOURCE_MODEL.get().objects.get(vehicle=vehicle)
    grab_info = prepare_grab_frame(flight.group.name, source.shortName, grab_time)
    print('grab info is ')
    print(grab_info)
    if grab_info:
        SAVE_IMAGE_FUNCTION = getClassByName('xgds_image.views.do_grab_frame')

        # TODO we are assuming there is a camera named for the vehicle
        camera = CAMERA_MODEL.get().objects.get(name=vehicle.name)
        if not author:
            # TODO assuming there is a user named camera
            author = User.objects.get(username='camera')
        return SAVE_IMAGE_FUNCTION(grab_info['segment'].startTime,
                                   grab_time,
                                   grab_info['file_path'],
                                   prefix,
                                   camera,
                                   author,
                                   vehicle)


def grabFrameFromSource(request, episode, source):
    """
    Look up the path and start time given a source and grab time.  Pass this to xgds_image to grab frame and save image set.
    :param request:
    :param episode: the episode name
    :param source: the source short name
    :return:
    """
    grab = request.POST.get('grab_time')
    if grab is None:
        result_dict = {'status': 'error',
                       'error': 'You must specify video grab time.'
                       }
        return JsonResponse(json.dumps(result_dict),
                            status=httplib.NOT_ACCEPTABLE, safe=False)

    grab_time = dateparser(grab)
    grab_info = prepare_grab_frame(str(episode), str(source), grab_time)

    if grab_info:
        # modify request to have new information
        request.POST._mutable = True
        request.POST['path'] = grab_info['file_path']
        request.POST['vehicle'] = grab_info['segment'].source.name
        request.POST['start_time'] = grab_info['segment'].startTime.isoformat()
        request.POST._mutable = False

        SAVE_IMAGE_FUNCTION = getClassByName('xgds_image.views.grab_frame_save_image')
        return SAVE_IMAGE_FUNCTION(request)

    result_dict = {'status': 'error',
                   'error': 'Could not find segment'
                   }
    return JsonResponse(json.dumps(result_dict),
                        status=httplib.NOT_ACCEPTABLE, safe=False)


def test(request):
    return render(request,"xgds_video/test.html")


def buildNoteForm(episodes, source, request, initial={}):
    moreInitial = callGetNoteExtras(episodes, source, request)
    if moreInitial:
        initial.update(moreInitial)
    return NoteForm(initial=initial)
    
    
# def liveImageStream(request):
#     # note forms
#     currentEpisodes = EPISODE_MODEL.get().objects.filter(endTime=None)
#     sources = SOURCE_MODEL.get().objects.all()
#     for source in sources:
#         source.form = buildNoteForm(currentEpisodes, source, request)
#     socketUrl = settings.XGDS_ZMQ_WEB_SOCKET_URL
#     if request.META['wsgi.url_scheme'] == 'https':
#         # must use secure WebSockets if web site is secure
#         socketUrl = re.sub(r'^ws:', 'wss:', socketUrl)
#
#     return render(request,
#                   "xgds_video/LiveImageStream.html",
#                   {'zmqURL': json.dumps(socketUrl),
#                    'sources': sources},
#                   )


# put a setting for the name of the function to call to generate extra text to insert in the form
# and then add the name of the plrpExplorer.views.getFlightFromFeed (context function)  extraNoteFormDataFunction
# feed has a source, look up active episode, (find episode with endtime of none) -- or use a known episode
# activeEpisode = EPISODE_MODEL.get().objects.filter(endTime=none)
# can find the groupflight that points to that episode
# and then find the flight in the group flight that has the same source.
# everything should be returned in a dictionary
def getNoteExtras(episodes=None, source=None, request=None):
    initial = {'source':source}
    return initial


def callGetNoteExtras(episodes, source, request):
    if settings.XGDS_VIDEO_NOTE_EXTRAS_FUNCTION:
        noteExtrasFn = getClassByName(settings.XGDS_VIDEO_NOTE_EXTRAS_FUNCTION)
        return noteExtrasFn(episodes, source, request)
    else:
        return None


def getSegments(source=None, episode=None):
    """
    Point to site settings to see real implementation of this function
    GET_SEGMENTS_METHOD
    """
    return None


def getEpisodeFromName(flightName):
    """
    Point to site settings to see real implementation of this function
    GET_EPISODE_FROM_NAME_METHOD
    """
    try:
        return EPISODE_MODEL.get().objects.get(shortName=flightName)
    except:
        return None


def getActiveEpisode():
    """
    Point to site settings to see real implementation of this function
    GET_ACTIVE_EPISODE
    """
    active_flights = ACTIVE_FLIGHT_MODEL.get().objects.all()
    for active in active_flights:
        if active.flight.group:
            try:
                episode = getClassByName(settings.XGDS_VIDEO_GET_EPISODE_FROM_NAME)(active.flight.group.name)
                return episode
            except:
                pass
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
    return render(request,
                  'xgds_video/map_recorded_playbacks.html',
                  ctx)


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
    noImagePath = "%s/xgds_video/images/NoImage.png" % settings.STATIC_ROOT
    noImageThumbnailPath = "%s/xgds_video/images/NoImage.thumbnail.png" % \
                           settings.STATIC_ROOT

    if not settings.XGDS_VIDEO_STILLS_ENABLED:
        if thumbnail:
            return buildImageResponse(noImageThumbnailPath, noImageThumbnailPath)
        else:
            return buildImageResponse(noImagePath, noImagePath)

    try:
        requestedTime = datetime.datetime.strptime(time, "%Y-%m-%d_%H-%M-%S")
    except:
        try:
            requestedTime = datetime.datetime.strptime(time, "%Y-%m-%d %H-%M-%S+00:00")
        except:
            requestedTime = datetime.datetime.strptime(time, "%Y-%m-%d %H:%M:%S+00:00")

    thumbnailPath = "%s/%s_%s.thumbnail.jpg" % (settings.IMAGE_CAPTURE_DIR, flightName, time)
    fullSizePath = "%s/%s_%s.jpg" % (settings.IMAGE_CAPTURE_DIR, flightName, time)

    # We generate full image and thumbnail together, so one check for 
    # existence should be OK.  If we don't find it, we generate one and cache it
    if not os.path.isfile(fullSizePath):
        captureStillImage(flightName, requestedTime)

    # The image should now be there, but just in case, we catch exceptions
    if thumbnail:
        thePath = thumbnailPath
        default = noImageThumbnailPath
    else:
        thePath = fullSizePath
        default = noImagePath
    response = buildImageResponse(thePath, default)
    if isDownload:
        response['Content-disposition'] = 'attachment; filename=%s' % os.path.basename(fullSizePath)
    return response


def buildImageResponse(thePath, default):
    # The image should now be there, but just in case, we catch exceptions
    try:
        f = open(thePath, "r")
    except IOError:
        f = open(default, "r")
    mimeType = "image/jpeg"
    imageBits = f.read()
    f.close()
    response = HttpResponse(imageBits, content_type=mimeType)
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
    
    form = buildNoteForm([episode], source, request, {'index':0})
# 
#     form = NoteForm()
#     form.index = 0
#     form.fields["index"] = 0
#     form.source = source
#     form.fields["source"] = source
#     form.fields["extras"].initial = callGetNoteExtras([episode], form.source, request, form)

    stillLocationFxn = getClassByName(settings.XGDS_VIDEO_GPS_LOCATION_METHOD)
    locationInfo = stillLocationFxn(flightName, timestamp)

    return render(request,
                  'xgds_video/video_still_viewer.html',
                  {'form': form,
                   'flightName': flightName,
                   'source': source,
                   'position': locationInfo,
                   'formattedTime': formattedTime,
                   'timeKey': time,
                   'event_timestring': event_timestring},
                  )


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
    chunkIndexPath = os.path.join(settings.RECORDED_VIDEO_DIR_BASE, getSegmentPath(flightName, None, s.segNumber), settings.INDEX_FILE_NAME)
#     chunkIndexPath = "%s/%s/Video/Recordings/Segment%03d/%s" % (
#         settings.RECORDED_VIDEO_DIR_BASE,
#         flightName, s.segNumber, settings.INDEX_FILE_NAME)
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
        segment = SEGMENT_MODEL.get().objects.get(episode=episode, startTime__lte=time,
                                           endTime__gte=time, source=source)
        return segment
    else:
        try:
            segment = SEGMENT_MODEL.get().objects.get(episode=episode, startTime__lte=time, endTime__gte=time, source=source)
        except:
            segment = SEGMENT_MODEL.get().objects.get(episode=episode, startTime__lte=time, endTime=None, source=source)
        return segment


def getSegmentForTimeFromSource(episode_name, source_short_name, time):
    episode = EPISODE_MODEL.get().objects.get(shortName=episode_name)
    source = SOURCE_MODEL.get().objects.get(shortName=source_short_name)
    try:
        segment = SEGMENT_MODEL.get().objects.get(episode=episode, startTime__lte=time, endTime__gte=time, source=source)
    except:
        segment = SEGMENT_MODEL.get().objects.get(episode=episode, startTime__lte=time, endTime=None, source=source)
    return segment


def getTimezoneFromFlightName(flightName):
    return settings.TIME_ZONE


def getEpisodeSegmentsJson(request, flightName=None, sourceShortName=None):
    """ flightName is either flightName or groupFlightName 
    Returns first segment of all sources that are part of a given episode.
    Used for both playing back videos from active episode and also
    for playing videos associated with each note.
    """
    try:
        episode = None
        if flightName:
            episode = getClassByName(settings.XGDS_VIDEO_GET_EPISODE_FROM_NAME)(flightName)
        else:
            episode = getClassByName(settings.XGDS_VIDEO_GET_ACTIVE_EPISODE)()
        if not episode:
            raise Exception('no episode')
    except:
        return HttpResponse(json.dumps({'error': 'No episode found'}), content_type='application/json', status=406)
    
    active = episode.endTime is None
    if not flightName:
        flightName = episode.shortName

    # get the segments
    segments = {}
    if sourceShortName:
        segments[sourceShortName] = [s.getDict() for s in episode.videosegment_set.filter(source__shortName=sourceShortName)]
    else:
        distinctSources = episode.videosegment_set.values('source__shortName').distinct()
        for theSource in distinctSources:
            sn = str(theSource['source__shortName'])
            segments[sn] = [ s.getDict() for s in episode.videosegment_set.filter(source__shortName=sn)]
        
    if not segments:
        return HttpResponse(json.dumps({'error': 'No segments found for ' + flightName}), content_type='application/json', status=406)

    result = []
    result.append({'active': active})
    result.append({'episode': episode.getDict()})
    result.append({'segments': segments})
    
    return HttpResponse(json.dumps(result, sort_keys=True, indent=4, cls=DatetimeJsonEncoder), content_type='application/json')


def getVideoContext(request, flightName=None, sourceShortName=None, time=None):
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
            try:
                requestedTime = datetime.datetime.strptime(time, "%Y-%m-%d %H:%M:%S+00:00")
            except:
                requestedTime = dateparse.parse_datetime(time)

    GET_ACTIVE_EPISODE_METHOD = getClassByName(settings.XGDS_VIDEO_GET_ACTIVE_EPISODE)
    activeepisode = GET_ACTIVE_EPISODE_METHOD()

    # this happens when user clicks on a flight name to view video
    if flightName:
        try:
            GET_EPISODE_FROM_NAME_METHOD = getClassByName(settings.XGDS_VIDEO_GET_EPISODE_FROM_NAME)
            episode = GET_EPISODE_FROM_NAME_METHOD(flightName)
            if not episode:
                raise Exception('no episode')

            if episode and episode == activeepisode:
                active = True
        except:
            return {}

    # this happens when user looks for live recorded
    if not episode:
        episode = activeepisode
        active = True
    if not episode:
        message = 'Video not found'
        if flightName:
            message += ' for ' + flightName
        else:
            message += ': no live video'
        messages.add_message(request, messages.ERROR, message)
        return redirect(reverse('error'))

    if episode:
        if not flightName:
            flightName = episode.shortName

    # get the segments
    segments = episode.videosegment_set.all()
    if not segments:
        msg = 'Video segments not found '
        if flightName:
            msg = msg + flightName
            return recordedVideoError(request, msg)

    sourceShortName = str(sourceShortName)
    if sourceShortName == 'None':
        sourceShortName = None
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
        source = SOURCE_MODEL.get().objects.get(pk=sourceDict['source'])
        sources.append(source)
        sourceVehicle[source.shortName] = source.vehicleName
        sourceSegments = segments.filter(source=source)
        segmentsDict[source.shortName] = [seg.getDict() for seg in sourceSegments]
        form = buildNoteForm([episode], source, request, {'index': index})
        source.form = form
        index = index + 1

    if flightName:
        if flightName.find('_') == -1:
            fullFlightName = flightName + "_" + sources[0].shortName
        else:
            fullFlightName = flightName
        GET_TIMEZONE_FROM_NAME_METHOD = getClassByName(settings.XGDS_VIDEO_GET_TIMEZONE_FROM_NAME)
        flightTimezone = GET_TIMEZONE_FROM_NAME_METHOD(str(fullFlightName))
    else:
        flightTimezone = GET_TIMEZONE_FROM_NAME_METHOD(None)

    if not segmentsDict:
        return recordedVideoError(request, "No video segments found " + flightName)
    segmentsJson = json.dumps(segmentsDict, sort_keys=True, indent=4, cls=DatetimeJsonEncoder)
    episodeJson = json.dumps(episode.getDict(), cls=DatetimeJsonEncoder)

    noteModelName = str(NOTE_MODEL.get().cls_type())
    noteForm = getClassByName(settings.XGDS_NOTES_BUILD_NOTES_FORM)({'vehicle__name':sourceShortName,
                                                                     'flight__group_name':episode.shortName})  #TODO this assumes the episode short name and group flight name are the same

    ctx = {
        'segmentsJson': segmentsJson,
        'isLive': active,
        'episode': episode,
        'episodeJson': episodeJson,
        'noteTimeStamp': requestedTime,  # in string format yy-mm-dd hh:mm:ss (in utc. converted to local time in js)
        'sources': sources,
        'flightName': flightName,
        'flightTZ': flightTimezone,
        'sourceVehicle': json.dumps(sourceVehicle),
        'SSE': settings.XGDS_SSE,
        'modelName': noteModelName,
        'searchModelDict': {noteModelName: settings.XGDS_MAP_SERVER_JS_MAP[noteModelName]},
        'searchForms': {noteModelName: [noteForm, settings.XGDS_MAP_SERVER_JS_MAP[noteModelName]]},
        'app': 'xgds_video/js/mapVideoApp.js',
        'templates': get_handlebars_templates(list(settings.XGDS_MAP_SERVER_HANDLEBARS_DIRS), 'XGDS_MAP_SERVER_HANDLEBARS_DIRS'),
    }

    if settings.XGDS_VIDEO_EXTRA_VIDEO_CONTEXT:
        extraVideoContextFn = getClassByName(settings.XGDS_VIDEO_EXTRA_VIDEO_CONTEXT)
        extraVideoContextFn(ctx)

    return ctx


def displayRecordedVideo(request, flightName=None, sourceShortName=None, time=None):
    """ TODO flightName is actually groupName """
    """
    Returns first segment of all sources that are part of a given episode.
    Used for both playing back videos from active episode and also
    for playing videos associated with each note.
    """

    ctx = getVideoContext(request, flightName, sourceShortName, time)
    active = ctx['isLive']

    theTemplate = 'xgds_video/map_recorded_playbacks.html'
    if active:
        theTemplate = 'xgds_video/map_active_playbacks.html'

    return render(request,
                  theTemplate,
                  ctx)


def displayLiveVideo(request, sourceShortName=None):
    """ Directly display RTSP feeds for the active episode.  
    This will either include all sources or be for a single source if it is passed in..
    """
    GET_ACTIVE_EPISODE_METHOD = getClassByName(settings.XGDS_VIDEO_GET_ACTIVE_EPISODE)
    episode = GET_ACTIVE_EPISODE_METHOD()
    if not episode:
        messages.add_message(request, messages.ERROR, 'There is no live video.')
        return redirect(reverse('error'))
    
    sources = []
    noteForms = []
    if sourceShortName:
        try:
            source = SOURCE_MODEL.get().objects.get(shortName=str(sourceShortName))
            sources.append(source)
            noteForms.append(buildNoteForm([episode], source, request, {'index':0}))
        except:
            pass
    else:
        # get sources and get feeds
        sources = SOURCE_MODEL.get().objects.filter(videosegment__episode = episode).distinct()
        for index,source in enumerate(sources):
            noteForms.append(buildNoteForm([episode], source, request, {'index':index}))
    
    noteModelName = str(NOTE_MODEL.get().cls_type())
#     noteForm = getClassByName(settings.XGDS_NOTES_BUILD_NOTES_FORM)({'vehicle__name':sourceShortName,
#                                                                      'flight__group_name':episode.shortName})
    
    theFilter = {}
    if settings.XGDS_VIDEO_NOTE_FILTER_FUNCTION:
        noteFilterFn = getClassByName(settings.XGDS_VIDEO_NOTE_FILTER_FUNCTION)
        theFilter = noteFilterFn(episode, sourceShortName)
    
    searchForms = getSearchForms(noteModelName, theFilter)
   
    ctx = {
        'episode': episode,
        'isLive': True,
        'zipped': zip(sources, noteForms),
        'SSE': settings.XGDS_SSE,
        'modelName': noteModelName,
        'flightName': episode.shortName,
        'flightTZ': settings.TIME_ZONE,
        'searchModelDict': {noteModelName:settings.XGDS_MAP_SERVER_JS_MAP[noteModelName]},
        'searchForms': searchForms,
#         'searchForms': {noteModelName: [noteForm,settings.XGDS_MAP_SERVER_JS_MAP[noteModelName]] },
        'app': 'xgds_video/js/mapVideoApp.js',
        'templates': get_handlebars_templates(list(settings.XGDS_MAP_SERVER_HANDLEBARS_DIRS), 'XGDS_MAP_SERVER_HANDLEBARS_DIRS'),
    }

    if settings.XGDS_VIDEO_EXTRA_VIDEO_CONTEXT:
        extraVideoContextFn = getClassByName(settings.XGDS_VIDEO_EXTRA_VIDEO_CONTEXT)
        extraVideoContextFn(ctx)

    theTemplate = 'xgds_video/map_live_playbacks.html'

    return render(request,
                  theTemplate,
                  ctx)


def noteFilterFunction(episode, sourceShortName):
    #TODO implement your own function that interprets episode and sourceShortName to make a useful note filter.
    return {}


def extraVideoContext(ctx):
    '''
    Add extra things to your context outside of xgds_video, like this:
#     mvpAppUrl = reverse('mvpApp_images_show_image', kwargs={'imageId': 'dummy'})
#     ctx['mvpAppUrl'] = mvpAppUrl
    and then make sure to update your settings.py to define where to find this method
    '''
    pass


def videoIndexFile(request, flightName=None, sourceShortName=None, segmentNumber=None):
    """
    modifies index file of recorded video to the correct host.
    """

    # use regex substitution to replace hostname, etc.
    (indexFileContents, indexFilePath) = util.getIndexFileContents(flightName, sourceShortName, segmentNumber)
    if not indexFileContents:
        return JsonResponse({'status': 'fail', 'exception': 'NO INDEX FILE CONTENTS'}, status=406)
    # return modified file in next line
    response = HttpResponse(indexFileContents, content_type="application/x-mpegurl")
    content_disposition = 'filename = "%s"' % os.path.basename(indexFilePath)
    response['Content-Disposition'] = content_disposition
    return response

