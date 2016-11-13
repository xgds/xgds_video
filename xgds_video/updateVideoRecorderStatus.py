#!/usr/bin/env python
import datetime
import os
import re
import time
import memcache
import logging
import json
import subprocess
import sys
import dateutil.parser
import glob
import socket

import django
django.setup()

from django.conf import settings
from xgds_status_board.models import Subsystem, SubsystemStatus
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


def resetVideoRecorderCache(flightName, subsystemStatus):
    """
    If it's a new active flight, reset the cache entry for video recorder.
    """
    status = subsystemStatus.getStatus()
    oldFlightName = status['flight']
    if oldFlightName != flightName:
        # flight changed! reset the status.
        defaultStatus = subsystemStatus.getDefaultStatus()
        defaultStatus['flight'] = flightName
        subsystemStatus.setStatus(defaultStatus)


def getColorLevel(indexFileExists, elapsedTsCreateTime, subsystemStatus):
    if (not indexFileExists) or (not elapsedTsCreateTime):
        return subsystemStatus.ERROR
    else: 
        if elapsedTsCreateTime <= 10:  # if ts file was created less than 10 seconds ago
            return subsystemStatus.OKAY
        elif (elapsedTsCreateTime > 10 ) and (elapsedTsCreateTime <=20): 
            return subsystemStatus.WARNING
        else: # elapsedSeconds > 20:
            return subsystemStatus.ERROR


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


def setVideoRecorderStatus(resourceNames):
    refreshRateSeconds = 5
    location = socket.gethostname()  # either shore or boat
    
    while True:
        for resourceName in resourceNames: 
            indexFileExists = False
            # get the flight from resource (resource name is part of subsystem name)
            try: 
                resource = BasaltResource.objects.get(name=resourceName)
                activeFlight = BasaltActiveFlight.objects.get(flight__vehicle = resource.vehicle)
                flightName = activeFlight.flight.name
            except:
                continue
            
            subsystemName = resourceName + '_' + location + '_video_recorder'
            try: 
                subsystemStatus = SubsystemStatus(subsystemName)
            except:
                logging.error('Error, invalid subsystem name: %s' % subsystemName)
                continue
            
            resetVideoRecorderCache(flightName, subsystemStatus)
            # load previous info
            jsonDict = subsystemStatus.getStatus()
            prevTsCount = jsonDict['tsCount']
            prevSegNum = jsonDict['segNumber']
            
            # make sure m3u8 index file exists
            indexFilePath = settings.DATA_ROOT + getActiveFlightLatestSegmentIndexFilePath() + 'prog_index.m3u8'
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
            jsonDict['flight'] = flightName
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
