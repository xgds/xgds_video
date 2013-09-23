
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

