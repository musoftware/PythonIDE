"""Visual Studio 2022 "Create a new project" (docs/DOTNET.md, "Project templates").

* catalog.py  installed ``dotnet new`` templates (template engine cache) + RAD IDE's own templates (no Qt)
* writers.py  the templates ``dotnet new`` does not have (Shared Project, .NET Framework old-style ...) (no Qt)
* create.py   create a project from a template into a new or an existing solution (no Qt)
* wizard.py   the dialog: Create a new project > Configure your new project > Additional information
"""
