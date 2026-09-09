//! Fetch venue instrument definitions through the upstream Nautilus adapter.
//! Public data only: this command accepts no credentials and submits no orders.
use anyhow::{bail, Context};
use nautilus_binance::{
    common::enums::{BinanceEnvironment, BinanceProductType},
    futures::http::client::BinanceFuturesHttpClient,
};
use nautilus_core::time::get_atomic_clock_realtime;
use nautilus_model::instruments::Instrument;
use std::{fs::OpenOptions, io::Write, path::PathBuf};

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    if args.len() != 2 {
        bail!("usage: nautilus_instruments <instrument-id> <new-output.json>");
    }
    let path = PathBuf::from(&args[1]);
    if path.exists() {
        bail!("refusing to overwrite {}", path.display());
    }
    let client = BinanceFuturesHttpClient::new(
        BinanceProductType::UsdM,
        BinanceEnvironment::Live,
        get_atomic_clock_realtime(),
        None,
        None,
        None,
        None,
        Some(30),
        None,
        false,
    )?;
    let instruments = client.request_instruments().await?;
    let instrument = instruments
        .into_iter()
        .find(|instrument| instrument.id().to_string() == args[0])
        .with_context(|| format!("instrument {} absent from Binance response", args[0]))?;
    let bytes = serde_json::to_vec_pretty(&instrument)?;
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .open(&path)?;
    file.write_all(&bytes)?;
    file.sync_all()?;
    println!(
        "Saved {} through nautilus-binance 0.63.0 to {}",
        args[0],
        path.display()
    );
    println!("Current venue metadata; not historical specification or account fee certification.");
    Ok(())
}
