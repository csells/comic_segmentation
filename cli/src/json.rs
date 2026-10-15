//! Insertion-ordered JSON values with Python `json` module semantics.
//!
//! Request identities, cache keys and durable records are SHA-256 digests of
//! `json.dumps` output, so serialization must match CPython byte for byte:
//! insertion order (or `sort_keys`), `float.__repr__`, `ensure_ascii` escapes
//! and the exact separators of each call site.

use indexmap::IndexMap;
use std::fmt::Write as _;

pub type Map = IndexMap<String, Value>;

#[derive(Clone, Debug, Default)]
pub enum Value {
    #[default]
    Null,
    Bool(bool),
    Int(i64),
    Float(f64),
    Str(String),
    Array(Vec<Value>),
    Object(Map),
}

impl PartialEq for Value {
    /// Python equality: `1 == 1.0` and `True == 1`; dict equality ignores order.
    fn eq(&self, other: &Self) -> bool {
        use Value::*;
        match (self, other) {
            (Null, Null) => true,
            (Str(a), Str(b)) => a == b,
            (Array(a), Array(b)) => a == b,
            (Object(a), Object(b)) => a.len() == b.len() && a.iter().all(|(k, v)| b.get(k) == Some(v)),
            _ => match (self.as_number(), other.as_number()) {
                (Some(a), Some(b)) => a == b,
                _ => false,
            },
        }
    }
}


impl Value {
    fn as_number(&self) -> Option<f64> {
        match self {
            Value::Bool(b) => Some(*b as i64 as f64),
            Value::Int(i) => Some(*i as f64),
            Value::Float(f) => Some(*f),
            _ => None,
        }
    }

    pub fn object() -> Value {
        Value::Object(Map::new())
    }

    pub fn get(&self, key: &str) -> Option<&Value> {
        match self {
            Value::Object(m) => m.get(key),
            _ => None,
        }
    }

    pub fn get_mut(&mut self, key: &str) -> Option<&mut Value> {
        match self {
            Value::Object(m) => m.get_mut(key),
            _ => None,
        }
    }

    /// Python `d.get(key)` treating a missing key and `None` alike.
    pub fn opt(&self, key: &str) -> &Value {
        static NULL: Value = Value::Null;
        self.get(key).unwrap_or(&NULL)
    }

    pub fn contains(&self, key: &str) -> bool {
        matches!(self, Value::Object(m) if m.contains_key(key))
    }

    /// Insert or replace, keeping an existing key's position (Python dict semantics).
    pub fn set(&mut self, key: &str, value: impl Into<Value>) {
        if let Value::Object(m) = self {
            m.insert(key.to_string(), value.into());
        } else {
            panic!("set on non-object");
        }
    }

    pub fn remove(&mut self, key: &str) -> Option<Value> {
        match self {
            Value::Object(m) => m.shift_remove(key),
            _ => None,
        }
    }

    pub fn as_object(&self) -> Option<&Map> {
        match self {
            Value::Object(m) => Some(m),
            _ => None,
        }
    }
    pub fn as_object_mut(&mut self) -> Option<&mut Map> {
        match self {
            Value::Object(m) => Some(m),
            _ => None,
        }
    }
    pub fn as_array(&self) -> Option<&Vec<Value>> {
        match self {
            Value::Array(a) => Some(a),
            _ => None,
        }
    }
    pub fn as_array_mut(&mut self) -> Option<&mut Vec<Value>> {
        match self {
            Value::Array(a) => Some(a),
            _ => None,
        }
    }
    pub fn as_str(&self) -> Option<&str> {
        match self {
            Value::Str(s) => Some(s),
            _ => None,
        }
    }
    /// Python `type(x) is int` (bools excluded).
    pub fn as_int(&self) -> Option<i64> {
        match self {
            Value::Int(i) => Some(*i),
            _ => None,
        }
    }
    pub fn as_bool(&self) -> Option<bool> {
        match self {
            Value::Bool(b) => Some(*b),
            _ => None,
        }
    }
    /// `int` or `float` (bools excluded), as used by probability checks.
    pub fn as_f64(&self) -> Option<f64> {
        match self {
            Value::Int(i) => Some(*i as f64),
            Value::Float(f) => Some(*f),
            _ => None,
        }
    }
    pub fn is_null(&self) -> bool {
        matches!(self, Value::Null)
    }
    pub fn is_object(&self) -> bool {
        matches!(self, Value::Object(_))
    }
    pub fn is_array(&self) -> bool {
        matches!(self, Value::Array(_))
    }
    pub fn is_str(&self) -> bool {
        matches!(self, Value::Str(_))
    }

    /// Python truthiness.
    pub fn truthy(&self) -> bool {
        match self {
            Value::Null => false,
            Value::Bool(b) => *b,
            Value::Int(i) => *i != 0,
            Value::Float(f) => *f != 0.0,
            Value::Str(s) => !s.is_empty(),
            Value::Array(a) => !a.is_empty(),
            Value::Object(m) => !m.is_empty(),
        }
    }

    /// Shallow merge like `{**self, **other}`.
    pub fn merged(&self, other: &Value) -> Value {
        let mut out = self.clone();
        if let (Value::Object(m), Value::Object(o)) = (&mut out, other) {
            for (k, v) in o {
                m.insert(k.clone(), v.clone());
            }
        }
        out
    }

    /// Return a copy with `key` set (`{**self, key: value}`).
    pub fn with(&self, key: &str, value: impl Into<Value>) -> Value {
        let mut out = self.clone();
        out.set(key, value);
        out
    }

    /// `{k: self[k] for k in keys}`; missing keys are an error.
    pub fn pick(&self, keys: &[&str]) -> Result<Value, String> {
        let mut m = Map::new();
        for k in keys {
            m.insert(k.to_string(), self.get(k).ok_or_else(|| format!("'{k}'"))?.clone());
        }
        Ok(Value::Object(m))
    }
}

impl From<bool> for Value {
    fn from(v: bool) -> Self {
        Value::Bool(v)
    }
}
impl From<i64> for Value {
    fn from(v: i64) -> Self {
        Value::Int(v)
    }
}
impl From<i32> for Value {
    fn from(v: i32) -> Self {
        Value::Int(v as i64)
    }
}
impl From<u32> for Value {
    fn from(v: u32) -> Self {
        Value::Int(v as i64)
    }
}
impl From<usize> for Value {
    fn from(v: usize) -> Self {
        Value::Int(v as i64)
    }
}
impl From<f64> for Value {
    fn from(v: f64) -> Self {
        Value::Float(v)
    }
}
impl From<&str> for Value {
    fn from(v: &str) -> Self {
        Value::Str(v.to_string())
    }
}
impl From<String> for Value {
    fn from(v: String) -> Self {
        Value::Str(v)
    }
}
impl From<&String> for Value {
    fn from(v: &String) -> Self {
        Value::Str(v.clone())
    }
}
impl From<Map> for Value {
    fn from(v: Map) -> Self {
        Value::Object(v)
    }
}
impl<T: Into<Value>> From<Vec<T>> for Value {
    fn from(v: Vec<T>) -> Self {
        Value::Array(v.into_iter().map(Into::into).collect())
    }
}
impl<T: Into<Value>> From<Option<T>> for Value {
    fn from(v: Option<T>) -> Self {
        v.map(Into::into).unwrap_or(Value::Null)
    }
}
impl From<&Value> for Value {
    fn from(v: &Value) -> Self {
        v.clone()
    }
}

/// Build an ordered object: `obj! { "a" => 1, "b" => "x" }`.
#[macro_export]
macro_rules! obj {
    () => { $crate::json::Value::Object($crate::json::Map::new()) };
    ($($k:expr => $v:expr),+ $(,)?) => {{
        let mut m = $crate::json::Map::new();
        $( m.insert(($k).to_string(), $crate::json::Value::from($v)); )+
        $crate::json::Value::Object(m)
    }};
}

/// Build an array of heterogeneous values: `arr![1, "x", obj!{}]`.
#[macro_export]
macro_rules! arr {
    () => { $crate::json::Value::Array(Vec::new()) };
    ($($v:expr),+ $(,)?) => { $crate::json::Value::Array(vec![$($crate::json::Value::from($v)),+]) };
}

// ---------------------------------------------------------------- serialization

#[derive(Clone, Copy)]
pub struct Style {
    pub sort_keys: bool,
    pub indent: Option<usize>,
    pub item_sep: &'static str,
    pub key_sep: &'static str,
}

/// `json.dumps(v)`
pub const DEFAULT: Style = Style { sort_keys: false, indent: None, item_sep: ", ", key_sep: ": " };
/// `json.dumps(v, sort_keys=True)`
pub const SORTED: Style = Style { sort_keys: true, indent: None, item_sep: ", ", key_sep: ": " };
/// `json.dumps(v, sort_keys=True, separators=(',', ':'))`
pub const SORTED_COMPACT: Style = Style { sort_keys: true, indent: None, item_sep: ",", key_sep: ":" };
/// `json.dumps(v, indent=2)`
pub const INDENT2: Style = Style { sort_keys: false, indent: Some(2), item_sep: ",", key_sep: ": " };

pub fn dumps_with(v: &Value, style: Style) -> String {
    let mut out = String::new();
    write_value(&mut out, v, style, 0);
    out
}

pub fn dumps(v: &Value) -> String {
    dumps_with(v, DEFAULT)
}

pub fn dumps_sorted(v: &Value) -> String {
    dumps_with(v, SORTED)
}

pub fn dumps_indent(v: &Value) -> String {
    dumps_with(v, INDENT2)
}

fn newline(out: &mut String, style: Style, level: usize) {
    if let Some(n) = style.indent {
        out.push('\n');
        for _ in 0..n * level {
            out.push(' ');
        }
    }
}

fn write_value(out: &mut String, v: &Value, style: Style, level: usize) {
    match v {
        Value::Null => out.push_str("null"),
        Value::Bool(true) => out.push_str("true"),
        Value::Bool(false) => out.push_str("false"),
        Value::Int(i) => {
            let _ = write!(out, "{i}");
        }
        Value::Float(f) => out.push_str(&float_repr(*f)),
        Value::Str(s) => write_str(out, s),
        Value::Array(a) => {
            if a.is_empty() {
                out.push_str("[]");
                return;
            }
            out.push('[');
            for (i, item) in a.iter().enumerate() {
                if i > 0 {
                    out.push_str(style.item_sep);
                }
                newline(out, style, level + 1);
                write_value(out, item, style, level + 1);
            }
            newline(out, style, level);
            out.push(']');
        }
        Value::Object(m) => {
            if m.is_empty() {
                out.push_str("{}");
                return;
            }
            out.push('{');
            let mut entries: Vec<(&String, &Value)> = m.iter().collect();
            if style.sort_keys {
                entries.sort_by(|a, b| a.0.cmp(b.0));
            }
            for (i, (k, item)) in entries.into_iter().enumerate() {
                if i > 0 {
                    out.push_str(style.item_sep);
                }
                newline(out, style, level + 1);
                write_str(out, k);
                out.push_str(style.key_sep);
                write_value(out, item, style, level + 1);
            }
            newline(out, style, level);
            out.push('}');
        }
    }
}

/// `json.encoder.py_encode_basestring_ascii`.
pub fn write_str(out: &mut String, s: &str) {
    out.push('"');
    for c in s.chars() {
        match c {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            '\u{8}' => out.push_str("\\b"),
            '\u{c}' => out.push_str("\\f"),
            ' '..='~' => out.push(c),
            _ => {
                let code = c as u32;
                if code >= 0x10000 {
                    let v = code - 0x10000;
                    let _ = write!(out, "\\u{:04x}\\u{:04x}", 0xd800 | ((v >> 10) & 0x3ff), 0xdc00 | (v & 0x3ff));
                } else {
                    let _ = write!(out, "\\u{code:04x}");
                }
            }
        }
    }
    out.push('"');
}

/// CPython `float.__repr__` (shortest round-trip digits, `repr` style switching).
pub fn float_repr(f: f64) -> String {
    if f.is_nan() {
        return "NaN".into();
    }
    if f.is_infinite() {
        return if f > 0.0 { "Infinity".into() } else { "-Infinity".into() };
    }
    if f == 0.0 {
        return if f.is_sign_negative() { "-0.0".into() } else { "0.0".into() };
    }
    // Rust's `{:e}` yields the shortest round-trip digits: d.ddddde<exp>.
    let sci = format!("{:e}", f.abs());
    let (mantissa, exp) = sci.split_once('e').unwrap();
    let exp: i32 = exp.parse().unwrap();
    let digits: String = mantissa.chars().filter(|c| *c != '.').collect();
    let decpt = exp + 1; // position of the decimal point relative to the digit string
    let mut out = String::new();
    if f < 0.0 {
        out.push('-');
    }
    if -4 < decpt && decpt <= 16 {
        if decpt <= 0 {
            out.push_str("0.");
            for _ in 0..(-decpt) {
                out.push('0');
            }
            out.push_str(&digits);
        } else if (decpt as usize) >= digits.len() {
            out.push_str(&digits);
            for _ in 0..(decpt as usize - digits.len()) {
                out.push('0');
            }
            out.push_str(".0");
        } else {
            out.push_str(&digits[..decpt as usize]);
            out.push('.');
            out.push_str(&digits[decpt as usize..]);
        }
    } else {
        out.push_str(&digits[..1]);
        if digits.len() > 1 {
            out.push('.');
            out.push_str(&digits[1..]);
        }
        let e = decpt - 1;
        let _ = write!(out, "e{}{:02}", if e < 0 { '-' } else { '+' }, e.abs());
    }
    out
}

// ---------------------------------------------------------------- parsing

#[derive(Debug, Clone, PartialEq)]
pub struct ParseError(pub String);

impl std::fmt::Display for ParseError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        f.write_str(&self.0)
    }
}

/// `json.loads(text)`: later duplicate keys replace earlier ones in place.
pub fn loads(text: &str) -> Result<Value, ParseError> {
    parse(text, false)
}

/// `json.loads(text, object_pairs_hook=unique)` rejecting duplicate keys.
pub fn loads_unique(text: &str) -> Result<Value, ParseError> {
    parse(text, true)
}

fn parse(text: &str, unique: bool) -> Result<Value, ParseError> {
    let mut p = Parser { s: text.as_bytes(), i: 0, unique, text };
    p.ws();
    let v = p.value()?;
    p.ws();
    if p.i != p.s.len() {
        return Err(p.err("Extra data"));
    }
    Ok(v)
}

struct Parser<'a> {
    s: &'a [u8],
    i: usize,
    unique: bool,
    text: &'a str,
}

impl Parser<'_> {
    fn err(&self, msg: &str) -> ParseError {
        // Mirror CPython's "msg: line L column C (char P)" with character offsets.
        let consumed = &self.text[..self.i.min(self.text.len())];
        let pos = consumed.chars().count();
        let line = consumed.matches('\n').count() + 1;
        let col = match consumed.rfind('\n') {
            Some(n) => consumed[n + 1..].chars().count() + 1,
            None => pos + 1,
        };
        ParseError(format!("{msg}: line {line} column {col} (char {pos})"))
    }

    fn ws(&mut self) {
        while self.i < self.s.len() && matches!(self.s[self.i], b' ' | b'\t' | b'\n' | b'\r') {
            self.i += 1;
        }
    }

    fn value(&mut self) -> Result<Value, ParseError> {
        match self.s.get(self.i) {
            Some(b'{') => self.object(),
            Some(b'[') => self.array(),
            Some(b'"') => Ok(Value::Str(self.string()?)),
            Some(b't') if self.s[self.i..].starts_with(b"true") => {
                self.i += 4;
                Ok(Value::Bool(true))
            }
            Some(b'f') if self.s[self.i..].starts_with(b"false") => {
                self.i += 5;
                Ok(Value::Bool(false))
            }
            Some(b'n') if self.s[self.i..].starts_with(b"null") => {
                self.i += 4;
                Ok(Value::Null)
            }
            Some(b'N') if self.s[self.i..].starts_with(b"NaN") => {
                self.i += 3;
                Ok(Value::Float(f64::NAN))
            }
            Some(b'I') if self.s[self.i..].starts_with(b"Infinity") => {
                self.i += 8;
                Ok(Value::Float(f64::INFINITY))
            }
            Some(b'-') if self.s[self.i..].starts_with(b"-Infinity") => {
                self.i += 9;
                Ok(Value::Float(f64::NEG_INFINITY))
            }
            Some(c) if *c == b'-' || c.is_ascii_digit() => self.number(),
            _ => Err(self.err("Expecting value")),
        }
    }

    fn number(&mut self) -> Result<Value, ParseError> {
        let start = self.i;
        if self.s[self.i] == b'-' {
            self.i += 1;
        }
        let int_start = self.i;
        if self.s.get(self.i) == Some(&b'0') {
            self.i += 1;
        } else if self.s.get(self.i).is_some_and(|c| c.is_ascii_digit()) {
            while self.s.get(self.i).is_some_and(|c| c.is_ascii_digit()) {
                self.i += 1;
            }
        } else {
            self.i = start;
            return Err(self.err("Expecting value"));
        }
        let _ = int_start;
        let mut is_float = false;
        if self.s.get(self.i) == Some(&b'.') && self.s.get(self.i + 1).is_some_and(|c| c.is_ascii_digit()) {
            is_float = true;
            self.i += 1;
            while self.s.get(self.i).is_some_and(|c| c.is_ascii_digit()) {
                self.i += 1;
            }
        }
        if matches!(self.s.get(self.i), Some(b'e') | Some(b'E')) {
            let save = self.i;
            self.i += 1;
            if matches!(self.s.get(self.i), Some(b'+') | Some(b'-')) {
                self.i += 1;
            }
            if self.s.get(self.i).is_some_and(|c| c.is_ascii_digit()) {
                is_float = true;
                while self.s.get(self.i).is_some_and(|c| c.is_ascii_digit()) {
                    self.i += 1;
                }
            } else {
                self.i = save;
            }
        }
        let text = std::str::from_utf8(&self.s[start..self.i]).unwrap();
        if is_float {
            Ok(Value::Float(text.parse().map_err(|_| self.err("Expecting value"))?))
        } else {
            match text.parse::<i64>() {
                Ok(i) => Ok(Value::Int(i)),
                Err(_) => Ok(Value::Float(text.parse().map_err(|_| self.err("Expecting value"))?)),
            }
        }
    }

    fn string(&mut self) -> Result<String, ParseError> {
        let open = self.i;
        self.i += 1;
        let mut out = String::new();
        loop {
            let Some(&c) = self.s.get(self.i) else {
                self.i = open;
                return Err(self.err("Unterminated string starting at"));
            };
            match c {
                b'"' => {
                    self.i += 1;
                    return Ok(out);
                }
                b'\\' => {
                    let esc = *self.s.get(self.i + 1).ok_or_else(|| self.err("Unterminated string starting at"))?;
                    self.i += 2;
                    match esc {
                        b'"' => out.push('"'),
                        b'\\' => out.push('\\'),
                        b'/' => out.push('/'),
                        b'b' => out.push('\u{8}'),
                        b'f' => out.push('\u{c}'),
                        b'n' => out.push('\n'),
                        b'r' => out.push('\r'),
                        b't' => out.push('\t'),
                        b'u' => {
                            let mut code = self.hex4()?;
                            if (0xd800..0xdc00).contains(&code)
                                && self.s.get(self.i) == Some(&b'\\')
                                && self.s.get(self.i + 1) == Some(&b'u')
                            {
                                let save = self.i;
                                self.i += 2;
                                let low = self.hex4()?;
                                if (0xdc00..0xe000).contains(&low) {
                                    code = 0x10000 + ((code - 0xd800) << 10) + (low - 0xdc00);
                                } else {
                                    self.i = save;
                                }
                            }
                            out.push(char::from_u32(code).unwrap_or('\u{fffd}'));
                        }
                        _ => {
                            self.i -= 1;
                            return Err(self.err("Invalid \\escape"));
                        }
                    }
                }
                c if c < 0x20 => return Err(self.err("Invalid control character at")),
                _ => {
                    // Copy one UTF-8 scalar.
                    let rest = &self.text[self.i..];
                    let ch = rest.chars().next().unwrap();
                    out.push(ch);
                    self.i += ch.len_utf8();
                }
            }
        }
    }

    fn hex4(&mut self) -> Result<u32, ParseError> {
        let h = self.s.get(self.i..self.i + 4).ok_or_else(|| self.err("Invalid \\uXXXX escape"))?;
        let v = u32::from_str_radix(std::str::from_utf8(h).unwrap_or("x"), 16)
            .map_err(|_| self.err("Invalid \\uXXXX escape"))?;
        self.i += 4;
        Ok(v)
    }

    fn array(&mut self) -> Result<Value, ParseError> {
        self.i += 1;
        let mut out = Vec::new();
        self.ws();
        if self.s.get(self.i) == Some(&b']') {
            self.i += 1;
            return Ok(Value::Array(out));
        }
        loop {
            self.ws();
            out.push(self.value()?);
            self.ws();
            match self.s.get(self.i) {
                Some(b',') => self.i += 1,
                Some(b']') => {
                    self.i += 1;
                    return Ok(Value::Array(out));
                }
                _ => return Err(self.err("Expecting ',' delimiter")),
            }
        }
    }

    fn object(&mut self) -> Result<Value, ParseError> {
        self.i += 1;
        let mut out = Map::new();
        self.ws();
        if self.s.get(self.i) == Some(&b'}') {
            self.i += 1;
            return Ok(Value::Object(out));
        }
        loop {
            self.ws();
            if self.s.get(self.i) != Some(&b'"') {
                return Err(self.err("Expecting property name enclosed in double quotes"));
            }
            let key = self.string()?;
            self.ws();
            if self.s.get(self.i) != Some(&b':') {
                return Err(self.err("Expecting ':' delimiter"));
            }
            self.i += 1;
            self.ws();
            let v = self.value()?;
            if self.unique && out.contains_key(&key) {
                return Err(ParseError("Duplicate JSON key".into()));
            }
            out.insert(key, v);
            self.ws();
            match self.s.get(self.i) {
                Some(b',') => self.i += 1,
                Some(b'}') => {
                    self.i += 1;
                    return Ok(Value::Object(out));
                }
                _ => return Err(self.err("Expecting ',' delimiter")),
            }
        }
    }
}

/// Python `repr()` of a list of ints, e.g. `[1, 2, 3]`.
pub fn py_int_list(values: &[i64]) -> String {
    let parts: Vec<String> = values.iter().map(|v| v.to_string()).collect();
    format!("[{}]", parts.join(", "))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn float_repr_matches_cpython() {
        let cases = [
            (0.5, "0.5"),
            (1.0, "1.0"),
            (1e-5, "1e-05"),
            (0.0001, "0.0001"),
            (1e16, "1e+16"),
            (1234567890123456.0, "1234567890123456.0"),
            (0.1 + 0.2, "0.30000000000000004"),
            (123.456, "123.456"),
            (-2.5e-7, "-2.5e-07"),
            (0.9876, "0.9876"),
            (1e22, "1e+22"),
            (100.0, "100.0"),
        ];
        for (f, want) in cases {
            assert_eq!(float_repr(f), want, "{f}");
        }
    }

    #[test]
    fn ascii_escapes_match_cpython() {
        // CPython: json.dumps('a"b\\c\n\x7f\u00e9\u2014\U0001F600')
        let v = Value::Str("a\"b\\c\n\u{7f}\u{e9}\u{2014}\u{1F600}".into());
        assert_eq!(dumps(&v), "\"a\\\"b\\\\c\\n\\u007f\\u00e9\\u2014\\ud83d\\ude00\"");
    }

    #[test]
    fn separators_and_indent() {
        let v = obj! {"b" => 1, "a" => arr![1, 2.5], "c" => obj!{}, "d" => arr![]};
        assert_eq!(dumps(&v), r#"{"b": 1, "a": [1, 2.5], "c": {}, "d": []}"#);
        assert_eq!(dumps_sorted(&v), r#"{"a": [1, 2.5], "b": 1, "c": {}, "d": []}"#);
        assert_eq!(dumps_with(&v, SORTED_COMPACT), r#"{"a":[1,2.5],"b":1,"c":{},"d":[]}"#);
        assert_eq!(dumps_indent(&v), "{\n  \"b\": 1,\n  \"a\": [\n    1,\n    2.5\n  ],\n  \"c\": {},\n  \"d\": []\n}");
    }

    #[test]
    fn parse_preserves_order_and_number_kinds() {
        let v = loads("{\"z\": 1, \"a\": 1.0, \"m\": [true, null, \"\\u00e9\\ud83d\\ude00\"], \"z\": 2}").unwrap();
        assert_eq!(dumps(&v), "{\"z\": 2, \"a\": 1.0, \"m\": [true, null, \"\\u00e9\\ud83d\\ude00\"]}");
        assert!(loads_unique("{\"a\":1,\"a\":2}").is_err());
        assert_eq!(loads("[").unwrap_err().0, "Expecting value: line 1 column 2 (char 1)");
    }

    #[test]
    fn python_equality() {
        assert_eq!(Value::Int(1), Value::Float(1.0));
        assert_eq!(Value::Bool(true), Value::Int(1));
        assert_eq!(obj! {"a" => 1, "b" => 2}, obj! {"b" => 2, "a" => 1});
        assert_ne!(arr![1, 2], arr![2, 1]);
    }
}
