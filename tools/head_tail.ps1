param(
  [Parameter(Mandatory=$true)][string]$Path,
  [int]$Head=40,
  [int]$Tail=40
)
if(-not (Test-Path $Path)) { Write-Host "not found: $Path"; exit 1 }
$sizeMB=[math]::Round(((Get-Item $Path).Length/1MB),2)
Write-Host ("{0} | SizeMB={1}" -f (Resolve-Path $Path), $sizeMB)
Write-Host "`n--- HEAD ($Head) ---"
Get-Content -Path $Path -TotalCount $Head | Write-Host
Write-Host "`n--- TAIL ($Tail) ---"
Get-Content -Path $Path -Tail $Tail | Write-Host
