Vite

Never hardcode localhost:8000 or any backend URL in component files. Define it once in api/client.js and import from there.
Environment-specific values (backend URL, port) belong in a .env file using Vite's VITE_ prefix convention: VITE_API_BASE_URL=http://localhost:8000/api. Access with import.meta.env.VITE_API_BASE_URL.
Add .env to .gitignore. Commit a .env.example with the same keys but no values.
The Vite dev server runs on port 5173 by default. The FastAPI backend runs on port 8000. Both must be running during development.
Do not import from src/ using relative paths like ../../components/Sidebar. Configure a path alias in vite.config.js so imports read @/components/Sidebar instead.
