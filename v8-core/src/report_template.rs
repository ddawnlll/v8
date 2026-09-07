//! Unified Report Template Engine via Minijinja (V8.6 M12, ANA-A4).
//!
//! Replaces hand-concatenated HTML string building with a single
//! registered template system for forensic and audit reports.

use minijinja::Environment;
use serde_json::Value;

pub const AUDIT_REPORT_TEMPLATE: &str = r#"<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{{ title }}</title>
<style>
{{ css }}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div style="display:flex; justify-content:space-between; align-items:flex-start;">
    <div>
      <h1>{{ title }}</h1>
      <div class="sub">{{ subtitle }}</div>
    </div>
    <div><span class="badge badge-ok">{{ status_badge }}</span></div>
  </div>
  <div class="meta-grid">
    <div><b>Runtime:</b> {{ runtime }}</div>
    <div><b>Engine Architecture:</b> {{ architecture }}</div>
    <div><b>Verification:</b> {{ verification }}</div>
    <div><b>Oracle Authority:</b> {{ authority }}</div>
  </div>
</header>
<div class="card">
  <h2>System Pipeline Execution Trace</h2>
  <div class="sec">Deterministic Pipeline Stages & Latency Profiling</div>
  <div class="pipeline">
    {% for step in pipeline_steps %}
    <div class="pipe-step">
      <b>{{ step.name }}</b>
      <code>{{ step.detail }}</code>
    </div>
    {% endfor %}
  </div>
</div>
</div>
</body>
</html>"#;

pub struct ReportRenderer {
    env: Environment<'static>,
}

impl ReportRenderer {
    pub fn new() -> Result<Self, String> {
        let mut env = Environment::new();
        env.add_template("audit_report", AUDIT_REPORT_TEMPLATE)
            .map_err(|e| format!("failed to compile audit_report template: {e}"))?;
        Ok(Self { env })
    }

    pub fn render_audit_report(&self, context: Value) -> Result<String, String> {
        let tmpl = self.env.get_template("audit_report")
            .map_err(|e| format!("template not found: {e}"))?;
        tmpl.render(context)
            .map_err(|e| format!("rendering error: {e}"))
    }
}
