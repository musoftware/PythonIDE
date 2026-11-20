"""Functions recovered from Greeter.exe (native machine code).

Each function below documents what the original code calls and which strings it uses.
Bodies translated by AI are marked; the others are stubs to complete by hand.
"""
from __future__ import annotations   # AI signatures may name tkinter types



def MainProc(*args):
    """Native function at 0x140001760 (355 bytes, 64 instructions).
    Calls: EndDialog, GetDlgItemTextA, sprintf, SetDlgItemTextA, SendDlgItemMessageA, MessageBoxA
    Strings: 'Hello, %s!'; 'About Greeter'; 'Greeter 1.0 - made with MinGW'; 'Type a name and press Greet'
    """
    # pseudo-C from Ghidra:
    # undefined8 MainProc(HWND param_1,int param_2,ushort param_3)
    # 
    # {
    #   char local_148 [208];
    #   CHAR local_78 [120];
    #   
    #   if (param_2 == 0x110) {
    #     SetDlgItemTextA(param_1,0x3eb,"Type a name and press Greet");
    #   }
    #   else {
    #     if (param_2 != 0x111) {
    #       return 0;
    #     }
    #     if (param_3 == 0x9c42) {
    #       MessageBoxA(param_1,"Greeter 1.0 - made with MinGW","About Greeter",0x40);
    #     }
    #     else if (param_3 < 0x9c43) {
    #       if (param_3 == 0x3ea) {
    #         GetDlgItemTextA(param_1,0x3e9,local_78,100);
    #         sprintf(local_148,"Hello, %s!",local_78);
    #         SetDlgItemTextA(param_1,0x3eb,local_148);
    #         SendDlgItemMessageA(param_1,0x3ed,0x180,0,(LPARAM)local_78);
    #       }
    #       else {
    #         if ((param_3 != 0x9c41) && (param_3 != 2)) {
    #           return 0;
    #         }
    #         EndDialog(param_1,0);
    #       }
    #     }
    #     else {
    #       if (param_3 != 0x9c43) {
    #         return 0;
    #       }
    #       SendDlgItemMessageA(param_1,0x3ed,0x184,0,0);
    #     }
    #   }
    #   return 1;
    # }
    # EndDialog(?, 0)
    # GetDlgItemTextA(?, 0x3e9, buffer, 100)
    # sprintf(buffer, 'Hello, %s!', buffer)
    # SetDlgItemTextA(?, 0x3eb, buffer)
    # SendDlgItemMessageA(?, 0x3ed, 0x180, 0, buffer)
    # SendDlgItemMessageA(?, 0x3ed, 0x184, 0, 0)
    # MessageBoxA(?, 'Greeter 1.0 - made with MinGW', 'About Greeter', 64)
    # SetDlgItemTextA(?, 0x3eb, 'Type a name and press Greet')
    raise NotImplementedError


def AboutProc(*args):
    """Native function at 0x1400018C3 (58 bytes, 15 instructions).
    Calls: EndDialog
    """
    # pseudo-C from Ghidra:
    # bool AboutProc(HWND param_1,int param_2,short param_3)
    # 
    # {
    #   bool bVar1;
    #   
    #   if ((param_2 == 0x111) && ((ushort)(param_3 - 1U) < 2)) {
    #     EndDialog(param_1,0);
    #     bVar1 = true;
    #   }
    #   else {
    #     bVar1 = param_2 == 0x110;
    #   }
    #   return bVar1;
    # }
    # EndDialog(?, 0)
    raise NotImplementedError


def WinMain(*args):
    """Native function at 0x1400018FD (88 bytes, 18 instructions).
    Calls: DialogBoxParamA
    """
    # pseudo-C from Ghidra:
    # int __stdcall WinMain(HINSTANCE hInstance,HINSTANCE hPrevInstance,LPSTR lpCmdLine,int nShowCmd)
    # 
    # {
    #   int iVar1;
    #   INT_PTR IVar2;
    #   
    #   if ((lpCmdLine == (LPSTR)0x0) || (*lpCmdLine != 'a')) {
    #     IVar2 = DialogBoxParamA(hInstance,(LPCSTR)0x65,(HWND)0x0,MainProc,0);
    #     iVar1 = (int)IVar2;
    #   }
    #   else {
    #     IVar2 = DialogBoxParamA(hInstance,(LPCSTR)0x66,(HWND)0x0,AboutProc,0);
    #     iVar1 = (int)IVar2;
    #   }
    #   return iVar1;
    # }
    # DialogBoxParamA(?, 101, 0, &0x140001760, 0)
    # DialogBoxParamA(?, 102, 0, &0x1400018C3, 0)
    raise NotImplementedError


def main(*args):
    """Native function at 0x140001960 (298 bytes, 86 instructions).
    Calls: __main, __p__acmdln, GetStartupInfoA, WinMain, IsDBCSLeadByte
    """
    # pseudo-C from Ghidra:
    # int __cdecl main(int _Argc,char **_Argv,char **_Env)
    # 
    # {
    #   BOOL BVar1;
    #   int iVar2;
    #   undefined8 *puVar3;
    #   _STARTUPINFOA local_88;
    #   HINSTANCE local_20;
    #   uint local_18;
    #   uint local_14;
    #   BYTE *local_10;
    #   
    #   __main();
    #   local_20 = (HINSTANCE)_refptr___ImageBase;
    #   puVar3 = (undefined8 *)__p__acmdln();
    #   local_10 = (BYTE *)*puVar3;
    #   if (local_10 == (BYTE *)0x0) {
    #     local_10 = "";
    #   }
    #   else {
    #     local_18 = 0;
    #     while ((' ' < (char)*local_10 || ((*local_10 != '\0' && (local_18 != 0))))) {
    #       if (*local_10 == '\"') {
    #         local_18 = (uint)(local_18 == 0);
    #       }
    #       BVar1 = IsDBCSLeadByte(*local_10);
    #       if ((BVar1 != 0) && (local_10[1] != '\0')) {
    #         local_10 = local_10 + 1;
    #       }
    #       local_10 = local_10 + 1;
    #     }
    #     for (; (*local_10 != '\0' && ((char)*local_10 < '!')); local_10 = local_10 + 1) {
    #     }
    #   }
    #   GetStartupInfoA(&local_88);
    #   if ((local_88.dwFlags & 1) == 0) {
    #     local_14 = 10;
    #   }
    #   else {
    #     local_14 = (uint)local_88.wShowWindow;
    #   }
    #   iVar2 = WinMain(local_20,(HINSTANCE)0x0,(LPSTR)local_10,local_14);
    #   return iVar2;
    # }
    # __main()
    # __p__acmdln()
    # GetStartupInfoA(buffer)
    # WinMain(?, 0)
    # IsDBCSLeadByte()
    raise NotImplementedError
