const root = document.getElementById("editor-root");
if (!root) {
    throw new Error("편집기 루트를 찾을 수 없습니다.");
}

const getCsrfToken = () => {
    const hiddenInput = document.querySelector('#csrf-form input[name="csrfmiddlewaretoken"]');
    return hiddenInput ? hiddenInput.value : "";
};

const defaultTheme = (() => {
    try {
        const raw = document.body.dataset.defaultTheme ?? "{}";
        return JSON.parse(raw);
    } catch (error) {
        console.error("기본 테마를 불러오는 중 오류", error);
        return {};
    }
})();

const state = {
    theme: { ...defaultTheme },
    isPreviewDirty: true,
};

const elements = {
    title: document.getElementById("input-title"),
    font: document.getElementById("select-font"),
    fontSize: document.getElementById("range-font-size"),
    background: document.getElementById("color-background"),
    textColor: document.getElementById("color-text"),
    headingColor: document.getElementById("color-heading"),
    accentColor: document.getElementById("color-accent"),
    blockquoteBg: document.getElementById("color-blockquote-bg"),
    blockquoteBorder: document.getElementById("color-blockquote-border"),
    codeBg: document.getElementById("color-code-bg"),
    codeText: document.getElementById("color-code-text"),
    listStyle: document.getElementById("select-list"),
    orderedListStyle: document.getElementById("select-olist"),
    pagePadding: document.getElementById("number-padding"),
    lineHeight: document.getElementById("number-line-height"),
    shadow: document.getElementById("select-shadow"),
    markdown: document.getElementById("markdown-input"),
    previewStyle: document.getElementById("preview-style"),
    previewOutput: document.getElementById("preview-output"),
    previewStatus: document.getElementById("preview-status"),
    btnPreview: document.getElementById("btn-preview"),
    btnDownload: document.getElementById("btn-download"),
    loadingTemplate: document.getElementById("loading-indicator"),
};

const urls = {
    preview: root.dataset.previewUrl,
    pdf: root.dataset.pdfUrl,
};

const ensureValue = (value, fallback) => (value === undefined || value === null ? fallback : value);

const setControlInitialValues = () => {
    const theme = state.theme;
    if (elements.title) elements.title.value = ensureValue(theme.title, "Untitled");
    if (elements.font && theme.fontFamily) elements.font.value = theme.fontFamily;
    if (elements.fontSize) elements.fontSize.value = ensureValue(theme.baseFontSize, 16);
    if (elements.background) elements.background.value = ensureValue(theme.backgroundColor, "#ffffff");
    if (elements.textColor) elements.textColor.value = ensureValue(theme.textColor, "#1f2933");
    if (elements.headingColor) elements.headingColor.value = ensureValue(theme.headingColor, "#0f172a");
    if (elements.accentColor) elements.accentColor.value = ensureValue(theme.accentColor, "#2563eb");
    if (elements.blockquoteBg) elements.blockquoteBg.value = ensureValue(theme.blockquoteBackground, "#eff6ff");
    if (elements.blockquoteBorder) elements.blockquoteBorder.value = ensureValue(theme.blockquoteBorderColor, "#2563eb");
    if (elements.codeBg) elements.codeBg.value = ensureValue(theme.codeBackground, "#0f172a");
    if (elements.codeText) elements.codeText.value = ensureValue(theme.codeTextColor, "#facc15");
    if (elements.listStyle && theme.listStyle) elements.listStyle.value = theme.listStyle;
    if (elements.orderedListStyle && theme.orderedListStyle) elements.orderedListStyle.value = theme.orderedListStyle;
    if (elements.pagePadding) {
        const paddingValue = ensureValue(theme.pagePadding, "48px");
        elements.pagePadding.value = parseInt(String(paddingValue).replace(/px/i, ""), 10) || 48;
    }
    if (elements.lineHeight) elements.lineHeight.value = ensureValue(theme.lineHeight, 1.7);
    if (elements.shadow && theme.cardShadow) elements.shadow.value = theme.cardShadow;
};

setControlInitialValues();

document.title = state.theme.title ?? "Markdown Styler";

const gatherTheme = () => ({
    title: elements.title?.value?.trim() || "Untitled",
    fontFamily: elements.font?.value || defaultTheme.fontFamily,
    baseFontSize: Number(elements.fontSize?.value) || defaultTheme.baseFontSize,
    backgroundColor: elements.background?.value || defaultTheme.backgroundColor,
    textColor: elements.textColor?.value || defaultTheme.textColor,
    headingColor: elements.headingColor?.value || defaultTheme.headingColor,
    accentColor: elements.accentColor?.value || defaultTheme.accentColor,
    blockquoteBackground: elements.blockquoteBg?.value || defaultTheme.blockquoteBackground,
    blockquoteBorderColor: elements.blockquoteBorder?.value || defaultTheme.blockquoteBorderColor,
    blockquoteTextColor: defaultTheme.blockquoteTextColor,
    codeBackground: elements.codeBg?.value || defaultTheme.codeBackground,
    codeTextColor: elements.codeText?.value || defaultTheme.codeTextColor,
    listStyle: elements.listStyle?.value || defaultTheme.listStyle,
    orderedListStyle: elements.orderedListStyle?.value || defaultTheme.orderedListStyle,
    pagePadding: `${Number(elements.pagePadding?.value) || 48}px`,
    lineHeight: Number(elements.lineHeight?.value) || defaultTheme.lineHeight,
    cardShadow: elements.shadow?.value || defaultTheme.cardShadow,
});

const updateStatus = (text, variant = "idle") => {
    if (!elements.previewStatus) return;
    elements.previewStatus.textContent = text;
    elements.previewStatus.classList.toggle("is-loading", variant === "loading");
    elements.previewStatus.classList.toggle("is-error", variant === "error");
};

let previewTimer;
let activePreviewSerial = 0;

const schedulePreview = (opts = { immediate: false }) => {
    state.isPreviewDirty = true;
    const delay = opts.immediate ? 0 : 280;
    clearTimeout(previewTimer);
    previewTimer = setTimeout(runPreview, delay);
};

const runPreview = async () => {
    if (!urls.preview) return;
    state.theme = gatherTheme();
    const markdown = elements.markdown?.value ?? "";
    updateStatus("렌더링 중...", "loading");
    const serial = ++activePreviewSerial;

    try {
        const response = await fetch(urls.preview, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify({
                markdown,
                theme: state.theme,
                title: state.theme.title,
            }),
        });

        if (!response.ok) {
            const payload = await response.json().catch(() => ({}));
            throw new Error(payload.error || `미리보기 요청 실패 (${response.status})`);
        }

        const data = await response.json();
        if (serial !== activePreviewSerial) return;

        if (elements.previewStyle) elements.previewStyle.textContent = data.css ?? "";
        if (elements.previewOutput) elements.previewOutput.innerHTML = data.html ?? "";
        document.title = `${state.theme.title} · Markdown Styler`;
        updateStatus("실시간 반영 완료", "idle");
        state.isPreviewDirty = false;
    } catch (error) {
        console.error(error);
        updateStatus(error.message || "미리보기 오류", "error");
    }
};

const attachControlListeners = () => {
    const inputs = [
        elements.title,
        elements.font,
        elements.fontSize,
        elements.background,
        elements.textColor,
        elements.headingColor,
        elements.accentColor,
        elements.blockquoteBg,
        elements.blockquoteBorder,
        elements.codeBg,
        elements.codeText,
        elements.listStyle,
        elements.orderedListStyle,
        elements.pagePadding,
        elements.lineHeight,
        elements.shadow,
    ].filter(Boolean);

    for (const input of inputs) {
        input.addEventListener("input", () => schedulePreview());
    }

    if (elements.markdown) {
        elements.markdown.addEventListener("input", () => schedulePreview());
    }

    if (elements.btnPreview) {
        elements.btnPreview.addEventListener("click", () => schedulePreview({ immediate: true }));
    }
};

attachControlListeners();

const toggleLoading = (isLoading) => {
    const existing = document.querySelector(".loading-overlay");
    if (isLoading) {
        if (existing) return existing;
        const template = elements.loadingTemplate?.content?.firstElementChild;
        if (!template) return null;
        const overlay = document.createElement("div");
        overlay.className = "loading-overlay";
        overlay.appendChild(template.cloneNode(true));
        document.body.appendChild(overlay);
        return overlay;
    }
    if (existing) existing.remove();
    return null;
};

const downloadPdf = async () => {
    if (!urls.pdf) return;
    state.theme = gatherTheme();
    const markdown = elements.markdown?.value ?? "";
    const overlay = toggleLoading(true);
    elements.btnDownload?.setAttribute("disabled", "true");

    try {
        const response = await fetch(urls.pdf, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": getCsrfToken(),
            },
            body: JSON.stringify({
                markdown,
                theme: state.theme,
                title: state.theme.title,
            }),
        });

        if (!response.ok) {
            const payload = await response.json().catch(() => ({}));
            throw new Error(payload.error || `PDF 생성 실패 (${response.status})`);
        }

        const blob = await response.blob();
        const link = document.createElement("a");
        const fileURL = URL.createObjectURL(blob);
        link.href = fileURL;
        const timestamp = new Date().toISOString().replace(/[:.]/g, "-");
        link.download = `${state.theme.title || "Document"}_${timestamp}.pdf`;
        document.body.appendChild(link);
        link.click();
        link.remove();
        URL.revokeObjectURL(fileURL);
    } catch (error) {
        console.error(error);
        alert(error.message || "PDF를 생성할 수 없습니다.");
    } finally {
        if (overlay) toggleLoading(false);
        elements.btnDownload?.removeAttribute("disabled");
    }
};

if (elements.btnDownload) {
    elements.btnDownload.addEventListener("click", downloadPdf);
}

schedulePreview({ immediate: true });
