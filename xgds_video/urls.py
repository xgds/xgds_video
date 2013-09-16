
from django.conf.urls.defaults import *

from xgds_video import settings
from xgds_video import views

urlpatterns = patterns(
    '',
    (r'liveVideoFeed/(?P<feedName>\w+)$', views.liveVideoFeed, {}, 'liveVideoFeed'),
    (r'recorded/(?P<episodeName>\w+)$',views.displayEpisodeRecordedVideo, {}, 'recorded'),
    (r'recorded/(?P<episodeName>\w+)/(?P<sourceName>\w+)$',views.displayEpisodeRecordedVideo, {}, 'recorded'),
    (r'playRecordedVideo/(?P<flightName>\w+)/(?P<segmentNumber>\d+)/$', views.playRecordedVideo, {}, 'playRecordedVideo'),
    
)


#    (r'^$', 'django.views.generic.simple.redirect_to',
#     {'url': settings.SCRIPT_NAME + 'plrpExplorer/'}),
