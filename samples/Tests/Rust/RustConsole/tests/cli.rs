//! Integration test: runs the compiled binary.
use std::process::Command;

#[test]
fn prints_hello() {
    let out = Command::new(env!("CARGO_BIN_EXE_rustconsole")).output().expect("run");
    assert!(String::from_utf8_lossy(&out.stdout).contains("Hello from RustConsole!"));
}
