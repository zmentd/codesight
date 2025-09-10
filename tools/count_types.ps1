param([Parameter(Mandatory=$true)][string]$Path)
if(-not (Test-Path $Path)) { Write-Host "not found: $Path"; exit 1 }
$sizeMB=[math]::Round(((Get-Item $Path).Length/1MB),2)
Write-Host ("File: {0}" -f (Resolve-Path $Path))
Write-Host ("SizeMB: {0}" -f $sizeMB)

$etype = @('Route','JSP','JavaMethod','Table','StoredProcedure','Role')
Write-Host "`n-- Entity Types --"
foreach($t in $etype){ $c=(Select-String -Path $Path -SimpleMatch -Pattern ('\"type\": \"'+$t+'\"') -Encoding UTF8 | Measure-Object).Count; '{0,-16} {1}' -f $t, $c | Write-Host }

$rtypes = @('renders','handlesRoute','mountedUnder','includesView','embedsView','redirectsTo','readsFrom','writesTo','deletesFrom','invokesProcedure','securedBy')
Write-Host "`n-- Relation Types --"
foreach($t in $rtypes){ $c=(Select-String -Path $Path -SimpleMatch -Pattern ('\"type\": \"'+$t+'\"') -Encoding UTF8 | Measure-Object).Count; '{0,-16} {1}' -f $t, $c | Write-Host }
