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

from django.conf.urls import url, include
from django.views.generic.base import RedirectView, TemplateView

from xgds_video import views, recordingUtil

urlpatterns = [url(r'^liveVideo/$', views.displayLiveVideo, {}, 'xgds_video_live'),  # active live undelayed video
               url(r'^liveVideo/(?P<sourceShortName>[^/]+)/$', views.displayLiveVideo, {}, 'xgds_video_live_source'),  # active live undelayed video
               url(r'videoIndexFile/(?P<flightName>[^/]+)/(?P<sourceShortName>[^/]+)/(?P<segmentNumber>[^/]+)/\w*\.m3u8', views.videoIndexFile, {}, 'xgds_video_index_file'),
               url(r'^noteVideo/(?P<flightName>\w+)/(?P<time>[^/]+)/$', views.displayRecordedVideo, {}, 'xgds_video_recorded_time'),  # recorded video for one note
               url(r'^noteVideo/(?P<flightName>\w+)/(?P<sourceShortName>[^/]+)/(?P<time>[^/]+)/$', views.displayRecordedVideo, {}, 'xgds_video_recorded_time'),  # recorded video for one note
               
               # full-size still from video
               url(r'^videoStillViewer/(?P<flightName>\w+)/(?P<time>[^/]+)/$', views.showStillViewerWindow, {},'videoStillViewer'), 
               # for AJAX-y pages where params are built later
               url(r'^videoStillViewer/$', views.showStillViewerWindow, {}, 'videoStillViewer'),
               
               url(r'^recorded/$', views.displayRecordedVideo, {}, 'xgds_video_recorded'),  # active live recorded video
               url(r'^recorded/(?P<flightName>\w+)/$', views.displayRecordedVideo, {}, 'xgds_video_recorded'),  # active live recorded video
               url(r'^recorded/(?P<flightName>\w+)/(?P<sourceShortName>\w+)/$', views.displayRecordedVideo, {}, 'xgds_video_recorded'),  # active live recorded video
               
               # url(r'^liveImageStream/$', views.liveImageStream, {}, 'live_image_stream'),  # shows image stream from rover.
    
               url(r'^test/$', views.test, {}, 'test'),  # debug only
               url(r'^testHLS$', TemplateView.as_view(template_name='xgds_video/testHLS.html'), {}, 'testHLS'),

               url(r'^stopRecording/(?P<flightName>\w+)', recordingUtil.stopFlightRecording, {}, 'xgds_video_stop_recording'), 
               url(r'^startRecording/(?P<flightName>\w+)', recordingUtil.startFlightRecording, {}, 'xgds_video_start_recording'),
    
               # Including these in this order ensures that reverse will return the non-rest urls for use in our server
               url(r'^rest/', include('xgds_video.restUrls')),
               url('', include('xgds_video.restUrls')),
               ]
