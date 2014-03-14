

from django.conf.urls import patterns

from xgds_video import views

urlpatterns = patterns(
    '',
    (r'liveVideoFeed/(?P<feedName>\w+)$', views.liveVideoFeed, {}, 'xgds_video_live'),
    (r'recorded/$', views.displayEpisodeRecordedVideo, {}, 'xgds_video_recorded'),
    (r'videoIndexFile/(?P<flightAndSource>[^/]+)/(?P<segmentNumber>[^/]+)/prog_index.m3u8', views.videoIndexFile, {}, 'xgds_video_index_file')
)
