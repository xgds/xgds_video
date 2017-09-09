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
	liveUrl: '/xgds_core/live/',
	addSegment: function(newSegment){
		// If this segment is not already in the player add it to the source options
		// and the playlist.
		var source = newSegment.source.shortName;
		if (!(source in xgds_video.options.displaySegments)) {
			// don't bother because we will reload the page when we are told to play
			return true;
		} 
		var segments = xgds_video.options.displaySegments[source];
		if (newSegment.segNumber in segments){
			return false;
		}
		xgds_video.options.displaySegments[newSegment.segNumber] = newSegment;
		xgds_video.setupPlaylist(source);
		return false
	},
	playSegment: function(segment){
		//TODO see if we might be paused.
		// make sure the segment is in the playlist, it really already should be.
		var reloadPage = xgds_video.addSegment(segment);
		if (reloadPage) {
			// reload the page
			//TODO open popup that lets user do this:
			window.location.href=xgds_video.liveUrl; // right now this redirects to the active flights page
		}
		// select it
		jwplayer(segment.source.shortName).playlistItem(segment.segNumber);
		xgds_video.options.playFlag = true;
		// play it
		player.play(true);
	},
	startEpisode: function(episode){
		var currentEpisode = xgds_video.options.episode;
		if (currentEpisode.shortName !== episode.shortName){
			//TODO open popup that lets user do this:
			window.location.href=xgds_video.liveUrl; // right now this redirects to the active flights page
		}
	},
	endEpisode: function(episode){
		var currentEpisode = xgds_video.options.episode;
		if (currentEpisode.shortName == episode.shortName){
			//TODO load the recorded page for this episode
			console.log('stop episode');
		}
	}
	
});