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
		moment.tz.setDefault(options.timeZone);
		xgds_video.initializeSegmentTimes();
		xgds_video.initializeEpisodeTimes(xgds_video.options.episode);
		return this;
	},
	initializeSegmentTimes: function() {
		for (var source in xgds_video.options.displaySegments) {
			var segments = xgds_video.options.displaySegments[source];
	        if ((segments != undefined) && (segments.length > 0)) {
	            $.each(segments, function(id) {
	                var segment = segments[id];
	                segment.startTime = getLocalTime(segment.startTime, xgds_video.options.timeZone); //moment(segment.startTime);
	                segment.endTime = getLocalTime(segment.endTime, xgds_video.options.timeZone); //moment(segment.endTime);
	
	                if(xgds_video.options.firstSegment == null) {
	                    xgds_video.options.firstSegment = segment;
	                }
	                if (xgds_video.options.lastSegment == null) {
	                    xgds_video.options.lastSegment = segment;
	                }
	
	                if (segment.startTime) {
	                    if(segment.startTime.isBefore(xgds_video.options.firstSegment.startTime)) {
	                        xgds_video.options.firstSegment = segment;
	                    }
	                }
	                if (segment.endTime) {
	                    if (segment.endTime.isAfter(xgds_video.options.lastSegment.endTime)) {
	                        xgds_video.options.lastSegment = segment;
	                    }
	                }
	            });
	        }
		}
	},
	commonOptions: {
		preload: 'auto',
		primary: 'flash',
		controls: false,
		analytics: {
			enabled: false,
			cookies: false
		},
		image: '/static/xgds_video/images/video-image.png',
		events: {
			onReady: function() {
				// console.log('ON READY ' + this.id);
				xgds_video.setupPlaylist(this.id);
				//xgds_video.startPlayer(this);
				//TODO it looks like this was already set up by the time we got here.
				if (!_.isEmpty(xgds_video.options.noteTimeStamp)) {
					var theMoment = new moment(xgds_video.options.noteTimeStamp);
					theMoment.tz(xgds_video.options.timeZone);
					xgds_video.seekAllPlayersToTime(theMoment);
				} else {
					try {
						//if there is a seektime in the url, start videos at that time.
						var splits = window.location.href.split('/')
						var theTimeString = splits[splits.length - 2];
						if (theTimeString.indexOf('%20') > 0) {
							theTimeString = theTimeString.replace('%20',' ');
							var theMoment = new moment(theTimeString);
							theMoment.tz(xgds_video.options.timeZone);
							xgds_video.seekAllPlayersToTime(theMoment);
						}
					} catch (err){
						// ulp
					}
				}
				xgds_video.startPlayer(this);
				xgds_video.audioController();
			},
//			onSeek: function(data) {
//				console.log('ON SEEK: ' + data.startPosition + " | " + data.offset);
//				console.log('POSITION IS NOW ' + this.getPosition());
//			},
//			onSeeked: function(data) {
//				console.log('ON SEEKED: ' + data.startPosition + " | " + data.offset);
//				console.log('POSITION IS NOW ' + this.getPosition());
//			},
			onComplete: function() {
				console.log('onComplete ' + this.id + ' ' + this.getState());
				//stop until start of the next segment.
				// we are already idle no need to pause
				//this.pause(true);
				//TODO I am pretty sure we don't need to do this because it is called by onTime
				xgds_video.onSegmentComplete(this);
			},
//			onFirstFrame: function(e){
//				console.log(e);
//			},
			onPlay: function(e) { //gets called per source
				//console.log('ON PLAY');
				// var segments = xgds_video.options.displaySegments[this.id];
				// var segment = segments[this.getPlaylistIndex()];
				var pendingActions = xgds_video.pendingPlayerActions[this.id];
				if (!(_.isUndefined(pendingActions)) && !(_.isEmpty(pendingActions))) {
					xgds_video.pendingPlayerActions[this.id] = [];
					for (var i = 0; i < pendingActions.length; i++) {
						pendingActions[i].action(pendingActions[i].arg);
					}
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
//			onBufferChange: function(e) {
//				console.log('BUFFER CHANGE')
//				console.log('POSITION: ' + this.getPosition());
//				console.log(' NEW DURATION: ' + e.duration);
//			},

			onIdle: function(e) {
				if (e.position > Math.floor(e.duration)) {
					//this.pause(true);
					xgds_video.onSegmentComplete(this);
				}
				//xgds_video.onTimeController(this);
			},
			onTime: function(object) {
				//console.log('ON TIME POSITION IS: ' + this.getPosition());
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

				// update test site time (all sources that are 'playing')
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
				//if at the end of the segment, pause.  do we even need to do this? won't it stop by itself at the end?
//				if (object.position > Math.floor(object.duration)) {
//					this.pause(true);
//					xgds_video.onSegmentComplete(this);
//				}
			}
		}
	},

	buildOptions: function(initial, theFile, autoStart, width){
		if (autoStart == false){
			autoStart = 'false';
		}
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
			if (player.getState() != 'playing') {
				switchPlayer = true;
			}
		} else if (jwplayer(xgds_video.options.onTimePlayer).getState() != 'playing') {
			switchPlayer = true;
		}
		if (xgds_video.options.hasMasterSlider && switchPlayer) {
			xgds_video.updateSliderFromPlayer();
		}
	},
	updateSliderFromPlayer: function() {
		var foundPlayingPlayer = false;
		for (var source in xgds_video.options.displaySegments) {
			if (jwplayer(source).getState() == 'playing') {
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
					//none of the players are in 'playing' state.
					xgds_video.options.onTimePlayer = sourceName;
				} //else leave the onTimePlayer as it is.
			}
		}
	},
	startPlayers: function() {
		/**
		 * Only called once onReady. Kickstarts the player with earliest starttime.
		 */
		// this happens after the player is ready anyhow.
//		if (!_.isEmpty(xgds_video.options.noteTimeStamp)) { 
//			var datetime = moment(xgds_video.options.noteTimeStamp); // noteTimeStamp is in UTC
//			datetime = getLocalTime(datetime, xgds_video.options.timeZone); // convert it to local time zone
//			//check if datetime is valid
//			if (datetime.isValid() && 
//				datetime.isSameOrAfter(xgds_video.options.firstSegment.startTime) &&
//				datetime.isBefore(xgds_video.options.lastSegment.endTime)) {
//				xgds_video.options.initialState = true; //to prevent onTime from being run right away before player had a chance to seek to init location
//				xgds_video.seekAllPlayersToTime(datetime);
//				return;
//			}
//		}
//		else {
			//  force an initial seek to buffer data
			xgds_video.options.initialState = true; //to prevent onTime from being run right away before player had a chance to seek to init location
			for (var source in xgds_video.options.displaySegments) {
                if (xgds_video.options.hasMasterSlider){
					jwplayer(source).playlistItem(0).seek(0);
				} else {
                	if (xgds_video.options.displaySegments[source][xgds_video.options.displaySegments[source].length - 1].endTime.isValid()){
						// IF we are in the error state of an 'active' flight with an ended last segment, DO NOT PLAY.
						jwplayer(source).pause();
					}  else {
						jwplayer(source).playlistItem(xgds_video.options.displaySegments[source].length - 1);
					}

				}	
			}
		//}

		//find the first segment and play it.
		if (xgds_video.options.hasMasterSlider){
			var startTime = xgds_video.options.firstSegment.startTime;
			for (var source in xgds_video.options.displaySegments) {
				var segments = xgds_video.options.displaySegments[source];
				if (startTime.isSameOrAfter(segments[0].startTime)) {
					jwplayer(source).pause(true);
				}
			}
		}
	},

	startPlayer:function(player) {
		var index = 0;
		if (xgds_video.options.noteTimeStamp != null && !_.isEmpty(xgds_video.options.noteTimeStamp)) { // noteTimeStamp is in local time (i.e. PDT)
			var datetime = xgds_video.options.noteTimeStamp;
			//check if datetime is valid
			if (datetime != 'Invalid Date') {
				noteDateTime = moment(datetime);
				if (noteDateTime.isSameOrAfter(xgds_video.options.firstSegment.startTime) &&
					(noteDateTime.isBefore(xgds_video.options.lastSegment.endTime))) {
					xgds_video.options.initialState = true; //to prevent onTime from being run right away before player had a chance to seek to init location
					xgds_video.seekAllPlayersToTime(noteDateTime);
					return;
				}
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

//	seekFromUrlOffset: function() {
//		/**
//		 * Only called once onReady. Reads offset from URL hash
//		 * (i.e. http://mvp.xgds.snrf/xgds_video/archivedImageStream/2014-06-19#19:00:00)
//		 * and seeks to that time.
//		 */
//
//		var timestr = window.location.hash.substr(1); //i.e. 19:00:00
//		xgds_video.seekHelper(timestr);
//	},

	audioController: function() {
		for (var source in xgds_video.options.displaySegments) {
			//TODO potentially onMeta can give us some info
			if (xgds_video.nameMatch(source, DEFAULT_AUDIO_SOURCE)) {
				//if no other player sounds are on, unmute this player
				jwplayer(source).setMute(false);
				jwplayer(source).setVolume(100); //todo use cookie
			} else {
				jwplayer(source).setMute(true);
			}
		}
	},

	nameMatch: function(name, compareTo) {
		var lower_name = name.toLowerCase();
		var lower_compare = compareTo.toLowerCase();
		return (lower_name.indexOf(lower_compare) >= 0 || lower_compare.indexOf(lower_name) >= 0)
	},

	setupAudioSlider : function() {
		$('.audioSlider').slider({
			step : 5,
			min : 0,
			max : 100,
			stop : xgds_video.handleAudioSliderChange,
			slide : xgds_video.handleAudioSliderChange,
			range : false,
			value: 0
		});

		var sliders = $('.audioSlider');
		_.forEach(sliders, function(slider) {
			var source_id = slider.id.substring(6, slider.id.length);
			var cookie_key = 'volume_' + source_id;
			var cookied_level = Cookies.get(cookie_key);
			if (_.isUndefined(cookied_level)) {
				if (xgds_video.nameMatch(source_id, DEFAULT_AUDIO_SOURCE)) {
					cookied_level = 100;
				} else {
					cookied_level = 0;
				}
				Cookies.set(cookie_key, cookied_level);
			}
			$(slider).slider('value', cookied_level);
		});
	},

	handleAudioSliderChange: function(event) {
		var new_value = $(event.target).slider('value');
		var source_id = event.target.id.substring(6, event.target.id.length);
		var cookie_key = 'volume_' + source_id;
		Cookies.set(cookie_key, new_value);
		if (new_value == 0){
			jwplayer(source_id).setMute(true);
		} else {
			jwplayer(source_id).setMute(false);
			jwplayer(source_id).setVolume(new_value);
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
			jwplayer(source).setup(thePlayerOptions);

		}
		xgds_video.setupAudioSlider();
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

	speedCallBack: function() {
		/**
		 * Updates the playback speed
		 */
		var speedStr = $('#playbackSpeed').val();
		if (_.isNull(speedStr) ||
				(Object.keys(xgds_video.options.displaySegments).length < 1)) {
			return;
		}

		var speed = parseFloat(speedStr);
		if (speed > 0) {
			for (var source in xgds_video.options.displaySegments) {
				var player = jwplayer(source);
				if (player != undefined) {
					player.setPlaybackRate(speed);
				}
			}
		}
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
		$('#playbuttonLink').addClass("active");
		$('#pausebutton').removeClass("active");
		$('#pausebuttonLink').removeClass("active");
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
					if ((segment.startTime.isSameOrBefore(currTime)) && (segment.endTime.isSameOrAfter(currTime))) {
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
		$('#playbutton').removeClass("active");
		$('#playbuttonLink').removeClass("active");
		$('#pausebutton').addClass("active");
		$('#pausebuttonLink').addClass("active");

		for (var source in xgds_video.options.displaySegments) {
			jwplayer(source).pause(true);
		}
	},

	handleFrameGrab: function(episode, source) {
		var grab_time = xgds_video.getPlayerVideoTime(source);

		$.ajax({
            type: "POST",
            url: '/xgds_video/grabImage/' + episode + '/' + source,
            datatype: 'json',
			data: {'grab_time': grab_time.format()},
            success: function (data) {
            	var image_json = data.json;
            	var url = '/xgds_map_server/view/' + image_model_name + '/' + image_json.pk;
            	window.open(url, target=image_json.name)
            },
            error: function (a) {
                console.log(a);
                alert('Error with frame grab.');
            }
        });
		// var player = jwplayer(source);

		// pause the player if it is playing
		// var player_state = player.getState();
		// if (player_state != 'paused'){
		// 	player.pause();
		// }



		// if (player_state != 'paused'){
		// 	player.play();
		// }


	}

});
