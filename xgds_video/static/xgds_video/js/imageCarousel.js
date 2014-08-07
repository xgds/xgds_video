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
var counter = 0;

$.extend(xgds_video, {
	haveNewData: false,
	
	//client side websocket event handlers
	onopen: function(zmq) {
		$('#socketStatus').html('connected');
		var topic = 'dds.Resolve.RESOLVE_CAM_ProcessedImage';
		var handler = function() {
			return function (zmq, topic, obj) {
				//upon receiving the image, display it.
				var data = obj.data.split(':');
				var imgType = data[0];
				var imgContent = data[1];
				haveNewData = true;
				
				//why don't I create a data package here and then do an append after existing html.
				xgds_video.cameraImage.append();
				
				
				$("#cameraImage").attr("src", "data:image/jpeg;base64,"+imgContent);
				$("#cameraImage2").attr("src", "data:image/jpeg;base64,"+imgContent);
				//how do I make sure it only displays the same image once?
				//TODO: archive these images for archived view.
			
			};
		counter = counter +1;
		}();
		
		zmq.subscribeJson(topic, handler);
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
