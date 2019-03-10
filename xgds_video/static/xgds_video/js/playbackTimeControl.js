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


// This is a bridge between the normal playback time control and the xgds_video time control

self.importScripts('/static/moment/moment.js');
//self.importScripts('/static/jquery/dist/jquery.min.js');

self.paused = false;
self.timeoutDelay = 100; // how many milliseconds until we re-post the time, default 10 hz
self.playbackSpeed = 1.0; // float multiplier of how fast we are changing the time.
self.currentTime = moment(moment.now()); // what is this time control's notion of 'current time'

setPaused = function(initPaused){
	paused = initPaused;
}

setPlaybackSpeed = function (initPlaybackSpeed){
	playbackSpeed = initPlaybackSpeed;
}

setCurrentTime = function (initCurrentTime){
	currentTime = moment(initCurrentTime)//.tz(xgds_video.options.timeZone);
}

setTimeoutDelay = function(initTimeoutDelay){
	timeoutDelay = initTimeoutDelay;
}

runTime = function() {
	var timeoutDelaySeconds = timeoutDelay/1000;
    var addSeconds = playbackSpeed * timeoutDelaySeconds;

    postMessage(self.currentTime.toISOString());
    if (!paused){
    	setTimeout("self.runTime()", timeoutDelay);
    }
}

onmessage = function(e) {
	if (e.data.length > 1){
		var arg = e.data[1];
		self[e.data[0]](arg);
	} else {
		self[e.data[0]]();
	}
}

