
/*
 * Form submission
 * 
 */
  $(function() {
    $(".noteSubmit").click(function() {
      // validate and process form here
    	var content = $("input#id_content").val();
    	var label = $("input#id_label").val();
    	var tags = $("input#id_tags").val();
    	var index = $("input#id_index").val();
    	alert("clicked " + index);
    	
    	 if (content == "") {
    		 $("input#content").focus();
    		 return false;
    	 }
    	var dataString = 'content='+ content + '&label=' + label + '&tags=' + tags;  
    	//alert (dataString);return false;  
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
  });
  
