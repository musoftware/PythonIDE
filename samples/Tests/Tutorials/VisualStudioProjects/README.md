# Visual Studio projects course checker

`check_course.py` checks `radide/tutorials/visual-studio-projects` with the IDE's own tutorial checker
(`radide.tutorials.check`): every `run` and `solution` block is built with `dotnet build` and run, and its output
must equal the following ```` ```text output ```` block; every `exercise` starter must not pass as given.

    python samples/Tests/Tutorials/VisualStudioProjects/check_course.py          # all lessons (28 blocks)
    python samples/Tests/Tutorials/VisualStudioProjects/check_course.py 09 12    # only some lessons

Lessons 09-12 (NuGet Package Manager + Console and Central Package Management, references / COM / DllImport /
Object Browser, Shared Projects + `#if` symbols + multi-targeting, multi-project solutions with Directory.Build.props)
need nuget.org the first time (Humanizer.Core, Newtonsoft.Json). The CHM is rebuilt with
`python tools/build_chm.py visual-studio-projects --verify`.
