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
	createSliderLegend: function(isResizing) {
		/**
		 * Create a slider ribbon that shows breaks between segments
		 */
		var ribbon = $("#ribbon");
		if (_.isUndefined(xgds_video.options.resizeSlider)){
			$( window ).resize(function() {
				xgds_video.createSliderLegend(true);
			});
			xgds_video.options.resizeSlider = true;
		}

		var singleSource = (Object.keys(xgds_video.options.displaySegments).length == 1);
		for (var sourceName in xgds_video.options.displaySegments) {
			var segments = xgds_video.options.displaySegments[sourceName];
			var source = segments[0].source;
			var dividerName = "divider-" + source.shortName;
			if (isResizing){
				$("#ribbon").find("#"+dividerName).remove();
			}
			var labels = {}; 
			var endPointCheck = true;
			$.each(segments, function(id) {
				var segment = segments[id];
				if (!segment.endTime) {
					endPointCheck = false;
					return false;
				}
			});
			if (!endPointCheck) {
				return;
			}
			//get the total slider range in seconds
			var firstSegmentStartMoment = moment(segments[0].startTime);
			var episodeStartMoment = singleSource ? firstSegmentStartMoment : moment(xgds_video.options.episode.startTime);
			var episodeEndMoment = singleSource ? moment(segments[segments.length - 1].endTime) : moment(xgds_video.options.episode.endTime);
			var totalDuration = episodeEndMoment.diff(episodeStartMoment, 'seconds');
			var color = source.displayColor;
			if (color == '') {
				//assign a random color
				color = '#' + (Math.random() * 0xFFFFFF << 0).toString(16);
			}

			var fullWidth = $("#masterSlider").width();
			var sourceRibbon = $('<div class="divider" id="' + dividerName + '"><strong class="sourceLabel" id="label_' + source.shortName + '" >' + source.shortName  + '</strong>');
			sourceRibbon.appendTo(ribbon)

			if (!singleSource){
				//handle empty space in front of first segment
				var emptySegmentDuration = firstSegmentStartMoment.diff(episodeStartMoment, 'seconds');
				var emptySegmentWidth = Math.round(fullWidth * (emptySegmentDuration / totalDuration));
				var emptySegmentHTML = '<img class="legend-segment ' + source.shortName + '-legend' +
				'" alt="emptySegment"' +
				' src="' + STATIC_URL + 'xgds_video/images/ipx.gif"' +
				'" width="' + emptySegmentWidth +
				'" height="4px" style="opacity:0;">';
				sourceRibbon.append(emptySegmentHTML);
			}
			//for each video segment
			$.each(segments, function(id) {
				var segment = segments[id];
				var source = segment.source;
				var segDuration = 0;
				var width = 0;
				//get the duration of the video segment
				var segmentStartMoment = moment(segment.startTime);
				var segmentEndMoment = moment(segment.endTime);
				segDuration = segmentEndMoment.diff(segmentStartMoment, 'seconds');
				width = fullWidth * (segDuration / totalDuration);
				width = Math.round(width);
				//draw the visualization
				var htmlNugget = '<img class="legend-segment ' +
				source.shortName + '-legend' + '" id="' +
				'Segment' + id + '" width="' + width + 'px"' +
				' src="' + STATIC_URL + 'xgds_video/images/ipx.gif"' +
				'alt="Segment' + id + 
				'" height="4px" ' +
				'style="background-color:' +
				color + ';">';
				sourceRibbon.append(htmlNugget);
				if ((id + 1) < segments.length) { //if there is a next segment
					var nextSegment = segments[id + 1];
					var nextSegmentStartMoment = moment(nextSegment.startTime);
					var gapTime = nextSegmentStartMoment.diff(segmentEndMoment, 'seconds');
					emptySegmentWidth = Math.round(fullWidth * (gapTime / totalDuration));
					var htmlNugget2 = '<img class="legend-segment ' + source.shortName + '-legend' +
					'" alt="emptySegment"' +
					' src="' + STATIC_URL + 'xgds_video/images/ipx.gif"' +
					'" width="' + emptySegmentWidth +
					'" height="5px" style="opacity:0.0;">';
					sourceRibbon.append(htmlNugget2);
				}
			});
			
		}
		var leftMargin = 0;
		var leftPadding = 0;
		var labels = $(".sourceLabel");
		for (var i=0; i<labels.length; i++){
			var l = $(labels[i]);
			if (l.width() > leftMargin) {
				leftMargin = l.width();
				leftPadding = parseInt(l.css('margin-right'));
			}
		}
		if (leftMargin > 0){
			var value = leftMargin + leftPadding;
			$("#masterSlider").css("margin-left", value + 'px');
		}
	},

	getPercent: function(width, totalWidth) {
		return Math.round(width / totalWidth * 100);
	},

	uponSliderMoveCallBack: function(event, ui) {
		/**
		 * Slider Callback:
		 * update slider time text when moving slider.
		 */
		//update slider time label on top
		xgds_video.options.movingSlider = true;
		xgds_video.setSliderTimeLabel(moment.unix(ui.value));
	},

	uponSliderStopCallBack: function(event, ui) {
		/**
		 * Slider Callback:
		 *    get the current slider position and do
		 *    offset = slider position - each video's start time
		 *    seek each video at offset. (means each video's offset will be different,
		 *    but their test site time same)
		 *    update the test site times to equal slider position.
		 */
		xgds_video.options.seekFlag = true;
		var currTime = xgds_video.masterSlider.slider('value'); //in seconds
		currTime = new Date(currTime * 1000); //convert to javascript date
		console.log('SLIDER STOPPED, go to ' + currTime);
		for (var source in xgds_video.options.displaySegments) {
			xgds_video.jumpToPosition(currTime, source); //sourceName);
			//XXX take care of the case where seek time is not within playable range.
			//then go to the nearest available segment and play from there.
		}
		xgds_video.options.movingSlider = false;
	},
	setupSlider: function() {
		/**
		 * initialize master slider with range (episode start time->episode end time)
		 */
		if (Object.keys(xgds_video.options.displaySegments).length == 0){
			return;
		}
		var endTime = xgds_video.options.episode.endTime ? xgds_video.options.episode.endTime : xgds_video.options.lastSegment.endTime;
		var endMoment = moment(endTime);
		var startMoment = moment(xgds_video.options.episode.startTime);
		//var duration = endMoment.diff(startMoment, 'seconds');
		if (xgds_video.options.episode.endTime) {
			xgds_video.masterSlider = $('#masterSlider').slider({
				step: 1,
				min: startMoment.unix(), //moment(xgds_video.options.firstSegment.startTime).unix(),
				max: endMoment.unix(), 
				stop: xgds_video.uponSliderStopCallBack,
				slide: xgds_video.uponSliderMoveCallBack,
				range: 'min'
			});
			xgds_video.setSliderTimeLabel(startMoment);
			xgds_video.createSliderLegend(false);
		} else {
			alert('The end time of a video segment is not available.' +
			'Cannot setup slider');
		}
	},
	setSliderTime:function(datetime) {
		//update the slider
		var seconds = Math.round(datetime.getTime() / 1000);
		$(xgds_video.masterSlider).slider('value', seconds);
		xgds_video.setSliderTimeLabel(datetime);
	}

});
