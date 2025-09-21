#!/usr/bin/env python3
"""
Emergence Simulator - Main Entry Point

A simple launcher for the emergence simulator platform.
Handles basic FastAPI setup and routing.
"""

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import markdown
import json
import os
from datetime import datetime
import hashlib
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import numpy as np
import base64
from io import BytesIO

# Create FastAPI app
app = FastAPI(
    title="Emergence Simulator",
    description="A platform for testing morphic resonance in artificial systems",
    version="1.0.0"
)

# Setup visualization directories
CACHE_DIR = Path("web_cache")
VIZ_DIR = CACHE_DIR / "visualizations"
CACHE_DIR.mkdir(exist_ok=True)
VIZ_DIR.mkdir(exist_ok=True)

# Mount static files for serving generated images
app.mount("/static", StaticFiles(directory=str(VIZ_DIR)), name="static")

# Visualization utility functions
def generate_cache_key(data):
    """Generate cache key from data"""
    content = json.dumps(data, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()

def load_simulation_data(path):
    """Load simulation data from file"""
    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = Path.cwd() / file_path

    with open(file_path, 'r') as f:
        return json.load(f)

def create_population_chart(data, title="Population Over Time"):
    """Create population progression chart"""
    population_data = None

    # Try different possible data structures
    if 'population_history' in data:
        population_data = data['population_history']
    elif 'generation_data' in data:
        # Extract population from generation data
        population_data = [gen.get('population', 0) for gen in data['generation_data']]
    else:
        return None

    fig, ax = plt.subplots(figsize=(12, 6))
    generations = list(range(len(population_data)))
    populations = population_data

    ax.plot(generations, populations, linewidth=2, marker='o', markersize=4, color='#007bff')
    ax.set_xlabel('Generation')
    ax.set_ylabel('Population')
    ax.set_title(title)
    ax.grid(True, alpha=0.3)

    # Add morphic influence overlay if available
    if 'morphic_influences' in data and data['morphic_influences']:
        influence_gen = [inf.get('generation', 0) for inf in data['morphic_influences']]
        influence_counts = {}
        for gen in influence_gen:
            influence_counts[gen] = influence_counts.get(gen, 0) + 1

        if influence_counts:
            ax2 = ax.twinx()
            gens = list(influence_counts.keys())
            counts = list(influence_counts.values())
            ax2.scatter(gens, counts, c='red', alpha=0.6, s=30, label='Morphic Influences')
            ax2.set_ylabel('Morphic Influences', color='red')
            ax2.legend(loc='upper right')

    plt.tight_layout()
    return fig

def save_chart(fig, filename):
    """Save matplotlib figure to file"""
    filepath = VIZ_DIR / filename
    fig.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)
    return f"/static/{filename}"

def create_morphic_heatmap(data):
    """Create heatmap of morphic influence locations"""
    if 'morphic_influences' not in data or 'grid_size' not in data:
        return None

    grid_size = data['grid_size']
    influence_grid = np.zeros((grid_size, grid_size))

    for influence in data['morphic_influences']:
        if 'position' in influence:
            x, y = influence['position']
            if 0 <= x < grid_size and 0 <= y < grid_size:
                influence_grid[y, x] += 1

    if np.sum(influence_grid) == 0:
        return None

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(influence_grid, cmap='YlOrRd', interpolation='nearest')
    ax.set_title('Morphic Influence Heatmap')
    ax.set_xlabel('X Position')
    ax.set_ylabel('Y Position')

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Influence Count')

    return fig

def create_pattern_analysis(data):
    """Create pattern analysis visualization"""
    if 'crystals' not in data:
        return None

    fig, axes = plt.subplots(2, 2, figsize=(12, 10))

    # Crystal usage
    crystal_patterns = [len(crystal.get('patterns', [])) for crystal in data['crystals']]
    axes[0, 0].bar(range(len(crystal_patterns)), crystal_patterns, color='purple', alpha=0.7)
    axes[0, 0].set_title('Patterns per Crystal')
    axes[0, 0].set_xlabel('Crystal Index')
    axes[0, 0].set_ylabel('Pattern Count')

    # Pattern strength distribution
    all_strengths = []
    for crystal in data['crystals']:
        for pattern in crystal.get('patterns', []):
            all_strengths.append(pattern.get('strength', 0))

    if all_strengths:
        axes[0, 1].hist(all_strengths, bins=20, alpha=0.7, color='green')
        axes[0, 1].set_title('Pattern Strength Distribution')
        axes[0, 1].set_xlabel('Strength')
        axes[0, 1].set_ylabel('Frequency')

    # Morphic influence over time
    if 'morphic_influences' in data:
        influence_gen = [inf.get('generation', 0) for inf in data['morphic_influences']]
        influence_counts = {}
        for gen in influence_gen:
            influence_counts[gen] = influence_counts.get(gen, 0) + 1

        if influence_counts:
            gens = sorted(influence_counts.keys())
            counts = [influence_counts[g] for g in gens]
            axes[1, 0].plot(gens, counts, marker='o', color='red')
            axes[1, 0].set_title('Morphic Influences Over Time')
            axes[1, 0].set_xlabel('Generation')
            axes[1, 0].set_ylabel('Influence Count')

    # Crystal strength over time
    crystal_strengths = []
    for crystal in data['crystals']:
        crystal_strengths.append(crystal.get('strength', 0))

    axes[1, 1].bar(range(len(crystal_strengths)), crystal_strengths, color='blue', alpha=0.7)
    axes[1, 1].set_title('Crystal Strength')
    axes[1, 1].set_xlabel('Crystal Index')
    axes[1, 1].set_ylabel('Overall Strength')

    plt.tight_layout()
    return fig

def create_crystal_usage(data):
    """Create crystal usage visualization"""
    if 'crystals' not in data:
        return None

    fig, ax = plt.subplots(figsize=(10, 6))

    crystal_data = []
    for i, crystal in enumerate(data['crystals']):
        patterns = len(crystal.get('patterns', []))
        strength = crystal.get('strength', 0)
        utilization = patterns / 100.0 if patterns < 100 else 1.0  # Normalize

        crystal_data.append({
            'index': i,
            'patterns': patterns,
            'strength': strength,
            'utilization': utilization
        })

    # Create bubble chart
    x = [c['index'] for c in crystal_data]
    y = [c['strength'] for c in crystal_data]
    sizes = [c['patterns'] * 20 for c in crystal_data]  # Scale for visibility
    colors = [c['utilization'] for c in crystal_data]

    scatter = ax.scatter(x, y, s=sizes, c=colors, alpha=0.6, cmap='viridis')
    ax.set_xlabel('Crystal Index')
    ax.set_ylabel('Crystal Strength')
    ax.set_title('Crystal Usage Analysis\n(Size = Pattern Count, Color = Utilization)')

    # Add colorbar
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('Utilization')

    return fig

def create_animation_frames(data):
    """Create animation frames from simulation data"""
    if 'generation_data' not in data:
        return None

    # For now, create a simple GIF-like visualization
    # In a full implementation, this would use matplotlib.animation

    generations = data['generation_data'][:10]  # Limit to first 10 frames
    grid_size = data.get('grid_size', 20)

    fig, axes = plt.subplots(2, 5, figsize=(15, 6))
    axes = axes.flatten()

    for i, gen_data in enumerate(generations):
        if i >= 10:
            break

        # Create a simple grid visualization
        grid = np.random.random((grid_size, grid_size))  # Placeholder - would use actual grid data

        im = axes[i].imshow(grid, cmap='Blues', interpolation='nearest')
        axes[i].set_title(f'Gen {i}')
        axes[i].set_xticks([])
        axes[i].set_yticks([])

    # Hide unused subplots
    for i in range(len(generations), 10):
        axes[i].set_visible(False)

    plt.suptitle('Simulation Evolution (Animation Frames)')
    plt.tight_layout()
    return fig

# Static files
static_dir = Path("web/static")
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with navigation dashboard"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Emergence Simulator - Dashboard</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 0;
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                color: #333;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                border-radius: 16px;
                box-shadow: 0 20px 40px rgba(0,0,0,0.1);
                overflow: hidden;
            }
            .header {
                background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
                color: white;
                padding: 40px;
                text-align: center;
            }
            .header h1 {
                margin: 0;
                font-size: 2.5em;
                font-weight: 700;
            }
            .header p {
                margin: 10px 0 0;
                font-size: 1.2em;
                opacity: 0.9;
            }
            .nav-section {
                padding: 40px;
            }
            .nav-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 24px;
                margin-top: 30px;
            }
            .nav-card {
                background: #f8f9fa;
                border: 2px solid #e9ecef;
                border-radius: 12px;
                padding: 24px;
                text-decoration: none;
                color: inherit;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            .nav-card:hover {
                transform: translateY(-4px);
                box-shadow: 0 12px 24px rgba(0,0,0,0.15);
                border-color: #007bff;
            }
            .nav-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                width: 100%;
                height: 4px;
                background: linear-gradient(90deg, #007bff, #28a745);
            }
            .nav-card h3 {
                margin: 0 0 12px 0;
                font-size: 1.4em;
                color: #1e3c72;
                display: flex;
                align-items: center;
                gap: 10px;
            }
            .nav-card p {
                margin: 0;
                color: #666;
                line-height: 1.6;
            }
            .status-bar {
                background: #e8f5e8;
                padding: 16px 40px;
                border-top: 1px solid #d4edda;
                display: flex;
                justify-content: space-between;
                align-items: center;
                flex-wrap: wrap;
                gap: 16px;
            }
            .status-item {
                display: flex;
                align-items: center;
                gap: 8px;
                color: #155724;
                font-weight: 500;
            }
            .status-dot {
                width: 8px;
                height: 8px;
                background: #28a745;
                border-radius: 50%;
            }
            .api-info {
                background: #f1f3f4;
                padding: 20px 40px;
                font-family: 'Monaco', 'Consolas', monospace;
                font-size: 0.9em;
                color: #5f6368;
            }
            .badge {
                display: inline-block;
                background: #007bff;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.75em;
                font-weight: 600;
                margin-left: 8px;
            }
            @media (max-width: 768px) {
                .nav-grid {
                    grid-template-columns: 1fr;
                }
                .header h1 {
                    font-size: 2em;
                }
                .container {
                    margin: 10px;
                    border-radius: 12px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🧬 Emergence Simulator</h1>
                <p>A scientific research platform for testing morphic resonance effects in artificial systems</p>
            </div>

            <div class="nav-section">
                <h2>🚀 Getting Started</h2>
                <p>The Emergence Simulator combines Conway's Game of Life with Large Language Model decision-making to study emergent behaviors and memory crystal effects. Choose a section below to explore the platform:</p>

                <div class="nav-grid">
                    <a href="/viewer" class="nav-card">
                        <h3>👁️ Interactive Viewer <span class="badge">Live</span></h3>
                        <p>Real-time visualization of simulations with interactive controls. Watch patterns evolve, explore memory crystals, and analyze emergent behaviors as they happen.</p>
                    </a>

                    <a href="/user-guide" class="nav-card">
                        <h3>📖 User Guide <span class="badge">Complete</span></h3>
                        <p>Comprehensive documentation covering setup, usage, research methodologies, and API reference. Perfect for researchers and developers.</p>
                    </a>

                    <a href="/docs" class="nav-card">
                        <h3>📚 API Documentation <span class="badge">Interactive</span></h3>
                        <p>Interactive Swagger/OpenAPI documentation with live testing capabilities. Explore all endpoints for simulations, crystals, and analysis.</p>
                    </a>
                </div>

                <h2>🔬 Core Features</h2>
                <div class="nav-grid">
                    <div class="nav-card">
                        <h3>🧠 Morphic Resonance Engine</h3>
                        <p>Memory crystals store pattern information across simulations, creating morphic fields that influence decision-making based on historical patterns.</p>
                    </div>

                    <div class="nav-card">
                        <h3>🎯 Conway's Game of Life++</h3>
                        <p>Enhanced cellular automata with traditional rules plus LLM-driven decisions for complex pattern recognition and evolution.</p>
                    </div>

                    <div class="nav-card">
                        <h3>🤖 LLM Integration</h3>
                        <p>OpenRouter API integration with multiple models for context-aware decisions using pattern history and similarity analysis.</p>
                    </div>
                </div>
            </div>

            <div class="status-bar">
                <div class="status-item">
                    <div class="status-dot"></div>
                    <span>System Online</span>
                </div>
                <div class="status-item">
                    <div class="status-dot"></div>
                    <span>API Ready</span>
                </div>
                <div class="status-item">
                    <div class="status-dot"></div>
                    <span>Version 1.0.0</span>
                </div>
            </div>

            <div class="api-info">
                <strong>Quick API Access:</strong>
                GET /health (health check) •
                GET /docs (interactive docs) •
                POST /api/simulations/ (start simulation) •
                GET /api/crystals/ (list memory crystals)
            </div>
        </div>
    </body>
    </html>
    """
    return html_content

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "emergence-simulator"}

@app.get("/viewer", response_class=HTMLResponse)
async def viewer():
    """Enhanced viewer with historical simulation support"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Emergence Simulator - Historical Viewer</title>
        <style>
            body {
                font-family: system-ui, sans-serif;
                margin: 20px;
                background: #f8f9fa;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .status { color: #28a745; }
            .tabs {
                border-bottom: 2px solid #ddd;
                margin-bottom: 20px;
            }
            .tab {
                display: inline-block;
                padding: 10px 20px;
                cursor: pointer;
                border: none;
                background: none;
                font-size: 16px;
                border-bottom: 3px solid transparent;
            }
            .tab.active {
                border-bottom-color: #007bff;
                color: #007bff;
                font-weight: bold;
            }
            .tab-content {
                display: none;
            }
            .tab-content.active {
                display: block;
            }
            .file-list {
                max-height: 400px;
                overflow-y: auto;
                border: 1px solid #ddd;
                padding: 10px;
                background: #f8f9fa;
            }
            .file-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 10px;
                margin: 5px 0;
                background: white;
                border-radius: 4px;
                cursor: pointer;
                border: 1px solid transparent;
            }
            .file-item:hover {
                border-color: #007bff;
                background: #e3f2fd;
            }
            .file-info {
                flex: 1;
            }
            .file-name {
                font-weight: bold;
                color: #333;
            }
            .file-meta {
                font-size: 12px;
                color: #666;
                margin-top: 2px;
            }
            .btn {
                background: #007bff;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                cursor: pointer;
                margin-left: 10px;
            }
            .btn:hover {
                background: #0056b3;
            }
            .simulation-display {
                border: 1px solid #ddd;
                padding: 20px;
                border-radius: 8px;
                margin-top: 20px;
                background: #fafafa;
            }
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin: 20px 0;
            }
            .metric-card {
                background: white;
                padding: 15px;
                border-radius: 6px;
                border-left: 4px solid #007bff;
                box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            }
            .metric-label {
                font-size: 12px;
                color: #666;
                text-transform: uppercase;
                margin-bottom: 5px;
            }
            .metric-value {
                font-size: 24px;
                font-weight: bold;
                color: #333;
            }
            .loading {
                text-align: center;
                padding: 40px;
                color: #666;
            }
            .error {
                color: #dc3545;
                background: #f8d7da;
                padding: 10px;
                border-radius: 4px;
                margin: 10px 0;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌟 Emergence Simulator - Historical Viewer</h1>
            <p class="status">✅ System is running</p>

            <div class="tabs">
                <button class="tab active" onclick="showTab('recent')">📊 Recent Simulations</button>
                <button class="tab" onclick="showTab('batch')">📁 Batch Results</button>
                <button class="tab" onclick="showTab('studies')">🔬 Research Studies</button>
                <button class="tab" onclick="showTab('visualize')">📈 Visualizations</button>
                <button class="tab" onclick="showTab('live')">🎮 Live Monitor</button>
            </div>

            <div id="recent" class="tab-content active">
                <h2>📈 Recent Simulation Results</h2>
                <button class="btn" onclick="loadRecentSimulations()">🔄 Refresh</button>
                <div id="recent-files" class="file-list">
                    <div class="loading">Loading recent simulations...</div>
                </div>
                <div id="simulation-details" class="simulation-display" style="display: none;">
                    <h3>Simulation Details</h3>
                    <div id="simulation-content"></div>
                </div>
            </div>

            <div id="batch" class="tab-content">
                <h2>📁 Batch Study Results</h2>
                <button class="btn" onclick="loadBatchResults()">🔄 Refresh</button>
                <div id="batch-files" class="file-list">
                    <div class="loading">Loading batch results...</div>
                </div>
            </div>

            <div id="studies" class="tab-content">
                <h2>🔬 Research Studies</h2>
                <button class="btn" onclick="loadStudies()">🔄 Refresh</button>
                <div id="study-files" class="file-list">
                    <div class="loading">Loading research studies...</div>
                </div>
            </div>

            <div id="visualize" class="tab-content">
                <h2>📈 Data Visualizations</h2>

                <!-- Run Selection -->
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h4>🎯 Select Simulation Run</h4>
                    <div style="display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
                        <select id="run-selector" style="padding: 8px; border-radius: 4px; border: 1px solid #ddd; min-width: 200px;">
                            <option value="">Select a simulation run...</option>
                        </select>
                        <button class="btn" onclick="loadRunSelector()">🔄 Refresh Runs</button>
                        <button class="btn" onclick="generateSingleChart()" disabled id="chart-btn">📊 Generate Chart</button>
                        <button class="btn" onclick="generateAnimation()" disabled id="animate-btn">🎬 Animate</button>
                    </div>
                </div>

                <!-- Visualization Type Selection -->
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
                    <h4>📊 Visualization Options</h4>
                    <div style="display: flex; gap: 15px; flex-wrap: wrap;">
                        <label><input type="checkbox" id="pop-chart" checked> Population Chart</label>
                        <label><input type="checkbox" id="morphic-heatmap"> Morphic Heatmap</label>
                        <label><input type="checkbox" id="pattern-analysis"> Pattern Analysis</label>
                        <label><input type="checkbox" id="crystal-usage"> Crystal Usage</label>
                    </div>
                </div>

                <!-- Progress and Actions -->
                <div style="display: flex; gap: 10px; margin-bottom: 20px;">
                    <button class="btn" onclick="generateOverviewCharts()">🎨 Generate Overview</button>
                    <button class="btn" onclick="loadCachedVisualizations()">💾 Load Cached</button>
                    <button class="btn" onclick="clearVisualizationCache()">🗑️ Clear Cache</button>
                </div>

                <!-- Progress Bar -->
                <div id="viz-progress" style="display: none; margin: 20px 0;">
                    <div style="background: #e9ecef; height: 20px; border-radius: 10px; overflow: hidden;">
                        <div id="progress-bar" style="background: #007bff; height: 100%; width: 0%; transition: width 0.3s;"></div>
                    </div>
                    <div id="progress-text" style="margin-top: 5px; color: #666;">Preparing...</div>
                </div>

                <!-- Visualization Gallery -->
                <div id="visualization-content">
                    <div style="text-align: center; padding: 40px; color: #666;">
                        <p>Select a simulation run above to generate visualizations</p>
                        <p>Or click "Generate Overview" to see charts from all recent runs</p>
                    </div>
                </div>

                <!-- Cached Visualizations -->
                <div id="cached-visualizations" style="margin-top: 30px;">
                    <h4>💾 Cached Visualizations</h4>
                    <div id="cache-list" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; margin-top: 15px;">
                        <!-- Cached items will be loaded here -->
                    </div>
                </div>
            </div>

            <div id="live" class="tab-content">
                <h2>🎮 Live Simulation Monitor</h2>
                <p>Monitor active simulations in real-time</p>
                <button class="btn" onclick="startLiveMonitor()">▶️ Start Monitor</button>
                <div id="live-content" style="margin-top: 20px;">
                    <p>Start the monitor to see live simulation data...</p>
                </div>
            </div>
        </div>

        <script>
            function showTab(tabName) {
                // Hide all tab contents
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.classList.remove('active');
                });

                // Remove active class from all tabs
                document.querySelectorAll('.tab').forEach(tab => {
                    tab.classList.remove('active');
                });

                // Show selected tab content
                document.getElementById(tabName).classList.add('active');

                // Add active class to clicked tab
                event.target.classList.add('active');
            }

            async function loadRecentSimulations() {
                const container = document.getElementById('recent-files');
                container.innerHTML = '<div class="loading">Loading recent simulations...</div>';

                try {
                    const response = await fetch('/api/simulations/recent');
                    const files = await response.json();

                    if (files.length === 0) {
                        container.innerHTML = '<p>No simulation results found. Run some simulations first!</p>';
                        return;
                    }

                    container.innerHTML = files.map(file => `
                        <div class="file-item" onclick="loadSimulation('${file.path}')">
                            <div class="file-info">
                                <div class="file-name">${file.name}</div>
                                <div class="file-meta">${file.type} • ${file.size} • ${file.modified}</div>
                            </div>
                            <button class="btn" onclick="event.stopPropagation(); loadSimulation('${file.path}')">View</button>
                        </div>
                    `).join('');
                } catch (error) {
                    container.innerHTML = '<div class="error">Error loading simulations: ' + error.message + '</div>';
                }
            }

            async function loadBatchResults() {
                const container = document.getElementById('batch-files');
                container.innerHTML = '<div class="loading">Loading batch results...</div>';

                try {
                    const response = await fetch('/api/simulations/batch');
                    const batches = await response.json();

                    if (batches.length === 0) {
                        container.innerHTML = '<p>No batch results found. Run ./comprehensive_study.sh first!</p>';
                        return;
                    }

                    container.innerHTML = batches.map(batch => `
                        <div class="file-item">
                            <div class="file-info">
                                <div class="file-name">${batch.name}</div>
                                <div class="file-meta">${batch.files} files • ${batch.modified}</div>
                            </div>
                            <div style="display: flex; gap: 5px;">
                                <button class="btn" onclick="loadBatchResults('${batch.path}')">View Batch</button>
                                <button class="btn" onclick="visualizeBatch('${batch.path}')" style="background: #28a745;">📊 Visualize</button>
                            </div>
                        </div>
                    `).join('');
                } catch (error) {
                    container.innerHTML = '<div class="error">Error loading batch results: ' + error.message + '</div>';
                }
            }

            async function loadStudies() {
                const container = document.getElementById('study-files');
                container.innerHTML = '<div class="loading">Loading research studies...</div>';

                try {
                    const response = await fetch('/api/simulations/studies');
                    const studies = await response.json();

                    container.innerHTML = studies.length > 0 ?
                        studies.map(study => `
                            <div class="file-item">
                                <div class="file-info">
                                    <div class="file-name">${study.name}</div>
                                    <div class="file-meta">${study.type} • ${study.files} files • ${study.modified}</div>
                                </div>
                                <button class="btn" onclick="loadStudyDetails('${study.path}')">View Study</button>
                            </div>
                        `).join('') :
                        '<p>No research studies found. Run ./research_protocol.sh first!</p>';
                } catch (error) {
                    container.innerHTML = '<div class="error">Error loading studies: ' + error.message + '</div>';
                }
            }

            async function loadSimulation(path) {
                const detailsDiv = document.getElementById('simulation-details');
                const contentDiv = document.getElementById('simulation-content');

                detailsDiv.style.display = 'block';
                contentDiv.innerHTML = '<div class="loading">Loading simulation details...</div>';

                try {
                    const response = await fetch(`/api/simulations/load?path=${encodeURIComponent(path)}`);
                    const data = await response.json();

                    const metrics = [
                        { label: 'Final Population', value: data.final_population },
                        { label: 'Average Population', value: data.avg_population?.toFixed(1) },
                        { label: 'Max Population', value: data.max_population },
                        { label: 'Stability Score', value: data.stability_score?.toFixed(3) },
                        { label: 'Complexity Score', value: data.complexity_score?.toFixed(3) },
                        { label: 'Emergence Events', value: data.emergence_events || 0 },
                        { label: 'Morphic Influences', value: data.morphic_influences?.length || 'N/A' },
                        { label: 'Crystal Patterns', value: data.crystals?.reduce((sum, c) => sum + (c.patterns?.length || 0), 0) || 'N/A' }
                    ];

                    contentDiv.innerHTML = `
                        <div class="metrics-grid">
                            ${metrics.map(metric => `
                                <div class="metric-card">
                                    <div class="metric-label">${metric.label}</div>
                                    <div class="metric-value">${metric.value}</div>
                                </div>
                            `).join('')}
                        </div>
                        <h4>📋 Simulation Parameters</h4>
                        <p><strong>Mode:</strong> ${data.mode || 'Unknown'}</p>
                        <p><strong>Generations:</strong> ${data.generations || 'Unknown'}</p>
                        <p><strong>Grid Size:</strong> ${data.grid_size || 'Unknown'}</p>
                        <p><strong>Timestamp:</strong> ${data.timestamp || 'Unknown'}</p>
                        ${data.morphic_influences ? `
                            <h4>🧬 Morphic Influence Rate</h4>
                            <p><strong>${((data.morphic_influences.length / (data.generations * data.grid_size * data.grid_size)) * 100).toFixed(1)}%</strong> of decisions influenced by pattern memory</p>
                        ` : ''}
                    `;
                } catch (error) {
                    contentDiv.innerHTML = '<div class="error">Error loading simulation: ' + error.message + '</div>';
                }
            }

            // Enhanced visualization functions
            let selectedRun = null;
            let visualizationCache = new Map();

            async function loadRunSelector() {
                const selector = document.getElementById('run-selector');

                try {
                    const response = await fetch('/api/simulations/recent');
                    const files = await response.json();

                    selector.innerHTML = '<option value="">Select a simulation run...</option>';
                    files.forEach(file => {
                        const option = document.createElement('option');
                        option.value = file.path;
                        option.textContent = `${file.name} (${file.type}) - ${file.modified}`;
                        selector.appendChild(option);
                    });
                } catch (error) {
                    console.error('Error loading runs:', error);
                }
            }

            function onRunSelected() {
                const selector = document.getElementById('run-selector');
                selectedRun = selector.value;

                const chartBtn = document.getElementById('chart-btn');
                const animateBtn = document.getElementById('animate-btn');

                if (selectedRun) {
                    chartBtn.disabled = false;
                    animateBtn.disabled = false;
                } else {
                    chartBtn.disabled = true;
                    animateBtn.disabled = true;
                }
            }

            function showProgress(text, percentage) {
                const progressDiv = document.getElementById('viz-progress');
                const progressBar = document.getElementById('progress-bar');
                const progressText = document.getElementById('progress-text');

                progressDiv.style.display = 'block';
                progressBar.style.width = percentage + '%';
                progressText.textContent = text;

                if (percentage >= 100) {
                    setTimeout(() => {
                        progressDiv.style.display = 'none';
                    }, 1000);
                }
            }

            async function generateSingleChart() {
                if (!selectedRun) {
                    alert('Please select a simulation run first');
                    return;
                }

                const content = document.getElementById('visualization-content');
                showProgress('Loading simulation data...', 20);

                try {
                    // Get selected visualization types
                    const selectedTypes = [];
                    if (document.getElementById('pop-chart').checked) selectedTypes.push('population');
                    if (document.getElementById('morphic-heatmap').checked) selectedTypes.push('heatmap');
                    if (document.getElementById('pattern-analysis').checked) selectedTypes.push('pattern');
                    if (document.getElementById('crystal-usage').checked) selectedTypes.push('crystal');

                    if (selectedTypes.length === 0) {
                        selectedTypes.push('population'); // Default
                    }

                    // Check cache first
                    const cacheKey = `chart_${selectedRun}_${selectedTypes.join('-')}`;
                    if (visualizationCache.has(cacheKey)) {
                        showProgress('Loading from cache...', 80);
                        content.innerHTML = visualizationCache.get(cacheKey);
                        showProgress('Complete!', 100);
                        return;
                    }

                    showProgress('Generating visualizations...', 60);

                    // Call the actual visualization API
                    const response = await fetch('/api/visualizations/single', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            path: selectedRun,
                            types: selectedTypes
                        })
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }

                    const result = await response.json();
                    showProgress('Rendering images...', 90);

                    let chartHtml = '<div style="padding: 20px;">';
                    chartHtml += `<h3>Visualization Results (${result.generated} charts)</h3>`;

                    result.charts.forEach(chart => {
                        if (chart.error) {
                            chartHtml += `
                                <div style="margin: 20px 0; padding: 15px; background: #f8d7da; border-radius: 8px; border-left: 4px solid #dc3545;">
                                    <h5>${chart.title}</h5>
                                    <p style="color: #721c24;">${chart.error}</p>
                                </div>
                            `;
                        } else {
                            chartHtml += `
                                <div style="margin: 30px 0; text-align: center;">
                                    <h4>${chart.title}</h4>
                                    <div style="margin: 20px 0;">
                                        <img src="${chart.url}" alt="${chart.title}"
                                             style="max-width: 100%; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                                    </div>
                                    <div style="background: #e3f2fd; padding: 10px; border-radius: 4px; margin: 10px 0;">
                                        ${chart.cached ? '💾 Loaded from cache' : '✨ Freshly generated'} • ${chart.type}
                                    </div>
                                    <div style="margin-top: 15px;">
                                        <a href="${chart.url}" download="${chart.title}.png" class="btn">📥 Download</a>
                                    </div>
                                </div>
                            `;
                        }
                    });

                    chartHtml += '</div>';

                    // Cache the result
                    visualizationCache.set(cacheKey, chartHtml);
                    content.innerHTML = chartHtml;
                    showProgress('Complete!', 100);

                } catch (error) {
                    content.innerHTML = '<div class="error">Error generating charts: ' + error.message + '</div>';
                    showProgress('Error occurred', 100);
                }
            }

            async function generateAnimation() {
                if (!selectedRun) {
                    alert('Please select a simulation run first');
                    return;
                }

                const content = document.getElementById('visualization-content');
                showProgress('Preparing animation data...', 30);

                try {
                    // Check cache first
                    const cacheKey = `animation_${selectedRun}`;
                    if (visualizationCache.has(cacheKey)) {
                        showProgress('Loading from cache...', 80);
                        content.innerHTML = visualizationCache.get(cacheKey);
                        showProgress('Complete!', 100);
                        return;
                    }

                    showProgress('Rendering animation frames...', 70);

                    // Call the animation API
                    const response = await fetch('/api/visualizations/animation', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ path: selectedRun })
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }

                    const result = await response.json();
                    showProgress('Loading animation...', 90);

                    const animationHtml = `
                        <div style="text-align: center; padding: 20px;">
                            <h4>${result.title}</h4>
                            <div style="margin: 20px 0;">
                                <img src="${result.url}" alt="${result.title}"
                                     style="max-width: 100%; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                            </div>
                            <div style="background: #f8d7da; padding: 10px; border-radius: 4px; margin: 10px 0;">
                                ${result.cached ? '💾 Loaded from cache' : '✨ Freshly generated'} • Animation frames
                            </div>
                            <div style="background: #fff3cd; padding: 10px; border-radius: 4px; margin: 10px 0;">
                                <strong>Note:</strong> This shows key animation frames. For interactive animations, use the enhanced viewer.
                            </div>
                            <div style="margin-top: 15px;">
                                <a href="${result.url}" download="${result.title}.png" class="btn">📥 Download Frames</a>
                            </div>
                        </div>
                    `;

                    // Cache the result
                    visualizationCache.set(cacheKey, animationHtml);
                    content.innerHTML = animationHtml;
                    showProgress('Animation ready!', 100);

                } catch (error) {
                    content.innerHTML = '<div class="error">Error generating animation: ' + error.message + '</div>';
                    showProgress('Error occurred', 100);
                }
            }

            async function generateOverviewCharts() {
                const content = document.getElementById('visualization-content');
                showProgress('Loading recent simulations...', 25);

                try {
                    showProgress('Analyzing data...', 50);
                    showProgress('Generating overview charts...', 75);

                    const response = await fetch('/api/visualizations/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ type: 'overview', refresh: true })
                    });
                    const result = await response.json();

                    content.innerHTML = `
                        <div style="margin-top: 20px;">
                            ${result.charts.map(chart => `
                                <div style="margin-bottom: 30px; text-align: center;">
                                    <h4>${chart.title}</h4>
                                    <img src="${chart.url}" alt="${chart.title}" style="max-width: 100%; border: 1px solid #ddd; border-radius: 8px;">
                                </div>
                            `).join('')}
                            <div style="text-align: center; margin-top: 20px; padding: 15px; background: #e3f2fd; border-radius: 8px;">
                                <p>${result.message}</p>
                            </div>
                        </div>
                    `;
                    showProgress('Overview complete!', 100);
                } catch (error) {
                    content.innerHTML = '<div class="error">Error generating overview: ' + error.message + '</div>';
                    showProgress('Error occurred', 100);
                }
            }

            async function loadCachedVisualizations() {
                const cacheList = document.getElementById('cache-list');

                // Also load server-side cached files
                try {
                    const response = await fetch('/api/visualizations/cached');
                    const serverCache = await response.json();

                    if (visualizationCache.size === 0 && serverCache.files.length === 0) {
                        cacheList.innerHTML = '<p style="text-align: center; color: #666;">No cached visualizations found</p>';
                        return;
                    }

                    let cacheHtml = '';

                    // Add server-side cached files
                    serverCache.files.forEach(file => {
                        const displayName = file.name.replace(/^(single_|overview_|animation_|heatmap_|pattern_|crystal_)/, '').replace(/\.png$/, '');
                        cacheHtml += `
                            <div style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; background: white; text-align: center;">
                                <div style="margin-bottom: 10px;">
                                    <img src="${file.url}" alt="${file.name}"
                                         style="max-width: 100%; max-height: 120px; border-radius: 4px; cursor: pointer;"
                                         onclick="showFullVisualization('${file.url}', '${file.name}')">
                                </div>
                                <h6 style="margin: 5px 0; font-size: 12px; color: #666;">${file.type}</h6>
                                <div style="margin: 5px 0; font-size: 11px; color: #999;">${file.size} • ${file.modified}</div>
                                <button class="btn" onclick="showFullVisualization('${file.url}', '${file.name}')"
                                        style="font-size: 12px; padding: 4px 8px; width: 100%;">👁️ View</button>
                            </div>
                        `;
                    });

                    // Add client-side cached items
                    visualizationCache.forEach((content, key) => {
                        const runName = key.replace(/^(chart_|animation_)/, '').split('/').pop();
                        const type = key.includes('animation') ? 'Animation' : 'Chart';
                        cacheHtml += `
                            <div style="border: 1px solid #ddd; border-radius: 8px; padding: 15px; background: white;">
                                <h6 style="margin: 0 0 5px 0; color: #007bff;">${type}</h6>
                                <div style="margin: 5px 0; font-size: 12px; color: #666;">${runName}</div>
                                <button class="btn" onclick="loadCachedVisualization('${key}')"
                                        style="font-size: 12px; padding: 4px 8px; width: 100%;">📊 Load</button>
                            </div>
                        `;
                    });

                    cacheList.innerHTML = cacheHtml || '<p style="text-align: center; color: #666;">No cached visualizations found</p>';
                } catch (error) {
                    console.error('Error loading cached visualizations:', error);
                    cacheList.innerHTML = '<p style="text-align: center; color: #dc3545;">Error loading cache</p>';
                }
            }

            function showFullVisualization(url, title) {
                const content = document.getElementById('visualization-content');
                content.innerHTML = `
                    <div style="text-align: center; padding: 20px;">
                        <h4>📊 ${title}</h4>
                        <div style="margin: 20px 0;">
                            <img src="${url}" alt="${title}"
                                 style="max-width: 100%; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                        </div>
                        <div style="background: #e3f2fd; padding: 10px; border-radius: 4px; margin: 10px 0;">
                            💾 Loaded from cache
                        </div>
                        <div style="margin-top: 15px;">
                            <a href="${url}" download="${title}" class="btn">📥 Download</a>
                        </div>
                    </div>
                `;
            }

            function loadCachedVisualization(cacheKey) {
                const content = document.getElementById('visualization-content');
                if (visualizationCache.has(cacheKey)) {
                    content.innerHTML = visualizationCache.get(cacheKey);
                }
            }

            function clearVisualizationCache() {
                visualizationCache.clear();
                document.getElementById('cache-list').innerHTML = '<p style="text-align: center; color: #666;">Cache cleared</p>';
                alert('Visualization cache cleared');
            }

            async function visualizeBatch(batchPath) {
                const content = document.getElementById('visualization-content');
                showProgress('Loading batch data...', 20);

                try {
                    showProgress('Analyzing batch files...', 50);

                    // Call the batch visualization API
                    const response = await fetch('/api/visualizations/batch', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ batch_path: batchPath })
                    });

                    if (!response.ok) {
                        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
                    }

                    const result = await response.json();
                    showProgress('Rendering batch visualization...', 90);

                    let batchHtml = '<div style="padding: 20px;">';
                    batchHtml += `<h3>📊 Batch Visualization: ${batchPath.split('/').pop()}</h3>`;
                    batchHtml += `<p>Analyzed ${result.files_processed} files from batch</p>`;

                    if (result.charts && result.charts.length > 0) {
                        result.charts.forEach(chart => {
                            batchHtml += `
                                <div style="margin: 30px 0; text-align: center;">
                                    <h4>${chart.title}</h4>
                                    <div style="margin: 20px 0;">
                                        <img src="${chart.url}" alt="${chart.title}"
                                             style="max-width: 100%; border: 1px solid #ddd; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1);">
                                    </div>
                                    <div style="background: #e3f2fd; padding: 10px; border-radius: 4px; margin: 10px 0;">
                                        ${chart.cached ? '💾 Loaded from cache' : '✨ Freshly generated'} • Batch Analysis
                                    </div>
                                    <div style="margin-top: 15px;">
                                        <a href="${chart.url}" download="${chart.title}.png" class="btn">📥 Download</a>
                                    </div>
                                </div>
                            `;
                        });
                    } else {
                        batchHtml += '<p>No visualizations available for this batch</p>';
                    }

                    batchHtml += '</div>';

                    content.innerHTML = batchHtml;
                    showProgress('Batch visualization complete!', 100);

                } catch (error) {
                    content.innerHTML = '<div class="error">Error visualizing batch: ' + error.message + '</div>';
                    showProgress('Error occurred', 100);
                }
            }

            // Legacy function for compatibility
            async function generateVisualization() {
                await generateOverviewCharts();
            }

            function refreshVisualization() {
                generateVisualization();
            }

            function startLiveMonitor() {
                document.getElementById('live-content').innerHTML = `
                    <div class="loading">Live monitoring not yet implemented</div>
                    <p>This feature will show real-time simulation progress in future versions.</p>
                `;
            }

            // Load recent simulations on page load
            document.addEventListener('DOMContentLoaded', function() {
                loadRecentSimulations();
                loadRunSelector();
                loadCachedVisualizations();

                // Add event listener for run selector
                const runSelector = document.getElementById('run-selector');
                if (runSelector) {
                    runSelector.addEventListener('change', onRunSelected);
                }
            });
        </script>
    </body>
    </html>
    """
    return html_content

@app.get("/user-guide", response_class=HTMLResponse)
async def user_guide():
    """Comprehensive user guide"""

    # Read the HTML template directly
    template_path = Path("web/templates/user_guide.html")
    if template_path.exists():
        with open(template_path, 'r', encoding='utf-8') as f:
            return f.read()

    # Fallback to basic markdown if template not found
    user_guide_markdown = """
# 📖 Emergence Simulator - User Guide

## 🌟 Overview

The **Emergence Simulator** is a scientific research platform designed to test **morphic resonance effects** in artificial systems. It combines Conway's Game of Life with large language model (LLM) decision-making to study emergent behaviors and memory crystal effects.

## 🚀 Getting Started

### Prerequisites
- **Python 3.8+** (Python 3.11 or 3.12 recommended for best compatibility)
- **Virtual environment support**
- **Internet connection** (for LLM API calls)

### Quick Setup
```bash
# 1. Set up environment and install dependencies
./launcher.sh

# 2. Start the server (auto-detects available port)
./run.sh

# 3. Or start manually after activating venv
source venv/bin/activate
python main.py
```

## 🏗️ Architecture & Features

### Core Components

#### 1. **Morphic Resonance Engine**
- **Memory Crystals**: Store pattern information across simulations
- **Morphic Fields**: Influence decision-making based on historical patterns
- **Resonance Detection**: Measures similarity between current and stored patterns

#### 2. **Conway's Game of Life Integration**
- **Enhanced Cellular Automata**: Traditional rules with LLM-driven decisions
- **Pattern Recognition**: Identifies and catalogs emergent structures
- **State Evolution**: Tracks generational changes and stability

#### 3. **LLM Decision Making**
- **OpenRouter Integration**: Supports multiple LLM models
- **Context-Aware Decisions**: Uses pattern history for informed choices
- **Caching System**: Optimizes API calls and response times

#### 4. **Database Layer**
- **SQLAlchemy ORM**: Async database operations
- **PostgreSQL Support**: Production-ready data storage
- **Migration System**: Schema versioning and updates

#### 5. **Web Interface**
- **FastAPI Backend**: High-performance API server
- **Interactive Viewer**: Real-time simulation visualization  
- **Results Dashboard**: Analysis and comparison tools

## 🔧 Configuration

### Environment Variables (`.env`)
```env
# Database Configuration
DATABASE_URL=sqlite:///emergence.db                    # Local SQLite
# DATABASE_URL=postgresql://user:pass@host/dbname      # Production PostgreSQL

# LLM Configuration
OPENROUTER_API_KEY=your_api_key_here                   # Required for LLM features
DEFAULT_MODEL=meta-llama/llama-3-70b-instruct          # Default LLM model

# Server Configuration
SECRET_KEY=your_secret_key_here                        # Change in production
BASE_URL=http://localhost:8000                         # Server base URL

# Optional Features
REDIS_URL=redis://localhost:6379                       # Caching (optional)
LOG_LEVEL=INFO                                         # Logging level
```

### Available LLM Models
- `meta-llama/llama-3-70b-instruct` (Recommended)
- `anthropic/claude-3-sonnet`
- `openai/gpt-4-turbo`
- `google/gemini-pro`

## 🎮 Usage Guide

### 1. **🚀 Comprehensive Training - Maximizing System Power**

#### **A. Setup for Maximum Performance**
```bash
# 1. Install dependencies including LLM integration
pip install requests  # Required for LLM calls

# 2. Configure environment for optimal results
export OPENROUTER_API_KEY="your_api_key_here"  # Enable LLM integration
export DATABASE_URL="sqlite:///emergence.db"   # Or PostgreSQL for production

# 3. Validate complete system
./training.sh --check-only
```

#### **B. Autopilot Training Runs - Full Scientific Studies**

**Small-Scale Validation (Fast Results):**
```bash
# Quick validation run (2-3 minutes)
./training.sh --mode=morphic --generations=20 --crystal-count=3 --grid-size=10

# Control comparison
./training.sh --mode=control --generations=20 --grid-size=10

# View results
cat results/simulation_morphic_*.json | grep -E "(decisions influenced|similarity-influence correlation)"
```

**Medium-Scale Research (5-10 minutes):**
```bash
# Research-grade morphic simulation
./training.sh --mode=morphic --generations=50 --crystal-count=5 --grid-size=15

# Control baseline
./training.sh --mode=control --generations=50 --grid-size=15

# Expected results: 30-50% decision influence rate
```

**Large-Scale Scientific Study (15-30 minutes):**
```bash
# Publication-quality run with LLM integration
export OPENROUTER_API_KEY="your_key"
./training.sh --mode=morphic --generations=100 --crystal-count=10 --grid-size=25

# Multiple control runs for statistical significance
for i in {1..3}; do
  ./training.sh --mode=control --generations=100 --grid-size=25
done

# Expected results: 40-60% decision influence, correlation >0.3
```

#### **C. Advanced Parameter Optimization**

**Pattern Scale Experiments:**
```bash
# Small patterns (3x3 focus)
./training.sh --mode=morphic --generations=75 --crystal-count=8 --grid-size=12

# Large patterns (7x7 focus)
./training.sh --mode=morphic --generations=75 --crystal-count=8 --grid-size=30

# Compare adaptive neighborhood effects
```

**Crystal Density Studies:**
```bash
# Low crystal density
./training.sh --mode=morphic --generations=50 --crystal-count=2 --grid-size=20

# Medium crystal density
./training.sh --mode=morphic --generations=50 --crystal-count=5 --grid-size=20

# High crystal density
./training.sh --mode=morphic --generations=50 --crystal-count=10 --grid-size=20

# Analyze influence rate vs crystal density
```

**Similarity Threshold Analysis:**
```bash
# Run multiple simulations and analyze results/simulation_morphic_*.json
# Look for patterns in influence thresholds and correlation strengths
ls -la results/ | grep morphic
```

#### **D. Batch Processing for Statistical Rigor**

**Automated Batch Runner:**
```bash
#!/bin/bash
# Create comprehensive_study.sh

echo "🔬 Starting Comprehensive Morphic Resonance Study"
mkdir -p batch_results/$(date +%Y%m%d_%H%M)
cd batch_results/$(date +%Y%m%d_%H%M)

# Run 5 morphic simulations
for i in {1..5}; do
  echo "Running morphic simulation $i/5..."
  ../../training.sh --mode=morphic --generations=75 --crystal-count=7 --grid-size=20
  mv ../../results/simulation_morphic_*.json morphic_run_$i.json
done

# Run 5 control simulations
for i in {1..5}; do
  echo "Running control simulation $i/5..."
  ../../training.sh --mode=control --generations=75 --grid-size=20
  mv ../../results/simulation_control_*.json control_run_$i.json
done

echo "✅ Batch complete! Results in $(pwd)"
```

**Run the comprehensive study:**
```bash
chmod +x comprehensive_study.sh
./comprehensive_study.sh
```

### 2. **📊 Analyzing Maximum-Power Results**

#### **A. Real-Time Performance Monitoring**
```bash
# Watch live influence rates during simulation
tail -f logs/*.log | grep -E "(decisions influenced|LLM decision|High similarity)"

# Monitor pattern storage
watch "ls -la results/ | tail -5"
```

#### **B. Statistical Analysis Scripts**

**Influence Rate Analysis:**
```bash
# Extract key metrics from all morphic runs
grep -h "decisions influenced" results/simulation_morphic_*.json | \
  sed 's/.*(\([0-9.]*\)%).*/\1/' | \
  awk '{sum+=$1; count++} END {print "Average influence rate:", sum/count "%"}'

# Correlation strength analysis
grep -h "similarity-influence correlation" results/simulation_morphic_*.json
```

**LLM Integration Analysis:**
```bash
# Count LLM decision events
grep -c "LLM decision" logs/*.log

# Analyze high-similarity pattern triggers
grep "High similarity pattern detected" logs/*.log | wc -l
```

#### **C. Comparative Effectiveness**

**Performance Comparison Script:**
```bash
#!/bin/bash
# Create analyze_results.sh

echo "📈 Morphic vs Control Analysis"
echo "=============================="

# Morphic results
echo "🧬 MORPHIC SIMULATIONS:"
for file in results/simulation_morphic_*.json; do
  echo "File: $(basename $file)"
  echo "  - $(jq -r '.final_population' $file) final population"
  echo "  - $(jq -r '.avg_population' $file) avg population"
  echo "  - $(jq -r '.morphic_influences | length' $file) morphic influences"
done

echo ""
echo "🎯 CONTROL SIMULATIONS:"
for file in results/simulation_control_*.json; do
  echo "File: $(basename $file)"
  echo "  - $(jq -r '.final_population' $file) final population"
  echo "  - $(jq -r '.avg_population' $file) avg population"
done
```

### 3. **🎯 Maximizing Morphic Effects**

#### **A. Optimal Parameter Combinations**

**High-Influence Configuration:**
```bash
# Maximum morphic influence setup
export OPENROUTER_API_KEY="your_key"  # Enable LLM for 95%+ influence
./training.sh --mode=morphic --generations=100 --crystal-count=15 --grid-size=25

# Expected: 50-70% influence rate with strong correlation
```

**Pattern Diversity Maximization:**
```bash
# Multiple grid sizes for diverse patterns
for size in 15 20 25; do
  ./training.sh --mode=morphic --generations=60 --crystal-count=8 --grid-size=$size
done

# Analyze pattern scale distribution in results
```

**LLM Decision Optimization:**
```bash
# Focus on high-similarity triggers
# Monitor logs for "High similarity pattern detected"
# Target: 10-20% of decisions should trigger LLM consultation
```

#### **B. Advanced Validation Protocols**

**Reproducibility Testing:**
```bash
# Same parameters, different random seeds
for seed in {42,123,789}; do
  RANDOM_SEED=$seed ./training.sh --mode=morphic --generations=50 --crystal-count=5 --grid-size=18
done

# Compare influence patterns across runs
```

**Morphic Memory Validation:**
```bash
# Long-term pattern accumulation test
./training.sh --mode=morphic --generations=200 --crystal-count=12 --grid-size=22

# Verify pattern storage growth
grep "structural patterns stored" results/simulation_morphic_*.json
```

### 4. **🔬 Research Methodologies**

#### **A. Scientific Study Design**

**Complete Research Protocol:**
```bash
#!/bin/bash
# Create research_protocol.sh - Publication-ready study

echo "🧬 COMPREHENSIVE MORPHIC RESONANCE RESEARCH STUDY"
echo "================================================="

# 1. System validation
echo "Phase 1: System Validation"
./training.sh --check-only

# 2. Baseline establishment (10 control runs)
echo "Phase 2: Control Baseline (n=10)"
mkdir -p research_study/controls
for i in {1..10}; do
  echo "  Control run $i/10..."
  ./training.sh --mode=control --generations=100 --grid-size=20
  mv results/simulation_control_*.json research_study/controls/control_$i.json
done

# 3. Morphic experiments (10 runs)
echo "Phase 3: Morphic Experiments (n=10)"
mkdir -p research_study/morphic
export OPENROUTER_API_KEY="your_key"  # Enable for max effect
for i in {1..10}; do
  echo "  Morphic run $i/10..."
  ./training.sh --mode=morphic --generations=100 --crystal-count=8 --grid-size=20
  mv results/simulation_morphic_*.json research_study/morphic/morphic_$i.json
done

# 4. Statistical analysis
echo "Phase 4: Statistical Analysis"
python3 -c "
import json, statistics
import glob

# Control analysis
controls = []
for file in glob.glob('research_study/controls/*.json'):
    with open(file) as f:
        data = json.load(f)
        controls.append(data['avg_population'])

# Morphic analysis
morphics = []
influences = []
for file in glob.glob('research_study/morphic/*.json'):
    with open(file) as f:
        data = json.load(f)
        morphics.append(data['avg_population'])
        if 'morphic_influences' in data:
            influences.append(len(data['morphic_influences']))

print(f'📊 RESEARCH RESULTS:')
print(f'Control avg population: {statistics.mean(controls):.2f} ± {statistics.stdev(controls):.2f}')
print(f'Morphic avg population: {statistics.mean(morphics):.2f} ± {statistics.stdev(morphics):.2f}')
print(f'Avg morphic influences: {statistics.mean(influences):.0f}')
print(f'Population difference: {statistics.mean(morphics) - statistics.mean(controls):.2f}')
"

echo "✅ Research study complete! Results in research_study/"
```

#### **B. Parameter Space Exploration**

**Grid Size Impact Study:**
```bash
# Study morphic effects across different scales
for grid_size in 15 20 25 30; do
  echo "Testing grid size: ${grid_size}x${grid_size}"
  ./training.sh --mode=morphic --generations=75 --crystal-count=6 --grid-size=$grid_size
  ./training.sh --mode=control --generations=75 --grid-size=$grid_size
done

# Analyze scale-dependent effects
```

**Crystal Density Optimization:**
```bash
# Find optimal crystal count for maximum influence
for crystals in 3 6 9 12 15; do
  echo "Testing crystal count: $crystals"
  ./training.sh --mode=morphic --generations=60 --crystal-count=$crystals --grid-size=22
done

# Expected: Higher crystal counts → Higher influence rates
```

**Generation Length Studies:**
```bash
# Study long-term morphic accumulation
for gens in 50 100 200 400; do
  echo "Testing generation length: $gens"
  ./training.sh --mode=morphic --generations=$gens --crystal-count=8 --grid-size=20
done

# Analyze: Does longer evolution → stronger morphic effects?
```

#### **C. Advanced Analysis Techniques**

**Real-Time Monitoring Dashboard:**
```bash
# Create monitoring script
cat > monitor_simulation.sh << 'EOF'
#!/bin/bash
while true; do
  clear
  echo "🔍 REAL-TIME MORPHIC RESONANCE MONITORING"
  echo "========================================="

  # Current simulations
  echo "📊 Active Simulations:"
  ps aux | grep training.sh | grep -v grep | wc -l

  # Recent results
  echo "📈 Latest Results:"
  ls -lt results/simulation_*.json | head -3

  # Influence metrics from latest run
  latest=$(ls -t results/simulation_morphic_*.json | head -1)
  if [ -f "$latest" ]; then
    echo "🧬 Latest Morphic Run:"
    echo "  - File: $(basename $latest)"
    echo "  - Decision influences: $(jq -r '.morphic_influences | length' $latest)"
    echo "  - Population: $(jq -r '.avg_population' $latest)"
  fi

  sleep 5
done
EOF
chmod +x monitor_simulation.sh
```

**Pattern Analysis Tools:**
```bash
# Create pattern analysis script
cat > analyze_patterns.sh << 'EOF'
#!/bin/bash
echo "🔍 MORPHIC PATTERN ANALYSIS"
echo "=========================="

for file in results/simulation_morphic_*.json; do
  echo "File: $(basename $file)"

  # Extract pattern metrics
  patterns=$(jq -r '.crystals[] | .patterns | length' $file | paste -sd+ | bc)
  influences=$(jq -r '.morphic_influences | length' $file)
  population=$(jq -r '.avg_population' $file)

  echo "  - Stored patterns: $patterns"
  echo "  - Morphic influences: $influences"
  echo "  - Avg population: $population"
  echo "  - Influence rate: $(echo "scale=1; $influences * 100 / ($population * 100)" | bc)%"
  echo ""
done
EOF
chmod +x analyze_patterns.sh
```

### 5. **📈 Performance Optimization & Scaling**

#### **A. High-Performance Configuration**

**Maximum Throughput Setup:**
```bash
# Optimize for research-grade performance
export DATABASE_URL="postgresql://user:pass@localhost/emergence"  # Use PostgreSQL
export OPENROUTER_API_KEY="your_key"  # Enable all LLM features
export LOG_LEVEL="WARNING"  # Reduce logging overhead

# Large-scale batch processing
./training.sh --mode=morphic --generations=500 --crystal-count=20 --grid-size=35
```

**Memory and Storage Management:**
```bash
# Monitor storage usage
du -sh results/
df -h .

# Cleanup old results (keep last 50)
ls -t results/simulation_*.json | tail -n +51 | xargs rm -f

# Archive important studies
tar -czf morphic_study_$(date +%Y%m%d).tar.gz research_study/
```

#### **B. Parallel Processing**

**Multi-Core Utilization:**
```bash
# Run multiple studies in parallel
{
  ./training.sh --mode=morphic --generations=100 --crystal-count=5 --grid-size=18 &
  ./training.sh --mode=morphic --generations=100 --crystal-count=10 --grid-size=18 &
  ./training.sh --mode=control --generations=100 --grid-size=18 &
  wait
}

echo "✅ Parallel batch complete"
```

**Distributed Research:**
```bash
# For multiple machines/containers
# Machine 1: Small grids
for size in 12 15 18; do
  ./training.sh --mode=morphic --generations=80 --crystal-count=7 --grid-size=$size
done

# Machine 2: Large grids
for size in 22 25 28; do
  ./training.sh --mode=morphic --generations=80 --crystal-count=7 --grid-size=$size
done
```

### 6. **🎯 Expected Results & Interpretation**

#### **A. Key Performance Indicators**

**Successful Morphic Implementation Shows:**
- **Decision Influence Rate**: 30-60% (vs 0% in control)
- **Similarity-Influence Correlation**: 0.3-0.7 (strong positive)
- **Pattern Storage**: 5-50 structural patterns per crystal
- **LLM Activation**: 5-20% of high-similarity patterns
- **Population Differences**: Measurable vs control groups

#### **B. Troubleshooting Performance**

**Low Influence Rates (<20%):**
```bash
# Check crystal count
./training.sh --mode=morphic --generations=50 --crystal-count=12 --grid-size=20

# Verify pattern storage
grep "structural patterns stored" results/simulation_morphic_*.json
```

**No LLM Activation:**
```bash
# Verify API key
echo $OPENROUTER_API_KEY

# Check for high-similarity patterns
grep "High similarity pattern detected" logs/*.log
```

**API Endpoints for Programmatic Access:**
```bash
# Start a new simulation
POST /api/simulations/
{
  "name": "max_performance_study",
  "mode": "morphic",
  "generations": 100,
  "crystal_count": 10,
  "grid_size": 25,
  "enable_llm": true
}

# Get simulation status
GET /api/simulations/{simulation_id}

# Get comprehensive results
GET /api/simulations/{simulation_id}/results
```

### 7. **🏆 Advanced Research Workflows**

#### **A. Publication-Ready Studies**

**Complete Scientific Protocol:**
```bash
#!/bin/bash
# Create publication_study.sh - For academic papers

echo "📄 PUBLICATION-READY MORPHIC RESONANCE STUDY"
echo "============================================"

# Parameters for rigorous study
STUDY_NAME="morphic_resonance_$(date +%Y%m%d)"
SAMPLE_SIZE=20
GENERATIONS=150
GRID_SIZE=22
CRYSTAL_COUNT=8

mkdir -p studies/$STUDY_NAME/{morphic,control,analysis}

# Phase 1: Control group (n=20)
echo "Phase 1: Control Group (n=$SAMPLE_SIZE)"
for i in $(seq 1 $SAMPLE_SIZE); do
  echo "  Control $i/$SAMPLE_SIZE..."
  ./training.sh --mode=control --generations=$GENERATIONS --grid-size=$GRID_SIZE
  mv results/simulation_control_*.json studies/$STUDY_NAME/control/control_$(printf "%02d" $i).json
done

# Phase 2: Morphic group (n=20)
echo "Phase 2: Morphic Group (n=$SAMPLE_SIZE)"
export OPENROUTER_API_KEY="your_key"
for i in $(seq 1 $SAMPLE_SIZE); do
  echo "  Morphic $i/$SAMPLE_SIZE..."
  ./training.sh --mode=morphic --generations=$GENERATIONS --crystal-count=$CRYSTAL_COUNT --grid-size=$GRID_SIZE
  mv results/simulation_morphic_*.json studies/$STUDY_NAME/morphic/morphic_$(printf "%02d" $i).json
done

# Phase 3: Statistical analysis
echo "Phase 3: Statistical Analysis"
python3 > studies/$STUDY_NAME/analysis/statistical_report.txt << 'PYEOF'
import json, glob, statistics
import numpy as np
from scipy import stats

# Load data
control_data = []
morphic_data = []
influence_data = []

for file in glob.glob(f'studies/{STUDY_NAME}/control/*.json'):
    with open(file) as f:
        data = json.load(f)
        control_data.append({
            'avg_population': data['avg_population'],
            'final_population': data['final_population'],
            'stability_score': data['stability_score'],
            'complexity_score': data['complexity_score']
        })

for file in glob.glob(f'studies/{STUDY_NAME}/morphic/*.json'):
    with open(file) as f:
        data = json.load(f)
        morphic_data.append({
            'avg_population': data['avg_population'],
            'final_population': data['final_population'],
            'stability_score': data['stability_score'],
            'complexity_score': data['complexity_score'],
            'morphic_influences': len(data.get('morphic_influences', []))
        })
        influence_data.append(len(data.get('morphic_influences', [])))

# Statistical analysis
print("MORPHIC RESONANCE RESEARCH STUDY RESULTS")
print("=" * 50)
print(f"Sample Size: {len(control_data)} control, {len(morphic_data)} morphic")
print()

# Population metrics
control_pop = [d['avg_population'] for d in control_data]
morphic_pop = [d['avg_population'] for d in morphic_data]

print("POPULATION ANALYSIS:")
print(f"Control avg population: {statistics.mean(control_pop):.2f} ± {statistics.stdev(control_pop):.2f}")
print(f"Morphic avg population: {statistics.mean(morphic_pop):.2f} ± {statistics.stdev(morphic_pop):.2f}")

# T-test for significance
t_stat, p_value = stats.ttest_ind(control_pop, morphic_pop)
print(f"T-test p-value: {p_value:.6f}")
print(f"Significant difference: {'Yes' if p_value < 0.05 else 'No'}")
print()

# Morphic influence analysis
print("MORPHIC INFLUENCE ANALYSIS:")
print(f"Avg morphic influences per run: {statistics.mean(influence_data):.0f}")
print(f"Total morphic decisions: {sum(influence_data)}")
print(f"Influence rate: {(sum(influence_data) / (len(morphic_data) * 150 * 22 * 22)) * 100:.1f}%")
print()

# Effect size (Cohen's d)
pooled_std = np.sqrt(((len(control_pop)-1)*np.var(control_pop) + (len(morphic_pop)-1)*np.var(morphic_pop)) / (len(control_pop)+len(morphic_pop)-2))
cohens_d = (statistics.mean(morphic_pop) - statistics.mean(control_pop)) / pooled_std
print(f"Effect size (Cohen's d): {cohens_d:.3f}")
print(f"Effect magnitude: {'Small' if abs(cohens_d) < 0.5 else 'Medium' if abs(cohens_d) < 0.8 else 'Large'}")
PYEOF

echo "✅ Publication study complete!"
echo "📊 Results available in: studies/$STUDY_NAME/"
echo "📄 Statistical report: studies/$STUDY_NAME/analysis/statistical_report.txt"
```

#### **B. Long-Term Evolution Studies**

**Extended Evolution Protocol:**
```bash
#!/bin/bash
# Long-term morphic accumulation study

echo "🕰️ LONG-TERM MORPHIC EVOLUTION STUDY"
echo "==================================="

# Study morphic effects over extended periods
STUDY_ID="longterm_$(date +%Y%m%d_%H%M)"
mkdir -p longterm_studies/$STUDY_ID

# Progressive generation lengths
for generations in 100 200 500 1000; do
  echo "Running ${generations}-generation study..."

  # Morphic run
  export OPENROUTER_API_KEY="your_key"
  ./training.sh --mode=morphic --generations=$generations --crystal-count=10 --grid-size=25
  mv results/simulation_morphic_*.json longterm_studies/$STUDY_ID/morphic_${generations}gen.json

  # Control run
  ./training.sh --mode=control --generations=$generations --grid-size=25
  mv results/simulation_control_*.json longterm_studies/$STUDY_ID/control_${generations}gen.json

  echo "  ✅ ${generations}-generation study complete"
done

# Analysis: How do morphic effects change over time?
python3 << 'EOF'
import json, glob
import matplotlib.pyplot as plt

generations = [100, 200, 500, 1000]
morphic_influences = []
control_populations = []
morphic_populations = []

for gen in generations:
    # Morphic data
    morphic_file = f'longterm_studies/{STUDY_ID}/morphic_{gen}gen.json'
    with open(morphic_file) as f:
        data = json.load(f)
        morphic_influences.append(len(data.get('morphic_influences', [])))
        morphic_populations.append(data['avg_population'])

    # Control data
    control_file = f'longterm_studies/{STUDY_ID}/control_{gen}gen.json'
    with open(control_file) as f:
        data = json.load(f)
        control_populations.append(data['avg_population'])

print("LONG-TERM EVOLUTION RESULTS:")
print("Generation Length | Morphic Influences | Morphic Pop | Control Pop | Difference")
print("-" * 75)
for i, gen in enumerate(generations):
    diff = morphic_populations[i] - control_populations[i]
    print(f"{gen:13d} | {morphic_influences[i]:17d} | {morphic_populations[i]:10.1f} | {control_populations[i]:10.1f} | {diff:+9.1f}")

# Save visualization data
with open(f'longterm_studies/{STUDY_ID}/evolution_data.json', 'w') as f:
    json.dump({
        'generations': generations,
        'morphic_influences': morphic_influences,
        'morphic_populations': morphic_populations,
        'control_populations': control_populations
    }, f, indent=2)
EOF

echo "📈 Long-term study data saved to: longterm_studies/$STUDY_ID/"
```

### 8. **🎯 Maximizing Research Impact**

#### **A. Multi-Scale Analysis**

**Cross-Scale Morphic Study:**
```bash
#!/bin/bash
# Study morphic effects across multiple scales simultaneously

echo "🔬 MULTI-SCALE MORPHIC RESONANCE ANALYSIS"
echo "========================================"

TIMESTAMP=$(date +%Y%m%d_%H%M)
mkdir -p multiscale_study_$TIMESTAMP

# Test matrix: Grid sizes x Crystal densities
grid_sizes=(15 20 25 30)
crystal_counts=(5 8 12 15)

for grid in "${grid_sizes[@]}"; do
  for crystals in "${crystal_counts[@]}"; do
    echo "Testing: ${grid}x${grid} grid, $crystals crystals"

    # Morphic run
    ./training.sh --mode=morphic --generations=80 --crystal-count=$crystals --grid-size=$grid
    mv results/simulation_morphic_*.json multiscale_study_$TIMESTAMP/morphic_g${grid}_c${crystals}.json

    # Control run
    ./training.sh --mode=control --generations=80 --grid-size=$grid
    mv results/simulation_control_*.json multiscale_study_$TIMESTAMP/control_g${grid}.json
  done
done

# Generate heatmap analysis
python3 << 'EOF'
import json, glob
import numpy as np

# Build results matrix
grid_sizes = [15, 20, 25, 30]
crystal_counts = [5, 8, 12, 15]

influence_matrix = np.zeros((len(grid_sizes), len(crystal_counts)))
population_diff_matrix = np.zeros((len(grid_sizes), len(crystal_counts)))

for i, grid in enumerate(grid_sizes):
    # Get control baseline for this grid size
    control_file = f'multiscale_study_{TIMESTAMP}/control_g{grid}.json'
    with open(control_file) as f:
        control_pop = json.load(f)['avg_population']

    for j, crystals in enumerate(crystal_counts):
        # Get morphic results
        morphic_file = f'multiscale_study_{TIMESTAMP}/morphic_g{grid}_c{crystals}.json'
        with open(morphic_file) as f:
            data = json.load(f)
            influences = len(data.get('morphic_influences', []))
            morphic_pop = data['avg_population']

            # Calculate metrics
            total_decisions = 80 * grid * grid  # generations * grid area
            influence_rate = (influences / total_decisions) * 100
            population_diff = morphic_pop - control_pop

            influence_matrix[i, j] = influence_rate
            population_diff_matrix[i, j] = population_diff

print("INFLUENCE RATE MATRIX (%):")
print("Grid\\Crystals", end="")
for c in crystal_counts:
    print(f"{c:8d}", end="")
print()
for i, g in enumerate(grid_sizes):
    print(f"{g:11d}", end="")
    for j in range(len(crystal_counts)):
        print(f"{influence_matrix[i,j]:8.1f}", end="")
    print()

print("\nPOPULATION DIFFERENCE MATRIX:")
print("Grid\\Crystals", end="")
for c in crystal_counts:
    print(f"{c:8d}", end="")
print()
for i, g in enumerate(grid_sizes):
    print(f"{g:11d}", end="")
    for j in range(len(crystal_counts)):
        print(f"{population_diff_matrix[i,j]:8.1f}", end="")
    print()

# Find optimal parameters
max_influence_idx = np.unravel_index(np.argmax(influence_matrix), influence_matrix.shape)
optimal_grid = grid_sizes[max_influence_idx[0]]
optimal_crystals = crystal_counts[max_influence_idx[1]]
max_influence = influence_matrix[max_influence_idx]

print(f"\nOPTIMAL CONFIGURATION:")
print(f"Grid size: {optimal_grid}x{optimal_grid}")
print(f"Crystal count: {optimal_crystals}")
print(f"Max influence rate: {max_influence:.1f}%")
EOF

echo "🎯 Multi-scale analysis complete! Results in multiscale_study_$TIMESTAMP/"
```

#### **B. Automated Research Pipeline**

**Complete Automation Script:**
```bash
#!/bin/bash
# Ultimate automated research pipeline

echo "🤖 AUTOMATED MORPHIC RESONANCE RESEARCH PIPELINE"
echo "==============================================="

PIPELINE_ID="pipeline_$(date +%Y%m%d_%H%M%S)"
mkdir -p automated_research/$PIPELINE_ID/{raw_data,analysis,reports}

# Configuration
export OPENROUTER_API_KEY="your_key"
TOTAL_RUNS=50
GENERATIONS=100
GRID_SIZE=20
CRYSTAL_COUNT=8

echo "📋 Pipeline Configuration:"
echo "  - Total runs: $TOTAL_RUNS (25 morphic, 25 control)"
echo "  - Generations per run: $GENERATIONS"
echo "  - Grid size: ${GRID_SIZE}x${GRID_SIZE}"
echo "  - Crystal count: $CRYSTAL_COUNT"
echo ""

# Progress tracking
start_time=$(date +%s)

# Run studies with progress indicators
for i in $(seq 1 25); do
    echo -ne "🧬 Morphic runs: [$i/25] "
    ./training.sh --mode=morphic --generations=$GENERATIONS --crystal-count=$CRYSTAL_COUNT --grid-size=$GRID_SIZE > /dev/null 2>&1
    mv results/simulation_morphic_*.json automated_research/$PIPELINE_ID/raw_data/morphic_$(printf "%03d" $i).json
    echo "✅"
done

for i in $(seq 1 25); do
    echo -ne "🎯 Control runs: [$i/25] "
    ./training.sh --mode=control --generations=$GENERATIONS --grid-size=$GRID_SIZE > /dev/null 2>&1
    mv results/simulation_control_*.json automated_research/$PIPELINE_ID/raw_data/control_$(printf "%03d" $i).json
    echo "✅"
done

# Comprehensive analysis
echo "📊 Running comprehensive analysis..."

python3 > automated_research/$PIPELINE_ID/reports/comprehensive_report.md << 'PYEOF'
import json, glob, statistics
import numpy as np
from scipy import stats
from datetime import datetime

print("# Automated Morphic Resonance Research Report")
print(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"**Pipeline ID:** {PIPELINE_ID}")
print()

# Load all data
morphic_files = glob.glob(f'automated_research/{PIPELINE_ID}/raw_data/morphic_*.json')
control_files = glob.glob(f'automated_research/{PIPELINE_ID}/raw_data/control_*.json')

morphic_data = []
control_data = []

for file in morphic_files:
    with open(file) as f:
        data = json.load(f)
        morphic_data.append(data)

for file in control_files:
    with open(file) as f:
        data = json.load(f)
        control_data.append(data)

print("## 📊 Sample Statistics")
print(f"- **Morphic runs:** {len(morphic_data)}")
print(f"- **Control runs:** {len(control_data)}")
print(f"- **Generations per run:** {GENERATIONS}")
print(f"- **Grid size:** {GRID_SIZE}x{GRID_SIZE}")
print()

# Population analysis
morphic_pops = [d['avg_population'] for d in morphic_data]
control_pops = [d['avg_population'] for d in control_data]

print("## 🧬 Population Dynamics")
print("| Metric | Morphic | Control | Difference |")
print("|--------|---------|---------|------------|")
print(f"| Mean | {statistics.mean(morphic_pops):.2f} | {statistics.mean(control_pops):.2f} | {statistics.mean(morphic_pops) - statistics.mean(control_pops):+.2f} |")
print(f"| Std Dev | {statistics.stdev(morphic_pops):.2f} | {statistics.stdev(control_pops):.2f} | - |")
print(f"| Min | {min(morphic_pops):.2f} | {min(control_pops):.2f} | - |")
print(f"| Max | {max(morphic_pops):.2f} | {max(control_pops):.2f} | - |")
print()

# Statistical significance
t_stat, p_value = stats.ttest_ind(morphic_pops, control_pops)
print("## 📈 Statistical Analysis")
print(f"- **T-statistic:** {t_stat:.4f}")
print(f"- **P-value:** {p_value:.6f}")
print(f"- **Significant:** {'✅ Yes (p < 0.05)' if p_value < 0.05 else '❌ No (p ≥ 0.05)'}")
print()

# Effect size
pooled_std = np.sqrt(((len(morphic_pops)-1)*np.var(morphic_pops) + (len(control_pops)-1)*np.var(control_pops)) / (len(morphic_pops)+len(control_pops)-2))
cohens_d = (statistics.mean(morphic_pops) - statistics.mean(control_pops)) / pooled_std
print(f"- **Effect size (Cohen's d):** {cohens_d:.4f}")
magnitude = 'Large' if abs(cohens_d) >= 0.8 else 'Medium' if abs(cohens_d) >= 0.5 else 'Small'
print(f"- **Effect magnitude:** {magnitude}")
print()

# Morphic influence analysis
influences = [len(d.get('morphic_influences', [])) for d in morphic_data]
total_influences = sum(influences)
total_decisions = len(morphic_data) * GENERATIONS * GRID_SIZE * GRID_SIZE

print("## 🌀 Morphic Resonance Effects")
print(f"- **Total morphic influences:** {total_influences:,}")
print(f"- **Total decisions:** {total_decisions:,}")
print(f"- **Influence rate:** {(total_influences / total_decisions) * 100:.2f}%")
print(f"- **Avg influences per run:** {statistics.mean(influences):.0f}")
print()

# Pattern storage analysis
total_patterns = 0
for d in morphic_data:
    for crystal in d.get('crystals', []):
        total_patterns += len(crystal.get('patterns', []))

print("## 💎 Memory Crystal Analysis")
print(f"- **Total patterns stored:** {total_patterns}")
print(f"- **Avg patterns per run:** {total_patterns / len(morphic_data):.1f}")
print(f"- **Avg crystal utilization:** {(total_patterns / (len(morphic_data) * CRYSTAL_COUNT)):.1f} patterns/crystal")
print()

print("## 🎯 Conclusions")
if p_value < 0.05:
    print("✅ **Significant morphic resonance effects detected**")
    print(f"- Morphic simulations show significantly different behavior (p = {p_value:.6f})")
    print(f"- Effect size is {magnitude.lower()} (Cohen's d = {cohens_d:.4f})")
    print(f"- {(total_influences / total_decisions) * 100:.1f}% of decisions influenced by pattern similarity")
else:
    print("⚠️ **No significant morphic resonance effects detected**")
    print("- Consider increasing sample size or adjusting parameters")

print(f"\n---\n*Report generated by Automated Research Pipeline v1.0*")
PYEOF

# Calculate runtime
end_time=$(date +%s)
runtime=$((end_time - start_time))
hours=$((runtime / 3600))
minutes=$(((runtime % 3600) / 60))
seconds=$((runtime % 60))

echo ""
echo "🎉 AUTOMATED RESEARCH PIPELINE COMPLETE!"
echo "========================================"
echo "📁 Results directory: automated_research/$PIPELINE_ID/"
echo "📊 Comprehensive report: automated_research/$PIPELINE_ID/reports/comprehensive_report.md"
echo "⏱️  Total runtime: ${hours}h ${minutes}m ${seconds}s"
echo ""
echo "📋 Summary:"
echo "  - Morphic runs completed: 25"
echo "  - Control runs completed: 25"
echo "  - Total decisions analyzed: $((50 * GENERATIONS * GRID_SIZE * GRID_SIZE))"
echo "  - Statistical analysis: ✅ Complete"
echo ""
echo "📖 View report: cat automated_research/$PIPELINE_ID/reports/comprehensive_report.md"
```

### 9. **🏆 Power User Quick Reference**

#### **A. Maximum Impact Commands**
```bash
# 🚀 ULTIMATE MORPHIC RESONANCE COMMANDS

# Quick validation (2 minutes)
export OPENROUTER_API_KEY="your_key"
./training.sh --mode=morphic --generations=25 --crystal-count=5 --grid-size=12

# Research-grade run (10 minutes)
./training.sh --mode=morphic --generations=100 --crystal-count=10 --grid-size=20

# Publication study (60 minutes)
./automated_research_pipeline.sh  # Runs 50 simulations with full analysis

# Real-time monitoring
./monitor_simulation.sh &  # Background monitoring dashboard

# Statistical analysis
./analyze_patterns.sh  # Pattern analysis across all results

# Archive important studies
tar -czf morphic_study_$(date +%Y%m%d).tar.gz research_study/ results/
```

#### **B. Performance Optimization**
```bash
# Maximum throughput configuration
export DATABASE_URL="postgresql://user:pass@localhost/emergence"
export LOG_LEVEL="WARNING"
export OPENROUTER_API_KEY="your_key"

# Parallel processing
./training.sh --mode=morphic --generations=100 --crystal-count=8 --grid-size=18 &
./training.sh --mode=morphic --generations=100 --crystal-count=12 --grid-size=22 &
wait

# Cleanup and archive
ls -t results/simulation_*.json | tail -n +51 | xargs rm -f
```

### 10. **Memory Crystals**

#### Creating Crystals
```python
# Store a pattern in a memory crystal
crystal = MemoryCrystal.create(
    pattern=grid_pattern,
    context="stable_oscillator",
    strength=0.8
)
```

#### Using Crystals
```python
# Query crystals for similar patterns
similar_crystals = crystal_manager.find_similar(
    pattern=current_pattern,
    threshold=0.7
)
```

### 3. **Data Analysis**

#### Viewing Results
- **Web Dashboard**: Navigate to `/viewer` for interactive results
- **API Access**: Use `/api/results/` endpoints for programmatic access
- **Export Options**: JSON, CSV, and visualization formats

#### Comparison Tools
```bash
# Compare morphic vs control runs
./scripts/compare_results.py --morphic=sim_001 --control=sim_002
```

## 📊 API Reference

### Core Endpoints

#### Simulations
- `POST /api/simulations/` - Create new simulation
- `GET /api/simulations/` - List all simulations  
- `GET /api/simulations/{id}` - Get simulation details
- `DELETE /api/simulations/{id}` - Delete simulation

#### Memory Crystals
- `POST /api/crystals/` - Create memory crystal
- `GET /api/crystals/` - List crystals
- `GET /api/crystals/{id}` - Get crystal details
- `PUT /api/crystals/{id}` - Update crystal

#### Analysis
- `GET /api/analysis/compare` - Compare simulations
- `GET /api/analysis/patterns` - Pattern analysis
- `GET /api/analysis/stats` - Statistical summaries

### System Endpoints
- `GET /` - API root and status
- `GET /health` - Health check
- `GET /docs` - Interactive API documentation
- `GET /user-guide` - This user guide

## 🔬 Scientific Research

### Experimental Design
1. **Control Groups**: Run standard Game of Life simulations
2. **Test Groups**: Run simulations with morphic resonance enabled
3. **Comparison**: Analyze differences in emergent patterns
4. **Statistical Analysis**: Measure significance of observed effects

### Key Metrics
- **Pattern Stability**: How long structures persist
- **Emergence Rate**: Frequency of new pattern types
- **Complexity Measures**: Shannon entropy, fractal dimensions
- **Resonance Strength**: Correlation with stored patterns

### Research Questions
- Do memory crystals influence pattern emergence?
- Can artificial systems exhibit morphic resonance?
- How does pattern history affect future evolution?
- What are the optimal parameters for resonance detection?

## 🛠️ Development

### Project Structure
```
emergence-simulator/
├── main.py                    # FastAPI application entry
├── launcher.sh               # Environment setup script  
├── run.sh                   # Quick server start script
├── training.sh              # Simulation runner
├── test.sh                  # Test suite runner
├── requirements.txt         # Python dependencies
├── requirements-py313.txt   # Python 3.13 compatible deps
├── .env                     # Environment configuration
├── web/                     # Web interface files
│   ├── static/             # CSS, JS, images
│   └── templates/          # HTML templates  
├── simulations/            # Simulation modules
├── storage/                # Database layer
└── logs/                   # Application logs
```

### Adding Features
1. **New Simulation Types**: Extend the simulation engine
2. **Custom LLM Models**: Add new model integrations  
3. **Analysis Tools**: Create new pattern recognition algorithms
4. **Visualization**: Enhance the web dashboard

### Testing
```bash
# Run basic tests
./test.sh

# Run full test suite (when implemented)
pytest tests/ -v

# Run specific test categories
pytest tests/test_simulations.py -v
pytest tests/test_crystals.py -v
```

## 🚨 Troubleshooting

### Common Issues

#### Package Installation Failures
```bash
# Python 3.13 compatibility issues
# Use Python 3.11 or 3.12, or run:
pip install --upgrade pip setuptools wheel
```

#### Port Conflicts
```bash
# The run script automatically finds available ports
./run.sh  # Will use 8001, 8002, etc. if 8000 is busy
```

#### Database Connection Issues
```bash
# Check database URL in .env
# For SQLite (default): DATABASE_URL=sqlite:///emergence.db
# Ensure write permissions in project directory
```

#### LLM API Errors
```bash
# Verify API key in .env file
# Check internet connection
# Verify model name is correct
```

### Performance Optimization
- **Database**: Use PostgreSQL for large-scale simulations
- **Caching**: Enable Redis for faster LLM response caching
- **Parallel Processing**: Use multiple worker processes
- **Memory**: Monitor RAM usage during large simulations

## 📚 Additional Resources

### Documentation
- **API Docs**: `/docs` - Interactive API documentation
- **Code Examples**: Check the `examples/` directory
- **Research Papers**: See `docs/research/` for scientific background

### Community
- **GitHub Issues**: Report bugs and feature requests
- **Discussions**: Share research findings and use cases
- **Contributing**: Pull requests welcome for improvements

### Support
- **Logs**: Check `logs/` directory for error details
- **Debug Mode**: Set `LOG_LEVEL=DEBUG` in .env
- **Health Check**: Use `/health` endpoint to verify system status

---

## 🎯 Quick Reference

### Essential Commands
```bash
./launcher.sh              # Full setup + testing
./run.sh                   # Start server (auto-port)
source venv/bin/activate   # Manual venv activation
./test.sh                  # Basic system tests
```

### Key URLs
- **Homepage**: `http://localhost:PORT/`
- **API Docs**: `http://localhost:PORT/docs`  
- **User Guide**: `http://localhost:PORT/user-guide`
- **Viewer**: `http://localhost:PORT/viewer`

### Configuration Files
- **Environment**: `.env`
- **Dependencies**: `requirements.txt`
- **Database**: SQLite (default) or PostgreSQL

---

*Last updated: September 2024 | Version 1.0.0*
    """
    
    # Convert markdown to HTML
    html_content = markdown.markdown(
        user_guide_markdown,
        extensions=['codehilite', 'fenced_code', 'tables', 'toc']
    )
    
    # Wrap in HTML template
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Emergence Simulator - User Guide</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 1000px;
                margin: 0 auto;
                padding: 20px;
                background: #fafafa;
            }}
            .container {{
                background: white;
                padding: 40px;
                border-radius: 8px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1, h2, h3 {{ color: #2c3e50; }}
            h1 {{ border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
            h2 {{ border-bottom: 1px solid #ecf0f1; padding-bottom: 5px; margin-top: 30px; }}
            code {{
                background: #f8f9fa;
                padding: 2px 6px;
                border-radius: 3px;
                font-family: 'Monaco', 'Consolas', monospace;
            }}
            pre {{
                background: #2c3e50;
                color: #ecf0f1;
                padding: 15px;
                border-radius: 5px;
                overflow-x: auto;
            }}
            pre code {{
                background: none;
                padding: 0;
                color: #ecf0f1;
            }}
            blockquote {{
                border-left: 4px solid #3498db;
                padding-left: 15px;
                margin-left: 0;
                font-style: italic;
                color: #666;
            }}
            table {{
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
            }}
            table th, table td {{
                border: 1px solid #ddd;
                padding: 12px;
                text-align: left;
            }}
            table th {{
                background: #f8f9fa;
                font-weight: 600;
            }}
            .nav-links {{
                background: #3498db;
                color: white;
                padding: 15px;
                border-radius: 5px;
                margin-bottom: 20px;
            }}
            .nav-links a {{
                color: white;
                text-decoration: none;
                margin-right: 15px;
                padding: 5px 10px;
                border-radius: 3px;
                background: rgba(255,255,255,0.2);
            }}
            .nav-links a:hover {{
                background: rgba(255,255,255,0.3);
            }}
            ul {{ padding-left: 20px; }}
            li {{ margin-bottom: 5px; }}
        </style>
    </head>
    <body>
        <div class="nav-links">
            <strong>🧭 Navigation:</strong>
            <a href="/">🏠 Home</a>
            <a href="/docs">📚 API Docs</a>
            <a href="/viewer">👁️ Viewer</a>
            <a href="/health">🔍 Health</a>
        </div>
        <div class="container">
            {html_content}
        </div>
    </body>
    </html>
    """
    
    return full_html

# API endpoints for historical simulation data
@app.get("/api/simulations/recent")
async def get_recent_simulations():
    """Get list of recent simulation files"""
    try:
        results_dir = Path("results")
        if not results_dir.exists():
            return []

        files = []
        for file_path in results_dir.glob("simulation_*.json"):
            try:
                stat = file_path.stat()
                size_mb = stat.st_size / (1024 * 1024)
                modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

                # Determine simulation type from filename
                sim_type = "Morphic" if "morphic" in file_path.name else "Control"

                files.append({
                    "name": file_path.name,
                    "path": str(file_path),
                    "type": sim_type,
                    "size": f"{size_mb:.1f} MB",
                    "modified": modified,
                    "timestamp": stat.st_mtime
                })
            except Exception as e:
                continue

        # Sort by modification time, newest first
        files.sort(key=lambda x: x["timestamp"], reverse=True)

        # Remove timestamp from response
        for file in files:
            del file["timestamp"]

        return files[:20]  # Return last 20 files
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading simulations: {str(e)}")

@app.get("/api/simulations/batch")
async def get_batch_results():
    """Get list of batch result directories"""
    try:
        batch_dir = Path("batch_results")
        if not batch_dir.exists():
            return []

        batches = []
        for batch_path in batch_dir.iterdir():
            if batch_path.is_dir():
                try:
                    stat = batch_path.stat()
                    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

                    # Count files in batch
                    file_count = len(list(batch_path.glob("*.json")))

                    batches.append({
                        "name": batch_path.name,
                        "path": str(batch_path),
                        "files": f"{file_count} files",
                        "modified": modified,
                        "timestamp": stat.st_mtime
                    })
                except Exception:
                    continue

        # Sort by modification time, newest first
        batches.sort(key=lambda x: x["timestamp"], reverse=True)

        # Remove timestamp from response
        for batch in batches:
            del batch["timestamp"]

        return batches
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading batch results: {str(e)}")

@app.get("/api/simulations/studies")
async def get_research_studies():
    """Get list of research study directories"""
    try:
        studies = []

        # Check studies directory
        studies_dir = Path("studies")
        if studies_dir.exists():
            for study_path in studies_dir.iterdir():
                if study_path.is_dir():
                    try:
                        stat = study_path.stat()
                        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

                        # Count total files in study
                        file_count = len(list(study_path.rglob("*.json")))

                        studies.append({
                            "name": study_path.name,
                            "path": str(study_path),
                            "type": "Research Study",
                            "files": f"{file_count} files",
                            "modified": modified,
                            "timestamp": stat.st_mtime
                        })
                    except Exception:
                        continue

        # Check automated research directory
        auto_research_dir = Path("automated_research")
        if auto_research_dir.exists():
            for pipeline_path in auto_research_dir.iterdir():
                if pipeline_path.is_dir():
                    try:
                        stat = pipeline_path.stat()
                        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

                        raw_data_dir = pipeline_path / "raw_data"
                        file_count = len(list(raw_data_dir.glob("*.json"))) if raw_data_dir.exists() else 0

                        studies.append({
                            "name": pipeline_path.name,
                            "path": str(pipeline_path),
                            "type": "Automated Pipeline",
                            "files": f"{file_count} files",
                            "modified": modified,
                            "timestamp": stat.st_mtime
                        })
                    except Exception:
                        continue

        # Sort by modification time, newest first
        studies.sort(key=lambda x: x["timestamp"], reverse=True)

        # Remove timestamp from response
        for study in studies:
            del study["timestamp"]

        return studies
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading studies: {str(e)}")

@app.get("/api/simulations/load")
async def load_simulation(path: str):
    """Load and return simulation data from JSON file"""
    try:
        file_path = Path(path)

        # Security check - ensure path is within project directory
        if not file_path.is_absolute():
            file_path = Path.cwd() / file_path

        # Resolve any .. path components and check if still within project
        resolved_path = file_path.resolve()
        project_root = Path.cwd().resolve()

        if not str(resolved_path).startswith(str(project_root)):
            raise HTTPException(status_code=403, detail="Access denied: Path outside project directory")

        if not resolved_path.exists():
            raise HTTPException(status_code=404, detail="Simulation file not found")

        if not resolved_path.suffix == ".json":
            raise HTTPException(status_code=400, detail="File must be a JSON file")

        # Load and return the simulation data
        with open(resolved_path, 'r') as f:
            data = json.load(f)

        return data
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Simulation file not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading simulation: {str(e)}")

@app.post("/api/visualizations/generate")
async def generate_visualizations(request: dict):
    """Generate actual visualizations from simulation data"""
    try:
        viz_type = request.get('type', 'overview')
        refresh = request.get('refresh', False)

        charts = []

        if viz_type == 'overview':
            # Load recent simulations
            results_dir = Path("results")
            if results_dir.exists():
                sim_files = list(results_dir.glob("simulation_*.json"))[:5]  # Last 5 simulations

                if sim_files:
                    # Generate overview population chart
                    cache_key = generate_cache_key({"type": "overview", "files": [str(f) for f in sim_files]})
                    chart_filename = f"overview_{cache_key}.png"
                    chart_path = VIZ_DIR / chart_filename

                    if not chart_path.exists() or refresh:
                        fig, ax = plt.subplots(figsize=(12, 8))

                        for i, sim_file in enumerate(sim_files):
                            try:
                                data = load_simulation_data(sim_file)
                                population_data = None

                                if 'population_history' in data:
                                    population_data = data['population_history']
                                elif 'generation_data' in data:
                                    population_data = [gen.get('population', 0) for gen in data['generation_data']]

                                if population_data:
                                    generations = list(range(len(population_data)))
                                    sim_type = "Morphic" if "morphic" in sim_file.name else "Control"
                                    color = '#007bff' if sim_type == "Morphic" else '#dc3545'

                                    ax.plot(generations, population_data,
                                           label=f"{sim_type} - {sim_file.stem[-8:]}",
                                           alpha=0.7, linewidth=2, color=color)
                            except Exception:
                                continue

                        ax.set_xlabel('Generation')
                        ax.set_ylabel('Population')
                        ax.set_title('Population Trends - Recent Simulations')
                        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                        ax.grid(True, alpha=0.3)
                        plt.tight_layout()

                        chart_url = save_chart(fig, chart_filename)
                    else:
                        chart_url = f"/static/{chart_filename}"

                    charts.append({
                        "title": "Population Trends Overview",
                        "url": chart_url
                    })

        return {
            "charts": charts,
            "generated": len(charts),
            "message": f"Generated {len(charts)} visualization(s)"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating visualizations: {str(e)}")

@app.post("/api/visualizations/single")
async def generate_single_visualization(request: dict):
    """Generate visualization for a single simulation"""
    try:
        path = request.get('path')
        viz_types = request.get('types', ['population'])  # Default to population

        if not path:
            raise HTTPException(status_code=400, detail="Path required")

        data = load_simulation_data(path)
        sim_name = Path(path).stem

        charts = []

        for viz_type in viz_types:
            # Generate cache key
            cache_key = generate_cache_key({"path": path, "type": viz_type})
            chart_filename = f"{viz_type}_{cache_key}.png"
            chart_path = VIZ_DIR / chart_filename

            if not chart_path.exists():
                fig = None
                title = f"{viz_type.title()}: {sim_name}"

                if viz_type == 'population':
                    fig = create_population_chart(data, title)
                elif viz_type == 'heatmap':
                    fig = create_morphic_heatmap(data)
                    title = f"Morphic Heatmap: {sim_name}"
                elif viz_type == 'pattern':
                    fig = create_pattern_analysis(data)
                    title = f"Pattern Analysis: {sim_name}"
                elif viz_type == 'crystal':
                    fig = create_crystal_usage(data)
                    title = f"Crystal Usage: {sim_name}"

                if fig:
                    chart_url = save_chart(fig, chart_filename)
                    charts.append({
                        "type": viz_type,
                        "title": title,
                        "url": chart_url,
                        "cached": False
                    })
                else:
                    charts.append({
                        "type": viz_type,
                        "title": title,
                        "error": f"No data available for {viz_type} visualization",
                        "cached": False
                    })
            else:
                chart_url = f"/static/{chart_filename}"
                charts.append({
                    "type": viz_type,
                    "title": f"{viz_type.title()}: {sim_name}",
                    "url": chart_url,
                    "cached": True
                })

        return {
            "charts": charts,
            "generated": len(charts)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating visualization: {str(e)}")

@app.post("/api/visualizations/animation")
async def generate_animation(request: dict):
    """Generate animation for a single simulation"""
    try:
        path = request.get('path')
        if not path:
            raise HTTPException(status_code=400, detail="Path required")

        data = load_simulation_data(path)
        sim_name = Path(path).stem

        # Generate cache key
        cache_key = generate_cache_key({"path": path, "type": "animation"})
        chart_filename = f"animation_{cache_key}.png"
        chart_path = VIZ_DIR / chart_filename

        if not chart_path.exists():
            fig = create_animation_frames(data)
            if fig:
                chart_url = save_chart(fig, chart_filename)
            else:
                raise HTTPException(status_code=400, detail="No generation data available for animation")
        else:
            chart_url = f"/static/{chart_filename}"

        return {
            "title": f"Animation Frames: {sim_name}",
            "url": chart_url,
            "cached": chart_path.exists(),
            "type": "animation"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating animation: {str(e)}")

@app.get("/api/visualizations/cached")
async def get_cached_visualizations():
    """Get list of cached visualization files"""
    try:
        if not VIZ_DIR.exists():
            return {"files": []}

        files = []
        for file_path in VIZ_DIR.glob("*.png"):
            try:
                stat = file_path.stat()
                size_mb = stat.st_size / (1024 * 1024)
                modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

                # Determine visualization type from filename
                viz_type = "Overview"
                if file_path.name.startswith("single_"):
                    viz_type = "Single Chart"
                elif file_path.name.startswith("animation_"):
                    viz_type = "Animation"
                elif file_path.name.startswith("heatmap_"):
                    viz_type = "Heatmap"
                elif file_path.name.startswith("pattern_"):
                    viz_type = "Pattern Analysis"
                elif file_path.name.startswith("crystal_"):
                    viz_type = "Crystal Usage"

                files.append({
                    "name": file_path.name,
                    "url": f"/static/{file_path.name}",
                    "type": viz_type,
                    "size": f"{size_mb:.2f} MB",
                    "modified": modified,
                    "timestamp": stat.st_mtime
                })
            except Exception:
                continue

        # Sort by modification time, newest first
        files.sort(key=lambda x: x["timestamp"], reverse=True)

        # Remove timestamp from response
        for file in files:
            del file["timestamp"]

        return {"files": files[:20]}  # Return last 20 files

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading cached visualizations: {str(e)}")

@app.post("/api/visualizations/batch")
async def visualize_batch(request: dict):
    """Generate visualizations for batch results"""
    try:
        batch_path = request.get('batch_path')
        if not batch_path:
            raise HTTPException(status_code=400, detail="Batch path required")

        batch_dir = Path(batch_path)
        if not batch_dir.exists():
            raise HTTPException(status_code=404, detail="Batch directory not found")

        # Find JSON files in batch directory
        json_files = list(batch_dir.glob("*.json"))
        if not json_files:
            return {"charts": [], "files_processed": 0, "message": "No JSON files found in batch"}

        # Generate cache key for batch
        cache_key = generate_cache_key({"batch_path": str(batch_path), "files": len(json_files)})
        chart_filename = f"batch_{cache_key}.png"
        chart_path = VIZ_DIR / chart_filename

        charts = []

        if not chart_path.exists():
            # Load all batch data
            morphic_data = []
            control_data = []

            for json_file in json_files:
                try:
                    data = load_simulation_data(json_file)
                    if 'morphic' in json_file.name.lower():
                        morphic_data.append(data)
                    else:
                        control_data.append(data)
                except Exception:
                    continue

            if morphic_data or control_data:
                # Create batch comparison chart
                fig, axes = plt.subplots(2, 2, figsize=(15, 10))

                # Population comparison
                ax = axes[0, 0]
                for i, data in enumerate(morphic_data[:5]):  # Limit to 5 for visibility
                    if 'population_history' in data:
                        population_data = data['population_history']
                    elif 'generation_data' in data:
                        population_data = [gen.get('population', 0) for gen in data['generation_data']]
                    else:
                        continue

                    generations = list(range(len(population_data)))
                    ax.plot(generations, population_data, label=f'Morphic {i+1}', alpha=0.7, color='blue')

                for i, data in enumerate(control_data[:5]):  # Limit to 5 for visibility
                    if 'population_history' in data:
                        population_data = data['population_history']
                    elif 'generation_data' in data:
                        population_data = [gen.get('population', 0) for gen in data['generation_data']]
                    else:
                        continue

                    generations = list(range(len(population_data)))
                    ax.plot(generations, population_data, label=f'Control {i+1}', alpha=0.7, color='red')

                ax.set_title('Batch Population Comparison')
                ax.set_xlabel('Generation')
                ax.set_ylabel('Population')
                ax.legend()
                ax.grid(True, alpha=0.3)

                # Average populations
                ax = axes[0, 1]
                morphic_avgs = [data.get('avg_population', 0) for data in morphic_data]
                control_avgs = [data.get('avg_population', 0) for data in control_data]

                if morphic_avgs:
                    ax.bar(['Morphic', 'Control'], [np.mean(morphic_avgs), np.mean(control_avgs)],
                           color=['blue', 'red'], alpha=0.7)
                    ax.set_title('Average Population Comparison')
                    ax.set_ylabel('Average Population')

                # Morphic influence rates
                ax = axes[1, 0]
                morphic_rates = []
                for data in morphic_data:
                    if 'morphic_influences' in data and 'generations' in data and 'grid_size' in data:
                        total_decisions = data['generations'] * data['grid_size'] * data['grid_size']
                        if total_decisions > 0:
                            rate = (len(data['morphic_influences']) / total_decisions) * 100
                            morphic_rates.append(rate)

                if morphic_rates:
                    ax.hist(morphic_rates, bins=10, alpha=0.7, color='purple')
                    ax.set_title('Morphic Influence Rate Distribution')
                    ax.set_xlabel('Influence Rate (%)')
                    ax.set_ylabel('Frequency')

                # Summary statistics
                ax = axes[1, 1]
                stats_data = {
                    'Morphic Runs': len(morphic_data),
                    'Control Runs': len(control_data),
                    'Avg Morphic Pop': np.mean(morphic_avgs) if morphic_avgs else 0,
                    'Avg Control Pop': np.mean(control_avgs) if control_avgs else 0
                }

                y_pos = range(len(stats_data))
                ax.barh(y_pos, list(stats_data.values()), alpha=0.7, color='green')
                ax.set_yticks(y_pos)
                ax.set_yticklabels(list(stats_data.keys()))
                ax.set_title('Batch Summary Statistics')

                plt.suptitle(f'Batch Analysis: {batch_dir.name}')
                plt.tight_layout()

                chart_url = save_chart(fig, chart_filename)
            else:
                raise HTTPException(status_code=400, detail="No valid simulation data found in batch")
        else:
            chart_url = f"/static/{chart_filename}"

        charts.append({
            "title": f"Batch Analysis: {batch_dir.name}",
            "url": chart_url,
            "cached": chart_path.exists()
        })

        return {
            "charts": charts,
            "files_processed": len(json_files),
            "morphic_files": len([f for f in json_files if 'morphic' in f.name.lower()]),
            "control_files": len([f for f in json_files if 'morphic' not in f.name.lower()])
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error visualizing batch: {str(e)}")

if __name__ == "__main__":
    print("🌟 Starting Emergence Simulator...")
    print("🌐 Web interface: http://localhost:8000")
    print("📚 API docs: http://localhost:8000/docs")
    print("🔍 Viewer: http://localhost:8000/viewer")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )