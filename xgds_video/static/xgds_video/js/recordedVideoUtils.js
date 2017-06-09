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
	defaultTimeFormat: "HH:mm:ss z",
//	toJsDateTime: function(jsonDateTime) {
//		/**
//		 * Helper for converting json datetime object to javascript date time
//		 */
//		if ((jsonDateTime) && (jsonDateTime != 'None') && (jsonDateTime != '') && (jsonDateTime != undefined)) {
//			//need to subtract one from month since Javascript datetime indexes month  0 to 11.
//			jsonDateTime.month = jsonDateTime.month - 1;
//			var utcDate = Date.UTC(jsonDateTime.year, 
//									 jsonDateTime.month, 
//									 jsonDateTime.day,
//									 jsonDateTime.hour, 
//									 jsonDateTime.min, 
//									 jsonDateTime.seconds, 
//									 0);
//			var result = new Date(utcDate);
//			return result;
//		}
//		return null;
//	},

	seekHelper: function(seekTimeStr) {
		/**
		 * Used by both seekCallBack and seekFromUrlOffset
		 * to seek all players to given time.
		 */
		var seekTime = xgds_video.seekTimeParser(seekTimeStr);
		var seekDateTime = null;
		//XXX for now assume seek time's date is same as first segment's end date
		seekDateTime = new Date(xgds_video.options.firstSegment.endTime);
		seekDateTime.setHours(parseInt(seekTime[0]));
		if (seekTime.length >= 2){
			seekDateTime.setMinutes(parseInt(seekTime[1]));
		} else {
			seekDateTime.setMinutes(0);
		}
		if (seekTime.length == 3){
			seekDateTime.setSeconds(parseInt(seekTime[2]));
		} else {
			seekDateTime.setSeconds(0);
		}
		xgds_video.seekAllPlayersToTime(seekDateTime);
	},

	convertJSONtoJavascriptDateTime: function(episode) {
		/**
		 * convert episode start/end time to javascript dateTime
		 */
		if (_.isEmpty(episode)) {
			return;
		}
		if (episode.startTime) {
			episode.startTime = moment(episode.startTime);
		}
		if (episode.endTime) {
			episode.endTime = moment(episode.endTime);
		}
	},

	seekTimeParser: function(str) {
		/**
		 * Helper to parse seektime into hours, minutes, seconds
		 */
		var hmsArray = str.split(':');
		return hmsArray;
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
			filePaths.push(indexFileUrl);
		});
		return filePaths;
	},

	getSliderTime: function() {
		if (!_.isUndefined(xgds_video.masterSlider)) {
			return new moment(xgds_video.masterSlider.slider('value') * 1000);
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
		var segments = xgds_video.options.displaySegments[source];

//		if (datetime >= xgds_video.options.displaySegments[source].startTime && datetime <= xgds_video.options.displaySegments[source].endTime) {
//		for (var i = 0; i < segments.length; i++) {
//		if ((datetime >= segments[i].startTime) &&
//		(datetime <= segments[i].endTime)) {
//		playlistIdx = i;
//		//in seconds
//		offset = Math.round((datetime - segments[i].startTime) / 1000);
//		break;
//		}
//		}
//		if ((playlistIdx != null) && (offset != null)) {
//		return {index: playlistIdx, offset: offset};
//		} 
//		}

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
		xgds_video.pendingPlayerActions[source] = [actionObj];
	},
	setPlaylistAndSeek:function(source, index, offset) {
		/**
		 * Ensures that seeking to a playlist item and offset works on both
		 * html 5 and flash.
		 * Example: setPlaylistAndSeek('ROV', 1, 120)
		 */
		console.log(source + ':' + index + ':' + offset + ' setPlaylistAndSeek');
		var player = jwplayer(source);
		var currentIndex = player.getPlaylistIndex();
		var currentOffset = 0;
		var playlistLoaded = false;
		if (currentIndex == index){
			playlistLoaded = true;
			currentOffset = Math.round(player.getPosition());
			if (currentOffset == offset){
				return;
			}
			console.log('current offset:' + currentOffset);
		}
		// Calling immediately seems to work better for HTML5,
		// Queuing in list for handling in onPlay(), below, works better for Flash. Yuck!
		if (player.getRenderingMode() == 'html5') {
			if (!playlistLoaded){
				player.playlistItem(index).seek(offset);
			} else {
				player.seek(offset);

			}
//			console.log("SET SEEK playlist index " + player.getPlaylistIndex());
		}
		else {
			if (!playlistLoaded){
				xgds_video.addPendingSeekAction(source, offset, player);
				console.log('238 playlistitem' + index);
				console.log(actionObj);
				player.playlistItem(index);
				console.log('new index: ' + player.getPlaylistIndex());
			} else {
				//TODO this is where we are having problems; even though the calculated offset is at a good time, the seek is not going to this offset.
				var pendingActions = xgds_video.pendingPlayerActions[source];
				if (!(_.isUndefined(pendingActions)) && !(_.isEmpty(pendingActions))) {
					for (var i = 0; i < pendingActions.length; i++) {
						if (pendingActions[i].arg == offset){
							console.log('ALREADY HAVE PENDING ACTION');
							return;
						}
					}
				}
				console.log(player.getState());
				console.log('238 seeking ' + offset);
				player.seek(offset);
				var newOffset = Math.round(player.getPosition());
				if (newOffset == currentOffset){
					console.log('********* error state, added seek action: ' + player.getState());
					xgds_video.addPendingSeekAction(source, offset, player);
				}
				console.log('new offset ' + newOffset);
				
			}
		}
	},
	jumpLocks: new Set([]),
	jumpToPosition:function(currentTime, source, seekValues) {
		/**
		 * Given current time in javascript datetime,
		 * find the playlist item and the offset (seconds) and seek to there.
		 */
		if (xgds_video.jumpLocks.has(source)) {
			console.log('*****JUMP LOCKED ' + source);
			return;
		}
		xgds_video.jumpLocks.add(source);
		if (_.isUndefined(seekValues)) {
			seekValues = xgds_video.getPlaylistIdxAndOffset(currentTime, source);
		}
		var player = jwplayer(source);
		console.log('261 ' + source + ' jump player state ' + player.getState());
		console.log(currentTime);
		//currentTime falls in one of the segments.
		if (!_.isUndefined(seekValues) && seekValues != false) {
			xgds_video.setPlaylistAndSeek(source, seekValues.index, seekValues.offset);
			if (xgds_video.options.playFlag) {
				console.log('259 play');
				player.play(true);
				console.log('267 ' + source + ' jump player state ' + player.getState());
//				console.log("jump to position " + source + " playlist index " + player.getPlaylistIndex());
			} else {
				console.log('271 pause');
				player.pause(true);
				console.log('273 ' + source + ' jump player state ' + player.getState());
			}
		} else { //current time is not in the playable range.
			//pause the player
			if ((player.getState() == 'PLAYING') || (player.getState() == 'IDLE')) {
				console.log('278 pause');
				player.pause(true);
				console.log('280 ' + source + ' jump player state ' + player.getState());
			}
		}
		xgds_video.jumpLocks.delete(source);
	},

	getNextAvailableSegment:function(currentTime) {
		var nearestSeg = null;
		var minDelta = Number.MAX_VALUE;
		for (var source in xgds_video.options.displaySegments) {
			if (currentTime.isSameOrAfter(xgds_video.options.displaySegments[source].startTime) && currentTime.isSameOrBefore(xgds_video.options.displaySegments[source].endTime)) {
				var segments = xgds_video.options.displaySegments[source];
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
	},

	onSegmentComplete:function(player) {
		/**
		 * When the segment is complete, go to the next available segment.
		 */
		console.log('on segment complete ' + player.id);
		//awaken idle players.
		var time = xgds_video.getSliderTime();
		xgds_video.awakenIdlePlayers(time, player.id);
		xgds_video.onTimeController(player);
		// if all other players are paused, go the the next available segment and play.
		if (xgds_video.allPaused()) {
			var time = xgds_video.getPlayerVideoTime(player.id);
			var seekTime = xgds_video.getNextAvailableSegment(time);
			console.log('on segment complete next available: ', JSON.stringify(seekTime));
			xgds_video.seekAllPlayersToTime(seekTime['time']);
		}
	},

	allPaused: function() {
		/**
		 * Returns true if all players are paused or idle.
		 */
		for (var source in xgds_video.options.displaySegments) {
			var state = jwplayer(source).getState();
			if ((state != 'PAUSED') && (state != 'IDLE')) {
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
		console.log('seek all players to time' + datetime);
		for (var source in xgds_video.options.displaySegments) {
			var segments = xgds_video.options.displaySegments[source];

			var player = jwplayer(source);
			if (player != undefined) {
				xgds_video.jumpToPosition(datetime, source, undefined);
			}
		}
		if (datetime != null) {
			console.log('calling set slider time' + datetime);
			xgds_video.setSliderTime(datetime);
		} else {
			console.log('DATETIME IS NULL?');
		}
	},

	awakenIdlePlayers: function(datetime, exceptThisPlayer) {
		//console.log('awaken idle players');
		if (_.isUndefined(datetime)) {
			return;
		}
		for (var source in xgds_video.options.displaySegments) {
			if (source != exceptThisPlayer) {
				var state = jwplayer(source).getState();
				if ((state == 'IDLE') || (state == 'PAUSED')) {
					console.log('about to call jump to position ' + source + ':' + state );
					xgds_video.jumpToPosition(datetime, source, undefined);
				}
			}
		}
	}

});