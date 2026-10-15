//! Durable spending ledger (integer micro-USD), compatible with the prototype's
//! `gemini_budget.Budget` JSONL format so both implementations share one cache.

use crate::contract;
use crate::json::{self, Value};
use crate::obj;
use indexmap::IndexMap;
use std::fs::File;
use std::io::{Read, Seek, SeekFrom, Write};
use std::os::fd::AsRawFd;
use std::path::{Path, PathBuf};

pub const RESERVE: i64 = 300000;

pub struct Budget {
    pub path: PathBuf,
    pub cap: i64,
    file: File,
    pub entries: IndexMap<String, Value>,
    /// Cache-only replay: never append, never reserve.
    pub offline: bool,
}

impl Budget {
    /// Open with an exclusive lock (shared and read-only when offline).
    pub fn open(path: &Path, cap: i64, offline: bool) -> Result<Budget, String> {
        let file = if offline {
            File::open(path).map_err(|e| format!("{}: {e}", path.display()))?
        } else {
            if let Some(parent) = path.parent() {
                std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
            }
            std::fs::OpenOptions::new().read(true).append(true).create(true).open(path).map_err(|e| e.to_string())?
        };
        let op = if offline { libc::LOCK_SH } else { libc::LOCK_EX } | libc::LOCK_NB;
        if unsafe { libc::flock(file.as_raw_fd(), op) } != 0 {
            return Err(format!("ledger is locked by another run: {}", path.display()));
        }
        let mut budget = Budget { path: path.to_path_buf(), cap, file, entries: IndexMap::new(), offline };
        let mut text = String::new();
        budget.file.seek(SeekFrom::Start(0)).map_err(|e| e.to_string())?;
        budget.file.read_to_string(&mut text).map_err(|e| e.to_string())?;
        let rows: Vec<Value> = text.lines().filter(|l| !l.is_empty()).map(|l| json::loads(l).map_err(|e| e.0)).collect::<Result<_, _>>()?;
        if rows.is_empty() {
            if offline {
                return Err("offline replay needs an existing ledger".into());
            }
            budget.append(&obj! {"kind" => "policy", "cap" => cap, "reserve" => RESERVE,
                "input_per_million_usd" => 0.75, "output_per_million_usd" => 3.75})?;
        } else if rows[0].opt("reserve") != &Value::Int(RESERVE) {
            return Err("existing budget policy differs".into());
        }
        let mut effective = if rows.is_empty() { cap } else { rows[0].opt("cap").as_int().unwrap_or(-1) };
        for row in rows.iter().skip(1) {
            match row.opt("kind").as_str() {
                Some("reserve") => {
                    let id = row.opt("id").as_str().unwrap_or("").to_string();
                    if budget.entries.contains_key(&id) {
                        return Err("corrupt duplicate reservation".into());
                    }
                    budget.entries.insert(id, row.clone());
                }
                Some("settle") => {
                    let id = row.opt("id").as_str().unwrap_or("");
                    let entry = budget.entries.get_mut(id).ok_or_else(|| format!("'{id}'"))?;
                    entry.set("cost", row.opt("cost").clone());
                }
                Some("approved_cap_change") => effective = row.opt("cap").as_int().unwrap_or(-1),
                _ => {}
            }
        }
        if effective != cap {
            return Err("existing budget cap differs; explicit approval amendment required".into());
        }
        Ok(budget)
    }

    pub fn append(&mut self, event: &Value) -> Result<(), String> {
        if self.offline {
            return Err("CACHE_ONLY_MISS: ledger writes disabled".into());
        }
        let line = json::dumps(event) + "\n";
        self.file.write_all(line.as_bytes()).map_err(|e| e.to_string())?;
        self.file.flush().map_err(|e| e.to_string())?;
        self.file.sync_all().map_err(|e| e.to_string())
    }

    pub fn used(&self) -> i64 {
        self.entries.values().map(|r| r.opt("cost").as_int().unwrap_or(0)).sum()
    }

    pub fn approve_cap(&mut self, new_cap: i64, reason: &str) -> Result<(), String> {
        if new_cap < self.used() || reason.is_empty() {
            return Err("invalid cap amendment".into());
        }
        self.append(&obj! {"kind" => "approved_cap_change", "cap" => new_cap, "reason" => reason})?;
        self.cap = new_cap;
        Ok(())
    }

    pub fn reserve(&mut self, identity: &str, path: &str, reservation: i64, input_rate: Value, output_rate: Value) -> Result<(), String> {
        if self.offline {
            return Err("CACHE_ONLY_MISS: reservations disabled".into());
        }
        if self.entries.contains_key(identity) {
            return Err("request already reserved; inspect/reuse its saved result".into());
        }
        if reservation <= 0 || input_rate.as_f64().unwrap_or(0.0) <= 0.0 || output_rate.as_f64().unwrap_or(0.0) <= 0.0 {
            return Err("invalid reservation or rates".into());
        }
        if self.used() + reservation > self.cap {
            return Err("spending cap reached; no request sent".into());
        }
        let event = obj! {"kind" => "reserve", "id" => identity, "path" => path, "cost" => reservation,
            "reservation" => reservation, "input_rate" => input_rate, "output_rate" => output_rate};
        self.append(&event)?;
        self.entries.insert(identity.to_string(), event);
        Ok(())
    }

    pub fn settle(&mut self, identity: &str, usage: &Value) -> Result<(), String> {
        let row = self.entries.get(identity).ok_or_else(|| format!("'{identity}'"))?.clone();
        let input = row.get("input_rate").cloned().unwrap_or(Value::Float(0.75));
        let output = row.get("output_rate").cloned().unwrap_or(Value::Float(3.75));
        let Some(cost) = contract::usage_cost(usage, &input, &output)? else { return Ok(()) };
        if cost > row.get("reservation").and_then(Value::as_int).unwrap_or(RESERVE) {
            return Err("usage exceeded reservation; stop and investigate".into());
        }
        self.append(&obj! {"kind" => "settle", "id" => identity, "cost" => cost, "usage" => usage.clone()})?;
        self.entries.get_mut(identity).unwrap().set("cost", cost);
        Ok(())
    }
}
