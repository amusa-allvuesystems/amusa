# amusa

Local tools for Entra ID / AD immutable IDs.

## Run locally (no Streamlit)

### One-time setup

```bash
cd /Users/amusa/amusa
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-cli.txt
```

### Convert ObjectGUID → Immutable ID (no Azure login)

Single GUID:

```bash
python amusa.py convert -g "12345678-1234-1234-1234-123456789abc"
```

CSV batch:

```bash
python amusa.py convert -i users.csv
python amusa.py convert -i users.csv -o results.csv
```

Input CSV needs an `ObjectGUID` column.

### Lookup from Entra (requires az login)

```bash
brew install azure-cli   # if needed
az login
python amusa.py lookup -u amusa@allvuesystems.com
python amusa.py lookup -i users.csv -o results.csv
```

Input CSV needs a `userPrincipalName` or `email` column.

---

## Shell scripts (alternative)

```bash
./scripts/get-immutable-id.sh user@example.com
./scripts/get-immutable-id.sh --all
```

PowerShell (Windows) — ObjectGUID conversion:

```powershell
./scripts/objectguid-to-immutable-id.ps1 -ObjectGuid "12345678-1234-1234-1234-123456789abc"
```

---

## Get ObjectGUIDs from on-prem AD

```powershell
Get-ADUser -Filter * -Properties ObjectGUID |
  Select-Object samAccountName, UserPrincipalName, ObjectGUID |
  Export-Csv users.csv -NoTypeInformation
```

Then:

```bash
python amusa.py convert -i users.csv
```
