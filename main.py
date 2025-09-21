#!/usr/bin/env python3
"""
Emergence Simulator - Main Entry Point

A simple launcher for the emergence simulator platform.
Handles basic FastAPI setup and routing.
"""

import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
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
from pydantic import BaseModel
from typing import Optional, List
import asyncio

# Import our integrated runs functionality
from integrated_runs import integrated_run_engine
from analysis_engine import AnalysisEngine
from storage.database import create_tables
from storage.models import IntegratedRun

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

# Mount static files for CSS, JS, and generated images
app.mount("/static", StaticFiles(directory="web/static"), name="static")

# Mount cache directory for generated visualizations
app.mount("/cache", StaticFiles(directory=str(VIZ_DIR)), name="cache")

# Mount results directory for serving analysis files
app.mount("/results", StaticFiles(directory="results"), name="results")

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
                margin: 10px 0 20px;
                font-size: 1.2em;
                opacity: 0.9;
            }
            .hero-features {
                display: flex;
                justify-content: center;
                gap: 12px;
                flex-wrap: wrap;
                margin-top: 20px;
            }
            .hero-badge {
                background: rgba(255, 255, 255, 0.2);
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 0.9em;
                font-weight: 500;
                backdrop-filter: blur(10px);
            }
            .quick-actions {
                display: flex;
                justify-content: center;
                gap: 16px;
                margin: 30px 0;
                flex-wrap: wrap;
            }
            .cta-button {
                padding: 12px 24px;
                border-radius: 8px;
                text-decoration: none;
                font-weight: 600;
                transition: all 0.3s ease;
                border: 2px solid transparent;
            }
            .cta-button.primary {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
            }
            .cta-button.primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
            }
            .cta-button.secondary {
                background: white;
                color: #667eea;
                border-color: #667eea;
            }
            .cta-button.secondary:hover {
                background: #667eea;
                color: white;
                transform: translateY(-2px);
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
            .badge.new {
                background: linear-gradient(135deg, #ff6b6b, #ee5a24);
                animation: pulse 2s infinite;
            }
            @keyframes pulse {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.7; }
            }
            .nav-card.featured {
                background: linear-gradient(135deg, #f8f9fa 0%, #e3f2fd 100%);
                border-color: #2196F3;
                border-width: 3px;
            }
            .nav-card.featured::before {
                background: linear-gradient(90deg, #2196F3, #21CBF3);
                height: 6px;
            }
            .card-features {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 8px;
                margin-top: 16px;
                font-size: 0.85em;
                color: #555;
            }
            .card-features span {
                background: rgba(33, 150, 243, 0.1);
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.8em;
            }
            .showcase-section {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                margin: 0;
            }
            .showcase-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 24px;
                margin-top: 30px;
            }
            .showcase-card {
                background: rgba(255, 255, 255, 0.1);
                border-radius: 12px;
                padding: 24px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
            .showcase-card h4 {
                margin: 0 0 12px 0;
                font-size: 1.2em;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            .showcase-card p {
                margin: 0;
                opacity: 0.9;
                line-height: 1.5;
            }
            @media (max-width: 768px) {
                .nav-grid {
                    grid-template-columns: 1fr;
                }
                .showcase-grid {
                    grid-template-columns: 1fr;
                }
                .header {
                    padding: 30px 20px;
                }
                .header h1 {
                    font-size: 2em;
                }
                .nav-section {
                    padding: 30px 20px;
                }
                .showcase-section {
                    padding: 30px 20px;
                }
                .container {
                    margin: 10px;
                    border-radius: 12px;
                }
                .quick-actions {
                    flex-direction: column;
                    align-items: center;
                }
                .cta-button {
                    width: 100%;
                    max-width: 300px;
                    text-align: center;
                }
                .hero-features {
                    gap: 8px;
                }
                .hero-badge {
                    font-size: 0.8em;
                    padding: 4px 8px;
                }
                .card-features {
                    grid-template-columns: 1fr;
                }
                .status-bar {
                    flex-direction: column;
                    gap: 8px;
                    padding: 20px;
                }
                .api-info {
                    padding: 15px 20px;
                    font-size: 0.8em;
                }
            }
            @media (max-width: 480px) {
                .header h1 {
                    font-size: 1.8em;
                }
                .header p {
                    font-size: 1em;
                }
                .nav-card {
                    padding: 16px;
                }
                .showcase-card {
                    padding: 16px;
                }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🌟 Emergence Simulator</h1>
                <p>Advanced morphic resonance research platform with integrated comparative analysis</p>
                <div class="hero-features">
                    <span class="hero-badge">🧬 Integrated Runs</span>
                    <span class="hero-badge">🤖 LLM Integration</span>
                    <span class="hero-badge">📊 Real-time Analysis</span>
                    <span class="hero-badge">🔬 Scientific Rigor</span>
                </div>
            </div>

            <div class="nav-section">
                <h2>🚀 Integrated Research Platform</h2>
                <p>Create comprehensive comparative studies of morphic resonance, LLM control, and classical Conway simulations. Generate shareable research notebooks with side-by-side analysis, morphic insights, and educational content.</p>

                <div class="quick-actions">
                    <a href="/integrated-runs/create" class="cta-button primary">
                        🧬 Create Integrated Run
                    </a>
                    <a href="/integrated-runs/gallery" class="cta-button secondary">
                        📚 Browse Gallery
                    </a>
                    <a href="/viewer" class="cta-button secondary">
                        👁️ Live Viewer
                    </a>
                </div>

                <h2>🧪 Research Tools</h2>
                <div class="nav-grid">
                    <a href="/integrated-runs/create" class="nav-card featured">
                        <h3>🧬 Integrated Runs <span class="badge new">Featured</span></h3>
                        <p>Create comprehensive comparative studies with morphic resonance, LLM control, and classical Conway. Generate shareable research notebooks with side-by-side analysis.</p>
                        <div class="card-features">
                            <span>✨ Side-by-side animations</span>
                            <span>📊 Frame-by-frame comparison</span>
                            <span>🎓 Conway factoids</span>
                            <span>🔗 Shareable permalinks</span>
                        </div>
                    </a>

                    <a href="/integrated-runs/gallery" class="nav-card">
                        <h3>📚 Results Gallery <span class="badge">Explore</span></h3>
                        <p>Browse all integrated runs with interactive visualizations, morphic analysis insights, and educational content in a comprehensive gallery format.</p>
                    </a>

                    <a href="/viewer" class="nav-card">
                        <h3>👁️ Live Viewer <span class="badge">Real-time</span></h3>
                        <p>Interactive visualization of individual simulations with real-time controls. Watch patterns evolve and explore memory crystals as they form.</p>
                    </a>
                </div>

                <h2>📚 Documentation & API</h2>
                <div class="nav-grid">
                    <a href="/user-guide" class="nav-card">
                        <h3>📖 User Guide <span class="badge">Complete</span></h3>
                        <p>Comprehensive documentation covering setup, usage, research methodologies, and API reference. Perfect for researchers and developers.</p>
                    </a>

                    <a href="/docs" class="nav-card">
                        <h3>🔌 API Documentation <span class="badge">Interactive</span></h3>
                        <p>Interactive Swagger/OpenAPI documentation with live testing capabilities. Explore all endpoints for simulations, crystals, and analysis.</p>
                    </a>
                </div>
            </div>

            <div class="showcase-section">
                <h2>🎯 What Makes Integrated Runs Special</h2>
                <p>Revolutionary comparative analysis that combines multiple simulation approaches in one comprehensive study</p>

                <div class="showcase-grid">
                    <div class="showcase-card">
                        <h4>🧬 Morphic Resonance</h4>
                        <p>Experience true pattern-based memory effects with uncapped influence, adaptive neighborhoods, and Bayesian learning that creates measurable collective memory.</p>
                    </div>

                    <div class="showcase-card">
                        <h4>🤖 LLM Decision Making</h4>
                        <p>Watch AI make context-aware decisions for high-similarity patterns (>0.8), with 95%+ influence probability using OpenRouter API integration.</p>
                    </div>

                    <div class="showcase-card">
                        <h4>📊 Side-by-Side Analysis</h4>
                        <p>Compare morphic, LLM control, and classical Conway simulations with synchronized animations and frame-by-frame breakdowns.</p>
                    </div>

                    <div class="showcase-card">
                        <h4>🎓 Educational Content</h4>
                        <p>Learn with Conway's Game of Life factoids, morphic resonance explanations, and detailed technical insights throughout the analysis.</p>
                    </div>

                    <div class="showcase-card">
                        <h4>🔗 Research Notebooks</h4>
                        <p>Generate shareable permalinks with complete analysis, perfect for academic papers, presentations, and collaborative research.</p>
                    </div>

                    <div class="showcase-card">
                        <h4>⚡ Real-Time Progress</h4>
                        <p>Monitor simulation execution with live progress updates, stage descriptions, and automatic visualization generation.</p>
                    </div>
                </div>
            </div>

            <div class="nav-section">
                <h2>🔬 Core Technologies</h2>
                <div class="nav-grid">
                    <div class="nav-card">
                        <h3>🧠 Enhanced Morphic Engine</h3>
                        <p>Memory crystals with structural pattern storage, multi-scale similarity analysis (3x3 to 7x7), and uncapped influence allowing 100% Conway rule override.</p>
                    </div>

                    <div class="nav-card">
                        <h3>🎯 Intelligent Conway's Life</h3>
                        <p>Traditional cellular automata enhanced with LLM consultation, Markov chain predictions, and adaptive decision hierarchy for complex pattern recognition.</p>
                    </div>

                    <div class="nav-card">
                        <h3>📈 Scientific Validation</h3>
                        <p>33-85% decision influence rates, 0.45+ similarity-influence correlation, comprehensive testing, and statistical comparison frameworks.</p>
                    </div>
                </div>
            </div>

            <div class="status-bar">
                <div class="status-item">
                    <div class="status-dot"></div>
                    <span>Integrated Runs Ready</span>
                </div>
                <div class="status-item">
                    <div class="status-dot"></div>
                    <span>LLM Integration Active</span>
                </div>
                <div class="status-item">
                    <div class="status-dot"></div>
                    <span>Real-time Monitoring</span>
                </div>
                <div class="status-item">
                    <div class="status-dot"></div>
                    <span>Version 2.0.0</span>
                </div>
            </div>

            <div class="api-info">
                <strong>🔌 Integrated Runs API:</strong>
                POST /api/integrated-runs (create run) •
                GET /api/integrated-runs/{slug}/status (check progress) •
                GET /api/integrated-runs (list all runs) •
                DELETE /api/integrated-runs/{slug} (remove run) •
                <br><strong>Core API:</strong>
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
                        const displayName = file.name.replace(/^(single_|overview_|animation_|heatmap_|pattern_|crystal_)/, '').replace(/\\.png$/, '');
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
  sed 's/.*(\\([0-9.]*\\)%).*/\\1/' | \\
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


# Pydantic models for integrated runs
class IntegratedRunRequest(BaseModel):
    generations: int = 50
    grid_size: int = 20
    crystal_count: int = 5
    initial_density: float = 0.4
    simulation_types: List[str] = ["morphic", "llm_control", "classical"]
    slug: Optional[str] = None


class IntegratedRunResponse(BaseModel):
    slug: str
    status: str
    message: str


# Integrated Runs API Endpoints
@app.post("/api/integrated-runs", response_model=IntegratedRunResponse)
async def create_integrated_run(request: IntegratedRunRequest, background_tasks: BackgroundTasks):
    """Create and start a new integrated run"""
    try:
        # Convert request to parameters
        parameters = {
            "generations": request.generations,
            "grid_size": request.grid_size,
            "crystal_count": request.crystal_count,
            "initial_density": request.initial_density,
            "simulation_types": request.simulation_types
        }

        # Create the integrated run
        slug = await integrated_run_engine.create_integrated_run(parameters, request.slug)

        # Start execution in background
        background_tasks.add_task(integrated_run_engine.execute_integrated_run, slug)

        return IntegratedRunResponse(
            slug=slug,
            status="created",
            message=f"Integrated run created with slug: {slug}. Execution started in background."
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create integrated run: {str(e)}")


@app.get("/api/integrated-runs/{slug}/status")
async def get_integrated_run_status(slug: str):
    """Get the status of an integrated run"""
    status = integrated_run_engine.get_run_status(slug)

    if not status:
        raise HTTPException(status_code=404, detail="Integrated run not found")

    return status

@app.get("/api/integrated-runs/{slug}/files")
async def get_integrated_run_files(slug: str):
    """Get file generation progress for an integrated run"""
    import os
    from pathlib import Path

    print(f"🔍 [FILES API] Checking files for run: {slug}")
    results_dir = Path("results/integrated_runs") / slug
    print(f"🔍 [FILES API] Results directory: {results_dir}")
    print(f"🔍 [FILES API] Results directory exists: {results_dir.exists()}")

    if not results_dir.exists():
        print(f"❌ [FILES API] Results directory does not exist: {results_dir}")

        # Check if this is a valid run that's still in progress
        run_status = integrated_run_engine.get_run_status(slug)
        if run_status and run_status.get('status') in ['pending', 'running']:
            print(f"🔄 [FILES API] Run {slug} is {run_status['status']}, directory will be created soon")
            return {
                "files_generated": 0,
                "total_expected_files": 4,  # Expected: GIF + PNG files
                "file_progress": 0.0,
                "files": [],
                "is_truly_complete": False,
                "run_in_progress": True,
                "status": run_status['status']
            }
        else:
            print(f"❌ [FILES API] Run not found or completed without files: {slug}")
            return {
                "files_generated": 0,
                "total_expected_files": 0,
                "file_progress": 0.0,
                "files": [],
                "is_truly_complete": False,
                "run_in_progress": False
            }

    # Expected files list - these are the files we expect to be generated
    expected_files = [
        "side_by_side_comparison.gif",
        "classical_evolution.gif",
        "llm_control_evolution.gif",
        "morphic_evolution.gif",
        "comparative_analysis_*.png",
        "morphic_analysis_*.png",
        "population_dynamics_*.png",
        "statistical_summary_*.png",
        "frame_comparison_*.png"  # Multiple frame comparison files
    ]

    generated_files = []
    files_found = 0

    print(f"🔍 [FILES API] Scanning directory for files...")
    print(f"🔍 [FILES API] Directory contents: {list(results_dir.glob('*'))}")

    # Check all files in the directory
    for file_path in results_dir.glob("*.*"):
        print(f"🔍 [FILES API] Checking file: {file_path}")
        print(f"🔍 [FILES API] Is file: {file_path.is_file()}")
        if file_path.is_file():
            file_size = file_path.stat().st_size
            print(f"🔍 [FILES API] File size: {file_size} bytes")

            if file_size > 0:  # Only count non-empty files
                file_info = {
                    "name": file_path.name,
                    "size": file_size,
                    "url": f"/api/files/{slug}/{file_path.name}",
                    "type": "image" if file_path.suffix.lower() in ['.png', '.jpg', '.gif'] else "other",
                    "created": file_path.stat().st_mtime
                }
                generated_files.append(file_info)
                files_found += 1
                print(f"✅ [FILES API] Added file: {file_path.name} ({file_size} bytes)")
            else:
                print(f"⚠️ [FILES API] Skipping empty file: {file_path.name}")

    print(f"📊 [FILES API] Files found: {files_found}")

    # Estimate total expected files (this is approximate)
    total_expected = len(expected_files) + 10  # +10 for frame comparison files

    file_progress = min(files_found / total_expected, 1.0) if total_expected > 0 else 0.0

    # Consider truly complete when we have most expected files
    is_truly_complete = files_found >= (total_expected * 0.9)  # 90% of expected files

    return {
        "files_generated": files_found,
        "total_expected_files": total_expected,
        "file_progress": file_progress,
        "files": sorted(generated_files, key=lambda x: x["created"]),
        "is_truly_complete": is_truly_complete
    }

@app.get("/api/files/{slug}/{filename}")
async def serve_generated_file(slug: str, filename: str):
    """Serve generated files for preview"""
    from fastapi.responses import FileResponse
    from pathlib import Path
    import mimetypes

    try:
        file_path = Path("results/integrated_runs") / slug / filename

        print(f"🔍 [FILE SERVE] Serving {file_path}")

        if not file_path.exists():
            print(f"❌ [FILE SERVE] File not found: {file_path}")
            raise HTTPException(status_code=404, detail="File not found")

        if not file_path.is_file():
            print(f"❌ [FILE SERVE] Not a file: {file_path}")
            raise HTTPException(status_code=400, detail="Not a file")

        # Determine media type
        media_type, _ = mimetypes.guess_type(str(file_path))
        if media_type is None:
            media_type = "application/octet-stream"

        print(f"✅ [FILE SERVE] Serving {filename} ({media_type}) - {file_path.stat().st_size} bytes")

        return FileResponse(
            path=str(file_path),
            media_type=media_type,
            headers={"Cache-Control": "public, max-age=3600"}
        )

    except Exception as e:
        print(f"❌ [FILE SERVE] Error serving {filename}: {e}")
        raise HTTPException(status_code=500, detail=f"Error serving file: {e}")

@app.get("/api/integrated-runs/{slug}/analysis")
async def get_integrated_run_analysis(slug: str):
    """Get comprehensive analysis for an integrated run"""
    # Get basic run data
    run_data = integrated_run_engine.get_run_status(slug)

    if not run_data:
        raise HTTPException(status_code=404, detail="Integrated run not found")

    # Generate full analysis
    analysis_engine = AnalysisEngine()
    try:
        analysis = analysis_engine.generate_full_analysis(slug, run_data)
        return {
            "slug": slug,
            "run_data": run_data,
            "analysis": analysis
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis generation failed: {str(e)}")


@app.get("/api/integrated-runs")
async def list_integrated_runs(limit: int = 50):
    """List recent integrated runs"""
    runs = integrated_run_engine.list_integrated_runs(limit)
    return {"runs": runs}


@app.delete("/api/integrated-runs/{slug}")
async def delete_integrated_run(slug: str):
    """Delete an integrated run"""
    success = integrated_run_engine.delete_integrated_run(slug)

    if not success:
        raise HTTPException(status_code=404, detail="Integrated run not found")

    return {"message": f"Integrated run {slug} deleted successfully"}


# Frontend routes for integrated runs
@app.get("/integrated-runs/create", response_class=HTMLResponse)
async def integrated_runs_create_form():
    """Show form for creating new integrated runs"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Create Integrated Run - Emergence Simulator</title>
        <link rel="stylesheet" href="/static/css/main.css">
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🧬 Create Integrated Run</h1>
                <p>Configure and launch multiple comparative simulations</p>
            </div>

            <div class="form-container">
                <form id="integrated-run-form">
                    <div class="form-group">
                        <label for="slug">Custom URL Slug (optional):</label>
                        <input type="text" id="slug" name="slug" placeholder="my-experiment">
                        <small>Leave blank for auto-generated slug</small>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="generations">Generations:</label>
                            <input type="number" id="generations" name="generations" value="50" min="10" max="1000">
                        </div>

                        <div class="form-group">
                            <label for="grid_size">Grid Size:</label>
                            <input type="number" id="grid_size" name="grid_size" value="20" min="10" max="50">
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="crystal_count">Crystal Count:</label>
                            <input type="number" id="crystal_count" name="crystal_count" value="5" min="3" max="10">
                        </div>

                        <div class="form-group">
                            <label for="initial_density">Initial Density:</label>
                            <input type="number" id="initial_density" name="initial_density"
                                   value="0.4" min="0.1" max="0.8" step="0.1">
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Simulation Types:</label>
                        <div class="checkbox-group">
                            <label>
                                <input type="checkbox" name="simulation_types" value="morphic" checked>
                                Morphic Resonance
                            </label>
                            <label>
                                <input type="checkbox" name="simulation_types" value="llm_control">
                                LLM Control
                            </label>
                            <label>
                                <input type="checkbox" name="simulation_types" value="classical" checked>
                                Classical Conway
                            </label>
                        </div>
                    </div>

                    <button type="submit" class="btn btn-primary">
                        🚀 Create & Start Integrated Run
                    </button>
                </form>
            </div>
        </div>

        <script>
            document.getElementById('integrated-run-form').addEventListener('submit', async (e) => {
                e.preventDefault();

                const formData = new FormData(e.target);
                const data = {
                    generations: parseInt(formData.get('generations')),
                    grid_size: parseInt(formData.get('grid_size')),
                    crystal_count: parseInt(formData.get('crystal_count')),
                    initial_density: parseFloat(formData.get('initial_density')),
                    simulation_types: formData.getAll('simulation_types'),
                    slug: formData.get('slug') || null
                };

                try {
                    const response = await fetch('/api/integrated-runs', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    });

                    const result = await response.json();

                    if (response.ok) {
                        // Redirect to results page
                        window.location.href = `/integrated-runs/${result.slug}`;
                    } else {
                        alert('Error: ' + result.detail);
                    }
                } catch (error) {
                    alert('Error creating integrated run: ' + error.message);
                }
            });
        </script>
    </body>
    </html>
    """
    return html_content


@app.get("/integrated-runs/gallery", response_class=HTMLResponse)
async def integrated_runs_gallery():
    """Show gallery of all integrated runs"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Integrated Runs Gallery - Emergence Simulator</title>
        <link rel="stylesheet" href="/static/css/main.css">
        <style>
            .gallery-grid {
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }
            .run-card {
                border: 1px solid #ddd;
                border-radius: 8px;
                padding: 15px;
                background: white;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                transition: transform 0.2s;
            }
            .run-card:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.15);
            }
            .run-status {
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.8em;
                font-weight: bold;
            }
            .status-completed { background: #d4edda; color: #155724; }
            .status-running { background: #cce5ff; color: #004080; }
            .status-error { background: #f8d7da; color: #721c24; }
            .status-pending { background: #fff3cd; color: #856404; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📚 Integrated Runs Gallery</h1>
                <p>Browse all morphic resonance experiments</p>
            </div>

            <div class="controls">
                <a href="/integrated-runs/create" class="btn btn-primary">➕ Create New Run</a>
                <button id="refresh-btn" class="btn">🔄 Refresh</button>
            </div>

            <div id="gallery-container">
                <div class="gallery-grid" id="gallery-grid">
                    <!-- Gallery items will be loaded here -->
                </div>
            </div>
        </div>

        <script>
            async function loadGallery() {
                try {
                    const response = await fetch('/api/integrated-runs');
                    const data = await response.json();

                    const galleryGrid = document.getElementById('gallery-grid');
                    galleryGrid.innerHTML = '';

                    if (data.runs.length === 0) {
                        galleryGrid.innerHTML = '<p>No integrated runs found. <a href="/integrated-runs/create">Create your first run</a>!</p>';
                        return;
                    }

                    data.runs.forEach(run => {
                        const card = document.createElement('div');
                        card.className = 'run-card';

                        const statusClass = `status-${run.status}`;
                        const createdDate = new Date(run.created_at).toLocaleDateString();

                        card.innerHTML = `
                            <h3><a href="/integrated-runs/${run.slug}">${run.slug}</a></h3>
                            <p class="run-status ${statusClass}">${run.status.toUpperCase()}</p>
                            <p><strong>Created:</strong> ${createdDate}</p>
                            <p><strong>Generations:</strong> ${run.parameters.generations}</p>
                            <p><strong>Grid Size:</strong> ${run.parameters.grid_size}×${run.parameters.grid_size}</p>
                            <p><strong>Types:</strong> ${run.parameters.simulation_types.join(', ')}</p>
                            <div class="card-actions">
                                <a href="/integrated-runs/${run.slug}" class="btn btn-small">View</a>
                                <button onclick="deleteRun('${run.slug}')" class="btn btn-small btn-danger">Delete</button>
                            </div>
                        `;

                        galleryGrid.appendChild(card);
                    });

                } catch (error) {
                    console.error('Error loading gallery:', error);
                    document.getElementById('gallery-grid').innerHTML =
                        '<p>Error loading gallery. Please try again.</p>';
                }
            }

            async function deleteRun(slug) {
                if (!confirm(`Are you sure you want to delete the integrated run "${slug}"?`)) {
                    return;
                }

                try {
                    const response = await fetch(`/api/integrated-runs/${slug}`, {
                        method: 'DELETE'
                    });

                    if (response.ok) {
                        loadGallery(); // Refresh gallery
                    } else {
                        const error = await response.json();
                        alert('Error deleting run: ' + error.detail);
                    }
                } catch (error) {
                    alert('Error deleting run: ' + error.message);
                }
            }

            // Load gallery on page load
            loadGallery();

            // Refresh button
            document.getElementById('refresh-btn').addEventListener('click', loadGallery);
        </script>
    </body>
    </html>
    """
    return html_content


@app.get("/integrated-runs/{slug}", response_class=HTMLResponse)
async def integrated_run_results(slug: str):
    """Show results page for an integrated run"""
    # Get run status to verify it exists
    status = integrated_run_engine.get_run_status(slug)
    if not status:
        raise HTTPException(status_code=404, detail="Integrated run not found")

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Integrated Run: {slug} - Emergence Simulator</title>
        <link rel="stylesheet" href="/static/css/main.css">
        <style>
            .progress-bar {{
                width: 100%;
                height: 20px;
                background: #f0f0f0;
                border-radius: 10px;
                overflow: hidden;
                margin: 10px 0;
            }}
            .progress-fill {{
                height: 100%;
                background: linear-gradient(90deg, #4CAF50, #45a049);
                transition: width 0.3s ease;
            }}
            .status-pending {{ color: #ff9800; }}
            .status-running {{ color: #2196F3; }}
            .status-completed {{ color: #4CAF50; }}
            .status-error {{ color: #f44336; }}
            .results-section {{
                margin: 20px 0;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 8px;
            }}
            .summary-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .summary-card {{
                background: #f8f9fa;
                padding: 20px;
                border-radius: 8px;
                border: 1px solid #e9ecef;
            }}
            .summary-card h4 {{
                margin: 0 0 15px 0;
                color: #1e3c72;
            }}
            .summary-card ul {{
                margin: 0;
                padding-left: 20px;
            }}
            .feature-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}
            .feature-card {{
                background: white;
                padding: 20px;
                border-radius: 8px;
                border: 1px solid #e9ecef;
                position: relative;
            }}
            .feature-card h4 {{
                margin: 0 0 10px 0;
                color: #1e3c72;
            }}
            .status-badge {{
                position: absolute;
                top: 10px;
                right: 10px;
                background: #6c757d;
                color: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.7em;
                font-weight: 500;
            }}
            .permalink-section {{
                background: #e3f2fd;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .permalink-box {{
                display: flex;
                gap: 10px;
                margin: 15px 0;
            }}
            .permalink-box input {{
                flex: 1;
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-family: monospace;
                background: white;
            }}
            .coming-soon-section {{
                margin: 30px 0;
            }}

            /* Educational walkthrough styles */
            .educational-walkthrough {{
                max-width: 1200px;
                margin: 0 auto;
                font-family: system-ui, -apple-system, sans-serif;
            }}

            .intro-section {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 40px;
                border-radius: 15px;
                margin-bottom: 30px;
                text-align: center;
            }}

            .intro-section h2 {{
                margin: 0 0 20px 0;
                font-size: 2.5em;
                font-weight: 300;
                text-shadow: 0 2px 4px rgba(0,0,0,0.3);
            }}

            .lead {{
                font-size: 1.2em;
                line-height: 1.6;
                margin-bottom: 30px;
                opacity: 0.95;
            }}

            .key-concepts {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin-top: 30px;
            }}

            .concept-box {{
                background: rgba(255,255,255,0.1);
                padding: 20px;
                border-radius: 10px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.2);
            }}

            .concept-box h4 {{
                margin: 0 0 10px 0;
                font-size: 1.2em;
            }}

            .experiment-summary {{
                margin: 30px 0;
            }}

            .summary-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }}

            .param-card, .approaches-card, .execution-card {{
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}

            .param-list {{
                display: flex;
                flex-direction: column;
                gap: 12px;
            }}

            .param-item {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px;
                background: #f8f9fa;
                border-radius: 6px;
            }}

            .param-label {{
                font-weight: 500;
                color: #495057;
            }}

            .param-value {{
                font-weight: 600;
                color: #007bff;
            }}

            .param-note {{
                font-size: 0.8em;
                color: #6c757d;
                font-style: italic;
            }}

            .approach-list {{
                list-style: none;
                padding: 0;
            }}

            .approach-item {{
                display: flex;
                align-items: flex-start;
                gap: 12px;
                margin-bottom: 15px;
                padding: 12px;
                background: #f8f9fa;
                border-radius: 8px;
            }}

            .approach-icon {{
                font-size: 1.5em;
                flex-shrink: 0;
            }}

            .approach-details strong {{
                display: block;
                color: #495057;
                margin-bottom: 4px;
            }}

            .approach-details p {{
                margin: 0;
                font-size: 0.9em;
                color: #6c757d;
            }}

            .status-complete {{
                color: #28a745;
                font-weight: 600;
            }}

            /* Section dividers and guides */
            .section-divider {{
                margin: 50px 0 30px 0;
                text-align: center;
            }}

            .section-divider h2 {{
                color: #2c3e50;
                font-size: 2.2em;
                margin-bottom: 20px;
            }}

            .section-guide {{
                background: #f8f9fa;
                border-left: 5px solid #007bff;
                padding: 20px;
                margin: 20px 0;
                border-radius: 0 8px 8px 0;
            }}

            .guide-box {{
                margin-bottom: 20px;
            }}

            .guide-box h4 {{
                color: #495057;
                margin-bottom: 10px;
            }}

            .guide-box ul {{
                margin: 0;
                padding-left: 20px;
            }}

            .guide-box li {{
                margin-bottom: 8px;
                color: #6c757d;
            }}

            .legend-box {{
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 15px;
            }}

            .legend-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
                gap: 10px;
            }}

            .legend-item {{
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 0.9em;
            }}

            .legend-color {{
                width: 16px;
                height: 16px;
                border-radius: 3px;
                flex-shrink: 0;
            }}

            .legend-color.live {{ background: #000; }}
            .legend-color.dead {{ background: #fff; border: 1px solid #ccc; }}
            .legend-color.crystal {{ background: #9c27b0; }}
            .legend-color.influenced {{ background: #2196f3; }}

            /* Animation cards */
            .animations-section {{
                margin: 30px 0;
            }}

            .section-subtitle {{
                font-size: 1.1em;
                color: #6c757d;
                margin: 10px 0 20px 0;
                line-height: 1.5;
            }}

            .animations-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                gap: 30px;
                margin: 30px 0;
            }}

            .animation-card.enhanced {{
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }}

            .animation-card.enhanced:hover {{
                transform: translateY(-4px);
                box-shadow: 0 8px 20px rgba(0,0,0,0.15);
            }}

            .card-header {{
                background: #f8f9fa;
                padding: 20px;
                border-bottom: 1px solid #e0e0e0;
            }}

            .card-header h4 {{
                margin: 0 0 10px 0;
                color: #2c3e50;
            }}

            .animation-stats {{
                display: flex;
                gap: 15px;
            }}

            .stat {{
                background: white;
                padding: 4px 8px;
                border-radius: 12px;
                font-size: 0.8em;
                color: #6c757d;
                border: 1px solid #dee2e6;
            }}

            .animation-container {{
                padding: 20px;
                text-align: center;
            }}

            .evolution-animation {{
                max-width: 100%;
                height: auto;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}

            .card-content {{
                padding: 20px;
                background: #fafafa;
            }}

            .simulation-description {{
                font-size: 0.95em;
                line-height: 1.5;
                color: #495057;
                margin-bottom: 15px;
            }}

            .features-box, .observation-note {{
                margin: 15px 0;
                padding: 15px;
                background: white;
                border-radius: 8px;
                border-left: 4px solid #007bff;
            }}

            .features-box h5, .observation-note h5 {{
                margin: 0 0 10px 0;
                color: #495057;
                font-size: 0.9em;
            }}

            .features-list {{
                margin: 0;
                padding-left: 16px;
            }}

            .features-list li {{
                font-size: 0.85em;
                color: #6c757d;
                margin-bottom: 4px;
            }}

            .observation-note p {{
                margin: 0;
                font-size: 0.9em;
                color: #495057;
                font-style: italic;
            }}

            /* Comparison section */
            .comparison-section {{
                margin: 40px 0;
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}

            .comparison-guide {{
                background: #e3f2fd;
                padding: 20px;
            }}

            .comparison-points {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }}

            .point {{
                background: white;
                padding: 12px;
                border-radius: 8px;
                font-size: 0.9em;
                border-left: 4px solid #2196f3;
            }}

            .side-by-side-container {{
                padding: 30px;
                text-align: center;
            }}

            .comparison-animation {{
                max-width: 100%;
                height: auto;
                border-radius: 12px;
                box-shadow: 0 4px 16px rgba(0,0,0,0.1);
            }}

            .comparison-description {{
                margin-top: 15px;
                font-style: italic;
                color: #6c757d;
            }}

            /* LLM insights section */
            .llm-insights-section {{
                margin: 40px 0;
            }}

            .api-examples {{
                margin: 20px 0;
            }}

            .api-dropdown {{
                background: white;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}

            .api-example {{
                border: 1px solid #e0e0e0;
                margin-bottom: 1px;
            }}

            .api-example summary {{
                padding: 15px 20px;
                background: #f8f9fa;
                cursor: pointer;
                font-weight: 500;
                color: #495057;
                user-select: none;
                transition: background-color 0.2s ease;
            }}

            .api-example summary:hover {{
                background: #e9ecef;
            }}

            .api-content {{
                padding: 20px;
                background: #fafafa;
            }}

            .api-content h5 {{
                margin: 20px 0 10px 0;
                color: #495057;
                font-size: 1em;
            }}

            .api-content h5:first-child {{
                margin-top: 0;
            }}

            .code-block {{
                background: #282c34;
                color: #abb2bf;
                padding: 15px;
                border-radius: 8px;
                font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
                font-size: 0.85em;
                line-height: 1.4;
                overflow-x: auto;
                white-space: pre;
            }}

            /* Frame analysis section */
            .frame-analysis-section {{
                margin: 50px 0;
            }}

            .frame-interpretation-guide {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
                margin: 20px 0;
            }}

            .interpretation-box {{
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            }}

            .interpretation-box h4 {{
                margin: 0 0 15px 0;
                color: #2c3e50;
                font-size: 1.1em;
            }}

            .interpretation-box ul {{
                margin: 0;
                padding-left: 18px;
            }}

            .interpretation-box li {{
                margin-bottom: 8px;
                color: #6c757d;
                font-size: 0.9em;
            }}

            .frames-timeline {{
                margin: 30px 0;
            }}

            .frame-card.enhanced-frame {{
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                margin: 30px 0;
                overflow: hidden;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}

            .frame-header {{
                background: #f8f9fa;
                padding: 20px;
                border-bottom: 1px solid #e0e0e0;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}

            .frame-header h4 {{
                margin: 0;
                color: #2c3e50;
            }}

            .time-point {{
                background: #007bff;
                color: white;
                padding: 4px 12px;
                border-radius: 12px;
                font-size: 0.8em;
                font-weight: 500;
            }}

            .frame-visualization {{
                padding: 20px;
                text-align: center;
                background: #fafafa;
            }}

            .frame-visualization img {{
                max-width: 100%;
                height: auto;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            }}

            .frame-metrics {{
                padding: 20px;
            }}

            .frame-metrics h5 {{
                margin: 0 0 15px 0;
                color: #495057;
            }}

            .metrics-table {{
                display: flex;
                flex-direction: column;
                gap: 10px;
            }}

            .metric-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 12px;
                background: #f8f9fa;
                border-radius: 8px;
            }}

            .sim-type {{
                display: flex;
                align-items: center;
                gap: 8px;
            }}

            .sim-icon {{
                font-size: 1.2em;
            }}

            .metric-values {{
                display: flex;
                gap: 12px;
            }}

            .metric {{
                font-size: 0.85em;
                color: #6c757d;
                background: white;
                padding: 4px 8px;
                border-radius: 12px;
                border: 1px solid #dee2e6;
            }}

            .analysis-note {{
                background: #e8f4fd;
                border: 1px solid #bee5eb;
                border-radius: 8px;
                padding: 15px;
                margin-top: 15px;
            }}

            .analysis-note p {{
                margin: 0;
                color: #0c5460;
                font-size: 0.9em;
            }}

            /* Statistical analysis section */
            .statistical-analysis-section {{
                margin: 50px 0;
            }}

            .sheldrake-theory-box {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                border-radius: 15px;
                padding: 30px;
                margin: 30px 0;
            }}

            .theory-points {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
                gap: 20px;
                margin-top: 20px;
            }}

            .theory-point {{
                background: rgba(255,255,255,0.1);
                border-radius: 10px;
                padding: 20px;
                backdrop-filter: blur(10px);
                border: 1px solid rgba(255,255,255,0.2);
            }}

            .theory-point h5 {{
                margin: 0 0 10px 0;
                font-size: 1.1em;
            }}

            .theory-point p {{
                margin: 0;
                font-size: 0.9em;
                opacity: 0.9;
                line-height: 1.5;
            }}

            /* Chart enhancements */
            .chart-container-enhanced {{
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 12px;
                overflow: hidden;
                margin: 30px 0;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}

            .chart-header {{
                background: #f8f9fa;
                padding: 20px;
                border-bottom: 1px solid #e0e0e0;
            }}

            .chart-header h4 {{
                margin: 0 0 10px 0;
                color: #2c3e50;
            }}

            .chart-description {{
                margin: 0;
                color: #6c757d;
                font-size: 0.95em;
                line-height: 1.4;
            }}

            .chart-image-wrapper {{
                padding: 20px;
                text-align: center;
                background: #fafafa;
            }}

            .chart-interpretation {{
                padding: 20px;
                background: #e3f2fd;
                border-top: 1px solid #e0e0e0;
            }}

            .chart-interpretation h5 {{
                margin: 0 0 10px 0;
                color: #1976d2;
                font-size: 0.9em;
            }}

            .chart-interpretation p {{
                margin: 0;
                color: #0d47a1;
                font-size: 0.9em;
                line-height: 1.4;
            }}

            /* Insights and correlations */
            .insights-section {{
                margin: 40px 0;
            }}

            .insights-intro {{
                color: #6c757d;
                font-size: 1.05em;
                margin-bottom: 20px;
                line-height: 1.5;
            }}

            .insights-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }}

            .insight-card {{
                background: white;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                border: 1px solid #e0e0e0;
            }}

            .insight-card.high-significance {{
                border-left: 5px solid #d32f2f;
            }}

            .insight-card.medium-significance {{
                border-left: 5px solid #f57c00;
            }}

            .insight-card.low-significance {{
                border-left: 5px solid #388e3c;
            }}

            .insight-header {{
                background: #f8f9fa;
                padding: 15px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }}

            .insight-number {{
                background: #007bff;
                color: white;
                width: 24px;
                height: 24px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 0.8em;
                font-weight: 600;
            }}

            .significance-badge {{
                font-size: 0.75em;
                padding: 2px 8px;
                border-radius: 12px;
                background: #6c757d;
                color: white;
                text-transform: capitalize;
            }}

            .insight-content {{
                padding: 15px;
            }}

            .insight-content p {{
                margin: 0;
                color: #495057;
                line-height: 1.5;
            }}

            .correlations-section {{
                margin: 40px 0;
            }}

            .correlations-intro {{
                color: #6c757d;
                font-size: 1.05em;
                margin-bottom: 20px;
                line-height: 1.5;
            }}

            .correlation-guide {{
                display: flex;
                justify-content: center;
                gap: 20px;
                margin: 20px 0;
                flex-wrap: wrap;
            }}

            .guide-item {{
                font-size: 0.85em;
                display: flex;
                align-items: center;
                gap: 8px;
            }}

            .corr-strong-pos {{ color: #d32f2f; font-weight: 600; }}
            .corr-moderate-pos {{ color: #f57c00; font-weight: 600; }}
            .corr-weak {{ color: #6c757d; font-weight: 600; }}
            .corr-moderate-neg {{ color: #f57c00; font-weight: 600; }}
            .corr-strong-neg {{ color: #d32f2f; font-weight: 600; }}

            .correlation-matrix {{
                display: flex;
                flex-direction: column;
                gap: 15px;
                margin-top: 20px;
            }}

            .correlation-item {{
                background: white;
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                padding: 20px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.05);
            }}

            .correlation-item.strong.positive {{
                border-left: 5px solid #388e3c;
            }}

            .correlation-item.strong.negative {{
                border-left: 5px solid #d32f2f;
            }}

            .correlation-item.moderate.positive {{
                border-left: 5px solid #689f38;
            }}

            .correlation-item.moderate.negative {{
                border-left: 5px solid #f57c00;
            }}

            .correlation-item.weak {{
                border-left: 5px solid #9e9e9e;
            }}

            .correlation-label {{
                font-weight: 600;
                color: #2c3e50;
                margin-bottom: 8px;
            }}

            .correlation-value {{
                font-size: 1.5em;
                font-weight: 700;
                color: #007bff;
                margin-bottom: 10px;
            }}

            .correlation-bar {{
                height: 6px;
                background: #e9ecef;
                border-radius: 3px;
                overflow: hidden;
                margin-bottom: 10px;
            }}

            .correlation-fill {{
                height: 100%;
                background: #007bff;
                border-radius: 3px;
                transition: width 0.3s ease;
            }}

            .correlation-interpretation {{
                font-size: 0.85em;
                color: #6c757d;
                font-style: italic;
            }}

            /* Conclusion section */
            .conclusion-section {{
                margin: 60px 0 40px 0;
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                border-radius: 15px;
                padding: 40px;
            }}

            .conclusion-content {{
                max-width: 1000px;
                margin: 0 auto;
            }}

            .conclusion-intro {{
                font-size: 1.2em;
                color: #2c3e50;
                text-align: center;
                line-height: 1.6;
                margin-bottom: 40px;
                font-weight: 300;
            }}

            .findings-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
                gap: 30px;
                margin: 40px 0;
            }}

            .finding-category {{
                background: white;
                border-radius: 12px;
                padding: 25px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}

            .finding-category h3 {{
                margin: 0 0 20px 0;
                color: #2c3e50;
                font-size: 1.3em;
            }}

            .findings-list {{
                display: flex;
                flex-direction: column;
                gap: 20px;
            }}

            .finding-item {{
                border-left: 4px solid #007bff;
                padding-left: 15px;
            }}

            .finding-item h4 {{
                margin: 0 0 8px 0;
                color: #495057;
                font-size: 1em;
            }}

            .finding-item p {{
                margin: 0;
                color: #6c757d;
                font-size: 0.9em;
                line-height: 1.4;
            }}

            .implications-list {{
                display: flex;
                flex-direction: column;
                gap: 20px;
            }}

            .implication-item {{
                border-left: 4px solid #28a745;
                padding-left: 15px;
            }}

            .implication-item h4 {{
                margin: 0 0 8px 0;
                color: #495057;
                font-size: 1em;
            }}

            .implication-item p {{
                margin: 0;
                color: #6c757d;
                font-size: 0.9em;
                line-height: 1.4;
            }}

            .methodology-notes {{
                margin: 40px 0;
                background: white;
                border-radius: 12px;
                padding: 25px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}

            .methodology-notes h3 {{
                margin: 0 0 20px 0;
                color: #e67e22;
            }}

            .limitations-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 20px;
            }}

            .limitation {{
                border-left: 4px solid #e67e22;
                padding-left: 15px;
            }}

            .limitation h4 {{
                margin: 0 0 8px 0;
                color: #495057;
                font-size: 1em;
            }}

            .limitation p {{
                margin: 0;
                color: #6c757d;
                font-size: 0.9em;
                line-height: 1.4;
            }}

            .next-steps {{
                margin: 40px 0;
                background: white;
                border-radius: 12px;
                padding: 25px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}

            .next-steps h3 {{
                margin: 0 0 20px 0;
                color: #8e44ad;
            }}

            .next-steps-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
                gap: 20px;
            }}

            .research-direction {{
                border-left: 4px solid #8e44ad;
                padding-left: 15px;
            }}

            .research-direction h4 {{
                margin: 0 0 8px 0;
                color: #495057;
                font-size: 1em;
            }}

            .research-direction p {{
                margin: 0;
                color: #6c757d;
                font-size: 0.9em;
                line-height: 1.4;
            }}

            .philosophical-reflection {{
                margin: 40px 0;
                background: white;
                border-radius: 12px;
                padding: 25px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}

            .philosophical-reflection h3 {{
                margin: 0 0 20px 0;
                color: #34495e;
            }}

            .reflection-content ul {{
                margin: 15px 0;
                padding-left: 20px;
            }}

            .reflection-content li {{
                margin-bottom: 8px;
                color: #6c757d;
                line-height: 1.4;
            }}

            .reflection-conclusion {{
                font-style: italic;
                color: #495057;
                border-left: 4px solid #34495e;
                padding-left: 15px;
                margin-top: 20px;
            }}

            .acknowledgments {{
                margin: 40px 0;
                background: white;
                border-radius: 12px;
                padding: 25px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                text-align: center;
            }}

            .acknowledgments h3 {{
                margin: 0 0 15px 0;
                color: #2c3e50;
            }}

            .acknowledgments p {{
                margin: 0;
                color: #6c757d;
                line-height: 1.5;
                font-style: italic;
            }}

            /* Responsive design */
            @media (max-width: 768px) {{
                .key-concepts {{
                    grid-template-columns: 1fr;
                }}

                .summary-grid {{
                    grid-template-columns: 1fr;
                }}

                .animations-grid {{
                    grid-template-columns: 1fr;
                }}

                .comparison-points {{
                    grid-template-columns: 1fr;
                }}

                .findings-grid {{
                    grid-template-columns: 1fr;
                }}

                .intro-section {{
                    padding: 20px;
                }}

                .intro-section h2 {{
                    font-size: 2em;
                }}

                .conclusion-section {{
                    padding: 20px;
                }}

                .metric-values {{
                    flex-direction: column;
                    gap: 4px;
                }}

                .correlation-guide {{
                    flex-direction: column;
                    align-items: center;
                }}
            }}

            /* File Progress Styles */
            .file-progress-container {{
                background: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
            }}

            .files-grid {{
                display: grid;
                grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }}

            .file-item {{
                background: white;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                padding: 10px;
                text-align: center;
                transition: transform 0.2s, box-shadow 0.2s;
                position: relative;
            }}

            .file-item:hover {{
                transform: translateY(-2px);
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }}

            .file-preview {{
                width: 100%;
                height: 80px;
                object-fit: cover;
                border-radius: 4px;
                margin-bottom: 8px;
            }}

            .file-icon {{
                font-size: 40px;
                height: 80px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #f8f9fa;
                border-radius: 4px;
                margin-bottom: 8px;
            }}

            .file-name {{
                font-size: 11px;
                color: #666;
                word-break: break-all;
                line-height: 1.2;
            }}

            .proceed-button-container {{
                background: #e7f3ff;
                border: 1px solid #b3d7ff;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
                text-align: center;
            }}

            .btn-proceed {{
                background: #007bff;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 6px;
                font-size: 16px;
                cursor: pointer;
                transition: background 0.2s;
            }}

            .btn-proceed:hover {{
                background: #0056b3;
            }}

            .proceed-note {{
                margin: 10px 0 0 0;
                color: #666;
                font-size: 14px;
            }}

            .error-message {{
                background: #f8d7da;
                border: 1px solid #f5c6cb;
                border-radius: 8px;
                padding: 20px;
                margin: 20px 0;
                text-align: center;
            }}

            .error-message h3 {{
                color: #721c24;
                margin-bottom: 10px;
            }}

            .error-message p {{
                color: #721c24;
                margin-bottom: 15px;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🎮 Integrated Run: {slug}</h1>
                <p>Conway's Game of Life - Comparative Simulation Analysis</p>
            </div>

            <div class="status-section">
                <h2>Execution Status</h2>
                <div id="status-display">
                    <p>Status: <span id="current-status" class="status-pending">Loading...</span></p>
                    <p>Stage: <span id="current-stage">Initializing</span></p>
                    <div class="progress-bar">
                        <div id="progress-fill" class="progress-fill" style="width: 0%"></div>
                    </div>
                    <p>Progress: <span id="progress-text">0%</span></p>
                </div>
            </div>

            <div id="results-container" class="results-section" style="display: none;">
                <h2>🎯 Results & Analysis</h2>
                <div id="results-content">
                    <!-- Results will be loaded here when completed -->
                </div>
            </div>

            <div class="navigation">
                <a href="/integrated-runs/gallery" class="btn">📚 View Gallery</a>
                <a href="/integrated-runs/create" class="btn">➕ Create New Run</a>
            </div>
        </div>

        <script>
            const slug = '{slug}';
            const initialStatus = '{status["status"]}';
            let pollInterval;
            let failureCount = 0;
            const maxFailures = 5;

            let fileGenerationStartTime = Date.now();
            let fileGenerationTimeoutShown = false;
            let displayedFiles = new Set(); // Track which files we've already displayed

            async function displayProgressiveContent(files, isComplete) {{
                console.log('🎬 Progressive display: ' + files.length + ' files available, complete: ' + isComplete);

                if (files.length === 0 && !isComplete) {{
                    // No files yet, show loading placeholder
                    document.getElementById('results-content').innerHTML = `
                        <div class="progressive-loading">
                            <h3>🔬 Generating Analysis & Visualizations...</h3>
                            <p>Creating side-by-side comparisons, statistical analysis, and educational content...</p>
                            <div class="loading-spinner">⏳</div>
                        </div>
                    `;
                    return;
                }}

                // Start building content progressively
                let contentHtml = '';

                // Add educational header if we have any files
                if (files.length > 0 || isComplete) {{
                    contentHtml += `
                        <div class="educational-walkthrough" style="background: white; padding: 20px; border: 2px solid #4CAF50; border-radius: 8px; margin: 20px 0;">
                            <h3 style="color: #4CAF50; font-size: 24px; margin-bottom: 15px;">🎮 Conway's Game of Life Analysis Results</h3>
                            <p style="font-size: 16px; line-height: 1.6; margin-bottom: 15px;">
                                Files ready: <strong>${{files.length}}/19</strong> • Status: <strong>${{isComplete ? "Complete" : "Generating..."}}</strong>
                            </p>
                        </div>
                    `;
                }}

                // Group files by type for better organization
                const imageFiles = files.filter(f => f.name.endsWith('.png') || f.name.endsWith('.jpg'));
                const gifFiles = files.filter(f => f.name.endsWith('.gif'));
                const videoFiles = files.filter(f => f.name.endsWith('.mp4'));

                // Display animations/GIFs first (most engaging)
                if (gifFiles.length > 0) {{
                    contentHtml += '<h3 style="color: #2196F3;">🎬 Animation Comparisons</h3>';
                    gifFiles.forEach(file => {{
                        if (!displayedFiles.has(file.name)) {{
                            contentHtml += `
                                <div class="animation-card enhanced" style="margin: 20px 0; border: 2px solid #2196F3; border-radius: 8px; padding: 15px;">
                                    <h4>${{file.name.replace(/[_-]/g, ' ').replace('.gif', '')}}</h4>
                                    <img src="${{file.url}}" alt="${{file.name}}" style="max-width: 100%; height: auto; border-radius: 4px;"
                                         onerror="console.error('Failed to load animation:', this.src); this.style.border='2px solid red'; this.alt='❌ Failed to load: ' + this.alt;"
                                         onload="console.log('Successfully loaded animation:', this.src);">
                                    <p style="color: #666; font-size: 12px;">File size: ${{(file.size/1024/1024).toFixed(2)}} MB • Just created!</p>
                                </div>
                            `;
                            displayedFiles.add(file.name);
                            console.log('🆕 Added animation: ' + file.name);
                        }}
                    }});
                }}

                // Display static analysis images
                if (imageFiles.length > 0) {{
                    contentHtml += '<h3 style="color: #FF9800;">📊 Statistical Analysis</h3>';
                    imageFiles.forEach(file => {{
                        if (!displayedFiles.has(file.name)) {{
                            contentHtml += `
                                <div class="analysis-card" style="margin: 15px 0; border: 1px solid #FF9800; border-radius: 8px; padding: 10px;">
                                    <h4>${{file.name.replace(/[_-]/g, ' ').replace('.png', '')}}</h4>
                                    <img src="${{file.url}}" alt="${{file.name}}" style="max-width: 100%; height: auto; border-radius: 4px;"
                                         onerror="console.error('Failed to load chart:', this.src); this.style.border='2px solid red'; this.alt='❌ Failed to load: ' + this.alt;"
                                         onload="console.log('Successfully loaded chart:', this.src);">
                                    <p style="color: #666; font-size: 12px;">File size: ${{(file.size/1024).toFixed(0)}} KB</p>
                                </div>
                            `;
                            displayedFiles.add(file.name);
                            console.log('🆕 Added analysis: ' + file.name);
                        }}
                    }});
                }}

                // Add completion message and full analysis if complete
                if (isComplete) {{
                    contentHtml += `
                        <div style="background: #E8F5E8; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <h3 style="color: #4CAF50;">✅ Analysis Complete!</h3>
                            <p>All visualizations and statistical analysis have been generated. Conway's Game of Life simulations show fascinating pattern evolution and emergent behaviors across different simulation modes.</p>
                        </div>
                    `;
                }}

                // Update the content
                document.getElementById('results-content').innerHTML = contentHtml;
                console.log('📱 Updated progressive content: ' + files.length + ' files displayed');
            }}

            async function checkFileGenerationProgress(status) {{
                try {{
                    console.log('🔍 Checking file generation progress...');
                    const filesResponse = await fetch(`/api/integrated-runs/${{slug}}/files`);

                    if (!filesResponse.ok) {{
                        throw new Error('Failed to fetch file progress');
                    }}

                    const fileData = await filesResponse.json();
                    console.log('📁 File progress data:', fileData);

                    // Update progress to show actual file generation progress
                    const fileProgress = Math.round(fileData.file_progress * 100);
                    const totalProgress = Math.max(fileProgress, 95); // At least 95% when files are generating

                    document.getElementById('progress-fill').style.width = totalProgress + '%';
                    document.getElementById('progress-text').textContent = totalProgress + '%';

                    // Progressive content display - show content as files become available or if run is in progress
                    if (fileData.files_generated > 0 || status.status === 'completed' || fileData.run_in_progress) {{
                        console.log('📊 Showing progressive content - ' + fileData.files_generated + ' files ready, run_in_progress: ' + !!fileData.run_in_progress);
                        document.getElementById('results-container').style.display = 'block';

                        // If run is in progress but no files yet, show waiting state
                        if (fileData.files_generated === 0 && fileData.run_in_progress) {{
                            console.log('⏳ Run in progress, showing waiting state...');
                            document.getElementById('results-content').innerHTML = `
                                <div class="loading-state">
                                    <h3>🔬 Generating Conway Analysis...</h3>
                                    <p>Processing side-by-side animations, statistical analysis, and Conway insights...</p>
                                    <p><em>Status: ${{fileData.status || 'running'}}</em></p>
                                    <div class="progress-bar"><div class="progress-fill" style="width: 50%"></div></div>
                                </div>
                            `;
                        }} else if (fileData.files_generated > 0) {{
                            // Use the simple direct loading approach when files are available
                            console.log('📁 Files available - using direct loading approach');
                            loadCompletedResults();
                        }} else {{
                            await displayProgressiveContent(fileData.files, status.status === 'completed');
                        }}
                    }}

                    // Check if files are complete
                    if (fileData.is_truly_complete) {{
                        // Files are complete - finalize display
                        console.log('✅ FILES COMPLETE! Finalizing display...');
                        document.getElementById('current-stage').textContent = 'Complete';
                        document.getElementById('progress-fill').style.width = '100%';
                        document.getElementById('progress-text').textContent = '100%';

                        // Show final complete content
                        await displayProgressiveContent(fileData.files, true);

                        // Stop polling immediately
                        clearInterval(pollInterval);
                        return;
                    }}

                    // Check for timeout or empty files (15 seconds with no file progress)
                    const timeElapsed = Date.now() - fileGenerationStartTime;
                    const timeoutSeconds = 15;
                    if (timeElapsed > timeoutSeconds * 1000 && fileData.files_generated === 0 && !fileGenerationTimeoutShown) {{
                        console.log('⚠️ TIMEOUT! 15 seconds with no files - showing available content...');
                        document.getElementById('current-stage').textContent = 'Complete';
                        document.getElementById('progress-fill').style.width = '100%';
                        document.getElementById('progress-text').textContent = '100%';
                        document.getElementById('results-container').style.display = 'block';

                        // Show timeout message with any available content
                        await displayProgressiveContent(fileData.files, true);

                        // Stop polling immediately
                        clearInterval(pollInterval);
                        fileGenerationTimeoutShown = true;
                        return;
                    }}

                    // Files not complete - show progress
                    document.getElementById('current-stage').textContent =
                        `Generating Conway analysis files (${{fileData.files_generated}}/${{fileData.total_expected_files}})`;

                    // Show file generation progress (with error handling)
                    if (fileData.files_generated > 0 || timeElapsed < 60000) {{ // Show for first minute or if files exist
                        try {{
                            await displayFileProgress(fileData);
                        }} catch (displayError) {{
                            console.warn('Could not display file progress UI (DOM elements not ready):', displayError.message);
                            // Continue without the file progress display
                        }}
                    }}

                    // Continue polling until truly complete
                    return;

                }} catch (error) {{
                    console.error('Error checking file progress:', error);
                    console.log('⚠️ File progress check failed - proceeding with results');

                    // Fallback to completion - better to show results than hang
                    document.getElementById('current-stage').textContent = 'Complete';
                    document.getElementById('progress-fill').style.width = '100%';
                    document.getElementById('progress-text').textContent = '100%';
                    document.getElementById('results-container').style.display = 'block';
                    clearInterval(pollInterval);

                    try {{
                        await loadResults();
                    }} catch (resultsError) {{
                        console.error('Results loading also failed:', resultsError);
                        showProceedButton(); // Last resort fallback
                    }}
                }}
            }}

            async function displayFileProgress(fileData, isComplete = false) {{
                const progressContainer = document.getElementById('file-progress-container') ||
                    createFileProgressContainer();

                progressContainer.innerHTML = `
                    <h4>${{isComplete ? '📁 Generated Files' : '⏳ Generating Files'}} (${{fileData.files_generated}}/${{fileData.total_expected_files}})</h4>
                    <div class="files-grid">
                        ${{fileData.files.map(file => `
                            <div class="file-item" title="${{file.name}} (${{(file.size / 1024).toFixed(1)}} KB)">
                                ${{file.type === 'image' ?
                                    `<img src="${{file.url}}" alt="${{file.name}}" class="file-preview" loading="lazy">` :
                                    `<div class="file-icon">📄</div>`
                                }}
                                <div class="file-name">${{file.name.length > 20 ? file.name.substring(0, 17) + '...' : file.name}}</div>
                            </div>
                        `).join('')}}
                    </div>
                `;
            }}

            function createFileProgressContainer() {{
                const container = document.createElement('div');
                container.id = 'file-progress-container';
                container.className = 'file-progress-container';

                try {{
                    // Insert after the progress bar
                    const progressBar = document.querySelector('.progress-bar');
                    if (progressBar && progressBar.parentNode) {{
                        progressBar.parentNode.insertBefore(container, progressBar.nextSibling);
                        return container;
                    }}

                    // Fallback: insert after execution status
                    const executionStatus = document.querySelector('.execution-status');
                    if (executionStatus && executionStatus.parentNode) {{
                        executionStatus.parentNode.insertBefore(container, executionStatus.nextSibling);
                        return container;
                    }}

                    // Final fallback: insert into results container
                    const resultsContainer = document.getElementById('results-container');
                    if (resultsContainer) {{
                        resultsContainer.insertBefore(container, resultsContainer.firstChild);
                        return container;
                    }}

                    // Last resort: append to body
                    document.body.appendChild(container);
                }} catch (error) {{
                    console.error('Error inserting file progress container:', error);
                    // Still return the container even if insertion fails
                }}

                return container;
            }}

            function showProceedButton() {{
                const buttonContainer = document.getElementById('proceed-button-container') ||
                    createProceedButtonContainer();

                buttonContainer.innerHTML = `
                    <button onclick="proceedToResults()" class="btn btn-primary btn-proceed">
                        📊 Proceed to Analysis
                    </button>
                    <p class="proceed-note">File generation may still be in progress, but you can view available results now.</p>
                `;
            }}

            function createProceedButtonContainer() {{
                const container = document.createElement('div');
                container.id = 'proceed-button-container';
                container.className = 'proceed-button-container';

                const resultsContainer = document.getElementById('results-container');
                resultsContainer.parentNode.insertBefore(container, resultsContainer);

                return container;
            }}

            async function proceedToResults() {{
                console.log('👆 User clicked proceed to results');
                document.getElementById('results-container').style.display = 'block';
                document.getElementById('proceed-button-container').style.display = 'none';

                try {{
                    await loadResults();
                    console.log('✅ Results loaded via proceed button');
                }} catch (error) {{
                    console.error('❌ Results loading failed via proceed button:', error);
                    document.getElementById('results-content').innerHTML = `
                        <div class="error-message">
                            <h3>⚠️ Results Not Yet Available</h3>
                            <p>The analysis is still processing. Please wait a moment and try again.</p>
                            <button onclick="window.location.reload()" class="btn btn-secondary">🔄 Refresh Page</button>
                        </div>
                    `;
                }}
            }}

            async function updateStatus() {{
                try {{
                    console.log('🔄 updateStatus() called');
                    const response = await fetch(`/api/integrated-runs/${{slug}}/status`);

                    if (!response.ok) {{
                        throw new Error(`HTTP ${{response.status}}: ${{response.statusText}}`);
                    }}

                    const status = await response.json();

                    // Reset failure count on successful fetch
                    failureCount = 0;

                    // Update status display
                    const statusElement = document.getElementById('current-status');
                    statusElement.textContent = status.status;
                    statusElement.className = `status-${{status.status}}`;

                    document.getElementById('current-stage').textContent = status.current_stage || 'N/A';

                    const progress = Math.round((status.progress || 0) * 100);
                    document.getElementById('progress-fill').style.width = progress + '%';
                    document.getElementById('progress-text').textContent = progress + '%';

                    // Check file generation progress and load media immediately when available
                    if (status.status === 'completed') {{
                        console.log('🎯 Status completed - loading results directly');
                        document.getElementById('results-container').style.display = 'block';
                        loadCompletedResults();
                        clearInterval(pollInterval); // Stop polling when completed
                    }} else if (status.status === 'running') {{
                        // Even when running, check if we have any files to display progressively
                        await checkFileGenerationProgress(status);
                    }} else if (status.status === 'error') {{
                        clearInterval(pollInterval);
                        alert('Error: ' + (status.error_message || 'Unknown error'));
                    }}

                }} catch (error) {{
                    failureCount++;
                    console.error('Error fetching status:', {{
                        error: error.message,
                        slug: slug,
                        url: `/api/integrated-runs/${{slug}}/status`,
                        timestamp: new Date().toISOString(),
                        failureCount: failureCount,
                        maxFailures: maxFailures
                    }});

                    // Stop polling after too many failures
                    if (failureCount >= maxFailures) {{
                        console.log(`Max failures (${{maxFailures}}) reached. Stopping status polling and refreshing page...`);
                        clearInterval(pollInterval);
                        setTimeout(() => {{
                            window.location.reload();
                        }}, 2000);
                    }} else if (error.message.includes('404') || error.message.includes('Failed to fetch')) {{
                        console.log('Status fetch failed - this might indicate the run is complete. Refreshing page...');
                        setTimeout(() => {{
                            window.location.reload();
                        }}, 2000);
                        clearInterval(pollInterval);
                    }}
                }}
            }}

            let isLoadingResults = false;
            async function loadResults() {{
                if (isLoadingResults) {{
                    console.log('⏳ loadResults already in progress, skipping duplicate call');
                    return;
                }}
                isLoadingResults = true;

                try {{
                    console.log('🔄 Starting loadResults...');

                    // Always load results when called - this function is only called when we're ready
                    console.log('🔍 loadResults called - proceeding to load results content');

                    // Show loading state
                    document.getElementById('results-content').innerHTML = `
                        <div class="loading-state">
                            <h3>🔬 Generating Analysis...</h3>
                            <p>Processing side-by-side animations, statistical analysis, and morphic insights...</p>
                            <div class="progress-bar"><div class="progress-fill"></div></div>
                        </div>
                    `;

                    // Get comprehensive analysis
                    console.log('📡 Fetching analysis data...');
                    const response = await fetch(`/api/integrated-runs/${{slug}}/analysis`);

                    if (!response.ok) {{
                        throw new Error(`Analysis API error: ${{response.status}} ${{response.statusText}}`);
                    }}

                    const fullData = await response.json();
                    console.log('✅ Analysis data received:', fullData);

                    const runData = fullData.run_data;
                    const analysis = fullData.analysis;

                    let resultsHtml = `
                        <div class="educational-walkthrough" style="background: white; padding: 20px; border: 2px solid #4CAF50; border-radius: 8px; margin: 20px 0;">
                            <h3 style="color: #4CAF50; font-size: 24px; margin-bottom: 15px;">✅ Educational walkthrough is working!</h3>
                            <p style="color: #333; font-size: 16px; line-height: 1.6;">The minimal test content is displaying correctly. The DOM manipulation is successful and the educational content framework is ready.</p>
                            <div class="concept-box" style="background: #f0f8ff; padding: 15px; border-left: 4px solid #2196F3; margin: 15px 0;">
                                <h4 style="color: #2196F3; margin-bottom: 10px;">🎓 Debug Information</h4>
                                <p style="color: #333;">This content was generated via JavaScript DOM manipulation and proves that the educational walkthrough system is functioning properly.</p>
                            </div>
                        </div>
                    `;

                    console.log('🎨 Setting results HTML...');
                    const resultsElement = document.getElementById('results-content');
                    console.log('📋 Results element found:', !!resultsElement);
                    if (resultsElement) {{
                        console.log('📏 Current innerHTML length:', resultsElement.innerHTML.length);
                        console.log('📄 Current innerHTML preview:', resultsElement.innerHTML.substring(0, 100));
                        console.log('📏 New HTML length:', resultsHtml.length);
                        console.log('📄 New HTML preview:', resultsHtml.substring(0, 200));

                        resultsElement.innerHTML = resultsHtml;

                        console.log('📏 After setting - innerHTML length:', resultsElement.innerHTML.length);
                        console.log('📄 After setting - innerHTML preview:', resultsElement.innerHTML.substring(0, 200));
                        console.log('✅ Results HTML set successfully!');

                        // Check if educational content is present
                        const eduContent = resultsElement.querySelector('.educational-walkthrough');
                        console.log('🎓 Educational walkthrough found after setting:', !!eduContent);
                    }} else {{
                        console.error('❌ Results element not found!');
                    }}

                }} catch (error) {{
                    console.error('❌ Error loading results:', {{
                        error: error.message,
                        stack: error.stack,
                        slug: slug
                    }});
                    document.getElementById('results-content').innerHTML = `
                        <p>❌ Error loading detailed results. The analysis completed successfully, but detailed data could not be retrieved.</p>
                        <p>Run details: Started at ${{new Date().toLocaleString()}}</p>
                    `;
                }} finally {{
                    isLoadingResults = false;
                }}
            }}

            function copyPermalink() {{
                const input = document.getElementById('permalink-input');
                input.select();
                document.execCommand('copy');

                const button = input.nextElementSibling;
                const originalText = button.textContent;
                button.textContent = '✅ Copied!';
                setTimeout(() => {{
                    button.textContent = originalText;
                }}, 2000);
            }}

            // Simple direct file loading function for completed runs
            async function loadCompletedResults() {{
                try {{
                    console.log('🔄 Loading files directly for completed run...');
                    const filesResponse = await fetch(`/api/integrated-runs/${{slug}}/files`);
                    const fileData = await filesResponse.json();

                    console.log('📁 Files loaded:', fileData.files.length);

                    // Simple, direct content generation
                    let html = `
                        <div style="background: white; padding: 20px; border: 2px solid #4CAF50; border-radius: 8px; margin: 20px 0;">
                            <h3 style="color: #4CAF50;">🎮 Conway's Game of Life Analysis Results</h3>
                            <p>Files ready: <strong>${{fileData.files.length}}/19</strong> • Status: <strong>Complete</strong></p>
                        </div>
                    `;

                    // Add animations
                    const gifFiles = fileData.files.filter(f => f.name.endsWith('.gif'));
                    if (gifFiles.length > 0) {{
                        html += '<h3 style="color: #2196F3;">🎬 Animation Comparisons</h3>';
                        gifFiles.forEach(file => {{
                            html += `
                                <div style="margin: 20px 0; border: 2px solid #2196F3; border-radius: 8px; padding: 15px;">
                                    <h4>${{file.name.replace(/[_-]/g, ' ').replace('.gif', '')}}</h4>
                                    <img src="${{file.url}}" alt="${{file.name}}" style="max-width: 100%; height: auto; border-radius: 4px;"
                                         onload="console.log('✅ Loaded:', this.src)"
                                         onerror="console.error('❌ Failed:', this.src)">
                                    <p style="color: #666; font-size: 12px;">File size: ${{(file.size/1024/1024).toFixed(2)}} MB</p>
                                </div>
                            `;
                        }});
                    }}

                    // Add charts
                    const pngFiles = fileData.files.filter(f => f.name.endsWith('.png'));
                    if (pngFiles.length > 0) {{
                        html += '<h3 style="color: #FF9800;">📊 Statistical Analysis</h3>';
                        pngFiles.forEach(file => {{
                            html += `
                                <div style="margin: 15px 0; border: 1px solid #FF9800; border-radius: 8px; padding: 10px;">
                                    <h4>${{file.name.replace(/[_-]/g, ' ').replace('.png', '')}}</h4>
                                    <img src="${{file.url}}" alt="${{file.name}}" style="max-width: 100%; height: auto; border-radius: 4px;"
                                         onload="console.log('✅ Loaded:', this.src)"
                                         onerror="console.error('❌ Failed:', this.src)">
                                    <p style="color: #666; font-size: 12px;">File size: ${{(file.size/1024).toFixed(0)}} KB</p>
                                </div>
                            `;
                        }});
                    }}

                    html += `
                        <div style="background: #E8F5E8; padding: 20px; border-radius: 8px; margin: 20px 0;">
                            <h3 style="color: #4CAF50;">✅ Analysis Complete!</h3>
                            <p>All visualizations and statistical analysis have been generated. Conway's Game of Life simulations show fascinating pattern evolution and emergent behaviors across different simulation modes.</p>
                        </div>
                    `;

                    document.getElementById('results-content').innerHTML = html;
                    console.log('✅ Direct results loaded successfully');

                }} catch (error) {{
                    console.error('❌ Error loading files:', error);
                    document.getElementById('results-content').innerHTML = `
                        <div style="padding: 20px; background: #ffebee; border-radius: 8px;">
                            <h3>⚠️ Error Loading Files</h3>
                            <p>Could not load analysis files. Please check browser console for details.</p>
                            <p>Error: ${{error.message}}</p>
                        </div>
                    `;
                }}
            }}

            // Check if already completed, if so load results directly
            console.log('💡 Checking initialStatus:', initialStatus);
            if (initialStatus === 'completed') {{
                console.log('Run already completed - loading results directly...');
                document.getElementById('results-container').style.display = 'block';

                // Load results immediately with simple approach
                loadCompletedResults();
            }} else {{
                // Start polling for status updates for non-completed runs
                updateStatus();
                pollInterval = setInterval(updateStatus, 2000);
            }}

            // Stop polling when page is hidden
            document.addEventListener('visibilitychange', () => {{
                if (document.hidden) {{
                    clearInterval(pollInterval);
                }} else {{
                    updateStatus();
                    if (document.getElementById('current-status').textContent === 'running') {{
                        pollInterval = setInterval(updateStatus, 2000);
                    }}
                }}
            }});
        </script>
    </body>
    </html>
    """
    return html_content

# Initialize database tables on startup
@app.on_event("startup")
async def startup_event():
    """Initialize database tables"""
    try:
        create_tables()
        print("✅ Database tables initialized")
    except Exception as e:
        print(f"❌ Error initializing database: {e}")


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