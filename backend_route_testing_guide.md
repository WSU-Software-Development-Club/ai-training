# Backend Route Testing Guide with Postman

This guide will help you test all the backend routes using Postman, a popular API testing tool. The backend is a Flask application that provides various endpoints for NCAA football data.

## Table of Contents

1. [Installing Postman](#installing-postman)
2. [Setting Up Postman](#setting-up-postman)
3. [Backend Server Setup](#backend-server-setup)
4. [API Endpoints Overview](#api-endpoints-overview)
5. [Testing Each Route](#testing-each-route)
6. [Expected Response Formats](#expected-response-formats)
7. [Troubleshooting](#troubleshooting)

## Installing Postman

### Option 1: Download from Website

1. Go to [https://www.postman.com/downloads/](https://www.postman.com/downloads/)
2. Click "Download the App"
3. Choose your operating system (Windows, Mac, or Linux)
4. Run the installer and follow the setup instructions

### Option 2: Browser Version

1. Go to [https://web.postman.co/](https://web.postman.co/)
2. Sign up for a free account or sign in
3. Use Postman directly in your browser (no installation required)

## Setting Up Postman

### Required Setup

1. **Create a New Collection** _(Optional but Recommended)_

   - Click "New" → "Collection"
   - Name it "NCAA Football API Tests"
   - Add description: "Testing backend routes for NCAA football data"
   - _Note: You can test individual requests without creating a collection_

2. **Set Base URL Variable** _(Optional but Recommended)_
   - In your collection, go to "Variables" tab
   - Add variable: `base_url` = `http://localhost:5000`
   - This allows you to easily change the server URL if needed
   - _Alternative: You can type the full URL directly in each request_

### Optional Setup

3. **Environment Setup** _(Optional)_
   - Create a new environment called "Development"
   - Add variable: `base_url` = `http://localhost:5000`
   - _This is useful if you plan to test against multiple environments_

## Backend Server Setup

Before testing routes, ensure your backend server is running using Docker:

### Option 1: Using Docker Compose (Recommended)

```bash
# From the project root directory
docker-compose up backend

# Or to run in detached mode
docker-compose up -d backend
```

### Option 2: Development with Docker Compose

```bash
# From the project root directory
docker-compose -f docker-compose.dev.yml up backend
```

The server should start on `http://localhost:5000` by default.

**Note**: Make sure Docker is installed and running on your system before executing these commands.

## API Endpoints Overview

The backend provides the following route categories:

| Category        | Prefix      | Description              |
| --------------- | ----------- | ------------------------ |
| Main Routes     | `/`         | Basic application info   |
| API Routes      | `/api`      | Health and status checks |
| Stats Routes    | `/stats`    | NCAA football statistics |
| History Routes  | `/history`  | Championship data        |
| Rankings Routes | `/rankings` | Team rankings            |

## Testing Each Route

### 1. Main Routes

#### GET `/` - Home Endpoint

- **Method**: GET
- **URL**: `{{base_url}}/`
- **Description**: Returns basic application information

**Postman Setup:**

1. Create new request _(in collection or standalone)_
2. Set method to GET
3. Set URL to `{{base_url}}/` _(or `http://localhost:5000/` directly)_
4. Click "Send"

**Expected Response:**

```json
{
  "message": "Hello from Flask backend!",
  "app_name": "React Flask Web App",
  "version": "1.0.0",
  "timestamp": "2024-01-15T10:30:45.123456"
}
```

#### GET `/about` - About Endpoint

- **Method**: GET
- **URL**: `{{base_url}}/about`

**Expected Response:**

```json
{
  "name": "React Flask Web App",
  "version": "1.0.0",
  "description": "A simple React and Flask application",
  "status": "running"
}
```

### 2. API Routes

#### GET `/api/health` - Health Check

- **Method**: GET
- **URL**: `{{base_url}}/api/health`

**Expected Response:**

```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123456",
  "version": "1.0.0"
}
```

#### GET `/api/status` - Application Status

- **Method**: GET
- **URL**: `{{base_url}}/api/status`

**Expected Response:**

```json
{
  "name": "React Flask Web App",
  "version": "1.0.0",
  "status": "running",
  "uptime": "active"
}
```

### 3. Stats Routes

#### GET `/stats/stat/{stat_id}` - Get Statistics by Category

- **Method**: GET
- **URL**: `{{base_url}}/stats/stat/1`
- **Description**: Get statistics for all teams in a specific category
- **Parameters**: `stat_id` (integer) - The statistics category ID

**Example URLs:**

- `{{base_url}}/stats/stat/1` - Total Offense
- `{{base_url}}/stats/stat/2` - Total Defense

**Expected Response Format:**

```json
{
  "success": true,
  "data": [...],
  "stat_name": "Category Name"
}
```

#### GET `/stats/stat/{stat_id}/team/{team_name}` - Get Team Statistics

- **Method**: GET
- **URL**: `{{base_url}}/stats/stat/1/team/Alabama`
- **Description**: Get statistics for a specific team in a specific category

#### GET `/stats/offense` - Get All Offense Statistics

- **Method**: GET
- **URL**: `{{base_url}}/stats/offense`

#### GET `/stats/offense/team/{team_name}` - Get Team Offense Statistics

- **Method**: GET
- **URL**: `{{base_url}}/stats/offense/team/Alabama`

#### GET `/stats/defense` - Get All Defense Statistics

- **Method**: GET
- **URL**: `{{base_url}}/stats/defense`

#### GET `/stats/defense/team/{team_name}` - Get Team Defense Statistics

- **Method**: GET
- **URL**: `{{base_url}}/stats/defense/team/Georgia`

### 4. History Routes

#### GET `/history/champions` - Get Championship Winners

- **Method**: GET
- **URL**: `{{base_url}}/history/champions`
- **Description**: Retrieves championship data from NCAA API

**Expected Response Format:**

```json
{
  "success": true,
  "data": [...],
  "count": 2,
  "message": "Championship data retrieved successfully"
}
```

### 5. Rankings Routes

#### GET `/rankings/ap-top25` - Get AP Top 25 Rankings

- **Method**: GET
- **URL**: `{{base_url}}/rankings/ap-top25`
- **Description**: Currently returns a "not implemented" message

**Expected Response:**

```json
{
  "success": false,
  "error": "AP Top 25 rankings route not implemented yet",
  "message": "This route would fetch AP Top 25 rankings from the NCAA API"
}
```

## Expected Response Formats

### Success Response Format

Most successful responses follow this pattern:

```json
{
    "success": true,
    "data": [...],
    "additional_fields": "..."
}
```

### Error Response Format

Error responses follow this pattern:

```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

### HTTP Status Codes

- **200**: Success
- **404**: Not Found (team not found, invalid stat ID)
- **500**: Internal Server Error (API failures, database issues)
- **501**: Not Implemented (rankings routes)

## Troubleshooting

### Common Issues

1. **Connection Refused**

   - Ensure the Flask server is running on `http://localhost:5000`
   - Check if the port is already in use
   - Verify the server started without errors

2. **CORS Errors**

   - The backend has CORS enabled for `http://localhost:3000` and `http://127.0.0.1:3000`
   - If testing from a different origin, you may need to update the CORS configuration

3. **404 Errors**

   - Double-check the URL path
   - Ensure you're using the correct HTTP method
   - Verify the route exists in the backend code

4. **500 Errors**
   - Check the Flask server logs for detailed error messages
   - Ensure all required environment variables are set
   - Verify database connections if applicable

### Testing Tips

1. **Use Collection Variables** _(Optional)_

   - Set `base_url` as a collection variable for easy environment switching
   - Use `{{base_url}}` in all your request URLs
   - _Alternative: Type full URLs directly in each request_

2. **Save Responses** _(Optional)_

   - Save example responses for documentation
   - Use Postman's "Save Response" feature

3. **Test Edge Cases**

   - Test with invalid team names
   - Test with non-existent stat IDs
   - Test with special characters in URLs

4. **Environment Switching** _(Optional)_
   - Create different environments for development, staging, and production
   - Use environment variables for different base URLs

### Postman Collection Export _(Optional)_

To share your collection with others:

1. Right-click on your collection
2. Select "Export"
3. Choose "Collection v2.1" format
4. Save the JSON file
5. Others can import this file to get all your requests

_Note: This is only useful if you've created a collection with multiple requests_

## Additional Resources

- [Postman Documentation](https://learning.postman.com/)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [NCAA API Documentation](https://ncaa-api.henrygd.me/)

---

**Note**: This guide assumes the backend server is running in development mode. For production testing, ensure you have the appropriate environment variables and configurations set up.
