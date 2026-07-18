(() => {
  const $ = (id) => document.getElementById(id);

  const I18N = {
    zh: {
      tagline: "YouTube 单视频下载",
      settings: "设置",
      videoUrl: "视频链接",
      urlPlaceholder: "粘贴 youtube.com / youtu.be / shorts 链接",
      parse: "解析",
      parsing: "解析中…",
      download: "下载",
      downloading: "下载中…",
      thumbnail: "封面",
      description: "简介",
      quality: "清晰度",
      qBest: "best（最高）",
      qAudio: "仅音频 (mp3)",
      qAudioShort: "仅音频",
      saveDir: "保存目录",
      cancel: "取消",
      history: "下载历史",
      refresh: "刷新",
      defaultSavePath: "默认保存路径",
      defaultQuality: "默认清晰度",
      proxyLabel: "代理地址（如 http://127.0.0.1:7890）",
      useSystemProxy: "使用系统代理（忽略上方手动代理）",
      terms: "我承诺仅将本工具用于个人合法用途，并遵守 YouTube 条款与版权规定",
      save: "保存",
      close: "关闭",
      downloadComplete: "下载完成",
      donateHint: "如果觉得有用，可以请作者喝杯咖啡 ☕",
      donateAlt: "微信收款码",
      openFolder: "打开目录",
      ok: "好的",
      delete: "删除",
      ffmpegOk: "ffmpeg 已就绪（内置或系统），可合并高清音视频。",
      ffmpegMissing:
        "未检测到 ffmpeg：高清合并可能失败。请运行 python scripts/fetch_ffmpeg.py，或 brew/conda 安装。",
      ffmpegMissingShort: "未检测到 ffmpeg：高清合并可能失败，请先获取内置或系统 ffmpeg。",
      noTitle: "（无标题）",
      channel: "频道：{name}",
      duration: "时长：{time}",
      noDescription: "（无简介）",
      pasteUrlFirst: "请先粘贴链接",
      acceptTermsFirst: "请先在设置中确认合法使用承诺",
      parseFirst: "请先解析视频",
      queued: "排队中…",
      donePrefix: "完成：",
      failed: "失败",
      downloadFailed: "下载失败",
      cancelled: "已取消",
      requestFailed: "请求失败 ({status})",
      emptyHistory: "暂无下载记录",
      untitled: "未命名",
      statusSuccess: "成功",
      statusFailed: "失败",
      statusCancelled: "已取消",
      savedTo: "已保存到：{path}",
      downloadDone: "下载已完成。",
      confirmDeleteHistory: "删除该历史记录？",
      confirmDeleteFile: "是否同时删除对应视频文件？\n选「取消」仅删记录。",
    },
    en: {
      tagline: "Single-video YouTube downloader",
      settings: "Settings",
      videoUrl: "Video URL",
      urlPlaceholder: "Paste youtube.com / youtu.be / shorts URL",
      parse: "Parse",
      parsing: "Parsing…",
      download: "Download",
      downloading: "Downloading…",
      thumbnail: "Thumbnail",
      description: "Description",
      quality: "Quality",
      qBest: "best (highest)",
      qAudio: "Audio only (mp3)",
      qAudioShort: "Audio only",
      saveDir: "Save folder",
      cancel: "Cancel",
      history: "Download history",
      refresh: "Refresh",
      defaultSavePath: "Default save path",
      defaultQuality: "Default quality",
      proxyLabel: "Proxy (e.g. http://127.0.0.1:7890)",
      useSystemProxy: "Use system proxy (ignore manual proxy above)",
      terms:
        "I will only use this tool for personal, lawful purposes and comply with YouTube Terms and copyright rules",
      save: "Save",
      close: "Close",
      downloadComplete: "Download complete",
      donateHint: "If you find this useful, buy the author a coffee ☕",
      donateAlt: "WeChat Pay QR code",
      openFolder: "Open folder",
      ok: "OK",
      delete: "Delete",
      ffmpegOk: "ffmpeg is ready (bundled or system) for high-quality merge.",
      ffmpegMissing:
        "ffmpeg not found: run python scripts/fetch_ffmpeg.py, or install via brew/conda.",
      ffmpegMissingShort:
        "ffmpeg not found: high-quality merge may fail. Fetch bundled or system ffmpeg first.",
      noTitle: "(No title)",
      channel: "Channel: {name}",
      duration: "Duration: {time}",
      noDescription: "(No description)",
      pasteUrlFirst: "Please paste a URL first",
      acceptTermsFirst: "Please accept the terms in Settings first",
      parseFirst: "Please parse the video first",
      queued: "Queued…",
      donePrefix: "Done: ",
      failed: "Failed",
      downloadFailed: "Download failed",
      cancelled: "Cancelled",
      requestFailed: "Request failed ({status})",
      emptyHistory: "No download history yet",
      untitled: "Untitled",
      statusSuccess: "Success",
      statusFailed: "Failed",
      statusCancelled: "Cancelled",
      savedTo: "Saved to: {path}",
      downloadDone: "Download finished.",
      confirmDeleteHistory: "Delete this history record?",
      confirmDeleteFile:
        "Also delete the video file?\nChoose Cancel to remove the record only.",
    },
  };

  const state = {
    video: null,
    taskId: null,
    pollTimer: null,
    settings: null,
    lang: "zh",
    lastFfmpegOk: null,
  };

  function t(key, vars = {}) {
    const dict = I18N[state.lang] || I18N.zh;
    let text = dict[key] ?? I18N.zh[key] ?? key;
    Object.entries(vars).forEach(([k, v]) => {
      text = text.replaceAll(`{${k}}`, String(v));
    });
    return text;
  }

  function applyI18n() {
    document.documentElement.lang = state.lang === "en" ? "en" : "zh-CN";
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      const key = el.classList.contains("is-busy")
        ? el.dataset.busyI18n || el.getAttribute("data-i18n")
        : el.getAttribute("data-i18n");
      if (key) el.textContent = t(key);
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      const key = el.getAttribute("data-i18n-placeholder");
      if (key) el.setAttribute("placeholder", t(key));
    });
    document.querySelectorAll("[data-i18n-alt]").forEach((el) => {
      const key = el.getAttribute("data-i18n-alt");
      if (key) el.setAttribute("alt", t(key));
    });
    $("langZh").classList.toggle("active", state.lang === "zh");
    $("langEn").classList.toggle("active", state.lang === "en");

    if (state.lastFfmpegOk != null) {
      $("ffmpegHint").textContent = state.lastFfmpegOk
        ? t("ffmpegOk")
        : t("ffmpegMissing");
    }
    if (state.video) renderPreview(state.video);
    loadHistory();
  }

  async function setLanguage(lang) {
    if (lang !== "zh" && lang !== "en") return;
    state.lang = lang;
    applyI18n();
    try {
      state.settings = await api("/api/settings", {
        method: "PUT",
        body: JSON.stringify({ language: lang }),
      });
    } catch (_) {
      /* keep UI language even if save fails */
    }
  }

  function showError(msg) {
    const el = $("errorMsg");
    if (!msg) {
      el.hidden = true;
      el.textContent = "";
      return;
    }
    el.hidden = false;
    el.textContent = msg;
  }

  function setButtonBusy(btn, busy, busyKey) {
    if (!btn) return;
    if (busy) {
      btn.classList.add("is-busy");
      btn.disabled = true;
      btn.dataset.busyI18n = busyKey;
      btn.setAttribute("aria-busy", "true");
      btn.textContent = t(busyKey);
    } else {
      btn.classList.remove("is-busy");
      delete btn.dataset.busyI18n;
      btn.removeAttribute("aria-busy");
      const key = btn.getAttribute("data-i18n");
      if (key) btn.textContent = t(key);
    }
  }

  async function api(path, options = {}) {
    const res = await fetch(path, {
      headers: { "Content-Type": "application/json", ...(options.headers || {}) },
      ...options,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = data.detail;
      const msg = Array.isArray(detail)
        ? detail.map((x) => x.msg || JSON.stringify(x)).join("; ")
        : detail || data.message || t("requestFailed", { status: res.status });
      throw new Error(msg);
    }
    return data;
  }

  async function loadSettings() {
    state.settings = await api("/api/settings");
    state.lang = state.settings.language === "en" ? "en" : "zh";
    $("downloadDir").value = state.settings.download_dir || "";
    $("quality").value = state.settings.quality || "1080";
    $("setDir").value = state.settings.download_dir || "";
    $("setQuality").value = state.settings.quality || "1080";
    $("setProxy").value = state.settings.proxy || "";
    $("setSystemProxy").checked = !!state.settings.use_system_proxy;
    $("setTerms").checked = !!state.settings.accepted_terms;
    applyI18n();
  }

  async function loadHealth() {
    const h = await api("/api/health");
    state.lastFfmpegOk = !!h.ffmpeg;
    $("ffmpegHint").textContent = h.ffmpeg ? t("ffmpegOk") : t("ffmpegMissing");
  }

  function formatDuration(seconds, fallback) {
    if (seconds != null && Number.isFinite(Number(seconds)) && Number(seconds) >= 0) {
      const s = Math.round(Number(seconds));
      const h = Math.floor(s / 3600);
      const m = Math.floor((s % 3600) / 60);
      const sec = s % 60;
      if (h > 0) {
        return `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
      }
      return `${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}`;
    }
    return fallback || "";
  }

  function renderPreview(video) {
    state.video = video;
    $("preview").hidden = false;
    $("title").textContent = video.title || t("noTitle");
    $("channel").textContent = video.channel
      ? t("channel", { name: video.channel })
      : "";
    const dur = formatDuration(video.duration, video.duration_string);
    $("duration").textContent = dur ? t("duration", { time: dur }) : "";
    $("description").textContent = video.description || t("noDescription");
    $("thumb").src = video.thumbnail || "";
    $("btnDownload").disabled = false;
  }

  async function parseUrl() {
    showError("");
    const url = $("url").value.trim();
    if (!url) {
      showError(t("pasteUrlFirst"));
      return;
    }
    setButtonBusy($("btnParse"), true, "parsing");
    try {
      const data = await api("/api/parse", {
        method: "POST",
        body: JSON.stringify({ url }),
      });
      renderPreview(data.video);
      state.lastFfmpegOk = !!data.ffmpeg;
      if (!data.ffmpeg) {
        $("ffmpegHint").textContent = t("ffmpegMissingShort");
      } else {
        $("ffmpegHint").textContent = t("ffmpegOk");
      }
    } catch (e) {
      showError(e.message);
      $("preview").hidden = true;
      $("btnDownload").disabled = true;
    } finally {
      setButtonBusy($("btnParse"), false);
      $("btnParse").disabled = false;
    }
  }

  function stopPoll() {
    if (state.pollTimer) {
      clearInterval(state.pollTimer);
      state.pollTimer = null;
    }
  }

  function setProgress(percent, text) {
    $("progressWrap").hidden = false;
    $("progressFill").style.width = `${Math.max(0, Math.min(100, percent || 0))}%`;
    $("progressText").textContent = text;
  }

  function formatSpeed(bps) {
    if (!bps) return "";
    const mb = bps / 1024 / 1024;
    if (mb >= 1) return `${mb.toFixed(1)} MB/s`;
    return `${(bps / 1024).toFixed(0)} KB/s`;
  }

  async function pollTask(taskId) {
    try {
      const tsk = await api(`/api/tasks/${taskId}`);
      const p = tsk.progress || {};
      const pct = p.percent || 0;
      if (tsk.status === "downloading" || tsk.status === "queued") {
        const speed = formatSpeed(p.speed);
        const eta = p.eta != null ? ` ETA ${p.eta}s` : "";
        setProgress(pct, `${pct}% ${speed}${eta}`.trim());
        $("btnCancel").hidden = false;
      } else if (tsk.status === "success") {
        stopPoll();
        setProgress(100, `${t("donePrefix")}${tsk.path || ""}`);
        $("btnCancel").hidden = true;
        setButtonBusy($("btnDownload"), false);
        $("btnDownload").disabled = false;
        await loadHistory();
        showDoneDialog(tsk.path || "");
      } else if (tsk.status === "failed") {
        stopPoll();
        setProgress(pct, t("failed"));
        showError(tsk.error || t("downloadFailed"));
        $("btnCancel").hidden = true;
        setButtonBusy($("btnDownload"), false);
        $("btnDownload").disabled = false;
        await loadHistory();
      } else if (tsk.status === "cancelled") {
        stopPoll();
        setProgress(0, t("cancelled"));
        $("btnCancel").hidden = true;
        setButtonBusy($("btnDownload"), false);
        $("btnDownload").disabled = false;
        await loadHistory();
      }
    } catch (e) {
      stopPoll();
      showError(e.message);
      setButtonBusy($("btnDownload"), false);
      $("btnDownload").disabled = false;
    }
  }

  async function startDownload() {
    showError("");
    if (!state.settings?.accepted_terms) {
      showError(t("acceptTermsFirst"));
      $("settingsDialog").showModal();
      return;
    }
    const url = $("url").value.trim();
    if (!url || !state.video) {
      showError(t("parseFirst"));
      return;
    }
    setButtonBusy($("btnDownload"), true, "downloading");
    $("btnCancel").hidden = true;
    setProgress(0, t("queued"));
    try {
      const data = await api("/api/download", {
        method: "POST",
        body: JSON.stringify({
          url,
          quality: $("quality").value,
          download_dir: $("downloadDir").value.trim() || undefined,
          title: state.video.title || "",
        }),
      });
      state.taskId = data.task_id;
      $("btnCancel").hidden = false;
      stopPoll();
      state.pollTimer = setInterval(() => pollTask(state.taskId), 800);
      pollTask(state.taskId);
    } catch (e) {
      showError(e.message);
      setButtonBusy($("btnDownload"), false);
      $("btnDownload").disabled = false;
    }
  }

  async function cancelDownload() {
    if (!state.taskId) return;
    try {
      await api(`/api/tasks/${state.taskId}/cancel`, { method: "POST" });
    } catch (e) {
      showError(e.message);
    }
  }

  function showDoneDialog(filePath) {
    $("donePath").textContent = filePath
      ? t("savedTo", { path: filePath })
      : t("downloadDone");
    $("btnOpenDonePath").hidden = !filePath;
    $("btnOpenDonePath").dataset.path = filePath || "";
    $("doneDialog").showModal();
  }

  function statusBadge(status) {
    const map = {
      success: t("statusSuccess"),
      failed: t("statusFailed"),
      cancelled: t("statusCancelled"),
    };
    return `<span class="badge ${status}">${map[status] || status}</span>`;
  }

  async function loadHistory() {
    const data = await api("/api/history");
    const box = $("historyList");
    if (!data.items?.length) {
      box.innerHTML = `<p class="empty">${escapeHtml(t("emptyHistory"))}</p>`;
      return;
    }
    const locale = state.lang === "en" ? "en-US" : "zh-CN";
    box.innerHTML = data.items
      .map((item) => {
        const time = item.created_at
          ? new Date(item.created_at * 1000).toLocaleString(locale)
          : "";
        const path = item.path || "";
        return `
        <div class="history-item" data-id="${item.id}">
          <div>
            <p class="title">${escapeHtml(item.title || t("untitled"))} ${statusBadge(item.status)}</p>
            <p class="sub">${escapeHtml(time)}${path ? " · " + escapeHtml(path) : ""}</p>
            ${item.error ? `<p class="sub">${escapeHtml(item.error)}</p>` : ""}
          </div>
          <div class="history-actions">
            ${path ? `<button type="button" class="btn ghost btn-open" data-path="${escapeAttr(path)}">${escapeHtml(t("openFolder"))}</button>` : ""}
            <button type="button" class="btn ghost danger btn-del" data-id="${item.id}">${escapeHtml(t("delete"))}</button>
          </div>
        </div>`;
      })
      .join("");
  }

  function escapeHtml(s) {
    return String(s)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }
  function escapeAttr(s) {
    return escapeHtml(s).replaceAll("'", "&#39;");
  }

  $("btnParse").addEventListener("click", parseUrl);
  $("btnDownload").addEventListener("click", startDownload);
  $("btnCancel").addEventListener("click", cancelDownload);
  $("btnRefreshHistory").addEventListener("click", loadHistory);
  $("btnSettings").addEventListener("click", () => $("settingsDialog").showModal());
  $("btnCloseSettings").addEventListener("click", () => $("settingsDialog").close());
  $("btnCloseDone").addEventListener("click", () => $("doneDialog").close());
  $("langZh").addEventListener("click", () => setLanguage("zh"));
  $("langEn").addEventListener("click", () => setLanguage("en"));
  $("btnOpenDonePath").addEventListener("click", async () => {
    const path = $("btnOpenDonePath").dataset.path;
    if (!path) return;
    try {
      await api("/api/open-path", {
        method: "POST",
        body: JSON.stringify({ path }),
      });
    } catch (err) {
      showError(err.message);
    }
  });

  $("url").addEventListener("keydown", (e) => {
    if (e.key === "Enter") parseUrl();
  });

  $("historyList").addEventListener("click", async (e) => {
    const openBtn = e.target.closest(".btn-open");
    const delBtn = e.target.closest(".btn-del");
    if (openBtn) {
      try {
        await api("/api/open-path", {
          method: "POST",
          body: JSON.stringify({ path: openBtn.dataset.path }),
        });
      } catch (err) {
        showError(err.message);
      }
    }
    if (delBtn) {
      if (!confirm(t("confirmDeleteHistory"))) return;
      const alsoFile = confirm(t("confirmDeleteFile"));
      try {
        await api("/api/history/delete", {
          method: "POST",
          body: JSON.stringify({ id: delBtn.dataset.id, delete_file: alsoFile }),
        });
        await loadHistory();
      } catch (err) {
        showError(err.message);
      }
    }
  });

  $("settingsForm").addEventListener("submit", async (e) => {
    e.preventDefault();
    try {
      state.settings = await api("/api/settings", {
        method: "PUT",
        body: JSON.stringify({
          download_dir: $("setDir").value.trim(),
          quality: $("setQuality").value,
          proxy: $("setProxy").value.trim(),
          use_system_proxy: $("setSystemProxy").checked,
          accepted_terms: $("setTerms").checked,
          language: state.lang,
        }),
      });
      $("downloadDir").value = state.settings.download_dir;
      $("quality").value = state.settings.quality;
      $("settingsDialog").close();
    } catch (err) {
      showError(err.message);
    }
  });

  $("url").addEventListener("paste", () => {
    setTimeout(() => {
      if ($("url").value.trim()) parseUrl();
    }, 50);
  });

  Promise.all([loadSettings(), loadHealth(), loadHistory()]).catch((e) =>
    showError(e.message)
  );
})();
