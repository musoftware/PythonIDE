// (c) 2026 Musoftware - https://musoftwares.com - MIT License
//
// Calculator - a pocket calculator in Rust (RAD IDE GUI Bridge: module radgui; Build > Publish makes an exe).
//
// The state lives in a struct inside a thread_local RefCell (the bridge calls the handlers one at a time);
// the engine methods return Result<(), String> and the `act` helper shows either the value or the error.
// Shows: many buttons, keyboard input on the form (KeyPress: event_arg(3) = key name, event_arg(4) = character),
// Result-based error handling, f64 formatting, a memory register.
use crate::radgui::*;
use std::cell::RefCell;

struct Calc {
    display: String,
    expression: String,
    acc: f64,
    memory: f64,
    op: Option<char>,
    fresh: bool,
    failed: bool,
}

impl Calc {
    fn new() -> Self {
        Calc { display: "0".into(), expression: String::new(), acc: 0.0, memory: 0.0, op: None, fresh: true, failed: false }
    }

    fn value(&self) -> f64 {
        self.display.parse().unwrap_or(0.0)
    }

    fn show(&mut self, x: f64) -> Result<(), String> {
        if !x.is_finite() || x.abs() > 1e15 {
            return Err("overflow".into());
        }
        self.display = str(x);
        Ok(())
    }

    fn digit(&mut self, d: &str) -> Result<(), String> {
        if self.failed {
            self.clear();
        }
        if self.fresh {
            self.display = if d == "." { "0".into() } else { String::new() };
            self.fresh = false;
        }
        if (d == "." && self.display.contains('.')) || self.display.len() >= 16 {
            return Ok(());
        }
        if self.display == "0" && d != "." {
            self.display.clear();
        }
        self.display.push_str(d);
        Ok(())
    }

    fn apply(&mut self) -> Result<(), String> {
        let x = self.value();
        self.acc = match self.op {
            Some('+') => self.acc + x,
            Some('-') => self.acc - x,
            Some('*') => self.acc * x,
            Some('/') if x == 0.0 => return Err("division by zero".into()),
            Some('/') => self.acc / x,
            _ => x,
        };
        let acc = self.acc;
        self.show(acc)
    }

    fn operation(&mut self, o: char) -> Result<(), String> {
        if self.failed {
            return Ok(());
        }
        if !self.fresh || self.op.is_none() {
            self.apply()?;
        }
        self.op = Some(o);
        self.fresh = true;
        self.expression = format!("{} {}", str(self.acc), o);
        Ok(())
    }

    fn result(&mut self) -> Result<(), String> {
        if self.failed || self.op.is_none() {
            return Ok(());
        }
        self.apply()?;
        self.op = None;
        self.fresh = true;
        self.expression.clear();
        Ok(())
    }

    fn clear(&mut self) {
        let memory = self.memory;
        *self = Calc::new();
        self.memory = memory;
    }

    fn unary(&mut self, what: char) -> Result<(), String> {
        if self.failed {
            return Ok(());
        }
        let x = self.value();
        let y = match what {
            'n' => -x,
            's' if x < 0.0 => return Err("negative square root".into()),
            's' => {
                self.fresh = true;
                x.sqrt()
            }
            _ => match self.op {
                Some(_) => self.acc * x / 100.0,
                None => x / 100.0,
            },
        };
        self.show(y)
    }

    fn back(&mut self) {
        if self.failed || self.fresh {
            return;
        }
        self.display.pop();
        if self.display.is_empty() || self.display == "-" {
            self.display = "0".into();
        }
    }
}

thread_local! {
    static CALC: RefCell<Calc> = RefCell::new(Calc::new());
}

/// Run one engine action, then show the display (or the error).
fn act(f: impl FnOnce(&mut Calc) -> Result<(), String>) {
    CALC.with(|c| {
        let mut c = c.borrow_mut();
        if let Err(why) = f(&mut c) {
            c.display = format!("Error: {}", why);
            c.expression.clear();
            c.failed = true;
            c.op = None;
            c.fresh = true;
        }
        set("lblDisplay", "Caption", &c.display);
        set("lblExpr", "Caption", &c.expression);
        set("lblMemory", "Caption", if c.memory != 0.0 { "M" } else { "" });
    });
}

pub fn frmCalc_Load() { act(|_| Ok(())); }
pub fn btn0_Click() { act(|c| c.digit("0")); }
pub fn btn1_Click() { act(|c| c.digit("1")); }
pub fn btn2_Click() { act(|c| c.digit("2")); }
pub fn btn3_Click() { act(|c| c.digit("3")); }
pub fn btn4_Click() { act(|c| c.digit("4")); }
pub fn btn5_Click() { act(|c| c.digit("5")); }
pub fn btn6_Click() { act(|c| c.digit("6")); }
pub fn btn7_Click() { act(|c| c.digit("7")); }
pub fn btn8_Click() { act(|c| c.digit("8")); }
pub fn btn9_Click() { act(|c| c.digit("9")); }
pub fn btnDot_Click() { act(|c| c.digit(".")); }
pub fn btnAdd_Click() { act(|c| c.operation('+')); }
pub fn btnSub_Click() { act(|c| c.operation('-')); }
pub fn btnMul_Click() { act(|c| c.operation('*')); }
pub fn btnDiv_Click() { act(|c| c.operation('/')); }
pub fn btnEquals_Click() { act(|c| c.result()); }
pub fn btnClear_Click() { act(|c| { c.clear(); Ok(()) }); }
pub fn btnSign_Click() { act(|c| c.unary('n')); }
pub fn btnSqrt_Click() { act(|c| c.unary('s')); }
pub fn btnPercent_Click() { act(|c| c.unary('%')); }
pub fn btnBack_Click() { act(|c| { c.back(); Ok(()) }); }
pub fn btnMC_Click() { act(|c| { c.memory = 0.0; Ok(()) }); }
pub fn btnMR_Click() { act(|c| { c.fresh = true; let m = c.memory; c.show(m) }); }
pub fn btnMPlus_Click() { act(|c| { c.memory += c.value(); c.fresh = true; Ok(()) }); }

/// The form gets the keys of all its controls: event_arg(3) = key name (Return ...), event_arg(4) = character.
pub fn frmCalc_KeyPress() {
    let key = event_arg(3);
    let ch = event_arg(4);
    act(|c| match ch.as_str() {
        d if d.len() == 1 && d.chars().all(|x| x.is_ascii_digit()) => c.digit(d),
        "." | "," => c.digit("."),
        "+" | "-" | "*" | "/" => c.operation(ch.chars().next().unwrap()),
        "=" => c.result(),
        _ => match key.as_str() {
            "Return" | "13" => c.result(),
            "Escape" | "27" => { c.clear(); Ok(()) }
            "BackSpace" | "8" => { c.back(); Ok(()) }
            _ => Ok(()),
        },
    });
}
