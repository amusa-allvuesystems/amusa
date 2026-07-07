# Publish without admin consent

IT declined Graph API admin consent. Here are options that still work.

## Recommended: Streamlit Cloud — ObjectGUID converter (no permissions)

The app now has a tab **"Convert ObjectGUID (no admin needed)"** that:

- Does **not** call Microsoft Graph
- Does **not** need Entra app registration or admin consent
- Converts on-prem AD `ObjectGUID` → base64 immutable ID (same as Entra hybrid match format)
- Supports CSV upload and batch conversion

### Publish on Streamlit Cloud (free)

1. [share.streamlit.io](https://share.streamlit.io) → deploy `gui/app.py` from branch `cursor/azure-immutable-id-a5bb`
2. **No secrets required** for the converter tab
3. Share the URL with your team

### What your team needs

A CSV from **on-premises Active Directory** with ObjectGUID, for example from PowerShell:

```powershell
Get-ADUser -Filter * -Properties ObjectGUID |
  Select-Object samAccountName, UserPrincipalName, ObjectGUID |
  Export-Csv users.csv -NoTypeInformation
```

Upload `users.csv` → pick ObjectGUID column → **Convert to immutable IDs**.

---

## Option 2: Run locally on your Mac (Graph lookup)

If **your account** has rights to read users (some IT roles do):

```bash
cd /Users/amusa/amusa
source .venv/bin/activate
az login
streamlit run gui/app.py
```

Use tab **"Lookup from Entra"** → sign-in method **Azure CLI**.

Works only if `az login` has permission to read other users — often still blocked for regular users.

---

## Option 3: Share the repo / scripts internally

Distribute via GitHub for colleagues who can run tools locally:

| Tool | Use case |
|------|----------|
| `gui/app.py` | GUI with both modes |
| `scripts/objectguid-to-immutable-id.ps1` | Single GUID conversion on Windows |
| `scripts/get-immutable-id.sh` | CLI lookup (needs `az login` + permissions) |

---

## Option 4: Ask IT for a one-time export

Request a CSV from IT with columns:

- `userPrincipalName`
- `onPremisesImmutableId`

No app deployment needed — team uses the spreadsheet directly.

---

## Option 5: PowerShell only (no web app)

On a machine with AD module access:

```powershell
Get-ADUser -Identity "username" | ForEach-Object {
  $bytes = $_.ObjectGUID.ToByteArray()
  $immutableId = [Convert]::ToBase64String($bytes)
  [pscustomobject]@{ User = $_.SamAccountName; ImmutableId = $immutableId }
}
```

---

## Comparison

| Method | Admin consent | Batch CSV | Hosted URL |
|--------|---------------|-----------|------------|
| **ObjectGUID converter (Streamlit)** | No | Yes | Yes (free) |
| Entra Graph lookup | Yes | Yes | Needs consent |
| Local `az login` | No* | Yes | No |
| IT export | No | Yes | No |

\*Uses your own account permissions; may still fail for other users.

---

## What changed in the app

Open your Streamlit app → use the first tab:

**Convert ObjectGUID (no admin needed)**

No Azure secrets, no 403 errors.
