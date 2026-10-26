from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

import pandas as pd


AVAILABLE_STATUSES = {"available", "free", "idle"}
BUSY_STATUSES = {"busy", "unavailable", "assigned", "not available"}
TASK_REQUEST_STOP_WORDS = {
    "task",
    "assign",
    "assignment",
    "find",
    "who",
    "can",
    "best",
    "for",
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "available",
    "employee",
}


def normalize_text(value: Any) -> str:
    if value is None or pd.isna(value):
        return ""
    return str(value).strip().lower()


def normalize_skills(value: Any) -> List[str]:
    if value is None or pd.isna(value):
        return []
    if isinstance(value, list):
        skills = value
    else:
        skills = str(value).split(",")
    cleaned = []
    for item in skills:
        skill = str(item).strip()
        if skill:
            cleaned.append(skill.lower())
    return cleaned


def validate_excel_structure(df: pd.DataFrame, required_columns: List[str], sheet_name: str) -> List[str]:
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        return [f"{sheet_name} is missing required column(s): {', '.join(missing)}"]
    return []


def ensure_row_ids(df: pd.DataFrame, column_name: str, sheet_name: str) -> List[str]:
    errors = []
    if column_name not in df.columns:
        return [f"{sheet_name} missing {column_name} column."]
    duplicates = df[df.duplicated(subset=[column_name], keep=False)][column_name].dropna().tolist()
    if duplicates:
        seen = set()
        dup_list = []
        for item in duplicates:
            value = str(item)
            if value not in seen:
                seen.add(value)
                dup_list.append(value)
        errors.append(f"{sheet_name} contains duplicate {column_name} values: {', '.join(dup_list[:5])}")
    return errors


def validate_employee_dataset(df: pd.DataFrame) -> List[str]:
    errors = []
    expected = [
        "employee_id",
        "employee_name",
        "skills",
        "email",
        "availability",
        "current_workload",
    ]
    errors.extend(validate_excel_structure(df, expected, "Employees"))
    errors.extend(ensure_row_ids(df, "employee_id", "Employees"))
    if any(column not in df.columns for column in expected):
        return errors
    for idx, row in df.iterrows():
        if normalize_text(row.get("employee_name")) == "":
            errors.append(f"Employees row {idx + 2} is missing employee_name.")
        if not isinstance(row.get("email", ""), str) or "@" not in str(row.get("email", "")):
            errors.append(f"Employees row {idx + 2} has an invalid email address.")
        if normalize_text(row.get("availability")) == "":
            errors.append(f"Employees row {idx + 2} is missing availability.")
    return errors


def validate_task_dataset(df: pd.DataFrame) -> List[str]:
    errors = []
    expected = [
        "task_id",
        "task_title",
        "task_description",
        "required_skills",
        "priority",
        "deadline",
        "status",
    ]
    errors.extend(validate_excel_structure(df, expected, "Tasks"))
    errors.extend(ensure_row_ids(df, "task_id", "Tasks"))
    if any(column not in df.columns for column in expected):
        return errors
    for idx, row in df.iterrows():
        if normalize_text(row.get("task_title")) == "":
            errors.append(f"Tasks row {idx + 2} is missing task_title.")
        if normalize_text(row.get("required_skills")) == "":
            errors.append(f"Tasks row {idx + 2} is missing required_skills.")
        if normalize_text(row.get("deadline")) == "":
            errors.append(f"Tasks row {idx + 2} is missing deadline.")
    return errors


def normalize_keyword(token: str) -> str:
    token = re.sub(r"[^a-z0-9]+", " ", token.lower()).strip()
    if not token:
        return ""
    if token.endswith("ing") and len(token) > 5:
        return token[:-3]
    if token.endswith("ed") and len(token) > 4:
        return token[:-2]
    return token


def task_match_score(task_row: pd.Series, query_tokens: List[str]) -> int:
    score = 0
    text_sections = {
        "task_title": str(task_row.get("task_title", "")),
        "task_description": str(task_row.get("task_description", "")),
        "required_skills": str(task_row.get("required_skills", "")),
        "department": str(task_row.get("department", "")),
    }

    for section_name, section_value in text_sections.items():
        section_tokens = [normalize_keyword(tok) for tok in re.split(r"\s+", section_value.lower()) if normalize_keyword(tok)]
        section_set = set(section_tokens)
        for token in query_tokens:
            if not token:
                continue
            if token in section_set:
                weight = 5 if section_name == "task_title" else 3 if section_name == "required_skills" else 2 if section_name == "task_description" else 1
                score += weight

    for token in query_tokens:
        if token in TASK_REQUEST_STOP_WORDS:
            continue
        if token in "".join(text_sections.values()).lower():
            score += 1

    return score


def find_task_by_request(tasks_df: pd.DataFrame, request_text: str) -> Dict[str, Any]:
    query = normalize_text(request_text)
    if not query:
        raise ValueError("Request text is required.")

    request_ids = {
        re.sub(r"[^a-z0-9]", "", token.lower())
        for token in re.findall(r"[a-z0-9][a-z0-9_-]*", query, flags=re.IGNORECASE)
    }
    for _, row in tasks_df.iterrows():
        task_id = re.sub(r"[^a-z0-9]", "", str(row.get("task_id", "")).lower())
        if task_id and task_id in request_ids:
            return row.to_dict()

    query_tokens = [normalize_keyword(token) for token in re.split(r"\s+", query) if normalize_keyword(token)]
    query_tokens = [token for token in query_tokens if token not in TASK_REQUEST_STOP_WORDS]

    if len(query_tokens) > 1 and any(token in query for token in [" and ", " or "]):
        raise ValueError("The request is ambiguous. Please specify a single task more clearly.")

    if not query_tokens:
        raise ValueError("Unable to identify the task from the request. Please specify the task more clearly.")

    candidates = []
    for _, row in tasks_df.iterrows():
        score = task_match_score(row, query_tokens)
        task_tokens = {
            normalize_keyword(token)
            for token in re.split(
                r"\s+",
                " ".join(
                    str(row.get(column, ""))
                    for column in (
                        "task_title",
                        "task_description",
                        "required_skills",
                        "department",
                    )
                ),
            )
            if normalize_keyword(token)
        }
        row_dict = row.to_dict()
        row_dict["_match_score"] = score
        row_dict["_matching_query_tokens"] = len(task_tokens.intersection(query_tokens))
        candidates.append(row_dict)

    candidates.sort(key=lambda item: item["_match_score"], reverse=True)
    if len(candidates) > 1 and candidates[0]["_match_score"] == candidates[1]["_match_score"] and candidates[0]["_match_score"] > 0:
        raise ValueError("The request is ambiguous. Please specify a single task more clearly.")

    best_match = candidates[0] if candidates else None
    if (
        best_match is None
        or best_match["_match_score"] <= 2
        or (len(query_tokens) > 1 and best_match["_matching_query_tokens"] < 2)
    ):
        available_titles = [
            str(title).strip()
            for title in tasks_df.get("task_title", pd.Series(dtype=str)).tolist()
            if str(title).strip()
        ]
        if available_titles:
            raise ValueError(
                "Unable to identify that task in the uploaded workbook. Available tasks: "
                + "; ".join(available_titles)
                + ". Please use one of these task names or IDs."
            )
        raise ValueError("Unable to identify the task from the request. Please specify the task more clearly.")

    return best_match


def is_employee_available(employee: Dict[str, Any]) -> bool:
    availability = normalize_text(employee.get("availability"))
    if availability in AVAILABLE_STATUSES:
        return True
    if availability in BUSY_STATUSES or any(
        status in availability for status in ("unavailable", "busy", "not available")
    ):
        return False
    if "available" in availability or "free" in availability:
        return True
    return True


def skill_match_score(employee_skills: List[str], task_skills: List[str]) -> int:
    if not task_skills:
        return 0
    matches = 0
    for skill in task_skills:
        if skill in employee_skills:
            matches += 1
    return matches


def workload_score(employee: Dict[str, Any]) -> float:
    workload = employee.get("current_workload")
    try:
        value = float(workload)
    except (TypeError, ValueError):
        return 0.5
    if value <= 2:
        return 1.0
    if value <= 4:
        return 0.7
    if value <= 6:
        return 0.4
    return 0.2


def department_relevance(employee_department: str, task_department: str) -> float:
    employee_department = normalize_text(employee_department)
    task_department = normalize_text(task_department)
    if not task_department:
        return 0.5
    if employee_department == task_department:
        return 1.0
    if task_department in employee_department or employee_department in task_department:
        return 0.8
    return 0.5


def rank_candidates(employees_df: pd.DataFrame, task: Dict[str, Any], assignment_history: List[Dict[str, Any]] | None = None) -> List[Dict[str, Any]]:
    task_skills = normalize_skills(task.get("required_skills"))
    task_department = str(task.get("department", "")).strip()

    ranked = []
    for _, row in employees_df.iterrows():
        employee = row.to_dict()
        if not is_employee_available(employee):
            continue

        skill_count = skill_match_score(normalize_skills(employee.get("skills")), task_skills)
        total_skills = max(len(task_skills), 1)
        skill_coverage = skill_count / total_skills
        dept_score = department_relevance(employee.get("department", ""), task_department)
        load_score = workload_score(employee)

        final_score = (skill_coverage * 70) + (dept_score * 15) + (load_score * 15)
        ranked.append(
            {
                **employee,
                "skill_count": skill_count,
                "skill_coverage": round(skill_coverage, 2),
                "department_score": round(dept_score, 2),
                "workload_score": round(load_score, 2),
                "final_score": round(final_score, 2),
            }
        )

    ranked.sort(key=lambda item: item["final_score"], reverse=True)
    return ranked


def summarize_candidate(employee: Dict[str, Any], task: Dict[str, Any]) -> str:
    task_title = str(task.get("task_title", "Task"))
    employee_name = str(employee.get("employee_name", "Employee"))
    department = str(employee.get("department", "Department"))
    skills = str(employee.get("skills", ""))
    task_skills = str(task.get("required_skills", ""))
    score = employee.get("final_score", 0)

    return (
        f"{employee_name} is a strong match for {task_title}. "
        f"Their department is {department}, and they bring relevant skills: {skills}. "
        f"This aligns with the task requirements: {task_skills}. "
        f"Overall fit score: {score}."
    )


def validate_email_address(email: str) -> bool:
    pattern = r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$"
    return bool(re.fullmatch(pattern, str(email).strip()))


def explain_no_match(reason: str) -> str:
    return reason


def detect_ambiguous_request(request_text: str, tasks_df: pd.DataFrame) -> bool:
    normalized = normalize_text(request_text)
    if not normalized:
        return True

    query_tokens = [normalize_keyword(token) for token in re.split(r"\s+", normalized) if normalize_keyword(token)]
    query_tokens = [token for token in query_tokens if token not in {"task", "assign", "find", "who", "can", "best", "for", "the", "a", "an", "and", "or", "multiple", "various", "some"}]
    if not query_tokens:
        return False

    matched_tasks = []
    for _, row in tasks_df.iterrows():
        task_text = " ".join(
            [
                str(row.get("task_title", "")),
                str(row.get("task_description", "")),
                str(row.get("required_skills", "")),
            ]
        ).lower()
        matches = 0
        for token in query_tokens:
            if token in task_text:
                matches += 1
        if matches > 0:
            matched_tasks.append(matches)

    return len(matched_tasks) > 1


def create_assignment_history_record(task: Dict[str, Any], employee: Dict[str, Any], email_status: str, status: str = "proposed") -> Dict[str, Any]:
    return {
        "task_id": task.get("task_id"),
        "task_title": task.get("task_title"),
        "employee_id": employee.get("employee_id"),
        "employee_name": employee.get("employee_name"),
        "email": employee.get("email"),
        "deadline": task.get("deadline"),
        "priority": task.get("priority"),
        "status": status,
        "email_status": email_status,
    }
