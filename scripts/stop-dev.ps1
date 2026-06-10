<#
.SYNOPSIS
  Stop processes listening on dev ports 8000, 8090, 8002, 5173.
#>
$ErrorActionPreference = "SilentlyContinue"
$ports = @(8000, 8090, 8002, 5173)
foreach ($port in $ports) {
    $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($c in $conns) {
        $procId = $c.OwningProcess
        if ($procId) {
            $p = Get-Process -Id $procId -ErrorAction SilentlyContinue
            if ($p) {
                Write-Host "Stopping PID=$procId ($($p.ProcessName)) port $port"
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            }
        }
    }
}
Write-Host "Done."
