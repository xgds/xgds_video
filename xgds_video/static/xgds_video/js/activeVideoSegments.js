var displaySegmentsGlobal = null;
var masterSliderGlobal = '';
var isPlayButtonPressed = true;
var earliestSegmentGlobal = null;


// resize the jwplayers when window is resized.
/*
window.onresize = function() {
    if (displaySegmentsGlobal != null) {
        var maxWidth = getMaxWidth(displaySegmentsGlobal);
        $.each(displaySegmentsGlobal, function(segIdx) {
            var segment = displaySegmentsGlobal[segIdx];
            var height = calculateHeight(maxWidth, segment.settings.height, segment.settings.width);
            var sourceName = segment.source.shortName;
            jwplayer('myPlayer' + sourceName).resize(maxWidth, height);
        });
    }
};
*/

function setText(id, messageText) {
    document.getElementById(id).innerHTML = messageText;
}


//helper to parse seektime into hours, minutes, seconds
function seekTimeParser(str) {
    var hmsArray = str.split(':');
    return hmsArray;
}


// find max width of the jwplayer
function getMaxWidth(displaySegments) {
    var width = window.innerWidth ||
        document.documentElement.clientWidth ||
        document.body.clientWidth;

    if (displaySegments.length > 1) {
        width = Math.round(width / 2);
    }

    width = width - 100;
    return width;
}


// find max height of jwplayer
function calculateHeight(newWidth, defaultHeight, defaultWidth) {
    var newHeight = defaultHeight;
    var ratio = newWidth / defaultWidth;
    newHeight = Math.round(defaultHeight * ratio);
    return newHeight;
}


/**
 * Seek Video from time.
 * Update the slider value, slider text
 * update the jwplayer position
 *    offset = seek time - video start time.
 **/
function seekToTime() {
    var seekTimeStr = document.getElementById('seekTime').value;
    if ((seekTimeStr == null) || (displaySegmentsGlobal.length < 1)) {
        return;
    }
    
    $.each(displaySegmentsGlobal, function(idx) {
        var segment = displaySegmentsGlobal[idx];
        var sourceName = segment.source.shortName;
        
        //for now assume that seekTime has the same date as first segments' endDate.
        var seekTime = seekTimeParser(seekTimeStr);
        var seekDateTime = new Date(segment.endTime);
        seekDateTime.setHours(seekTime[0]);
        seekDateTime.setMinutes(seekTime[1]);
        seekDateTime.setSeconds(seekTime[2]);

        var offset = Math.round((seekDateTime - segment.startTime) / 1000); //in seconds
        console.log("seekto time offset: ", offset);
        var player = jwplayer('myPlayer'+sourceName);
        setText('testSiteTime'+sourceName, seekTimeStr+' '+segment.timeZone);
        if (offset >= 0) {
            var doSeek = true;
            var state = player.getState();
            if (state == 'IDLE') {
                player.setMute(true).play(true).onPlay(function() {
                    if (doSeek) {
                        doSeek = false;
                        player.pause(true).seek(offset).play(true);
                    }
                });
            } else {
                if (state != 'BUFFERING') {
                    player.seek(offset).play(true);
                }
            }
        }
    });
}


/**
 * initialize master slider with range (episode start time-> episode end time)
 **/
function setupSlider(episode, latestSegEndTime) {
    var endTime = (episode.endTime) ? episode.endTime : latestSegEndTime; 

    masterSliderGlobal = $('#masterSlider').slider({
        step: 1,
        min: Math.round(episode.startTime.getTime()/1000), //in seconds
        max: Math.round(endTime.getTime()/1000), //in seconds
        stop: uponSliderStop,
        slide: uponSliderMove,
        range: 'min'
    });
    var sliderTime = new Date($('#masterSlider').slider('value')*1000);
    $('#sliderTimeLabel').val(sliderTime.toTimeString());
}


/**
 * Callback function for play/pause button
 **/
function playPauseButtonCallBack() {
    
    isPlayButtonPressed = !isPlayButtonPressed;
    $.each(displaySegmentsGlobal, function(idx) {
        var sourceName = displaySegmentsGlobal[idx].source.shortName;
        var player = jwplayer('myPlayer' + sourceName);

        if ((player.getState() == 'PLAYING') ||
            (player.getState() == 'PAUSED')) {

            if (isPlayButtonPressed == true) {
                document.getElementById("playbutton").className="fa fa-pause fa-2x"
                player.play(true);
            } else {
                document.getElementById("playbutton").className="fa fa-play fa-2x"
                player.pause(true);
            }
        }
    });
}


function padNum(num, size) {
    var s = num + '';
    while (s.length < size) {
        s = '0' + s;
    }
    return s;
}


/**
 * Initialize jw player and call update values
 **/
function setupJWplayer(displaySegments, earliestSegTime, episode) {
    var maxWidth = getMaxWidth(displaySegments);
    displaySegmentsGlobal = displaySegments; // sets global var
    $.each(displaySegmentsGlobal, function(segIdx) {
        var segment = displaySegmentsGlobal[segIdx];
        var sourceName = segment.source.shortName;
        var filePath = baseUrl + episode.shortName + '_' + sourceName +
            '/Video/Recordings/' +
            segment.directoryName + padNum(segment.segNumber, 3) +
            '/' + segment.indexFileName;
        var height = calculateHeight(maxWidth, segment.settings.height,
                                     segment.settings.width);

        console.log('file path: ' + filePath);
        jwplayer('myPlayer' + sourceName).setup(
        {
            file: filePath,
            width: maxWidth,
            height: height,
            controls: false,
            autostart: false,
            skin: '/static/javascript/jwplayer/jw6-skin-sdk/skins/five/five.xml',
            events: {
                onReady: function() {
                    if (earliestSegTime.toDateString() == segment.startTime.toDateString()) {
                        earliestSegmentGlobal = segment;
                        
                        // play the video with earliest time
                        jwplayer('myPlayer' + sourceName).play(true);
                        console.log("about to call update values");
                        updateValues();
                    }
                }
            }
        });
    });
}


/**
 * Slider Callback:
 * update slider time text when moving slider.
 **/
function uponSliderMove(event, ui) {
    var sliderTime = new Date(ui.value*1000);
    $('#sliderTimeLabel').val(sliderTime.toTimeString());
}


/**
 * Slider Callback:
 * For each displaySegment,
 *    get the current slider position and do
 *    offset = slider position - each video's start time
 *    seek each video at offset. (means each video's offset will be different, but their test site time same)
 *    update the test site times to equal slider position.
 **/
function uponSliderStop(event, ui) {
    var curSliderTime = ui.value;

    $.each(displaySegmentsGlobal, function(segIdx) {
        var segment = displaySegmentsGlobal[segIdx];
        var sourceName = segment.source.shortName;
        var offset = curSliderTime - Math.round(segment.startTime.getTime()/1000); //in seconds
        var player = jwplayer('myPlayer' + sourceName);

        if (offset >= 0) { //slider has passed video's start time (safe to play)
            var doSeek = true;
            var state = player.getState();
            if (state == 'IDLE') {
                player.setMute(true).play(true).onPlay(function() {
                    if (doSeek) {
                        doSeek = false;
                        player.pause(true).setMute(true).seek(offset).play(true);
                    }
                });
            } else {
                if (state != 'BUFFERING') {
                    player.seek(offset).play(true);
                }
            }
        } else { // video is not ready to play yet
            player.stop();
        }
        
        var testSiteTime = new Date(segment.startTime.getTime() + (offset*1000)); //initialize dateTime with ms
        testSiteTime = testSiteTime.toTimeString();
        setText('testSiteTime'+sourceName, testSiteTime+' '+segment.timeZone);
    });
}


/* this gets called every second to update the slider as video progresses */
function updateValues() {
    var elapsedSeconds = jwplayer('myPlayer' + earliestSegmentGlobal.source.shortName).getPosition();

    //update slider
    var sliderTime = new Date(earliestSegmentGlobal.startTime.getTime() + elapsedSeconds*1000);
    masterSliderGlobal.slider('value', Math.round(sliderTime.getTime()/1000));
    $('#sliderTimeLabel').val(sliderTime.toTimeString());

    // if slider time >= start time of other videos and they are paused, awake them
    $.each(displaySegmentsGlobal, function(idx) {
        var segment = displaySegmentsGlobal[idx];
        var sourceName = segment.source.shortName;
        var player = jwplayer('myPlayer'+sourceName);

        if ((sliderTime >= segment.startTime) &&
            (player.getState() == 'IDLE')) {
            player.play(true);
        }

        if (!isPlayButtonPressed) {
            player.pause(true);
        }
        //should all be synced to earliestSegment
        setText('testSiteTime' + sourceName, sliderTime.toTimeString()+' '+ segment.timeZone);
    });
    setTimeout(updateValues, 1000);
}

/**************************************************************
For unit testing with node unit
***************************************************************/

/*
if (typeof exports !== 'undefined') {
    exports.secondsToHMS = secondsToHMS
}
*/
