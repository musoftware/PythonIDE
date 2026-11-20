#[allow(unused_imports)]
use crate::radgui::*;
pub fn t_cslib() -> f64 { use crate::CsLib; CsLib::Add(2, 3).as_f64() }
pub fn t_vblib() -> f64 { use crate::VbLib; VbLib::Add(2, 3).as_f64() }
pub fn t_ringlib() -> f64 { use crate::RingLib; RingLib::Add(2, 3).as_f64() }
pub fn t_jslib() -> f64 { use crate::JsLib; JsLib::Add(2, 3).as_f64() }
pub fn t_tslib() -> f64 { use crate::TsLib; TsLib::Add(2, 3).as_f64() }
pub fn t_clib() -> f64 { use crate::CLib; CLib::Add(2, 3).as_f64() }
pub fn t_cpplib() -> f64 { use crate::CppLib; CppLib::Add(2, 3).as_f64() }
pub fn t_rustlib() -> f64 { use crate::RustLib; RustLib::add(2, 3).as_f64() }
pub fn t_fortlib() -> f64 { use crate::FortLib; FortLib::add(2, 3).as_f64() }
pub fn t_perllib() -> f64 { use crate::PerlLib; PerlLib::Add(2, 3).as_f64() }
pub fn t_dartlib() -> f64 { use crate::DartLib; DartLib::Add(2, 3).as_f64() }
pub fn t_javalib() -> f64 { use crate::JavaLib; JavaLib::add(2, 3).as_f64() }
pub fn t_phplib() -> f64 { use crate::PhpLib; PhpLib::Add(2, 3).as_f64() }
pub fn t_pslib() -> f64 { use crate::PsLib; PsLib::Add(2, 3).as_f64() }
pub fn t_pylib() -> f64 { use crate::PyLib; PyLib::Add(2, 3).as_f64() }
