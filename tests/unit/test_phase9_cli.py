from pathlib import Path

from ultragravity.cli import _collect_approval_stats, _collect_telemetry_stats, _handle_policy_command


def test_collect_approval_stats(tmp_path):
    audit_dir = tmp_path / "audit"
    audit_dir.mkdir(parents=True)
    (audit_dir / "actions-20260216.jsonl").write_text(
        "\n".join(
            [
                '{"event_type":"permission_outcome","permission":{"approved":true}}',
                '{"event_type":"permission_outcome","permission":{"approved":false}}',
                '{"event_type":"policy_decision","decision":{"allow":true}}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    stats = _collect_approval_stats(audit_dir)
    assert stats["prompted"] == 2
    assert stats["approved"] == 1
    assert stats["denied"] == 1


def test_collect_telemetry_stats(tmp_path):
    telemetry_dir = tmp_path / "telemetry"
    telemetry_dir.mkdir(parents=True)
    (telemetry_dir / "provider-20260216.jsonl").write_text(
        "\n".join(
            [
                '{"provider":"gemini","estimated_tokens":100,"actual_tokens":80,"success":true}',
                '{"provider":"gemini","estimated_tokens":90,"actual_tokens":0,"success":false}',
                '{"provider":"mistral","estimated_tokens":70,"actual_tokens":60,"success":true}',
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    stats = _collect_telemetry_stats(telemetry_dir)
    assert stats["gemini"]["requests"] == 2
    assert stats["gemini"]["successes"] == 1
    assert stats["gemini"]["failures"] == 1
    assert stats["gemini"]["actual_tokens"] == 80
    assert stats["mistral"]["requests"] == 1


def test_policy_command_set_and_read(tmp_path):
    config_path = tmp_path / "config.yaml"
    db_path = tmp_path / "memory.db"
    config_path.write_text(
        "\n".join(
            [
                "memory:",
                "  enabled: true",
                "  backend: sqlite",
                f"  sqlite_path: {db_path}",
                "  max_events: 100",
                "  retrieval_top_k: 5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    set_code = _handle_policy_command("balanced", str(config_path))
    assert set_code == 0

    read_code = _handle_policy_command(None, str(config_path))
    assert read_code == 0


def test_policy_command_invalid_value(tmp_path):
    config_path = tmp_path / "config.yaml"
    db_path = tmp_path / "memory.db"
    config_path.write_text(
        "\n".join(
            [
                "memory:",
                "  enabled: true",
                "  backend: sqlite",
                f"  sqlite_path: {db_path}",
                "  max_events: 100",
                "  retrieval_top_k: 5",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    code = _handle_policy_command("invalid-profile", str(config_path))
    assert code == 2
