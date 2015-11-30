//__BEGIN_LICENSE__
// Copyright (c) 2015, United States Government, as represented by the
// Administrator of the National Aeronautics and Space Administration.
// All rights reserved.
//
// The xGDS platform is licensed under the Apache License, Version 2.0
// (the "License"); you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
// http://www.apache.org/licenses/LICENSE-2.0.
//
// Unless required by applicable law or agreed to in writing, software distributed
// under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
// CONDITIONS OF ANY KIND, either express or implied. See the License for the
// specific language governing permissions and limitations under the License.
//__END_LICENSE__

//prepare the form when the DOM is ready 
$(document).ready(function() { 
	
	hideError();
	
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
		    autocomplete_url: "{% url 'note_tags_list' %}"
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
