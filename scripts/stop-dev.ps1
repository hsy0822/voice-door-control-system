<#
.SYNOPSIS
  尝试结束本机占用门禁开发默认端口的进程（需为当前用户启动的进程）。
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
                Write-Host "停止 PID=$procId ($($p.ProcessName)) 端口 $port"
                Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            }
        }
    }
}
Write-Host "完成（若无监听端口则无任何操作）。" -ForegroundColor Green
