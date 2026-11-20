// sub_140001000
void sub_140001000(void)

{
  return;
}

// sub_140001017
void sub_140001017(void)

{
  fflush((FILE *)0x0);
  return;
}

// entry
int entry(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4)

{
  int iVar1;
  
  *(undefined4 *)PTR_DAT_140005440 = 1;
  iVar1 = sub_14000108E(param_1,param_2,param_3,param_4);
  return iVar1;
}

// sub_14000105F
int sub_14000105F(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4)

{
  int iVar1;
  
  *(undefined4 *)PTR_DAT_140005440 = 0;
  iVar1 = sub_14000108E(param_1,param_2,param_3,param_4);
  return iVar1;
}

// sub_14000108E
int sub_14000108E(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4)

{
  undefined1 uVar1;
  int iVar2;
  FILE *_File;
  LPTOP_LEVEL_EXCEPTION_FILTER pPVar3;
  undefined7 extraout_var;
  undefined4 *puVar4;
  uint *puVar5;
  undefined8 uVar6;
  ulonglong uVar7;
  undefined *puVar8;
  undefined8 *puVar9;
  undefined8 uVar10;
  undefined8 *puVar11;
  undefined8 uVar12;
  longlong unaff_GS_OFFSET;
  undefined4 local_5c;
  undefined8 local_58;
  undefined *local_50;
  undefined8 local_48;
  longlong local_40;
  undefined *local_38;
  longlong local_30;
  undefined4 local_28;
  int local_24;
  longlong local_20;
  longlong local_18;
  int local_c;
  
  local_28 = 0x30;
  local_30 = *(longlong *)(unaff_GS_OFFSET + 0x30);
  local_20 = *(longlong *)(local_30 + 8);
  local_c = 0;
  local_24 = 0;
  while( true ) {
    puVar8 = PTR_DAT_140005490;
    local_38 = PTR_DAT_140005490;
    local_40 = local_20;
    local_48 = 0;
    local_18 = 0;
    LOCK();
    if (*(longlong *)PTR_DAT_140005490 == 0) {
      *(longlong *)PTR_DAT_140005490 = local_20;
    }
    else {
      local_18 = *(longlong *)PTR_DAT_140005490;
    }
    UNLOCK();
    if (local_18 == 0) goto LAB_140001128;
    if (local_18 == local_20) break;
    Sleep(1000);
  }
  local_c = 1;
LAB_140001128:
  if (*(int *)PTR_DAT_1400054a0 == 1) {
    sub_140003720(0x1f,puVar8,param_3,param_4);
  }
  if (*(int *)PTR_DAT_1400054a0 == 0) {
    *(undefined4 *)PTR_DAT_1400054a0 = 1;
    _File = (FILE *)__acrt_iob_func(2);
    uVar12 = 0;
    uVar10 = 4;
    setvbuf(_File,(char *)0x0,4,0);
    iVar2 = sub_14000162F(sub_140001017);
    if (iVar2 != 0) {
                    /* WARNING: Subroutine does not return */
      abort();
    }
    sub_1400027D0();
    pPVar3 = SetUnhandledExceptionFilter((LPTOP_LEVEL_EXCEPTION_FILTER)PTR_FUN_140005520);
    *(LPTOP_LEVEL_EXCEPTION_FILTER *)PTR_DAT_140005480 = pPVar3;
    _set_invalid_parameter_handler(sub_140001000);
    sub_1400030E0();
    uVar1 = sub_1400013EC();
    DAT_140009018 = (int)CONCAT71(extraout_var,uVar1);
    if (*(int *)PTR_DAT_140005440 == 0) {
      _set_app_type(1);
    }
    else {
      _set_app_type(2);
    }
    puVar4 = (undefined4 *)__p__fmode();
    *puVar4 = *(undefined4 *)PTR_DAT_140005510;
    puVar5 = (uint *)__p__commode();
    uVar7 = (ulonglong)*(uint *)PTR_DAT_1400054f0;
    *puVar5 = *(uint *)PTR_DAT_1400054f0;
    uVar6 = sub_140001DB0();
    local_24 = (int)uVar6;
    if (local_24 < 0) {
      sub_140003720(8,uVar7,uVar10,uVar12);
    }
    if (*(int *)PTR_DAT_1400053c0 == 1) {
      sub_1400028EA(PTR_FUN_140005530);
    }
    if (*(int *)PTR_DAT_140005420 == -1) {
      _configthreadlocale(-1);
    }
    puVar8 = PTR_DAT_1400054e0;
    iVar2 = _initterm_e(PTR_DAT_1400054d0);
    if (iVar2 != 0) {
      sub_140003720(10,puVar8,uVar10,uVar12);
    }
    local_5c = *(undefined4 *)PTR_DAT_140005540;
    puVar9 = &DAT_140009008;
    uVar7 = (ulonglong)*(uint *)PTR_DAT_140005500;
    puVar11 = &DAT_140009010;
    uVar10 = sub_140003760(&DAT_140009004,&DAT_140009008,&DAT_140009010,*(uint *)PTR_DAT_140005500,
                           &local_5c);
    local_24 = (int)uVar10;
    if (local_24 < 0) {
      sub_140003720(8,puVar9,puVar11,uVar7);
    }
    puVar9 = &DAT_140009008;
    uVar10 = sub_1400014F0(DAT_140009004,&DAT_140009008);
    local_24 = (int)uVar10;
    if (local_24 != 0) {
      sub_140003720(8,puVar9,puVar11,uVar7);
    }
    _initterm(PTR_DAT_1400054b0,PTR_DAT_1400054c0);
    sub_140001D87();
    *(undefined4 *)PTR_DAT_1400054a0 = 2;
  }
  else {
    DAT_14000901c = 1;
  }
  if (local_c == 0) {
    local_50 = PTR_DAT_140005490;
    local_58 = 0;
    LOCK();
    *(undefined8 *)PTR_DAT_140005490 = 0;
    UNLOCK();
  }
  if (*(longlong *)PTR_PTR_140005410 != 0) {
    (**(code **)PTR_PTR_140005410)(0,2,0);
  }
  puVar9 = (undefined8 *)sub_140003710();
  *puVar9 = DAT_140009010;
  local_24 = sub_140001BA0();
  if (DAT_140009018 == 0) {
                    /* WARNING: Subroutine does not return */
    exit(local_24);
  }
  if (DAT_14000901c == 0) {
    _cexit();
  }
  return local_24;
}

// sub_1400013EC
bool sub_1400013EC(void)

{
  int *piVar1;
  bool bVar2;
  
  *(undefined4 *)PTR_DAT_140005450 = 1;
  *(undefined4 *)PTR_DAT_140005460 = 1;
  *(undefined4 *)PTR_DAT_140005470 = 1;
  if (*(short *)PTR_IMAGE_DOS_HEADER_1400053e0 == 0x5a4d) {
    piVar1 = (int *)(PTR_IMAGE_DOS_HEADER_1400053e0 +
                    *(int *)(PTR_IMAGE_DOS_HEADER_1400053e0 + 0x3c));
    if (*piVar1 == 0x4550) {
      if ((short)piVar1[6] == 0x10b) {
        if ((uint)piVar1[0x1d] < 0xf) {
          bVar2 = false;
        }
        else {
          bVar2 = piVar1[0x3a] != 0;
        }
      }
      else if ((short)piVar1[6] == 0x20b) {
        if ((uint)piVar1[0x21] < 0xf) {
          bVar2 = false;
        }
        else {
          bVar2 = piVar1[0x3e] != 0;
        }
      }
      else {
        bVar2 = false;
      }
    }
    else {
      bVar2 = false;
    }
  }
  else {
    bVar2 = false;
  }
  return bVar2;
}

// sub_1400014F0
undefined8 sub_1400014F0(int param_1,longlong *param_2)

{
  longlong lVar1;
  void *pvVar2;
  undefined8 uVar3;
  size_t sVar4;
  void *pvVar5;
  int local_1c;
  
  pvVar2 = malloc((longlong)(param_1 + 1) << 3);
  if (pvVar2 == (void *)0x0) {
    uVar3 = 1;
  }
  else {
    lVar1 = *param_2;
    for (local_1c = 0; local_1c < param_1; local_1c = local_1c + 1) {
      sVar4 = strlen(*(char **)(lVar1 + (longlong)local_1c * 8));
      pvVar5 = malloc(sVar4 + 1);
      *(void **)((longlong)local_1c * 8 + (longlong)pvVar2) = pvVar5;
      if (*(longlong *)((longlong)pvVar2 + (longlong)local_1c * 8) == 0) {
        return 1;
      }
      memcpy(*(void **)((longlong)pvVar2 + (longlong)local_1c * 8),
             *(void **)(lVar1 + (longlong)local_1c * 8),sVar4 + 1);
    }
    *(undefined8 *)((longlong)pvVar2 + (longlong)local_1c * 8) = 0;
    *param_2 = (longlong)pvVar2;
    uVar3 = 0;
  }
  return uVar3;
}

// sub_14000162F
void sub_14000162F(undefined8 param_1)

{
  _crt_atexit(param_1);
  return;
}

// sub_140001650
void sub_140001650(void)

{
  return;
}

// sub_140001660
undefined8 sub_140001660(void)

{
  return 0;
}

// sub_140001670
void sub_140001670(void)

{
  HMODULE hModule;
  code *pcVar1;
  
  hModule = GetModuleHandleA("libgcc_s_dw2-1.dll");
  if (hModule == (HMODULE)0x0) {
    pcVar1 = sub_140001650;
    DAT_140004000 = sub_140001660;
  }
  else {
    DAT_140009020 = LoadLibraryA("libgcc_s_dw2-1.dll");
    pcVar1 = GetProcAddress(hModule,"__register_frame_info");
    DAT_140004000 = GetProcAddress(hModule,"__deregister_frame_info");
    if (pcVar1 == (FARPROC)0x0) goto LAB_1400016ee;
  }
  (*pcVar1)(&DAT_140006000,&DAT_140009040);
LAB_1400016ee:
  sub_14000162F(sub_140001720);
  return;
}

// sub_140001720
void sub_140001720(void)

{
  if (DAT_140004000 != (code *)0x0) {
    (*DAT_140004000)(&DAT_140006000);
  }
  if (DAT_140009020 == 0) {
    return;
  }
                    /* WARNING: Could not recover jumptable at 0x00014000174e. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  FreeLibrary();
  return;
}

// sub_140001760
LRESULT sub_140001760(HWND param_1,UINT param_2,WPARAM param_3,LPARAM param_4)

{
  int iVar1;
  int iVar2;
  LRESULT LVar3;
  undefined8 uVar4;
  CHAR local_98 [64];
  CHAR local_58 [32];
  CHAR local_38 [32];
  
  if (param_2 == 2) {
    PostQuitMessage(0);
  }
  else if (param_2 == 0x111) {
    if ((short)param_3 == 0x67) {
      GetDlgItemTextA(param_1,0x65,local_38,0x20);
      uVar4 = 0x20;
      GetDlgItemTextA(param_1,0x66,local_58,0x20);
      iVar1 = atoi(local_38);
      iVar2 = atoi(local_58);
      sub_140003630(local_98,"Sum = %d",(ulonglong)(uint)(iVar1 + iVar2),uVar4);
      SetDlgItemTextA(param_1,0x68,local_98);
    }
  }
  else {
    if (param_2 != 1) {
      LVar3 = DefWindowProcA(param_1,param_2,param_3,param_4);
      return LVar3;
    }
    CreateWindowExA(0,"STATIC","First number:",0x50000000,10,0xc,100,0x14,param_1,(HMENU)0x0,
                    (HINSTANCE)0x0,(LPVOID)0x0);
    CreateWindowExA(0,"EDIT","",0x50800000,0x78,10,0x78,0x16,param_1,(HMENU)0x65,(HINSTANCE)0x0,
                    (LPVOID)0x0);
    CreateWindowExA(0,"STATIC","Second number:",0x50000000,10,0x2a,100,0x14,param_1,(HMENU)0x0,
                    (HINSTANCE)0x0,(LPVOID)0x0);
    CreateWindowExA(0,"EDIT","",0x50800000,0x78,0x28,0x78,0x16,param_1,(HMENU)0x66,(HINSTANCE)0x0,
                    (LPVOID)0x0);
    CreateWindowExA(0,"BUTTON","Add",0x50000000,0xfa,0x19,0x46,0x1a,param_1,(HMENU)0x67,
                    (HINSTANCE)0x0,(LPVOID)0x0);
    CreateWindowExA(0,"STATIC","",0x50000000,10,0x4b,300,0x14,param_1,(HMENU)0x68,(HINSTANCE)0x0,
                    (LPVOID)0x0);
  }
  return 0;
}

// sub_140001A64
void sub_140001A64(HINSTANCE param_1)

{
  BOOL BVar1;
  HCURSOR pHVar2;
  MSG local_a8;
  WNDCLASSA local_78;
  
  local_78.hIcon = (HICON)0x0;
  local_78.hCursor = (HCURSOR)0x0;
  local_78._0_16_ = ZEXT816(0x140001760) << 0x40;
  local_78.hInstance = 0;
  local_78._16_8_ = param_1;
  local_78._16_16_ = (undefined1  [16])local_78._16_16_ << 0x40;
  local_78.lpszClassName = "RadCalc";
  local_78._48_16_ = ZEXT816(0x10);
  pHVar2 = LoadCursorA((HINSTANCE)0x0,(LPCSTR)0x7f00);
  local_78.hCursor = pHVar2;
  RegisterClassA(&local_78);
  CreateWindowExA(0,"RadCalc","Adder",0x10cf0000,-0x80000000,-0x80000000,0x168,0xa0,(HWND)0x0,
                  (HMENU)0x0,param_1,(LPVOID)0x0);
  while( true ) {
    BVar1 = GetMessageA(&local_a8,(HWND)0x0,0,0);
    if (BVar1 == 0) break;
    TranslateMessage(&local_a8);
    DispatchMessageA(&local_a8);
  }
  return;
}

// sub_140001BA0
void sub_140001BA0(void)

{
  BOOL BVar1;
  undefined8 *puVar2;
  _STARTUPINFOA local_88;
  HINSTANCE local_20;
  uint local_18;
  uint local_14;
  BYTE *local_10;
  
  sub_140001D87();
  local_20 = (HINSTANCE)PTR_IMAGE_DOS_HEADER_1400053e0;
  puVar2 = (undefined8 *)__p__acmdln();
  local_10 = (BYTE *)*puVar2;
  if (local_10 == (BYTE *)0x0) {
    local_10 = "";
  }
  else {
    local_18 = 0;
    while ((' ' < (char)*local_10 || ((*local_10 != '\0' && (local_18 != 0))))) {
      if (*local_10 == '\"') {
        local_18 = (uint)(local_18 == 0);
      }
      BVar1 = IsDBCSLeadByte(*local_10);
      if ((BVar1 != 0) && (local_10[1] != '\0')) {
        local_10 = local_10 + 1;
      }
      local_10 = local_10 + 1;
    }
    for (; (*local_10 != '\0' && ((char)*local_10 < '!')); local_10 = local_10 + 1) {
    }
  }
  GetStartupInfoA(&local_88);
  if ((local_88.dwFlags & 1) == 0) {
    local_14 = 10;
  }
  else {
    local_14 = (uint)local_88.wShowWindow;
  }
  sub_140001A64(local_20);
  return;
}

// sub_140001CD0
void sub_140001CD0(void)

{
  for (; *(longlong *)PTR_DAT_140004010 != 0; PTR_DAT_140004010 = PTR_DAT_140004010 + 8) {
    (**(code **)PTR_DAT_140004010)();
  }
  return;
}

// sub_140001D0F
void sub_140001D0F(void)

{
  uint local_10;
  uint local_c;
  
  local_c = (uint)*(undefined8 *)PTR_DAT_1400053d0;
  if (local_c == 0xffffffff) {
    local_c = 0;
    while (*(longlong *)(PTR_DAT_1400053d0 + (ulonglong)(local_c + 1) * 8) != 0) {
      local_c = local_c + 1;
    }
  }
  for (local_10 = local_c; local_10 != 0; local_10 = local_10 - 1) {
    (**(code **)(PTR_DAT_1400053d0 + (ulonglong)local_10 * 8))();
  }
  sub_14000162F(sub_140001CD0);
  return;
}

// sub_140001D87
void sub_140001D87(void)

{
  if (DAT_140009080 == 0) {
    DAT_140009080 = 1;
    sub_140001D0F();
  }
  return;
}

// sub_140001DB0
undefined8 sub_140001DB0(void)

{
  return 0;
}

// tls_callback_0
void tls_callback_0(undefined8 param_1,int param_2)

{
  longlong *local_10;
  
  if (*(int *)PTR_DAT_1400053b0 != 2) {
    *(undefined4 *)PTR_DAT_1400053b0 = 2;
  }
  if (param_2 == 2) {
    for (local_10 = &DAT_140005700; local_10 != &DAT_140005700; local_10 = local_10 + 1) {
      if (*local_10 != 0) {
        (*(code *)*local_10)();
      }
    }
  }
  else if (param_2 == 1) {
    sub_140002FE1(param_1,1);
  }
  return;
}

// sub_140001E5C
undefined8 sub_140001E5C(void)

{
  return 0;
}

// tls_callback_1
void tls_callback_1(undefined8 param_1,uint param_2)

{
  if ((param_2 == 3) || (param_2 == 0)) {
    sub_140002FE1(param_1,param_2);
  }
  return;
}

// sub_140001EC0
undefined8 sub_140001EC0(int *param_1)

{
  int iVar1;
  undefined8 uVar2;
  undefined8 uVar3;
  char *local_50;
  
  iVar1 = *param_1;
  if (iVar1 == 6) {
    local_50 = "Partial loss of significance (PLOSS)";
    goto LAB_140001f73;
  }
  if (iVar1 < 7) {
    if (iVar1 == 5) {
      local_50 = "Total loss of significance (TLOSS)";
      goto LAB_140001f73;
    }
    if (iVar1 < 6) {
      if (iVar1 == 4) {
        local_50 = "The result is too small to be represented (UNDERFLOW)";
        goto LAB_140001f73;
      }
      if (iVar1 < 5) {
        if (iVar1 == 3) {
          local_50 = "Overflow range error (OVERFLOW)";
          goto LAB_140001f73;
        }
        if (iVar1 < 4) {
          if (iVar1 == 1) {
            local_50 = "Argument domain error (DOMAIN)";
            goto LAB_140001f73;
          }
          if (iVar1 == 2) {
            local_50 = "Argument singularity (SIGN)";
            goto LAB_140001f73;
          }
        }
      }
    }
  }
  local_50 = "Unknown error";
LAB_140001f73:
  uVar2 = *(undefined8 *)(param_1 + 2);
  uVar3 = __acrt_iob_func(2);
  sub_1400036A0(uVar3,"_matherr(): %s in %s(%g, %g)  (retval=%g)\n",local_50,uVar2);
  return 0;
}

// sub_140001FF0
void sub_140001FF0(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4)

{
  undefined8 uVar1;
  undefined8 local_res10;
  undefined8 local_res18;
  undefined8 local_res20;
  
  local_res10 = param_2;
  local_res18 = param_3;
  local_res20 = param_4;
  uVar1 = __acrt_iob_func(2);
  sub_1400036A0(uVar1,"Mingw-w64 runtime failure:\n",param_3,param_4);
  uVar1 = __acrt_iob_func(2);
  sub_1400035E0(uVar1,param_1,&local_res10);
                    /* WARNING: Subroutine does not return */
  abort();
}

// sub_140002055
void sub_140002055(ulonglong param_1,undefined8 param_2,longlong param_3,undefined8 param_4)

{
  BOOL BVar1;
  DWORD DVar2;
  IMAGE_DOS_HEADER *pIVar3;
  SIZE_T SVar4;
  PDWORD lpflOldProtect;
  ulonglong uVar5;
  _MEMORY_BASIC_INFORMATION local_48;
  longlong local_18;
  uint local_10;
  int local_c;
  
  local_c = 0;
  while( true ) {
    if (DAT_1400090f8 <= local_c) {
      local_18 = sub_1400032CB(param_1);
      if (local_18 == 0) {
        sub_140001FF0("Address %p has no image-section",param_1,param_3,param_4);
      }
      *(longlong *)(DAT_1400090f0 + (longlong)local_c * 0x28 + 0x20) = local_18;
      *(undefined4 *)((longlong)local_c * 0x28 + DAT_1400090f0) = 0;
      pIVar3 = sub_140003417();
      uVar5 = (ulonglong)*(uint *)(local_18 + 0xc);
      *(char **)((longlong)local_c * 0x28 + DAT_1400090f0 + 0x18) = pIVar3->e_magic + uVar5;
      SVar4 = VirtualQuery(*(LPCVOID *)((longlong)local_c * 0x28 + DAT_1400090f0 + 0x18),&local_48,
                           0x30);
      if (SVar4 == 0) {
        sub_140001FF0("  VirtualQuery failed for %d bytes at address %p",
                      (ulonglong)*(uint *)(local_18 + 8),
                      *(undefined8 *)((longlong)local_c * 0x28 + DAT_1400090f0 + 0x18),uVar5);
      }
      if ((((local_48.Protect != 0x40) && (local_48.Protect != 4)) && (local_48.Protect != 0x80)) &&
         (local_48.Protect != 8)) {
        if (local_48.Protect == 2) {
          local_10 = 4;
        }
        else {
          local_10 = 0x40;
        }
        *(PVOID *)(DAT_1400090f0 + (longlong)local_c * 0x28 + 8) = local_48.BaseAddress;
        *(SIZE_T *)(DAT_1400090f0 + (longlong)local_c * 0x28 + 0x10) = local_48.RegionSize;
        lpflOldProtect = (PDWORD)((longlong)local_c * 0x28 + DAT_1400090f0);
        uVar5 = (ulonglong)local_10;
        BVar1 = VirtualProtect(local_48.BaseAddress,local_48.RegionSize,local_10,lpflOldProtect);
        if (BVar1 == 0) {
          DVar2 = GetLastError();
          sub_140001FF0("  VirtualProtect failed with code 0x%x",(ulonglong)DVar2,uVar5,
                        lpflOldProtect);
        }
      }
      DAT_1400090f8 = DAT_1400090f8 + 1;
      return;
    }
    if ((*(ulonglong *)((longlong)local_c * 0x28 + DAT_1400090f0 + 0x18) <= param_1) &&
       (param_3 = DAT_1400090f0,
       param_1 < (ulonglong)
                 *(uint *)(*(longlong *)((longlong)local_c * 0x28 + DAT_1400090f0 + 0x20) + 8) +
                 *(longlong *)((longlong)local_c * 0x28 + DAT_1400090f0 + 0x18))) break;
    local_c = local_c + 1;
  }
  return;
}

// sub_140002333
void sub_140002333(void)

{
  DWORD local_10;
  int local_c;
  
  for (local_c = 0; local_c < DAT_1400090f8; local_c = local_c + 1) {
    if (*(int *)((longlong)local_c * 0x28 + DAT_1400090f0) != 0) {
      VirtualProtect(*(LPVOID *)((longlong)local_c * 0x28 + DAT_1400090f0 + 8),
                     *(SIZE_T *)((longlong)local_c * 0x28 + DAT_1400090f0 + 0x10),
                     *(DWORD *)((longlong)local_c * 0x28 + DAT_1400090f0),&local_10);
    }
  }
  return;
}

// sub_14000240B
void sub_14000240B(void *param_1,void *param_2,size_t param_3,undefined8 param_4)

{
  if (param_3 != 0) {
    sub_140002055((ulonglong)param_1,param_2,param_3,param_4);
    memcpy(param_1,param_2,param_3);
  }
  return;
}

// sub_140002452
void sub_140002452(uint *param_1,uint *param_2,ulonglong *param_3,longlong param_4)

{
  uint *puVar1;
  uint uVar2;
  byte bVar3;
  ulonglong *puVar4;
  int local_54;
  ulonglong local_50;
  longlong local_48;
  longlong local_40;
  uint local_34;
  longlong local_30;
  ulonglong *local_28;
  uint *local_20;
  uint *local_18;
  uint *local_10;
  
  local_28 = (ulonglong *)((longlong)param_2 - (longlong)param_1);
  if (7 < (longlong)local_28) {
    local_10 = param_1;
    if ((((0xb < (longlong)local_28) && (*param_1 == 0)) && (param_1[1] == 0)) && (param_1[2] == 0))
    {
      local_10 = param_1 + 3;
    }
    if ((*local_10 == 0) && (local_10[1] == 0)) {
      puVar4 = param_3;
      puVar1 = local_10;
      if (local_10[2] != 1) {
        sub_140001FF0("  Unknown pseudo relocation protocol version %d.\n",(ulonglong)local_10[2],
                      param_3,param_4);
        puVar1 = local_10;
      }
      while (local_18 = puVar1 + 3, local_18 < param_2) {
        local_28 = (ulonglong *)((longlong)param_3 + (ulonglong)puVar1[4]);
        local_30 = *(longlong *)((longlong)param_3 + (ulonglong)*local_18);
        uVar2 = puVar1[5] & 0xff;
        if (uVar2 == 0x40) {
          local_50 = *local_28;
        }
        else if (uVar2 < 0x41) {
          if (uVar2 == 0x20) {
            local_50 = (ulonglong)(uint)*local_28;
            if (((uint)*local_28 & 0x80000000) != 0) {
              local_50 = local_50 | 0xffffffff00000000;
            }
          }
          else {
            if (0x20 < uVar2) goto LAB_14000265c;
            if (uVar2 == 8) {
              local_50 = (ulonglong)(byte)*local_28;
              if (((byte)*local_28 & 0x80) != 0) {
                local_50 = local_50 | 0xffffffffffffff00;
              }
            }
            else {
              if (uVar2 != 0x10) goto LAB_14000265c;
              local_50 = (ulonglong)(ushort)*local_28;
              if (((ushort)*local_28 & 0x8000) != 0) {
                local_50 = local_50 | 0xffffffffffff0000;
              }
            }
          }
        }
        else {
LAB_14000265c:
          local_50 = 0;
          sub_140001FF0("  Unknown pseudo relocation bit size %d.\n",(ulonglong)(puVar1[5] & 0xff),
                        puVar4,param_4);
        }
        local_50 = local_30 + (local_50 - ((ulonglong)*local_18 + (longlong)param_3));
        local_34 = local_18[2] & 0xff;
        if (local_34 < 0x40) {
          bVar3 = (byte)local_18[2];
          local_40 = (1L << (bVar3 & 0x3f)) + -1;
          local_48 = -1L << (bVar3 - 1 & 0x3f);
          if ((local_40 < (longlong)local_50) || ((longlong)local_50 < local_48)) {
            puVar4 = local_28;
            param_4 = local_30;
            sub_140001FF0("%d bit pseudo relocation at %p out of range, targeting %p, yielding the value %p.\n"
                          ,(ulonglong)local_34,local_28,local_30);
          }
        }
        uVar2 = local_18[2] & 0xff;
        if (uVar2 == 0x40) {
          puVar4 = (ulonglong *)0x8;
          sub_14000240B(local_28,&local_50,8,param_4);
          puVar1 = local_18;
        }
        else {
          puVar1 = local_18;
          if (uVar2 < 0x41) {
            if (uVar2 == 0x20) {
              puVar4 = (ulonglong *)0x4;
              sub_14000240B(local_28,&local_50,4,param_4);
              puVar1 = local_18;
            }
            else if (uVar2 < 0x21) {
              if (uVar2 == 8) {
                puVar4 = (ulonglong *)0x1;
                sub_14000240B(local_28,&local_50,1,param_4);
                puVar1 = local_18;
              }
              else if (uVar2 == 0x10) {
                puVar4 = (ulonglong *)0x2;
                sub_14000240B(local_28,&local_50,2,param_4);
                puVar1 = local_18;
              }
            }
          }
        }
      }
    }
    else {
      for (local_20 = local_10; local_20 < param_2; local_20 = local_20 + 2) {
        local_28 = (ulonglong *)((longlong)param_3 + (ulonglong)local_20[1]);
        local_54 = *local_20 + *(int *)local_28;
        sub_14000240B(local_28,&local_54,4,param_4);
      }
    }
  }
  return;
}

// sub_1400027D0
void sub_1400027D0(void)

{
  longlong lVar1;
  word wVar2;
  undefined6 extraout_var;
  ulonglong uVar3;
  longlong in_R9;
  undefined8 auStack_40 [6];
  undefined4 local_c;
  
  if (DAT_1400090fc == 0) {
    DAT_1400090fc = 1;
    auStack_40[0] = 0x1400027fa;
    wVar2 = sub_14000331B();
    local_c = (undefined4)CONCAT62(extraout_var,wVar2);
    auStack_40[0] = 0x140002822;
    uVar3 = sub_1400035A0();
    lVar1 = -uVar3;
    DAT_1400090f0 = (longlong)auStack_40 + lVar1 + 0x37 & 0xfffffffffffffff0;
    DAT_1400090f8 = 0;
    *(undefined8 *)((longlong)auStack_40 + lVar1) = 0x140002867;
    sub_140002452((uint *)PTR_DAT_140005400,(uint *)PTR_DAT_1400053f0,
                  (ulonglong *)PTR_IMAGE_DOS_HEADER_1400053e0,in_R9);
    *(undefined8 *)((longlong)auStack_40 + lVar1) = 0x14000286c;
    sub_140002333();
  }
  return;
}

// sub_140002880
void sub_140002880(undefined4 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4,
                  undefined8 param_5)

{
  undefined4 local_38 [2];
  undefined8 local_30;
  undefined8 local_28;
  undefined8 local_20;
  undefined8 local_18;
  
  if (DAT_140009100 != (code *)0x0) {
    local_18 = param_5;
    local_38[0] = param_1;
    local_30 = param_2;
    local_28 = param_3;
    local_20 = param_4;
    (*DAT_140009100)(local_38);
  }
  return;
}

// sub_1400028EA
void sub_1400028EA(undefined8 param_1)

{
  DAT_140009100 = param_1;
  __setusermatherr(param_1);
  return;
}

// sub_140002920
undefined4 sub_140002920(uint *param_1)

{
  uint uVar1;
  bool bVar2;
  code *extraout_RAX;
  code *extraout_RAX_00;
  code *extraout_RAX_01;
  undefined4 local_c;
  
  local_c = 1;
  bVar2 = false;
  if ((param_1[1] & 2) != 0) {
    return 1;
  }
  if (((*param_1 & 0x20ffffff) == 0x20474343) && ((param_1[1] & 1) == 0)) {
    return 0;
  }
  uVar1 = *param_1;
  if (uVar1 == 0xc0000096) {
LAB_140002aab:
    signal(4);
    if (extraout_RAX_00 == (code *)0x1) {
      signal(4);
      return 0;
    }
    if (extraout_RAX_00 == (code *)0x0) {
      return 1;
    }
    (*extraout_RAX_00)(4);
    return 0;
  }
  if (0xc0000096 < uVar1) {
    return 1;
  }
  if (0xc0000095 < uVar1) {
    return 1;
  }
  if (uVar1 < 0xc0000094) {
    if (uVar1 != 0xc0000093) {
      if (0xc0000093 < uVar1) {
        return 1;
      }
      if (uVar1 == 0xc0000092) {
        return 0;
      }
      if (0xc0000092 < uVar1) {
        return 1;
      }
      if (0xc0000091 < uVar1) {
        return 1;
      }
      if (uVar1 < 0xc000008d) {
        if (uVar1 == 0xc000008c) {
          return 0;
        }
        if (0xc000008c < uVar1) {
          return 1;
        }
        if (uVar1 != 0xc000001d) {
          if (0xc000001d < uVar1) {
            return 1;
          }
          if (uVar1 == 0xc0000008) {
            return 0;
          }
          if (0xc0000008 < uVar1) {
            return 1;
          }
          if (uVar1 == 0x80000002) {
            return 0;
          }
          if (uVar1 != 0xc0000005) {
            return 1;
          }
          signal(0xb);
          if (extraout_RAX == (code *)0x1) {
            signal(0xb);
            return 0;
          }
          if (extraout_RAX == (code *)0x0) {
            return 1;
          }
          (*extraout_RAX)(0xb);
          return 0;
        }
        goto LAB_140002aab;
      }
    }
    bVar2 = true;
  }
  signal(8);
  if (extraout_RAX_01 == (code *)0x1) {
    signal(8);
    if (bVar2) {
      sub_1400030E0();
    }
    local_c = 0;
  }
  else if (extraout_RAX_01 != (code *)0x0) {
    (*extraout_RAX_01)(8);
    local_c = 0;
  }
  return local_c;
}

// sub_140002B7A
int sub_140002B7A(longlong *param_1)

{
  uint uVar1;
  bool bVar2;
  code *extraout_RAX;
  code *extraout_RAX_00;
  code *extraout_RAX_01;
  int local_c;
  
  local_c = 0;
  bVar2 = false;
  if (((*(uint *)*param_1 & 0x20ffffff) == 0x20474343) && ((*(uint *)(*param_1 + 4) & 1) == 0)) {
    return -1;
  }
  uVar1 = *(uint *)*param_1;
  if (uVar1 == 0xc0000096) {
LAB_140002cea:
    signal(4);
    if (extraout_RAX_00 == (code *)0x1) {
      signal(4);
      local_c = -1;
    }
    else if (extraout_RAX_00 != (code *)0x0) {
      (*extraout_RAX_00)(4);
      local_c = -1;
    }
    goto LAB_140002db0;
  }
  if ((0xc0000096 < uVar1) || (0xc0000095 < uVar1)) goto LAB_140002db0;
  if (uVar1 < 0xc0000094) {
    if (uVar1 != 0xc0000093) {
      if (0xc0000093 < uVar1) goto LAB_140002db0;
      if (uVar1 != 0xc0000092) {
        if ((0xc0000092 < uVar1) || (0xc0000091 < uVar1)) goto LAB_140002db0;
        if (0xc000008c < uVar1) goto LAB_140002d3e;
        if (uVar1 != 0xc000008c) {
          if (0xc000008c < uVar1) goto LAB_140002db0;
          if (uVar1 == 0xc000001d) goto LAB_140002cea;
          if (0xc000001d < uVar1) goto LAB_140002db0;
          if (uVar1 != 0xc0000008) {
            if (0xc0000008 < uVar1) goto LAB_140002db0;
            if (uVar1 != 0x80000002) {
              if (uVar1 == 0xc0000005) {
                signal(0xb);
                if (extraout_RAX == (code *)0x1) {
                  signal(0xb);
                  local_c = -1;
                }
                else if (extraout_RAX != (code *)0x0) {
                  (*extraout_RAX)(0xb);
                  local_c = -1;
                }
              }
              goto LAB_140002db0;
            }
          }
        }
      }
      local_c = -1;
      goto LAB_140002db0;
    }
LAB_140002d3e:
    bVar2 = true;
  }
  signal(8);
  if (extraout_RAX_01 == (code *)0x1) {
    signal(8);
    if (bVar2) {
      sub_1400030E0();
    }
    local_c = -1;
  }
  else if (extraout_RAX_01 != (code *)0x0) {
    (*extraout_RAX_01)(8);
    local_c = -1;
  }
LAB_140002db0:
  if ((local_c == 0) && (DAT_140009120 != (code *)0x0)) {
    local_c = (*DAT_140009120)(param_1);
  }
  return local_c;
}

// sub_140002DE0
undefined8 sub_140002DE0(undefined4 param_1,undefined8 param_2)

{
  undefined8 uVar1;
  undefined4 *puVar2;
  
  if (DAT_140009168 == 0) {
    uVar1 = 0;
  }
  else {
    puVar2 = calloc(1,0x18);
    if (puVar2 == (undefined4 *)0x0) {
      uVar1 = 0xffffffff;
    }
    else {
      *puVar2 = param_1;
      *(undefined8 *)(puVar2 + 2) = param_2;
      EnterCriticalSection((LPCRITICAL_SECTION)&DAT_140009140);
      *(undefined4 **)(puVar2 + 4) = DAT_140009170;
      DAT_140009170 = puVar2;
      LeaveCriticalSection((LPCRITICAL_SECTION)&DAT_140009140);
      uVar1 = 0;
    }
  }
  return uVar1;
}

// sub_140002E81
undefined8 sub_140002E81(int param_1)

{
  int *local_18;
  int *local_10;
  
  if (DAT_140009168 != 0) {
    EnterCriticalSection((LPCRITICAL_SECTION)&DAT_140009140);
    local_10 = (int *)0x0;
    for (local_18 = DAT_140009170; local_18 != (int *)0x0; local_18 = *(int **)(local_18 + 4)) {
      if (param_1 == *local_18) {
        if (local_10 == (int *)0x0) {
          DAT_140009170 = *(int **)(local_18 + 4);
        }
        else {
          *(undefined8 *)(local_10 + 4) = *(undefined8 *)(local_18 + 4);
        }
        free(local_18);
        break;
      }
      local_10 = local_18;
    }
    LeaveCriticalSection((LPCRITICAL_SECTION)&DAT_140009140);
  }
  return 0;
}

// sub_140002F42
void sub_140002F42(void)

{
  DWORD DVar1;
  LPVOID pvVar2;
  DWORD *local_10;
  
  if (DAT_140009168 != 0) {
    EnterCriticalSection((LPCRITICAL_SECTION)&DAT_140009140);
    for (local_10 = DAT_140009170; local_10 != (DWORD *)0x0; local_10 = *(DWORD **)(local_10 + 4)) {
      pvVar2 = TlsGetValue(*local_10);
      DVar1 = GetLastError();
      if ((DVar1 == 0) && (pvVar2 != (LPVOID)0x0)) {
        (**(code **)(local_10 + 2))(pvVar2);
      }
    }
    LeaveCriticalSection((LPCRITICAL_SECTION)&DAT_140009140);
  }
  return;
}

// sub_140002FE1
undefined8 sub_140002FE1(undefined8 param_1,uint param_2)

{
  void *pvVar1;
  void *local_10;
  
  if (param_2 == 3) {
    sub_140002F42();
  }
  else if (param_2 < 4) {
    if (param_2 == 2) {
      sub_1400030E0();
    }
    else if (param_2 < 3) {
      if (param_2 == 0) {
        sub_140002F42();
        if (DAT_140009168 == 1) {
          local_10 = DAT_140009170;
          while (local_10 != (void *)0x0) {
            pvVar1 = *(void **)((longlong)local_10 + 0x10);
            free(local_10);
            local_10 = pvVar1;
          }
          DAT_140009170 = (void *)0x0;
          DAT_140009168 = 0;
          DeleteCriticalSection((LPCRITICAL_SECTION)&DAT_140009140);
        }
      }
      else if (param_2 == 1) {
        if (DAT_140009168 == 0) {
          InitializeCriticalSection((LPCRITICAL_SECTION)&DAT_140009140);
        }
        DAT_140009168 = 1;
      }
    }
  }
  return 1;
}

// sub_1400030E0
void sub_1400030E0(void)

{
  return;
}

// sub_1400030F0
undefined8 sub_1400030F0(short *param_1)

{
  undefined8 uVar1;
  
  if (*param_1 == 0x5a4d) {
    if (*(int *)((longlong)param_1 + (longlong)*(int *)(param_1 + 0x1e)) == 0x4550) {
      if ((short)((int *)((longlong)param_1 + (longlong)*(int *)(param_1 + 0x1e)))[6] == 0x20b) {
        uVar1 = 1;
      }
      else {
        uVar1 = 0;
      }
    }
    else {
      uVar1 = 0;
    }
  }
  else {
    uVar1 = 0;
  }
  return uVar1;
}

// sub_14000316C
longlong sub_14000316C(longlong param_1,ulonglong param_2)

{
  longlong lVar1;
  uint local_14;
  longlong local_10;
  
  lVar1 = param_1 + *(int *)(param_1 + 0x3c);
  local_14 = 0;
  local_10 = lVar1 + (ulonglong)*(ushort *)(lVar1 + 0x14) + 0x18;
  while( true ) {
    if (*(ushort *)(lVar1 + 6) <= local_14) {
      return 0;
    }
    if ((*(uint *)(local_10 + 0xc) <= param_2) &&
       (param_2 < (uint)(*(int *)(local_10 + 8) + *(int *)(local_10 + 0xc)))) break;
    local_14 = local_14 + 1;
    local_10 = local_10 + 0x28;
  }
  return local_10;
}

// sub_140003205
IMAGE_SECTION_HEADER * sub_140003205(char *param_1)

{
  int iVar1;
  undefined *puVar2;
  int iVar3;
  size_t sVar4;
  undefined8 uVar5;
  uint local_14;
  IMAGE_SECTION_HEADER *local_10;
  
  sVar4 = strlen(param_1);
  puVar2 = PTR_IMAGE_DOS_HEADER_1400053e0;
  if ((sVar4 < 9) &&
     (uVar5 = sub_1400030F0((short *)PTR_IMAGE_DOS_HEADER_1400053e0), (int)uVar5 != 0)) {
    iVar1 = *(int *)(puVar2 + 0x3c);
    local_14 = 0;
    local_10 = (IMAGE_SECTION_HEADER *)
               (puVar2 + (ulonglong)*(ushort *)(puVar2 + (longlong)iVar1 + 0x14) + (longlong)iVar1 +
                         0x18);
    for (; local_14 < *(ushort *)(puVar2 + (longlong)iVar1 + 6); local_14 = local_14 + 1) {
      iVar3 = strncmp(local_10->Name,param_1,8);
      if (iVar3 == 0) {
        return local_10;
      }
      local_10 = local_10 + 1;
    }
  }
  return (IMAGE_SECTION_HEADER *)0x0;
}

// sub_1400032CB
longlong sub_1400032CB(longlong param_1)

{
  undefined *puVar1;
  undefined8 uVar2;
  longlong lVar3;
  
  puVar1 = PTR_IMAGE_DOS_HEADER_1400053e0;
  uVar2 = sub_1400030F0((short *)PTR_IMAGE_DOS_HEADER_1400053e0);
  if ((int)uVar2 == 0) {
    lVar3 = 0;
  }
  else {
    lVar3 = sub_14000316C((longlong)puVar1,param_1 - (longlong)puVar1);
  }
  return lVar3;
}

// sub_14000331B
word sub_14000331B(void)

{
  undefined *puVar1;
  word wVar2;
  undefined8 uVar3;
  
  puVar1 = PTR_IMAGE_DOS_HEADER_1400053e0;
  uVar3 = sub_1400030F0((short *)PTR_IMAGE_DOS_HEADER_1400053e0);
  if ((int)uVar3 == 0) {
    wVar2 = 0;
  }
  else {
    wVar2 = *(word *)(puVar1 + (longlong)*(int *)(puVar1 + 0x3c) + 6);
  }
  return wVar2;
}

// sub_14000336B
/* WARNING: Enum "SectionFlags": Some values do not have unique names */

IMAGE_SECTION_HEADER * sub_14000336B(longlong param_1)

{
  int iVar1;
  undefined *puVar2;
  undefined8 uVar3;
  longlong local_res8;
  uint local_14;
  IMAGE_SECTION_HEADER *local_10;
  
  puVar2 = PTR_IMAGE_DOS_HEADER_1400053e0;
  uVar3 = sub_1400030F0((short *)PTR_IMAGE_DOS_HEADER_1400053e0);
  if ((int)uVar3 != 0) {
    iVar1 = *(int *)(puVar2 + 0x3c);
    local_14 = 0;
    local_10 = (IMAGE_SECTION_HEADER *)
               (puVar2 + (ulonglong)*(ushort *)(puVar2 + (longlong)iVar1 + 0x14) + (longlong)iVar1 +
                         0x18);
    local_res8 = param_1;
    for (; local_14 < *(ushort *)(puVar2 + (longlong)iVar1 + 6); local_14 = local_14 + 1) {
      if ((local_10->Characteristics & IMAGE_SCN_MEM_EXECUTE) != 0) {
        if (local_res8 == 0) {
          return local_10;
        }
        local_res8 = local_res8 + -1;
      }
      local_10 = local_10 + 1;
    }
  }
  return (IMAGE_SECTION_HEADER *)0x0;
}

// sub_140003417
IMAGE_DOS_HEADER * sub_140003417(void)

{
  undefined8 uVar1;
  IMAGE_DOS_HEADER *pIVar2;
  
  pIVar2 = (IMAGE_DOS_HEADER *)PTR_IMAGE_DOS_HEADER_1400053e0;
  uVar1 = sub_1400030F0((short *)PTR_IMAGE_DOS_HEADER_1400053e0);
  if ((int)uVar1 == 0) {
    pIVar2 = (IMAGE_DOS_HEADER *)0x0;
  }
  return pIVar2;
}

// sub_14000344B
uint sub_14000344B(longlong param_1)

{
  undefined *puVar1;
  uint uVar2;
  undefined8 uVar3;
  longlong lVar4;
  
  puVar1 = PTR_IMAGE_DOS_HEADER_1400053e0;
  uVar3 = sub_1400030F0((short *)PTR_IMAGE_DOS_HEADER_1400053e0);
  if ((int)uVar3 == 0) {
    uVar2 = 0;
  }
  else {
    lVar4 = sub_14000316C((longlong)puVar1,param_1 - (longlong)puVar1);
    if (lVar4 == 0) {
      uVar2 = 0;
    }
    else {
      uVar2 = ~*(uint *)(lVar4 + 0x24) >> 0x1f;
    }
  }
  return uVar2;
}

// sub_1400034BC
char * sub_1400034BC(int param_1)

{
  uint uVar1;
  undefined *puVar2;
  undefined8 uVar3;
  char *pcVar4;
  longlong lVar5;
  int local_res8;
  undefined *local_10;
  
  puVar2 = PTR_IMAGE_DOS_HEADER_1400053e0;
  uVar3 = sub_1400030F0((short *)PTR_IMAGE_DOS_HEADER_1400053e0);
  if ((int)uVar3 == 0) {
    pcVar4 = (char *)0x0;
  }
  else {
    uVar1 = *(uint *)(puVar2 + (longlong)*(int *)(puVar2 + 0x3c) + 0x90);
    if (uVar1 == 0) {
      pcVar4 = (char *)0x0;
    }
    else {
      lVar5 = sub_14000316C((longlong)puVar2,(ulonglong)uVar1);
      if (lVar5 == 0) {
        pcVar4 = (char *)0x0;
      }
      else {
        local_10 = puVar2 + uVar1;
        local_res8 = param_1;
        if (local_10 == (undefined *)0x0) {
          pcVar4 = (char *)0x0;
        }
        else {
          while( true ) {
            if ((*(int *)(local_10 + 4) == 0) && (*(int *)(local_10 + 0xc) == 0)) {
              return (char *)0x0;
            }
            if (local_res8 < 1) break;
            local_res8 = local_res8 + -1;
            local_10 = local_10 + 0x14;
          }
          pcVar4 = puVar2 + *(uint *)(local_10 + 0xc);
        }
      }
    }
  }
  return pcVar4;
}

// sub_1400035A0
ulonglong sub_1400035A0(void)

{
  ulonglong in_RAX;
  ulonglong uVar1;
  undefined8 *puVar2;
  undefined8 local_res8 [4];
  
  puVar2 = local_res8;
  uVar1 = in_RAX;
  if (0xfff < in_RAX) {
    do {
      puVar2 = puVar2 + -0x200;
      *puVar2 = *puVar2;
      uVar1 = uVar1 - 0x1000;
    } while (0x1000 < uVar1);
  }
  *(undefined8 *)((longlong)puVar2 - uVar1) = *(undefined8 *)((longlong)puVar2 - uVar1);
  return in_RAX;
}

// sub_1400035E0
void sub_1400035E0(undefined8 param_1,undefined8 param_2,undefined8 param_3)

{
  undefined8 *puVar1;
  
  puVar1 = (undefined8 *)sub_140003700();
  __stdio_common_vfprintf(*puVar1,param_1,param_2,0,param_3);
  return;
}

// sub_140003630
undefined4
sub_140003630(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4)

{
  undefined4 uVar1;
  ulonglong *puVar2;
  undefined8 local_res18;
  undefined8 local_res20;
  
  local_res18 = param_3;
  local_res20 = param_4;
  puVar2 = (ulonglong *)sub_140003700();
  uVar1 = __stdio_common_vsprintf(*puVar2 | 2,param_1,0xffffffffffffffff,param_2,0,&local_res18);
  return uVar1;
}

// sub_1400036A0
undefined4
sub_1400036A0(undefined8 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4)

{
  undefined4 uVar1;
  undefined8 *puVar2;
  undefined8 local_res18;
  undefined8 local_res20;
  
  local_res18 = param_3;
  local_res20 = param_4;
  puVar2 = (undefined8 *)sub_140003700();
  uVar1 = __stdio_common_vfprintf(*puVar2,param_1,param_2,0,&local_res18);
  return uVar1;
}

// sub_140003700
undefined * sub_140003700(void)

{
  return &DAT_140004060;
}

// sub_140003710
undefined * sub_140003710(void)

{
  return *(undefined **)PTR_PTR_140005430;
}

// sub_140003720
void sub_140003720(uint param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4)

{
  undefined8 uVar1;
  
  uVar1 = __acrt_iob_func(2);
  sub_1400036A0(uVar1,"runtime error %d\n",(ulonglong)param_1,param_4);
                    /* WARNING: Subroutine does not return */
  _exit(0xff);
}

// sub_140003760
undefined8
sub_140003760(undefined4 *param_1,undefined8 *param_2,undefined8 *param_3,int param_4,
             undefined4 *param_5)

{
  undefined4 uVar1;
  undefined4 *puVar2;
  undefined8 *puVar3;
  
  _initialize_narrow_environment();
  if (param_4 == 0) {
    uVar1 = 1;
  }
  else {
    uVar1 = 2;
  }
  _configure_narrow_argv(uVar1);
  puVar2 = (undefined4 *)__p___argc();
  *param_1 = *puVar2;
  puVar3 = (undefined8 *)__p___argv();
  *param_2 = *puVar3;
  puVar3 = (undefined8 *)__p__environ();
  *param_3 = *puVar3;
  _set_new_mode(*param_5);
  return 0;
}