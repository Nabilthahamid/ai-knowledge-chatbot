$runtimeDirectory = Join-Path $PSScriptRoot 'ollama-runtime'
$ollamaExecutable = Join-Path $runtimeDirectory 'ollama.exe'
if (-not (Test-Path -LiteralPath $ollamaExecutable)) {
    $installedOllama = Get-Command ollama -ErrorAction SilentlyContinue
    if (-not $installedOllama) {
        throw 'Install Ollama from https://ollama.com/download/windows, then open a new terminal and retry.'
    }
    $ollamaExecutable = $installedOllama.Source
} else {
    $env:OLLAMA_MODELS = Join-Path $runtimeDirectory 'models'
}
$env:OLLAMA_HOST = '127.0.0.1:11434'
& $ollamaExecutable serve
