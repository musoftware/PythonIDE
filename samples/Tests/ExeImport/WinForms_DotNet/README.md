# WinForms_DotNet

**Exe import: .NET WinForms** - ilspycmd decompiles the assembly; InitializeComponent -> .form; C# handlers translated to Python (100% of statements).

**Try it:** `build.bat` (dotnet 9 SDK) -> bin\WinHello.exe; import it.

*Origin:* agents5 exe-managed (copied from the IDE's test runs, build output removed).

No binaries are kept in the repo: `source/` + `build.bat` rebuild the test program with the IDE's toolchains, so the import can be repeated.
