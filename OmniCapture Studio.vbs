' OmniCapture Studio — Zero-Console Windows Launcher
' Launches the Desktop GUI application with zero CMD prompt flash.
Set oShell = CreateObject("WScript.Shell")
Set oFSO = CreateObject("Scripting.FileSystemObject")
strDir = oFSO.GetParentFolderName(WScript.ScriptFullName)

strVenvPythonw = strDir & "\.venv\Scripts\pythonw.exe"
strPyw = strDir & "\studio.pyw"

If oFSO.FileExists(strVenvPythonw) Then
    oShell.Run """" & strVenvPythonw & """ """ & strPyw & """", 0, False
Else
    oShell.Run "pythonw """ & strPyw & """", 0, False
End If
