import json
from io import BytesIO
from urllib.error import URLError
from unittest.mock import patch

import ollama_explainer


def make_assignment_data():
    task = {
        "task_id": "TASK001",
        "task_title": "Python API Development",
        "task_description": "Implement the REST API.",
        "required_skills": "Python, FastAPI, REST API",
        "department": "Development",
        "priority": "High",
        "deadline": "2026-11-05",
    }
    candidates = [
        {
            "employee_id": "EMP001",
            "employee_name": "Ananya Raman",
            "department": "Development",
            "skills": "Python, FastAPI, REST API",
            "availability": "Available",
            "current_workload": 2,
            "skill_coverage": 1.0,
            "department_score": 1.0,
            "workload_score": 1.0,
            "final_score": 100.0,
        },
        {
            "employee_id": "EMP002",
            "employee_name": "Rahul Kumar",
            "department": "Testing",
            "skills": "API testing",
            "availability": "Available",
            "current_workload": 4,
            "skill_coverage": 0.0,
            "department_score": 0.5,
            "workload_score": 0.7,
            "final_score": 25.5,
        },
    ]
    return task, candidates


def test_successful_ollama_explanation_uses_configured_local_model():
    task, candidates = make_assignment_data()
    response = BytesIO(
        json.dumps(
            {
                "response": "Ananya Raman is suitable because her recorded skills include Python, FastAPI, and REST API, and the task requires exactly those skills. Rahul Kumar ranked lower because his available skills do not match the task as closely."
            }
        ).encode()
    )

    with patch.object(ollama_explainer, "urlopen", return_value=response) as mocked_urlopen:
        result = ollama_explainer.explain_assignment(
            task,
            candidates,
            model="gemma3:4b",
            endpoint="http://localhost:11434",
        )

    assert result["source"] == "Ollama"
    assert result["model"] == "gemma3:4b"
    assert "Ananya Raman" in result["explanation"]
    assert "FastAPI" in result["explanation"]
    assert "Rahul Kumar" in result["explanation"]
    request = mocked_urlopen.call_args.args[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert payload["model"] == "gemma3:4b"
    assert "EMP001" in payload["prompt"]
    assert "EMP002" in payload["prompt"]
    request = mocked_urlopen.call_args.args[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert payload["model"] == "gemma3:4b"
    assert "EMP001" in payload["prompt"]
    assert "EMP002" in payload["prompt"]


def test_ollama_connection_failure_returns_rule_based_fallback():
    task, candidates = make_assignment_data()
    with patch.object(ollama_explainer, "urlopen", side_effect=URLError("connection refused")):
        result = ollama_explainer.explain_assignment(task, candidates)

    assert result["source"] == "Rule-based fallback"
    assert "Ananya Raman" in result["explanation"]
    assert "Eligible alternatives" in result["explanation"]
    assert "connection refused" in result["fallback_reason"]


def test_busy_or_unavailable_employee_is_never_selected_for_explanation():
    task, candidates = make_assignment_data()
    candidates[0]["availability"] = "Currently Unavailable"

    with patch.object(ollama_explainer, "urlopen", side_effect=URLError("connection refused")):
        result = ollama_explainer.explain_assignment(task, candidates)

    assert "Rahul Kumar" in result["explanation"]
    assert "Ananya Raman" not in result["explanation"]


def test_no_available_candidate_is_rejected():
    task, candidates = make_assignment_data()
    for candidate in candidates:
        candidate["availability"] = "Busy"

    try:
        ollama_explainer.explain_assignment(task, candidates)
        assert False, "Expected no eligible candidate to be rejected"
    except ValueError as exc:
        assert "No available employee" in str(exc)
