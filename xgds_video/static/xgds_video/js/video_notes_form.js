
/*
 * Form submission
 * 
 */
  /*$(function() {
    $(".noteSubmit").click(function() {
      // validate and process form here
    	var content = $("input#id_content").val();
    	var label = $("input#id_label").val();
    	var tags = $("input#id_tags").val();
    	var index = $("input#id_index").val();
    	var extras = $("input#id_extras").val();
    	
    	 if (content == "") {
    		 $("input#content").focus();
    		 return false;
    	 }
    	var dataString = 'content='+ content + '&label=' + label + '&tags=' + tags + '&extras=' + extras;  
    	alert (dataString);return false;  
    	$.ajax({  
    	  type: "POST",  
    	  url: submitNoteUrl,  
    	  data: dataString,  
    	  success: function() {  
    		  alert("you are the WINNER!")
    		  $("input#content").reset();
    		  $("input#label").reset();
    		  $("input#tags").reset();
    	  }  
    	});  
    });
  }); */

 
// pre-submit callback 
function showRequest(formData, jqForm, options) { 
    // formData is an array; here we use $.param to convert it to a string to display it 
    // but the form plugin does this for you automatically when it submits the data 
    var queryString = $.param(formData); 
 
    // jqForm is a jQuery object encapsulating the form element.  To access the 
    // DOM element for the form do this: 
    // var formElement = jqForm[0]; 
 
//    alert('About to submit: \n\n' + queryString); 
 
    // here we could return false to prevent the form from being submitted; 
    // returning anything other than false will allow the form submit to continue 
    return true; 
} 
 
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
 
//    alert('status: ' + statusText + '\n\nresponseText: \n' + responseText + 
//        '\n\nThe output div should have already been updated with the responseText.'); 
} 
  
