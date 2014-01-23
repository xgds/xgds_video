//prepare the form when the DOM is ready 
$(document).ready(function() { 
	
	$('.create_note_form').each(function() {
		var index = $(this).find("input#id_index").val();
	   // bind form using 'ajaxForm' 
       $(this).ajaxForm(options);
       
       // bind the fancy tags for each form
       var tagsId = "input#id_tags" + index;
       var input_idTags = $(this).find(tagsId);
       input_idTags.tagsInput({
	    	width: 'auto',
		    height: '14px',
		    autocomplete_url: '{% url note_tags_list %}'
//		    autocomplete:{selectFirst:true,width:'80px',autoFill:true}
			});
			
       var tagsId_tag = "input#id_tags" + index + "_tag";
       $(this).find(tagsId_tag).blur(function(e) {
		    if (! $(this).data('autocomplete_active')) {
		        if ($(this).attr('value') && $(this).attr('value') != 'add a tag') {
		        	input_idTags.addTag($(this).attr('value'));
		        }
		    }
		});
	});
	    
    
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
    
}); 
