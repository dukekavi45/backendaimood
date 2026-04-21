# 🚀 MoodWave Backend — Deployment & Setup Guide

This is the Flask backend for MoodWave, an AI-powered music recommendation engine.

## 🌐 Live API
**Backend URL**: *(Link your Railway URL here)*  
**Frontend UI**: [aimusicrecommendation.netlify.app](https://aimusicrecommendation.netlify.app)

---

## 🛠️ 1. Database Setup (MySQL)

### LOCAL SETUP
1.  **Install MySQL**: Ensure MySQL Server is installed and running on your machine.
2.  **Create Database**: Open your MySQL terminal/Workbench and run:
    ```sql
    CREATE DATABASE mood_wave;
    ```
3.  **Initialize Schema**: The backend is configured to automatically run `schema.sql` on its first run. Alternatively, you can manually import it:
    ```bash
    mysql -u root -p mood_wave < schema.sql
    ```

### RAILWAY SETUP (Cloud)
1.  In your Railway project, click **+ New** -> **Database** -> **Add MySQL**.
2.  Railway will create the database automatically.
3.  **Link to App**: Go to your Backend service -> **Variables** -> **Add Reference Variable** -> Select **MYSQL_URL**. 
4.  The backend code will detect this and set up the tables automatically on the first deploy.

---

## 🐍 2. Local Development Setup

1.  **Clone & Navigate**:
    ```bash
    cd backend
    ```
2.  **Virtual Environment**:
    ```bash
    python -m venv venv
    venv\Scripts\activate  # Windows
    source venv/bin/activate  # Mac/Linux
    ```
3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
4.  **Environment Variables**:
    Create a `.env` file and fill in:
    - `SECRET_KEY`, `JWT_SECRET`
    - `DB_HOST`, `DB_USER`, `DB_PASSWORD`
    - `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`
    - `YOUTUBE_API_KEY`

5.  **Run Server**:
    ```bash
    python app.py
    ```

---

## ☁️ 3. Deploying to Railway

1.  **Push to GitHub**: Push this `backend/` folder to your GitHub repository.
2.  **Connect to Railway**: 
    - Create a **New Project** on Railway.
    - Connect your GitHub repo.
3.  **Add Variables**: Copy the contents of your `.env` into the **Variables** tab (use the Bulk Import feature).
4.  **Done!**: Railway uses the `railway.toml` and `Procfile` included here to build and start the server automatically.

---

## 🎨 Screenshots
Images of the application are located in the `/images` directory of this repository for documentation.
