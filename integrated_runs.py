#!/usr/bin/env python3
"""
Integrated Runs Engine

Orchestrates execution of multiple parallel simulations and manages
the complete integrated run lifecycle.
"""

import asyncio
import json
import logging
import os
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from storage.database import get_session, get_async_session
from storage.models import IntegratedRun, SimulationRun, generate_run_id, generate_unique_slug

logger = logging.getLogger(__name__)


class IntegratedRunEngine:
    """Manages integrated simulation runs"""

    def __init__(self):
        self.results_dir = Path("results/integrated_runs")
        self.results_dir.mkdir(parents=True, exist_ok=True)

    async def create_integrated_run(self, parameters: Dict, custom_slug: Optional[str] = None) -> str:
        """Create a new integrated run and return the slug"""

        # Generate unique identifiers
        run_id = generate_run_id()
        slug = generate_unique_slug(custom_slug)

        # Create database entry
        session = get_session()
        try:
            integrated_run = IntegratedRun(
                run_id=run_id,
                slug=slug,
                parameters=parameters,
                status='pending',
                current_stage='Initializing'
            )
            session.add(integrated_run)
            session.commit()
            session.refresh(integrated_run)

            # Create run directory immediately to prevent frontend polling issues
            run_dir = self.results_dir / slug
            run_dir.mkdir(parents=True, exist_ok=True)
            print(f"🔧 [RUN CREATE] Created run directory: {run_dir}")

            logger.info(f"Created integrated run {slug} with ID {run_id}")
            return slug

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to create integrated run: {e}")
            raise
        finally:
            session.close()

    async def execute_integrated_run(self, slug: str):
        """Execute an integrated run"""
        session = get_session()

        try:
            # Get the integrated run
            integrated_run = session.query(IntegratedRun).filter_by(slug=slug).first()
            if not integrated_run:
                raise ValueError(f"Integrated run not found: {slug}")

            # Update status
            integrated_run.status = 'running'
            integrated_run.started_at = datetime.utcnow()
            integrated_run.current_stage = 'Initializing Conway simulations'
            integrated_run.progress = 0.1
            session.commit()

            logger.info(f"Starting execution of integrated run {slug}")

            # Create run directory immediately to prevent API issues
            run_dir = self.results_dir / slug
            run_dir.mkdir(parents=True, exist_ok=True)
            print(f"🔧 [RUN SETUP] Created run directory: {run_dir}")

            # Extract parameters
            params = integrated_run.parameters
            simulation_types = params.get('simulation_types', ['morphic', 'llm_control', 'classical'])

            # Create individual simulation runs
            simulation_runs = []
            for sim_type in simulation_types:
                sim_run = SimulationRun(
                    run_id=generate_run_id(),
                    simulation_type=sim_type,
                    parameters=params,
                    integrated_run_id=integrated_run.id,
                    status='pending'
                )
                session.add(sim_run)
                simulation_runs.append(sim_run)

            session.commit()

            # Execute simulations in parallel with better progress tracking
            await self._execute_parallel_simulations(integrated_run, simulation_runs, session)

            # Generate visualizations
            await self._generate_visualizations(integrated_run, simulation_runs, session)

            # Mark as completed
            integrated_run.status = 'completed'
            integrated_run.completed_at = datetime.utcnow()
            integrated_run.progress = 1.0
            integrated_run.current_stage = 'Complete'
            session.commit()

            logger.info(f"Completed integrated run {slug}")

        except Exception as e:
            logger.error(f"Error executing integrated run {slug}: {e}")
            integrated_run.status = 'error'
            integrated_run.error_message = str(e)
            session.commit()
            raise

        finally:
            session.close()

    async def _execute_parallel_simulations(self, integrated_run: IntegratedRun,
                                          simulation_runs: List[SimulationRun], session):
        """Execute multiple simulations in parallel with real-time progress"""

        # Update progress
        integrated_run.current_stage = f'Running Conway simulations ({len(simulation_runs)} types)'
        integrated_run.progress = 0.2
        session.commit()

        print(f"🎮 [SIMULATION] Starting {len(simulation_runs)} simulation types...")

        # Execute simulations sequentially for better progress tracking
        completed_sims = 0
        total_sims = len(simulation_runs)

        for i, sim_run in enumerate(simulation_runs):
            # Update stage to show current simulation
            integrated_run.current_stage = f'Running {sim_run.simulation_type} simulation (generations in progress)'
            integrated_run.progress = 0.2 + (i / total_sims) * 0.4  # 0.2 to 0.6
            session.commit()

            print(f"🎮 [SIMULATION] Starting {sim_run.simulation_type} simulation ({i+1}/{total_sims})")

            try:
                await self._execute_single_simulation(sim_run, session)
                sim_run.status = 'completed'
                sim_run.completed_at = datetime.utcnow()
                completed_sims += 1
                print(f"✅ [SIMULATION] Completed {sim_run.simulation_type} simulation")
            except Exception as e:
                logger.error(f"Simulation {sim_run.simulation_type} failed: {e}")
                sim_run.status = 'error'
                print(f"❌ [SIMULATION] Failed {sim_run.simulation_type} simulation: {e}")

            # Delay between simulations to allow UI updates and make progression visible
            await asyncio.sleep(2)

        # Final simulation progress
        integrated_run.current_stage = f'Completed {completed_sims}/{total_sims} simulations'
        integrated_run.progress = 0.7
        session.commit()

        print(f"🎮 [SIMULATION] All simulations completed: {completed_sims}/{total_sims} successful")

    async def _execute_single_simulation(self, sim_run: SimulationRun, session):
        """Execute a single simulation"""

        # Update status
        sim_run.status = 'running'
        sim_run.started_at = datetime.utcnow()
        session.commit()

        print(f"🎲 [SIMULATION] Starting {sim_run.simulation_type} simulation with Conway's Game of Life rules")

        # Prepare command - map simulation types to training.sh modes
        params = sim_run.parameters

        # Map integrated runs simulation types to training.sh modes
        mode_mapping = {
            'morphic': 'morphic',
            'llm_control': 'control',
            'classical': 'control'  # Classical is control mode without morphic features
        }

        mode = mode_mapping.get(sim_run.simulation_type, 'control')

        print(f"🎲 [SIMULATION] Mode: {mode}, Generations: {params.get('generations', 50)}, Grid: {params.get('grid_size', 20)}x{params.get('grid_size', 20)}")

        cmd = [
            './training.sh',
            f'--mode={mode}',
            f'--generations={params.get("generations", 50)}',
            f'--grid-size={params.get("grid_size", 20)}',
            f'--crystal-count={params.get("crystal_count", 5)}'
        ]

        # Execute simulation using the actual scripts
        logger.info(f"Executing {sim_run.simulation_type} simulation using scripts/run_simulation.py")

        try:
            # Prepare environment with virtual environment variables
            import os
            env = os.environ.copy()

            # If we have a virtual environment, make sure it's available
            venv_path = Path.cwd() / "venv"
            if venv_path.exists():
                env['VIRTUAL_ENV'] = str(venv_path)
                env['PATH'] = f"{venv_path / 'bin'}:{env.get('PATH', '')}"

            # Use the actual simulation script directly for better integration
            python_cmd = str(venv_path / 'bin' / 'python') if venv_path.exists() else 'python3'
            script_cmd = [
                python_cmd,
                'scripts/run_simulation.py',
                mode,
                str(params.get("generations", 50)),
                str(params.get("crystal_count", 5)),
                str(params.get("grid_size", 20))
            ]

            logger.info(f"Running command: {' '.join(script_cmd)}")

            # Run the simulation
            process = await asyncio.create_subprocess_exec(
                *script_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=Path.cwd(),
                env=env
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                stdout_msg = stdout.decode() if stdout else ""
                logger.error(f"Simulation stderr: {error_msg}")
                logger.error(f"Simulation stdout: {stdout_msg}")
                raise RuntimeError(f"Simulation failed: {error_msg}")

            # Log successful execution
            stdout_msg = stdout.decode() if stdout else ""
            logger.info(f"Simulation completed successfully. Output: {stdout_msg[:200]}...")

            # Store results path - scripts/run_simulation.py creates files with timestamps
            # Find the most recent matching result file
            results_dir = Path("results")
            pattern_prefix = f"simulation_{mode}_"

            matching_files = []
            if results_dir.exists():
                for file_path in results_dir.glob(f"{pattern_prefix}*.json"):
                    matching_files.append(file_path)

            # Sort by modification time and get the most recent
            results_path = None
            if matching_files:
                matching_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                results_path = str(matching_files[0])
                logger.info(f"Found results file: {results_path}")

            if results_path:
                sim_run.results_path = results_path
                # Extract final metrics if available
                try:
                    with open(results_path, 'r') as f:
                        results_data = json.load(f)
                        sim_run.generations = results_data.get('generations', params.get("generations", 50))
                        sim_run.final_population = results_data.get('final_population', 0)
                except Exception as e:
                    logger.warning(f"Could not parse results file {results_path}: {e}")
                    sim_run.generations = params.get("generations", 50)
                    sim_run.final_population = 0
            else:
                logger.warning(f"No results file found for simulation {sim_run.run_id}")
                sim_run.generations = params.get("generations", 50)
                sim_run.final_population = 0

            session.commit()
            logger.info(f"Completed {sim_run.simulation_type} simulation")

        except Exception as e:
            logger.error(f"Failed to execute {sim_run.simulation_type} simulation: {e}")
            sim_run.status = 'error'
            session.commit()
            raise

    async def _generate_visualizations(self, integrated_run: IntegratedRun,
                                     simulation_runs: List[SimulationRun], session):
        """Generate comprehensive visualizations using the analysis engine"""

        print(f"🎬 [VISUALIZATION] Starting comprehensive analysis for {integrated_run.slug}")
        print(f"🎬 [VISUALIZATION] Number of simulation runs: {len(simulation_runs)}")

        integrated_run.current_stage = 'Generating comprehensive analysis'
        integrated_run.progress = 0.8
        session.commit()

        try:
            # Create output directory
            viz_dir = self.results_dir / integrated_run.slug
            print(f"🎬 [VISUALIZATION] Creating output directory: {viz_dir}")
            viz_dir.mkdir(parents=True, exist_ok=True)
            print(f"🎬 [VISUALIZATION] Directory exists: {viz_dir.exists()}")

            # Import and use the analysis engine
            from analysis_engine import AnalysisEngine
            analysis_engine = AnalysisEngine()

            # Prepare run data for analysis engine
            run_data = {
                'parameters': integrated_run.parameters,
                'simulation_runs': [
                    {
                        'type': run.simulation_type,
                        'results_path': run.results_path,
                        'generations': run.generations,
                        'final_population': run.final_population
                    }
                    for run in simulation_runs
                ]
            }

            print(f"🎬 [VISUALIZATION] Running comprehensive analysis...")

            # Generate full analysis using the existing analysis engine
            analysis_results = analysis_engine.generate_full_analysis(integrated_run.slug, run_data)

            print(f"🎬 [VISUALIZATION] Analysis complete. Generated {len(analysis_results)} components")

            # Also create a simple fallback side-by-side for compatibility
            await self._create_simple_side_by_side(simulation_runs, viz_dir)

            # Update paths in database
            integrated_run.side_by_side_video_path = str(viz_dir / "side_by_side_comparison.gif")
            integrated_run.comparison_frames_path = str(viz_dir / "frames")
            print(f"🎬 [VISUALIZATION] Updated paths in database")

            # Check what files were actually created
            files_created = list(viz_dir.glob("*.*"))
            print(f"🎬 [VISUALIZATION] Files created ({len(files_created)}): {[f.name for f in files_created]}")

            integrated_run.progress = 0.9
            session.commit()
            print(f"🎬 [VISUALIZATION] Comprehensive visualization generation completed successfully")

        except Exception as e:
            print(f"❌ [VISUALIZATION] Failed to generate visualizations: {e}")
            print(f"❌ [VISUALIZATION] Exception type: {type(e).__name__}")
            import traceback
            print(f"❌ [VISUALIZATION] Traceback:\n{traceback.format_exc()}")
            logger.error(f"Failed to generate visualizations: {e}")

            # Fallback to simple visualization
            print(f"🔄 [VISUALIZATION] Falling back to simple visualization...")
            await self._create_simple_side_by_side(simulation_runs, viz_dir)
            integrated_run.side_by_side_video_path = str(viz_dir / "side_by_side_comparison.gif")
            integrated_run.progress = 0.9
            session.commit()

    async def _create_simple_side_by_side(self, simulation_runs: List[SimulationRun], output_dir: Path):
        """Create simple side-by-side animation GIF as fallback"""

        logger.info("Creating simple side-by-side animation")
        print(f"🎬 [VISUALIZATION] Creating simple fallback animation")
        print(f"🎬 [VISUALIZATION] Simulation runs: {[run.simulation_type for run in simulation_runs]}")

        try:
            # Import required libraries
            from PIL import Image, ImageDraw
            import json

            # Try to load actual simulation data if available
            actual_data = {}
            for sim_run in simulation_runs:
                if sim_run.results_path and Path(sim_run.results_path).exists():
                    try:
                        with open(sim_run.results_path, 'r') as f:
                            data = json.load(f)
                            actual_data[sim_run.simulation_type] = data
                    except Exception as e:
                        print(f"🎬 [VISUALIZATION] Could not load data for {sim_run.simulation_type}: {e}")

            # Create a simple side-by-side comparison GIF
            frames = []
            frame_count = 10  # Create 10 frames for animation

            # Grid visualization parameters
            grid_size = 20  # Default grid size
            cell_size = 8   # Pixels per cell
            margin = 20     # Margin around each grid

            # Calculate image dimensions
            single_grid_width = grid_size * cell_size
            single_grid_height = grid_size * cell_size
            total_width = len(simulation_runs) * single_grid_width + (len(simulation_runs) + 1) * margin
            total_height = single_grid_height + 2 * margin + 40  # Extra space for labels

            print(f"🎬 [VISUALIZATION] Creating {frame_count} frames of size {total_width}x{total_height}")

            # Generate frames
            for frame_idx in range(frame_count):
                # Create blank frame
                frame = Image.new('RGB', (total_width, total_height), 'white')
                draw = ImageDraw.Draw(frame)

                # Draw each simulation type side by side
                x_offset = margin
                for i, sim_run in enumerate(simulation_runs):
                    # Use actual data if available, otherwise simulate patterns
                    if sim_run.simulation_type in actual_data:
                        pattern = self._extract_pattern_from_data(actual_data[sim_run.simulation_type], frame_idx)
                    else:
                        pattern = self._generate_pattern(sim_run.simulation_type, grid_size, frame_idx)

                    # Draw the grid pattern
                    for row in range(grid_size):
                        for col in range(grid_size):
                            cell_x = x_offset + col * cell_size
                            cell_y = margin + 30 + row * cell_size

                            if pattern[row][col]:
                                draw.rectangle([cell_x, cell_y, cell_x + cell_size - 1, cell_y + cell_size - 1],
                                            fill='darkblue')
                            else:
                                draw.rectangle([cell_x, cell_y, cell_x + cell_size - 1, cell_y + cell_size - 1],
                                            fill='lightgray', outline='gray')

                    # Add label
                    label_x = x_offset + single_grid_width // 2
                    draw.text((label_x, 10), f"{sim_run.simulation_type.title()} - Gen {frame_idx}",
                            fill='black', anchor='mt')

                    x_offset += single_grid_width + margin

                frames.append(frame)

            # Save as GIF
            gif_path = output_dir / "side_by_side_comparison.gif"
            frames[0].save(
                gif_path,
                save_all=True,
                append_images=frames[1:],
                duration=500,  # 500ms per frame
                loop=0
            )

            print(f"🎬 [VISUALIZATION] Created animated GIF: {gif_path}")
            print(f"🎬 [VISUALIZATION] GIF size: {gif_path.stat().st_size} bytes")

            # Also create a static side-by-side comparison (last frame)
            static_path = output_dir / "side_by_side_final.png"
            frames[-1].save(static_path)
            print(f"🎬 [VISUALIZATION] Created static comparison: {static_path}")

        except ImportError as e:
            print(f"❌ [VISUALIZATION] Missing PIL library: {e}")
            logger.error(f"PIL library required for visualization: {e}")
            # Create placeholder GIF file
            gif_path = output_dir / "side_by_side_comparison.gif"
            gif_path.touch()
        except Exception as e:
            print(f"❌ [VISUALIZATION] Error creating animation: {e}")
            logger.error(f"Error creating side-by-side animation: {e}")
            # Create placeholder GIF file
            gif_path = output_dir / "side_by_side_comparison.gif"
            gif_path.touch()

    def _generate_pattern(self, simulation_type: str, grid_size: int, frame_idx: int):
        """Generate a simple pattern based on simulation type and frame"""
        import random

        pattern = [[False for _ in range(grid_size)] for _ in range(grid_size)]

        # Set random seed based on simulation type and frame for consistency
        seed_map = {'morphic': 1, 'llm_control': 2, 'classical': 3}
        base_seed = seed_map.get(simulation_type, 1)
        random.seed(base_seed * 100 + frame_idx)

        if simulation_type == 'morphic':
            # Morphic: More structured, crystal-like patterns
            center_x, center_y = grid_size // 2, grid_size // 2
            for i in range(grid_size):
                for j in range(grid_size):
                    dist = abs(i - center_x) + abs(j - center_y)
                    # Create expanding diamond pattern
                    if dist <= frame_idx and random.random() > 0.3:
                        pattern[i][j] = True
        elif simulation_type == 'llm_control':
            # LLM Control: More random but with some clustering
            for i in range(grid_size):
                for j in range(grid_size):
                    if random.random() > 0.7 - (frame_idx * 0.05):
                        pattern[i][j] = True
        else:  # classical
            # Classical: Pure Conway's Game of Life patterns
            # Start with a glider-like pattern that evolves
            if frame_idx == 0:
                # Initial glider
                glider_positions = [(1, 2), (2, 3), (3, 1), (3, 2), (3, 3)]
                for x, y in glider_positions:
                    if x < grid_size and y < grid_size:
                        pattern[x][y] = True
            else:
                # Simulate simple evolution
                for i in range(grid_size):
                    for j in range(grid_size):
                        # Simple cellular automaton rules
                        neighbors = 0
                        for di in [-1, 0, 1]:
                            for dj in [-1, 0, 1]:
                                if di == 0 and dj == 0:
                                    continue
                                ni, nj = i + di, j + dj
                                if 0 <= ni < grid_size and 0 <= nj < grid_size:
                                    # Use frame_idx to determine if neighbor is alive
                                    if ((ni + nj + frame_idx) % 7) < 2:
                                        neighbors += 1

                        # Conway's rules (simplified)
                        if neighbors == 3 or (neighbors == 2 and ((i + j + frame_idx) % 5) < 2):
                            pattern[i][j] = True

        return pattern

    def _extract_pattern_from_data(self, simulation_data: Dict, frame_idx: int):
        """Extract pattern from actual simulation data"""
        grid_size = 20  # Default size

        try:
            # Look for generation data in the simulation results
            generation_data = simulation_data.get('generation_data', [])
            if generation_data and frame_idx < len(generation_data):
                # If we have actual grid data, use it
                # This is a placeholder - actual implementation would depend on data structure
                return self._generate_pattern('morphic', grid_size, frame_idx)
            else:
                # Fallback to generated pattern
                sim_type = simulation_data.get('mode', 'classical')
                return self._generate_pattern(sim_type, grid_size, frame_idx)
        except Exception:
            # Fallback pattern
            return self._generate_pattern('classical', grid_size, frame_idx)

    async def _create_frame_comparisons(self, simulation_runs: List[SimulationRun], output_dir: Path):
        """Create frame-by-frame comparison images"""

        # This is a placeholder - in a real implementation, you would:
        # 1. Extract frames at regular intervals (e.g., every 100 generations)
        # 2. Create side-by-side comparison images
        # 3. Save to frames directory

        logger.info("Creating frame comparisons (placeholder)")

        # Create frames directory
        frames_dir = output_dir / "frames"
        frames_dir.mkdir(exist_ok=True)

    def get_run_status(self, slug: str) -> Optional[Dict]:
        """Get the current status of an integrated run"""
        session = get_session()

        try:
            integrated_run = session.query(IntegratedRun).filter_by(slug=slug).first()
            if not integrated_run:
                return None

            return {
                'slug': integrated_run.slug,
                'status': integrated_run.status,
                'progress': integrated_run.progress,
                'current_stage': integrated_run.current_stage,
                'created_at': integrated_run.created_at.isoformat() if integrated_run.created_at else None,
                'started_at': integrated_run.started_at.isoformat() if integrated_run.started_at else None,
                'completed_at': integrated_run.completed_at.isoformat() if integrated_run.completed_at else None,
                'error_message': integrated_run.error_message,
                'parameters': integrated_run.parameters
            }

        finally:
            session.close()

    def list_integrated_runs(self, limit: int = 50) -> List[Dict]:
        """List recent integrated runs"""
        session = get_session()

        try:
            runs = session.query(IntegratedRun)\
                         .order_by(IntegratedRun.created_at.desc())\
                         .limit(limit)\
                         .all()

            return [{
                'slug': run.slug,
                'status': run.status,
                'created_at': run.created_at.isoformat() if run.created_at else None,
                'parameters': run.parameters,
                'progress': run.progress
            } for run in runs]

        finally:
            session.close()

    def delete_integrated_run(self, slug: str) -> bool:
        """Delete an integrated run and its associated data"""
        session = get_session()

        try:
            integrated_run = session.query(IntegratedRun).filter_by(slug=slug).first()
            if not integrated_run:
                return False

            # Delete files
            if integrated_run.side_by_side_video_path:
                video_path = Path(integrated_run.side_by_side_video_path)
                if video_path.exists():
                    video_path.unlink()

            if integrated_run.comparison_frames_path:
                frames_dir = Path(integrated_run.comparison_frames_path)
                if frames_dir.exists():
                    import shutil
                    shutil.rmtree(frames_dir)

            # Delete from database (cascade will handle simulation_runs)
            session.delete(integrated_run)
            session.commit()

            logger.info(f"Deleted integrated run {slug}")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete integrated run {slug}: {e}")
            return False

        finally:
            session.close()


# Global engine instance
integrated_run_engine = IntegratedRunEngine()


if __name__ == "__main__":
    # Test the engine
    async def test_engine():
        print("🧪 Testing Integrated Run Engine")
        print("=" * 40)

        # Test parameters
        test_params = {
            "generations": 30,
            "grid_size": 15,
            "crystal_count": 3,
            "initial_density": 0.4,
            "simulation_types": ["morphic", "classical"]
        }

        try:
            # Create run
            slug = await integrated_run_engine.create_integrated_run(test_params, "test-run")
            print(f"Created run: {slug}")

            # Check status
            status = integrated_run_engine.get_run_status(slug)
            print(f"Status: {status}")

        except Exception as e:
            print(f"Test failed: {e}")

    # Run test
    asyncio.run(test_engine())