@echo off
call .venv\Scripts\activate.bat
echo Running Scrum Team test suite...
python -m pytest tests
pause
