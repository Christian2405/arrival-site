"""
Quality Test Suite — 100 real trade scenario questions with expected answers.

Usage:
    python -m scripts.quality_test

    # Run only first N questions:
    python -m scripts.quality_test --count 10

    # Output to CSV:
    python -m scripts.quality_test --csv results.csv

Requires ANTHROPIC_API_KEY set in .env.
Sends each question through the actual chat pipeline and scores against expected answers.
"""

import asyncio
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app import config

# ---------------------------------------------------------------------------
# 100 Questions with Expected Answers
# Scoring: 3 = Correct & specific, 2 = Partial/vague, 1 = Wrong, 0 = Dangerous
# ---------------------------------------------------------------------------

QUESTIONS = [
    # ── HVAC — Error Codes ──────────────────────────────────────────────
    {
        "id": 1,
        "category": "HVAC - Error Codes",
        "question": "Rheem furnace blinking 3 times",
        "expected": "3 blinks = pressure switch fault. Check condensate drain first (clog is most common cause on 90%+ furnaces). If clear, check inducer motor and hose to pressure switch for cracks.",
        "must_contain": ["pressure switch", "condensate", "inducer"],
    },
    {
        "id": 2,
        "category": "HVAC - Error Codes",
        "question": "Carrier furnace code 34",
        "expected": "Code 34 = ignition proving failure (flame lost after ignition). Check flame sensor — clean with emery cloth. If sensor is clean, check gas valve, gas pressure, and ground wire to sensor.",
        "must_contain": ["ignition", "flame sensor"],
    },
    {
        "id": 3,
        "category": "HVAC - Error Codes",
        "question": "Lennox furnace flashing code E228",
        "expected": "E228 = primary limit switch open. Likely causes: dirty filter (check first), blocked return air, failed blower motor, or cracked heat exchanger.",
        "must_contain": ["limit switch", "filter"],
    },
    {
        "id": 4,
        "category": "HVAC - Error Codes",
        "question": "Goodman furnace blinking 4 times",
        "expected": "4 blinks = high temperature limit switch open. Check air filter first, then verify blower is running and all registers are open. If recurring, suspect cracked heat exchanger.",
        "must_contain": ["limit", "filter", "blower"],
    },
    {
        "id": 5,
        "category": "HVAC - Error Codes",
        "question": "Trane furnace flashing red 5 times",
        "expected": "5 red blinks = flame sensed with no call for heat. Gas valve may be leaking — shut off gas immediately. Could also be a stuck gas valve or wiring issue.",
        "must_contain": ["flame", "gas valve"],
    },
    {
        "id": 6,
        "category": "HVAC - Error Codes",
        "question": "Carrier furnace code 13",
        "expected": "Code 13 = limit switch lockout. Limit tripped 3 times. Check filter, ductwork, blower wheel, and blower capacitor. Could also indicate oversized furnace for the ductwork.",
        "must_contain": ["limit", "filter"],
    },
    {
        "id": 7,
        "category": "HVAC - Error Codes",
        "question": "Rinnai tankless error code 11",
        "expected": "Code 11 = no ignition. Check gas supply valve is open, check gas line pressure (minimum 5\" WC for NG), clean flame rod, check igniter. If recently installed, purge air from gas line.",
        "must_contain": ["ignition", "gas"],
    },
    {
        "id": 8,
        "category": "HVAC - Error Codes",
        "question": "Rinnai tankless error code 12",
        "expected": "Code 12 = flame failure (flame detected then lost). Check for wind/drafting issues, clean flame rod, check gas pressure. May need venting inspection.",
        "must_contain": ["flame", "gas pressure"],
    },
    {
        "id": 9,
        "category": "HVAC - Error Codes",
        "question": "Daikin mini split flashing green light",
        "expected": "Flashing green on indoor unit typically indicates normal operation/communication. Check the number of flashes and any error codes on the remote. If continuous rapid flashing, could be communication error between indoor and outdoor unit.",
        "must_contain": ["indoor", "outdoor"],
    },
    {
        "id": 10,
        "category": "HVAC - Error Codes",
        "question": "Mitsubishi mini split error code E6",
        "expected": "E6 = indoor/outdoor communication error. Check wiring between units, verify all connections are tight, check for proper voltage at outdoor unit. Common after power surges.",
        "must_contain": ["communication", "wiring"],
    },

    # ── HVAC — Diagnostics ──────────────────────────────────────────────
    {
        "id": 11,
        "category": "HVAC - Diagnostics",
        "question": "No cool call on a 10-year-old Carrier, what do I check first?",
        "expected": "Check the capacitor first — on a 10-year Carrier, the dual run capacitor is the #1 failure. Measure with a meter (should be within 10% of rated uF). If cap is good, check contactor (pitted contacts), then refrigerant charge.",
        "must_contain": ["capacitor", "contactor"],
    },
    {
        "id": 12,
        "category": "HVAC - Diagnostics",
        "question": "Trane heat pump runs but no heat, aux heat works fine",
        "expected": "Check reversing valve — listen for the click when switching modes. If no click, check 24V signal to valve solenoid. If signal present, valve is stuck. Also check outdoor coil for ice buildup (defrost board issue).",
        "must_contain": ["reversing valve"],
    },
    {
        "id": 13,
        "category": "HVAC - Diagnostics",
        "question": "AC compressor hums but won't start",
        "expected": "Hard start issue. Check the run capacitor first — weak cap is the most common cause. If cap is good, check for locked rotor (high amp draw). May need a hard start kit (SPP5/SPP6). Could also be a bad compressor.",
        "must_contain": ["capacitor"],
    },
    {
        "id": 14,
        "category": "HVAC - Diagnostics",
        "question": "Furnace igniter glows but no flame",
        "expected": "Gas valve not opening. Check 24V signal to gas valve. If 24V present, gas valve is bad. If no 24V, check flame sensor (dirty sensor can prevent valve from opening on retry). Also verify gas is on and pressure is correct.",
        "must_contain": ["gas valve", "24V"],
    },
    {
        "id": 15,
        "category": "HVAC - Diagnostics",
        "question": "Furnace short cycling — runs for 2 minutes then shuts off",
        "expected": "Likely high limit tripping. Check dirty filter first, then verify blower is at correct speed (should be on high for heat). Check ductwork for blockages. If filter and airflow are fine, suspect cracked heat exchanger.",
        "must_contain": ["limit", "filter", "airflow"],
    },
    {
        "id": 16,
        "category": "HVAC - Diagnostics",
        "question": "AC running but not cooling, suction line isn't cold",
        "expected": "Low refrigerant charge or compressor issue. Check pressures — if both sides are low, you have a leak. If suction is high and discharge is low, compressor is weak. Check for a frozen evaporator coil too.",
        "must_contain": ["refrigerant", "pressures"],
    },
    {
        "id": 17,
        "category": "HVAC - Diagnostics",
        "question": "Indoor blower motor won't turn on, thermostat calling for fan",
        "expected": "Check blower capacitor first (most common). Then check for 120V at motor leads. If voltage present and motor is hot, motor is bad. If no voltage, check control board — fan relay may be failed.",
        "must_contain": ["capacitor", "control board"],
    },
    {
        "id": 18,
        "category": "HVAC - Diagnostics",
        "question": "Thermostat blank, no power",
        "expected": "Check for 24V at thermostat R terminal. If no voltage, check transformer — should have 24V on secondary. If transformer output is 0V, check primary 120V input. Also check for a blown 3A fuse on the control board.",
        "must_contain": ["24V", "transformer"],
    },
    {
        "id": 19,
        "category": "HVAC - Diagnostics",
        "question": "Condenser fan not spinning but compressor running",
        "expected": "Fan motor or capacitor. Try spinning the blade manually — if it starts and keeps running, capacitor is bad. If it won't start or overheats quickly, motor is bad. Don't let compressor run long without condenser fan — head pressure will spike.",
        "must_contain": ["capacitor", "motor"],
    },
    {
        "id": 20,
        "category": "HVAC - Diagnostics",
        "question": "Ductless mini split leaking water from indoor unit",
        "expected": "Clogged condensate drain line is the most common cause. Pull the filters and check the drain pan. Blow out the drain line with nitrogen or compressed air. On Mitsubishi/Fujitsu units, check the drain pump if equipped.",
        "must_contain": ["condensate", "drain"],
    },

    # ── HVAC — Refrigerant & Charging ───────────────────────────────────
    {
        "id": 21,
        "category": "HVAC - Refrigerant",
        "question": "What superheat should I target on a fixed orifice system?",
        "expected": "10-15F superheat. Measure suction line temp at the service valve, subtract the saturated suction temp from your gauge reading. High superheat = undercharged or restricted metering. Low superheat = overcharged or poor airflow.",
        "must_contain": ["10", "15", "superheat"],
    },
    {
        "id": 22,
        "category": "HVAC - Refrigerant",
        "question": "What subcooling should I target on a TXV system?",
        "expected": "8-12F subcooling. Measure liquid line temp at the service valve, subtract from the saturated liquid temp on your high-side gauge. Low subcooling = undercharged. High subcooling = overcharged or restricted.",
        "must_contain": ["subcooling", "8", "12"],
    },
    {
        "id": 23,
        "category": "HVAC - Refrigerant",
        "question": "R-410A normal operating pressures on a 95 degree day?",
        "expected": "Roughly 120-130 PSI suction side and 340-380 PSI discharge side at 95F ambient. Exact pressures depend on indoor wet bulb and system design. Always check manufacturer specs.",
        "must_contain": ["120", "350"],
    },
    {
        "id": 24,
        "category": "HVAC - Refrigerant",
        "question": "Customer has an R-22 system that's low on charge. What are my options?",
        "expected": "R-22 is phased out. Options: 1) Top off with reclaimed R-22 (expensive, $50-100/lb). 2) Retrofit to R-407C (closest drop-in, requires oil change to POE). 3) Replace the system — usually the best long-term option if the unit is over 10 years old.",
        "must_contain": ["phased out", "R-407C"],
    },
    {
        "id": 25,
        "category": "HVAC - Refrigerant",
        "question": "How do I find a refrigerant leak?",
        "expected": "Start with a visual inspection — look for oil stains at joints and connections. Electronic leak detector is fastest for finding the general area. Confirm with soap bubbles or dye test. Common leak points: service valves, flare fittings, evaporator coil, condenser coil.",
        "must_contain": ["leak detector", "oil"],
    },

    # ── Electrical — Wire Sizing ────────────────────────────────────────
    {
        "id": 26,
        "category": "Electrical - Wire Sizing",
        "question": "What size wire do I need for a 50-amp circuit, 100-foot run?",
        "expected": "6 AWG copper for 50A per NEC, but at 100ft you need to account for voltage drop — go to 4 AWG. Use THHN in conduit or 6/3 NM-B if allowed by local code.",
        "must_contain": ["6 AWG", "4 AWG", "voltage drop"],
    },
    {
        "id": 27,
        "category": "Electrical - Wire Sizing",
        "question": "What size wire for a 40 amp circuit?",
        "expected": "8 AWG copper, 40A breaker, THHN in conduit. For NM-B (Romex), use 8/3 with ground.",
        "must_contain": ["8 AWG"],
    },
    {
        "id": 28,
        "category": "Electrical - Wire Sizing",
        "question": "What size wire for a 100 amp sub panel, 75 foot run?",
        "expected": "3 AWG copper or 1 AWG aluminum for 100A. At 75ft, voltage drop is borderline — you may want to bump to 2 AWG copper. Don't forget the ground wire and a main breaker in the sub panel.",
        "must_contain": ["3 AWG", "100"],
    },
    {
        "id": 29,
        "category": "Electrical - Wire Sizing",
        "question": "What breaker size for a 240V electric water heater?",
        "expected": "Most residential electric water heaters are 4500W at 240V = 18.75A. NEC requires 125% for continuous loads = 23.4A. Use a 30A 2-pole breaker with 10 AWG wire.",
        "must_contain": ["30A", "10 AWG"],
    },
    {
        "id": 30,
        "category": "Electrical - Wire Sizing",
        "question": "What's the max distance for 14 AWG on a 15-amp circuit before voltage drop is a problem?",
        "expected": "About 50 feet one-way for 3% voltage drop on a 15A circuit with 14 AWG copper. Beyond that, bump up to 12 AWG. NEC recommends keeping voltage drop under 3% for branch circuits.",
        "must_contain": ["50", "voltage drop"],
    },

    # ── Electrical — Panels & Breakers ──────────────────────────────────
    {
        "id": 31,
        "category": "Electrical - Panels",
        "question": "Square D QO vs Homeline — what's the difference?",
        "expected": "QO is commercial-grade — better trip curves, Visi-Trip indicator, higher interrupting capacity (10kA vs 22kA). Homeline is residential/budget. Don't mix them — different bus bar clips.",
        "must_contain": ["commercial", "trip"],
    },
    {
        "id": 32,
        "category": "Electrical - Panels",
        "question": "Can I put a tandem breaker in any slot?",
        "expected": "No — only in slots rated for tandems. Check the panel door label for which slots accept tandem/half-size breakers. On Square D QO panels, tandems only go in specific bottom slots. Putting them in wrong slots is a code violation.",
        "must_contain": ["slot", "code"],
    },
    {
        "id": 33,
        "category": "Electrical - Panels",
        "question": "How do I test a GFCI breaker?",
        "expected": "Press the TEST button on the breaker — it should trip immediately. If it doesn't trip, the breaker is bad. Also test with a GFCI tester at the outlet. For troubleshooting nuisance trips: disconnect the neutral and check for ground faults on the circuit.",
        "must_contain": ["test button", "trip"],
    },
    {
        "id": 34,
        "category": "Electrical - Panels",
        "question": "Why does my AFCI breaker keep tripping?",
        "expected": "Common causes: 1) Shared neutral with another circuit. 2) Old wiring with loose connections (arcing). 3) Certain appliances cause false trips (vacuums, treadmills). Check all connections in the circuit for tightness. Try disconnecting loads one at a time to isolate.",
        "must_contain": ["neutral", "arcing"],
    },
    {
        "id": 35,
        "category": "Electrical - Panels",
        "question": "How do I check a capacitor with a multimeter?",
        "expected": "Disconnect power, discharge cap (short terminals with insulated screwdriver). Set meter to uF (capacitance). Read across terminals. Compare to rating on cap — should be within 10%. If no uF setting, use ohms — needle should swing then return to infinity.",
        "must_contain": ["discharge", "uF"],
    },

    # ── Plumbing — Water Heaters ────────────────────────────────────────
    {
        "id": 36,
        "category": "Plumbing - Water Heaters",
        "question": "AO Smith water heater status light blinking 4 times",
        "expected": "4 blinks = high temperature shutdown / ECO tripped. Turn gas off, wait 10 minutes, relight. If it trips again, check thermostat setting, sediment buildup (flush the tank), then suspect a bad gas valve.",
        "must_contain": ["ECO", "temperature"],
    },
    {
        "id": 37,
        "category": "Plumbing - Water Heaters",
        "question": "Water heater pilot won't stay lit",
        "expected": "Most common cause is a bad thermocouple — it's not generating enough millivolts to hold the gas valve open. Replace the thermocouple ($10 part). If new thermocouple doesn't fix it, the gas valve may be bad.",
        "must_contain": ["thermocouple"],
    },
    {
        "id": 38,
        "category": "Plumbing - Water Heaters",
        "question": "What temperature should a residential water heater be set to?",
        "expected": "120F is the standard for residential. Prevents scalding and saves energy. 140F if there's a commercial dishwasher or the customer wants hotter water (use a mixing valve at that temp).",
        "must_contain": ["120"],
    },
    {
        "id": 39,
        "category": "Plumbing - Water Heaters",
        "question": "How do I flush a tankless water heater?",
        "expected": "Close isolation valves, connect a pump and two hoses to service ports, run white vinegar through the heat exchanger for 45-60 minutes. Then flush with clean water. Rinnai and Navien recommend annual descaling.",
        "must_contain": ["vinegar", "pump"],
    },
    {
        "id": 40,
        "category": "Plumbing - Water Heaters",
        "question": "Tankless water heater giving lukewarm water",
        "expected": "Check for scale buildup in the heat exchanger — descale if overdue. Check the inlet filter/screen for debris. Verify gas pressure is correct. If it's a Rinnai with crossover, check the recirculation valve.",
        "must_contain": ["scale", "heat exchanger"],
    },

    # ── Plumbing — General ──────────────────────────────────────────────
    {
        "id": 41,
        "category": "Plumbing - General",
        "question": "What size gas line for a tankless water heater?",
        "expected": "Minimum 3/4\" gas line for most residential tankless units. Some high-output units (199k BTU) need 1\". Run length matters — check the manufacturer's spec for your unit's BTU rating and pipe run.",
        "must_contain": ["3/4", "BTU"],
    },
    {
        "id": 42,
        "category": "Plumbing - General",
        "question": "How do I solder copper pipe?",
        "expected": "Clean the fitting and pipe with emery cloth until shiny. Apply flux. Heat the fitting (not the solder) with a torch until the solder flows by capillary action. Use lead-free solder on potable water. Wipe the joint with a damp rag.",
        "must_contain": ["flux", "lead-free", "fitting"],
    },
    {
        "id": 43,
        "category": "Plumbing - General",
        "question": "PEX-A vs PEX-B — which should I use?",
        "expected": "PEX-A is more flexible, can use expansion fittings (full flow, no restriction), and has thermal memory (kinks can be fixed with a heat gun). PEX-B is stiffer, uses crimp rings, and is cheaper. For repipes, PEX-A with expansion is the better choice.",
        "must_contain": ["expansion", "crimp"],
    },
    {
        "id": 44,
        "category": "Plumbing - General",
        "question": "What's the minimum slope for a drain line?",
        "expected": "1/4 inch per foot for pipes 3\" and smaller. 1/8 inch per foot for 4\" and larger. This is per UPC/IPC code.",
        "must_contain": ["1/4"],
    },
    {
        "id": 45,
        "category": "Plumbing - General",
        "question": "Garbage disposal is humming but not spinning",
        "expected": "Jammed flywheel. Turn power off, use the hex key (Allen wrench) in the bottom of the unit to manually turn the flywheel. If no Allen key, use a broom handle from the top to push the impellers. Reset the button on the bottom.",
        "must_contain": ["hex key", "flywheel"],
    },

    # ── Electrical — Troubleshooting ────────────────────────────────────
    {
        "id": 46,
        "category": "Electrical - Troubleshooting",
        "question": "How do I trace a dead circuit?",
        "expected": "Start at the panel — verify the breaker is on and has proper voltage (120V L-N or 240V L-L). If panel voltage is good, check the first device on the circuit. Look for a tripped GFCI upstream. Check for burnt wire nuts or backstab connections.",
        "must_contain": ["panel", "GFCI"],
    },
    {
        "id": 47,
        "category": "Electrical - Troubleshooting",
        "question": "Outlet reads 0 volts but breaker isn't tripped",
        "expected": "Check for a tripped GFCI upstream — could be in the garage, bathroom, or exterior. Check for a loose neutral at the panel or first junction box. Backstab connections fail frequently — check for pushed-in wires that have worked loose.",
        "must_contain": ["GFCI", "neutral"],
    },
    {
        "id": 48,
        "category": "Electrical - Troubleshooting",
        "question": "Lights flickering throughout the house",
        "expected": "If it's all circuits, check the main breaker connections and the utility connection at the meter. Could be a loose neutral at the meter base or the utility drop. If only one circuit, check connections at the panel and first device. Call the utility to check their side if main connections look good.",
        "must_contain": ["neutral", "meter"],
    },
    {
        "id": 49,
        "category": "Electrical - Troubleshooting",
        "question": "How do I wire a 3-way switch?",
        "expected": "Power goes to the common terminal on the first switch. Travelers (usually red and white with black tape) connect between the two switches on the brass terminals. The second switch common goes to the light. Ground both switches.",
        "must_contain": ["common", "travelers"],
    },
    {
        "id": 50,
        "category": "Electrical - Troubleshooting",
        "question": "How do I test for a bootleg ground?",
        "expected": "A bootleg ground is when someone jumpers the neutral to ground at the outlet — a standard tester will show correct wiring. Use a tester with a GFCI test button or an impedance tester. On a bootleg ground, the GFCI test will fail because neutral and ground are the same.",
        "must_contain": ["neutral", "ground", "GFCI"],
    },

    # ── HVAC — Equipment Knowledge ──────────────────────────────────────
    {
        "id": 51,
        "category": "HVAC - Equipment",
        "question": "What's the difference between a single-stage and two-stage furnace?",
        "expected": "Single-stage has one heat output — full blast or off. Two-stage has high and low fire. Low fire runs most of the time (more efficient, more even heat, quieter). High fire kicks in on cold days. Two-stage is worth the upgrade for comfort.",
        "must_contain": ["high", "low", "comfort"],
    },
    {
        "id": 52,
        "category": "HVAC - Equipment",
        "question": "What does AFUE mean and what's a good number?",
        "expected": "Annual Fuel Utilization Efficiency — how much heat per dollar of gas. 80% = standard efficiency. 90%+ = high efficiency (condensing furnace with PVC exhaust). 96-98% is top of the line. Below 80% is an older model worth replacing.",
        "must_contain": ["efficiency", "80", "90"],
    },
    {
        "id": 53,
        "category": "HVAC - Equipment",
        "question": "How do I read a Carrier model number to find the tonnage?",
        "expected": "Look for the 3-digit number in the model string — divide by 12 to get tons. Example: 24ACC636 — 636 divided by 12 = 3 tons (technically the 36 in positions 7-8 = 36,000 BTU = 3 tons). On some models, look for 24, 30, 36, 42, 48, 60 in the model number.",
        "must_contain": ["12", "BTU", "ton"],
    },
    {
        "id": 54,
        "category": "HVAC - Equipment",
        "question": "What's a communicating thermostat and do I need one?",
        "expected": "Communicating systems use a data bus instead of standard 24V wires — the thermostat, furnace, and outdoor unit talk to each other digitally. Trane ComfortLink, Carrier Infinity, and Lennox iComfort are examples. You MUST use the matching thermostat — can't use a standard one.",
        "must_contain": ["communicating", "data"],
    },
    {
        "id": 55,
        "category": "HVAC - Equipment",
        "question": "Goodman vs Carrier — which is better?",
        "expected": "Different markets. Carrier has better build quality and longer track record in premium installs. Goodman is budget-friendly with widely available parts — great for rental properties and price-sensitive jobs. Both make reliable equipment when installed correctly. Installation quality matters more than brand.",
        "must_contain": ["installation", "quality"],
    },

    # ── HVAC — Installation & Best Practices ────────────────────────────
    {
        "id": 56,
        "category": "HVAC - Installation",
        "question": "What's the correct static pressure for a residential furnace?",
        "expected": "Total external static pressure should be 0.5\" WC or less for most residential furnaces. Measure at the supply and return plenum with a manometer. High static (over 0.7\") means undersized ductwork, dirty filter, or restrictive coil.",
        "must_contain": ["0.5", "static", "ductwork"],
    },
    {
        "id": 57,
        "category": "HVAC - Installation",
        "question": "How do I size ductwork for a 3-ton system?",
        "expected": "3 tons = 1200 CFM (400 CFM/ton). Return trunk should be at least 20x20 or 20\" round. Supply trunk 18x18 minimum. Use a duct calculator or Manual D for branch runs. 6\" flex for 100 CFM per run, 7\" for 125 CFM.",
        "must_contain": ["1200", "CFM", "400"],
    },
    {
        "id": 58,
        "category": "HVAC - Installation",
        "question": "How many CFM per ton for cooling?",
        "expected": "400 CFM per ton is the standard rule. So a 3-ton system needs 1200 CFM, 4-ton needs 1600 CFM. Verify with a flow hood or static pressure test. Low airflow causes frozen coils and poor efficiency.",
        "must_contain": ["400", "CFM"],
    },
    {
        "id": 59,
        "category": "HVAC - Installation",
        "question": "What's the minimum clearance for a furnace exhaust vent?",
        "expected": "For 90%+ furnaces (PVC vent): 12\" from any window, door, or air intake per most codes. 3' above any forced air intake within 10'. For 80% furnaces (metal B-vent): 1' above the roofline and follow B-vent clearance tables for combustibles.",
        "must_contain": ["12", "PVC"],
    },
    {
        "id": 60,
        "category": "HVAC - Installation",
        "question": "How do I properly charge a mini split after installation?",
        "expected": "Weigh in the charge — don't rely on superheat/subcooling alone on mini splits. Factory charge covers 25ft of lineset. For longer runs, add refrigerant per the manufacturer's chart (usually specified per additional foot). Verify charge with subcooling method.",
        "must_contain": ["weigh", "lineset"],
    },

    # ── Plumbing — Drain & Sewer ────────────────────────────────────────
    {
        "id": 61,
        "category": "Plumbing - Drain",
        "question": "What size drain line for a bathroom group?",
        "expected": "3\" minimum for a toilet (water closet). 1-1/2\" for a lavatory. 2\" for a shower. The vent for the toilet should be 2\" minimum. All per UPC/IPC.",
        "must_contain": ["3\"", "toilet"],
    },
    {
        "id": 62,
        "category": "Plumbing - Drain",
        "question": "How do I clear a main sewer line?",
        "expected": "Use a drain machine with a 3/4\" or 1\" cable. Go through the main cleanout. Feed cable until you feel resistance, then work through the blockage. If the cable won't clear it, camera the line — could be root intrusion or a broken pipe.",
        "must_contain": ["cable", "cleanout", "camera"],
    },
    {
        "id": 63,
        "category": "Plumbing - Drain",
        "question": "What causes a sewer smell in the house?",
        "expected": "Dry P-trap is the most common cause — run water in all drains that aren't used regularly. Also check for cracked vent pipes in the attic, bad wax ring on the toilet, or a missing cleanout cap. Check any floor drains in the basement.",
        "must_contain": ["P-trap", "wax ring"],
    },
    {
        "id": 64,
        "category": "Plumbing - Drain",
        "question": "What's the maximum distance from a fixture to its vent?",
        "expected": "Depends on pipe size. 1-1/4\" = 5 feet, 1-1/2\" = 6 feet (UPC) or 5 feet (IPC), 2\" = 8 feet, 3\" = 12 feet. These are developed (actual pipe length) distances. Beyond this, you get siphoning problems.",
        "must_contain": ["feet", "pipe size"],
    },
    {
        "id": 65,
        "category": "Plumbing - Drain",
        "question": "How do I install a cleanout?",
        "expected": "Install at the base of each soil/waste stack and at every change of direction greater than 45 degrees. Use a wye fitting with a cleanout plug. Make sure it's accessible — can't bury it in a wall without an access panel. Cleanout should face the direction of flow.",
        "must_contain": ["wye", "accessible"],
    },

    # ── Gas Work ────────────────────────────────────────────────────────
    {
        "id": 66,
        "category": "Gas",
        "question": "How do I test gas lines for leaks?",
        "expected": "Pressure test with a manometer or gauge. Bring the system to test pressure (typically 3 PSI for low-pressure residential) and hold for 15 minutes with no drop. Can also use soap bubbles or electronic leak detector on individual fittings.",
        "must_contain": ["pressure", "manometer"],
    },
    {
        "id": 67,
        "category": "Gas",
        "question": "What size gas pipe for a 200,000 BTU furnace, 30-foot run?",
        "expected": "At 30 feet with 200k BTU on natural gas (0.5\" WC drop), you need at least 1\" black iron pipe. Check IFGC Table 402.4 or the gas pipe sizing chart for your local code. CSST may need a larger size depending on the brand.",
        "must_contain": ["1\"", "black iron"],
    },
    {
        "id": 68,
        "category": "Gas",
        "question": "How do I measure gas pressure at a furnace?",
        "expected": "Use a manometer on the pressure tap at the gas valve. Natural gas should read 3.5\" WC inlet pressure (7\" WC for LP). With all appliances running, if inlet drops below 3\" WC, the supply line is undersized or there's a restriction.",
        "must_contain": ["manometer", "3.5", "WC"],
    },
    {
        "id": 69,
        "category": "Gas",
        "question": "What's the difference between natural gas and propane for furnaces?",
        "expected": "Different orifice sizes — propane runs at higher pressure (11\" WC vs 3.5\" WC) with smaller orifices. Most furnaces can be converted with a LP conversion kit. Gas valve must be adjusted. Never run NG orifices on LP — it will overheat.",
        "must_contain": ["orifice", "pressure"],
    },
    {
        "id": 70,
        "category": "Gas",
        "question": "How do I properly purge a gas line?",
        "expected": "After cutting in new work, open the furthest fixture from the meter and let gas push the air out. Use a combustible gas detector at the purge point — when it reads gas, close it up. Never purge into a confined space or near ignition sources.",
        "must_contain": ["purge", "air"],
    },

    # ── Building & Construction ─────────────────────────────────────────
    {
        "id": 71,
        "category": "Building",
        "question": "How do I find a wall stud?",
        "expected": "Stud finder is fastest. Otherwise: knock on the wall (solid sound = stud). Electrical outlets are typically nailed to a stud — check which side. Standard spacing is 16\" on center, sometimes 24\" OC. Measure 16\" from a corner to find the first stud.",
        "must_contain": ["16\"", "stud finder"],
    },
    {
        "id": 72,
        "category": "Building",
        "question": "What size header for a 6-foot opening in a load-bearing wall?",
        "expected": "For a 6-foot span in a load-bearing wall, typical is a double 2x10 or double 2x12 depending on the load above and local code. Always verify with a structural engineer for load-bearing modifications. LVL beams are another option for longer spans.",
        "must_contain": ["2x10", "2x12"],
    },
    {
        "id": 73,
        "category": "Building",
        "question": "How do I level a bathroom floor for tile?",
        "expected": "Pour self-leveling compound. Clean and prime the subfloor first. Mix SLC to the right consistency (pourable). Pour and spread with a gauge rake. For low spots over 1/4\", may need multiple pours. Check with a straightedge — should be within 1/8\" in 10 feet for tile.",
        "must_contain": ["self-leveling", "straightedge"],
    },
    {
        "id": 74,
        "category": "Building",
        "question": "What's the R-value I need for attic insulation?",
        "expected": "R-38 to R-60 depending on climate zone. Zone 1-3 (south): R-38 minimum. Zone 4-8 (north): R-49 to R-60. Check your local energy code. Most existing homes have R-19 or less — adding blown-in fiberglass or cellulose is the cheapest upgrade.",
        "must_contain": ["R-38", "R-49"],
    },
    {
        "id": 75,
        "category": "Building",
        "question": "How do I repair a small drywall hole?",
        "expected": "For fist-sized holes: cut a piece of drywall slightly larger. Cut a clean square around the hole with a drywall saw. Cut backing strips from wood or use a California patch. Screw new drywall to the backing. Tape, mud, and sand — three coats.",
        "must_contain": ["backing", "tape", "mud"],
    },

    # ── Mini Splits ─────────────────────────────────────────────────────
    {
        "id": 76,
        "category": "HVAC - Mini Splits",
        "question": "What's the maximum lineset length for a Mitsubishi mini split?",
        "expected": "Depends on the model, but most residential Mitsubishi units allow up to 65-100 feet with a maximum elevation difference of 33 feet. Check the specific model's installation manual. Longer runs require additional refrigerant charge.",
        "must_contain": ["65", "feet", "refrigerant"],
    },
    {
        "id": 77,
        "category": "HVAC - Mini Splits",
        "question": "How do I vacuum and purge a mini split lineset?",
        "expected": "After brazing the connections, pull a vacuum with a micron gauge — hold 500 microns or below for at least 15 minutes. If it rises, you have a leak. Never purge with the factory charge — that's wasteful and illegal (R-410A). After good vacuum, open the service valves to release the factory charge.",
        "must_contain": ["vacuum", "micron", "500"],
    },
    {
        "id": 78,
        "category": "HVAC - Mini Splits",
        "question": "Mini split outdoor unit is making a loud humming noise",
        "expected": "Check the compressor mounting bolts — they can loosen over time. Check for debris in the fan. Listen for bearing noise in the fan motor. Could also be refrigerant noise (restriction) — check pressures. On inverter units, a harmonic hum at certain speeds can be normal.",
        "must_contain": ["compressor", "fan"],
    },
    {
        "id": 79,
        "category": "HVAC - Mini Splits",
        "question": "How many indoor heads can I run on a multi-zone mini split?",
        "expected": "Depends on the outdoor unit capacity. Most residential multi-zone systems support 2-5 indoor heads. Don't exceed the combined capacity of the outdoor unit. Mitsubishi MXZ series goes up to 5 zones. Total connected capacity can be 100-130% of outdoor unit rating.",
        "must_contain": ["outdoor unit", "zones"],
    },
    {
        "id": 80,
        "category": "HVAC - Mini Splits",
        "question": "What causes ice on a mini split outdoor unit in heating mode?",
        "expected": "Normal in heating mode — the outdoor coil acts as an evaporator and will frost up. The defrost cycle should clear it every 30-90 minutes. If ice doesn't clear, check the defrost board, reversing valve, outdoor thermistor, or low refrigerant charge.",
        "must_contain": ["defrost", "normal"],
    },

    # ── Commercial HVAC ─────────────────────────────────────────────────
    {
        "id": 81,
        "category": "HVAC - Commercial",
        "question": "What's the difference between a rooftop unit and a split system?",
        "expected": "Rooftop unit (RTU) is self-contained — everything in one box on the roof. Split system separates the condenser (outside) and air handler (inside). RTUs are easier to install but harder to service on the roof. Split systems are more common in residential and light commercial.",
        "must_contain": ["rooftop", "self-contained"],
    },
    {
        "id": 82,
        "category": "HVAC - Commercial",
        "question": "How often should commercial HVAC filters be changed?",
        "expected": "Every 1-3 months depending on the environment. Restaurants and shops with high traffic: monthly. Offices: every 2-3 months. Use a manometer to measure pressure drop across the filter — replace when it reaches the manufacturer's recommended max.",
        "must_contain": ["monthly", "pressure"],
    },
    {
        "id": 83,
        "category": "HVAC - Commercial",
        "question": "What's an economizer and how does it work?",
        "expected": "An economizer uses outside air for free cooling when conditions are right — typically when outdoor temp is below the return air temp (usually below 65-70F). Damper opens to bring in cool outside air and modulates based on a sensor. Saves energy by reducing compressor run time.",
        "must_contain": ["outside air", "damper"],
    },
    {
        "id": 84,
        "category": "HVAC - Commercial",
        "question": "What's a VRF system?",
        "expected": "Variable Refrigerant Flow — commercial version of a mini split on steroids. One large outdoor unit, multiple indoor units, and a branch controller. Can heat and cool simultaneously in different zones. Daikin, Mitsubishi, and LG are the major brands. Expensive but very efficient.",
        "must_contain": ["variable", "refrigerant", "zones"],
    },
    {
        "id": 85,
        "category": "HVAC - Commercial",
        "question": "How do I check a belt on an AHU?",
        "expected": "Check tension — should deflect about 1\" per foot of span when you push with your thumb. Check for cracks, glazing, or fraying on the belt surface. Check alignment of the pulleys with a straightedge. Misaligned pulleys eat belts fast. Replace in matched sets on multi-belt drives.",
        "must_contain": ["tension", "alignment"],
    },

    # ── Safety Scenarios ────────────────────────────────────────────────
    {
        "id": 86,
        "category": "Safety",
        "question": "I smell gas in the basement near the furnace",
        "expected": "Don't flip any switches or create sparks. Open windows for ventilation. Shut off the gas at the meter if you can reach it safely. Check the gas connections at the furnace with soap bubbles or a leak detector. If the smell is strong, evacuate and call the gas company.",
        "must_contain": ["evacuate", "gas"],
    },
    {
        "id": 87,
        "category": "Safety",
        "question": "Found aluminum wiring in an older house — what do I do?",
        "expected": "Aluminum wiring (pre-1972) is a fire hazard at connections due to oxidation and expansion. Options: 1) COPALUM crimp connectors (best, requires certified installer). 2) AlumiConn connectors (DIY-friendly). 3) Complete rewire (expensive but permanent). Don't use wire nuts — they're not rated for aluminum-to-copper.",
        "must_contain": ["aluminum", "COPALUM"],
    },
    {
        "id": 88,
        "category": "Safety",
        "question": "Can I work on a live 240V panel?",
        "expected": "You can, but you shouldn't unless absolutely necessary. If you must: use properly rated PPE (Class 00 gloves minimum), stand on a rubber mat, use insulated tools, and work with one hand. Best practice is always to de-energize and LOTO. Know your arc flash boundaries.",
        "must_contain": ["PPE", "de-energize"],
    },
    {
        "id": 89,
        "category": "Safety",
        "question": "How do I test for carbon monoxide from a furnace?",
        "expected": "Use a combustion analyzer in the flue. CO should be below 100 PPM in the flue on a properly tuned furnace (ideally below 50 PPM). Check ambient CO in the room with a separate CO detector — anything above 9 PPM ambient is a problem. Check the heat exchanger for cracks.",
        "must_contain": ["combustion analyzer", "PPM"],
    },
    {
        "id": 90,
        "category": "Safety",
        "question": "Water heater T&P valve is leaking — can I cap it off?",
        "expected": "NEVER cap a T&P (temperature and pressure) relief valve — it's a critical safety device that prevents the tank from exploding. If it's dripping, either the water temperature is too high, water pressure is too high (check expansion tank), or the valve itself is bad. Replace the valve, don't cap it.",
        "must_contain": ["never", "safety", "replace"],
    },

    # ── General Knowledge ───────────────────────────────────────────────
    {
        "id": 91,
        "category": "General",
        "question": "What's the best brand of furnace to install?",
        "expected": "Installation quality matters more than brand. That said: Carrier/Bryant are reliable workhorses. Trane is built heavy (commercial quality). Lennox is quiet but finicky. Goodman is great for budget jobs. Rheem is solid mid-range. Pick what your supply house stocks well for parts availability.",
        "must_contain": ["installation"],
    },
    {
        "id": 92,
        "category": "General",
        "question": "How do I calculate heat load for a house?",
        "expected": "Manual J calculation is the proper way — accounts for square footage, insulation, windows, climate zone, and orientation. Quick rule of thumb: 25-30 BTU per square foot in northern climates, 20-25 in southern. A 2000 sqft house in the north might need 50-60k BTU furnace.",
        "must_contain": ["Manual J", "BTU", "square foot"],
    },
    {
        "id": 93,
        "category": "General",
        "question": "What's the most common reason for a service call on a furnace?",
        "expected": "Dirty filter — by far. Causes high limit trips, short cycling, reduced airflow, and frozen evap coils in cooling. Second most common is a dirty flame sensor. Third is igniter failure. These three cover probably 60% of residential furnace calls.",
        "must_contain": ["dirty filter", "flame sensor"],
    },
    {
        "id": 94,
        "category": "General",
        "question": "How do I read an electrical meter with a clamp?",
        "expected": "Open the jaws, clamp around a SINGLE conductor (not the whole cable — that would read 0 due to opposing fields). Set to AC amps. The reading is the current flowing through that wire. For DC circuits, use a DC clamp meter. Keep the wire centered in the jaws for accuracy.",
        "must_contain": ["single conductor", "amps"],
    },
    {
        "id": 95,
        "category": "General",
        "question": "What tools should every HVAC tech have?",
        "expected": "Essentials: digital manifold gauges, multimeter with clamp, combustion analyzer, manometer, refrigerant scale, vacuum pump with micron gauge, leak detector, temperature probes, and a good set of hand tools. Nice to have: thermal camera, psychrometer, and a borescope for heat exchanger inspection.",
        "must_contain": ["manifold", "multimeter", "combustion analyzer"],
    },

    # ── Scenario Questions ──────────────────────────────────────────────
    {
        "id": 96,
        "category": "Scenario",
        "question": "Customer says their AC is blowing warm air and it was working fine yesterday",
        "expected": "Most likely the outdoor unit isn't running. Check if the condenser is running — if the fan and compressor are both off, check the disconnect and breaker. If the fan runs but compressor doesn't, check the capacitor and compressor. If everything looks like it's running, check refrigerant pressures.",
        "must_contain": ["outdoor unit", "capacitor"],
    },
    {
        "id": 97,
        "category": "Scenario",
        "question": "I'm getting a call back on a furnace I installed last week — no heat",
        "expected": "On a new install callback: check thermostat wiring first (common to have a wrong wire on the terminal strip). Verify gas is on and the gas valve is open. Check the error codes on the board. Make sure the vent is clear and the condensate drain is properly installed with a trap.",
        "must_contain": ["wiring", "thermostat"],
    },
    {
        "id": 98,
        "category": "Scenario",
        "question": "Customer complains about high energy bills after new AC installation",
        "expected": "Check the refrigerant charge — over or undercharge kills efficiency. Verify ductwork connections are sealed (new install can knock ducts loose). Check static pressure — if the system is fighting ductwork, it runs longer. Verify the system is sized correctly (Manual J). Check the programmable thermostat settings.",
        "must_contain": ["charge", "ductwork", "static pressure"],
    },
    {
        "id": 99,
        "category": "Scenario",
        "question": "Water damage on the ceiling below a bathroom — what's the source?",
        "expected": "Common sources: toilet wax ring (check for rocking), shower pan or curb (run the shower for 20 min and check), supply line connections, bathtub overflow, or a drain leak. Toilets and shower pans are the most common. Check for soft or discolored subfloor around the toilet base.",
        "must_contain": ["wax ring", "shower pan"],
    },
    {
        "id": 100,
        "category": "Scenario",
        "question": "How do I troubleshoot a zone control system where one zone isn't getting heat?",
        "expected": "Check the zone damper — listen for it opening when the zone calls for heat. Check for 24V at the zone board for that zone. If the damper has power but isn't opening, the damper motor is bad. If no power, check the zone thermostat and the zone board. Bypass the zone board to test if the issue is the board or the damper.",
        "must_contain": ["damper", "zone board"],
    },
]


async def run_test(count: int | None = None, csv_path: str | None = None):
    """Send each question through the AI and score the response."""
    from app.services.anthropic import chat_with_claude

    questions = QUESTIONS[:count] if count else QUESTIONS
    results = []
    total_score = 0
    total_possible = len(questions) * 3

    print(f"\n{'='*80}")
    print(f"  ARRIVAL AI QUALITY TEST — {len(questions)} Questions")
    print(f"{'='*80}\n")

    for i, q in enumerate(questions):
        print(f"[{i+1}/{len(questions)}] Q: {q['question']}")

        t0 = time.time()
        try:
            result = await chat_with_claude(
                message=q["question"],
                max_tokens=1024,
            )
            response = result.get("response", "")
            elapsed = time.time() - t0

            # Score the response
            response_lower = response.lower()
            keywords_found = sum(1 for kw in q["must_contain"] if kw.lower() in response_lower)
            keywords_total = len(q["must_contain"])

            if keywords_found == keywords_total:
                score = 3  # All key concepts present
            elif keywords_found >= keywords_total * 0.5:
                score = 2  # Partial — has some key concepts
            elif keywords_found > 0:
                score = 1  # Mostly wrong but not dangerous
            else:
                score = 1  # No key concepts found

            # Check for dangerous advice
            dangerous_phrases = [
                "cap the t&p", "cap the relief", "bypass the safety",
                "jump the limit", "leave it jumped", "ignore the code",
            ]
            if any(dp in response_lower for dp in dangerous_phrases):
                score = 0  # Dangerous advice

            total_score += score

            score_label = {3: "CORRECT", 2: "PARTIAL", 1: "WRONG", 0: "DANGEROUS"}[score]
            print(f"  A: {response[:150]}{'...' if len(response) > 150 else ''}")
            print(f"  Score: {score}/3 ({score_label}) | Keywords: {keywords_found}/{keywords_total} | {elapsed:.1f}s")
            print()

            results.append({
                "id": q["id"],
                "category": q["category"],
                "question": q["question"],
                "expected": q["expected"],
                "actual": response,
                "score": score,
                "score_label": score_label,
                "keywords_found": keywords_found,
                "keywords_total": keywords_total,
                "elapsed_seconds": round(elapsed, 1),
            })

        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({
                "id": q["id"],
                "category": q["category"],
                "question": q["question"],
                "expected": q["expected"],
                "actual": f"ERROR: {e}",
                "score": 0,
                "score_label": "ERROR",
                "keywords_found": 0,
                "keywords_total": len(q["must_contain"]),
                "elapsed_seconds": 0,
            })
            print()

    # Summary
    avg_score = total_score / len(questions) if questions else 0
    print(f"\n{'='*80}")
    print(f"  RESULTS SUMMARY")
    print(f"{'='*80}")
    print(f"  Total Score: {total_score}/{total_possible} ({avg_score:.2f}/3.00 average)")
    print(f"  Correct (3):   {sum(1 for r in results if r['score'] == 3)}")
    print(f"  Partial (2):   {sum(1 for r in results if r['score'] == 2)}")
    print(f"  Wrong (1):     {sum(1 for r in results if r['score'] == 1)}")
    print(f"  Dangerous (0): {sum(1 for r in results if r['score'] == 0)}")
    print(f"  Errors:        {sum(1 for r in results if r['score_label'] == 'ERROR')}")
    print()

    # Category breakdown
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"total": 0, "count": 0}
        categories[cat]["total"] += r["score"]
        categories[cat]["count"] += 1

    print("  By Category:")
    for cat, data in sorted(categories.items()):
        avg = data["total"] / data["count"]
        print(f"    {cat}: {avg:.2f}/3.00 ({data['count']} questions)")

    # Write CSV if requested
    if csv_path:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=results[0].keys())
            writer.writeheader()
            writer.writerows(results)
        print(f"\n  Results written to {csv_path}")

    print()
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Arrival AI quality test")
    parser.add_argument("--count", type=int, help="Number of questions to test (default: all)")
    parser.add_argument("--csv", type=str, help="Output results to CSV file")
    args = parser.parse_args()

    asyncio.run(run_test(count=args.count, csv_path=args.csv))
