# 🛍️ KindKart: Community Peer-to-Peer Donation Platform

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![Flask](https://img.shields.io/badge/Framework-Flask-green)
![WebSockets](https://img.shields.io/badge/RealTime-Socket.IO-orange)
![Database](https://img.shields.io/badge/Database-PostgreSQL-blue)
![UI](https://img.shields.io/badge/UI-Neobrutalism-ff69b4)

KindKart is an immersive, full-stack web application built to facilitate **community-driven resource allocation**. It functions as an interactive platform where users can donate essential items, respond to local needs, and communicate securely in real-time. Designed as a comprehensive academic project, it showcases robust MVC web architecture, real-time bidirectional communication, and secure relational data modeling.

---

## 🏗️ System Architecture & Workflows

KindKart relies on a structured **MVC (Model-View-Controller)** pattern combined with modern **WebSockets** for real-time functionalities.

### Real-Time Chat & Bidirectional Data Flow
Unlike traditional HTTP systems, KindKart utilizes an **Eventlet-powered WebSocket server** to push chat messages and notifications instantly to clients without page reloads.

```mermaid
sequenceDiagram
    participant Sender as User A (Browser)
    participant Server as Flask + Socket.IO
    participant DB as PostgreSQL
    participant Receiver as User B (Browser)

    Sender->>Server: HTTP POST (sendMessage)
    Note over Server: Validates auth & payload
    Server->>DB: Save Message & Notification
    DB-->>Server: Commit Successful
    Server-->>Sender: 200 OK (HTTP Response)
    Note over Server: WebSockets Push Event
    Server->>Receiver: socket.emit('message', data)
    Receiver->>Receiver: Instantly display in chat!
```

### Full-Stack Architecture
```mermaid
graph TD
    A[Client UI / Browser] -->|HTTP Requests| B[Flask Router / Blueprints]
    B -->|Database Queries| C[(PostgreSQL / SQLite)]
    C -->|ORM Objects| B
    B -->|Jinja2 Templates| A
    
    A <-->|Persistent WebSocket Pipe| D[Eventlet Server / Socket.IO]
    B --> D
```

---

## ✨ Core Features

1. **🔐 Secure Authentication Pipeline**
   - Robust CSRF validation, password hashing via `Bcrypt`, and session continuity using `Flask-Login`.
2. **📢 Dynamic Needs Board & Matchmaking**
   - A centralized hub where individuals broadcast requirements, and donors directly fulfill those needs. Fulfilling needs instantly grants an elevated +20 Reputation Score bonus.
3. **⚡ Real-Time Socket.IO Communication**
   - Persistent bi-directional chat rooms connecting donors and recipients instantly, built on an asynchronous Eventlet engine.
4. **📊 Analytics & Admin Dashboard**
   - Live system-wide metrics integrated with `Chart.js` rendering rich visual analytics for data categories and user engagement ratios.
5. **🏆 Advanced Gamification Engine**
   - Live algorithmic Leaderboard ranking top philanthropists, paired with a dynamically generated, printable "Certificate of Appreciation" for the absolute #1 ranked user.
6. **🤖 Smart Tagging & Algorithmic Filtering**
   - Heuristical text-processing generating dynamic keywords (Smart Tags), alongside advanced contextual tools like "Near Me" location filtering and an automated "Item Expiry" chron-engine.
7. **🎨 Neo-Brutalist Global Design**
   - High-contrast, accessibility-friendly UI with an interactive, natively styled **Global Dark Mode** powered by `localStorage` persistence and dynamic CSS Variables.

---

## 🛠️ Technology Stack

| Layer | Technologies Used |
| :--- | :--- |
| **Backend Framework** | Python 3.8+, Flask, Jinja2 |
| **Database & ORM** | PostgreSQL (Production), SQLite (Local), `Flask-SQLAlchemy` |
| **Real-Time Engine** | `Flask-SocketIO`, `eventlet` |
| **Security & Auth** | `Flask-Bcrypt`, `Flask-WTF`, CSRF Protection |
| **Frontend Utilities** | Vanilla JS, Chart.js, Neo-Brutalist CSS, Google Fonts |
| **Deployment Engine** | `Gunicorn` (WSGI Production Server) |

---

## 💻 Local Setup Instructions

**1. Clone or Download the Repository**
```bash
cd KindKart_
```

**2. Initialize Virtual Environment & Install Dependencies**
```bash
pip install -r requirements.txt
```

**3. Execution (Development Mode)**
KindKart features an auto-migrating database schema. Running the entry point automatically creates the SQLite database.
```bash
python run.py
```
*Access locally at `http://127.0.0.1:5000`*

---

## ☁️ Cloud Deployment (Render.com)

To transition from localhost to a permanent live cloud server with real-time WebSocket support:

1. **Initialize Git & Push to GitHub**:
    ```bash
    git init
    git add .
    git commit -m "Initial Release"
    ```
2. **Deploy via Render**:
    - Connect your GitHub to a new **Web Service** on Render.com
    - **Language**: Python 3
    - **Build Command**: `pip install -r requirements.txt`
    - **Start Command**: 
      ```bash
      gunicorn --worker-class eventlet -w 1 run:app
      ```
    - **Environment Variables**: MUST set `DATABASE_URL` with your PostgreSQL internal/external string. (e.g. `postgresql://user:pass@host/dbname`)
3. **Custom Domain (Optional)**:
    - In Render Dashboard -> Settings -> Custom Domains, input your premium domain and copy the generated DNS records to your registrar. The platform provisions SSL certificates automatically!

---

*Built with ❤️ for a stronger, more connected community.*
