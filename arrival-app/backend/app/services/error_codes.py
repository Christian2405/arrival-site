"""
Static error code lookup — hardcoded from manufacturer documentation.
Instant answers without RAG latency. This is the fastest path for common error codes.

Usage:
    from app.services.error_codes import lookup_error_code
    result = lookup_error_code("Rheem furnace 3 blinks")
    if result:
        # Inject result into Claude prompt as context
        ...
"""

import re
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Error Code Database
# Compiled from manufacturer documentation, service manuals, and field experience.
# Format: { "brand_model_pattern": { "code": { "meaning": ..., "causes": [...], "action": ... } } }
# ---------------------------------------------------------------------------

RHEEM_FURNACE_BLINKS = {
    "1": {
        "meaning": "System lockout — retry.",
        "causes": [
            "System locked out after 3 failed ignition attempts",
            "Gas supply issue",
            "Igniter failure",
        ],
        "action": "Cycle power to reset. If it locks out again, check gas supply, igniter, and flame sensor.",
    },
    "2": {
        "meaning": "Pressure switch stuck closed.",
        "causes": [
            "Pressure switch contacts welded shut",
            "Wiring short to pressure switch",
            "Defective pressure switch",
        ],
        "action": "Check pressure switch — disconnect the hose and see if the switch opens. If stuck closed, replace it.",
    },
    "3": {
        "meaning": "Pressure switch fault — switch didn't close or opened during operation.",
        "causes": [
            "Plugged condensate drain (most common on 90%+ furnaces)",
            "Failed inducer motor or weak motor",
            "Cracked or water-logged hose from inducer to pressure switch",
            "Blocked flue or intake pipe",
            "Defective pressure switch",
        ],
        "action": "Check condensate drain first — blow out with compressed air. If clear, check inducer motor (listen for bearing noise), inspect hose for cracks or water. If all good, swap the pressure switch.",
    },
    "4": {
        "meaning": "High temperature limit switch open.",
        "causes": [
            "Dirty air filter (check this first)",
            "Blocked return air or closed registers",
            "Failed blower motor or weak capacitor",
            "Cracked heat exchanger",
        ],
        "action": "Replace filter, verify all registers are open, check blower operation. If limit keeps tripping with good airflow, suspect heat exchanger.",
    },
    "5": {
        "meaning": "Flame sensed when no flame should be present.",
        "causes": [
            "Leaking gas valve",
            "Short in flame sensor wiring",
            "Residual flame from slow gas shutoff",
        ],
        "action": "SAFETY CONCERN — shut off gas immediately. Check gas valve for leaks. Inspect flame sensor wiring for shorts to ground.",
    },
    "6": {
        "meaning": "Power or low voltage wiring issue.",
        "causes": [
            "Low voltage (check 24V transformer)",
            "Miswired thermostat",
            "Loose connections on control board",
        ],
        "action": "Check 24V transformer output. Verify thermostat wiring matches the board terminals. Check all connections on the control board.",
    },
    "7": {
        "meaning": "Gas valve circuit failure.",
        "causes": [
            "Failed gas valve",
            "Open circuit in gas valve wiring",
            "Control board failure",
        ],
        "action": "Check for 24V at the gas valve when calling for heat. If voltage present but valve doesn't open, replace gas valve. If no voltage, check board.",
    },
    "9": {
        "meaning": "Ignition failure — no flame detected after ignition trial.",
        "causes": [
            "Dirty flame sensor (most common)",
            "Gas supply off or low gas pressure",
            "Cracked igniter",
            "Gas valve failure",
        ],
        "action": "Clean flame sensor with fine emery cloth or steel wool first. Check gas supply and pressure. Inspect igniter for cracks.",
    },
    "10": {
        "meaning": "Polarity or grounding issue.",
        "causes": [
            "Hot and neutral reversed at furnace",
            "Poor chassis ground",
            "Floating neutral in panel",
        ],
        "action": "Check polarity at the furnace outlet — hot should be on the narrow blade. Verify good chassis ground. Check panel neutral.",
    },
}

CARRIER_FURNACE_CODES = {
    "11": {
        "meaning": "No previous error code history.",
        "causes": ["Normal — system has no stored faults"],
        "action": "No action needed. This is an informational code.",
    },
    "12": {
        "meaning": "Blower on after power up — blower running without a call for heat.",
        "causes": [
            "Control board detected heat in the heat exchanger at startup",
            "Thermostat calling for fan only",
            "Board issue",
        ],
        "action": "Check thermostat settings. If in heat mode, may indicate residual heat — wait for blower to shut off. If persistent, check board.",
    },
    "13": {
        "meaning": "Limit switch lockout — limit tripped 3 consecutive times.",
        "causes": [
            "Dirty filter",
            "Restricted ductwork",
            "Failed blower motor or weak capacitor",
            "Oversized furnace for ductwork",
        ],
        "action": "Replace filter. Check static pressure across furnace (should be under 0.5\" WC). Verify blower is running at correct speed. Check blower capacitor.",
    },
    "14": {
        "meaning": "Ignition lockout — failed to ignite after multiple attempts.",
        "causes": [
            "Dirty flame sensor (most common)",
            "Gas supply issue",
            "Weak or cracked igniter",
            "Gas valve failure",
        ],
        "action": "Clean flame sensor with emery cloth. Check gas supply and pressure. Inspect igniter. Cycle power to reset lockout.",
    },
    "21": {
        "meaning": "Gas heating lockout — unit locked out on failed ignition.",
        "causes": [
            "Same as code 14 — persistent ignition failure",
            "Intermittent gas supply",
        ],
        "action": "Same diagnostic as code 14. If keeps locking out after flame sensor cleaning, check gas pressure at manifold.",
    },
    "22": {
        "meaning": "Abnormal flame proving signal — flame detected without gas valve energized.",
        "causes": [
            "Leaking gas valve",
            "Flame sensor circuit shorted",
            "Residual heat in heat exchanger",
        ],
        "action": "SAFETY — check gas valve for internal leak. Inspect flame sensor wiring. Shut off gas if valve is leaking.",
    },
    "23": {
        "meaning": "Pressure switch didn't open during the off cycle.",
        "causes": [
            "Pressure switch stuck closed",
            "Wiring issue",
        ],
        "action": "Check pressure switch — disconnect hose and check if contacts open. Replace if stuck.",
    },
    "24": {
        "meaning": "Secondary voltage fuse blown.",
        "causes": [
            "Thermostat wire short",
            "Shorted component on 24V circuit",
            "Water damage to low voltage wiring",
        ],
        "action": "Check 3A fuse on board. Find and fix the short before replacing the fuse. Check thermostat wiring carefully.",
    },
    "31": {
        "meaning": "Pressure switch didn't close or opened during inducer operation.",
        "causes": [
            "Blocked flue or intake",
            "Failed inducer motor",
            "Plugged condensate drain/trap",
            "Disconnected or cracked pressure switch hose",
            "Defective pressure switch",
        ],
        "action": "Check flue and intake for blockages. Check condensate drain. Verify inducer is running. Inspect pressure switch hose.",
    },
    "33": {
        "meaning": "Limit switch or flame rollout switch open.",
        "causes": [
            "Dirty filter",
            "Blocked ductwork",
            "Failed blower",
            "Flame rollout — SERIOUS: possible cracked heat exchanger",
        ],
        "action": "If LIMIT: check filter and airflow. If FLAME ROLLOUT: do NOT reset — inspect heat exchanger for cracks. Rollout indicates combustion gases escaping.",
    },
    "34": {
        "meaning": "Ignition proving failure — flame lost after establishing.",
        "causes": [
            "Dirty flame sensor (most common on Carrier)",
            "Weak flame sensor signal",
            "Low gas pressure",
            "Poor ground wire to flame sensor",
        ],
        "action": "Clean flame sensor with fine emery cloth — this is the #1 cause on Carrier furnaces. Check sensor microamp reading (should be >1.5µA). Check ground wire.",
    },
    "41": {
        "meaning": "Blower motor fault — motor didn't reach target speed.",
        "causes": [
            "Failed blower motor",
            "Bad motor capacitor (PSC motors)",
            "Wiring issue between board and motor",
            "Dirty blower wheel causing excessive drag",
        ],
        "action": "Check blower motor capacitor first (PSC motors). On ECM motors, check for power at motor connector. Clean blower wheel if dirty.",
    },
    "42": {
        "meaning": "Inducer motor fault.",
        "causes": [
            "Failed inducer motor",
            "Blocked flue causing motor overload",
            "Bad inducer motor capacitor",
            "Wiring issue",
        ],
        "action": "Check inducer motor operation — listen for bearing noise. Check flue for blockages. On older units, check inducer capacitor.",
    },
    "44": {
        "meaning": "Blower running below target RPM.",
        "causes": [
            "Dirty blower wheel",
            "Ductwork restriction",
            "Failing motor bearings",
            "ECM motor fault",
        ],
        "action": "Clean blower wheel. Check static pressure. If motor is making noise, it's likely failing.",
    },
    "45": {
        "meaning": "Control circuitry lockout — board self-diagnostic failure.",
        "causes": [
            "Control board failure",
            "Power surge damage",
        ],
        "action": "Cycle power to attempt reset. If code persists, replace control board.",
    },
}

GOODMAN_FURNACE_BLINKS = {
    "1": {
        "meaning": "System lockout — retry after 1 hour or power cycle.",
        "causes": [
            "System locked out after repeated failed ignition attempts",
            "Gas supply issue",
            "Igniter/sensor failure",
        ],
        "action": "Cycle power to reset. If relocks out, check gas supply, igniter, and flame sensor.",
    },
    "2": {
        "meaning": "Pressure switch stuck closed.",
        "causes": [
            "Pressure switch contacts welded",
            "Wiring short",
        ],
        "action": "Check if pressure switch is stuck closed with inducer off. Replace if stuck.",
    },
    "3": {
        "meaning": "Pressure switch didn't close.",
        "causes": [
            "Plugged condensate drain",
            "Failed inducer motor",
            "Blocked flue/intake",
            "Cracked pressure switch hose",
        ],
        "action": "Check condensate drain and trap first. Check inducer operation. Inspect flue for blockages.",
    },
    "4": {
        "meaning": "High temperature limit switch open.",
        "causes": [
            "Dirty filter (most common)",
            "Blocked return air",
            "Failed blower motor or capacitor",
            "Cracked heat exchanger",
        ],
        "action": "Replace filter. Check blower operation and capacitor. If trips with clean filter and good airflow, suspect heat exchanger.",
    },
    "5": {
        "meaning": "Flame sensed without gas valve command.",
        "causes": [
            "Leaking gas valve",
            "Flame sensor wiring short",
        ],
        "action": "SAFETY — shut off gas. Check gas valve for internal leak.",
    },
    "6": {
        "meaning": "115V power or low voltage issue.",
        "causes": [
            "Power interruption",
            "24V transformer issue",
            "Loose connections",
        ],
        "action": "Check line voltage and 24V transformer output. Tighten all connections on board.",
    },
    "7": {
        "meaning": "Gas valve circuit error.",
        "causes": [
            "Failed gas valve",
            "Open wiring to gas valve",
            "Board failure",
        ],
        "action": "Check for 24V at gas valve during call for heat. If voltage present, replace gas valve.",
    },
    "8": {
        "meaning": "Igniter circuit issue.",
        "causes": [
            "Failed igniter (cracked or worn)",
            "Open circuit to igniter",
            "Board igniter relay failure",
        ],
        "action": "Check igniter resistance — should be 40-200 ohms for silicon carbide, 11-17 ohms for silicon nitride. Replace if out of range.",
    },
    "9": {
        "meaning": "No ignition — flame not detected during trial.",
        "causes": [
            "Dirty flame sensor",
            "No gas — supply off or low pressure",
            "Igniter not getting hot enough",
        ],
        "action": "Clean flame sensor. Check gas supply and pressure at manifold. Inspect igniter glow pattern.",
    },
}

LENNOX_FURNACE_CODES = {
    "E225": {
        "meaning": "Abnormal flame-proving signal.",
        "causes": [
            "Flame sensor issue",
            "Gas valve leaking",
            "Wiring fault",
        ],
        "action": "Check flame sensor circuit. Verify gas valve closes completely when not calling for heat.",
    },
    "E227": {
        "meaning": "Pressure switch didn't close.",
        "causes": [
            "Blocked condensate drain",
            "Failed inducer",
            "Blocked vent/intake",
            "Bad pressure switch or hose",
        ],
        "action": "Check condensate drain first. Verify inducer is running. Inspect vent for blockages.",
    },
    "E228": {
        "meaning": "Primary limit switch open.",
        "causes": [
            "Dirty filter (check first)",
            "Blocked return air",
            "Failed blower motor",
            "Cracked heat exchanger",
        ],
        "action": "Replace filter. Verify all registers are open. Check blower motor operation. If limit keeps tripping with good airflow, inspect heat exchanger.",
    },
    "E229": {
        "meaning": "Induced draft motor fault.",
        "causes": [
            "Failed inducer motor",
            "Blocked vent pipe",
            "Wiring issue to inducer",
        ],
        "action": "Check inducer motor operation. Inspect vent pipe for blockages. Check wiring connections.",
    },
    "E250": {
        "meaning": "Ignition lockout — failed to ignite.",
        "causes": [
            "Dirty flame sensor",
            "Gas supply issue",
            "Weak igniter",
            "Low gas pressure",
        ],
        "action": "Clean flame sensor. Check gas supply and manifold pressure. Inspect igniter. Cycle power to clear lockout.",
    },
    "E270": {
        "meaning": "Communication error between iComfort thermostat and furnace.",
        "causes": [
            "Wiring issue on communication bus",
            "Thermostat firmware issue",
            "Board communication failure",
        ],
        "action": "Check 4-wire communication cable between thermostat and furnace. Power cycle both. May need firmware update on thermostat.",
    },
    "E300": {
        "meaning": "High stage pressure switch fault.",
        "causes": [
            "Blocked condensate in high-fire mode",
            "Inducer not reaching high speed",
            "Vent sizing issue",
        ],
        "action": "Check condensate drain. Verify inducer reaches high speed. Review vent sizing for high-fire BTU input.",
    },
}

TRANE_FURNACE_BLINKS = {
    "1": {
        "meaning": "System normal — call for heat.",
        "causes": ["Normal operation — thermostat calling for heat"],
        "action": "No action needed. System is operating normally.",
    },
    "2": {
        "meaning": "System normal — no call for heat.",
        "causes": ["Normal standby operation"],
        "action": "No action needed. System is in standby.",
    },
    "3": {
        "meaning": "Pressure switch fault.",
        "causes": [
            "Plugged condensate drain",
            "Failed inducer motor",
            "Blocked vent",
            "Bad pressure switch or hose",
        ],
        "action": "Check condensate drain first. Verify inducer is running. Inspect vent and intake. Check pressure switch hose.",
    },
    "4": {
        "meaning": "High temperature limit open.",
        "causes": [
            "Dirty filter",
            "Restricted airflow",
            "Failed blower",
        ],
        "action": "Replace filter. Check airflow. Verify blower is running.",
    },
    "5": {
        "meaning": "Flame sensed with no call for heat.",
        "causes": [
            "Gas valve leaking",
            "Flame sensor shorted",
        ],
        "action": "SAFETY — shut off gas. Check gas valve for internal leak.",
    },
    "6": {
        "meaning": "Power or low voltage error.",
        "causes": [
            "Low voltage",
            "Transformer issue",
        ],
        "action": "Check 24V transformer. Check line voltage.",
    },
    "7": {
        "meaning": "Gas valve error.",
        "causes": [
            "Failed gas valve",
            "Wiring open",
        ],
        "action": "Check 24V at gas valve. Replace if energized but not opening.",
    },
    "9": {
        "meaning": "Ignition failure.",
        "causes": [
            "Dirty flame sensor",
            "Gas supply issue",
            "Igniter failure",
        ],
        "action": "Clean flame sensor. Check gas supply. Inspect igniter.",
    },
    "10": {
        "meaning": "Polarity/grounding issue.",
        "causes": [
            "Hot and neutral reversed",
            "Poor ground",
        ],
        "action": "Check outlet polarity. Verify proper ground.",
    },
}

RINNAI_TANKLESS_CODES = {
    "02": {
        "meaning": "Short circuit in the water flow control valve.",
        "causes": [
            "Failed flow control valve",
            "Wiring issue",
        ],
        "action": "Check wiring to flow control valve. Replace valve if wiring is good.",
    },
    "03": {
        "meaning": "Bath fill function communication error.",
        "causes": ["Bath fill adapter communication failure"],
        "action": "Check bath fill adapter connections. Reset unit.",
    },
    "05": {
        "meaning": "Temperature too high — exceeded safety limit.",
        "causes": [
            "Scale buildup restricting flow",
            "Flow sensor failure",
            "Recirculation pump set too high",
        ],
        "action": "Flush the heat exchanger with vinegar/descaler. Check flow rate. Verify recirculation pump speed.",
    },
    "10": {
        "meaning": "Blocked exhaust or air supply.",
        "causes": [
            "Blocked vent termination (bird nest, ice, debris)",
            "Vent pipe too long or too many elbows",
            "Condensate backup in vent",
        ],
        "action": "Inspect vent termination for blockages. Check vent length against installation manual limits. Check for condensate in vent pipe.",
    },
    "11": {
        "meaning": "No ignition — unit failed to light.",
        "causes": [
            "Gas supply valve closed",
            "Low gas pressure (need minimum 5\" WC for NG)",
            "Dirty flame rod",
            "Failed igniter",
            "Air in gas line (new installations)",
        ],
        "action": "Check gas supply valve is open. Check gas line pressure. Clean flame rod. If new install, purge air from gas line.",
    },
    "12": {
        "meaning": "Flame failure — flame detected then lost.",
        "causes": [
            "Wind or drafting issue at vent termination",
            "Dirty flame rod",
            "Low gas pressure (intermittent)",
            "Venting issue",
        ],
        "action": "Check vent termination for wind exposure. Clean flame rod. Check gas pressure under load. Inspect venting.",
    },
    "14": {
        "meaning": "Thermal fuse failure.",
        "causes": [
            "Overheating — scale buildup most common",
            "Thermal fuse tripped",
        ],
        "action": "MUST REPLACE thermal fuse. Flush heat exchanger before restarting — scale caused the overheat. Do not bypass fuse.",
    },
    "16": {
        "meaning": "Over temperature — water too hot.",
        "causes": [
            "Scale buildup restricting flow",
            "Low water flow rate",
            "Temperature sensor failure",
        ],
        "action": "Flush heat exchanger. Check water flow rate (minimum 0.4 GPM). Check inlet and outlet temperature sensors.",
    },
    "25": {
        "meaning": "Condensate drainage issue.",
        "causes": [
            "Blocked condensate drain line",
            "Neutralizer cartridge full",
        ],
        "action": "Clear condensate drain line. Replace neutralizer cartridge if equipped.",
    },
    "32": {
        "meaning": "Outgoing water temperature sensor failure.",
        "causes": [
            "Failed thermistor",
            "Wiring issue",
        ],
        "action": "Check thermistor resistance. Replace if out of spec.",
    },
    "61": {
        "meaning": "Combustion fan motor issue.",
        "causes": [
            "Failed fan motor",
            "Wiring issue",
            "Board failure",
        ],
        "action": "Check fan motor operation. Check wiring. If fan doesn't spin freely, replace motor.",
    },
    "65": {
        "meaning": "Water flow control valve issue.",
        "causes": [
            "Valve stuck or failed",
            "Scale buildup in valve",
        ],
        "action": "Descale valve. Replace if stuck.",
    },
    "79": {
        "meaning": "Fan current detection failure.",
        "causes": [
            "Fan motor deteriorating",
            "Board issue",
        ],
        "action": "Check fan motor current draw. Replace motor if high.",
    },
}

AO_SMITH_BLINKS = {
    "1": {
        "meaning": "Normal operation.",
        "causes": ["System operating normally"],
        "action": "No action needed.",
    },
    "2": {
        "meaning": "Thermopile voltage low.",
        "causes": [
            "Weak thermopile",
            "Poor flame contact with thermopile",
            "Bad gas control valve",
        ],
        "action": "Check thermopile millivolt output (should be >400mV open circuit, >250mV under load). Clean thermopile. Replace if weak.",
    },
    "4": {
        "meaning": "High temperature shutdown — ECO tripped.",
        "causes": [
            "Thermostat set too high",
            "Sediment buildup causing hot spots",
            "Failed thermostat (running away)",
            "Bad gas control valve",
        ],
        "action": "Turn off gas, wait 10 minutes, relight. If trips again, check thermostat setting (120°F standard), flush tank for sediment, then suspect gas valve.",
    },
    "5": {
        "meaning": "Sensor failure.",
        "causes": [
            "Failed temperature sensor/thermistor",
            "Wiring issue to sensor",
        ],
        "action": "Check sensor wiring connections. Replace sensor if connections are good.",
    },
    "7": {
        "meaning": "Gas control valve failure.",
        "causes": ["Internal gas control valve malfunction"],
        "action": "Replace gas control valve. Do not attempt to repair.",
    },
    "8": {
        "meaning": "Power supply issue (electronic ignition models).",
        "causes": [
            "Inadequate power supply",
            "Wiring issue",
        ],
        "action": "Check power supply voltage. Verify wiring.",
    },
}

DAIKIN_MINI_SPLIT_CODES = {
    "A1": {
        "meaning": "Indoor PCB defect.",
        "causes": ["Failed indoor unit control board"],
        "action": "Reset power. If persistent, replace indoor PCB.",
    },
    "A3": {
        "meaning": "Condensate drain level abnormal — drain pan full.",
        "causes": [
            "Clogged condensate drain line",
            "Drain pump failure",
            "Dirty or clogged drain pan",
        ],
        "action": "Clear condensate drain line. Check drain pump operation. Clean drain pan.",
    },
    "A5": {
        "meaning": "Freeze protection activated.",
        "causes": [
            "Dirty filter restricting airflow",
            "Low refrigerant charge",
            "Failed fan motor (low airflow)",
        ],
        "action": "Clean filters first. Check airflow. If filters are clean, check refrigerant charge.",
    },
    "A6": {
        "meaning": "Fan motor fault.",
        "causes": [
            "Failed indoor fan motor",
            "Wiring issue",
            "PCB fan output failure",
        ],
        "action": "Check fan motor operation. Check wiring. May need motor or PCB replacement.",
    },
    "C4": {
        "meaning": "Heat exchanger (liquid pipe) thermistor fault.",
        "causes": [
            "Failed thermistor",
            "Wiring issue",
        ],
        "action": "Check thermistor resistance against spec. Replace if out of range.",
    },
    "C9": {
        "meaning": "Suction air thermistor fault.",
        "causes": [
            "Failed thermistor",
            "Wiring issue",
        ],
        "action": "Check thermistor resistance. Replace if faulty.",
    },
    "E1": {
        "meaning": "Outdoor PCB defect.",
        "causes": ["Failed outdoor unit control board"],
        "action": "Reset power. If persistent, replace outdoor PCB.",
    },
    "E5": {
        "meaning": "Compressor overload (OL) protection activated.",
        "causes": [
            "Low refrigerant charge",
            "Dirty outdoor coil",
            "Failed outdoor fan",
            "Compressor failure",
        ],
        "action": "Clean outdoor coil. Check refrigerant charge. Verify outdoor fan is running. Check compressor amps.",
    },
    "E6": {
        "meaning": "Compressor lock / overcurrent.",
        "causes": [
            "Compressor failure (locked rotor)",
            "Low voltage",
            "Wiring issue",
        ],
        "action": "Check voltage at outdoor unit. Check compressor windings. If compressor is locked, replace.",
    },
    "E7": {
        "meaning": "Outdoor fan motor fault.",
        "causes": [
            "Failed outdoor fan motor",
            "Fan blade obstruction",
            "Wiring issue",
        ],
        "action": "Check for obstructions. Check fan motor operation. Replace if faulty.",
    },
    "F3": {
        "meaning": "Discharge pipe temperature too high.",
        "causes": [
            "Low refrigerant charge",
            "Restriction in refrigerant circuit",
            "Dirty outdoor coil",
            "Non-condensables in system",
        ],
        "action": "Check refrigerant charge. Clean outdoor coil. Check for restrictions. May need to recover, evacuate, and recharge.",
    },
    "F6": {
        "meaning": "High pressure protection activated.",
        "causes": [
            "Dirty outdoor coil",
            "Overcharge",
            "Outdoor fan not running",
            "Non-condensables",
        ],
        "action": "Clean outdoor coil. Check refrigerant charge. Verify outdoor fan operation.",
    },
    "H6": {
        "meaning": "Compressor position detection error.",
        "causes": [
            "Compressor failure",
            "Wiring issue between outdoor PCB and compressor",
        ],
        "action": "Check compressor wiring. Check voltage. May indicate compressor failure.",
    },
    "J3": {
        "meaning": "Discharge pipe thermistor fault.",
        "causes": [
            "Failed thermistor",
            "Wiring issue",
        ],
        "action": "Check thermistor resistance. Replace if out of range.",
    },
    "L4": {
        "meaning": "Inverter compressor overheat.",
        "causes": [
            "Dirty outdoor coil",
            "Low refrigerant",
            "Poor airflow over condenser",
        ],
        "action": "Clean outdoor coil. Check charge. Verify outdoor fan.",
    },
    "U0": {
        "meaning": "Low refrigerant or refrigerant shortage.",
        "causes": [
            "Refrigerant leak",
            "Undercharge",
        ],
        "action": "Leak check the system. Repair leak and recharge to nameplate spec.",
    },
    "U2": {
        "meaning": "Power supply abnormality (drop/instantaneous power failure).",
        "causes": [
            "Power supply voltage issue",
            "Unstable power",
        ],
        "action": "Check power supply voltage. May need dedicated circuit or voltage stabilizer.",
    },
    "U4": {
        "meaning": "Communication error between indoor and outdoor units.",
        "causes": [
            "Wiring fault between indoor and outdoor units",
            "Loose connections",
            "PCB failure (either unit)",
            "Power supply issue",
        ],
        "action": "Check wiring between indoor and outdoor units. Verify all connections are tight. Check for proper voltage at both units. Power cycle.",
    },
}

MITSUBISHI_MINI_SPLIT_CODES = {
    "E0": {
        "meaning": "Remote controller signal receiving error.",
        "causes": [
            "Remote controller malfunction",
            "Indoor unit receiver issue",
        ],
        "action": "Replace remote batteries. Check for IR signal interference. Try resetting the remote.",
    },
    "E6": {
        "meaning": "Indoor/outdoor communication error.",
        "causes": [
            "Wiring fault between units",
            "Loose connections at terminal blocks",
            "PCB failure",
            "Power surge damage",
        ],
        "action": "Check wiring between indoor and outdoor units. Verify all connections are tight at terminal blocks. Check for proper voltage at outdoor unit. Common after power surges.",
    },
    "E9": {
        "meaning": "Indoor/outdoor communication error (different from E6 on some models).",
        "causes": [
            "Communication cable fault",
            "Board failure",
        ],
        "action": "Same as E6 — check communication wiring. May need board replacement.",
    },
    "P1": {
        "meaning": "Intake sensor error.",
        "causes": [
            "Failed thermistor",
            "Wiring issue",
        ],
        "action": "Check thermistor resistance. Replace if out of spec.",
    },
    "P2": {
        "meaning": "Pipe (coil) sensor error.",
        "causes": [
            "Failed thermistor on coil",
            "Wiring issue",
        ],
        "action": "Check coil thermistor resistance against spec. Replace if faulty.",
    },
    "P8": {
        "meaning": "Pipe temperature error.",
        "causes": [
            "Refrigerant charge issue",
            "Restriction in system",
            "Thermistor reading abnormal temp",
        ],
        "action": "Check refrigerant charge. Check for restrictions. Verify thermistor readings.",
    },
    "U1": {
        "meaning": "High pressure protection.",
        "causes": [
            "Dirty outdoor coil",
            "Overcharge",
            "Outdoor fan failure",
            "Non-condensables in system",
        ],
        "action": "Clean outdoor coil. Check fan operation. Verify refrigerant charge.",
    },
    "U2": {
        "meaning": "Compressor overcurrent / abnormal.",
        "causes": [
            "Low refrigerant",
            "Compressor failure",
            "Electrical issue",
        ],
        "action": "Check refrigerant charge. Check compressor amp draw. Check voltage.",
    },
    "U5": {
        "meaning": "Abnormal indoor coil temperature (freeze protection).",
        "causes": [
            "Dirty filter",
            "Low refrigerant",
            "Indoor fan issue",
        ],
        "action": "Clean filters. Check refrigerant charge. Verify indoor fan operation.",
    },
}

# ---------------------------------------------------------------------------
# Brand aliases — maps variations to the canonical brand key
# ---------------------------------------------------------------------------

BRAND_ALIASES = {
    "rheem": "rheem",
    "ruud": "rheem",  # Same manufacturer
    "carrier": "carrier",
    "bryant": "carrier",  # Same parent company
    "payne": "carrier",  # Same parent company
    "goodman": "goodman",
    "amana": "goodman",  # Same manufacturer
    "lennox": "lennox",
    "trane": "trane",
    "american standard": "trane",  # Same manufacturer
    "rinnai": "rinnai",
    "ao smith": "ao_smith",
    "a.o. smith": "ao_smith",
    "a o smith": "ao_smith",
    "aosmith": "ao_smith",
    "daikin": "daikin",
    "mitsubishi": "mitsubishi",
    "fujitsu": "fujitsu",
}

# ---------------------------------------------------------------------------
# Brand → equipment type → code dictionary mapping
# ---------------------------------------------------------------------------

ERROR_CODE_DB = {
    "rheem": {
        "furnace": RHEEM_FURNACE_BLINKS,
    },
    "carrier": {
        "furnace": CARRIER_FURNACE_CODES,
    },
    "goodman": {
        "furnace": GOODMAN_FURNACE_BLINKS,
    },
    "lennox": {
        "furnace": LENNOX_FURNACE_CODES,
    },
    "trane": {
        "furnace": TRANE_FURNACE_BLINKS,
    },
    "rinnai": {
        "tankless": RINNAI_TANKLESS_CODES,
        "water heater": RINNAI_TANKLESS_CODES,
    },
    "ao_smith": {
        "water heater": AO_SMITH_BLINKS,
    },
    "daikin": {
        "mini split": DAIKIN_MINI_SPLIT_CODES,
        "minisplit": DAIKIN_MINI_SPLIT_CODES,
        "air conditioner": DAIKIN_MINI_SPLIT_CODES,
        "heat pump": DAIKIN_MINI_SPLIT_CODES,
    },
    "mitsubishi": {
        "mini split": MITSUBISHI_MINI_SPLIT_CODES,
        "minisplit": MITSUBISHI_MINI_SPLIT_CODES,
        "air conditioner": MITSUBISHI_MINI_SPLIT_CODES,
        "heat pump": MITSUBISHI_MINI_SPLIT_CODES,
    },
}

# Equipment type aliases
EQUIPMENT_ALIASES = {
    "furnace": "furnace",
    "heater": "furnace",
    "gas furnace": "furnace",
    "tankless": "tankless",
    "tankless water heater": "tankless",
    "water heater": "water heater",
    "mini split": "mini split",
    "mini-split": "mini split",
    "minisplit": "mini split",
    "ductless": "mini split",
    "air conditioner": "air conditioner",
    "ac": "air conditioner",
    "a/c": "air conditioner",
    "heat pump": "heat pump",
}

# Patterns to extract error codes from natural language queries
_CODE_PATTERNS = [
    # "error code 11", "fault code E228", "code 34"
    re.compile(r"(?:error|fault|diagnostic|status)\s*(?:code)?\s*#?\s*([A-Za-z]?\d+)", re.I),
    # "E228", "E6", "U4" (letter + number codes)
    re.compile(r"\b([A-Z]\d{1,3})\b"),
    # "blinking 3 times", "3 blinks", "flashing 3", "3 flashes"
    re.compile(r"(?:blink(?:ing|s)?|flash(?:ing|es)?)\s*(\d{1,2})\s*(?:times?)?", re.I),
    re.compile(r"(\d{1,2})\s*(?:blinks?|flash(?:es)?|times?)", re.I),
    # "code 34", "code E228"
    re.compile(r"code\s+([A-Za-z]?\d+)", re.I),
    # Just a number in context like "rheem 3" or "carrier 34"
    re.compile(r"(\d{1,3})$"),
]


def _extract_brand(text: str) -> str | None:
    """Try to find a brand name in the query text."""
    text_lower = text.lower()
    for alias, canonical in sorted(BRAND_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in text_lower:
            return canonical
    return None


def _extract_equipment_type(text: str) -> str | None:
    """Try to find equipment type in the query text."""
    text_lower = text.lower()
    for alias, canonical in sorted(EQUIPMENT_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in text_lower:
            return canonical
    return None


def _extract_code(text: str) -> str | None:
    """Try to extract an error/fault code from the query text."""
    for pattern in _CODE_PATTERNS:
        match = pattern.search(text)
        if match:
            return match.group(1).upper().lstrip("0") or "0"  # Normalize: strip leading zeros
    return None


def lookup_error_code(query: str) -> dict | None:
    """
    Look up an error code from natural language query.

    Returns:
        dict with keys: brand, equipment, code, meaning, causes, action
        None if no match found.

    Examples:
        lookup_error_code("Rheem furnace blinking 3 times")
        lookup_error_code("Carrier code 34")
        lookup_error_code("Rinnai tankless error 11")
        lookup_error_code("Daikin U4")
    """
    brand = _extract_brand(query)
    if not brand:
        return None

    code = _extract_code(query)
    if not code:
        return None

    equipment = _extract_equipment_type(query)

    # Look up in the database
    brand_db = ERROR_CODE_DB.get(brand, {})

    if equipment:
        # Try the specific equipment type
        equip_db = brand_db.get(equipment)
        if equip_db and code in equip_db:
            entry = equip_db[code]
            return {
                "brand": brand,
                "equipment": equipment,
                "code": code,
                **entry,
            }

    # Try all equipment types for this brand
    for equip_type, equip_db in brand_db.items():
        if code in equip_db:
            entry = equip_db[code]
            return {
                "brand": brand,
                "equipment": equip_type,
                "code": code,
                **entry,
            }

    return None


def format_error_code_context(result: dict) -> str:
    """
    Format an error code lookup result as context to inject into the Claude prompt.
    This gives Claude the exact answer so it doesn't have to guess.
    """
    brand_display = result["brand"].replace("_", " ").title()
    causes_list = "\n".join(f"  {i+1}. {c}" for i, c in enumerate(result["causes"]))

    return f"""## VERIFIED Error Code — Use This Exact Information
**{brand_display} {result['equipment'].title()} — Code {result['code']}**
Meaning: {result['meaning']}
Common causes (ranked by likelihood):
{causes_list}
Recommended action: {result['action']}

IMPORTANT: This error code data comes from the manufacturer's official documentation. Use this EXACT meaning and cause ranking in your response. Do NOT substitute a different meaning — this is the verified correct definition for this code. Lead with the meaning, then walk through the causes and diagnostic steps."""
