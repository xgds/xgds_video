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
var locomotePlayers = {};

// Mouse handling callbacks for refresh button to restart player if it gets stuck
$(".icon-arrows-ccw").mousedown(function(event) {
    event.target.style.color = "#FF0000";
})

$(".icon-arrows-ccw").mouseup(function(event) {
    event.target.style.color = "";
})

$(".icon-arrows-ccw").click(function() {
    playerId = event.target.id.split("_")[0];
    player = locomotePlayers[playerId];
    streamUrl = player.streamStatus().streamURL
    player.stop();
    player.play(streamUrl);
})

$.extend(xgds_video,{
	locomotes: [],
	locomoteConfig: {keepAlive:60, 
					 buffer:1, 
					 scaleUp:true},
	buildLocomotePlayer: function(sourceName, url){
			var locomote = new Locomote(sourceName, STATIC_URL + 'locomote/dist/Player.swf');
	        locomotePlayers[sourceName] = locomote;
		xgds_video.locomotes.push(locomote);
		locomote.on('apiReady', function() {
			locomote.config(xgds_video.locomoteConfig);
			locomote.muteSpeaker();
			locomote.play(url);
		});
		locomote.on('error', function(err) {
	          console.log(err);
	        });
	},
	disableGridstackResizing: function() {
		// This allows you to doubleclick and full screen one.
		var items = $.find(".grid-stack-item");
		for (var i=0; i<items.length; i++) {
			var item = items[i];
			$(item).resizable('destroy');
		}
	}

});
