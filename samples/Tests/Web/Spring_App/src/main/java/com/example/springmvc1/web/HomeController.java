package com.example.springmvc1.web;

import java.util.ArrayList;
import java.util.List;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;

@Controller
public class HomeController {

	public record Product(int id, String name, double price) { }

	private final List<Product> products = new ArrayList<>(List.of(
			new Product(1, "Keyboard", 25.0), new Product(2, "Mouse", 12.5), new Product(3, "Monitor", 180.0)));

	@GetMapping("/")
	public String index(Model model) {
		model.addAttribute("title", "SpringMvc1");
		return "index";
	}

	@GetMapping("/products")
	public String products(Model model) {
		model.addAttribute("products", products);
		return "products/list";
	}

	@GetMapping("/products/{id}")
	public String product(@PathVariable int id, Model model) {
		model.addAttribute("product", products.stream().filter(p -> p.id() == id).findFirst().orElse(null));
		return "products/details";
	}

	@PostMapping("/products")
	public String add(@RequestParam String name, @RequestParam(defaultValue = "0") double price) {
		products.add(new Product(products.size() + 1, name, price));
		return "redirect:/products";
	}
}
