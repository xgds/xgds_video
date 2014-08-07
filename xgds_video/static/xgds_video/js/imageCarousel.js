// __BEGIN_LICENSE__
// Copyright (C) 2008-2010 United States Government as represented by
// the Administrator of the National Aeronautics and Space Administration.
// All Rights Reserved.
// __END_LICENSE__

/*
 * Handlers for websocket that connects tornado server to client
 * for displaying rover images. 
 */

xgds_video = {}; //namespace
var imageSources = $("#imageSources");

$.extend(xgds_video, {
	haveNewData: false,
	
	//client side websocket event handlers
	onopen: function(zmq) {
		$('#socketStatus').html('connected');
		//there is a topic per camera source. I'm assuming that we'll know these sources beforehand.
		var topic1 = 'dds.Resolve.RESOLVE_CAM_ProcessedImage';
		var topic2 = 'dds.Resolve.RESOLVE_CAM_ProcessedImage2';
		var handler = function() {
			return function (zmq, topic, obj) {
				//upon receiving the image, display it.
				var data = obj.data.split(':');
				var imgType = data[0];
				var imgContent = data[1];
				
				haveNewData = true;
				
				if (topic =='dds.Resolve.RESOLVE_CAM_ProcessedImage') {
					$("#cameraImage").attr("src", "data:image/jpeg;base64,"+imgContent);
				} else if (topic == 'dds.Resolve.RESOLVE_CAM_ProcessedImage2') {
					$("#cameraImage2").attr("src", "data:image/jpeg;base64,"+imgContent);
				}
			};
		}();
		
		zmq.subscribeJson(topic1, handler);
	},
	onclose: function(zmq) {
		console.log("on close");
		$('#socketStatus').html('disconnected');
	},
	zmqInit: function() {
        var zmqUrl = zmqURL.replace('{{host}}', window.location.hostname);
		var zmq = new ZmqManager(zmqUrl, 
								{onopen: xgds_video.onopen,
								 onclose: xgds_video.onclose,
								 autoReconnect: true});
		
		//how do we know how many sources of images we will have from zmq messages?
//		var newImageSource = '<div class="item" id="item style="background-color:grey>' +
//		'{% include "xgds_video/video_notes.html with data=form source="dummy" STATIC_URL=STATIC_URL %}' +
//		'</section>' + 
//		'<img style="display:block;" id="'+"cameraImage"+counter+'" src=""></img>'+
//		'</div>';
		zmq.start();
	}
});
