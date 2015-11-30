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

    function initializePackery() {
      //update  sizing
        var $container = $('#container');
        $container.packery({
        itemSelector: '.item',
        gutter: 10
        });
        
        makeResizable($container);
    }
    
    function makeResizable($container) {
        // get item elements, jQuery-ify them
        var $itemElems = $( $container.packery('getItemElements') );
        
        var $lockAspects = $(".lockAspect");
        // make item elements draggable
        $lockAspects.draggable().resizable({
            aspectRatio: true
        });
        
        var $freeAspects = $(".freeAspect");
        if ($freeAspects !== null){
            $freeAspects.draggable().resizable();
        }
        
        // bind Draggable events to Packery
        $container.packery( 'bindUIDraggableEvents', $itemElems );
        
        // handle resizing
        var resizeTimeout;
        $itemElems.on( 'resize', function( event, ui ) {
          // debounce
          if ( resizeTimeout ) {
            clearTimeout( resizeTimeout );
          }
        
          resizeTimeout = setTimeout( function() {
            $container.packery( 'fit', ui.element[0] );
          }, 100 );
    });
    }
    /*
  // get item elements, jQuery-ify them
  var $itemElems = $( $container.packery('getItemElements') );
  // make item elements draggable
  $itemElems.draggable().resizable();
  // bind Draggable events to Packery
  $container.packery( 'bindUIDraggableEvents', $itemElems );
  
  // handle resizing
  var resizeTimeout;
  $itemElems.on( 'resize', function( event, ui ) {
    // debounce
    if ( resizeTimeout ) {
      clearTimeout( resizeTimeout );
    }
  
    resizeTimeout = setTimeout( function() {
      $container.packery( 'fit', ui.element[0] );
    }, 100 );
  });*/
