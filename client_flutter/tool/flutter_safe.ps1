param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$FlutterArgs
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$localPropertiesPath = Join-Path $projectRoot "android\local.properties"
$flutterRoot = $null

if (Test-Path $localPropertiesPath) {
    $flutterSdkLine = Get-Content $localPropertiesPath |
        Where-Object { $_ -match '^flutter\.sdk=' } |
        Select-Object -First 1
    if ($flutterSdkLine) {
        $flutterRoot = ($flutterSdkLine -replace '^flutter\.sdk=', '').Trim()
        $flutterRoot = $flutterRoot -replace '\\\\', '\'
    }
}

if (-not $flutterRoot) {
    $flutterRoot = $env:FLUTTER_ROOT
}

if (-not $flutterRoot) {
    throw "Unable to resolve Flutter SDK path from android/local.properties."
}

$flutterRoot = [System.IO.Path]::GetFullPath($flutterRoot)
$dartExe = Join-Path $flutterRoot "bin\cache\dart-sdk\bin\dart.exe"
$snapshotPath = Join-Path $flutterRoot "bin\cache\flutter_tools.snapshot"
$androidSdkStub = Join-Path $PSScriptRoot "android-sdk-stub"

if (-not (Test-Path $dartExe)) {
    throw "Dart executable not found: $dartExe"
}

if (-not (Test-Path $snapshotPath)) {
    throw "flutter_tools.snapshot not found: $snapshotPath"
}

$env:GIT_CONFIG_COUNT = "1"
$env:GIT_CONFIG_KEY_0 = "safe.directory"
$env:GIT_CONFIG_VALUE_0 = $flutterRoot

if (-not $env:ANDROID_HOME) {
    $env:ANDROID_HOME = $androidSdkStub
}
if (-not $env:ANDROID_SDK_ROOT) {
    $env:ANDROID_SDK_ROOT = $androidSdkStub
}

& $dartExe $snapshotPath @FlutterArgs
exit $LASTEXITCODE
