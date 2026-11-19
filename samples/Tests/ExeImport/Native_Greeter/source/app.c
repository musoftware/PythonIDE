#include <windows.h>
#include <stdio.h>
#include "res.h"
static HINSTANCE hInst;
static INT_PTR CALLBACK AboutProc(HWND h, UINT m, WPARAM w, LPARAM l) {
  if (m == WM_COMMAND && (LOWORD(w) == IDOK || LOWORD(w) == IDCANCEL)) { EndDialog(h, 0); return TRUE; }
  return m == WM_INITDIALOG;
}
static INT_PTR CALLBACK MainProc(HWND h, UINT m, WPARAM w, LPARAM l) {
  char name[100], buf[200];
  switch (m) {
  case WM_INITDIALOG:
    SetDlgItemTextA(h, IDC_RESULT, "Type a name and press Greet");
    return TRUE;
  case WM_COMMAND:
    switch (LOWORD(w)) {
    case IDC_GREET:
      GetDlgItemTextA(h, IDC_NAME, name, 100);
      sprintf(buf, "Hello, %s!", name);
      SetDlgItemTextA(h, IDC_RESULT, buf);
      SendDlgItemMessageA(h, IDC_LIST, LB_ADDSTRING, 0, (LPARAM)name);
      return TRUE;
    case IDM_CLEAR:
      SendDlgItemMessageA(h, IDC_LIST, LB_RESETCONTENT, 0, 0);
      return TRUE;
    case IDM_ABOUT:
      MessageBoxA(h, "Greeter 1.0 - made with MinGW", "About Greeter", MB_OK | MB_ICONINFORMATION);
      return TRUE;
    case IDM_EXIT:
    case IDCANCEL:
      EndDialog(h, 0);
      return TRUE;
    }
  }
  return FALSE;
}
int WINAPI WinMain(HINSTANCE hi, HINSTANCE p, LPSTR c, int s) {
  hInst = hi;
  if (c && c[0] == 'a') return (int)DialogBoxParamA(hi, MAKEINTRESOURCEA(IDD_ABOUT), NULL, AboutProc, 0);
  return (int)DialogBoxParamA(hi, MAKEINTRESOURCEA(IDD_MAIN), NULL, MainProc, 0);
}
