#![allow(dead_code)]

use std::path::Path;
use serde::{Deserialize, Serialize};
use crate::error::V8CoreError;

/// Header metadata for state checkpoint.
#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CheckpointHeader {
    pub version: u32,
    pub timestamp: i64,
    pub bar_index: usize,
    pub tape_hash: String,
}

/// A serialized snapshot of the simulation runloop state.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SimulationCheckpoint {
    pub header: CheckpointHeader,
    pub payload_bytes: Vec<u8>,
}

impl SimulationCheckpoint {
    pub fn new(bar_index: usize, tape_hash: String, payload: Vec<u8>) -> Self {
        Self {
            header: CheckpointHeader {
                version: 1,
                timestamp: std::time::SystemTime::now()
                    .duration_since(std::time::UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_secs() as i64,
                bar_index,
                tape_hash,
            },
            payload_bytes: payload,
        }
    }

    /// Save snapshot atomically to disk using binary encoding.
    pub fn save_to_file<P: AsRef<Path>>(&self, path: P) -> Result<(), V8CoreError> {
        let path = path.as_ref();
        let tmp_path = path.with_extension("tmp");
        let bytes = bincode::serialize(self)
            .map_err(|e| V8CoreError::Checkpoint(format!("serialize failed: {e}")))?;
        std::fs::write(&tmp_path, bytes)
            .map_err(|e| V8CoreError::Checkpoint(format!("write tmp failed: {e}")))?;
        std::fs::rename(&tmp_path, path)
            .map_err(|e| V8CoreError::Checkpoint(format!("rename failed: {e}")))?;
        Ok(())
    }

    /// Load snapshot from disk.
    pub fn load_from_file<P: AsRef<Path>>(path: P) -> Result<Self, V8CoreError> {
        let bytes = std::fs::read(path)
            .map_err(|e| V8CoreError::Checkpoint(format!("read file failed: {e}")))?;
        bincode::deserialize(&bytes)
            .map_err(|e| V8CoreError::Checkpoint(format!("deserialize failed: {e}")))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_checkpoint_roundtrip() {
        let cp = SimulationCheckpoint::new(100, "abc123hash".into(), vec![1, 2, 3, 4, 5]);
        let tmp_file = std::env::temp_dir().join("test_checkpoint.chk");
        cp.save_to_file(&tmp_file).unwrap();

        let loaded = SimulationCheckpoint::load_from_file(&tmp_file).unwrap();
        assert_eq!(loaded.header.bar_index, 100);
        assert_eq!(loaded.header.tape_hash, "abc123hash");
        assert_eq!(loaded.payload_bytes, vec![1, 2, 3, 4, 5]);
        let _ = std::fs::remove_file(tmp_file);
    }
}
