/**
 * ensures that only one onTime event is enabled
 */
function onTimeController(thisObj) {
    if (!xgds_video.playFlag) {
        return;
    }

    var switchPlayer = false;            
    if (thisObj.id == xgds_video.onTimePlayer) {
        var state = jwplayer(thisObj.id).getState();
        if (state != 'PLAYING') { 
        //XXX later when there is a play button, make sure playFlag is also on. If it's on pause, do nothing. 
            switchPlayer = true;
        }
    } else {
        if (jwplayer(xgds_video.onTimePlayer).getState() != 'PLAYING') { //XXX and if the play button is on.
            switchPlayer = true; 
        }
    }
    if (switchPlayer) {
        var foundPlayingPlayer = false;
        for (var key in xgds_video.displaySegments) {
            var source = xgds_video.displaySegments[key][0].source.shortName;
            if (jwplayer(source).getState() == 'PLAYING') {
                xgds_video.onTimePlayer = source;
                foundPlayingPlayer = true;
                break;
            }
        }
        if (foundPlayingPlayer == false) {
            //set the xgds_video.onTimePlayer to the player with the nearest segment
            //to current slider time
            var time = getSliderTime();
            var sourceName = getNextAvailableSegment(time)['source'];
            xgds_video.onTimePlayer = sourceName; 
        }
    }
}


/**
 * Only called once onReady. Kickstarts the player with earliest starttime.
 */
function playFirstSegment() {
    for (var key in xgds_video.displaySegments) {
        var segments = xgds_video.displaySegments[key];
        var sourceName = segments[0].source.shortName;

        if (xgds_video.firstSegment.startTime == segments[0].startTime) {
            jwplayer(sourceName).play(true);
        }
    }
}


/**
 * Initialize jw player and call update values
 */
function setupJWplayer() {
    if (xgds_video.episode) { //if episode exists
        var maxWidth = getMaxWidth(Object.keys(xgds_video.displaySegments).length);
        for (var key in xgds_video.displaySegments) {
            // list of video segments with same source & episode
            var segments = xgds_video.displaySegments[key]; 
            // source of the video segments
            var source = segments[0].source;
            // paths of the video segments 
            var videoPaths = getFilePaths(xgds_video.episode, segments);
            //width and height of the player
            var size = calculateSize(maxWidth, segments[0].settings.height,
                                         segments[0].settings.width);
            
            jwplayer(source.shortName).setup({
                file: videoPaths[0],
                autostart: false,
                width: maxWidth,
                height: size[1],
                //aspectratio: "16:9",
                mute: false,
                controls: true, //for debugging
                skin: xgds_video.skinURL,
                listbar: {
                    position: 'right',
                    size: 150
                },
                events: {
                    onReady: function() {
                       playFirstSegment();
                    },
                    onBeforeComplete: function() {
                        //this.pause(true);
                    },
                    onComplete: function() {
                        xgds_video.haltOtherEvents = true;
                        //stop until start of the next segment.
                        var counter = 0;
                        jwplayer(this.id).pause(true);
                        onSegmentComplete(this);
                        console.log("onComplete");
                        xgds_video.haltOtherEvents = false;
                    },
                    onPlay: function(e) { //gets called per source
                        if (!xgds_video.haltOtherEvents) {
                        onTimeController(this);

                        var idxAndOffsets = xgds_video.seekOffsetList;
                        for (var keySource in idxAndOffsets) {
                            var player = jwplayer(keySource);
                            var idx = idxAndOffsets[keySource].index;
                            var offset = idxAndOffsets[keySource].offset;
                            var threshold = 0;
                            
                            //if the player's idx is not correct, set it again.
                            while (!checkPlaylistIdx(keySource)) {
                                player.playlistItem(idx);
                            }

                            if (player.getState() != 'BUFFERING') {
                                player.seek(offset);
                                
                                while (!withinRange(player.getPosition(), offset)) {
                                    player.seek(offset);
                                     
                                    if (threshold > 1000) {
                                        break;
                                    }
                                    threshold = threshold + 1;
                                }

                                delete xgds_video.seekOffsetList[keySource];
                            }
                        }
                        }
                    },
                    onPause: function(e) {
                        //just make sure the item does get paused.
                        if (!xgds_video.haltOtherEvents) {
                            onTimeController(this);
                        }
                    },
                    onBuffer: function(e) {
                        if (!xgds_video.haltOtherEvents) { 
                            onTimeController(this);
                        }
                    },
                    onIdle: function(e) {
                        if (!xgds_video.haltOtherEvents) {
                            if (e.position > Math.floor(e.duration)) {//e.duration - 1) {
                                this.pause(true);
                                console.log("onIdle");
                                onSegmentComplete(this);
                            }
                            onTimeController(this);
                        }
                    }, 
                    onTime: function(object) {
                        // need this. otherwise slider jumps around while moving.
                        if (xgds_video.movingSlider == true) {
                            return;
                        }

                        if (!xgds_video.playFlag) {
                            this.pause(true);
                            return;
                        }

                        // update test site time (all sources that are 'PLAYING')
                        var testSiteTime = getPlayerVideoTime(this.id);
                        setPlayerTimeLabel(testSiteTime, this.id);

                        //if this call is from the current 'onTimePlayer'
                        if (xgds_video.onTimePlayer == this.id) {
                            // update the slider here.
                            var updateTime = getPlayerVideoTime(this.id);
                            awakenIdlePlayers(updateTime,this.id);
                            setSliderTime(updateTime);                        
                        }
                        //if at the end of the segment, pause.
                        if (object.position > Math.floor(object.duration)) {//object.duration - 1) { 
                            this.pause(true);
                            console.log("onTime");
                            onSegmentComplete(this);
                        }
                    },
                },
            });

            // load the segments as playlist.
            var playlist = [];
            for (var k = 0; k < videoPaths.length; k++) {
                var newItem = {
                    file: videoPaths[k],
                    title: videoPaths[k]
                };
                playlist.push(newItem);
            }
            jwplayer(source.shortName).load(playlist);
         }
    } else {
        alert('episode not available. Cannot set up jwplayer');
    }
}



/**********************************
            Call-backs
***********************************/

/**
 * Updates the player and the slider times based on 
 * the seek time value specified in the 'seek' text box.
 */
function seekCallBack() {
    var seekTimeStr = document.getElementById('seekTime').value;
    if ((seekTimeStr == null) || 
        (Object.keys(xgds_video.displaySegments).length < 1)) {
        return;
    }
    var seekDateTime = null;
    for (var key in xgds_video.displaySegments) {
        var segments = xgds_video.displaySegments[key];
        var sourceName = segments[0].source.shortName;
        
        //XXX for now assume seek time's date is same as first segment's end date
        var seekTime = seekTimeParser(seekTimeStr);
        seekDateTime = new Date(segments[0].endTime); 
        seekDateTime.setHours(parseInt(seekTime[0]));
        seekDateTime.setMinutes(parseInt(seekTime[1]));
        seekDateTime.setSeconds(parseInt(seekTime[2]));

        var player = jwplayer(sourceName);
        if (player != undefined) {
            jumpToPosition(seekDateTime,sourceName);
        }
    }
    if (seekDateTime != null) {
        setSliderTime(seekDateTime);
    }
}


/**
 * Callback function for play/pause button
 */
function playPauseButtonCallBack() {
    xgds_video.playFlag = !xgds_video.playFlag;
    if (xgds_video.playFlag) {
        document.getElementById('playbutton').className = 'fa fa-pause fa-2x';
    } else {
        document.getElementById('playbutton').className = 'fa fa-play fa-2x';
    }

    var currTime = getSliderTime();
    for (var key in xgds_video.displaySegments) {
        var segments = xgds_video.displaySegments[key];
        var sourceName = segments[0].source.shortName;
        jumpToPosition(currTime, sourceName);
    }
    setSliderTime(currTime);
}


