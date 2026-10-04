"""PPB-MoE：应用层稀疏 MoE 的编排层（专家池 / 运行时 / 治理 / 观测）。"""

from moecore.registry import ExpertRegistry, ExpertSpec, RouteDecision
from moecore.orchestrator import ExpertAdapter, Orchestrator, OrchestrationRecord
from moecore.governance import AddonManifest, Conflict, Governance
from moecore.observability import CognitiveMonitor, ObservabilityEvent

__version__ = "0.1.0"
__all__ = ["ExpertRegistry", "ExpertSpec", "RouteDecision",
           "ExpertAdapter", "Orchestrator", "OrchestrationRecord",
           "AddonManifest", "Conflict", "Governance",
           "CognitiveMonitor", "ObservabilityEvent", "__version__"]
