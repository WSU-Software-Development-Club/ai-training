# Flask Backend Guide: Learning Flask with the NCAA API

## Table of Contents

1. [What is a Backend?](#what-is-a-backend)
2. [Python Basics for Flask](#python-basics-for-flask)
3. [Flask Basics](#flask-basics)
4. [Working with APIs](#working-with-apis)
5. [Project Structure](#project-structure)
6. [Routes vs Service Functions](#routes-vs-service-functions)
7. [Error Handling](#error-handling)
8. [Implementation Example](#implementation-example)
9. [Next Steps](#next-steps)

## What is a Backend?

A **backend** is the server-side part of a web application that handles data processing, business logic, and communication with external services (like APIs). Think of it as the "engine" that powers your web application.

### How Backend Interacts with Frontend

```
Frontend (React) → HTTP Request → Backend (Flask) → External API → Backend → JSON Response → Frontend
```

1. **Frontend** sends a request (like "get me championship winners")
2. **Backend** receives the request and processes it
3. **Backend** may fetch data from external APIs
4. **Backend** returns data as JSON to the frontend
5. **Frontend** displays the data to the user

## Python Basics for Flask

Coming from C/C++, here are the key Python concepts you need:

### Functions

```python
# Python function (similar to C functions)
def get_championship_winners():
    return "Alabama won in 2020"

# Function with parameters
def add_numbers(a, b):
    return a + b

# Function with default parameters
def greet(name="World"):
    return f"Hello, {name}!"
```

### Dictionaries (Key-Value Pairs)

```python
# Similar to C++ std::map or C structs
team_data = {
    "name": "Alabama",
    "year": 2020,
    "conference": "SEC"
}

# Access values
print(team_data["name"])  # Output: Alabama
print(team_data.get("year", "Unknown"))  # Safe access with default

# Add new key-value pairs
team_data["coach"] = "Nick Saban"
```

### JSON (JavaScript Object Notation)

JSON is a text format for storing and exchanging data. It looks like Python dictionaries:

```python
# This is JSON data (as a string)
json_string = '{"name": "Alabama", "year": 2020}'

# Convert JSON string to Python dictionary
import json
data = json.loads(json_string)
print(data["name"])  # Output: Alabama

# Convert Python dictionary to JSON string
team_info = {"name": "Alabama", "year": 2020}
json_output = json.dumps(team_info)
print(json_output)  # Output: {"name": "Alabama", "year": 2020}
```

### Making HTTP Requests

```python
import requests

# Make a GET request to an API
response = requests.get("https://api.example.com/data")

# Check if request was successful
if response.status_code == 200:
    data = response.json()  # Convert JSON response to Python dictionary
    print(data)
else:
    print(f"Error: {response.status_code}")
```

## Flask Basics

Flask is a lightweight web framework for Python. It's like having a web server that can respond to HTTP requests.

### Creating a Flask App

```python
from flask import Flask

# Create Flask application instance
app = Flask(__name__)

# Define a route (URL endpoint)
@app.route('/')
def home():
    return "Hello, World!"

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
```

### Defining Routes

Routes define what happens when someone visits a specific URL:

```python
@app.route('/api/teams')
def get_teams():
    return {"teams": ["Alabama", "Georgia", "Ohio State"]}

@app.route('/api/teams/<team_id>')
def get_team(team_id):
    return {"team_id": team_id, "name": "Alabama"}
```

### Returning JSON

Flask automatically converts Python dictionaries to JSON:

```python
from flask import jsonify

@app.route('/api/champions')
def get_champions():
    champions = [
        {"year": 2020, "team": "Alabama"},
        {"year": 2019, "team": "LSU"}
    ]
    return jsonify(champions)  # Returns JSON response
```

### Importing Modules

```python
# Import entire module
import requests
import json

# Import specific functions
from flask import Flask, jsonify, request

# Import from your own files
from services.history_service import get_championship_winners
```

## Working with APIs

### What is an API?

An **API (Application Programming Interface)** is a way for different software applications to communicate with each other. In our case, we'll use the Henrygd NCAA API to get college football data.

### How the NCAA API Works

The Henrygd NCAA API provides college football data through simple HTTP GET requests. You make a request using the same path structure as the URL on ncaa.com, and you get a JSON response.

**Base URL**: `https://ncaa-api.henrygd.me/`

#### Example API Endpoints:

1. **Rankings**: `rankings/football/fbs/associated-press`

   - Returns AP Top 25 rankings
   - Example: GET request to get current rankings

2. **History**: `history/football/fbs`

   - Returns championship winners from past years
   - Example: GET request to get all-time champions

3. **Stats**: `stats/football/fbs/current/team/{stat_category_id}`
   - Returns statistics for a specific stat category (not individual teams)
   - The "team" in the URL means it's team-level statistics, but the ID is a stat category
   - Example: `stats/football/fbs/current/team/785` returns blocked field goals stats for all teams

#### Understanding Stats API Categories and Pagination

The stats API uses category IDs to specify what type of statistics to return. Here are some common stat categories:

- **21**: Total Offense (yards per game)
- **22**: Total Defense (yards allowed per game)
- **701**: 3rd Down Conversion Pct Defense
- **785**: Blocked Field Goals
- **28**: Scoring Defense (points allowed per game)

**Important**: The stats API returns rankings/statistics for ALL teams in a particular category, but the data is paginated across multiple pages (usually 1-5 pages).

**Pagination**: Most stat categories have multiple pages of data. The API uses URLs like:

- Page 1: `/stats/football/fbs/current/team/701`
- Page 2: `/stats/football/fbs/current/team/701/p2`
- Page 3: `/stats/football/fbs/current/team/701/p3`

**Two Main Use Cases**:

1. **Get All Teams**: Fetch statistics for all teams across all pages
2. **Find Specific Team**: Search through all pages to find a specific team's statistics

For example, `/stats/football/fbs/current/team/701` returns 3rd down conversion defense rankings for all FBS teams, showing which teams allow the lowest conversion percentage.

### Making API Requests

```python
import requests

def fetch_ncaa_data(endpoint):
    base_url = "https://ncaa-api.henrygd.me"
    full_url = f"{base_url}/{endpoint}"

    try:
        response = requests.get(full_url)
        response.raise_for_status()  # Raises exception for bad status codes
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
```

## Project Structure

Here's how we organize our Flask backend:

```
backend/
├── app.py                 # Main entry point, creates Flask app
├── routes/               # Contains route definitions
│   ├── history.py        # Routes for championship data
│   ├── rankings.py       # Routes for rankings (stub)
│   └── stats.py          # Routes for statistics (stub)
├── services/             # Contains API service functions
│   ├── history_service.py    # Fetches championship data
│   ├── rankings_service.py   # Would fetch rankings (stub)
│   └── stats_service.py      # Would fetch stats (stub)
└── requirements.txt      # Python dependencies
```

### Why This Structure?

- **Separation of Concerns**: Routes handle HTTP requests, services handle data fetching
- **Modularity**: Each file has a specific purpose
- **Maintainability**: Easy to find and modify specific functionality
- **Scalability**: Easy to add new routes and services

## Routes vs Service Functions

This is a crucial concept to understand:

### Routes (in routes/ folder)

- **Purpose**: Define URL endpoints that the frontend can call
- **Responsibilities**:
  - Handle HTTP requests from frontend
  - Call appropriate service functions
  - Return JSON responses
  - Handle errors and status codes

```python
# Example route
@app.route('/history/champions')
def get_champions_route():
    # Call service function to get data
    champions = get_championship_winners()

    # Return JSON response
    return jsonify({
        "success": True,
        "data": champions
    })
```

### Service Functions (in services/ folder)

- **Purpose**: Actually fetch data from external APIs
- **Responsibilities**:
  - Make HTTP requests to external APIs
  - Process and clean the data
  - Return data to routes
  - Handle API-specific errors

```python
# Example service function
def get_championship_winners():
    # Make request to NCAA API
    response = requests.get("https://ncaa-api.henrygd.me/history/football/fbs")

    # Process response
    if response.status_code == 200:
        return response.json()
    else:
        return None
```

### The Flow

1. Frontend calls `/history/champions`
2. Route function `get_champions_route()` is executed
3. Route calls service function `get_championship_winners()`
4. Service function fetches data from NCAA API
5. Service function returns data to route
6. Route returns JSON response to frontend

## Error Handling

Proper error handling is essential for a robust backend:

### HTTP Status Codes

- **200**: Success
- **400**: Bad Request (client error)
- **404**: Not Found
- **500**: Internal Server Error (server error)

### Error Handling Example

```python
from flask import jsonify

@app.route('/history/champions')
def get_champions_route():
    try:
        champions = get_championship_winners()

        if champions is None:
            return jsonify({
                "success": False,
                "error": "Failed to fetch championship data"
            }), 500

        return jsonify({
            "success": True,
            "data": champions
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
```

## Implementation Example

Let's implement the championship winners functionality:

### 1. Service Function (services/history_service.py)

```python
import requests

def get_championship_winners():
    """
    Fetch championship winners from NCAA API
    Returns: List of championship data or None if error
    """
    try:
        url = "https://ncaa-api.henrygd.me/history/football/fbs"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            return response.json()
        else:
            print(f"API returned status code: {response.status_code}")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching championship data: {e}")
        return None
```

### 2. Route (routes/history.py)

```python
from flask import Blueprint, jsonify
from services.history_service import get_championship_winners

# Create blueprint for history routes
history_bp = Blueprint('history', __name__, url_prefix='/history')

@history_bp.route('/champions', methods=['GET'])
def get_champions():
    """
    Route to get championship winners
    Returns: JSON response with championship data
    """
    try:
        champions = get_championship_winners()

        if champions is None:
            return jsonify({
                "success": False,
                "error": "Failed to fetch championship data from NCAA API"
            }), 500

        return jsonify({
            "success": True,
            "data": champions,
            "count": len(champions) if isinstance(champions, list) else 1
        })

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Internal server error: {str(e)}"
        }), 500
```

### 3. Main App (app.py)

```python
from flask import Flask
from flask_cors import CORS
from routes.history import history_bp

# Create Flask app
app = Flask(__name__)

# Enable CORS for frontend communication
CORS(app)

# Register blueprints
app.register_blueprint(history_bp)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
```

## Next Steps

### Adding New Routes

Once you understand the pattern, you can easily add new functionality:

1. **Create service function** in `services/` folder
2. **Create route** in `routes/` folder
3. **Register blueprint** in `app.py`

### Example: Simplified Stats Implementation

**⚠️ Difficulty Warning: The stats methods are more complex than other parts of this guide!**

The stats API involves pagination (multiple pages of data) and searching through large datasets. While the other examples in this guide are beginner-friendly, the stats implementation requires understanding:

- **Pagination**: The NCAA API returns data in chunks across multiple pages
- **Large Responses**: A single stats request can return 1500+ lines of JSON data
- **Search Logic**: Finding specific teams requires iterating through all pages

**Why is the response so large?**

- The NCAA has ~130 FBS teams
- Each team has multiple stat fields (rank, team name, games played, yards, average, etc.)
- All teams are returned in a single response for complete rankings
- JSON formatting adds significant overhead

**What `get_all_teams_stats()` does:**

- Fetches statistics for ALL teams across ALL pages
- Combines data from multiple API calls into one response
- Returns complete rankings (e.g., best offense to worst offense)
- Useful for building leaderboards or comparing all teams

**Alternative approach:**

- Use `get_team_stats(stat_id, team_name)` for specific teams only
- Much smaller response, faster execution
- Good for "show me Alabama's offense stats" type queries

The stats API is now set up for learners to implement themselves:

```python
# config/api_config.py
NCAA_API_BASE_URL = "https://ncaa-api.henrygd.me"

STAT_CATEGORIES = {
    21: "Total Offense",
    22: "Total Defense",
    701: "3rd Down Conversion Pct Defense",
    785: "Blocked Field Goals",
}

# services/stats_service.py
from config.api_config import NCAA_API_BASE_URL

def get_all_teams_stats(stat_id):
    """Fetch statistics for all teams across all pages"""
    # TODO: Implement this function
    # Hint: You'll need to handle pagination by checking for multiple pages
    # The API uses URLs like: /stats/football/fbs/current/team/{stat_id} and /stats/football/fbs/current/team/{stat_id}/p{page}

    print(f"get_all_teams_stats not implemented yet for stat ID: {stat_id}")
    return None

def get_team_stats(stat_id, team_name):
    """Find specific team by searching all pages"""
    # TODO: Implement this function
    # Hint: You'll need to search through all pages to find the specific team
    # Look for the team name in the 'Team' field of each record

    print(f"get_team_stats not implemented yet for stat ID: {stat_id}, team: {team_name}")
    return None

def get_offense_stats():
    """Fetch total offense statistics for all teams"""
    return get_all_teams_stats(21)

def get_team_offense_stats(team_name):
    """Find a specific team's offense statistics"""
    return get_team_stats(21, team_name)

# routes/stats.py
@stats_bp.route('/offense', methods=['GET'])
def get_offense_stats_route():
    """Route to get total offense statistics for all teams"""
    offense_data = get_offense_stats()

    if offense_data is None:
        return jsonify({
            "success": False,
            "error": "Failed to fetch offense statistics"
        }), 500

    return jsonify({
        "success": True,
        "data": offense_data,
        "stat_name": "Total Offense"
    })
```

**Key Benefits of This Approach**:

- **Learners implement the core functions** - `get_all_teams_stats()` and `get_team_stats()`
- **Simple wrapper functions** - `get_offense_stats()` just calls the core function with stat ID 21
- **Clean routes** - No complex error handling, just basic success/failure responses
- **Configurable** - Base URL and stat categories are in a separate config file
- **Beginner-friendly** - Clear TODOs and hints, no overwhelming implementation details

**When to Use Each Function**:

| Function                | Use Case                        | Response Size       | Speed  | Example                               |
| ----------------------- | ------------------------------- | ------------------- | ------ | ------------------------------------- |
| `get_all_teams_stats()` | Complete rankings, leaderboards | Large (1500+ lines) | Slower | "Show me all teams ranked by offense" |
| `get_team_stats()`      | Specific team lookup            | Small (~10 lines)   | Faster | "Show me Alabama's offense stats"     |

**Performance Considerations**:

- `get_all_teams_stats()` makes multiple API calls (one per page)
- `get_team_stats()` may need to search through all pages to find a team
- Consider caching results if calling frequently
- Large responses take longer to transfer over the network

### Learning Resources

- [Flask Documentation](https://flask.palletsprojects.com/)
- [Python Requests Library](https://requests.readthedocs.io/)
- [HTTP Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Status)

### Common Pitfalls to Avoid

1. **Don't put API calls directly in routes** - use service functions
2. **Always handle errors** - APIs can fail
3. **Use proper HTTP status codes** - helps frontend handle responses
4. **Test your endpoints** - use tools like Postman or curl
