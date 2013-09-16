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

from geocamUtil.loader import getModelByName
from xgds_video import settings
from xgds_video import util

SOURCE_MODEL = getModelByName(settings.XGDS_VIDEO_SOURCE_MODEL)
SETTINGS_MODEL = getModelByName(settings.XGDS_VIDEO_SETTINGS_MODEL)
FEED_MODEL = getModelByName(settings.XGDS_VIDEO_FEED_MODEL)
SEGMENT_MODEL = getModelByName(settings.XGDS_VIDEO_SEGMENT_MODEL)
EPISODE_MODEL = getModelByName(settings.XGDS_VIDEO_EPISODE_MODEL)

def liveVideoFeed(request, feedName):
 
    feedData = []
    if feedName.lower() != 'all':
        videofeeds = FEED_MODEL.objects.filter(shortName=feedName)
        if videofeeds:
            form = NoteForm()
            form.index = 0
        feedData.append((videofeeds[0],form))
    else:
        videofeeds = FEED_MODEL.objects.filter(active=True)
        index = 0
        for feed in videofeeds:
            form = NoteForm()
            form.index = index
            index += 1
            feedData.append((feed,form))
    
    return render_to_response("xgds_video/video_feeds.html",
        {'videoFeedData': feedData},
        context_instance=RequestContext(request)
    )


def getEarliestSegmentTime(segments):
    return min([seg.startTime for seg in segments])


def getLatestSegmentTime(segments):
    return max([seg.endTime for seg in segments])


def firstSegmentForSource(source, episode):
    segments = SEGMENT_MODEL.objects.filter(source=source, startTime__gte=episode.startTime,
				endTime__lte=episode.endTime)
    return segments[:1][0]


"""
Returns first segment of all sources that are part of a given episode.
"""
def displayEpisodeRecordedVideo(request, episodeName, sourceName=None):

    episode = EPISODE_MODEL.objects.get(shortName=episodeName)
    
    if sourceName == None:
	sources = SOURCE_MODEL.objects.all()
    else: 
	sources = [SOURCE_MODEL.objects.get(shortName=sourceName)]

    segments = [firstSegmentForSource(source,episode) for source in sources]  
 
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

def getRecordedVideoDir(flight, segmentNumber):
    recordedVideoDir = "%s/%s/Video/Recordings/Segment%s" % \
        (settings.RECORDED_VIDEO_DIR_BASE,
         flight.name,
         segmentNumber)
    return recordedVideoDir


def startRecording(flight):
    videoFeed = flight.assetRole.videofeed_set.all()[0]
    segmentNumber = 0
    recordedVideoDir = getRecordedVideoDir(flight, segmentNumber)
    print "Recorded video dir:", recordedVideoDir
    makedirsIfNeeded(recordedVideoDir)

    flightVideo = FlightVideo.objects.filter(flight=flight)
    if flightVideo.count() == 0:
        flightVideo = FlightVideo(flight=flight,
                                  startTime=datetime.datetime.now(),
                                  endTime=None,
                                  height=videoFeed.height,
                                  width=videoFeed.width)
        flightVideo.save()
    else:
        flightVideo = flightVideo[0]
    videoSegment = VideoSegment(path="Segment",
                                startTime=flightVideo.startTime,
                                endTime=flightVideo.endTime,
                                segNumber=0,
                                compressionRate=None,
                                playbackDataRate=None,
                                flightVideo=flightVideo,
                                indexFileName="prog_index.m3u8")
    videoSegment.save()
   
    if settings.PYRAPTORD_SERVICE is True:
	pyraptord = getZerorpcClient('pyraptord')

    assetName = flight.assetRole.name

    vlcSvc = '%s_vlc' % assetName
    vlcCmd = ('%s %s %s'
              % (settings.VLC_PATH,
                 videoFeed.url,
                 settings.VLC_PARAMETERS))

    print vlcCmd

    segmenterSvc = '%s_segmenter' % assetName
    segmenterCmd = ('%s -b %s/%s/Video/Recordings/Segment%s -f %s -t 5 -S 3 -p -program-duration %s'
                    % (settings.MEDIASTREAMSEGMENTER_PATH,
                       settings.RECORDED_VIDEO_URL_BASE,
                       flight.name,
                       segmentNumber,
                       recordedVideoDir,
                       settings.MAX_FLIGHT_DURATION))

    print segmenterCmd

    if settings.PYRAPTORD_SERVICE is True:
	stopPyraptordServiceIfRunning(vlcSvc)
	stopPyraptordServiceIfRunning(segmenterSvc)

	pyraptord.updateServiceConfig(vlcSvc,
                                  {'command': vlcCmd})
	pyraptord.updateServiceConfig(segmenterSvc,
                                  {'command': segmenterCmd})

	pyraptord.restart(vlcSvc)
	pyraptord.restart(segmenterSvc)


def playRecordedVideo(request, flightName, segmentNumber=0):
    flight = NewFlight.objects.get(name=flightName)
    recordedVideoDir = getRecordedVideoDir(flight, segmentNumber)
    indexFileHandle = open("%s/%s" % \
                               (recordedVideoDir, settings.VIDEO_INDEX_FILE_NAME),
                           "r")
    indexFileData = indexFileHandle.read()
    indexFileData = "%s%s\n" % (indexFileData, settings.VIDEO_INDEX_FILE_END_TAG)
    
    return HttpResponse(indexFileData, mimetype='application/x-mpegurl')
       

def stopRecording(flight):
    if settings.PYRAPTORD_SERVICE is True:
	pyraptord = getZerorpcClient('pyraptord')
    assetName = flight.assetRole.name
    vlcSvc = '%s_vlc' % assetName
    segmenterSvc = '%s_segmenter' % assetName
    
    if settings.PYRAPTORD_SERVICE is True:
	stopPyraptordServiceIfRunning(pyraptord, vlcSvc)
	stopPyraptordServiceIfRunning(pyraptord, segmenterSvc)

    
