//set up google earth
var ge;
function init() {
    google.earth.createInstance('map3d', initCB, failureCB);
}

function initCB(instance) {
    ge = instance;
    ge.getWindow().setVisibility(true);
}

function failureCB(errorCode) {
}
