const AUTH_LABELS = {
  default: "Default (Azure CLI / existing login)",
  browser: "Interactive browser login",
  service_principal: "Service principal (env vars)",
};

let authStatus = null;
let lastResults = [];

const authModeSelect = document.getElementById("auth-mode");
const authBadge = document.getElementById("auth-badge");
const authHostedMessage = document.getElementById("auth-hosted-message");
const lookupBtn = document.getElementById("lookup-btn");
const userCount = document.getElementById("user-count");
const alertBox = document.getElementById("alert");
const resultsSection = document.getElementById("results-section");
const resultsTableBody = document.querySelector("#results-table tbody");
const loading = document.getElementById("loading");
const downloadBtn = document.getElementById("download-btn");
const copyBtn = document.getElementById("copy-btn");
const csvFileInput = document.getElementById("csv-file");
const csvColumnWrap = document.getElementById("csv-column-wrap");
const csvColumnSelect = document.getElementById("csv-column");

function showAlert(message, type = "error") {
  alertBox.textContent = message;
  alertBox.classList.remove("hidden", "success");
  if (type === "success") {
    alertBox.classList.add("success");
  }
}

function hideAlert() {
  alertBox.classList.add("hidden");
}

function setLoading(active) {
  loading.classList.toggle("hidden", !active);
  lookupBtn.disabled = active || !authStatus?.ready;
}

function getActiveTab() {
  return document.querySelector(".tab.active")?.dataset.tab || "single";
}

function parseBatchUsers(text) {
  return text
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
}

function updateUserCount() {
  const tab = getActiveTab();
  let count = 0;

  if (tab === "single") {
    count = document.getElementById("single-user").value.trim() ? 1 : 0;
  } else if (tab === "batch") {
    count = parseBatchUsers(document.getElementById("batch-users").value).length;
  } else if (tab === "csv") {
    count = csvFileInput.files?.length ? "CSV ready" : 0;
  }

  userCount.textContent =
    typeof count === "number" && count > 0
      ? `${count} user(s) ready`
      : count === "CSV ready"
        ? "CSV file selected"
        : "";
}

function renderAuthStatus(status) {
  authStatus = status;
  authModeSelect.innerHTML = "";

  status.available_auth_modes.forEach((mode) => {
    const option = document.createElement("option");
    option.value = mode;
    option.textContent = AUTH_LABELS[mode] || mode;
    if (mode === status.default_auth_mode) {
      option.selected = true;
    }
    authModeSelect.appendChild(option);
  });

  if (status.hosted) {
    authHostedMessage.classList.remove("hidden");
    if (status.service_principal_configured) {
      authHostedMessage.textContent = `Running on ${status.platform || "hosted environment"} with service principal credentials.`;
      authBadge.textContent = "Connected";
      authBadge.classList.remove("hidden", "error");
    } else {
      authHostedMessage.textContent =
        "Azure credentials missing. Set AZURE_TENANT_ID, AZURE_CLIENT_ID, and AZURE_CLIENT_SECRET.";
      authBadge.textContent = "Not configured";
      authBadge.classList.remove("hidden");
      authBadge.classList.add("error");
    }
  } else {
    authHostedMessage.classList.add("hidden");
    authBadge.classList.add("hidden");
  }

  lookupBtn.disabled = !status.ready;
  updateUserCount();
}

async function loadAuthStatus() {
  const response = await fetch("/api/auth/status");
  if (!response.ok) {
    throw new Error("Unable to load authentication status.");
  }
  renderAuthStatus(await response.json());
}

function setupTabs() {
  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((item) => {
        item.classList.remove("active");
        item.setAttribute("aria-selected", "false");
      });
      document.querySelectorAll(".tab-panel").forEach((panel) => panel.classList.remove("active"));

      tab.classList.add("active");
      tab.setAttribute("aria-selected", "true");
      document.getElementById(`tab-${tab.dataset.tab}`).classList.add("active");
      updateUserCount();
    });
  });
}

function renderResults(payload) {
  lastResults = payload.results;
  document.getElementById("metric-processed").textContent = payload.processed;
  document.getElementById("metric-succeeded").textContent = payload.succeeded;
  document.getElementById("metric-errors").textContent = payload.errors;

  resultsTableBody.innerHTML = "";
  payload.results.forEach((row) => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${escapeHtml(row.input)}</td>
      <td>${escapeHtml(row.display_name || "")}</td>
      <td>${escapeHtml(row.user_principal_name || "")}</td>
      <td class="immutable-id">${escapeHtml(row.immutable_id || "")}</td>
      <td class="${row.success ? "status-ok" : "status-error"}">
        ${row.success ? "OK" : escapeHtml(row.error || "Error")}
      </td>
    `;
    resultsTableBody.appendChild(tr);
  });

  resultsSection.classList.remove("hidden");
  hideAlert();

  if (payload.errors > 0) {
    showAlert(`${payload.errors} lookup(s) failed. See the Status column for details.`, "error");
  } else {
    showAlert(`Successfully fetched ${payload.succeeded} immutable ID(s).`, "success");
  }
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

async function lookupUsers() {
  hideAlert();
  setLoading(true);

  try {
    const authMode = authModeSelect.value;
    const tab = getActiveTab();
    let response;

    if (tab === "csv") {
      const file = csvFileInput.files?.[0];
      if (!file) {
        showAlert("Choose a CSV file first.");
        return;
      }

      const formData = new FormData();
      formData.append("file", file);
      formData.append("auth_mode", authMode);
      if (csvColumnSelect.value) {
        formData.append("column", csvColumnSelect.value);
      }

      response = await fetch("/api/lookup/csv", {
        method: "POST",
        body: formData,
      });
    } else {
      let users = [];
      if (tab === "single") {
        const value = document.getElementById("single-user").value.trim();
        if (value) {
          users = [value];
        }
      } else {
        users = parseBatchUsers(document.getElementById("batch-users").value);
      }

      if (!users.length) {
        showAlert("Enter at least one user identifier.");
        return;
      }

      response = await fetch("/api/lookup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ users, auth_mode: authMode }),
      });
    }

    const payload = await response.json();
    if (!response.ok) {
      showAlert(payload.detail || "Lookup failed.");
      return;
    }

    renderResults(payload);
  } catch (error) {
    showAlert(error.message || "Unexpected error during lookup.");
  } finally {
    setLoading(false);
  }
}

function downloadResultsCsv() {
  if (!lastResults.length) {
    return;
  }

  const headers = ["Input", "Display Name", "User Principal Name", "Immutable ID", "Status", "Error"];
  const lines = [headers.join(",")];

  lastResults.forEach((row) => {
    lines.push(
      [
        csvEscape(row.input),
        csvEscape(row.display_name || ""),
        csvEscape(row.user_principal_name || ""),
        csvEscape(row.immutable_id || ""),
        row.success ? "OK" : "Error",
        csvEscape(row.error || ""),
      ].join(","),
    );
  });

  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "immutable_id_results.csv";
  link.click();
  URL.revokeObjectURL(url);
}

function csvEscape(value) {
  const text = String(value);
  if (/[",\n]/.test(text)) {
    return `"${text.replaceAll('"', '""')}"`;
  }
  return text;
}

async function copyImmutableIds() {
  const ids = lastResults
    .filter((row) => row.success && row.immutable_id)
    .map((row) => row.immutable_id)
    .join("\n");

  if (!ids) {
    showAlert("No immutable IDs to copy.");
    return;
  }

  await navigator.clipboard.writeText(ids);
  showAlert("Copied immutable IDs to clipboard.", "success");
}

async function handleCsvSelection() {
  csvColumnWrap.classList.add("hidden");
  csvColumnSelect.innerHTML = "";

  const file = csvFileInput.files?.[0];
  if (!file) {
    updateUserCount();
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch("/api/csv/columns", {
      method: "POST",
      body: formData,
    });
    const payload = await response.json();
    if (!response.ok) {
      showAlert(payload.detail || "Could not read CSV columns.");
      return;
    }

    payload.columns.forEach((column) => {
      const option = document.createElement("option");
      option.value = column;
      option.textContent = column;
      if (column === payload.suggested_column) {
        option.selected = true;
      }
      csvColumnSelect.appendChild(option);
    });

    csvColumnWrap.classList.remove("hidden");
    updateUserCount();
  } catch (error) {
    showAlert(error.message || "Could not read CSV file.");
  }
}

lookupBtn.addEventListener("click", lookupUsers);
downloadBtn.addEventListener("click", downloadResultsCsv);
copyBtn.addEventListener("click", copyImmutableIds);
csvFileInput.addEventListener("change", handleCsvSelection);
document.getElementById("single-user").addEventListener("input", updateUserCount);
document.getElementById("batch-users").addEventListener("input", updateUserCount);

setupTabs();
loadAuthStatus().catch((error) => showAlert(error.message));
