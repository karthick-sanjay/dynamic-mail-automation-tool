(function () {
  "use strict";

  // ── DOM refs ──────────────────────────────────────────────────────────────
  const form         = document.getElementById("campaignForm");
  const submitBtn    = document.getElementById("submitBtn");
  const previewBtn   = document.getElementById("previewBtn");
  const toast        = document.getElementById("toast");
  const charCount    = document.getElementById("charCount");
  const msgField     = document.getElementById("message");
  const togglePass   = document.querySelector(".toggle-pass");
  const appPwInput   = document.getElementById("appPassword");
  const resultPanel  = document.getElementById("resultPanel");
  const resultTitle  = document.getElementById("resultTitle");
  const resultIcon   = document.getElementById("resultIcon");
  const resultBody   = document.getElementById("resultBody");

  const logoDropzone   = document.getElementById("logoDropzone");
  const logoFileInput  = document.getElementById("logoFileInput");
  const browseBtn      = document.getElementById("browseBtn");
  const dropzoneIdle   = document.getElementById("dropzoneIdle");
  const dropzonePreview= document.getElementById("dropzonePreview");
  const logoPreviewImg = document.getElementById("logoPreviewImg");
  const logoFileName   = document.getElementById("logoFileName");
  const removeLogoBtn  = document.getElementById("removeLogoBtn");
  const logoBase64     = document.getElementById("logoBase64");
  const previewWrap    = document.getElementById("emailPreviewWrap");
  const previewFrame   = document.getElementById("emailPreviewFrame");

  // ── Datetime min ──────────────────────────────────────────────────────────
  (function () {
    const dt  = document.getElementById("scheduledTime");
    const now = new Date(Date.now() + 5 * 60000);
    dt.min = dt.value = new Date(now - now.getTimezoneOffset() * 60000)
      .toISOString().slice(0, 16);
  })();

  // ── Char counter ──────────────────────────────────────────────────────────
  msgField.addEventListener("input", () => {
    charCount.textContent = `${msgField.value.length} chars`;
    if (previewWrap.style.display !== "none") updatePreview();
  });

  // ── Toggle password ───────────────────────────────────────────────────────
  togglePass.addEventListener("click", () => {
    const show = appPwInput.type === "password";
    appPwInput.type = show ? "text" : "password";
    togglePass.querySelector(".eye-icon").textContent = show ? "🙈" : "👁";
  });

  // ── Logo file upload ──────────────────────────────────────────────────────
  function handleLogoFile(file) {
    if (!file || !file.type.startsWith("image/")) {
      showToast("Please upload an image file (PNG, JPG, SVG, WEBP).", "error");
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      showToast("Logo file must be under 2 MB.", "error");
      return;
    }
    const reader = new FileReader();
    reader.onload = (e) => {
      const dataUrl = e.target.result;
      logoBase64.value      = dataUrl;          // stored as base64 data URL
      logoPreviewImg.src    = dataUrl;
      logoFileName.textContent = file.name;
      dropzoneIdle.style.display    = "none";
      dropzonePreview.style.display = "flex";
      logoDropzone.style.borderStyle = "solid";
      logoDropzone.style.borderColor = "var(--accent3)";
      if (previewWrap.style.display !== "none") updatePreview();
    };
    reader.readAsDataURL(file);
  }

  function clearLogo() {
    logoBase64.value      = "";
    logoFileInput.value   = "";
    logoPreviewImg.src    = "";
    logoFileName.textContent = "";
    dropzoneIdle.style.display    = "block";
    dropzonePreview.style.display = "none";
    logoDropzone.style.borderStyle = "dashed";
    logoDropzone.style.borderColor = "";
    if (previewWrap.style.display !== "none") updatePreview();
  }

  // Click to browse — guard against null (elements inside hidden divs)
  if (browseBtn) browseBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    logoFileInput.click();
  });
  if (logoDropzone) logoDropzone.addEventListener("click", () => {
    if (!logoBase64.value) logoFileInput.click();
  });
  if (logoFileInput) logoFileInput.addEventListener("change", () => {
    if (logoFileInput.files[0]) handleLogoFile(logoFileInput.files[0]);
  });

  // Remove logo
  if (removeLogoBtn) removeLogoBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    clearLogo();
  });

  // Drag and drop
  if (logoDropzone) {
    logoDropzone.addEventListener("dragover", (e) => {
      e.preventDefault();
      logoDropzone.classList.add("drag-over");
    });
    logoDropzone.addEventListener("dragleave", () => {
      logoDropzone.classList.remove("drag-over");
    });
    logoDropzone.addEventListener("drop", (e) => {
      e.preventDefault();
      logoDropzone.classList.remove("drag-over");
      const file = e.dataTransfer.files[0];
      if (file) handleLogoFile(file);
    });
  }

  // ── Live email preview ────────────────────────────────────────────────────
  function getBranding() {
    return {
      brand_name:   document.getElementById("brandName").value.trim() || "Newsletter",
      logo_url:     logoBase64.value || "",
      accent_color: "#b8976a",  // fixed warm gold — matches fixed charcoal header
      website_url:  document.getElementById("websiteUrl").value.trim(),
      twitter:      document.getElementById("twitter").value.trim(),
      instagram:    document.getElementById("instagram").value.trim(),
      linkedin:     document.getElementById("linkedin").value.trim(),
      facebook:     document.getElementById("facebook").value.trim(),
    };
  }

  function buildPreviewHTML(message, branding) {
    const accent    = "#b8976a";   // fixed warm gold accent
    const HEADER_BG = "#1c1c1e";   // fixed charcoal header
    const STRIP_BG  = "#f5f3ef";
    const STRIP_TXT = "#8c7355";

    const brandName  = branding.brand_name  || "Newsletter";
    const logoUrl    = branding.logo_url;
    const websiteUrl = branding.website_url;

    // Header block — large logo + brand name beneath, or big serif text
    let logoBlock;
    if (logoUrl) {
      logoBlock =
        `<img src="${logoUrl}" alt="${brandName}"
             style="max-height:110px;max-width:300px;object-fit:contain;
                    display:block;margin:0 auto 22px auto;">`
        + `<span style="display:block;text-align:center;font-family:Georgia,serif;
                        font-size:11px;letter-spacing:7px;text-transform:uppercase;
                        color:rgba(255,255,255,0.5);">${brandName}</span>`;
    } else {
      logoBlock =
        `<span style="display:block;text-align:center;font-family:Georgia,serif;
                      font-size:34px;font-weight:400;letter-spacing:8px;
                      text-transform:uppercase;color:#ffffff;line-height:1.15;">${brandName}</span>`
        + `<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:18px;"><tr>`
        + `<td style="border-top:1px solid rgba(255,255,255,0.15);font-size:0;">&nbsp;</td>`
        + `<td align="center" style="padding:0 14px;color:rgba(255,255,255,0.28);font-size:9px;">&#10022;</td>`
        + `<td style="border-top:1px solid rgba(255,255,255,0.15);font-size:0;">&nbsp;</td>`
        + `</tr></table>`;
    }
    if (websiteUrl) {
      logoBlock = `<a href="${websiteUrl}" style="text-decoration:none;">${logoBlock}</a>`;
    }

    // Social links
    const socials = [];
    const pf = {Twitter:branding.twitter, Instagram:branding.instagram, LinkedIn:branding.linkedin, Facebook:branding.facebook};
    for (const [label, val] of Object.entries(pf)) {
      if (val) {
        const href = val.startsWith("http") ? val : `https://${label.toLowerCase()}.com/${val.replace("@","")}`;
        socials.push(`<a href="${href}" style="color:#aaa;text-decoration:none;font-size:10px;letter-spacing:0.15em;text-transform:uppercase;font-family:Arial,sans-serif;margin:0 8px;">${label}</a>`);
      }
    }
    const socialRow = socials.length
      ? `<tr><td align="center" style="padding:0 0 14px;">${socials.join('<span style="color:#ddd;">&#183;</span>')}</td></tr>`
      : "";

    const websiteRow = websiteUrl
      ? `<tr><td align="center" style="padding:0 0 12px;"><a href="${websiteUrl}"
           style="color:${accent};font-size:11px;text-decoration:none;
                  letter-spacing:0.08em;font-family:Arial,sans-serif;">
           ${websiteUrl.replace(/https?:\/\//,"").replace(/\/$/,"")}</a></td></tr>`
      : "";

    const msg   = message || "Your message will appear here.";
    const paras = msg.split("\n\n").map(p =>
      `<p style="margin:0 0 22px 0;color:#2a2a2a;font-size:16px;line-height:1.9;font-family:Georgia,serif;">${p.split("\n").join("<br>")}</p>`
    ).join("");

    return `<!DOCTYPE html><html><head><meta charset="UTF-8">
<style>body{margin:0;padding:0;background:#eceae6;}</style></head>
<body style="background:#eceae6;padding:28px 0;font-family:Georgia,serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" border="0"
  style="max-width:560px;width:100%;background:#fff;
         box-shadow:0 12px 50px rgba(0,0,0,0.13);">

  <tr><td style="background:${accent};height:4px;font-size:0;">&nbsp;</td></tr>

  <tr><td align="center" style="background:${HEADER_BG};padding:52px 44px 48px;">
    ${logoBlock}
  </td></tr>

  <tr><td style="background:#2e2e32;height:1px;font-size:0;">&nbsp;</td></tr>

  <tr><td align="center" style="background:${STRIP_BG};padding:12px 40px;
    font-family:Arial,sans-serif;font-size:10px;letter-spacing:0.22em;
    text-transform:uppercase;color:${STRIP_TXT};">
    ${brandName}&nbsp;&nbsp;&#183;&nbsp;&nbsp;Newsletter
  </td></tr>

  <tr><td style="padding:44px 52px 36px;background:#fff;">${paras}</td></tr>

  <tr><td align="center" style="padding:0 52px 32px;background:#fff;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0"><tr>
      <td style="border-top:1px solid #e4e3df;font-size:0;">&nbsp;</td>
      <td align="center" style="padding:0 14px;color:#c8c5bc;font-size:13px;letter-spacing:6px;white-space:nowrap;">&#10022; &#10022; &#10022;</td>
      <td style="border-top:1px solid #e4e3df;font-size:0;">&nbsp;</td>
    </tr></table>
  </td></tr>

  <tr><td style="background:#f7f6f3;padding:28px 40px 32px;border-top:1px solid #edecea;">
    <table width="100%" cellpadding="0" cellspacing="0" border="0">
      <tr><td align="center" style="padding:0 0 16px;">
        <span style="font-family:Georgia,serif;font-size:13px;letter-spacing:4px;color:#aaa;text-transform:uppercase;">${brandName}</span>
      </td></tr>
      ${websiteRow}${socialRow}
      <tr><td style="border-top:1px solid #e8e7e3;font-size:0;">&nbsp;</td></tr>
      <tr><td align="center" style="padding:16px 0 0;color:#c0c0c0;font-size:11px;line-height:1.8;font-family:Arial,sans-serif;">
        You received this because you subscribed to <strong style="color:#999;">${brandName}</strong>.<br>
        Reply &#8220;unsubscribe&#8221; to opt out.
      </td></tr>
    </table>
  </td></tr>

</table>
<table width="560" cellpadding="0" cellspacing="0" border="0" style="max-width:560px;margin-top:18px;">
  <tr><td align="center" style="color:#b8b5ae;font-size:10px;letter-spacing:0.14em;text-transform:uppercase;font-family:Arial,sans-serif;">Sent with MailForge</td></tr>
</table>
</td></tr></table>
</body></html>`;
  }

  function updatePreview() {
    const html = buildPreviewHTML(msgField.value, getBranding());
    const doc  = previewFrame.contentDocument || previewFrame.contentWindow.document;
    doc.open(); doc.write(html); doc.close();
  }

  previewBtn.addEventListener("click", () => {
    const isOpen = previewWrap.style.display !== "none";
    previewWrap.style.display = isOpen ? "none" : "block";
    previewBtn.querySelector("span").textContent = isOpen ? "👁 Preview Email" : "✕ Close Preview";
    if (!isOpen) updatePreview();
  });

  // Update preview when branding fields change
  ["brandName","websiteUrl","twitter","instagram","linkedin","facebook"].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.addEventListener("input", () => {
      if (previewWrap.style.display !== "none") updatePreview();
    });
  });

  // ── Step dots ─────────────────────────────────────────────────────────────
  const stepDots = document.querySelectorAll(".step");
  function activateStep(n) {
    stepDots.forEach((s, i) => {
      s.classList.remove("active","done");
      if (i + 1 < n)  s.classList.add("done");
      if (i + 1 === n) s.classList.add("active");
    });
  }
  document.querySelectorAll(".form-section").forEach((sec, idx) => {
    sec.querySelectorAll("input,textarea").forEach(el =>
      el.addEventListener("focus", () => activateStep(idx + 1))
    );
  });

  // ── Validation ────────────────────────────────────────────────────────────
  function setError(id, msg) {
    const el    = document.getElementById("err-" + id);
    const input = document.getElementById(id);
    if (el)    el.textContent = msg;
    if (input) input.classList.toggle("error", !!msg);
  }
  function clearErrors() {
    document.querySelectorAll(".field-error").forEach(e => e.textContent = "");
    document.querySelectorAll("input,textarea").forEach(e => e.classList.remove("error"));
  }
  function isValidEmail(e) { return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(e.trim()); }

  function validateForm(d) {
    let ok = true;
    if (!d.gmail_address)                   { setError("gmailAddress","Gmail address is required."); ok=false; }
    else if (!isValidEmail(d.gmail_address)) { setError("gmailAddress","Enter a valid Gmail address."); ok=false; }
    if (!d.app_password)                    { setError("appPassword","App Password is required."); ok=false; }
    else if (d.app_password.replace(/\s/g,"").length < 16)
                                            { setError("appPassword","App Password must be 16 characters."); ok=false; }
    if (!d.sheet_url)                       { setError("sheetUrl","Google Sheet URL is required."); ok=false; }
    else if (!d.sheet_url.includes("docs.google.com/spreadsheets"))
                                            { setError("sheetUrl","Enter a valid Google Sheets URL."); ok=false; }
    if (!d.subject.trim())                  { setError("subject","Subject line is required."); ok=false; }
    if (!d.message.trim())                  { setError("message","Message body is required."); ok=false; }
    if (!d.scheduled_time)                  { setError("scheduledTime","Please pick a date and time."); ok=false; }
    else if (new Date(d.scheduled_time) <= new Date())
                                            { setError("scheduledTime","Scheduled time must be in the future."); ok=false; }
    return ok;
  }

  // ── Toast ─────────────────────────────────────────────────────────────────
  let toastTimer;
  function showToast(msg, type="success", ms=6000) {
    clearTimeout(toastTimer);
    toast.textContent = msg;
    toast.className   = `toast ${type} show`;
    toastTimer = setTimeout(() => { toast.className = "toast"; }, ms);
  }

  // ── Result panel ──────────────────────────────────────────────────────────
  function showResult(type, title, lines) {
    resultPanel.style.display = "block";
    resultPanel.className     = `result-panel ${type}`;
    resultIcon.textContent    = type==="success" ? "✓" : type==="error" ? "✗" : "⚠";
    resultTitle.textContent   = title;
    resultBody.innerHTML = lines.map(l => {
      if (l.startsWith("✓")) return `<span class="ok">${l}</span>`;
      if (l.startsWith("✗")) return `<span class="fail">${l}</span>`;
      return `<span class="info">${l}</span>`;
    }).join("\n");
    resultPanel.scrollIntoView({ behavior:"smooth", block:"nearest" });
  }

  // ── Collect form data ─────────────────────────────────────────────────────
  function getFormData() {
    return {
      gmail_address:  document.getElementById("gmailAddress").value.trim(),
      app_password:   document.getElementById("appPassword").value.trim(),
      sheet_url:      document.getElementById("sheetUrl").value.trim(),
      subject:        document.getElementById("subject").value.trim() || "Newsletter",
      message:        msgField.value.trim() || "This is a test email.",
      scheduled_time: document.getElementById("scheduledTime").value,
      ...getBranding(),
    };
  }

  // ── Schedule ──────────────────────────────────────────────────────────────
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    clearErrors();
    const data = getFormData();
    if (!validateForm(data)) return;

    submitBtn.disabled = true;
    submitBtn.classList.add("loading");

    try {
      const res  = await fetch("/api/schedule", {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify(data),
      });
      const json = await res.json();

      if (res.ok && json.success) {
        showToast("✓ " + json.message, "success", 8000);
        form.reset();
        clearErrors();
        activateStep(1);
        resultPanel.style.display = "none";
        previewWrap.style.display = "none";
        charCount.textContent = "0 chars";
        clearLogo();
        const dt  = document.getElementById("scheduledTime");
        const now = new Date(Date.now() + 5 * 60000);
        dt.value  = new Date(now - now.getTimezoneOffset()*60000).toISOString().slice(0,16);
      } else {
        showToast("✗ " + (json.error||"Unknown error"), "error", 8000);
      }
    } catch {
      showToast("✗ Could not reach the server.", "error", 8000);
    } finally {
      submitBtn.disabled = false;
      submitBtn.classList.remove("loading");
    }
  });

  // ── Entrance animation ────────────────────────────────────────────────────
  document.querySelectorAll(".form-section").forEach((sec, i) => {
    sec.style.cssText = `opacity:0;transform:translateY(16px);
      transition:opacity 0.5s ${0.5+i*0.1}s ease,transform 0.5s ${0.5+i*0.1}s ease`;
    requestAnimationFrame(() => {
      sec.style.opacity = 1;
      sec.style.transform = "translateY(0)";
    });
  });
})();