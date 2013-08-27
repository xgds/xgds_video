# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from django.db import models

from geocamUtil.models import UuidField

from xgds_video import settings


class VideoTrack(models.Model):
    """
    A VideoTrack represents video from a particular camera.
    """
    # name: human-readable title for the track
    name = models.CharField(max_length=128, blank=True, null=True)
    # trackCode: a short mnemonic code for the track suitable to embed in a URL
    trackCode = models.CharField(max_length=32, blank=True, null=True)
    url = models.CharField(max_length=512, blank=False)
    width = models.IntegerField()
    height = models.IntegerField()
    uuid = UuidField()

    def __unicode__(self):
        return u'%s: %s' % (self.id, self.name)


class VideoSegment(models.Model):
    """
    A VideoSegment represents the data from a particular video track
    over a time interval with continuous video data. It points to a file
    on disk that contains the data.

    Several (not necessarily contiguous) VideoSegments can belong to a
    VideoEpisode.
    """
    path = models.CharField(max_length=256)  # directoryName
    startTime = models.DateTimeField(null=True, blank=True)  # second precision, utc
    endTime = models.DateTimeField(null=True, blank=True)
    segNumber = models.PositiveIntegerField(null=True, blank=True)
    compressionRate = models.FloatField(null=True, blank=True)
    playbackDataRate = models.FloatField(null=True, blank=True)
    episode = models.ForeignKey(settings.XGDS_VIDEO_EPISODE_MODEL, null=True)
    indexFileName = models.CharField(max_length=50)  # prog_index.m3u8
    uuid = UuidField()

    def __unicode__(self):
	return (u'VideoSegment(%s, %s, %s, %s, %s)' %
                (self.id,
                 self.path,
                 self.startTime,
                 self.endTime,
                 self.segNumber))


class VideoEpisode(models.Model):
    """
    A VideoEpisode represents the data from a particular video track
    over a time interval that has some operational meaning (such as a PLRP
    flight).

    A single VideoEpisode can contain many VideoSegments. We might not
    have continuous video data over the entire VideoEpisode time
    interval.
    """
    # episodeCode: a short mnemonic code for the episode, suitable for embedding in a url
    episodeCode = models.CharField(max_length=256, null=True, blank=True)
    startTime = models.DateTimeField(null=True, blank=True)  # second precision, utc
    endTime = models.DateTimeField(null=True, blank=True)
    height = models.PositiveIntegerField(null=True, blank=True)
    width = models.PositiveIntegerField(null=True, blank=True)
    uuid = UuidField()

    def __unicode__(self):
	return (u'VideoEpisode(%s, %s, %s, %s, %s)' %
                (self.id,
                 self.startTime,
                 self.endTime,
                 self.height,
                 self.width))
