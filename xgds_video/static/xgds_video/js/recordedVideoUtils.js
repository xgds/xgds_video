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

// TODO better to have the server provide
moment.tz.add([
    'America/Los_Angeles|PST PDT|80 70|0101|1Lzm0 1zb0 Op0',
    'America/New_York|EST EDT|50 40|0101|1Lz50 1zb0 Op0'
]);

jQuery(function($) {
    var windowWidth = $(window).width();
    $(window).resize(function()  {
        if (windowWidth != $(window).width()) {
            return;
        }
    });
});



/**
 * Helper for converting json datetime object to javascript date time
 */
function toJsDateTime(jsonDateTime) {
    if ((jsonDateTime) && (jsonDateTime != 'None') && (jsonDateTime != '') && (jsonDateTime != undefined)) {
        //need to subtract one from month since Javascript datetime indexes month
        //as 0 to 11.
        jsonDateTime.month = jsonDateTime.month - 1;
        return new Date(Date.UTC(jsonDateTime.year, jsonDateTime.month, jsonDateTime.day,
                jsonDateTime.hour, jsonDateTime.min, jsonDateTime.seconds, 0));
    }
    return null;
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
    if (_.isEmpty(episode)) {
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
    if (!_.isUndefined(xgds_video.masterSlider)) {
        return new Date(xgds_video.masterSlider.slider('value') * 1000);
    } else {
        return new Date(); // TODO this is probably not right you may be on delay
    }
}

function getLocalTimeString(datetime){
    var utctime = moment(datetime);
    var pdttime = utctime.tz(xgds_video.flightTZ)
    var time = pdttime.format("HH:mm:ss z")
    return time;
}
function setSliderTimeLabel(datetime) {
//    var time = datetime.toTimeString().replace('GMT-0700', '');
    $('#sliderTimeLabel').text(getLocalTimeString(datetime));
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
    $('#testSiteTime' + sourceName).html(getLocalTimeString(datetime));
}


function withinRange(position, offset) {
    return ((position < offset + 20) && (position > offset - 20));
}


/**
 * Find the playlist item index and offset the current time
 * falls under for this player.
 */
function getPlaylistIdxAndOffset(currentTime, source) {
    var playlistIdx = null;
    var offset = null;
    var segments = xgds_video.displaySegments[source];
    
    if (currentTime >= xgds_video.displaySegments[source].startTime && currentTime <= xgds_video.displaySegments[source].endTime) {
        for (var i = 0; i < segments.length; i++) {
            if ((currentTime >= segments[i].startTime) &&
                    (currentTime <= segments[i].endTime)) {
                playlistIdx = i;
                //in seconds
                offset = Math.round((currentTime - segments[i].startTime) / 1000);
                break;
            }
        }
        if ((playlistIdx != null) && (offset != null)) {
            return {index: playlistIdx, offset: offset};
        } 
    }
    return false;
}


/**
 * Ensures that seeking to a playlist item and offset works on both
 * html 5 and flash.
 * Example: setPlaylistAndSeek('ROV', 1, 120)
 */
function setPlaylistAndSeek(source, index, offset) {
    var player = jwplayer(source);
    // Calling immediately seems to work better for HTML5,
    // Queuing in list for handling in onPlay(), below, works better for Flash. Yuck!
    if (player.getRenderingMode() == 'html5') {
        player.playlistItem(index).seek(offset);
        console.log("SET SEEK playlist index " + player.getPlaylistIndex());
    }
    else {
        var actionObj = new Object();
        actionObj.action = player.seek;
    	actionObj.arg = offset;
        pendingPlayerActions[source] = [actionObj];
/*
        if (xgds_video.playFlag) {
if ((player.getState() == 'PLAYING') ||
                (player.getState() == 'IDLE')) {
	    console.log("pausing from setplaylist and seek");
	    player.pause(true);
}
        }
*/
        player.playlistItem(index);
        console.log("SET SEEK " + source + " playlist index " + player.getPlaylistIndex());
        console.log("SET SEEK " + source + " SEEK " + offset);
    }
}


/**
 * Given current time in javascript datetime,
 * find the playlist item and the offset (seconds) and seek to there.
 */
function jumpToPosition(currentTime, source) {
    var seekValues = getPlaylistIdxAndOffset(currentTime, source);
    var player = jwplayer(source);
    //currentTime falls in one of the segments.
    if (seekValues != false) {
        setPlaylistAndSeek(source, seekValues.index, seekValues.offset);
        if (xgds_video.playFlag) {
            player.play(true);
            console.log("jump to position " + source + " playlist index " + player.getPlaylistIndex());
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
    for (var source in xgds_video.displaySegments) {
        if (currentTime >= xgds_video.displaySegments[source].startTime && currentTime <= xgds_video.displaySegments[source].endTime) {
            var segments = xgds_video.displaySegments[source];
            for (var id in segments) {
                var segment = segments[id];
                var delta = segment.startTime - currentTime;
    
                if ((delta < minDelta) && (delta >= 0)) {
                    minDelta = delta;
                    nearestSeg = segment;
                }
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
function onSegmentComplete(player) {
    //awaken idle players.
    var time = getSliderTime();
    awakenIdlePlayers(time, player.id);
    onTimeController(player);
    // if all other players are paused, go the the next available segment and play.
    if (allPaused()) {
        var time = getPlayerVideoTime(player.id);
        var seekTime = getNextAvailableSegment(time);
        console.log('on segment complete next available: ', JSON.stringify(seekTime));
        seekAllPlayersToTime(seekTime['time']);
    }
}


/**
 * Returns true if all players are paused or idle.
 */
function allPaused() {
    var allPaused = true;
    for (var source in xgds_video.displaySegments) {
        var segments = xgds_video.displaySegments[key];
        var state = jwplayer(source).getState();
        if ((state != 'PAUSED') && (state != 'IDLE')) {
            allPaused = false;
            break;
        }
    }
    return allPaused;
}

/**
 * Show still viewer when user clicks the "Still" button
 */
function showStillViewer(groupName, source, timestring) {
    // if source name is already appended to groupName, don't add it again
    if (groupName.substr(groupName.length-3, 3) == source) {
        window.open(videoStillViewerUrl + "/" + groupName + "/" + timestring, "_blank");
    } else {
        window.open(videoStillViewerUrl + "/" + groupName + "_" + source + "/" + 
		    timestring, "_blank");
    }   
}

/**
 * Returns Date/Time formatted for use in still frame URL
 */
function getUrlFormatPlayerTime(source) {
    var timestamp = getPlayerVideoTime(source);
    var urlFormatTimestamp = timestamp.getUTCFullYear() + "-" + padNum(timestamp.getUTCMonth()+1,2) + "-" +
	padNum(timestamp.getUTCDate(), 2) + "_" + padNum(timestamp.getUTCHours(),2) + '-' + 
	padNum(timestamp.getUTCMinutes(), 2) + '-' + padNum(timestamp.getUTCSeconds(), 2);

    return urlFormatTimestamp
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
    for (var source in xgds_video.displaySegments) {
        var segments = xgds_video.displaySegments[source];

        var player = jwplayer(source);
        if (player != undefined) {
            jumpToPosition(datetime, source);
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
    for (var source in xgds_video.displaySegments) {
        if (source != exceptThisPlayer) {
            var state = jwplayer(source).getState();
            if ((state == 'IDLE') || (state == 'PAUSED')) {
                var segments = xgds_video.displaySegments[source];
                for (var s in segments) {
                    var segment = segments[s];
                    if ((datetime >= segment.startTime) && (datetime <= segment.endTime)) {
                        console.log("AWAKENING " + source + " TO SEGMENT " + s);
                        jumpToPosition(dateTime, source);
                    }
                }
            }
        }
    }
}
