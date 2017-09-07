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
			sse.subscribe('videoEpisode', trackSse.handleEpisodeEvent, channel);
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
		sse.subscribe('videoSegment', trackSse.handleSegmentEvent, channel);
	},
	handleSegmentEvent: function(event){
		var data = JSON.parse(event.data);
		var status = event.status;
		var channel = sse.parseEventChannel(event);
		if (status == 'start'){
			//TODO handle start, end and play events
		}
	},
	handleEpisodeEvent: function(event){
		var data = JSON.parse(event.data);
		var status = event.status;
		//TODO reload the page on start or end .. though we may end an episode and then there is delay ...
	}
});