# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

import platform

XGDS_VIDEO_NEW_DIR_PERMISSIONS = 0777
XGDS_VIDEO_MAX_EPISODE_DURATION_MINUTES = 180

XGDS_VIDEO_SOURCE_MODEL = 'xgds_video.VideoSource'
XGDS_VIDEO_SETTINGS_MODEL = 'xgds_video.VideoSettings'
XGDS_VIDEO_FEED_MODEL = 'xgds_video.VideoFeed'
XGDS_VIDEO_SEGMENT_MODEL = 'xgds_video.VideoSegment'
XGDS_VIDEO_EPISODE_MODEL = 'xgds_video.VideoEpisode'

XGDS_VIDEO_INDEX_FILE_NAME = "prog_index.m3u8"
XGDS_VIDEO_INDEX_FILE_END_TAG = "#EXT-X-ENDLIST"
if platform.system() == 'Linux':
    XGDS_VIDEO_VLC_PATH = '/usr/bin/vlc'
    XGDS_VIDEO_SEGMENTER_PATH = '/usr/local/bin/avconv'
    XGDS_VIDEO_SEGMENTER_ARGS = '-i pipe:0 -strict experimental -codec copy -map 0 -g 30 -f hls -hls_time 5 -hls_list_size 99999 prog_index.m3u8'
else:
    XGDS_VIDEO_VLC_PATH = "/Applications/VLC.app/Contents/MacOS/VLC"
    XGDS_VIDEO_SEGMENTER_PATH = "/usr/bin/mediastreamsegmenter"
    XGDS_VIDEO_SEGMENTER_ARGS = '-b %(recordingUrl)sSegment%(segmentNumber)s -f %(recordedVideoDir)s -t 5 -S 3 -p -program-duration %(maxFlightDuration)s'
XGDS_VIDEO_VLC_PARAMETERS = "--intf=dummy --sout='#std{access=file,mux=ts,dst=-}'"

XGDS_VIDEO_TIME_ZONE = {'name': 'Pacific', 'code': 'America/Los_Angeles'}

# set this in siteSettings.py. example: 'plrpExplorer.views.getNoteExtras'
XGDS_VIDEO_NOTE_EXTRAS_FUNCTION = None

# set this to true if you want to allow note input for logged in users when they are looking at video
XGDS_VIDEO_INCLUDE_NOTE_INPUT = False

# set this in siteSettings.py. example: 'mvpApp.views.extraVideoContext'
XGDS_VIDEO_EXTRA_VIDEO_CONTEXT = 'xgds_video.views.extraVideoContext'


# Delayed video information
XGDS_VIDEO_DELAY_MINIMUM_SEC = 20.0
XGDS_VIDEO_SEGMENT_SEC = 5.0

ZEROMQ_PORTS = 'path to ports.json file -- set this in siteSettings.py'

XGDS_VIDEO_GET_EPISODE_FROM_NAME = 'xgds_video.views.getEpisodeFromName'
XGDS_VIDEO_GET_ACTIVE_EPISODE = 'xgds_video.views.getActiveEpisode'
XGDS_VIDEO_GET_SOURCES_FROM_VEHICLE = 'xgds_video.views.getSourcesFromVehicle'

# set this in siteSettings.py example: DATA_URL
RECORDED_VIDEO_URL_BASE = None

# Path in data where you will find your video files
XGDS_VIDEO_INDEX_FILE_METHOD = 'xgds_video.util.getIndexFileSuffix'

# include this in your siteSettings.py BOWER_INSTALLED_APPS
XGDS_VIDEO_BOWER_INSTALLED_APPS = (
    'jwplayer',
    'https://datejs.googlecode.com/files/date.js',
    'masonry',
    'AC_QuickTime=https://java.net/projects/swinglabs/sources/svn/content/trunk/website/web/scripts/AC_QuickTime.js?raw=true',
)
