var masterSlider = '';
var playFlag = true;


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


function getRandomColor() {
    var letters = '0123456789ABCDEF'.split('');
    var color = '#';
    for (var i = 0; i < 6; i++) {
        color += letters[Math.round(Math.random() * 15)];
    }
    return color;
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
            break;
        }
    }
   
    var player = jwplayer('myPlayer'+sourceName);
    if ((playlistIdx != null) && (offset != null)) { //currTime falls in one of the segments.
        if (player.getState() != 'BUFFERING') {
            //update the player
            player.playlistItem(playlistIdx).play(true);
            player.seek(offset);

            //set test site time of the player
            var testSiteTime = getPlayerVideoTime(sourceName);
            setText('testSiteTime' + sourceName, currTime.toString() + ' ' + segments[0].timeZone);

            //update the slider //XXX this is going to get called for each source. Don't do that. call it once.
            masterSlider.slider('value', Math.round(currTime.getTime() / 1000));
            var sliderTime = new Date(masterSlider.slider('value') * 1000);
            $('#sliderTimeLabel').val(sliderTime.toTimeString());

            if (playFlag) {
                player.play(true);
            } else {
                player.pause(true);
            }
        }
    } else { //current time is not in the playable range.
        //pause the player
        player.pause(true);
    }
}


function jumpToNearestSegment(currentTime) {
    var nearestSeg = null;
    var minDelta = Number.MAX_VALUE;
    var sources = [];

    for (var key in displaySegments) {
        var segments = displaySegments[key];
        sources.push(segments[0].source.shortName);
        $.each(segments, function(id) {
            var segment = segments[id]; 
            var delta = Math.abs(currentTime - segment.startTime);

            if (delta < minDelta) {
                minDelta = delta;
                nearestSeg = segment;
            }
        });
    }

    return nearestSeg.startTime; // need to seek to this time.
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
 * Helper that returns slowest time given list of javascript datetimes.
 */
function getEarliestTime(dateTimes) {
    dateTimes.sort(function(a, b){
        return Date.parse(a) - Date.parse(b);
    });

    return dateTimes[0];

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
        var startTime = masterSlider.slider('option', 'min');
        var endTime = masterSlider.slider('option', 'max');
        var totalDuration = endTime - startTime;  // in seconds
        var color = getRandomColor();

        //handle empty space infront of first segment
        emptySegmentDuration = Math.round(segments[0].startTime / 1000) - startTime;
        emptySegmentWidth = masterSlider.width() * (emptySegmentDuration / totalDuration);
        masterSlider.before('<img class="' + source.shortName + '" width="' + emptySegmentWidth + '" height="5px" style="opacity:0.0;">');

        //for each video segment
        $.each(segments, function(id) {
            var segment = segments[id];
            var source = segment.source;
            //get the duration of the =video segment
            var segDuration = Math.round((segment.endTime - segment.startTime) / 1000); //in seconds
            var width = masterSlider.width() * (segDuration / totalDuration);

            //draw the visualization
            masterSlider.before('<img class="' + source.shortName + '" id=' + id + ' width="' + width +
                                '" height="5px" style="background-color:'+color+';">');
            var emptySegmentDuration;
            var emptySegmentWidth;

            if (segments[id + 1]) { //if there is a next segment
                var nextSegment = segments[id+1];
                emptySegmentDuration = Math.round((nextSegment.startTime - segment.endTime) / 1000);
                emptySegmentWidth = masterSlider.width() * (emptySegmentDuration / totalDuration);
                masterSlider.before('<img class="' + source.shortName + '" width="' + emptySegmentWidth +
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
            masterSlider = $('#masterSlider').slider({
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
                                var player = jwplayer('myPlayer' + sourceName);
                                player.pause(true);
                            }
                            document.getElementById('playbutton').className = 'fa fa-play fa-2x';
                        }
                    },
                    onComplete: function() {
                        //upon complete, stop. It should start segment at the right time (in updateValues).
                        jwplayer('myPlayer' + source.shortName).pause(true);
                    }
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
            seekToOffset(seekDateTime,sourceName);
        }
    }
}


/**
 * Callback function for play/pause button
 */
function playPauseButtonCallBack() {
    playFlag = !playFlag;
    if (playFlag) {
        document.getElementById('playbutton').className = 'fa fa-pause fa-2x';
    } else {
        document.getElementById('playbutton').className = 'fa fa-play fa-2x';
    }

    var currTime = new Date(masterSlider.slider('value') * 1000);
    for (var key in displaySegments) {
        var segments = displaySegments[key];
        var sourceName = segments[0].source.shortName;
        seekToOffset(currTime, sourceName);
    }
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
    var currTime = masterSlider.slider('value'); //in seconds
    currTime = new Date(currTime * 1000); //convert to javascript date

    for (var key in displaySegments) {
        var segments = displaySegments[key];
        var source = segments[0].source;
        var player = jwplayer('myPlayer' + source.shortName);
        seekToOffset(currTime, source.shortName);
    }
}


/**
 * updateValues increments the slider every second (if the state is 'play').
 */
function updateValues() {
    if (playFlag == true) {
        //get the current time from the segment that is playing.
        var currentVideoTimes = [];
        var idleSources = []; //list of sources that are idle.
        for (var key in displaySegments) { //for each source
            var segments = displaySegments[key];
            var sourceName = segments[0].source.shortName;
            var state = jwplayer('myPlayer'+sourceName).getState();
            console.log("state of "+sourceName+" is "+state);

            if (state == 'PLAYING') {
                currentVideoTimes.push(getPlayerVideoTime(sourceName)); 
            } /*else if ((state == 'BUFFERING') || (state == undefined)) {
                //if one of the players is buffering or undefined, pause all players and don't update the slider time.
                for (var key2 in displaySegments) {
                    var sourceName2 = displaySegments[key2][0].source.shortName;
                    var player = jwplayer('myPlayer'+sourceName2);
                    if (player.getState() == 'PLAYING') {
                        player.pause(true);
                    }
                }
                setText('testSiteTime'+sourceName, "the state of this player is: "+state);
                
                //recurse every second!
                setTimeout(updateValues, 1000);
                return;
            } */ else if (state == 'IDLE') {
                idleSources.push(sourceName);
            }

            //update player time stamp
            var testSiteTime = getPlayerVideoTime(sourceName);
            setText('testSiteTime' + sourceName, testSiteTime.toString() + ' ' + segments[0].timeZone);
        }
        var sliderTime = null;
        //if some players are currently playing, grab the earliest time and update the master slider to that time.
        if (currentVideoTimes.length != 0) {
            sliderTime = getEarliestTime(currentVideoTimes);
              
            //if some videos are idle, wake them up.
            for (var id in idleSources) {
                //are they still idle at this point? 
                var idleSource = idleSources[id];
                if (jwplayer('myPlayer'+ idleSource).getState() == 'IDLE') {
                    seekToOffset(sliderTime,idleSource);
                }
            }
        } else { //all players are paused (in btw segments)
            var prevTime = new Date(masterSlider.slider('value') * 1000);
            sliderTime = jumpToNearestSegment(prevTime); 
           
            //make all videos seek to SliderTime
            for (var key in displaySegments) {
                var segments2 = displaySegments[key];
                var sourceName3 = segments2[0].source.shortName;
                seekToOffset(sliderTime, sourceName3);
            }
        }

        //update the master slider value and time.
        masterSlider.slider('value', Math.round(sliderTime.getTime() / 1000));
        $('#sliderTimeLabel').val(sliderTime.toTimeString());
    } else { //playFlag == false
        //all videos should be paused
        for (var key in displaySegments) {
            var segments = displaySegments[key];
            var sourceName = segmetns[0].source.shortName;
            var state = jwplayer('myPlayer'+sourceName).getState();
            if (state != 'PAUSED') {
                jwplayer('myPlayer'+sourceName).pause(true);
            }
        }
    }

    //recurse every second!
    setTimeout(updateValues, 1000);
}
