# RustEgui

A native desktop application made with egui / eframe 0.31: a text box, a slider, a button and a list.
This is the project that File > New Project > Native > Rust (Cargo) > *egui Desktop App* creates.

* The first build downloads and compiles eframe and its dependencies. It takes about a minute (or longer on
  a slow connection). Later builds are quick.
* Ctrl+F5 runs it (`cargo run`). Release builds (`cargo build --release`) have no console window.
* rust-analyzer completes the egui API (`ui.` lists `button`, `label`, `add`, `horizontal` ...).
