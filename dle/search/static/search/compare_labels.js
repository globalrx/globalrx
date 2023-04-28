document.body.addEventListener('click', shouldLabelsBeShown, true);
document.body.addEventListener('mouseup', shouldLabelsBeShown, true); // adding for spacebar selects

function shouldLabelsBeShown() {
  var checkedBoxes = document.querySelectorAll('input[name=compare]:checked');
  // var link = document.getElementById('compare-button-container');
  const compareLabelsButton = document.getElementById("compare-labels-button");

  if(checkedBoxes.length == 2 || checkedBoxes.length == 3) {
    compareLabelsButton.disabled = false;
  } else {
    compareLabelsButton.disabled = true;
  }
}

function compareLabels() {
  var checkedBoxes = document.querySelectorAll('input[name=compare]:checked');
  var compareUrl = '../compare/compare_labels?';
  var searchTerm = document.querySelector('.ais-SearchBox-input').value;

  compareUrl += 'search_text=' + searchTerm;

  for (i = 0; i < checkedBoxes.length; i++) {
    if(i == 0) {
      compareUrl += `&first-label=${checkedBoxes[0].value}`;
    } else if(i == 1) {
      compareUrl += `&second-label=${checkedBoxes[1].value}`;
    } else if(i == 2) {
      compareUrl += `&third-label=${checkedBoxes[2].value}`;
    }
  }
  location.href = compareUrl;
}