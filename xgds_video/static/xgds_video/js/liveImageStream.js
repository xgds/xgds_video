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

$.extend(xgds_video, {
	haveNewData: false,
	
	//client side websocket event handlers
	onopen: function(zmq) {
		$('#socketStatus').html('connected');
		//there is a topic per camera source. I'm assuming that we'll know these sources beforehand.
		var topic1 = 'RapidImagesensorSampleHazCamLeft';
		var topic2 = 'RapidImagesensorSampleGroundCam';
		
		var handler = function() {
			return function (zmq, topic, obj) {
				console.log("data: ", obj.data);
				//upon receiving the image, display it.
				var data = obj.data.split(':');
				var imgType = data[0];
				var imgContent = data[1];
				
				haveNewData = true;
				
				if (topic == topic1) {
					$("#cameraImage1").attr("src", "data:image/jpeg;base64,"+imgContent);
				} else if (topic == topic2) {
					$("#cameraImage2").attr("src", "data:image/jpeg;base64,"+imgContent);
				}
			};
		}();
		
		zmq.subscribeJson(topic1, handler);
		zmq.subscribeJson(topic2, handler);
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
		zmq.start();
	}
});
