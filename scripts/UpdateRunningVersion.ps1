$integration_name = "here_comes_the_bus"
$local_custom = $PSScriptRoot + "\custom_components\"
$ha_custom = "\\homeassistant.local\config\custom_components\"
robocopy /s /mir $local_custom$integration_name  $ha_custom$integration_name /XD "__pycache__" ".git" ".vscode"