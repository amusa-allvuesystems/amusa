# Deploy to Streamlit Community Cloud (free)

Share the immutable ID lookup GUI with your team at a URL like `https://your-app.streamlit.app`.

**Cost:** Streamlit Community Cloud is **free**. You do **not** need an Azure subscription — only a free Entra app registration to call Microsoft Graph.

## 1. Get the code on GitHub

Use branch `cursor/azure-immutable-id-a5bb` (or `main` after [PR #2](https://github.com/amusa-allvuesystems/amusa/pull/2) is merged).

The repo must contain `gui/app.py` and `requirements.txt`.

## 2. Create an Azure app registration (free — no subscription needed)

**Full walkthrough:** [ENTRA_APP_SETUP.md](ENTRA_APP_SETUP.md)

Quick version in [Microsoft Entra admin center](https://entra.microsoft.com):

1. **App registrations** → **New registration**
   - Name: `amusa-immutable-id-gui`
   - Supported account types: **Single tenant**
2. Note the **Application (client) ID** and **Directory (tenant) ID**
3. **Certificates & secrets** → **New client secret** → copy the value
4. **API permissions** → **Add permission** → **Microsoft Graph** → **Application permissions**
   - Add `User.Read.All`
5. Click **Grant admin consent for [your tenant]**

## 3. Deploy on Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
2. Click **Create app**
3. Configure:
   - **Repository:** `amusa-allvuesystems/amusa`
   - **Branch:** `cursor/azure-immutable-id-a5bb` (or `main` if merged)
   - **Main file path:** `gui/app.py`
4. Click **Advanced settings** if needed (Python 3.11+ is fine)
5. Open **Secrets** and paste:

```toml
AZURE_TENANT_ID = "your-tenant-id"
AZURE_CLIENT_ID = "your-app-client-id"
AZURE_CLIENT_SECRET = "your-client-secret"
```

Or nested format:

```toml
[azure]
tenant_id = "your-tenant-id"
client_id = "your-app-client-id"
client_secret = "your-client-secret"
```

6. Click **Deploy**, then **Reboot app** if you add or change secrets later

Deployment usually takes 2–5 minutes. Streamlit gives you a public URL.

## 4. Share with your team

Send the app URL (e.g. `https://amusa-immutable-id.streamlit.app`).

Team members can:

1. Open the URL
2. Upload a CSV or paste user emails/UPNs
3. Click **Fetch immutable IDs**
4. Download results

No `az login` required — the app uses the service principal from secrets.

## 5. Security note

Free Streamlit apps have a **public URL** (anyone with the link can open it). Mitigations:

- Don't share the URL outside your team
- Only store credentials in Streamlit **Secrets** (never in the repo)
- Rotate the Entra client secret periodically

For Entra-only login on the website itself, you'd need paid Streamlit Teams or Azure App Service.

## Troubleshooting

| Issue | Fix |
|-------|-----|
| App won't start | Check deploy logs in Streamlit Cloud → Manage app → Logs |
| `Authentication failed: DefaultAzureCredential` | Secrets not loaded — add them in Streamlit Cloud → Settings → Secrets, then **Reboot app**. Use branch `cursor/azure-immutable-id-a5bb`. |
| `Authentication failed` | Verify tenant/client/secret in Secrets; confirm admin consent for `User.Read.All` |
| `403` / insufficient privileges | App registration needs **Application** permission `User.Read.All` with admin consent |
| `User not found` | Check UPN/email matches Entra ID exactly |

## Update the app

Push to `main` — Streamlit Cloud redeploys automatically.

To change secrets: Streamlit Cloud → your app → **Settings** → **Secrets** → Save (app restarts).
