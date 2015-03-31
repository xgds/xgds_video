// __BEGIN_LICENSE__
//Copyright (c) 2015, United States Government, as represented by the 
//Administrator of the National Aeronautics and Space Administration. 
//All rights reserved.
//
//The xGDS platform is licensed under the Apache License, Version 2.0 
//(the "License"); you may not use this file except in compliance with the License. 
//You may obtain a copy of the License at 
//http://www.apache.org/licenses/LICENSE-2.0.
//
//Unless required by applicable law or agreed to in writing, software distributed 
//under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR 
//CONDITIONS OF ANY KIND, either express or implied. See the License for the 
//specific language governing permissions and limitations under the License.
// __END_LICENSE__

var pendingPlayerActions = {};
var playlistsLoaded = false;

/**
 * ensures that only one onTime event is enabled
 */
function onTimeController(player) {
    if (!xgds_video.playFlag) {
        return;
    }
    if (xgds_video.seekFlag || xgds_video.movingSlider) {
        return;
    }

    var switchPlayer = false;
    if (player.id == xgds_video.onTimePlayer) {
        if (player.getState() != 'PLAYING') {
            switchPlayer = true;
        }
    } else if (jwplayer(xgds_video.onTimePlayer).getState() != 'PLAYING') {
        switchPlayer = true;
    }
    if (switchPlayer) {
        updateSliderFromPlayer();
    }
}

function updateSliderFromPlayer() {
	var foundPlayingPlayer = false;
    for (var source in xgds_video.displaySegments) {
        if (jwplayer(source).getState() == 'PLAYING') {
            xgds_video.onTimePlayer = source;
            foundPlayingPlayer = true;
            console.log("TIME DRIVING PLAYER " + source);
            break;
        }
    }
    
    if (foundPlayingPlayer == false) {
        //set the xgds_video.onTimePlayer to the player with the nearest segment
        //to current slider time
        var time = getSliderTime();
        var sourceName = getNextAvailableSegment(time)['source'];
        if (!(_.isUndefined(sourceName)) && !(_.isEmpty(sourceName))) { //there is only one segment for each source and
            //none of the players are in 'PLAYING' state.
            xgds_video.onTimePlayer = sourceName;
            console.log("TIME DRIVING PLAYER NEXT SEGMENT" + sourceName);
        } //else leave the onTimePlayer as it is.
    }
}


/**
 * Only called once onReady. Kickstarts the player with earliest starttime.
 */
function startPlayers() {
    if (xgds_video.noteTimeStamp != null) { // noteTimeStamp is in local time (i.e. PDT)
        var datetime = xgds_video.noteTimeStamp;
        //check if datetime is valid
        if ((datetime != 'Invalid Date') && ((datetime >= xgds_video.firstSegment.startTime) &&
            (datetime < xgds_video.lastSegment.endTime))) {
            xgds_video.initialState = true; //to prevent onTime from being run right away before player had a chance to seek to init location
            seekAllPlayersToTime(datetime);
            return;
        }
    }
    
    //find the first segment and play it.
    var startTime = xgds_video.firstSegment.startTime;
    for (var source in xgds_video.displaySegments) {
        var segments = xgds_video.displaySegments[source];
        if (startTime >= segments[0].startTime) {
            console.log('starting ' + source);
            jwplayer(source).play(true);
        } else {
            console.log('delaying ' + source);
        }
    }
}


/**
 * Only called once onReady. Reads offset from URL hash
 * (i.e. http://mvp.xgds.snrf/xgds_video/archivedImageStream/2014-06-19#19:00:00)
 * and seeks to that time.
 */
function seekFromUrlOffset() {
    var timestr = window.location.hash.substr(1); //i.e. 19:00:00
    seekHelper(timestr);
}


/**
 * If the source is a diver, and no other divers are enabled, turn it on.
 */
function soundController() {
    var soundOn = false;
    for (var source in xgds_video.displaySegments) {
        //TODO fix -- encode in DB or check if there is an audio stream, potentiall onMeta can give us some info
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
    var videoHeight = Math.round(maxWidth * (9/16));

    for (var source in xgds_video.displaySegments) {
    //for (var i = 0; i < numSources; i = i + 1) {
    //    var source = Object.keys(xgds_video.displaySegments)[i];
        // list of video segments with same source & episode (if given)
        var segments = xgds_video.displaySegments[source];
        xgds_video.displaySegments[source].startTime = segments[0].startTime;
        xgds_video.displaySegments[source].endTime = segments[segments.length - 1].endTime;
        
        //if there are no segments to show, dont build a player.
        if (_.isUndefined(segments) || _.isEmpty(segments)) {
            continue;
        }
        
        // paths of the video segments
        var flightName = xgds_video.flightName;
        if (flightName == null) {
            flightName = xgds_video.episode + '_' + xgds_video.sourceVehicle[source]; //TODO: TEST THIS!
        }
        var videoPaths = getFilePaths(flightName, source, segments);
        
        jwplayer(source).setup({
            file: videoPaths[0], // note jwplayer bug prevents initial load of playlist until onReady
            autostart: false,
            width: maxWidth,
            height: videoHeight,
            //skin: STATIC_URL + 'external/js/jwplayer/jw6-skin-sdk/skins/six/six.xml',
            mute: true,
            analytics: {
                enabled: false,
                cookies: false
            },
	    /*listbar: {
		position: "right",
		size: 240
	    },
            controls: true, //for debugging
            */
            events: {
                onReady: function() {
                    setupPlaylist(this.id);
                    //if there is a seektime in the url, start videos at that time.
                    if (window.location.hash) {
                        seekFromUrlOffset();
                    } else {
                        startPlayers();
                    }
                    soundController();
                },
                onComplete: function() {
                    //stop until start of the next segment.
                    this.pause(true);
                    onSegmentComplete(this);
                },
                onPlay: function(e) { //gets called per source
                    console.log("onPlay: playlist " + this.id + " index " + this.getPlaylistIndex());
                    var segments = xgds_video.displaySegments[this.id];
                    var segment = segments[this.getPlaylistIndex()];
                    console.log("seg start " + segment.startTime + " seg end " + segment.endTime);
                    var pendingActions = pendingPlayerActions[this.id];
                    if (!(_.isUndefined(pendingActions)) && !(_.isEmpty(pendingActions))) {
                        for (var i = 0; i < pendingActions.length; i++) {
                            console.log(this.id + " ABOUT TO SEEK ");
                            pendingActions[i].action(pendingActions[i].arg);
                            console.log(this.id + ": pending: " + pendingActions[i].arg);
                            console.log("onPlay1: playlist " + this.id + " index " + this.getPlaylistIndex());
                        }
                        pendingPlayerActions[this.id] = [];
                    }
                    if (xgds_video.initialState == true) {
                        xgds_video.initialState = false;
                    }
                    if (xgds_video.seekFlag) {
                        xgds_video.seekFlag = false;
                        console.log("onPlay2: playlist " + this.id + " index " + this.getPlaylistIndex());
                        updateSliderFromPlayer();
                        console.log("onPlay3: playlist " + this.id + " index " + this.getPlaylistIndex());
                    }
                    onTimeController(this);
                    console.log("onPlay4: playlist " + this.id + " index " + this.getPlaylistIndex());
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
		/*onSeek: function(e) {
		    console.log("seek playlist index " + this.getPlaylistIndex());
		    console.log('seek ');
		    onTimeController(this);
                },*/
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
                    if (!xgds_video.seekFlag && !xgds_video.movingSlider) {
                        var testSiteTime = getPlayerVideoTime(this.id);
                        setPlayerTimeLabel(testSiteTime, this.id);

                        if (xgds_video.initialState != true) {
                            //if this call is from the current 'onTimePlayer'
                            if (xgds_video.onTimePlayer == this.id) {
                                // update the slider here.
                                var updateTime = getPlayerVideoTime(this.id);
                                if (!(_.isUndefined(updateTime))) {
                                    awakenIdlePlayers(updateTime, this.id);
                                    setSliderTime(updateTime);
                                }
                            }
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
    }
}

/*
 * Set up the playlist for the given source
 */
function setupPlaylist(source) {
    // list of video segments with same source & episode (if given)
    var segments = xgds_video.displaySegments[source];
    
    // paths of the video segments
    var flightName = xgds_video.flightName;
    if (flightName == null) {
        flightName = xgds_video.episode + '_' + xgds_video.sourceVehicle[source]; //TODO: TEST THIS!
    }

    var videoPaths = getFilePaths(flightName, source, segments);
    
    // load the segments as playlist.
    var myplaylist = [];
    for (var k = 0; k < videoPaths.length; k++) {
        var mysources = [];
        var newItem = {
            file: videoPaths[k],
            label: videoPaths[k]
        };
        mysources.push(newItem);
        myplaylist.push({title: source + " " + k, sources:mysources});
    };
    jwplayer(source).load(myplaylist);
}


/**********************************
            Call-backs
 ***********************************/

/**
 * Updates the player and the slider times based on
 * the seek time value specified in the 'seek' text box.
 */
function seekCallBack() {
    var seekTimeStr = $('#seekTime').value();
    if ((seekTimeStr == null) ||
        (Object.keys(xgds_video.displaySegments).length < 1)) {
        return;
    }
    seekHelper(seekTimeStr);
}


/**
 * Callback function for play/pause button
 */
function playPauseButtonCallBack() {
    xgds_video.playFlag = !xgds_video.playFlag;
    if (xgds_video.playFlag) {
        $('#playbutton').addClass("icon-pause");
        $('#playbutton').removeClass("icon-play");
    } else {
        $('#playbutton').removeClass("icon-pause");
        $('#playbutton').addClass("icon-play");
    }

    var currTime = getSliderTime();
    for (var source in xgds_video.displaySegments) {
        var segments = xgds_video.displaySegments[source];

        if (!xgds_video.playFlag) {
            jwplayer(source).pause(true);
        } else {
            // make sure that you have stuff to play for each source
            var segments = xgds_video.displaySegments[source];
            var currentIndex = jwplayer(source).getPlaylistIndex();
            if (!(_.isUndefined(currentIndex))) {
	            var segment = segments[currentIndex];
                if ((segment.startTime <= currTime) && (segment.endTime >= currTime)) {
                    jwplayer(source).play(true);
                }
            }
        }
    }
    setSliderTime(currTime);
}


/**
 * Event for 'Image Info" button click
 */
function imageInfoButtonEvent(sourceShortName) {
    var jsTime = getPlayerVideoTime(sourceShortName);
    var unixTime = toUnixPosixTime(jsTime);
    // yes this is hacky but the image info page's url is using a
    // dataproduct id and there's no straightforward way of getting these names
    // others than hard coding it here.
    var imageName = "";
    //TODO this needs to be removed from this javascript.
    if (sourceShortName == 'HZR') {
        imageName = 'HazCamRight-' + unixTime;
    } else if (sourceShortName == 'HZL') {
        imageName = 'HazCamLeft-' + unixTime;
    } else if (sourceShortName == 'NVS') {
        imageName = 'NIRVSS-' + unixTime;
    } else if (sourceShortName == 'GND') {
        imageName = 'GroundCam-' + unixTime;
    } else if (sourceShortName == 'TXC') {
        imageName = 'TextureCam-' + unixTime;
    } else {
        console.log("ERROR: cannot define image name in 'imageInfoButtonEvent'. Invalid camera name given.");
    }
    var filePath = mvpAppUrl.replace('dummy',imageName);
    window.open(filePath);
}
