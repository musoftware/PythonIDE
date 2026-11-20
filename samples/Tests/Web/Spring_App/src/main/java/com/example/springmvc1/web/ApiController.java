package com.example.springmvc1.web;

import java.time.Instant;
import java.util.Map;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class ApiController {

	@GetMapping("/time")
	public Map<String, Object> time() {
		return Map.of("time", Instant.now().toString(), "app", "SpringMvc1");
	}
}
