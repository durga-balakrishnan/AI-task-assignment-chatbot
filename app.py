import os
import hashlib
import re
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

import email_service
import ollama_explainer
import task_assignment


DATASET_FILE = "employees_tasks.xlsx"
HISTORY_FILE = "assignment_history.csv"


def ensure_files() -> None:
    if not os.path.exists(DATASET_FILE):
        from create_dataset import create_dataset

        create_dataset(DATASET_FILE)
    if not os.path.exists(HISTORY_FILE):
        pd.DataFrame(
            columns=[
                "task_id",
                "task_title",
                "employee_id",
                "employee_name",
                "recipient",
                "deadline",
                "priority",
                "assignment_time",
                "status",
                "email_status",
            ]
        ).to_csv(HISTORY_FILE, index=False)


def load_data() -> Dict[str, pd.DataFrame]:
    ensure_files()
    workbook = pd.ExcelFile(DATASET_FILE)
    data = {}
    for sheet in workbook.sheet_names:
        data[sheet] = pd.read_excel(DATASET_FILE, sheet_name=sheet)
    return data


def load_history() -> pd.DataFrame:
    if not os.path.exists(HISTORY_FILE):
        return pd.DataFrame(
            columns=[
                "task_id",
                "task_title",
                "employee_id",
                "employee_name",
                "recipient",
                "deadline",
                "priority",
                "assignment_time",
                "status",
                "email_status",
                "email_error",
            ]
        )
    history = pd.read_csv(HISTORY_FILE)
    if "email_error" not in history.columns:
        history["email_error"] = ""
    return history


def latest_task_history(history: pd.DataFrame, task_id: Any) -> tuple[int, pd.Series] | None:
    if history.empty or "task_id" not in history.columns:
        return None
    normalized_id = str(task_id).strip().casefold()
    task_rows = history[
        history["task_id"].astype(str).str.strip().str.casefold() == normalized_id
    ]
    if task_rows.empty:
        return None
    if "assignment_time" in task_rows.columns:
        timestamps = pd.to_datetime(task_rows["assignment_time"], errors="coerce", utc=True)
        if timestamps.notna().any():
            latest_timestamp = timestamps.max()
            latest_rows = task_rows.loc[timestamps[timestamps == latest_timestamp].index]
            row_index = int(latest_rows.index[-1])
            return row_index, history.loc[row_index]
    row_index = int(task_rows.index[-1])
    return row_index, history.loc[row_index]


def is_assignment_complete(record: pd.Series) -> bool:
    email_status = str(record.get("email_status", "")).strip().casefold()
    assignment_status = str(record.get("status", "")).strip().casefold()
    return email_status in {"successful", "success", "sent"} or assignment_status in {
        "completed",
        "complete",
        "done",
        "closed",
    }


def save_history(record: Dict[str, Any]) -> bool:
    history = load_history()
    if latest_task_history(history, record.get("task_id")) is not None:
        return False
    history = pd.concat([history, pd.DataFrame([record])], ignore_index=True)
    history.to_csv(HISTORY_FILE, index=False)
    return True


def update_history_row(row_index: int, updates: Dict[str, Any]) -> bool:
    history = load_history()
    if row_index not in history.index:
        return False
    for column, value in updates.items():
        history.loc[row_index, column] = value
    history.to_csv(HISTORY_FILE, index=False)
    return True


def display_dashboard(data: Dict[str, pd.DataFrame], history: pd.DataFrame) -> None:
    employees = data.get("Employees", pd.DataFrame())
    tasks = data.get("Tasks", pd.DataFrame())
    assigned = history[history["status"].astype(str).str.lower().isin(["confirmed", "sent", "completed"])].copy()
    successful_emails = history[history["email_status"].astype(str).str.lower().isin(["sent", "success", "successful"])].copy()

    st.subheader("Dashboard")
    cols = st.columns(6)
    cols[0].metric("Total employees", len(employees))
    cols[1].metric("Available employees", len(employees[employees["availability"].astype(str).str.lower().str.contains("available")]))
    cols[2].metric("Total tasks", len(tasks))
    cols[3].metric("Unassigned tasks", len(tasks))
    cols[4].metric("Confirmed assignments", len(assigned))
    cols[5].metric("Successful emails", len(successful_emails))


def render_dataset_tabs(data: Dict[str, pd.DataFrame]) -> None:
    st.subheader("Employee Dataset")
    employees = data.get("Employees", pd.DataFrame())
    if not employees.empty:
        st.dataframe(employees, use_container_width=True)

    st.subheader("Task Dataset")
    tasks = data.get("Tasks", pd.DataFrame())
    if not tasks.empty:
        st.dataframe(tasks, use_container_width=True)


def render_history(history: pd.DataFrame) -> None:
    st.subheader("Assignment History")
    if history.empty:
        st.info("No assignment history yet.")
        return
    st.dataframe(history, use_container_width=True)


def render_settings() -> None:
    config = email_service.get_email_config()
    ollama_config = ollama_explainer.get_ollama_config()
    st.subheader("Settings")
    st.write("Email configuration status:")
    st.write({
        "SMTP host configured": bool(config["host"]),
        "SMTP email configured": bool(config["email"].strip()),
        "SMTP password configured": bool(
            config["email"].strip()
            and config["password"].strip()
            and config["password"].strip().upper() != "PASTE_APP_PASSWORD_HERE"
        ),
        "Demo mode": config["demo_mode"],
    })
    st.write("Local Ollama explanation configuration:")
    st.write({
        "Model": ollama_config["model"],
        "Endpoint": ollama_config["endpoint"],
        "API key required": False,
    })


def load_uploaded_workbook(uploaded_file: Any) -> Dict[str, pd.DataFrame]:
    try:
        workbook = pd.ExcelFile(BytesIO(uploaded_file.getvalue()))
        required_sheets = {"Employees", "Tasks"}
        sheet_lookup = {str(sheet).strip().casefold(): sheet for sheet in workbook.sheet_names}
        missing_sheets = {
            sheet for sheet in required_sheets if sheet.casefold() not in sheet_lookup
        }
        if missing_sheets:
            raise ValueError(f"Workbook is missing worksheet(s): {', '.join(sorted(missing_sheets))}")

        def read_sheet(sheet_name: str, canonical_columns: Dict[str, List[str]]) -> pd.DataFrame:
            actual_sheet_name = sheet_lookup[sheet_name.casefold()]
            raw = pd.read_excel(workbook, sheet_name=actual_sheet_name, header=None)
            aliases = {
                re.sub(r"[^a-z0-9]", "", alias.casefold()): canonical
                for canonical, names in canonical_columns.items()
                for alias in [canonical, *names]
            }

            def normalize_headers(row: pd.Series) -> List[str]:
                normalized = []
                for value in row:
                    key = re.sub(r"[^a-z0-9]", "", str(value).strip().casefold())
                    normalized.append(aliases.get(key, ""))
                return normalized

            header_row = None
            normalized_header = None
            expected_count = len(canonical_columns)
            for row_index in range(min(len(raw), 15)):
                candidate = normalize_headers(raw.iloc[row_index])
                matches = sum(bool(column) for column in candidate)
                if matches >= max(2, expected_count // 2):
                    header_row = row_index
                    normalized_header = candidate
                    break

            if header_row is None or normalized_header is None:
                raise ValueError(
                    f"Could not locate recognizable column headers in the {actual_sheet_name} worksheet. "
                    "Check the worksheet's header row and required columns."
                )

            data = raw.iloc[header_row + 1 :].copy()
            data.columns = normalized_header
            data = data.loc[:, [column for column in data.columns if column]]
            data = data.dropna(how="all").reset_index(drop=True)
            return data

        employee_columns = {
            "employee_id": ["employee id", "staff id", "id"],
            "employee_name": ["employee name", "name", "staff name"],
            "department": ["department", "team"],
            "skills": ["skill", "skill set", "expertise", "skills/expertise"],
            "email": ["email address", "email id", "e-mail"],
            "availability": ["availability", "available status", "status"],
            "current_workload": ["current workload", "workload", "current tasks"],
        }
        task_columns = {
            "task_id": ["task id", "id"],
            "task_title": ["task title", "title", "task name"],
            "task_description": ["task description", "description", "details"],
            "required_skills": ["required skills", "skills required", "skills"],
            "department": ["department", "team"],
            "priority": ["priority"],
            "deadline": ["deadline", "due date"],
            "status": ["status", "task status"],
        }
        data = {
            "Employees": read_sheet("Employees", employee_columns),
            "Tasks": read_sheet("Tasks", task_columns),
        }
        for frame in data.values():
            if "department" not in frame.columns:
                frame["department"] = ""

        errors = task_assignment.validate_employee_dataset(data["Employees"])
        errors.extend(task_assignment.validate_task_dataset(data["Tasks"]))
        if errors:
            raise ValueError("; ".join(errors))
        return data
    except (ValueError, OSError, ImportError) as exc:
        raise ValueError(f"Could not use uploaded workbook: {exc}") from exc


def show_assignment_result(
    task: Dict[str, Any],
    employee: Dict[str, Any],
    email_details: Dict[str, str],
    explanation: str,
    explanation_source: str,
) -> None:
    st.success("Recommendation ready")
    st.subheader("Recommended Employee")
    st.write(f"Employee: {employee.get('employee_name')}")
    st.write(f"Department: {employee.get('department')}")
    st.write(f"Email: {employee.get('email')}")
    st.write(f"Availability: {employee.get('availability')}")
    st.write(f"Current workload: {employee.get('current_workload')}")
    st.write(f"Matching score: {employee.get('final_score', 'N/A')}")
    st.write(f"Skill coverage: {employee.get('skill_coverage', 'N/A')}")
    st.write(f"Reason ({explanation_source}):")
    st.write(explanation)

    st.subheader("Email Preview")
    st.write(f"To: {email_details['recipient']}")
    st.write(f"Subject: {email_details['subject']}")
    st.text_area("Message", email_details['body'], height=250)


def suggest_task(request_text: str, tasks_df: pd.DataFrame) -> Dict[str, Any]:
    return task_assignment.find_task_by_request(tasks_df, request_text)


def main() -> None:
    st.set_page_config(page_title="AI-Powered Smart Task Assignment Chatbot", layout="wide")
    st.title("AI-Powered Smart Task Assignment Chatbot")

    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "last_assignment" not in st.session_state:
        st.session_state.last_assignment = None

    with st.sidebar:
        st.header("Navigation")
        pages = ["Dashboard", "Task Assignment Chatbot", "Employee Dataset", "Task Dataset", "Assignment History", "Settings"]
        page = st.radio("Go to", pages, index=1)

    data = load_data()
    history = load_history()

    if page == "Dashboard":
        display_dashboard(data, history)
    elif page == "Employee Dataset":
        render_dataset_tabs(data)
    elif page == "Task Dataset":
        render_dataset_tabs(data)
    elif page == "Assignment History":
        render_history(history)
    elif page == "Settings":
        render_settings()
    else:
        st.subheader("Task Assignment Chatbot")
        for message in st.session_state.chat_history:
            st.write(message)

        uploaded_file = st.file_uploader("Upload employee/task workbook (.xlsx)", type=["xlsx"])
        assignment_data = data
        dataset_signature = "default"
        if uploaded_file is not None:
            try:
                dataset_signature = hashlib.sha256(uploaded_file.getvalue()).hexdigest()
                assignment_data = load_uploaded_workbook(uploaded_file)
                st.success(f"Using uploaded workbook: {uploaded_file.name}")
            except ValueError as exc:
                st.error(str(exc))
                assignment_data = {}

        prompt = st.text_input("Enter your assignment request:")
        if prompt:
            tasks_df = assignment_data.get("Tasks", pd.DataFrame())
            if tasks_df.empty:
                if uploaded_file is None:
                    st.error("No task dataset found.")
            else:
                try:
                    task = suggest_task(prompt, tasks_df)
                    latest_entry = latest_task_history(history, task.get("task_id"))
                    if latest_entry is not None and is_assignment_complete(latest_entry[1]):
                        st.info("This task already has a successful or completed assignment and cannot be assigned again.")
                        st.dataframe(
                            pd.DataFrame([latest_entry[1]]).drop(
                                columns=["email_error"], errors="ignore"
                            ),
                            use_container_width=True,
                        )
                    elif latest_entry is not None:
                        history_index, previous_assignment = latest_entry
                        st.warning("The latest email attempt failed. Retry will use the same assigned employee and task details.")
                        st.write(f"Assigned employee: {previous_assignment.get('employee_name', '')}")
                        recipient = str(previous_assignment.get("recipient", "")).strip()
                        if not recipient:
                            recipient = str(previous_assignment.get("email", "")).strip()
                        st.write(f"Recipient: {recipient or 'Missing from assignment history'}")
                        prior_error_value = previous_assignment.get("email_error", "")
                        prior_error = (
                            ""
                            if pd.isna(prior_error_value)
                            else str(prior_error_value).strip()
                        )
                        if prior_error:
                            st.error(f"Previous email error: {prior_error}")

                        if st.button("Retry Sending Email", key=f"retry-email-{task.get('task_id')}"):
                            employee_name = str(previous_assignment.get("employee_name", "")).strip()
                            if not employee_name:
                                employee_name = recipient or "Employee"
                            if not recipient or not task_assignment.validate_email_address(recipient):
                                send_result = {
                                    "success": False,
                                    "message": "The recipient email in assignment history is missing or invalid.",
                                }
                            else:
                                send_result = email_service.send_assignment_email(
                                    task.get("task_title", "Task"),
                                    task.get("task_description", "No description"),
                                    task.get("priority", "Medium"),
                                    task.get("deadline", "TBD"),
                                    employee_name,
                                    recipient,
                                )

                            update_history_row(
                                history_index,
                                {
                                    "email_status": "Successful" if send_result.get("success") else "Failed",
                                    "email_error": "" if send_result.get("success") else send_result.get("message", "Email failed to send."),
                                },
                            )
                            st.rerun()
                    else:
                        employees_df = assignment_data.get("Employees", pd.DataFrame())
                        candidates = task_assignment.rank_candidates(employees_df, task)
                        if not candidates:
                            st.warning("No suitable employee is available for this task. Check employee availability and workload in the uploaded workbook.")
                        else:
                            selected = candidates[0]
                            explanation_key = (
                                prompt,
                                str(task.get("task_id")),
                                str(selected.get("employee_id")),
                                str(selected.get("final_score")),
                                dataset_signature,
                            )
                            cached_assignment = st.session_state.last_assignment
                            if cached_assignment and cached_assignment.get("explanation_key") == explanation_key:
                                explanation_result = cached_assignment["explanation_result"]
                            else:
                                explanation_result = ollama_explainer.explain_assignment(task, candidates)
                            email_details = email_service.build_assignment_email(
                                task.get("task_title", "Task"),
                                task.get("task_description", "No description"),
                                task.get("priority", "Medium"),
                                task.get("deadline", "TBD"),
                                selected.get("employee_name", "Employee"),
                                selected.get("email", ""),
                            )
                            st.session_state.last_assignment = {
                                "task": task,
                                "employee": selected,
                                "email_details": email_details,
                                "explanation_key": explanation_key,
                                "explanation_result": explanation_result,
                            }
                            show_assignment_result(
                                task,
                                selected,
                                email_details,
                                explanation_result["explanation"],
                                explanation_result["source"],
                            )
                            if explanation_result.get("fallback_reason"):
                                st.caption(f"Local Ollama was unavailable; showing the rule-based explanation. ({explanation_result['fallback_reason']})")
                            st.session_state.chat_history.append(f"User: {prompt}")
                            st.session_state.chat_history.append(f"Assistant: Recommended {selected.get('employee_name')} for {task.get('task_title')}")

                            if st.button(
                                "Confirm and Send Email",
                                key=f"confirm-email-{task.get('task_id')}",
                                disabled=latest_task_history(load_history(), task.get("task_id")) is not None,
                            ):
                                if not selected.get("email") or not task_assignment.validate_email_address(selected.get("email")):
                                    st.error("Recipient email is invalid.")
                                else:
                                    send_result = email_service.send_assignment_email(
                                        task.get("task_title", "Task"),
                                        task.get("task_description", "No description"),
                                        task.get("priority", "Medium"),
                                        task.get("deadline", "TBD"),
                                        selected.get("employee_name", "Employee"),
                                        selected.get("email", ""),
                                    )
                                    email_status = "Successful" if send_result.get("success") else "Failed"
                                    record = {
                                        "task_id": task.get("task_id"),
                                        "task_title": task.get("task_title"),
                                        "employee_id": selected.get("employee_id"),
                                        "employee_name": selected.get("employee_name"),
                                        "recipient": selected.get("email"),
                                        "deadline": task.get("deadline"),
                                        "priority": task.get("priority"),
                                        "assignment_time": pd.Timestamp.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
                                        "status": "Confirmed",
                                        "email_status": email_status,
                                        "email_error": "" if send_result.get("success") else send_result.get("message", "Email failed to send."),
                                    }
                                    saved = save_history(record)
                                    if not saved:
                                        st.warning("An assignment record already exists for this task. No duplicate history row was added.")
                                    if send_result.get("success"):
                                        st.success(send_result.get("message", "Email sent successfully."))
                                    else:
                                        st.error(f"Email error: {send_result.get('message', 'Email failed to send.')}")

                            if st.button("Cancel Assignment"):
                                st.info("Assignment cancelled.")
                except ValueError as exc:
                    st.error(str(exc))


if __name__ == "__main__":
    main()
