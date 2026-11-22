# (c) 2026 Musoftware - https://musoftwares.com - MIT License
# Ring Notepad - a small text editor made with the RingQt form designer.
# Shows: MenuStrip (File/Edit/Format/Help), a ToolStrip, a multi-line TextBox (qTextEdit), the Open/Save/Font dialog
# components, the clipboard (Cut/Copy/Paste), a StatusBar with live counts, and opening a file passed on
# the command line (ring _radrun.ring notes.txt  or  RingNotepad.exe notes.txt after Build > Publish).

load "Form1_designer.ring"

cFileName = ""          # the file being edited ("" = Untitled)
lDirty = false          # changed since the last save
lWrap = true            # Format > Word Wrap

# ---------------- Event handlers ----------------

func Form1_Load
    # the last command-line argument that is an existing file is opened
    for i = len(sysargv) to 2 step -1
        cArg = sysargv[i]
        if lower(right(cArg, 5)) != ".ring" and fexists(cArg)
            OpenFile(cArg)
            exit
        ok
    next
    UpdateStatus()

func txtEditor_TextChanged
    lDirty = true
    UpdateTitle()
    UpdateStatus()

# ---- File
func mnuFileNew_Click
    txtEditor.setPlainText("")
    cFileName = ""
    lDirty = false
    UpdateTitle()

func mnuFileOpen_Click
    if dlgOpen.ShowDialog() = "OK"
        OpenFile(dlgOpen.FileName)
    ok

func mnuFileSave_Click
    if cFileName = ""
        mnuFileSaveAs_Click()
    else
        SaveFile(cFileName)
    ok

func mnuFileSaveAs_Click
    dlgSave.FileName = cFileName
    if dlgSave.ShowDialog() = "OK"
        SaveFile(dlgSave.FileName)
    ok

func mnuFileExit_Click
    Form1.close()

# ---- Edit (qTextEdit talks to the system clipboard itself)
func mnuEditCut_Click
    txtEditor.cut()

func mnuEditCopy_Click
    txtEditor.copy()

func mnuEditPaste_Click
    txtEditor.paste()

func mnuEditSelectAll_Click
    txtEditor.selectAll()

func mnuEditUpper_Click
    # upper-cases the whole text (Arabic letters have no case and stay as they are)
    txtEditor.setPlainText(upper(txtEditor.toPlainText()))

func mnuEditTime_Click
    txtEditor.insertPlainText(date() + " " + time())

# ---- Format
func mnuFormatFont_Click
    if dlgFont.ShowDialog() = "OK"
        txtEditor.setStyleSheet("font-family:'" + dlgFont.FontName + "';font-size:" + dlgFont.FontSize + "pt;")
    ok

func mnuFormatWrap_Click
    lWrap = not lWrap
    if lWrap txtEditor.setLineWrapMode(1) else txtEditor.setLineWrapMode(0) ok
    lblStatus.setText(lblStatus.text() + "   Wrap: " + iif(lWrap, "on", "off"))

# ---- ToolStrip (tsMain): the buttons run the same code as the menu items
func tbNew_Click
    mnuFileNew_Click()

func tbOpen_Click
    mnuFileOpen_Click()

func tbSave_Click
    mnuFileSave_Click()

func tbCut_Click
    mnuEditCut_Click()

func tbCopy_Click
    mnuEditCopy_Click()

func tbPaste_Click
    mnuEditPaste_Click()

func tbUpper_Click
    mnuEditUpper_Click()

func tbTime_Click
    mnuEditTime_Click()

func mnuHelpAbout_Click
    oMsg = new qMessageBox(Form1)
    oMsg.setWindowTitle("About Ring Notepad")
    oMsg.setText("Ring Notepad - a RAD IDE example (RingQt)." + nl +
                 "(c) 2026 Musoftware - https://musoftwares.com - MIT License")
    oMsg.show()

# ---------------- helpers ----------------

func OpenFile cFile
    txtEditor.setPlainText(read(cFile))
    cFileName = cFile
    lDirty = false
    UpdateTitle()
    UpdateStatus()

func SaveFile cFile
    write(cFile, txtEditor.toPlainText())
    cFileName = cFile
    lDirty = false
    UpdateTitle()
    lblStatus.setText("Saved " + cFile)

func UpdateTitle
    cName = "Untitled"
    if cFileName != "" cName = JustFileName(cFileName) ok
    if lDirty cName = "*" + cName ok
    Form1.setWindowTitle("Ring Notepad - " + cName)

func UpdateStatus
    cText = txtEditor.toPlainText()
    nLines = 1  nWords = 0  nChars = 0  lInWord = false
    for i = 1 to len(cText)
        c = cText[i]
        nByte = ascii(c)
        if (nByte & 192) != 128 nChars++ ok           # count UTF-8 characters, not bytes
        if c = nl nLines++ ok
        if c = " " or c = nl or c = char(9) or c = char(13)
            lInWord = false
        but not lInWord
            lInWord = true
            nWords++
        ok
    next
    lblStatus.setText("Lines: " + nLines + "   Words: " + nWords + "   Chars: " + nChars)

func JustFileName cPath
    cPath = substr(cPath, "\", "/")
    for i = len(cPath) to 1 step -1
        if cPath[i] = "/" return substr(cPath, i + 1) ok
    next
    return cPath

func iif lCond, vYes, vNo
    if lCond return vYes ok
    return vNo
