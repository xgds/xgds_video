var options = {
                //target:        '#output0',   // target element(s) to be updated with server response
                //beforeSubmit:  showRequest,  // pre-submit callback
                //success:       showResponse,  // post-submit callback

                // other available options:
                url: submitNoteUrl,        // override for form's 'action' attribute
                type: 'post',        // 'get' or 'post', override for form's 'method' attribute
                dataType: 'json',        // 'xml', 'script', or 'json' (expected server response type)
                //clearForm: false        // clear all form fields after successful submit
                //resetForm: true        // reset the form after successful submit

                // $.ajax options can be used here too, for example:
                timeout: 3000
            };

/*
 * Form submission
 *
 */
  $(function() {

	  $('.noteSubmit').on('click', function(e) {
		  var parent = $(this).closest('form');
		  // validate and process form here
		  var content = parent.find('input#id_content').val();
		  if (content == '') {
			  parent.find('input#content').focus();
			  return false;
		  }
		  var index = parent.find('input#id_index').val();
		  var tagsId = 'input#id_tags' + index;
		  var tags = parent.find(tagsId).val();
		  var label = parent.find('select#id_label option:selected').val();
		  var extras = parent.find('input#id_extras').val();
		  var dataString = 'content=' + content + '&label=' + label + '&tags=' + tags  + '&extras=' + extras;
		  
		  // not live, pull the time out of the video
		  if (isLive == false) {
			  var event_time = getPlayerVideoTime(parent.find('input#source').val())
			  var iso_string = event_time.toISOString();
			  iso_string = iso_string.replace("T"," ");
			  iso_string = iso_string.substring(0, 19);
			  dataString = dataString + '&event_time=' + iso_string;
		  }
		  
		  $.ajax({
			  type: 'POST',
			  url: submitNoteUrl,
			  data: dataString,
			  complete: function() {
				  //alert ('complete')
				  parent.find('input#id_content').val('');
				  parent.find('select#id_label').prop('selectedIndex', 0);
				  parent.find(tagsId).importTags('');
			  },
			  success: function(response) {
				  //alert ('success')
				  parent.find('input#id_content').val('');
				  parent.find('select#id_label').prop('selectedIndex', 0);
				  parent.find(tagsId).importTags('');
			  },
			  error: function(resp) {
				  console.log(resp);
				  //alert(resp.getAllResponseHeaders());
			  }

		  });
		  e.preventDefault();
	  });
  });
/*

// pre-submit callback
function showRequest(formData, jqForm, options) {
    // formData is an array; here we use $.param to convert it to a string to display it
    // but the form plugin does this for you automatically when it submits the data
    var queryString = $.param(formData);

    // jqForm is a jQuery object encapsulating the form element.  To access the
    // DOM element for the form do this:
    // var formElement = jqForm[0];

    alert('About to submit: \n\n' + queryString);

    // here we could return false to prevent the form from being submitted;
    // returning anything other than false will allow the form submit to continue
    return true;
}
*/

// post-submit callback
function showResponse(responseText, statusText, xhr, $form)  {
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
