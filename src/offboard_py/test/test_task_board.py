from offboard_py.task_catalog import parse_tasks


def test_parse_tasks_uses_defaults_only_when_requested():
    base_tasks = parse_tasks('', use_defaults_when_empty=True)
    popup_tasks = parse_tasks('[]', use_defaults_when_empty=False)

    assert len(base_tasks) == 4
    assert popup_tasks == []
