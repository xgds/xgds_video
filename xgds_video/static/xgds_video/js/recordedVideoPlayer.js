/**
 * ensures that only one onTime event is enabled
 */
function onTimeController(thisObj) {
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
        for (var key in xgds_video.displaySegments) {
            var source = xgds_video.displaySegments[key][0].source.shortName;
            if (jwplayer(source).getState() == 'PLAYING') {
                xgds_video.onTimePlayer = source;
                break;
            }
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
                    onComplete: function() {
                        // upon complete, stop. It should start segment at next seg's start time. 
                        jwplayer(this.id).pause(true);
                       
                        // if all other players are paused, go the the next available segment and play.
                        if (allPaused()) {
                            var time = getPlayerVideoTime(this.id); 
                            time = new Date (time.getTime() + 1000); //add a second so nextAvailSeg fcn is not confused.XXX see if this is really necessary. 
                            var seekTime = getNextAvailableSegment(time);
                            seekAllPlayersToTime(seekTime);
                        }
                    },
                    onPlay: function(e) { //gets called per source
                        onTimeController(this);
                    },
                    onPause: function(e) {
                        onTimeController(this);
                    },
                    onBuffer: function(e) {
                        onTimeController(this);
                    },
                    onIdle: function(e) {
                        onTimeController(this);
                    }, 
                    onTime: function(object) {
                        //if at the end of the segment, pause.
                         if (object.position > object.duration - 1) { 
                            this.pause(); 
                         }

                        // need this. otherwise slider jumps around while moving.
                        if (xgds_video.movingSlider == true) {
                            return;
                        }

                        // update test site time (all sources that are 'PLAYING')
                        var testSiteTime = getPlayerVideoTime(this.id);
                        setPlayerTimeLabel(testSiteTime, this.id);

                        //if this call is from the current 'onTimePlayer'
                        if (xgds_video.onTimePlayer == this.id) {
                            // update the slider here.
                            //XXX if the play flag is off, shouldn't be player shouldn't be playing.
                                                        //awake idle players
                            //awakeIdlePlayers(updateTime); //XXX doesn't wok!

                            var updateTime = getPlayerVideoTime(this.id);
                            setSliderTime(updateTime);                        
                        }
                    },
                    /*
                    onPlaylistItem: function(object) {
                        if (this.id == xgds_video.playerId) {
                            //XXX make sure it doesn't run infinitely.
                            while (this.getPlaylistIndex() != xgds_video.playerIdx) {
                                this.playlistItem(xgds_video.playerIdx);
                            }
                

                            if (xgds_video.playerOffset != null) {
                                this.seek(xgds_video.playerOffset);
                                xgds_video.playerId = "";
                                xgds_video.playerOffset = null;
                            }
                        }
                    },*/
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
/*
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
            xgds_video.playerTime = seekDateTime;
            xgds_video.playerSource = sourceName;
        }
    }
    if (seekDateTime != null) {
        setSliderTime(seekDateTime);
    }
    */
}


/**
 * Callback function for play/pause button
 */
function playPauseButtonCallBack() {
/*
    xgds_video.playFlag = !xgds_video.playFlag;
    if (xgds_video.playFlag) {
        document.getElementById('playbutton').className = 'fa fa-pause fa-2x';
    } else {
        document.getElementById('playbutton').className = 'fa fa-play fa-2x';
    }

    var currTime = new Date(xgds_video.masterSlider.slider('value') * 1000);
    for (var key in xgds_video.displaySegments) {
        var segments = xgds_video.displaySegments[key];
        var sourceName = segments[0].source.shortName;
        jumpToPosition(currTime, sourceName);
        xgds_video.playerTime = getPlayerVideoTime(sourceName);
        xgds_video.playerSource = sourceName;
    }
    setSliderTime(currTime);
    */
}


