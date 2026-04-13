# Weekforge
Forge your week, train with purpose.

## Setup Instructions

This project uses [uv](https://github.com/astral-sh/uv) as its package manager and requires Python 3.13+.

1. **Install UV**  
   If you don't have `uv` installed, you can install it via curl (macOS/Linux):
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```
   *Alternatively, if you have Python setup: `pip install uv`*

2. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd weekforge
   ```

3. **Install Dependencies**  
   `uv` will automatically create a virtual environment (`.venv`) and install all required packages from `uv.lock`.
   ```bash
   uv sync
   ```

4. **Environment Variables**  
   Copy the provided `.env.template` file to create your local `.env` configuration file.
   ```bash
   cp .env.template .env
   ```

5. **Verify Installation**  
   Run the CLI to ensure everything is set up correctly:
   ```bash
   uv run weekforge --help
   ```

## Development Commands

- **Linting & Formatting**: `uv run ruff check .`
- **Type Checking**: `uv run mypy src/`
- **Testing**: `uv run pytest` (runs the test suite)
- **Testing (Verbose)**: `uv run pytest -v`
- **Testing SPECIFIC directories**: `uv run pytest tests/<dir-name>`
