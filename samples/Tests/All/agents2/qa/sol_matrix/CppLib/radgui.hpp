// RAD IDE GUI Bridge - C++ convenience layer over radgui.h (std::string in/out).
//   rad::set("lblOut", "Caption", "Hi");   std::string s = rad::get("txtA", "Text");
//   rad::call("lstLog", "AddItem", "x");   double x = rad::num(s);   rad::str(3.5) -> "3.5"
//   std::string r = rad::hub("Helpers.add", "[2, 3]");   (RAD Hub, JSON text)
#ifndef RADGUI_HPP
#define RADGUI_HPP

#include <initializer_list>
#include <ostream>
#include <stdexcept>
#include <string>
#include <type_traits>
#include <vector>

#include "radgui.h"

namespace rad {

inline void set(const std::string &obj, const std::string &prop, const std::string &value) {
    rad_set(obj.c_str(), prop.c_str(), value.c_str());
}
inline void set(const std::string &obj, const std::string &prop, double value) {
    rad_set_num(obj.c_str(), prop.c_str(), value);
}
inline void set(const std::string &obj, const std::string &prop, int value) {
    rad_set_num(obj.c_str(), prop.c_str(), (double)value);
}
inline std::string get(const std::string &obj, const std::string &prop) { return rad_get(obj.c_str(), prop.c_str()); }
inline double get_num(const std::string &obj, const std::string &prop) { return rad_get_num(obj.c_str(), prop.c_str()); }
inline std::string call(const std::string &obj, const std::string &method, const std::string &args = "") {
    return rad_call(obj.c_str(), method.c_str(), args.c_str());
}
inline void msgbox(const std::string &text) { rad_msgbox(text.c_str()); }
inline std::string input(const std::string &prompt) { return rad_input(prompt.c_str()); }
inline void show(const std::string &form) { rad_show(form.c_str()); }
inline void hide(const std::string &form) { rad_hide(form.c_str()); }
inline void end() { rad_end(); }
inline void print(const std::string &text) { rad_print(text.c_str()); }
inline double num(const std::string &text) { return rad_num(text.c_str()); }
inline std::string str(double x) { return rad_str(x); }
inline std::string arg(int i) { return rad_arg(i); }

// RAD Hub: JSON text of the result; throws std::string on error is avoided - check rad::error()
inline std::string hub(const std::string &name, const std::string &json_args = "[]") {
    return radcall(name.c_str(), json_args.c_str());
}
inline std::string error() { return rad_error(); }

// JSON helpers for workers / hub results
inline double json_num(const std::string &j) { return rad_json_num(j.c_str()); }
inline std::string json_str(const std::string &j) { return rad_json_str(j.c_str()); }
inline std::string json(const std::string &text) { return rad_json_quote(text.c_str()); }
inline std::string json(double x) { return rad_json_numtext(x); }

// ---------------------------------------------------------------- References (Add Reference)
// A JSON value returned by a referenced project's function (see <Lib>.ref.hpp).
//   double x = MathLib::Add(2, 3);          std::string s = MathLib::Hello("Ann").str();
class Value {
public:
    Value() : j_("null") {}
    explicit Value(const std::string &json_text) : j_(json_text.empty() ? "null" : json_text) {}
    const std::string &json() const { return j_; }
    double num() const { return rad_json_num(j_.c_str()); }
    std::string str() const { return is_string() ? std::string(rad_json_str(j_.c_str())) : j_; }
    bool boolean() const { return j_ == "true" || (j_ != "false" && j_ != "null" && j_ != "\"\"" && num() != 0); }
    bool is_null() const { return j_ == "null"; }
    bool is_string() const { return !j_.empty() && j_[0] == '"'; }
    operator double() const { return num(); }
    explicit operator std::string() const { return str(); }
private:
    std::string j_;
};
inline std::ostream &operator<<(std::ostream &os, const Value &v) { return os << v.str(); }

// C++ value -> JSON text (arguments of reference calls)
template <class T>
inline typename std::enable_if<std::is_arithmetic<T>::value && !std::is_same<T, bool>::value, std::string>::type
to_json(T x) { return rad_json_numtext((double)x); }
inline std::string to_json(bool b) { return b ? "true" : "false"; }
inline std::string to_json(const char *s) { return s ? std::string(rad_json_quote(s)) : std::string("null"); }
inline std::string to_json(const std::string &s) { return rad_json_quote(s.c_str()); }
inline std::string to_json(const Value &v) { return v.json(); }
inline std::string to_json(std::nullptr_t) { return "null"; }
template <class T>
inline std::string to_json(const std::vector<T> &v) {
    std::string out = "[";
    for (size_t i = 0; i < v.size(); i++) out += (i ? ", " : "") + to_json(v[i]);
    return out + "]";
}

// Call "<Module>.<function>" through RAD Hub with JSON argument texts; throws on error.
inline Value invoke(const std::string &target, std::initializer_list<std::string> args) {
    std::string a = "[";
    size_t i = 0;
    for (const std::string &s : args) a += (i++ ? ", " : "") + s;
    a += "]";
    const char *r = radcall(target.c_str(), a.c_str());
    if (!r || !*r) throw std::runtime_error(target + ": " + rad_error());
    return Value(r);
}

}  // namespace rad

#endif
