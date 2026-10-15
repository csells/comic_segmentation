//! Control-flow outcomes shared by the converter.

use std::fmt;

#[derive(Debug, Clone, PartialEq)]
pub enum Error {
    /// Budget, account or unknown request state: stop resumably, never certify.
    Blocked(String),
    /// The page reached its optional spend limit: fall back to the whole page.
    PageBudget(String),
    /// A model mapping that references orders or IDs outside its inputs.
    Mapping(String),
    /// Invalid data (Python ValueError/KeyError/TypeError/OSError analogue).
    Value(String),
}

impl Error {
    pub fn message(&self) -> &str {
        match self {
            Error::Blocked(m) | Error::PageBudget(m) | Error::Mapping(m) | Error::Value(m) => m,
        }
    }

    /// Convert data errors to a blocked run with a context prefix; keep control flow.
    pub fn block(self, prefix: &str) -> Error {
        match self {
            Error::Value(m) | Error::Mapping(m) => Error::Blocked(format!("{prefix}{m}")),
            other => other,
        }
    }
}

impl fmt::Display for Error {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        f.write_str(self.message())
    }
}

impl std::error::Error for Error {}

impl From<String> for Error {
    fn from(m: String) -> Self {
        Error::Value(m)
    }
}

impl From<&str> for Error {
    fn from(m: &str) -> Self {
        Error::Value(m.to_string())
    }
}

impl From<std::io::Error> for Error {
    fn from(e: std::io::Error) -> Self {
        Error::Value(e.to_string())
    }
}

impl From<crate::json::ParseError> for Error {
    fn from(e: crate::json::ParseError) -> Self {
        Error::Value(e.0)
    }
}

pub type R<T> = Result<T, Error>;

/// Python `_require(condition, message)`.
pub fn require(condition: bool, message: &str) -> R<()> {
    if condition { Ok(()) } else { Err(Error::Value(message.to_string())) }
}
