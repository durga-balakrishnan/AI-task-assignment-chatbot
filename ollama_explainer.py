from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from dotenv import load_dotenv

import task_assignment


DEFAULT_MODEL = "gemma3:4b"
DEFAULT_ENDPOINT = "http://localhost:11434"
DEFAULT_TIMEOUT_SECONDS = 30

load_dotenv()


def get_ollama_config() -> Dict[str, str]:
    return {
        "model": os.getenv("OLLAMA_MODEL", DEFAULT_MODEL).strip() or DEFAULT_MODEL,
        "endpoint": os.getenv("OLLAMA_ENDPOINT", DEFAULT_ENDPOINT).rstrip("/"),
    }


def _fallback_explanation(task: Dict[str, Any], selected: Dict[str, Any], candidates: List[Dict[str, Any]]) -> str:
    explanation = task_assignment.summarize_candidate(selected, task)
    lower_ranked = candidates[1:]
    if lower_ranked:
        comparisons = []
        for candidate in lower_ranked[:3]:
            comparisons.append(
                f"{candidate.get('employee_name')} ranked lower with a score of "
                f"{candidate.get('final_score')}; skill coverage "
                f"{candidate.get('skill_coverage')}, department relevance "
                f"{candidate.get('department_score')}, and workload score "
                f"{candidate.get('workload_score')}."
            )
        explanation += " Eligible alternatives: " + " ".join(comparisons)
    return explanation


def _employee_facts(employee: Dict[str, Any], task: Dict[str, Any], selected: Dict[str, Any]) -> Dict[str, str]:
    name = str(employee.get("employee_name"))
    department = str(employee.get("department"))
    skills = task_assignment.normalize_skills(employee.get("skills"))
    required_skills = task_assignment.normalize_skills(task.get("required_skills"))
    matched_skills = [skill for skill in required_skills if skill in skills]
    skill_coverage = employee.get("skill_coverage")
    final_score = employee.get("final_score")
    employee_id = str(employee.get("employee_id"))
    facts = {
        f"{employee_id}_availability": f"{name} is marked {employee.get('availability')} in the workbook.",
        f"{employee_id}_workload": f"{name}'s recorded current workload is {employee.get('current_workload')}.",
        f"{employee_id}_department": (
            f"{name}'s department ({department}) matches the task department."
            if task_assignment.normalize_text(department) == task_assignment.normalize_text(task.get("department"))
            else f"{name}'s department is {department}; the task department is {task.get('department')}."
        ),
        f"{employee_id}_skills": (
            f"{name}'s recorded skills match {len(matched_skills)} of {len(required_skills)} required skills"
            + (f": {', '.join(matched_skills)}." if matched_skills else ".")
        ),
        f"{employee_id}_coverage": f"{name}'s rule-based skill coverage is {skill_coverage}.",
        f"{employee_id}_score": f"{name}'s rule-based matching score is {final_score}.",
    }
    if employee_id == str(selected.get("employee_id")):
        facts[f"{employee_id}_selected"] = (
            f"The Python rule-based matcher selected {name} for {task.get('task_title')}."
        )
    else:
        facts[f"{employee_id}_ranked_lower"] = (
            f"{name} ranked below the selected employee with a rule-based score of {final_score}."
        )
    return facts


def _build_prompt(task: Dict[str, Any], candidates: List[Dict[str, Any]]) -> str:
    selected = candidates[0]
    lower_candidates = candidates[1:]
    context = {
        "task": {
            key: task.get(key)
            for key in (
                "task_id",
                "task_title",
                "task_description",
                "required_skills",
                "department",
                "priority",
                "deadline",
            )
        },
        "selected_employee": {
            key: selected.get(key)
            for key in (
                "employee_id",
                "employee_name",
                "department",
                "skills",
                "availability",
                "current_workload",
                "skill_coverage",
                "department_score",
                "workload_score",
                "final_score",
            )
        },
        "eligible_alternatives_ranked_lower": [
            {
                key: candidate.get(key)
                for key in (
                    "employee_id",
                    "employee_name",
                    "department",
                    "skills",
                    "availability",
                    "current_workload",
                    "skill_coverage",
                    "department_score",
                    "workload_score",
                    "final_score",
                )
            }
            for candidate in lower_candidates[:3]
        ],
    }
    return (
        "Use only the supplied workbook facts in the JSON below. Do not invent or change any employee details, skills, availability, workload, scores, departments, deadlines, or task requirements. "
        "Do not recommend a different employee. Explain in plain English why the selected employee is suitable for the task and, if relevant, why lower-ranked eligible employees ranked lower. "
        "The selected employee is the Python rule-based recommendation and must not be overridden. Use only these facts and keep the answer brief but clear.\n\n"
        f"Assignment data:\n{json.dumps(context, ensure_ascii=False, default=str)}"
    )


def explain_assignment(
    task: Dict[str, Any],
    ranked_candidates: List[Dict[str, Any]],
    model: Optional[str] = None,
    endpoint: Optional[str] = None,
    timeout: int = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, str]:
    eligible_candidates = [
        candidate
        for candidate in ranked_candidates
        if task_assignment.is_employee_available(candidate)
    ]
    if not eligible_candidates:
        raise ValueError("No available employee can be explained as a recommendation.")

    selected = eligible_candidates[0]
    fallback = _fallback_explanation(task, selected, eligible_candidates)
    config = get_ollama_config()
    selected_model = model or config["model"]
    selected_endpoint = (endpoint or config["endpoint"]).rstrip("/")
    request_body = json.dumps(
        {
            "model": selected_model,
            "prompt": _build_prompt(task, eligible_candidates),
            "stream": False,
        }
    ).encode("utf-8")
    request = Request(
        f"{selected_endpoint}/api/generate",
        data=request_body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
        explanation = result.get("response", "").strip()
        if not explanation:
            raise ValueError("Ollama returned an empty explanation.")
        return {
            "explanation": explanation,
            "source": "Ollama",
            "model": selected_model,
        }
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, ValueError) as exc:
        return {
            "explanation": fallback,
            "source": "Rule-based fallback",
            "model": selected_model,
            "fallback_reason": str(exc),
        }
