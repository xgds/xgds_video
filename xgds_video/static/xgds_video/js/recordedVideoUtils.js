//__BEGIN_LICENSE__
//Copyright (c) 2015, United States Government, as represented by the
//Administrator of the National Aeronautics and Space Administration.
//All rights reserved.

//The xGDS platform is licensed under the Apache License, Version 2.0
//(the "License"); you may not use this file except in compliance with the License.
//You may obtain a copy of the License at
//http://www.apache.org/licenses/LICENSE-2.0.

//Unless required by applicable law or agreed to in writing, software distributed
//under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
//CONDITIONS OF ANY KIND, either express or implied. See the License for the
//specific language governing permissions and limitations under the License.
//__END_LICENSE__

jQuery(function($) {
	var windowWidth = $(window).width();
	$(window).resize(function()  {
		if (windowWidth != $(window).width()) {
			return;
		}
	});
});

var xgds_video = xgds_video || {};
$.extend(xgds_video,{
	defaultTimeFormat: "MM/DD/YY HH:mm:ss z",
	seekHelper: function(seekTimeStr) {
		/**
		 * Used by both seekCallBack and seekFromUrlOffset
		 * to seek all players to given time.
		 */
		var seekTime = xgds_video.seekTimeParser(seekTimeStr);

		if (seekTime != null){
			var newTime = moment(playback.currentTime); // start with the current date

			// update the time
			newTime.hour(seekTime.hour());
			newTime.minute(seekTime.minute());
			newTime.second(seekTime.second());

			// check the time is within range
			if (xgds_video.options.episode.endTime != undefined){
				var range = new DateRange(xgds_video.options.episode.startTime,
					xgds_video.options.episode.endTime);
				if (range.contains(newTime)) {
					xgds_video.seekAllPlayersToTime(newTime);
					return;
				}
			}
			alert("Invalid jump to time.");
		}

	},

	initializeEpisodeTimes: function(episode) {
		/**
		 * convert episode start/end time to javascript dateTime
		 */
		if (_.isEmpty(episode)) {
			return;
		}
		if (episode.startTime) {
			episode.startTime = getLocalTime(episode.startTime, xgds_video.options.timeZone); //moment(episode.startTime);
		}
		if (episode.endTime) {
			episode.endTime = getLocalTime(episode.endTime, xgds_video.options.timeZone); //moment(episode.endTime);
		}
	},

	seekTimeParser: function(input) {
		/**
		 * Helper to parse seektime into hours, minutes, seconds
		 */
		var parsedMoment = moment(input,'MM/DD/YY HH:mm:ss');
		if (!parsedMoment.isValid()){
			parsedMoment = moment(input,'HH:mm:ss');
		}
		return parsedMoment;
	},

	padNum: function(num, size) {
		var s = num + '';
		while (s.length < size) {
			s = '0' + s;
		}
		return s;
	},

	getFilePaths:function(flightName, sourceShortName, segments) {
		/**
		 * Helper that returns file paths of video segments with same source
		 */
		var filePaths = [];
		$.each(segments, function(id) {
			var segment = segments[id];
			var indexFileUrl = xgds_video.options.indexFileUrl.replace('flightName', flightName);
			indexFileUrl = indexFileUrl.replace('sourceShortName', sourceShortName);
			indexFileUrl = indexFileUrl.replace('segmentIndex', xgds_video.padNum(segment.segNumber, 3));
			indexFileUrl = indexFileUrl + segment.indexFileName;
			filePaths.push(indexFileUrl);
		});
		return filePaths;
	},

	getSliderTime: function() {
		if (!_.isUndefined(xgds_video.masterSlider)) {
			var result = new moment(xgds_video.masterSlider.slider('value') * 1000);
			result.tz(xgds_video.options.timeZone);
			return result;
		} else {
			return new moment(); // TODO this is probably not right you may be on delay
		}
	},

	setSliderTimeLabel:function(datetimeMoment) {
		var timeString = getLocalTimeString(datetimeMoment, xgds_video.options.timeZone, xgds_video.defaultTimeFormat);
		$('#sliderTimeLabel').text(timeString);
	},

	setPlayerTimeLabel:function(datetime, sourceName) {
		/**
		 * Set test site time of the player
		 */
		var timeString = getLocalTimeString(moment(datetime), xgds_video.options.timeZone, xgds_video.defaultTimeFormat);
		$('#testSiteTime' + sourceName).html(timeString);
	},

	withinRange:function(position, offset) {
		return ((position < offset + 20) && (position > offset - 20));
	},

	getPlaylistIdxAndOffset:function(datetime, source) {
		/**
		 * Find the playlist item index and offset the current time
		 * falls under for this player.
		 */
		if (_.isUndefined(datetime)) {
			return false;
		}
		var playlistIdx = null;
		var offset = null;
		var nowMoment = moment(datetime);
		var segments = xgds_video.options.displaySegments[source];
		for (var i = 0; i < segments.length; i++ ) { 
			var segment = segments[i];
			if (_.isUndefined(segment.startTime)){
				break;
			}
			if (nowMoment.isBefore(segment.startTime)) {
				break;
			} else if (nowMoment.isSame(segment.startTime)){
				playlistIdx = i;
				offset = Math.round(nowMoment.diff(segment.startTime, 'seconds'));
				break;
			} else if (nowMoment.isAfter(segment.startTime)){
				if (_.isUndefined(segment.endTime)){
					playlistIdx = i;
					offset = Math.round(nowMoment.diff(segment.startTime, 'seconds'));
					break;
				} else if (nowMoment.isBefore(segment.endTime)){
					playlistIdx = i;
					offset = Math.round(nowMoment.diff(segment.startTime, 'seconds'));
					break;
				}
			}
		}

		if ((playlistIdx != null) && (offset != null)) {
			return {index: playlistIdx, offset: offset};
		}
		return false;
	},
	addPendingSeekAction: function(source, offset, player) {
		var actionObj = {action: player.seek,
						 arg: offset };
		if (xgds_video.pendingPlayerActions[source] == undefined){
			xgds_video.pendingPlayerActions[source] = [actionObj];
		} else {
			xgds_video.pendingPlayerActions[source].push(actionObj);
		} 
			
	},
	addPendingPauseAction: function(source, player) {
		var actionObj = {action: player.pause,
						 arg: true };
		if (xgds_video.pendingPlayerActions[source] == undefined){
			xgds_video.pendingPlayerActions[source] = [actionObj];
		} else {
			xgds_video.pendingPlayerActions[source].push(actionObj);
		}
	},
	setPlaylistAndSeek:function(source, index, offset) {
		/**
		 * Ensures that seeking to a playlist item and offset works on both
		 * html 5 and flash.
		 * Example: setPlaylistAndSeek('ROV', 1, 120)
		 */
		var player = jwplayer(source);
		var lastState = player.getState();
		var currentIndex = player.getPlaylistIndex();
		var currentOffset = 0;
		var playlistLoaded = false;
		if (currentIndex == index){
			playlistLoaded = true;
			var playerPosition = player.getPosition();
			currentOffset = Math.round(playerPosition);
			if (currentOffset == offset){
				return;
			}
		}
		if (!playlistLoaded){
			player.playlistItem(index);
			lastState = player.getState();
		}
		try {
			if (lastState !== 'playing'){
				xgds_video.addPendingSeekAction(source, offset, player);
				//xgds_video.addPendingPauseAction(source, player);
			} else {
				player.seek(offset);
			}
		} catch (err){
			console.log(err);
		}
	},
	jumpLocks: new Set([]),
	jumpToPosition:function(currentTime, source, seekValues) {
		/**
		 * Given current time in javascript datetime,
		 * find the playlist item and the offset (seconds) and seek to there.
		 */
		if (_.isUndefined(source)){
			for (var source in xgds_video.options.displaySegments) {
				var player = jwplayer(source);
				if (player != undefined) {
					xgds_video.jumpToPosition(currentTime, source, seekValues);
				}
			}
			return;
		}
		if (xgds_video.jumpLocks.has(source)) {
			return;
		}
		xgds_video.jumpLocks.add(source);
		if (_.isUndefined(seekValues)) {
			seekValues = xgds_video.getPlaylistIdxAndOffset(currentTime, source);
		}
		var player = jwplayer(source);
		//currentTime falls in one of the segments.
		if (!_.isUndefined(seekValues) && seekValues != false) {
			xgds_video.setPlaylistAndSeek(source, seekValues.index, seekValues.offset);
			console.log('telling player to play');
			player.play(true);
			if (!xgds_video.options.playFlag) {
				console.log('telling player to pause');
				player.pause(true);
			}
		} else { //current time is not in the playable range.
			//pause the player
			if ((player.getState() == 'playing') || (player.getState() == 'idle')) {
				player.pause(true);
			}
		}
		xgds_video.jumpLocks.delete(source);
	},

	getNextAvailableSegment:function(currentTime) {
		var nearestSeg = null;
		var minDelta = Number.MAX_VALUE;
		for (var source in xgds_video.options.displaySegments) {
			// see if the source spans the time
			if (currentTime.isSameOrAfter(xgds_video.options.displaySegments[source].startTime) && currentTime.isSameOrBefore(xgds_video.options.displaySegments[source].endTime)) {
				var segments = xgds_video.options.displaySegments[source];
				for (var id=0; id<segments.length; id++) {
					// see if this segment starts before the time.
						
					var segment = segments[id];
					if (currentTime.isSameOrAfter(segment.startTime) && currentTime.isSameOrBefore(segment.endTime)) {
						var delta = currentTime.diff(segment.startTime);

						if ((delta < minDelta) && (delta >= 0)) {
							minDelta = delta;
							nearestSeg = segment;
						}
					}
				}
			}
		}
		if (nearestSeg == null) {
			return {'time': currentTime, 'source': ''};
		} else {
			return {'time': nearestSeg.startTime, 'source': nearestSeg.source.shortName}; // need to seek to this time.
		}
	},

	onSegmentComplete:function(player) {
		/**
		 * When the segment is complete, go to the next available segment.
		 */
		//awaken idle players.
		var time = xgds_video.getSliderTime();
		xgds_video.awakenIdlePlayers(time, player.id);
		xgds_video.onTimeController(player);
		// if all other players are paused, go the the next available segment and play.
		if (xgds_video.allPaused()) {
			var time = xgds_video.getPlayerVideoTime(player.id);
			var seekTime = xgds_video.getNextAvailableSegment(time);
			xgds_video.seekAllPlayersToTime(seekTime['time']);
		}
	},

	allPaused: function() {
		/**
		 * Returns true if all players are paused or idle.
		 */
		for (var source in xgds_video.options.displaySegments) {
			var state = jwplayer(source).getState();
			if ((state != 'paused') && (state != 'idle')) {
				return false;
			}
		}
		return true;
	},


	showStillViewer: function(groupName, source, timestring) {
		/**
		 * Show still viewer when user clicks the "Still" button
		 */
		// if source name is already appended to groupName, don't add it again
		if (groupName.substr(groupName.length-3, 3) == source) {
			window.open(videoStillViewerUrl + "/" + groupName + "/" + timestring, "_blank");
		} else {
			window.open(videoStillViewerUrl + "/" + groupName + "_" + source + "/" + 
					timestring, "_blank");
		}   
	},

	getUrlFormatPlayerTime: function(source) {
		/**
		 * Returns Date/Time formatted for use in still frame URL
		 */
		var timestamp = getPlayerVideoTime(source);
		var urlFormatTimestamp = timestamp.getUTCFullYear() + "-" + xgds_video.padNum(timestamp.getUTCMonth()+1,2) + "-" +
		padNum(timestamp.getUTCDate(), 2) + "_" + xgds_video.padNum(timestamp.getUTCHours(),2) + '-' + 
		padNum(timestamp.getUTCMinutes(), 2) + '-' + xgds_video.padNum(timestamp.getUTCSeconds(), 2);
		return urlFormatTimestamp
	},

	getPlayerVideoTime:function(source) {
		/**
		 * Helper for returning current test site time from the jwplayer.
		 */
		var segments = xgds_video.options.displaySegments[source];
		var player = jwplayer(source);
		var index = player.getPlaylistIndex();
		var offset = player.getPosition();

		var currentTime = moment(segments[index].startTime);
		currentTime.add(offset, 's');
		return currentTime;
	},


	seekAllPlayersToTime: function(datetime) {
		if (!_.isNull(datetime)) {
			xgds_video.jumpToPosition(datetime);
			xgds_video.setSliderTime(datetime);
		} else {
			console.log('Seek all players to time: DATETIME IS NULL?');
		}
	},

	awakenIdlePlayers: function(datetime, exceptThisPlayer) {
		if (_.isUndefined(datetime)) {
			return;
		}
		for (var source in xgds_video.options.displaySegments) {
			if (source != exceptThisPlayer) {
				var state = jwplayer(source).getState();
				if ((state == 'idle') || (state == 'paused')) {
					xgds_video.jumpToPosition(datetime, source, undefined);
				}
			}
		}
	}

});