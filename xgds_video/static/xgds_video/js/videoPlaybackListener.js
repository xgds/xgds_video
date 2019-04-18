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
    playbackListener: {
		lastUpdate: undefined,
		initialize: function() {
			//noop
		},
		doSetTime: function(currentTime){
		},
		start: function(currentTime){
			xgds_video.jumpToPosition(currentTime);
		    xgds_video.playButtonCallback(currentTime);
		},
		update: function(currentTime){
		},
		pause: function() {
			xgds_video.pauseButtonCallback();
		}
	},
	sliderStopListener: function(currentTime) {
    	xgds_video.jumpToPosition(currentTime);
	}
});