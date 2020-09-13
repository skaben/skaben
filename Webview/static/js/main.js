
window.addEventListener("contextmenu", (event) => {
  alert("intercept RMB event");
  event.preventDefault();
});


const clicker = this.document.querySelector(".testJs");

clicker.addEventListener("click", (event) => {
  event.preventDefault();
  alert("Javascript working");
});