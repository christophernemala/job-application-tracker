const appState = {
  invoiceWorkbook: null,
  bankWorkbook: null,
  invoicesRaw: [],
  bankRaw: [],
  invoices: [],
  bank: [],
  matches: [],
  unmatchedInvoices: [],
  unmatchedBank: [],
  config: {
    amountTolerance: 0.01,
    allowVariance: false,
    dateWindow: 7,
    threshold: 0.75,
    weights: {
      reference: 0.45,
      amount: 0.35,
      date: 0.1,
      customer: 0.1
    },
    enableGrouping: false
  },
  ui: {
    activeTab: "matched",
    chartMode: "amount",
    search: "",
    currency: "all",
    dateFrom: "",
    dateTo: "",
    sort: "score-desc"
  },
  mappingContext: null
};

const headerAliases = {
  invoice: {
    invoiceNumber: ["invoice number", "invoice #", "invoice_no", "inv number", "inv #", "inv_no"],
    customerName: ["customer", "customer name", "client", "client name", "account"],
    invoiceDate: ["invoice date", "inv date", "date", "bill date"],
    dueDate: ["due date", "payment due", "due"],
    amount: ["amount", "total", "invoice amount", "balance"],
    currency: ["currency", "ccy", "curr"],
    reference: ["reference", "ref", "memo", "description"]
  },
  bank: {
    transactionDate: ["transaction date", "date", "value date", "posted date"],
    description: ["description", "details", "narration", "memo"],
    amount: ["amount", "amt", "debit", "credit", "value"],
    currency: ["currency", "ccy", "curr"],
    reference: ["reference", "ref", "payment reference", "payer ref"],
    bankId: ["bank id", "transaction id", "id", "txn id"]
  }
};

const requiredFields = {
  invoice: ["invoiceNumber", "amount", "invoiceDate"],
  bank: ["transactionDate", "amount", "description"]
};

const elements = {
  themeToggle: document.getElementById("theme-toggle"),
  helpOpen: document.getElementById("help-open"),
  sampleBtn: document.getElementById("sample-btn"),
  resetBtn: document.getElementById("reset-btn"),
  invoiceDrop: document.getElementById("invoice-drop"),
  bankDrop: document.getElementById("bank-drop"),
  invoiceFile: document.getElementById("invoice-file"),
  bankFile: document.getElementById("bank-file"),
  invoiceSheet: document.getElementById("invoice-sheet"),
  bankSheet: document.getElementById("bank-sheet"),
  invoiceName: document.getElementById("invoice-file-name"),
  bankName: document.getElementById("bank-file-name"),
  invoiceRows: document.getElementById("invoice-row-count"),
  bankRows: document.getElementById("bank-row-count"),
  runBtn: document.getElementById("run-btn"),
  cancelBtn: document.getElementById("cancel-btn"),
  progressFill: document.getElementById("progress-fill"),
  progressGlow: document.getElementById("progress-glow"),
  engineStatus: document.getElementById("engine-status"),
  statsGrid: document.getElementById("stats-grid"),
  chartToggle: document.querySelector(".chart-toggle"),
  pieChart: document.getElementById("pie-chart"),
  barChart: document.getElementById("bar-chart"),
  exportBtn: document.getElementById("export-btn"),
  tabs: document.querySelectorAll(".tab"),
  search: document.getElementById("search"),
  currencyFilter: document.getElementById("currency-filter"),
  dateFrom: document.getElementById("date-from"),
  dateTo: document.getElementById("date-to"),
  sort: document.getElementById("sort"),
  resultsBody: document.getElementById("results-body"),
  emptyState: document.getElementById("empty-state"),
  toastStack: document.getElementById("toast-stack"),
  helpModal: document.getElementById("help-modal"),
  mappingModal: document.getElementById("mapping-modal"),
  mappingBody: document.getElementById("mapping-body"),
  applyMapping: document.getElementById("apply-mapping"),
  allowVariance: document.getElementById("allow-variance"),
  groupingMode: document.getElementById("grouping-mode"),
  tolerance: document.getElementById("tolerance"),
  dateWindow: document.getElementById("date-window"),
  threshold: document.getElementById("threshold"),
  weightReference: document.getElementById("weight-reference"),
  weightAmount: document.getElementById("weight-amount"),
  weightDate: document.getElementById("weight-date"),
  weightCustomer: document.getElementById("weight-customer")
};

let charts = {
  pie: null,
  bar: null
};

let cancelRequested = false;

init();

function init() {
  setupTheme();
  setupParticles();
  setupMagnetism();
  setupUploads();
  setupControls();
  setupModals();
  updateStats();
  updateCharts();
  renderTable();
}

function setupTheme() {
  const storedTheme = localStorage.getItem("theme");
  if (storedTheme) {
    document.documentElement.dataset.theme = storedTheme;
  } else if (window.matchMedia("(prefers-color-scheme: light)").matches) {
    document.documentElement.dataset.theme = "light";
  }
  elements.themeToggle.addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "light" ? "dark" : "light";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("theme", next);
  });
}

function setupParticles() {
  const canvas = document.getElementById("particles");
  const ctx = canvas.getContext("2d");
  const particles = [];

  function resize() {
    canvas.width = window.innerWidth;
    canvas.height = window.innerHeight;
  }
  resize();
  window.addEventListener("resize", resize);

  for (let i = 0; i < 80; i += 1) {
    particles.push({
      x: Math.random() * canvas.width,
      y: Math.random() * canvas.height,
      r: Math.random() * 2 + 0.6,
      vx: (Math.random() - 0.5) * 0.3,
      vy: (Math.random() - 0.5) * 0.3,
      alpha: Math.random() * 0.7 + 0.2
    });
  }

  function animate() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "rgba(109, 241, 255, 0.65)";
    particles.forEach((p) => {
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
      if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
      ctx.globalAlpha = p.alpha;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    });
    ctx.globalAlpha = 1;
    requestAnimationFrame(animate);
  }
  animate();
}

function setupUploads() {
  setupDropZone(elements.invoiceDrop, elements.invoiceFile, "invoice");
  setupDropZone(elements.bankDrop, elements.bankFile, "bank");

  elements.invoiceFile.addEventListener("change", (event) => handleFile(event.target.files[0], "invoice"));
  elements.bankFile.addEventListener("change", (event) => handleFile(event.target.files[0], "bank"));

  elements.invoiceSheet.addEventListener("change", () => parseSelectedSheet("invoice"));
  elements.bankSheet.addEventListener("change", () => parseSelectedSheet("bank"));
}

function setupDropZone(zone, input, type) {
  ["dragenter", "dragover"].forEach((eventName) => {
    zone.addEventListener(eventName, (event) => {
      event.preventDefault();
      zone.classList.add("active");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    zone.addEventListener(eventName, (event) => {
      event.preventDefault();
      zone.classList.remove("active");
    });
  });

  zone.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    if (file) {
      input.files = event.dataTransfer.files;
      handleFile(file, type);
    }
  });
}

function setupControls() {
  elements.sampleBtn.addEventListener("click", generateSampleData);
  elements.resetBtn.addEventListener("click", resetWorkspace);
  elements.runBtn.addEventListener("click", runReconciliation);
  elements.cancelBtn.addEventListener("click", () => {
    cancelRequested = true;
    showToast("Reconciliation cancelled.", "warning");
  });
  elements.exportBtn.addEventListener("click", exportReport);

  elements.chartToggle.addEventListener("click", (event) => {
    if (event.target.matches("button[data-chart]")) {
      document.querySelectorAll(".chart-toggle button").forEach((btn) => btn.classList.remove("active"));
      event.target.classList.add("active");
      appState.ui.chartMode = event.target.dataset.chart;
      updateCharts();
    }
  });

  elements.tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      elements.tabs.forEach((btn) => btn.classList.remove("active"));
      tab.classList.add("active");
      appState.ui.activeTab = tab.dataset.tab;
      renderTable();
    });
  });

  elements.search.addEventListener("input", (event) => {
    appState.ui.search = event.target.value.trim().toLowerCase();
    renderTable();
  });

  [elements.currencyFilter, elements.dateFrom, elements.dateTo, elements.sort].forEach((element) => {
    element.addEventListener("change", () => {
      appState.ui.currency = elements.currencyFilter.value;
      appState.ui.dateFrom = elements.dateFrom.value;
      appState.ui.dateTo = elements.dateTo.value;
      appState.ui.sort = elements.sort.value;
      renderTable();
    });
  });

  [
    elements.allowVariance,
    elements.groupingMode,
    elements.tolerance,
    elements.dateWindow,
    elements.threshold,
    elements.weightReference,
    elements.weightAmount,
    elements.weightDate,
    elements.weightCustomer
  ].forEach((input) => {
    input.addEventListener("change", syncConfig);
  });
}

function setupMagnetism() {
  const buttons = document.querySelectorAll(".primary-btn");
  buttons.forEach((button) => {
    button.addEventListener("mousemove", (event) => {
      const rect = button.getBoundingClientRect();
      const x = event.clientX - rect.left - rect.width / 2;
      const y = event.clientY - rect.top - rect.height / 2;
      button.style.transform = `translate(${x * 0.08}px, ${y * 0.08}px)`;
    });
    button.addEventListener("mouseleave", () => {
      button.style.transform = "translate(0, 0)";
    });
  });
}

function setupModals() {
  elements.helpOpen.addEventListener("click", () => elements.helpModal.showModal());
  document.querySelectorAll("[data-close]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const target = document.getElementById(btn.dataset.close);
      if (target) target.close();
    });
  });

  elements.applyMapping.addEventListener("click", () => {
    if (!appState.mappingContext) return;
    const { type, headers, rawData } = appState.mappingContext;
    const mapping = {};
    Object.keys(headerAliases[type]).forEach((field) => {
      const select = document.getElementById(`map-${field}`);
      mapping[field] = select?.value || "";
    });
    const normalized = normalizeRows(rawData, type, mapping);
    applyNormalizedData(type, normalized, rawData);
    appState.mappingContext = null;
    elements.mappingModal.close();
  });
}

function syncConfig() {
  appState.config.allowVariance = elements.allowVariance.checked;
  appState.config.enableGrouping = elements.groupingMode.checked;
  appState.config.amountTolerance = Number(elements.tolerance.value || 0.01);
  appState.config.dateWindow = Number(elements.dateWindow.value || 7);
  appState.config.threshold = Number(elements.threshold.value || 0.75);
  appState.config.weights.reference = Number(elements.weightReference.value || 0.45);
  appState.config.weights.amount = Number(elements.weightAmount.value || 0.35);
  appState.config.weights.date = Number(elements.weightDate.value || 0.1);
  appState.config.weights.customer = Number(elements.weightCustomer.value || 0.1);
}

async function handleFile(file, type) {
  if (!file) return;
  try {
    const workbook = await readWorkbook(file);
    if (type === "invoice") {
      appState.invoiceWorkbook = workbook;
      elements.invoiceName.textContent = file.name;
      populateSheetOptions(workbook, elements.invoiceSheet);
    } else {
      appState.bankWorkbook = workbook;
      elements.bankName.textContent = file.name;
      populateSheetOptions(workbook, elements.bankSheet);
    }
    showToast(`${type === "invoice" ? "Invoice" : "Bank"} file loaded. Select a sheet.`, "success");
  } catch (error) {
    showToast("Failed to parse Excel file.", "error");
  }
}

function readWorkbook(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const data = new Uint8Array(event.target.result);
        const workbook = XLSX.read(data, { type: "array" });
        resolve(workbook);
      } catch (error) {
        reject(error);
      }
    };
    reader.onerror = () => reject(new Error("File read failed"));
    reader.readAsArrayBuffer(file);
  });
}

function populateSheetOptions(workbook, select) {
  select.innerHTML = "";
  workbook.SheetNames.forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    select.appendChild(option);
  });
  select.value = workbook.SheetNames[0] || "";
  select.dispatchEvent(new Event("change"));
}

function parseSelectedSheet(type) {
  const workbook = type === "invoice" ? appState.invoiceWorkbook : appState.bankWorkbook;
  const sheetName = type === "invoice" ? elements.invoiceSheet.value : elements.bankSheet.value;
  if (!workbook || !sheetName) return;
  const sheet = workbook.Sheets[sheetName];
  const rawData = XLSX.utils.sheet_to_json(sheet, { defval: "" });
  const headers = Object.keys(rawData[0] || {});
  const mapping = detectMapping(headers, type);
  if (mapping.missing.length) {
    openMappingModal(type, headers, rawData, mapping.mapping);
    return;
  }
  const normalized = normalizeRows(rawData, type, mapping.mapping);
  applyNormalizedData(type, normalized, rawData);
}

function detectMapping(headers, type) {
  const mapping = {};
  const missing = [];
  const normalizedHeaders = headers.map((header) => header.toLowerCase().trim());

  Object.entries(headerAliases[type]).forEach(([field, aliases]) => {
    const foundIndex = normalizedHeaders.findIndex((header) => aliases.includes(header));
    if (foundIndex !== -1) {
      mapping[field] = headers[foundIndex];
    } else {
      mapping[field] = "";
      if (requiredFields[type].includes(field)) missing.push(field);
    }
  });

  return { mapping, missing };
}

function openMappingModal(type, headers, rawData, suggested) {
  appState.mappingContext = { type, headers, rawData };
  elements.mappingBody.innerHTML = "";
  const fragment = document.createDocumentFragment();

  Object.keys(headerAliases[type]).forEach((field) => {
    const wrapper = document.createElement("label");
    wrapper.className = "setting";
    wrapper.innerHTML = `<span>${field}</span>`;
    const select = document.createElement("select");
    select.id = `map-${field}`;
    const emptyOption = document.createElement("option");
    emptyOption.value = "";
    emptyOption.textContent = "Not available";
    select.appendChild(emptyOption);
    headers.forEach((header) => {
      const option = document.createElement("option");
      option.value = header;
      option.textContent = header;
      select.appendChild(option);
    });
    select.value = suggested[field] || "";
    wrapper.appendChild(select);
    fragment.appendChild(wrapper);
  });

  elements.mappingBody.appendChild(fragment);
  elements.mappingModal.showModal();
}

function applyNormalizedData(type, normalized, rawData) {
  if (type === "invoice") {
    appState.invoicesRaw = rawData;
    appState.invoices = normalized;
    elements.invoiceRows.textContent = `${normalized.length} rows`;
  } else {
    appState.bankRaw = rawData;
    appState.bank = normalized;
    elements.bankRows.textContent = `${normalized.length} rows`;
  }
  updateCurrencyFilter();
}

function normalizeRows(rows, type, mapping) {
  return rows.map((row, index) => {
    if (type === "invoice") {
      return {
        invoiceNumber: cleanText(row[mapping.invoiceNumber] || `INV-${index + 1}`),
        customerName: cleanText(row[mapping.customerName] || ""),
        invoiceDate: parseDate(row[mapping.invoiceDate]) || todayString(),
        dueDate: parseDate(row[mapping.dueDate]) || parseDate(row[mapping.invoiceDate]) || todayString(),
        amount: parseMoney(row[mapping.amount]),
        currency: normalizeCurrency(row[mapping.currency], row[mapping.amount]) || "USD",
        reference: cleanRef(row[mapping.reference] || "")
      };
    }
    return {
      transactionDate: parseDate(row[mapping.transactionDate]) || todayString(),
      description: cleanText(row[mapping.description] || ""),
      amount: parseMoney(row[mapping.amount]),
      currency: normalizeCurrency(row[mapping.currency], row[mapping.amount]) || "USD",
      reference: cleanRef(row[mapping.reference] || ""),
      bankId: cleanText(row[mapping.bankId] || `BANK-${index + 1}`)
    };
  });
}

function cleanText(value) {
  return String(value || "").replace(/\s+/g, " ").trim();
}

function cleanRef(value) {
  return cleanText(value).toUpperCase();
}

function parseMoney(value) {
  if (typeof value === "number") return value;
  const cleaned = String(value || "").replace(/[^0-9.-]/g, "");
  return Number(cleaned || 0);
}

function normalizeCurrency(currency, amountField) {
  const text = String(currency || amountField || "").toUpperCase();
  const match = text.match(/(USD|EUR|GBP|JPY|AUD|CAD|CHF|CNY|HKD|SGD)/);
  return match ? match[1] : "";
}

function parseDate(value) {
  if (!value) return "";
  if (value instanceof Date) return value.toISOString().split("T")[0];
  if (typeof value === "number") {
    const date = XLSX.SSF.parse_date_code(value);
    if (date) {
      const jsDate = new Date(Date.UTC(date.y, date.m - 1, date.d));
      return jsDate.toISOString().split("T")[0];
    }
  }
  const parsed = new Date(value);
  if (!Number.isNaN(parsed.valueOf())) {
    return parsed.toISOString().split("T")[0];
  }
  return "";
}

function todayString() {
  return new Date().toISOString().split("T")[0];
}

function updateCurrencyFilter() {
  const currencies = new Set([
    ...appState.invoices.map((row) => row.currency),
    ...appState.bank.map((row) => row.currency)
  ]);
  const options = ["all", ...currencies].filter(Boolean);
  elements.currencyFilter.innerHTML = "";
  options.forEach((currency) => {
    const option = document.createElement("option");
    option.value = currency;
    option.textContent = currency === "all" ? "All Currencies" : currency;
    elements.currencyFilter.appendChild(option);
  });
}

async function runReconciliation() {
  if (!appState.invoices.length || !appState.bank.length) {
    showToast("Please upload both invoice and bank files.", "warning");
    return;
  }
  cancelRequested = false;
  syncConfig();
  updateEngineProgress(5, "Parse", "Parsing and validating input...");
  await delay(250);
  updateEngineProgress(20, "Normalize", "Normalizing formats and cleaning references...");
  await delay(250);
  updateEngineProgress(40, "Score", "Scoring candidate pairs...");
  await delay(250);

  const usedBank = new Set();
  const matches = [];
  const unmatchedInvoices = [];

  const batchSize = 200;
  for (let i = 0; i < appState.invoices.length; i += batchSize) {
    if (cancelRequested) return;
    const batch = appState.invoices.slice(i, i + batchSize);
    batch.forEach((invoice) => {
      const { match, score, explanation, amountPass } = findBestMatch(invoice, usedBank);
      if (match && score >= appState.config.threshold && amountPass) {
        usedBank.add(match.index);
        matches.push(buildMatchRecord(invoice, match.bank, score, explanation, "one-to-one"));
      } else if (appState.config.enableGrouping) {
        const grouped = findGroupedMatch(invoice, usedBank);
        if (grouped) {
          grouped.indices.forEach((idx) => usedBank.add(idx));
          matches.push(buildGroupedRecord(invoice, grouped, "one-to-many"));
        } else {
          unmatchedInvoices.push(buildUnmatchedInvoice(invoice));
        }
      } else {
        unmatchedInvoices.push(buildUnmatchedInvoice(invoice));
      }
    });
    updateEngineProgress(40 + Math.round(((i + batch.length) / appState.invoices.length) * 35), "Match", "Matching invoices to bank lines...");
    await delay(0);
  }

  if (appState.config.enableGrouping && !cancelRequested) {
    const manyToOneMatches = matchManyToOne(unmatchedInvoices, usedBank);
    manyToOneMatches.matched.forEach((match) => matches.push(match));
    unmatchedInvoices.length = 0;
    unmatchedInvoices.push(...manyToOneMatches.unmatched);
  }

  appState.unmatchedBank = appState.bank
    .map((bank, index) => ({ bank, index }))
    .filter(({ index }) => !usedBank.has(index))
    .map(({ bank }) => buildUnmatchedBank(bank));

  appState.matches = matches;
  appState.unmatchedInvoices = unmatchedInvoices;

  updateEngineProgress(90, "Validate", "Validating output and generating insights...");
  await delay(250);
  updateEngineProgress(100, "Report", "Reporting complete.");
  await delay(200);

  showToast("Reconciliation complete.", "success");
  updateStats();
  updateCharts();
  renderTable();
}

function updateEngineProgress(percent, step, statusText) {
  elements.progressFill.style.width = `${percent}%`;
  document.querySelectorAll(".step").forEach((item) => {
    item.classList.toggle("active", item.dataset.step === step);
  });
  typeStatus(statusText);
}

function typeStatus(text) {
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (reducedMotion) {
    elements.engineStatus.textContent = text;
    return;
  }
  let index = 0;
  elements.engineStatus.textContent = "";
  const interval = setInterval(() => {
    elements.engineStatus.textContent += text.charAt(index);
    index += 1;
    if (index >= text.length) clearInterval(interval);
  }, 20);
}

function findBestMatch(invoice, usedBank) {
  let best = null;
  let bestScore = 0;
  let bestExplanation = null;
  let amountPass = false;

  appState.bank.forEach((bank, index) => {
    if (usedBank.has(index)) return;
    const { score, explanation, amountPass: pass } = computeScore(invoice, bank);
    if (score > bestScore) {
      bestScore = score;
      best = { bank, index };
      bestExplanation = explanation;
      amountPass = pass;
    }
  });

  return {
    match: best,
    score: bestScore,
    explanation: bestExplanation,
    amountPass
  };
}

function computeScore(invoice, bank) {
  const amountDiff = Math.abs(invoice.amount - bank.amount);
  const amountPass = appState.config.allowVariance || amountDiff <= appState.config.amountTolerance;

  const referenceHit = referenceMatch(invoice, bank);
  const amountScore = amountDiff <= appState.config.amountTolerance ? 1 : Math.max(0, 1 - amountDiff / Math.max(invoice.amount, 1));
  const dateScore = dateProximity(invoice, bank);
  const customerScore = customerSimilarity(invoice, bank);

  const weightedScore =
    referenceHit * appState.config.weights.reference +
    amountScore * appState.config.weights.amount +
    dateScore * appState.config.weights.date +
    customerScore * appState.config.weights.customer;

  const score = Math.min(1, weightedScore);

  return {
    score,
    amountPass,
    explanation: {
      referenceHit: referenceHit > 0.7,
      amountDiff: amountDiff.toFixed(2),
      dateGap: dateGapDays(invoice, bank),
      customerSimilarity: customerScore.toFixed(2),
      breakdown: {
        reference: referenceHit.toFixed(2),
        amount: amountScore.toFixed(2),
        date: dateScore.toFixed(2),
        customer: customerScore.toFixed(2)
      }
    }
  };
}

function referenceMatch(invoice, bank) {
  const ref = invoice.reference || invoice.invoiceNumber;
  const haystack = `${bank.reference} ${bank.description}`.toUpperCase();
  if (!ref) return 0;
  if (haystack.includes(ref)) return 1;
  if (haystack.includes(invoice.invoiceNumber)) return 0.9;
  return stringSimilarity(ref, bank.reference || bank.description || "");
}

function dateGapDays(invoice, bank) {
  const invDate = new Date(invoice.invoiceDate || invoice.dueDate);
  const bankDate = new Date(bank.transactionDate);
  return Math.abs((invDate - bankDate) / (1000 * 60 * 60 * 24));
}

function dateProximity(invoice, bank) {
  const gap = dateGapDays(invoice, bank);
  if (gap <= appState.config.dateWindow) {
    return 1 - gap / (appState.config.dateWindow + 1);
  }
  return 0;
}

function customerSimilarity(invoice, bank) {
  if (!invoice.customerName) return 0;
  return stringSimilarity(invoice.customerName, bank.description || "");
}

function tokenize(text) {
  return new Set(cleanText(text).toLowerCase().split(" ").filter(Boolean));
}

function stringSimilarity(a, b) {
  if (!a || !b) return 0;
  const tokensA = tokenize(a);
  const tokensB = tokenize(b);
  const intersection = [...tokensA].filter((token) => tokensB.has(token)).length;
  const union = new Set([...tokensA, ...tokensB]).size || 1;
  const jaccard = intersection / union;
  const levenshteinScore = 1 - levenshteinDistance(a.toLowerCase(), b.toLowerCase()) / Math.max(a.length, b.length, 1);
  return Math.max(0, Math.min(1, (jaccard * 0.6 + levenshteinScore * 0.4)));
}

function levenshteinDistance(a, b) {
  const matrix = Array.from({ length: a.length + 1 }, () => new Array(b.length + 1).fill(0));
  for (let i = 0; i <= a.length; i += 1) matrix[i][0] = i;
  for (let j = 0; j <= b.length; j += 1) matrix[0][j] = j;
  for (let i = 1; i <= a.length; i += 1) {
    for (let j = 1; j <= b.length; j += 1) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      matrix[i][j] = Math.min(
        matrix[i - 1][j] + 1,
        matrix[i][j - 1] + 1,
        matrix[i - 1][j - 1] + cost
      );
    }
  }
  return matrix[a.length][b.length];
}

function findGroupedMatch(invoice, usedBank) {
  const candidates = appState.bank
    .map((bank, index) => ({ bank, index }))
    .filter(({ index }) => !usedBank.has(index))
    .sort((a, b) => Math.abs(invoice.amount - a.bank.amount) - Math.abs(invoice.amount - b.bank.amount))
    .slice(0, 40);

  for (let i = 0; i < candidates.length; i += 1) {
    for (let j = i + 1; j < candidates.length; j += 1) {
      const sum = candidates[i].bank.amount + candidates[j].bank.amount;
      const diff = Math.abs(sum - invoice.amount);
      if (diff <= appState.config.amountTolerance) {
        const score = Math.min(1, 0.7 + (1 - diff / Math.max(invoice.amount, 1)) * 0.3);
        return {
          banks: [candidates[i].bank, candidates[j].bank],
          indices: [candidates[i].index, candidates[j].index],
          score,
          amount: sum
        };
      }
    }
  }
  return null;
}

function matchManyToOne(unmatchedInvoices, usedBank) {
  const remaining = [...unmatchedInvoices];
  const matched = [];
  const usedInvoices = new Set();

  appState.bank.forEach((bank, index) => {
    if (usedBank.has(index)) return;
    const candidates = remaining
      .map((invoice, idx) => ({ invoice, idx }))
      .filter(({ idx }) => !usedInvoices.has(idx))
      .sort((a, b) => Math.abs(bank.amount - a.invoice.amount) - Math.abs(bank.amount - b.invoice.amount))
      .slice(0, 40);

    for (let i = 0; i < candidates.length; i += 1) {
      for (let j = i + 1; j < candidates.length; j += 1) {
        const sum = candidates[i].invoice.amount + candidates[j].invoice.amount;
        const diff = Math.abs(sum - bank.amount);
        if (diff <= appState.config.amountTolerance) {
          usedBank.add(index);
          usedInvoices.add(candidates[i].idx);
          usedInvoices.add(candidates[j].idx);
          const invoices = [candidates[i].invoice, candidates[j].invoice];
          matched.push(buildManyToOneRecord(bank, invoices));
          return;
        }
      }
    }
  });

  const stillUnmatched = remaining.filter((_, idx) => !usedInvoices.has(idx));
  return { matched, unmatched: stillUnmatched };
}

function buildMatchRecord(invoice, bank, score, explanation, mode) {
  return {
    type: "matched",
    mode,
    invoice,
    bank,
    score,
    explanation,
    confidence: score >= 0.85 ? "high" : score >= 0.7 ? "medium" : "low"
  };
}

function buildGroupedRecord(invoice, group, mode) {
  return {
    type: "matched",
    mode,
    invoice,
    bank: {
      description: group.banks.map((b) => b.description).join(" | "),
      reference: group.banks.map((b) => b.reference).join(" + "),
      transactionDate: group.banks[0].transactionDate,
      amount: group.amount,
      currency: invoice.currency
    },
    score: group.score,
    explanation: {
      grouped: true,
      referenceHit: false,
      amountDiff: Math.abs(group.amount - invoice.amount).toFixed(2),
      dateGap: "Grouped",
      customerSimilarity: "0"
    },
    confidence: "medium"
  };
}

function buildManyToOneRecord(bank, invoices) {
  return {
    type: "matched",
    mode: "many-to-one",
    invoice: {
      invoiceNumber: invoices.map((inv) => inv.invoiceNumber).join(" + "),
      customerName: invoices.map((inv) => inv.customerName).join(" | "),
      invoiceDate: invoices[0].invoiceDate,
      dueDate: invoices[0].dueDate,
      amount: invoices.reduce((sum, inv) => sum + inv.amount, 0),
      currency: bank.currency,
      reference: invoices.map((inv) => inv.reference).join(" + ")
    },
    bank,
    score: 0.78,
    explanation: {
      grouped: true,
      referenceHit: false,
      amountDiff: Math.abs(bank.amount - invoices.reduce((sum, inv) => sum + inv.amount, 0)).toFixed(2),
      dateGap: "Grouped",
      customerSimilarity: "0"
    },
    confidence: "medium"
  };
}

function buildUnmatchedInvoice(invoice) {
  return { type: "unmatched-invoice", invoice, confidence: "low" };
}

function buildUnmatchedBank(bank) {
  return { type: "unmatched-bank", bank, confidence: "low" };
}

function updateStats() {
  const totalInvoices = appState.invoices.reduce((sum, invoice) => sum + invoice.amount, 0);
  const totalBank = appState.bank.reduce((sum, bank) => sum + bank.amount, 0);
  const matchedAmount = appState.matches.reduce((sum, match) => sum + match.invoice.amount, 0);
  const unmatchedCount = appState.unmatchedInvoices.length + appState.unmatchedBank.length;
  const matchRate = appState.invoices.length
    ? ((appState.matches.length / appState.invoices.length) * 100).toFixed(1)
    : 0;

  const stats = [
    { label: "Total Invoices Amount", value: totalInvoices, delta: `${matchRate}% match rate` },
    { label: "Total Bank Amount", value: totalBank, delta: `Across ${appState.bank.length} records` },
    { label: "Matched Amount", value: matchedAmount, delta: `${appState.matches.length} matches` },
    { label: "Unmatched Count", value: unmatchedCount, delta: "Needs review" }
  ];

  elements.statsGrid.innerHTML = "";
  stats.forEach((stat) => {
    const card = document.createElement("div");
    card.className = "stat-card";
    card.innerHTML = `
      <div class="stat-label">${stat.label}</div>
      <div class="stat-value" data-value="${stat.value}">$0.00</div>
      <div class="delta-chip">${stat.delta}</div>
    `;
    elements.statsGrid.appendChild(card);
    animateNumber(card.querySelector(".stat-value"), stat.value);
  });
}

function animateNumber(element, value) {
  const isCurrency = !Number.isNaN(value);
  const start = 0;
  const duration = 800;
  const startTime = performance.now();

  function step(now) {
    const progress = Math.min(1, (now - startTime) / duration);
    const current = start + (value - start) * progress;
    element.textContent = isCurrency ? formatCurrency(current) : Math.round(current).toString();
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function updateCharts() {
  const mode = appState.ui.chartMode;
  const matchedAmount = appState.matches.reduce((sum, match) => sum + match.invoice.amount, 0);
  const unmatchedAmount = appState.unmatchedInvoices.reduce((sum, item) => sum + item.invoice.amount, 0);
  const matchedCount = appState.matches.length;
  const unmatchedCount = appState.unmatchedInvoices.length;

  const pieData = mode === "amount" ? [matchedAmount, unmatchedAmount] : [matchedCount, unmatchedCount];

  if (!charts.pie) {
    charts.pie = new Chart(elements.pieChart.getContext("2d"), {
      type: "pie",
      data: {
        labels: ["Matched", "Unmatched"],
        datasets: [{
          data: pieData,
          backgroundColor: ["#49f5a8", "#ff7aa2"],
          borderWidth: 0
        }]
      },
      options: {
        plugins: {
          legend: {
            labels: { color: "#fff" }
          }
        }
      }
    });
  } else {
    charts.pie.data.datasets[0].data = pieData;
    charts.pie.update();
  }

  const aging = computeAgingBuckets();
  if (!charts.bar) {
    charts.bar = new Chart(elements.barChart.getContext("2d"), {
      type: "bar",
      data: {
        labels: Object.keys(aging),
        datasets: [{
          label: "Unmatched Invoices",
          data: Object.values(aging),
          backgroundColor: "rgba(109, 241, 255, 0.7)",
          borderRadius: 8
        }]
      },
      options: {
        scales: {
          y: {
            ticks: { color: "#fff" },
            grid: { color: "rgba(255,255,255,0.1)" }
          },
          x: {
            ticks: { color: "#fff" },
            grid: { color: "rgba(255,255,255,0.05)" }
          }
        },
        plugins: { legend: { display: false } }
      }
    });
  } else {
    charts.bar.data.datasets[0].data = Object.values(aging);
    charts.bar.update();
  }
}

function computeAgingBuckets() {
  const buckets = {
    Current: 0,
    "1-30": 0,
    "31-60": 0,
    "61-90": 0,
    "91-180": 0,
    "181-360": 0,
    "361+": 0
  };
  const today = new Date();
  appState.unmatchedInvoices.forEach(({ invoice }) => {
    const due = new Date(invoice.dueDate || invoice.invoiceDate);
    const diff = Math.floor((today - due) / (1000 * 60 * 60 * 24));
    if (diff <= 0) buckets.Current += 1;
    else if (diff <= 30) buckets["1-30"] += 1;
    else if (diff <= 60) buckets["31-60"] += 1;
    else if (diff <= 90) buckets["61-90"] += 1;
    else if (diff <= 180) buckets["91-180"] += 1;
    else if (diff <= 360) buckets["181-360"] += 1;
    else buckets["361+"] += 1;
  });
  return buckets;
}

function renderTable() {
  let rows = [];
  if (appState.ui.activeTab === "matched") rows = [...appState.matches];
  if (appState.ui.activeTab === "unmatched-invoices") rows = [...appState.unmatchedInvoices];
  if (appState.ui.activeTab === "unmatched-bank") rows = [...appState.unmatchedBank];

  rows = applyFilters(rows);
  rows = applySort(rows);

  elements.resultsBody.innerHTML = "";
  if (!rows.length) {
    elements.emptyState.hidden = false;
    return;
  }
  elements.emptyState.hidden = true;

  rows.forEach((row, index) => {
    const mainRow = document.createElement("tr");
    const drawerRow = document.createElement("tr");
    drawerRow.className = "drawer";
    drawerRow.hidden = true;

    const data = buildRowData(row);
    mainRow.innerHTML = `
      <td>
        <div>${data.title}</div>
        <div class="muted">${data.subtitle}</div>
      </td>
      <td>${formatCurrency(data.amount, data.currency)}</td>
      <td>${data.date}</td>
      <td>${data.score}</td>
      <td>${data.reference}</td>
      <td><span class="status ${data.confidence}">${data.confidence.toUpperCase()}</span></td>
      <td><button class="row-expand" data-index="${index}" aria-label="Expand row">Details</button></td>
    `;

    drawerRow.innerHTML = `
      <td colspan="7">
        <div class="drawer-content">
          ${data.details}
        </div>
      </td>
    `;

    elements.resultsBody.appendChild(mainRow);
    elements.resultsBody.appendChild(drawerRow);
  });

  elements.resultsBody.querySelectorAll(".row-expand").forEach((button, idx) => {
    button.addEventListener("click", () => {
      const drawer = elements.resultsBody.querySelectorAll(".drawer")[idx];
      drawer.hidden = !drawer.hidden;
    });
  });
}

function applyFilters(rows) {
  return rows.filter((row) => {
    const data = buildRowData(row);
    const search = appState.ui.search;
    if (search) {
      const haystack = `${data.title} ${data.subtitle} ${data.reference}`.toLowerCase();
      if (!haystack.includes(search)) return false;
    }
    if (appState.ui.currency !== "all" && data.currency !== appState.ui.currency) return false;
    if (appState.ui.dateFrom && data.date < appState.ui.dateFrom) return false;
    if (appState.ui.dateTo && data.date > appState.ui.dateTo) return false;
    return true;
  });
}

function applySort(rows) {
  const [field, direction] = appState.ui.sort.split("-");
  const sorted = [...rows];
  sorted.sort((a, b) => {
    const dataA = buildRowData(a);
    const dataB = buildRowData(b);
    let diff = 0;
    if (field === "score") diff = dataA.scoreValue - dataB.scoreValue;
    if (field === "amount") diff = dataA.amount - dataB.amount;
    if (field === "date") diff = dataA.date.localeCompare(dataB.date);
    return direction === "asc" ? diff : -diff;
  });
  return sorted;
}

function buildRowData(row) {
  if (row.type === "matched") {
    return {
      title: row.invoice.invoiceNumber,
      subtitle: row.invoice.customerName || row.bank.description,
      amount: row.invoice.amount,
      currency: row.invoice.currency,
      date: row.invoice.invoiceDate,
      score: `${Math.round(row.score * 100)}%`,
      scoreValue: row.score,
      reference: row.bank.reference || row.invoice.reference,
      confidence: row.confidence,
      details: `
        <strong>Match Mode:</strong> ${row.mode}<br />
        <strong>Reference Hit:</strong> ${row.explanation?.referenceHit ? "Yes" : "No"}<br />
        <strong>Amount Difference:</strong> ${row.explanation?.amountDiff}<br />
        <strong>Date Gap:</strong> ${row.explanation?.dateGap} days<br />
        <strong>Breakdown:</strong> Ref ${row.explanation?.breakdown?.reference || "0"}, Amount ${row.explanation?.breakdown?.amount || "0"}, Date ${row.explanation?.breakdown?.date || "0"}, Customer ${row.explanation?.breakdown?.customer || "0"}
      `
    };
  }

  if (row.type === "unmatched-invoice") {
    return {
      title: row.invoice.invoiceNumber,
      subtitle: row.invoice.customerName,
      amount: row.invoice.amount,
      currency: row.invoice.currency,
      date: row.invoice.invoiceDate,
      score: "0%",
      scoreValue: 0,
      reference: row.invoice.reference,
      confidence: row.confidence,
      details: "No matching bank transaction found within tolerance."
    };
  }

  return {
    title: row.bank.bankId,
    subtitle: row.bank.description,
    amount: row.bank.amount,
    currency: row.bank.currency,
    date: row.bank.transactionDate,
    score: "0%",
    scoreValue: 0,
    reference: row.bank.reference,
    confidence: row.confidence,
    details: "No matching invoice found for this bank transaction."
  };
}

function formatCurrency(value, currency = "USD") {
  if (Number.isNaN(value)) return "-";
  const safeCurrency = currency && currency.length === 3 ? currency : "USD";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: safeCurrency,
    maximumFractionDigits: 2
  }).format(value);
}

function exportReport() {
  if (!appState.matches.length && !appState.unmatchedInvoices.length) {
    showToast("No data to export.", "warning");
    return;
  }
  const workbook = XLSX.utils.book_new();
  const summary = [
    ["AR Reconciliation Engine Report"],
    ["Generated", new Date().toLocaleString()],
    [""],
    ["Total Invoices", appState.invoices.length],
    ["Total Bank Records", appState.bank.length],
    ["Matched", appState.matches.length],
    ["Unmatched Invoices", appState.unmatchedInvoices.length],
    ["Unmatched Bank", appState.unmatchedBank.length],
    [""],
    ["Settings"],
    ["Tolerance", appState.config.amountTolerance],
    ["Date Window", appState.config.dateWindow],
    ["Threshold", appState.config.threshold],
    ["Allow Variance", appState.config.allowVariance ? "Yes" : "No"],
    ["Grouping Mode", appState.config.enableGrouping ? "Yes" : "No"]
  ];

  const summarySheet = XLSX.utils.aoa_to_sheet(summary);
  XLSX.utils.book_append_sheet(workbook, summarySheet, "Summary");

  const matchedRows = appState.matches.map((match) => ({
    Invoice: match.invoice.invoiceNumber,
    Customer: match.invoice.customerName,
    InvoiceDate: match.invoice.invoiceDate,
    DueDate: match.invoice.dueDate,
    Amount: match.invoice.amount,
    Currency: match.invoice.currency,
    BankReference: match.bank.reference,
    BankDescription: match.bank.description,
    BankDate: match.bank.transactionDate,
    Score: Math.round(match.score * 100),
    Explanation: `Ref:${match.explanation?.breakdown?.reference} Amount:${match.explanation?.breakdown?.amount} Date:${match.explanation?.breakdown?.date}`
  }));

  const unmatchedInvoiceRows = appState.unmatchedInvoices.map((item) => ({
    Invoice: item.invoice.invoiceNumber,
    Customer: item.invoice.customerName,
    InvoiceDate: item.invoice.invoiceDate,
    DueDate: item.invoice.dueDate,
    Amount: item.invoice.amount,
    Currency: item.invoice.currency,
    Reference: item.invoice.reference
  }));

  const unmatchedBankRows = appState.unmatchedBank.map((item) => ({
    BankId: item.bank.bankId,
    Description: item.bank.description,
    TransactionDate: item.bank.transactionDate,
    Amount: item.bank.amount,
    Currency: item.bank.currency,
    Reference: item.bank.reference
  }));

  XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(matchedRows), "Matched");
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(unmatchedInvoiceRows), "Unmatched Invoices");
  XLSX.utils.book_append_sheet(workbook, XLSX.utils.json_to_sheet(unmatchedBankRows), "Unmatched Bank");

  XLSX.writeFile(workbook, `AR_Reconciliation_Report_${todayString()}.xlsx`);
  showToast("Export completed.", "success");
}

function generateSampleData() {
  const invoices = [];
  const bank = [];
  const currencies = ["USD", "EUR", "GBP"];
  for (let i = 1; i <= 60; i += 1) {
    const amount = Number((Math.random() * 9000 + 300).toFixed(2));
    const date = new Date();
    date.setDate(date.getDate() - Math.floor(Math.random() * 40));
    const due = new Date(date);
    due.setDate(due.getDate() + 20);
    invoices.push({
      invoiceNumber: `INV-${String(i).padStart(5, "0")}`,
      customerName: `Customer ${String.fromCharCode(65 + (i % 26))}`,
      invoiceDate: date.toISOString().split("T")[0],
      dueDate: due.toISOString().split("T")[0],
      amount,
      currency: currencies[i % currencies.length],
      reference: `REF-${String(i).padStart(4, "0")}`
    });
  }

  invoices.forEach((invoice, index) => {
    if (index % 5 !== 0) {
      bank.push({
        transactionDate: invoice.invoiceDate,
        description: `${invoice.customerName} payment`,
        amount: invoice.amount + (Math.random() > 0.8 ? 0.5 : 0),
        currency: invoice.currency,
        reference: invoice.reference,
        bankId: `BANK-${String(index + 1).padStart(5, "0")}`
      });
    }
  });

  appState.invoices = invoices;
  appState.bank = bank;
  elements.invoiceRows.textContent = `${invoices.length} rows`;
  elements.bankRows.textContent = `${bank.length} rows`;
  elements.invoiceName.textContent = "Sample_Invoices.xlsx";
  elements.bankName.textContent = "Sample_Bank.xlsx";
  updateCurrencyFilter();
  showToast("Sample data loaded.", "success");
}

function resetWorkspace() {
  appState.invoices = [];
  appState.bank = [];
  appState.matches = [];
  appState.unmatchedInvoices = [];
  appState.unmatchedBank = [];
  elements.invoiceName.textContent = "No file selected";
  elements.bankName.textContent = "No file selected";
  elements.invoiceRows.textContent = "0 rows";
  elements.bankRows.textContent = "0 rows";
  elements.invoiceSheet.innerHTML = "<option value=\"\">Select sheet</option>";
  elements.bankSheet.innerHTML = "<option value=\"\">Select sheet</option>";
  renderTable();
  updateStats();
  updateCharts();
  showToast("Workspace reset.", "warning");
}

function showToast(message, type) {
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  elements.toastStack.appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
