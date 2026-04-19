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

## User Profile Configuration

Weekforge personalizes its outputs using a User Profile stored directly as a Notion page. You provide the ID of this page in your `.env` file (`NOTION_USER_PROFILE_PAGE_ID`). The application extracts the contents of this page as Markdown and injects it into prompt templates to provide the LLM with your specific physiological and training context.

### Setup Instructions

1. Create a new page in your Notion workspace.
2. Ensure the integration has read access to this page (or its parent database).
3. Copy the page ID and set it as `NOTION_USER_PROFILE_PAGE_ID` in your `.env` file.
4. Copy and paste the template below into the page, and fill it out.

### Profile Template

Here is the baseline template to use for your Notion profile page. You can customize the content under the headings to match your specific context.

```markdown
## Baseline
- Training age: 5 years (intermediate, consistent 2+ years)

## Goals
1. Primary goal - Performance: Mountaineering prep for multi-peak alpine week going for 4000m, uphill endurance, loaded carry, eccentric descent, altitude tolerance are needed. 
2. Secondary goal — Aesthetics: Shoulder-forward hypertrophy (OHP, lateral/rear delts for width) while leaning out through conditioning volume; maintain arms and chest

## Conditions
- Ankylosing spondylitis [low risk] - SI joint sensitivity, may cause instability during flare (then prescribe flare-friendly substitutions (split-stance, elevated pulls, isometrics)); avoid deep lumbar flexion and heavy axial compression; prioritize neutral spine and hip-dominant patterns.

## Preferences
- Likes: Outdoor training, free weights, pull ups, kettlebells, climbing-specific work, varied sessions, technique work, weight/volume progression
- Dislikes: Long running sessions on flat
- Motivation: Data-driven; responds to measurable progress and clear structure

## Injuries
- None currently

## Heart Rate Zones
Method: %LTHR | LTHR: 168 | Max HR: 191
- Z1: 101–119 bpm (recovery)
- Z2: 119–134 bpm (aerobic)
- Z3: 134–156 bpm (tempo)
- Z4: 156–176 bpm (threshold)
- Z5: >176 bpm (anaerobic)
```
