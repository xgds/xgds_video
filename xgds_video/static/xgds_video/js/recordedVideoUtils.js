jQuery(function($) {
    var windowWidth = $(window).width();
    $(window).resize(function()  {
        if (windowWidth != $(window).width()) {
            location.reload();
            return;
        }
    });
});

/***
 * Helper that converts javascript datetime to UNIX POSIX time.
 * http://unixtime.info/javascript.html
 */
function toUnixPosixTime(jsTime) {
    return jsTime.getTime() / 1000;
}


/**
 * Helper for converting json datetime object to javascript date time
 */
function toJsDateTime(jsonDateTime) {
    if ((jsonDateTime) && (jsonDateTime != 'None') && (jsonDateTime != '') && (jsonDateTime != undefined)) {
        //need to subtract one from month since Javascript datetime indexes month
        //as 0 to 11.
        jsonDateTime.month = jsonDateTime.month - 1;
        return new Date(jsonDateTime.year, jsonDateTime.month, jsonDateTime.day,
                jsonDateTime.hour, jsonDateTime.min, jsonDateTime.seconds, 0);
    } else {
        return null;
    }
}


/**
 * Used by both seekCallBack and seekFromUrlOffset
 * to seek all players to given time.
 */
function seekHelper(seekTimeStr) {
    var seekTime = seekTimeParser(seekTimeStr);
    var seekDateTime = null;
    //XXX for now assume seek time's date is same as first segment's end date
    seekDateTime = new Date(xgds_video.firstSegment.endTime);
    seekDateTime.setHours(parseInt(seekTime[0]));
    seekDateTime.setMinutes(parseInt(seekTime[1]));
    seekDateTime.setSeconds(parseInt(seekTime[2]));
    seekAllPlayersToTime(seekDateTime);
}


/**
 * convert episode start/end time to javascript dateTime
 */
function convertJSONtoJavascriptDateTime(episode) {
    if (isEmpty(episode)) {
        return;
    }
    if (episode.startTime) {
        episode.startTime = toJsDateTime(episode.startTime);
    }
    if (episode.endTime) {
        episode.endTime = toJsDateTime(episode.endTime);
    }
}


/**
 * Checks if json dict is empty
 */
function isEmpty(ob) {
    for (var i in ob) {
        return false;
    }
    return true;
}


function setText(id, messageText) {
    document.getElementById(id).innerHTML = messageText;
}


/**
 * Helper to parse seektime into hours, minutes, seconds
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
//'flightName' 'sourceShortName' 'segmentIndex'

function getFilePaths(flightName, sourceShortName, segments) {
    var filePaths = [];
    $.each(segments, function(id) {
        var segment = segments[id];
        var indexFileUrl = xgds_video.indexFileUrl.replace('flightName', flightName);
        indexFileUrl = indexFileUrl.replace('sourceShortName', sourceShortName);
        indexFileUrl = indexFileUrl.replace('segmentIndex', padNum(segment.segNumber, 3));
        filePaths.push(indexFileUrl);
    });
    return filePaths;
}


function getSliderTime() {
    return new Date(xgds_video.masterSlider.slider('value') * 1000);
}


function setSliderTimeLabel(datetime) {
    var time = datetime.toTimeString().replace('GMT-0700', '');
    $('#sliderTimeLabel').text(time);
}


function setSliderTime(datetime) {
    //update the slider
    var seconds = Math.round(datetime.getTime() / 1000);
    xgds_video.masterSlider.slider('value', seconds);
    setSliderTimeLabel(datetime);
}


/**
 * Set test site time of the player
 */
function setPlayerTimeLabel(datetime, sourceName) {
    setText('testSiteTime' + sourceName, datetime.toString());
}


function withinRange(position, offset) {
    return ((position < offset + 20) && (position > offset - 20));
}


/**
 * Find the playlist item index and offset the current time
 * falls under for this player.
 */
function getPlaylistIdxAndOffset(currTime, sourceName) {
    var playlistIdx = null;
    var offset = null;
    var segments = xgds_video.displaySegments[sourceName];
    for (var i = 0; i < segments.length; i++) {
        if ((currTime >= segments[i].startTime) &&
                (currTime <= segments[i].endTime)) {
            playlistIdx = i;
            //in seconds
            offset = Math.round((currTime - segments[i].startTime) / 1000);
            break;
        }
    }
    if ((playlistIdx != null) && (offset != null)) {
        return {index: playlistIdx, offset: offset};
    } else {
        return false;
    }
}


/**
 * Ensures that seeking to a playlist item and offset works on both
 * html 5 and flash.
 * Example: setPlaylistAndSeek('ROV', 1, 120)
 */
function setPlaylistAndSeek(playerName, index, offset) {
    var p = jwplayer(playerName);
    var myplaylist = p.getPlaylist();
    // Calling immediately seems to work better for HTML5,
    // Queuing in list for handling in onPlay(), below, works better for Flash. Yuck!
    if (p.getRenderingMode() == 'html5') {
        p.playlistItem(index).seek(offset);
    console.log("SET SEEK playlist index " + p.getPlaylistIndex());
    }
    else {
        var actionObj = new Object();
        actionObj.action = p.seek;
    	actionObj.arg = offset;
        pendingPlayerActions[playerName] = [actionObj];
/*
        if (xgds_video.playFlag) {
if ((p.getState() == 'PLAYING') ||
                (p.getState() == 'IDLE')) {
	    console.log("pausing from setplaylist and seek");
	    p.pause(true);
}
        }
*/
        p.playlistItem(index);
    console.log("SET SEEK " + playerName + " playlist index " + p.getPlaylistIndex());
    }
}


/**
 * Given current time in javascript datetime,
 * find the playlist item and the offset (seconds) and seek to there.
 */
function jumpToPosition(currTime, sourceName) {
    var seekValues = getPlaylistIdxAndOffset(currTime, sourceName);
    var player = jwplayer(sourceName);
    //currTime falls in one of the segments.
    if (seekValues != false) {
        setPlaylistAndSeek(sourceName, seekValues.index, seekValues.offset);
        if (xgds_video.playFlag) {
            player.play(true);
    console.log("jump to position " + sourceName + " playlist index " + player.getPlaylistIndex());
        } else {
            player.pause(true);
        }
    } else { //current time is not in the playable range.
        //pause the player
        if ((player.getState() == 'PLAYING') ||
                (player.getState() == 'IDLE')) {
            player.pause(true);
        }
    }
}


function getNextAvailableSegment(currentTime) {
    var nearestSeg = null;
    var minDelta = Number.MAX_VALUE;
    for (var key in xgds_video.displaySegments) {
        var segments = xgds_video.displaySegments[key];
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
        return {'time': currentTime, 'source': ''};
    } else {
        return {'time': nearestSeg.startTime, 'source': nearestSeg.source.shortName}; // need to seek to this time.
    }
}


/**
 * When the segment is complete, go to the next available segment.
 */
function onSegmentComplete(thisObj) {
    //awaken idle players.
    var time = getSliderTime();
    awakenIdlePlayers(time, thisObj.id);
    onTimeController(thisObj);
    // if all other players are paused, go the the next available segment and play.
    if (allPaused()) {
        var time = getPlayerVideoTime(thisObj.id);
        var seekTime = getNextAvailableSegment(time);
        console.log('seekTime: ', seekTime.toString());
        seekAllPlayersToTime(seekTime['time']);
    }
}


/**
 * Returns true if all players are paused or idle.
 */
function allPaused() {
    var allPaused = true;
    for (var key in xgds_video.displaySegments) {
        var segments = xgds_video.displaySegments[key];
        var sourceName = segments[0].source.shortName;
        var state = jwplayer(sourceName).getState();
        if ((state != 'PAUSED') && (state != 'IDLE')) {
            allPaused = false;
            break;
        }
    }
    return allPaused;
}


/**
 * Helper for returning current test site time from the jwplayer.
 */
function getPlayerVideoTime(source) {
    var segments = xgds_video.displaySegments[source];
    var player = jwplayer(source);
    var index = player.getPlaylistIndex();
    var offset = player.getPosition();

    var miliSeconds = segments[index].startTime.getTime() + (offset * 1000);
    var currentTime = new Date(miliSeconds);
    return currentTime;
}


function seekAllPlayersToTime(datetime) {
    for (var key in xgds_video.displaySegments) {
        var segments = xgds_video.displaySegments[key];
        var sourceName = segments[0].source.shortName;

        var player = jwplayer(sourceName);
        if (player != undefined) {
            jumpToPosition(datetime, sourceName);
        }
    }
    if (datetime != null) {
        setSliderTime(datetime);
    }
}


function awakenIdlePlayers(datetime, exceptThisPlayer) {
    if (_.isUndefined(datetime)) {
        return;
    }
    for (var sourceName in xgds_video.displaySegments) {
        if (sourceName != exceptThisPlayer) {
	    var state = jwplayer(sourceName).getState();
            if ((state == 'IDLE') || (state == 'PAUSED')) {
                var segments = xgds_video.displaySegments[sourceName];
                for (var s in segments) {
                    var segment = segments[s];
                    if ((datetime >= segment.startTime) && (datetime <= segment.endTime)) {
			jumpToPosition(dateTime, sourceName);
                    }
                }
            }
        }
    }
}
