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

from django.conf.urls import url
from django.views.generic.base import RedirectView, TemplateView

from xgds_video import views, recordingUtil

urlpatterns = [
    url(r'^liveVideo/$', views.displayLiveVideo, {'loginRequired': False}, 'xgds_video_live'),  # active live undelayed video
    url(r'^liveVideo/(?P<sourceShortName>[^/]+)/$', views.displayLiveVideo, {'loginRequired': False}, 'xgds_video_live_source'),  # active live undelayed video
    url(r'videoIndexFile/(?P<flightName>[^/]+)/(?P<sourceShortName>[^/]+)/(?P<segmentNumber>[^/]+)/prog_index.m3u8', views.videoIndexFile, {'loginRequired': False}, 'xgds_video_index_file'),
    url(r'^noteVideo/(?P<flightName>\w+)/(?P<time>[^/]+)/$', views.displayRecordedVideo, {}, 'xgds_video_recorded_time'),  # recorded video for one note
    url(r'^noteVideo/(?P<flightName>\w+)/(?P<sourceShortName>[^/]+)/(?P<time>[^/]+)/$', views.displayRecordedVideo, {}, 'xgds_video_recorded_time'),  # recorded video for one note
    # full-size still from video
    url(r'^videoStillViewer/(?P<flightName>\w+)/(?P<time>[^/]+)/$', views.showStillViewerWindow, {},'videoStillViewer'), 
    # for AJAX-y pages where params are built later
    url(r'^videoStillViewer/$', views.showStillViewerWindow, {}, 'videoStillViewer'),
    url(r'^videoStill/(?P<flightName>\w+)/(?P<time>[^/]+).thumbnail.jpg/$', views.displayVideoStillThumb, {}, 'videoStillThumb'),  # still thumbnail
    url(r'^videoStill/(?P<flightName>\w+)/(?P<time>[^/]+).jpg/$', views.displayVideoStill, {}, 'videoStill'),  # full-size still from video
    url(r'^videoStill/(?P<flightName>\w+)/(?P<time>[^/]+).jpg/(?P<isDownload>\d)/$', views.displayVideoStill, {}, 'xgds_video_downloadStill'),  # full-size still from video
    url(r'^recorded/$', views.displayRecordedVideo, {'loginRequired': False}, 'xgds_video_recorded'),  # active live recorded video
    url(r'^recorded/(?P<flightName>\w+)/$', views.displayRecordedVideo, {'loginRequired': False}, 'xgds_video_recorded'),  # active live recorded video
    url(r'^recorded/(?P<flightName>\w+)/(?P<sourceShortName>\w+)/$', views.displayRecordedVideo, {'loginRequired': False}, 'xgds_video_recorded'),  # active live recorded video
    url(r'^liveImageStream/$', views.liveImageStream, {'loginRequired': False}, 'live_image_stream'),  # shows image stream from rover.
    url(r'^test/$', views.test, {}, 'test'),  # debug only
    url(r'^recorded/(?P<flightName>\w+).json$', views.getEpisodeSegmentsJson, {'loginRequired': False}, 'xgds_video_recorded_json'),  # active recorded video json
    url(r'^recorded/(?P<flightName>\w+)/(?P<sourceShortName>\w+).json$', views.getEpisodeSegmentsJson, {'loginRequired': False}, 'xgds_video_recorded_json'),  # active recorded video json
    url(r'^stopRecording/(?P<flightName>\w+)', recordingUtil.stopFlightRecording, {'loginRequired': False}, 'xgds_video_stop_recording'), 
    url(r'^startRecording/(?P<flightName>\w+)', recordingUtil.startFlightRecording, {'loginRequired': False}, 'xgds_video_start_recording'),
    url(r'^testHLS$', TemplateView.as_view(template_name='xgds_video/testHLS.html'), {}, 'testHLS'),
                
    ]
