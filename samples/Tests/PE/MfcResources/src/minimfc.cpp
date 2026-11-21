// MiniMfc - a tiny MFC-compatible program for the RAD IDE PE workbench tests.
//
// The MFC library itself is not needed: this file re-creates the parts of MFC that end up in a real MFC
// binary - AFX_MSGMAP / AFX_MSGMAP_ENTRY tables with the same memory layout (32-bit: 24-byte entries,
// 64-bit: 32-byte entries), DECLARE_MESSAGE_MAP / BEGIN_MESSAGE_MAP macros, a virtual GetMessageMap()
// (so RTTI + vtables look like MFC's) and a dispatcher that walks the message-map chain exactly like
// CWnd::OnWndMsg / AfxFindMessageEntry. Retargeting or adding an entry in the exe therefore changes what
// the program really does, which is what the tests check.
#define WIN32_LEAN_AND_MEAN
#ifndef UNICODE
#define UNICODE
#endif
#ifndef _UNICODE
#define _UNICODE
#endif
#include <windows.h>
#include <commctrl.h>
#include "resource.h"

// ---------------------------------------------------------------- MFC-compatible message maps
struct AFX_MSGMAP;
// CCmdTarget is complete before AFX_PMSG (as in afxwin.h), so member pointers are single code pointers
class CCmdTarget {
public:
    virtual ~CCmdTarget() {}
    static const AFX_MSGMAP* PASCAL GetThisMessageMap();
    virtual const AFX_MSGMAP* GetMessageMap() const;
};
typedef void (CCmdTarget::*AFX_PMSG)(void);

struct AFX_MSGMAP_ENTRY {
    UINT nMessage;      // windows message
    UINT nCode;         // control code or WM_NOTIFY code
    UINT nID;           // control ID (or 0 for windows messages)
    UINT nLastID;       // used for entries specifying a range of control id's
    UINT_PTR nSig;      // signature type (action) or pointer to message #
    AFX_PMSG pfn;       // routine to call (or special value)
};

struct AFX_MSGMAP {
    const AFX_MSGMAP* (PASCAL* pfnGetBaseMap)();
    const AFX_MSGMAP_ENTRY* lpEntries;
};

enum AfxSig {           // numbering of MFC 7+ (afxmsg_.h) for the signatures used here
    AfxSig_end = 0,
    AfxSig_l_w_l = 14,  // LRESULT (WPARAM, LPARAM)   ON_MESSAGE
    AfxSig_vv = 19,     // void ()                     ON_COMMAND / ON_BN_CLICKED / ON_WM_CLOSE
    AfxSig_vw = 20,     // void (UINT)                 ON_CONTROL_RANGE / ON_WM_TIMER
};
#define AfxSigCmd_v AfxSig_vv
#define CN_COMMAND 0
#define CN_UPDATE_COMMAND_UI ((UINT)(-1))

#define DECLARE_MESSAGE_MAP() \
protected: \
    static const AFX_MSGMAP* PASCAL GetThisMessageMap(); \
    virtual const AFX_MSGMAP* GetMessageMap() const;

#define BEGIN_MESSAGE_MAP(theClass, baseClass) \
    const AFX_MSGMAP* theClass::GetMessageMap() const { return GetThisMessageMap(); } \
    const AFX_MSGMAP* PASCAL theClass::GetThisMessageMap() { \
        typedef theClass ThisClass; typedef baseClass TheBaseClass; \
        static const AFX_MSGMAP_ENTRY _messageEntries[] = {

#define END_MESSAGE_MAP() \
        {0, 0, 0, 0, AfxSig_end, (AFX_PMSG)0 } }; \
        static const AFX_MSGMAP messageMap = { &TheBaseClass::GetThisMessageMap, &_messageEntries[0] }; \
        return &messageMap; }

#define ON_COMMAND(id, memberFxn) \
    { WM_COMMAND, CN_COMMAND, (WORD)id, (WORD)id, AfxSigCmd_v, static_cast<AFX_PMSG>(&ThisClass::memberFxn) },
#define ON_UPDATE_COMMAND_UI(id, memberFxn) \
    { WM_COMMAND, CN_UPDATE_COMMAND_UI, (WORD)id, (WORD)id, AfxSig_vw,       (AFX_PMSG)(static_cast<void (CCmdTarget::*)(UINT)>(&ThisClass::memberFxn)) },
#define ON_CONTROL(code, id, memberFxn) \
    { WM_COMMAND, (WORD)code, (WORD)id, (WORD)id, AfxSigCmd_v, static_cast<AFX_PMSG>(&ThisClass::memberFxn) },
#define ON_BN_CLICKED(id, memberFxn) ON_CONTROL(BN_CLICKED, id, memberFxn)
#define ON_EN_CHANGE(id, memberFxn) ON_CONTROL(EN_CHANGE, id, memberFxn)
#define ON_CONTROL_RANGE(code, id, idLast, memberFxn) \
    { WM_COMMAND, (WORD)code, (WORD)id, (WORD)idLast, AfxSig_vw, \
      (AFX_PMSG)(static_cast<void (CCmdTarget::*)(UINT)>(&ThisClass::memberFxn)) },
#define ON_MESSAGE(message, memberFxn) \
    { message, 0, 0, 0, AfxSig_l_w_l, \
      (AFX_PMSG)(static_cast<LRESULT (CCmdTarget::*)(WPARAM, LPARAM)>(&ThisClass::memberFxn)) },
#define ON_WM_CLOSE() { WM_CLOSE, 0, 0, 0, AfxSig_vv, static_cast<AFX_PMSG>(&ThisClass::OnClose) },
#define ON_WM_TIMER() { WM_TIMER, 0, 0, 0, AfxSig_vw, \
      (AFX_PMSG)(static_cast<void (CCmdTarget::*)(UINT)>(&ThisClass::OnTimer)) },

// ---------------------------------------------------------------- classes
const AFX_MSGMAP* CCmdTarget::GetMessageMap() const { return GetThisMessageMap(); }
const AFX_MSGMAP* PASCAL CCmdTarget::GetThisMessageMap() {
    static const AFX_MSGMAP_ENTRY _messageEntries[] = { {0, 0, 0, 0, AfxSig_end, (AFX_PMSG)0 } };
    static const AFX_MSGMAP messageMap = { NULL, &_messageEntries[0] };
    return &messageMap;
}

class CWnd : public CCmdTarget {
public:
    HWND m_hWnd = NULL;
    BOOL OnWndMsg(UINT message, WPARAM wParam, LPARAM lParam, LRESULT* pResult);
    void SetDlgItemTextW_(int id, const wchar_t* s) { ::SetDlgItemTextW(m_hWnd, id, s); }
    DECLARE_MESSAGE_MAP()
};
BEGIN_MESSAGE_MAP(CWnd, CCmdTarget)
END_MESSAGE_MAP()

static const AFX_MSGMAP_ENTRY* AfxFindMessageEntry(const AFX_MSGMAP_ENTRY* e, UINT nMsg, UINT nCode, UINT nID) {
    while (e->nSig != AfxSig_end) {
        if (e->nMessage == nMsg && e->nCode == nCode && nID >= e->nID && nID <= e->nLastID)
            return e;
        e++;
    }
    return NULL;
}

BOOL CWnd::OnWndMsg(UINT message, WPARAM wParam, LPARAM lParam, LRESULT* pResult) {
    UINT nCode = 0, nID = 0;
    if (message == WM_COMMAND) { nCode = HIWORD(wParam); nID = LOWORD(wParam); }
    for (const AFX_MSGMAP* map = GetMessageMap(); map != NULL;
         map = map->pfnGetBaseMap ? map->pfnGetBaseMap() : NULL) {
        const AFX_MSGMAP_ENTRY* e = AfxFindMessageEntry(map->lpEntries, message, nCode, nID);
        if (!e)
            continue;
        union { AFX_PMSG pfn; void (CCmdTarget::*pfn_vw)(UINT); LRESULT (CCmdTarget::*pfn_lwl)(WPARAM, LPARAM); } mmf;
        mmf.pfn = e->pfn;
        switch (e->nSig) {
        case AfxSig_vv: (this->*mmf.pfn)(); *pResult = 0; return TRUE;
        case AfxSig_vw: (this->*mmf.pfn_vw)(message == WM_COMMAND ? nID : (UINT)wParam); *pResult = 0; return TRUE;
        case AfxSig_l_w_l: *pResult = (this->*mmf.pfn_lwl)(wParam, lParam); return TRUE;
        }
    }
    return FALSE;
}

class CDialog : public CWnd {
public:
    UINT m_nIDTemplate;
    explicit CDialog(UINT nIDTemplate) : m_nIDTemplate(nIDTemplate) {}
    INT_PTR DoModal(HWND hParent = NULL);
    virtual BOOL OnInitDialog() { return TRUE; }
    void EndDialog(int r) { ::EndDialog(m_hWnd, r); }
    void OnOK() { EndDialog(IDOK); }
    void OnCancel() { EndDialog(IDCANCEL); }
    void OnClose() { EndDialog(IDCANCEL); }
    static INT_PTR CALLBACK DlgProc(HWND h, UINT m, WPARAM w, LPARAM l);
    DECLARE_MESSAGE_MAP()
};
BEGIN_MESSAGE_MAP(CDialog, CWnd)
    ON_COMMAND(IDOK, OnOK)
    ON_COMMAND(IDCANCEL, OnCancel)
    ON_WM_CLOSE()
END_MESSAGE_MAP()

INT_PTR CALLBACK CDialog::DlgProc(HWND h, UINT m, WPARAM w, LPARAM l) {
    CDialog* self;
    if (m == WM_INITDIALOG) {
        self = (CDialog*)l;
        self->m_hWnd = h;
        SetWindowLongPtrW(h, GWLP_USERDATA, (LONG_PTR)self);
        return self->OnInitDialog();
    }
    self = (CDialog*)GetWindowLongPtrW(h, GWLP_USERDATA);
    if (!self)
        return FALSE;
    LRESULT r = 0;
    if (self->OnWndMsg(m, w, l, &r)) {
        SetWindowLongPtrW(h, DWLP_MSGRESULT, r);
        return TRUE;
    }
    return FALSE;
}

INT_PTR CDialog::DoModal(HWND hParent) {
    return DialogBoxParamW(GetModuleHandleW(NULL), MAKEINTRESOURCEW(m_nIDTemplate), hParent, DlgProc, (LPARAM)this);
}

class CAboutDlg : public CDialog {
public:
    CAboutDlg() : CDialog(IDD_ABOUT) {}
    void OnAboutOk() { EndDialog(IDOK); }
    DECLARE_MESSAGE_MAP()
};
BEGIN_MESSAGE_MAP(CAboutDlg, CDialog)
    ON_BN_CLICKED(IDOK, OnAboutOk)
END_MESSAGE_MAP()

class CMainDlg : public CDialog {
public:
    HACCEL m_hAccel = NULL;
    int m_nChanges = 0;
    CMainDlg() : CDialog(IDD_MAIN) {}
    BOOL OnInitDialog() override;
    void ShowString(UINT ids);
    void OnButton1();
    void OnButton2();
    void OnInfo();
    void OnEditChange();
    void OnRadio(UINT nID);
    void OnFileHello();
    void OnFileExit();
    void OnHelpAbout();
    void OnEditClear();
    void OnUpdateHello(UINT) {}
    void OnTimer(UINT nIDEvent);
    LRESULT OnUserPing(WPARAM w, LPARAM l);
    DECLARE_MESSAGE_MAP()
};
BEGIN_MESSAGE_MAP(CMainDlg, CDialog)
    ON_BN_CLICKED(IDC_BUTTON1, OnButton1)
    ON_BN_CLICKED(IDC_BUTTON2, OnButton2)
    ON_BN_CLICKED(IDC_INFO, OnInfo)
    ON_EN_CHANGE(IDC_EDIT1, OnEditChange)
    ON_CONTROL_RANGE(BN_CLICKED, IDC_RADIO1, IDC_RADIO3, OnRadio)
    ON_COMMAND(ID_FILE_HELLO, OnFileHello)
    ON_COMMAND(ID_FILE_EXIT, OnFileExit)
    ON_COMMAND(ID_HELP_ABOUT, OnHelpAbout)
    ON_COMMAND(ID_EDIT_CLEAR, OnEditClear)
    ON_UPDATE_COMMAND_UI(ID_FILE_HELLO, OnUpdateHello)
    ON_MESSAGE(WM_USER + 100, OnUserPing)
    ON_WM_TIMER()
END_MESSAGE_MAP()

BOOL CMainDlg::OnInitDialog() {
    // DLGINIT: MFC fills combo boxes from RT_DLGINIT (240); do the same here
    HRSRC hr = FindResourceW(NULL, MAKEINTRESOURCEW(IDD_MAIN), MAKEINTRESOURCEW(240));
    if (hr) {
        const BYTE* p = (const BYTE*)LockResource(LoadResource(NULL, hr));
        while (p && *(const WORD*)p) {
            WORD id = *(const WORD*)p, msg = *(const WORD*)(p + 2);
            DWORD len = *(const DWORD*)(p + 4);
            SendDlgItemMessageA(m_hWnd, id, msg, 0, (LPARAM)(p + 8));
            p += 8 + len;
        }
    }
    SendDlgItemMessageW(m_hWnd, IDC_COMBO1, CB_SETCURSEL, 0, 0);
    SendDlgItemMessageW(m_hWnd, IDC_LIST1, LB_ADDSTRING, 0, (LPARAM)L"MiniMfc started");
    SendMessageW(m_hWnd, WM_SETICON, ICON_BIG, (LPARAM)LoadIconW(GetModuleHandleW(NULL), MAKEINTRESOURCEW(IDI_APP)));
    return TRUE;
}

void CMainDlg::ShowString(UINT ids) {
    wchar_t buf[256] = L"";
    LoadStringW(GetModuleHandleW(NULL), ids, buf, 256);
    SetDlgItemTextW_(IDC_STATUS, buf);
}
void CMainDlg::OnButton1() { ShowString(IDS_HELLO); }
void CMainDlg::OnButton2() { ShowString(IDS_BYE); }
void CMainDlg::OnInfo() { MessageBoxW(m_hWnd, L"MiniMfc information", L"MiniMfc", MB_OK | MB_ICONINFORMATION); }
void CMainDlg::OnEditChange() {
    wchar_t buf[64];
    wsprintfW(buf, L"Edited %d", ++m_nChanges);
    SetDlgItemTextW_(IDC_STATUS, buf);
}
void CMainDlg::OnRadio(UINT nID) {
    wchar_t buf[64];
    wsprintfW(buf, L"Radio %u", nID - IDC_RADIO1 + 1);
    SetDlgItemTextW_(IDC_STATUS, buf);
}
void CMainDlg::OnFileHello() { SetDlgItemTextW_(IDC_STATUS, L"Menu Hello"); }
void CMainDlg::OnFileExit() { EndDialog(IDOK); }
void CMainDlg::OnHelpAbout() { CAboutDlg dlg; dlg.DoModal(m_hWnd); }
void CMainDlg::OnEditClear() { SetDlgItemTextW_(IDC_EDIT1, L""); SetDlgItemTextW_(IDC_STATUS, L"Cleared"); }
void CMainDlg::OnTimer(UINT nIDEvent) { KillTimer(m_hWnd, nIDEvent); }
LRESULT CMainDlg::OnUserPing(WPARAM w, LPARAM) {
    SetDlgItemTextW_(IDC_STATUS, L"Ping");
    return (LRESULT)(w + 1);
}

int WINAPI wWinMain(HINSTANCE, HINSTANCE, LPWSTR, int) {
    INITCOMMONCONTROLSEX icc = { sizeof(icc), ICC_STANDARD_CLASSES };
    InitCommonControlsEx(&icc);
    CMainDlg dlg;
    return (int)dlg.DoModal();
}
