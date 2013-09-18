

from django.conf.urls.defaults import *

from xgds_video import settings
from xgds_video import views

urlpatterns = patterns(
    '',
    (r'liveVideoFeed/(?P<feedName>\w+)$', views.liveVideoFeed, {}, 'xgds_video_live'),
    (r'recorded/(?P<episodeName>\w+)$',views.displayEpisodeRecordedVideo, {}, 'xgds_video_recorded'),
    (r'recorded/(?P<episodeName>\w+)/(?P<sourceName>\w+)$',views.displayEpisodeRecordedVideo, {}, 'xgds_video_recorded'),
)


#    (r'^$', 'django.views.generic.simple.redirect_to',
#     {'url': settings.SCRIPT_NAME + 'plrpExplorer/'}),
