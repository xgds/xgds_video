
from django.contrib import admin

from xgds_video.models import *  # pylint: disable=W0401

admin.site.register(VideoSource)
admin.site.register(VideoSettings)
admin.site.register(VideoFeed)
admin.site.register(VideoSegment)
admin.site.register(VideoEpisode)
admin.site.register(VideoSourceGroup)
admin.site.register(VideoSourceGroupEntry)
