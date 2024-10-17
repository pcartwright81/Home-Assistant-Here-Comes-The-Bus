$IntegrationName = "here_comes_the_bus"
$RootPath = (Split-Path $PSScriptRoot -Parent)
$Local = $RootPath + "\custom_components\" + $IntegrationName
$Remote = "\\homeassistant.local\config\custom_components\" + $IntegrationName
robocopy /s /mir $Local $Remote /XD "__pycache__" ".git" ".vscode"