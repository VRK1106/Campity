# Campity: Priority-Driven Peer-to-Peer Task Management for Campus 🚀

Campity is an innovative, campus-exclusive web platform designed to resolve the recurring problem of urgent, last-minute student errands (like printing or parcel pickup) through a secure and accountable peer-to-peer network.

It transforms disorganized social requests into a reliable, efficient system, directly supporting a more productive and collaborative "**Smart Education**" environment.

---

## ✨ Key Features & Technical Highlights

This project goes beyond basic application development by demonstrating technical excellence in several critical areas:

### 1. Intelligent Task Prioritization (Priority Queue)
The core technical innovation is the use of a **Priority Queue** (implemented using Python's `heapq` module) to dynamically sort available tasks.

* **Logic:** Tasks are assigned priority based on critical factors: **Task Category** (e.g., 'Medical' tasks are prioritized highest) and the specified **Reward** value.
* **Benefit:** This ensures the most **urgent, high-value requests** are always displayed at the top of the available feed, maximizing response time and overall platform efficiency.

### 2. Comprehensive Accountability & Trust Protocol
Trust and reliability are built directly into the system's workflow:

* **Reward/Favor Exchange:** Tasks clearly specify the compensation, whether it's a **Cash** amount or a detailed **Favor** (text description).
* **Status Enforcement:** The unique task status, **`awaiting_rating`**, is enforced when a helper reports completion. This prevents task abandonment and forces the poster to finalize the transaction.
* **Peer-Based Rating System:** Features a full **1-5 star rating system** where the poster rates the helper's performance. The system then calculates the helper's overall **average rating**, providing a clear measure of their reputation and discouraging misuse.

### 3. Dynamic Task Management
* **Secure File Handling:** Tasks support secure file uploads (e.g., documents for printing). Files are saved to a central `uploads` directory, and the acceptor can securely download the required file via a dedicated route.
* **Dynamic Posting Form:** The task creation form dynamically adjusts inputs (Number or Text) based on the chosen reward type, ensuring clean data capture.
* **Streamlined Deadlines:** Deadlines are user-friendly, automatically defaulting to the current date and requiring the user to only input the necessary time.

---

## 💻 Tech Stack & Dependencies

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Backend Framework** | **Python 3.10+ / Flask** | Lightweight core for routing and application logic. |
| **Data Structures** | **Python `heapq`** | Implements the **Priority Queue** for intelligent task sorting. |
| **Database/ORM** | **SQLite / Flask-SQLAlchemy** | Efficient, object-oriented database management. |
| **Security** | **Flask-Bcrypt** | Secure hashing of user passwords. |
| **Frontend** | **HTML / Jinja2 / Tailwind CSS** | Server-side rendering for dynamic content and modern, responsive design. |

---

## 🛠️ Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone [Your GitHub Repo Link]
    cd Campity
    ```

2.  **Create and Activate Virtual Environment:**
    ```bash
    python -m venv venv
    # On Windows
    .\venv\Scripts\activate.bat
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Database Initialization (Crucial Step!):**
    You must delete any existing `campity.db` file to ensure the application creates a fresh database with the correct schema (including `category` and `file_path` columns).
    ```bash
    # Manually delete campity.db if it exists.
    python app.py
    ```

5.  **Run the Application:**
    ```bash
    python app.py
    ```
    The application will be accessible at `http://127.0.0.1:5000/`.

---

## 🎓 Project Contributors

* **Reshekumar V** - (Lead Developer / [Your Focus Area])
* **Rishapthi J** - (e.g., Frontend Specialist / Database Modeling)
* **Pon Prathakshana G** - (e.g., Priority Queue Implementation)
* **Naveen S** - (e.g., Security & Authentication)

---

## 📄 License

This project is licensed under the **MIT License**.
