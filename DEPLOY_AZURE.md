# Deploy to Azure App Service

Host the immutable ID lookup GUI for your team on Azure App Service with Entra ID sign-in.

**Team URL example:** `https://amusa-immutable-id.azurewebsites.net`

## Architecture

- **Azure Web App for Containers** runs the Streamlit app (Docker)
- **App settings** store the Graph API service principal credentials
- **Entra authentication** (optional, recommended) restricts who can open the website

You need **two** Entra configurations:

| Purpose | What it does |
|---------|----------------|
| **Graph API app registration** | Lets the app read `onPremisesImmutableId` from Microsoft Graph |
| **App Service authentication** | Lets only your org sign in to the website |

These can be the same app registration for a small internal tool, but separate registrations are cleaner for production.

---

## 1. Prerequisites

- Azure subscription
- [Azure CLI](https://learn.microsoft.com/en-us/cli/azure/install-azure-cli): `az login`
- Docker optional (Azure builds the image for you via ACR)

Set variables (change names to something globally unique):

```bash
RESOURCE_GROUP="rg-amusa-immutable-id"
LOCATION="westeurope"
ACR_NAME="amusaimmutableidacr"        # letters/numbers only, globally unique
APP_NAME="amusa-immutable-id"         # globally unique
PLAN_NAME="asp-amusa-immutable-id"
IMAGE_NAME="amusa-gui"
```

---

## 2. Create Graph API app registration

In [Entra admin center](https://entra.microsoft.com):

1. **App registrations** → **New registration**
   - Name: `amusa-immutable-id-graph`
   - Single tenant
2. Copy **Tenant ID** and **Client ID**
3. **Certificates & secrets** → **New client secret**
4. **API permissions** → **Microsoft Graph** → **Application permissions** → `User.Read.All`
5. **Grant admin consent**

Save these for app settings:

- `AZURE_TENANT_ID`
- `AZURE_CLIENT_ID`
- `AZURE_CLIENT_SECRET`

---

## 3. Build and deploy the container

From the repo root:

```bash
az group create --name "$RESOURCE_GROUP" --location "$LOCATION"

az acr create \
  --resource-group "$RESOURCE_GROUP" \
  --name "$ACR_NAME" \
  --sku Basic \
  --admin-enabled true

az acr build \
  --registry "$ACR_NAME" \
  --image "${IMAGE_NAME}:latest" \
  .

az appservice plan create \
  --name "$PLAN_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --is-linux \
  --sku B1

ACR_LOGIN_SERVER=$(az acr show --name "$ACR_NAME" --query loginServer -o tsv)
ACR_USERNAME=$(az acr credential show --name "$ACR_NAME" --query username -o tsv)
ACR_PASSWORD=$(az acr credential show --name "$ACR_NAME" --query "passwords[0].value" -o tsv)

az webapp create \
  --resource-group "$RESOURCE_GROUP" \
  --plan "$PLAN_NAME" \
  --name "$APP_NAME" \
  --deployment-container-image-name "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest"

az webapp config container set \
  --name "$APP_NAME" \
  --resource-group "$RESOURCE_GROUP" \
  --docker-custom-image-name "${ACR_LOGIN_SERVER}/${IMAGE_NAME}:latest" \
  --docker-registry-server-url "https://${ACR_LOGIN_SERVER}" \
  --docker-registry-server-user "$ACR_USERNAME" \
  --docker-registry-server-password "$ACR_PASSWORD"
```

---

## 4. Configure app settings

```bash
az webapp config appsettings set \
  --resource-group "$RESOURCE_GROUP" \
  --name "$APP_NAME" \
  --settings \
    AZURE_TENANT_ID="<tenant-id>" \
    AZURE_CLIENT_ID="<graph-app-client-id>" \
    AZURE_CLIENT_SECRET="<graph-app-client-secret>" \
    WEBSITES_PORT=8000 \
    SCM_DO_BUILD_DURING_DEPLOYMENT=false
```

Restart the app:

```bash
az webapp restart --resource-group "$RESOURCE_GROUP" --name "$APP_NAME"
```

Open `https://${APP_NAME}.azurewebsites.net` — the GUI should load.

---

## 5. Restrict access with Entra ID (recommended)

In [Azure Portal](https://portal.azure.com):

1. Open your Web App → **Authentication**
2. Click **Add identity provider** → **Microsoft**
3. Choose **Pick an existing app registration** or create new
4. Set **Restrict access** → **Require authentication**
5. Set unauthenticated requests → **HTTP 302 Found redirect to login page**
6. **Token store**: enabled
7. Save

Now only users in your tenant can open the app. Graph lookups still use the service principal from step 2.

---

## 6. Share with your team

Send: `https://${APP_NAME}.azurewebsites.net`

Team workflow:

1. Sign in with work account (if Entra auth enabled)
2. Upload CSV or paste user emails/UPNs
3. Click **Fetch immutable IDs**
4. Download results

---

## Update after code changes

Rebuild and redeploy:

```bash
az acr build \
  --registry "$ACR_NAME" \
  --image "${IMAGE_NAME}:latest" \
  .

az webapp restart --resource-group "$RESOURCE_GROUP" --name "$APP_NAME"
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| App won't start | **Log stream**: Portal → Web App → Log stream, or `az webapp log tail -g $RESOURCE_GROUP -n $APP_NAME` |
| Application Error | Check `WEBSITES_PORT=8000` is set |
| Authentication failed in app | Verify `AZURE_*` app settings; confirm Graph `User.Read.All` has admin consent |
| 403 from Graph | Application permission (not delegated); admin consent required |
| Redirect/login loops | In Authentication settings, set **Client secret** for the auth app registration |

---

## Optional: custom domain & HTTPS

Portal → Web App → **Custom domains** → add `immutable-id.allvuesystems.com` (or your domain) and bind a certificate.

---

## Cost estimate

- **B1 App Service plan**: ~$13/month
- **Basic ACR**: ~$5/month

Use a shared App Service plan if you host multiple small internal tools.
