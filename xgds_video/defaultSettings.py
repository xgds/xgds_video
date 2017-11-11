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

import platform
from geocamUtil.SettingsUtil import getOrCreateArray

XGDS_VIDEO_NEW_DIR_PERMISSIONS = 0777
XGDS_VIDEO_MAX_EPISODE_DURATION_MINUTES = 180

# Size of playlist "window" for HLS live video.  Wowza and Teradek default to 3, but this can be adjusted on Wowza
XGDS_VIDEO_LIVE_PLAYLIST_SIZE = 3

XGDS_VIDEO_SOURCE_MODEL = 'xgds_video.VideoSource'
XGDS_VIDEO_SETTINGS_MODEL = 'xgds_video.VideoSettings'
XGDS_VIDEO_FEED_MODEL = 'xgds_video.VideoFeed'
XGDS_VIDEO_SEGMENT_MODEL = 'xgds_video.VideoSegment'
XGDS_VIDEO_EPISODE_MODEL = 'xgds_video.VideoEpisode'

XGDS_VIDEO_INDEX_FILE_NAME = "playlist.m3u8" # for vlc use prog_index.m3u8"
if platform.system() == 'Linux':
    XGDS_VIDEO_VLC_PATH = '/usr/bin/vlc'
    XGDS_VIDEO_SEGMENTER_PATH = '/usr/bin/avconv'
    XGDS_VIDEO_SEGMENTER_ARGS = '-i pipe:0 -strict experimental -codec copy -map 0 -g 30 -f hls -hls_time 5 -hls_list_size 99999 prog_index.m3u8'
else:
    XGDS_VIDEO_VLC_PATH = "/Applications/VLC.app/Contents/MacOS/VLC"
    XGDS_VIDEO_SEGMENTER_PATH = "/usr/bin/mediastreamsegmenter"
    XGDS_VIDEO_SEGMENTER_ARGS = '-b %(recordingUrl)sSegment%(segmentNumber)s -f %(recordedVideoDir)s -t 5 -S 3 -p -program-duration %(maxFlightDuration)s'
XGDS_VIDEO_VLC_PARAMETERS = "--intf=dummy --sout='#std{access=file,mux=ts,dst=-}'"

XGDS_VIDEO_TIME_ZONE = {'name': 'Pacific', 'code': 'America/Los_Angeles'}

# turn on if you can generate stills
XGDS_VIDEO_STILLS_ENABLED = False

# set this in siteSettings.py. example: 'plrpExplorer.views.getNoteExtras'
XGDS_VIDEO_NOTE_EXTRAS_FUNCTION = None

# set this to true if you want to allow note input for logged in users when they are looking at video
XGDS_VIDEO_INCLUDE_NOTE_INPUT = False

# override this in siteSettings.py. example: 'mvpApp.views.extraVideoContext'
XGDS_VIDEO_EXTRA_VIDEO_CONTEXT = 'xgds_video.views.extraVideoContext'

# override this in siteSettings.py
XGDS_VIDEO_NOTE_FILTER_FUNCTION = 'xgds_video.views.noteFilterFunction'

# support turning off for testing
XGDS_VIDEO_ON = False

# Delayed video information
XGDS_VIDEO_DELAY_MINIMUM_SEC = 20.0
XGDS_VIDEO_SEGMENT_SEC = 5.0
XGDS_VIDEO_DELAY_SECONDS = 0

ZEROMQ_PORTS = 'path to ports.json file -- set this in siteSettings.py'

XGDS_VIDEO_GET_EPISODE_FROM_NAME = 'xgds_video.views.getEpisodeFromName'
XGDS_VIDEO_GET_ACTIVE_EPISODE = 'xgds_video.views.getActiveEpisode'
XGDS_VIDEO_GET_SOURCES_FROM_VEHICLE = 'xgds_video.views.getSourcesFromVehicle'
XGDS_VIDEO_GET_TIMEZONE_FROM_NAME = 'xgds_video.views.getTimezoneFromFlightName'


# set this in siteSettings.py example: DATA_URL
RECORDED_VIDEO_DIR_BASE = None
RECORDED_VIDEO_URL_BASE = None


# Path in data where you will find your video files
# This returns a tuple of the path to the index file and the segment that corresponds to that index file.
XGDS_VIDEO_INDEX_FILE_METHOD = 'xgds_video.util.getIndexFilePath'

# Method for looking up delay from a flight
XGDS_VIDEO_DELAY_AMOUNT_METHOD = 'xgds_video.util.getDelaySeconds'

# The old method is VLC
XGDS_VIDEO_RECORDING_METHOD = 'HLS'

XGDS_VIDEO_NUM_BUFFERED_CHUNKS = 3
XGDS_VIDEO_EXPECTED_CHUNK_DURATION_SECONDS = 2
XGDS_VIDEO_BUFFER_FUDGE_FACTOR = XGDS_VIDEO_NUM_BUFFERED_CHUNKS * XGDS_VIDEO_EXPECTED_CHUNK_DURATION_SECONDS + 15


# Override this in your siteSettings to include a key for enterprise JWPLAYER
"""

 IMPORTANT YOU MUST INCLUDE THIS IN siteSettings
 TEMPLATE_CONTEXT_PROCESSORS = (global_settings.TEMPLATE_CONTEXT_PROCESSORS + (
     ...
     'xgds_video.context_processors.SettingsContextProcessor.SettingsContextProcessor'
 """
JWPLAYER_KEY = None

BOWER_INSTALLED_APPS = getOrCreateArray('BOWER_INSTALLED_APPS')
BOWER_INSTALLED_APPS += ['jwplayer=https://ssl.p.jwpcdn.com/player/download/jwplayer-7.10.7.zip',
                         'moment',
                         'moment-timezone',
                         'packery'
                         ]
