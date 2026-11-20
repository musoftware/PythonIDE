# AspNet_App

**aspnet-web (ASP.NET Core MVC)** - made with File > New Project > Web > ASP.NET Core Web App > *ASP.NET Core MVC*
(`dotnet new mvc --no-https`, .NET 9 SDK).

What it shows:
- **Ctrl+F5**: `dotnet watch run` behind the IDE's dev server - Preview, Requests, hot reload after a save.
- **F5**: `dotnet build` + netcoredbg attached to the site - put a breakpoint (F9) in
  `Controllers/HomeController.cs` (`return View();` in `Index`), open `/` in the Preview: it stops there (Locals,
  Call Stack, F10/F11, Continue). Tested: breakpoint hit, page served after Continue.
- **Framework** dock (Site > Framework Tools): *Routes* (`/`, `/Home/Privacy`, `/Home/Error` - double-click opens the
  action), *dotnet CLI* (New MVC controller / view / Razor page, EF Core packages + migrations, build, test, publish),
  *Tools* (SDK, netcoredbg, csharp-ls, dotnet-ef).
- IntelliSense (Ctrl+Space inside the quotes): `View("` -> view names, `asp-controller="` / `asp-action="` ->
  controllers / actions, `asp-page="`, `<partial name="`.

`bin/` and `obj/` were removed; the first run rebuilds them.
