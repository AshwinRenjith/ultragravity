from ultragravity.memory import MemoryManager, SQLiteMemoryRepository


def test_sqlite_repository_preferences_and_events(tmp_path):
    db_path = tmp_path / "memory.db"
    repo = SQLiteMemoryRepository(db_path=str(db_path), max_events=100)
    repo.initialize()

    repo.set_preference("policy_profile", "strict")
    assert repo.get_preference("policy_profile") == "strict"

    event_id = repo.add_event(
        session_id="session-1",
        kind="task_success",
        content="Summarized latest model updates",
        metadata={"mode": "BROWSER"},
    )
    assert event_id > 0

    recent = repo.list_recent_events(limit=10)
    assert len(recent) == 1
    assert recent[0].content == "Summarized latest model updates"


def test_memory_manager_retrieval_top_k_and_goal_augmentation(tmp_path):
    db_path = tmp_path / "memory.db"
    repo = SQLiteMemoryRepository(db_path=str(db_path), max_events=100)
    manager = MemoryManager(repo, retrieval_top_k=2)

    manager.remember("task_success", "Found deepmind model release notes", {"mode": "BROWSER"})
    manager.remember("summary", "Token optimization strategy documented", {})
    manager.remember("task_failure", "Desktop permission denied once", {})

    facts = manager.retrieve_relevant_facts("model token", top_k=2)
    assert 1 <= len(facts) <= 2

    augmented = manager.augment_goal_with_memory("Summarize model updates", top_k=2)
    assert "Relevant Memory:" in augmented


def test_execution_snapshot_roundtrip(tmp_path):
    db_path = tmp_path / "memory.db"
    repo = SQLiteMemoryRepository(db_path=str(db_path), max_events=100)
    manager = MemoryManager(repo, retrieval_top_k=3)

    payload = {
        "plan_id": "plan-123",
        "current_step_index": 2,
        "aborted": False,
        "completed": False,
    }

    manager.save_execution_state("plan-123", payload)
    loaded = manager.load_execution_state("plan-123")

    assert loaded is not None
    assert loaded["plan_id"] == "plan-123"
    assert loaded["current_step_index"] == 2
