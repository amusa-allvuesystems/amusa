# amusa

Utilities for working with Microsoft Entra ID (Azure AD) immutable IDs.

## Get immutable ID from Azure

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
