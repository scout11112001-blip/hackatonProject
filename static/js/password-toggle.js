/* Show/hide password on the login page (TASK-017). Progressive enhancement:
   without this script the toggle stays hidden and the form works as before. */
(function () {
  "use strict";
  var buttons = document.querySelectorAll("[data-password-toggle]");
  Array.prototype.forEach.call(buttons, function (button) {
    var input = document.getElementById(button.getAttribute("aria-controls"));
    if (!input) {
      return;
    }
    function setShown(shown) {
      input.type = shown ? "text" : "password";
      button.setAttribute("aria-pressed", shown ? "true" : "false");
    }
    button.addEventListener("click", function () {
      setShown(input.type === "password");
    });
    if (input.form) {
      // Submit as a password field so browsers and password managers treat it as one.
      input.form.addEventListener("submit", function () {
        setShown(false);
      });
    }
    button.hidden = false;
  });
})();
