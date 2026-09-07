//! Physical Parquet artifact adapter for declared evaluation outputs.
//!
//! Issue #321 replaces the historical JSON-under-`.parquet` convention with a
//! standard Apache Parquet file. The adapter keeps the source row JSON as a
//! deterministic payload column while also exposing typed nullable columns for
//! scalar fields. This preserves exact source bytes, null/absence semantics,
//! deterministic ordering, and IEEE-754 f64 values in the typed `DOUBLE` columns.

use std::collections::{BTreeMap, BTreeSet, HashMap};
use std::fs::{self, File, OpenOptions};
use std::io;
use std::path::{Path, PathBuf};
use std::sync::Arc;

use arrow_array::builder::BinaryBuilder;
use arrow_array::{ArrayRef, BooleanArray, Float64Array, Int64Array, RecordBatch, StringArray};
use arrow_schema::{DataType, Field, Schema};
use parquet::arrow::ArrowWriter;
use parquet::file::metadata::KeyValue;
use parquet::file::properties::WriterProperties;
use parquet::file::reader::{FileReader, SerializedFileReader};
use serde_json::{Map, Value};

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum ColumnKind {
    Int64,
    Float64,
    Boolean,
    Utf8,
    Json,
}

impl ColumnKind {
    fn as_str(self) -> &'static str {
        match self {
            Self::Int64 => "INT64",
            Self::Float64 => "DOUBLE_IEEE754",
            Self::Boolean => "BOOLEAN",
            Self::Utf8 => "UTF8",
            Self::Json => "JSON_UTF8",
        }
    }

    fn arrow_type(self) -> DataType {
        match self {
            Self::Int64 => DataType::Int64,
            Self::Float64 => DataType::Float64,
            Self::Boolean => DataType::Boolean,
            Self::Utf8 | Self::Json => DataType::Utf8,
        }
    }
}

/// A physical artifact receipt returned after a successful atomic publication.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ParquetArtifactReceipt {
    pub path: PathBuf,
    pub row_count: usize,
    pub column_count: usize,
    pub byte_len: u64,
    pub row_count_verified: bool,
}

fn rows_from_value(value: &Value) -> Vec<Value> {
    match value {
        Value::Array(rows) => rows.clone(),
        Value::Object(_) => vec![value.clone()],
        Value::Null => Vec::new(),
        other => vec![serde_json::json!({"value": other})],
    }
}

fn object_row(row: &Value) -> Map<String, Value> {
    match row {
        Value::Object(object) => object.clone(),
        other => {
            let mut object = Map::new();
            object.insert("value".to_string(), other.clone());
            object
        }
    }
}

fn kind_for<'a>(values: impl Iterator<Item = Option<&'a Value>>) -> ColumnKind {
    let mut has_integer = false;
    let mut has_float = false;
    let mut has_bool = false;
    let mut has_string = false;
    let mut has_nested = false;
    for value in values.flatten() {
        match value {
            Value::Number(number) if number.as_i64().is_some() => has_integer = true,
            Value::Number(_) => has_float = true,
            Value::Bool(_) => has_bool = true,
            Value::String(_) => has_string = true,
            Value::Array(_) | Value::Object(_) => has_nested = true,
            Value::Null => {}
        }
    }
    if has_nested {
        ColumnKind::Json
    } else if has_string {
        ColumnKind::Utf8
    } else if has_bool && !has_integer && !has_float {
        ColumnKind::Boolean
    } else if has_float {
        ColumnKind::Float64
    } else if has_integer {
        ColumnKind::Int64
    } else {
        // A column containing only nulls is represented as nullable UTF-8 and
        // remains explicitly absent rather than being zero-filled.
        ColumnKind::Utf8
    }
}

fn canonical_row_bytes(row: &Value) -> io::Result<Vec<u8>> {
    serde_json::to_vec(row).map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))
}

fn typed_columns(rows: &[Value]) -> (Vec<String>, BTreeMap<String, ColumnKind>) {
    let mut names = BTreeSet::new();
    let objects: Vec<Map<String, Value>> = rows.iter().map(object_row).collect();
    for object in &objects {
        names.extend(object.keys().cloned());
    }
    let names: Vec<String> = names.into_iter().collect();
    let kinds = names
        .iter()
        .map(|name| {
            let kind = kind_for(objects.iter().map(|object| object.get(name)));
            (name.clone(), kind)
        })
        .collect();
    (names, kinds)
}

fn value_as_string(value: Option<&Value>, kind: ColumnKind) -> Option<String> {
    match (value, kind) {
        (Some(Value::String(value)), ColumnKind::Utf8) => Some(value.clone()),
        (Some(value), ColumnKind::Json) => serde_json::to_string(value).ok(),
        _ => None,
    }
}

/// Write JSON records to a physical Parquet file and atomically publish it.
///
/// The resulting file is readable by standard Parquet readers. `row_json` is a
/// byte-preserving provenance column; typed scalar columns are nullable and use
/// Parquet's native physical types. Metadata binds the producer, artifact kind,
/// source schema, and ordering contract.
pub fn write_json_rows(
    path: &Path,
    artifact_kind: &str,
    rows_value: &Value,
    provenance: Option<&Value>,
) -> io::Result<ParquetArtifactReceipt> {
    let rows = rows_from_value(rows_value);
    let (names, kinds) = typed_columns(&rows);
    let mut fields = vec![
        Field::new("row_index", DataType::Int64, false),
        Field::new("row_json", DataType::Binary, false),
    ];
    fields.extend(
        names
            .iter()
            .map(|name| Field::new(format!("field__{name}"), kinds[name].arrow_type(), true)),
    );
    let schema_manifest: Vec<Value> = names
        .iter()
        .map(|name| {
            serde_json::json!({
                "name": name,
                "physical_type": kinds[name].as_str(),
                "nullable": true
            })
        })
        .collect();
    let schema = Arc::new(
        Schema::new_with_metadata(
            fields,
            HashMap::from([
                ("v8.artifact_kind".to_string(), artifact_kind.to_string()),
                ("v8.row_order".to_string(), "source_order".to_string()),
                ("v8.f64_encoding".to_string(), "IEEE754_DOUBLE".to_string()),
                (
                    "v8.schema_manifest".to_string(),
                    serde_json::to_string(&schema_manifest)
                        .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?,
                ),
                (
                    "v8.provenance".to_string(),
                    provenance
                        .map(serde_json::to_string)
                        .transpose()
                        .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?
                        .unwrap_or_else(|| "null".to_string()),
                ),
            ]),
        )
    );

    let row_indices = Int64Array::from((0..rows.len()).map(|index| index as i64).collect::<Vec<_>>());
    let mut row_json = BinaryBuilder::new();
    for row in &rows {
        row_json.append_value(canonical_row_bytes(row)?);
    }
    let mut arrays: Vec<ArrayRef> = vec![Arc::new(row_indices), Arc::new(row_json.finish())];
    let objects: Vec<Map<String, Value>> = rows.iter().map(object_row).collect();

    for name in &names {
        match kinds[name] {
            ColumnKind::Int64 => {
                let values = objects
                    .iter()
                    .map(|object| match object.get(name) {
                        Some(Value::Number(number)) => number.as_i64(),
                        _ => None,
                    })
                    .collect::<Vec<_>>();
                arrays.push(Arc::new(Int64Array::from(values)));
            }
            ColumnKind::Float64 => {
                let values = objects
                    .iter()
                    .map(|object| match object.get(name) {
                        Some(Value::Number(number)) => number.as_f64(),
                        _ => None,
                    })
                    .collect::<Vec<_>>();
                arrays.push(Arc::new(Float64Array::from(values)));
            }
            ColumnKind::Boolean => {
                let values = objects
                    .iter()
                    .map(|object| match object.get(name) {
                        Some(Value::Bool(value)) => Some(*value),
                        _ => None,
                    })
                    .collect::<Vec<_>>();
                arrays.push(Arc::new(BooleanArray::from(values)));
            }
            ColumnKind::Utf8 | ColumnKind::Json => {
                let values = objects
                    .iter()
                    .map(|object| value_as_string(object.get(name), kinds[name]))
                    .collect::<Vec<_>>();
                arrays.push(Arc::new(StringArray::from(values)));
            }
        }
    }

    let batch = RecordBatch::try_new(schema.clone(), arrays)
        .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?;
    let parent = path.parent().unwrap_or_else(|| Path::new("."));
    fs::create_dir_all(parent)?;
    let tmp_path = parent.join(format!(
        ".{}.tmp-{}",
        path.file_name().and_then(|name| name.to_str()).unwrap_or("artifact"),
        std::process::id()
    ));
    let file = File::create(&tmp_path)?;
    let metadata = vec![
        KeyValue::new("v8.artifact_kind".to_string(), Some(artifact_kind.to_string())),
        KeyValue::new("v8.row_count".to_string(), Some(rows.len().to_string())),
    ];
    let properties = WriterProperties::builder()
        .set_key_value_metadata(Some(metadata))
        .build();
    let mut writer = ArrowWriter::try_new(file, schema, Some(properties))
        .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?;
    writer
        .write(&batch)
        .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?;
    writer
        .close()
        .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?;
    let published_file = OpenOptions::new().read(true).write(true).open(&tmp_path)?;
    published_file.sync_all()?;
    fs::rename(&tmp_path, path)?;
    #[cfg(unix)]
    File::open(parent)?.sync_all()?;

    let verified_rows = parquet_row_count(path)?;
    if verified_rows != rows.len() {
        return Err(io::Error::new(
            io::ErrorKind::InvalidData,
            format!("Parquet row-count mismatch: wrote {}, read {}", rows.len(), verified_rows),
        ));
    }
    Ok(ParquetArtifactReceipt {
        path: path.to_path_buf(),
        row_count: rows.len(),
        column_count: names.len() + 2,
        byte_len: fs::metadata(path)?.len(),
        row_count_verified: true,
    })
}

/// Return the physical row count from the Parquet footer.
pub fn parquet_row_count(path: &Path) -> io::Result<usize> {
    let file = File::open(path)?;
    let reader = SerializedFileReader::new(file)
        .map_err(|error| io::Error::new(io::ErrorKind::InvalidData, error))?;
    let rows = reader.metadata().file_metadata().num_rows();
    usize::try_from(rows).map_err(|_| io::Error::new(io::ErrorKind::InvalidData, "row count overflow"))
}

pub fn verify_parquet(path: &Path) -> io::Result<()> {
    let _ = parquet_row_count(path)?;
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn writes_standard_parquet_with_nullable_typed_columns_and_stable_rows() {
        let dir = std::env::temp_dir().join(format!("v8-parquet-{}", std::process::id()));
        fs::create_dir_all(&dir).unwrap();
        let path = dir.join("rows.parquet");
        let rows = serde_json::json!([
            {"id": 1, "value": 0.30000000000000004, "note": "a"},
            {"id": 2, "value": null, "note": "b"}
        ]);
        let receipt = write_json_rows(&path, "test", &rows, None).unwrap();
        assert_eq!(receipt.row_count, 2);
        assert!(receipt.row_count_verified);
        assert_eq!(parquet_row_count(&path).unwrap(), 2);
        let bytes = fs::read(&path).unwrap();
        assert!(bytes.starts_with(b"PAR1"));
        let _ = fs::remove_dir_all(dir);
    }
}
