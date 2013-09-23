from __future__ import division
import base64
import datetime
import pickle
import re
import sys
import stat
import logging
import glob
import os
from cStringIO import StringIO
import math
from datetime import date, datetime, timedelta
from uuid import uuid4
import cStringIO
import string
import pprint
import multiprocessing

from pyproj import Proj

try:
    from PIL import Image
except ImportError:
    import Image
try:
    import zerorpc
except ImportError:
    pass  # zerorpc not needed for most views

from django.contrib.auth import logout
from django.core import serializers, mail
from django.utils import simplejson
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import permission_required
from django.db.utils import IntegrityError
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseNotFound
from django.shortcuts import render, render_to_response
from django.template import RequestContext
from django.utils.encoding import *
from django.forms.formsets import formset_factory
from django.forms.models import modelformset_factory
#from django.views.generic.list_detail import object_list
from django.core.files.storage import get_storage_class
from django.core.files.base import ContentFile
from django.core.paginator import Paginator
from django.core.exceptions import ObjectDoesNotExist
from django.core.urlresolvers import reverse
from django.views.decorators.cache import cache_control

from geocamPycroraptor2 import prexceptions
from geocamUtil.KmlUtil import wrapKmlDjango
from xgds_planner import exportPlanKml
from plrpUtil import kmlTools, spreadsheetTools
from geocamUtil import anyjson as json

from plrpExplorer.models import *
from plrpExplorer import flightTools, settings
from plrpExplorer.FlightTimeOffset import flightTimeOffset
from plrpExplorer.flightTools import secondsToTime
from plrpExplorer.flightTools import decimalDegreesToDegreesMinutes
from plrpExplorer.flightTools import degreesMinutesWithHemisphereCode
from plrpExplorer.forms import *

from xgds_planner.exportPlan import getWaypointNumber, getRecordDict, \
    getPointRecord, getSegmentRecord
from xgds_data.views import specializedSearchForm, sortFormula, makeFilters, \
    recordRequest, log_and_render
from xgds_data.models import logEnabled
if logEnabled() :
    from xgds_data.models import RequestLog, RequestArgument, ResponseLog, ResponseArgument, ResponseList

from xgds_notes.forms import NoteForm

from operator import attrgetter

from xgds_notes.diggpaginator import *

from xgds_planner2 import (models,
                           planImporter,
                           choosePlanExporter)

from geocamUtil.loader import getModelByName, getClassByName
from xgds_video import settings
from xgds_video import util

SOURCE_MODEL = getModelByName(settings.XGDS_VIDEO_SOURCE_MODEL)
SETTINGS_MODEL = getModelByName(settings.XGDS_VIDEO_SETTINGS_MODEL)
FEED_MODEL = getModelByName(settings.XGDS_VIDEO_FEED_MODEL)
SEGMENT_MODEL = getModelByName(settings.XGDS_VIDEO_SEGMENT_MODEL)
EPISODE_MODEL = getModelByName(settings.XGDS_VIDEO_EPISODE_MODEL)

# NOTE_EXTRAS_FUNCTION = getClassByName(settings.XGS_VIDEO_NOTE_EXTRAS_FUNCTION)

# put a setting for the name of the function to call to generate extra text to insert in the form
# and then add the name of the plrpExplorer.views.getFlightFromFeed (context function)  extraNoteFormDataFunction
# feed has a source, look up active episode, (find episode with endtime of none) -- or use a known episode
# activeEpisode = EPISODE_MODEL.objects.filter(endTime=none)
# can find the groupflight that points to that episode
# and then find the flight in the group flight that has the same source.
def getNoteExtras(feed=None, episode=None, source=None):
    return None
    

def liveVideoFeed(request, feedName):
    feedData = []

    #get the active episodes
    currentEpisodes = EPISODE_MODEL.objects.filter(endTime = None)
    if feedName.lower() != 'all':
        videofeeds = FEED_MODEL.objects.filter(shortName=feedName).select_related('source')
        if videofeeds:
            form = NoteForm()
            form.index = 0
            form.source = videofeeds[0].source
            if form.source:
                form.update(form.source.getNoteExtras(currentEpisodes))
#             form.extras = NOTE_EXTRAS_FUNCTION(videofeeds[0], form.activeEpisode, videofeeds[0].source);
        feedData.append((videofeeds[0],form))
    else:
        videofeeds = FEED_MODEL.objects.filter(active=True)
        index = 0
        for feed in videofeeds:
            form = NoteForm()
            form.index = index
            form.source = feed.source
            if form.source:
                form.update(form.source.getNoteExtras(currentEpisodes))
            index += 1
            feedData.append((feed,form))
 
    return render_to_response("xgds_video/video_feeds.html",
        {'videoFeedData': feedData,
	     'currentEpisodes': currentEpisodes},
        context_instance=RequestContext(request)
    )


def getEarliestSegmentTime(segments):
    return min([seg.startTime for seg in segments])


def getLatestSegmentTime(segments):
    
    return max([seg.endTime for seg in segments])


def firstSegmentForSource(source, episode):
    if episode.endTime:
        segments = SEGMENT_MODEL.objects.filter(source=source, startTime__gte=episode.startTime,
						endTime__lte=episode.endTime)
    else:  #endTime of segment might be null if flight has not been stopped.
        segments = SEGMENT_MODEL.objects.filter(source=source, startTime__gte=episode.startTime) #XXX double check
    if segments:
        return segments[:1][0]
    return


"""
Helper for displayEpisodeRecordedVideo
"""
def makedirsIfNeeded(path):
    if not os.path.exists(path):
        os.makedirs(path)
        os.chmod(path, (stat.S_IRWXO | stat.S_IRWXG | stat.S_IRWXU))


"""
Returns first segment of all sources that are part of a given episode.
"""
def displayEpisodeRecordedVideo(request):#, episodeName, sourceName=None):
    episodeName = request.GET.get("episode")
    sourceName = request.GET.get("source")
    
    if not episodeName:
        episode = EPISODE_MODEL.objects.filter(endTime=None)[0]
    else:
        episode = EPISODE_MODEL.objects.get(shortName=episodeName)
    
    if sourceName is None:
        sources = SOURCE_MODEL.objects.all()
    else: 
        sources = [SOURCE_MODEL.objects.get(shortName=sourceName)]

    segments = []
    for source in sources:
        found = firstSegmentForSource(source,episode)
        if found:
            segments.append(found)
    
    earliestTime = None
    latestTime = None
    segmentsJson = None
    sourcesJson = None
    episodeJson = None
    if segments:
        earliestTime = util.convertUtcToLocal(getEarliestSegmentTime(segments))
        latestTime = util.convertUtcToLocal(getLatestSegmentTime(segments))

        segmentsJson = json.dumps([seg.getDict() for seg in segments], sort_keys=True, indent=4) 
        sourcesJson = json.dumps([source.getDict() for source in sources], sort_keys=True, indent=4)
        episodeJson = json.dumps(episode.getDict())

    return render_to_response('xgds_video/activeVideoSegments.html',
			{'segmentsJson': segmentsJson,
			 'baseUrl': settings.RECORDED_VIDEO_URL_BASE,
			 'episode': episode,
			 'episodeJson': episodeJson,
			 'earliestTime': earliestTime,
			 'latestTime': latestTime,
			 'sources': sources,
			},
			context_instance=RequestContext(request)
			)	
    

def getActiveFlights():
    return ActiveFlight.objects.all()


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
				segNumber= segmentNumber,
				indexFileName="prog_index.m3u8",
				startTime=startTime,
				endTime=None,
				settings=videoSettings,
				source=source)
    videoSegment.save()
   
    if settings.PYRAPTORD_SERVICE is True:
        pyraptord = getZerorpcClient('pyraptord')

    assetName = source.shortName #flight.assetRole.name

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

    print vlcCmd + "|" +segmenterCmd

    if settings.PYRAPTORD_SERVICE is True:
        stopPyraptordServiceIfRunning(vlcSvc)
        stopPyraptordServiceIfRunning(segmenterSvc)
	pyraptord.updateServiceConfig(vlcSvc,
				      {'command': vlcCmd})
	pyraptord.updateServiceConfig(segmenterSvc,
				      {'command': segmenterCmd})
	pyraptord.restart(vlcSvc)
	pyraptord.restart(segmenterSvc)


def stopRecording(source, endTime):
    if settings.PYRAPTORD_SERVICE is True:
        pyraptord = getZerorpcClient('pyraptord')
    assetName = source.shortName #flight.assetRole.name
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

