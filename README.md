# amusa

Utilities for working with Microsoft Entra ID (Azure AD) immutable IDs.

## Deploy for your team

| Platform | Guide | Best for |
|----------|-------|----------|
| **Azure App Service** | **[DEPLOY_AZURE.md](DEPLOY_AZURE.md)** | Production, Entra-only access, Allvue tenant |
| Streamlit Cloud | [DEPLOY_STREAMLIT.md](DEPLOY_STREAMLIT.md) | Quick public pilot |

**Recommended for Allvue:** Azure App Service with Entra authentication → `https://your-app.azurewebsites.net`

## Web app

Modern web UI for looking up `onPremisesImmutableId` values from Microsoft Entra ID.

**Important:** `http://localhost:8000` only works on the machine where you start the app. If you are using a Cursor Cloud Agent, run the app on your own computer (clone the repo locally), not in the cloud environment.

### Quick start

```bash
chmod +x run-web.sh
az login
./run-web.sh
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
az login
uvicorn web.server:app --host localhost --port 8000 --reload
```

Open **http://localhost:8000** in your browser.

### Features

- **Single user** — look up one email, UPN, or object ID
- **Batch paste** — paste a list of identifiers (one per line)
- **CSV upload** — upload a file and auto-detect the user column
- **Export** — download results as CSV or copy immutable IDs to clipboard

### Authentication

- **Default** — uses Azure CLI after `az login`
- **Interactive browser** — opens a browser sign-in flow
- **Service principal** — available when `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, and `AZURE_CLIENT_SECRET` are set

### Legacy Streamlit GUI

The original Streamlit UI is still available:

```bash
./run-gui.sh
```

Then open **http://localhost:8501**.

### Troubleshooting "This site can't be reached"

1. **Start the app first** — opening the URL before running the command above will fail.
2. **Run locally** — Cloud Agent / remote VMs do not expose `localhost` to your browser. Clone the repo and run `./run-web.sh` on your laptop.
3. **Check the terminal** — if the server crashed, read the error there and fix it (often missing `pip install -r requirements.txt` or `python3-venv` not installed).
4. **Try another port** if 8000 is in use:

```bash
uvicorn web.server:app --host localhost --port 8001 --reload
```

## Get immutable ID from Azure (CLI)

Requires [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli) and Graph API access (`User.Read.All` or `Directory.Read.All`).

```bash
az login
./scripts/get-immutable-id.sh user@example.com
```

List all users:

```bash
./scripts/get-immutable-id.sh --all
```

Service principal auth:

```bash
export AZURE_CLIENT_ID=...
export AZURE_CLIENT_SECRET=...
export AZURE_TENANT_ID=...
./scripts/get-immutable-id.sh user@example.com
```

## Convert on-prem AD ObjectGUID to immutable ID

For hybrid identity hard-matching, convert an on-premises AD user's ObjectGUID to the base64 immutable ID format Entra expects:

```powershell
./scripts/objectguid-to-immutable-id.ps1 -ObjectGuid "00000000-0000-0000-0000-000000000000"
```
