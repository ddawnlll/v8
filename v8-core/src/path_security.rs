#![allow(dead_code)]

use std::path::{Path, PathBuf};
use crate::error::V8CoreError;

/// Sanitize and validate that a requested path does not escape permissible bounds.
pub fn sanitize_path<P: AsRef<Path>>(untrusted: P) -> Result<PathBuf, V8CoreError> {
    let path = untrusted.as_ref();
    // Rejects empty path
    if path.as_os_str().is_empty() {
        return Err(V8CoreError::PathSanitization("path cannot be empty".into()));
    }

    // Check for obvious path traversal elements if relative
    let components: Vec<_> = path.components().collect();
    let mut depth: isize = 0;
    for c in components {
        match c {
            std::path::Component::ParentDir => {
                depth -= 1;
                if depth < 0 && !path.is_absolute() {
                    return Err(V8CoreError::PathSanitization(format!(
                        "path traversal detected: {:?}",
                        path
                    )));
                }
            }
            std::path::Component::Normal(_) => {
                depth += 1;
            }
            _ => {}
        }
    }

    Ok(path.to_path_buf())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_valid_paths() {
        assert!(sanitize_path("data/test.tape").is_ok());
        assert!(sanitize_path("./artifacts/receipt.json").is_ok());
    }

    #[test]
    fn test_traversal_detection() {
        assert!(sanitize_path("../../etc/passwd").is_err());
        assert!(sanitize_path("foo/../../../bar").is_err());
    }
}
