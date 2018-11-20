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

urlpatterns = [url(r'^videoStill/(?P<flightName>\w+)/(?P<time>[^/]+).thumbnail.jpg/$', views.displayVideoStillThumb, {}, 'videoStillThumb'),  # still thumbnail
               url(r'^videoStill/(?P<flightName>\w+)/(?P<time>[^/]+).jpg/$', views.displayVideoStill, {}, 'videoStill'),  # full-size still from video
               url(r'^videoStill/(?P<flightName>\w+)/(?P<time>[^/]+).jpg/(?P<isDownload>\d)/$', views.displayVideoStill, {}, 'xgds_video_downloadStill'),  # full-size still from video
               url(r'^recorded/(?P<flightName>\w+).json$', views.getEpisodeSegmentsJson, {}, 'xgds_video_recorded_json'),  # active recorded video json
               url(r'^recorded/(?P<flightName>\w+)/(?P<sourceShortName>\w+).json$', views.getEpisodeSegmentsJson, {}, 'xgds_video_recorded_json'),  # active recorded video json
               url(r'^grabFrame', views.grabFrame, {}, 'grab_frame'),  # grab frame
               ]
