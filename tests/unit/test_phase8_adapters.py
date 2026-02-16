from ultragravity.tools import BrowserAdapter, DesktopAdapter, SkillAdapter


class MockBrowser:
    def __init__(self):
        self.started = False
        self.navigated = []
        self.actions = []

    def start(self):
        self.started = True

    def navigate(self, url):
        self.navigated.append(url)

    def execute_action(self, action_plan):
        self.actions.append(action_plan)

    def get_screenshot(self, path):
        return path


class MockDesktop:
    def __init__(self):
        self.actions = []

    def execute_action(self, action_plan):
        self.actions.append(action_plan)

    def get_screenshot(self, path):
        return path


class MockSkill:
    def __init__(self, name):
        self.name = name

    def execute(self, params):
        return {"status": "success", "message": "done", "instruction": params.get("instruction")}


def test_browser_adapter_fallback_on_missing_coordinates():
    adapter = BrowserAdapter(MockBrowser())

    result = adapter.execute(
        "execute_action",
        {
            "action_plan": {
                "action": "click",
                "target_element": {"description": "button", "coordinates": []},
            }
        },
    )

    assert result.success is True
    assert result.payload.get("fallback") == "wait"


def test_desktop_adapter_requires_coordinates_for_interactive_actions():
    adapter = DesktopAdapter(MockDesktop())

    result = adapter.execute(
        "execute_action",
        {
            "action_plan": {
                "action": "type",
                "target_element": {"description": "field", "coordinates": []},
            }
        },
    )

    assert result.success is False


def test_skill_adapter_executes_named_skill():
    adapter = SkillAdapter([MockSkill("SearchSkill")])

    result = adapter.execute("execute", {"skill": "SearchSkill", "instruction": "test query"})
    assert result.success is True
    assert result.payload["status"] == "success"
