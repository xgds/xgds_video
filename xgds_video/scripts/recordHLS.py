#! /usr/bin/env python
import requests
import memcache
import m3u8
import time
import json
import datetime
import os

class HLSRecorder:
    sourceUrl = None
    m3u8DirPath = None
    m3u8FilePath = None
    recorderId = None
    m3u8Obj = None
    stopRecording = False
    maxSegmentNumber = -1
    httpSession = None
    cache = None

    def __init__(self, sourceUrl, m3u8DirPath, recorderId):
        self.sourceUrl = sourceUrl
        self.m3u8DirPath = m3u8DirPath
        self.recorderId = recorderId

        self.m3u8Filename = os.path.basename(sourceUrl)
        self.m3u8FilePath = "%s/%s" % (m3u8DirPath, self.m3u8Filename)
        self.httpSession = requests.Session()

        self.cache = memcache.Client(['127.0.0.1:11211'], debug=0)
        self.cache.set("recordHLS:%s:stopRecording" % recorderId,
                       self.stopRecording)

    def updateCachedStatus(self):
        myKey = "recordHLS:%s:recordingStatus" % self.recorderId
        status = {"currentSegment":self.maxSegmentNumber,
                  "totalDuration":self.getm3u8TotalTime(self.m3u8Obj),
                  "lastUpdate":datetime.datetime.utcnow().isoformat()}
        self.cache.set(myKey, json.dumps(status))

    def getm3u8TotalTime(self, m3u8Obj):
        totalTime = 0.0
        for seg in m3u8Obj.segments:
            totalTime = totalTime + seg.duration
        return totalTime

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
            

    def initRecording(self):
        self.m3u8Obj = self.getM3U8()
        if self.m3u8Obj:
            f = open(self.m3u8FilePath,"w")
            f.write(self.m3u8Obj.dumps())
            f.close()
    
            for seg in self.m3u8Obj.segments:
                videoData = self.httpSession.get("%s/%s" % (os.path.dirname(self.sourceUrl),
                                             seg.uri))
                f = open("%s/%s" % (self.m3u8DirPath, seg.uri),"w")
                f.write(videoData.content)
                f.close()
    
            self.maxSegmentNumber = self.segmentNumber(self.m3u8Obj.segments[-1])
            
            totalTime = self.getm3u8TotalTime(self.m3u8Obj)
            lastSegmentDuration = self.m3u8Obj.segments[-1].duration
            sleepDuration = totalTime - lastSegmentDuration
            time.sleep(sleepDuration)

    def recordNextBlock(self, sleepAfterRecord=True):

        m3u8Latest = self.getM3U8()

        videoDiscontinuity = True
        for seg in m3u8Latest.segments:
            if self.segmentNumber(seg) > self.maxSegmentNumber:
                if self.segmentNumber(seg) == self.maxSegmentNumber+1:
                    videoDiscontinuity = False
                videoData = self.httpSession.get("%s/%s" % (os.path.dirname(self.sourceUrl),
                                                            seg.uri))
                f = open("%s/%s" % (self.m3u8DirPath, seg.uri),"w")
                f.write(videoData.content)
                f.close()
                self.m3u8Obj.add_segment(seg)

        if videoDiscontinuity:
            print "recordHLS: *** Warning: discontinuity in video stream! ***"
        f = open(self.m3u8FilePath,"w")
        f.write(self.m3u8Obj.dumps())
        f.close()

        self.maxSegmentNumber = self.segmentNumber(m3u8Latest.segments[-1])
        self.updateCachedStatus()
        if sleepAfterRecord:
            totalTime = self.getm3u8TotalTime(m3u8Latest)
            lastSegmentDuration = m3u8Latest.segments[-1].duration
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
    opts, args = parser.parse_args()
    if len(args) != 0:
        parser.error('expected no arguments')
    if (not opts.sourceUrl) or (not opts.outputDir) or (not opts.recorderId):
        parser.error("All options are required")

    print "Start HLS recording:"
    print "  Recorder ID:", opts.recorderId
    print "  Source URL:", opts.sourceUrl
    print "  Output path:", opts.outputDir

    hlsRecorder = HLSRecorder(opts.sourceUrl, opts.outputDir, opts.recorderId)
    hlsRecorder.initRecording()
    hlsRecorder.runRecordingLoop()
    print "recordHLS: Recording Complete. End tag written. Exiting..."

if __name__ == '__main__':
    main()
