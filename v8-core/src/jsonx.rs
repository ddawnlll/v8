//! Python-`json`-compatible tape line parser.
//!
//! The tape is written by Python tooling whose `json.dumps` (default
//! `allow_nan=True`) emits `NaN`, `Infinity` and `-Infinity` as bare literals,
//! and whose `json.loads` accepts them. `serde_json` rejects them as invalid
//! JSON, so a strict parse would fail *before* the oracle's classification
//! (a NaN OHLC must raise "non-finite OHLC", not a generic JSON error).
//!
//! This parser accepts the Python extensions: each non-finite literal is
//! recorded with its JSON path (e.g. `payload.open`) and the slot is emitted
//! as `null` so the caller can still classify it exactly as the oracle does.
//! Finite tapes parse identically to `serde_json`.

use serde_json::Value;

/// One non-finite literal found in a line, with its JSON path so the caller
/// can classify it exactly as `_validate_tape_rows` would.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct NonFinite {
    pub path: String,
    pub kind: &'static str, // "nan" | "inf" | "ninf"
}

pub struct Line {
    pub value: Value,
    pub nonfinite: Vec<NonFinite>,
}

/// Parse one tape line (a complete JSON value). On a structurally invalid
/// line returns `Err(message)`; Python-style non-finite literals are handled
/// per the module docstring.
pub fn parse_line(s: &str) -> Result<Line, String> {
    let mut p = Parser { b: s.as_bytes().to_vec(), i: 0, line: s.to_string(), nonfinite: Vec::new() };
    p.skip_ws();
    let value = p.parse_value(&mut String::new())?;
    p.skip_ws();
    if p.i != p.b.len() {
        return Err(format!("trailing content at column {}", p.i + 1));
    }
    Ok(Line { value, nonfinite: p.nonfinite })
}

struct Parser {
    b: Vec<u8>,
    i: usize,
    line: String,
    nonfinite: Vec<NonFinite>,
}

impl Parser {
    fn skip_ws(&mut self) {
        while self.i < self.b.len() && matches!(self.b[self.i], b' ' | b'\t' | b'\n' | b'\r') {
            self.i += 1;
        }
    }

    fn peek(&self) -> Option<u8> {
        self.b.get(self.i).copied()
    }

    fn parse_value(&mut self, path: &mut String) -> Result<Value, String> {
        self.skip_ws();
        match self.peek() {
            Some(b'{') => self.parse_object(path),
            Some(b'[') => self.parse_array(path),
            Some(b'"') => Ok(Value::String(self.parse_string()?)),
            Some(b't') => self.parse_keyword("true", Value::Bool(true)),
            Some(b'f') => self.parse_keyword("false", Value::Bool(false)),
            Some(b'n') if self.b[self.i..].starts_with(b"null") => {
                self.i += 4;
                Ok(Value::Null)
            }
            // Python's `json.dumps` emits NaN with an uppercase N.
            Some(b'N') if self.b[self.i..].starts_with(b"NaN") => {
                self.i += 3;
                self.record_nonfinite(path, "nan");
                Ok(Value::Null)
            }
            Some(b'I') if self.b[self.i..].starts_with(b"Infinity") => {
                self.i += 8;
                self.record_nonfinite(path, "inf");
                Ok(Value::Null)
            }
            Some(b'-') => {
                // `-Infinity` (Python) vs a negative number.
                if self.b[self.i..].starts_with(b"-Infinity") {
                    self.i += 9;
                    self.record_nonfinite(path, "ninf");
                    Ok(Value::Null)
                } else {
                    self.parse_number()
                }
            }
            Some(c) if c.is_ascii_digit() => self.parse_number(),
            _ => Err(self.err("expected value")),
        }
    }

    fn record_nonfinite(&mut self, path: &str, kind: &'static str) {
        self.nonfinite.push(NonFinite { path: path.to_string(), kind });
    }

    fn parse_keyword(&mut self, kw: &str, v: Value) -> Result<Value, String> {
        if self.b[self.i..].starts_with(kw.as_bytes()) {
            self.i += kw.len();
            Ok(v)
        } else {
            Err(self.err("expected value"))
        }
    }

    fn parse_object(&mut self, path: &mut String) -> Result<Value, String> {
        debug_assert_eq!(self.peek(), Some(b'{'));
        self.i += 1;
        self.skip_ws();
        let mut map = serde_json::Map::new();
        if self.peek() == Some(b'}') {
            self.i += 1;
            return Ok(Value::Object(map));
        }
        loop {
            self.skip_ws();
            if self.peek() != Some(b'"') {
                return Err(self.err("expected string key"));
            }
            let key = self.parse_string()?;
            self.skip_ws();
            if self.peek() != Some(b':') {
                return Err(self.err("expected ':'"));
            }
            self.i += 1;
            let key_path = if path.is_empty() {
                key.clone()
            } else {
                format!("{path}.{key}")
            };
            let v = self.parse_value(&mut key_path.clone())?;
            map.insert(key, v);
            self.skip_ws();
            match self.peek() {
                Some(b',') => {
                    self.i += 1;
                }
                Some(b'}') => {
                    self.i += 1;
                    return Ok(Value::Object(map));
                }
                _ => return Err(self.err("expected ',' or '}'")),
            }
        }
    }

    fn parse_array(&mut self, path: &mut String) -> Result<Value, String> {
        debug_assert_eq!(self.peek(), Some(b'['));
        self.i += 1;
        self.skip_ws();
        let mut arr = Vec::new();
        if self.peek() == Some(b']') {
            self.i += 1;
            return Ok(Value::Array(arr));
        }
        let mut idx = 0usize;
        loop {
            let item_path = format!("{path}[{idx}]");
            arr.push(self.parse_value(&mut item_path.clone())?);
            idx += 1;
            self.skip_ws();
            match self.peek() {
                Some(b',') => {
                    self.i += 1;
                }
                Some(b']') => {
                    self.i += 1;
                    return Ok(Value::Array(arr));
                }
                _ => return Err(self.err("expected ',' or ']'")),
            }
        }
    }

    fn parse_string(&mut self) -> Result<String, String> {
        debug_assert_eq!(self.peek(), Some(b'"'));
        self.i += 1;
        let mut out = Vec::new();
        loop {
            let c = self.peek().ok_or_else(|| self.err("unterminated string"))?;
            match c {
                b'"' => {
                    self.i += 1;
                    return String::from_utf8(out).map_err(|e| e.to_string());
                }
                b'\\' => {
                    self.i += 1;
                    let esc = self.peek().ok_or_else(|| self.err("bad escape"))?;
                    self.i += 1;
                    match esc {
                        b'"' => out.push(b'"'),
                        b'\\' => out.push(b'\\'),
                        b'/' => out.push(b'/'),
                        b'b' => out.push(0x08),
                        b'f' => out.push(0x0c),
                        b'n' => out.push(b'\n'),
                        b'r' => out.push(b'\r'),
                        b't' => out.push(b'\t'),
                        b'u' => {
                            let hex = self.b.get(self.i..self.i + 4).ok_or_else(|| self.err("bad \\u"))?;
                            let cp = u32::from_str_radix(std::str::from_utf8(hex).unwrap(), 16)
                                .map_err(|_| self.err("bad \\u"))?;
                            self.i += 4;
                            // Encode the code point as UTF-8; surrogate pairs
                            // are left as WTF-8 pass-through, matching what
                            // round-trips a Python-written tape byte-for-byte.
                            if let Some(ch) = char::from_u32(cp) {
                                let mut buf = [0u8; 4];
                                out.extend_from_slice(ch.encode_utf8(&mut buf).as_bytes());
                            }
                        }
                        _ => return Err(self.err("bad escape")),
                    }
                }
                c => {
                    out.push(c);
                    self.i += 1;
                }
            }
        }
    }

    fn parse_number(&mut self) -> Result<Value, String> {
        let start = self.i;
        if self.peek() == Some(b'-') {
            self.i += 1;
        }
        while self.i < self.b.len() && self.b[self.i].is_ascii_digit() {
            self.i += 1;
        }
        if self.peek() == Some(b'.') {
            self.i += 1;
            while self.i < self.b.len() && self.b[self.i].is_ascii_digit() {
                self.i += 1;
            }
        }
        if matches!(self.peek(), Some(b'e') | Some(b'E')) {
            self.i += 1;
            if matches!(self.peek(), Some(b'+') | Some(b'-')) {
                self.i += 1;
            }
            while self.i < self.b.len() && self.b[self.i].is_ascii_digit() {
                self.i += 1;
            }
        }
        let text = std::str::from_utf8(&self.b[start..self.i]).unwrap();
        // Mirror CPython json: integers that fit i64 are integers; anything
        // else parses as float (exact round-trip through f64).
        if !text.contains(['.', 'e', 'E']) {
            if let Ok(i) = text.parse::<i64>() {
                return Ok(Value::Number(i.into()));
            }
        }
        let f: f64 = text
            .parse()
            .map_err(|_| self.err("number out of range"))?;
        if !f.is_finite() {
            return Err(self.err("number out of range"));
        }
        serde_json::Number::from_f64(f)
            .map(Value::Number)
            .ok_or_else(|| self.err("number out of range"))
    }

    fn err(&self, msg: &str) -> String {
        format!("{msg} at column {} of: {}", self.i + 1, self.line)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parses_finite_line_identically_to_serde() {
        let line = r#"{"source":"binance-um","channel":"kline","payload":{"open":1.5,"high":2.0,"low":1.0,"close":1.7,"volume":3.25,"closed":true},"event_id":"s:1"}"#;
        let ours = parse_line(line).unwrap();
        let theirs: Value = serde_json::from_str(line).unwrap();
        assert_eq!(ours.value, theirs);
        assert!(ours.nonfinite.is_empty());
    }

    #[test]
    fn records_python_nan_at_path() {
        let line = r#"{"source":"binance-um","channel":"kline","payload":{"open":NaN,"high":2.0,"low":1.0,"close":1.7},"event_id":"s:1"}"#;
        let l = parse_line(line).unwrap();
        assert!(l.nonfinite.iter().any(|n| n.path == "payload.open" && n.kind == "nan"));
    }

    #[test]
    fn records_negative_infinity() {
        let line = r#"{"channel":"funding","payload":{"funding_rate":-Infinity},"event_id":"f1"}"#;
        let l = parse_line(line).unwrap();
        assert!(l.nonfinite.iter().any(|n| n.path == "payload.funding_rate" && n.kind == "ninf"));
    }

    #[test]
    fn rejects_structural_garbage() {
        assert!(parse_line("{not json").is_err());
        assert!(parse_line("").is_err());
    }

    #[test]
    fn large_finite_exponent_ok() {
        let l = parse_line("1e308").unwrap();
        assert_eq!(l.value.as_f64(), Some(1e308));
    }
}
