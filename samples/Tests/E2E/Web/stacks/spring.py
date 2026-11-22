# (c) 2026 Musoftware - https://musoftwares.com - MIT License
"""RAD Store on Spring Boot (Spring MVC + Thymeleaf): New Project > Web > Spring Boot MVC + Thymeleaf; SQLite
through sqlite-jdbc (added to pom.xml in the editor), the home page is static/index.html (Design View)."""
TITLE = "Spring Boot MVC + Thymeleaf + SQLite"
LANG, TEMPLATE, NAME = "spring-web", "spring-mvc", "SpringStore"
TOOLS = []
PKG = "com/example/springstore"
RES = "src/main/resources"
WEBROOT = f"{RES}/static"
DB_FILE = "data/store.db"
DESIGN = f"{RES}/static/index.html"
DESIGN_TARGET = "#home"
ROUTES = {"home": "/", "products": "/products", "add": "/products/add", "edit": "/products/{id}/edit",
          "login": "/login", "logout": "/logout", "ar": "/ar.html", "api": "/api/products",
          "css": "/css/site.css", "js": "/js/app.js"}
DEBUG = {"file": f"src/main/java/{PKG}/web/HomeController.java", "match": "var rows = query(", "path": "/products"}
DEBUG_TIMEOUT = 900
DEBUG_SETTLE = 8.0
INTELLI = {"file": f"src/main/java/{PKG}/web/HomeController.java", "after": "public String products(",
           "type": 'return "store/pro', "expect": "store/products", "timeout": 40,
           "html_file": f"{RES}/static/index.html", "css_file": f"{RES}/static/css/site.css"}
PUBLISH_EXPECT = ["pom.xml", "mvnw.cmd", f"src/main/java/{PKG}/web/HomeController.java",
                  f"{RES}/templates/store/products.html", f"{RES}/static/index.html"]
PUBLISH_FORBID = ["data/store.db"]
PUBLISH_EXCLUDES = ["target"]
RUN_TIMEOUT = 1200
PUBLISHED_TIMEOUT = 900


def toolchain_check():
    from radide.web_site.frameworks.spring import find_jdk
    return "" if find_jdk() else "no JDK 17+ (JAVA_HOME, PATH, %LOCALAPPDATA%\\Java, RADIDE\\tools\\jdk*)"


def after_create(j, win, project, folder):
    from pathlib import Path
    j.check((Path(folder) / "src/main/java" / PKG).is_dir(), f"package folder {PKG} not created")
    return "start.spring.io / offline project"


def after_code(j, win, project, folder):
    """pom.xml in the editor: add the SQLite JDBC driver (version managed by Spring Boot)."""
    from pathlib import Path
    pom = Path(folder) / "pom.xml"
    text = pom.read_text(encoding="utf-8")
    if "sqlite-jdbc" not in text:
        dep = ("<dependencies>\n\t\t<dependency>\n\t\t\t<groupId>org.xerial</groupId>\n"
               "\t\t\t<artifactId>sqlite-jdbc</artifactId>\n\t\t</dependency>")
        j.edit(pom, text.replace("<dependencies>", dep, 1))
    return "pom.xml: + org.xerial:sqlite-jdbc"


def serve_published(dest, port, **_):
    import os
    from pathlib import Path
    from radide.web_site.frameworks.spring import SpringPlugin, mvnw
    env = dict(os.environ)
    env.update(SpringPlugin().env())
    env.pop("SPRING_PROFILES_ACTIVE", None)          # production: templates from the classpath
    env.update({"SERVER_PORT": str(port), "SERVER_ADDRESS": "127.0.0.1"})
    return [mvnw(Path(dest)), "-B", "-q", "spring-boot:run"], str(dest), env


DB_SQL = """-- RAD Store schema (Databases workspace)
CREATE TABLE IF NOT EXISTS products (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  price REAL NOT NULL DEFAULT 0
);
INSERT INTO products (name, price) VALUES ('Laptop', 999.5), ('Phone', 450);
"""

CONTROLLER = """package com.example.springstore.web;

import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.util.ArrayList;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;

import jakarta.servlet.http.HttpServletResponse;
import jakarta.servlet.http.HttpSession;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.ModelAttribute;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseBody;

/** RAD Store: products (SQLite through JDBC), login, JSON API. */
@Controller
public class HomeController {

	public record Product(long id, String name, double price) { }

	private final String url;

	public HomeController() throws Exception {
		Path dir = Path.of("data");
		Files.createDirectories(dir);
		url = "jdbc:sqlite:" + dir.resolve("store.db").toAbsolutePath();
		exec("CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, price REAL NOT NULL DEFAULT 0)");
		if (query("SELECT id, name, price FROM products").isEmpty()) {
			exec("INSERT INTO products (name, price) VALUES ('Laptop', 999.5), ('Phone', 450)");
		}
	}

	private List<Product> query(String sql, Object... args) {
		try (Connection c = DriverManager.getConnection(url); PreparedStatement st = c.prepareStatement(sql)) {
			for (int i = 0; i < args.length; i++) st.setObject(i + 1, args[i]);
			List<Product> out = new ArrayList<>();
			try (ResultSet rs = st.executeQuery()) {
				while (rs.next()) out.add(new Product(rs.getLong("id"), rs.getString("name"), rs.getDouble("price")));
			}
			return out;
		} catch (Exception e) {
			throw new IllegalStateException(e);
		}
	}

	private int exec(String sql, Object... args) {
		try (Connection c = DriverManager.getConnection(url); PreparedStatement st = c.prepareStatement(sql)) {
			for (int i = 0; i < args.length; i++) st.setObject(i + 1, args[i]);
			return st.executeUpdate();
		} catch (Exception e) {
			throw new IllegalStateException(e);
		}
	}

	private static String csrf(HttpSession s) {
		Object t = s.getAttribute("csrf");
		if (t == null) {
			byte[] b = new byte[16];
			new SecureRandom().nextBytes(b);
			t = HexFormat.of().formatHex(b);
			s.setAttribute("csrf", t);
		}
		return (String) t;
	}

	private static boolean csrfOk(HttpSession s, Map<String, String> f) {
		return csrf(s).equals(f.get("csrf"));
	}

	@ModelAttribute
	public void common(Model model, HttpSession session) {
		model.addAttribute("csrf", csrf(session));
		model.addAttribute("user", session.getAttribute("user"));
	}

	private static List<String> validate(Map<String, String> f) {
		List<String> errors = new ArrayList<>();
		if (f.getOrDefault("name", "").isBlank()) errors.add("Name is required");
		try {
			if (Double.parseDouble(f.getOrDefault("price", "")) < 0) errors.add("Price must be a positive number");
		} catch (NumberFormatException e) {
			errors.add("Price must be a positive number");
		}
		return errors;
	}

	private static String form(Model m, String title, List<String> errors, String name, String price, Long pid) {
		m.addAttribute("title", title);
		m.addAttribute("errors", errors);
		m.addAttribute("name", name);
		m.addAttribute("price", price);
		m.addAttribute("pid", pid);
		return "store/form";
	}

	@GetMapping("/products")
	public String products(@RequestParam(defaultValue = "") String q, Model model) {
		var rows = query("SELECT id, name, price FROM products WHERE name LIKE ? ORDER BY id", "%" + q + "%");
		model.addAttribute("products", rows);
		model.addAttribute("q", q);
		return "store/products";
	}

	@GetMapping("/products/add")
	public String addForm(HttpSession s, Model m) {
		if (s.getAttribute("user") == null) return "redirect:/login?next=/products/add";
		return form(m, "Add product", List.of(), "", "", null);
	}

	@PostMapping("/products/add")
	public String add(@RequestParam Map<String, String> f, HttpSession s, Model m, HttpServletResponse res) {
		if (s.getAttribute("user") == null) return "redirect:/login?next=/products/add";
		if (!csrfOk(s, f)) { res.setStatus(400); return "store/error"; }
		List<String> errors = validate(f);
		if (!errors.isEmpty()) {
			res.setStatus(422);
			return form(m, "Add product", errors, f.getOrDefault("name", ""), f.getOrDefault("price", ""), null);
		}
		exec("INSERT INTO products (name, price) VALUES (?, ?)", f.get("name").trim(), Double.parseDouble(f.get("price")));
		return "redirect:/products";
	}

	@GetMapping("/products/{id}/edit")
	public String editForm(@PathVariable long id, HttpSession s, Model m, HttpServletResponse res) {
		if (s.getAttribute("user") == null) return "redirect:/login?next=/products/" + id + "/edit";
		var rows = query("SELECT id, name, price FROM products WHERE id = ?", id);
		if (rows.isEmpty()) { res.setStatus(404); return "store/error"; }
		Product p = rows.get(0);
		return form(m, "Edit product", List.of(), p.name(), String.valueOf(p.price()), p.id());
	}

	@PostMapping("/products/{id}/edit")
	public String edit(@PathVariable long id, @RequestParam Map<String, String> f, HttpSession s, Model m,
					   HttpServletResponse res) {
		if (s.getAttribute("user") == null) return "redirect:/login";
		if (!csrfOk(s, f)) { res.setStatus(400); return "store/error"; }
		List<String> errors = validate(f);
		if (!errors.isEmpty()) {
			res.setStatus(422);
			return form(m, "Edit product", errors, f.getOrDefault("name", ""), f.getOrDefault("price", ""), id);
		}
		exec("UPDATE products SET name = ?, price = ? WHERE id = ?", f.get("name").trim(),
				Double.parseDouble(f.get("price")), id);
		return "redirect:/products";
	}

	@PostMapping("/products/{id}/delete")
	public String delete(@PathVariable long id, @RequestParam Map<String, String> f, HttpSession s,
						 HttpServletResponse res) {
		if (s.getAttribute("user") == null) return "redirect:/login";
		if (!csrfOk(s, f)) { res.setStatus(400); return "store/error"; }
		exec("DELETE FROM products WHERE id = ?", id);
		return "redirect:/products";
	}

	@GetMapping("/login")
	public String loginPage(@RequestParam(defaultValue = "/products") String next, Model m) {
		m.addAttribute("next", next);
		m.addAttribute("error", "");
		return "store/login";
	}

	@PostMapping("/login")
	public String login(@RequestParam Map<String, String> f, HttpSession s, Model m, HttpServletResponse res) {
		if (!csrfOk(s, f)) { res.setStatus(400); return "store/error"; }
		boolean ok = "admin".equals(f.get("username")) && MessageDigest.isEqual(
				f.getOrDefault("password", "").getBytes(), "secret".getBytes());
		if (!ok) {
			res.setStatus(401);
			m.addAttribute("next", f.getOrDefault("next", "/products"));
			m.addAttribute("error", "Invalid user name or password");
			return "store/login";
		}
		s.setAttribute("user", "admin");
		String next = f.getOrDefault("next", "/products");
		return "redirect:" + (next.startsWith("/") ? next : "/products");
	}

	@GetMapping("/logout")
	public String logout(HttpSession s) {
		s.removeAttribute("user");
		return "redirect:/";
	}

	@GetMapping("/api/products")
	@ResponseBody
	public List<Product> api() {
		return query("SELECT id, name, price FROM products ORDER BY id");
	}
}
"""

NAV = """<!DOCTYPE html>
<html xmlns:th="http://www.thymeleaf.org">
<body>
<nav class="top" th:fragment="nav"><a href="/">Home</a> <a href="/products">Products</a> <a href="/ar.html">العربية</a>
<span th:if="${user}"><span class="user" th:text="${user}">admin</span> <a href="/logout">Log out</a></span>
<a th:unless="${user}" href="/login">Log in</a></nav>
</body>
</html>
"""

HEAD = """<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title th:text="${title} + ' - RAD Store'">RAD Store</title><link rel="stylesheet" href="/css/site.css"></head>"""

PRODUCTS = f"""<!DOCTYPE html>
<html lang="en" xmlns:th="http://www.thymeleaf.org">
{HEAD.replace("${title} + ' - RAD Store'", "'Products - RAD Store'")}
<body>
<nav th:replace="~{{store/nav :: nav}}"></nav>
<main>
<h1>Products</h1>
<form method="get" class="search"><input name="q" th:value="${{q}}" placeholder="Search"><button>Search</button></form>
<p th:if="${{user}}"><a class="btn" href="/products/add">Add product</a></p>
<table id="products"><thead><tr><th>Name</th><th>Price</th><th></th></tr></thead><tbody>
<tr th:each="p : ${{products}}" th:attr="data-id=${{p.id}}"><td class="name" th:text="${{p.name}}">x</td>
<td th:text="${{#numbers.formatDecimal(p.price, 1, 2, 'POINT')}}">0</td>
<td><a th:if="${{user}}" th:href="@{{/products/{{id}}/edit(id=${{p.id}})}}">Edit</a></td></tr>
</tbody></table>
<p class="count"><span th:text="${{#lists.size(products)}}">0</span> products</p>
</main>
<script src="/js/app.js"></script>
</body>
</html>
"""

FORM = f"""<!DOCTYPE html>
<html lang="en" xmlns:th="http://www.thymeleaf.org">
{HEAD}
<body>
<nav th:replace="~{{store/nav :: nav}}"></nav>
<main>
<h1 th:text="${{title}}">Product</h1>
<p class="error" th:each="e : ${{errors}}" th:text="${{e}}">error</p>
<form method="post" class="product">
  <input type="hidden" name="csrf" th:value="${{csrf}}">
  <label>Name <input name="name" th:value="${{name}}" required></label>
  <label>Price <input name="price" th:value="${{price}}" type="number" step="0.01" min="0"></label>
  <button type="submit">Save</button>
</form>
<form th:if="${{pid}}" method="post" th:action="@{{/products/{{id}}/delete(id=${{pid}})}}" class="delete">
  <input type="hidden" name="csrf" th:value="${{csrf}}"><button type="submit">Delete</button>
</form>
</main>
</body>
</html>
"""

LOGIN = f"""<!DOCTYPE html>
<html lang="en" xmlns:th="http://www.thymeleaf.org">
{HEAD.replace("${title} + ' - RAD Store'", "'Log in - RAD Store'")}
<body>
<nav th:replace="~{{store/nav :: nav}}"></nav>
<main>
<h1>Log in</h1>
<p class="error" th:if="${{error}}" th:text="${{error}}">error</p>
<form method="post" class="login">
  <input type="hidden" name="csrf" th:value="${{csrf}}"><input type="hidden" name="next" th:value="${{next}}">
  <label>User name <input name="username"></label>
  <label>Password <input name="password" type="password"></label>
  <button type="submit">Log in</button>
</form>
</main>
</body>
</html>
"""

ERROR = """<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><title>Error - RAD Store</title></head>
<body><h1>Request refused</h1><p><a href="/">Home</a></p></body></html>
"""

INDEX = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>RAD Store</title>
<link rel="stylesheet" href="/css/site.css">
</head>
<body>
<nav class="top"><a href="/">Home</a> <a href="/products">Products</a> <a href="/ar.html">العربية</a> <a href="/login">Log in</a></nav>
<main id="home">
</main>
<script src="/js/app.js"></script>
</body>
</html>
"""

AR = """<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>متجر راد</title><link rel="stylesheet" href="/css/site.css"></head>
<body>
<nav class="top"><a href="/">English</a> <a href="/products">المنتجات</a></nav>
<main><h1>مرحبا بكم في متجر راد</h1><p>أفضل الأجهزة بأفضل الأسعار.</p></main>
</body>
</html>
"""

CSS = """/* RAD Store */
body { font-family: "Segoe UI", Tahoma, sans-serif; margin: 0; background: #f6f7fb; color: #222; }
nav.top { background: #6db33f; padding: 10px 16px; }
nav.top a, nav.top .user { color: #fff; margin-inline-end: 14px; text-decoration: none; }
main { max-width: 900px; margin: 20px auto; padding: 0 16px; }
table { width: 100%; border-collapse: collapse; background: #fff; }
th, td { padding: 8px; border-bottom: 1px solid #ddd; text-align: start; }
.error { color: #b00020; font-weight: bold; }
.hero { padding: 40px 20px; background: linear-gradient(90deg, #3d7f1f, #6db33f); color: #fff; border-radius: 12px; }
"""


def files():
    return {f"src/main/java/{PKG}/web/HomeController.java": CONTROLLER,
            f"{RES}/templates/store/nav.html": NAV, f"{RES}/templates/store/products.html": PRODUCTS,
            f"{RES}/templates/store/form.html": FORM, f"{RES}/templates/store/login.html": LOGIN,
            f"{RES}/templates/store/error.html": ERROR, f"{RES}/static/index.html": INDEX,
            f"{RES}/static/ar.html": AR, f"{RES}/static/css/site.css": CSS,
            f"{RES}/static/js/app.js": "// RAD Store\ndocument.addEventListener('DOMContentLoaded', () => { document.body.dataset.ready = '1'; });\n"}
