#!/usr/bin/env python
import datetime
import os
import re
import time
import logging
import json
import subprocess
import sys
import dateutil.parser
import glob
import socket

import django
from apps.geocamUtil.loader import LazyGetModelByName
django.setup()

from django.conf import settings
from xgds_status_board.models import Subsystem, SubsystemStatus
from xgds_status_board.util import *
from basaltApp.models import BasaltActiveFlight, BasaltResource
from basaltApp.views import getActiveEpisode
from xgds_video.util import getSegmentPath
    
    
def getActiveFlightLatestSegment():
    """
    Get the latest video segment in the active flight
    """
    activeepisode = getActiveEpisode()
    segments = activeepisode.videosegment_set.all()    
    if not segments:
        return None
    latestSegment = segments.latest('startTime')
    return latestSegment

    
def getActiveFlightLatestSegmentIndexFilePath():
    """
    Get the latest .m3u8 file for the active flight. 
    """
    latestSegment = getActiveFlightLatestSegment()
    latestSegNumber = latestSegment.segNumber
    activeFlight = BasaltActiveFlight.objects.all()[0]
    indexFilePath = getSegmentPath(activeFlight.flight.name, "", latestSegNumber)
    return indexFilePath


def checkIndexFileExists(indexFilePath):
    if os.path.isfile(indexFilePath):
        return True
    else: 
        return False
    

def getTsFileCount(segmentDir):
    """
    Count the .ts files inside given segment directory.
    """
    return len(glob.glob1(segmentDir,"*.ts"))


def setVideoRecorderStatusCache(episodePK, sourcePK):
    source = LazyGetModelByName(settings.XGDS_VIDEO_SOURCE_MODEL).get().objects.get(pk=sourcePK)
    episode = LazyGetModelByName(settings.XGDS_VIDEO_EPISODE_MODEL).get().objects.get(pk=episodePK)
    subsystemName = source.name + '_recorder'
    subsystemStatus = SubsystemStatus(subsystemName)
    subsystemStatus.setStatus(getDefaultStatus(subsystemStatus, episode.shortName + '_' + source.name))
    
# def resetVideoRecorderCache(flightName, subsystemStatus):
#     """
#     If it's a new active flight, reset the cache entry for video recorder.
#     """
#     status = subsystemStatus.getStatus()
#     oldFlightName = status['flight']
#     if oldFlightName != flightName:
#         # flight changed! reset the status.
#         defaultStatus = getDefaultStatus(subsystemStatus)
#         defaultStatus['flight'] = flightName
#         subsystemStatus.setStatus(defaultStatus)


def getColorLevel(indexFileExists, elapsedTsCreateTime, subsystemStatus):
    if (not indexFileExists) or (not elapsedTsCreateTime):
        return ERROR_COLOR
    else: 
        if elapsedTsCreateTime <= 10:  # if ts file was created less than 10 seconds ago
            return OKAY_COLOR
        elif (elapsedTsCreateTime > 10 ) and (elapsedTsCreateTime <=20): 
            return WARNING_COLOR
        else: # elapsedSeconds > 20:
            return ERROR_COLOR


def checkTsFileCount(prevSegNum, segNum, prevTsCount, tsFileCount):
    '''
    Returns true if the ts file count is incrementing. False if count is the same.
    '''
    # check if new ts file was created.
    if prevSegNum == segNum:  # still writing to the same segment. 
        if (tsFileCount - prevTsCount) > 0:  # new ts file was written
            return True
    else:  # new segment dir was created.
        return True
    return False

def getDefaultStatus(subsystemStatus, flightName):
    return {"name": subsystemStatus.name, 
            "displayName": subsystemStatus.displayName, 
            "elapsedTime": "",
            "statusColor": NO_DATA,
            "indexFileExists": 0,
            "lastUpdated": "",
            "segNumber": 0,
            "tsCount": 0,
            "flight": flightName 
          }

def setVideoRecorderStatus(resourceNames):
    refreshRateSeconds = 5
    
    jsonDicts = {}
    subsystemStatuses = {}
    for resourceName in resourceNames:
        try:
            subsystemName = resourceName + '_recorder'
            subsystemStatus = SubsystemStatus(subsystemName)
            subsystemStatuses[resourceName] = subsystemStatus
            flightName = ""
            try: 
                #TODO have the start flight fix what is in memcache, have it call some registered function
                
                resource = BasaltResource.objects.get(name=resourceName)
                activeFlight = BasaltActiveFlight.objects.get(flight__vehicle = resource.vehicle)
                flightName = activeFlight.flight.name
            except:
                continue
            jsonDict = subsystemStatuses[resourceName].getStatus()
            if 'segNumber' not in jsonDict:
                jsonDict = getDefaultStatus(subsystemStatus, flightName)
                subsystemStatus.setStatus(jsonDict)
                
            jsonDicts[resourceName] = jsonDict
        except:
            logging.error('Error, invalid subsystem name: %s' % resourceName)
            continue
         
    
    while True:
        for resourceName in resourceNames: 
            subsystemStatus = subsystemStatuses[resourceName]
            jsonDict = subsystemStatus.getStatus() #this gets updated by recordHLS2
            indexFileExists = False
            
            # load previous info
            prevTsCount = jsonDict['tsCount']
            prevSegNum = jsonDict['segNumber']
            
            # make sure m3u8 index file exists
            indexFilePath = settings.DATA_ROOT + getActiveFlightLatestSegmentIndexFilePath() + settings.XGDS_VIDEO_INDEX_FILE_NAME
            indexFileExists = checkIndexFileExists(indexFilePath)
            tsFileCount = getTsFileCount(indexFilePath)
            segNum = getActiveFlightLatestSegment().segNumber
            
            incrementingTs = checkTsFileCount(prevSegNum, segNum, prevTsCount, tsFileCount)
            lastUpdatedTime = dateutil.parser.parse(jsonDict['lastUpdated'])
            if incrementingTs: 
                jsonDict['elapsedTime'] = subsystemStatus.getElapsedTimeString(lastUpdatedTime)
                jsonDict['lastUpdated'] = datetime.datetime.utcnow().isoformat()
                
            elapsedTimeSeconds = subsystemStatus.getElapsedTimeSeconds(lastUpdatedTime)
            statusColor = getColorLevel(indexFileExists, elapsedTimeSeconds, subsystemStatus)
            
            jsonDict['indexFileExists'] = indexFileExists
            jsonDict['segNumber'] = segNum
            jsonDict['tsCount'] = tsFileCount 
            jsonDict['statusColor'] =  statusColor
            subsystemStatus.setStatus(jsonDict)
        time.sleep(refreshRateSeconds)
        
        
def main():
    import optparse
    parser = optparse.OptionParser('usage: %prog')
    parser.add_option('-n', '--resourceNames',
                      default="",
                      help='name of the subsystem to ping')
    opts, _args = parser.parse_args()
    resourceNames = opts.resourceNames.replace(' ', '').split(',')
    setVideoRecorderStatus(resourceNames)
    

if __name__ == '__main__':
    main()
