//globals. There are more in the template.
var g_masterSlider = '';
var g_playFlag = true;
var g_initialState = true;

var g_seekFlag = false;
var g_seekOffsetList = {}; 

/***************************
           Helpers
****************************/

jQuery(function($) {
var windowWidth = $(window).width();
    $(window).resize(function()  {
        if (windowWidth != $(window).width()) {
            location.reload();
            return;
        }
    });
});


//checks if json dict is empty
function isEmpty(ob){
   for(var i in ob){ return false;}
  return true;
}


function setText(id, messageText) {
    document.getElementById(id).innerHTML = messageText;
}


/**
 * helper to parse seektime into hours, minutes, seconds
 */
function seekTimeParser(str) {
    var hmsArray = str.split(':');
    return hmsArray;
}

function padNum(num, size) {
    var s = num + '';
    while (s.length < size) {
        s = '0' + s;
    }
    return s;
}


/**
 * Helper that returns file paths of video segments with same source
 */
function getFilePaths(episode, segments) {
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


//TODO: get the color from either the vehicle or the source. Need to add color column to the model
function getRandomColor() {
    var letters = '0123456789ABCDEF'.split('');
    var color = '#';
    for (var i = 0; i < 6; i++) {
        color += letters[Math.round(Math.random() * 15)];
    }
    return color;
}


function setSliderTime(datetime) {
    //update the slider
    g_masterSlider.slider('value', Math.round(datetime.getTime() / 1000));
    $('#sliderTimeLabel').val(datetime.toTimeString());
}


function setPlayerTimeLabel(datetime, sourceName) {
    //set test site time of the player
    setText('testSiteTime' + sourceName, datetime.toString());
}


/**
 * Helper
 * Given current time in javascript datetime,
 * find the playlist item and the offset (seconds) and seek to there.
 */
function seekToOffset(currTime, sourceName) {
    //find the playlist item index and offset the current time falls under for this player.
    var playlistIdx = null;
    var offset = null;
    var segments = displaySegments[sourceName];
    for (var i = 0; i < segments.length; i++) {
        if ((currTime >= segments[i].startTime) && (currTime <= segments[i].endTime)) {
            playlistIdx = i;
            offset = Math.round((currTime - segments[i].startTime) / 1000); //in seconds
            
            //seek later (onPlay). Otherwise it won't work.
            g_seekFlag = true;
            g_seekOffsetList[sourceName] = offset  

            break;
        }
    }
   
    var player = jwplayer('myPlayer'+sourceName);
    if ((playlistIdx != null) && (offset != null)) { //currTime falls in one of the segments.
        //update the player
        player.playlistItem(playlistIdx);
    
        if (g_playFlag) {
            player.play(true);
        } else {
            player.pause(true);
        }
    } else { //current time is not in the playable range.
        //pause the player
        player.pause(true);
        return;
    }
}


function getNextAvailableSegment(currentTime) {
    var nearestSeg = null;
    var minDelta = Number.MAX_VALUE;
    var sources = [];

    for (var key in displaySegments) {
        var segments = displaySegments[key];
        sources.push(segments[0].source.shortName);
        for (var id in segments) {
            var segment = segments[id]; 
            var delta = segment.startTime - currentTime;

            if ((delta < minDelta) && (delta >= 0)) {
                minDelta = delta;
                nearestSeg = segment;
            }
        }
    }
    
    if (nearestSeg == null) {
        return currentTime;
    } else {
        return nearestSeg.startTime; // need to seek to this time.
    }
}


/**
 * Helper for returning current test site time from the jwplayer.
 */
function getPlayerVideoTime(source) {
    var segments = displaySegments[source];
    var player = jwplayer('myPlayer' + source);
    var index = player.getPlaylistIndex(); //index of video segment it is currently playing
    var offset = player.getPosition(); //in seconds

    var totalPlayTime = 0;
    for (var i = 0; i < index; i++) {
        totalPlayTime += segments[i].endTime.getTime() - segments[i].startTime.getTime(); //in miliseconds
    }
    totalPlayTime += (offset * 1000);

    var currentTime = segments[0].startTime.getTime() + totalPlayTime;
    currentTime = new Date(currentTime);
    return currentTime;
}

/** 
 * Helper that returns slowest time among all players in 'PLAYING' state.
 * If none are in 'PLAYING' state, it gets the nearest segment start time.
 */
function getUpdateTime() {
    //get the current time from the segment that is playing.        
    var earliestPlayerTime = Number.MAX_VALUE;
 
    for (var key in displaySegments) { //for each source
        var segments = displaySegments[key];
        var sourceName = segments[0].source.shortName;
        var state = jwplayer('myPlayer'+sourceName).getState();

        if (state == 'PLAYING') {
            if (getPlayerVideoTime(sourceName) < earliestPlayerTime) {
                earliestPlayerTime = getPlayerVideoTime(sourceName);
            }
        } 
    }
    
    var updateTime = null;
    if (earliestPlayerTime == Number.MAX_VALUE) { //none of the players were in 'PLAYING' state.
        var prevTime = new Date(g_masterSlider.slider('value') * 1000);
        updateTime = getNextAvailableSegment(prevTime);
    } else { //at least one player was in 'PLAYING' state
        updateTime = earliestPlayerTime;
    }
    return updateTime;
}


/****************************   
           Set-up
*****************************/

/**
 * Create a slider legend that shows breaks between segments
 */
function createSliderLegend() {
    for (var key in displaySegments) {
        //construct a playlist from these video segments!
        var segments = displaySegments[key]; //list of video segments with same source & episode
        var source = segments[0].source;

        //get the total slider range in seconds
        var startTime = g_masterSlider.slider('option', 'min');
        var endTime = g_masterSlider.slider('option', 'max');
        var totalDuration = endTime - startTime;  // in seconds
        var color = getRandomColor();

        //handle empty space infront of first segment
        emptySegmentDuration = Math.round(segments[0].startTime / 1000) - startTime;
        emptySegmentWidth = g_masterSlider.width() * (emptySegmentDuration / totalDuration);
        g_masterSlider.before('<img class="' + source.shortName + '" width="' + emptySegmentWidth + '" height="5px" style="opacity:0.0;">');

        //for each video segment
        $.each(segments, function(id) {
            var segment = segments[id];
            var source = segment.source;
            //get the duration of the =video segment
            var segDuration = Math.round((segment.endTime - segment.startTime) / 1000); //in seconds
            var width = g_masterSlider.width() * (segDuration / totalDuration);

            //draw the visualization
            g_masterSlider.before('<img class="' + source.shortName + '" id=' + id + ' width="' + width +
                                '" height="5px" style="background-color:'+color+';">');
            var emptySegmentDuration;
            var emptySegmentWidth;

            if (segments[id + 1]) { //if there is a next segment
                var nextSegment = segments[id+1];
                emptySegmentDuration = Math.round((nextSegment.startTime - segment.endTime) / 1000);
                emptySegmentWidth = g_masterSlider.width() * (emptySegmentDuration / totalDuration);
                g_masterSlider.before('<img class="' + source.shortName + '" width="' + emptySegmentWidth +
                                    '" height="5px" style="opacity:0.0;">');
            }
        });
        //wrap segments of each source in a div
        $('.'+source.shortName ).wrapAll( '<div class="divider";"></div>');
    }
}

/**
 * initialize master slider with range (episode start time->episode end time)
 */
function setupSlider() {
    if (episode) { //video episode needed to set slider range
        var endTime = (episode.endTime) ? episode.endTime : lastSegment.endTime;
        if (endTime) {
            g_masterSlider = $('#masterSlider').slider({
                step: 1,
                min: Math.floor(firstSegment.startTime.getTime() / 1000), //in seconds
                max: Math.ceil(endTime.getTime() / 1000), //in seconds
                stop: uponSliderStopCallBack,
                slide: uponSliderMoveCallBack,
                range: 'min'
            });
            var sliderTime = new Date($('#masterSlider').slider('value') * 1000);
            $('#sliderTimeLabel').val(sliderTime.toTimeString());
            createSliderLegend();
        } else {
            alert('The end time of video segment not available. Cannot setup slider');
        }
    } else {
        alert('The video episode is not available.');
    }
}


/**
 * Initialize jw player and call update values
 */
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
                file: videoPaths[0],
                autostart: false,
                width: maxWidth,
                height: size[1],
                mute: true,
                controlbar: 'none',
                skin: STATIC_URL + 'external/js/jwplayer/jw6-skin-sdk/skins/five/five.xml',
                events: {
                    onReady: function() {
                        //if it's the first segment, it should start playing.
                        if (firstSegment.startTime == segments[0].startTime) {
                            jwplayer('myPlayer' + source.shortName).play(true);
                            //updateValues();
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
                                var player = jwplayer('myPlayer' + sourceName);
                                player.pause(true);
                            }
                            document.getElementById('playbutton').className = 'fa fa-play fa-2x';
                        }
                    },
                    onComplete: function() {
                        //upon complete, stop. It should start segment at the right time (in updateValues).
                        jwplayer('myPlayer' + source.shortName).pause(true);
                    },
                    onPlay: function(e) {
                        if (g_initialState) {
                            updateValues();
                            g_initialState = false;
                        }
                        if (g_seekFlag) {
                            if (!isEmpty(g_seekOffsetList)) {
                                for (var source in g_seekOffsetList) {
                                    jwplayer('myPlayer'+source).seek(g_seekOffsetList[source]);
                                }
                            }
                            g_seekOffsetList = {};
                            g_seekFlag = false;
                        }
                    }
                }, 
                listbar: {
                position: 'right',
                size: 150
                },
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



/**********************************
            Call-backs
***********************************/

/**
 * Updates the player and the slider times based on 
 * the seek time value specified in the 'seek' text box.
 */
function seekCallBack() {
    var seekTimeStr = document.getElementById('seekTime').value;

    if ((seekTimeStr == null) || (Object.keys(displaySegments).length < 1)) {
        return;
    }

    var seekDateTime = null;
    for (var key in displaySegments) {
        var segments = displaySegments[key];
        var sourceName = segments[0].source.shortName;

        var seekTime = seekTimeParser(seekTimeStr);
        seekDateTime = new Date(segments[0].endTime); //XXX for now assume seek time's date is same as first segment's end date
        seekDateTime.setHours(parseInt(seekTime[0]));
        seekDateTime.setMinutes(parseInt(seekTime[1]));
        seekDateTime.setSeconds(parseInt(seekTime[2]));

        var player = jwplayer('myPlayer' + sourceName);
        if (player != undefined) {
            seekToOffset(seekDateTime,sourceName);
            setPlayerTimeLabel(getPlayerVideoTime(sourceName),sourceName);
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
    g_playFlag = !g_playFlag;
    if (g_playFlag) {
        document.getElementById('playbutton').className = 'fa fa-pause fa-2x';
    } else {
        document.getElementById('playbutton').className = 'fa fa-play fa-2x';
    }

    var currTime = new Date(g_masterSlider.slider('value') * 1000);
    for (var key in displaySegments) {
        var segments = displaySegments[key];
        var sourceName = segments[0].source.shortName;
        seekToOffset(currTime, sourceName);
        setPlayerTimeLabel(getPlayerVideoTime(sourceName), sourceName);
    }
    setSliderTime(currTime);
}


/**
 * Slider Callback:
 * update slider time text when moving slider.
 */
function uponSliderMoveCallBack(event, ui) {
    var sliderTime = new Date(ui.value * 1000);
    $('#sliderTimeLabel').val(sliderTime.toTimeString());
}


/**
 * Slider Callback:
 *    get the current slider position and do
 *    offset = slider position - each video's start time
 *    seek each video at offset. (means each video's offset will be different, but their test site time same)
 *    update the test site times to equal slider position.
 */
function uponSliderStopCallBack(event, ui) {
    var currTime = g_masterSlider.slider('value'); //in seconds
    currTime = new Date(currTime * 1000); //convert to javascript date

    for (var key in displaySegments) {
        var sourceName = displaySegments[key][0].source.shortName;
        seekToOffset(currTime, sourceName);
        setPlayerTimeLabel(getPlayerVideoTime(sourceName), sourceName);
    }
}


/**
 * updateValues increments the slider every second (if the state is 'play').
 */
function updateValues() {
    if (g_playFlag == true) { 
        var updateTime = getUpdateTime();
        var udpateSliderTime = true;

        //update players
        for (var key in displaySegments) { //for each source
            var segments = displaySegments[key];
            var sourceName = segments[0].source.shortName;
            var state = jwplayer('myPlayer'+sourceName).getState();
            if (state == 'PLAYING') {
                //No op
                var testSiteTime = getPlayerVideoTime(sourceName);
                setText('testSiteTime' + sourceName, testSiteTime.toString());
            } else if (state == 'PAUSED') {
                //it is in between segments. don't do anything. 
            } else if (state == 'IDLE') {
                seekToOffset(updateTime, sourceName);
                setPlayerTimeLabel(getPlayerVideoTime(sourceName), sourceName);
            } else if (state == 'BUFFERING') {
                updateSliderTime = false; //XXX don't udpate the time, and don't do anything.
            } 
            else { //undefined
                //No op
            }
        }

        //update slider
        if (updateSliderTime) {
            setSliderTime(updateTime);
        }

    } else { //g_playFlag == false
        for (var key in displaySegments) {
            var segments = displaySegments[key];
            var sourceName = segments[0].source.shortName;
            var state = jwplayer('myPlayer'+sourceName).getState();
            if (state == 'PLAYING') {
                jwplayer('myPlayer'+sourceName).pause(true);
            }
        }
    }

    //recurse every second!
    setTimeout(updateValues, 1000);
} 
