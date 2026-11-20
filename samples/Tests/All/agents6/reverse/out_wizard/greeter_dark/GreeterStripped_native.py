"""Functions recovered from Greeter_stripped.exe (native machine code).

Each function below documents what the original code calls and which strings it uses.
Bodies translated by AI are marked; the others are stubs to complete by hand.
"""
from __future__ import annotations   # AI signatures may name tkinter types



def sub_140001760(*args):
    """Native function at 0x140001760 (355 bytes, 64 instructions).
    Calls: EndDialog, GetDlgItemTextA, sprintf, SetDlgItemTextA, SendDlgItemMessageA, MessageBoxA
    Strings: 'Hello, %s!'; 'About Greeter'; 'Greeter 1.0 - made with MinGW'; 'Type a name and press Greet'
    """
    # pseudo-C from Ghidra:
    # undefined8 sub_140001760(HWND param_1,int param_2,ushort param_3)
    # 
    # {
    #   undefined8 uVar1;
    #   CHAR local_148 [208];
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
    #         uVar1 = 100;
    #         GetDlgItemTextA(param_1,0x3e9,local_78,100);
    #         sub_1400033F0(local_148,"Hello, %s!",local_78,uVar1);
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


def sub_1400018C3(*args):
    """Native function at 0x1400018C3 (58 bytes, 15 instructions).
    Calls: EndDialog
    """
    # pseudo-C from Ghidra:
    # bool sub_1400018C3(HWND param_1,int param_2,short param_3)
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


def sub_1400018FD(*args):
    """Native function at 0x1400018FD (88 bytes, 18 instructions).
    Calls: DialogBoxParamA
    """
    # pseudo-C from Ghidra:
    # void sub_1400018FD(HINSTANCE param_1,undefined8 param_2,char *param_3)
    # 
    # {
    #   if ((param_3 == (char *)0x0) || (*param_3 != 'a')) {
    #     DialogBoxParamA(param_1,(LPCSTR)0x65,(HWND)0x0,sub_140001760,0);
    #   }
    #   else {
    #     DialogBoxParamA(param_1,(LPCSTR)0x66,(HWND)0x0,sub_1400018C3,0);
    #   }
    #   return;
    # }
    # DialogBoxParamA(?, 101, 0, &0x140001760, 0)
    # DialogBoxParamA(?, 102, 0, &0x1400018C3, 0)
    raise NotImplementedError


def sub_140001DB0(*args):
    """Native function at 0x140001DB0 (100 bytes, 25 instructions).
    Calls: __acrt_iob_func, printf, abort
    Strings: 'Mingw-w64 runtime failure:\n'
    """
    # pseudo-C from Ghidra:
    # void sub_140001DB0(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4)
    # 
    # {
    #   undefined8 uVar1;
    #   undefined8 local_res10;
    #   undefined8 local_res18;
    #   undefined8 local_res20;
    #   
    #   local_res10 = param_2;
    #   local_res18 = param_3;
    #   local_res20 = param_4;
    #   uVar1 = __acrt_iob_func(2);
    #   sub_140003460(uVar1,"Mingw-w64 runtime failure:\n",param_3,param_4);
    #   uVar1 = __acrt_iob_func(2);
    #   sub_1400033A0(uVar1,param_1,&local_res10);
    #                     /* WARNING: Subroutine does not return */
    #   abort();
    # }
    # __acrt_iob_func(2)
    # printf(?, 'Mingw-w64 runtime failure:\n')
    # __acrt_iob_func(2)
    # printf(?, ?, buffer)
    # abort()
    raise NotImplementedError


def sub_140001E15(*args):
    """Native function at 0x140001E15 (734 bytes, 192 instructions).
    Calls: sub_14000308B, sub_140001DB0, sub_1400031D7, VirtualQuery, VirtualProtect, GetLastError
    Strings: 'Address %p has no image-section'; '  VirtualQuery failed for %d bytes at address %p'; '  VirtualProtect failed with code 0x%x'
    """
    # pseudo-C from Ghidra:
    # void sub_140001E15(ulonglong param_1,undefined8 param_2,longlong param_3,undefined8 param_4)
    # 
    # {
    #   BOOL BVar1;
    #   DWORD DVar2;
    #   IMAGE_DOS_HEADER *pIVar3;
    #   SIZE_T SVar4;
    #   PDWORD lpflOldProtect;
    #   ulonglong uVar5;
    #   _MEMORY_BASIC_INFORMATION local_48;
    #   longlong local_18;
    #   uint local_10;
    #   int local_c;
    #   
    #   local_c = 0;
    #   while( true ) {
    #     if (DAT_1400090f8 <= local_c) {
    #       local_18 = sub_14000308B(param_1);
    #       if (local_18 == 0) {
    #         sub_140001DB0("Address %p has no image-section",param_1,param_3,param_4);
    #       }
    #       *(longlong *)(DAT_1400090f0 + (longlong)local_c * 0x28 + 0x20) = local_18;
    #       *(undefined4 *)((longlong)local_c * 0x28 + DAT_1400090f0) = 0;
    #       pIVar3 = sub_1400031D7();
    #       uVar5 = (ulonglong)*(uint *)(local_18 + 0xc);
    #       *(char **)((longlong)local_c * 0x28 + DAT_1400090f0 + 0x18) = pIVar3->e_magic + uVar5;
    #       SVar4 = VirtualQuery(*(LPCVOID *)((longlong)local_c * 0x28 + DAT_1400090f0 + 0x18),&local_48,
    #                            0x30);
    #       if (SVar4 == 0) {
    #         sub_140001DB0("  VirtualQuery failed for %d bytes at address %p",
    #                       (ulonglong)*(uint *)(local_18 + 8),
    #                       *(undefined8 *)((longlong)local_c * 0x28 + DAT_1400090f0 + 0x18),uVar5);
    #       }
    #       if ((((local_48.Protect != 0x40) && (local_48.Protect != 4)) && (local_48.Protect != 0x80)) &&
    #          (local_48.Protect != 8)) {
    #         if (local_48.Protect == 2) {
    #           local_10 = 4;
    #         }
    #         else {
    #           local_10 = 0x40;
    #         }
    #         *(PVOID *)(DAT_1400090f0 + (longlong)local_c * 0x28 + 8) = local_48.BaseAddress;
    #         *(SIZE_T *)(DAT_1400090f0 + (longlong)local_c * 0x28 + 0x10) = local_48.RegionSize;
    #         lpflOldProtect = (PDWORD)((longlong)local_c * 0x28 + DAT_1400090f0);
    #         uVar5 = (ulonglong)local_10;
    #         BVar1 = VirtualProtect(local_48.BaseAddress,local_48.RegionSize,local_10,lpflOldProtect);
    #         if (BVar1 == 0) {
    #           DVar2 = GetLastError();
    #           sub_140001DB0("  VirtualProtect failed with code 0x%x",(ulonglong)DVar2,uVar5,
    #                         lpflOldProtect);
    #         }
    #       }
    #       DAT_1400090f8 = DAT_1400090f8 + 1;
    #       return;
    #     }
    #     if ((*(ulonglong *)((longlong)local_c * 0x28 + DAT_1400090f0 + 0x18) <= param_1) &&
    #        (param_3 = DAT_1400090f0,
    #        param_1 < (ulonglong)
    #                  *(uint *)(*(longlong *)((longlong)local_c * 0x28 + DAT_1400090f0 + 0x20) + 8) +
    #                  *(longlong *)((longlong)local_c * 0x28 + DAT_1400090f0 + 0x18))) break;
    #     local_c = local_c + 1;
    #   }
    #   return;
    # }
    # sub_14000308B()
    # sub_140001DB0('Address %p has no image-section')
    # sub_1400031D7()
    # VirtualQuery(?, buffer, 48)
    # sub_140001DB0('  VirtualQuery failed for %d bytes at address %p')
    # VirtualProtect()
    # GetLastError()
    # sub_140001DB0('  VirtualProtect failed with code 0x%x', ?)
    raise NotImplementedError


def sub_140002212(*args):
    """Native function at 0x140002212 (894 bytes, 255 instructions).
    Calls: sub_1400021CB, sub_140001DB0
    Strings: '  Unknown pseudo relocation protocol version %d.\n'; '  Unknown pseudo relocation bit size %d.\n'; '%d bit pseudo relocation at %p out of range, targeting %p, 
    """
    # pseudo-C from Ghidra:
    # void sub_140002212(uint *param_1,uint *param_2,ulonglong *param_3,longlong param_4)
    # 
    # {
    #   uint *puVar1;
    #   uint uVar2;
    #   byte bVar3;
    #   ulonglong *puVar4;
    #   int local_54;
    #   ulonglong local_50;
    #   longlong local_48;
    #   longlong local_40;
    #   uint local_34;
    #   longlong local_30;
    #   ulonglong *local_28;
    #   uint *local_20;
    #   uint *local_18;
    #   uint *local_10;
    #   
    #   local_28 = (ulonglong *)((longlong)param_2 - (longlong)param_1);
    #   if (7 < (longlong)local_28) {
    #     local_10 = param_1;
    #     if ((((0xb < (longlong)local_28) && (*param_1 == 0)) && (param_1[1] == 0)) && (param_1[2] == 0))
    #     {
    #       local_10 = param_1 + 3;
    #     }
    #     if ((*local_10 == 0) && (local_10[1] == 0)) {
    #       puVar4 = param_3;
    #       puVar1 = local_10;
    #       if (local_10[2] != 1) {
    #         sub_140001DB0("  Unknown pseudo relocation protocol version %d.\n",(ulonglong)local_10[2],
    #                       param_3,param_4);
    #         puVar1 = local_10;
    #       }
    #       while (local_18 = puVar1 + 3, local_18 < param_2) {
    #         local_28 = (ulonglong *)((longlong)param_3 + (ulonglong)puVar1[4]);
    #         local_30 = *(longlong *)((longlong)param_3 + (ulonglong)*local_18);
    #         uVar2 = puVar1[5] & 0xff;
    #         if (uVar2 == 0x40) {
    #           local_50 = *local_28;
    #         }
    #         else if (uVar2 < 0x41) {
    #           if (uVar2 == 0x20) {
    #             local_50 = (ulonglong)(uint)*local_28;
    #             if (((uint)*local_28 & 0x80000000) != 0) {
    #               local_50 = local_50 | 0xffffffff00000000;
    #             }
    #           }
    #           else {
    #             if (0x20 < uVar2) goto LAB_14000241c;
    #             if (uVar2 == 8) {
    #               local_50 = (ulonglong)(byte)*local_28;
    #               if (((byte)*local_28 & 0x80) != 0) {
    #                 local_50 = local_50 | 0xffffffffffffff00;
    #               }
    #             }
    #             else {
    #               if (uVar2 != 0x10) goto LAB_14000241c;
    #               local_50 = (ulonglong)(ushort)*local_28;
    #               if (((ushort)*local_28 & 0x8000) != 0) {
    #                 local_50 = local_50 | 0xffffffffffff0000;
    #               }
    #             }
    #           }
    #         }
    #         else {
    # LAB_14000241c:
    #           local_50 = 0;
    #           sub_140001DB0("  Unknown pseudo relocation bit size %d.\n",(ulonglong)(puVar1[5] & 0xff),
    #                         puVar4,param_4);
    #         }
    #         local_50 = local_30 + (local_50 - ((ulonglong)*local_18 + (longlong)param_3));
    #         local_34 = local_18[2] & 0xff;
    #         if (local_34 < 0x40) {
    #           bVar3 = (byte)local_18[2];
    #           local_40 = (1L << (bVar3 & 0x3f)) + -1;
    #           local_48 = -1L << (bVar3 - 1 & 0x3f);
    #           if ((local_40 < (longlong)local_50) || ((longlong)local_50 < local_48)) {
    #             puVar4 = local_28;
    #             param_4 = local_30;
    #             sub_140001DB0("%d bit pseudo relocation at %p out of range, targeting %p, yielding the value %p.\n"
    # sub_1400021CB(?, buffer, 4)
    # sub_140001DB0('  Unknown pseudo relocation protocol version %d.\n')
    # sub_140001DB0('  Unknown pseudo relocation bit size %d.\n')
    # sub_140001DB0('%d bit pseudo relocation at %p out of range, targeting %p, yielding the value %p.\n')
    # sub_1400021CB(?, buffer, 2)
    # sub_1400021CB(?, buffer, 1)
    # sub_1400021CB(?, buffer, 4)
    # sub_1400021CB(?, buffer, 8)
    raise NotImplementedError


def sub_1400034E0(*args):
    """Native function at 0x1400034E0 (55 bytes, 14 instructions).
    Calls: __acrt_iob_func, printf, _exit
    Strings: 'runtime error %d\n'
    """
    # pseudo-C from Ghidra:
    # void sub_1400034E0(uint param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4)
    # 
    # {
    #   undefined8 uVar1;
    #   
    #   uVar1 = __acrt_iob_func(2);
    #   sub_140003460(uVar1,"runtime error %d\n",(ulonglong)param_1,param_4);
    #                     /* WARNING: Subroutine does not return */
    #   _exit(0xff);
    # }
    # __acrt_iob_func(2)
    # printf(?, 'runtime error %d\n')
    # _exit(255)
    raise NotImplementedError
