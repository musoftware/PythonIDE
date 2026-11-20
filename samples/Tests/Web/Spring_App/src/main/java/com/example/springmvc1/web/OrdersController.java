package com.example.springmvc1.web;

import org.springframework.stereotype.Controller;
import org.springframework.ui.Model;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;

@Controller
@RequestMapping("/orders")
public class OrdersController {

	@GetMapping
	public String index(Model model) {
		model.addAttribute("message", "Hello from OrdersController");
		return "orders/index";
	}
}
