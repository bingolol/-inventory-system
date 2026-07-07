' 进销存管理系统 - 启动包装脚本
' 双击此文件将通过 pythonw.exe 启动桌面客户端（pywebview 原生窗口）
' 不会显示任何控制台窗口

Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")

' 获取脚本所在目录
scriptDir = fso.GetParentFolderName(WScript.ScriptFullName)

' 启动 Python 启动器（.pyw 不会弹出控制台窗口）
pywPath = scriptDir & "\run.pyw"

' 查找 pythonw.exe
pythonw = "pythonw.exe"
If Not fso.FileExists(pythonw) Then
    ' 尝试从 PATH 查找
    On Error Resume Next
    pythonw = shell.Exec("where pythonw.exe").StdOut.ReadAll
    pythonw = Trim(pythonw)
    If InStr(pythonw, vbCrLf) > 0 Then
        pythonw = Left(pythonw, InStr(pythonw, vbCrLf) - 1)
    End If
    On Error GoTo 0
End If

If fso.FileExists(pywPath) Then
    ' 使用 pythonw.exe 运行启动器（pywebview 桌面客户端模式）
    shell.Run """" & pythonw & """ """ & pywPath & """", 0, False
Else
    MsgBox "找不到启动文件: " & pywPath, vbCritical, "进销存管理系统"
End If
