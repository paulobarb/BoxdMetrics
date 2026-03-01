# 📦 BoxdMetrics

## 🎯 Objective
The goal is not just to analyze movie data, but to build a robust, automated, and secure infrastructure to host that analysis.

* **Containerization:** Docker & Docker Compose
* **CI/CD:** GitHub Actions for automated testing and building
* **Security:** Image scanning (Trivy) and dependency checks
* **Cloud:** Deployment to a VPS (AWS/DigitalOcean) with SSL
* **Infrastructure as Code:** Managing environments via config

---

## 🛠 Tech Stack

| Category | Technology | Usage |
| :--- | :--- | :--- |
| **Infrastructure** | **Docker & Compose** | Container orchestration for local & prod |
| **Backend** | **FastAPI (Python)** | REST API to process data |
| **Data Processing** | **Pandas** | ETL for Letterboxd CSV exports |
| **Frontend** | **React** | UI to visualize stats |
| **CI/CD** | **GitHub Actions** | Automated build, test, and lint pipelines |
| **Security** | **Trivy** | Vulnerability scanning for Docker images |
| **Cloud** | **Linux VPS** | Production deployment target |

---

## 🚀 Quick Start

### Prerequisites
* Docker & Docker Compose
* Your Letterboxd `watched.csv` file

### Running the Project
1.  **Clone the repo:**
    ```bash
    git clone [https://github.com/paulobarb/BoxdMetrics.git](https://github.com/paulobarb/BoxdMetrics.git)
    cd BoxdMetrics
    ```

2.  **Add Data:**
    Place your `watched.csv` inside `src/backend/data/`.

3.  **Spin up containers:**
    ```bash
    docker-compose up --build
    ```

4.  **Verify:**
    * API will be running at `http://localhost:8000`
    * Console logs will show the "Total Movies Watched" count.
