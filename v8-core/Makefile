.PHONY: all bench bench-full bench-quick bench-case clippy test

TAPE ?= ../research/tape/quad-1h-12m/tape.jsonl
ITERATIONS ?= 3

all: bench
	@# Default target: run the data-backed performance benchmark

bench:
	cargo bench --bench benchmark_runner -- --tape "$(TAPE)" --iterations "$(ITERATIONS)"

bench-full:
	cargo bench --bench benchmark_runner -- --tape "$(TAPE)" --iterations 10

bench-quick:
	cargo bench --bench benchmark_runner -- --tape "$(TAPE)" --iterations 1

bench-case:
	@cargo run --quiet --bin v8-core -- bench $(CASE)

clippy:
	@cargo clippy --quiet

test:
	@cargo test --quiet
