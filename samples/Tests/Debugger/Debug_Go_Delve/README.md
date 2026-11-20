# Debug_Go_Delve

**go-bridge: Go debugger (Delve `dlv dap`)** - the program is built with `-gcflags="all=-N -l"` and Delve
attaches to it. Breakpoints, steps, expandable Locals/Watch (structs, slices), hit counts, logpoints, goroutines
in the Threads window.

Needs Go (PATH or `%LOCALAPPDATA%\RADIDE\toolchains\go`) and Delve (PATH or `%LOCALAPPDATA%\RADIDE\tools\dlv`;
Debug > Install Delve builds it with `go install github.com/go-delve/delve/cmd/dlv@latest`).

**Try it:** line 22 (`total += square(numbers[i])`) with Breakpoint Settings > hit count = 3, line 12 with a logpoint
`sq n={n}`, F5: stops with `i = 2`; expand `p` and `numbers`; Watch `p.Label`; Debug > Windows > Threads.
