# AI-Powered Smart Task Assignment Chatbot

This project is a beginner-friendly prototype for assigning tasks to employees based on a dataset in Excel. It uses Streamlit for the UI, Pandas for processing the workbook, and a rule-based task matching engine. Email sending is available with Gmail SMTP and defaults to demo mode for safety.

## Local Ollama explanations

Python rule-based matching remains responsible for task and employee selection. After selection, the app can ask a local Ollama model to explain the recommendation and compare eligible lower-ranked candidates. The LLM does not choose or change the recommended employee. If Ollama is stopped or returns an unusable response, the app shows the existing rule-based explanation instead.

Install and start Ollama on Windows, then pull the model from PowerShell:

```powershell
ollama pull gemma3:4b
ollama serve
```

Ollama normally listens at `http://localhost:11434`. In another PowerShell terminal, verify it is responding:

```powershell
ollama list
Invoke-RestMethod -Method Get -Uri http://localhost:11434/api/tags
```

The model and local endpoint are configurable in `.env`:

```env
OLLAMA_MODEL=gemma3:4b
OLLAMA_ENDPOINT=http://localhost:11434
```

No external LLM service or API key is used. The app sends the selected task and eligible candidates' workbook data to the local Ollama endpoint. Email preview and sending remain separate; an email is sent only after the manager confirms.

In the chatbot page, upload an `.xlsx` workbook with `Employees` and `Tasks` worksheets. Header capitalization and spaces are normalized (for example, `Employee ID` becomes `employee_id`), and title rows above the headers are supported. The workbook's employee and task columns are validated and its data is used for matching and the explanation. Department is optional; if missing, it is left blank and contributes a neutral department score rather than being guessed.

## Architecture

- `app.py`: Streamlit UI and workflow entry point.
- `task_assignment.py`: Validation, task matching, ranking, and duplication logic.
- `email_service.py`: Message generation and SMTP sending.
- `create_dataset.py`: Creates the sample Excel workbook.
- `assignment_history.csv`: Keeps records of assignment attempts and outcomes.

## Setup on Windows

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python create_dataset.py
streamlit run app.py
```

If PowerShell blocks script execution, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

Then activate the virtual environment and continue.

## Email configuration

Create a local `.env` file from `.env.example`:

```powershell
Copy-Item .env.example .env
```

Update `.env` with your Gmail credentials:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_EMAIL=your_authorized_email@gmail.com
SMTP_APP_PASSWORD=your_google_app_password
EMAIL_DEMO_MODE=true
```

Use a Google App Password if 2-Step Verification is enabled. Demo mode is enabled by default so you can preview the email flow without sending real messages.

## Features

- Upload and validate employee/task Excel sheets
- Identify tasks using natural-language requests
- Rank employees based on skills, department, and workload
- Exclude unavailable employees
- Preview assignment email before confirmation
- Send email only after explicit confirmation
- Save assignment history
- Retry failed email submissions for the existing assignment; retries update the history row and preserve the SMTP error message
- Prevent duplicate assignment-history rows for the same task

## Testing

Run:

```powershell
python -m pytest -q
```

Ollama integration tests mock the local HTTP response and connection failure, so the test suite does not require Ollama to be running and never sends email.

## Demo workflow

1. Upload or generate the workbook.
2. Enter a request such as "Who can develop a Python API?"
3. Review the recommended employee and explanation.
4. Preview the email.
5. Click "Confirm and Send Email" to send using SMTP or demo mode.

## Notes

- This is a prototype designed for a one-hour implementation.
- Real email delivery depends on valid SMTP credentials and email provider rules.
- Never commit `.env` files or real passwords to source control.
