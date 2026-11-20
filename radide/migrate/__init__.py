"""Project migration (File > Migrate Project...): convert a project of another IDE into a RAD IDE
project, in the same language or in another one.

* ``source``         - read a foreign project into a neutral MigrationSource (forms in the .form model +
                       the original event code): VB6 .vbp/.frm, WinForms C# .csproj, WinForms VB.NET .vbproj,
                       .sln (first WinForms project), and any adapter registered in
                       radide.features.foreign_projects that provides ``migrate_source=callable(path)``.
* ``vb6_to_python``  - VB6 code -> python-tk / python-qt by rules (AST of radide/runtimes/vbparse.py).
* ``vb6_to_vbnet``   - VB6 code -> VB.NET (WinForms, SDK-style .vbproj buildable with ``dotnet build``).
* ``cs_qt``          - C# WinForms code -> python-qt (Qt variant of radide/importers/exe/dotnet.PyEmitter).
* ``vbnet``          - VB.NET WinForms (.Designer.vb + code) -> neutral forms; VB.NET code -> VB6 (vb-basic).
* ``engine``         - plan (preview of the mapping) + migrate (writes the project and MIGRATION_REPORT.md).
* ``runtime/``       - helper modules copied into migrated Python projects (vb6compat.py, vb6format.py).

The migrated project never depends on the IDE at run time.
"""
