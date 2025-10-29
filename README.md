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

Before you begin, you'll need to install the following tools on your machine:

> **Note**: This project uses specific versions of Python and Node.js. If you use version managers like `pyenv` or `nvm`, you can use the included `.python-version` and `.nvmrc` files to automatically switch to the correct versions.

#### Install Docker Desktop

**Download and install Docker Desktop:**

- **Windows**: [Download Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- **Mac**: [Download Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)

#### Install Python

**Required Version: Python 3.11**

**Windows:**

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download Python 3.11.x (latest 3.11 version)
3. Run the installer and **check "Add Python to PATH"**
4. Verify installation:
   ```cmd
   python --version
   ```
   Should show: `Python 3.11.x`

**Mac:**

1. Go to [python.org/downloads](https://www.python.org/downloads/)
2. Download Python 3.11.x (latest 3.11 version)
3. Run the installer
4. Verify installation:
   ```bash
   python3 --version
   ```
   Should show: `Python 3.11.x`

#### Install Node.js

**Required Version: Node.js 18**

**Windows:**

1. Go to [nodejs.org](https://nodejs.org/)
2. Download Node.js 18.x LTS version
3. Run the installer
4. Verify installation:
   ```cmd
   node --version
   npm --version
   ```
   Should show: `v18.x.x`

**Mac:**

1. Go to [nodejs.org](https://nodejs.org/)
2. Download Node.js 18.x LTS version
3. Run the installer
4. Verify installation:
   ```bash
   node --version
   npm --version
   ```
   Should show: `v18.x.x`

### 1. Clone the Repository

**Windows (Command Prompt or PowerShell):**

```cmd
git clone https://github.com/WSU-Software-Development-Club/ai-training.git
cd ai-training
```

**Mac (Terminal):**

```bash
git clone https://github.com/WSU-Software-Development-Club/ai-training.git
cd ai-training
```

### 2. Start Docker Desktop

Make sure Docker Desktop is running before proceeding. You should see the Docker icon in your system tray (Windows) or menu bar (Mac).

### 3. Run the Application

**For development with hot reloading (slow, be patient):**

```bash
docker-compose -f docker-compose.dev.yml up --build
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

**Python not found:**

- **Windows**: Make sure you checked "Add Python to PATH" during installation
- **Mac**: Try using `python3` instead of `python`
- Restart your terminal/command prompt after installation

**Node.js not found:**

- Restart your terminal/command prompt after installation
- Try running `npm` commands from the project directory

**Port already in use:**

- Stop other applications using ports 3000 or 5000
- Use environment variables to override ports (see below)
- Or modify the ports in `docker-compose.yml`

**Permission denied (Mac/Linux):**

```bash
sudo chown -R $USER:$USER .
```

**Windows firewall:**

- Allow Docker through Windows Firewall when prompted

### Port Conflicts

If ports 3000 or 5000 are already in use on your machine, you have several options:

**Important Notes:**

- When changing ports, both frontend and backend ports should be changed together
- CORS origins are automatically configured based on the FRONTEND_PORT
- No manual CORS configuration needed!

#### Option 1: Use Environment Variables (Recommended)

Create a `.env` file in your project root:

```bash
# .env file
BACKEND_PORT=5001
FRONTEND_PORT=3001
```

Then run with environment variables:

**Windows:**

```cmd
set BACKEND_PORT=5001 && set FRONTEND_PORT=3001 && docker-compose up --build
```

**Mac/Linux:**

```bash
BACKEND_PORT=5001 FRONTEND_PORT=3001 docker-compose up --build
```

#### Option 2: Use Different Ports in Docker Compose

Run with port overrides:

```bash
docker-compose up --build -p 5001:5000 -p 3001:3000
```

#### Option 3: Find and Kill the Process Using the Port

**Windows:**

```cmd
# Find what's using port 5000
netstat -ano | findstr :5000

# Kill the process (replace PID with actual process ID)
taskkill /PID <PID> /F
```

**Mac/Linux:**

```bash
# Find what's using port 5000
lsof -i :5000

# Kill the process (replace PID with actual process ID)
kill -9 <PID>
```

#### Option 4: Create a Local Override File

Create `docker-compose.override.yml` (this file is automatically ignored by git):

```yaml
version: "3.8"

services:
  backend:
    ports:
      - "5001:5000"

  frontend:
    ports:
      - "3001:3000"
```

Then just run: `docker-compose up --build`

#### Option 5: Custom CORS Origins (Advanced)

If you need custom CORS origins beyond the automatic configuration:

```bash
# Override CORS origins completely
CORS_ORIGINS="http://localhost:3003,http://127.0.0.1:3003,https://yourdomain.com" docker-compose up --build
```

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
