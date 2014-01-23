{% with videoFeedData=data %}
//prepare the form when the DOM is ready
$(document).ready(function() {

	{% for feed, form in videoFeedData %}

	   // bind form using 'ajaxForm'
       $('#create_note{{ form.index }}').ajaxForm(options);

       // bind the fancy tags for each form
       console.log("binding tags for form#create_note{{ form.index }} #id_tags{{ form.index }}");
	    $('form#create_note{{ form.index }} #id_tags{{ form.index }}').tagsInput({
	    	width: 'auto',
		    height: '14px',
		    autocomplete_url: '{% url note_tags_list %}'
//		    autocomplete:{selectFirst:true,width:'80px',autoFill:true}
			});

	    console.log("BLUR  for form#create_note{{ form.index }} #id_tags{{ form.index }}_tag")
		$('form#create_note{{ form.index }} #id_tags{{ form.index }}_tag').blur(function(e) {
		    if (! $(this).data('autocomplete_active')) {
		        if ($(this).attr('value') && $(this).attr('value') != 'add a tag') {
		            $('form#create_note{{ form.index }} #id_tags{{ form.index }}').addTag($(this).attr('value'));
		        }
		    }
		});


//		$('form#create_note{{ form.index }} #id_tags_tag').delegate('.ui-autocomplete-input', 'blur', function(eventObj) {
//		    if (! $(this).data('autocomplete_active')) {
//		        if ($(this).attr('value') && $(this).attr('value') != 'add a tag') {
//		        	 $('form#create_note{{ form.index }} #id_tags').addTag($(this).attr('value'));
//		        }
//		    }
//		});

    {% endfor %}

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
{% endwith %}
