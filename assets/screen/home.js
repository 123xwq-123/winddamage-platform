/* 新版大屏主页交互：总览 / 上传分析 / 报告渲染 / 3D 标签定位 */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var farm = $("farm");
  var lastPayload = null;   // 最近一次分析结果
  var pendingFile = null;   // 已选未分析的文件

  /* ── 时钟 ── */
  var WEEK = ["日", "一", "二", "三", "四", "五", "六"];
  function tick() {
    var d = new Date(), p = function (n) { return (n < 10 ? "0" : "") + n; };
    $("sc-clock-time").textContent = p(d.getHours()) + ":" + p(d.getMinutes()) + ":" + p(d.getSeconds());
    $("sc-clock-date").textContent = d.getFullYear() + "-" + p(d.getMonth() + 1) + "-" + p(d.getDate()) + " 星期" + WEEK[d.getDay()];
  }
  tick(); setInterval(tick, 1000);

  /* ── 当前用户 ── */
  fetch("/screen/api/me").then(function (r) { return r.json(); }).then(function (u) {
    if (u.username) {
      $("sc-username").textContent = u.username;
      $("sc-avatar").textContent = u.username.charAt(0).toUpperCase();
      $("sc-role").textContent = u.role === "admin" ? "管理员" : "巡检员";
    }
  }).catch(function () {});

  /* ── 总览 ── */
  function loadOverview() {
    fetch("/screen/api/overview").then(function (r) { return r.json(); }).then(function (o) {
      $("sc-g-val").textContent = o.completion + "%";
      $("sc-gauge-arc").style.strokeDashoffset = 314 - 314 * (o.completion / 100);
      var max = Math.max(o.total, o.week, o.high_risk, o.recheck, 1);
      $("sc-k-total").textContent = o.total;      $("sc-b-total").style.width = (100 * o.total / max) + "%";
      $("sc-k-week").textContent = o.week;        $("sc-b-week").style.width = (100 * o.week / max) + "%";
      $("sc-k-high").textContent = o.high_risk;   $("sc-b-high").style.width = (100 * o.high_risk / max) + "%";
      $("sc-k-recheck").textContent = o.recheck;  $("sc-b-recheck").style.width = (100 * o.recheck / max) + "%";
    }).catch(function () {});
  }
  loadOverview();

  /* ── 上传（拖拽 + 点击） ── */
  var drop = $("sc-drop");
  drop.addEventListener("click", function () { $("sc-file").click(); });
  $("sc-file").addEventListener("change", function () { pickFile(this.files[0]); });
  ["dragenter", "dragover"].forEach(function (ev) {
    drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add("drag"); });
  });
  ["dragleave", "drop"].forEach(function (ev) {
    drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove("drag"); });
  });
  drop.addEventListener("drop", function (e) { pickFile(e.dataTransfer.files[0]); });

  function pickFile(f) {
    if (!f || !/^image\//.test(f.type)) return;
    pendingFile = f;
    $("sc-drop-text").innerHTML = "已选择：<b>" + esc(f.name) + "</b><br>点击底部「开始分析」";
    $("sc-analyze").disabled = false;
    showImageInfo({ filename: f.name, meta: "待分析" });
  }

  /* ── 分析 ── */
  $("sc-analyze").addEventListener("click", function () {
    if (!pendingFile) return;
    var btn = this;
    btn.disabled = true; btn.textContent = "⏳ 分析中…";
    var fd = new FormData();
    fd.append("file", pendingFile);
    fetch("/screen/api/analyze", { method: "POST", body: fd })
      .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(function (p) { lastPayload = p; renderReport(p); loadOverview(); })
      .catch(function (e) { alert("分析失败：" + e.message); })
      .finally(function () { btn.textContent = "▶ 开始分析"; btn.disabled = false; });
  });

  /* ── 渲染报告 ── */
  function renderReport(p) {
    var kv = p.kv || {};
    $("sc-r-level").textContent = p.risk.level || "—";
    $("sc-r-type").textContent = p.risk.type || "无";
    $("sc-r-conf").textContent = p.risk.confidence || "—";
    setKv($("sc-report-kv"), ["component", "location", "size", "advice", "model", "time", "report_no"], kv);
    showImageInfo(p.image_info || {});
    renderLoc(p.locator || {});
    renderRecent(p.recent || []);
    /* 3D：损伤高亮 */
    var loc = p.locator || {};
    farm.contentWindow.postMessage({
      type: "wd:damage", hasDamage: !!loc.hasDamage,
      part: loc.part || "", type: loc.type || "", location: loc.location || ""
    }, "*");
    $("sc-dmg-txt").textContent = loc.hasDamage ? (loc.part || "") + "·" + (loc.type || "") : "";
    $("sc-dmg-tag").style.display = loc.hasDamage ? "block" : "none";
    $("sc-dmg-dot").style.display = loc.hasDamage ? "block" : "none";
    if (loc.part) $("sc-nac").textContent = loc.part;
    $("sc-export").disabled = !p.record_id;
  }

  function setKv(box, keys, data) {
    var labels = ["构件", "损伤位置", "程度/尺寸", "处置建议", "模型", "时间", "报告编号"];
    var spans = box.querySelectorAll(".v");
    keys.forEach(function (k, i) {
      if (spans[i]) spans[i].textContent = (data && data[k]) || "—";
    });
    if (box.children.length !== keys.length * 2) {   // 初次：重建 .k
      box.innerHTML = "";
      keys.forEach(function (k, i) {
        var a = document.createElement("span"); a.className = "k"; a.textContent = labels[i] || k;
        var b = document.createElement("span"); b.className = "v"; b.textContent = (data && data[k]) || "—";
        box.appendChild(a); box.appendChild(b);
      });
    }
  }

  function showImageInfo(info) {
    var box = $("sc-imginfo");
    var dim = (info.meta || "").split("|").map(function (s) { return s.trim(); });
    box.innerHTML =
      '<span class="k">文件名</span><span class="v">' + esc(info.filename || "—") + "</span>" +
      '<span class="k">尺寸/格式</span><span class="v">' + esc(dim[0] || "—") + "</span>" +
      '<span class="k">大小</span><span class="v">' + esc(dim[2] || (dim[1] ? dim.join(" · ") : "—")) + "</span>";
  }

  function renderLoc(loc) {
    var box = $("sc-loc");
    if (!loc.hasDamage) { box.innerHTML = '<div class="sc-empty">未见损伤，状态正常</div>'; return; }
    function row(cls, part, txt, conf) {
      return '<div class="sc-loc-row"><span class="dot ' + cls + '"></span><span class="p">' +
        esc(part || "—") + '</span><span class="t">' + esc(txt || "") + "</span></div>";
    }
    box.innerHTML =
      row("red", loc.part, loc.type, "") +
      row("ye", "位置范围", loc.location || "—", "") +
      row("gr", "处置", (lastPayload && lastPayload.kv && lastPayload.kv.advice) || "", "");
  }

  function renderRecent(rows) {
    var box = $("sc-recent");
    if (!rows.length) { box.innerHTML = '<div class="sc-empty">暂无检测记录</div>'; return; }
    var h = '<table class="sc-mini"><tr><th>图片</th><th>构件</th><th>类型</th><th>优先级</th></tr>';
    rows.forEach(function (r) {
      h += "<tr><td>" + esc(r.image_name || ("#" + r.id)) + "</td><td>" + esc(r.component || "—") +
           "</td><td>" + esc(r.damage_type || "无") + "</td><td>" +
           (r.high_risk ? '<span class="sc-badge hi">高</span>' : '<span class="sc-badge ok">正常</span>') +
           "</td></tr>";
    });
    box.innerHTML = h + "</table>";
  }

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  /* ── 清空 ── */
  $("sc-clear").addEventListener("click", function () {
    lastPayload = null; pendingFile = null;
    $("sc-file").value = "";
    $("sc-analyze").disabled = true; $("sc-export").disabled = true;
    $("sc-drop-text").innerHTML = "拖拽巡检图片到此处<br>或点击选择文件";
    $("sc-imginfo").innerHTML = '<div class="sc-empty" style="grid-column:1/-1">等待上传图片…</div>';
    ["sc-r-level", "sc-r-type", "sc-r-conf"].forEach(function (id) { $(id).textContent = "—"; });
    $("sc-report-kv").innerHTML = ["构件", "损伤位置", "程度/尺寸", "处置建议", "模型", "时间", "报告编号"]
      .map(function (t) { return '<span class="k">' + t + '</span><span class="v">—</span>'; }).join("");
    $("sc-loc").innerHTML = '<div class="sc-empty">暂无损伤定位数据</div>';
    $("sc-dmg-tag").style.display = "none"; $("sc-dmg-dot").style.display = "none";
    farm.contentWindow.postMessage({ type: "wd:damage", hasDamage: false }, "*");
  });

  /* ── 导出（Task 7 提供 /screen/api/export/{id}） ── */
  $("sc-export").addEventListener("click", function () {
    if (lastPayload && lastPayload.record_id) {
      location.href = "/screen/api/export/" + lastPayload.record_id;
    }
  });

  /* ── 3D 标签每帧定位 ── */
  var tagEls = {};
  document.querySelectorAll(".sc-tag[data-anchor]").forEach(function (el) {
    tagEls[el.getAttribute("data-anchor")] = el;
  });
  /* damage 锚点走 #sc-dmg-tag / #sc-dmg-dot，其余按 data-anchor 查找 */
  addEventListener("message", function (e) {
    var m = e.data || {};
    if (m.type !== "wd:labels" || !m.labels) return;
    m.labels.forEach(function (l) {
      var el = tagEls[l.id];
      if (!el) {
        if (l.id !== "damage") return;
        el = $("sc-dmg-tag");
      }
      if (l.id === "damage") {
        el = $("sc-dmg-tag");
        var dot = $("sc-dmg-dot");
        if (el.style.display !== "none") {
          el.style.transform = "translate(" + (l.x + 14) + "px," + (l.y - 10) + "px)";
          if (dot) dot.style.transform = "translate(" + (l.x - 7) + "px," + (l.y - 7) + "px)";
        }
        return;
      }
      el.style.display = l.visible ? "block" : "none";
      el.style.transform = "translate(" + (l.x - el.offsetWidth / 2) + "px," + (l.y - 30) + "px)";
    });
  });
})();
