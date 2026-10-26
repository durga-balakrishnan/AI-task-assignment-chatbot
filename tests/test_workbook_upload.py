from io import BytesIO

import pandas as pd
import pytest

from app import load_uploaded_workbook


class UploadedFile:
    def __init__(self, content: bytes):
        self.content = content

    def getvalue(self) -> bytes:
        return self.content


def create_workbook(headers_with_title_row: bool = False) -> bytes:
    employees = pd.DataFrame(
        [
            ["EMP101", "Test Employee", "Development", "Python, FastAPI", "test@example.com", "Available", 2],
        ],
        columns=[
            "Employee ID",
            "Employee Name",
            "Department",
            "Skills",
            "Email Address",
            "Availability",
            "Current Workload",
        ],
    )
    tasks = pd.DataFrame(
        [
            ["TASK101", "Test API Task", "Implement endpoint", "Python, FastAPI", "Development", "High", "2026-11-05", "Open"],
        ],
        columns=[
            "Task ID",
            "Task Title",
            "Task Description",
            "Required Skills",
            "Department",
            "Priority",
            "Deadline",
            "Status",
        ],
    )

    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        if headers_with_title_row:
            employees.to_excel(writer, sheet_name="Employees", index=False, startrow=2)
            tasks.to_excel(writer, sheet_name="Tasks", index=False, startrow=1)
            employees_ws = writer.sheets["Employees"]
            employees_ws["A1"] = "Employee Roster"
            tasks_ws = writer.sheets["Tasks"]
            tasks_ws["A1"] = "Task List"
        else:
            employees.to_excel(writer, sheet_name="Employees", index=False)
            tasks.to_excel(writer, sheet_name="Tasks", index=False)
    return output.getvalue()


def test_loads_standard_spaced_headers_and_normalizes_columns():
    result = load_uploaded_workbook(UploadedFile(create_workbook()))

    assert result["Employees"].columns.tolist() == [
        "employee_id",
        "employee_name",
        "department",
        "skills",
        "email",
        "availability",
        "current_workload",
    ]
    assert result["Tasks"].columns.tolist() == [
        "task_id",
        "task_title",
        "task_description",
        "required_skills",
        "department",
        "priority",
        "deadline",
        "status",
    ]
    assert result["Employees"].iloc[0]["employee_id"] == "EMP101"


def test_loads_workbook_with_title_rows_before_column_headers():
    result = load_uploaded_workbook(UploadedFile(create_workbook(headers_with_title_row=True)))

    assert len(result["Employees"]) == 1
    assert result["Employees"].iloc[0]["employee_name"] == "Test Employee"
    assert result["Tasks"].iloc[0]["task_id"] == "TASK101"


def test_workbook_without_department_columns_uses_blank_neutral_department():
    output = BytesIO()
    employees = pd.DataFrame(
        [["EMP201", "No Department", "Python, FastAPI", "employee@example.com", "Available", 1]],
        columns=["Employee ID", "Employee Name", "Skills", "Email", "Availability", "Current Workload"],
    )
    tasks = pd.DataFrame(
        [["TASK201", "Task without department", "Description", "Python, FastAPI", "High", "2026-11-05", "Open"]],
        columns=["Task ID", "Task Title", "Task Description", "Required Skills", "Priority", "Deadline", "Status"],
    )
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        employees.to_excel(writer, sheet_name="Employees", index=False)
        tasks.to_excel(writer, sheet_name="Tasks", index=False)

    result = load_uploaded_workbook(UploadedFile(output.getvalue()))

    assert result["Employees"].iloc[0]["department"] == ""
    assert result["Tasks"].iloc[0]["department"] == ""


def test_reports_missing_columns_without_cascading_row_errors():
    employees = pd.DataFrame([{"Employee": "Example"}])
    tasks = pd.DataFrame([{"Task": "Example"}])
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        employees.to_excel(writer, sheet_name="Employees", index=False)
        tasks.to_excel(writer, sheet_name="Tasks", index=False)

    with pytest.raises(ValueError, match="Could not locate recognizable column headers"):
        load_uploaded_workbook(UploadedFile(output.getvalue()))
