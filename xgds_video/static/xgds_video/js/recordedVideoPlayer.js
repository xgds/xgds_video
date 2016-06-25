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

var xgds_video = xgds_video || {};
$.extend(xgds_video,{
	initialize: function(options){
		xgds_video.options = options;
	},
	commonOptions: {
		controls: false,
		analytics: {
			enabled: false,
			cookies: false
		},
		events: {
			onReady: function() {
				xgds_video.setupPlaylist(this.id);
				//if there is a seektime in the url, start videos at that time.
				if (window.location.hash) {
					xgds_video.seekFromUrlOffset();
				} else {
					xgds_video.startPlayer(this);
				}
				xgds_video.soundController();
			},
			onComplete: function() {
				//stop until start of the next segment.
				this.pause(true);
				xgds_video.onSegmentComplete(this);
			},
			onPlay: function(e) { //gets called per source
				var segments = xgds_video.options.displaySegments[this.id];
				var segment = segments[this.getPlaylistIndex()];
				var pendingActions = xgds_video.pendingPlayerActions[this.id];
				if (!(_.isUndefined(pendingActions)) && !(_.isEmpty(pendingActions))) {
					for (var i = 0; i < pendingActions.length; i++) {
						pendingActions[i].action(pendingActions[i].arg);
					}
					xgds_video.pendingPlayerActions[this.id] = [];
				}
				if (xgds_video.options.initialState == true) {
					xgds_video.options.initialState = false;
				}
				if (xgds_video.options.seekFlag) {
					xgds_video.options.seekFlag = false;
					if (xgds_video.options.hasMasterSlider){ 
						xgds_video.updateSliderFromPlayer();
					}
				}
				xgds_video.onTimeController(this);
			},
			onPause: function(e) {
				//just make sure the item does get paused.
				xgds_video.onTimeController(this);
			},
			onBuffer: function(e) {
				xgds_video.onTimeController(this);
			},
			onIdle: function(e) {
				if (e.position > Math.floor(e.duration)) {
					this.pause(true);
					xgds_video.onSegmentComplete(this);
				}
				xgds_video.onTimeController(this);
			},
			onSeek: function(e) {
				//  onTimeController(this);
			},
			onTime: function(object) {
				if (!xgds_video.options.hasMasterSlider){
					return;
				}
				// need this. otherwise slider jumps around while moving.
				if (xgds_video.options.movingSlider == true) {
					return;
				}

				if (!xgds_video.options.playFlag) {
					this.pause(true);
					return;
				}

				// update test site time (all sources that are 'PLAYING')
				if (!xgds_video.options.seekFlag && !xgds_video.options.movingSlider) {
					var testSiteTime = xgds_video.getPlayerVideoTime(this.id);
					xgds_video.setPlayerTimeLabel(testSiteTime, this.id);

					if (!xgds_video.initialState) {
						//if this call is from the current 'onTimePlayer'
						if (xgds_video.options.onTimePlayer == this.id) {
							// update the slider here.
							var updateTime = xgds_video.getPlayerVideoTime(this.id);
							if (!(_.isUndefined(updateTime))) {
								xgds_video.awakenIdlePlayers(updateTime, this.id);
								xgds_video.setSliderTime(updateTime);
							}
						}
					}
				}
				//if at the end of the segment, pause.
				if (object.position > Math.floor(object.duration)) {
					this.pause(true);
					xgds_video.onSegmentComplete(this);
				}
			}
		}
	},

	buildOptions: function(initial, theFile, autoStart, width){
		initial['autostart'] = autoStart;
		initial['file'] = theFile;
		initial['width'] = width;
		initial['aspectratio'] = "16:9"; //TODO get *this* from the video
		var result =  $.extend(initial, xgds_video.commonOptions);
		return result;
	},
	pendingPlayerActions : {},
	playlistsLoaded : false,
	onTimeController: function(player) {
		/**
		 * ensures that only one onTime event is enabled
		 */

		if (!xgds_video.options.playFlag) {
			return;
		}
		if (xgds_video.options.seekFlag || xgds_video.options.movingSlider) {
			return;
		}

		var switchPlayer = false;
		if (player.id == xgds_video.options.onTimePlayer) {
			if (player.getState() != 'PLAYING') {
				switchPlayer = true;
			}
		} else if (jwplayer(xgds_video.options.onTimePlayer).getState() != 'PLAYING') {
			switchPlayer = true;
		}
		if (xgds_video.options.hasMasterSlider && switchPlayer) {
			xgds_video.updateSliderFromPlayer();
		}
	},
	updateSliderFromPlayer: function() {
		var foundPlayingPlayer = false;
		for (var source in xgds_video.options.displaySegments) {
			if (jwplayer(source).getState() == 'PLAYING') {
				xgds_video.options.onTimePlayer = source;
				foundPlayingPlayer = true;
				break;
			}
		}

		if (foundPlayingPlayer == false) {
			//set the xgds_video.onTimePlayer to the player with the nearest segment
			//to current slider time
			if (xgds_video.options.hasMasterSlider){
				var time = xgds_video.getSliderTime();
				var sourceName = xgds_video.getNextAvailableSegment(time)['source'];
				if (!(_.isUndefined(sourceName)) && !(_.isEmpty(sourceName))) { //there is only one segment for each source and
					//none of the players are in 'PLAYING' state.
					xgds_video.options.onTimePlayer = sourceName;
				} //else leave the onTimePlayer as it is.
			}
		}
	},
	startPlayers: function() {
		/**
		 * Only called once onReady. Kickstarts the player with earliest starttime.
		 */
		if (xgds_video.options.noteTimeStamp != null) { // noteTimeStamp is in local time (i.e. PDT)
			var datetime = xgds_video.options.noteTimeStamp;
			//check if datetime is valid
			if ((datetime != 'Invalid Date') && ((datetime >= xgds_video.options.firstSegment.startTime) &&
					(datetime < xgds_video.options.lastSegment.endTime))) {
				xgds_video.options.initialState = true; //to prevent onTime from being run right away before player had a chance to seek to init location
				xgds_video.seekAllPlayersToTime(datetime);
				return;
			}
		}
		else {
			//  force an initial seek to buffer data
			xgds_video.options.initialState = true; //to prevent onTime from being run right away before player had a chance to seek to init location
			for (var source in xgds_video.options.displaySegments) {
                if (xgds_video.options.hasMasterSlider){
					jwplayer(source).playlistItem(0).seek(0);
				} else {
					jwplayer(source).playlistItem(xgds_video.options.displaySegments[source].length - 1);
				}	
			}
		}

		//find the first segment and play it.
		if (xgds_video.options.hasMasterSlider){
			var startTime = xgds_video.options.firstSegment.startTime;
			for (var source in xgds_video.options.displaySegments) {
				var segments = xgds_video.options.displaySegments[source];
				if (startTime >= segments[0].startTime) {
					jwplayer(source).pause(true);
				}
			}
		}
	},

	startPlayer:function(player) {
		var index = 0;
		if (xgds_video.options.noteTimeStamp != null) { // noteTimeStamp is in local time (i.e. PDT)
			var datetime = xgds_video.options.noteTimeStamp;
			//check if datetime is valid
			if ((datetime != 'Invalid Date') && ((datetime >= xgds_video.options.firstSegment.startTime) &&
					(datetime < xgds_video.options.lastSegment.endTime))) {
				xgds_video.options.initialState = true; //to prevent onTime from being run right away before player had a chance to seek to init location
				xgds_video.seekAllPlayersToTime(datetime);
				return;
			}
		} else {
			// force an initial seek to buffer data
			xgds_video.options.initialState = true; //to prevent onTime from being run right away before player had a chance to seek to init location
			if (!xgds_video.options.hasMasterSlider){
				index = player.getPlaylist().length - 1;
				player.playlistItem(index);
			} else {
				player.playlistItem(0);
			}
		}

		//find the  segment and play it.
		if (xgds_video.options.hasMasterSlider){
			var startTime = xgds_video.options.firstSegment.startTime;
			var segments = xgds_video.options.displaySegments[player.id];
			if (startTime >= segments[0].startTime) {
				//            player.pause(true);
			} else {
				player.pause(true);
			}
		} else {
			xgds_video.options.playFlag = true;
			player.play(true);
		}
	},

	seekFromUrlOffset: function() {
		/**
		 * Only called once onReady. Reads offset from URL hash
		 * (i.e. http://mvp.xgds.snrf/xgds_video/archivedImageStream/2014-06-19#19:00:00)
		 * and seeks to that time.
		 */

		var timestr = window.location.hash.substr(1); //i.e. 19:00:00
		xgds_video.seekHelper(timestr);
	},

	soundController: function() {
		/**
		 * If the source is a diver, and no other divers are enabled, turn it on.
		 */
		var soundOn = false;
		for (var source in xgds_video.options.displaySegments) {
			//TODO fix -- encode in DB or check if there is an audio stream, potentiall onMeta can give us some info
			if (source.match('RD')) { //if the source is a research diver
				//if no other player sounds are on, unmute this player
				if (!soundOn) {
					jwplayer(source).setMute(false);
					soundOn = true;
				} else {
					//there is already a player that is not muted. Turn off this
					//player's sound.
					if (!jwplayer(source).getMute()) {
						jwplayer(source).setMute(true);
					}
				}
			}
		}
	},

	getWidthHeight: function(){
		var numSources = Object.keys(xgds_video.options.displaySegments).length;
		var maxWidth = xgds_video.getMaxWidth(numSources);
		var videoHeight = Math.round(maxWidth * (9/16));
		return [maxWidth, videoHeight]
	},

	presizeVideoDivs: function() {
		xgds_video.options.wh = xgds_video.getWidthHeight();
		for (var source in xgds_video.options.displaySegments) {
			$("#"+ source).width(xgds_video.options.wh[0]);
			$("#"+ source).height(xgds_video.options.wh[1]);
		}
	},


	setupJWplayer: function(jwplayerOptions, width) {
		/**
		 * Initialize jw player and call update values
		 */
		xgds_video.presizeVideoDivs();

		for (var source in xgds_video.options.displaySegments) {
			// list of video segments with same source & episode (if given)
			var segments = xgds_video.options.displaySegments[source];
			xgds_video.options.displaySegments[source].startTime = segments[0].startTime;
			xgds_video.options.displaySegments[source].endTime = segments[segments.length - 1].endTime;

			//if there are no segments to show, don't build a player.
			if (_.isUndefined(segments) || _.isEmpty(segments)) {
				continue;
			}

			// paths of the video segments
			var flightName = xgds_video.options.flightName;
			if (flightName == null) {
				flightName = xgds_video.options.episode + '_' + xgds_video.options.sourceVehicle[source]; //TODO: TEST THIS!
			}
			var videoPaths = xgds_video.getFilePaths(flightName, source, segments);
			var thePlayerOptions = xgds_video.buildOptions(jwplayerOptions, videoPaths[0], xgds_video.options.playFlag, width);
			var thePlayer = jwplayer(source).setup(thePlayerOptions);

		}
	},

	setupPlaylist:function(source) {
		/*
		 * Set up the playlist for the given source
		 */

		// list of video segments with same source & episode (if given)
		var segments = xgds_video.options.displaySegments[source];

		// paths of the video segments
		var flightName = xgds_video.options.flightName;
		if (flightName == null) {
			flightName = xgds_video.options.episode + '_' + xgds_video.options.sourceVehicle[source]; //TODO: TEST THIS!
		}

		var videoPaths = xgds_video.getFilePaths(flightName, source, segments);

		// load the segments as playlist.
		var myplaylist = [];
		for (var k = 0; k < videoPaths.length; k++) {
			var mysources = [];
			var newItem = {
					file: videoPaths[k],
					label: videoPaths[k]
			};
			mysources.push(newItem);
			myplaylist.push({title: source + " " + k, sources:mysources});
		};
		jwplayer(source).load(myplaylist);
	},



	seekCallBack: function() {
		/**
		 * Updates the player and the slider times based on
		 * the seek time value specified in the 'seek' text box.
		 */
		var seekTimeStr = $('#seekTime').val();
		if ((seekTimeStr == null) ||
				(Object.keys(xgds_video.options.displaySegments).length < 1)) {
			return;
		}
		xgds_video.seekHelper(seekTimeStr);
	},

	playButtonCallback: function() {
		if (xgds_video.options.playFlag){
			return;
		}
		xgds_video.options.playFlag = true;
		$('#playbutton').addClass("active");
		$('#pausebutton').removeClass("active");
		if (xgds_video.options.hasMasterSlider){
			var currTime = xgds_video.getSliderTime();
		}
		for (var source in xgds_video.options.displaySegments) {
			var segments = xgds_video.options.displaySegments[source];

			// make sure that you have stuff to play for each source
			var segments = xgds_video.options.displaySegments[source];
			if (xgds_video.options.hasMasterSlider){
				var currentIndex = jwplayer(source).getPlaylistIndex();
				if (!(_.isUndefined(currentIndex))) {
					var segment = segments[currentIndex];
					if ((segment.startTime <= currTime) && (segment.endTime >= currTime)) {
						jwplayer(source).play(true);
					}
				}
			} else {
				// no slider = active mode, so play the latest thing in the list.
				var theplaylist = jwplayer(source).getPlaylist();
				jwplayer(source).playlistItem(theplaylist.length - 1);
			}
		}
		if (xgds_video.options.hasMasterSlider){
			xgds_video.setSliderTime(currTime);
		}
	},

	pauseButtonCallback: function() {
		if (!xgds_video.options.playFlag){
			return;
		}
		xgds_video.options.playFlag = false;
		$('#pausebutton').addClass("active");
		$('#playbutton').removeClass("active");
		for (var source in xgds_video.options.displaySegments) {
			jwplayer(source).pause(true);
		}
	}

});
