#!/usr/bin/env python3
"""
Database Models for Emergence Simulator

Defines SQLAlchemy models for storing simulation runs, integrated runs,
and associated metadata.
"""

from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from storage.database import Base
import uuid
from datetime import datetime


class SimulationRun(Base):
    """Individual simulation run record"""
    __tablename__ = "simulation_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_id = Column(String(50), unique=True, nullable=False, index=True)
    simulation_type = Column(String(20), nullable=False)  # 'morphic', 'llm_control', 'classical'
    parameters = Column(JSON, nullable=False)
    status = Column(String(20), nullable=False, default='pending')  # 'pending', 'running', 'completed', 'error'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Results data
    generations = Column(Integer)
    final_population = Column(Integer)
    results_path = Column(String(500))  # Path to results JSON file
    animation_path = Column(String(500))  # Path to animation file

    # Relationship to integrated runs
    integrated_run_id = Column(Integer, ForeignKey('integrated_runs.id'))
    integrated_run = relationship("IntegratedRun", back_populates="simulation_runs")


class IntegratedRun(Base):
    """Integrated run combining multiple simulation types"""
    __tablename__ = "integrated_runs"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    run_id = Column(String(50), unique=True, nullable=False, index=True)

    # Parameters
    parameters = Column(JSON, nullable=False)

    # Status tracking
    status = Column(String(20), nullable=False, default='pending')  # 'pending', 'running', 'completed', 'error'
    progress = Column(Float, default=0.0)  # 0.0 to 1.0
    current_stage = Column(String(100))  # Description of current stage

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    # Visual assets
    side_by_side_video_path = Column(String(500))  # Path to combined animation
    comparison_frames_path = Column(String(500))  # Path to frame comparison directory

    # Error handling
    error_message = Column(Text)

    # Relationships
    simulation_runs = relationship("SimulationRun", back_populates="integrated_run", cascade="all, delete-orphan")


class ComparisonFrame(Base):
    """Individual frame comparison storage"""
    __tablename__ = "comparison_frames"

    id = Column(Integer, primary_key=True, index=True)
    integrated_run_id = Column(Integer, ForeignKey('integrated_runs.id'))
    frame_number = Column(Integer, nullable=False)
    generation = Column(Integer, nullable=False)

    # Frame paths for each simulation type
    morphic_frame_path = Column(String(500))
    llm_control_frame_path = Column(String(500))
    classical_frame_path = Column(String(500))

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    integrated_run = relationship("IntegratedRun")


class MorphicEvent(Base):
    """Track morphic resonance events for educational purposes"""
    __tablename__ = "morphic_events"

    id = Column(Integer, primary_key=True, index=True)
    simulation_run_id = Column(Integer, ForeignKey('simulation_runs.id'))

    generation = Column(Integer, nullable=False)
    event_type = Column(String(50), nullable=False)  # 'crystal_formed', 'llm_consultation', 'uncapped_influence'

    # Event details
    pattern_similarity = Column(Float)
    influence_probability = Column(Float)
    decision_source = Column(String(20))  # 'llm', 'markov', 'conway'
    neighborhood_size = Column(String(10))  # '3x3', '5x5', '7x7'

    # Pattern info
    pattern_data = Column(JSON)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship
    simulation_run = relationship("SimulationRun")


def generate_unique_slug(base_slug: str = None) -> str:
    """Generate a unique URL slug"""
    if base_slug:
        # Clean and format the base slug
        slug = base_slug.lower().replace(' ', '-').replace('_', '-')
        # Remove special characters
        import re
        slug = re.sub(r'[^a-z0-9\-]', '', slug)
        # Ensure it doesn't start or end with dash
        slug = slug.strip('-')
        if not slug:
            slug = "run"
    else:
        slug = "run"

    # Add timestamp for uniqueness
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    unique_id = str(uuid.uuid4())[:8]

    return f"{slug}-{timestamp}-{unique_id}"


def generate_run_id() -> str:
    """Generate a unique run ID"""
    return str(uuid.uuid4())


if __name__ == "__main__":
    # Test the models
    print("🗄️  Database Models Test")
    print("=" * 40)

    # Test slug generation
    test_slugs = [
        "My Test Run",
        "morphic_experiment_1",
        "",
        "Special Characters!@#$%",
    ]

    for test_slug in test_slugs:
        result = generate_unique_slug(test_slug)
        print(f"'{test_slug}' -> '{result}'")

    print(f"\nSample run ID: {generate_run_id()}")