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
        var path = xgds_video.baseUrl + episode.shortName + '_' + 
            source.shortName + '/Video/Recordings/' +
            segment.directoryName + padNum(segment.segNumber, 3) + 
            '/' + segment.indexFileName;
        filePaths.push(path);
    });
    return filePaths;
}


//XXX: get the color from either the vehicle or the source. 
//     Need to add color column to the model
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
    var seconds = Math.round(datetime.getTime() / 1000);
    xgds_video.masterSlider.slider('value', seconds);
    $('#sliderTimeLabel').val(datetime.toTimeString());
}


function setPlayerTimeLabel(datetime, sourceName) {
    //set test site time of the player
    setText('testSiteTime' + sourceName, datetime.toString());
}


function checkPlaylistIdx(source) {
    return (jwplayer(source).getPlaylistIndex() == 
            xgds_video.seekOffsetList[source].index)
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
 * Given current time in javascript datetime,
 * find the playlist item and the offset (seconds) and seek to there.
 */
function jumpToPosition(currTime, sourceName) {
    var seekValues = getPlaylistIdxAndOffset(currTime, sourceName);
    var player = jwplayer(sourceName);
    //currTime falls in one of the segments.
    if (seekValues != false) {
        //update the player
        player.playlistItem(seekValues.index) 
        //chrome plays in flash mode. Seek later (otherwise doesn't work)
        xgds_video.seekOffsetList[sourceName] = seekValues;
        //seek(seekValues.offset); //XXX works in safari, not in chrome
        if (xgds_video.playFlag) {
            player.play(true);
        } else {
            player.pause(true);
        }
    } else { //current time is not in the playable range.
        //pause the player
        if (player.getState() == 'PLAYING') {
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
        return currentTime;
    } else {
        return nearestSeg.startTime; // need to seek to this time.
    }
}


/** XXX double check logic 
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

        jumpToPosition(datetime,sourceName);
    }
}

var counter = 0;

/*
function awakeIdlePlayers(datetime) {
    var idlePlayers = [];
    for (var key in xgds_video.displaySegments) {
        var segments = xgds_video.displaySegments[key];
        var sourceName = segments[0].source.shortName;
        var player = jwplayer(sourceName);
        var state = player.getState();

        if ((state == 'IDLE') || (state == 'PAUSED')) { //XXX TODO: and playflag is on!!
            //if date time falls under the player's segment, 
            /*
            if (datetime == segments[player.getPlaylistIndex()].startTime) {
                player.play(true);
                console.log("inside the conditional, told player to play");   
            } */
/*            
            var idxAndOffset = getPlaylistIdxAndOffset(datetime, sourceName);
            if (idxAndOffset != false) {
                player.play(true).playlistItem(idxAndOffset.index).seek(idxAndOffset.offset);
                idlePlayers.push(player);
            }
        }
    }

    return idlePlayers;
}
*/
