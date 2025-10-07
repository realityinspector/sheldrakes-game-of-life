#!/usr/bin/env python3
"""
Morphic Field Configuration

Defines parameters for controlling morphic field behavior in simulations
"""

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class MorphicFieldConfig:
    """Parameters controlling morphic field behavior"""

    # Core field parameters
    field_strength: float = 0.6  # 0.0-1.0, master influence multiplier
    temporal_decay: float = 0.1  # How fast crystal influence fades (0=no decay, 1=instant decay)
    cross_system_coupling: float = 0.0  # 0.0-1.0, inter-run influence (future use)
    similarity_threshold: float = 0.7  # Minimum similarity for morphic influence
    influence_exponent: float = 2.0  # Non-linearity in similarity->influence mapping

    # Crystal parameters
    crystal_count: int = 5  # Number of memory crystals
    crystal_capacity: int = 50  # Max patterns per crystal

    # Simulation parameters
    generations: int = 50  # Number of generations to run
    grid_size: int = 25  # Grid dimensions (grid_size x grid_size)
    initial_density: float = 0.4  # Initial population density (0.0-1.0)

    def to_dict(self):
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict):
        """Create from dictionary"""
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def validate(self) -> tuple[bool, Optional[str]]:
        """
        Validate configuration parameters
        Returns: (is_valid, error_message)
        """
        errors = []

        # Validate field strength
        if not 0.0 <= self.field_strength <= 1.0:
            errors.append(f"field_strength must be in [0.0, 1.0], got {self.field_strength}")

        # Validate temporal decay
        if not 0.0 <= self.temporal_decay <= 1.0:
            errors.append(f"temporal_decay must be in [0.0, 1.0], got {self.temporal_decay}")

        # Validate cross-system coupling
        if not 0.0 <= self.cross_system_coupling <= 1.0:
            errors.append(f"cross_system_coupling must be in [0.0, 1.0], got {self.cross_system_coupling}")

        # Validate similarity threshold
        if not 0.0 <= self.similarity_threshold <= 1.0:
            errors.append(f"similarity_threshold must be in [0.0, 1.0], got {self.similarity_threshold}")

        # Validate influence exponent
        if not 0.5 <= self.influence_exponent <= 5.0:
            errors.append(f"influence_exponent should be in [0.5, 5.0], got {self.influence_exponent}")

        # Validate crystal count
        if not 1 <= self.crystal_count <= 20:
            errors.append(f"crystal_count must be in [1, 20], got {self.crystal_count}")

        # Validate crystal capacity
        if not 10 <= self.crystal_capacity <= 500:
            errors.append(f"crystal_capacity must be in [10, 500], got {self.crystal_capacity}")

        # Validate generations
        if not 1 <= self.generations <= 10000:
            errors.append(f"generations must be in [1, 10000], got {self.generations}")

        # Validate grid size
        if not 5 <= self.grid_size <= 100:
            errors.append(f"grid_size must be in [5, 100], got {self.grid_size}")

        # Validate initial density
        if not 0.0 <= self.initial_density <= 1.0:
            errors.append(f"initial_density must be in [0.0, 1.0], got {self.initial_density}")

        if errors:
            return False, "; ".join(errors)

        return True, None

    def __str__(self):
        """String representation"""
        return (
            f"MorphicFieldConfig("
            f"field_strength={self.field_strength:.2f}, "
            f"temporal_decay={self.temporal_decay:.2f}, "
            f"similarity_threshold={self.similarity_threshold:.2f}, "
            f"crystals={self.crystal_count}, "
            f"generations={self.generations})"
        )


# Preset configurations for common experiments
PRESETS = {
    'no_field': MorphicFieldConfig(
        field_strength=0.0,
        temporal_decay=0.0,
        similarity_threshold=1.0  # Impossible threshold
    ),
    'weak_field': MorphicFieldConfig(
        field_strength=0.3,
        temporal_decay=0.5,
        similarity_threshold=0.8
    ),
    'moderate_field': MorphicFieldConfig(
        field_strength=0.6,
        temporal_decay=0.1,
        similarity_threshold=0.7
    ),
    'strong_field': MorphicFieldConfig(
        field_strength=0.9,
        temporal_decay=0.05,
        similarity_threshold=0.5
    ),
    'no_decay': MorphicFieldConfig(
        field_strength=0.6,
        temporal_decay=0.0,
        similarity_threshold=0.7
    ),
    'rapid_decay': MorphicFieldConfig(
        field_strength=0.6,
        temporal_decay=0.9,
        similarity_threshold=0.7
    )
}


def get_preset(name: str) -> MorphicFieldConfig:
    """Get a preset configuration by name"""
    if name not in PRESETS:
        raise ValueError(f"Unknown preset: {name}. Available: {list(PRESETS.keys())}")
    return PRESETS[name]


def parse_config_from_args(args) -> MorphicFieldConfig:
    """
    Parse MorphicFieldConfig from command line arguments

    Expected args format:
    - args.field_strength: float
    - args.temporal_decay: float
    - args.similarity_threshold: float
    - etc.
    """
    config_dict = {}

    # Map argument names to config fields
    for field_name in MorphicFieldConfig.__dataclass_fields__:
        if hasattr(args, field_name):
            config_dict[field_name] = getattr(args, field_name)

    return MorphicFieldConfig(**config_dict)


if __name__ == "__main__":
    # Test configuration
    print("🧪 Testing MorphicFieldConfig")
    print("=" * 50)

    # Test default config
    default_config = MorphicFieldConfig()
    print(f"\nDefault config: {default_config}")
    valid, error = default_config.validate()
    print(f"Valid: {valid}")
    if error:
        print(f"Error: {error}")

    # Test presets
    print("\n📋 Available presets:")
    for name, config in PRESETS.items():
        print(f"  {name}: {config}")
        valid, error = config.validate()
        if not valid:
            print(f"    ⚠️  Warning: {error}")

    # Test validation with invalid values
    print("\n🔍 Testing validation:")
    invalid_config = MorphicFieldConfig(field_strength=1.5, crystal_count=100)
    valid, error = invalid_config.validate()
    print(f"Invalid config: {invalid_config}")
    print(f"Valid: {valid}")
    print(f"Error: {error}")

    print("\n✅ Configuration module ready")
