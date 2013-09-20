
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
  

/*
* Fancy tag input
*/

$('form#create_note #id_tags').tagsInput( { 
    width: '100px',
    height: '25px',
    autocomplete_url: '{% url note_tags_list %}' 
} );

/***
** UI fixup: Add any tag that's been entered on tab-out.
** Disable if an autocomplete record is being selected to prevent double-adding tags.
**/
$('#page-content').on(
    'autocompletefocus',
    'input.ui-autocomplete-input',
    function() {
        $(this).data('autocomplete_active', true);
    }
).on(
    'autocompleteclose',
    'input.ui-autocomplete-input',
    function() {
        $(this).data('autocomplete_active', false);
    }
);

$('#id_tags_tag').blur( function(e) {
    if ( ! $(this).data('autocomplete_active') ) {
        if ( $(this).attr('value') && $(this).attr('value') != 'add a tag' ) {
            $('form#create_note #id_tags').addTag($(this).attr('value'));
        }
    }
});

