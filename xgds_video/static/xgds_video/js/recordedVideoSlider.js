/**
 * Create a slider legend that shows breaks between segments
 */
function createSliderLegend() {
    for (var key in xgds_video.displaySegments) {
        var segments = xgds_video.displaySegments[key]; 
        //list of video segments with same source & episode
        var source = segments[0].source;

        //get the total slider range in seconds
        var startTime = xgds_video.masterSlider.slider('option', 'min');
        var endTime = xgds_video.masterSlider.slider('option', 'max');
        var totalDuration = endTime - startTime;  // in seconds
        var color = getRandomColor();

        //handle empty space infront of first segment
        var segStartTimeInSeconds = Math.round(segments[0].startTime / 1000);
        var emptySegmentDuration =  segStartTimeInSeconds - startTime;
        var emptySegmentWidth = xgds_video.masterSlider.width() * 
                                (emptySegmentDuration / totalDuration);
        xgds_video.masterSlider.before('<img class="' + source.shortName + 
                                       '" width="' + emptySegmentWidth + 
                                       '" height="5px" style="opacity:0.0;">');

        //for each video segment
        $.each(segments, function(id) {
            var segment = segments[id];
            var source = segment.source;
            //get the duration of the =video segment
            var segDuration = Math.round((segment.endTime - 
                              segment.startTime) / 1000); //in seconds
            var width = xgds_video.masterSlider.width() * 
                        (segDuration / totalDuration);

            //draw the visualization
            xgds_video.masterSlider.before('<img class="' + 
                                            source.shortName + '" id=' + 
                                            id + ' width="' + width +
                                            '" height="5px" '+
                                            'style="background-color:' + 
                                            color + ';">');

            if (segments[id + 1]) { //if there is a next segment
                var nextSegment = segments[id + 1];
                emptySegmentDuration = Math.round((nextSegment.startTime - 
                                                   segment.endTime) / 1000);
                emptySegmentWidth = xgds_video.masterSlider.width() * 
                                    (emptySegmentDuration / totalDuration);
                xgds_video.masterSlider.before('<img class="' + 
                                         source.shortName + 
                                        '" width="' + emptySegmentWidth +
                                        '" height="5px" style="opacity:0.0;">');
            }
        });
        //wrap segments of each source in a div
        $('.' + source.shortName ).wrapAll( '<div class="divider";"></div>');
    }
}


/**
 * Slider Callback:
 * update slider time text when moving slider.
 */
function uponSliderMoveCallBack(event, ui) {
    xgds_video.movingSlider = true;
    var sliderTime = new Date(ui.value * 1000);
    $('#sliderTimeLabel').val(sliderTime.toTimeString());
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
    xgds_video.movingSlider = false;
    var currTime = xgds_video.masterSlider.slider('value'); //in seconds
    currTime = new Date(currTime * 1000); //convert to javascript date

    for (var key in xgds_video.displaySegments) {
        var sourceName = xgds_video.displaySegments[key][0].source.shortName;
        jumpToPosition(currTime, sourceName);

        //XXX take care of the case where seek time is not within playable range.
        //then go to the nearest available segment and play from there.
    }
}


/**
 * initialize master slider with range (episode start time->episode end time)
 */
function setupSlider() {
    if (xgds_video.episode) { //video episode needed to set slider range
        var endTime = (xgds_video.episode.endTime) ? xgds_video.episode.endTime : 
                       xgds_video.lastSegment.endTime;
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
            $('#sliderTimeLabel').val(sliderTime.toTimeString());
            createSliderLegend();
        } else {
            alert('The end time of video segment not available.'+
                  'Cannot setup slider');
        }
    } else {
        alert('The video episode is not available.');
    }
}

