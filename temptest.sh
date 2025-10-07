# Complete Phase 2 Testing Suite
# Run this command to validate everything the agent built

echo "🧪 Testing Phase 2 Implementation" && \
echo "=================================" && \
echo "" && \
\
echo "📋 Test 1: Verify new files exist..." && \
ls -lh morphic_config.py batch_runner.py PHASE2_IMPLEMENTATION.md QUICK_START_PHASE2.md && \
echo "✅ All new files present" && \
echo "" && \
\
echo "📋 Test 2: Config module validation..." && \
./venv/bin/python morphic_config.py && \
echo "" && \
\
echo "📋 Test 3: Single morphic simulation with parameters..." && \
./training.sh --mode=morphic --generations=20 --grid-size=15 --crystal-count=3 --field-strength=0.8 --temporal-decay=0.2 --similarity-threshold=0.6 && \
echo "" && \
\
echo "📋 Test 4: Verify time series output format..." && \
ls -lh timeseries_data/*.json && \
echo "Latest time series file:" && \
ls -t timeseries_data/*.json | head -1 | xargs cat | python3 -m json.tool | head -30 && \
echo "" && \
\
echo "📋 Test 5: Batch runner dry-run (5 experiments)..." && \
./venv/bin/python batch_runner.py --experiment-type=focused --dry-run --limit=5 && \
echo "" && \
\
echo "📋 Test 6: Small parameter sweep (3 actual runs)..." && \
timeout 5m ./venv/bin/python batch_runner.py --experiment-type=focused --limit=3 && \
echo "" && \
\
echo "📋 Test 7: Verify dataset manifest..." && \
cat timeseries_data/manifest.json | python3 -m json.tool && \
echo "" && \
\
echo "📋 Test 8: Compare morphic vs control outputs..." && \
echo "Control run:" && \
./training.sh --mode=classical --generations=15 --grid-size=15 && \
echo "Morphic run:" && \
./training.sh --mode=morphic --generations=15 --grid-size=15 --field-strength=0.5 && \
echo "" && \
\
echo "📊 FINAL REPORT" && \
echo "===============" && \
echo "Time series files generated: $(ls timeseries_data/*.json 2>/dev/null | wc -l)" && \
echo "Latest morphic simulation:" && \
ls -t timeseries_data/morphic_*.json 2>/dev/null | head -1 | xargs -I {} sh -c 'cat {} | python3 -c "import json, sys; d=json.load(sys.stdin); print(f\"  Field strength: {d[\"config\"].get(\"field_strength\", \"N/A\")}\"); print(f\"  Generations: {len(d[\"timeseries\"][\"population\"])}\"); print(f\"  Final pop: {d[\"summary_stats\"][\"final_population\"]}\"); print(f\"  Avg influence: {d[\"summary_stats\"].get(\"avg_influence_rate\", 0):.2%}\")"' && \
echo "" && \
echo "✅ Phase 2 Implementation Test Complete!" && \
echo "Ready for Phase 3: ML Detector Training"