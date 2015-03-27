# __BEGIN_LICENSE__
# Copyright (C) 2008-2010 United States Government as represented by
# the Administrator of the National Aeronautics and Space Administration.
# All Rights Reserved.
# __END_LICENSE__

from xgds_video import settings


def SettingsContextProcessor(request):
    """
    Adds various settings to the context
    """
    return {
        'JWPLAYER_KEY': settings.JWPLAYER_KEY
    }
