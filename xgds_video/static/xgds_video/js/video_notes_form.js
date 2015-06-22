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

var options = {
        // target: '#output0', // target element(s) to be updated with
        // server response
        // beforeSubmit: showRequest, // pre-submit callback
        // success: showResponse, // post-submit callback

        // other available options:
        url: submitNoteUrl, // override for form's 'action' attribute
        type: 'post',       // 'get' or 'post', override for form's 'method' attribute
        dataType: 'json',   // 'xml', 'script', or 'json' (expected server response type)
        // clearForm: false // clear all form fields after successful submit
        // resetForm: true // reset the form after successful submit

        // $.ajax options can be used here too, for example:
        timeout: 3000
};

var check_image_url = 'url(' + STATIC_URL + 'xgds_video/images/check.png)';
var cross_image_url = 'url(' + STATIC_URL + 'xgds_video/images/cross.png)';

function showSuccess(errorMessage, index) {
    $('#error_content' + index).text(errorMessage);
    $('#error_image' + index).css('background', check_image_url);
    $('#error_div' + index).show();
}

function showError(errorMessage, index) {
    $('#error_content' + index).text(errorMessage);
    $('#error_image' + index).css('background', cross_image_url);
    $('#error_div' + index).show();
}

function hideError(index) {
    // $('#error_content').text('');
    $('#error_div' + index).hide();
}

/*
 * Form submission
 *
 */
$(function() {
    $('.noteSubmit').on('click', function(e) {
        var parent = $(this).closest('form');
        // get the index
        var index = parent.find('input#id_index').val();
        // validate and process form here
        var content_text = parent.find('input#id_content' + index);
        var content = content_text.val();

        hideError(index);
        var tagsId = 'input#id_tags' + index;
        var tagInput = parent.find(tagsId);
        var tags = tagInput.val();

        if (tags == '') {
            var addtag = parent.find('input#id_tags' + index + '_tag');
            // see if we have any contents in the tag that should be created as a tag
            if (addtag.val() != '' && addtag.val() != 'add a tag') {
                tagInput.addTag(addtag.val());
                tags = tagInput.val();
            }
        }
        if ((content == '') && (tags == '')) {
            content_text.focus();
            showError('Note must not be empty.', index);
            return false;
        }
        var extras = parent.find('input#id_extras').val();
        var dataString = 'content=' + content + '&tags=' + tags + '&extras=' + extras;
        // not live, pull the time out of the video
        var iso_string = '';
        if (isLive == false) {
            var event_time = getPlayerVideoTime(parent.find('input#source').val());
            iso_string = event_time.toISOString();
            iso_string = iso_string.replace('T', ' ');
            iso_string = iso_string.substring(0, 19);
            dataString = dataString + '&event_time=' + iso_string;
        } else {
            try {
                if (event_timestring !== undefined){
                    dataString = dataString + '&event_time=' + event_timestring;
                }
            }
            catch(err) {
                console.log(err.message);
            }
        } 
        $.ajax({
            type: 'POST',
            url: submitNoteUrl,
            data: dataString,
            success: function(response) {
                showSuccess('Saved ' + content + ' ' + iso_string, index);
                content_text.val('');
                tagInput.importTags('');
            },
            error: function(jqXHR, textStatus, errorThrown) {
                if (errorThrown == '' && textStatus == 'error') {
                    showError('Lost server connection', index);
                } else {
                    showError(textStatus + ' ' + errorThrown, index);
                }
                console.log(jqXHR.getAllResponseHeaders());
            }

        });
        e.preventDefault();
    });
});

/*
 * // pre-submit callback function showRequest(formData, jqForm, options) { //
 * formData is an array; here we use $.param to convert it to a string to
 * display it // but the form plugin does this for you automatically when it
 * submits the data var queryString = $.param(formData); // jqForm is a jQuery
 * object encapsulating the form element. To access the // DOM element for the
 * form do this: // var formElement = jqForm[0];
 *
 * alert('About to submit: \n\n' + queryString); // here we could return false
 * to prevent the form from being submitted; // returning anything other than
 * false will allow the form submit to continue return true; }
 */

//post-submit callback
function showResponse(responseText, statusText, xhr, $form) {
    // for normal html responses, the first argument to the success callback
    // is the XMLHttpRequest object's responseText property

    // if the ajaxForm method was passed an Options Object with the dataType
    // property set to 'xml' then the first argument to the success callback
    // is the XMLHttpRequest object's responseXML property

    // if the ajaxForm method was passed an Options Object with the dataType
    // property set to 'json' then the first argument to the success callback
    // is the json data object returned by the server

    alert('status: ' + statusText + '\n\nresponseText: \n' + responseText +
    '\n\nThe output div should have already been updated with the responseText.');
}
