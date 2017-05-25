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
	getMaxWidth:function(quantity) {
		// TODO DELETE this is also not used
		var width = window.innerWidth ||
		document.documentElement.clientWidth ||
		document.body.clientWidth;
		if (quantity > 1) {
			width = Math.round(width / 2);
		}
		width = width - 100;
		return width;
	},
	calculateSize:function(newWidth, defaultHeight, defaultWidth) {
		// TODO DELETE this is not used
		var resultHeight = defaultHeight;
		var resultWidth = newWidth;
		// the default size of the video is bigger than the new size so we have to scale down.
		if (defaultWidth > newWidth) {
			ratio = newWidth / defaultWidth;
			resultHeight = Math.round(defaultHeight * ratio);
			resultWidth = Math.round(defaultWidth * ratio);
		} else if (newWidth > defaultWidth) {
			// the default size of the video is smaller than the new size so we have to cap it at defaults
			resultHeight = defaultHeight;
			resultWidth = defaultWidth;
		}
		return [resultWidth, resultHeight];
	},
	readAspectRatio:function(aspectRatio){
		var splits = aspectRatio.split(':');
		var aspectWidth = parseInt(splits[0]);
		var aspectHeight = parseInt(splits[1]);
		return {width:aspectWidth,
			    height:aspectHeight};
	},
	calculateSizeWithRatio:function(container, aspectRatioString) {
		var aspectRatio = xgds_video.readAspectRatio(aspectRatioString);
		var containerWidth = $(container).width();
		var containerHeight = $(container).height();
		
		if (containerWidth == 0  || containerHeight == 0) {
			// default to 95% width
			return ['95%'];
		}
		
		// first check if width will fit:
		var calculatedWidth = (aspectRatio.width * containerHeight) / aspectRatio.height;
		// if it does, go with that.
		if (calculatedWidth <= containerWidth) {
			return [calculatedWidth, containerHeight];
		}
		var calculatedHeight = (aspectRatio.height * containerWidth) / aspectRatio.width;
		return [containerWidth, calculatedHeight];
	}

});