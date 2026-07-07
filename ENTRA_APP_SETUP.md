# Create Entra app registration (step by step)

This app registration lets the Streamlit tool read `onPremisesImmutableId` from Microsoft Graph. **It is free** — you do not need an Azure subscription.

You will copy three values into Streamlit Cloud Secrets:

- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`

---

## Step 1 — Open Entra admin center

1. Go to [https://entra.microsoft.com](https://entra.microsoft.com)
2. Sign in with your Allvue work account
3. Confirm the tenant name shows **Allvue Systems, LLC** (top-right)

---

## Step 2 — Create the app registration

1. In the left menu, click **Applications** → **App registrations**
2. Click **+ New registration**
3. Fill in:
   - **Name:** `amusa-immutable-id-gui` (any name is fine)
   - **Supported account types:** select **Accounts in this organizational directory only (Single tenant)**
   - **Redirect URI:** leave blank (not needed for this app)
4. Click **Register**

---

## Step 3 — Copy Tenant ID and Client ID

On the app **Overview** page, copy and save:

| Copy this | Where it goes |
|-----------|----------------|
| **Application (client) ID** | `AZURE_CLIENT_ID` |
| **Directory (tenant) ID** | `AZURE_TENANT_ID` |

Keep this browser tab open.

---

## Step 4 — Create a client secret

1. In the left menu, click **Certificates & secrets**
2. Under **Client secrets**, click **+ New client secret**
3. **Description:** `streamlit-gui`
4. **Expires:** choose 12 or 24 months (set a calendar reminder to rotate before expiry)
5. Click **Add**
6. **Immediately copy the secret Value** (not the Secret ID)

   ⚠️ You can only see the value once. If you lose it, create a new secret.

| Copy this | Where it goes |
|-----------|----------------|
| Secret **Value** | `AZURE_CLIENT_SECRET` |

---

## Step 5 — Add Microsoft Graph permission

1. In the left menu, click **API permissions**
2. Click **+ Add a permission**
3. Click **Microsoft Graph**
4. Click **Application permissions** (not Delegated)

   > Application = the app runs as itself (correct for Streamlit Cloud)  
   > Delegated = acts as a signed-in user (not what we want here)

5. Search for and check **User.Read.All**
6. Click **Add permissions**

You should now see:

```text
Microsoft Graph    User.Read.All    Application
```

Status may show: **Not granted for Allvue Systems, LLC**

---

## Step 6 — Grant admin consent

Application permissions require admin approval.

### If you are an Entra admin

1. On the **API permissions** page, click **Grant admin consent for Allvue Systems, LLC**
2. Click **Yes**
3. Status should change to **Granted for Allvue Systems, LLC** with a green check

### If you are not an admin

Send this to your IT / Entra administrator:

> Please grant admin consent for app registration **amusa-immutable-id-gui** (Application permission: Microsoft Graph `User.Read.All`).  
> This is for an internal tool that reads `onPremisesImmutableId` for hybrid identity user matching.

You cannot complete Streamlit lookups until consent is granted.

---

## Step 7 — Paste into Streamlit Cloud Secrets

1. Open [share.streamlit.io](https://share.streamlit.io) → your app
2. **Manage app** → **Settings** → **Secrets**
3. Paste (with your real values):

```toml
AZURE_TENANT_ID = "paste-directory-tenant-id-here"
AZURE_CLIENT_ID = "paste-application-client-id-here"
AZURE_CLIENT_SECRET = "paste-client-secret-value-here"
```

4. Click **Save**
5. **Reboot app**

---

## Step 8 — Verify it works

1. Open your Streamlit app URL
2. Sidebar should say **Azure credentials loaded**
3. Paste a test user email (e.g. your own UPN)
4. Click **Fetch immutable IDs**

Expected result:

- **Success:** JSON/table with `onPremisesImmutableId` (may be empty/null if not set for that user)
- **403 / insufficient privileges:** admin consent not granted (Step 6)
- **Authentication failed:** wrong tenant/client/secret, or secret expired

---

## Quick checklist

- [ ] App registration created (single tenant)
- [ ] Client ID copied → `AZURE_CLIENT_ID`
- [ ] Tenant ID copied → `AZURE_TENANT_ID`
- [ ] Client secret created and value copied → `AZURE_CLIENT_SECRET`
- [ ] `User.Read.All` added as **Application** permission
- [ ] Admin consent granted (green check)
- [ ] Secrets saved in Streamlit Cloud
- [ ] App rebooted

---

## Security tips

- Never commit secrets to GitHub
- Rotate the client secret before it expires
- Only share the Streamlit URL with your team
- If the secret is exposed, delete it in Entra and create a new one
