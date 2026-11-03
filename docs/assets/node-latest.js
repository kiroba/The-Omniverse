// Points the "Download Omni Node" button at the newest Omni Node release, prereleases included
// (GitHub's /releases/latest skips prereleases). Runs in the visitor's browser against the public
// GitHub API (60 requests/hour per visitor, no token, no server). If anything fails, the button
// keeps the version written in index.html.
(function () {
  var btn = document.getElementById('omni-node-dl');
  if (!btn || !window.fetch) return;
  var label = document.getElementById('omni-node-ver');
  fetch('https://api.github.com/repos/kiroba/Omni-Node-Daemon/releases?per_page=10', {
    headers: { Accept: 'application/vnd.github+json' }
  })
    .then(function (r) { return r.ok ? r.json() : []; })
    .then(function (releases) {
      for (var i = 0; i < releases.length; i++) {
        var rel = releases[i];
        if (rel.draft) continue;
        var assets = rel.assets || [];
        for (var j = 0; j < assets.length; j++) {
          if (/\.apk$/i.test(assets[j].name)) {
            btn.href = assets[j].browser_download_url;
            if (label) label.textContent = rel.tag_name;
            return;
          }
        }
      }
    })
    .catch(function () {});
})();
