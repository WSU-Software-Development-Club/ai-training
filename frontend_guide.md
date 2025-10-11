# React Frontend Guide: Learning React with the NCAA Football App

## Table of Contents

1. [What is a Frontend?](#what-is-a-frontend)
2. [JavaScript Basics for React](#javascript-basics-for-react)
3. [React Basics](#react-basics)
4. [Working with APIs](#working-with-apis)
5. [Project Structure](#project-structure)
6. [Components vs Pages](#components-vs-pages)
7. [State Management](#state-management)
8. [Implementation Example](#implementation-example)
9. [Next Steps](#next-steps)

## What is a Frontend?

A **frontend** is the client-side part of a web application that users interact with directly. It's what you see in your web browser - the buttons, forms, text, and images. Think of it as the "user interface" that displays data and handles user interactions.

### How Frontend Interacts with Backend

```
User Interaction → Frontend (React) → HTTP Request → Backend (Flask) → JSON Response → Frontend → Display to User
```

1. **User** clicks a button or fills out a form
2. **Frontend** sends a request to the backend (like "get me championship winners")
3. **Backend** processes the request and returns JSON data
4. **Frontend** receives the data and updates the display
5. **User** sees the updated information

## JavaScript Basics for React

Coming from C/C++, here are the key JavaScript concepts you need:

### Variables and Constants

```javascript
// JavaScript variables (similar to C variables)
let teamName = "Alabama";
let year = 2020;

// Constants (similar to C const)
const CONFERENCE = "SEC";

// Objects (similar to C++ structs or C structs)
const teamData = {
  name: "Alabama",
  year: 2020,
  conference: "SEC",
};

// Access object properties
console.log(teamData.name); // Output: Alabama
console.log(teamData["year"]); // Output: 2020
```

### Functions

```javascript
// JavaScript function (similar to C functions)
function getChampionshipWinners() {
  return "Alabama won in 2020";
}

// Arrow function (modern JavaScript syntax)
const addNumbers = (a, b) => {
  return a + b;
};

// Arrow function with implicit return
const greet = (name = "World") => `Hello, ${name}!`;

// Function with parameters
function formatTeamName(team) {
  return `${team.name} (${team.conference})`;
}
```

### Arrays

```javascript
// Arrays (similar to C arrays, but dynamic)
const teams = ["Alabama", "Georgia", "Ohio State"];

// Array methods
teams.push("Clemson"); // Add to end
teams.pop(); // Remove from end
teams.length; // Get length

// Array iteration
teams.forEach((team) => {
  console.log(team);
});

// Array mapping (creates new array)
const teamObjects = teams.map((team) => ({
  name: team,
  conference: "SEC",
}));
```

### Destructuring

```javascript
// Extract values from objects
const team = { name: "Alabama", conference: "SEC", year: 2020 };
const { name, conference } = team;
console.log(name); // Output: Alabama

// Extract values from arrays
const scores = [31, 24];
const [homeScore, awayScore] = scores;
console.log(homeScore); // Output: 31
```

### Template Literals

```javascript
// String interpolation (similar to C++ string formatting)
const teamName = "Alabama";
const year = 2020;
const message = `${teamName} won the championship in ${year}`;
// Output: "Alabama won the championship in 2020"
```

### Async/Await (for API calls)

```javascript
// Making API requests (similar to network calls in C)
async function fetchTeamData() {
  try {
    const response = await fetch("https://api.example.com/teams");
    const data = await response.json();
    return data;
  } catch (error) {
    console.error("Error fetching data:", error);
    return null;
  }
}
```

## React Basics

React is a JavaScript library for building user interfaces. It's like having a toolkit for creating interactive web pages.

### What is React?

React uses **components** - reusable pieces of UI that can contain both HTML-like structure (JSX) and JavaScript logic. Think of components like functions that return HTML.

### Creating a React Component

```javascript
import React from "react";

// Function component (modern React)
function TeamCard({ team }) {
  return (
    <div className="team-card">
      <h3>{team.name}</h3>
      <p>Conference: {team.conference}</p>
    </div>
  );
}

// Export the component
export default TeamCard;
```

### JSX (JavaScript XML)

JSX looks like HTML but is actually JavaScript:

```javascript
// This JSX:
const element = <h1>Hello, {teamName}!</h1>;

// Gets converted to JavaScript:
const element = React.createElement("h1", null, "Hello, ", teamName, "!");
```

**JSX Rules:**

- Use `className` instead of `class`
- Use `{}` to embed JavaScript expressions
- Always close tags: `<div></div>` or `<div />`
- Use camelCase for attributes: `onClick`, `onChange`

### Props (Component Parameters)

Props are like function parameters for components:

```javascript
// Parent component passes data to child
function App() {
  const team = { name: "Alabama", conference: "SEC" };

  return (
    <div>
      <TeamCard team={team} />
    </div>
  );
}

// Child component receives props
function TeamCard({ team }) {
  return (
    <div>
      <h3>{team.name}</h3>
      <p>{team.conference}</p>
    </div>
  );
}
```

### State with useState

State is data that can change over time. In React, we use the `useState` hook:

```javascript
import React, { useState } from "react";

function ScoreDisplay() {
  // State variable and setter function
  const [score, setScore] = useState(0);

  const incrementScore = () => {
    setScore(score + 1); // Update state
  };

  return (
    <div>
      <p>Score: {score}</p>
      <button onClick={incrementScore}>Add Point</button>
    </div>
  );
}
```

### Event Handling

```javascript
function SearchBar({ onSearch }) {
  const [searchTerm, setSearchTerm] = useState("");

  const handleSubmit = (event) => {
    event.preventDefault(); // Prevent page reload
    onSearch(searchTerm);
  };

  const handleChange = (event) => {
    setSearchTerm(event.target.value);
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="text"
        value={searchTerm}
        onChange={handleChange}
        placeholder="Search teams..."
      />
      <button type="submit">Search</button>
    </form>
  );
}
```

### Conditional Rendering

```javascript
function GameStatus({ status }) {
  // Conditional rendering based on state
  if (status === "Final") {
    return <span className="final">Final</span>;
  } else if (status === "Live") {
    return <span className="live">Live</span>;
  } else {
    return <span className="upcoming">Upcoming</span>;
  }
}

// Or using ternary operator
function GameStatus({ status }) {
  return (
    <span className={status === "Final" ? "final" : "live"}>{status}</span>
  );
}
```

### Lists and Keys

```javascript
function TeamList({ teams }) {
  return (
    <ul>
      {teams.map((team) => (
        <li key={team.id}>
          {" "}
          {/* Key is required for list items */}
          {team.name} - {team.conference}
        </li>
      ))}
    </ul>
  );
}
```

## Working with APIs

### What is an API?

An **API (Application Programming Interface)** is a way for different software applications to communicate with each other. In our case, we'll use our Flask backend API to get college football data.

### How Our Backend API Works

Our Flask backend provides college football data through HTTP GET requests. The frontend makes requests to our backend endpoints and receives JSON responses.

**Base URL**: `http://localhost:5000`

#### Example API Endpoints:

1. **Championship History**: `/history/champions`

   - Returns championship winners from past years
   - Example: GET request to get all-time champions

2. **Rankings**: `/rankings/ap-top25`

   - Returns AP Top 25 rankings
   - Example: GET request to get current rankings

3. **Statistics**: `/stats/offense`
   - Returns team statistics for specific categories
   - Example: GET request to get offensive statistics

### Making API Requests

```javascript
// Generic API request function
const apiRequest = async (endpoint, options = {}) => {
  const url = `http://localhost:5000${endpoint}`;

  const defaultOptions = {
    headers: {
      "Content-Type": "application/json",
    },
  };

  const config = { ...defaultOptions, ...options };

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("API request failed:", error);
    throw error;
  }
};

// Specific API functions
export const api = {
  getChampions: () => apiRequest("/history/champions"),
  getRankings: () => apiRequest("/rankings/ap-top25"),
  getOffenseStats: () => apiRequest("/stats/offense"),
};
```

### Using useEffect for API Calls

```javascript
import React, { useState, useEffect } from "react";
import { api } from "../services/api";

function ChampionsPage() {
  const [champions, setChampions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchChampions = async () => {
      try {
        setLoading(true);
        const data = await api.getChampions();
        setChampions(data.data); // Assuming API returns { data: [...] }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchChampions();
  }, []); // Empty dependency array means run once on mount

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {error}</div>;

  return (
    <div>
      {champions.map((champion) => (
        <div key={champion.year}>
          {champion.year}: {champion.team}
        </div>
      ))}
    </div>
  );
}
```

## Project Structure

Here's how we organize our React frontend:

```
frontend/
├── src/
│   ├── App.js                 # Main entry point, sets up routing
│   ├── index.js               # React app initialization
│   ├── components/            # Reusable UI components
│   │   ├── Header.js          # Site header with navigation
│   │   ├── ScoreCard.js       # Individual game score display
│   │   ├── TeamCard.js        # Individual team display
│   │   └── SearchBar.js       # Search input component
│   ├── pages/                 # Page-level components
│   │   ├── HomePage.js        # Main landing page
│   │   ├── RankingsPage.js   # Rankings display page
│   │   ├── StatsPage.js       # Statistics page
│   │   └── TeamsPage.js       # Teams listing page
│   ├── services/              # API service functions
│   │   └── api.js             # API request functions
│   ├── utils/                 # Utility functions
│   │   ├── helpers.js         # Helper functions
│   │   └── mockData.js        # Mock data for development
│   ├── constants/             # App configuration
│   │   └── index.js           # App constants and config
│   └── styles/                # CSS files
│       ├── components/        # Component-specific styles
│       └── pages/            # Page-specific styles
├── public/                    # Static assets
└── package.json              # Dependencies and scripts
```

### Why This Structure?

- **Separation of Concerns**: Components handle UI, services handle data fetching
- **Modularity**: Each file has a specific purpose
- **Maintainability**: Easy to find and modify specific functionality
- **Scalability**: Easy to add new components and pages
- **Reusability**: Components can be used across multiple pages

## Components vs Pages

This is a crucial concept to understand:

### Components (in components/ folder)

- **Purpose**: Reusable pieces of UI that can be used across multiple pages
- **Responsibilities**:
  - Display specific data (like a team card or score card)
  - Handle user interactions (like search or filtering)
  - Maintain their own state if needed
  - Accept props from parent components

```javascript
// Example component
function ScoreCard({ game }) {
  const { homeTeam, awayTeam, homeScore, awayScore, status } = game;

  return (
    <div className="score-card">
      <div className="teams">
        <div className="team">
          {awayTeam} {awayScore}
        </div>
        <div className="vs">@</div>
        <div className="team">
          {homeTeam} {homeScore}
        </div>
      </div>
      <div className="status">{status}</div>
    </div>
  );
}
```

### Pages (in pages/ folder)

- **Purpose**: Complete page layouts that combine multiple components
- **Responsibilities**:
  - Fetch data from APIs
  - Manage page-level state
  - Coordinate multiple components
  - Handle routing and navigation

```javascript
// Example page
function HomePage() {
  const [scores, setScores] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchScores = async () => {
      try {
        const data = await api.getScores();
        setScores(data.data);
      } catch (error) {
        console.error("Error fetching scores:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchScores();
  }, []);

  if (loading) return <div>Loading...</div>;

  return (
    <div className="home-page">
      <Header title="NCAA Football" />
      <div className="scores-grid">
        {scores.map((game) => (
          <ScoreCard key={game.id} game={game} />
        ))}
      </div>
    </div>
  );
}
```

### The Flow

1. User visits a page (like `/rankings`)
2. Page component (`RankingsPage`) loads and fetches data from API
3. Page component renders multiple child components (`TeamCard`, `SearchBar`)
4. Child components receive data as props and display it
5. User interactions in components trigger events that update page state

## State Management

State management is how we handle data that can change over time in our React application.

### Local State (useState)

For data that only one component needs:

```javascript
function SearchBar() {
  const [searchTerm, setSearchTerm] = useState("");

  const handleChange = (event) => {
    setSearchTerm(event.target.value);
  };

  return (
    <input
      type="text"
      value={searchTerm}
      onChange={handleChange}
      placeholder="Search..."
    />
  );
}
```

### Lifting State Up

When multiple components need the same data, lift state to their common parent:

```javascript
// Parent component manages state
function HomePage() {
  const [filteredScores, setFilteredScores] = useState([]);
  const [selectedConference, setSelectedConference] = useState("All");

  const handleConferenceChange = (conference) => {
    setSelectedConference(conference);
    // Filter scores based on selected conference
    const filtered = scores.filter(
      (game) => conference === "All" || game.conference === conference
    );
    setFilteredScores(filtered);
  };

  return (
    <div>
      <FilterBar onConferenceChange={handleConferenceChange} />
      <ScoresList scores={filteredScores} />
    </div>
  );
}

// Child components receive state and callbacks
function FilterBar({ onConferenceChange }) {
  return (
    <select onChange={(e) => onConferenceChange(e.target.value)}>
      <option value="All">All Conferences</option>
      <option value="SEC">SEC</option>
      <option value="Big Ten">Big Ten</option>
    </select>
  );
}

function ScoresList({ scores }) {
  return (
    <div>
      {scores.map((game) => (
        <ScoreCard key={game.id} game={game} />
      ))}
    </div>
  );
}
```

### State Patterns

**1. Loading States**

```javascript
const [loading, setLoading] = useState(true);
const [data, setData] = useState(null);

useEffect(() => {
  const fetchData = async () => {
    setLoading(true);
    try {
      const result = await api.getData();
      setData(result);
    } catch (error) {
      console.error("Error:", error);
    } finally {
      setLoading(false);
    }
  };

  fetchData();
}, []);
```

**2. Error States**

```javascript
const [error, setError] = useState(null);

const handleApiCall = async () => {
  try {
    setError(null);
    const result = await api.getData();
    setData(result);
  } catch (err) {
    setError(err.message);
  }
};
```

**3. Form States**

```javascript
const [formData, setFormData] = useState({
  teamName: "",
  conference: "",
  year: "",
});

const handleInputChange = (field, value) => {
  setFormData((prev) => ({
    ...prev,
    [field]: value,
  }));
};
```

## Implementation Example

Let's implement the championship winners functionality:

### 1. API Service (services/api.js)

```javascript
const API_BASE_URL = "http://localhost:5000";

const apiRequest = async (endpoint, options = {}) => {
  const url = `${API_BASE_URL}${endpoint}`;

  const defaultOptions = {
    headers: {
      "Content-Type": "application/json",
    },
  };

  const config = { ...defaultOptions, ...options };

  try {
    const response = await fetch(url, config);

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return await response.json();
  } catch (error) {
    console.error("API request failed:", error);
    throw error;
  }
};

export const api = {
  getChampions: () => apiRequest("/history/champions"),
  getRankings: () => apiRequest("/rankings/ap-top25"),
  getOffenseStats: () => apiRequest("/stats/offense"),
};
```

### 2. Component (components/ChampionCard.js)

```javascript
import React from "react";
import "../styles/components/ChampionCard.css";

const ChampionCard = ({ champion }) => {
  const { year, team, score } = champion;

  return (
    <div className="champion-card">
      <div className="champion-card__year">{year}</div>
      <div className="champion-card__team">{team}</div>
      {score && <div className="champion-card__score">{score}</div>}
    </div>
  );
};

export default ChampionCard;
```

### 3. Page (pages/ChampionsPage.js)

```javascript
import React, { useState, useEffect } from "react";
import ChampionCard from "../components/ChampionCard";
import { api } from "../services/api";
import "../styles/pages/ChampionsPage.css";

const ChampionsPage = () => {
  const [champions, setChampions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchChampions = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await api.getChampions();

        if (response.success) {
          setChampions(response.data);
        } else {
          setError(response.error || "Failed to fetch champions");
        }
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchChampions();
  }, []);

  if (loading) {
    return (
      <div className="champions-page">
        <div className="loading">Loading champions...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="champions-page">
        <div className="error">Error: {error}</div>
      </div>
    );
  }

  return (
    <div className="champions-page">
      <h1>NCAA Football Champions</h1>
      <div className="champions-grid">
        {champions.map((champion) => (
          <ChampionCard key={champion.year} champion={champion} />
        ))}
      </div>
    </div>
  );
};

export default ChampionsPage;
```

### 4. App Routing (App.js)

```javascript
import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import ChampionsPage from "./pages/ChampionsPage";
import HomePage from "./pages/HomePage";
import RankingsPage from "./pages/RankingsPage";
import "./App.css";

function App() {
  return (
    <Router>
      <div className="app">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/champions" element={<ChampionsPage />} />
          <Route path="/rankings" element={<RankingsPage />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
```

## Next Steps

### Adding New Features

Once you understand the pattern, you can easily add new functionality:

1. **Create API function** in `services/api.js`
2. **Create component** in `components/` folder
3. **Create page** in `pages/` folder
4. **Add route** in `App.js`

### Example: Adding Rankings Feature

**1. API Function**

```javascript
// In services/api.js
export const api = {
  // ... existing functions
  getRankings: () => apiRequest("/rankings/ap-top25"),
};
```

**2. Component**

```javascript
// components/RankingCard.js
import React from "react";

const RankingCard = ({ team, rank }) => {
  return (
    <div className="ranking-card">
      <div className="rank">#{rank}</div>
      <div className="team">{team}</div>
    </div>
  );
};

export default RankingCard;
```

**3. Page**

```javascript
// pages/RankingsPage.js
import React, { useState, useEffect } from "react";
import RankingCard from "../components/RankingCard";
import { api } from "../services/api";

const RankingsPage = () => {
  const [rankings, setRankings] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchRankings = async () => {
      try {
        const response = await api.getRankings();
        if (response.success) {
          setRankings(response.data);
        }
      } catch (error) {
        console.error("Error fetching rankings:", error);
      } finally {
        setLoading(false);
      }
    };

    fetchRankings();
  }, []);

  if (loading) return <div>Loading rankings...</div>;

  return (
    <div className="rankings-page">
      <h1>AP Top 25 Rankings</h1>
      <div className="rankings-list">
        {rankings.map((team, index) => (
          <RankingCard key={index} team={team} rank={index + 1} />
        ))}
      </div>
    </div>
  );
};

export default RankingsPage;
```

**4. Route**

```javascript
// In App.js
<Route path="/rankings" element={<RankingsPage />} />
```

### Learning Resources

- [React Documentation](https://react.dev/)
- [JavaScript MDN Web Docs](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
- [CSS Flexbox Guide](https://css-tricks.com/snippets/css/a-guide-to-flexbox/)
- [CSS Grid Guide](https://css-tricks.com/snippets/css/complete-guide-grid/)

### Common Pitfalls to Avoid

1. **Don't mutate state directly** - use setState functions
2. **Always provide keys for list items** - helps React track changes
3. **Handle loading and error states** - APIs can fail
4. **Use useEffect dependencies correctly** - prevents infinite loops
5. **Don't put API calls directly in components** - use service functions
6. **Test your components** - use React testing tools

### Development Workflow

1. **Start with mock data** - build UI first, then connect to API
2. **Use browser developer tools** - inspect elements and debug
3. **Test API endpoints** - use tools like Postman or browser network tab
4. **Use console.log for debugging** - check browser console for errors
5. **Break down complex features** - build one component at a time

### Performance Tips

1. **Use React.memo for expensive components** - prevents unnecessary re-renders
2. **Use useCallback for event handlers** - prevents child re-renders
3. **Use useMemo for expensive calculations** - caches computed values
4. **Lazy load components** - load pages only when needed
5. **Optimize images** - use appropriate formats and sizes

## Stats System Implementation Guide

### How the Stats System Works

The stats system in this app is designed to be **scalable** and **easy to understand**. Here's how it works:

#### 1. The Big Picture

```
User selects "Total Offense" → Frontend checks if backend supports it →
If supported: Calls backend API → Gets real data → Displays table
If not supported: Uses mock data → Displays table
```

#### 2. Key Files and Their Roles

**`frontend/src/services/api.js`** - The "phone book" that knows how to call different APIs
**`frontend/src/pages/StatsPage.js`** - The main page that shows the stats table
**`frontend/src/components/StatsTable.js`** - The table component that displays the data
**`frontend/src/utils/mockData.js`** - Fake data for categories not yet connected to backend

#### 3. How to Add a New Stat Category

Adding a new stat category is **super simple** - just add one line!

**Step 1: Add the category to the mapping**

In `frontend/src/services/api.js`, find this section:

```javascript
const STAT_CATEGORY_ENDPOINTS = {
  "Total Offense": "/stats/offense",
  "Total Defense": "/stats/defense",
  "Rushing Offense": "/stats/offense/rushing",
  "Rushing Defense": "/stats/defense/rushing",
  // Add more categories as backend endpoints become available
};
```

**Step 2: Add your new category**

```javascript
const STAT_CATEGORY_ENDPOINTS = {
  "Total Offense": "/stats/offense",
  "Total Defense": "/stats/defense",
  "Rushing Offense": "/stats/offense/rushing",
  "Rushing Defense": "/stats/defense/rushing",
  "Passing Offense": "/stats/passing/offense", // ← Just add this line!
  // Add more categories as backend endpoints become available
};
```

**That's it!** The system automatically:

- ✅ Adds "Passing Offense" to the dropdown menu
- ✅ Knows to call the backend when user selects it
- ✅ Handles loading and error states
- ✅ Falls back to mock data if backend isn't ready

#### 4. Understanding the Code Flow

**When user selects a category:**

1. **StatsPage.js** calls `hasBackendSupport(selectedCategory)`
2. **api.js** checks if the category exists in `STAT_CATEGORY_ENDPOINTS`
3. **If supported:** Calls `getStats(selectedCategory)` → Backend API → Real data
4. **If not supported:** Uses mock data from `mockData.js`
5. **StatsTable.js** displays the data in a table

**The magic is in these two functions:**

```javascript
// Check if backend supports this category
export const hasBackendSupport = (category) => {
  return STAT_CATEGORY_ENDPOINTS.hasOwnProperty(category);
};

// Get stats for any supported category
export const getStats = async (category) => {
  const endpoint = STAT_CATEGORY_ENDPOINTS[category];
  if (!endpoint) {
    throw new Error(`No backend support for category: ${category}`);
  }
  return apiRequest(endpoint);
};
```

#### 5. Real Example: Adding "Scoring Offense"

Let's say you want to add "Scoring Offense" stats:

**Step 1:** Add to the mapping

```javascript
"Scoring Offense": "/stats/scoring/offense",
```

**Step 2:** Make sure the backend has this endpoint (that's a backend task)

**Step 3:** Test it! The frontend will automatically:

- Show "Scoring Offense" in the dropdown
- Call `/stats/scoring/offense` when selected
- Display the data in the table

#### 6. Understanding the Data Flow

**Backend Response Structure:**

```javascript
{
  "success": true,
  "data": {
    "sport": "Football",
    "title": "Total Offense",
    "updated": "Friday, October 10, 2025",
    "page": 1,
    "pages": 3,
    "data": [
      {
        "Rank": "1",
        "Team": "Texas Tech",
        "G": "5",
        "Plays": "384",
        "YDS": "2844",
        "Yds/Play": "7.41",
        "Off TDs": "29",
        "YPG": "568.8"
      }
      // ... more teams
    ]
  },
  "stat_name": "Total Offense"
}
```

**Frontend Processing:**

```javascript
// In StatsPage.js
const response = await getStats(selectedCategory);
if (response.success && response.data && response.data.data) {
  setStats(response.data.data); // Extract just the team data array
}
```

**StatsTable Display:**

- Takes the array of team objects
- Creates columns dynamically based on the data keys
- Displays Rank, Team, and all other stats

#### 7. Common Questions

**Q: Why do we need mock data?**
A: Mock data lets us build and test the UI before the backend is ready. It's like having a practice dummy before the real game.

**Q: What if the backend endpoint doesn't exist yet?**
A: The frontend will show an error message. Add the endpoint to the backend, then add it to the mapping.

**Q: How do I know what endpoint to use?**
A: Check the backend routes in `backend/routes/stats.py`. Each route has a URL path like `/stats/offense`.

**Q: Can I add multiple categories at once?**
A: Yes! Just add multiple lines to the `STAT_CATEGORY_ENDPOINTS` object.

#### 8. Best Practices

1. **Always test with mock data first** - Make sure the UI works before connecting to backend
2. **Use descriptive category names** - "Total Offense" is better than "TO"
3. **Keep the mapping simple** - One line per category, that's it
4. **Handle errors gracefully** - The system shows error messages if something goes wrong
5. **Test both supported and unsupported categories** - Make sure mock data still works

#### 9. Troubleshooting

**Problem:** Category shows in dropdown but gives error when selected
**Solution:** Check that the backend endpoint exists and works

**Problem:** Data doesn't display correctly
**Solution:** Check the data structure in browser console (F12 → Network tab)

**Problem:** Mock data doesn't show
**Solution:** Make sure the category name matches exactly in `mockData.js`

This system is designed to be **beginner-friendly** while still being **powerful and scalable**. Once you understand this pattern, you can add new features quickly and confidently!
