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
//var locomotePlayers = {};
//
//// Mouse handling callbacks for refresh button to restart player if it gets stuck
//$(".icon-arrows-ccw").mousedown(function(event) {
//    event.target.style.color = "#FF0000";
//})
//
//$(".icon-arrows-ccw").mouseup(function(event) {
//    event.target.style.color = "";
//})
//
//$(".icon-arrows-ccw").click(function() {
//    playerId = event.target.id.split("_")[0];
//    player = locomotePlayers[playerId];
//    streamUrl = player.streamStatus().streamURL
//    player.stop();
//    player.play(streamUrl);
//})

$.extend(xgds_video,{
	liveJWPlayer_options: {
		autostart:'viewable',
		width: '95%',
		stretching: 'uniform',
        aspectratio: '16:9',
        rtmp: {
            bufferlength: 1.0
        }
	},
	buildLiveJWPlayer: function(sourceName, url, aspectratio){
		var container = $('#' + sourceName);
		var size = xgds_video.calculateSizeWithRatio(container, aspectratio);
		var options = Object.assign({}, xgds_video.liveJWPlayer_options, {'sources': [{'file': url}],
																		  'aspectratio': aspectratio});
		if (size.length == 2){
			options['width'] = size[0];
			options['height'] = size[1];
		}
		jwplayer(sourceName).setup(options);
	}

});
