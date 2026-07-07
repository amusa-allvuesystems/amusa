# Convert an on-premises AD ObjectGUID to the Entra ID onPremisesImmutableId format.
param(
    [Parameter(Mandatory = $true)]
    [string]$ObjectGuid
)

$guid = [guid]::Parse($ObjectGuid)
$bytes = $guid.ToByteArray()
$immutableId = [Convert]::ToBase64String($bytes)

[pscustomobject]@{
    ObjectGuid   = $ObjectGuid
    ImmutableId  = $immutableId
}
