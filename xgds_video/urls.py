# __BEGIN_LICENSE__
#Copyright (c) 2015, United States Government, as represented by the 
#Administrator of the National Aeronautics and Space Administration. 
#All rights reserved.
#
#The xGDS platform is licensed under the Apache License, Version 2.0 
#(the "License"); you may not use this file except in compliance with the License. 
#You may obtain a copy of the License at 
#http://www.apache.org/licenses/LICENSE-2.0.
#
#Unless required by applicable law or agreed to in writing, software distributed 
#under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR 
#CONDITIONS OF ANY KIND, either express or implied. See the License for the 
#specific language governing permissions and limitations under the License.
# __END_LICENSE__

from django.conf.urls import patterns

from xgds_video import views

urlpatterns = patterns(
    'xgds_video.views',
    (r'liveVideoFeed/(?P<feedName>\w+)$', views.liveVideoFeed, {'loginRequired': False}, 'xgds_video_live'),
    (r'videoIndexFile/(?P<flightName>[^/]+)/(?P<sourceShortName>[^/]+)/(?P<segmentNumber>[^/]+)/prog_index.m3u8', views.videoIndexFile, {'loginRequired': False}, 'xgds_video_index_file'),
    (r'^noteVideo2013/(?P<flightName>\w+)/(?P<time>[^/]+)/$', views.displayRecordedVideo, {}, 'noteVideo2013'),  # recorded video for one note
    # full-size still from video
    (r'^videoStillViewer/(?P<flightName>\w+)/(?P<time>[^/]+)/$', views.showStillViewerWindow, {},
     'videoStillViewer'), 
    # for AJAX-y pages where params are built later
    (r'^videoStillViewer/$', views.showStillViewerWindow, {}, 'videoStillViewer'),
    (r'^videoStill/(?P<flightName>\w+)/(?P<time>[^/]+).thumbnail.jpg/$', views.displayVideoStillThumb, {}, 'videoStillThumb'),  # still thumbnail
    (r'^videoStill/(?P<flightName>\w+)/(?P<time>[^/]+).jpg/$', views.displayVideoStill, {}, 'videoStill'),  # full-size still from video
    (r'^recorded/$', views.displayRecordedVideo, {'loginRequired': False}, 'xgds_video_recorded'),  # active live recorded video
    (r'^recorded/(?P<flightName>\w+)/$', views.displayRecordedVideo, {'loginRequired': False}, 'xgds_video_recorded'),  # active live recorded video
    (r'^recorded/(?P<flightName>\w+)/(?P<sourceShortName>\w+)/$', views.displayRecordedVideo, {'loginRequired': False}, 'xgds_video_recorded'),  # active live recorded video
    (r'^liveImageStream/$', views.liveImageStream, {'loginRequired': False}, 'live_image_stream'),  # shows image stream from rover.
    (r'^test/$', views.test, {}, 'test'),  # debug only
)
