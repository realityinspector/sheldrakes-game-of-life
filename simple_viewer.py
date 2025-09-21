#!/usr/bin/env python3
"""
Simple Historical Viewer Test - Simplified version for testing
"""

import uvicorn
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json
import os
from datetime import datetime
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import numpy as np
import seaborn as sns
from typing import List, Optional
import hashlib
import base64

# Create FastAPI app
app = FastAPI(title="Emergence Simulator - Historical Viewer")

# Setup directories
CACHE_DIR = Path("web_cache")
VIZ_DIR = CACHE_DIR / "visualizations"
STATIC_DIR = CACHE_DIR / "static"

# Create directories if they don't exist
CACHE_DIR.mkdir(exist_ok=True)
VIZ_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)

# Mount static files - point directly to visualization directory
app.mount("/static", StaticFiles(directory=str(VIZ_DIR)), name="static")

# Configure matplotlib style
plt.style.use('seaborn-v0_8' if 'seaborn-v0_8' in plt.style.available else 'default')
sns.set_palette("husl")

@app.get("/")
async def root():
    return {"message": "Historical Viewer API", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

@app.get("/viewer", response_class=HTMLResponse)
async def viewer():
    """Simplified historical viewer"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Historical Simulation Viewer</title>
        <style>
            body { font-family: system-ui, sans-serif; margin: 20px; background: #f8f9fa; }
            .container { max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }
            .file-list { max-height: 400px; overflow-y: auto; border: 1px solid #ddd; padding: 10px; }
            .file-item { padding: 10px; margin: 5px 0; background: #f8f9fa; border-radius: 4px; cursor: pointer; }
            .file-item:hover { background: #e3f2fd; }
            .btn { background: #007bff; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; margin: 5px; }
            .metrics-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }
            .metric-card { background: #f8f9fa; padding: 15px; border-radius: 6px; border-left: 4px solid #007bff; }
            .metric-label { font-size: 12px; color: #666; text-transform: uppercase; }
            .metric-value { font-size: 24px; font-weight: bold; color: #333; }
            .loading { text-align: center; padding: 40px; color: #666; }
            .error { color: #dc3545; background: #f8d7da; padding: 10px; border-radius: 4px; margin: 10px 0; }
            #details { display: none; margin-top: 20px; padding: 20px; border: 1px solid #ddd; border-radius: 8px; }
            .selected { background: #e3f2fd !important; border: 2px solid #007bff !important; }
            .compare-panel { background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 10px 0; }
            .tabs { display: flex; border-bottom: 2px solid #ddd; margin-bottom: 20px; }
            .tab { padding: 10px 20px; cursor: pointer; border: none; background: none; border-bottom: 3px solid transparent; }
            .tab.active { border-bottom-color: #007bff; color: #007bff; font-weight: bold; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }
            .viz-container { margin: 20px 0; text-align: center; }
            .viz-container img { max-width: 100%; border: 1px solid #ddd; border-radius: 8px; }
            .animation-controls { margin: 10px 0; }
            .animation-controls button { margin: 0 5px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🌟 Enhanced Historical Simulation Viewer</h1>

            <div class="tabs">
                <button class="tab active" onclick="showTab('browse')">📁 Browse</button>
                <button class="tab" onclick="showTab('compare')">⚖️ Compare</button>
                <button class="tab" onclick="showTab('visualize')">📊 Visualize</button>
                <button class="tab" onclick="showTab('animate')">🎬 Animate</button>
            </div>

            <div id="browse" class="tab-content active">
                <h2>📈 Recent Simulations</h2>
                <button class="btn" onclick="loadRecentSimulations()">🔄 Refresh</button>
                <button class="btn" onclick="clearSelection()">Clear Selection</button>
                <div class="compare-panel">
                    <strong>Selected for comparison:</strong> <span id="selected-count">0</span> simulations
                    <button class="btn" onclick="compareSelected()" style="margin-left: 10px;">Compare Selected</button>
                </div>
                <div id="recent-files" class="file-list">
                    <div class="loading">Loading recent simulations...</div>
                </div>

                <div id="details">
                    <h3>Simulation Details</h3>
                    <div id="details-content"></div>
                </div>
            </div>

            <div id="compare" class="tab-content">
                <h2>⚖️ Simulation Comparison</h2>
                <div id="comparison-content">
                    <p>Select simulations in the Browse tab, then switch here to compare them.</p>
                </div>
            </div>

            <div id="visualize" class="tab-content">
                <h2>📊 Visualizations</h2>
                <button class="btn" onclick="generateVisualization()">🎨 Generate Charts</button>
                <button class="btn" onclick="refreshVisualization()">🔄 Refresh</button>
                <div id="visualization-content">
                    <p>Click "Generate Charts" to create visualizations from your simulation data.</p>
                </div>
            </div>

            <div id="animate" class="tab-content">
                <h2>🎬 Pattern Animation</h2>
                <button class="btn" onclick="generateAnimation()">🎯 Animate Selected</button>
                <div class="animation-controls">
                    <button class="btn" onclick="playAnimation()">▶️ Play</button>
                    <button class="btn" onclick="pauseAnimation()">⏸️ Pause</button>
                    <button class="btn" onclick="resetAnimation()">⏹️ Reset</button>
                </div>
                <div id="animation-content">
                    <p>Select a simulation in the Browse tab, then generate animations here.</p>
                </div>
            </div>
        </div>

        <script>
            let selectedSimulations = [];
            let currentSimulationData = null;

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

            function toggleSelection(path, element) {
                const index = selectedSimulations.indexOf(path);
                if (index > -1) {
                    selectedSimulations.splice(index, 1);
                    element.classList.remove('selected');
                } else {
                    selectedSimulations.push(path);
                    element.classList.add('selected');
                }
                updateSelectionCount();
            }

            function updateSelectionCount() {
                document.getElementById('selected-count').textContent = selectedSimulations.length;
            }

            function clearSelection() {
                selectedSimulations = [];
                document.querySelectorAll('.file-item').forEach(item => {
                    item.classList.remove('selected');
                });
                updateSelectionCount();
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
                        <div class="file-item" onclick="toggleSelection('${file.path}', this)"
                             ondblclick="loadSimulation('${file.path}')">
                            <strong>${file.name}</strong><br>
                            <small>${file.type} • ${file.size} • ${file.modified}</small>
                            <div style="margin-top: 5px;">
                                <button class="btn" onclick="event.stopPropagation(); loadSimulation('${file.path}')" style="font-size: 12px; padding: 4px 8px;">View</button>
                                <button class="btn" onclick="event.stopPropagation(); generateSingleVisualization('${file.path}')" style="font-size: 12px; padding: 4px 8px;">📊 Chart</button>
                            </div>
                        </div>
                    `).join('');
                } catch (error) {
                    container.innerHTML = '<div class="error">Error loading simulations: ' + error.message + '</div>';
                }
            }

            async function loadSimulation(path) {
                const detailsDiv = document.getElementById('details');
                const contentDiv = document.getElementById('details-content');

                detailsDiv.style.display = 'block';
                contentDiv.innerHTML = '<div class="loading">Loading simulation details...</div>';

                try {
                    const response = await fetch(`/api/simulations/load?path=${encodeURIComponent(path)}`);
                    const data = await response.json();
                    currentSimulationData = data;

                    const metrics = [
                        { label: 'Final Population', value: data.final_population },
                        { label: 'Average Population', value: data.avg_population?.toFixed(1) },
                        { label: 'Max Population', value: data.max_population },
                        { label: 'Stability Score', value: data.stability_score?.toFixed(3) },
                        { label: 'Complexity Score', value: data.complexity_score?.toFixed(3) },
                        { label: 'Emergence Events', value: data.emergence_events || 0 },
                        { label: 'Morphic Influences', value: data.morphic_influences?.length || 'N/A' }
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

            async function compareSelected() {
                if (selectedSimulations.length < 2) {
                    alert('Please select at least 2 simulations to compare.');
                    return;
                }

                const content = document.getElementById('comparison-content');
                content.innerHTML = '<div class="loading">Loading comparison...</div>';

                try {
                    const response = await fetch('/api/simulations/compare', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ paths: selectedSimulations })
                    });
                    const comparison = await response.json();

                    content.innerHTML = `
                        <h3>📊 Comparison Results</h3>
                        <div class="metrics-grid">
                            ${Object.entries(comparison.metrics).map(([metric, values]) => `
                                <div class="metric-card">
                                    <div class="metric-label">${metric}</div>
                                    <div class="metric-value">
                                        ${values.map((val, idx) => `<div>Sim ${idx + 1}: ${val}</div>`).join('')}
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                        ${comparison.visualization_url ? `
                            <div class="viz-container">
                                <img src="${comparison.visualization_url}" alt="Comparison Chart">
                            </div>
                        ` : ''}
                    `;

                    showTab('compare');
                } catch (error) {
                    content.innerHTML = '<div class="error">Error comparing simulations: ' + error.message + '</div>';
                }
            }

            async function generateVisualization() {
                const content = document.getElementById('visualization-content');
                content.innerHTML = '<div class="loading">Generating visualizations...</div>';

                try {
                    const response = await fetch('/api/visualizations/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ type: 'overview', refresh: true })
                    });
                    const result = await response.json();

                    content.innerHTML = `
                        <div class="viz-container">
                            ${result.charts.map(chart => `
                                <div>
                                    <h4>${chart.title}</h4>
                                    <img src="${chart.url}" alt="${chart.title}">
                                </div>
                            `).join('')}
                        </div>
                    `;
                } catch (error) {
                    content.innerHTML = '<div class="error">Error generating visualizations: ' + error.message + '</div>';
                }
            }

            async function generateSingleVisualization(path) {
                try {
                    const response = await fetch('/api/visualizations/single', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ path: path })
                    });
                    const result = await response.json();

                    // Show in visualization tab
                    document.getElementById('visualization-content').innerHTML = `
                        <div class="viz-container">
                            <h4>${result.title}</h4>
                            <img src="${result.url}" alt="${result.title}">
                        </div>
                    `;
                    showTab('visualize');
                } catch (error) {
                    alert('Error generating visualization: ' + error.message);
                }
            }

            async function generateAnimation() {
                if (!currentSimulationData) {
                    alert('Please select and load a simulation first.');
                    return;
                }

                const content = document.getElementById('animation-content');
                content.innerHTML = '<div class="loading">Generating animation...</div>';

                try {
                    const response = await fetch('/api/animations/generate', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ path: currentSimulationData.path || selectedSimulations[0] })
                    });
                    const result = await response.json();

                    content.innerHTML = `
                        <div class="viz-container">
                            <h4>${result.title}</h4>
                            <video controls style="max-width: 100%;">
                                <source src="${result.url}" type="video/mp4">
                                Your browser does not support the video tag.
                            </video>
                        </div>
                    `;
                } catch (error) {
                    content.innerHTML = '<div class="error">Error generating animation: ' + error.message + '</div>';
                }
            }

            function refreshVisualization() {
                generateVisualization();
            }

            function playAnimation() { /* Animation controls - to be implemented */ }
            function pauseAnimation() { /* Animation controls - to be implemented */ }
            function resetAnimation() { /* Animation controls - to be implemented */ }

            // Load simulations on page load
            document.addEventListener('DOMContentLoaded', function() {
                loadRecentSimulations();
            });
        </script>
    </body>
    </html>
    """
    return html_content

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

# Utility functions for visualization
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

    ax.plot(generations, populations, linewidth=2, marker='o', markersize=4)
    ax.set_xlabel('Generation')
    ax.set_ylabel('Population')
    ax.set_title(title)
    ax.grid(True, alpha=0.3)

    # Add morphic influence overlay if available
    if 'morphic_influences' in data:
        influence_gen = [inf.get('generation', 0) for inf in data['morphic_influences']]
        influence_counts = {}
        for gen in influence_gen:
            influence_counts[gen] = influence_counts.get(gen, 0) + 1

        if influence_counts:
            ax2 = ax.twinx()
            gens = list(influence_counts.keys())
            counts = list(influence_counts.values())
            ax2.scatter(gens, counts, c='red', alpha=0.6, s=20, label='Morphic Influences')
            ax2.set_ylabel('Morphic Influences', color='red')
            ax2.legend()

    plt.tight_layout()
    return fig

def create_comparison_chart(data_list, titles):
    """Create comparison chart for multiple simulations"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))

    # Population comparison
    ax = axes[0, 0]
    for i, (data, title) in enumerate(zip(data_list, titles)):
        population_data = None
        if 'population_history' in data:
            population_data = data['population_history']
        elif 'generation_data' in data:
            population_data = [gen.get('population', 0) for gen in data['generation_data']]

        if population_data:
            generations = list(range(len(population_data)))
            ax.plot(generations, population_data, label=title, linewidth=2)
    ax.set_xlabel('Generation')
    ax.set_ylabel('Population')
    ax.set_title('Population Comparison')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Morphic influence comparison
    ax = axes[0, 1]
    morphic_rates = []
    labels = []
    for data, title in zip(data_list, titles):
        if 'morphic_influences' in data and 'generations' in data and 'grid_size' in data:
            total_decisions = data['generations'] * data['grid_size'] * data['grid_size']
            rate = (len(data['morphic_influences']) / total_decisions) * 100
            morphic_rates.append(rate)
            labels.append(title[:20])  # Truncate long titles

    if morphic_rates:
        bars = ax.bar(labels, morphic_rates, alpha=0.7)
        ax.set_ylabel('Morphic Influence Rate (%)')
        ax.set_title('Morphic Influence Comparison')
        ax.tick_params(axis='x', rotation=45)

        # Add value labels on bars
        for bar, rate in zip(bars, morphic_rates):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{rate:.1f}%', ha='center', va='bottom')

    # Metrics comparison
    ax = axes[1, 0]
    metrics = ['avg_population', 'final_population', 'stability_score', 'complexity_score']
    x = np.arange(len(metrics))
    width = 0.8 / len(data_list)

    for i, (data, title) in enumerate(zip(data_list, titles)):
        values = [data.get(metric, 0) for metric in metrics]
        ax.bar(x + i * width, values, width, label=title, alpha=0.7)

    ax.set_xlabel('Metrics')
    ax.set_ylabel('Values')
    ax.set_title('Key Metrics Comparison')
    ax.set_xticks(x + width * (len(data_list) - 1) / 2)
    ax.set_xticklabels(['Avg Pop', 'Final Pop', 'Stability', 'Complexity'])
    ax.legend()

    # Crystal patterns analysis
    ax = axes[1, 1]
    if all('crystals' in data for data in data_list):
        pattern_counts = []
        for data, title in zip(data_list, titles):
            total_patterns = sum(len(crystal.get('patterns', [])) for crystal in data['crystals'])
            pattern_counts.append(total_patterns)

        bars = ax.bar(labels, pattern_counts, alpha=0.7, color='purple')
        ax.set_ylabel('Total Patterns Stored')
        ax.set_title('Memory Crystal Usage')
        ax.tick_params(axis='x', rotation=45)

        for bar, count in zip(bars, pattern_counts):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{count}', ha='center', va='bottom')

    plt.tight_layout()
    return fig

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

    fig, ax = plt.subplots(figsize=(10, 8))
    im = ax.imshow(influence_grid, cmap='YlOrRd', interpolation='nearest')
    ax.set_title('Morphic Influence Heatmap')
    ax.set_xlabel('X Position')
    ax.set_ylabel('Y Position')

    # Add colorbar
    cbar = plt.colorbar(im, ax=ax)
    cbar.set_label('Influence Count')

    return fig

# API endpoints for comparison and visualization
@app.post("/api/simulations/compare")
async def compare_simulations(request: dict):
    """Compare multiple simulations"""
    try:
        paths = request.get('paths', [])
        if len(paths) < 2:
            raise HTTPException(status_code=400, detail="At least 2 simulations required for comparison")

        # Load simulation data
        data_list = []
        titles = []
        for path in paths:
            data = load_simulation_data(path)
            data_list.append(data)
            titles.append(Path(path).stem)

        # Generate cache key
        cache_key = generate_cache_key({"type": "comparison", "paths": paths})
        viz_path = VIZ_DIR / f"comparison_{cache_key}.png"

        # Generate visualization if not cached
        if not viz_path.exists():
            fig = create_comparison_chart(data_list, titles)
            fig.savefig(viz_path, dpi=150, bbox_inches='tight')
            plt.close(fig)

        # Extract metrics for comparison
        metrics = {}
        metric_names = ['avg_population', 'final_population', 'stability_score', 'complexity_score']

        for metric in metric_names:
            metrics[metric] = [data.get(metric, 0) for data in data_list]

        # Add morphic influence rates
        morphic_rates = []
        for data in data_list:
            if 'morphic_influences' in data and 'generations' in data and 'grid_size' in data:
                total_decisions = data['generations'] * data['grid_size'] * data['grid_size']
                rate = (len(data['morphic_influences']) / total_decisions) * 100
                morphic_rates.append(f"{rate:.1f}%")
            else:
                morphic_rates.append("N/A")

        metrics['morphic_influence_rate'] = morphic_rates

        return {
            "metrics": metrics,
            "visualization_url": f"/static/{viz_path.name}",
            "simulation_count": len(data_list)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing simulations: {str(e)}")

@app.post("/api/visualizations/generate")
async def generate_overview_visualizations(request: dict):
    """Generate overview visualizations from all available data"""
    try:
        refresh = request.get('refresh', False)
        viz_type = request.get('type', 'overview')

        # Generate cache key
        cache_key = generate_cache_key({"type": viz_type, "timestamp": datetime.now().date().isoformat()})

        charts = []

        # Load recent simulations
        results_dir = Path("results")
        if results_dir.exists():
            sim_files = list(results_dir.glob("simulation_*.json"))[:10]  # Last 10 simulations

            if sim_files:
                # Population trends chart
                pop_chart_path = VIZ_DIR / f"population_trends_{cache_key}.png"
                if not pop_chart_path.exists() or refresh:
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
                                label = f"{sim_file.stem[-8:]}" # Last 8 chars (timestamp)
                                ax.plot(generations, population_data,
                                       label=label, alpha=0.7, linewidth=1)
                        except Exception:
                            continue

                    ax.set_xlabel('Generation')
                    ax.set_ylabel('Population')
                    ax.set_title('Population Trends - Recent Simulations')
                    ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
                    ax.grid(True, alpha=0.3)
                    plt.tight_layout()
                    fig.savefig(pop_chart_path, dpi=150, bbox_inches='tight')
                    plt.close(fig)

                charts.append({
                    "title": "Population Trends",
                    "url": f"/static/{pop_chart_path.name}"
                })

                # Morphic influence distribution
                influence_chart_path = VIZ_DIR / f"morphic_distribution_{cache_key}.png"
                if not influence_chart_path.exists() or refresh:
                    morphic_data = []
                    control_data = []

                    for sim_file in sim_files:
                        try:
                            data = load_simulation_data(sim_file)
                            if 'morphic_influences' in data and 'generations' in data and 'grid_size' in data:
                                total_decisions = data['generations'] * data['grid_size'] * data['grid_size']
                                rate = (len(data['morphic_influences']) / total_decisions) * 100

                                if 'morphic' in sim_file.name:
                                    morphic_data.append(rate)
                                else:
                                    control_data.append(rate)
                        except Exception:
                            continue

                    if morphic_data:
                        fig, ax = plt.subplots(figsize=(10, 6))

                        ax.hist(morphic_data, bins=10, alpha=0.7, label='Morphic Simulations', color='blue')
                        if control_data:
                            ax.hist(control_data, bins=10, alpha=0.7, label='Control Simulations', color='red')

                        ax.set_xlabel('Morphic Influence Rate (%)')
                        ax.set_ylabel('Frequency')
                        ax.set_title('Distribution of Morphic Influence Rates')
                        ax.legend()
                        ax.grid(True, alpha=0.3)
                        plt.tight_layout()
                        fig.savefig(influence_chart_path, dpi=150, bbox_inches='tight')
                        plt.close(fig)

                        charts.append({
                            "title": "Morphic Influence Distribution",
                            "url": f"/static/{influence_chart_path.name}"
                        })

        return {"charts": charts}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating visualizations: {str(e)}")

@app.post("/api/visualizations/single")
async def generate_single_visualization(request: dict):
    """Generate visualization for a single simulation"""
    try:
        path = request.get('path')
        if not path:
            raise HTTPException(status_code=400, detail="Path required")

        data = load_simulation_data(path)
        sim_name = Path(path).stem

        # Generate cache key
        cache_key = generate_cache_key({"path": path, "type": "single"})
        viz_path = VIZ_DIR / f"single_{cache_key}.png"

        if not viz_path.exists():
            fig = create_population_chart(data, f"Population: {sim_name}")
            if fig:
                fig.savefig(viz_path, dpi=150, bbox_inches='tight')
                plt.close(fig)
            else:
                raise HTTPException(status_code=400, detail="No population data available for visualization")

        return {
            "title": f"Population Chart: {sim_name}",
            "url": f"/static/{viz_path.name}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating single visualization: {str(e)}")

@app.post("/api/animations/generate")
async def generate_animation(request: dict):
    """Generate animation for simulation data"""
    try:
        path = request.get('path')
        if not path:
            raise HTTPException(status_code=400, detail="Path required")

        data = load_simulation_data(path)
        sim_name = Path(path).stem

        # For now, return a placeholder - animation generation is complex
        # In a full implementation, this would create an MP4 animation
        return {
            "title": f"Animation: {sim_name}",
            "url": "/static/placeholder_animation.mp4",
            "message": "Animation generation is a placeholder - would create MP4 showing grid evolution"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating animation: {str(e)}")

if __name__ == "__main__":
    print("🌟 Starting Simple Historical Viewer...")
    print("🌐 Web interface: http://localhost:8005")
    print("🔍 Viewer: http://localhost:8005/viewer")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8005,
        log_level="info"
    )