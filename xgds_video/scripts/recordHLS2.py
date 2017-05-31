#! /usr/bin/env python
import requests
import memcache
import m3u8
import time
import json
import datetime
import pytz
import copy
import os
from collections import deque
from xgds_video.recordingUtil import invokeMakeNewSegment

RECORDER_SEGMENT_BUFFER_SIZE = 6

class HLSRecorder:
    def __init__(self, sourceUrl, m3u8DirPath, recorderId, episodePK, sourcePK):
        self.stopRecording = False
        self.m3u8Full = None
        self.maxSegmentNumber = None
        self.sourceUrl = sourceUrl
        self.m3u8DirPath = m3u8DirPath
        self.recorderId = recorderId
        self.episodePK = episodePK
        self.sourcePK = sourcePK
        self.segmentBuffer = deque([], RECORDER_SEGMENT_BUFFER_SIZE)
        self.segmentIDBuffer = deque([], RECORDER_SEGMENT_BUFFER_SIZE)

        self.m3u8Filename = os.path.basename(sourceUrl)
        self.m3u8FilePath = "%s/%s" % (m3u8DirPath, self.m3u8Filename)
        self.httpSession = requests.Session()

        self.cache = memcache.Client(['127.0.0.1:11211'], debug=0)
        self.cache.set("recordHLS:%s:stopRecording" % recorderId,
                       self.stopRecording)

    def updateCachedStatus(self, analyzedSegments):
        myKey = "recordHLS:%s:recordingStatus" % self.recorderId
        status = {"currentSegment": analyzedSegments['lastSegmentNumber'],
                  "totalDuration":analyzedSegments['totalTime'],
                  "lastUpdate":datetime.datetime.utcnow().isoformat()}
        self.cache.set(myKey, json.dumps(status))

    
    def playlistTotalTime(self, playlist):
        totalTime = 0
        for seg in playlist:
            totalTime += seg.duration
        return totalTime
    
    
    def analyzeM3U8Segments(self, m3u8Obj, contiguous=True):
        totalTime = 0.0
        #TODO this does not handle a gap.
        lastSegmentNumber = None
        lastGoodSegment = None
        nextGoodSegment = None
        nextGoodSegmentNumber = None
        gap = False #gap within the m3u8 segments
        discontinuity = False #gap between 2 m3u8 files
        firstHit = False
        for seg in m3u8Obj.segments:
            segNumber = self.segmentNumber(seg)
            print "Seg number:", segNumber
            print "Max segment:", self.maxSegmentNumber
            if segNumber > self.maxSegmentNumber:
                if self.maxSegmentNumber >= 0 and not firstHit:
                    print "if 1"
                    firstHit = True
                    if self.maxSegmentNumber + 1 < segNumber:
                        print "if 2"
                        discontinuity = True # discontinuity between files
                        nextGoodSegment = seg
                        nextGoodSegmentNumber = segNumber
                if contiguous:
                    print "if 3"
                    if not lastSegmentNumber:
                        print "if 4"
                        lastSegmentNumber = segNumber
                        totalTime = totalTime + seg.duration
                        lastGoodSegment = seg
                    else:
                        if lastSegmentNumber + 1 == segNumber:
                            print "if 5"
                            totalTime = totalTime + seg.duration
                            lastSegmentNumber = segNumber
                            lastGoodSegment = seg
                        else:
                            print "if 6"
                            gap = True
                            nextGoodSegment = seg
                            nextGoodSegmentNumber = segNumber
                            break
                else:
                    print "if 7"
                    totalTime = totalTime + seg.duration
                    lastGoodSegment = seg
                    lastSegmentNumber = segNumber
            elif segNumber == self.maxSegmentNumber:
                print 'segNumber equals max segment number '
                lastSegmentNumber = segNumber
                lastGoodSegment = seg

        result = {'lastSegment':lastGoodSegment,
                'lastSegmentNumber': lastSegmentNumber,
                'nextSegment': nextGoodSegment,
                'nextSegmentNumber': nextGoodSegmentNumber,
                'totalTime':totalTime,
                'gap': gap,
                'discontinuity': discontinuity}
        print "M3U8 analysis", result
        return result

    def segmentNumber(self, segmentObj):
        segFileName = os.path.basename(segmentObj.uri)
        name,ext = os.path.splitext(segFileName)
        try:
            baseName, otherNumber, segNum = name.split("_")
        except:
            baseName,segNum = name.split("-")
            
        return int(segNum)

    def getM3U8(self):
        try:
            m3u8String = self.httpSession.get(self.sourceUrl).text
            m3u8Obj = m3u8.loads(m3u8String)
            if not m3u8Obj.files:
                # m3u8 must have a playlist which holds the files, read that one.
                baseUrl = os.path.dirname(self.sourceUrl)
                for p in m3u8Obj.playlists:
                    playlistUri = p.uri
                    m3u8String = self.httpSession.get(os.path.join(baseUrl, playlistUri)).text
                    m3u8Obj = m3u8.loads(m3u8String)
            return m3u8Obj
        except:
            time.sleep(0.5)
            print "%s %s %s" % ("recordHLS:",
                                "*** Warning: Exception polling Source.",
                                "Trying again... ***")
            return  None # skip and give source a break
            

    def saveM3U8ToFile(self):
        f = open(self.m3u8FilePath,"w")
        f.write(self.m3u8Full.dumps())
        f.close()
        
    def saveM3U8SegmentsToDisk(self, analyzedSegments, addSegmentsToList=True):
        for seg in self.m3u8Full.segments:
            videoData = self.httpSession.get("%s/%s" % (os.path.dirname(self.sourceUrl),
                                         seg.uri))
            f = open("%s/%s" % (self.m3u8DirPath, seg.uri),"w")
            f.write(videoData.content)
            f.close()
            if addSegmentsToList:
                self.m3u8Full.add_segment(seg)
            if seg == analyzedSegments['lastSegment']:
                #done -- we do not expect any problems in this initial state but if we want to be thorough we should handle making a new xgds segment in here
                break

    
    def addToSegmentBuffer(self, seg, flushed=False):
        self.segmentBuffer.append({'chunk':seg, 'flushed': flushed})
        self.segmentIDBuffer.append(self.segmentNumber(seg))
        
    
    def segmentInBuffer(self, seg):
        segNumber = self.segmentNumber(seg)
        return segNumber in self.segmentIDBuffer
    
    
    def initXgdsSegmentRecording(self):
        firstm3u8 = self.getM3U8()
        if firstm3u8:
            self.m3u8Full = copy.deepcopy(firstm3u8)
            self.m3u8Full.segments = m3u8.model.SegmentList()  # Initialize with empty list          
            #TODO we have never seen gaps here but it is theoretically possible.
            for chunk in firstm3u8:
                self.addToSegmentBuffer(chunk)
            sleepDuration = self.playlistTotalTime(firstm3u8) - firstm3u8.segments[-1].duration
            self.flushVideoAndPlaylist()
            time.sleep(sleepDuration)


    def flushVideoAndPlaylist(self):
        for segData in self.segmentBuffer:
            currSegNumber = self.segmentNumber(segData['chunk'])
            if self.maxSegmentNumber and ((currSegNumber - self.maxSegmentNumber) != 1) and not segData['flushed']:
                self.makeNewXgdsSegment()
            if not segData['flushed']:
                self.storeVideoUpdateIndex(segData['chunk'])
                segData['flushed'] = True
            self.maxSegmentNumber = currSegNumber
            
            
                
    def storeVideoUpdateIndex(self, seg):
        videoData = self.httpSession.get("%s/%s" % (os.path.dirname(self.sourceUrl),
                                                    seg.uri))
        f = open("%s/%s" % (self.m3u8DirPath, seg.uri),"w")
        f.write(videoData.content)
        f.close()
        self.m3u8Full.add_segment(seg)
        
        f = open(self.m3u8FilePath,"w")
        f.write(self.m3u8Full.dumps())
        f.close()


    def makeNewXgdsSegment(self, m3u8Latest=None, seg=None, segNumber=None):
        ''' Make a new segment because we hit a discontinuity or gap '''
        # update self.m3u8FilePath & self.m3u8DirPath
        # build the new m3u8 object that has the m3u8 segments we care about
        
        # First be sure existing index file is flushed to disk
        self.saveM3U8ToFile()
        
        # Now create playlist for new xGDS segment with empty chunk list
        newM3u8Full = copy.deepcopy(self.m3u8Full)
        newM3u8Full.segments = m3u8.model.SegmentList()  # Initialize with empty list
        self.m3u8Full = newM3u8Full          

        # **TODO** SUPER IMPORTANT read the start time from the ts file of the next m3u8 segment somehow
        startTime = datetime.datetime.now(pytz.utc)
        
        # construct the new segment object
        parentDirectory = os.path.dirname(self.m3u8DirPath)
        segmentInfo = invokeMakeNewSegment(self.sourcePK, parentDirectory, self.sourceUrl, startTime, self.episodePK)
        self.sourceUrl = segmentInfo['videoFeed'].url
        self.m3u8DirPath = segmentInfo['recordedVideoDir']
        self.m3u8FilePath = "%s/%s" % (self.m3u8DirPath, self.m3u8Filename)


    def recordNextBlock(self, sleepAfterRecord=True):
        m3u8Latest = self.getM3U8()
        
        for chunk in m3u8Latest:
            if not self.segmentInBuffer(chunk):
                self.addToSegmentBuffer(chunk)

        self.flushVideoAndPlaylist()

        if sleepAfterRecord:
            #TODO handle discontinuity better
            sleepDuration = self.playlistTotalTime(m3u8Latest) - m3u8Latest.segments[-1].duration
            time.sleep(sleepDuration)

    def runRecordingLoop(self):
        while not self.stopRecording:
            self.recordNextBlock()
            self.stopRecording = self.cache.get("recordHLS:%s:stopRecording" %
                                                self.recorderId)

        # When done write final copy of index with end tag
        self.m3u8Full.is_endlist = True
        f = open(self.m3u8FilePath,"w")
        f.write(self.m3u8Full.dumps())
        f.close()


def main():
    import optparse
    parser = optparse.OptionParser('usage: %prog --sourceUrl <m3u8 URL> ' + 
                                   '--outputDir <dirname> ' +
                                   '--recorderId <recorderID>')
    parser.add_option('--sourceUrl', dest="sourceUrl",
                      help='URL to m3u8 file on source')
    parser.add_option('--outputDir', dest="outputDir",
                      help='directory to write m3u8 index file and video files')
    parser.add_option('--recorderId', dest="recorderId",
                      help='ID to separate from other instances. E.g. EV1')
    parser.add_option('--episodePK', dest="episodePK",
                      help='Primary key of xGDS episode being recorded')
    parser.add_option('--sourcePK', dest="sourcePK",
                      help='Primary key of xGDS source DB record')
    opts, args = parser.parse_args()
    if len(args) != 0:
        parser.error('expected no arguments')
    if (not opts.sourceUrl) or (not opts.outputDir) or (not opts.recorderId):
        parser.error("All options are required")

    print "Start HLS recording:"
    print "  Recorder ID:", opts.recorderId
    print "  Source URL:", opts.sourceUrl
    print "  Output path:", opts.outputDir
    
    hlsRecorder = HLSRecorder(opts.sourceUrl, opts.outputDir, opts.recorderId, opts.episodePK, opts.sourcePK)
    hlsRecorder.initXgdsSegmentRecording()
    hlsRecorder.runRecordingLoop()
    print "recordHLS: Recording Complete. End tag written. Exiting..."

if __name__ == '__main__':
    main()
