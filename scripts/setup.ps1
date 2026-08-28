param(
    [switch]$WithDev,
    [switch]$WithAsr,
    [switch]$InstallPython
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"

function Test-PythonLauncher {
    param(
        [string]$Executable,
        [string[]]$LauncherArguments
    )
    try {
        & $Executable @LauncherArguments -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Find-PythonLauncher {
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        $listedPython = & $py.Source list --format=exe --one ">=3.11" 2>$null
        if ($LASTEXITCODE -eq 0 -and $listedPython) {
            $listedPath = @($listedPython)[0].Trim()
            if ((Test-Path -LiteralPath $listedPath) -and (Test-PythonLauncher -Executable $listedPath -LauncherArguments @())) {
                return @($listedPath)
            }
        }
    }

    $searchRoots = @(
        (Join-Path $env:LOCALAPPDATA "Python"),
        (Join-Path $env:LOCALAPPDATA "Programs\Python"),
        (Join-Path $env:ProgramFiles "Python")
    )
    foreach ($searchRoot in $searchRoots) {
        if (-not (Test-Path -LiteralPath $searchRoot)) { continue }
        $explicitPython = Get-ChildItem -LiteralPath $searchRoot -Filter python.exe -Recurse -ErrorAction SilentlyContinue |
            Where-Object { Test-PythonLauncher -Executable $_.FullName -LauncherArguments @() } |
            Sort-Object FullName -Descending |
            Select-Object -First 1
        if ($explicitPython) {
            return @($explicitPython.FullName)
        }
    }

    $python = Get-Command python -ErrorAction SilentlyContinue
    if (
        $python -and
        $python.Source -notlike "*\Microsoft\WindowsApps\*" -and
        (Test-PythonLauncher -Executable $python.Source -LauncherArguments @())
    ) {
        return @($python.Source)
    }
    return $null
}

$launcher = @(Find-PythonLauncher)
if ($launcher.Count -eq 0 -or -not $launcher[0]) {
    if (-not $InstallPython) {
        Write-Host "[ACTION_REQUIRED] Python 3.11 or later is not installed."
        Write-Host "Ask the user before installing software, then rerun:"
        Write-Host "powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -InstallPython"
        Write-Host "Official guide: https://docs.python.org/3/using/windows.html"
        exit 10
    }

    $pythonManager = Get-Command py -ErrorAction SilentlyContinue
    $managerAvailable = $false
    if ($pythonManager) {
        & $pythonManager.Source help install *> $null
        $managerAvailable = $LASTEXITCODE -eq 0
    }

    if ($managerAvailable) {
        Write-Host "Installing Python 3.13 with the official Python Install Manager."
        & $pythonManager.Source install 3.13
        if ($LASTEXITCODE -ne 0) {
            throw "Python Install Manager could not install Python 3.13."
        }
    } else {
        $winget = Get-Command winget -ErrorAction SilentlyContinue
        if (-not $winget) {
            Write-Host "[ACTION_REQUIRED] An automatic official install path is unavailable."
            Write-Host "Use the official Python Install Manager: https://www.python.org/downloads/windows/"
            exit 11
        }

        Write-Host "Installing Python 3.13 for the current user from the Windows Package Manager source."
        & $winget.Source install --exact --id Python.Python.3.13 --scope user --silent --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            throw "Python installation failed. Review the installer message before retrying."
        }
    }
    $launcher = @(Find-PythonLauncher)
    if ($launcher.Count -eq 0 -or -not $launcher[0]) {
        Write-Host "[ACTION_REQUIRED] Python was installed, but this terminal cannot see it yet."
        Write-Host "Close and reopen the AI agent or terminal, then run scripts/setup.ps1 again."
        exit 12
    }
}

Push-Location $repoRoot
try {
    Write-Host "[1/6] Checking Python 3.11+"
    $launcherExe = $launcher[0]
    $launcherArgs = @()
    if ($launcher.Count -gt 1) {
        $launcherArgs = $launcher[1..($launcher.Count - 1)]
    }
    & $launcherExe @launcherArgs -c "import sys; print('      Python ' + sys.version.split()[0])"

    Write-Host "[2/6] Preparing .venv"
    if (-not (Test-Path $venvPython)) {
        & $launcherExe @launcherArgs -m venv .venv
        if ($LASTEXITCODE -ne 0) {
            throw "Failed to create .venv."
        }
    } else {
        Write-Host "      Existing .venv will be reused."
    }

    Write-Host "[3/6] Installing the application"
    $extras = @()
    if ($WithDev) { $extras += "dev" }
    if ($WithAsr) { $extras += "asr" }
    $packageSpec = "."
    if ($extras.Count -gt 0) {
        $packageSpec = ".[$($extras -join ',')]"
    }
    & $venvPython -m pip install --editable $packageSpec
    if ($LASTEXITCODE -ne 0) {
        throw "Package installation failed."
    }

    Write-Host "[4/6] Preparing .env"
    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        Write-Host "      Created .env. The safe API-key guide follows."
    } else {
        Write-Host "      Existing .env was preserved."
    }

    Write-Host "[5/6] Checking the bundled production defaults"
    & $venvPython -c "from video_storyboard.knowledge import load_builtin_guidance; print(load_builtin_guidance().profile.profile_id)"
    if ($LASTEXITCODE -ne 0) {
        throw "Bundled production defaults are invalid."
    }

    Write-Host "[6/6] Running local diagnostics (no generation API calls)"
    & $venvPython scripts\doctor.py
    if ($LASTEXITCODE -ne 0) {
        throw "Diagnostics reported a blocking failure."
    }

    Write-Host "Base installation finished. Open the beginner setup page with scripts/open_setup.py now; its screens guide the Google setup."
} finally {
    Pop-Location
}
