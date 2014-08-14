var pendingPlayerActions = {};

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
            switchPlayer = true;
        }
    } else {
        if (jwplayer(xgds_video.onTimePlayer).getState() != 'PLAYING') {
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
            if (sourceName != '') { //there is only one segment for each source and
                //none of the players are in 'PLAYING' state.
                xgds_video.onTimePlayer = sourceName;
            } //else leave the onTimPlayer as it is.
        }
    }
}


/**
 * Only called once onReady. Kickstarts the player with earliest starttime.
 */
function startPlayers() {
    if (xgds_video.noteTimeStamp != null) { // noteTimeStamp is in local time (i.e. PDT)
        var datetime = xgds_video.noteTimeStamp;
        //check if datetime is valid
        if ((datetime != 'Invalid Date') &&
                ((datetime > xgds_video.firstSegment.startTime) &&
                        (datetime < xgds_video.lastSegment.endTime))) {
            xgds_video.initialState = true; //to prevent onTime from being run right away before player had a chance to seek to init location
            seekAllPlayersToTime(datetime);
            return;
        }
    }
    //find the first segment and play it.
    for (var key in xgds_video.displaySegments) {
        var segments = xgds_video.displaySegments[key];
        var sourceName = segments[0].source.shortName;

        if (xgds_video.firstSegment.startTime == segments[0].startTime) {
            jwplayer(sourceName).play(true);
        }
    }
}


/**
 * If the source is a diver, and no other divers are enabled, turn it on.
 */
function soundController() {
    var soundOn = false;
    for (var source in xgds_video.displaySegments) {
        if (source.match('RD')) { //if the source is a research diver
            //if no other player sounds are on, unmute this player
            if (!soundOn) {
                jwplayer(source).setMute(false);
                soundOn = true;
            } else {
                //there is already a player that is not muted. Turn off this
                //player's sound.
                if (!jwplayer(source).getMute()) {
                    jwplayer(source).setMute(true);
                }
            }

        }
    }
}


/**
 * Initialize jw player and call update values
 */
function setupJWplayer() {
    var numSources = Object.keys(xgds_video.displaySegments).length;
    var maxWidth = getMaxWidth(numSources);
    for (var source in xgds_video.displaySegments) {
        // list of video segments with same source & episode (if given)
        var segments = xgds_video.displaySegments[source];
        //if there are no segments to show, dont build a player.
        if (typeof segments == 'undefined' || segments.length == 0) {
            continue;
        }
        // paths of the video segments
        var videoPaths = [];
        if (isEmpty(xgds_video.episode)) { //if episode does not exist
            videoPaths = getFilePaths(null, segments);
        } else {
            videoPaths = getFilePaths(xgds_video.episode, segments);
        }
        jwplayer(source).setup({
            file: videoPaths[0],
            autostart: false,
            width: maxWidth,
            height: maxWidth * (9 / 16),
            skin: STATIC_URL + 'external/js/jwplayer/jw6-skin-sdk/skins/six/six.xml',
            mute: true,
            analytics: {
                enabled: false,
                cookies: false
            },
            controls: true, //for debugging
            events: {
                onReady: function() {
                    startPlayers();
                    soundController();
                },
                onBeforeComplete: function() {
                    //this.pause(true);
                },
                onComplete: function() {
                    //stop until start of the next segment.
                    var counter = 0;
                    jwplayer(this.id).pause(true);
                    onSegmentComplete(this);
                },
                onPlay: function(e) { //gets called per source
                    onTimeController(this);
                    var pendingActions = pendingPlayerActions[this.id];
                    if (pendingActions.length != 0) {
                        for (var i = 0; i < pendingActions.length; i++) {
                            pendingActions[i].action(pendingActions[i].arg);
                        }
                        pendingPlayerActions[this.id] = [];
                        if (xgds_video.initialState == true) {
                            xgds_video.initialState = false;
                        }
                    } else {
                        if (xgds_video.initialState == true) {
                            xgds_video.initialState = false;
                        }
                    }
                },
                onPause: function(e) {
                    //just make sure the item does get paused.
                    onTimeController(this);
                },
                onBuffer: function(e) {
                    onTimeController(this);
                },
                onIdle: function(e) {
                    if (e.position > Math.floor(e.duration)) {
                        this.pause(true);
                        onSegmentComplete(this);
                    }
                    onTimeController(this);
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

                    if (xgds_video.initialState != true) {
                        //if this call is from the current 'onTimePlayer'
                        if (xgds_video.onTimePlayer == this.id) {
                            // update the slider here.
                            var updateTime = getPlayerVideoTime(this.id);
                            awakenIdlePlayers(updateTime, this.id);
                            setSliderTime(updateTime);
                            updateToolTip(false, updateTime);
                        }
                    }
                    //if at the end of the segment, pause.
                    if (object.position > Math.floor(object.duration)) {
                        this.pause(true);
                        onSegmentComplete(this);
                    }
                }
            }
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
        jwplayer(source).load(playlist);
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
    var seekTime = seekTimeParser(seekTimeStr);
    var seekDateTime = null;
    //XXX for now assume seek time's date is same as first segment's end date
    seekDateTime = new Date(segments[0].endTime);
    seekDateTime.setHours(parseInt(seekTime[0]));
    seekDateTime.setMinutes(parseInt(seekTime[1]));
    seekDateTime.setSeconds(parseInt(seekTime[2]));
    seekAllPlayersToTime(seekDateTime);
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

        if (xgds_video.playFlag) {
            jwplayer(sourceName).play(true);
        } else {
            jwplayer(sourceName).pause(true);
        }
    }
    setSliderTime(currTime);
}
