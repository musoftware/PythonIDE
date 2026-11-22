package com.example.springstore.web;

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
