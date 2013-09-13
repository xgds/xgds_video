
from django.conf.urls.defaults import *

from plrpExplorer import settings
from plrpExplorer import views

urlpatterns = patterns(
    '',
    (r'liveVideoFeed/(?P<shortName>\w+)$', views.liveVideoFeed, {}, 'liveVideoFeed'),
    (r'activeSegments/(?P<asset_role_name>\w+)$',views.getActiveRecordedSegments, {}, 'activeSegments'),
    (r'activeSegments/$',views.getActiveRecordedSegments, {}, 'activeSegments'),
    (r'playRecordedVideo/(?P<flightName>\w+)/(?P<segmentNumber>\d+)/$', views.playRecordedVideo, {}, 'playRecordedVideo'),
    
)


#    (r'^$', 'django.views.generic.simple.redirect_to',
#     {'url': settings.SCRIPT_NAME + 'plrpExplorer/'}),
