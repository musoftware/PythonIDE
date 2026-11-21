"""Shared Projects (.shproj + .projitems) and the editor's "project context" (docs/DOTNET.md, "Shared Projects").

* model.py         the Shared Project model: create / items / consumers / solution entries + the .sln
                   SharedMSBuildProjectFiles lines - the API other slices use (no Qt)
* preprocessor.py  DefineConstants per configuration + target framework, inactive #if regions (no Qt)
* context.py       ProjectContext: the contexts of a file (consuming project x target framework) (no Qt)
* ctxbar.py        the project-context combo above the editor + greying (Qt)
* ui.py            Solution Explorer nodes, menus, dialogs, SharedReferencesTab (Qt)
"""
