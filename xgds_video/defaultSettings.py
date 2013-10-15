# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

XGDS_VIDEO_NEW_DIR_PERMISSIONS = 0777
XGDS_VIDEO_MAX_EPISODE_DURATION_MINUTES = 180

XGDS_VIDEO_SOURCE_MODEL = 'xgds_video.VideoSource'
XGDS_VIDEO_SETTINGS_MODEL = 'xgds_video.VideoSettings'
XGDS_VIDEO_FEED_MODEL = 'xgds_video.VideoFeed'
XGDS_VIDEO_SEGMENT_MODEL = 'xgds_video.VideoSegment'
XGDS_VIDEO_EPISODE_MODEL = 'xgds_video.VideoEpisode'

XGDS_VIDEO_INDEX_FILE_NAME = "prog_index.m3u8"
XGDS_VIDEO_INDEX_FILE_END_TAG = "#EXT-X-ENDLIST"
XGDS_VIDEO_VLC_PATH = "/Applications/VLC.app/Contents/MacOS/VLC"
XGDS_VIDEO_VLC_PARAMETERS = "--intf=dummy --sout='#std{access=file,mux=ts,dst=-}'"
XGDS_VIDEO_MEDIASTREAMSEGMENTER_PATH = "/usr/bin/mediastreamsegmenter"

XGDS_VIDEO_TIME_ZONE = {'name': 'Pacific', 'code': 'America/Los_Angeles'}

# set this in siteSettings.py. example: 'plrpExplorer.views.getNoteExtras'
XGDS_VIDEO_NOTE_EXTRAS_FUNCTION = None
