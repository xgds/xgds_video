

from django.conf.urls import patterns

from xgds_video import views

urlpatterns = patterns(
    'xgds_video.views',
    (r'liveVideoFeed/(?P<feedName>\w+)$', views.liveVideoFeed, {}, 'xgds_video_live'),
    (r'recorded/$', views.displayRecordedVideo, {}, 'xgds_video_recorded'),  # active live recorded video
    (r'videoIndexFile/(?P<flightAndSource>[^/]+)/(?P<segmentNumber>[^/]+)/prog_index.m3u8', views.videoIndexFile, {}, 'xgds_video_index_file'),
    (r'^noteVideo2013/(?P<flightName>\w+)/(?P<time>[^/]+)/$', views.displayRecordedVideo, {}, 'noteVideo2013'),  # recorded video for one note
    (r'^recorded/(?P<flightName>\w+)/$', views.displayRecordedVideo, {}, 'flight_video_recorded'),  # recorded video for one flight
    (r'^liveImageStream/$', views.liveImageStream, {}, 'live_image_stream'), # shows image stream from rover.
    (r'^archivedImageStream/$', views.archivedImageStream, {}, 'archived_image_stream')
    )