# Open Folder - project type detection

File > Open Folder (also "Open folder in RAD IDE" from Explorer and `radide <folder>` on the command line)
detects what kind of project a folder holds (radide/project_detect.py) and offers to create the RAD IDE project
file (radide/features/open_detect.py). These folders have **no** project.radproj on purpose.

| Folder | Detected as | Default in the dialog |
|---|---|---|
| `MultiRepo/` | PHP site in `backend/`, Flutter app in `mobile/`, static site in `site/` | list -> Create RAD IDE solution (`MultiRepo.radsln`, one project per sub-folder) |
| `WordPressSite/` | WordPress site (php-web) | Create RAD IDE project |
| `FlaskMini/` | Flask app (python-flask, `web.app = app`) | Create RAD IDE project |
| `PyTkApp/` | Python Tkinter GUI program (python-tk, startup `main`) | Create RAD IDE project |
| `GodotGame/` | Godot game (godot, `native_app`: your .tscn scenes stay yours) | Create RAD IDE project |
| `GoModule/` | Go module (go.mod) | Open in place (go run / go test, nothing written) |
| `LooseCSharp/` | C# files with their own `Main`, no .csproj | Open in place (built in the IDE state folder) |
| `LuaScripts/` | Lua scripts | Open in place (each script is a run target) |

Try: File > Open Folder > pick one of them. Pick "Open as plain folder" + "Don't ask again" to get the old
folder workspace; right-click it in Solution Explorer > **Detect Project Type...** to be asked again.
Opening a copy is recommended (Create writes project.radproj / .radsln into the folder).

## Automated test

`tools/build_cases.py` writes ~45 project layouts (PHP, Laravel/CodeIgniter/Symfony/WordPress, Node/Express/Next/Vite,
static, Django/Flask/FastAPI, Tk/Qt/pygame/Jupyter, C/C++/Make, C#, Java, Go, Ruby/Rails/Sinatra, Ring, Lua, Perl,
PowerShell, Fortran, Dart, Godot, VB, Kotlin, VB.NET, multi-project) and copies of samples into
`%TEMP%\radide_opendetect_cases` (or `RADIDE_OPENDETECT_CASES`). Projects made with the real tools are optional extra
cases in the same folder: `composer create-project laravel/laravel LaravelNew`, `dotnet new console -o DotnetConsole`,
`dotnet new webapi -o DotnetWebApi`, `cargo new CargoHello`, `go mod init` (GoHello), `npm create vite@latest vite-react
-- --template react`, `flutter create --no-pub flutter_app`.

`tools/test_open_detect.py [case ...]` opens every folder through the IDE (offscreen MainWindow, test settings),
answers the dialog with its default, checks the detected type, the written project file (and, for sample copies, that
it matches the sample's own project.radproj), that no user file changed, and runs some of them (PHP / static /
Laravel sites serve a page; Python, dotnet console, cargo, Go, loose C#/Java, C, Perl, Lua, Dart, PowerShell print).
