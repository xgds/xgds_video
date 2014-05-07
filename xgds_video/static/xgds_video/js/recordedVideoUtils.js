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


//helper for converting json datetime object to javascript date time
function toJsDateTime(jsonDateTime) {
    if ((jsonDateTime) && (jsonDateTime != "None") && (jsonDateTime != "") && (jsonDateTime != undefined)) {
        //need to subtract one from month since Javascript datetime indexes month
        //as 0 to 11.
        jsonDateTime.month = jsonDateTime.month - 1;
        return new Date(jsonDateTime.year, jsonDateTime.month, jsonDateTime.day, 
                jsonDateTime.hour, jsonDateTime.min, jsonDateTime.seconds, 0);  
    } else { 
        return null;
    }
}


//convert episode start/end time to javascript dateTime
function convertJSONtoJavascriptDateTime(episode) {
    if (episode) {
        if (episode.startTime) {
            episode.startTime = toJsDateTime(episode.startTime);
        }
        if (episode.endTime) {
            episode.endTime = toJsDateTime(episode.endTime);
        }
    }
}


//checks if json dict is empty
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

        var indexFileUrl = xgds_video.indexFileUrl.replace('flightAndSource',
                            episode.shortName + '_' + source.shortName);
        indexFileUrl = indexFileUrl.replace('segmentIndex', padNum(segment.segNumber, 3));
        filePaths.push(indexFileUrl);
    });
    return filePaths;
}


function getSliderTime() {
    return new Date(xgds_video.masterSlider.slider('value') * 1000);
}


//slider knob shows the time (at which slider knob is located) as a tool tip.
function updateToolTip(ui, sliderTime) {
    var target = ui.handle || $('.ui-slider-handle');
    var tooltip = '<div class="tooltip"><div class="tooltip-inner">' + getTimeString(sliderTime) + '</div><div class="tooltip-arrow"></div></div>';
    $(target).html(tooltip);
}


function setSliderTimeLabel(datetime) {
    var time = datetime.toTimeString().replace("GMT-0700","");
    $('#sliderTimeLabel').val(time);
}


function setSliderTime(datetime) {
    //update the slider
    var seconds = Math.round(datetime.getTime() / 1000);
    xgds_video.masterSlider.slider('value', seconds);
    setSliderTimeLabel(datetime);
}


function setPlayerTimeLabel(datetime, sourceName) {
    //set test site time of the player
    setText('testSiteTime' + sourceName, datetime.toString());
}


function withinRange(position, offset) {
    return ((position < offset + 20) && (position > offset - 20));
}


/**
 * find the playlist item index and offset the current time
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
function setPlaylistAndSeek(playerName, playlist, offset) {
    var p = jwplayer(playerName);
    var actionObj = new Object();
    actionObj.action = p.seek;
    actionObj.arg = offset;
    // Calling immediately seems to work better for HTML5,
    // Queuing in list for handling in onPlay(), below, works better for Flash. Yuck!
    if (p.getRenderingMode() == 'html5') {
        p.playlistItem(playlist).seek(offset);
    }
    else {
        pendingPlayerActions[playerName] = [actionObj];
        p.playlistItem(playlist);
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
	var target = $('.ui-slider-handle') || ui.handle;
	var tooltip = '<div class="tooltip"><div class="tooltip-inner">' + getTimeString(datetime) + '</div><div class="tooltip-arrow"></div></div>';
	$(target).html(tooltip);
}


function awakenIdlePlayers(datetime, exceptThisPlayer) {
    for (var key in xgds_video.displaySegments) {
        var segments = xgds_video.displaySegments[key];
        var sourceName = segments[0].source.shortName;
        var player = jwplayer(sourceName);
        var state = player.getState();
        if (sourceName != exceptThisPlayer) {
            if ((state == 'IDLE') || (state == 'PAUSED')) {
               var canJump = true;
                for (var s in segments) {
                    var segment = segments[s];
                    if (datetime.getTime() == segment.endTime.getTime()) {
                        canJump = false;
                        break;
                    }
                }
                if (canJump) {
                    jumpToPosition(datetime, sourceName);
                }
            }
        }
    }
}

