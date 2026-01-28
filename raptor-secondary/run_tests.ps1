Param([string[]]$Targets = @('tests'))
$ErrorActionPreference = 'Stop'
.\.venv\Scripts\Activate.ps1
pytest -q --maxfail=1 --disable-warnings --capture=no @Targets
