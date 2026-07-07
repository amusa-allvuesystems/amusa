# Deploy to Streamlit Community Cloud

Share the immutable ID lookup GUI with your team at a URL like `https://your-app.streamlit.app`.

## 1. Merge the code to `main`

Merge [PR #2](https://github.com/amusa-allvuesystems/amusa/pull/2) (or ensure `main` contains `gui/app.py` and `requirements.txt`).

## 2. Create an Azure app registration

In [Microsoft Entra admin center](https://entra.microsoft.com):

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
   - **Branch:** `main`
   - **Main file path:** `gui/app.py`
4. Click **Advanced settings** if needed (Python 3.11+ is fine)
5. Open **Secrets** and paste:

```toml
AZURE_TENANT_ID = "your-tenant-id"
AZURE_CLIENT_ID = "your-app-client-id"
AZURE_CLIENT_SECRET = "your-client-secret"
```

6. Click **Deploy**

Deployment usually takes 2–5 minutes. Streamlit gives you a public URL.

## 4. Share with your team

Send the app URL (e.g. `https://amusa-immutable-id.streamlit.app`).

Team members can:

1. Open the URL
2. Upload a CSV or paste user emails/UPNs
3. Click **Fetch immutable IDs**
4. Download results

No `az login` required — the app uses the service principal from secrets.

## 5. Restrict access (recommended)

Streamlit Community Cloud free tier apps are public URLs. Options:

- **Streamlit Teams** (paid): private apps and SSO
- **Don't put sensitive data in the repo** — only secrets in the Streamlit dashboard
- Rotate the client secret periodically in Entra and update Streamlit secrets

For strict Entra-only access, use Azure App Service with authentication instead (see README).

## Troubleshooting

| Issue | Fix |
|-------|-----|
| App won't start | Check deploy logs in Streamlit Cloud → Manage app → Logs |
| `Authentication failed` | Verify tenant/client/secret in Secrets; confirm admin consent for `User.Read.All` |
| `403` / insufficient privileges | App registration needs **Application** permission `User.Read.All` with admin consent |
| `User not found` | Check UPN/email matches Entra ID exactly |

## Update the app

Push to `main` — Streamlit Cloud redeploys automatically.

To change secrets: Streamlit Cloud → your app → **Settings** → **Secrets** → Save (app restarts).
