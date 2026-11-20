// sub_140001000
void sub_140001000(void)

{
  return;
}

// safe_flush
void safe_flush(void)

{
  fflush((FILE *)0x0);
  return;
}

// WinMainCRTStartup
int WinMainCRTStartup(void)

{
  int iVar1;
  
  *(undefined4 *)_refptr___mingw_app_type = 1;
  iVar1 = __tmainCRTStartup();
  return iVar1;
}

// mainCRTStartup
int mainCRTStartup(void)

{
  int iVar1;
  
  *(undefined4 *)_refptr___mingw_app_type = 0;
  iVar1 = __tmainCRTStartup();
  return iVar1;
}

// __tmainCRTStartup
int __tmainCRTStartup(void)

{
  undefined1 uVar1;
  int iVar2;
  FILE *_File;
  LPTOP_LEVEL_EXCEPTION_FILTER pPVar3;
  undefined7 extraout_var;
  undefined4 *puVar4;
  undefined8 uVar5;
  undefined8 *puVar6;
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
    local_38 = _refptr___native_startup_lock;
    local_40 = local_20;
    local_48 = 0;
    local_18 = 0;
    LOCK();
    if (*(longlong *)_refptr___native_startup_lock == 0) {
      *(longlong *)_refptr___native_startup_lock = local_20;
    }
    else {
      local_18 = *(longlong *)_refptr___native_startup_lock;
    }
    UNLOCK();
    if (local_18 == 0) goto LAB_140001128;
    if (local_18 == local_20) break;
    Sleep(1000);
  }
  local_c = 1;
LAB_140001128:
  if (*(int *)_refptr___native_startup_state == 1) {
    _amsg_exit(0x1f);
  }
  if (*(int *)_refptr___native_startup_state == 0) {
    *(undefined4 *)_refptr___native_startup_state = 1;
    _File = (FILE *)__acrt_iob_func(2);
    setvbuf(_File,(char *)0x0,4,0);
    iVar2 = atexit(safe_flush);
    if (iVar2 != 0) {
                    /* WARNING: Subroutine does not return */
      abort();
    }
    _pei386_runtime_relocator();
    pPVar3 = SetUnhandledExceptionFilter
                       ((LPTOP_LEVEL_EXCEPTION_FILTER)_refptr__gnu_exception_handler);
    *(LPTOP_LEVEL_EXCEPTION_FILTER *)_refptr___mingw_oldexcpt_handler = pPVar3;
    _set_invalid_parameter_handler(sub_140001000);
    _text();
    uVar1 = check_managed_app();
    managedapp = (int)CONCAT71(extraout_var,uVar1);
    if (*(int *)_refptr___mingw_app_type == 0) {
      __set_app_type(1);
    }
    else {
      __set_app_type(2);
    }
    puVar4 = (undefined4 *)__p__fmode();
    *puVar4 = *(undefined4 *)_refptr__fmode;
    puVar4 = (undefined4 *)__p__commode();
    *puVar4 = *(undefined4 *)_refptr__commode;
    local_24 = _text();
    if (local_24 < 0) {
      _amsg_exit(8);
    }
    if (*(int *)_refptr__MINGW_INSTALL_DEBUG_MATHERR == 1) {
      __mingw_setusermatherr(_refptr__matherr);
    }
    if (*(int *)_refptr___globallocalestatus == -1) {
      _configthreadlocale(-1);
    }
    iVar2 = _initterm_e(_refptr___xi_a,_refptr___xi_z);
    if (iVar2 != 0) {
      _amsg_exit(10);
    }
    local_5c = *(undefined4 *)_refptr__newmode;
    uVar5 = __getmainargs(&argc,&argv,&envp,*(int *)_refptr__dowildcard,&local_5c);
    local_24 = (int)uVar5;
    if (local_24 < 0) {
      _amsg_exit(8);
    }
    uVar5 = duplicate_ppstrings(argc,(longlong *)&argv);
    local_24 = (int)uVar5;
    if (local_24 != 0) {
      _amsg_exit(8);
    }
    _initterm(_refptr___xc_a,_refptr___xc_z);
    __main();
    *(undefined4 *)_refptr___native_startup_state = 2;
  }
  else {
    has_cctor = 1;
  }
  if (local_c == 0) {
    local_50 = _refptr___native_startup_lock;
    local_58 = 0;
    LOCK();
    *(undefined8 *)_refptr___native_startup_lock = 0;
    UNLOCK();
  }
  if (*(longlong *)_refptr___dyn_tls_init_callback != 0) {
    (**(code **)_refptr___dyn_tls_init_callback)(0,2,0);
  }
  puVar6 = (undefined8 *)__p___initenv();
  *puVar6 = envp;
  local_24 = main(argc,argv,envp);
  if (managedapp == 0) {
                    /* WARNING: Subroutine does not return */
    exit(local_24);
  }
  if (has_cctor == 0) {
    _cexit();
  }
  return local_24;
}

// check_managed_app
bool check_managed_app(void)

{
  int *piVar1;
  bool bVar2;
  
  *(undefined4 *)_refptr___mingw_initltsdrot_force = 1;
  *(undefined4 *)_refptr___mingw_initltsdyn_force = 1;
  *(undefined4 *)_refptr___mingw_initltssuo_force = 1;
  if (*(short *)_refptr___ImageBase == 0x5a4d) {
    piVar1 = (int *)(_refptr___ImageBase + *(int *)(_refptr___ImageBase + 0x3c));
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

// duplicate_ppstrings
undefined8 duplicate_ppstrings(int param_1,longlong *param_2)

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

// atexit
int __cdecl atexit(_func_5014 *param_1)

{
  int iVar1;
  
  iVar1 = _crt_atexit(param_1);
  return iVar1;
}

// .text
int __cdecl _text(FILE *_File,char *_Format,va_list _ArgList)

{
  int iVar1;
  undefined8 *puVar2;
  
  puVar2 = (undefined8 *)__local_stdio_printf_options();
  iVar1 = __stdio_common_vfprintf(*puVar2,_File,_Format,0,_ArgList);
  return iVar1;
}

// .weak.__deregister_frame_info.hmod_libgcc
undefined8 _weak___deregister_frame_info_hmod_libgcc(void)

{
  return 0;
}

// __gcc_register_frame
void __gcc_register_frame(void)

{
  HMODULE hModule;
  code *pcVar1;
  
  hModule = GetModuleHandleA("libgcc_s_dw2-1.dll");
  if (hModule == (HMODULE)0x0) {
    pcVar1 = _text;
    DAT_140004000 = _weak___deregister_frame_info_hmod_libgcc;
  }
  else {
    hmod_libgcc = LoadLibraryA("libgcc_s_dw2-1.dll");
    pcVar1 = GetProcAddress(hModule,"__register_frame_info");
    DAT_140004000 = GetProcAddress(hModule,"__deregister_frame_info");
    if (pcVar1 == (FARPROC)0x0) goto LAB_1400016ee;
  }
  (*pcVar1)(&DAT_140006000,&obj);
LAB_1400016ee:
  atexit(__gcc_deregister_frame);
  return;
}

// __gcc_deregister_frame
void __gcc_deregister_frame(void)

{
  if (DAT_140004000 != (code *)0x0) {
    (*DAT_140004000)(&DAT_140006000);
  }
  if (hmod_libgcc == (HMODULE)0x0) {
    return;
  }
                    /* WARNING: Could not recover jumptable at 0x00014000174e. Too many branches */
                    /* WARNING: Treating indirect jump as call */
  FreeLibrary(hmod_libgcc);
  return;
}

// MainProc
undefined8 MainProc(HWND param_1,int param_2,ushort param_3)

{
  char local_148 [208];
  CHAR local_78 [120];
  
  if (param_2 == 0x110) {
    SetDlgItemTextA(param_1,0x3eb,"Type a name and press Greet");
  }
  else {
    if (param_2 != 0x111) {
      return 0;
    }
    if (param_3 == 0x9c42) {
      MessageBoxA(param_1,"Greeter 1.0 - made with MinGW","About Greeter",0x40);
    }
    else if (param_3 < 0x9c43) {
      if (param_3 == 0x3ea) {
        GetDlgItemTextA(param_1,0x3e9,local_78,100);
        sprintf(local_148,"Hello, %s!",local_78);
        SetDlgItemTextA(param_1,0x3eb,local_148);
        SendDlgItemMessageA(param_1,0x3ed,0x180,0,(LPARAM)local_78);
      }
      else {
        if ((param_3 != 0x9c41) && (param_3 != 2)) {
          return 0;
        }
        EndDialog(param_1,0);
      }
    }
    else {
      if (param_3 != 0x9c43) {
        return 0;
      }
      SendDlgItemMessageA(param_1,0x3ed,0x184,0,0);
    }
  }
  return 1;
}

// AboutProc
bool AboutProc(HWND param_1,int param_2,short param_3)

{
  bool bVar1;
  
  if ((param_2 == 0x111) && ((ushort)(param_3 - 1U) < 2)) {
    EndDialog(param_1,0);
    bVar1 = true;
  }
  else {
    bVar1 = param_2 == 0x110;
  }
  return bVar1;
}

// WinMain
int __stdcall WinMain(HINSTANCE hInstance,HINSTANCE hPrevInstance,LPSTR lpCmdLine,int nShowCmd)

{
  int iVar1;
  INT_PTR IVar2;
  
  if ((lpCmdLine == (LPSTR)0x0) || (*lpCmdLine != 'a')) {
    IVar2 = DialogBoxParamA(hInstance,(LPCSTR)0x65,(HWND)0x0,MainProc,0);
    iVar1 = (int)IVar2;
  }
  else {
    IVar2 = DialogBoxParamA(hInstance,(LPCSTR)0x66,(HWND)0x0,AboutProc,0);
    iVar1 = (int)IVar2;
  }
  return iVar1;
}

// main
int __cdecl main(int _Argc,char **_Argv,char **_Env)

{
  BOOL BVar1;
  int iVar2;
  undefined8 *puVar3;
  _STARTUPINFOA local_88;
  HINSTANCE local_20;
  uint local_18;
  uint local_14;
  BYTE *local_10;
  
  __main();
  local_20 = (HINSTANCE)_refptr___ImageBase;
  puVar3 = (undefined8 *)__p__acmdln();
  local_10 = (BYTE *)*puVar3;
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
  iVar2 = WinMain(local_20,(HINSTANCE)0x0,(LPSTR)local_10,local_14);
  return iVar2;
}

// __do_global_dtors
void __do_global_dtors(void)

{
  for (; *(longlong *)p_0 != 0; p_0 = p_0 + 8) {
    (**(code **)p_0)();
  }
  return;
}

// __do_global_ctors
void __do_global_ctors(void)

{
  uint local_10;
  uint local_c;
  
  local_c = (uint)*(undefined8 *)_refptr___CTOR_LIST__;
  if (local_c == 0xffffffff) {
    local_c = 0;
    while (*(longlong *)(_refptr___CTOR_LIST__ + (ulonglong)(local_c + 1) * 8) != 0) {
      local_c = local_c + 1;
    }
  }
  for (local_10 = local_c; local_10 != 0; local_10 = local_10 - 1) {
    (**(code **)(_refptr___CTOR_LIST__ + (ulonglong)local_10 * 8))();
  }
  atexit(__do_global_dtors);
  return;
}

// __main
void __main(void)

{
  if (initialized == 0) {
    initialized = 1;
    __do_global_ctors();
  }
  return;
}

// tls_callback_0
void tls_callback_0(undefined8 param_1,int param_2)

{
  longlong *local_10;
  
  if (*(int *)_refptr__CRT_MT != 2) {
    *(undefined4 *)_refptr__CRT_MT = 2;
  }
  if (param_2 == 2) {
    for (local_10 = &_CRT_XDZ; local_10 != &_CRT_XDZ; local_10 = local_10 + 1) {
      if (*local_10 != 0) {
        (*(code *)*local_10)();
      }
    }
  }
  else if (param_2 == 1) {
    __mingw_TLScallback(param_1,1);
  }
  return;
}

// __tlregdtor
undefined8 __tlregdtor(void)

{
  return 0;
}

// tls_callback_1
void tls_callback_1(undefined8 param_1,uint param_2)

{
  if ((param_2 == 3) || (param_2 == 0)) {
    __mingw_TLScallback(param_1,param_2);
  }
  return;
}

// mark_section_writable
void mark_section_writable(ulonglong param_1,undefined8 param_2,longlong param_3,undefined8 param_4)

{
  BOOL BVar1;
  DWORD DVar2;
  IMAGE_DOS_HEADER *pIVar3;
  SIZE_T SVar4;
  PDWORD lpflOldProtect;
  ulonglong uVar5;
  _MEMORY_BASIC_INFORMATION local_48;
  PIMAGE_SECTION_HEADER local_18;
  uint local_10;
  int local_c;
  
  local_c = 0;
  while( true ) {
    if (maxSections <= local_c) {
      local_18 = __mingw_GetSectionForAddress(param_1);
      if (local_18 == (PIMAGE_SECTION_HEADER)0x0) {
        _text("Address %p has no image-section",param_1,param_3,param_4);
      }
      *(PIMAGE_SECTION_HEADER *)(the_secs + (longlong)local_c * 0x28 + 0x20) = local_18;
      *(undefined4 *)((longlong)local_c * 0x28 + the_secs) = 0;
      pIVar3 = _GetPEImageBase();
      uVar5 = (ulonglong)local_18->VirtualAddress;
      *(char **)((longlong)local_c * 0x28 + the_secs + 0x18) = pIVar3->e_magic + uVar5;
      SVar4 = VirtualQuery(*(LPCVOID *)((longlong)local_c * 0x28 + the_secs + 0x18),&local_48,0x30);
      if (SVar4 == 0) {
        _text("  VirtualQuery failed for %d bytes at address %p",
              (ulonglong)(local_18->Misc).PhysicalAddress,
              *(undefined8 *)((longlong)local_c * 0x28 + the_secs + 0x18),uVar5);
      }
      if ((((local_48.Protect != 0x40) && (local_48.Protect != 4)) && (local_48.Protect != 0x80)) &&
         (local_48.Protect != 8)) {
        if (local_48.Protect == 2) {
          local_10 = 4;
        }
        else {
          local_10 = 0x40;
        }
        *(PVOID *)(the_secs + (longlong)local_c * 0x28 + 8) = local_48.BaseAddress;
        *(SIZE_T *)(the_secs + (longlong)local_c * 0x28 + 0x10) = local_48.RegionSize;
        lpflOldProtect = (PDWORD)((longlong)local_c * 0x28 + the_secs);
        uVar5 = (ulonglong)local_10;
        BVar1 = VirtualProtect(local_48.BaseAddress,local_48.RegionSize,local_10,lpflOldProtect);
        if (BVar1 == 0) {
          DVar2 = GetLastError();
          _text("  VirtualProtect failed with code 0x%x",(ulonglong)DVar2,uVar5,lpflOldProtect);
        }
      }
      maxSections = maxSections + 1;
      return;
    }
    if ((*(ulonglong *)((longlong)local_c * 0x28 + the_secs + 0x18) <= param_1) &&
       (param_3 = the_secs,
       param_1 < (ulonglong)*(uint *)(*(longlong *)((longlong)local_c * 0x28 + the_secs + 0x20) + 8)
                 + *(longlong *)((longlong)local_c * 0x28 + the_secs + 0x18))) break;
    local_c = local_c + 1;
  }
  return;
}

// restore_modified_sections
void restore_modified_sections(void)

{
  DWORD local_10;
  int local_c;
  
  for (local_c = 0; local_c < maxSections; local_c = local_c + 1) {
    if (*(int *)((longlong)local_c * 0x28 + the_secs) != 0) {
      VirtualProtect(*(LPVOID *)((longlong)local_c * 0x28 + the_secs + 8),
                     *(SIZE_T *)((longlong)local_c * 0x28 + the_secs + 0x10),
                     *(DWORD *)((longlong)local_c * 0x28 + the_secs),&local_10);
    }
  }
  return;
}

// __write_memory
void __write_memory(void *param_1,void *param_2,size_t param_3,undefined8 param_4)

{
  if (param_3 != 0) {
    mark_section_writable((ulonglong)param_1,param_2,param_3,param_4);
    memcpy(param_1,param_2,param_3);
  }
  return;
}

// do_pseudo_reloc
void do_pseudo_reloc(uint *param_1,uint *param_2,ulonglong *param_3,longlong param_4)

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
        _text("  Unknown pseudo relocation protocol version %d.\n",(ulonglong)local_10[2],param_3,
              param_4);
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
            if (0x20 < uVar2) goto LAB_14000241c;
            if (uVar2 == 8) {
              local_50 = (ulonglong)(byte)*local_28;
              if (((byte)*local_28 & 0x80) != 0) {
                local_50 = local_50 | 0xffffffffffffff00;
              }
            }
            else {
              if (uVar2 != 0x10) goto LAB_14000241c;
              local_50 = (ulonglong)(ushort)*local_28;
              if (((ushort)*local_28 & 0x8000) != 0) {
                local_50 = local_50 | 0xffffffffffff0000;
              }
            }
          }
        }
        else {
LAB_14000241c:
          local_50 = 0;
          _text("  Unknown pseudo relocation bit size %d.\n",(ulonglong)(puVar1[5] & 0xff),puVar4,
                param_4);
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
            _text("%d bit pseudo relocation at %p out of range, targeting %p, yielding the value %p.\n"
                  ,(ulonglong)local_34,local_28,local_30);
          }
        }
        uVar2 = local_18[2] & 0xff;
        if (uVar2 == 0x40) {
          puVar4 = (ulonglong *)0x8;
          __write_memory(local_28,&local_50,8,param_4);
          puVar1 = local_18;
        }
        else {
          puVar1 = local_18;
          if (uVar2 < 0x41) {
            if (uVar2 == 0x20) {
              puVar4 = (ulonglong *)0x4;
              __write_memory(local_28,&local_50,4,param_4);
              puVar1 = local_18;
            }
            else if (uVar2 < 0x21) {
              if (uVar2 == 8) {
                puVar4 = (ulonglong *)0x1;
                __write_memory(local_28,&local_50,1,param_4);
                puVar1 = local_18;
              }
              else if (uVar2 == 0x10) {
                puVar4 = (ulonglong *)0x2;
                __write_memory(local_28,&local_50,2,param_4);
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
        __write_memory(local_28,&local_54,4,param_4);
      }
    }
  }
  return;
}

// _pei386_runtime_relocator
/* WARNING: Function: ___chkstk_ms replaced with injection: alloca_probe */

void _pei386_runtime_relocator(void)

{
  longlong lVar1;
  word wVar2;
  undefined6 extraout_var;
  longlong in_R9;
  undefined8 auStack_40 [6];
  undefined1 auStack_10 [4];
  int local_c;
  
  if (was_init_0 == 0) {
    was_init_0 = 1;
    auStack_40[0] = 0x1400025ba;
    wVar2 = __mingw_GetSectionCount();
    local_c = (int)CONCAT62(extraout_var,wVar2);
    auStack_40[0] = 0x1400025e2;
    lVar1 = -((longlong)local_c * 0x28 + 0xfU & 0xfffffffffffffff0);
    the_secs = auStack_10 + lVar1;
    maxSections = 0;
    *(undefined8 *)((longlong)auStack_40 + lVar1) = 0x140002627;
    do_pseudo_reloc((uint *)_refptr___RUNTIME_PSEUDO_RELOC_LIST__,
                    (uint *)_refptr___RUNTIME_PSEUDO_RELOC_LIST_END__,
                    (ulonglong *)_refptr___ImageBase,in_R9);
    *(undefined8 *)((longlong)auStack_40 + lVar1) = 0x14000262c;
    restore_modified_sections();
  }
  return;
}

// __mingw_raise_matherr
void __mingw_raise_matherr
               (undefined4 param_1,undefined8 param_2,undefined8 param_3,undefined8 param_4,
               undefined8 param_5)

{
  undefined4 local_38 [2];
  undefined8 local_30;
  undefined8 local_28;
  undefined8 local_20;
  undefined8 local_18;
  
  if (stUserMathErr != (code *)0x0) {
    local_18 = param_5;
    local_38[0] = param_1;
    local_30 = param_2;
    local_28 = param_3;
    local_20 = param_4;
    (*stUserMathErr)(local_38);
  }
  return;
}

// __mingw_setusermatherr
void __mingw_setusermatherr(undefined8 param_1)

{
  stUserMathErr = param_1;
  __setusermatherr(param_1);
  return;
}

// _gnu_exception_handler
int _gnu_exception_handler(longlong *param_1)

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
LAB_140002aaa:
    signal(4);
    if (extraout_RAX_00 == (code *)0x1) {
      signal(4);
      local_c = -1;
    }
    else if (extraout_RAX_00 != (code *)0x0) {
      (*extraout_RAX_00)(4);
      local_c = -1;
    }
    goto LAB_140002b70;
  }
  if ((0xc0000096 < uVar1) || (0xc0000095 < uVar1)) goto LAB_140002b70;
  if (uVar1 < 0xc0000094) {
    if (uVar1 != 0xc0000093) {
      if (0xc0000093 < uVar1) goto LAB_140002b70;
      if (uVar1 != 0xc0000092) {
        if ((0xc0000092 < uVar1) || (0xc0000091 < uVar1)) goto LAB_140002b70;
        if (0xc000008c < uVar1) goto LAB_140002afe;
        if (uVar1 != 0xc000008c) {
          if (0xc000008c < uVar1) goto LAB_140002b70;
          if (uVar1 == 0xc000001d) goto LAB_140002aaa;
          if (0xc000001d < uVar1) goto LAB_140002b70;
          if (uVar1 != 0xc0000008) {
            if (0xc0000008 < uVar1) goto LAB_140002b70;
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
              goto LAB_140002b70;
            }
          }
        }
      }
      local_c = -1;
      goto LAB_140002b70;
    }
LAB_140002afe:
    bVar2 = true;
  }
  signal(8);
  if (extraout_RAX_01 == (code *)0x1) {
    signal(8);
    if (bVar2) {
      _text();
    }
    local_c = -1;
  }
  else if (extraout_RAX_01 != (code *)0x0) {
    (*extraout_RAX_01)(8);
    local_c = -1;
  }
LAB_140002b70:
  if ((local_c == 0) && (__mingw_oldexcpt_handler != (code *)0x0)) {
    local_c = (*__mingw_oldexcpt_handler)(param_1);
  }
  return local_c;
}

// ___w64_mingwthr_add_key_dtor
undefined8 ___w64_mingwthr_add_key_dtor(undefined4 param_1,undefined8 param_2)

{
  undefined8 uVar1;
  undefined4 *puVar2;
  
  if (__mingwthr_cs_init == 0) {
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
      EnterCriticalSection((LPCRITICAL_SECTION)&__mingwthr_cs);
      *(undefined4 **)(puVar2 + 4) = key_dtor_list;
      key_dtor_list = puVar2;
      LeaveCriticalSection((LPCRITICAL_SECTION)&__mingwthr_cs);
      uVar1 = 0;
    }
  }
  return uVar1;
}

// ___w64_mingwthr_remove_key_dtor
undefined8 ___w64_mingwthr_remove_key_dtor(int param_1)

{
  int *local_18;
  int *local_10;
  
  if (__mingwthr_cs_init != 0) {
    EnterCriticalSection((LPCRITICAL_SECTION)&__mingwthr_cs);
    local_10 = (int *)0x0;
    for (local_18 = key_dtor_list; local_18 != (int *)0x0; local_18 = *(int **)(local_18 + 4)) {
      if (param_1 == *local_18) {
        if (local_10 == (int *)0x0) {
          key_dtor_list = *(int **)(local_18 + 4);
        }
        else {
          *(undefined8 *)(local_10 + 4) = *(undefined8 *)(local_18 + 4);
        }
        free(local_18);
        break;
      }
      local_10 = local_18;
    }
    LeaveCriticalSection((LPCRITICAL_SECTION)&__mingwthr_cs);
  }
  return 0;
}

// __mingwthr_run_key_dtors
void __mingwthr_run_key_dtors(void)

{
  DWORD DVar1;
  LPVOID pvVar2;
  DWORD *local_10;
  
  if (__mingwthr_cs_init != 0) {
    EnterCriticalSection((LPCRITICAL_SECTION)&__mingwthr_cs);
    for (local_10 = key_dtor_list; local_10 != (DWORD *)0x0; local_10 = *(DWORD **)(local_10 + 4)) {
      pvVar2 = TlsGetValue(*local_10);
      DVar1 = GetLastError();
      if ((DVar1 == 0) && (pvVar2 != (LPVOID)0x0)) {
        (**(code **)(local_10 + 2))(pvVar2);
      }
    }
    LeaveCriticalSection((LPCRITICAL_SECTION)&__mingwthr_cs);
  }
  return;
}

// __mingw_TLScallback
undefined8 __mingw_TLScallback(undefined8 param_1,uint param_2)

{
  void *pvVar1;
  void *local_10;
  
  if (param_2 == 3) {
    __mingwthr_run_key_dtors();
  }
  else if (param_2 < 4) {
    if (param_2 == 2) {
      _text();
    }
    else if (param_2 < 3) {
      if (param_2 == 0) {
        __mingwthr_run_key_dtors();
        if (__mingwthr_cs_init == 1) {
          local_10 = key_dtor_list;
          while (local_10 != (void *)0x0) {
            pvVar1 = *(void **)((longlong)local_10 + 0x10);
            free(local_10);
            local_10 = pvVar1;
          }
          key_dtor_list = (void *)0x0;
          __mingwthr_cs_init = 0;
          DeleteCriticalSection((LPCRITICAL_SECTION)&__mingwthr_cs);
        }
      }
      else if (param_2 == 1) {
        if (__mingwthr_cs_init == 0) {
          InitializeCriticalSection((LPCRITICAL_SECTION)&__mingwthr_cs);
        }
        __mingwthr_cs_init = 1;
      }
    }
  }
  return 1;
}

// _FindPESection
PIMAGE_SECTION_HEADER __cdecl _FindPESection(PBYTE pImageBase,DWORD_PTR rva)

{
  int iVar1;
  uint local_14;
  PIMAGE_SECTION_HEADER local_10;
  
  iVar1 = *(int *)(pImageBase + 0x3c);
  local_14 = 0;
  local_10 = (PIMAGE_SECTION_HEADER)
             (pImageBase +
             (ulonglong)*(ushort *)(pImageBase + (longlong)iVar1 + 0x14) + (longlong)iVar1 + 0x18);
  while( true ) {
    if (*(ushort *)(pImageBase + (longlong)iVar1 + 6) <= local_14) {
      return (PIMAGE_SECTION_HEADER)0x0;
    }
    if ((local_10->VirtualAddress <= rva) &&
       (rva < (local_10->Misc).PhysicalAddress + local_10->VirtualAddress)) break;
    local_14 = local_14 + 1;
    local_10 = local_10 + 1;
  }
  return local_10;
}

// _FindPESectionByName
IMAGE_SECTION_HEADER * _FindPESectionByName(char *param_1)

{
  int iVar1;
  undefined *puVar2;
  BOOL BVar3;
  int iVar4;
  size_t sVar5;
  uint local_14;
  IMAGE_SECTION_HEADER *local_10;
  
  sVar5 = strlen(param_1);
  puVar2 = _refptr___ImageBase;
  if ((sVar5 < 9) && (BVar3 = _text(_refptr___ImageBase), BVar3 != 0)) {
    iVar1 = *(int *)(puVar2 + 0x3c);
    local_14 = 0;
    local_10 = (IMAGE_SECTION_HEADER *)
               (puVar2 + (ulonglong)*(ushort *)(puVar2 + (longlong)iVar1 + 0x14) + (longlong)iVar1 +
                         0x18);
    for (; local_14 < *(ushort *)(puVar2 + (longlong)iVar1 + 6); local_14 = local_14 + 1) {
      iVar4 = strncmp(local_10->Name,param_1,8);
      if (iVar4 == 0) {
        return local_10;
      }
      local_10 = local_10 + 1;
    }
  }
  return (IMAGE_SECTION_HEADER *)0x0;
}

// __mingw_GetSectionForAddress
PIMAGE_SECTION_HEADER __mingw_GetSectionForAddress(longlong param_1)

{
  undefined *pImageBase;
  BOOL BVar1;
  PIMAGE_SECTION_HEADER p_Var2;
  
  pImageBase = _refptr___ImageBase;
  BVar1 = _text(_refptr___ImageBase);
  if (BVar1 == 0) {
    p_Var2 = (PIMAGE_SECTION_HEADER)0x0;
  }
  else {
    p_Var2 = _FindPESection(pImageBase,param_1 - (longlong)pImageBase);
  }
  return p_Var2;
}

// __mingw_GetSectionCount
word __mingw_GetSectionCount(void)

{
  undefined *puVar1;
  word wVar2;
  BOOL BVar3;
  
  puVar1 = _refptr___ImageBase;
  BVar3 = _text(_refptr___ImageBase);
  if (BVar3 == 0) {
    wVar2 = 0;
  }
  else {
    wVar2 = *(word *)(puVar1 + (longlong)*(int *)(puVar1 + 0x3c) + 6);
  }
  return wVar2;
}

// _FindPESectionExec
/* WARNING: Enum "SectionFlags": Some values do not have unique names */

IMAGE_SECTION_HEADER * _FindPESectionExec(longlong param_1)

{
  int iVar1;
  undefined *puVar2;
  BOOL BVar3;
  longlong local_res8;
  uint local_14;
  IMAGE_SECTION_HEADER *local_10;
  
  puVar2 = _refptr___ImageBase;
  BVar3 = _text(_refptr___ImageBase);
  if (BVar3 != 0) {
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

// _GetPEImageBase
IMAGE_DOS_HEADER * _GetPEImageBase(void)

{
  BOOL BVar1;
  IMAGE_DOS_HEADER *pIVar2;
  
  pIVar2 = (IMAGE_DOS_HEADER *)_refptr___ImageBase;
  BVar1 = _text(_refptr___ImageBase);
  if (BVar1 == 0) {
    pIVar2 = (IMAGE_DOS_HEADER *)0x0;
  }
  return pIVar2;
}

// _IsNonwritableInCurrentImage
BOOL __cdecl _IsNonwritableInCurrentImage(PBYTE pTarget)

{
  undefined *pImageBase;
  BOOL BVar1;
  uint uVar2;
  PIMAGE_SECTION_HEADER p_Var3;
  
  pImageBase = _refptr___ImageBase;
  BVar1 = _text(_refptr___ImageBase);
  if (BVar1 == 0) {
    uVar2 = 0;
  }
  else {
    p_Var3 = _FindPESection(pImageBase,(longlong)pTarget - (longlong)pImageBase);
    if (p_Var3 == (PIMAGE_SECTION_HEADER)0x0) {
      uVar2 = 0;
    }
    else {
      uVar2 = ~p_Var3->Characteristics >> 0x1f;
    }
  }
  return uVar2;
}

// __mingw_enum_import_library_names
char * __mingw_enum_import_library_names(int param_1)

{
  uint uVar1;
  undefined *pImageBase;
  BOOL BVar2;
  char *pcVar3;
  PIMAGE_SECTION_HEADER p_Var4;
  int local_res8;
  undefined *local_10;
  
  pImageBase = _refptr___ImageBase;
  BVar2 = _text(_refptr___ImageBase);
  if (BVar2 == 0) {
    pcVar3 = (char *)0x0;
  }
  else {
    uVar1 = *(uint *)(pImageBase + (longlong)*(int *)(pImageBase + 0x3c) + 0x90);
    if (uVar1 == 0) {
      pcVar3 = (char *)0x0;
    }
    else {
      p_Var4 = _FindPESection(pImageBase,(ulonglong)uVar1);
      if (p_Var4 == (PIMAGE_SECTION_HEADER)0x0) {
        pcVar3 = (char *)0x0;
      }
      else {
        local_10 = pImageBase + uVar1;
        local_res8 = param_1;
        if (local_10 == (undefined *)0x0) {
          pcVar3 = (char *)0x0;
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
          pcVar3 = pImageBase + *(uint *)(local_10 + 0xc);
        }
      }
    }
  }
  return pcVar3;
}

// ___chkstk_ms
/* WARNING: This is an inlined function */

ulonglong ___chkstk_ms(void)

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

// sprintf
int __cdecl sprintf(char *_Dest,char *_Format,...)

{
  int iVar1;
  ulonglong *puVar2;
  undefined8 in_R8;
  undefined8 in_R9;
  undefined8 local_res18;
  undefined8 local_res20;
  
  local_res18 = in_R8;
  local_res20 = in_R9;
  puVar2 = (ulonglong *)__local_stdio_printf_options();
  iVar1 = __stdio_common_vsprintf(*puVar2 | 2,_Dest,0xffffffffffffffff,_Format,0,&local_res18);
  return iVar1;
}

// fprintf
int __cdecl fprintf(FILE *_File,char *_Format,...)

{
  int iVar1;
  undefined8 *puVar2;
  undefined8 in_R8;
  undefined8 in_R9;
  undefined8 local_res18;
  undefined8 local_res20;
  
  local_res18 = in_R8;
  local_res20 = in_R9;
  puVar2 = (undefined8 *)__local_stdio_printf_options();
  iVar1 = __stdio_common_vfprintf(*puVar2,_File,_Format,0,&local_res18);
  return iVar1;
}

// __local_stdio_printf_options
undefined * __local_stdio_printf_options(void)

{
  return &options;
}

// __p___initenv
undefined * __p___initenv(void)

{
  return *(undefined **)_refptr___imp___initenv;
}

// _amsg_exit
void __cdecl _amsg_exit(int param_1)

{
  FILE *param0;
  
  param0 = (FILE *)__acrt_iob_func(2);
  fprintf(param0,"runtime error %d\n",param_1);
                    /* WARNING: Subroutine does not return */
  _exit(0xff);
}

// __getmainargs
undefined8
__getmainargs(undefined4 *param_1,undefined8 *param_2,undefined8 *param_3,int param_4,
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