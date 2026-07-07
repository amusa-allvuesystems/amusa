# amusa

Utilities for working with Microsoft Entra ID (Azure AD) immutable IDs.

## Deploy for your team (Streamlit Cloud)

See **[DEPLOY_STREAMLIT.md](DEPLOY_STREAMLIT.md)** for step-by-step instructions to publish at a shared URL like `https://your-app.streamlit.app`.

Quick summary:

1. Merge the GUI to `main`
2. Create an Azure app registration with Graph `User.Read.All` (application permission)
3. Deploy at [share.streamlit.io](https://share.streamlit.io) with main file `gui/app.py`
4. Add secrets: `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`

## GUI (CSV upload)

Web UI for batch lookups from a CSV file or pasted user list.

**Important:** `http://localhost:8501` only works on the machine where you start Streamlit. If you are using a Cursor Cloud Agent, run the GUI on your own computer (clone the repo locally), not in the cloud environment.

### Quick start

```bash
chmod +x run-gui.sh
./run-gui.sh
```

Or manually:

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
az login
streamlit run gui/app.py
```

Wait until the terminal shows:

```text
You can now view your Streamlit app in your browser.
Local URL: http://localhost:8501
```

Then open **http://localhost:8501** in your browser.

### Troubleshooting "This site can't be reached"

1. **Start Streamlit first** — opening the URL before running the command above will fail.
2. **Run locally** — Cloud Agent / remote VMs do not expose `localhost` to your browser. Clone the repo and run `./run-gui.sh` on your laptop.
3. **Check the terminal** — if Streamlit crashed, read the error there and fix it (often missing `pip install -r requirements.txt` or `python3-venv` not installed).
4. **Try another port** if 8501 is in use:

```bash
streamlit run gui/app.py --server.port 8502
```

1. Upload a CSV with a `userPrincipalName`, `email`, or similar column (see `sample_users.csv`)
2. Choose the user identifier column
3. Click **Fetch immutable IDs**
4. Download results as CSV

Authentication options in the sidebar:

- **Default** — uses Azure CLI after `az login`
- **Interactive browser** — opens a browser sign-in flow
- **Service principal** — available when `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, and `AZURE_CLIENT_SECRET` are set

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
