// The Omniverse downloads hub. Static page, no backend: release data comes
// straight from the public GitHub API, and binaries are served by GitHub Releases.
const REPO = "kiroba/The-Omniverse";
const API = `https://api.github.com/repos/${REPO}`;

// Each app maps to a release asset file name (set in .github/workflows/release.yml).
const APPS = [
  { id: "superapp", name: "The Omni-Hub", icon: "◎", platform: "android", asset: "omniverse-superapp-android-arm64.apk",
    desc: "Every Omniverse experience in one app." },
  { id: "kickback", name: "The KickBack", icon: "💬", platform: "android", asset: "kickback-social-android-arm64.apk",
    desc: "The human-verified social feed." },
  { id: "plaza", name: "Idle Plaza & Brawler", icon: "🕹", platform: "android", asset: "idle-plaza-android-arm64.apk",
    desc: "Hang out, idle, and brawl in the plaza." },
  { id: "monitor", name: "Mesh Monitor", icon: "📡", platform: "android", asset: "mesh-monitor-android-arm64.apk",
    desc: "Watch your peers and mesh health live." },
  { id: "phaser", name: "OmniPhaser Studio", icon: "🎨", platform: "android", asset: "phaser-studio-android-arm64.apk",
    desc: "2D creation studio." },
  { id: "omnicast", name: "OmniCast", icon: "📺", platform: "android", asset: "omnicast-android-arm64.apk",
    desc: "Classroom Mode preview. Live calls aren't wired yet." },
  { id: "brawler", name: "Plaza Brawler", icon: "🥊", platform: "android", asset: "plaza-brawler-android-arm64.apk",
    desc: "An offline fighter for now: you play on your own phone, with no online matches yet." },
  { id: "windows", name: "The Omni-Hub for Windows", icon: "🪟", platform: "windows", asset: "omniverse-windows-x64.zip",
    desc: "Desktop app for Windows 10 and 11 (x64)." },
  { id: "kickback-win", name: "The KickBack for Windows", icon: "💬", platform: "windows", asset: "kickback-social-windows-x64.zip",
    desc: "KickBack on your PC, talking to the daemon here or over Tailscale." },
  { id: "builder", name: "Interactive GUI Builder", icon: "🛠", platform: "tools", href: "downloads/omniverse_interactive_gui_builder.py",
    desc: "Python desktop panel for standalone builds." },
];

const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const mb = (b) => (b / 1048576).toFixed(1) + " MB";
const date = (d) => new Date(d).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });

// Cache API responses for 10 minutes so visitors stay well under GitHub's 60 requests/hour limit.
async function gh(path) {
  const key = "omni:" + path, hit = JSON.parse(localStorage.getItem(key) || "null");
  if (hit && Date.now() - hit.t < 600000) return hit.d;
  const r = await fetch(API + path, { headers: { Accept: "application/vnd.github+json" } });
  if (!r.ok) throw new Error(r.status);
  const d = await r.json();
  try { localStorage.setItem(key, JSON.stringify({ t: Date.now(), d })); } catch (_) {}
  return d;
}

function detectOS() {
  const ua = navigator.userAgent;
  if (/Android/i.test(ua)) return "android";
  if (/Windows/i.test(ua)) return "windows";
  return null;
}

let latest = null, filter = "all";

function renderApps() {
  const assets = Object.fromEntries((latest?.assets || []).map((a) => [a.name, a]));
  $("#app-grid").innerHTML = APPS.filter((a) => filter === "all" || a.platform === filter).map((a) => {
    const asset = assets[a.asset];
    const url = a.href || asset?.browser_download_url;
    const meta = [
      `<span class="pill">${a.platform}</span>`,
      asset ? `<span class="pill ok">${esc(latest.tag_name)} · ${mb(asset.size)}</span>` : "",
      asset?.download_count ? `<span class="pill">${asset.download_count} downloads</span>` : "",
    ].join("");
    return `<div class="card">
      <div class="icon">${a.icon}</div><h3>${esc(a.name)}</h3><p>${esc(a.desc)}</p>
      <div class="meta">${meta}</div>
      <div class="actions">
        <a class="btn sm primary" ${url ? `href="${url}"` : 'aria-disabled="true"'}>${url ? "Download" : "Coming soon"}</a>
        ${a.platform !== "tools" ? `<a class="btn sm ghost" href="#" data-help="${a.platform}">How to install</a>` : ""}
      </div></div>`;
  }).join("");
}

function renderReleases(rels) {
  if (!rels.length) {
    $("#release-list").innerHTML = `<p class="muted">No releases published yet. The first one appears here automatically when a version tag is pushed.</p>`;
    return;
  }
  $("#release-list").innerHTML = rels.slice(0, 8).map((r, i) => `
    <details class="row" ${i === 0 ? "open" : ""}>
      <summary><span>${esc(r.name || r.tag_name)} ${r.prerelease ? '<span class="pill">beta</span>' : ""}</span><span class="muted small">${date(r.published_at)}</span></summary>
      <div class="body">${esc((r.body || "").slice(0, 1200))}</div>
      <div class="assets">${r.assets.map((a) => `<a href="${a.browser_download_url}">⬇ ${esc(a.name)} <span class="muted small">${mb(a.size)}</span></a>`).join("")}</div>
    </details>`).join("");
}

function renderIssues(items) {
  const issues = items.filter((i) => !i.pull_request);
  $("#issue-list").innerHTML = issues.length ? issues.slice(0, 10).map((i) => `
    <div class="row issue"><a href="${i.html_url}" target="_blank" rel="noopener">#${i.number} ${esc(i.title)}</a>
    <span class="muted small">${date(i.created_at)}</span></div>`).join("") : `<p class="muted">Nothing open right now.</p>`;
}

const HELP = {
  android: `<h3>Install on Android</h3><ol><li>Tap <b>Download</b> and open the APK.</li><li>If asked, allow your browser to <b>install unknown apps</b>.</li><li>Tap <b>Install</b>. Updates install the same way.</li></ol><p class="muted small">Needs a 64-bit (arm64) phone, which covers almost every phone from 2017 on.</p>`,
  windows: `<h3>Install on Windows</h3><ol><li>Download and unzip the folder.</li><li>Run <b>omniverse.exe</b> inside it.</li><li>If SmartScreen warns you, click <b>More info → Run anyway</b>. The app isn't code-signed yet.</li></ol>`,
};

document.addEventListener("click", (e) => {
  const t = e.target.closest("[data-help],[data-filter],.close,.modal");
  if (!t) return;
  if (t.dataset.help) { e.preventDefault(); $("#modal-body").innerHTML = HELP[t.dataset.help]; $("#modal").hidden = false; }
  else if (t.dataset.filter) { filter = t.dataset.filter; document.querySelectorAll(".tab").forEach((b) => b.classList.toggle("active", b === t)); renderApps(); }
  else if (t.classList.contains("close") || e.target === t) $("#modal").hidden = true;
});

async function init() {
  const os = detectOS();
  renderApps();
  try {
    const rels = await gh("/releases?per_page=10");
    latest = rels.find((r) => !r.draft) || null;
    renderReleases(rels);
    renderApps();
    $("#release-note").textContent = latest ? `Latest: ${latest.tag_name}, published ${date(latest.published_at)}` : "";
    const pick = APPS.find((a) => a.platform === os && latest?.assets.some((x) => x.name === a.asset));
    if (pick) {
      const a = latest.assets.find((x) => x.name === pick.asset);
      $("#primary-dl").href = a.browser_download_url;
      $("#primary-dl").textContent = `Download for ${os === "android" ? "Android" : "Windows"}`;
      $("#detect").textContent = `${pick.name} ${latest.tag_name} · ${mb(a.size)}`;
    }
  } catch (err) {
    $("#release-list").innerHTML = `<p class="muted">Couldn't reach GitHub right now. <a href="https://github.com/${REPO}/releases">See releases on GitHub</a>.</p>`;
  }
  gh("/issues?state=open&per_page=20").then(renderIssues).catch(() => { $("#issue-list").innerHTML = `<p class="muted"><a href="https://github.com/${REPO}/issues">View issues on GitHub</a></p>`; });
}

// Lightweight starfield
(function stars() {
  const c = $("#stars"), x = c.getContext("2d"); let s = [];
  const size = () => { c.width = innerWidth; c.height = innerHeight; s = Array.from({ length: 140 }, () => ({ x: Math.random() * c.width, y: Math.random() * c.height, r: Math.random() * 1.3, v: Math.random() * 0.25 + 0.05 })); };
  size(); addEventListener("resize", size);
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) { s.forEach((p) => { x.fillStyle = "#fff8"; x.fillRect(p.x, p.y, p.r, p.r); }); return; }
  (function tick() { x.clearRect(0, 0, c.width, c.height); x.fillStyle = "#ffffffaa"; s.forEach((p) => { p.y += p.v; if (p.y > c.height) p.y = 0; x.fillRect(p.x, p.y, p.r * 1.6, p.r * 1.6); }); requestAnimationFrame(tick); })();
})();

init();

// ---- Tester report (no account): builds plain text, then the phone's share sheet or the clipboard.
(function () {
  var f = document.getElementById('tester-report');
  if (!f) return;
  var $ = function (id) { return document.getElementById(id); };
  function text() {
    return ['[Omniverse tester report]',
      'App: ' + $('r-app').value,
      'Step: ' + ($('r-step').value.trim() || '-'),
      'What happened: ' + $('r-what').value.trim(),
      'Phone: ' + ($('r-phone').value.trim() || '-'),
      'Browser: ' + navigator.userAgent,
      'Page: ' + location.href.split('#')[0]].join('\n');
  }
  function say(m) { $('r-msg').textContent = m; }
  function ready() {
    if (!$('r-what').value.trim()) { say('Please say what happened first.'); $('r-what').focus(); return false; }
    return true;
  }
  function copy(t) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(t).then(function () { say('Copied. Paste it into a message to Keith.'); });
    }
    var a = document.createElement('textarea'); a.value = t; document.body.appendChild(a); a.select();
    try { document.execCommand('copy'); say('Copied. Paste it into a message to Keith.'); }
    catch (e) { say('Couldn\'t copy. Select the text and copy it yourself.'); }
    document.body.removeChild(a);
    return Promise.resolve();
  }
  $('r-copy').addEventListener('click', function () { if (ready()) copy(text()); });
  $('r-send').addEventListener('click', function () {
    if (!ready()) return;
    var t = text();
    if (navigator.share) {
      navigator.share({ title: 'Omniverse tester report', text: t })
        .then(function () { say('Thanks! Report shared.'); })
        .catch(function (e) { if (e && e.name !== 'AbortError') copy(t); });
    } else { copy(t); }
  });
})();
