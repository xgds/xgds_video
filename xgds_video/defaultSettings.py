# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

XGDS_VIDEO_RECORDING_URL_BASE = "*** Set me in siteSettings.py ***"
XGDS_VIDEO_RECORDING_DIR_BASE = "*** Set me in siteSettings.py ***"

XGDS_VIDEO_NEW_DIR_PERMISSIONS = 0777
XGDS_VIDEO_MAX_EPISODE_DURATION_MINUTES = 180

XGDS_VIDEO_TRACK_MODEL = 'xgds_video.VideoTrack'
XGDS_VIDEO_SEGMENT_MODEL = 'xgds_video.VideoSegment'
XGDS_VIDEO_EPISODE_MODEL = 'xgds_video.VideoEpisode'

XGDS_VIDEO_INDEX_FILE_NAME = "prog_index.m3u8"
XGDS_VIDEO_INDEX_FILE_END_TAG = "#EXT-X-ENDLIST"
XGDS_VIDEO_VLC_PATH = "/Applications/VLC.app/Contents/MacOS/VLC"
XGDS_VIDEO_VLC_PARAMETERS = "--intf=dummy --sout='#std{access=file,mux=ts,dst=-}'"
XGDS_VIDEO_MEDIASTREAMSEGMENTER_PATH = "/usr/bin/mediastreamsegmenter"
