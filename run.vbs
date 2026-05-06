' run.vbs - Silent launcher for Invoice System
' Sets INVOICES_APP_DIR so the app always finds its database
' regardless of which Windows user account runs it

Dim objShell, objFSO, appDir, pathFile

Set objShell = CreateObject("WScript.Shell")
Set objFSO   = CreateObject("Scripting.FileSystemObject")

' Find the app directory from install_path.txt (same folder as this script)
appDir = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Try to read install_path.txt for the authoritative install location
Dim pathFilePath
pathFilePath = appDir & "\install_path.txt"
If objFSO.FileExists(pathFilePath) Then
    Dim ts
    Set ts = objFSO.OpenTextFile(pathFilePath, 1)
    Dim storedPath
    storedPath = Trim(ts.ReadLine())
    ts.Close
    If objFSO.FolderExists(storedPath) Then
        appDir = storedPath
    End If
End If

' Set environment variable so database.py always finds the right folder
objShell.Environment("Process")("INVOICES_APP_DIR") = appDir

' Launch Python app silently (0 = hidden window, False = don't wait)
objShell.CurrentDirectory = appDir
objShell.Run "python app.py", 0, False
