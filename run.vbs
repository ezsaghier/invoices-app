' run.vbs - Launches Invoice System with no terminal window visible
Set objShell = CreateObject("WScript.Shell")
objShell.CurrentDirectory = "D:\InvoicesApp"
objShell.Run "python app.py", 0, False
