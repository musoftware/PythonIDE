"""Command line helper for Java projects (build, Maven Central libraries in libs/):

    python radjava.py build <project-folder> [--quiet] [--force]   compile with javac if anything changed
    python radjava.py pkg   <project-folder> list
    python radjava.py pkg   <project-folder> add    <group:artifact[:version]>   (downloads into libs/ + dependencies)
    python radjava.py pkg   <project-folder> remove <group:artifact>
    python radjava.py pkg   <project-folder> search <text>
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from radide.languages.java_bridge import cli  # noqa: E402

if __name__ == "__main__":
    sys.exit(cli(sys.argv[1:]))
