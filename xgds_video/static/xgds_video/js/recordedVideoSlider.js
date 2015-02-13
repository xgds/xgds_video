/**
 * Create a slider legend that shows breaks between segments
 */
function createSliderLegend() {
    for (var source in xgds_video.displaySegments) {
        var labels = {}; //key: position, value: label
        var segments = xgds_video.displaySegments[source];
        //list of video segments with same source & episode
        var source = segments[0].source;
        //do not create a legend if any of the segments are missing an end time
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
        var startTime = xgds_video.masterSlider.slider('option', 'min');
        var endTime = xgds_video.masterSlider.slider('option', 'max');
        var totalDuration = endTime - startTime;  // in seconds
        var color = source.displayColor;
        if (color == '') {
            //assign a random color
            alert('display color is not set in video source. Assigning random color.');
            color = '#' + (Math.random() * 0xFFFFFF << 0).toString(16);
        }
        //handle empty space in front of first segment
        var segStartTimeInSeconds = Math.round(segments[0].startTime / 1000);
        var emptySegmentDuration = segStartTimeInSeconds - startTime;
        var fullWidth = $("#masterSlider").width(); 
        var emptySegmentWidth = fullWidth * (emptySegmentDuration / totalDuration);
        var sliderHTML = '<img class="legend-segment ' + source.shortName + '-legend' +
                         '" alt="emptySegment"' +
                         ' src="' + STATIC_URL + 'xgds_video/images/ipx.gif"' +
                         '" width="' + emptySegmentWidth +
                         '" height="4px" style="opacity:0;">';
        xgds_video.masterSlider.before(sliderHTML);
        //for each video segment
        $.each(segments, function(id) {
            var segment = segments[id];
            var source = segment.source;
            var segDuration = 0;
            var width = 0;
            //get the duration of the video segment
            segDuration = segment.endTime - segment.startTime;
            segDuration = Math.round(segDuration / 1000); //in seconds
            width = fullWidth * (segDuration / totalDuration);
            width = Math.round(width);
            //draw the visualization
            xgds_video.masterSlider.before('<img class="legend-segment ' +
                    source.shortName + '-legend' + '" id="' +
                    'Segment' + id + '" width="' + width + 'px"' +
                    ' src="' + STATIC_URL + 'xgds_video/images/ipx.gif"' +
                    'alt="Segment' + id + 
                    '" height="4px" ' +
                    'style="background-color:' +
                    color + ';">');
            if ((id + 1) < segments.length) { //if there is a next segment
                var nextSegment = segments[id + 1];
                var gapTime = nextSegment.startTime - segment.endTime;
                emptySegmentDuration = Math.round(gapTime / 1000);
                emptySegmentWidth = Math.round(fullWidth * (emptySegmentDuration / totalDuration));
                xgds_video.masterSlider.before('<img class="legend-segment ' + source.shortName + '-legend' +
                        '" alt="emptySegment"' +
                        ' src="' + STATIC_URL + 'xgds_video/images/ipx.gif"' +
                        '" width="' + emptySegmentWidth +
                '" height="5px" style="opacity:0.0;">');
            }
        });
        //wrap segments of each source in a div
        $('.' + source.shortName + '-legend').wrapAll('<div class="divider">' + source.shortName + '&nbsp;&nbsp;</div>');
    }
}


function getPercent(width, totalWidth) {
    return Math.round(width / totalWidth * 100);
}


/**
 * Slider Callback:
 * update slider time text when moving slider.
 */
function uponSliderMoveCallBack(event, ui) {
    //update slider time label on top
    xgds_video.movingSlider = true;
    var sliderTime = new Date(ui.value * 1000);
    setSliderTimeLabel(sliderTime);
}


/**
 * Slider Callback:
 *    get the current slider position and do
 *    offset = slider position - each video's start time
 *    seek each video at offset. (means each video's offset will be different,
 *    but their test site time same)
 *    update the test site times to equal slider position.
 */
function uponSliderStopCallBack(event, ui) {
    xgds_video.seekFlag = true;
    var currTime = xgds_video.masterSlider.slider('value'); //in seconds
    currTime = new Date(currTime * 1000); //convert to javascript date
    for (var source in xgds_video.displaySegments) {
        jumpToPosition(currTime, source); //sourceName);
        //XXX take care of the case where seek time is not within playable range.
        //then go to the nearest available segment and play from there.
    }
    xgds_video.movingSlider = false;
}


/**
 * initialize master slider with range (episode start time->episode end time)
 */
function setupSlider() {
    var endTime = null;
    if (_.isEmpty(xgds_video.episode)) {
        if (Object.keys(xgds_video.displaySegments).length < 1) {
            return;
        } else {
            endTime = xgds_video.lastSegment.endTime;
        }
    } else { //video episode needed to set slider range
        endTime = (xgds_video.episode.endTime) ? xgds_video.episode.endTime :
            xgds_video.lastSegment.endTime;
    }
    var duration = Math.ceil(endTime.getTime() / 1000) -
    Math.floor(xgds_video.firstSegment.startTime.getTime() / 1000);
    //for time hover label
    if (endTime) {
        xgds_video.masterSlider = $('#masterSlider').slider({
            step: 1,
            //all times are in seconds
            min: Math.floor(xgds_video.firstSegment.startTime.getTime() / 1000),
            max: Math.ceil(endTime.getTime() / 1000),
            stop: uponSliderStopCallBack,
            slide: uponSliderMoveCallBack,
            range: 'min'
        });
        var sliderTime = new Date($('#masterSlider').slider('value') * 1000);
        setSliderTimeLabel(sliderTime);
        createSliderLegend();
    } else {
        alert('The end time of video segment not available.' +
        'Cannot setup slider');
    }
}
