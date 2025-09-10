# React Flask Web App

A simple web application with a React.js frontend and Flask backend, containerized with Docker.

## Project Structure

```
├── backend/           # Flask backend
│   ├── routes/        # API routes
│   ├── utils/         # Utility functions
│   ├── app.py         # Main Flask application
│   ├── config.py      # Configuration settings
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/          # React.js frontend
│   ├── src/
│   │   ├── pages/     # Page components
│   │   ├── components/ # Reusable components
│   │   ├── constants/ # CSS variables and config
│   │   ├── services/  # API calls
│   │   └── utils/     # Helper functions
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml # Docker orchestration
└── README.md
```

## Getting Started

### Prerequisites

Before you begin, you'll need to install Docker Desktop on your machine:

#### Install Docker Desktop

**Download and install Docker Desktop:**

- **Windows**: [Download Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- **Mac**: [Download Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)

### 1. Clone the Repository

**Windows (Command Prompt or PowerShell):**

```cmd
git clone https://github.com/yourusername/ai-training.git
cd ai-training
```

**Mac (Terminal):**

```bash
git clone https://github.com/yourusername/ai-training.git
cd ai-training
```

### 2. Start Docker Desktop

Make sure Docker Desktop is running before proceeding. You should see the Docker icon in your system tray (Windows) or menu bar (Mac).

### 3. Run the Application

**For development with hot reloading (extra dev feautres):**

```bash
docker-compose -f docker-compose.dev.yml up --build
```

**Or use the regular compose file:**

```bash
docker-compose up --build
```

### 4. Access the Application

Once the containers are running, you can access:

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:5000

### Development

#### Hot Reloading (Recommended)

The Docker setup includes hot reloading for both frontend and backend:

- **Frontend**: React's Fast Refresh automatically updates the UI when you save changes
- **Backend**: Flask's debug mode with `use_reloader=True` automatically restarts the server when you save Python files

Use the development compose file for the best experience:

```bash
docker-compose -f docker-compose.dev.yml up --build
```

#### Running Services Individually

For development, you can also run the services individually (Not Recommended):

#### Backend (Flask)

**Windows:**

```cmd
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

**Mac:**

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

#### Frontend (React)

**Windows:**

```cmd
cd frontend
npm install
npm start
```

**Mac:**

```bash
cd frontend
npm install
npm start
```

## Troubleshooting

### Common Issues

**Docker not starting:**

- Make sure Docker Desktop is installed and running
- Restart Docker Desktop if it's not responding

**Port already in use:**

- Stop other applications using ports 3000 or 5000
- Or modify the ports in `docker-compose.yml`

**Permission denied (Mac/Linux):**

```bash
sudo chown -R $USER:$USER .
```

**Windows firewall:**

- Allow Docker through Windows Firewall when prompted

### Stopping the Application

**Stop Docker containers:**

```bash
docker-compose down
```

**Stop and remove all containers and volumes:**

```bash
docker-compose down -v
```

## API Endpoints

- `GET /` - Returns a welcome message
- `GET /about` - Returns application information
- `GET /api/health` - Returns the health status of the backend
- `GET /api/status` - Returns detailed application status

## Technologies Used

- **Backend**: Flask (Python)
- **Frontend**: React.js
- **Containerization**: Docker & Docker Compose
- **Package Management**: pip (Python), npm (Node.js)
