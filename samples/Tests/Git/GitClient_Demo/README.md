# GitClient_Demo

**Tests the full Git client** (Git menu + Git Changes window): branches, push / pull with progress,
merge with a real conflict and the 3-way resolver, stash, history graph, blame, compare, tags,
amend, .gitignore helper and the GitHub tab.

A git repository cannot live inside this repository, so this sample is a script that builds one:

    python make_demo_repo.py                 (creates %TEMP%\RADIDE_GitDemo\Calc + remote.git)

**Try it** - open `%TEMP%\RADIDE_GitDemo\Calc\project.radproj` in RAD IDE, then *Git > Git Changes*:

1. **Graph** tab: 4 commits, two lanes (main and feature/mul), branch / tag labels.
2. **Branches** tab: main (current), feature/mul, docs. *Push* publishes main to the local "server"
   (`remote.git`) - the progress bar runs, the branch then tracks `origin/main`.
3. *Git > Merge into current branch...* > `feature/mul`: the merge stops with a conflict in `calc.py`,
   the yellow banner appears. *Resolve Conflicts...* opens the resolver: Incoming | Current panes on top
   (tick *Show base* for the common ancestor), the Result below. Use *Take Incoming / Take Current /
   Take Both* per conflict (or edit the result), *Accept Merge*, then *Continue* in the banner.
4. Change `calc.py`, *Stash* (tool bar); the **Stashes** tab shows it with its diff; *Pop* brings it back.
5. Open `calc.py`, *Git > Blame current file*: every line shows commit, date and author (Alice / Bob).
   *Git > Toggle inline blame* writes the same at the end of the lines in the editor.
6. *Git > Compare current file with commit...*: pick any commit / branch / tag in the list.
7. Tick **Amend** under the commit message to reword the last commit; graph context menu has
   cherry-pick, revert, reset, new branch / tag here.
8. Right-click a changed file: Discard, Blame, Compare, *Ignore all *.ext files* (opens the .gitignore
   editor with templates and an "is this path ignored?" tester).
9. **GitHub** tab: needs a GitHub remote and the GitHub CLI; if `gh` is missing, *Download GitHub CLI*
   puts the official portable zip into `%LOCALAPPDATA%\RADIDE\tools\gh`.

Error explanations: add a remote with a wrong URL (*Git > Remotes...*), *Fetch*: the message explains
that the server cannot be reached / sign-in is needed instead of only showing git's output.
