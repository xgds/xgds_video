#! /usr/bin/env python
import requests
import memcache
import m3u8
import time
import json
import datetime
import pytz
import os
from xgds_video.recordingUtil import invokeMakeNewSegment

class HLSRecorder:
    def __init__(self, sourceUrl, m3u8DirPath, recorderId, episodePK, sourcePK):
        self.stopRecording = False
        self.m3u8Obj = None
        self.maxSegmentNumber = -1
        self.sourceUrl = sourceUrl
        self.m3u8DirPath = m3u8DirPath
        self.recorderId = recorderId
        self.episodePK = episodePK
        self.sourcePK = sourcePK

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

    def analyzeM3U8Segments(self, m3u8Obj, contiguous=False):
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
            if segNumber > self.maxSegmentNumber:
                if not firstHit:
                    firstHit = True
                    if self.maxSegmentNumber + 1 < segNumber:
                        discontinuity = True # discontinuity between files
                        nextGoodSegment = seg
                        nextGoodSegmentNumber = segNumber
                if contiguous:
                    if not lastSegmentNumber:
                        lastSegmentNumber = segNumber
                        totalTime = totalTime + seg.duration
                        lastGoodSegment = seg
                    else:
                        if lastSegmentNumber + 1 == segNumber:
                            totalTime = totalTime + seg.duration
                            lastSegmentNumber = segNumber
                            lastGoodSegment = seg
                        else:
                            gap = True
                            nextGoodSegment = seg
                            break
                else:
                    totalTime = totalTime + seg.duration
                    lastGoodSegment = seg
        return {'lastSegment':lastGoodSegment,
                'lastSegmentNumber': lastSegmentNumber,
                'nextSegment': nextGoodSegment,
                'nextSegmentNumber': nextGoodSegmentNumber,
                'totalTime':totalTime,
                'gap': gap,
                'discontinuity': discontinuity}

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
        f.write(self.m3u8Obj.dumps())
        f.close()
        
    def saveM3U8SegmentsToDisk(self, analyzedSegments, addSegmentsToList=True):
        for seg in self.m3u8Obj.segments:
            videoData = self.httpSession.get("%s/%s" % (os.path.dirname(self.sourceUrl),
                                         seg.uri))
            f = open("%s/%s" % (self.m3u8DirPath, seg.uri),"w")
            f.write(videoData.content)
            f.close()
            if addSegmentsToList:
                self.m3u8Obj.add_segment(seg)
            if seg == analyzedSegments['lastSegment']:
                #done -- we do not expect any problems in this initial state but if we want to be thorough we should handle making a new xgds segment in here
                break

    def initXgdsSegmentRecording(self):
        self.m3u8Obj = self.getM3U8()
        if self.m3u8Obj:
            self.saveM3U8ToFile()
            
            #TODO we have never seen gaps here but it is theoretically possible.
            analyzedSegments = self.analyzeM3U8Segments(self.m3u8Obj)
            self.saveM3U8SegmentsToDisk(analyzedSegments, False)
    
            self.maxSegmentNumber = analyzedSegments['lastSegmentNumber']
            sleepDuration = analyzedSegments['totalTime'] - analyzedSegments['lastSegment'].duration
            time.sleep(sleepDuration)

    def storeVideoUpdateIndex(self, seg):
        videoData = self.httpSession.get("%s/%s" % (os.path.dirname(self.sourceUrl),
                                                    seg.uri))
        f = open("%s/%s" % (self.m3u8DirPath, seg.uri),"w")
        f.write(videoData.content)
        f.close()
        self.m3u8Obj.add_segment(seg)
        
        f = open(self.m3u8FilePath,"w")
        f.write(self.m3u8Obj.dumps())
        f.close()


    def makeNewXgdsSegment(self, m3u8Latest, seg, segNumber):
        ''' Make a new segment because we hit a discontinuity or gap '''
        # update self.m3u8FilePath & self.m3u8DirPath
        # build the new m3u8 object that has the m3u8 segments we care about
        
        # **TODO** super important read the start time from the ts file of the next m3u8 segment somehow
        startTime = datetime.datetime.now(pytz.utc)
        
        # construct the new segment object
        parentDirectory = os.path.dirname(self.m3u8DirPath)
        segmentInfo = invokeMakeNewSegment(self.sourcePK, parentDirectory, self.sourceUrl, startTime, self.episodePK)
        self.sourceUrl = segmentInfo['videoFeed'].url
        self.m3u8DirPath = segmentInfo['recordedVideoDir']
        
        # first identify segments to remove
        deathrow = []
        for s in m3u8Latest.segments:
            if s != seg:
                deathrow.append(s)
            else:
                break;
        
        newSegmentList = [s for s in m3u8Latest.segments if s not in deathrow]
        m3u8Latest.segments = m3u8.model.SegmentList()
        for s in newSegmentList:
            m3u8Latest.add_segment(s)
        self.m3u8Obj = m3u8Latest
        
    def recordNextBlock(self, sleepAfterRecord=True):

        m3u8Latest = self.getM3U8()
        videoNewData = (len(m3u8Latest.segments) > 0)
        
        if videoNewData:
            analyzedSegments = self.analyzeM3U8Segments(m3u8Latest)
            if analyzedSegments['discontinuity']:
                # we want to start a brand new xgds segment with a new m3u8 file based on the m3u8Latest throwing out any overlap data with previous m3u8
                # and then we want to store starting from the next good segment using its starting number, and go to the end of the m3u8.
                self.makeNewXgdsSegment(m3u8Latest, analyzedSegments['nextSegment'], analyzedSegments['nextSegmentNumber'])
                self.saveM3U8SegmentsToDisk(analyzedSegments, False)
                self.saveM3U8ToFile()
                
            elif analyzedSegments['gap']:
                # first we want to save any m3u8 segments up to the gap
                for seg in m3u8Latest.segments:
                    if seg == analyzedSegments['nextSegment']:
                        break;  # This is the first segment after the gap
                    self.storeVideoUpdateIndex(seg)
                
                self.maxSegmentNumber = analyzedSegments['lastSegmentNumber']
                self.updateCachedStatus(analyzedSegments)

                # then we want to start a brand new xgds segment with a new m3u8 file based on the m3u8Latest, throwing out any before the gap
                # and then we want to store starting from the next good segment using its starting number, and go to the end of the m3u8
                self.makeNewXgdsSegment(m3u8Latest, analyzedSegments['nextSegment'], analyzedSegments['nextSegmentNumber'])
                self.saveM3U8SegmentsToDisk(analyzedSegments, False)
                self.saveM3U8ToFile()

            else:
                for seg in m3u8Latest.segments:
                    self.storeVideoUpdateIndex(seg)
       
            self.maxSegmentNumber = analyzedSegments['lastSegmentNumber']
            self.updateCachedStatus(analyzedSegments)
        
            if sleepAfterRecord:
                #TODO handle discontinuity better
                totalTime = analyzedSegments['totalTime']
                lastGoodSegment = analyzedSegments['lastSegment']
                lastSegmentDuration = lastGoodSegment.duration
                sleepDuration = totalTime - lastSegmentDuration
                time.sleep(sleepDuration)

    def runRecordingLoop(self):
        while not self.stopRecording:
            self.recordNextBlock()
            self.stopRecording = self.cache.get("recordHLS:%s:stopRecording" %
                                                self.recorderId)

        # When done write final copy of index with end tag
        self.m3u8Obj.is_endlist = True
        f = open(self.m3u8FilePath,"w")
        f.write(self.m3u8Obj.dumps())
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