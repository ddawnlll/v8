"""Complete-run cache contracts: hits must be exact and complete."""
from __future__ import annotations

from dataclasses import asdict

from v8.experts.failed_breakout import FailedBreakoutExpert
from v8.experts.trend_pullback import TrendPullbackExpert
from v8.lab import Lab
from v8.schema import ExperimentManifest
from v8.synth import make_synthetic_tape


def _manifest(tape):
    return ExperimentManifest(
        experiment_id='fast-cache-test', code_hash='', data_hash='',
        universe=('SOLUSDT',), start_ns=tape[0].event_time,
        end_ns=tape[-1].event_time)


def test_complete_run_cache_restores_byte_identical_artifacts(tmp_path):
    tape = make_synthetic_tape(seed=19, n_bars=180)
    experts = [TrendPullbackExpert(), FailedBreakoutExpert()]
    cache = tmp_path / 'cache'

    first_dir = tmp_path / 'first'
    first = Lab(first_dir)
    first.ingest(tape)
    report_a = first.run(_manifest(tape), experts, cache_dir=cache)
    artifacts_a = {
        name: (first_dir / name).read_bytes()
        for name in ('candidates.jsonl', 'evaluations.jsonl',
                     'outcomes.jsonl', 'states.jsonl', 'manifest.json',
                     'report.json')
    }

    second_dir = tmp_path / 'second'
    second = Lab(second_dir)
    second.ingest(tape)
    report_b = second.run(_manifest(tape), experts, cache_dir=cache)
    artifacts_b = {
        name: (second_dir / name).read_bytes()
        for name in artifacts_a
    }

    assert asdict(report_b) == asdict(report_a)
    assert artifacts_b == artifacts_a


def test_complete_run_cache_does_not_cross_manifest_changes(tmp_path):
    tape = make_synthetic_tape(seed=23, n_bars=80)
    cache = tmp_path / 'cache'
    experts = [TrendPullbackExpert()]

    first = Lab(tmp_path / 'first')
    first.ingest(tape)
    first.run(_manifest(tape), experts, cache_dir=cache)

    second = Lab(tmp_path / 'second')
    second.ingest(tape)
    changed = ExperimentManifest(
        experiment_id='fast-cache-test', code_hash='', data_hash='',
        universe=('SOLUSDT',), start_ns=tape[0].event_time,
        end_ns=tape[-1].event_time, round_trip_cost_r=0.11)
    second.run(changed, experts, cache_dir=cache)

    complete_dirs = [p for p in cache.iterdir()
                     if p.is_dir() and (p / 'candidates.jsonl').is_file()]
    assert len(complete_dirs) == 2
    assert list((cache / 'states').glob('*.pkl'))


def test_restored_hardlink_detaches_before_append(tmp_path):
    tape = make_synthetic_tape(seed=29, n_bars=90)
    experts = [TrendPullbackExpert()]
    cache = tmp_path / 'cache'
    first = Lab(tmp_path / 'first')
    first.ingest(tape)
    first.run(_manifest(tape), experts, cache_dir=cache)

    second = Lab(tmp_path / 'second')
    second.ingest(tape)
    second.run(_manifest(tape), experts, cache_dir=cache)
    complete_dir = next(p for p in cache.iterdir()
                        if (p / 'candidates.jsonl').is_file())
    cached = complete_dir / 'candidates.jsonl'
    before = cached.read_bytes()
    second.candidates.append({
        'source': 'test', 'event_id': 'cow', 'kind': 'test'})
    assert cached.read_bytes() == before


def test_state_cache_survives_manifest_only_change(tmp_path, monkeypatch):
    tape = make_synthetic_tape(seed=31, n_bars=120)
    experts = [TrendPullbackExpert()]
    cache = tmp_path / 'cache'

    first = Lab(tmp_path / 'first')
    first.ingest(tape)
    first.run(_manifest(tape), experts, cache_dir=cache)

    import v8.lab as lab_module

    def unexpected_state_build(*args, **kwargs):
        raise AssertionError('state cache was not used')

    monkeypatch.setattr(lab_module, 'build_multi_state', unexpected_state_build)
    second = Lab(tmp_path / 'second')
    second.ingest(tape)
    changed = ExperimentManifest(
        experiment_id='fast-cache-test', code_hash='', data_hash='',
        universe=('SOLUSDT',), start_ns=tape[0].event_time,
        end_ns=tape[-1].event_time, round_trip_cost_r=0.11)
    second.run(changed, experts, cache_dir=cache)
