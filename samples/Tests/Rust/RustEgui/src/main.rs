//! RustEgui - an egui desktop application (eframe 0.31).
//! The first build downloads and compiles eframe (a few minutes); later builds are quick.
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]   // no console window in release builds

use eframe::egui;

fn main() -> eframe::Result {
    let options = eframe::NativeOptions {
        viewport: egui::ViewportBuilder::default().with_inner_size([420.0, 320.0]).with_title("RustEgui"),
        ..Default::default()
    };
    eframe::run_native("RustEgui", options, Box::new(|_cc| Ok(Box::new(App::default()))))
}

struct App {
    name: String,
    age: u32,
    items: Vec<String>,
}

impl Default for App {
    fn default() -> Self {
        Self { name: "World".to_owned(), age: 30, items: Vec::new() }
    }
}

impl eframe::App for App {
    fn update(&mut self, ctx: &egui::Context, _frame: &mut eframe::Frame) {
        egui::CentralPanel::default().show(ctx, |ui| {
            ui.heading("RustEgui");
            ui.horizontal(|ui| {
                ui.label("Your name: ");
                ui.text_edit_singleline(&mut self.name);
            });
            ui.add(egui::Slider::new(&mut self.age, 0..=120).text("age"));
            if ui.button("Add to list").clicked() {
                self.items.push(format!("{} ({})", self.name, self.age));
            }
            ui.label(format!("Hello '{}', age {}", self.name, self.age));
            ui.separator();
            egui::ScrollArea::vertical().show(ui, |ui| {
                for item in &self.items {
                    ui.label(item);
                }
            });
        });
    }
}
