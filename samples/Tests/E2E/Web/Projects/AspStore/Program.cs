// RAD Store - ASP.NET Core minimal APIs + Microsoft.Data.Sqlite
using System.Collections.Concurrent;
using System.Globalization;
using System.Net;
using System.Security.Cryptography;
using Microsoft.Data.Sqlite;

var builder = WebApplication.CreateBuilder(args);
var app = builder.Build();

var dbPath = Path.Combine(app.Environment.ContentRootPath, "data", "store.db");
Directory.CreateDirectory(Path.GetDirectoryName(dbPath)!);
var cs = $"Data Source={dbPath}";
Exec("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, price REAL NOT NULL DEFAULT 0)");
if (Query("SELECT COUNT(*) AS n FROM products").First()["n"] is long n && n == 0)
    Exec("INSERT INTO products (name, price) VALUES ('Laptop', 999.5), ('Phone', 450)");

var sessions = new ConcurrentDictionary<string, Dictionary<string, string>>();

app.UseDefaultFiles();
app.UseStaticFiles();

app.MapGet("/products", (HttpContext ctx) =>
{
    var s = Session(ctx);
    var q = ctx.Request.Query["q"].ToString();
    var rows = Query("SELECT id, name, price FROM products WHERE name LIKE $q ORDER BY id", ("$q", $"%{q}%"));
    var trs = string.Join("", rows.Select(p => $"<tr data-id=\"{p["id"]}\"><td class=\"name\">{H(p["name"])}</td>" +
        $"<td>{Convert.ToDouble(p["price"]).ToString("0.00", CultureInfo.InvariantCulture)}</td><td>" +
        (s.ContainsKey("user") ? $"<a href=\"/products/{p["id"]}/edit\">Edit</a>" : "") + "</td></tr>"));
    return Page(ctx, "Products", "<h1>Products</h1>" +
        (s.ContainsKey("user") ? "<p><a class=\"btn\" href=\"/products/add\">Add product</a></p>" : "") +
        $"<table id=\"products\"><thead><tr><th>Name</th><th>Price</th><th></th></tr></thead><tbody>{trs}</tbody></table>" +
        $"<p class=\"count\">{rows.Count} products</p>");
});

app.MapGet("/products/add", (HttpContext ctx) => RequireLogin(ctx) ??
    Page(ctx, "Add product", "<h1>Add product</h1>" + Form(ctx, new List<string>(), "", "")));
app.MapPost("/products/add", async (HttpContext ctx) =>
{
    if (RequireLogin(ctx) is IResult r) return r;
    var f = await ctx.Request.ReadFormAsync();
    if (!CsrfOk(ctx, f)) return Results.BadRequest("Bad CSRF token");
    var (errors, name, price) = Validate(f["name"], f["price"]);
    if (errors.Count > 0)
        return Page(ctx, "Add product", "<h1>Add product</h1>" + Form(ctx, errors, name, f["price"].ToString()), 422);
    Exec("INSERT INTO products (name, price) VALUES ($n, $p)", ("$n", name), ("$p", price));
    return Results.Redirect("/products");
});

app.MapGet("/products/{id:int}/edit", (HttpContext ctx, int id) =>
{
    if (RequireLogin(ctx) is IResult r) return r;
    var row = Query("SELECT * FROM products WHERE id = $id", ("$id", id)).FirstOrDefault();
    if (row is null) return Results.NotFound();
    return Page(ctx, "Edit product", "<h1>Edit product</h1>" +
        Form(ctx, new List<string>(), row["name"]!.ToString()!, Convert.ToDouble(row["price"]).ToString(CultureInfo.InvariantCulture)) +
        $"<form method=\"post\" action=\"/products/{id}/delete\" class=\"delete\"><input type=\"hidden\" name=\"csrf\" value=\"{Session(ctx)["csrf"]}\"><button type=\"submit\">Delete</button></form>");
});
app.MapPost("/products/{id:int}/edit", async (HttpContext ctx, int id) =>
{
    if (RequireLogin(ctx) is IResult r) return r;
    var f = await ctx.Request.ReadFormAsync();
    if (!CsrfOk(ctx, f)) return Results.BadRequest("Bad CSRF token");
    var (errors, name, price) = Validate(f["name"], f["price"]);
    if (errors.Count > 0)
        return Page(ctx, "Edit product", "<h1>Edit product</h1>" + Form(ctx, errors, name, f["price"].ToString()), 422);
    Exec("UPDATE products SET name = $n, price = $p WHERE id = $id", ("$n", name), ("$p", price), ("$id", id));
    return Results.Redirect("/products");
});
app.MapPost("/products/{id:int}/delete", async (HttpContext ctx, int id) =>
{
    if (RequireLogin(ctx) is IResult r) return r;
    var f = await ctx.Request.ReadFormAsync();
    if (!CsrfOk(ctx, f)) return Results.BadRequest("Bad CSRF token");
    Exec("DELETE FROM products WHERE id = $id", ("$id", id));
    return Results.Redirect("/products");
});

app.MapGet("/login", (HttpContext ctx) => Page(ctx, "Log in", LoginForm(ctx, "")));
app.MapPost("/login", async (HttpContext ctx) =>
{
    var f = await ctx.Request.ReadFormAsync();
    if (!CsrfOk(ctx, f)) return Results.BadRequest("Bad CSRF token");
    if (f["username"] == "admin" && CryptographicOperations.FixedTimeEquals(
            System.Text.Encoding.UTF8.GetBytes(f["password"].ToString()), "secret"u8))
    {
        Session(ctx)["user"] = "admin";
        var next = f["next"].ToString();
        return Results.Redirect(next.StartsWith('/') ? next : "/products");
    }
    return Page(ctx, "Log in", LoginForm(ctx, "Invalid user name or password"), 401);
});
app.MapGet("/logout", (HttpContext ctx) => { Session(ctx).Remove("user"); return Results.Redirect("/"); });

app.MapGet("/api/products", () => Results.Json(Query("SELECT id, name, price FROM products ORDER BY id")
    .Select(p => new { id = (long)p["id"]!, name = (string)p["name"]!, price = Convert.ToDouble(p["price"]) })));

app.Run();

// ---------------------------------------------------------------- helpers
List<Dictionary<string, object?>> Query(string sql, params (string, object)[] args)
{
    using var c = new SqliteConnection(cs);
    c.Open();
    using var cmd = c.CreateCommand();
    cmd.CommandText = sql;
    foreach (var (k, v) in args) cmd.Parameters.AddWithValue(k, v);
    using var rd = cmd.ExecuteReader();
    var list = new List<Dictionary<string, object?>>();
    while (rd.Read())
    {
        var row = new Dictionary<string, object?>();
        for (int i = 0; i < rd.FieldCount; i++) row[rd.GetName(i)] = rd.IsDBNull(i) ? null : rd.GetValue(i);
        list.Add(row);
    }
    return list;
}

int Exec(string sql, params (string, object)[] args)
{
    using var c = new SqliteConnection(cs);
    c.Open();
    using var cmd = c.CreateCommand();
    cmd.CommandText = sql;
    foreach (var (k, v) in args) cmd.Parameters.AddWithValue(k, v);
    return cmd.ExecuteNonQuery();
}

static string H(object? s) => WebUtility.HtmlEncode(s?.ToString() ?? "");

Dictionary<string, string> Session(HttpContext ctx)
{
    var sid = ctx.Request.Cookies["sid"];
    if (sid is null || !sessions.TryGetValue(sid, out var s))
    {
        sid = Convert.ToHexString(RandomNumberGenerator.GetBytes(16));
        s = new Dictionary<string, string> { ["csrf"] = Convert.ToHexString(RandomNumberGenerator.GetBytes(16)) };
        sessions[sid] = s;
        ctx.Response.Cookies.Append("sid", sid, new CookieOptions { HttpOnly = true, SameSite = SameSiteMode.Lax, Path = "/" });
        ctx.Items["sid"] = sid;
    }
    return s;
}

bool CsrfOk(HttpContext ctx, IFormCollection f) => f["csrf"] == Session(ctx)["csrf"];

IResult? RequireLogin(HttpContext ctx) => Session(ctx).ContainsKey("user") ? null
    : Results.Redirect("/login?next=" + Uri.EscapeDataString(ctx.Request.Path));

(List<string>, string, double) Validate(string? name, string? price)
{
    var errors = new List<string>();
    name = (name ?? "").Trim();
    if (name == "") errors.Add("Name is required");
    if (!double.TryParse(price, NumberStyles.Float, CultureInfo.InvariantCulture, out var p) || p < 0)
        errors.Add("Price must be a positive number");
    return (errors, name, p);
}

string Form(HttpContext ctx, List<string> errors, string name, string price) =>
    string.Join("", errors.Select(e => $"<p class=\"error\">{H(e)}</p>")) +
    $"<form method=\"post\" class=\"product\"><input type=\"hidden\" name=\"csrf\" value=\"{Session(ctx)["csrf"]}\">" +
    $"<label>Name <input name=\"name\" value=\"{H(name)}\" required></label>" +
    $"<label>Price <input name=\"price\" value=\"{H(price)}\" type=\"number\" step=\"0.01\" min=\"0\"></label>" +
    "<button type=\"submit\">Save</button></form>";

string LoginForm(HttpContext ctx, string error) => "<h1>Log in</h1>" +
    (error != "" ? $"<p class=\"error\">{H(error)}</p>" : "") +
    $"<form method=\"post\" class=\"login\"><input type=\"hidden\" name=\"csrf\" value=\"{Session(ctx)["csrf"]}\">" +
    $"<input type=\"hidden\" name=\"next\" value=\"{H(ctx.Request.Query["next"].ToString() is { Length: > 0 } nx ? nx : "/products")}\">" +
    "<label>User name <input name=\"username\"></label><label>Password <input name=\"password\" type=\"password\"></label>" +
    "<button type=\"submit\">Log in</button></form>";

IResult Page(HttpContext ctx, string title, string body, int status = 200)
{
    var s = Session(ctx);
    var nav = s.TryGetValue("user", out var u) ? $"<span class=\"user\">{H(u)}</span> <a href=\"/logout\">Log out</a>" : "<a href=\"/login\">Log in</a>";
    var html = "<!DOCTYPE html><html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">" +
        $"<title>{H(title)} - RAD Store</title><link rel=\"stylesheet\" href=\"/css/site.css\"></head><body>" +
        $"<nav class=\"top\"><a href=\"/\">Home</a> <a href=\"/products\">Products</a> <a href=\"/ar.html\">العربية</a> {nav}</nav>" +
        $"<main>{body}</main><script src=\"/js/app.js\"></script></body></html>";
    return Results.Content(html, "text/html; charset=utf-8", System.Text.Encoding.UTF8, status);
}
