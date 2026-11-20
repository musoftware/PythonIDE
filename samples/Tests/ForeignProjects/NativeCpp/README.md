# NativeCpp - a Visual C++ console project (.vcxproj)

Hand-written in the layout of the Visual Studio "Console App" template: `ProjectConfigurations`
(Debug|x64, Release|x64), `PlatformToolset v143`, `ClCompile` / `ClInclude` items and a
`NativeCpp.vcxproj.filters` file (the *Source Files* / *Header Files* folders of Solution Explorer).

## In RAD IDE

* Open `NativeCpp.vcxproj`: Solution Explorer shows the filters as folders.
* Build / F5:
  * with Visual Studio or Build Tools (C++ workload, found by `vswhere`): `MSBuild NativeCpp.vcxproj
    -p:Configuration=Debug -p:Platform=x64`, then the program runs (MSVC programs are run without the
    debugger; use *Open in Visual Studio* to debug them);
  * without them: the `ClCompile` sources are compiled with MinGW `g++` (`%LOCALAPPDATA%\RADIDE\toolchains\mingw64`)
    into the IDE state folder, and F5 debugs with `gdb -i dap` (breakpoints, locals).
* **Add > New Item > C++ File / Header File** adds `ClCompile` / `ClInclude` to the `.vcxproj` and the
  matching `<Filter>` entry to the `.filters` file.
