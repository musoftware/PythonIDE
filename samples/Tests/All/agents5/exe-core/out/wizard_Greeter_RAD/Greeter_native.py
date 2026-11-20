"""Functions recovered from Greeter.exe (native machine code).

Each function below documents what the original code calls and which strings it uses.
Bodies translated by AI are marked; the others are stubs to complete by hand.
"""



def MainProc(*args):
    """Native function at 0x140001760 (355 bytes, 64 instructions).
    Calls: EndDialog, GetDlgItemTextA, sprintf, SetDlgItemTextA, SendDlgItemMessageA, MessageBoxA
    Strings: 'Hello, %s!'; 'About Greeter'; 'Greeter 1.0 - made with MinGW'; 'Type a name and press Greet'
    """
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
    # EndDialog(?, 0)
    raise NotImplementedError


def WinMain(*args):
    """Native function at 0x1400018FD (88 bytes, 18 instructions).
    Calls: DialogBoxParamA
    """
    # DialogBoxParamA(?, 101, 0, &0x140001760, 0)
    # DialogBoxParamA(?, 102, 0, &0x1400018C3, 0)
    raise NotImplementedError


def main(*args):
    """Native function at 0x140001960 (298 bytes, 86 instructions).
    Calls: __main, __p__acmdln, GetStartupInfoA, WinMain, IsDBCSLeadByte
    """
    # __main()
    # __p__acmdln()
    # GetStartupInfoA(buffer)
    # WinMain(?, 0)
    # IsDBCSLeadByte()
    raise NotImplementedError
