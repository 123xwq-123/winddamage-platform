/* 批量检测大屏页：多选上传、整批分析、进度表、CSV 导出 */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var files = [];
  var results = [];

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  /* ── 选择文件 ── */
  var drop = $("drop");
  drop.addEventListener("click", function () { $("files").click(); });
  $("files").addEventListener("change", function () { addFiles(this.files); });
  ["dragenter", "dragover"].forEach(function (ev) {
    drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.add("drag"); });
  });
  ["dragleave", "drop"].forEach(function (ev) {
    drop.addEventListener(ev, function (e) { e.preventDefault(); drop.classList.remove("drag"); });
  });
  drop.addEventListener("drop", function (e) { addFiles(e.dataTransfer.files); });

  function addFiles(list) {
    Array.prototype.forEach.call(list || [], function (f) {
      if (/^image\//.test(f.type)) files.push(f);
    });
    $("drop-text").innerHTML = "已选择 <b>" + files.length + "</b> 张图片";
    var h = "";
    files.forEach(function (f, i) { h += esc(f.name) + "（" + (f.size / 1024).toFixed(0) + " KB）<br>"; });
    $("filelist").innerHTML = h;
    $("filelist").hidden = false;
    $("run").disabled = !files.length;
  }

  /* ── 批量分析 ── */
  $("run").addEventListener("click", function () {
    if (!files.length) return;
    var btn = this;
    btn.disabled = true; btn.textContent = "⏳ 批量分析中…";
    $("result").innerHTML = '<div class="sc-empty">上传并分析中，请稍候（' + files.length + " 张）…</div>";
    var fd = new FormData();
    files.forEach(function (f) { fd.append("files", f); });
    fetch("/screen/api/batch", { method: "POST", body: fd })
      .then(function (r) { if (!r.ok) throw new Error("HTTP " + r.status); return r.json(); })
      .then(function (d) { results = d.results || []; render(d); })
      .catch(function (e) { $("result").innerHTML = '<div class="sc-empty">批量分析失败：' + esc(e.message) + "</div>"; })
      .finally(function () { btn.textContent = "▶ 开始批量分析"; btn.disabled = false; });
  });

  function render(d) {
    $("sum").hidden = false;
    $("sum-total").textContent = d.total || results.length;
    $("sum-ok").textContent = d.ok_count != null ? d.ok_count : results.filter(function (r) { return r.ok; }).length;
    $("sum-high").textContent = d.high_risk || 0;
    $("sum-fail").textContent = results.filter(function (r) { return !r.ok; }).length;
    var h = '<table class="sc-mini"><tr><th>图片</th><th>构件</th><th>损伤类型</th><th>优先级</th><th>耗时</th><th>状态</th></tr>';
    results.forEach(function (r) {
      if (r.ok) {
        h += "<tr><td>" + esc(r.filename) + "</td><td>" + esc(r.component || "—") + "</td><td>" +
          esc(r.damage_type || "无") + "</td><td>" + esc(r.priority || "—") + "</td><td>" +
          (r.infer_time != null ? Number(r.infer_time).toFixed(1) + "s" : "—") + "</td><td>" +
          (r.high_risk ? '<span class="sc-badge hi">高风险</span>' : '<span class="sc-badge ok">正常</span>') +
          "</td></tr>";
      } else {
        h += '<tr><td>' + esc(r.filename) + '</td><td colspan="4" class="err">' + esc(r.error || "失败") +
          '</td><td><span class="sc-badge hi">失败</span></td></tr>';
      }
    });
    $("result").innerHTML = h + "</table>";
    $("export").disabled = !results.length;
  }

  /* ── CSV 导出（客户端生成，含 BOM 便于 Excel 识别） ── */
  $("export").addEventListener("click", function () {
    var rows = [["图片", "构件", "损伤类型", "优先级", "风险", "耗时(s)", "记录ID", "错误"]];
    results.forEach(function (r) {
      rows.push([r.filename, r.component || "", r.damage_type || "", r.priority || "",
                 r.ok ? (r.high_risk ? "高" : "正常") : "", r.infer_time || "", r.record_id || "", r.error || ""]);
    });
    var csv = "\uFEFF" + rows.map(function (row) {
      return row.map(function (c) { return '"' + String(c).replace(/"/g, '""') + '"'; }).join(",");
    }).join("\r\n");
    var a = document.createElement("a");
    a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    a.download = "batch_" + new Date().toISOString().slice(0, 10) + ".csv";
    a.click();
    URL.revokeObjectURL(a.href);
  });
})();
