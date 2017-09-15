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

from glob import glob
import time
import os
import m3u8
import pytz
import re
import json
from threading import Timer
from datetime import datetime
from glob import glob
import traceback

from django.conf import settings
from django.db import models

from geocamUtil.models import UuidField
from geocamUtil.datetimeJsonEncoder import DatetimeJsonEncoder

from xgds_video import util
from xgds_video import recordingUtil
from xgds_core.views import getDelay

if settings.XGDS_CORE_REDIS:
    from xgds_core.redisUtil import publishRedisSSE


#  pylint: disable=C1001,E1101

#  incase settings is shadowed
# videoSettings = settings


class AbstractVideoSource(models.Model):
    # name: human-readable title
    name = models.CharField(max_length=128, blank=True, null=True,
                            help_text='Same as assetrole in NewFlight. ie, ROV', db_index=True)
    # shortName: a short mnemonic code suitable to embed in a URL
    shortName = models.CharField(max_length=32, blank=True, null=True, db_index=True,
                                 help_text='ie, ROV')
    uuid = UuidField(db_index=True)
    displayColor = models.CharField(max_length=56, blank=True, null=True,
                                    help_text='in html format. i.e. #7B3221')

    @property
    def vehicleName(self):
        return None

    class Meta:
        abstract = True

    def __unicode__(self):
        return u"%s(%s, name='%s')" % (self.__class__.__name__, self.pk, self.name)

    def getDict(self):
        return {"name": self.name, "shortName": self.shortName,
                "displayColor": self.displayColor, "uuid": self.uuid,
                "vehicleName": self.vehicleName}


class VideoSource(AbstractVideoSource):
    """
    A VideoSource represents a persistent source of video. It is used for grouping
    video data together.

    Depending on the application, this could be an asset role such as
    "research diver 1", or a particular camera, or something else. Driven
    by the needs of the application.
    """
    pass


class AbstractVideoSettings(models.Model):
    width = models.IntegerField()
    height = models.IntegerField()
    compressionRate = models.FloatField(null=True, blank=True)
    playbackDataRate = models.FloatField(null=True, blank=True)
    aspectRatio = models.CharField(max_length=8, default='16:9')


    def getDict(self):
        return {"width": self.width, 
                "height": self.height, 
                "compressionRate": self.compressionRate, 
                "playbackDataRate": self.playbackDataRate,
                "aspectRatio": self.aspectRatio
                }

    class Meta:
        abstract = True

    def __unicode__(self):
        return u"%s(%s, %s x %s)" % (self.__class__.__name__, self.pk, self.width, self.height)


class VideoSettings(AbstractVideoSettings):
    """
    A VideoSettings object records all of the metadata about a VideoSegment
    that we need for playback.
    """
    pass


DEFAULT_SETTINGS_FIELD = lambda: models.ForeignKey(VideoSettings, null=True, blank=True)
DEFAULT_SOURCE_FIELD = lambda: models.ForeignKey(VideoSource, null=True, blank=True)


class AbstractVideoFeed(models.Model):
    # name: human-readable title
    name = models.CharField(max_length=128, blank=True, null=True)
    # shortName: a short mnemonic code suitable to embed in a URL
    shortName = models.CharField(max_length=32, blank=True, null=True, db_index=True)
    # url: the url where you can watch the live video
    url = models.CharField(max_length=512, blank=False)
    realtimeUrl = models.CharField(max_length=512, blank=True, null=True)
    active = models.BooleanField(default=False)
    settings = 'set to DEFAULT_SETTINGS_FIELD() or similar in derived classes'
    source = 'set to DEFAULT_SOURCE_FIELD() or similar in derived classes'
    uuid = UuidField(db_index=True)

    class Meta:
        abstract = True

    def __unicode__(self):
        return (u"%s(%s, url='%s', shortName='%s', active=%s)" %
                (self.__class__.__name__,
                 self.pk,
                 self.url,
                 self.shortName,
                 self.active))


class VideoFeed(AbstractVideoFeed):
    """
    A VideoFeed gives you enough information to watch a live video.
    """
    settings = DEFAULT_SETTINGS_FIELD()
    source = DEFAULT_SOURCE_FIELD()


DEFAULT_EPISODE_FIELD = lambda: models.ForeignKey('xgds_video.VideoEpisode', null=True, blank=True)


class AbstractVideoSegment(models.Model):
    directoryName = models.CharField(max_length=256, help_text="ie. Segment")
    segNumber = models.PositiveIntegerField(null=True, blank=True, help_text="ie. 1", db_index=True)
    indexFileName = models.CharField(max_length=50, help_text="ie. prog_index.m3u8", default=settings.XGDS_VIDEO_INDEX_FILE_NAME)
    startTime = models.DateTimeField(null=True, blank=True, help_text="Second precision, utc. Start time needs to be later than episode start time", db_index=True)  # second precision, utc
    endTime = models.DateTimeField(null=True, blank=True, help_text="needs to be earlier than episode end time", db_index=True)
    settings = 'set to DEFAULT_SETTINGS_FIELD() or similar in derived classes'
    source = 'set to DEFAULT_SOURCE_FIELD() or similar in derived classes'
    episode = 'set to DEFAULT_EPISODE_FIELD() or similar in derived classes'
    uuid = UuidField()

    def adjustSegmentTimes(self, force=False):
        """ Read through the ts files in this segment's directory
        and calculate end time.
        This is used when restarting video because it died.
        """
        if force or not self.endTime:
            dir = os.path.join(settings.RECORDED_VIDEO_DIR_BASE, util.getSegmentPath(self.episode.shortName, self.source.name, self.segNumber))
            videoChunks = glob("%s/*.ts" % dir)
            videoChunks = sorted(videoChunks, key = lambda chunk: int(re.sub(".+prog_index-(\d+).ts", "\\1", chunk)))
            if len(videoChunks) > 0:
                (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(videoChunks[0])
                try:
                    index = m3u8.load('%s/%s' % (dir, self.indexFileName))
                    m3u8segment = index.segments[0]
                    duration = m3u8segment.duration
                except:
                    print "NO INDEX.M3U8 FILE for segment %s %d" % (self.episode.shortName, self.segNumber)
                    recordingUtil.stopRecordingAndCleanSegments(self.source, videoChunks)
                    return (None, None)
                
                startTime = mtime - duration
                startDT = datetime.fromtimestamp(startTime, pytz.utc)
                (mode, ino, dev, nlink, uid, gid, size, atime, mtime, ctime) = os.stat(videoChunks[-1])
                endTime = mtime
                endDT = datetime.fromtimestamp(endTime, pytz.utc)
                print "Segment: Start: %s End: %s" % (startDT, endDT)
                self.startTime = startDT
                self.endTime = endDT
                self.save()
        return (self.startTime, self.endTime)
        

    def getDict(self):
        return {"directoryName": self.directoryName,
                "segNumber": self.segNumber,
                "indexFileName": self.indexFileName,
                "source": self.source.getDict(),
                "startTime": self.startTime, #util.pythonDatetimeToJSON(self.startTime), # util.convertUtcToLocal(self.startTime)),
                "endTime": self.endTime, # util.pythonDatetimeToJSON(self.endTime), # util.convertUtcToLocal(self.endTime)),
                "timeZone": settings.XGDS_VIDEO_TIME_ZONE['name'],
                "settings": self.settings.getDict(),
                "episode": self.episode.getDict()}
    
    def getSseType(self):
        return self.__class__.__name__.lower()

    def broadcast(self, status):
        # By the time you call this you know that this instance has been newly inserted into the database and needs to broadcast itself
        try:
            if settings.XGDS_SSE and settings.XGDS_CORE_REDIS:
                result = {'status': status,
                          'data': self.getDict()}
                json_string = json.dumps(result, cls=DatetimeJsonEncoder)
                print 'seg:broadcast'
                print json_string
                publishRedisSSE(self.source.name, self.getSseType(), json_string)
                
                if status == 'start': 
                    result = {'status': 'play',
                              'data': self.getDict()}
                    json_string = json.dumps(result, cls=DatetimeJsonEncoder)
                    print 'seg:broadcast (delay)'
                    print json_string
                    t = Timer(getDelay() + settings.XGDS_VIDEO_BUFFER_FUDGE_FACTOR, publishRedisSSE, [self.source.name, self.getSseType(), json_string])
                    t.start()
                return json_string
        except:
            traceback.print_exc()

    class Meta:
        abstract = True

    def __unicode__(self):
        return (u"%s(%s,sourceName=%s, segNumber=%s, self.startTime=%s, self.endTime='%s', self.episode='%s')" %
                (self.__class__.__name__,
                 self.pk,
                 self.source.shortName,
                 self.segNumber,
                 self.startTime,
                 self.endTime,
                 self.episode))


class VideoSegment(AbstractVideoSegment):
    """
    A VideoSegment represents the data from a particular video source
    over a time interval with continuous video data. It points to a file
    on disk that contains the data.
    """
    settings = DEFAULT_SETTINGS_FIELD()
    source = DEFAULT_SOURCE_FIELD()
    episode = DEFAULT_EPISODE_FIELD()


class AbstractVideoEpisode(models.Model):
    # shortName: a short mnemonic code for the episode, suitable for embedding in a url
    shortName = models.CharField(max_length=32, null=True, blank=True, help_text="Same as flight_group name. ie, 20130711B", db_index=True)
    startTime = models.DateTimeField(null=True, blank=True, help_text="Should be earlier than start times of all video segments associated with this episode. Automatically created when the flight is started.", db_index=True)  # second precision, utc
    endTime = models.DateTimeField(null=True, blank=True, help_text="Should be later than end times of all video segments associated with this episode. If end time is empty, the flight has not stopped.", db_index=True)
    uuid = UuidField(db_index=True)
    sourceGroup = models.ForeignKey('VideoSourceGroup', null=True, blank=True, help_text="Newly added.")

    def getDict(self):
        episodeStartTime = None
        episodeEndTime = None

        if self.startTime:
            episodeStartTime = self.startTime #util.pythonDatetimeToJSON(self.startTime)

        if self.endTime:  # if endTime is none (when live stream has not ended)
            episodeEndTime = self.endTime # util.pythonDatetimeToJSON(self.endTime)

        return {"shortName": self.shortName,
                "startTime": episodeStartTime,
                "endTime": episodeEndTime}

    def getSseType(self):
        return self.__class__.__name__.lower()

    def broadcast(self, status):
        # By the time you call this you know that this instance has been newly inserted into the database and needs to broadcast itself
        try:
            if settings.XGDS_SSE and settings.XGDS_CORE_REDIS:
                result = {'status': status,
                          'data': self.getDict()}
                json_string = json.dumps(result, cls=DatetimeJsonEncoder)
                print 'epi:broadcast (delay)'
                print json_string
                t = Timer(getDelay(), publishRedisSSE, ['sse', self.getSseType(), json_string])
                t.start()
                return json_string
        except:
            traceback.print_exc()

    class Meta:
        abstract = True

    def __unicode__(self):
        return (u"%s(%s, shortName='%s', startTime=%s, endTime=%s)" %
                (self.__class__.__name__,
                 self.pk,
                 self.shortName,
                 repr(self.startTime),
                 repr(self.endTime)))


class VideoEpisode(AbstractVideoEpisode):
    """
    A VideoEpisode represents a time interval that has some operational
    meaning (such as a PLRP flight).

    A single VideoEpisode can span multiple VideoSources and each of
    those sources can contain many VideoSegments over the given time
    interval. We might not have continuous video data over the entire
    VideoEpisode time interval for any of the sources.
    """
    pass


######################################################################
# non-extensible classes

class VideoSourceGroup(models.Model):
    """
    A VideoSourceGroup represents an ordered list of VideoSource objects.
    """
    # name: human-readable title
    name = models.CharField(max_length=64, blank=True, null=True, help_text="human-readable title", db_index=True)
    # shortName: a short mnemonic code suitable to embed in a URL
    shortName = models.CharField(max_length=32, blank=True, null=True, db_index=True, help_text="a short mnemonic code suitable to embed in a URL")
    uuid = UuidField(db_index=True)

    def __unicode__(self):
        return (u"VideoSourceGroup(%s, name='%s', shortName='%s')"
                % (self.pk, self.name, self.shortName))


class AbstractVideoSourceGroupEntry(models.Model):
    """
    An entry in the ordered list of the VideoSourceGroup.
    """
    rank = models.PositiveIntegerField(db_index=True)
    source = 'set to DEFAULT_SOURCE_FIELD() or similar in derived classes'
    group = models.ForeignKey('VideoSourceGroup', related_name='sources')

    class Meta:
        abstract = True
        ordering = ['rank']

    def __unicode__(self):
        return (u"VideoSourceGroupEntry(%s, rank=%s, source='%s', group='%s')"
                % (self.pk, self.rank, self.source.name, self.group.name))


class VideoSourceGroupEntry(AbstractVideoSourceGroupEntry):
    source = DEFAULT_SOURCE_FIELD()


class AbstractStillFrame(models.Model):
    event_time = models.DateTimeField(null=True, blank=True, db_index=True)
    name = models.CharField(max_length=128, null=True, blank=True, db_index=True)
    width = models.IntegerField(null=True, blank=True)
    height = models.IntegerField(null=True, blank=True)
    url = models.CharField(max_length=512, null=True, blank=True)
    thumbnailUrl = models.CharField(max_length=512, null=True, blank=True)

    @property
    def videoUrl(self):
        return '' #TODO implement

    class Meta:
        abstract = True
        ordering = ['event_time']

    def __unicode__(self):
        return "%s" % (self.name)
