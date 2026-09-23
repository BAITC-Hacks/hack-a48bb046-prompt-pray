import { spawnSync } from 'node:child_process'
import { fileURLToPath } from 'node:url'

// Use the backend virtual environment: it owns FastAPI/SQLAlchemy dependencies.
const python = process.env.BROWSER_TEST_PYTHON || fileURLToPath(new URL(
  process.platform === 'win32' ? '../../backend/.venv/Scripts/python.exe' : '../../backend/.venv/bin/python',
  import.meta.url
))
const result = spawnSync(python, [fileURLToPath(new URL('../../backend/scripts/test_frontend.py', import.meta.url)), '--browser'], {
  stdio: 'inherit'
})
if (result.error) console.error(`Could not start backend Python (${python}): ${result.error.message}`)
process.exit(result.status ?? 1)
