"""Functions recovered from Adder.exe (native machine code).

Each function below documents what the original code calls and which strings it uses.
Bodies translated by AI are marked; the others are stubs to complete by hand.
"""


def sub_140001760(*args):
    """Native function at 0x140001760 (772 bytes, 128 instructions).
    Calls: CreateWindowExA, DefWindowProcA, GetDlgItemTextA, atoi, sprintf, SetDlgItemTextA, PostQuitMessage
    Strings: 'First number:'; 'STATIC'; 'EDIT'; 'Second number:'; 'BUTTON'; 'Sum = %d'
    """
    # CreateWindowExA(0, 'STATIC', 'First number:', 0x50000000, 10, 12, 100, 20, ?, 0, 0, 0)
    # CreateWindowExA(0, 'EDIT', '', 0x50800000, 120, 10, 120, 22, ?, 101, 0, 0)
    # CreateWindowExA(0, 'STATIC', 'Second number:', 0x50000000, 10, 42, 100, 20, ?, 0, 0, 0)
    # CreateWindowExA(0, 'EDIT', '', 0x50800000, 120, 40, 120, 22, ?, 102, 0, 0)
    # CreateWindowExA(0, 'BUTTON', 'Add', 0x50000000, 250, 25, 70, 26, ?, 103, 0, 0)
    # CreateWindowExA(0, 'STATIC', '', 0x50000000, 10, 75, 0x12c, 20, ?, 104, 0, 0)
    # DefWindowProcA()
    # GetDlgItemTextA(?, 101, buffer, 32)
    # GetDlgItemTextA(?, 102, buffer, 32)
    # atoi(buffer)
    # atoi(buffer)
    # sprintf(buffer, 'Sum = %d', ?)
    # SetDlgItemTextA(?, 104, buffer)
    # PostQuitMessage(0)
    raise NotImplementedError

def sub_140001A64(*args):
    """Native function at 0x140001A64 (307 bytes, 58 instructions).
    Calls: LoadCursorA, RegisterClassA, CreateWindowExA
    Strings: 'RadCalc'; 'Adder'
    """
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
    # __acrt_iob_func(2)
    # printf(?, 'runtime error %d\n')
    # _exit(255)
    raise NotImplementedError
