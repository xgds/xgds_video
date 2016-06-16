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
	locomotes: [],
	locomoteConfig: {keepAlive:60, 
					 buffer:1, 
					 scaleUp:true},
	buildLocomotePlayer: function(sourceName, url){
		var locomote = new Locomote(sourceName, STATIC_URL + 'locomote/dist/Player.swf');
		xgds_video.locomotes.push(locomote);
		locomote.on('apiReady', function() {
			locomote.config(xgds_video.locomoteConfig);
			locomote.play(url);
		});
		locomote.on('error', function(err) {
	          console.log(err);
	        });
	},
	disableGridstackResizing: function() {
		var items = $.find(".grid-stack-item");
		for (var i=0; i<items.length; i++) {
			var item = items[i];
			$(item).resizable('destroy');
		}
	}

});