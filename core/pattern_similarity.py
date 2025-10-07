import numpy as np
from scipy.spatial.distance import hamming
from scipy.signal import convolve2d
from scipy.sparse import csr_matrix
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def extract_subpatterns(grid):
    """Extract 3x3, 5x5, 7x7 subgrids for multi-scale matching"""
    if not isinstance(grid, np.ndarray):
        grid = np.array(grid)

    subpatterns = []
    for size in [3, 5, 7]:
        if grid.shape[0] < size or grid.shape[1] < size:
            continue
        for i in range(0, grid.shape[0] - size + 1, 2):
            for j in range(0, grid.shape[1] - size + 1, 2):
                subpatterns.append(grid[i:i+size, j:j+size])
    return subpatterns

def calculate_pattern_similarity(current_grid, crystal_pattern):
    """
    Calculate multi-metric similarity between patterns
    Returns: similarity score [0, 1]
    """
    if not isinstance(current_grid, np.ndarray):
        current_grid = np.array(current_grid)

    stored_grid = crystal_pattern['grid']
    if not isinstance(stored_grid, np.ndarray):
        stored_grid = np.array(stored_grid)

    # Ensure grids are same size for comparison
    min_rows = min(current_grid.shape[0], stored_grid.shape[0])
    min_cols = min(current_grid.shape[1], stored_grid.shape[1])

    current_crop = current_grid[:min_rows, :min_cols]
    stored_crop = stored_grid[:min_rows, :min_cols]

    # Hamming distance for exact matching
    hamming_sim = 1 - hamming(current_crop.flatten(), stored_crop.flatten())

    # Convolution for translation-invariant detection
    try:
        kernel_size = min(5, min_rows, min_cols)
        if kernel_size >= 3:
            kernel = stored_crop[:kernel_size, :kernel_size]
            if kernel.sum() > 0:
                conv_result = convolve2d(current_crop, kernel, mode='valid')
                conv_sim = np.max(conv_result) / (kernel.sum() * 255) if kernel.sum() > 0 else 0
            else:
                conv_sim = 0
        else:
            conv_sim = 0
    except Exception as e:
        logger.warning(f"Convolution failed: {e}")
        conv_sim = 0

    # Subpattern matching with proper size handling
    subpattern_scores = []
    try:
        stored_subs = crystal_pattern.get('subpatterns', [])
        current_subs = extract_subpatterns(current_crop)

        if stored_subs and current_subs:
            # Group subpatterns by size for efficient comparison
            stored_by_size = {}
            current_by_size = {}

            for sub in stored_subs:
                size = sub.shape
                if size not in stored_by_size:
                    stored_by_size[size] = []
                stored_by_size[size].append(sub)

            for sub in current_subs:
                size = sub.shape
                if size not in current_by_size:
                    current_by_size[size] = []
                current_by_size[size].append(sub)

            # Compare subpatterns of matching sizes
            for size in stored_by_size:
                if size in current_by_size:
                    stored_patterns = stored_by_size[size][:3]  # Limit for performance
                    current_patterns = current_by_size[size][:3]

                    for stored_sub in stored_patterns:
                        best_score = 0
                        for current_sub in current_patterns:
                            score = 1 - hamming(stored_sub.flatten(), current_sub.flatten())
                            best_score = max(best_score, score)
                        subpattern_scores.append(best_score)

        subpattern_sim = np.mean(subpattern_scores) if subpattern_scores else 0
    except Exception as e:
        logger.warning(f"Subpattern matching failed: {e}")
        subpattern_sim = 0

    # Weighted combination
    similarity = 0.3 * hamming_sim + 0.4 * conv_sim + 0.3 * subpattern_sim
    return min(1.0, max(0.0, similarity))

class MarkovPatternPredictor:
    def __init__(self, history_size=100):
        self.transitions = {}  # (pattern_t) -> {pattern_t+1: count}
        self.history_size = history_size

    def update(self, pattern_from, pattern_to):
        """Update transition matrix with new observation"""
        try:
            # Convert patterns to hashable format
            key_from = self._pattern_to_key(pattern_from)
            key_to = self._pattern_to_key(pattern_to)

            if key_from not in self.transitions:
                self.transitions[key_from] = {}

            if key_to not in self.transitions[key_from]:
                self.transitions[key_from][key_to] = 0

            self.transitions[key_from][key_to] += 1

            # Limit history size for memory management
            if len(self.transitions) > self.history_size:
                oldest_key = next(iter(self.transitions))
                del self.transitions[oldest_key]
        except Exception as e:
            logger.warning(f"Markov update failed: {e}")

    def predict_next(self, current_pattern):
        """Predict probability distribution of next patterns"""
        try:
            key = self._pattern_to_key(current_pattern)

            if key not in self.transitions:
                return {}

            # Normalize to probabilities
            total = sum(self.transitions[key].values())
            if total == 0:
                return {}

            probs = {k: v/total for k, v in self.transitions[key].items()}
            return probs
        except Exception as e:
            logger.warning(f"Markov prediction failed: {e}")
            return {}

    def _pattern_to_key(self, pattern):
        """Convert pattern to hashable key using sparse representation"""
        try:
            if not isinstance(pattern, np.ndarray):
                pattern = np.array(pattern)

            # Use smaller patterns for keys to avoid memory issues
            if pattern.shape[0] > 5 or pattern.shape[1] > 5:
                pattern = pattern[:5, :5]

            sparse = csr_matrix(pattern)
            return (sparse.data.tobytes(), sparse.indices.tobytes(), sparse.indptr.tobytes())
        except Exception as e:
            logger.warning(f"Pattern key generation failed: {e}")
            return hash(tuple(tuple(row) for row in pattern))

def update_crystal_strength_bayesian(crystal, success, all_crystals):
    """
    Bayesian update of crystal strength
    P(crystal|success) = P(success|crystal) * P(crystal) / P(success)
    """
    try:
        # Prior: current strength
        prior = crystal['strength']

        # Likelihood: success rate when this crystal was active
        activations = crystal.get('activation_history', [])
        if len(activations) > 0:
            successes = sum(1 for a in activations if a.get('emergent', False))
            likelihood = successes / len(activations)
        else:
            likelihood = 0.5  # Uninformative prior

        # Evidence: overall success rate
        total_successes = sum(c.get('total_successes', 0) for c in all_crystals)
        total_trials = sum(c.get('total_trials', 1) for c in all_crystals)
        evidence = total_successes / total_trials if total_trials > 0 else 0.5

        # Posterior
        if evidence > 0:
            posterior = (likelihood * prior) / evidence
            posterior = min(1.0, max(0.0, posterior))
        else:
            posterior = prior

        # Apply update with learning rate
        learning_rate = 0.1
        crystal['strength'] = (1 - learning_rate) * crystal['strength'] + learning_rate * posterior

        # Initialize activation_history if it doesn't exist
        if 'activation_history' not in crystal:
            crystal['activation_history'] = []

        # Track history
        crystal['activation_history'].append({
            'timestamp': datetime.now().isoformat(),
            'emergent': success,
            'posterior': posterior
        })

        return crystal['strength']
    except Exception as e:
        logger.error(f"Bayesian strength update failed: {e}")
        return crystal.get('strength', 0.5)

def get_adaptive_neighborhood(grid, i, j, grid_size, pattern_scale=None):
    """
    Extract neighborhood of adaptive size based on pattern scale
    Returns neighborhood and size used
    """
    if pattern_scale is None:
        # Default to 3x3 neighborhood
        size = 1
    else:
        # Adapt neighborhood size to pattern scale
        if pattern_scale <= 3:
            size = 1  # 3x3 neighborhood
        elif pattern_scale <= 5:
            size = 2  # 5x5 neighborhood
        else:
            size = 3  # 7x7 neighborhood

    # Extract neighborhood with bounds checking
    start_i = max(0, i - size)
    end_i = min(grid_size, i + size + 1)
    start_j = max(0, j - size)
    end_j = min(grid_size, j + size + 1)

    neighborhood = grid[start_i:end_i, start_j:end_j]
    actual_size = neighborhood.shape[0]

    return neighborhood, actual_size

def get_morphic_influence_for_cell(neighborhood, crystals, conway_decision, grid=None, i=None, j=None, grid_size=None, morphic_config=None, current_generation=0):
    """
    Calculate morphic influence for a single cell based on pattern similarity

    Args:
        neighborhood: Current cell neighborhood
        crystals: List of memory crystals
        conway_decision: Decision from Conway's rules
        grid: Full grid (optional, for adaptive neighborhoods)
        i, j: Cell position (optional, for adaptive neighborhoods)
        grid_size: Grid dimensions (optional)
        morphic_config: MorphicFieldConfig object with field parameters
        current_generation: Current generation number for temporal decay

    Returns: (influenced_decision, influence_strength, debug_info)
    """
    if not crystals:
        return conway_decision, 0.0, {'reason': 'no_crystals'}

    # Use default field parameters if config not provided
    if morphic_config is None:
        field_strength = 0.6
        temporal_decay = 0.1
        similarity_threshold = 0.7
        influence_exponent = 2.0
    else:
        field_strength = morphic_config.field_strength
        temporal_decay = morphic_config.temporal_decay
        similarity_threshold = morphic_config.similarity_threshold
        influence_exponent = morphic_config.influence_exponent

    try:
        # Find patterns similar to current neighborhood
        similarities = []
        best_pattern_scale = None

        for crystal in crystals:
            for pattern in crystal['patterns'][-20:]:  # Use recent patterns
                try:
                    # Determine pattern scale for adaptive neighborhood
                    pattern_grid = pattern.get('grid', [])
                    if isinstance(pattern_grid, np.ndarray):
                        pattern_scale = max(pattern_grid.shape)
                    else:
                        pattern_scale = 3  # Default

                    # Use adaptive neighborhood if grid position is available
                    if grid is not None and i is not None and j is not None:
                        adaptive_neighborhood, actual_size = get_adaptive_neighborhood(
                            grid, i, j, grid_size, pattern_scale
                        )
                        sim = calculate_pattern_similarity(adaptive_neighborhood, pattern)
                    else:
                        sim = calculate_pattern_similarity(neighborhood, pattern)

                    # Apply similarity threshold from config
                    if sim > similarity_threshold * 0.5:  # Lower bound for consideration
                        # Calculate crystal age and apply temporal decay
                        pattern_generation = pattern.get('generation', 0)
                        crystal_age = current_generation - pattern_generation if current_generation > pattern_generation else 0

                        # Apply exponential temporal decay
                        time_factor = np.exp(-temporal_decay * crystal_age) if temporal_decay > 0 else 1.0

                        # Apply influence exponent to similarity
                        similarity_transformed = sim ** influence_exponent

                        # Calculate weighted score with all factors
                        weighted_score = similarity_transformed * crystal['strength'] * time_factor

                        similarities.append({
                            'similarity': sim,
                            'strength': crystal['strength'],
                            'crystal': crystal,
                            'pattern': pattern,
                            'weighted_score': weighted_score,
                            'pattern_scale': pattern_scale,
                            'crystal_age': crystal_age,
                            'time_factor': time_factor,
                            'similarity_transformed': similarity_transformed
                        })

                        # Track the best pattern scale for potential LLM context
                        if best_pattern_scale is None or sim > 0.7:
                            best_pattern_scale = pattern_scale

                except Exception:
                    continue

        if not similarities:
            return conway_decision, 0.0, {'reason': 'no_similar_patterns'}

        # Sort by weighted score (similarity * crystal strength)
        similarities.sort(key=lambda x: x['weighted_score'], reverse=True)

        # Use top matches for influence
        top_matches = similarities[:3]
        total_influence = sum(m['weighted_score'] for m in top_matches)

        if total_influence < 0.1:  # Threshold for meaningful influence
            return conway_decision, 0.0, {'reason': 'weak_influence', 'total': total_influence}

        # Get Markov predictions from best matching crystal
        best_match = top_matches[0]
        markov_decision = conway_decision  # Default fallback
        llm_decision = None

        # Try LLM integration for very high similarity patterns
        if best_match['similarity'] > 0.8:  # Very high similarity threshold
            try:
                context = generate_llm_context([best_match['crystal']], neighborhood)
                if context:
                    logger.info(f"High similarity pattern detected ({best_match['similarity']:.3f}) - querying LLM")
                    llm_decision = query_llm_for_decision(context)
                    if llm_decision is not None:
                        logger.info(f"LLM provided decision: {llm_decision}")
            except Exception as e:
                logger.debug(f"LLM integration failed: {e}")

        try:
            markov_predictor = best_match['crystal']['markov_predictor']
            next_probs = markov_predictor.predict_next(neighborhood)

            if next_probs:
                # Find the most probable transition
                best_prob = 0
                for pattern_key, prob in next_probs.items():
                    if prob > best_prob:
                        best_prob = prob
                        # Heuristic: if probability > 0.6, lean toward life
                        markov_decision = 1 if prob > 0.6 else 0
        except Exception as e:
            logger.debug(f"Markov prediction failed: {e}")

        # Priority: LLM > Markov > Conway
        if llm_decision is not None:
            predicted_decision = llm_decision
            decision_source = 'llm'
        else:
            predicted_decision = markov_decision
            decision_source = 'markov'

        # Calculate final influence probability with field strength
        base_influence = total_influence * field_strength

        # Boost influence for LLM decisions and very high similarity
        if llm_decision is not None:
            # LLM decisions get 95% minimum influence when available
            influence_probability = max(0.95 * field_strength, base_influence)
        elif best_match['similarity'] > 0.9:
            # Near-perfect matches get 90% minimum influence
            influence_probability = max(0.9 * field_strength, base_influence)
        else:
            # Normal morphic influence with field strength applied
            influence_probability = min(1.0, base_influence)

        # Apply morphic influence probabilistically
        if np.random.random() < influence_probability:
            final_decision = predicted_decision
            applied_influence = True
        else:
            final_decision = conway_decision
            applied_influence = False

        debug_info = {
            'reason': 'morphic_influence',
            'top_similarity': best_match['similarity'],
            'total_influence': total_influence,
            'influence_probability': influence_probability,
            'markov_decision': markov_decision,
            'llm_decision': llm_decision,
            'decision_source': decision_source,
            'conway_decision': conway_decision,
            'applied_influence': applied_influence,
            'num_matches': len(similarities),
            'pattern_scale': best_match.get('pattern_scale', 3),
            'adaptive_neighborhood': best_pattern_scale,
            'field_strength': field_strength,
            'temporal_decay': temporal_decay,
            'crystal_age': best_match.get('crystal_age', 0),
            'time_factor': best_match.get('time_factor', 1.0),
            'similarity_transformed': best_match.get('similarity_transformed', best_match['similarity'])
        }

        return final_decision, total_influence, debug_info

    except Exception as e:
        logger.error(f"Morphic influence calculation failed: {e}")
        return conway_decision, 0.0, {'reason': 'error', 'error': str(e)}

def generate_llm_context(crystal_patterns, current_state):
    """Generate context for LLM decision-making"""
    try:
        import os
        if not os.getenv('OPENROUTER_API_KEY'):
            return None

        # Find similar historical patterns
        similar_patterns = []
        for crystal in crystal_patterns:
            for pattern in crystal.get('patterns', []):
                sim = calculate_pattern_similarity(current_state, pattern)
                if sim > 0.7:
                    similar_patterns.append({
                        'pattern': pattern,
                        'similarity': sim,
                        'outcome': pattern.get('outcome', 'unknown')
                    })

        # Build context string
        current_sum = np.sum(current_state) if isinstance(current_state, np.ndarray) else sum(sum(row) for row in current_state)
        context = f"""
Current neighborhood state has {current_sum} live cells.
Found {len(similar_patterns)} similar historical patterns.

Historical outcomes:
"""

        for sp in similar_patterns[:3]:
            context += f"- Pattern with {sp['similarity']:.2f} similarity led to {sp['outcome']}\n"

        context += "\nBased on morphic field memory, suggest next state (0 or 1):"

        return context
    except Exception as e:
        logger.warning(f"LLM context generation failed: {e}")
        return None

def query_llm_for_decision(context):
    """Query LLM for morphic decision when available (synchronous)"""
    try:
        import os
        import requests
        import time

        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            logger.debug("No OPENROUTER_API_KEY found")
            return None

        # Rate limiting to avoid overwhelming the API
        time.sleep(0.1)  # 100ms delay between calls

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/anthropics/claude-code",
                "X-Title": "Morphic Resonance Simulator"
            },
            json={
                "model": "anthropic/claude-3-haiku",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are analyzing a Conway's Game of Life pattern for morphic resonance. Respond with only '0' for death or '1' for life."
                    },
                    {
                        "role": "user",
                        "content": context
                    }
                ],
                "max_tokens": 3,
                "temperature": 0.1
            },
            timeout=3.0
        )

        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()

            # Extract 0 or 1 from response
            if '1' in content:
                logger.info(f"LLM decision: 1 (life) for pattern")
                return 1
            elif '0' in content:
                logger.info(f"LLM decision: 0 (death) for pattern")
                return 0
            else:
                logger.warning(f"LLM gave unclear response: {content}")
                return None
        else:
            logger.warning(f"LLM API error: {response.status_code} - {response.text}")
            return None

    except requests.exceptions.Timeout:
        logger.debug("LLM query timed out")
        return None
    except requests.exceptions.RequestException as e:
        logger.debug(f"LLM request failed: {e}")
        return None
    except Exception as e:
        logger.debug(f"LLM query failed: {e}")
        return None

async def query_llm_for_decision_async(context):
    """Async version for future use"""
    try:
        import os
        import httpx

        api_key = os.getenv('OPENROUTER_API_KEY')
        if not api_key:
            return None

        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://github.com/anthropics/claude-code",
                    "X-Title": "Morphic Resonance Simulator"
                },
                json={
                    "model": "anthropic/claude-3-haiku",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are analyzing a Conway's Game of Life pattern for morphic resonance. Respond with only '0' for death or '1' for life."
                        },
                        {
                            "role": "user",
                            "content": context
                        }
                    ],
                    "max_tokens": 3,
                    "temperature": 0.1
                },
                timeout=3.0
            )

            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content'].strip()
                if '1' in content:
                    return 1
                elif '0' in content:
                    return 0

            return None
    except Exception as e:
        logger.debug(f"LLM query failed: {e}")
        return None

def validate_morphic_implementation(crystals, morphic_influences=None):
    """Comprehensive validation suite"""
    try:
        validation_results = []

        # Test 1: Pattern storage is structural, not hash
        structural_patterns = 0
        for crystal in crystals:
            for pattern in crystal.get('patterns', []):
                if 'grid' not in pattern:
                    return False, "Pattern missing grid data"
                if not isinstance(pattern['grid'], (np.ndarray, list)):
                    return False, "Pattern grid is not array-like"
                structural_patterns += 1

        validation_results.append(f"✅ {structural_patterns} structural patterns stored")

        # Test 2: Similarity metrics are bounded
        test_grid = np.random.randint(0, 2, (5, 5))  # Smaller for testing
        similarity_tests = 0
        for crystal in crystals:
            for pattern in crystal.get('patterns', []):
                sim = calculate_pattern_similarity(test_grid, pattern)
                if not (0 <= sim <= 1):
                    return False, f"Similarity {sim} out of bounds [0,1]"
                similarity_tests += 1

        validation_results.append(f"✅ {similarity_tests} similarity calculations bounded [0,1]")

        # Test 3: Markov predictions validity
        markov_tests = 0
        for crystal in crystals:
            if 'markov_predictor' in crystal:
                predictor = crystal['markov_predictor']
                if len(predictor.transitions) > 0:
                    predictions = predictor.predict_next(test_grid)
                    if predictions:
                        total = sum(predictions.values())
                        if abs(total - 1.0) > 0.001:
                            return False, f"Markov predictions sum to {total}, not 1.0"
                        markov_tests += 1

        validation_results.append(f"✅ {markov_tests} Markov predictors validated")

        # Test 4: Actual morphic influence application
        if morphic_influences:
            influenced_decisions = sum(1 for inf in morphic_influences if inf.get('applied_influence', False))
            total_decisions = len(morphic_influences)
            influence_rate = influenced_decisions / total_decisions if total_decisions > 0 else 0

            validation_results.append(f"✅ {influenced_decisions}/{total_decisions} decisions influenced ({influence_rate:.1%})")

            # Test correlation between similarity and influence application
            similarities = []
            influences = []
            for inf in morphic_influences:
                if 'top_similarity' in inf and 'applied_influence' in inf:
                    similarities.append(inf['top_similarity'])
                    influences.append(1 if inf['applied_influence'] else 0)

            if len(similarities) > 20 and len(set(similarities)) > 1 and len(set(influences)) > 1:
                correlation = np.corrcoef(similarities, influences)[0, 1]
                if correlation > 0.2:
                    validation_results.append(f"✅ Similarity-influence correlation: {correlation:.3f}")
                else:
                    validation_results.append(f"⚠️  Weak similarity-influence correlation: {correlation:.3f}")
            else:
                validation_results.append("⚠️  Insufficient data for correlation analysis")

        # Test 5: Crystal strength evolution
        strength_changes = 0
        for crystal in crystals:
            history = crystal.get('activation_history', [])
            if len(history) > 1:
                strength_changes += 1

        validation_results.append(f"✅ {strength_changes} crystals show strength evolution")

        return True, "; ".join(validation_results)

    except Exception as e:
        return False, f"Validation error: {e}"