# Smart Task Management System (Sankar Group Assignment)

A secure, responsive Python and Flask-based web application featuring user authentication, REST APIs, PostgreSQL storage, real-time WebSocket notifications, and a Pandas/NumPy-driven analytics module.

---

## 🚀 Key Features

1. **Authentication (Flask)**
   * Complete user registration and login/logout system.
   * Naive cookie session-based route security with custom decorators.

2. **REST API Development**
   * High-performance endpoints for adding, updating, and deleting tasks.
   * Schema: Title, Description, Priority (Low/Medium/High), Status (Pending/Completed), and Created Date.

3. **PostgreSQL Integration**
   * Fully organized relational schema for storing user identities and task items.
   * Auto-initialization of tables using SQLAlchemy ORM.

4. **Analytics Dashboard (Pandas & NumPy)**
   * High-performance data computations on task collections.
   * Displays live metrics for: **Total Tasks**, **Completed Tasks**, **Pending Tasks**, and **Completion Rate (%)**.

5. **WebSocket Feature (Flask-SocketIO)**
   * Instant socket pipeline between client and server.
   * Pushes real-time alerts to the user interface when tasks are created, updated, or deleted.

6. **Glassmorphic Frontend (HTML5 & CSS3)**
   * Ambient responsive layout styled with modern CSS variables, soft blurs, neon state accents, and smooth slide animations.

---

## 🛠️ Technology Stack

* **Backend:** Python 3.13+, Flask, Flask-SQLAlchemy, Flask-SocketIO
* **Database:** PostgreSQL (with `psycopg2-binary` driver)
* **Analytics Engine:** Pandas, NumPy
* **Frontend:** HTML5, CSS3 (Vanilla), Vanilla JS + Socket.IO Client CDN

---

## ⚙️ Project Setup Guide

Follow these steps to set up and launch the project on your machine:

### 1. Setup Virtual Environment & Install Dependencies
First, create a virtual environment and install the required dependencies:

1. Create a Python virtual environment:
   ```bash
   python -m venv venv
   ```
2. Activate the virtual environment:
   * **Windows (PowerShell):**
     ```powershell
     .\venv\Scripts\Activate.ps1
     ```
   * **Windows (CMD):**
     ```cmd
     .\venv\Scripts\activate.bat
     ```
   * **Mac/Linux:**
     ```bash
     source venv/bin/activate
     ```
3. Install the required libraries:
   ```bash
   pip install -r requirements.txt
   ```

### 2. Configure Environment Variables
Copy the `.env.example` template to a new file named `.env` in the root directory:
* On Windows (CMD):
  ```cmd
  copy .env.example .env
  ```
* On Windows (PowerShell):
  ```powershell
  copy .env.example .env
  ```
* On Mac/Linux:
  ```bash
  cp .env.example .env
  ```
*(Note: You do not need to fill in database credentials here. Leave `DATABASE_URL` blank so that the application setup wizard can configure it for you).*

### 3. Run the Application
1. Start the Flask application:
   ```bash
   python app.py
   ```
2. The server will run at: **`http://localhost:5000`**

### 4. Run the Database Setup Wizard
1. Open your web browser and navigate to `http://localhost:5000`.
2. Since the database is not yet configured, you will be redirected to the secure **Database Setup** wizard.
3. Input your PostgreSQL connection parameters:
   * **Host:** `localhost`
   * **Port:** `5432`
   * **Database Name:** The name of the database you want to use (e.g. `task_db`).
   * **Username:** Your PostgreSQL username (e.g. `postgres`).
   * **Password:** Your PostgreSQL password.
4. Click **Save & Connect**.
5. The application will:
   * Test the connection to your PostgreSQL server.
   * **Auto-create the database** on your server if it does not exist yet.
   * Auto-provision the relational schema (tables).
   * Save the connection settings back to your git-ignored `.env` file for future runs.
   * Redirect you to the login screen where you can register or sign in!

---

## 📂 Project Structure

```
ShankarGroup_assessment/
├── static/
│   ├── css/
│   │   └── style.css       # Premium CSS stylesheet
│   └── js/
│       └── app.js          # REST API integrations & Socket.IO listener
├── templates/
│   ├── base.html           # Master layout template
│   ├── auth.html           # Glassmorphic Login/Register screen
│   └── dashboard.html      # Responsive workspace with live analytics
├── .env                    # Active configurations (git-ignored)
├── .env.example            # Environment configuration template
├── analytics.py            # Pandas & NumPy analysis logic
├── app.py                  # Main application router and server configuration
├── config.py               # Settings loader
├── models.py               # SQLAlchemy Database schemas
├── requirements.txt        # Backend dependencies
├── schema.sql              # Raw PostgreSQL DDL queries
└── Python Development Internship Assignment.pdf
```
