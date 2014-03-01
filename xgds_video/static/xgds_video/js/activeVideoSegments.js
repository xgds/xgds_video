//globals
/* //defined in the template. Copied here for reference.
    var xgds_video = { masterSlider: '',
                       playFlag: true,
                       initialState: true,
                       seekOffsetList: {},
                       playerTime: null,
                       playerSource: null,
                       baseUrl = "{{ baseUrl}}",
                       episode = ({{ episodeJson|safe }}=="None") ? 
                                 null : {{ episodeJson|safe }},
                       displaySegments = {{ segmentsJson|safe }},
                       firstSegment = null,
                       lastSegment = null
                       };
*/


/**
 * Helper that returns slowest time among all players in 'PLAYING' state.
 * If none are in 'PLAYING' state, it gets the nearest segment start time.
 */
/*
function getUpdateTime() {
    //get the current time from the segment that is playing.
    var earliestPlayerTime = Number.MAX_VALUE;
    var timeInPlayableRange = Number.MAX_VALUE;
    var sliderTime = new Date(xgds_video.masterSlider.slider('value') * 1000);

    for (var key in xgds_video.displaySegments) { //for each source
        var segments = xgds_video.displaySegments[key];
        var sourceName = segments[0].source.shortName;
        var state = jwplayer(sourceName).getState();
        var playerTime = getPlayerVideoTime(sourceName);

        //this is needed for the case where one of the players is paused (or both)
        //but it's paused at a time that can be played (within segment)
        if (getPlaylistIdxAndOffset(sliderTime, sourceName) != false ) {
            if (sliderTime < timeInPlayableRange) {
                timeInPlayableRange = sliderTime;
            }
        }
    
        if (state == 'PLAYING') {
            if (playerTime < earliestPlayerTime) {
                earliestPlayerTime = getPlayerVideoTime(sourceName);
            }
        }
    } 

    var updateTime = null;
    //none of the players were in 'PLAYING' state.
    if (earliestPlayerTime == Number.MAX_VALUE) { 
        //check if any of the players are in a playable range.
        if (timeInPlayableRange != Number.MAX_VALUE) {
            updateTime = timeInPlayableRange;
        } else { //all players are in between segments
            var prevTime = new Date(xgds_video.masterSlider.slider('value') * 1000);
            updateTime = getNextAvailableSegment(prevTime);
        }
    } else { //at least one player was in 'PLAYING' state
        updateTime = earliestPlayerTime;
    }
    return updateTime;
}
*/

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
                        // otherwise slider jumps around while moving.
                        if (xgds_video.movingSlider == true) {
                            return;
                        }

                        // update test site time (all sources that are 'PLAYING')
                        var testSiteTime = getPlayerVideoTime(this.id);
                        setPlayerTimeLabel(testSiteTime, this.id);

                        if (xgds_video.onTimePlayer == this.id) {
                            // update the slider here.
                            //XXX if the play flag is off, shouldn't be player shouldn't be playing.
                            var updateTime = getPlayerVideoTime(this.id);
                            setSliderTime(updateTime);
                        }
                    }
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
            xgds_video.playerTime = seekDateTime;
            xgds_video.playerSource = sourceName;
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

    var currTime = new Date(xgds_video.masterSlider.slider('value') * 1000);
    for (var key in xgds_video.displaySegments) {
        var segments = xgds_video.displaySegments[key];
        var sourceName = segments[0].source.shortName;
        jumpToPosition(currTime, sourceName);
        xgds_video.playerTime = getPlayerVideoTime(sourceName);
        xgds_video.playerSource = sourceName;
    }
    setSliderTime(currTime);
}


