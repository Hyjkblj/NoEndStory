# 检查 Git 安装位置
Write-Host "正在检查 Git 安装位置..." -ForegroundColor Yellow
Write-Host ""

# 常见安装路径
$gitPaths = @(
    "C:\Program Files\Git\bin\git.exe",
    "C:\Program Files (x86)\Git\bin\git.exe",
    "$env:LOCALAPPDATA\Programs\Git\bin\git.exe",
    "$env:ProgramFiles\Git\cmd\git.exe",
    "$env:ProgramFiles(x86)\Git\cmd\git.exe"
)

$found = $false
foreach ($path in $gitPaths) {
    if (Test-Path $path) {
        Write-Host "找到 Git: $path" -ForegroundColor Green
        $found = $true
        
        # 尝试运行
        Write-Host "测试运行..." -ForegroundColor Yellow
        & $path --version
        
        Write-Host ""
        Write-Host "Git 已安装但不在 PATH 中！" -ForegroundColor Yellow
        Write-Host "解决方案：" -ForegroundColor Cyan
        Write-Host "1. 临时添加到当前会话：" -ForegroundColor White
        Write-Host "   `$env:PATH += `";C:\Program Files\Git\bin`"" -ForegroundColor Gray
        Write-Host ""
        Write-Host "2. 永久添加到 PATH：" -ForegroundColor White
        Write-Host "   - 右键'此电脑' -> 属性 -> 高级系统设置" -ForegroundColor Gray
        Write-Host "   - 环境变量 -> 系统变量 -> Path -> 编辑" -ForegroundColor Gray
        Write-Host "   - 添加: C:\Program Files\Git\bin" -ForegroundColor Gray
        Write-Host ""
        Write-Host "3. 或者重新安装 Git，安装时选择 'Add Git to PATH'" -ForegroundColor White
        break
    }
}

if (-not $found) {
    Write-Host "未找到 Git 安装！" -ForegroundColor Red
    Write-Host ""
    Write-Host "请安装 Git：" -ForegroundColor Yellow
    Write-Host "1. 访问: https://git-scm.com/downloads" -ForegroundColor White
    Write-Host "2. 下载 Windows 版本" -ForegroundColor White
    Write-Host "3. 安装时选择 'Add Git to PATH'" -ForegroundColor White
    Write-Host "4. 安装后重启 PowerShell" -ForegroundColor White
}

