"""The Demo lab's tables. Importing registers them; ``db.connect`` binds them to the database."""

from scene_onboarding_demo.schemas.behavior import Arena, Kinematics, Recording, Trajectory
from scene_onboarding_demo.schemas.lab import ScoreSheet, SessionInfo

__all__ = ["Arena", "Kinematics", "Recording", "ScoreSheet", "SessionInfo", "Trajectory"]
