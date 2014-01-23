# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from django.db import models
from geocamUtil.models import UuidField
from xgds_video import settings
from xgds_video import util

# pylint: disable=C1001,E1101

#incase settings is shadowed
videoSettings = settings


class AbstractVideoSource(models.Model):
    # name: human-readable title
    name = models.CharField(max_length=128, blank=True, null=True,
                            help_text='Same as assetrole in NewFlight. ie, ROV')
    # shortName: a short mnemonic code suitable to embed in a URL
    shortName = models.CharField(max_length=32, blank=True, null=True, db_index=True,
                                  help_text='ie, ROV')
    uuid = UuidField(db_index=True)

    class Meta:
        abstract = True

    def __unicode__(self):
        return u'%s: %s' % (self.id, self.name)

    def getDict(self):
        return {"name": self.name, "shortName": self.shortName, "uuid": self.uuid}


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
    uuid = UuidField()

    def getDict(self):
        return {"width": self.width, "height": self.height, "compressionRate": self.compressionRate, "playbackDataRate": self.playbackDataRate}

    class Meta:
        abstract = True

    def __unicode__(self):
        return u'%s: (%s: %s)' % (self.id, self.width, self.height)


class VideoSettings(AbstractVideoSettings):
    """
    A VideoSettings object records all of the metadata about a VideoSegment
    that we need for playback.
    """
    pass


class AbstractVideoFeed(models.Model):
    # name: human-readable title
    name = models.CharField(max_length=128, blank=True, null=True)
    # shortName: a short mnemonic code suitable to embed in a URL
    shortName = models.CharField(max_length=32, blank=True, null=True, db_index=True)
    # url: the url where you can watch the live video
    url = models.CharField(max_length=512, blank=False)
    active = models.BooleanField(default=False)
    settings = models.ForeignKey(videoSettings.XGDS_VIDEO_SETTINGS_MODEL)
    source = models.ForeignKey(videoSettings.XGDS_VIDEO_SOURCE_MODEL)
    uuid = UuidField(db_index=True)

    class Meta:
        abstract = True

    def __unicode__(self):
        return (u'VideoFeed(%s, %s, %s)' %
                (self.url,
                 self.shortName,
                 self.active))


class VideoFeed(AbstractVideoFeed):
    """
    A VideoFeed gives you enough information to watch a live video.
    """
    pass



class AbstractVideoSegment(models.Model):
    directoryName = models.CharField(max_length=256, help_text="ie. Segment")
    segNumber = models.PositiveIntegerField(null=True, blank=True, help_text="ie. 1")
    indexFileName = models.CharField(max_length=50, help_text="ie. prog_index.m3u8")
    startTime = models.DateTimeField(null=True, blank=True, help_text="Second precision, utc. Start time needs to be later than episode start time")  # second precision, utc
    endTime = models.DateTimeField(null=True, blank=True, help_text="needs to be earlier than episode end time")
    settings = models.ForeignKey(videoSettings.XGDS_VIDEO_SETTINGS_MODEL, null=True, blank=True, help_text="usually (640: 360)")
    source = models.ForeignKey(videoSettings.XGDS_VIDEO_SOURCE_MODEL, null=True, blank=True, help_text="from video source. same as NewFlight's AssetRole.")
    uuid = UuidField()

    def getDict(self):
        return {"directoryName": self.directoryName, "segNumber": self.segNumber,
                "indexFileName": self.indexFileName, "source": self.source.getDict(),
                "startTime": util.pythonDatetimeToJSON(util.convertUtcToLocal(self.startTime)),
                "endTime": util.pythonDatetimeToJSON(util.convertUtcToLocal(self.endTime)),
                "timeZone": settings.XGDS_VIDEO_TIME_ZONE['name'],
                "settings": self.settings.getDict()}

    class Meta:
        abstract = True

    def __unicode__(self):
        return (u'VideoSegment(%s, %s, %s, %s)' %
                (self.id,
                 self.directoryName,
                 self.segNumber,
                 self.indexFileName))


class VideoSegment(AbstractVideoSegment):
    """
    A VideoSegment represents the data from a particular video source
    over a time interval with continuous video data. It points to a file
    on disk that contains the data.
    """
    pass


class AbstractVideoEpisode(models.Model):
    # shortName: a short mnemonic code for the episode, suitable for embedding in a url
    shortName = models.CharField(max_length=256, null=True, blank=True, help_text="Same as flight_group name. ie, 20130711B")
    startTime = models.DateTimeField(null=True, blank=True, help_text="Should be earlier than start times of all video segments associated with this episode. Automatically created when the flight is started.")  # second precision, utc
    endTime = models.DateTimeField(null=True, blank=True, help_text="Should be later than end times of all video segments associated with this episode. If end time is empty, the flight has not stopped.")
    uuid = UuidField()
    sourceGroup = models.ForeignKey('VideoSourceGroup', null=True, blank=True, help_text="Newly added.")

    def getDict(self):
        episodeStartTime = None
        episodeEndTime = None

        if self.startTime:
            episodeStartTime = util.pythonDatetimeToJSON(util.convertUtcToLocal(self.startTime))

        if self.endTime:  # if endTime is none (when live stream has not ended)
            episodeEndTime = util.pythonDatetimeToJSON(util.convertUtcToLocal(self.endTime))

        return {"shortName": self.shortName,
                "startTime": episodeStartTime,
                "endTime": episodeEndTime}

    class Meta:
        abstract = True

    def __unicode__(self):
        return (u'VideoEpisode(%s, %s, %s, %s)' %
                (self.id,
                 self.shortName,
                 self.startTime,
                 self.endTime))


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
    name = models.CharField(max_length=128, blank=True, null=True, help_text="human-readable title")
    # shortName: a short mnemonic code suitable to embed in a URL
    shortName = models.CharField(max_length=32, blank=True, null=True, db_index=True, help_text="a short mnemonic code suitable to embed in a URL")
    sources = models.ManyToManyField(settings.XGDS_VIDEO_SOURCE_MODEL, through='VideoSourceGroupEntry')
    uuid = UuidField(db_index=True)


class VideoSourceGroupEntry(models.Model):
    """
    An entry in the ordered list of the VideoSourceGroup.
    """
    rank = models.PositiveIntegerField()
    source = models.ForeignKey(settings.XGDS_VIDEO_SOURCE_MODEL)
    group = models.ForeignKey('VideoSourceGroup')

    class Meta:
        ordering = ['rank']
