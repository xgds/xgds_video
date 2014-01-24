function getMaxWidth(quantity) {
	  var width = window.innerWidth ||
    			  document.documentElement.clientWidth ||
    			  document.body.clientWidth;
	  if (quantity > 1){
		  width = Math.round(width / 2);
	  }
	  width = width - 100;
	  return width;
}

function calculateSize(newWidth, defaultHeight, defaultWidth) {
	 var resultHeight = defaultHeight;
	 var resultWidth = newWidth;
	 // the default size of the video is bigger than the new size so we have to scale down.
    if (defaultWidth > newWidth){
        ratio = newWidth / defaultWidth
        resultHeight = Math.round(defaultHeight * ratio)
        resultWidth = Math.round(defaultWidth * ratio)
    } else if (newWidth > defaultWidth) {
   	 // the default size of the video is smaller than the new size so we have to cap it at defaults
        resultHeight = defaultHeight
        resultWidth = defaultWidth
    }
    return [resultWidth, resultHeight];
}

