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

pub const CHECKPOINT_VERSION: u32 = 1;

impl SimulationCheckpoint {
    pub fn new(bar_index: usize, tape_hash: String, payload: Vec<u8>) -> Self {
        Self {
            header: CheckpointHeader {
                version: CHECKPOINT_VERSION,
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
        if self.header.version != CHECKPOINT_VERSION {
            return Err(V8CoreError::Checkpoint(format!(
                "unsupported checkpoint version {}",
                self.header.version
            )));
        }
        let parent = path.parent().unwrap_or_else(|| Path::new("."));
        std::fs::create_dir_all(parent)
            .map_err(|e| V8CoreError::Checkpoint(format!("create checkpoint directory: {e}")))?;
        let tmp_path = parent.join(format!(
            ".{}.tmp-{}",
            path.file_name().and_then(|n| n.to_str()).unwrap_or("checkpoint"),
            std::process::id()
        ));
        let bytes = bincode::serialize(self)
            .map_err(|e| V8CoreError::Checkpoint(format!("serialize failed: {e}")))?;
        let mut file = std::fs::OpenOptions::new()
            .create(true)
            .truncate(true)
            .write(true)
            .open(&tmp_path)
            .map_err(|e| V8CoreError::Checkpoint(format!("open tmp failed: {e}")))?;
        use std::io::Write;
        file.write_all(&bytes)
            .map_err(|e| V8CoreError::Checkpoint(format!("write tmp failed: {e}")))?;
        file.sync_all()
            .map_err(|e| V8CoreError::Checkpoint(format!("sync tmp failed: {e}")))?;
        std::fs::rename(&tmp_path, path)
            .map_err(|e| V8CoreError::Checkpoint(format!("rename failed: {e}")))?;
        sync_directory(parent)?;
        Ok(())
    }

    /// Load snapshot from disk.
    pub fn load_from_file<P: AsRef<Path>>(path: P) -> Result<Self, V8CoreError> {
        let bytes = std::fs::read(path)
            .map_err(|e| V8CoreError::Checkpoint(format!("read file failed: {e}")))?;
        let checkpoint: Self = bincode::deserialize(&bytes)
            .map_err(|e| V8CoreError::Checkpoint(format!("deserialize failed: {e}")))?;
        if checkpoint.header.version != CHECKPOINT_VERSION {
            return Err(V8CoreError::Checkpoint(format!(
                "unsupported checkpoint version {}",
                checkpoint.header.version
            )));
        }
        Ok(checkpoint)
    }

    /// Load only when the persisted checkpoint belongs to the requested tape.
    pub fn load_for_tape<P: AsRef<Path>>(
        path: P,
        expected_tape_hash: &str,
    ) -> Result<Self, V8CoreError> {
        let checkpoint = Self::load_from_file(path)?;
        if checkpoint.header.tape_hash != expected_tape_hash {
            return Err(V8CoreError::Checkpoint(format!(
                "checkpoint tape hash mismatch: stored {}, expected {}",
                checkpoint.header.tape_hash, expected_tape_hash
            )));
        }
        Ok(checkpoint)
    }
}

fn sync_directory(path: &Path) -> Result<(), V8CoreError> {
    #[cfg(unix)]
    {
        let dir = std::fs::File::open(path)
            .map_err(|e| V8CoreError::Checkpoint(format!("open checkpoint directory: {e}")))?;
        dir.sync_all()
            .map_err(|e| V8CoreError::Checkpoint(format!("sync checkpoint directory: {e}")))?;
    }
    #[cfg(not(unix))]
    let _ = path;
    Ok(())
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
