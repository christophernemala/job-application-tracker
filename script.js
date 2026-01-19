const appState = {
  invoice: { file: null, workbook: null, sheet: null, rows: [], mapped: [], headers: [] },
  bank: { file: null, workbook: null, sheet: null, rows: [], mapped: [], headers: [] },
  results: { matched: [], unmatchedInvoices: [], unmatchedBank: [] },
  settings: {
    threshold: 0.75,
    tolerance: 0.01,
    allowVariance: false,
    grouping: false,
    dateWindow: 7,
    useCustomer: true
  },
  chartMode: "amount",
  charts: { pie: null, bar: null },
  activeTab: "matched",
  search: "",
  currency: "",
  dateFrom: "",
  dateTo: "",
  sortBy: "score",
  cancel: false
};

const headerDictionary = {
  invoiceNumber: ["invoice", "invoice number", "invoice no", "inv", "inv no", "number"],
  customerName: ["customer", "client", "account", "customer name", "name"],
  invoiceDate: ["invoice date", "date", "inv date"],
  dueDate: ["due date", "due", "payment due"],
  amount: ["amount", "total", "invoice amount", "value"],
  currency: ["currency", "ccy", "curr"],
  reference: ["reference", "ref", "memo", "payment ref"]
};

const bankDictionary = {
  transactionDate: ["transaction date", "date", "value date", "posted"],
  description: ["description", "details", "narrative", "memo"],
  amount: ["amount", "value", "payment"],
  currency: ["currency", "ccy", "curr"],
  reference: ["reference", "ref", "payment ref"],
  bankId: ["bank id", "id", "transaction id"]
};

const elements = {
  invoiceFile: document.getElementById("invoiceFile"),
  bankFile: document.getElementById("bankFile"),
  invoiceMeta: document.getElementById("invoiceMeta"),
  bankMeta: document.getElementById("bankMeta"),
  invoiceSheet: document.getElementById("invoiceSheet"),
  bankSheet: document.getElementById("bankSheet"),
  thresholdRange: document.getElementById("thresholdRange"),
  thresholdValue: document.getElementById("thresholdValue"),
  toleranceValue: document.getElementById("toleranceValue"),
  allowVariance: document.getElementById("allowVariance"),
  enableGrouping: document.getElementById("enableGrouping"),
  dateWindow: document.getElementById("dateWindow"),
  useCustomer: document.getElementById("useCustomer"),
  startRecon: document.getElementById("startRecon"),
  engineSection: document.getElementById("engineSection"),
  engineStatus: document.getElementById("engineStatus"),
  progressBar: document.getElementById("progressBar"),
  cancelRecon: document.getElementById("cancelRecon"),
  resetRecon: document.getElementById("resetRecon"),
  statsGrid: document.getElementById("statsGrid"),
  analytics: document.getElementById("analytics"),
  charts: document.getElementById("charts"),
  results: document.getElementById("results"),
  exportSection: document.getElementById("export"),
  searchInput: document.getElementById("searchInput"),
  currencyFilter: document.getElementById("currencyFilter"),
  dateFrom: document.getElementById("dateFrom"),
  dateTo: document.getElementById("dateTo"),
  sortBy: document.getElementById("sortBy"),
  tableHead: document.getElementById("tableHead"),
  tableBody: document.getElementById("tableBody"),
  emptyState: document.getElementById("emptyState"),
  mappingModal: document.getElementById("mappingModal"),
  mappingBody: document.getElementById("mappingBody"),
  applyMapping: document.getElementById("applyMapping"),
  helpModal: document.getElementById("helpModal"),
  toastContainer: document.getElementById("toastContainer"),
  themeToggle: document.getElementById("themeToggle"),
  helpToggle: document.getElementById("helpToggle"),
  sampleData: document.getElementById("sampleData"),
  exportBtn: document.getElementById("exportBtn"),
  exportExcel: document.getElementById("exportExcel")
};

let pendingMapping = null;

const formatMoney = (value, currency = "USD") => {
  const safe = Number.isFinite(value) ? value : 0;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency
  }).format(safe);
};

const toISO = (date) => {
  if (!date) return "";
  if (date instanceof Date && !Number.isNaN(date.getTime())) {
    return date.toISOString().slice(0, 10);
  }
  const parsed = new Date(date);
  if (!Number.isNaN(parsed.getTime())) {
    return parsed.toISOString().slice(0, 10);
  }
  return "";
};

const parseExcelDate = (value) => {
  if (typeof value === "number") {
    const utcDays = Math.floor(value - 25569);
    const date = new Date(utcDays * 86400 * 1000);
    return toISO(date);
  }
  return toISO(value);
};

const parseMoney = (value) => {
  if (value === null || value === undefined) return 0;
  if (typeof value === "number") return value;
  const cleaned = String(value)
    .replace(/[^0-9.-]+/g, "")
    .replace(/(\..*)\./g, "$1");
  const parsed = parseFloat(cleaned);
  return Number.isNaN(parsed) ? 0 : parsed;
};

const cleanRef = (value) =>
  String(value || "")
    .replace(/\s+/g, " ")
    .trim()
    .toUpperCase();

const tokenize = (value) =>
  cleanRef(value)
    .split(/[\s,./_-]+/)
    .filter(Boolean);

const jaccard = (a, b) => {
  const setA = new Set(tokenize(a));
  const setB = new Set(tokenize(b));
  if (!setA.size && !setB.size) return 0;
  const intersection = [...setA].filter((x) => setB.has(x)).length;
  const union = new Set([...setA, ...setB]).size;
  return union ? intersection / union : 0;
};

const levenshteinLite = (a, b) => {
  const s = cleanRef(a);
  const t = cleanRef(b);
  if (!s && !t) return 0;
  const matrix = Array.from({ length: s.length + 1 }, () => []);
  for (let i = 0; i <= s.length; i += 1) matrix[i][0] = i;
  for (let j = 0; j <= t.length; j += 1) matrix[0][j] = j;
  for (let i = 1; i <= s.length; i += 1) {
    for (let j = 1; j <= t.length; j += 1) {
      const cost = s[i - 1] === t[j - 1] ? 0 : 1;
      matrix[i][j] = Math.min(
        matrix[i - 1][j] + 1,
        matrix[i][j - 1] + 1,
        matrix[i - 1][j - 1] + cost
      );
    }
  }
  return matrix[s.length][t.length];
};

const similarityScore = (a, b) => {
  const jac = jaccard(a, b);
  const lev = levenshteinLite(a, b);
  const maxLen = Math.max(cleanRef(a).length, cleanRef(b).length) || 1;
  const levScore = 1 - lev / maxLen;
  return (jac * 0.6 + levScore * 0.4);
};

const detectMapping = (headers, dictionary) => {
  const map = {};
  Object.keys(dictionary).forEach((key) => {
    const synonyms = dictionary[key];
    const match = headers.find((header) =>
      synonyms.some((syn) => header.includes(syn))
    );
    if (match) map[key] = match;
  });
  return map;
};

const headersFromRows = (rows) =>
  rows.length ? Object.keys(rows[0]).map((h) => h.trim().toLowerCase()) : [];

const openModal = (modal) => {
  modal.hidden = false;
  modal.setAttribute("aria-hidden", "false");
};

const closeModal = (modal) => {
  modal.hidden = true;
  modal.setAttribute("aria-hidden", "true");
};

const showToast = (message, type = "info") => {
  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  toast.dataset.type = type;
  elements.toastContainer.appendChild(toast);
  setTimeout(() => toast.remove(), 3500);
};

const setProgress = (value, text) => {
  elements.progressBar.style.width = `${value}%`;
  typewriter(text, elements.engineStatus);
};

const typewriter = (text, target) => {
  let index = 0;
  target.textContent = "";
  const step = () => {
    if (index <= text.length) {
      target.textContent = text.slice(0, index);
      index += 1;
      requestAnimationFrame(step);
    }
  };
  step();
};

const updateSettings = () => {
  appState.settings.threshold = parseFloat(elements.thresholdRange.value);
  appState.settings.tolerance = parseFloat(elements.toleranceValue.value) || 0.01;
  appState.settings.allowVariance = elements.allowVariance.checked;
  appState.settings.grouping = elements.enableGrouping.checked;
  appState.settings.dateWindow = parseInt(elements.dateWindow.value, 10) || 7;
  appState.settings.useCustomer = elements.useCustomer.checked;
  elements.thresholdValue.textContent = appState.settings.threshold.toFixed(2);
};

const loadWorkbook = async (file) => {
  const data = await file.arrayBuffer();
  return XLSX.read(data, { type: "array" });
};

const updateSheetSelect = (select, workbook) => {
  select.innerHTML = "";
  workbook.SheetNames.forEach((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name;
    select.appendChild(option);
  });
  select.disabled = workbook.SheetNames.length <= 1;
};

const readSheet = (workbook, sheetName) => {
  const sheet = workbook.Sheets[sheetName];
  return XLSX.utils.sheet_to_json(sheet, { defval: "" });
};

const normalizeInvoices = (rows, mapping) =>
  rows.map((row, index) => {
    const amount = parseMoney(row[mapping.amount]);
    const currency = (row[mapping.currency] || "USD").toString().toUpperCase();
    return {
      id: `INV-${index + 1}`,
      invoiceNumber: cleanRef(row[mapping.invoiceNumber] || row[mapping.reference] || `INV-${index + 1}`),
      customerName: cleanRef(row[mapping.customerName] || ""),
      invoiceDate: parseExcelDate(row[mapping.invoiceDate]),
      dueDate: parseExcelDate(row[mapping.dueDate]) || parseExcelDate(row[mapping.invoiceDate]),
      amount,
      currency,
      reference: cleanRef(row[mapping.reference] || row[mapping.invoiceNumber] || "")
    };
  });

const normalizeBank = (rows, mapping) =>
  rows.map((row, index) => {
    const amount = parseMoney(row[mapping.amount]);
    const currency = (row[mapping.currency] || "USD").toString().toUpperCase();
    return {
      id: `BNK-${index + 1}`,
      transactionDate: parseExcelDate(row[mapping.transactionDate]),
      description: cleanRef(row[mapping.description] || ""),
      amount,
      currency,
      reference: cleanRef(row[mapping.reference] || row[mapping.bankId] || ""),
      bankId: cleanRef(row[mapping.bankId] || `BNK-${index + 1}`)
    };
  });

const validateHeaders = (headers, dictionary) => {
  const mapping = detectMapping(headers, dictionary);
  const required = Object.keys(dictionary);
  const missing = required.filter((key) => !mapping[key]);
  return { mapping, missing };
};

const buildMappingModal = (headers, dictionary, currentMapping, type) => {
  elements.mappingBody.innerHTML = "";
  Object.keys(dictionary).forEach((field) => {
    const label = document.createElement("label");
    label.textContent = field;
    const select = document.createElement("select");
    select.dataset.field = field;
    const empty = document.createElement("option");
    empty.value = "";
    empty.textContent = "--";
    select.appendChild(empty);
    headers.forEach((header) => {
      const opt = document.createElement("option");
      opt.value = header;
      opt.textContent = header;
      if (currentMapping[field] === header) opt.selected = true;
      select.appendChild(opt);
    });
    label.appendChild(select);
    elements.mappingBody.appendChild(label);
  });
  pendingMapping = { type, headers, dictionary };
  openModal(elements.mappingModal);
};

const applyMapping = () => {
  if (!pendingMapping) return;
  const { type } = pendingMapping;
  const selected = {};
  elements.mappingBody.querySelectorAll("select").forEach((select) => {
    if (select.value) selected[select.dataset.field] = select.value;
  });
  if (type === "invoice") {
    appState.invoice.mapped = normalizeInvoices(appState.invoice.rows, selected);
  } else {
    appState.bank.mapped = normalizeBank(appState.bank.rows, selected);
  }
  pendingMapping = null;
  closeModal(elements.mappingModal);
  showToast("Mapping applied.");
  toggleReconReady();
};

const toggleReconReady = () => {
  const ready = appState.invoice.mapped.length && appState.bank.mapped.length;
  elements.startRecon.disabled = !ready;
};

const handleFile = async (type, file) => {
  try {
    const workbook = await loadWorkbook(file);
    const state = type === "invoice" ? appState.invoice : appState.bank;
    state.file = file;
    state.workbook = workbook;
    updateSheetSelect(type === "invoice" ? elements.invoiceSheet : elements.bankSheet, workbook);
    const sheetName = workbook.SheetNames[0];
    state.sheet = sheetName;
    const rows = readSheet(workbook, sheetName);
    state.rows = rows;
    state.headers = headersFromRows(rows);
    const dictionary = type === "invoice" ? headerDictionary : bankDictionary;
    const { mapping, missing } = validateHeaders(state.headers, dictionary);
    if (missing.length) {
      buildMappingModal(state.headers, dictionary, mapping, type);
    } else {
      if (type === "invoice") {
        state.mapped = normalizeInvoices(rows, mapping);
      } else {
        state.mapped = normalizeBank(rows, mapping);
      }
      showToast(`${file.name} parsed successfully.`);
      toggleReconReady();
    }
  } catch (error) {
    showToast("Failed to parse file.", "error");
  }
};

const handleSheetChange = (type) => {
  const state = type === "invoice" ? appState.invoice : appState.bank;
  const select = type === "invoice" ? elements.invoiceSheet : elements.bankSheet;
  const sheetName = select.value;
  state.sheet = sheetName;
  const rows = readSheet(state.workbook, sheetName);
  state.rows = rows;
  state.headers = headersFromRows(rows);
  const dictionary = type === "invoice" ? headerDictionary : bankDictionary;
  const { mapping, missing } = validateHeaders(state.headers, dictionary);
  if (missing.length) {
    buildMappingModal(state.headers, dictionary, mapping, type);
  } else {
    if (type === "invoice") {
      state.mapped = normalizeInvoices(rows, mapping);
    } else {
      state.mapped = normalizeBank(rows, mapping);
    }
    showToast("Sheet updated.");
    toggleReconReady();
  }
};

const matchScore = (invoice, bank) => {
  const refMatch = similarityScore(invoice.reference, bank.reference || bank.description);
  const invMatch = similarityScore(invoice.invoiceNumber, bank.description || bank.reference);
  const refScore = Math.max(refMatch, invMatch);

  const amountDiff = Math.abs(invoice.amount - bank.amount);
  const amountTolerance = appState.settings.tolerance;
  const amountPass = amountDiff <= amountTolerance || appState.settings.allowVariance;
  const amountScore = amountPass
    ? 1 - Math.min(amountDiff / Math.max(invoice.amount, 1), 1)
    : 0;

  const dateInv = new Date(invoice.invoiceDate || invoice.dueDate || Date.now());
  const dateBank = new Date(bank.transactionDate || Date.now());
  const dayDiff = Math.abs((dateInv - dateBank) / 86400000);
  const dateScore = Math.max(0, 1 - dayDiff / Math.max(appState.settings.dateWindow, 1));

  const customerScore = appState.settings.useCustomer
    ? similarityScore(invoice.customerName, bank.description)
    : 0;

  const score = 0.5 * refScore + 0.25 * amountScore + 0.15 * dateScore + 0.1 * customerScore;

  return {
    score,
    amountPass,
    explanation: {
      reference: refScore,
      amount: amountScore,
      date: dateScore,
      customer: customerScore,
      dayDiff: Math.round(dayDiff)
    }
  };
};

const reconcile = async () => {
  appState.cancel = false;
  elements.engineSection.hidden = false;
  setProgress(10, "Parsing and validating... ");
  await wait(300);
  setProgress(25, "Normalizing transactions... ");
  await wait(300);
  setProgress(45, "Scoring potential matches... ");

  const matched = [];
  const unmatchedInvoices = [];
  const unmatchedBank = [...appState.bank.mapped];
  const usedBank = new Set();

  const invoices = appState.invoice.mapped;
  const chunkSize = 250;

  for (let i = 0; i < invoices.length; i += chunkSize) {
    if (appState.cancel) return;
    const chunk = invoices.slice(i, i + chunkSize);
    chunk.forEach((invoice) => {
      let best = null;
      appState.bank.mapped.forEach((bank, index) => {
        if (usedBank.has(index)) return;
        const result = matchScore(invoice, bank);
        if (!best || result.score > best.score) {
          best = { ...result, bank, index };
        }
      });
      if (best && best.score >= appState.settings.threshold && best.amountPass) {
        usedBank.add(best.index);
        unmatchedBank.splice(unmatchedBank.findIndex((b) => b.id === best.bank.id), 1);
        matched.push({
          invoice,
          bank: best.bank,
          score: best.score,
          explanation: best.explanation
        });
      } else {
        unmatchedInvoices.push({ invoice, candidate: best });
      }
    });
    setProgress(45 + Math.round((i / invoices.length) * 40), "Matching transactions... ");
    await wait(10);
  }

  if (appState.settings.grouping) {
    setProgress(85, "Evaluating group matches... ");
    const groupMatches = groupMatch(unmatchedInvoices, unmatchedBank);
    groupMatches.matched.forEach((match) => matched.push(match));
    appState.results.unmatchedInvoices = groupMatches.unmatchedInvoices;
    appState.results.unmatchedBank = groupMatches.unmatchedBank;
  } else {
    appState.results.unmatchedInvoices = unmatchedInvoices;
    appState.results.unmatchedBank = unmatchedBank;
  }

  appState.results.matched = matched;
  setProgress(100, "Report compiled. Ready.");
  showToast("Reconciliation complete.");
};

const groupMatch = (unmatchedInvoices, unmatchedBank) => {
  const matched = [];
  const remainingBank = [...unmatchedBank];
  const remainingInvoices = [];

  unmatchedInvoices.forEach(({ invoice }) => {
    let paired = null;
    for (let i = 0; i < remainingBank.length; i += 1) {
      for (let j = i + 1; j < remainingBank.length; j += 1) {
        const sum = remainingBank[i].amount + remainingBank[j].amount;
        const diff = Math.abs(sum - invoice.amount);
        if (diff <= appState.settings.tolerance) {
          const combinedDesc = `${remainingBank[i].description} ${remainingBank[j].description}`;
          const result = matchScore(invoice, { ...remainingBank[i], amount: sum, description: combinedDesc });
          if (result.score >= appState.settings.threshold) {
            paired = { banks: [remainingBank[i], remainingBank[j]], result };
            break;
          }
        }
      }
      if (paired) break;
    }
    if (paired) {
      paired.banks.forEach((bank) => {
        const index = remainingBank.findIndex((item) => item.id === bank.id);
        if (index >= 0) remainingBank.splice(index, 1);
      });
      matched.push({
        invoice,
        bank: {
          id: paired.banks.map((b) => b.id).join(" + "),
          transactionDate: paired.banks[0].transactionDate,
          description: paired.banks.map((b) => b.description).join(" | "),
          amount: paired.banks.reduce((sum, b) => sum + b.amount, 0),
          currency: paired.banks[0].currency,
          reference: paired.banks.map((b) => b.reference).join(" | "),
          bankId: paired.banks.map((b) => b.bankId).join(" | ")
        },
        score: paired.result.score,
        explanation: paired.result.explanation
      });
    } else {
      remainingInvoices.push({ invoice, candidate: null });
    }
  });

  return { matched, unmatchedInvoices: remainingInvoices, unmatchedBank: remainingBank };
};

const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const renderStats = () => {
  const totalInvoices = appState.invoice.mapped.length;
  const totalBank = appState.bank.mapped.length;
  const matchedCount = appState.results.matched.length;
  const unmatchedCount = appState.results.unmatchedInvoices.length + appState.results.unmatchedBank.length;

  const totalInvoiceAmount = appState.invoice.mapped.reduce((sum, row) => sum + row.amount, 0);
  const totalBankAmount = appState.bank.mapped.reduce((sum, row) => sum + row.amount, 0);
  const matchedAmount = appState.results.matched.reduce((sum, row) => sum + row.invoice.amount, 0);

  elements.statsGrid.innerHTML = [
    { label: "Total Invoices Amount", value: formatMoney(totalInvoiceAmount), delta: `${totalInvoices} invoices` },
    { label: "Total Bank Amount", value: formatMoney(totalBankAmount), delta: `${totalBank} entries` },
    { label: "Matched Amount", value: formatMoney(matchedAmount), delta: `${matchedCount} matches` },
    { label: "Unmatched Count", value: unmatchedCount.toString(), delta: "Review backlog" }
  ]
    .map(
      (card) => `
      <div class="stat-card">
        <div class="label">${card.label}</div>
        <div class="value">${card.value}</div>
        <div class="delta positive">${card.delta}</div>
      </div>
    `
    )
    .join("");
};

const renderCharts = () => {
  const matchedCount = appState.results.matched.length;
  const unmatchedCount = appState.results.unmatchedInvoices.length + appState.results.unmatchedBank.length;
  const matchedAmount = appState.results.matched.reduce((sum, row) => sum + row.invoice.amount, 0);
  const unmatchedAmount = appState.results.unmatchedInvoices.reduce((sum, row) => sum + row.invoice.amount, 0);

  const pieData = appState.chartMode === "amount"
    ? [matchedAmount, unmatchedAmount]
    : [matchedCount, unmatchedCount];

  if (appState.charts.pie) appState.charts.pie.destroy();
  if (appState.charts.bar) appState.charts.bar.destroy();

  appState.charts.pie = new Chart(document.getElementById("pieChart"), {
    type: "pie",
    data: {
      labels: ["Matched", "Unmatched"],
      datasets: [
        {
          data: pieData,
          backgroundColor: ["#5dff9f", "#ff5a7f"]
        }
      ]
    },
    options: {
      plugins: {
        legend: { labels: { color: "#e6eeff" } }
      }
    }
  });

  const buckets = ["Current", "1-30", "31-60", "61-90", "91-180", "181-360", "361+"];
  const bucketCounts = buckets.map(() => 0);
  const today = new Date();

  appState.results.unmatchedInvoices.forEach(({ invoice }) => {
    const due = new Date(invoice.dueDate || invoice.invoiceDate || Date.now());
    const diff = Math.floor((today - due) / 86400000);
    let index = 0;
    if (diff <= 0) index = 0;
    else if (diff <= 30) index = 1;
    else if (diff <= 60) index = 2;
    else if (diff <= 90) index = 3;
    else if (diff <= 180) index = 4;
    else if (diff <= 360) index = 5;
    else index = 6;
    bucketCounts[index] += 1;
  });

  appState.charts.bar = new Chart(document.getElementById("barChart"), {
    type: "bar",
    data: {
      labels: buckets,
      datasets: [
        {
          label: "Invoices",
          data: bucketCounts,
          backgroundColor: "rgba(108, 246, 255, 0.7)",
          borderRadius: 8
        }
      ]
    },
    options: {
      plugins: { legend: { display: false } },
      scales: {
        x: { ticks: { color: "#e6eeff" } },
        y: { ticks: { color: "#e6eeff" } }
      }
    }
  });
};

const renderTable = () => {
  const { activeTab } = appState;
  const rows = getFilteredRows();
  if (!rows.length) {
    elements.tableBody.innerHTML = "";
    elements.emptyState.hidden = false;
    return;
  }
  elements.emptyState.hidden = true;

  if (activeTab === "matched") {
    elements.tableHead.innerHTML = `
      <tr>
        <th>Invoice</th>
        <th>Customer</th>
        <th>Amount</th>
        <th>Score</th>
        <th>Bank Ref</th>
        <th>Status</th>
      </tr>
    `;
    elements.tableBody.innerHTML = rows
      .map((row, index) => {
        const badge = scoreBadge(row.score);
        return `
        <tr class="data-row" data-index="${index}">
          <td>${row.invoice.invoiceNumber}</td>
          <td>${row.invoice.customerName || "-"}</td>
          <td>${formatMoney(row.invoice.amount, row.invoice.currency)}</td>
          <td><span class="badge-pill ${badge.class}">${badge.label}</span></td>
          <td>${row.bank.reference || row.bank.bankId}</td>
          <td>Matched</td>
        </tr>
        <tr class="details" data-details="${index}" hidden>
          <td colspan="6">
            <strong>Explanation:</strong>
            Ref ${Math.round(row.explanation.reference * 100)}% · Amount ${Math.round(
          row.explanation.amount * 100
        )}% · Date ${Math.round(row.explanation.date * 100)}% · Customer ${Math.round(
          row.explanation.customer * 100
        )}% · Day Δ ${row.explanation.dayDiff}
          </td>
        </tr>
      `;
      })
      .join("");
  } else if (activeTab === "unmatchedInvoices") {
    elements.tableHead.innerHTML = `
      <tr>
        <th>Invoice</th>
        <th>Customer</th>
        <th>Amount</th>
        <th>Due</th>
        <th>Candidate Score</th>
      </tr>
    `;
    elements.tableBody.innerHTML = rows
      .map((row, index) => {
        const score = row.candidate ? row.candidate.score : 0;
        const badge = scoreBadge(score);
        return `
        <tr class="data-row" data-index="${index}">
          <td>${row.invoice.invoiceNumber}</td>
          <td>${row.invoice.customerName || "-"}</td>
          <td>${formatMoney(row.invoice.amount, row.invoice.currency)}</td>
          <td>${row.invoice.dueDate || "-"}</td>
          <td><span class="badge-pill ${badge.class}">${badge.label}</span></td>
        </tr>
      `;
      })
      .join("");
  } else {
    elements.tableHead.innerHTML = `
      <tr>
        <th>Bank ID</th>
        <th>Description</th>
        <th>Amount</th>
        <th>Date</th>
        <th>Currency</th>
      </tr>
    `;
    elements.tableBody.innerHTML = rows
      .map(
        (row) => `
        <tr>
          <td>${row.bankId}</td>
          <td>${row.description}</td>
          <td>${formatMoney(row.amount, row.currency)}</td>
          <td>${row.transactionDate}</td>
          <td>${row.currency}</td>
        </tr>
      `
      )
      .join("");
  }
};

const scoreBadge = (score) => {
  if (score >= 0.85) return { class: "high", label: "High" };
  if (score >= 0.65) return { class: "medium", label: "Medium" };
  return { class: "low", label: "Low" };
};

const getFilteredRows = () => {
  let rows = [];
  if (appState.activeTab === "matched") rows = [...appState.results.matched];
  if (appState.activeTab === "unmatchedInvoices") rows = [...appState.results.unmatchedInvoices];
  if (appState.activeTab === "unmatchedBank") rows = [...appState.results.unmatchedBank];

  if (appState.search) {
    const query = appState.search.toLowerCase();
    rows = rows.filter((row) => {
      const target = appState.activeTab === "unmatchedBank"
        ? `${row.description} ${row.reference} ${row.bankId}`
        : `${row.invoice.invoiceNumber} ${row.invoice.customerName} ${row.invoice.reference}`;
      return target.toLowerCase().includes(query);
    });
  }

  if (appState.currency) {
    rows = rows.filter((row) => {
      const curr = appState.activeTab === "unmatchedBank" ? row.currency : row.invoice.currency;
      return curr === appState.currency;
    });
  }

  if (appState.dateFrom || appState.dateTo) {
    rows = rows.filter((row) => {
      const dateStr = appState.activeTab === "unmatchedBank" ? row.transactionDate : row.invoice.invoiceDate;
      if (!dateStr) return false;
      const date = new Date(dateStr);
      const from = appState.dateFrom ? new Date(appState.dateFrom) : null;
      const to = appState.dateTo ? new Date(appState.dateTo) : null;
      if (from && date < from) return false;
      if (to && date > to) return false;
      return true;
    });
  }

  rows.sort((a, b) => {
    if (appState.sortBy === "amount") {
      const av = appState.activeTab === "unmatchedBank" ? a.amount : a.invoice.amount;
      const bv = appState.activeTab === "unmatchedBank" ? b.amount : b.invoice.amount;
      return bv - av;
    }
    if (appState.sortBy === "date") {
      const av = appState.activeTab === "unmatchedBank" ? a.transactionDate : a.invoice.invoiceDate;
      const bv = appState.activeTab === "unmatchedBank" ? b.transactionDate : b.invoice.invoiceDate;
      return new Date(bv) - new Date(av);
    }
    const av = appState.activeTab === "matched" ? a.score : a.candidate?.score || 0;
    const bv = appState.activeTab === "matched" ? b.score : b.candidate?.score || 0;
    return bv - av;
  });

  return rows;
};

const populateCurrencyFilter = () => {
  const set = new Set([
    ...appState.invoice.mapped.map((row) => row.currency),
    ...appState.bank.mapped.map((row) => row.currency)
  ]);
  elements.currencyFilter.innerHTML = `<option value="">All currencies</option>${[...set]
    .map((curr) => `<option value="${curr}">${curr}</option>`)
    .join("")}`;
};

const renderAll = () => {
  elements.analytics.hidden = false;
  elements.charts.hidden = false;
  elements.results.hidden = false;
  elements.exportSection.hidden = false;
  renderStats();
  renderCharts();
  populateCurrencyFilter();
  renderTable();
};

const exportWorkbook = () => {
  const wb = XLSX.utils.book_new();
  const summary = [
    ["AR Reconciliation Engine Report"],
    ["Generated", new Date().toLocaleString()],
    ["Threshold", appState.settings.threshold],
    ["Tolerance", appState.settings.tolerance],
    ["Allow Variance", appState.settings.allowVariance],
    ["Grouping", appState.settings.grouping],
    ["Date Window", appState.settings.dateWindow],
    ["Matched", appState.results.matched.length],
    ["Unmatched Invoices", appState.results.unmatchedInvoices.length],
    ["Unmatched Bank", appState.results.unmatchedBank.length]
  ];
  XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(summary), "Summary");

  const matchedRows = appState.results.matched.map((row) => ({
    invoiceNumber: row.invoice.invoiceNumber,
    customerName: row.invoice.customerName,
    invoiceDate: row.invoice.invoiceDate,
    dueDate: row.invoice.dueDate,
    amount: row.invoice.amount,
    currency: row.invoice.currency,
    bankReference: row.bank.reference,
    bankDescription: row.bank.description,
    bankAmount: row.bank.amount,
    score: row.score,
    explanation: JSON.stringify(row.explanation)
  }));

  const unmatchedInvoices = appState.results.unmatchedInvoices.map((row) => ({
    invoiceNumber: row.invoice.invoiceNumber,
    customerName: row.invoice.customerName,
    invoiceDate: row.invoice.invoiceDate,
    dueDate: row.invoice.dueDate,
    amount: row.invoice.amount,
    currency: row.invoice.currency,
    reference: row.invoice.reference
  }));

  const unmatchedBank = appState.results.unmatchedBank.map((row) => ({
    bankId: row.bankId,
    transactionDate: row.transactionDate,
    description: row.description,
    amount: row.amount,
    currency: row.currency,
    reference: row.reference
  }));

  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(matchedRows), "Matched");
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(unmatchedInvoices), "Unmatched Invoices");
  XLSX.utils.book_append_sheet(wb, XLSX.utils.json_to_sheet(unmatchedBank), "Unmatched Bank");

  XLSX.writeFile(wb, `ar_reconciliation_${new Date().toISOString().slice(0, 10)}.xlsx`);
};

const setTheme = (mode) => {
  document.documentElement.dataset.theme = mode;
  localStorage.setItem("theme", mode);
};

const toggleTheme = () => {
  const current = localStorage.getItem("theme") || "dark";
  setTheme(current === "dark" ? "light" : "dark");
};

const initTheme = () => {
  const stored = localStorage.getItem("theme");
  if (stored) setTheme(stored);
};

const generateSample = () => {
  const invoices = Array.from({ length: 40 }).map((_, index) => {
    const amount = Math.round((Math.random() * 9000 + 1000) * 100) / 100;
    const date = new Date();
    date.setDate(date.getDate() - Math.floor(Math.random() * 30));
    const due = new Date(date);
    due.setDate(due.getDate() + 15);
    return {
      invoiceNumber: `INV-${String(index + 1).padStart(4, "0")}`,
      customerName: `Customer ${String.fromCharCode(65 + (index % 26))}`,
      invoiceDate: toISO(date),
      dueDate: toISO(due),
      amount,
      currency: "USD",
      reference: `REF-${String(index + 1).padStart(4, "0")}`
    };
  });

  const bank = Array.from({ length: 36 }).map((_, index) => {
    const inv = invoices[index];
    const variance = Math.random() > 0.85 ? (Math.random() - 0.5) * 5 : 0;
    return {
      transactionDate: inv ? inv.invoiceDate : toISO(new Date()),
      description: inv ? `PAYMENT ${inv.reference} ${inv.customerName}` : "Misc payment",
      amount: inv ? inv.amount + variance : Math.random() * 5000,
      currency: "USD",
      reference: inv ? inv.reference : `BANK-${index}`,
      bankId: `BANK-${String(index + 1).padStart(4, "0")}`
    };
  });

  appState.invoice.mapped = invoices;
  appState.bank.mapped = bank;
  elements.invoiceMeta.textContent = "Sample invoices loaded";
  elements.bankMeta.textContent = "Sample bank loaded";
  toggleReconReady();
  showToast("Sample data generated.");
};

const initEvents = () => {
  elements.invoiceFile.addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (!file) return;
    elements.invoiceMeta.textContent = `${file.name}`;
    handleFile("invoice", file);
  });
  elements.bankFile.addEventListener("change", (event) => {
    const file = event.target.files[0];
    if (!file) return;
    elements.bankMeta.textContent = `${file.name}`;
    handleFile("bank", file);
  });
  elements.invoiceSheet.addEventListener("change", () => handleSheetChange("invoice"));
  elements.bankSheet.addEventListener("change", () => handleSheetChange("bank"));
  elements.applyMapping.addEventListener("click", applyMapping);

  document.querySelectorAll("[data-close]").forEach((btn) => {
    btn.addEventListener("click", () => closeModal(document.getElementById(btn.dataset.close)));
  });

  elements.thresholdRange.addEventListener("input", updateSettings);
  elements.toleranceValue.addEventListener("input", updateSettings);
  elements.allowVariance.addEventListener("change", updateSettings);
  elements.enableGrouping.addEventListener("change", updateSettings);
  elements.dateWindow.addEventListener("input", updateSettings);
  elements.useCustomer.addEventListener("change", updateSettings);

  elements.startRecon.addEventListener("click", async () => {
    updateSettings();
    await reconcile();
    renderAll();
  });

  elements.cancelRecon.addEventListener("click", () => {
    appState.cancel = true;
    elements.engineSection.hidden = true;
    showToast("Reconciliation cancelled.");
  });

  elements.resetRecon.addEventListener("click", () => {
    window.location.reload();
  });

  elements.searchInput.addEventListener("input", (event) => {
    appState.search = event.target.value;
    renderTable();
  });
  elements.currencyFilter.addEventListener("change", (event) => {
    appState.currency = event.target.value;
    renderTable();
  });
  elements.dateFrom.addEventListener("change", (event) => {
    appState.dateFrom = event.target.value;
    renderTable();
  });
  elements.dateTo.addEventListener("change", (event) => {
    appState.dateTo = event.target.value;
    renderTable();
  });
  elements.sortBy.addEventListener("change", (event) => {
    appState.sortBy = event.target.value;
    renderTable();
  });

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
      tab.classList.add("active");
      appState.activeTab = tab.dataset.tab;
      renderTable();
    });
  });

  document.querySelectorAll(".chart-toggle .ghost-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".chart-toggle .ghost-btn").forEach((item) => item.classList.remove("active"));
      btn.classList.add("active");
      appState.chartMode = btn.dataset.chart;
      renderCharts();
    });
  });

  elements.tableBody.addEventListener("click", (event) => {
    const row = event.target.closest(".data-row");
    if (!row) return;
    const details = elements.tableBody.querySelector(`[data-details="${row.dataset.index}"]`);
    if (details) details.hidden = !details.hidden;
  });

  elements.themeToggle.addEventListener("click", toggleTheme);
  elements.helpToggle.addEventListener("click", () => openModal(elements.helpModal));
  elements.sampleData.addEventListener("click", generateSample);
  elements.exportBtn.addEventListener("click", exportWorkbook);
  elements.exportExcel.addEventListener("click", exportWorkbook);
};

initTheme();
initEvents();
updateSettings();
