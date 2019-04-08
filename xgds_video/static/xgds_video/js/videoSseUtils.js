// __BEGIN_LICENSE__
//Copyright (c) 2015, United States Government, as represented by the 
//Administrator of the National Aeronautics and Space Administration. 
//All rights reserved.
//
//The xGDS platform is licensed under the Apache License, Version 2.0 
//(the "License"); you may not use this file except in compliance with the License. 
//You may obtain a copy of the License at 
//http://www.apache.org/licenses/LICENSE-2.0.
//
//Unless required by applicable law or agreed to in writing, software distributed 
//under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR 
//CONDITIONS OF ANY KIND, either express or implied. See the License for the 
//specific language governing permissions and limitations under the License.
// __END_LICENSE__

videoSse = {}; //namespace

$.extend(videoSse, {
	initialize: function() {
		if (isLive) {
			videoSse.allChannels(videoSse.subscribeSegment);
			sse.subscribe('videoepisode', videoSse.handleEpisodeEvent, "handleEpisodeEvent", 'sse');
		}
	},
	allChannels: function(theFunction){
		var channels = sse.getChannels();
		for (var i=0; i<channels.length; i++){
			var channel = channels[i];
			if (channel != 'sse') {
				theFunction(channel);
			}
		}
	},
	subscribeSegment: function(channel) {
		sse.subscribe('videosegment', videoSse.handleSegmentEvent, "handleSegmentEvent", channel);
	},
	handleSegmentEvent: function(event){
		var data = JSON.parse(event.data);
		var status = data.status;
		if (status == 'start'){
			xgds_video.addSegment(data.data);
		} else if (status == 'end') {
			xgds_video.endSegment(data.data);
		} else if (status == 'play') {
			xgds_video.playSegment(data.data);
		}
	},
	handleEpisodeEvent: function(event){
		var data = JSON.parse(event.data);
		var status = data.status;
		if (status == 'start') {
			xgds_video.startEpisode(data.data);
		} else if (status == 'end') {
			xgds_video.endEpisode(data.data);
			// actually stop the episode and load the recorded page.
			// TODO fire this event from back end
		}
			
	}
});