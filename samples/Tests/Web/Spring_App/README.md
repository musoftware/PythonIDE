# Spring_App

**spring-web (Spring Boot 4.2 MVC + Thymeleaf, Java 17, Maven wrapper)** - made with New Project > Web >
Spring Boot Web App > *Spring Boot MVC + Thymeleaf* (project from start.spring.io + RAD IDE's home controller, product
pages, `/api/time`; `OrdersController` + `templates/orders/index.html` were added with the CLI panel command
`new controller Orders`).

What it shows:
- **Ctrl+F5**: `mvnw spring-boot:run` (SERVER_PORT from the IDE, profile `dev`). The dev profile reads templates and
  static files from `src/main/resources`, so editing a page + save reloads the Preview at once; saving a `.java` file
  runs `mvnw -o compile` and devtools restarts the app. (The first run downloads Maven and the dependencies.)
- **F5**: the JVM starts with JDWP (`suspend=y`) and the IDE's Java debugger attaches - breakpoint in
  `HomeController.products` + open `/products`: stops with `this` / `model` in Locals. Tested.
- **Framework** dock: routes from `@GetMapping`/`@PostMapping`/`@RequestMapping`, Maven commands, tools (JDK, jdtls).
- IntelliSense: `return "` in a controller -> Thymeleaf view names + `redirect:/...`; `th:href="@{` -> routes;
  `th:replace="~{` -> templates and `th:fragment`s.

`target/` was removed.
