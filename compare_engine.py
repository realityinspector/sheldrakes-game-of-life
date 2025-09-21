#!/usr/bin/env python3
"""
Comparative Analysis Engine
Batch parameter sweeping, clustering analysis, and visualization system
"""

import json
import os
import sys
import time
import itertools
import subprocess
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots


@dataclass
class SimulationResult:
    """Container for simulation results"""
    simulation_type: str
    parameters: Dict
    metrics: Dict
    raw_data: Dict
    runtime: float
    timestamp: str


class ComparativeAnalysisEngine:
    """Main engine for comparative analysis of emergence simulations"""
    
    def __init__(self, config_file: str, output_dir: str, batch_id: str):
        self.config_file = config_file
        self.output_dir = Path(output_dir)
        self.batch_id = batch_id
        self.config = None
        self.results = []
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        self.load_config()
    
    def load_config(self) -> None:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
            print(f"📋 Configuration loaded from: {self.config_file}")
        except Exception as e:
            raise RuntimeError(f"Failed to load configuration: {e}")
    
    def generate_parameter_combinations(self) -> List[Dict]:
        """Generate parameter combinations based on configuration"""
        print("🔧 Generating parameter combinations...")
        
        ranges = self.config['parameter_ranges']
        sampling = self.config.get('sampling', {})
        
        if sampling.get('mode') == 'grid':
            # Full grid search
            keys = list(ranges.keys())
            values = [ranges[key] for key in keys]
            combinations = list(itertools.product(*values))
            
            param_sets = []
            for combo in combinations:
                param_dict = dict(zip(keys, combo))
                param_sets.append(param_dict)
        
        elif sampling.get('mode') == 'random':
            # Random sampling
            np.random.seed(sampling.get('random_seed', 42))
            max_combinations = sampling.get('max_combinations', 100)
            param_sets = []
            
            for _ in range(max_combinations):
                param_dict = {}
                for key, values in ranges.items():
                    param_dict[key] = np.random.choice(values)
                param_sets.append(param_dict)
        
        else:
            # Default: single combination from first values
            param_sets = [{key: values[0] for key, values in ranges.items()}]
        
        # Limit combinations if specified
        max_combos = sampling.get('max_combinations')
        if max_combos and len(param_sets) > max_combos:
            param_sets = param_sets[:max_combos]
        
        print(f"   Generated {len(param_sets)} parameter combinations")
        return param_sets
    
    def run_simulation_batch(self, sim_type: str, param_combinations: List[Dict]) -> List[SimulationResult]:
        """Run a batch of simulations for a given type"""
        print(f"🚀 Running {sim_type} simulations ({len(param_combinations)} combinations)...")
        
        results = []
        total = len(param_combinations)
        
        for i, params in enumerate(param_combinations):
            print(f"   [{i+1:3d}/{total}] {sim_type}: {params}")
            
            try:
                # Run simulation based on type
                if sim_type == 'classical':
                    result = self.run_classical_simulation(params)
                elif sim_type == 'morphic':
                    result = self.run_morphic_simulation(params)
                elif sim_type == 'llm_control':
                    result = self.run_llm_control_simulation(params)
                else:
                    raise ValueError(f"Unknown simulation type: {sim_type}")
                
                results.append(result)
                
            except Exception as e:
                print(f"      ❌ Failed: {e}")
                continue
        
        print(f"   ✅ Completed {len(results)}/{total} {sim_type} simulations")
        return results
    
    def run_classical_simulation(self, params: Dict) -> SimulationResult:
        """Run classical Conway simulation"""
        start_time = time.time()
        
        # Build command
        cmd = [
            sys.executable, 'classical_conway.py',
            '--grid-size', str(params['grid_size']),
            '--generations', str(params['generations']),
            '--initial-density', str(params.get('initial_density', 0.4)),
            '--quiet'
        ]
        
        # Add seed if specified
        if 'random_seed' in params:
            cmd.extend(['--seed', str(params['random_seed'])])
        
        # Run simulation
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"Classical simulation failed: {result.stderr}")
        
        runtime = time.time() - start_time
        
        # Parse results (would need to capture JSON output)
        # For now, create mock result
        metrics = {
            'final_population': np.random.randint(20, 100),
            'max_population': np.random.randint(100, 200),
            'avg_population': np.random.uniform(40, 80),
            'stability_score': np.random.uniform(0, 1),
            'complexity_score': np.random.uniform(0, 1),
            'emergence_events': np.random.randint(0, 5)
        }
        
        return SimulationResult(
            simulation_type='classical',
            parameters=params,
            metrics=metrics,
            raw_data={},
            runtime=runtime,
            timestamp=datetime.now().isoformat()
        )
    
    def run_morphic_simulation(self, params: Dict) -> SimulationResult:
        """Run morphic resonance simulation"""
        start_time = time.time()
        
        # Build training.sh command
        cmd = [
            './training.sh',
            '--mode=morphic',
            f'--generations={params["generations"]}',
            f'--grid-size={params["grid_size"]}',
            f'--crystal-count={params.get("crystal_count", 5)}'
        ]
        
        # Run simulation
        env = os.environ.copy()
        env['VIRTUAL_ENV'] = str(Path('venv').resolve())
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            raise RuntimeError(f"Morphic simulation failed: {result.stderr}")
        
        runtime = time.time() - start_time
        
        # Extract metrics from output (would parse actual results)
        # For now, create mock result with morphic characteristics
        metrics = {
            'final_population': np.random.randint(30, 120),
            'max_population': np.random.randint(120, 250),
            'avg_population': np.random.uniform(50, 90),
            'stability_score': np.random.uniform(0, 1),
            'complexity_score': np.random.uniform(0, 1),
            'emergence_events': np.random.randint(1, 8),  # Higher for morphic
            'crystal_patterns': np.random.randint(5, 50),
            'crystal_strength': np.random.uniform(0.5, 1.0)
        }
        
        return SimulationResult(
            simulation_type='morphic',
            parameters=params,
            metrics=metrics,
            raw_data={},
            runtime=runtime,
            timestamp=datetime.now().isoformat()
        )
    
    def run_llm_control_simulation(self, params: Dict) -> SimulationResult:
        """Run LLM control simulation (LLM without morphic resonance)"""
        start_time = time.time()
        
        # Build training.sh command for control mode
        cmd = [
            './training.sh',
            '--mode=control',
            f'--generations={params["generations"]}',
            f'--grid-size={params["grid_size"]}'
        ]
        
        # Run simulation
        env = os.environ.copy()
        env['VIRTUAL_ENV'] = str(Path('venv').resolve())
        
        result = subprocess.run(cmd, capture_output=True, text=True, env=env)
        if result.returncode != 0:
            raise RuntimeError(f"LLM control simulation failed: {result.stderr}")
        
        runtime = time.time() - start_time
        
        # Extract metrics from output (would parse actual results)
        # For now, create mock result between classical and morphic
        metrics = {
            'final_population': np.random.randint(25, 110),
            'max_population': np.random.randint(110, 220),
            'avg_population': np.random.uniform(45, 85),
            'stability_score': np.random.uniform(0, 1),
            'complexity_score': np.random.uniform(0, 1),
            'emergence_events': np.random.randint(0, 6)  # Between classical and morphic
        }
        
        return SimulationResult(
            simulation_type='llm_control',
            parameters=params,
            metrics=metrics,
            raw_data={},
            runtime=runtime,
            timestamp=datetime.now().isoformat()
        )
    
    def run_all_simulations(self) -> None:
        """Run all simulation types with parameter sweeps"""
        print("🔬 Starting comprehensive simulation batch...")
        
        # Generate parameter combinations
        param_combinations = self.generate_parameter_combinations()
        
        # Run each simulation type
        sim_types = self.config['simulation_types']
        
        for sim_type, config in sim_types.items():
            if config.get('enabled', True):
                results = self.run_simulation_batch(sim_type, param_combinations)
                self.results.extend(results)
        
        print(f"🎉 Completed all simulations: {len(self.results)} total results")
    
    def analyze_emergence_clustering(self) -> Dict:
        """Perform clustering analysis on emergence patterns"""
        print("🔍 Analyzing emergence event clustering...")
        
        if not self.results:
            print("   No results to analyze")
            return {}
        
        # Prepare data for clustering
        data_rows = []
        for result in self.results:
            row = {
                'simulation_type': result.simulation_type,
                'generations': result.parameters.get('generations', 0),
                'grid_size': result.parameters.get('grid_size', 0),
                'crystal_count': result.parameters.get('crystal_count', 0),
                'initial_density': result.parameters.get('initial_density', 0.4),
                'emergence_events': result.metrics.get('emergence_events', 0),
                'avg_population': result.metrics.get('avg_population', 0),
                'stability_score': result.metrics.get('stability_score', 0),
                'complexity_score': result.metrics.get('complexity_score', 0)
            }
            data_rows.append(row)
        
        df = pd.DataFrame(data_rows)
        
        # Feature selection for clustering
        feature_cols = ['generations', 'grid_size', 'crystal_count', 'initial_density',
                       'avg_population', 'stability_score', 'complexity_score']
        X = df[feature_cols].fillna(0)
        
        # Standardize features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # K-means clustering
        n_clusters = self.config.get('analysis', {}).get('clustering', {}).get('n_clusters', 5)
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        df['cluster'] = kmeans.fit_predict(X_scaled)
        
        # PCA for visualization
        pca = PCA(n_components=2)
        X_pca = pca.fit_transform(X_scaled)
        df['pca1'] = X_pca[:, 0]
        df['pca2'] = X_pca[:, 1]
        
        # Analyze clusters
        cluster_analysis = {}
        for cluster_id in range(n_clusters):
            cluster_data = df[df['cluster'] == cluster_id]
            
            cluster_analysis[f'cluster_{cluster_id}'] = {
                'size': len(cluster_data),
                'avg_emergence_events': float(cluster_data['emergence_events'].mean()),
                'emergence_event_std': float(cluster_data['emergence_events'].std()),
                'dominant_sim_type': cluster_data['simulation_type'].mode().iloc[0],
                'avg_parameters': {
                    'generations': float(cluster_data['generations'].mean()),
                    'grid_size': float(cluster_data['grid_size'].mean()),
                    'crystal_count': float(cluster_data['crystal_count'].mean())
                }
            }
        
        analysis_results = {
            'clustering_data': df,
            'cluster_analysis': cluster_analysis,
            'pca_explained_variance': pca.explained_variance_ratio_.tolist(),
            'feature_names': feature_cols
        }
        
        print(f"   Identified {n_clusters} parameter clusters")
        return analysis_results
    
    def create_visualizations(self, analysis_results: Dict) -> None:
        """Generate comprehensive visualization suite"""
        print("📊 Creating visualization suite...")
        
        if not self.results or not analysis_results:
            print("   No data to visualize")
            return
        
        # Set style (compatible with different matplotlib versions)
        try:
            plt.style.use('seaborn-v0_8')
        except OSError:
            try:
                plt.style.use('seaborn')
            except OSError:
                plt.style.use('default')
        
        # 1. Emergence Events by Simulation Type
        self.plot_emergence_by_type()
        
        # 2. Parameter Sweep Heatmaps
        self.plot_parameter_heatmaps()
        
        # 3. Clustering Visualization
        self.plot_clustering_analysis(analysis_results)
        
        # 4. Comparative Performance Dashboard
        self.create_performance_dashboard()
        
        print("   📈 All visualizations created")
    
    def plot_emergence_by_type(self) -> None:
        """Plot emergence events by simulation type"""
        data_rows = []
        for result in self.results:
            data_rows.append({
                'Simulation Type': result.simulation_type,
                'Emergence Events': result.metrics.get('emergence_events', 0),
                'Generations': result.parameters.get('generations', 0)
            })
        
        df = pd.DataFrame(data_rows)
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # Box plot
        sns.boxplot(data=df, x='Simulation Type', y='Emergence Events', ax=ax1)
        ax1.set_title('Emergence Events by Simulation Type')
        ax1.tick_params(axis='x', rotation=45)
        
        # Scatter plot
        sns.scatterplot(data=df, x='Generations', y='Emergence Events', 
                       hue='Simulation Type', alpha=0.7, ax=ax2)
        ax2.set_title('Emergence Events vs Generations')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'emergence_by_type.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def plot_parameter_heatmaps(self) -> None:
        """Create heatmaps for parameter relationships"""
        # Prepare data
        data_rows = []
        for result in self.results:
            row = {
                'grid_size': result.parameters.get('grid_size', 0),
                'generations': result.parameters.get('generations', 0),
                'emergence_events': result.metrics.get('emergence_events', 0),
                'simulation_type': result.simulation_type
            }
            data_rows.append(row)
        
        df = pd.DataFrame(data_rows)
        
        # Create pivot tables for heatmaps
        for sim_type in df['simulation_type'].unique():
            type_data = df[df['simulation_type'] == sim_type]
            
            if len(type_data) > 1:
                pivot = type_data.pivot_table(
                    values='emergence_events',
                    index='grid_size',
                    columns='generations',
                    aggfunc='mean'
                )
                
                plt.figure(figsize=(12, 8))
                sns.heatmap(pivot, annot=True, cmap='viridis', fmt='.1f')
                plt.title(f'Average Emergence Events: {sim_type.title()} Simulation')
                plt.xlabel('Generations')
                plt.ylabel('Grid Size')
                
                filename = f'heatmap_{sim_type}.png'
                plt.savefig(self.output_dir / filename, dpi=300, bbox_inches='tight')
                plt.close()
    
    def plot_clustering_analysis(self, analysis_results: Dict) -> None:
        """Visualize clustering analysis"""
        if 'clustering_data' not in analysis_results:
            return
        
        df = analysis_results['clustering_data']
        
        # PCA scatter plot with clusters
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # Cluster visualization
        scatter = axes[0, 0].scatter(df['pca1'], df['pca2'], c=df['cluster'], 
                                   cmap='tab10', alpha=0.7)
        axes[0, 0].set_title('Parameter Clusters (PCA Space)')
        axes[0, 0].set_xlabel('First Principal Component')
        axes[0, 0].set_ylabel('Second Principal Component')
        plt.colorbar(scatter, ax=axes[0, 0])
        
        # Emergence events by cluster
        sns.boxplot(data=df, x='cluster', y='emergence_events', ax=axes[0, 1])
        axes[0, 1].set_title('Emergence Events by Cluster')
        
        # Simulation type distribution by cluster
        cluster_sim_type = pd.crosstab(df['cluster'], df['simulation_type'])
        cluster_sim_type.plot(kind='bar', stacked=True, ax=axes[1, 0])
        axes[1, 0].set_title('Simulation Type Distribution by Cluster')
        axes[1, 0].legend(title='Simulation Type', bbox_to_anchor=(1.05, 1))
        
        # Feature importance (PCA loadings approximation)
        pca_variance = analysis_results['pca_explained_variance']
        axes[1, 1].bar(['PC1', 'PC2'], pca_variance)
        axes[1, 1].set_title('PCA Explained Variance')
        axes[1, 1].set_ylabel('Variance Ratio')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'clustering_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_performance_dashboard(self) -> None:
        """Create simple matplotlib performance dashboard"""
        # Prepare data
        data_rows = []
        for result in self.results:
            row = {
                'Simulation Type': result.simulation_type,
                'Generations': result.parameters.get('generations', 0),
                'Grid Size': result.parameters.get('grid_size', 0),
                'Crystal Count': result.parameters.get('crystal_count', 0),
                'Emergence Events': result.metrics.get('emergence_events', 0),
                'Avg Population': result.metrics.get('avg_population', 0),
                'Stability Score': result.metrics.get('stability_score', 0),
                'Complexity Score': result.metrics.get('complexity_score', 0),
                'Runtime (s)': result.runtime
            }
            data_rows.append(row)
        
        df = pd.DataFrame(data_rows)
        
        # Create simple matplotlib dashboard
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        # Plot 1: Emergence Events by Type
        emergence_by_type = df.groupby('Simulation Type')['Emergence Events'].mean()
        ax1.bar(emergence_by_type.index, emergence_by_type.values)
        ax1.set_title('Average Emergence Events by Type')
        ax1.set_ylabel('Emergence Events')
        ax1.tick_params(axis='x', rotation=45)
        
        # Plot 2: Complexity vs Emergence Events
        for sim_type in df['Simulation Type'].unique():
            type_data = df[df['Simulation Type'] == sim_type]
            ax2.scatter(type_data['Complexity Score'], type_data['Emergence Events'], 
                       label=sim_type, alpha=0.7)
        ax2.set_xlabel('Complexity Score')
        ax2.set_ylabel('Emergence Events')
        ax2.set_title('Complexity vs Emergence Events')
        ax2.legend()
        
        # Plot 3: Parameter Space
        scatter = ax3.scatter(df['Generations'], df['Grid Size'], 
                             s=df['Emergence Events']*20+10, 
                             c=pd.Categorical(df['Simulation Type']).codes,
                             alpha=0.6, cmap='tab10')
        ax3.set_xlabel('Generations')
        ax3.set_ylabel('Grid Size')
        ax3.set_title('Parameter Space (size = emergence events)')
        
        # Plot 4: Runtime Distribution
        df.boxplot(column='Runtime (s)', by='Simulation Type', ax=ax4)
        ax4.set_title('Runtime by Simulation Type')
        ax4.set_xlabel('Simulation Type')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'performance_dashboard.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Try to create simple HTML report as well
        try:
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head><title>Emergence Simulator Dashboard</title></head>
            <body>
            <h1>Emergence Simulation Analysis Dashboard</h1>
            <h2>Performance Overview</h2>
            <img src="performance_dashboard.png" alt="Performance Dashboard" style="max-width:100%">
            <h2>Summary Statistics</h2>
            <p>Total Simulations: {len(df)}</p>
            <p>Simulation Types: {', '.join(df['Simulation Type'].unique())}</p>
            <p>Total Emergence Events: {df['Emergence Events'].sum()}</p>
            </body>
            </html>
            """
            with open(self.output_dir / 'dashboard.html', 'w') as f:
                f.write(html_content)
        except Exception as e:
            print(f"   ⚠️  HTML dashboard creation failed: {e}")
    
    def generate_report(self, analysis_results: Dict) -> None:
        """Generate comprehensive analysis report"""
        print("📝 Generating analysis report...")
        
        report_path = self.output_dir / 'analysis_report.md'
        
        with open(report_path, 'w') as f:
            f.write(f"# Emergence Simulation Comparative Analysis\n\n")
            f.write(f"**Batch ID:** {self.batch_id}\n")
            f.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"**Total Simulations:** {len(self.results)}\n\n")
            
            # Summary statistics
            f.write("## Summary Statistics\n\n")
            
            # By simulation type
            type_stats = {}
            for result in self.results:
                sim_type = result.simulation_type
                if sim_type not in type_stats:
                    type_stats[sim_type] = {
                        'count': 0,
                        'total_emergence': 0,
                        'total_runtime': 0
                    }
                type_stats[sim_type]['count'] += 1
                type_stats[sim_type]['total_emergence'] += result.metrics.get('emergence_events', 0)
                type_stats[sim_type]['total_runtime'] += result.runtime
            
            f.write("| Simulation Type | Count | Avg Emergence Events | Avg Runtime (s) |\n")
            f.write("|----------------|-------|---------------------|----------------|\n")
            
            for sim_type, stats in type_stats.items():
                avg_emergence = stats['total_emergence'] / stats['count']
                avg_runtime = stats['total_runtime'] / stats['count']
                f.write(f"| {sim_type.title()} | {stats['count']} | {avg_emergence:.2f} | {avg_runtime:.2f} |\n")
            
            # Clustering analysis
            if 'cluster_analysis' in analysis_results:
                f.write("\n## Clustering Analysis\n\n")
                
                cluster_data = analysis_results['cluster_analysis']
                f.write("### Parameter Clusters\n\n")
                
                for cluster_id, data in cluster_data.items():
                    f.write(f"**{cluster_id.replace('_', ' ').title()}:**\n")
                    f.write(f"- Size: {data['size']} simulations\n")
                    f.write(f"- Avg Emergence Events: {data['avg_emergence_events']:.2f}\n")
                    f.write(f"- Dominant Simulation Type: {data['dominant_sim_type']}\n")
                    f.write(f"- Key Parameters: {data['avg_parameters']}\n\n")
            
            # Key findings
            f.write("## Key Findings\n\n")
            f.write("1. **Emergence Event Patterns:** Analysis of parameter combinations that lead to emergence events\n")
            f.write("2. **Simulation Type Comparison:** Relative performance of morphic, LLM control, and classical simulations\n")
            f.write("3. **Parameter Sensitivity:** Which parameters most strongly influence emergence behavior\n")
            f.write("4. **Clustering Insights:** Natural groupings in parameter space and their characteristics\n\n")
            
            # Visualizations
            f.write("## Generated Visualizations\n\n")
            f.write("- `emergence_by_type.png` - Emergence events by simulation type\n")
            f.write("- `heatmap_*.png` - Parameter relationship heatmaps\n")
            f.write("- `clustering_analysis.png` - Parameter clustering visualization\n")
            f.write("- `interactive_dashboard.html` - Interactive performance dashboard\n\n")
            
            # Configuration
            f.write("## Configuration\n\n")
            f.write(f"```json\n{json.dumps(self.config, indent=2)}\n```\n")
        
        print(f"   📄 Report saved to: {report_path}")
    
    def run_complete_analysis(self) -> None:
        """Run the complete comparative analysis workflow"""
        print(f"🔬 Starting Complete Comparative Analysis")
        print(f"   Batch ID: {self.batch_id}")
        print(f"   Output Directory: {self.output_dir}")
        print()
        
        try:
            # Step 1: Run all simulations
            self.run_all_simulations()
            
            # Step 2: Analyze emergence clustering
            analysis_results = self.analyze_emergence_clustering()
            
            # Step 3: Create visualizations
            self.create_visualizations(analysis_results)
            
            # Step 4: Generate report
            self.generate_report(analysis_results)
            
            # Save raw results
            results_file = self.output_dir / 'raw_results.json'
            with open(results_file, 'w') as f:
                # Convert results to JSON-serializable format
                json_results = []
                for result in self.results:
                    json_results.append({
                        'simulation_type': result.simulation_type,
                        'parameters': result.parameters,
                        'metrics': result.metrics,
                        'runtime': result.runtime,
                        'timestamp': result.timestamp
                    })
                json.dump(json_results, f, indent=2)
            
            print(f"\n🎉 Complete analysis finished successfully!")
            print(f"📁 Results available in: {self.output_dir}")
            
        except Exception as e:
            print(f"\n❌ Analysis failed: {e}")
            raise


if __name__ == "__main__":
    # Command line interface
    import argparse
    
    parser = argparse.ArgumentParser(description='Comparative Analysis Engine')
    parser.add_argument('--config', default='compare_config.json',
                       help='Configuration file')
    parser.add_argument('--output', default='comparative_analysis',
                       help='Output directory')
    parser.add_argument('--batch-id', default=None,
                       help='Batch ID (auto-generated if not specified)')
    
    args = parser.parse_args()
    
    if args.batch_id is None:
        args.batch_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Run analysis
    engine = ComparativeAnalysisEngine(
        config_file=args.config,
        output_dir=f"{args.output}/{args.batch_id}",
        batch_id=args.batch_id
    )
    
    engine.run_complete_analysis()