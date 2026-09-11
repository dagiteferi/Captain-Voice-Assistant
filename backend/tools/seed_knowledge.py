"""Seed the knowledge base with sample maritime operations documents.

Usage:
    python tools/seed_knowledge.py

Requires the backend to be running at http://localhost:8000.
Sends documents via the POST /api/v1/knowledge/documents endpoint.
"""

import httpx
import sys

BACKEND_URL = "http://localhost:8000"

SAMPLE_DOCUMENTS = [
    {
        "title": "Emergency Engine Shutdown Procedures",
        "content": (
            "Emergency Engine Shutdown Procedures for Vessel Alpha: "
            "1. Immediately notify the bridge of engine emergency. "
            "2. Press the Emergency Stop button located on the Main Engine Control Panel (MECP). "
            "3. Close the fuel supply valve by turning the red handle counter-clockwise until fully shut. "
            "4. Activate the emergency ventilation system to clear engine room of fumes. "
            "5. Engage the turning gear to prevent engine seizure during cooldown. "
            "6. Monitor all temperature gauges — if any reading exceeds 95°C, activate fire suppression. "
            "7. Log the shutdown time, reason, and all readings in the Engine Room Log Book. "
            "8. Do NOT attempt restart without Chief Engineer authorization."
        ),
    },
    {
        "title": "Fire Safety Protocol",
        "content": (
            "Fire Safety Protocol — All Vessels: "
            "Upon detecting fire or smoke: 1. Sound the general alarm (7 short blasts + 1 long). "
            "2. Report fire location, type, and severity to the bridge immediately. "
            "3. Activate fixed fire suppression (CO2 or foam) for the affected compartment. "
            "4. Close all ventilation dampers to the fire zone. "
            "5. Boundary cooling: apply water to adjacent bulkheads to prevent fire spread. "
            "6. Muster all crew at designated stations and conduct headcount. "
            "7. Prepare lifeboats for launch if fire cannot be controlled within 15 minutes. "
            "Fire extinguisher types: Class A (water) for solids, Class B (foam) for liquids, "
            "Class C (CO2) for electrical, Class D (dry powder) for metals."
        ),
    },
    {
        "title": "Navigation Watch Procedures",
        "content": (
            "Navigation Watch Standing Orders: "
            "The Officer of the Watch (OOW) must maintain a proper lookout at all times per COLREG Rule 5. "
            "Radar must be monitored continuously in restricted visibility. "
            "AIS (Automatic Identification System) shall remain active and transmitting. "
            "Course alterations greater than 10 degrees require Captain notification. "
            "Speed changes require Captain approval unless emergency collision avoidance. "
            "All vessel contacts within 5 nautical miles must be plotted and tracked. "
            "Weather updates must be logged every 4 hours. "
            "The OOW must never leave the bridge unattended without proper relief."
        ),
    },
    {
        "title": "Man Overboard (MOB) Procedures",
        "content": (
            "Man Overboard Recovery Procedure: "
            "1. Shout 'MAN OVERBOARD' and indicate port or starboard side. "
            "2. Throw the nearest lifebuoy with smoke signal and light. "
            "3. Press the MOB button on GPS to mark position. "
            "4. Sound 3 prolonged blasts on the ship's whistle. "
            "5. Execute the Williamson Turn: put the helm hard over to the side the person fell, "
            "then when 60 degrees off original course, shift helm hard the other way. "
            "6. Detail a lookout to maintain visual contact with the person. "
            "7. Prepare rescue boat for immediate launch. "
            "8. Reduce speed and approach the person from downwind. "
            "9. Use the rescue sling or scramble net for recovery."
        ),
    },
    {
        "title": "Fuel Bunkering Operations",
        "content": (
            "Fuel Bunkering Checklist and Procedures: "
            "Pre-bunkering: 1. Complete the bunkering safety checklist with the supplier. "
            "2. Verify fuel grade, quantity, and tank allocation. "
            "3. Close all non-essential overboard valves (scuppers, drains). "
            "4. Deploy oil spill containment equipment at manifold area. "
            "5. Ensure fire extinguishers are positioned at the manifold. "
            "During bunkering: Monitor tank levels continuously. "
            "Maximum fill level is 95% to allow for thermal expansion. "
            "Maintain radio communication with supplier on VHF Channel 69. "
            "Post-bunkering: Sound all tanks, calculate received quantity, sign BDN (Bunker Delivery Note)."
        ),
    },
    {
        "title": "Ballast Water Management",
        "content": (
            "Ballast Water Management Plan (per BWM Convention): "
            "All ballast water exchange must occur at least 200 nautical miles from shore "
            "and in water depth of at least 200 meters. "
            "Sequential exchange method: empty tank completely, then refill with ocean water. "
            "Flow-through method: pump 3 times the tank volume through the tank. "
            "Record all ballast operations in the Ballast Water Record Book. "
            "Ballast water treatment system must be operational before entering port waters. "
            "Report ballast water status to port authorities 24 hours before arrival."
        ),
    },
    {
        "title": "Cargo Loading Stability Calculations",
        "content": (
            "Cargo Loading and Stability Requirements: "
            "Before loading, verify the current displacement, trim, and GM (metacentric height). "
            "Minimum GM must be 0.15 meters for all loading conditions. "
            "Maximum deck cargo load per square meter is specified in the Capacity Plan. "
            "Loading sequence must follow the approved Cargo Securing Manual. "
            "Monitor draft readings forward, midship, and aft during loading. "
            "Calculate free surface effect for all partially filled tanks. "
            "Verify shear force and bending moment do not exceed hull design limits. "
            "The ship must meet the Intact Stability Criteria (IS Code) at all times."
        ),
    },
    {
        "title": "Bridge Communication Protocols",
        "content": (
            "Bridge Communication and Reporting Procedures: "
            "VHF Channel 16 is the international distress and calling frequency — monitor continuously. "
            "Channel 13 is for bridge-to-bridge navigation safety. "
            "GMDSS (Global Maritime Distress and Safety System) equipment must be tested daily. "
            "DSC (Digital Selective Calling) controller must have correct MMSI programmed. "
            "Position reports to company: every 6 hours via satellite or email. "
            "Arrival reports: 72h, 48h, 24h, and final ETA notices to port agent. "
            "All bridge communications must be logged with timestamp and operator name."
        ),
    },
    {
        "title": "Crew Rest Hours and Watchkeeping",
        "content": (
            "Crew Rest Hours (per MLC 2006 and STCW): "
            "Minimum rest: 10 hours in any 24-hour period, split into no more than 2 periods, "
            "one of which must be at least 6 consecutive hours. "
            "Minimum rest: 77 hours in any 7-day period. "
            "Watch schedules: 4 hours on, 8 hours off (standard three-watch system). "
            "The Master may suspend rest hour requirements in genuine emergency situations "
            "but must document the reason and restore normal rest as soon as practicable. "
            "Rest hour records must be maintained and available for inspection."
        ),
    },
    {
        "title": "Enclosed Space Entry Procedure",
        "content": (
            "Enclosed Space Entry Permit and Procedures: "
            "NEVER enter an enclosed space without a valid Enclosed Space Entry Permit. "
            "Atmosphere testing required: O2 must be 20.9% (±0.5%), "
            "H2S below 5 ppm, CO below 25 ppm, LEL below 1%. "
            "Continuous ventilation must run for at least 30 minutes before entry. "
            "A standby person must remain at the entrance at all times — never enter to rescue. "
            "Communication check between entrant and standby every 5 minutes. "
            "Emergency breathing apparatus (EEBA) must be available at the entrance. "
            "Rescue team must be on standby with SCBA and rescue equipment."
        ),
    },
    {
        "title": "Medical Emergency Response",
        "content": (
            "Medical Emergency Response at Sea: "
            "1. Assess the scene for safety before approaching the casualty. "
            "2. Check airway, breathing, circulation (ABC). "
            "3. Administer first aid per the Ship Captain's Medical Guide. "
            "4. Contact TMAS (Telemedical Maritime Assistance Service) on VHF or satellite phone. "
            "5. Prepare medical report: patient details, symptoms, vital signs, medications given. "
            "6. If evacuation needed, request MEDEVAC via Coast Guard on Channel 16. "
            "7. Prepare helicopter landing area (clear deck, secure loose items, fire crew standby). "
            "8. All medications administered must be logged in the Ship's Medical Log."
        ),
    },
    {
        "title": "Anchor Handling and Mooring",
        "content": (
            "Anchor Handling Procedures: "
            "Before anchoring: verify charted depth, bottom type, and swinging room. "
            "Approach the anchorage position heading into the wind or current (whichever is stronger). "
            "Let go anchor when vessel has slight sternway. "
            "Pay out cable: standard scope is 5-7 times the depth. "
            "After anchoring: take anchor bearings from at least 2 fixed objects. "
            "Set anchor watch alarm on radar (guard zone). "
            "Mooring: always use a minimum of 2 head lines, 2 stern lines, "
            "2 breast lines, and 2 spring lines for alongside berth."
        ),
    },
    {
        "title": "MARPOL Waste Management",
        "content": (
            "MARPOL Waste Disposal Regulations: "
            "Annex I (Oil): No oil discharge within 12 nm of land. Beyond 12 nm, "
            "oil content must be below 15 ppm using approved OWS (Oil-Water Separator). "
            "Annex IV (Sewage): Treated sewage may be discharged beyond 3 nm. "
            "Untreated sewage: only beyond 12 nm at speed > 4 knots. "
            "Annex V (Garbage): No plastic disposal at sea — EVER. "
            "Food waste: ground to < 25mm, only beyond 12 nm. "
            "All waste transfers must be recorded in the Garbage Record Book. "
            "Oil Record Book Part I (machinery) and Part II (cargo) must be maintained."
        ),
    },
    {
        "title": "Vessel Pre-Departure Checklist",
        "content": (
            "Pre-Departure Checklist: "
            "1. All crew aboard and accounted for (muster check). "
            "2. Navigation equipment tested: GPS, Radar, ECDIS, compass, AIS. "
            "3. Steering gear tested (full port to full starboard and return). "
            "4. Main engine tested ahead and astern. "
            "5. All watertight doors closed and tested. "
            "6. Cargo secured per the Cargo Securing Manual. "
            "7. Stability condition verified and approved by the Master. "
            "8. Passage plan reviewed and approved. "
            "9. Weather forecast reviewed — no adverse conditions expected. "
            "10. Port clearance documents obtained from authorities."
        ),
    },
    {
        "title": "Heavy Weather Preparation",
        "content": (
            "Heavy Weather Preparation Procedures: "
            "When storm warning received or significant weather deterioration expected: "
            "1. Alter course to reduce exposure if possible (avoid eye of storm). "
            "2. Reduce speed to prevent structural damage from wave impact. "
            "3. Secure all movable objects on deck and in holds. "
            "4. Close all weathertight doors, hatches, and ventilators. "
            "5. Check bilge alarm systems and ensure bilge pumps are operational. "
            "6. Ballast adjustments: increase draft and GM for better stability. "
            "7. Advise crew to use safety harnesses when moving on exposed decks. "
            "8. Increase engine room monitoring frequency."
        ),
    },
]


def main():
    print(f"Seeding {len(SAMPLE_DOCUMENTS)} maritime knowledge documents...")
    print(f"Backend URL: {BACKEND_URL}")

    with httpx.Client(timeout=30.0) as client:
        response = client.post(
            f"{BACKEND_URL}/api/v1/knowledge/documents",
            json={"documents": SAMPLE_DOCUMENTS},
            headers={
                "Content-Type": "application/json",
                "X-User-Role": "captain",
            },
        )

        if response.status_code == 201:
            data = response.json()
            print(f"\n✓ Successfully ingested {data['ingested_count']} documents!")
            print(f"  Document IDs: {data['document_ids'][:3]}... (and {len(data['document_ids']) - 3} more)")
        else:
            print(f"\n✗ Failed with status {response.status_code}")
            print(f"  Response: {response.text}")
            sys.exit(1)


if __name__ == "__main__":
    main()
