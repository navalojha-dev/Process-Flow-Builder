"""Inline knowledge base for v0.1.

Replaces the future DevRev adapter. Three things live here:

  AGENTFLEET   — the agents Stage 4 picks from.
  CAPABILITIES — Shipsy modules Stage 3 (As-Is/To-Be/Impact) names.
  VERTICALS    — per-vertical playbook hints used by Stages 1-4.

When the DevRev API is wired up (`kb/devrev.py`), this module becomes
the *fallback* — used only if DevRev is unreachable or returns nothing
useful for a query. Until then, this is the source of truth.
"""
from __future__ import annotations

# --------------------------------------------------------------------------
# AgentFleet — agents Stage 4 picks from
# --------------------------------------------------------------------------

AGENTFLEET: list[dict] = [
    {
        "agent": "ATLAS",
        "tagline": "Control Tower Agent",
        "fit": [
            "missed slot tokens", "route deviation", "idle drivers",
            "DC plan time", "exception routing to right manager",
        ],
        "default_phase": "Now",
    },
    {
        "agent": "ASTRA",
        "tagline": "Driver Assist Agent",
        "fit": [
            "unplanned stoppages", "route deviation", "missed pre-departure scans",
            "at-risk receiving windows", "driver-side nudges",
        ],
        "default_phase": "Phase 2",
    },
    {
        "agent": "NEXA",
        "tagline": "Settlement Agent",
        "fit": [
            "sub-contractor reconciliation", "rate contracts", "cost vs revenue",
            "settlement cycle time", "trip-level operating cost",
        ],
        "default_phase": "Phase 2",
    },
    {
        "agent": "VERA",
        "tagline": "Dispute Resolution Agent",
        "fit": [
            "damage claims", "detention", "demurrage", "ePOD evidence",
            "dispute paperwork",
        ],
        "default_phase": "Future",
    },
    {
        "agent": "Address Intelligence",
        "tagline": "Geocoding + Precision",
        "fit": [
            "address standardisation", "geofence reliability", "messy addresses",
            "yard / port / store precision", "growing customer base",
        ],
        "default_phase": "Now",
    },
    {
        "agent": "Routing Engine",
        "tagline": "200+ Constraint Optimiser",
        "fit": [
            "complex routing constraints", "Ramadan / school / camera time-windows",
            "truck-bay matching", "cross-border lanes", "dynamic re-routing",
            "fleet-scale planning",
        ],
        "default_phase": "Now",
    },
    {
        "agent": "Service Time AI",
        "tagline": "Historical Service-Time Predictor",
        "fit": [
            "service time prediction", "per-customer dwell time",
            "hyper / super delivery windows", "feeding routing with learnt times",
        ],
        "default_phase": "Phase 2",
    },
]


def agentfleet_for_prompt() -> str:
    """Compact rendering of the catalog for the Stage 4 prompt."""
    lines = ["AGENTFLEET CATALOG (pick 4-6 most relevant):"]
    for a in AGENTFLEET:
        lines.append(
            f"  • {a['agent']} — {a['tagline']}\n"
            f"      fits: {', '.join(a['fit'])}\n"
            f"      default phase: {a['default_phase']}"
        )
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Capabilities — Shipsy modules Stage 3 cites in to-be bullets
# --------------------------------------------------------------------------

CAPABILITIES: dict[str, str] = {
    "routing-engine":
        "Constraint-aware routing engine. 200+ constraints (time windows, "
        "vehicle eligibility, driver skills, road rules, capacity, slot tokens). "
        "Replaces standalone routing tools (Roadnet, etc.) at fleet scale.",
    "dispatch-control-tower":
        "Live truck-on-map, at-risk SLA detection, idle / deviation alerts, "
        "exception queue. Single screen for dispatchers across 24×7 ops.",
    "driver-app-epod":
        "Phone-GPS driven Driver App. Geofence-based milestones, in-app ePOD "
        "(image + timestamp + geo), navigation, accept-in-app trip handoff.",
    "settlement-finance":
        "Trip-level operating cost tracking, sub-contractor rate contracts + "
        "payouts, plan-vs-actual reconciliation, automated invoicing.",
    "customer-comms":
        "Configurable stage-wise communication (SMS/WhatsApp/email), live "
        "tracking links, sharp predicted windows, geofence-validated delivery.",
    "analytics-bi":
        "ShipsyBI dashboards: productivity, plan time, planner / dispatcher / "
        "driver KPIs, drill-down on exceptions, near-real-time refresh.",
    "master-data":
        "Unified master data: customers, drivers, assets, rate contracts. "
        "Bi-directional sync to ERPs (Oracle EBS, SAP), CRMs, CS systems.",
    "documentation":
        "Trip-spawned document tasks (CRO tokens, EIRs, gate passes, MoT "
        "waybills). Driver app shows attached docs at gate / checkpoint.",
}


def capabilities_for_prompt() -> str:
    lines = ["SHIPSY CAPABILITIES (cite by id when writing to-be bullets):"]
    for cap_id, desc in CAPABILITIES.items():
        lines.append(f"  [{cap_id}] {desc}")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Verticals — per-vertical playbook hints
# --------------------------------------------------------------------------

VERTICALS: dict[str, dict] = {
    "fmcg-distribution": {
        "summary":
            "B2B day-delivery to supermarkets / hypermarkets. Pre-sales orders "
            "→ next-day routing → wave dispatch → store-side receiving windows.",
        "row_emphasis": [
            "Order Ingestion · Pre-Sales to Plan",
            "Routing & Plan Generation",
            "Warehouse Picking & Loading",
            "Last Mile · Delivery to Store",
            "Store Communication & Slot Adherence",
        ],
        "common_pain": [
            "planner effort in legacy routing tool",
            "Excel macros for holds/returns",
            "no DC plan-time visibility",
            "regional road restrictions (Ramadan, school zones, camera fines)",
            "MoT waybill portal integration",
            "service-time uncertainty at hyper/super",
        ],
        "typical_agents": ["Routing Engine", "ATLAS", "Service Time AI", "Address Intelligence"],
    },
    "container-drayage": {
        "summary":
            "Container movement: port ↔ port, port ↔ warehouse, local + GCC "
            "cross-border. Multi-asset (truck-head + trailer + genset + dolly).",
        "row_emphasis": [
            "Booking & Order Mgmt",
            "First Mile · Pickup at Port",
            "Middle Mile · Hub-to-Hub + Cross-border",
            "Last Mile · Delivery + Empty Return",
            "Documentation Workflow",
        ],
        "common_pain": [
            "manual job → asset combo matching",
            "documentation off-system (CRO tokens, EIRs)",
            "no in-truck telematics — phone-call visibility",
            "cross-border permit / visa tribal knowledge",
            "no live map, no exception queue",
        ],
        "typical_agents": ["ATLAS", "Routing Engine", "Address Intelligence", "ASTRA", "NEXA"],
    },
    "post-and-parcel": {
        "summary":
            "CEP / express. High-volume parcels through hubs, sortation, "
            "last-mile to consumers. Multi-region, multi-modal, often franchised.",
        "row_emphasis": [
            "Booking & First Mile Pickup",
            "Hub Sortation",
            "Middle Mile Linehaul",
            "Last Mile Delivery",
            "Customer Communication",
        ],
        "common_pain": [
            "manual sortation",
            "linehaul load balancing",
            "last-mile route density",
            "consumer ETA expectations",
            "consignee unreachable / failed delivery",
        ],
        "typical_agents": ["Routing Engine", "ATLAS", "Address Intelligence", "ASTRA"],
    },
    "pallet-network": {
        "summary":
            "Pallet hub-and-spoke between independent member depots. Trunking "
            "overnight, regional collection + delivery.",
        "row_emphasis": [
            "Booking & Allocation",
            "Collection at Depot",
            "Trunk to Hub",
            "Sortation at Hub",
            "Delivery from Receiving Depot",
        ],
        "common_pain": [
            "member visibility into network",
            "trunk consolidation",
            "PoD return latency",
            "exception handling between members",
        ],
        "typical_agents": ["ATLAS", "Routing Engine", "Address Intelligence", "NEXA"],
    },
    "q-commerce": {
        "summary":
            "Hyperlocal 10-30 min delivery. Dark stores, rider fleets, very "
            "high orders/hour, dynamic re-batching.",
        "row_emphasis": [
            "Order Capture",
            "Dark Store Picking",
            "Rider Allocation",
            "Last Mile · 10-30 min",
            "Customer Communication",
        ],
        "common_pain": [
            "rider supply imbalance",
            "batch optimisation under SLA",
            "store stockouts at order time",
            "customer comms during 10-min windows",
        ],
        "typical_agents": ["Routing Engine", "ATLAS", "Address Intelligence"],
    },
    "3pl-cross-border": {
        "summary":
            "Cross-border full-truck-load and groupage. Multi-country, customs, "
            "varied rate cards.",
        "row_emphasis": [
            "Quote & Booking",
            "First Mile Pickup",
            "Customs + Linehaul",
            "Last Mile Delivery",
            "Settlement",
        ],
        "common_pain": [
            "rate card complexity",
            "customs delay visibility",
            "subcontractor payouts",
            "documentation chain",
        ],
        "typical_agents": ["ATLAS", "NEXA", "Routing Engine", "VERA"],
    },
    "cold-chain": {
        "summary":
            "Temperature-controlled distribution. Reefer assets, temperature "
            "logging, regulatory compliance.",
        "row_emphasis": [
            "Order Mgmt",
            "Reefer-aware Allocation",
            "In-transit Temperature Monitoring",
            "Last Mile",
            "Compliance Reporting",
        ],
        "common_pain": [
            "temperature breach visibility",
            "reefer asset compatibility",
            "compliance reporting",
            "customer claims",
        ],
        "typical_agents": ["ATLAS", "ASTRA", "Routing Engine", "VERA"],
    },
    "other": {
        "summary":
            "Vertical not in the standard catalog. Stage 1 should infer the "
            "closest analogue from the transcript.",
        "row_emphasis": [],
        "common_pain": [],
        "typical_agents": [],
    },
}


def vertical_for_prompt(vertical: str) -> str:
    v = VERTICALS.get(vertical, VERTICALS["other"])
    if not v["row_emphasis"]:
        return f"VERTICAL: {vertical} (no specific playbook — design from transcript)."
    lines = [
        f"VERTICAL PLAYBOOK · {vertical}",
        f"  Summary: {v['summary']}",
        f"  Row emphasis (suggested, override per transcript):",
    ]
    for r in v["row_emphasis"]:
        lines.append(f"    - {r}")
    lines.append("  Common pain themes to listen for:")
    for p in v["common_pain"]:
        lines.append(f"    - {p}")
    lines.append(f"  Typical AgentFleet picks: {', '.join(v['typical_agents'])}")
    return "\n".join(lines)


VERTICAL_NAMES = list(VERTICALS.keys())
