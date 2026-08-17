//! Optional Vulkan f64 replay backend.
//!
//! This module is deliberately feature-gated. The default binary remains a
//! CPU-only build. The first GPU slice is a small f64 compute path used by the
//! replay backend once an adapter advertises shader f64; unsupported replay
//! cells continue through the CPU/SIMD backend.

use crate::backend::{ReplayCell, ReplayKernel};
use crate::data::Dataset;
use crate::simulator::{risk_unit, validate_geometry, FillPolicy, Outcome, HOUR_NS};

#[derive(Debug, Clone)]
pub struct GpuConfig {
    pub round_trip_cost_r: f64,
    pub round_trip_cost_bps: Option<f64>,
    pub funding_rate_r: f64,
    pub funding_hours: i64,
    pub funding_schedule: Vec<(i64, f64)>,
    pub fill_policy: FillPolicy,
}

impl Default for GpuConfig {
    fn default() -> Self {
        Self {
            round_trip_cost_r: 0.07,
            round_trip_cost_bps: None,
            funding_rate_r: 0.0,
            funding_hours: 8,
            funding_schedule: Vec::new(),
            fill_policy: FillPolicy::BarClose,
        }
    }
}

/// A GPU backend is constructed lazily by the replay command. Device creation
/// is intentionally not part of hashes or manifests.
pub struct GpuBackend {
    device: wgpu::Device,
    queue: wgpu::Queue,
    pipeline: wgpu::ComputePipeline,
    #[cfg(target_os = "linux")]
    contract_pipeline: wgpu::ComputePipeline,
    bind_group_layout: wgpu::BindGroupLayout,
    replay_pipeline: wgpu::ComputePipeline,
    replay_bind_group_layout: wgpu::BindGroupLayout,
    config: GpuConfig,
    limits: wgpu::Limits,
}

impl GpuBackend {
    /// Probe the native Vulkan adapter and require the shader-f64 feature.
    pub fn new() -> Result<Self, String> {
        Self::new_with_config(GpuConfig::default())
    }

    pub fn new_with_config(config: GpuConfig) -> Result<Self, String> {
        #[cfg(not(target_os = "linux"))]
        {
            let _ = config;
            Err("Vulkan GPU backend is enabled only on Linux builds".into())
        }
        #[cfg(target_os = "linux")]
        {
            Self::new_linux(config)
        }
    }

    #[cfg(target_os = "linux")]
    fn new_linux(config: GpuConfig) -> Result<Self, String> {
        let mut instance_desc = wgpu::InstanceDescriptor::new_without_display_handle();
        instance_desc.backends = wgpu::Backends::VULKAN;
        let instance = wgpu::Instance::new(instance_desc);
        let adapter = pollster::block_on(instance.request_adapter(&wgpu::RequestAdapterOptions {
            power_preference: wgpu::PowerPreference::HighPerformance,
            compatible_surface: None,
            force_fallback_adapter: false,
            apply_limit_buckets: false,
        }))
        .map_err(|e| format!("GPU adapter unavailable: {e}"))?;

        let features = adapter.features();
        if !features.contains(wgpu::Features::SHADER_F64) {
            return Err(format!(
                "GPU adapter {:?} does not expose shader f64",
                adapter.get_info().name
            ));
        }

        let (device, queue) = pollster::block_on(adapter.request_device(&wgpu::DeviceDescriptor {
            label: Some("v8-replay-gpu"),
            required_features: wgpu::Features::SHADER_F64,
            required_limits: wgpu::Limits::default(),
            experimental_features: wgpu::ExperimentalFeatures::disabled(),
            memory_hints: wgpu::MemoryHints::Performance,
            trace: wgpu::Trace::Off,
        }))
        .map_err(|e| format!("GPU device unavailable: {e}"))?;

        let shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("v8-replay-f64-probe"),
            source: wgpu::ShaderSource::Glsl {
                shader: std::borrow::Cow::Borrowed(
                    "#version 450\n\
                     layout(local_size_x = 1) in;\n\
                     layout(set = 0, binding = 0, std430) readonly buffer Input { double values[]; } input_values;\n\
                     layout(set = 0, binding = 1, std430) writeonly buffer Output { double values[]; } output_values;\n\
                     void main() {\n\
                         uint i = gl_GlobalInvocationID.x;\n\
                         output_values.values[i] = input_values.values[i] * 2.0 + 1.0;\n\
                     }\n",
                ),
                stage: wgpu::naga::ShaderStage::Compute,
                defines: &[],
            },
        });
        let bind_group_layout = device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
            label: Some("v8-replay-gpu-layout"),
            entries: &[
                wgpu::BindGroupLayoutEntry {
                    binding: 0,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: true },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
                wgpu::BindGroupLayoutEntry {
                    binding: 1,
                    visibility: wgpu::ShaderStages::COMPUTE,
                    ty: wgpu::BindingType::Buffer {
                        ty: wgpu::BufferBindingType::Storage { read_only: false },
                        has_dynamic_offset: false,
                        min_binding_size: None,
                    },
                    count: None,
                },
            ],
        });
        let pipeline_layout = device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
            label: Some("v8-replay-gpu-pipeline-layout"),
            bind_group_layouts: &[Some(&bind_group_layout)],
            immediate_size: 0,
        });
        let pipeline = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some("v8-replay-gpu-pipeline"),
            layout: Some(&pipeline_layout),
            module: &shader,
            entry_point: Some("main"),
            compilation_options: Default::default(),
            cache: None,
        });
        let contract_shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("v8-replay-f64-contract-probe"),
            source: wgpu::ShaderSource::Glsl {
                shader: std::borrow::Cow::Borrowed(
                    "#version 450\n\
                     layout(local_size_x = 1) in;\n\
                     layout(set = 0, binding = 0, std430) readonly buffer Input { double values[]; } input_values;\n\
                     layout(set = 0, binding = 1, std430) writeonly buffer Output { double values[]; } output_values;\n\
                     void main() {\n\
                         output_values.values[0] = input_values.values[0] * input_values.values[1] + input_values.values[2];\n\
                     }\n",
                ),
                stage: wgpu::naga::ShaderStage::Compute,
                defines: &[],
            },
        });
        let contract_pipeline = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some("v8-replay-f64-contract-pipeline"),
            layout: Some(&pipeline_layout),
            module: &contract_shader,
            entry_point: Some("main"),
            compilation_options: Default::default(),
            cache: None,
        });

        let replay_shader = device.create_shader_module(wgpu::ShaderModuleDescriptor {
            label: Some("v8-replay-f64-shader"),
            source: wgpu::ShaderSource::Glsl {
                shader: std::borrow::Cow::Borrowed(REPLAY_SHADER),
                stage: wgpu::naga::ShaderStage::Compute,
                defines: &[],
            },
        });
        let replay_bind_group_layout =
            device.create_bind_group_layout(&wgpu::BindGroupLayoutDescriptor {
                label: Some("v8-replay-f64-layout"),
                entries: &[
                    storage_layout(0, true),
                    storage_layout(1, true),
                    storage_layout(2, true),
                    storage_layout(3, true),
                    storage_layout(4, false),
                    storage_layout(5, false),
                ],
            });
        let replay_pipeline_layout =
            device.create_pipeline_layout(&wgpu::PipelineLayoutDescriptor {
                label: Some("v8-replay-f64-pipeline-layout"),
                bind_group_layouts: &[Some(&replay_bind_group_layout)],
                immediate_size: 0,
            });
        let replay_pipeline = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
            label: Some("v8-replay-f64-pipeline"),
            layout: Some(&replay_pipeline_layout),
            module: &replay_shader,
            entry_point: Some("main"),
            compilation_options: Default::default(),
            cache: None,
        });
        let limits = device.limits();
        let backend = Self {
            device,
            queue,
            pipeline,
            contract_pipeline,
            bind_group_layout,
            replay_pipeline,
            replay_bind_group_layout,
            config,
            limits,
        };
        if !backend.f64_contract_probe()? {
            return Err(
                "GPU f64 path contracts multiply-add; deterministic no-contraction probe failed"
                    .into(),
            );
        }
        Ok(backend)
    }

    /// Execute the tiny f64 kernel. This is kept public for the first AMD
    /// probe and parity smoke test; replay packing is added on top of the same
    /// device/pipeline boundary.
    pub fn f64_probe(&self, values: &[f64]) -> Result<Vec<f64>, String> {
        use wgpu::util::DeviceExt;
        if values.is_empty() {
            return Ok(Vec::new());
        }
        if values.len() as u32 > self.limits.max_compute_workgroups_per_dimension {
            return Err(format!(
                "GPU probe length {} exceeds device dispatch limit {}",
                values.len(),
                self.limits.max_compute_workgroups_per_dimension
            ));
        }
        let bytes = bytemuck::cast_slice(values);
        let input = self
            .device
            .create_buffer_init(&wgpu::util::BufferInitDescriptor {
                label: Some("v8-gpu-probe-input"),
                contents: bytes,
                usage: wgpu::BufferUsages::STORAGE,
            });
        let output_size = (std::mem::size_of_val(values)) as u64;
        let output = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("v8-gpu-probe-output"),
            size: output_size,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC,
            mapped_at_creation: false,
        });
        let staging = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("v8-gpu-probe-staging"),
            size: output_size,
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        let bind_group = self.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("v8-gpu-probe-bind-group"),
            layout: &self.bind_group_layout,
            entries: &[
                wgpu::BindGroupEntry {
                    binding: 0,
                    resource: input.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 1,
                    resource: output.as_entire_binding(),
                },
            ],
        });
        let mut encoder = self
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("v8-gpu-probe-encoder"),
            });
        {
            let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
                label: Some("v8-gpu-probe-pass"),
                timestamp_writes: None,
            });
            pass.set_pipeline(&self.pipeline);
            pass.set_bind_group(0, &bind_group, &[]);
            pass.dispatch_workgroups(values.len() as u32, 1, 1);
        }
        encoder.copy_buffer_to_buffer(&output, 0, &staging, 0, output_size);
        self.queue.submit(Some(encoder.finish()));
        let slice = staging.slice(..);
        let (tx, rx) = std::sync::mpsc::channel();
        slice.map_async(wgpu::MapMode::Read, move |result| {
            let _ = tx.send(result);
        });
        let _ = self.device.poll(wgpu::PollType::Wait {
            submission_index: None,
            timeout: None,
        });
        rx.recv()
            .map_err(|e| format!("GPU map callback failed: {e}"))?
            .map_err(|e| format!("GPU readback failed: {e}"))?;
        let mapped = slice
            .get_mapped_range()
            .map_err(|e| format!("GPU mapped range failed: {e}"))?;
        let result = bytemuck::cast_slice::<u8, f64>(&mapped).to_vec();
        drop(mapped);
        staging.unmap();
        Ok(result)
    }

    /// Detects a fused multiply-add in the shader path. The CPU contract
    /// evaluates `(a*b)+c` with a rounded multiply followed by a rounded add;
    /// a fused GPU result is a different bit pattern for this triplet.
    #[cfg(target_os = "linux")]
    pub fn f64_contract_probe(&self) -> Result<bool, String> {
        use wgpu::util::DeviceExt;
        let values = [1.0000000000000002_f64, 0.9999999999999998_f64, -1.0_f64];
        let expected = (values[0] * values[1]) + values[2];
        let input = self
            .device
            .create_buffer_init(&wgpu::util::BufferInitDescriptor {
                label: Some("v8-gpu-contract-input"),
                contents: bytemuck::cast_slice(&values),
                usage: wgpu::BufferUsages::STORAGE,
            });
        let output_size = std::mem::size_of::<f64>() as u64;
        let output = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("v8-gpu-contract-output"),
            size: output_size,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC,
            mapped_at_creation: false,
        });
        let staging = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("v8-gpu-contract-staging"),
            size: output_size,
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        let bind_group = self.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("v8-gpu-contract-bind-group"),
            layout: &self.bind_group_layout,
            entries: &[
                wgpu::BindGroupEntry {
                    binding: 0,
                    resource: input.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 1,
                    resource: output.as_entire_binding(),
                },
            ],
        });
        let mut encoder = self
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("v8-gpu-contract-encoder"),
            });
        {
            let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
                label: Some("v8-gpu-contract-pass"),
                timestamp_writes: None,
            });
            pass.set_pipeline(&self.contract_pipeline);
            pass.set_bind_group(0, &bind_group, &[]);
            pass.dispatch_workgroups(1, 1, 1);
        }
        encoder.copy_buffer_to_buffer(&output, 0, &staging, 0, output_size);
        self.queue.submit(Some(encoder.finish()));
        let slice = staging.slice(..);
        let (tx, rx) = std::sync::mpsc::channel();
        slice.map_async(wgpu::MapMode::Read, move |result| {
            let _ = tx.send(result);
        });
        let _ = self.device.poll(wgpu::PollType::Wait {
            submission_index: None,
            timeout: None,
        });
        rx.recv()
            .map_err(|e| format!("GPU contract map callback failed: {e}"))?
            .map_err(|e| format!("GPU contract readback failed: {e}"))?;
        let mapped = slice
            .get_mapped_range()
            .map_err(|e| format!("GPU contract mapped range failed: {e}"))?;
        let observed = bytemuck::cast_slice::<u8, f64>(&mapped)
            .first()
            .copied()
            .ok_or_else(|| "GPU contract readback was empty".to_string())?;
        drop(mapped);
        staging.unmap();
        Ok(observed.to_bits() == expected.to_bits())
    }

    fn replay_cells(
        &self,
        dataset: &Dataset,
        cells: &[ReplayCell],
    ) -> Result<Vec<Outcome>, String> {
        if self.config.fill_policy != FillPolicy::BarClose {
            return Err(
                "GPU replay supports only the BarClose fill policy; use CPU for FILL_AT_LIMIT"
                    .into(),
            );
        }
        if cells.is_empty() {
            return Ok(Vec::new());
        }
        if cells.iter().any(|c| !gpu_eligible(c)) {
            return Err("GPU replay received a cell outside the static bar-close subset".into());
        }
        const MAX_CELLS_PER_DISPATCH: usize = 4096;
        if cells.len() > MAX_CELLS_PER_DISPATCH
            || cells.len() as u32 > self.limits.max_compute_workgroups_per_dimension
        {
            return Err(format!(
                "GPU replay batch {} exceeds per-dispatch limit {}",
                cells.len(),
                MAX_CELLS_PER_DISPATCH
                    .min(self.limits.max_compute_workgroups_per_dimension as usize)
            ));
        }

        let mut bars = Vec::<f64>::new();
        let mut funding = Vec::<f64>::new();
        let mut cell_f = Vec::<f64>::with_capacity(cells.len() * 6);
        let mut cell_i = Vec::<u32>::with_capacity(cells.len() * 4);
        let mut metadata = Vec::<(usize, usize, usize)>::with_capacity(cells.len());
        for cell in cells {
            validate_geometry(&cell.draft)?;
            let symbol = dataset
                .bars
                .iter()
                .find(|b| b.symbol == cell.symbol)
                .ok_or_else(|| format!("GPU replay: no bars for {}", cell.symbol))?;
            let expiry = cell.draft.geom_i64("expiry_bars").unwrap_or(0) as usize;
            let end = cell.end.min(cell.start.saturating_add(expiry + 1));
            if cell.start >= end || end > symbol.closes.len() {
                return Err("GPU replay: invalid cell window".into());
            }
            let bar_offset = bars.len() / 4;
            let entry = symbol.closes[cell.start];
            let unit = risk_unit(&cell.draft, entry)?;
            let entry_time = symbol.available_times[cell.start];
            let sign = if cell.draft.direction == "LONG" {
                1.0
            } else {
                -1.0
            };
            let mut settlements = 0i64;
            let mut funding_paid = 0.0;
            for i in cell.start..end {
                bars.extend_from_slice(&[
                    symbol.opens[i],
                    symbol.highs[i],
                    symbol.lows[i],
                    symbol.closes[i],
                ]);
                let total = funding_boundaries_crossed(
                    entry_time,
                    symbol.available_times[i],
                    self.config.funding_hours,
                );
                let new_settlements = total - settlements;
                if new_settlements > 0 {
                    if self.config.funding_schedule.is_empty() {
                        funding_paid += sign * self.config.funding_rate_r * new_settlements as f64;
                    } else {
                        for boundary in funding_boundary_times(
                            entry_time,
                            symbol.available_times[i],
                            self.config.funding_hours,
                        )
                        .into_iter()
                        .skip(settlements as usize)
                        {
                            let rate = self
                                .config
                                .funding_schedule
                                .iter()
                                .find(|(time, _)| *time == boundary)
                                .map(|(_, rate)| *rate)
                                .ok_or_else(|| {
                                    format!("funding schedule missing boundary {boundary}")
                                })?;
                            funding_paid += sign * entry * rate / unit;
                        }
                    }
                    settlements = total;
                }
                funding.push(funding_paid);
            }
            let g = &cell.draft.risk_geometry;
            let stop_ref = g.get("stop_ref").and_then(|v| v.as_f64()).unwrap_or(0.0);
            let flags = if g.contains_key("stop_ref") { 1 } else { 0 };
            let cost = match self.config.round_trip_cost_bps {
                Some(bps) => (bps / 10_000.0) * entry / unit,
                None => self.config.round_trip_cost_r,
            };
            cell_f.extend_from_slice(&[
                g.get("target_r").and_then(|v| v.as_f64()).unwrap_or(0.0),
                g.get("stop_r").and_then(|v| v.as_f64()).unwrap_or(0.0),
                g.get("atr_ref").and_then(|v| v.as_f64()).unwrap_or(0.0),
                g.get("risk_frac").and_then(|v| v.as_f64()).unwrap_or(0.0),
                stop_ref,
                cost,
            ]);
            cell_i.extend_from_slice(&[
                bar_offset as u32,
                (end - cell.start) as u32,
                u32::from(cell.draft.direction == "LONG"),
                flags,
            ]);
            metadata.push((cell.start, end, bar_offset));
        }

        let bars_buf = storage_buffer(&self.device, "gpu-bars", bytemuck::cast_slice(&bars), false);
        let funding_buf = storage_buffer(
            &self.device,
            "gpu-funding",
            bytemuck::cast_slice(&funding),
            true,
        );
        let f_buf = storage_buffer(
            &self.device,
            "gpu-cell-f",
            bytemuck::cast_slice(&cell_f),
            false,
        );
        let i_buf = storage_buffer(
            &self.device,
            "gpu-cell-i",
            bytemuck::cast_slice(&cell_i),
            false,
        );
        let out_f_size = (cell_f.len() / 6 * 8 * std::mem::size_of::<f64>()) as u64;
        let out_i_size = (cell_i.len() / 4 * 3 * std::mem::size_of::<u32>()) as u64;
        let max_storage = self.limits.max_storage_buffer_binding_size;
        for (name, size) in [
            ("bars", (bars.len() * 8) as u64),
            ("funding", (funding.len() * 8) as u64),
            ("cell-f", (cell_f.len() * 8) as u64),
            ("cell-i", (cell_i.len() * 4) as u64),
            ("out-f", out_f_size),
            ("out-i", out_i_size),
        ] {
            if size > max_storage {
                return Err(format!(
                    "GPU {name} buffer {size} bytes exceeds device storage limit {max_storage}"
                ));
            }
        }
        let out_f = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("gpu-out-f"),
            size: out_f_size,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC,
            mapped_at_creation: false,
        });
        let out_i = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("gpu-out-i"),
            size: out_i_size,
            usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC,
            mapped_at_creation: false,
        });
        let stage_f = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("gpu-stage-f"),
            size: out_f_size,
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        let stage_i = self.device.create_buffer(&wgpu::BufferDescriptor {
            label: Some("gpu-stage-i"),
            size: out_i_size,
            usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
            mapped_at_creation: false,
        });
        let group = self.device.create_bind_group(&wgpu::BindGroupDescriptor {
            label: Some("gpu-replay-bind-group"),
            layout: &self.replay_bind_group_layout,
            entries: &[
                wgpu::BindGroupEntry {
                    binding: 0,
                    resource: bars_buf.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 1,
                    resource: f_buf.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 2,
                    resource: i_buf.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 3,
                    resource: funding_buf.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 4,
                    resource: out_f.as_entire_binding(),
                },
                wgpu::BindGroupEntry {
                    binding: 5,
                    resource: out_i.as_entire_binding(),
                },
            ],
        });
        let mut encoder = self
            .device
            .create_command_encoder(&wgpu::CommandEncoderDescriptor {
                label: Some("gpu-replay-encoder"),
            });
        {
            let mut pass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
                label: Some("gpu-replay-pass"),
                timestamp_writes: None,
            });
            pass.set_pipeline(&self.replay_pipeline);
            pass.set_bind_group(0, &group, &[]);
            pass.dispatch_workgroups(cells.len() as u32, 1, 1);
        }
        encoder.copy_buffer_to_buffer(&out_f, 0, &stage_f, 0, out_f_size);
        encoder.copy_buffer_to_buffer(&out_i, 0, &stage_i, 0, out_i_size);
        self.queue.submit(Some(encoder.finish()));
        let (f, i) = readback_pair(&self.device, &stage_f, &stage_i, out_f_size, out_i_size)?;
        let mut outcomes = Vec::with_capacity(cells.len());
        for (n, cell) in cells.iter().enumerate() {
            let fo = &f[n * 8..n * 8 + 8];
            let io = &i[n * 3..n * 3 + 3];
            let symbol = dataset
                .bars
                .iter()
                .find(|b| b.symbol == cell.symbol)
                .unwrap();
            let endpoint = match io[0] {
                1 => "TARGET",
                2 => "STOP",
                _ => "EXPIRY",
            };
            let horizon = io[1] as usize;
            let (start, end, _) = metadata[n];
            let available_idx = if endpoint == "EXPIRY" {
                end.saturating_sub(1)
            } else {
                start.saturating_add(horizon)
            };
            outcomes.push(Outcome {
                endpoint: endpoint.into(),
                net_r: fo[0],
                label_status: if endpoint == "EXPIRY" {
                    "RIGHT_CENSORED"
                } else {
                    "MATURE"
                }
                .into(),
                horizon_bars: io[1] as i64,
                label_available_time: symbol.available_times[available_idx],
                mae_r: fo[1],
                mfe_r: fo[2],
                ambiguous_bars: io[2] as i64,
                entry_price: fo[3],
                risk_unit_price: fo[4],
                market_move_r: fo[5],
                cost_r: fo[6],
                funding_r: fo[7],
            });
        }
        Ok(outcomes)
    }
}

impl ReplayKernel for GpuBackend {
    fn evaluate(
        &self,
        dataset: &Dataset,
        cells: &[ReplayCell],
        output: &mut [Outcome],
    ) -> Result<(), String> {
        if cells.len() != output.len() {
            return Err("GPU replay output size mismatch".into());
        }
        const MAX_CELLS_PER_DISPATCH: usize = 4096;
        let chunk_size = MAX_CELLS_PER_DISPATCH
            .min(self.limits.max_compute_workgroups_per_dimension as usize)
            .max(1);
        for (offset, chunk) in cells.chunks(chunk_size).enumerate() {
            let outcomes = self.replay_cells(dataset, chunk)?;
            let lo = offset * chunk_size;
            let hi = lo + outcomes.len();
            output[lo..hi].clone_from_slice(&outcomes);
        }
        Ok(())
    }
}

fn funding_boundaries_crossed(entry_ns: i64, time_ns: i64, hours: i64) -> i64 {
    if time_ns <= entry_ns || hours <= 0 {
        return 0;
    }
    let entry_hour = entry_ns / HOUR_NS;
    let time_hour = time_ns / HOUR_NS;
    time_hour / hours - entry_hour / hours
}

fn funding_boundary_times(entry_ns: i64, time_ns: i64, hours: i64) -> Vec<i64> {
    if time_ns <= entry_ns || hours <= 0 {
        return Vec::new();
    }
    let entry_hour = entry_ns / HOUR_NS;
    let time_hour = time_ns / HOUR_NS;
    let first = (entry_hour / hours + 1) * hours;
    let last = (time_hour / hours) * hours;
    (first..=last)
        .map(|hour| hour * HOUR_NS)
        .step_by(hours as usize)
        .collect()
}

#[cfg(target_os = "linux")]
fn storage_layout(binding: u32, read_only: bool) -> wgpu::BindGroupLayoutEntry {
    wgpu::BindGroupLayoutEntry {
        binding,
        visibility: wgpu::ShaderStages::COMPUTE,
        ty: wgpu::BindingType::Buffer {
            ty: wgpu::BufferBindingType::Storage { read_only },
            has_dynamic_offset: false,
            min_binding_size: None,
        },
        count: None,
    }
}

fn storage_buffer(
    device: &wgpu::Device,
    label: &str,
    bytes: &[u8],
    _read_only: bool,
) -> wgpu::Buffer {
    use wgpu::util::DeviceExt;
    device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some(label),
        contents: bytes,
        usage: wgpu::BufferUsages::STORAGE,
    })
}

fn gpu_eligible(cell: &ReplayCell) -> bool {
    let g = &cell.draft.risk_geometry;
    (cell.draft.direction == "LONG" || cell.draft.direction == "SHORT")
        && cell.thesis.is_none()
        && !g.contains_key("trigger_ref")
        && !g.contains_key("limit_price")
        && !g.contains_key("trail_stop_atr")
        && !g.contains_key("breakeven_roll_at_mfe_r")
        && !g.contains_key("scale_out_ratio")
        && !g.contains_key("pyramid_add_rules")
        && !g.contains_key("time_exit_bars")
        && g.contains_key("target_r")
        && g.contains_key("stop_r")
        && (g.contains_key("atr_ref") || g.contains_key("risk_frac"))
}

/// Whether the cell belongs to the GPU's static bar-close kernel subset.
/// Auto dispatch uses this to form a mixed CPU/GPU batch; explicit `gpu`
/// remains strict and still rejects unsupported cells in `evaluate`.
pub fn supports_cell(cell: &ReplayCell) -> bool {
    gpu_eligible(cell)
}

fn readback_pair(
    device: &wgpu::Device,
    f_buf: &wgpu::Buffer,
    i_buf: &wgpu::Buffer,
    f_size: u64,
    i_size: u64,
) -> Result<(Vec<f64>, Vec<u32>), String> {
    let f_slice = f_buf.slice(..);
    let i_slice = i_buf.slice(..);
    let (ftx, frx) = std::sync::mpsc::channel();
    let (itx, irx) = std::sync::mpsc::channel();
    f_slice.map_async(wgpu::MapMode::Read, move |r| {
        let _ = ftx.send(r);
    });
    i_slice.map_async(wgpu::MapMode::Read, move |r| {
        let _ = itx.send(r);
    });
    let _ = device.poll(wgpu::PollType::Wait {
        submission_index: None,
        timeout: None,
    });
    frx.recv()
        .map_err(|e| format!("GPU f readback callback: {e}"))?
        .map_err(|e| format!("GPU f readback: {e}"))?;
    irx.recv()
        .map_err(|e| format!("GPU i readback callback: {e}"))?
        .map_err(|e| format!("GPU i readback: {e}"))?;
    let fm = f_slice
        .get_mapped_range()
        .map_err(|e| format!("GPU f map: {e}"))?;
    let im = i_slice
        .get_mapped_range()
        .map_err(|e| format!("GPU i map: {e}"))?;
    if fm.len() != f_size as usize || im.len() != i_size as usize {
        return Err("GPU readback length mismatch".into());
    }
    let f = bytemuck::cast_slice::<u8, f64>(&fm).to_vec();
    let i = bytemuck::cast_slice::<u8, u32>(&im).to_vec();
    drop(fm);
    drop(im);
    f_buf.unmap();
    i_buf.unmap();
    Ok((f, i))
}

#[cfg(target_os = "linux")]
const REPLAY_SHADER: &str = r#"#version 450
layout(local_size_x = 1) in;
layout(set=0,binding=0,std430) readonly buffer Bars { double v[]; } bars;
layout(set=0,binding=1,std430) readonly buffer CellF { double v[]; } cf;
layout(set=0,binding=2,std430) readonly buffer CellI { uint v[]; } ci;
layout(set=0,binding=3,std430) readonly buffer Funding { double v[]; } funding;
layout(set=0,binding=4,std430) writeonly buffer OutF { double v[]; } of;
layout(set=0,binding=5,std430) writeonly buffer OutI { uint v[]; } oi;
void main() {
  uint n = gl_GlobalInvocationID.x;
  uint ib = n * 4u; uint fb = n * 6u; uint ob = n * 8u; uint xb = n * 3u;
  uint bo = ci.v[ib]; uint bl = ci.v[ib+1]; bool lng = ci.v[ib+2] != 0u; bool has_sr = ci.v[ib+3] != 0u;
  double tr = cf.v[fb]; double sr = cf.v[fb+1]; double atr = cf.v[fb+2]; double rf = cf.v[fb+3]; double srp = cf.v[fb+4]; double cost = cf.v[fb+5];
  double sign = lng ? 1.0 : -1.0; double entry = bars.v[bo*4u+3u]; double unit = atr > 0.0 ? atr : entry * rf;
  double target = entry + sign * tr * unit; double stop = has_sr ? srp : entry - sign * sr * unit;
  double mae = 0.0; double mfe = 0.0; double exitp = entry; double market_move = 0.0; double funding_paid = 0.0; uint endpoint = 0u; uint horizon = 0u; uint ambiguous = 0u; bool closed = false;
  for (uint j=1u; j<bl; j++) {
    uint b = (bo+j)*4u; double op=bars.v[b]; double hi=bars.v[b+1u]; double lo=bars.v[b+2u]; double cl=bars.v[b+3u]; market_move=(cl-entry)/unit; funding_paid=funding.v[bo+j];
    double fav = lng ? hi : lo; double adv = lng ? lo : hi;
    double mf = max(sign*(fav-entry)/unit, 0.0); double ma = max(sign*(entry-adv)/unit, 0.0); mfe=max(mfe,mf); mae=max(mae,ma); horizon++;
    bool ht = lng ? hi >= target : lo <= target; bool hs = lng ? lo <= stop : hi >= stop;
    if (ht && hs) { ambiguous++; endpoint=2u; exitp=lng ? min(stop,op) : max(stop,op); closed=true; break; }
    if (ht) { endpoint=1u; exitp=lng ? max(target,op) : min(target,op); closed=true; break; }
    if (hs) { endpoint=2u; exitp=lng ? min(stop,op) : max(stop,op); closed=true; break; }
    exitp=cl;
  }
  if (!closed) { endpoint=0u; exitp=bars.v[(bo+bl-1u)*4u+3u]; funding_paid=funding.v[bo+bl-1u]; }
  double net = sign*(exitp-entry)/unit - cost - funding_paid;
  of.v[ob]=net; of.v[ob+1u]=mae; of.v[ob+2u]=mfe; of.v[ob+3u]=entry; of.v[ob+4u]=unit; of.v[ob+5u]=market_move; of.v[ob+6u]=cost; of.v[ob+7u]=funding_paid;
  oi.v[xb]=endpoint; oi.v[xb+1u]=horizon; oi.v[xb+2u]=ambiguous;
}
"#;
