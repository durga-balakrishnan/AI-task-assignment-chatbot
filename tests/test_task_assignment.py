import pandas as pd

from task_assignment import (
    detect_ambiguous_request,
    find_task_by_request,
    rank_candidates,
    validate_email_address,
)


def make_tasks():
    return pd.DataFrame(
        [
            {
                "task_id": "TASK001",
                "task_title": "Python API Development",
                "task_description": "Implement and debug the REST API.",
                "required_skills": "Python, FastAPI, REST API",
                "department": "Development",
                "priority": "High",
                "deadline": "2026-11-05",
                "status": "Open",
            },
            {
                "task_id": "TASK002",
                "task_title": "REST API Testing",
                "task_description": "Create and run API test cases.",
                "required_skills": "API testing, Selenium, test cases",
                "department": "Testing",
                "priority": "High",
                "deadline": "2026-11-08",
                "status": "Open",
            },
        ]
    )


def make_employees():
    return pd.DataFrame(
        [
            {
                "employee_id": "EMP001",
                "employee_name": "Ananya Raman",
                "department": "Development",
                "skills": "Python, FastAPI, REST API",
                "email": "ananya@example.com",
                "availability": "Available",
                "current_workload": 2,
            },
            {
                "employee_id": "EMP002",
                "employee_name": "Rahul Kumar",
                "department": "Testing",
                "skills": "API testing, Selenium, test cases",
                "email": "rahul@example.com",
                "availability": "Busy",
                "current_workload": 1,
            },
            {
                "employee_id": "EMP003",
                "employee_name": "Priya S",
                "department": "Data Analytics",
                "skills": "Python, Pandas, SQL, Excel",
                "email": "priya@example.com",
                "availability": "Available",
                "current_workload": 3,
            },
        ]
    )


def test_api_task_identification():
    task = find_task_by_request(make_tasks(), "Who can develop a Python API?")
    assert task["task_id"] == "TASK001"


def test_api_testing_task_identification():
    task = find_task_by_request(make_tasks(), "Assign the API testing task")
    assert task["task_id"] == "TASK002"


def test_short_task_id_is_identified_from_uploaded_workbook():
    tasks = pd.DataFrame(
        [
            {
                "task_id": "T001",
                "task_title": "Python API Development",
                "task_description": "Implement the API.",
                "required_skills": "Python, FastAPI",
                "department": "Development",
                "priority": "High",
                "deadline": "2026-11-05",
                "status": "Open",
            }
        ]
    )

    task = find_task_by_request(tasks, "Assign T001 to Durga Balakrishnan")

    assert task["task_id"] == "T001"


def test_database_setup_request_matches_an_existing_workbook_task():
    tasks = pd.DataFrame(
        [
            {
                "task_id": "TASK_DB",
                "task_title": "Database Setup",
                "task_description": "Set up the application database.",
                "required_skills": "SQL, PostgreSQL",
                "department": "Database",
                "priority": "High",
                "deadline": "2026-11-10",
                "status": "Open",
            }
        ]
    )

    task = find_task_by_request(tasks, "Assign Database Setup to an available employee")

    assert task["task_id"] == "TASK_DB"


def test_database_setup_does_not_false_match_database_record_validation():
    tasks = pd.DataFrame(
        [
            {
                "task_id": "TASK006",
                "task_title": "Database Record Validation",
                "task_description": "Validate database records.",
                "required_skills": "SQL, database validation, PostgreSQL",
                "department": "Database",
                "priority": "High",
                "deadline": "2026-11-07",
                "status": "Open",
            }
        ]
    )

    try:
        find_task_by_request(tasks, "Assign Database Setup to an available employee")
        assert False, "Expected Database Setup not to be confused with record validation"
    except ValueError as exc:
        assert "Database Record Validation" in str(exc)


def test_skill_based_employee_matching():
    employee_rank = rank_candidates(make_employees(), {"required_skills": "Python, FastAPI, REST API", "department": "Development"})
    assert employee_rank[0]["employee_id"] == "EMP001"


def test_prior_assignment_does_not_make_employee_ineligible_for_other_tasks():
    employees = make_employees()
    task = {"required_skills": "Python, FastAPI, REST API", "department": "Development"}
    history = [{"task_id": "TASK002", "employee_id": "EMP001"}]

    ranked = rank_candidates(employees, task, history)

    assert ranked[0]["employee_id"] == "EMP001"


def test_excluding_busy_employees():
    employee_rank = rank_candidates(make_employees(), {"required_skills": "API testing, Selenium, test cases", "department": "Testing"})
    assert all(employee["employee_id"] != "EMP002" for employee in employee_rank)


def test_excluding_unavailable_employee_with_qualified_status():
    employees = make_employees()
    employees.loc[0, "availability"] = "Currently Unavailable"
    ranked = rank_candidates(employees, {"required_skills": "Python, FastAPI, REST API", "department": "Development"})
    assert all(employee["employee_id"] != "EMP001" for employee in ranked)


def test_invalid_email_address():
    assert validate_email_address("invalid-email") is False
    assert validate_email_address("ananya@example.com") is True


def test_ambiguous_requests():
    assert detect_ambiguous_request("Python and testing tasks", make_tasks()) is True


def test_missing_skills():
    employees = make_employees().copy()
    employees.loc[0, "skills"] = ""
    task = {"required_skills": "Python, FastAPI, REST API", "department": "Development"}
    ranked = rank_candidates(employees, task)
    assert len(ranked) >= 1


def test_unknown_task_request():
    try:
        find_task_by_request(make_tasks(), "Develop a unicorn blockchain app")
        assert False, "Expected ValueError for unknown task"
    except ValueError as exc:
        assert "Available tasks:" in str(exc)
        assert "Python API Development" in str(exc)

    try:
        find_task_by_request(make_tasks(), "API and testing")
        assert False, "Expected ValueError for ambiguous request"
    except ValueError:
        pass
