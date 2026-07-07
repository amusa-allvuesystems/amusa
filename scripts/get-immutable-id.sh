#!/usr/bin/env bash
# Fetch the Entra ID (Azure AD) onPremisesImmutableId for a user via Microsoft Graph.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  get-immutable-id.sh <user-upn-or-object-id>
  get-immutable-id.sh --all

Examples:
  ./scripts/get-immutable-id.sh amusa@allvuesystems.com
  ./scripts/get-immutable-id.sh --all

Authentication (pick one):
  az login
  AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, AZURE_TENANT_ID (service principal)
EOF
}

ensure_az_login() {
  if az account show &>/dev/null; then
    return 0
  fi

  if [[ -n "${AZURE_CLIENT_ID:-}" && -n "${AZURE_CLIENT_SECRET:-}" && -n "${AZURE_TENANT_ID:-}" ]]; then
    az login \
      --service-principal \
      -u "$AZURE_CLIENT_ID" \
      -p "$AZURE_CLIENT_SECRET" \
      --tenant "$AZURE_TENANT_ID" \
      --output none
    return 0
  fi

  echo "Not logged in to Azure. Run 'az login' or set AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID." >&2
  exit 1
}

get_user_immutable_id() {
  local user_id="$1"
  az rest \
    --method GET \
    --url "https://graph.microsoft.com/v1.0/users/${user_id}?\$select=displayName,userPrincipalName,onPremisesImmutableId" \
    --query '{displayName: displayName, userPrincipalName: userPrincipalName, onPremisesImmutableId: onPremisesImmutableId}' \
    -o json
}

get_all_immutable_ids() {
  az rest \
    --method GET \
    --url "https://graph.microsoft.com/v1.0/users?\$select=displayName,userPrincipalName,onPremisesImmutableId" \
    --query "value[].{displayName: displayName, userPrincipalName: userPrincipalName, onPremisesImmutableId: onPremisesImmutableId}" \
    -o json
}

main() {
  if [[ $# -lt 1 ]]; then
    usage >&2
    exit 1
  fi

  ensure_az_login

  case "$1" in
    -h|--help)
      usage
      ;;
    --all)
      get_all_immutable_ids
      ;;
    *)
      get_user_immutable_id "$1"
      ;;
  esac
}

main "$@"
