(function () {
  "use strict";

  var root = document.querySelector("[data-chat-poll-url]");
  if (!root) {
    return;
  }
  var list = document.getElementById("chat-messages");
  var status = root.querySelector("[data-chat-status]");
  var url = root.dataset.chatPollUrl;
  var interval = Number(root.dataset.chatPollMs) || 5000;
  var maxErrors = Number(root.dataset.chatMaxErrors) || 5;
  var errors = 0;
  var timer = null;
  var inFlight = false;
  var stopped = false;

  function lastId() {
    var items = list.querySelectorAll("li[data-message-id]");
    if (items.length === 0) {
      return "0";
    }
    return items[items.length - 1].getAttribute("data-message-id");
  }

  function schedule() {
    if (!stopped && !document.hidden && timer === null && !inFlight) {
      timer = setTimeout(poll, interval);
    }
  }

  function poll() {
    if (inFlight || stopped) {
      return;
    }
    inFlight = true;
    timer = null;
    fetch(url + "?after=" + encodeURIComponent(lastId()), {
      credentials: "same-origin",
      cache: "no-store",
      headers: { "X-Requested-With": "XMLHttpRequest" },
    })
      .then(function (response) {
        if (response.status === 204) {
          errors = 0;
          return;
        }
        if (response.redirected || (response.ok && !response.headers.get("X-Chat-Fragment"))) {
          throw new Error("redirected");
        }
        if (response.ok) {
          return response.text().then(function (text) {
            var doc = new DOMParser().parseFromString(text, "text/html");
            var nodes = doc.body.querySelectorAll("li[data-message-id]");
            var added = false;
            for (var i = 0; i < nodes.length; i += 1) {
              var node = nodes[i];
              if (document.getElementById(node.id)) {
                continue;
              }
              list.appendChild(document.importNode(node, true));
              added = true;
            }
            if (added) {
              var empty = document.getElementById("chat-empty");
              if (empty) {
                empty.parentNode.removeChild(empty);
              }
              if (list.lastElementChild) {
                list.lastElementChild.scrollIntoView({ block: "nearest" });
              }
            }
            errors = 0;
          });
        }
        throw new Error("status " + response.status);
      })
      .catch(function () {
        errors += 1;
        if (errors >= maxErrors) {
          stopped = true;
          status.textContent = "Автообновление остановлено. Нажмите «Обновить».";
        }
      })
      .then(function () {
        inFlight = false;
        schedule();
      });
  }

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      clearTimeout(timer);
      timer = null;
    } else if (!stopped && timer === null && !inFlight) {
      poll();
    }
  });

  schedule();
})();
