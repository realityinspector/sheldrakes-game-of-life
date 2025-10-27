# 🌊 Morphic Field Phenomenology Lab

**A computational laboratory for characterizing what morphic fields would look like if they existed**

Rather than trying to prove or disprove Rupert Sheldrake's morphic resonance hypothesis, this project takes a different approach: *What patterns and signatures would morphic fields produce in measurable systems?* Can we build detectors for those signatures?

## 🎯 Core Concept

This is **phenomenology, not metaphysics**. We're not claiming morphic fields are real—we're creating "toy morphic fields" in cellular automata to:

1. **Generate synthetic morphic data** with known parameters (field strength, decay rates, cross-system coupling)
2. **Characterize morphic signatures** (temporal autocorrelation, pattern recurrence, influence clustering)
3. **Train ML detectors** to recognize morphic-like patterns in time series data
4. **Compare against controls** to understand what makes morphic dynamics distinctive

Think of it as: *"If physicists can predict gravitational wave signatures before detecting them, can we predict morphic field signatures before looking for them in real systems?"*

## 🧬 What We've Found So Far

**Key Finding**: Pattern memory can destabilize systems. Our initial experiments show:

- **Morphic simulations** (with pattern memory) experience 22% population collapse
- **Classical simulations** (pure Conway rules) remain stable
- **Implication**: Memory without exploration leads to premature convergence

This suggests morphic-like mechanisms create distinctive dynamics—memory constrains the search space, preventing discovery of stable attractors that pure evolution finds naturally.

## 🔬 Current Implementation

### Three Simulation Modes

1. **Morphic** - Pattern memory influences cell decisions via "crystals" (successful pattern storage)
2. **LLM-Control** - AI consultation for high-similarity patterns (>0.8 similarity threshold)
3. **Classical** - Pure Conway's Game of Life baseline

### Pattern Memory Mechanism

- **Multi-scale analysis**: 3×3 → 5×5 → 7×7 adaptive neighborhoods
- **Similarity metrics**: Hamming distance + convolution + subpattern matching
- **Bayesian learning**: Crystal strength updates based on success rates
- **Influence system**: Perfect pattern matches can achieve 100% rule override

### Visualization & Analysis

- Real-time animated comparisons (morphic vs control vs classical)
- Frame-by-frame analysis with morphic influence markers
- Population dynamics, complexity evolution, pattern diversity tracking
- Statistical summaries and correlation analysis

## 🚀 Quick Start

```bash
# 1. Set up environment variables (optional)
cp .env.example .env
# Edit .env with your API keys if using LLM features

# 2. Complete setup + validation
./launcher.sh

# 3. Run comparative simulation
./training.sh --mode=morphic --generations=50

# 4. Start web interface
./run.sh
# Visit: http://localhost:8000

# 5. View historical results
python simple_viewer.py
# Visit: http://localhost:8005
```

## 📊 Research Applications

This framework enables investigation of:

- **Memory vs exploration tradeoffs** in evolutionary systems
- **Pattern emergence** under different influence regimes
- **Cross-system resonance** (do independent runs converge?)
- **Temporal dynamics** of collective memory formation
- **Threshold effects** in pattern-influenced systems

Relevant to:
- Machine learning (overfitting, catastrophic forgetting)
- Evolutionary algorithms (exploitation vs exploration)
- Self-organizing systems (stigmergy, collective intelligence)
- Cultural evolution (tradition vs innovation)

## 🎯 Roadmap

**Phase 1** (Current): Comparative simulation framework with visualization
**Phase 2**: Time series data generation and feature extraction
**Phase 3**: ML detector training ("morphic field signature" classifier)
**Phase 4**: Cross-domain application (other cellular automata, real data)

See [ROADMAP.md](ROADMAP.md) for detailed vision and [PLAN.md](PLAN.md) for implementation specifics.

## 🛠️ Technical Stack

- **Core**: Python 3.13+, NumPy, pattern similarity engine
- **Visualization**: Matplotlib, Pillow (GIF generation)
- **Web**: FastAPI, SQLite (PostgreSQL-ready)
- **ML Ready**: Data structures prepared for PyTorch/TensorFlow integration
- **API**: Optional OpenRouter integration for LLM decisions

## 📈 Current Status

- ✅ Pattern-based morphic resonance with multi-scale analysis
- ✅ Comparative analysis framework (morphic vs control)
- ✅ Web interface with historical viewer
- ✅ Animation and statistical visualization
- ✅ Initial findings on memory-induced instability
- ✅ Time series dataset generation and batch processing
- 🔄 ML detector training pipeline (Phase 3 - ready to begin)

## 🔧 Configuration

```bash
# Simulation parameters
GENERATIONS=50              # Evolution steps
GRID_SIZE=25               # Arena dimensions
CRYSTAL_COUNT=5            # Pattern memory capacity
INITIAL_DENSITY=0.4        # Starting cell density

# Morphic field parameters (future)
FIELD_STRENGTH=0.6         # Influence magnitude
TEMPORAL_DECAY=0.1         # How fast influence fades
CROSS_SYSTEM_COUPLING=0.3  # Inter-run resonance
```

## 📄 License

MIT License - This is research infrastructure, not a claim about reality.

## 🙏 Acknowledgments

Rupert Sheldrake for the provocative hypothesis that inspired this computational exploration. This project neither proves nor disproves morphic resonance—it explores what such phenomena would look like if instantiated in artificial systems.

**Built with Claude Code** - An experiment in AI-assisted scientific infrastructure development.

---

*"The question is not whether morphic fields exist, but what patterns they would produce if they did—and whether those patterns appear in nature."*