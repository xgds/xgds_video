var masterSlider = '';
var playFlag = true;


function setText(id, messageText) {
    document.getElementById(id).innerHTML = messageText;
}


//helper to parse seektime into hours, minutes, seconds
function seekTimeParser(str) {
    var hmsArray = str.split(':');
    return hmsArray;
}


function getPlaylistIdxAndOffset(segments, currTime) {
    /*
     * Helper for uponSliderStop.
     * Given current time in javascript datetime,
     * find the playlist item and the offset (seconds) to seek to.
     */
    var playlistIdx = 0;
    var offset = 0;
    for (var i = 0; i < segments.length; i++) {
        if ((currTime >= segments[i].startTime) && (currTime <= segments[i].endTime)) {
            playlistIdx = i;
            offset = currTime - segments[i].startTime;
            return [playlistIdx, offset];
        }
    }
    return false;
}


/**
 * Seek Video from time.
 * Update the slider value, slider text
 * update the jwplayer position
 *    offset = seek time - video start time.
 **/
function seekToTime() {
    var seekTimeStr = document.getElementById('seekTime').value;

    if ((seekTimeStr == null) || (Object.keys(displaySegments).length < 1)) {
        return;
    }

    for (var key in displaySegments) {
        var segments = displaySegments[key];
        var sourceName = segments[0].source.shortName;

        var seekTime = seekTimeParser(seekTimeStr);
        var seekDateTime = new Date(segments[0].endTime); //XXX for now assume seek time's date is same as first segment's end date
        seekDateTime.setHours(parseInt(seekTime[0]));
        seekDateTime.setMinutes(parseInt(seekTime[1]));
        seekDateTime.setSeconds(parseInt(seekTime[2]));

        var player = jwplayer('myPlayer' + sourceName);
        if (player != undefined) {
            if (getPlaylistIdxAndOffset(segments, seekDateTime)) { //if seek time falls under a playable range
                var idx = getPlaylistIdxAndOffset(segments, seekDateTime)[0];
                var offset = getPlaylistIdxAndOffset(segments, seekDateTime)[1];
                
                //update the player
                jwplayer('myPlayer'+sourceName).playlistItem(idx).play(true);
                jwplayer('myPlayer'+sourceName).seek(offset);
                
                //update the slider
                masterSlider.slider('value', Math.round(seekDateTime.getTime()/1000)); //increment slider value by one second
                var sliderTime = new Date(masterSlider.slider('value')*1000);
                $('#sliderTimeLabel').val(sliderTime.toTimeString());

                if (playFlag) {
                    player.play(true);
                } else {
                    player.pause(true);
                }
            }
        }
    }
}


/**
 * initialize master slider with range (episode start time->episode end time)
 **/
 //XXX slider legend : http://stackoverflow.com/questions/10224856/jquery-ui-slider-labels-under-slider
function setupSlider() {
    if (episode) { //video episode needed to set slider range
        var endTime = (episode.endTime) ? episode.endTime : lastSegment.endTime;
        if (endTime) {
            masterSlider = $('#masterSlider').slider({
                step: 1,
                min: Math.floor(firstSegment.startTime.getTime() / 1000), //in seconds
                max: Math.ceil(endTime.getTime() / 1000), //in seconds
                stop: uponSliderStop,
                slide: uponSliderMove,
                range: 'min'
            });
            var sliderTime = new Date($('#masterSlider').slider('value') * 1000);
            $('#sliderTimeLabel').val(sliderTime.toTimeString());
        } else {
            alert('The end time of video segment not available. Cannot setup slider');
        }
    } else {
        alert('The video episode is not available.');
    }
}


/**
 * Callback function for play/pause button
 **/
function playPauseButtonCallBack() {
    playFlag = !playFlag;
    if (playFlag) {
        for (var key in displaySegments) {
            var segments = displaySegments[key];
            var sourceName = segments[0].source.shortName;
            var player = jwplayer('myPlayer' + sourceName);
            var currTime = new Date(masterSlider.slider('value') * 1000);
            if (getPlaylistIdxAndOffset(segments, currTime)) { //if seek time falls under a playable range
                var idx = getPlaylistIdxAndOffset(segments, currTime)[0];
                var offset = getPlaylistIdxAndOffset(segments, currTime)[1];
                if (player.getState() != 'BUFFERING') {
                    player.playlistItem(idx);//.play(true);
                    player.seek(offset);    
                    player.play(true);
                }
            }
        }
        document.getElementById('playbutton').className = 'fa fa-pause fa-2x';
    } else {
        for (var key in displaySegments) {
            var segments = displaySegments[key];
            var sourceName = segments[0].source.shortName;
            var player = jwplayer('myPlayer' + sourceName);
            player.pause(true);
        }
        document.getElementById('playbutton').className = 'fa fa-play fa-2x';
    }
}


function padNum(num, size) {
    var s = num + '';
    while (s.length < size) {
        s = '0' + s;
    }
    return s;
}


function getFilePaths(episode, segments) {
    /*
     * Helper that returns file paths of video segments with same source
     */
    var filePaths = [];
    $.each(segments, function(id) {
        var segment = segments[id];
        var source = segment.source;
        var sourceName = segment.source.shortName;
        var path = baseUrl + episode.shortName + '_' + source.shortName + '/Video/Recordings/' +
            segment.directoryName + padNum(segment.segNumber, 3) + '/' + segment.indexFileName;
        filePaths.push(path);
    });
    return filePaths;
}


/**
 * Initialize jw player and call update values
 **/

function setupJWplayer() {
    if (episode) { //if episode exists
        var maxWidth = getMaxWidth(Object.keys(displaySegments).length);
        for (var key in displaySegments) {
            //construct a playlist from these video segments!
            var segments = displaySegments[key]; //list of video segments with same source & episode
            var source = segments[0].source;
            var videoPaths = getFilePaths(episode, segments);
            var size = calculateSize(maxWidth, segments[0].settings.height,
                                         segments[0].settings.width);

            jwplayer('myPlayer' + source.shortName).setup({
                //height: size[1],
            	aspectRatio: '16:9',
                width: size[0],
                file: videoPaths[0],
                autostart: false,
                mute: true,
                controlbar: 'none',
                skin: STATIC_URL + 'external/js/jwplayer/jw6-skin-sdk/skins/five/five.xml',
                events: {
                    onReady: function() {
                        //if it's the first segment, it should start playing.
                        if (firstSegment.startTime == segments[0].startTime) {
                            jwplayer('myPlayer' + source.shortName).play(true);
                            updateValues();
                        }
                    },
                    onBuffer: function(e) {
                        if ((e.oldstate == 'PLAYING') || (e.oldstate == 'PAUSED')) {
                            //all the players need to be paused, including the slider.
                            if (e.oldstate == 'PLAYING') {
                                playState = !playState; //change the state to paused
                            }

                            //pause all the players
                            for (var key in displaySegments) {
                                var segments = displaySegments[key];
                                var sourceName = segments[0].source.shortName;
                                var player = jwplayer('myPlayer'+sourceName);
                                player.pause(true);
                            }   
                            document.getElementById("playbutton").className="fa fa-play fa-2x"
                        }
                    },
                    onComplete: function() {
                        //upon complete, stop. It should start segment at the right time (in updateValues).
                        jwplayer('myPlayer' + source.shortName).pause(true);
                    }
                },
                listbar: { //this list bar is just for debug
                    position: 'right',
                    size: 120
                }
            });

            var playlist = [];
            for (var k = 0; k < videoPaths.length; k++) {
                var newItem = {
                    file: videoPaths[k],
                    title: videoPaths[k]
                };
                playlist.push(newItem);
            }
            jwplayer('myPlayer' + source.shortName).load(playlist);
         }
    } else {
        alert('episode not available. Cannot set up jwplayer');
    }
}


/**
 * Slider Callback:
 * update slider time text when moving slider.
 **/
function uponSliderMove(event, ui) {
    var sliderTime = new Date(ui.value * 1000);
    $('#sliderTimeLabel').val(sliderTime.toTimeString());
}


/**
 * Slider Callback:
 *    get the current slider position and do
 *    offset = slider position - each video's start time
 *    seek each video at offset. (means each video's offset will be different, but their test site time same)
 *    update the test site times to equal slider position.
 **/
function uponSliderStop(event, ui) {
    var currTime = masterSlider.slider('value'); //in seconds
    currTime = new Date(currTime * 1000); //convert to javascript date

    for (var key in displaySegments) {
        var segments = displaySegments[key];
        var source = segments[0].source;

        var player = jwplayer('myPlayer' + source.shortName);
        //given current time, which segment and what is the offset in that segment?
        if (getPlaylistIdxAndOffset(segments, currTime)) { // if the seektime is in the playable range (within segment start and stop times)
            var index = getPlaylistIdxAndOffset(segments, currTime)[0];
            var offset = getPlaylistIdxAndOffset(segments, currTime)[1];
            var state = player.getState();
            if (state == 'PAUSED') {
                //XXX this doesn't pause properly
                player.playlistItem(index).setMute(true).seek(offset).pause(true);
            } else if ((state == 'PLAYING') || (state == 'IDLE')) {
                player.playlistItem(index).setMute(true).seek(offset).play(true);
            } else { //buffering
                // player is not ready yet
            }

            //set testsite time for each player (get it from the player itself. this should match slider time)
            var testSiteMiliSec = 0;
            for (var s = 0; s < index; s++) {
                testSiteMiliSec += segments[s].endTime.getTime() - segments[s].startTime.getTime();
            }
            testSiteMiliSec += (offset * 1000);
            testSiteMiliSec += segments[0].startTime.getTime();
            var testSiteTime = new Date(testSiteMiliSec);
            setText('testSiteTime' + source.shortName, testSiteTime.toString() + ' ' + segments[0].timeZone);
        } else {
            if (jwplayer('myPlayer' + source.shortName).getState() == 'PLAYING') {
                jwplayer('myPlayer' + source.shortName).pause(true);
            }
        }
    }
}


/*
 * updateValues increments the slider every second (if the state is 'play').
 */
function updateValues() {
    if (!playFlag) {
        return;
    }
    
    //play the videos and update slider only if play flag is on.
    for (var key in displaySegments) {
        var segments = displaySegments[key];
        var sourceName = segments[0].source.shortName;
        var datetime = new Date(masterSlider.slider('value')*1000);

        if (playFlag){ 
            if (jwplayer('myPlayer'+sourceName).getState() != 'PLAYING') {
                if (getPlaylistIdxAndOffset(segments,datetime)) {
                    var playlistIdx = getPlaylistIdxAndOffset(segments,datetime)[0];
                    var itemOffset = getPlaylistIdxAndOffset(segments,datetime)[1];
                    jwplayer('myPlayer'+sourceName).playlistItem(playlistIdx).play(true);
                    jwplayer('myPlayer'+sourceName).seek(itemOffset);
                } else {
                    //no playable range, so pause it.
                    if (jwplayer('myPlayer' + sourceName).getState() == 'PLAYING') {
                        jwplayer('myPlayer' + sourceName).pause(true);
                    }
                }
            }
        }

        //update the player time stamp
        setText('testSiteTime'+sourceName, datetime.toString()+' '+segments[0].timeZone);
    }

    // update the slider count.
    var currTime = masterSlider.slider('value') + 1; //in seconds
    masterSlider.slider('value', currTime); //increment slider value by one second
    //XXX investigate why it's incrementing by two seconds
    var sliderTime = new Date(masterSlider.slider('value') * 1000);
    $('#sliderTimeLabel').val(sliderTime.toTimeString());

    //recurse every second!
    setTimeout(updateValues, 1000);
}

