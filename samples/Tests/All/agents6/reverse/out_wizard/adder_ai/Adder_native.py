"""Functions recovered from Adder.exe (native machine code).

Each function below documents what the original code calls and which strings it uses.
Bodies translated by AI are marked; the others are stubs to complete by hand.
"""



def sub_140001760(root: tk.Tk, event: tk.Event):
    """Native function at 0x140001760 (772 bytes, 128 instructions).
    Calls: CreateWindowExA, DefWindowProcA, GetDlgItemTextA, atoi, sprintf, SetDlgItemTextA, PostQuitMessage
    Strings: 'First number:'; 'STATIC'; 'EDIT'; 'Second number:'; 'BUTTON'; 'Sum = %d'
    """
    # translated by AI from the machine code - review it
    import tkinter as tk
    from tkinter import messagebox
    """
    Handles the window message processing logic for the main dialog window.
    Corresponds to the sub_140001760 function.

    Args:
        root: The main Tkinter root window object.
        event: The Tkinter event object (used to simulate message parameters).
    """
    # In a real tkinter app, the WM_COMMAND handling is typically done 
    # via command callbacks attached to widgets. Here we simulate the logic.

    if event.widget == root:
        # Simulation of Message Check:
        # If param_2 == 2 (WM_CLOSE or similar exit): PostQuitMessage(0)
        if event.type == tk.WM_DELETE_WINDOW:
            print("Exiting application.")
            root.destroy()
            return

        # If param_2 == 0x111 (WM_COMMAND):
        # The 'event.widget' being a button or a specific control ID is used here.
        if event.detail and event.detail == 103:  # ID for btnAdd (0x67)
            # GetDlgItemTextA(param_1, 0x65, ...)
            first_number = txt_first_number.get()
            # GetDlgItemTextA(param_1, 0x66, ...)
            second_number = txt_second_number.get()

            try:
                # atoi(local_38) and atoi(local_58)
                num1 = int(first_number)
                num2 = int(second_number)

                # sub_140003630(local_98, "Sum = %d", ...)
                sum_result = num1 + num2
                result_text = f"Sum = {sum_result}"

                # SetDlgItemTextA(param_1, 0x68, local_98)
                lbl_result.config(text=result_text)
            except ValueError:
                lbl_result.config(text="Error: Please enter valid numbers.")


def sub_140001A64(*args):
    """Native function at 0x140001A64 (307 bytes, 58 instructions).
    Calls: LoadCursorA, RegisterClassA, CreateWindowExA
    Strings: 'RadCalc'; 'Adder'
    """
    # pseudo-C from Ghidra:
    # void sub_140001A64(HINSTANCE param_1)
    # 
    # {
    #   BOOL BVar1;
    #   HCURSOR pHVar2;
    #   MSG local_a8;
    #   WNDCLASSA local_78;
    #   
    #   local_78.hIcon = (HICON)0x0;
    #   local_78.hCursor = (HCURSOR)0x0;
    #   local_78._0_16_ = ZEXT816(0x140001760) << 0x40;
    #   local_78.hInstance = 0;
    #   local_78._16_8_ = param_1;
    #   local_78._16_16_ = (undefined1  [16])local_78._16_16_ << 0x40;
    #   local_78.lpszClassName = "RadCalc";
    #   local_78._48_16_ = ZEXT816(0x10);
    #   pHVar2 = LoadCursorA((HINSTANCE)0x0,(LPCSTR)0x7f00);
    #   local_78.hCursor = pHVar2;
    #   RegisterClassA(&local_78);
    #   CreateWindowExA(0,"RadCalc","Adder",0x10cf0000,-0x80000000,-0x80000000,0x168,0xa0,(HWND)0x0,
    #                   (HMENU)0x0,param_1,(LPVOID)0x0);
    #   while( true ) {
    #     BVar1 = GetMessageA(&local_a8,(HWND)0x0,0,0);
    #     if (BVar1 == 0) break;
    #     TranslateMessage(&local_a8);
    #     DispatchMessageA(&local_a8);
    #   }
    #   return;
    # }
    # LoadCursorA(0, 0x7f00)
    # RegisterClassA(buffer)
    # CreateWindowExA(0, 'RadCalc', 'Adder', 0x10cf0000, 0x80000000, 0x80000000, 0x168, 160, 0, 0, ?, 0)
    # ?(buffer, 0, 0, 0)
    # ?(buffer)
    # ?(buffer)
    raise NotImplementedError


def sub_140001FF0(*args):
    """Native function at 0x140001FF0 (100 bytes, 25 instructions).
    Calls: __acrt_iob_func, printf, abort
    Strings: 'Mingw-w64 runtime failure:\n'
    """
    # pseudo-C from Ghidra:
    # void sub_140001FF0(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4)
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
    #   sub_1400036A0(uVar1,"Mingw-w64 runtime failure:\n",param_3,param_4);
    #   uVar1 = __acrt_iob_func(2);
    #   sub_1400035E0(uVar1,param_1,&local_res10);
    #                     /* WARNING: Subroutine does not return */
    #   abort();
    # }
    # __acrt_iob_func(2)
    # printf(?, 'Mingw-w64 runtime failure:\n')
    # __acrt_iob_func(2)
    # printf(?, ?, buffer)
    # abort()
    raise NotImplementedError


def sub_140002055(*args):
    """Native function at 0x140002055 (734 bytes, 192 instructions).
    Calls: sub_1400032CB, sub_140001FF0, sub_140003417, VirtualQuery, VirtualProtect, GetLastError
    Strings: 'Address %p has no image-section'; '  VirtualQuery failed for %d bytes at address %p'; '  VirtualProtect failed with code 0x%x'
    """
    # pseudo-C from Ghidra:
    # void sub_140002055(ulonglong param_1,undefined8 param_2,longlong param_3,undefined8 param_4)
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
    #       local_18 = sub_1400032CB(param_1);
    #       if (local_18 == 0) {
    #         sub_140001FF0("Address %p has no image-section",param_1,param_3,param_4);
    #       }
    #       *(longlong *)(DAT_1400090f0 + (longlong)local_c * 0x28 + 0x20) = local_18;
    #       *(undefined4 *)((longlong)local_c * 0x28 + DAT_1400090f0) = 0;
    #       pIVar3 = sub_140003417();
    #       uVar5 = (ulonglong)*(uint *)(local_18 + 0xc);
    #       *(char **)((longlong)local_c * 0x28 + DAT_1400090f0 + 0x18) = pIVar3->e_magic + uVar5;
    #       SVar4 = VirtualQuery(*(LPCVOID *)((longlong)local_c * 0x28 + DAT_1400090f0 + 0x18),&local_48,
    #                            0x30);
    #       if (SVar4 == 0) {
    #         sub_140001FF0("  VirtualQuery failed for %d bytes at address %p",
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
    #           sub_140001FF0("  VirtualProtect failed with code 0x%x",(ulonglong)DVar2,uVar5,
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
    # sub_1400032CB()
    # sub_140001FF0('Address %p has no image-section')
    # sub_140003417()
    # VirtualQuery(?, buffer, 48)
    # sub_140001FF0('  VirtualQuery failed for %d bytes at address %p')
    # VirtualProtect()
    # GetLastError()
    # sub_140001FF0('  VirtualProtect failed with code 0x%x', ?)
    raise NotImplementedError


def sub_140002452(*args):
    """Native function at 0x140002452 (894 bytes, 255 instructions).
    Calls: sub_14000240B, sub_140001FF0
    Strings: '  Unknown pseudo relocation protocol version %d.\n'; '  Unknown pseudo relocation bit size %d.\n'; '%d bit pseudo relocation at %p out of range, targeting %p, 
    """
    # pseudo-C from Ghidra:
    # void sub_140002452(uint *param_1,uint *param_2,ulonglong *param_3,longlong param_4)
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
    #         sub_140001FF0("  Unknown pseudo relocation protocol version %d.\n",(ulonglong)local_10[2],
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
    #             if (0x20 < uVar2) goto LAB_14000265c;
    #             if (uVar2 == 8) {
    #               local_50 = (ulonglong)(byte)*local_28;
    #               if (((byte)*local_28 & 0x80) != 0) {
    #                 local_50 = local_50 | 0xffffffffffffff00;
    #               }
    #             }
    #             else {
    #               if (uVar2 != 0x10) goto LAB_14000265c;
    #               local_50 = (ulonglong)(ushort)*local_28;
    #               if (((ushort)*local_28 & 0x8000) != 0) {
    #                 local_50 = local_50 | 0xffffffffffff0000;
    #               }
    #             }
    #           }
    #         }
    #         else {
    # LAB_14000265c:
    #           local_50 = 0;
    #           sub_140001FF0("  Unknown pseudo relocation bit size %d.\n",(ulonglong)(puVar1[5] & 0xff),
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
    #             sub_140001FF0("%d bit pseudo relocation at %p out of range, targeting %p, yielding the value %p.\n"
    # sub_14000240B(?, buffer, 4)
    # sub_140001FF0('  Unknown pseudo relocation protocol version %d.\n')
    # sub_140001FF0('  Unknown pseudo relocation bit size %d.\n')
    # sub_140001FF0('%d bit pseudo relocation at %p out of range, targeting %p, yielding the value %p.\n')
    # sub_14000240B(?, buffer, 2)
    # sub_14000240B(?, buffer, 1)
    # sub_14000240B(?, buffer, 4)
    # sub_14000240B(?, buffer, 8)
    raise NotImplementedError


def sub_140003720(*args):
    """Native function at 0x140003720 (55 bytes, 14 instructions).
    Calls: __acrt_iob_func, printf, _exit
    Strings: 'runtime error %d\n'
    """
    # pseudo-C from Ghidra:
    # void sub_140003720(uint param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4)
    # 
    # {
    #   undefined8 uVar1;
    #   
    #   uVar1 = __acrt_iob_func(2);
    #   sub_1400036A0(uVar1,"runtime error %d\n",(ulonglong)param_1,param_4);
    #                     /* WARNING: Subroutine does not return */
    #   _exit(0xff);
    # }
    # __acrt_iob_func(2)
    # printf(?, 'runtime error %d\n')
    # _exit(255)
    raise NotImplementedError
