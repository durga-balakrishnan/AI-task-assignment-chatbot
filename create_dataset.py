from __future__ import annotations

import pandas as pd


def create_dataset(file_path: str = "employees_tasks.xlsx") -> None:
    employees = [
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
            "availability": "Available",
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
        {
            "employee_id": "EMP004",
            "employee_name": "Vikram Singh",
            "department": "Frontend",
            "skills": "React, JavaScript, UI testing",
            "email": "vikram@example.com",
            "availability": "Available",
            "current_workload": 2,
        },
        {
            "employee_id": "EMP005",
            "employee_name": "Meera Jain",
            "department": "Documentation",
            "skills": "Technical writing, documentation, API docs",
            "email": "meera@example.com",
            "availability": "Busy",
            "current_workload": 6,
        },
        {
            "employee_id": "EMP006",
            "employee_name": "Arjun Patel",
            "department": "Database",
            "skills": "SQL, database validation, PostgreSQL",
            "email": "arjun@example.com",
            "availability": "Available",
            "current_workload": 2,
        },
        {
            "employee_id": "EMP007",
            "employee_name": "Sonia Iyer",
            "department": "Cloud",
            "skills": "AWS, deployment, CI/CD",
            "email": "sonia@example.com",
            "availability": "Available",
            "current_workload": 4,
        },
        {
            "employee_id": "EMP008",
            "employee_name": "Karthik Nair",
            "department": "AI/ML",
            "skills": "NLP, model evaluation, Python",
            "email": "karthik@example.com",
            "availability": "Available",
            "current_workload": 3,
        },
        {
            "employee_id": "EMP009",
            "employee_name": "Deepa Rao",
            "department": "IT Support",
            "skills": "Troubleshooting, network, connectivity",
            "email": "deepa@example.com",
            "availability": "Available",
            "current_workload": 1,
        },
        {
            "employee_id": "EMP010",
            "employee_name": "Nikhil Bose",
            "department": "Frontend",
            "skills": "React, form validation, testing",
            "email": "nikhil@example.com",
            "availability": "Available",
            "current_workload": 5,
        },
    ]

    tasks = [
        {
            "task_id": "TASK001",
            "task_title": "Python API Development",
            "task_description": "Implement and debug the REST API for the internal service.",
            "required_skills": "Python, FastAPI, REST API",
            "department": "Development",
            "priority": "High",
            "deadline": "2026-11-05",
            "status": "Open",
        },
        {
            "task_id": "TASK002",
            "task_title": "REST API Testing",
            "task_description": "Create and run API testing coverage for the service endpoints.",
            "required_skills": "API testing, Selenium, test cases",
            "department": "Testing",
            "priority": "High",
            "deadline": "2026-11-08",
            "status": "Open",
        },
        {
            "task_id": "TASK003",
            "task_title": "Sales Dashboard Creation",
            "task_description": "Create an analytical sales dashboard using Excel and dashboards.",
            "required_skills": "Python, Pandas, SQL, Excel",
            "department": "Data Analytics",
            "priority": "Medium",
            "deadline": "2026-11-12",
            "status": "Open",
        },
        {
            "task_id": "TASK004",
            "task_title": "React UI Improvement",
            "task_description": "Improve the user interface for the web portal and forms.",
            "required_skills": "React, JavaScript, UI testing",
            "department": "Frontend",
            "priority": "Medium",
            "deadline": "2026-11-10",
            "status": "Open",
        },
        {
            "task_id": "TASK005",
            "task_title": "Technical Documentation",
            "task_description": "Document the API and onboarding steps for users and support staff.",
            "required_skills": "Technical writing, documentation, API docs",
            "department": "Documentation",
            "priority": "Low",
            "deadline": "2026-11-15",
            "status": "Open",
        },
        {
            "task_id": "TASK006",
            "task_title": "Database Record Validation",
            "task_description": "Validate and reconcile database records across the reporting tables.",
            "required_skills": "SQL, database validation, PostgreSQL",
            "department": "Database",
            "priority": "High",
            "deadline": "2026-11-07",
            "status": "Open",
        },
        {
            "task_id": "TASK007",
            "task_title": "AWS Application Deployment",
            "task_description": "Deploy the application to AWS and ensure environment health checks.",
            "required_skills": "AWS, deployment, CI/CD",
            "department": "Cloud",
            "priority": "High",
            "deadline": "2026-11-09",
            "status": "Open",
        },
        {
            "task_id": "TASK008",
            "task_title": "NLP Model Evaluation",
            "task_description": "Evaluate the NLP model performance against the business benchmark.",
            "required_skills": "NLP, model evaluation, Python",
            "department": "AI/ML",
            "priority": "High",
            "deadline": "2026-11-11",
            "status": "Open",
        },
        {
            "task_id": "TASK009",
            "task_title": "IT Connectivity Troubleshooting",
            "task_description": "Diagnose connectivity problems for office users and restore service.",
            "required_skills": "Troubleshooting, network, connectivity",
            "department": "IT Support",
            "priority": "High",
            "deadline": "2026-11-06",
            "status": "Open",
        },
        {
            "task_id": "TASK010",
            "task_title": "Frontend Form Testing",
            "task_description": "Verify the frontend form behavior, error handling, and validation rules.",
            "required_skills": "React, form validation, testing",
            "department": "Frontend",
            "priority": "Medium",
            "deadline": "2026-11-14",
            "status": "Open",
        },
    ]

    requests = [
        {"request_text": "Who can develop a Python API?", "expected_task_id": "TASK001", "expected_employee_id": "EMP001"},
        {"request_text": "Assign the API testing task.", "expected_task_id": "TASK002", "expected_employee_id": "EMP002"},
        {"request_text": "Find someone with SQL and database skills.", "expected_task_id": "TASK006", "expected_employee_id": "EMP006"},
        {"request_text": "Assign the AWS deployment task to an available employee.", "expected_task_id": "TASK007", "expected_employee_id": "EMP007"},
        {"request_text": "Who is best for the NLP model evaluation task?", "expected_task_id": "TASK008", "expected_employee_id": "EMP008"},
    ]

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        pd.DataFrame(employees).to_excel(writer, sheet_name="Employees", index=False)
        pd.DataFrame(tasks).to_excel(writer, sheet_name="Tasks", index=False)
        pd.DataFrame(requests).to_excel(writer, sheet_name="Example_Requests", index=False)


if __name__ == "__main__":
    create_dataset()
    print("Dataset created successfully: employees_tasks.xlsx")
