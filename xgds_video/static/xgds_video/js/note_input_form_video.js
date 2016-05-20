//__BEGIN_LICENSE__
// Copyright (c) 2015, United States Government, as represented by the
// Administrator of the National Aeronautics and Space Administration.
// All rights reserved.
//
// The xGDS platform is licensed under the Apache License, Version 2.0
// (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
// http://www.apache.org/licenses/LICENSE-2.0.
//
// Unless required by applicable law or agreed to in writing, software distributed
// under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
// CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.
//__END_LICENSE__

var xgds_notes = xgds_notes || {};
$.extend(xgds_notes,{
	getEventTime: function(context) {
		var parent = $(context).closest('form');
		
		// not live, pull the time out of the video
		var dataString = '';
        var iso_string = '';
        if (isLive == false) {
        	var source = parent.find('input#source').val();
            var event_time = getPlayerVideoTime(source);
            iso_string = event_time.toISOString();
            iso_string = iso_string.replace('T', ' ');
            iso_string = iso_string.substring(0, 19);
            dataString = dataString + '&event_time=' + iso_string;
        } else {
            try {
                if (event_timestring !== undefined){
                    dataString = dataString + '&event_time=' + event_timestring;
                } else {
                    dataString = dataString + "&serverNow=true";
                }
            }
            catch(err) {
                dataString = dataString + "&serverNow=true";
            }
        } 
        return dataString;
	}
});
        
