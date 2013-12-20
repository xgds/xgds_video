
var displaySegmentsGlobal = null;
var masterSliderGlobal = '';
var isPlayButtonPressed = true;
var earliestSegmentGlobal = null;

// resize the jwplayers when window is resized.
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

function setText(id, messageText) {
    document.getElementById(id).innerHTML = messageText;
}

function secondsToHMS(totalSec) {
    var hours = parseInt(totalSec / 3600) % 24;
    var minutes = parseInt(totalSec / 60) % 60;
    var seconds = Math.floor(totalSec % 60);
    var hms = ((hours < 10 ? '0' + hours : hours) + ':' +
               (minutes < 10 ? '0' + minutes : minutes) + ':' +
               (seconds < 10 ? '0' + seconds : seconds));
    return hms;
}

function HMStoSeconds(hmsString) {
    var hmsArray = hmsString.split(':');
    var seconds = (parseFloat(hmsArray[0] * 3600) +
                   parseFloat(hmsArray[1] * 60) +
                   parseFloat(hmsArray[2]));
    return seconds;
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
    console.log('inside height');
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
    var seekTime = document.getElementById('seekTime');
    if (seekTime != null) {
        var seekTimeInSeconds = HMStoSeconds(seekTime);
    }
    console.log("seekTime", seekTime);
    $.each(displaySegmentsGlobal, function(idx) {
        var segment = displaySegmentsGlobal[idx];
        var sourceName = segment.source.shortName;
        var offset = seekTimeInSeconds - HMStoSeconds(segment.startTime);
        var player = jwplayer('myPlayer' + sourceName);
        var testSiteTime = secondsToHMS(HMStoSeconds(segment.startTime) + offset);

        //update the test site time of each video
        setText('testSiteTime' + sourceName, testSiteTime + ' ' + segment.timeZone);
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
    var endTime = latestSegEndTime;
    if (episode.endTime != null) {
        endTime = episode.endTime;
    }

    console.log("episode's start time: " + episode.startTime);

    masterSliderGlobal = $('#masterSlider').slider({
        step: 1,
        min: HMStoSeconds(episode.startTime),
        max: HMStoSeconds(endTime),
        stop: uponSliderStop,
        slide: uponSliderMove,
        range: 'min'
    });
    $('#sliderTimeLabel').val(secondsToHMS($('#masterSlider').slider('value')));
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
                document.getElementById("playbutton").className="fa fa-play fa-2x"
                player.play(true);
            } else {
                document.getElementById("playbutton").className="fa fa-pause fa-2x"
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
                    if (earliestSegTime == HMStoSeconds(segment.startTime)) {
                        // set earliest segment global
                        earliestSegmentGlobal = segment;
                        /*
                        // if there is an offset in the url itself, start there.
                        if (window.location.hash) { //in the format #t=HH:MM:SS
                            seekToTime(true);
                        }*/

                        // play the video with earliest time
                        jwplayer('myPlayer' + sourceName).play(true);
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
    $('#sliderTimeLabel').val(secondsToHMS(ui.value));
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
        var offset = curSliderTime - HMStoSeconds(segment.startTime);
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

        var testSiteTime = secondsToHMS(HMStoSeconds(segment.startTime) + offset);
        setText('testSiteTime' + sourceName,
                testSiteTime + ' ' + segment.timeZone);
    });
}

function updateValues() {
    // calculate slider time
    var elapsedSeconds = jwplayer('myPlayer' + earliestSegmentGlobal.source.shortName).getPosition();

    var sliderTime = HMStoSeconds(earliestSegmentGlobal.startTime) + elapsedSeconds;
    masterSliderGlobal.slider('value', sliderTime);

    // update slider time text
    var sliderTimeInHMS = secondsToHMS(sliderTime);
    $('#sliderTimeLabel').val(sliderTimeInHMS);

    // if slider time >= start time of other videos and they are paused, awake them
    $.each(displaySegmentsGlobal, function(idx) {
        var segment = displaySegmentsGlobal[idx];
        var sourceName = segment.source.shortName;
        var player = jwplayer('myPlayer' + sourceName);

        if ((sliderTime >= HMStoSeconds(segment.startTime)) &&
            (player.getState() == 'IDLE')) {
            player.play(true);
        }

        if (!isPlayButtonPressed) {
            player.pause(true);
        }

        //should all be synced to earliestSegment
        setText('testSiteTime' + sourceName,
                sliderTimeInHMS + ' ' + segment.timeZone);
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
