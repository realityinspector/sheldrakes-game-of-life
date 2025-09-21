Based on the user's detailed request, here is a revised and more explicit AI coding prompt for a coding agent.

### 🌟 Project: Enhanced Emergence Simulator - Integrated Runs & Morphic Analysis

### 🎯 Objective
Create a new feature for the "Emergence Simulator" application called "Integrated Runs." This feature will enable users to configure, execute, and analyze comparative simulations of Conway's Game of Life with a focus on morphic resonance. The results will be presented on a single, comprehensive, shareable page that resembles an interactive research notebook or infographic.

### 📝 Task List

Create a new file named `CHANGE-ROUND.md` with the following checklist. You will work through this checklist in order.

**`CHANGE-ROUND.md` Checklist:**

- [ ] **1. Backend Development:**
    - [ ] **Create new API endpoint:** Develop a `POST /api/integrated-runs` endpoint to accept a JSON payload for simulation parameters (e.g., `generations`, `grid_size`, `crystal_count`, `initial_density`, `simulation_types`, `slug`).
    - [ ] **Implement integrated run engine:** Write the core logic for the integrated run engine. This engine will orchestrate the execution of multiple parallel simulations (e.g., `morphic`, `llm_control`, `classical`) based on the submitted parameters.
    - [ ] **Update database schema:** Add a new table to store `integrated_run` records. This table must store:
        - `run_id` (primary key)
        - `slug` (unique URL slug)
        - `timestamp`
        - `parameters` (JSON or similar)
        - `status` (e.g., 'pending', 'running', 'completed', 'error')
        - References to associated simulation runs.
    - [ ] **Implement progress tracking:** Modify the simulation engine to emit progress updates (e.g., percentage complete, current generation) that can be queried by the frontend.
    - [ ] **Store visual assets:** Create a mechanism to save:
        - Side-by-side animation videos (e.g., `.mp4` or `.webm`) for each run.
        - Frame-by-frame image comparisons for every `n` frames (default `n=100`).

- [ ] **2. Frontend Development:**
    - [ ] **Create submission form:** Design and build a new web form at a new `/integrated-runs/create` endpoint. The form should allow users to input all simulation parameters and an optional custom URL slug.     - [ ] **Develop results page:** Create a new dynamic page at `/integrated-runs/{slug}`. This page will be the core of the feature. It should:
        - Display a loading spinner and real-time progress updates while the simulation is running.
        - Upon completion, display the results in a single, long-scrolling page with distinct sections.
    - [ ] **Create gallery page:** Build a gallery page at `/integrated-runs/gallery` that lists all completed integrated runs. Each entry should include:
        - The `run_id` and `slug`.
        - A small preview image or a thumbnail of the main animation.
        - The creation date and key parameters.
    - [ ] **Implement CRUD for galleries:** Add functionality to update or delete integrated runs from the gallery.

- [ ] **3. Visualization & Analysis:**
    - [ ] **Side-by-side animation:** On the results page, display the full-length side-by-side video of the `morphic`, `llm_control`, and `classical` simulations.
    - [ ] **Frame-by-frame comparison:** Create a section that displays a grid of side-by-side still images. For every `n` frames (default `100`), show a comparison of the grids from each simulation type. The user should be able to scroll through these comparisons to see subtle differences in pattern evolution.
    - [ ] **Component-by-component analysis (The Infographic/Notebook Look):**
        - Integrate an "Enable Instructions" toggle. When enabled, each section of the page will be wrapped in a container with a markdown-rendered explanation.
        - **Morphic Resonance Walkthrough:** For the morphic simulation results, embed **explicit, inline explanations** of the morphic resonance components based on the `FINAL_ENHANCED_IMPLEMENTATION.md` file. These explanations must appear as the user scrolls. For example:
            - **Section 1: Initial State:** Explain the `initial_density` parameter.
            - **Section 2: The Crystal Forms:** When the first patterns are stored, show an infographic-style section explaining "Memory Crystals". Use a visual element to represent a "crystal."
            - **Section 3: Adaptive Neighborhoods in Action:** Explain how `pattern_scale` dictates the neighborhood size (e.g., `3x3`, `5x5`, `7x7`) as the simulation progresses. Display the neighborhood size currently in use.
            - **Section 4: The LLM Weighs In:** When the LLM is consulted, add a section explaining that high-similarity patterns (>0.8) triggered the LLM and that its decisions get a 95%+ influence probability. Display the LLM's decision (0 or 1).
            - **Section 5: Uncapped Influence:** When a near-perfect or perfect match occurs, explain that the `80% cap was removed` and that these patterns can now achieve `90%+` or `100%` influence, respectively, and are overriding the Conway rules.
    - [ ] **Conway Factoid Toggle:** Implement a separate "Conway Factoids" toggle. When enabled, display a small, unobtrusive factoid about Conway's Game of Life on each comparison image. The factoids should be pulled from a new `conway_factoids.json` file you will create.
    - [ ] **Charts & Data:** Below the visual comparisons, display all relevant charts and reporting data as described in `README.md` and `FINAL_ENHANCED_IMPLEMENTATION.md`. This includes:
        - Complexity, stability, and convergence metrics.
        - Heatmaps and scatter plots from the `compare.sh` engine.
        - The decision tracking audit trail for each simulation, showing the source (`llm`, `markov`, `conway`) and final influence probability.

### 🛠️ Required Revisions & Implementation Details

- **Morphic Resonance Logic:** Ensure all core morphic components are accurately represented on the results page as described in the analysis section above. This includes: LLM integration, uncapped influence, adaptive neighborhood sizing, and the influence hierarchy.
- **Codebase Integration:** Integrate the new features seamlessly with the existing `Emergence Simulator` architecture.
- **URL Slugs & Permalinks:** Ensure the custom URL slug functionality is robust and can be used to generate permalinks for sharing the results of a specific run.
- **CRUD Functionality:** The gallery page must include buttons or links to update and delete entries. This implies a need for a new API layer to handle these requests.