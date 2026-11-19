#include <windows.h>
#include <stdio.h>
#define ID_A 101
#define ID_B 102
#define ID_ADD 103
#define ID_OUT 104
static LRESULT CALLBACK WndProc(HWND h, UINT m, WPARAM w, LPARAM l) {
  char a[32], b[32], buf[64];
  switch (m) {
  case WM_CREATE:
    CreateWindowExA(0, "STATIC", "First number:", WS_CHILD|WS_VISIBLE, 10, 12, 100, 20, h, (HMENU)0, NULL, NULL);
    CreateWindowExA(0, "EDIT", "", WS_CHILD|WS_VISIBLE|WS_BORDER, 120, 10, 120, 22, h, (HMENU)ID_A, NULL, NULL);
    CreateWindowExA(0, "STATIC", "Second number:", WS_CHILD|WS_VISIBLE, 10, 42, 100, 20, h, (HMENU)0, NULL, NULL);
    CreateWindowExA(0, "EDIT", "", WS_CHILD|WS_VISIBLE|WS_BORDER, 120, 40, 120, 22, h, (HMENU)ID_B, NULL, NULL);
    CreateWindowExA(0, "BUTTON", "Add", WS_CHILD|WS_VISIBLE|BS_PUSHBUTTON, 250, 25, 70, 26, h, (HMENU)ID_ADD, NULL, NULL);
    CreateWindowExA(0, "STATIC", "", WS_CHILD|WS_VISIBLE, 10, 75, 300, 20, h, (HMENU)ID_OUT, NULL, NULL);
    return 0;
  case WM_COMMAND:
    if (LOWORD(w) == ID_ADD) {
      GetDlgItemTextA(h, ID_A, a, 32); GetDlgItemTextA(h, ID_B, b, 32);
      sprintf(buf, "Sum = %d", atoi(a) + atoi(b));
      SetDlgItemTextA(h, ID_OUT, buf);
    }
    return 0;
  case WM_DESTROY: PostQuitMessage(0); return 0;
  }
  return DefWindowProcA(h, m, w, l);
}
int WINAPI WinMain(HINSTANCE hi, HINSTANCE p, LPSTR c, int s) {
  WNDCLASSA wc = {0}; MSG msg;
  wc.lpfnWndProc = WndProc; wc.hInstance = hi; wc.lpszClassName = "RadCalc";
  wc.hbrBackground = (HBRUSH)(COLOR_BTNFACE + 1); wc.hCursor = LoadCursor(NULL, IDC_ARROW);
  RegisterClassA(&wc);
  HWND h = CreateWindowExA(0, "RadCalc", "Adder", WS_OVERLAPPEDWINDOW|WS_VISIBLE, CW_USEDEFAULT, CW_USEDEFAULT, 360, 160, NULL, NULL, hi, NULL);
  while (GetMessageA(&msg, NULL, 0, 0)) { TranslateMessage(&msg); DispatchMessageA(&msg); }
  return 0;
}
