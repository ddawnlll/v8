//! Hash-bound prospective shadow-run boundary (V8.3, D-138).
//!
//! This module owns only provenance and lifecycle safety. It deliberately does
//! not calculate returns, compare economic outcomes, or promote a challenger.
//! A valid shadow receipt therefore remains `NO_ECONOMIC_CLAIM`.

use blake3::Hasher;
use serde::{Deserialize, Serialize};
use std::fs::{self, File, OpenOptions};
use std::io::{self, BufRead, BufReader, Write};
use std::path::{Path, PathBuf};
use thiserror::Error;

use crate::hash;

pub const SHADOW_SCHEMA_VERSION: &str = "v8.shadow.v1";
pub const NO_ECONOMIC_CLAIM: &str = "NO_ECONOMIC_CLAIM";
pub const PROMOTION_FORBIDDEN: &str = "PROMOTION_FORBIDDEN";

#[derive(Debug, Error)]
pub enum ShadowError {
    #[error("shadow IO error: {0}")]
    Io(#[from] io::Error),
    #[error("shadow serialization error: {0}")]
    Serialization(#[from] serde_json::Error),
    #[error("shadow blocked: {0}")]
    Blocked(String),
    #[error("shadow data blocked: {0}")]
    DataBlocked(String),
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProspectiveShadowManifest {
    pub schema: String,
    pub manifest_id: String,
    pub mode: String,
    pub freeze_cutoff_ns: i64,
    pub code_hash: String,
    pub config_hash: String,
    pub dataset_hash: String,
    pub authority_hash: String,
    pub incumbent_id: String,
    pub challenger_id: String,
    pub artifact_namespace: String,
    pub economic_claim: String,
}

impl ProspectiveShadowManifest {
    pub fn validate(&self) -> Result<(), ShadowError> {
        let fields = [
            ("schema", self.schema.as_str()),
            ("manifest_id", self.manifest_id.as_str()),
            ("mode", self.mode.as_str()),
            ("code_hash", self.code_hash.as_str()),
            ("config_hash", self.config_hash.as_str()),
            ("dataset_hash", self.dataset_hash.as_str()),
            ("authority_hash", self.authority_hash.as_str()),
            ("incumbent_id", self.incumbent_id.as_str()),
            ("challenger_id", self.challenger_id.as_str()),
            ("artifact_namespace", self.artifact_namespace.as_str()),
        ];
        for (name, value) in fields {
            if value.trim().is_empty() {
                return Err(ShadowError::Blocked(format!(
                    "manifest field {name} is empty"
                )));
            }
        }
        if self.schema != SHADOW_SCHEMA_VERSION {
            return Err(ShadowError::Blocked(format!(
                "unsupported manifest schema {}",
                self.schema
            )));
        }
        if self.mode != "PROSPECTIVE_SHADOW" {
            return Err(ShadowError::Blocked(format!(
                "shadow mode must be PROSPECTIVE_SHADOW, got {}",
                self.mode
            )));
        }
        if self.incumbent_id == self.challenger_id {
            return Err(ShadowError::Blocked(
                "incumbent and challenger identities must differ".to_string(),
            ));
        }
        if self.economic_claim != NO_ECONOMIC_CLAIM {
            return Err(ShadowError::Blocked(
                "prospective shadow must remain NO_ECONOMIC_CLAIM".to_string(),
            ));
        }
        let expected = self.canonical_hash_without_id()?;
        if self.manifest_id != expected {
            return Err(ShadowError::Blocked(format!(
                "manifest_id mismatch: expected {expected}, got {}",
                self.manifest_id
            )));
        }
        Ok(())
    }

    /// Control-plane constructor: seal a manifest before it crosses into the
    /// compute plane. The CLI consumes already-sealed manifests from disk.
    #[allow(dead_code)]
    pub fn seal(mut self) -> Result<Self, ShadowError> {
        self.manifest_id.clear();
        self.manifest_id = self.canonical_hash_without_id()?;
        self.validate()?;
        Ok(self)
    }

    fn canonical_hash_without_id(&self) -> Result<String, ShadowError> {
        let mut value = serde_json::to_value(self)?;
        value["manifest_id"] = serde_json::Value::String(String::new());
        Ok(hash::hash_value_sha256(&value))
    }

    pub fn save(&self, path: &Path) -> Result<(), ShadowError> {
        self.validate()?;
        write_if_same(path, &serde_json::to_vec_pretty(self)?)
    }

    pub fn load(path: &Path) -> Result<Self, ShadowError> {
        let bytes = fs::read(path)?;
        let manifest: Self = serde_json::from_slice(&bytes)?;
        manifest.validate()?;
        Ok(manifest)
    }
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ProspectiveObservation {
    pub event_id: String,
    pub knowledge_time_ns: i64,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ArtifactBinding {
    pub path: String,
    pub kind: String,
    pub blake3_hash: String,
    pub size_bytes: u64,
    pub manifest_id: String,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ShadowReceipt {
    pub schema: String,
    pub manifest_id: String,
    pub manifest_hash: String,
    pub status: String,
    pub observations: usize,
    pub first_knowledge_time_ns: i64,
    pub last_knowledge_time_ns: i64,
    pub incumbent_id: String,
    pub challenger_id: String,
    pub economic_claim: String,
    pub promotion: String,
    pub artifacts: Vec<ArtifactBinding>,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ShadowRequest {
    pub manifest_path: PathBuf,
    pub observations_path: PathBuf,
    pub out_dir: PathBuf,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct ArtifactIndexRequest {
    pub manifest_path: PathBuf,
    pub artifact_paths: Vec<PathBuf>,
    pub out_path: PathBuf,
}

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq, Eq)]
pub struct CanonicalArtifactIndex {
    pub schema: String,
    pub manifest_id: String,
    pub economic_claim: String,
    pub artifacts: Vec<ArtifactBinding>,
}

pub fn run(request: &ShadowRequest) -> Result<ShadowReceipt, ShadowError> {
    let manifest = ProspectiveShadowManifest::load(&request.manifest_path)?;
    let observations = read_observations(&request.observations_path, manifest.freeze_cutoff_ns)?;
    if observations.is_empty() {
        return Err(ShadowError::DataBlocked(
            "prospective observation stream is empty".to_string(),
        ));
    }

    let observed_hash = file_blake3(&request.observations_path)?;
    if observed_hash != manifest.dataset_hash {
        return Err(ShadowError::Blocked(format!(
            "dataset hash mismatch: manifest {}, observations {}",
            manifest.dataset_hash, observed_hash
        )));
    }

    fs::create_dir_all(&request.out_dir)?;
    let manifest_out = request.out_dir.join("shadow-manifest.json");
    manifest.save(&manifest_out)?;

    let manifest_artifact = bind_artifact(&manifest_out, "MANIFEST", &manifest.manifest_id)?;
    let observation_artifact = bind_artifact(
        &request.observations_path,
        "PROSPECTIVE_OBSERVATIONS",
        &manifest.manifest_id,
    )?;
    let receipt = ShadowReceipt {
        schema: SHADOW_SCHEMA_VERSION.to_string(),
        manifest_id: manifest.manifest_id.clone(),
        manifest_hash: manifest.manifest_id.clone(),
        status: "SHADOW_RECORDED".to_string(),
        observations: observations.len(),
        first_knowledge_time_ns: observations
            .first()
            .map(|row| row.knowledge_time_ns)
            .unwrap_or_default(),
        last_knowledge_time_ns: observations
            .last()
            .map(|row| row.knowledge_time_ns)
            .unwrap_or_default(),
        incumbent_id: manifest.incumbent_id.clone(),
        challenger_id: manifest.challenger_id.clone(),
        economic_claim: NO_ECONOMIC_CLAIM.to_string(),
        promotion: PROMOTION_FORBIDDEN.to_string(),
        artifacts: vec![manifest_artifact, observation_artifact],
    };
    let receipt_path = request.out_dir.join("shadow-receipt.json");
    write_if_same(&receipt_path, &serde_json::to_vec_pretty(&receipt)?)?;
    verify_output_bundle(&request.out_dir, &manifest)?;
    Ok(receipt)
}

/// Bind an arbitrary diagnostic/report/ledger bundle to one sealed manifest.
/// The index is intentionally a lineage artifact, not an economic summary.
pub fn index_artifacts(
    request: &ArtifactIndexRequest,
) -> Result<CanonicalArtifactIndex, ShadowError> {
    let manifest = ProspectiveShadowManifest::load(&request.manifest_path)?;
    if request.artifact_paths.is_empty() {
        return Err(ShadowError::DataBlocked(
            "artifact index has no declared files".to_string(),
        ));
    }
    if request
        .artifact_paths
        .iter()
        .any(|path| path == &request.out_path)
    {
        return Err(ShadowError::Blocked(
            "artifact index cannot include its own output".to_string(),
        ));
    }

    let mut artifacts = Vec::with_capacity(request.artifact_paths.len());
    let mut names = std::collections::BTreeSet::new();
    for path in &request.artifact_paths {
        let name = path
            .file_name()
            .map(|value| value.to_string_lossy().into_owned())
            .ok_or_else(|| {
                ShadowError::Blocked(format!("artifact has no file name: {}", path.display()))
            })?;
        if !names.insert(name.clone()) {
            return Err(ShadowError::Blocked(format!(
                "duplicate artifact file name in bundle: {name}"
            )));
        }
        artifacts.push(bind_artifact(
            path,
            "DECLARED_BUNDLE_ARTIFACT",
            &manifest.manifest_id,
        )?);
    }
    artifacts.sort_by(|left, right| left.path.cmp(&right.path));
    let index = CanonicalArtifactIndex {
        schema: SHADOW_SCHEMA_VERSION.to_string(),
        manifest_id: manifest.manifest_id,
        economic_claim: NO_ECONOMIC_CLAIM.to_string(),
        artifacts,
    };
    write_if_same(&request.out_path, &serde_json::to_vec_pretty(&index)?)?;
    Ok(index)
}

pub fn verify_output_bundle(
    out_dir: &Path,
    expected_manifest: &ProspectiveShadowManifest,
) -> Result<ShadowReceipt, ShadowError> {
    let manifest_path = out_dir.join("shadow-manifest.json");
    let receipt_path = out_dir.join("shadow-receipt.json");
    let manifest = ProspectiveShadowManifest::load(&manifest_path)?;
    if manifest != *expected_manifest {
        return Err(ShadowError::Blocked(
            "output manifest differs from requested manifest".to_string(),
        ));
    }
    let receipt: ShadowReceipt = serde_json::from_slice(&fs::read(&receipt_path)?)?;
    if receipt.manifest_id != expected_manifest.manifest_id
        || receipt.manifest_hash != expected_manifest.manifest_id
        || receipt.economic_claim != NO_ECONOMIC_CLAIM
        || receipt.promotion != PROMOTION_FORBIDDEN
    {
        return Err(ShadowError::Blocked(
            "shadow receipt has invalid authority or promotion binding".to_string(),
        ));
    }
    let entries = fs::read_dir(out_dir)?;
    for entry in entries {
        let entry = entry?;
        let name = entry.file_name().to_string_lossy().into_owned();
        if name != "shadow-manifest.json" && name != "shadow-receipt.json" {
            return Err(ShadowError::Blocked(format!(
                "mixed or undeclared output artifact: {name}"
            )));
        }
    }
    Ok(receipt)
}

fn read_observations(
    path: &Path,
    freeze_cutoff_ns: i64,
) -> Result<Vec<ProspectiveObservation>, ShadowError> {
    let file = File::open(path)?;
    let reader = BufReader::new(file);
    let mut rows = Vec::new();
    let mut previous = None;
    for (line_no, line) in reader.lines().enumerate() {
        let line = line?;
        if line.trim().is_empty() {
            continue;
        }
        let row: ProspectiveObservation = serde_json::from_str(&line).map_err(|e| {
            ShadowError::DataBlocked(format!("invalid observation line {}: {e}", line_no + 1))
        })?;
        if row.event_id.trim().is_empty() {
            return Err(ShadowError::DataBlocked(format!(
                "observation line {} has empty event_id",
                line_no + 1
            )));
        }
        if row.knowledge_time_ns <= freeze_cutoff_ns {
            return Err(ShadowError::Blocked(format!(
                "observation {} is not prospective: {} <= {}",
                row.event_id, row.knowledge_time_ns, freeze_cutoff_ns
            )));
        }
        if previous.is_some_and(|last| row.knowledge_time_ns < last) {
            return Err(ShadowError::Blocked(format!(
                "observation line {} is out of chronological order",
                line_no + 1
            )));
        }
        previous = Some(row.knowledge_time_ns);
        rows.push(row);
    }
    Ok(rows)
}

fn bind_artifact(
    path: &Path,
    kind: &str,
    manifest_id: &str,
) -> Result<ArtifactBinding, ShadowError> {
    let metadata = fs::metadata(path)?;
    Ok(ArtifactBinding {
        path: path
            .file_name()
            .map(|name| name.to_string_lossy().into_owned())
            .unwrap_or_else(|| path.to_string_lossy().into_owned()),
        kind: kind.to_string(),
        blake3_hash: file_blake3(path)?,
        size_bytes: metadata.len(),
        manifest_id: manifest_id.to_string(),
    })
}

fn file_blake3(path: &Path) -> Result<String, ShadowError> {
    let file = File::open(path)?;
    let mut reader = BufReader::with_capacity(1024 * 1024, file);
    let mut hasher = Hasher::new();
    let mut buffer = [0u8; 64 * 1024];
    loop {
        let n = std::io::Read::read(&mut reader, &mut buffer)?;
        if n == 0 {
            break;
        }
        hasher.update(&buffer[..n]);
    }
    Ok(hasher.finalize().to_hex().to_string())
}

fn write_if_same(path: &Path, bytes: &[u8]) -> Result<(), ShadowError> {
    if path.exists() {
        let current = fs::read(path)?;
        if current != bytes {
            return Err(ShadowError::Blocked(format!(
                "refusing to overwrite divergent artifact {}",
                path.display()
            )));
        }
        return Ok(());
    }
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }
    let mut file = OpenOptions::new().create_new(true).write(true).open(path)?;
    file.write_all(bytes)?;
    file.sync_all()?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn fixture_dir(name: &str) -> PathBuf {
        let dir = std::env::temp_dir().join(format!("v83-shadow-{}-{name}", std::process::id()));
        let _ = fs::remove_dir_all(&dir);
        fs::create_dir_all(&dir).unwrap();
        dir
    }

    fn fixture_manifest(dataset_hash: String) -> ProspectiveShadowManifest {
        ProspectiveShadowManifest {
            schema: SHADOW_SCHEMA_VERSION.to_string(),
            manifest_id: String::new(),
            mode: "PROSPECTIVE_SHADOW".to_string(),
            freeze_cutoff_ns: 100,
            code_hash: "code-hash".to_string(),
            config_hash: "config-hash".to_string(),
            dataset_hash,
            authority_hash: "authority-hash".to_string(),
            incumbent_id: "v8.2-incumbent".to_string(),
            challenger_id: "v8.3-challenger".to_string(),
            artifact_namespace: "shadow-test".to_string(),
            economic_claim: NO_ECONOMIC_CLAIM.to_string(),
        }
    }

    #[test]
    fn cutoff_is_strictly_forward_and_ordered() {
        let dir = fixture_dir("cutoff");
        let observations = dir.join("observations.jsonl");
        fs::write(
            &observations,
            "{\"event_id\":\"e1\",\"knowledge_time_ns\":100}\n",
        )
        .unwrap();
        let manifest = fixture_manifest(file_blake3(&observations).unwrap())
            .seal()
            .unwrap();
        let manifest_path = dir.join("manifest.json");
        manifest.save(&manifest_path).unwrap();
        let err = run(&ShadowRequest {
            manifest_path,
            observations_path: observations,
            out_dir: dir.join("out"),
        })
        .unwrap_err();
        assert!(err.to_string().contains("not prospective"));
    }

    #[test]
    fn records_a_deterministic_allocation_neutral_bundle() {
        let dir = fixture_dir("record");
        let observations = dir.join("observations.jsonl");
        fs::write(
            &observations,
            "{\"event_id\":\"e1\",\"knowledge_time_ns\":101}\n{\"event_id\":\"e2\",\"knowledge_time_ns\":102}\n",
        )
        .unwrap();
        let manifest = fixture_manifest(file_blake3(&observations).unwrap())
            .seal()
            .unwrap();
        let manifest_path = dir.join("manifest.json");
        manifest.save(&manifest_path).unwrap();
        let request = ShadowRequest {
            manifest_path,
            observations_path: observations,
            out_dir: dir.join("out"),
        };
        let first = run(&request).unwrap();
        let second = run(&request).unwrap();
        assert_eq!(first, second);
        assert_eq!(first.economic_claim, NO_ECONOMIC_CLAIM);
        assert_eq!(first.promotion, PROMOTION_FORBIDDEN);
    }

    #[test]
    fn mixed_output_artifact_fails_closed() {
        let dir = fixture_dir("mixed");
        let observations = dir.join("observations.jsonl");
        fs::write(
            &observations,
            "{\"event_id\":\"e1\",\"knowledge_time_ns\":101}\n",
        )
        .unwrap();
        let manifest = fixture_manifest(file_blake3(&observations).unwrap())
            .seal()
            .unwrap();
        let manifest_path = dir.join("manifest.json");
        manifest.save(&manifest_path).unwrap();
        let out_dir = dir.join("out");
        let request = ShadowRequest {
            manifest_path,
            observations_path: observations,
            out_dir: out_dir.clone(),
        };
        run(&request).unwrap();
        fs::write(out_dir.join("stale-report.json"), b"{}").unwrap();
        let err = verify_output_bundle(&out_dir, &manifest).unwrap_err();
        assert!(err.to_string().contains("mixed or undeclared"));
    }

    #[test]
    fn artifact_index_is_deterministic_and_rejects_self_output() {
        let dir = fixture_dir("index");
        let observations = dir.join("observations.jsonl");
        let report = dir.join("report.json");
        fs::write(
            &observations,
            "{\"event_id\":\"e1\",\"knowledge_time_ns\":101}\n",
        )
        .unwrap();
        fs::write(&report, b"diagnostic-only").unwrap();
        let manifest = fixture_manifest(file_blake3(&observations).unwrap())
            .seal()
            .unwrap();
        let manifest_path = dir.join("manifest.json");
        manifest.save(&manifest_path).unwrap();
        let index_path = dir.join("artifact-index.json");
        let request = ArtifactIndexRequest {
            manifest_path: manifest_path.clone(),
            artifact_paths: vec![observations.clone(), report.clone()],
            out_path: index_path.clone(),
        };
        let first = index_artifacts(&request).unwrap();
        let second = index_artifacts(&request).unwrap();
        assert_eq!(first, second);
        assert_eq!(first.economic_claim, NO_ECONOMIC_CLAIM);

        let duplicate = ArtifactIndexRequest {
            manifest_path,
            artifact_paths: vec![observations, report],
            out_path: dir.join("report.json"),
        };
        let err = index_artifacts(&duplicate).unwrap_err();
        assert!(err.to_string().contains("cannot include its own output"));
    }
}
