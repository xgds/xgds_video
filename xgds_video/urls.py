

from django.conf.urls import patterns

from xgds_video import views

urlpatterns = patterns(
    '',
    (r'liveVideoFeed/(?P<feedName>\w+)$', views.liveVideoFeed, {}, 'xgds_video_live'),
    (r'recorded/$', views.displayEpisodeRecordedVideo, {}, 'xgds_video_recorded'),
)
