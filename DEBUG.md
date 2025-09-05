# Debugging Guide for Jyotishika

This guide explains how to set up and use debugging features for the Jyotishika Flask application.

## Quick Start

### Method 1: Using Cursor's Debug Panel (Recommended)

1. **Open the Debug Panel**: Press `Cmd+Shift+D` (Mac) or `Ctrl+Shift+D` (Windows/Linux)
2. **Select Configuration**: Choose "Debug Flask App" from the dropdown
3. **Set Breakpoints**: Click in the left margin of any line in your code to set breakpoints
4. **Start Debugging**: Press `F5` or click the green play button

### Method 2: Using the Debug Script

```bash
# From the project root directory
./debug.sh
```

### Method 3: Manual Flask Debug Mode

```bash
cd backend
export FLASK_ENV=development
export FLASK_DEBUG=1
export EPHE_PATH=./ephe
python3 -m flask --app app run --host=0.0.0.0 --port=8080 --debug
```

## Debug Configurations Available

### 1. Debug Flask App
- **Purpose**: Main Flask application debugging
- **Features**: Full debugging with breakpoints, variable inspection
- **Environment**: Development mode with debug logging

### 2. Debug Flask App (Module)
- **Purpose**: Alternative Flask module debugging
- **Features**: Uses Flask's module launcher
- **Environment**: Same as above but different launch method

### 3. Debug Tests
- **Purpose**: Debug pytest test cases
- **Features**: Step through test execution
- **Environment**: Testing mode

## Setting Breakpoints

### In Cursor/VS Code:
1. Click in the left margin next to any line number
2. A red dot will appear indicating a breakpoint
3. When the code execution reaches this line, it will pause

### Common Breakpoint Locations:
- **API Entry Points**: `backend/app/routes.py` line 10 (chart function start)
- **Error Handling**: `backend/app/routes.py` line 25 (validation error)
- **Astro Calculations**: `backend/app/routes.py` line 44 (ascendant calculation)
- **Planet Computations**: `backend/app/routes.py` line 47 (planet calculations)

## Debug Features

### Variable Inspection
- Hover over variables to see their values
- Use the "Variables" panel in the debug sidebar
- Add variables to the "Watch" panel for continuous monitoring

### Call Stack
- View the call stack in the "Call Stack" panel
- Navigate between different function calls
- See the execution path that led to the current breakpoint

### Debug Console
- Execute Python expressions in the current context
- Test variable values and function calls
- Modify variables during debugging

## Environment Variables for Debug Mode

```bash
FLASK_ENV=development      # Flask environment
FLASK_DEBUG=1             # Enable Flask debug mode
DEBUG=True                # Application debug flag
LOG_LEVEL=DEBUG           # Logging level
EPHE_PATH=./backend/ephe  # Ephemeris data path
PORT=8080                 # Server port
ALLOWED_ORIGINS=*         # CORS origins
```

## Testing Your Debug Setup

1. **Start the debugger** using one of the methods above
2. **Set a breakpoint** in `backend/app/routes.py` at line 10 (chart function)
3. **Make a test request**:
   ```bash
   curl -X POST http://localhost:8080/chart \
     -H "Content-Type: application/json" \
     -d '{
       "datetime": "2024-01-01T12:00:00",
       "latitude": 40.7128,
       "longitude": -74.0060,
       "houseSystem": "PLACIDUS",
       "ayanamsha": "LAHIRI",
       "nodeType": "MEAN",
       "include": {
         "signsForEachPlanet": true,
         "housesForEachPlanet": true,
         "houseCusps": true
       }
     }'
   ```
4. **The debugger should pause** at your breakpoint
5. **Inspect variables** and step through the code

## Troubleshooting

### Common Issues:

1. **"EPHE_PATH not set"**: Ensure the ephemeris data directory exists at `./backend/ephe`
2. **Port already in use**: Change the PORT environment variable or kill existing processes
3. **Breakpoints not hit**: Ensure you're using the debug configuration, not running normally
4. **Import errors**: Make sure you're running from the correct directory (`backend/`)

### Debug Logs:
The application includes extensive logging. Check the terminal output for:
- 🔵 API Request received
- ✅ Validated Payload
- 🎉 Chart calculation successful
- ❌ Error messages with details

## Advanced Debugging

### Conditional Breakpoints:
- Right-click on a breakpoint to add conditions
- Example: `payload.latitude > 0` to only break for positive latitudes

### Log Points:
- Add log points instead of breakpoints for non-intrusive debugging
- Right-click in margin and select "Add Logpoint"

### Exception Breakpoints:
- Break on all exceptions or specific exception types
- Access via the "Breakpoints" panel

## Performance Considerations

- Debug mode is slower than production mode
- Use debug mode only during development
- Remove breakpoints before committing code
- Consider using log points for production debugging
