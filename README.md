# Library Management System (Flask + DevOps)

A beginner-friendly mini project for college DevOps/CI-CD demonstration.

This project includes:
- Full-stack web app using Flask, HTML, CSS, Bootstrap
- SQLite database with CRUD + issue/return workflow
- Docker containerization
- Jenkins pipeline for CI/CD-style automation
- Git/GitHub workflow steps

---

## 1) Project Folder Structure

```text
library-management-system/
│── app.py
│── requirements.txt
│── Dockerfile
│── Jenkinsfile
│── .gitignore
│── README.md
│
├── db/
│   └── schema.sql
│
├── static/
│   └── css/
│       └── style.css
│
└── templates/
    ├── base.html
    ├── login.html
    ├── dashboard.html
    ├── books.html
    ├── add_book.html
    ├── edit_book.html
    ├── issue_book.html
    └── issued_books.html
```

---

## 2) Features Implemented

1. Admin Login
2. Add Book
3. View Books
4. Update Book Details
5. Delete Book
6. Search Books
7. Issue Book
8. Return Book
9. Dashboard with totals
10. Responsive UI (Bootstrap)

---

## 3) Tech Stack

- Frontend: HTML, CSS, Bootstrap
- Backend: Python Flask
- Database: SQLite (easy for local setup)
- DevOps: Git, Docker, Jenkins

---

## 4) Local Setup (Windows + VS Code)

### Prerequisites
- Python 3.10+
- Git
- Docker Desktop
- Jenkins (local or server)

### Steps

1. Open terminal in project folder.
2. Create and activate virtual environment:

```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the app:

```bash
python app.py
```

5. Open browser:

```text
http://localhost:5000
```

### Demo Login Credentials
- Username: `admin`
- Password: `admin123`

---

## 5) Database Setup

The app auto-creates tables on first run via [`db.create_all()`](app.py:301).

Optional manual schema is provided in [`db/schema.sql`](db/schema.sql).

If you want to load sample SQL manually (SQLite CLI):

```bash
sqlite3 library.db ".read db/schema.sql"
```

---

## 6) Docker Setup

### Build Docker Image

```bash
docker build -t library-management-system:latest .
```

### Run Docker Container

```bash
docker run -d --name lms-app -p 5000:5000 library-management-system:latest
```

### Stop and Remove Container

```bash
docker stop lms-app
docker rm lms-app
```

---

## 7) Jenkins Pipeline Setup

[`Jenkinsfile`](Jenkinsfile) includes stages:
1. Clone Repository
2. Install Dependencies
3. Build Docker Image
4. Run Docker Container

### Jenkins Configuration Steps

1. Open Jenkins dashboard.
2. Create **New Item** → **Pipeline**.
3. In pipeline config:
   - Select **Pipeline script from SCM**
   - SCM: Git
   - Repository URL: your GitHub repo URL
   - Script Path: `Jenkinsfile`
4. Save and click **Build Now**.
5. Check console output for each stage.

> Note: Current [`Jenkinsfile`](Jenkinsfile) uses `bat` commands for Windows Jenkins nodes.

---

## 8) Git + GitHub Commands

```bash
git init
git add .
git commit -m "Initial commit: Library Management System with Docker and Jenkins"
git branch -M main
git remote add origin https://github.com/<your-username>/library-management-system.git
git push -u origin main
```

---

## 9) CI/CD Workflow (Simple Explanation)

1. Developer pushes code to GitHub.
2. Jenkins pulls latest code.
3. Jenkins installs dependencies.
4. Jenkins builds Docker image.
5. Jenkins runs updated container.
6. Application becomes available on configured host/port.

This automates build and deployment basics for a mini project demonstration.

---

## 10) Sample Screenshots Description (For Report)

Include these screenshots in your college submission:

1. **Login Page** – admin login form
2. **Dashboard** – cards showing total/issued/available books
3. **Books List** – table with search, edit, delete options
4. **Add Book Page** – form to add new book
5. **Issue Book Page** – borrower + book selection
6. **Issued Books Page** – return action and status badges
7. **Docker Running** – `docker ps` showing `lms-app`
8. **Jenkins Build Console** – successful pipeline stages

---

## 11) Common Errors and Fixes

### Error: `ModuleNotFoundError: No module named 'flask'`
**Fix:**
```bash
pip install -r requirements.txt
```

### Error: Port 5000 already in use
**Fix:** Stop old process/container or use different port:
```bash
docker run -d --name lms-app -p 5001:5000 library-management-system:latest
```

### Error: Jenkins `docker` not recognized
**Fix:**
- Install Docker on Jenkins machine
- Add Docker to system PATH
- Restart Jenkins service

### Error: Git push rejected (authentication)
**Fix:**
- Use GitHub Personal Access Token instead of password
- Verify remote URL and permissions

---

## 12) Viva Questions and Answers

1. **What is Flask?**
   Flask is a lightweight Python web framework used to build web applications quickly.

2. **Why did you use SQLite?**
   SQLite is serverless and easy for beginners, ideal for mini projects.

3. **What is SQLAlchemy?**
   SQLAlchemy is an ORM that maps Python classes to database tables.

4. **What is CRUD in this project?**
   Create, Read, Update, Delete operations on books.

5. **What is Docker?**
   Docker packages application + dependencies into a container for consistent execution.

6. **Why use Jenkins?**
   Jenkins automates build and deployment steps after code changes.

7. **What does CI/CD mean?**
   CI = Continuous Integration, CD = Continuous Delivery/Deployment.

8. **What are pipeline stages in your Jenkinsfile?**
   Clone repo, install dependencies, build Docker image, run container.

9. **How is security handled in this mini project?**
   Basic session login is used for demo; production should use hashed passwords and proper auth.

10. **How does issue/return work?**
    Issuing decreases available quantity; returning increases it and marks record returned.

---

## 13) Important Notes for College Submission

- Keep screenshots of running app + Docker + Jenkins.
- Explain each stage of [`Jenkinsfile`](Jenkinsfile) in viva.
- Mention that this project demonstrates full DevOps flow at beginner level.
- For production, improve auth, validation, testing, and deployment strategy.

---

## 14) Main Entry Files

- Flask app: [`app.py`](app.py)
- Docker config: [`Dockerfile`](Dockerfile)
- Jenkins pipeline: [`Jenkinsfile`](Jenkinsfile)
- Dependencies: [`requirements.txt`](requirements.txt)
- SQL schema: [`db/schema.sql`](db/schema.sql)

