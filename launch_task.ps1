$User = (Get-WmiObject -Class Win32_ComputerSystem).UserName
if ($null -eq $User) { $User = $env:USERNAME }
$Action = New-ScheduledTaskAction -Execute "C:\Users\sures\.gemini\antigravity-ide\scratch\pdf-desktop-app\venv\Scripts\pythonw.exe" -Argument "app.py" -WorkingDirectory "C:\Users\sures\.gemini\antigravity-ide\scratch\pdf-desktop-app"
$Principal = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive
$Task = New-ScheduledTask -Action $Action -Principal $Principal
Register-ScheduledTask -TaskName "ForceLaunchPDF" -InputObject $Task -Force | Out-Null
Start-ScheduledTask -TaskName "ForceLaunchPDF"
Start-Sleep -Seconds 2
Unregister-ScheduledTask -TaskName "ForceLaunchPDF" -Confirm:$false
