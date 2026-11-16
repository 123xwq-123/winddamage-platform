/* 历史记录大屏页：筛选/分页/详情抽屉/备注/删除 */
(function () {
  "use strict";
  var $ = function (id) { return document.getElementById(id); };
  var page = 1, pageSize = 15, total = 0, lastDetail = null;

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function load() {
    var q = new URLSearchParams({
      page: page, page_size: pageSize,
      search: $("f-search").value.trim(),
      risk: $("f-risk").value,
      date_from: $("f-from").value, date_to: $("f-to").value,
      sort: $("f-sort").value,
    });
    fetch("/screen/api/records?" + q).then(function (r) { return r.json(); })
      .then(function (d) {
        total = d.total || 0;
        $("f-total").textContent = "共 " + total + " 条";
        var pages = Math.max(1, Math.ceil(total / pageSize));
        $("pg-info").textContent = page + " / " + pages;
        $("pg-prev").disabled = page <= 1;
        $("pg-next").disabled = page >= pages;
        renderRows(d.rows || []);
      }).catch(function () { renderRows([]); });
  }

  function renderRows(rows) {
    if (!rows.length) {
      $("rows").innerHTML = '<tr><td colspan="10"><div class="sc-empty">无匹配记录</div></td></tr>';
      return;
    }
    var h = "";
    rows.forEach(function (r) {
      h += "<tr><td>" + r.id + "</td><td>" + esc(r.timestamp) + "</td><td>" + esc(r.image_name) +
        "</td><td>" + esc(r.component || "—") + "</td><td>" + esc(r.damage_type || "无") +
        '</td><td>' + esc(r.priority || "—") + "</td><td>" +
        (r.high_risk ? '<span class="sc-badge hi">高风险</span>' : '<span class="sc-badge ok">正常</span>') +
        "</td><td>" + (r.infer_time != null ? Number(r.infer_time).toFixed(1) + "s" : "—") +
        "</td><td>" + esc(r.note || "") +
        '</td><td><span class="sc-link" data-act="detail" data-id="' + r.id + '">详情</span>' +
        '<span class="sc-link danger" data-act="del" data-id="' + r.id + '">删除</span></td></tr>';
    });
    $("rows").innerHTML = h;
  }

  $("rows").addEventListener("click", function (e) {
    var t = e.target;
    if (!t.dataset || !t.dataset.act) return;
    var id = parseInt(t.dataset.id, 10);
    if (t.dataset.act === "detail") openDetail(id);
    if (t.dataset.act === "del" && confirm("确认删除记录 #" + id + "？")) {
      fetch("/screen/api/records/" + id, { method: "DELETE" })
        .then(function (r) { if (!r.ok) throw 0; load(); });
    }
  });

  /* ── 详情抽屉 ── */
  function openDetail(id) {
    fetch("/screen/api/records/" + id).then(function (r) {
      if (!r.ok) throw new Error("HTTP " + r.status);
      return r.json();
    }).then(function (d) {
      lastDetail = d;
      $("drawer-title").textContent = "#" + d.id + " · " + (d.image_name || "");
      $("note-input").value = d.note || "";
      var rep = d.json_report || {};
      var h = "";
      if (d.image_file_id) {
        h += '<img src="/history/' + d.id + '/image" alt="" style="max-width:100%;max-height:300px;border-radius:6px;margin-bottom:14px;border:1px solid rgba(103,232,249,.3)">';
      }
      Object.keys(rep).forEach(function (sec) {
        h += '<div class="sc-sec"><div class="t">' + esc(sec) + "</div>";
        var obj = rep[sec] || {};
        h += '<div class="sc-kv">' + Object.keys(obj).map(function (k) {
          return '<span class="k">' + esc(k) + '</span><span class="v">' + esc(obj[k]) + "</span>";
        }).join("") + "</div></div>";
      });
      $("drawer-body").innerHTML = h || '<div class="sc-empty">无报告内容</div>';
      $("drawer").classList.add("open");
    }).catch(function (e) { alert("加载详情失败：" + e.message); });
  }

  $("drawer-mask").addEventListener("click", closeDrawer);
  $("drawer-close").addEventListener("click", closeDrawer);
  function closeDrawer() { $("drawer").classList.remove("open"); }

  $("note-save").addEventListener("click", function () {
    if (!lastDetail) return;
    fetch("/screen/api/records/" + lastDetail.id + "/note", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ note: $("note-input").value }),
    }).then(function (r) {
      if (!r.ok) throw 0;
      closeDrawer(); load();
    });
  });

  /* ── 筛选/分页 ── */
  $("f-go").addEventListener("click", function () { page = 1; load(); });
  ["f-search"].forEach(function (id) {
    $(id).addEventListener("keydown", function (e) { if (e.key === "Enter") { page = 1; load(); } });
  });
  $("pg-prev").addEventListener("click", function () { if (page > 1) { page--; load(); } });
  $("pg-next").addEventListener("click", function () { page++; load(); });

  load();
})();
