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

const cloneTheme = () => JSON.parse(JSON.stringify(defaultTheme || {}));

const parseNumberOr = (value, fallback) => {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : fallback;
};

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

const defaultBulletSequence = Array.isArray(defaultTheme.customBulletSequence)
    ? [...defaultTheme.customBulletSequence]
    : ["•", "◦", "▪"];

const defaultOrderedDigits = Array.isArray(defaultTheme.customOrderedDigits)
    ? [...defaultTheme.customOrderedDigits]
    : ["0", "1", "2"];

const DEFAULT_ORDERED_BASE = clamp(
    Math.round(parseNumberOr(defaultTheme.customOrderedBase, defaultOrderedDigits.length || 3)),
    2,
    10,
);

const sanitizeOrderedBase = (value) => {
    const parsed = Math.round(parseNumberOr(value, DEFAULT_ORDERED_BASE));
    return clamp(Number.isNaN(parsed) ? DEFAULT_ORDERED_BASE : parsed, 2, 10);
};

const state = {
    theme: cloneTheme(),
    isPreviewDirty: true,
    isPaletteCollapsed: false,
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
    btnReset: document.getElementById("btn-reset-theme"),
    btnTogglePalette: document.getElementById("btn-toggle-palette"),
    paletteSlot: document.querySelector(".palette-slot"),
    toggleCustomBullets: document.getElementById("toggle-custom-bullets"),
    bulletEditor: document.querySelector('[data-role="bullet-editor"]'),
    bulletSequenceList: document.getElementById("bullet-sequence-list"),
    btnAddBullet: document.getElementById("btn-add-bullet"),
    toggleCustomOrdered: document.getElementById("toggle-custom-ordered"),
    orderedEditor: document.querySelector('[data-role="ordered-editor"]'),
    orderedSequenceList: document.getElementById("ordered-sequence-list"),
    customOrderedBase: document.getElementById("number-ordered-base"),
    customOrderedPrefix: document.getElementById("input-ordered-prefix"),
    customOrderedSuffix: document.getElementById("input-ordered-suffix"),
    loadingTemplate: document.getElementById("loading-indicator"),
};

const urls = {
    preview: root.dataset.previewUrl,
    pdf: root.dataset.pdfUrl,
};

const ensureValue = (value, fallback) => (value === undefined || value === null ? fallback : value);

const applyPaletteCollapsedState = (collapsed) => {
    state.isPaletteCollapsed = collapsed;
    root.classList.toggle("workspace__layout--palette-collapsed", collapsed);
    elements.paletteSlot?.classList.toggle("palette-slot--collapsed", collapsed);
    if (elements.btnTogglePalette) {
        elements.btnTogglePalette.textContent = collapsed ? "▶" : "◀";
        elements.btnTogglePalette.setAttribute("aria-pressed", collapsed ? "true" : "false");
        elements.btnTogglePalette.setAttribute("aria-label", collapsed ? "팔레트 펼치기" : "팔레트 접기");
    }
};

function addBulletRow(value = "") {
    if (!elements.bulletSequenceList) return;
    const row = document.createElement("div");
    row.className = "sequence-editor__item";

    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = "아이콘";
    input.value = value ?? "";
    input.addEventListener("input", () => schedulePreview());
    row.appendChild(input);

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "sequence-editor__remove";
    remove.setAttribute("aria-label", "아이콘 삭제");
    remove.textContent = "×";
    remove.addEventListener("click", () => {
        row.remove();
        updateBulletRemoveButtons();
        schedulePreview({ immediate: true });
    });
    row.appendChild(remove);

    elements.bulletSequenceList.appendChild(row);
}

function updateBulletRemoveButtons() {
    if (!elements.bulletSequenceList) return;
    const rows = elements.bulletSequenceList.querySelectorAll(".sequence-editor__item");
    rows.forEach((row) => {
        const remove = row.querySelector(".sequence-editor__remove");
        if (remove) {
            remove.disabled = rows.length <= 1;
        }
    });
}

function renderBulletSequence(values = []) {
    if (!elements.bulletSequenceList) return;
    const effective = Array.isArray(values) && values.length ? [...values] : [...defaultBulletSequence];
    elements.bulletSequenceList.innerHTML = "";
    if (!effective.length) {
        effective.push("");
    }
    effective.forEach((value) => addBulletRow(value));
    updateBulletRemoveButtons();
}

function readBulletSequence() {
    if (!elements.bulletSequenceList) return [];
    return Array.from(elements.bulletSequenceList.querySelectorAll("input[type='text']"))
        .map((input) => input.value.trim())
        .filter((value) => value.length > 0);
}

function setBulletEditorDisabled(disabled) {
    if (elements.bulletEditor) {
        elements.bulletEditor.setAttribute("aria-disabled", disabled ? "true" : "false");
    }
    if (elements.btnAddBullet) {
        elements.btnAddBullet.disabled = disabled;
    }
    const inputs = elements.bulletSequenceList?.querySelectorAll("input[type='text']") ?? [];
    inputs.forEach((input) => {
        input.disabled = disabled;
    });
    const removers = elements.bulletSequenceList?.querySelectorAll(".sequence-editor__remove") ?? [];
    removers.forEach((btn) => {
        btn.disabled = disabled;
    });
}

function renderOrderedSequence(baseValue, values = []) {
    if (!elements.orderedSequenceList) return;
    const targetBase = sanitizeOrderedBase(baseValue);
    elements.orderedSequenceList.innerHTML = "";
    for (let i = 0; i < targetBase; i += 1) {
        const row = document.createElement("div");
        row.className = "sequence-editor__item";

        const indexLabel = document.createElement("span");
        indexLabel.className = "sequence-editor__index";
        indexLabel.textContent = String(i);
        row.appendChild(indexLabel);

        const input = document.createElement("input");
        input.type = "text";
        input.placeholder = defaultOrderedDigits[i] ?? String(i);
        input.value = (values[i] ?? defaultOrderedDigits[i] ?? "");
        input.addEventListener("input", () => schedulePreview());
        row.appendChild(input);

        elements.orderedSequenceList.appendChild(row);
    }
}

function readOrderedSequence() {
    if (!elements.orderedSequenceList) return [];
    return Array.from(elements.orderedSequenceList.querySelectorAll("input[type='text']"))
        .map((input) => input.value.trim());
}

function ensureOrderedDigits(values, base) {
    const digits = [];
    for (let i = 0; i < base; i += 1) {
        const candidate = (values[i] ?? "").trim();
        if (candidate) {
            digits.push(candidate);
        } else if (defaultOrderedDigits[i]) {
            digits.push(defaultOrderedDigits[i]);
        } else {
            digits.push(String(i));
        }
    }
    return digits;
}

function setOrderedEditorDisabled(disabled) {
    if (elements.orderedEditor) {
        elements.orderedEditor.setAttribute("aria-disabled", disabled ? "true" : "false");
    }
    if (elements.customOrderedBase) elements.customOrderedBase.disabled = disabled;
    if (elements.customOrderedPrefix) elements.customOrderedPrefix.disabled = disabled;
    if (elements.customOrderedSuffix) elements.customOrderedSuffix.disabled = disabled;
    const inputs = elements.orderedSequenceList?.querySelectorAll("input[type='text']") ?? [];
    inputs.forEach((input) => {
        input.disabled = disabled;
    });
}

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
    const bulletValues = Array.isArray(theme.customBulletSequence) ? theme.customBulletSequence : [];
    renderBulletSequence(bulletValues);
    if (elements.toggleCustomBullets) {
        elements.toggleCustomBullets.checked = !!theme.useCustomBullets && bulletValues.length > 0;
    }

    const baseValue = sanitizeOrderedBase(theme.customOrderedBase);
    if (elements.customOrderedBase) {
        elements.customOrderedBase.value = baseValue;
    }
    const orderedValues = Array.isArray(theme.customOrderedDigits) ? theme.customOrderedDigits : [];
    renderOrderedSequence(baseValue, orderedValues);
    if (elements.toggleCustomOrdered) elements.toggleCustomOrdered.checked = !!theme.useCustomOrdered;

    if (elements.customOrderedPrefix) {
        elements.customOrderedPrefix.value = ensureValue(
            theme.orderedMarkerPrefix,
            defaultTheme.orderedMarkerPrefix ?? ""
        );
    }
    if (elements.customOrderedSuffix) {
        elements.customOrderedSuffix.value = ensureValue(
            theme.orderedMarkerSuffix,
            defaultTheme.orderedMarkerSuffix ?? "."
        );
    }

    updateCustomControlsState();
};

setControlInitialValues();
applyPaletteCollapsedState(false);

document.title = state.theme.title ?? "Markdown Styler";

function updateCustomControlsState() {
    const bulletsEnabled = elements.toggleCustomBullets?.checked ?? false;
    setBulletEditorDisabled(!bulletsEnabled);
    updateBulletRemoveButtons();

    const orderedEnabled = elements.toggleCustomOrdered?.checked ?? false;
    setOrderedEditorDisabled(!orderedEnabled);
}

const gatherTheme = () => {
    const bulletSequence = readBulletSequence();
    const orderedBase = sanitizeOrderedBase(elements.customOrderedBase?.value);
    if (elements.customOrderedBase) {
        elements.customOrderedBase.value = orderedBase;
    }
    const orderedDigitsRaw = readOrderedSequence();
    const orderedDigits = ensureOrderedDigits(orderedDigitsRaw, orderedBase);

    const useCustomBullets = (elements.toggleCustomBullets?.checked ?? false) && bulletSequence.length > 0;
    const useCustomOrdered = elements.toggleCustomOrdered?.checked ?? false;

    return {
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
        useCustomBullets,
        customBulletSequence: bulletSequence,
        useCustomOrdered,
        customOrderedDigits: orderedDigits,
        customOrderedBase: orderedDigits.length,
        orderedMarkerPrefix: elements.customOrderedPrefix?.value?.trim() ?? defaultTheme.orderedMarkerPrefix ?? "",
        orderedMarkerSuffix: elements.customOrderedSuffix?.value?.trim() ?? defaultTheme.orderedMarkerSuffix ?? ".",
    };
};

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
        elements.customOrderedPrefix,
        elements.customOrderedSuffix,
    ].filter(Boolean);

    for (const input of inputs) {
        input.addEventListener("input", () => schedulePreview());
    }

    if (elements.toggleCustomBullets) {
        elements.toggleCustomBullets.addEventListener("change", () => {
            updateCustomControlsState();
            schedulePreview();
        });
    }

    if (elements.toggleCustomOrdered) {
        elements.toggleCustomOrdered.addEventListener("change", () => {
            updateCustomControlsState();
            schedulePreview();
        });
    }

    if (elements.customOrderedBase) {
        elements.customOrderedBase.addEventListener("change", () => {
            const currentValues = readOrderedSequence();
            const nextBase = sanitizeOrderedBase(elements.customOrderedBase.value);
            elements.customOrderedBase.value = nextBase;
            renderOrderedSequence(nextBase, currentValues);
            updateCustomControlsState();
            schedulePreview({ immediate: true });
        });
        elements.customOrderedBase.addEventListener("input", () => {
            const currentValues = readOrderedSequence();
            const nextBase = sanitizeOrderedBase(elements.customOrderedBase.value);
            renderOrderedSequence(nextBase, currentValues);
            updateCustomControlsState();
            schedulePreview();
        });
    }

    if (elements.btnAddBullet) {
        elements.btnAddBullet.addEventListener("click", () => {
            addBulletRow("");
            updateBulletRemoveButtons();
            schedulePreview({ immediate: true });
        });
    }

    if (elements.markdown) {
        elements.markdown.addEventListener("input", () => schedulePreview());
    }

    if (elements.btnPreview) {
        elements.btnPreview.addEventListener("click", () => schedulePreview({ immediate: true }));
    }

    if (elements.btnReset) {
        elements.btnReset.addEventListener("click", () => {
            state.theme = cloneTheme();
            setControlInitialValues();
            document.title = state.theme.title ?? "Markdown Styler";
            schedulePreview({ immediate: true });
        });
    }

    if (elements.btnTogglePalette) {
        elements.btnTogglePalette.addEventListener("click", () => {
            applyPaletteCollapsedState(!state.isPaletteCollapsed);
        });
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
