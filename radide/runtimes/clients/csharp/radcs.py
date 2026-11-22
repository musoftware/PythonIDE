"""Command line helper for C# projects (build, NuGet packages). Used by the IDE and the bridge:

    python radcs.py build <project-folder> [--quiet]     build _build/csharp/RadApp.csproj if anything changed
    python radcs.py init  <project-folder>               create _build/csharp/RadApp.csproj (the NuGet manifest)
    python radcs.py pkg   <project-folder> list|add|remove [<package>[@<version>]]
"""
import sys
from pathlib import Path

# absolute(), not resolve(): reached through the pyroot junction in a release build (never _internal)
sys.path.insert(0, str(Path(__file__).absolute().parents[4]))

from radide.languages.csharp_bridge import cli  # noqa: E402

if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
