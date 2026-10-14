// The search dialog renders inside a shadow root, which page stylesheets
// cannot reach. Give it the same square, opaque plate as the rest of the site
// (no rounded corners, no frosted glass). If its markup changes, the selectors
// stop matching and the dialog keeps its default look.
(function () {
  "use strict";

  var css = [
    "*, *::before, *::after { border-radius: 0 !important; }",
    "dialog > div:first-child {",
    "  background-color: rgb(17 15 11 / 0.45) !important;",
    "  -webkit-backdrop-filter: none !important; backdrop-filter: none !important;",
    "}",
    "dialog > div:nth-child(2) {",
    "  background-color: rgb(var(--color-background)) !important;",
    "  border: 1px solid rgb(var(--color-foreground)) !important;",
    "  -webkit-backdrop-filter: none !important; backdrop-filter: none !important;",
    "}",
  ].join("\n");

  function patch(host) {
    var root = host.shadowRoot;
    // Only the search host attaches an open shadow root directly to <body>.
    if (!root || root.querySelector("style[data-bh-plate]")) return;
    var style = document.createElement("style");
    style.setAttribute("data-bh-plate", "");
    style.textContent = css;
    root.appendChild(style);
  }

  function scan() {
    for (var i = 0; i < document.body.children.length; i++) {
      patch(document.body.children[i]);
    }
  }

  function start() {
    scan();
    new MutationObserver(scan).observe(document.body, { childList: true });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
