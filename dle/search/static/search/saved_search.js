function getUrl() {
  var url = document.URL;
  document.getElementById("id_url").value = url;
}
window.addEventListener('load', getUrl);
document.body.addEventListener('click', getUrl, true); 
document.body.addEventListener('keyup', getUrl, true);
