import time

from PIL import Image

from ultragravity.call_reduction import (
    DeterministicRouter,
    StateChangeDetector,
    TTLCache,
    build_summary_cache_key,
    build_tool_cache_key,
    build_vision_cache_key,
)


def _make_image(path, color):
    image = Image.new("RGB", (64, 64), color=color)
    image.save(path)


def test_state_change_detector_identifies_unchanged_image_and_url(tmp_path):
    image_path = tmp_path / "screen.png"
    _make_image(image_path, color=(10, 20, 30))

    detector = StateChangeDetector(image_distance_threshold=5)
    first = detector.inspect(str(image_path), mode="BROWSER", url="https://example.com")
    second = detector.inspect(str(image_path), mode="BROWSER", url="https://example.com")

    assert first.changed is True
    assert second.changed is False


def test_state_change_detector_identifies_changed_url(tmp_path):
    image_path = tmp_path / "screen.png"
    _make_image(image_path, color=(10, 20, 30))

    detector = StateChangeDetector(image_distance_threshold=5)
    detector.inspect(str(image_path), mode="BROWSER", url="https://example.com/a")
    changed = detector.inspect(str(image_path), mode="BROWSER", url="https://example.com/b")

    assert changed.changed is True
    assert changed.changed_by_url is True


def test_deterministic_router_shortcuts_wait_on_unchanged_state():
    router = DeterministicRouter()
    plan = router.route(
        instruction="Continue task",
        mode="BROWSER",
        state_changed=False,
        last_action="click",
        current_url="https://example.com",
    )

    assert plan is not None
    assert plan["action"] == "wait"


def test_ttl_cache_expires_entries():
    cache = TTLCache(ttl_seconds=1, max_entries=10)
    cache.set("key", {"value": 1})
    assert cache.get("key") == {"value": 1}
    time.sleep(1.1)
    assert cache.get("key") is None


def test_cache_keys_are_deterministic_and_distinct(tmp_path):
    image_path = tmp_path / "screen.png"
    _make_image(image_path, color=(100, 100, 100))

    detector = StateChangeDetector()
    snapshot = detector.inspect(str(image_path), mode="BROWSER", url="https://example.com")

    vision_key_1 = build_vision_cache_key("Find news", snapshot)
    vision_key_2 = build_vision_cache_key("Find news", snapshot)
    vision_key_3 = build_vision_cache_key("Find different", snapshot)

    summary_key_1 = build_summary_cache_key("content", "goal")
    summary_key_2 = build_summary_cache_key("content", "goal")
    summary_key_3 = build_summary_cache_key("other", "goal")

    tool_key_1 = build_tool_cache_key("skill", "ExtractionSkill", {"instruction": "read"})
    tool_key_2 = build_tool_cache_key("skill", "ExtractionSkill", {"instruction": "read"})
    tool_key_3 = build_tool_cache_key("skill", "ExtractionSkill", {"instruction": "other"})

    assert vision_key_1 == vision_key_2
    assert vision_key_1 != vision_key_3

    assert summary_key_1 == summary_key_2
    assert summary_key_1 != summary_key_3

    assert tool_key_1 == tool_key_2
    assert tool_key_1 != tool_key_3
