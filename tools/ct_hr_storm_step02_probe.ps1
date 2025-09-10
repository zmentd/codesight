$ErrorActionPreference='Stop'
$f='D:\Prj\NBCU\storm\codesight\projects\ct-hr-storm\output\step02_output.json'
if(-not (Test-Path $f)){ Write-Host "File not found: $f"; exit 1 }
$sizeMB=[math]::Round(((Get-Item $f).Length/1MB),2)
Write-Host "File: $f"
Write-Host "SizeMB: $sizeMB"

Write-Host "`n-- Counts --"
try { $jsp = (Select-String -Path $f -Pattern '"path"\s*:\s*"[^"\n]+\.jsp"' -Encoding UTF8 -AllMatches | Measure-Object).Count } catch { $jsp = -1 }
Write-Host ("jsp_paths".PadRight(26) + " " + $jsp)

try { $stormps = (Select-String -Path $f -SimpleMatch -Pattern 'StormPS(' -Encoding UTF8 | Measure-Object).Count } catch { $stormps = -1 }
Write-Host ("StormPS(".PadRight(26) + " " + $stormps)

try { $roles = (Select-String -Path $f -Pattern 'javax\.annotation\.security\.RolesAllowed' -Encoding UTF8 | Measure-Object).Count } catch { $roles = -1 }
Write-Host ("rolesAllowed".PadRight(26) + " " + $roles)

try { $jaxrs = (Select-String -Path $f -Pattern 'javax\.ws\.rs\.Path' -Encoding UTF8 | Measure-Object).Count } catch { $jaxrs = -1 }
Write-Host ("jaxrsPath".PadRight(26) + " " + $jaxrs)

try { $fulltext = (Select-String -Path $f -SimpleMatch -Pattern '"full_text"' -Encoding UTF8 | Measure-Object).Count } catch { $fulltext = -1 }
Write-Host ("full_text_keys".PadRight(26) + " " + $fulltext)

try { $codekeys = (Select-String -Path $f -SimpleMatch -Pattern '"code"' -Encoding UTF8 | Measure-Object).Count } catch { $codekeys = -1 }
Write-Host ("code_keys".PadRight(26) + " " + $codekeys)

try { $restKey = (Select-String -Path $f -SimpleMatch -Pattern '"rest_endpoints"' -Encoding UTF8 | Measure-Object).Count } catch { $restKey = -1 }
Write-Host ("rest_endpoints_key".PadRight(26) + " " + $restKey)

try { $configKey = (Select-String -Path $f -SimpleMatch -Pattern '"configuration_details"' -Encoding UTF8 | Measure-Object).Count } catch { $configKey = -1 }
Write-Host ("configuration_details_key".PadRight(26) + " " + $configKey)

Write-Host "`n-- Contexts --"
Write-Host "--- javax.ws.rs.Path ---"
$ctx1 = Select-String -Path $f -Pattern 'javax\.ws\.rs\.Path' -Encoding UTF8 -Context 1,3 | Select-Object -First 1
if($ctx1){ $ctx1.Context.PreContext | Write-Host; $ctx1.Line | Write-Host; $ctx1.Context.PostContext | Write-Host } else { Write-Host 'none' }

Write-Host "--- StormPS( ---"
$ctx2 = Select-String -Path $f -SimpleMatch -Pattern 'StormPS(' -Encoding UTF8 -Context 0,2 | Select-Object -First 1
if($ctx2){ $ctx2.Context.PreContext | Write-Host; $ctx2.Line | Write-Host; $ctx2.Context.PostContext | Write-Host } else { Write-Host 'none' }
