#![allow(dead_code)]

/// Initialize standard tracing facade for V8 core runtime.
pub fn init_telemetry() {
    tracing::info!("v8-core telemetry initialized");
}

/// Helper function for recording step duration metric.
pub fn record_duration_metric(name: &'static str, duration_sec: f64) {
    metrics::gauge!(name).set(duration_sec);
}
