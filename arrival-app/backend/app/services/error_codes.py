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
    "11": {
        "meaning": "Rollout switch open — flames detected outside the combustion chamber.",
        "causes": [
            "Cracked or failed heat exchanger (MOST SERIOUS — primary cause)",
            "Blocked flue or vent pipe causing backdrafting",
            "Blocked heat exchanger cells (debris or scale buildup)",
            "Rollout switch failed (less common)",
        ],
        "action": "SAFETY — do NOT reset the rollout switch without a thorough inspection. Inspect the heat exchanger for cracks — use a mirror and flashlight, or run a combustion analyzer and check for elevated CO in the supply air duct. Check the flue pipe for blockages. If the heat exchanger is cracked, shut the furnace down and condemn it or replace the heat exchanger. A cracked heat exchanger can leak carbon monoxide.",
    },
    "12": {
        "meaning": "Blower motor on after power up — residual heat detected in the heat exchanger.",
        "causes": [
            "Control board detected elevated temperature at startup and ran the blower to dissipate heat",
            "Limit switch was closed at power-up indicating heat still present",
            "Thermostat set to fan ON (not auto) keeping blower running",
        ],
        "action": "This is typically informational — the board ran the blower to clear residual heat. Check thermostat fan setting (should be AUTO not ON). If this code appears repeatedly, verify that the furnace is actually shutting down normally between cycles (check gas valve is closing). Usually no repair needed.",
    },
    "13": {
        "meaning": "Limit circuit lockout — high temperature limit tripped 3 consecutive times.",
        "causes": [
            "Dirty or clogged air filter (check this FIRST — most common cause)",
            "Blocked or closed supply/return registers",
            "Failed blower motor or weak blower capacitor (not moving enough air)",
            "Undersized or restricted ductwork",
            "Dirty blower wheel reducing air volume",
        ],
        "action": "Replace the air filter immediately. Open all supply and return registers. Check blower motor operation — verify it's running at the correct speed. Check blower capacitor (PSC motors: measure µF, must be within 5% of rating). Measure total external static pressure (should be under 0.5\" WC). If static is high with a clean filter, ductwork may be undersized. Clean blower wheel if dirty.",
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
    "32": {
        "meaning": "Low flame signal — microamp reading below threshold during operation.",
        "causes": [
            "Dirty flame sensor (most common — carbon buildup on sensor rod)",
            "Poor ground connection to flame sensor or furnace chassis",
            "Low gas pressure at manifold (below nameplate spec)",
            "Cracked flame sensor insulator",
        ],
        "action": "Clean flame sensor rod with fine emery cloth or Scotch-Brite — remove carbon buildup. Check microamp reading (should be >1.5µA, ideally >2.0µA). Verify solid ground wire from sensor bracket to chassis. Check manifold gas pressure with a manometer. If sensor is clean and grounded but reading is still low, replace the flame sensor.",
    },
    "43": {
        "meaning": "Check gas valve connection — control board not detecting proper gas valve circuit.",
        "causes": [
            "Loose or disconnected wiring at gas valve terminals",
            "Gas valve coil open circuit (failed valve)",
            "Control board gas valve driver circuit failure",
        ],
        "action": "Check wiring connections at the gas valve — push connectors firmly onto spade terminals. Measure gas valve coil resistance (typically 15-100 ohms depending on model). If coil is open (infinite resistance), replace gas valve. If coil is good and wiring is tight, suspect control board.",
    },
    "46": {
        "meaning": "Gas valve (GV) circuit fault — abnormal current flow in gas valve circuit.",
        "causes": [
            "Gas valve coil partially shorted (drawing excessive current)",
            "Wiring short between gas valve leads",
            "Control board gas valve relay or triac failure",
        ],
        "action": "Measure gas valve coil resistance — compare to manufacturer spec. Check gas valve wiring for shorts (inspect wire insulation for damage, especially near hot surfaces). If valve coil resistance is out of spec, replace gas valve. If wiring and valve are good, replace control board.",
    },
    "131": {
        "meaning": "115VAC power issue — line voltage problem detected (Infinity/Greenspeed models).",
        "causes": [
            "Line voltage out of acceptable range (too high or too low)",
            "Loose wiring at line voltage connections on control board",
            "Shared circuit causing voltage fluctuations under load",
        ],
        "action": "Measure line voltage at the furnace disconnect and at the control board terminal — should be 108-132VAC. Check for loose connections on line voltage terminals. Ensure furnace is on a dedicated circuit. If voltage is consistently low, the utility feed may need attention.",
    },
    "132": {
        "meaning": "115VAC power issue during last heat demand — voltage dropped during furnace operation (Infinity/Greenspeed models).",
        "causes": [
            "Voltage dropped below threshold when blower or igniter energized (high current draw event)",
            "Undersized circuit wiring causing voltage drop under load",
            "Loose neutral or hot connection causing intermittent voltage drop",
            "Shared circuit with other equipment causing voltage sag",
        ],
        "action": "Measure voltage at the furnace while it is running (not just at idle). Check voltage during igniter operation (igniter draws 3-7 amps and can cause a voltage dip). Tighten all wire connections at the disconnect and breaker. Verify wire gauge is adequate for the circuit length. Ensure furnace is not sharing a circuit with other high-draw equipment.",
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
    "E220": {
        "meaning": "High limit fault in low fire — heat exchanger overheating at low stage.",
        "causes": [
            "Dirty air filter restricting airflow (most common)",
            "Blower motor not ramping to correct low-fire speed",
            "Partially blocked return air or closed registers",
            "Dirty blower wheel reducing air volume",
        ],
        "action": "Replace air filter. Verify blower is running at the correct low-fire speed (check DIP switch or control board speed settings). Ensure all registers are open and return air is unobstructed. Clean blower wheel if dirty.",
    },
    "E221": {
        "meaning": "High limit fault in high fire — heat exchanger overheating at high stage.",
        "causes": [
            "Dirty air filter (most common)",
            "Blower motor not reaching high-fire speed (bad capacitor, failing motor)",
            "Severely restricted ductwork or undersized duct system",
            "Dirty or damaged blower wheel",
        ],
        "action": "Replace air filter. Check blower capacitor (PSC motors) or ECM motor operation. Measure static pressure — should be under 0.5\" WC total. If static is high with clean filter, ductwork is undersized. Clean blower wheel.",
    },
    "E222": {
        "meaning": "Rollout switch open — flames rolling out of combustion chamber.",
        "causes": [
            "Cracked or failed heat exchanger (SERIOUS — most common cause)",
            "Blocked flue or vent pipe",
            "Blocked heat exchanger passages (scale or debris)",
            "Oversized gas orifice causing excessive flame",
        ],
        "action": "SAFETY — do NOT reset the rollout switch without thorough inspection. Inspect heat exchanger for cracks using a mirror and flashlight, or a combustion analyzer checking for elevated CO in the supply air. Check flue pipe for blockages. If heat exchanger is cracked, unit should be shut down and heat exchanger or furnace replaced.",
    },
    "E230": {
        "meaning": "Blower motor fault — motor failed to start or not running at correct speed.",
        "causes": [
            "Failed blower motor (most common)",
            "Bad motor run capacitor (PSC motors)",
            "Wiring fault between control board and motor",
            "Control board blower relay or motor output failure",
        ],
        "action": "Check blower motor capacitor first on PSC motors (measure microfarads — must be within 5% of rating). On ECM motors, check for power at motor plug from the board. Spin blower by hand to check for free rotation. If motor hums but won't spin, capacitor or motor has failed.",
    },
    "E231": {
        "meaning": "Blower motor overcurrent — motor drawing excessive amps.",
        "causes": [
            "Dirty blower wheel causing excessive drag (most common)",
            "Failing motor bearings (grinding noise)",
            "Blower running against excessively restricted ductwork",
            "Motor winding partially shorted",
        ],
        "action": "Clean blower wheel thoroughly — excessive dirt buildup is the #1 cause. Listen for bearing noise and check for shaft play. Measure motor amp draw against nameplate rating. Check static pressure for ductwork restrictions. If motor is pulling high amps with clean wheel and reasonable static pressure, motor is failing.",
    },
    "E241": {
        "meaning": "Low flame signal — flame sensor not detecting adequate flame.",
        "causes": [
            "Dirty flame sensor rod (carbon buildup — most common)",
            "Poor ground connection on flame sensor circuit",
            "Low gas pressure at manifold",
            "Cracked flame sensor porcelain insulator",
        ],
        "action": "Clean flame sensor with fine emery cloth or Scotch-Brite pad — remove all carbon buildup from the rod. Check microamp reading (should be >2µA). Verify solid ground wire. Check gas pressure at manifold with a manometer. If clean sensor still reads low, replace the flame sensor.",
    },
    "E251": {
        "meaning": "Ignition retry lockout — unit failed to ignite after maximum retries.",
        "causes": [
            "Dirty flame sensor (most common — unit ignites but loses flame)",
            "Gas supply issue (valve off, low pressure, air in line)",
            "Failed or weak hot surface igniter",
            "Gas valve not opening (failed valve or wiring issue)",
        ],
        "action": "Clean flame sensor first. Check gas supply — verify manual shutoff valve is open and measure manifold pressure. Inspect hot surface igniter for cracks (they often crack invisibly — measure resistance: 40-200Ω for silicon carbide, 11-17Ω for silicon nitride). Cycle power to clear lockout, then monitor ignition sequence.",
    },
    "E260": {
        "meaning": "Gas valve relay failure — control board cannot energize the gas valve.",
        "causes": [
            "Control board gas valve relay failed (most common)",
            "Gas valve coil open circuit",
            "Wiring fault between board and gas valve",
        ],
        "action": "Check for 24V at the gas valve terminals during a call for heat. If no voltage, the board relay has likely failed — replace the control board. If voltage is present but valve won't open, measure gas valve coil resistance. Replace gas valve if coil is open.",
    },
    "E290": {
        "meaning": "Transformer fault — low voltage transformer issue detected.",
        "causes": [
            "24V transformer failing or output voltage too low",
            "Excessive load on 24V circuit (shorted thermostat wire, failed component)",
            "Loose connections at transformer terminals",
        ],
        "action": "Measure transformer secondary output — should be 24-28VAC under load. Check for shorts on the 24V circuit (disconnect thermostat wires and re-measure). Tighten connections at transformer terminals. If output is low with no load, replace the transformer.",
    },
    "E311": {
        "meaning": "Outdoor temperature sensor fault — sensor used for heat pump defrost and staging (heat pump models).",
        "causes": [
            "Failed outdoor temperature thermistor (open or shorted)",
            "Wiring damage from UV exposure or rodent chewing",
            "Corroded connections at the outdoor sensor plug",
        ],
        "action": "Locate outdoor temp sensor (usually clipped to the outdoor coil or liquid line). Check wiring for physical damage. Measure thermistor resistance and compare to manufacturer temp/resistance chart. Replace if out of range. Check connector for corrosion.",
    },
    "E320": {
        "meaning": "Low compressor suction pressure — pressure dropped below safety threshold (heat pump models).",
        "causes": [
            "Low refrigerant charge (leak in system — most common)",
            "Dirty or iced-over outdoor coil in heat mode",
            "Failed defrost control (coil staying iced)",
            "Restriction in refrigerant circuit (plugged filter-drier or TXV)",
        ],
        "action": "Check outdoor coil for ice buildup — if heavily iced, verify defrost board and defrost sensor are working. Check refrigerant charge — connect gauges and look for low suction pressure. If charge is low, leak check the system (check service valves, indoor coil, line set connections). Check filter-drier for restriction (temp drop across it indicates blockage).",
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
    "19": {
        "meaning": "Electrical grounding issue — unit detecting improper ground.",
        "causes": [
            "Missing or poor ground connection at the power supply",
            "Ground wire disconnected inside the unit",
            "GFCI outlet tripping intermittently (if unit is on GFCI circuit)",
        ],
        "action": "Verify the unit has a solid ground connection at the outlet/disconnect. Check the ground wire inside the unit at the PCB. If unit is on a GFCI circuit, the GFCI may be tripping — Rinnai recommends a dedicated non-GFCI circuit. Measure resistance from unit chassis to ground.",
    },
    "25": {
        "meaning": "Condensate drain blocked — condensate not draining properly (condensing models).",
        "causes": [
            "Blocked condensate drain line (most common)",
            "Condensate neutralizer cartridge full or clogged",
            "Frozen condensate drain line (cold climate installations)",
        ],
        "action": "Clear condensate drain line — disconnect and flush with water. Check neutralizer cartridge and replace if full (typically every 1-2 years). In cold climates, ensure drain line is insulated and routed to prevent freezing. Check for proper slope on drain line.",
    },
    "29": {
        "meaning": "Condensate neutralizer issue — problem with neutralizer assembly (condensing models).",
        "causes": [
            "Neutralizer cartridge spent/exhausted",
            "Neutralizer assembly clogged with scale or debris",
            "Neutralizer drain hose kinked or blocked",
        ],
        "action": "Replace the condensate neutralizer cartridge. Flush the neutralizer assembly with clean water. Check drain hose routing for kinks. Verify proper flow from the neutralizer to the drain.",
    },
    "31": {
        "meaning": "Incoming (cold) water temperature sensor fault.",
        "causes": [
            "Failed inlet water temperature thermistor (open or shorted)",
            "Corroded sensor connections from water exposure",
            "Wiring fault between sensor and PCB",
        ],
        "action": "Check sensor connections at the PCB for corrosion. Measure thermistor resistance and compare to Rinnai spec chart. Replace sensor if resistance is out of range. Check for water leaks near the sensor that could cause corrosion.",
    },
    "34": {
        "meaning": "Combustion air temperature sensor fault.",
        "causes": [
            "Failed combustion air thermistor",
            "Sensor exposed to excessive heat or moisture",
            "Wiring fault between sensor and PCB",
        ],
        "action": "Locate the combustion air temperature sensor inside the unit. Check for heat damage or moisture on the sensor. Measure thermistor resistance and compare to spec. Replace if faulty.",
    },
    "41": {
        "meaning": "Heat exchanger over-temperature — heat exchanger exceeded safe temperature limit.",
        "causes": [
            "Scale buildup inside heat exchanger (most common — restricts water flow and creates hot spots)",
            "Low water flow rate through the unit",
            "Combustion issue causing excessive heat (blocked air intake, improper gas pressure)",
        ],
        "action": "Flush the heat exchanger with a descaling solution (white vinegar or commercial descaler) using a pump kit — run for at least 45 minutes. Check water flow rate after descaling. If error persists after flushing, check gas pressure and combustion air supply. Repeated occurrences indicate the heat exchanger may need replacement.",
    },
    "52": {
        "meaning": "Modulating gas valve issue — valve not adjusting flame properly.",
        "causes": [
            "Failed modulating gas valve motor or actuator",
            "Gas valve solenoid failure",
            "PCB modulating valve control circuit failure",
            "Wiring fault between PCB and gas valve",
        ],
        "action": "Check wiring connections at the gas valve and PCB. Listen for the modulating motor actuating during operation. If valve is not modulating, check for voltage signals from the PCB to the valve. Gas valve assembly may need replacement if actuator has failed.",
    },
    "57": {
        "meaning": "Bypass valve issue — bypass valve not operating correctly.",
        "causes": [
            "Bypass valve stuck open or closed (scale buildup)",
            "Bypass valve motor or actuator failure",
            "Wiring fault to bypass valve",
        ],
        "action": "Descale the bypass valve — scale buildup is the most common cause of bypass valve failures. Check valve motor operation. Check wiring between PCB and valve. Replace bypass valve assembly if motor has failed.",
    },
    "70": {
        "meaning": "PCB (printed circuit board) failure — internal board malfunction.",
        "causes": [
            "PCB component failure (often from power surge or lightning)",
            "Water damage to PCB from internal leak",
            "Insect or rodent damage to PCB",
        ],
        "action": "Inspect PCB for visible damage — burnt components, water stains, insect debris. Check for internal water leaks above the PCB. Replace the PCB. Consider installing a surge protector on the circuit to prevent future damage.",
    },
    "71": {
        "meaning": "Electronic gas valve fault — gas valve solenoid circuit error.",
        "causes": [
            "Gas valve solenoid coil failure",
            "Wiring fault between PCB and gas valve",
            "PCB gas valve driver circuit failure",
        ],
        "action": "Check wiring connections at the gas valve. Measure gas valve solenoid coil resistance. If coil is open or shorted, replace the gas valve assembly. If coil resistance is normal and wiring is good, PCB may need replacement.",
    },
    "72": {
        "meaning": "Flame detection after burner shutdown — flame still sensed after gas valve should be closed.",
        "causes": [
            "Gas valve not closing fully (internal leak)",
            "Flame rod sensing residual heat or electrical interference",
            "PCB flame sensing circuit malfunction",
        ],
        "action": "SAFETY CONCERN — this may indicate a leaking gas valve. After the unit shuts down, verify no flame is present by visual inspection. If flame persists after gas valve closes, shut off the gas supply and replace the gas valve. If no actual flame, check flame rod for fouling and check for electrical interference.",
    },
    "73": {
        "meaning": "Combustion chamber temperature rise abnormal — temperature rising too quickly or too high.",
        "causes": [
            "Blocked or restricted combustion air intake",
            "Improper gas pressure (too high)",
            "Heat exchanger partially blocked with scale (hot spots)",
            "Combustion fan issue causing improper air/fuel ratio",
        ],
        "action": "Check combustion air intake for blockages. Measure gas pressure at the unit inlet — should match nameplate rating. Flush heat exchanger to remove scale. Check combustion fan operation. Perform combustion analysis (CO levels in flue gas) to verify proper air/fuel ratio.",
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
    "3": {
        "meaning": "Thermopile voltage low with WV circuit closed — gas valve likely needs replacing.",
        "causes": [
            "Gas control valve internal failure (WV circuit stuck closed)",
            "Wiring fault between thermopile and gas control valve",
            "Thermopile generating insufficient voltage under load",
        ],
        "action": "Measure thermopile voltage under load at the gas valve terminals. If voltage is adequate (>250mV) but WV circuit reads closed, the gas control valve has failed internally — replace the gas control valve.",
    },
    "6": {
        "meaning": "False pilot detection — electronics detecting flame when none is present.",
        "causes": [
            "Failed gas control valve electronics (most common)",
            "Electrical interference from nearby wiring or equipment",
            "Moisture or corrosion on gas control valve sensor contacts",
        ],
        "action": "Replace the gas control valve assembly. This code almost always indicates an internal electronics failure in the valve. Before replacing, verify there is no actual residual flame present.",
    },
    "9": {
        "meaning": "Poor calibration or pressure switch fault (power vent models).",
        "causes": [
            "Pressure switch out of calibration or failed",
            "Blocked vent or intake on power vent unit",
            "Weak blower motor on power vent assembly",
            "Condensate blocking exhaust path",
        ],
        "action": "Check pressure switch operation with a manometer — verify it closes at the correct setpoint. Inspect vent and intake for blockages. Check power vent blower motor for proper operation. Clear any condensate from exhaust path.",
    },
}

RHEEM_WATER_HEATER_BLINKS = {
    "1": {
        "meaning": "Normal operation — pilot is lit and system is functioning correctly.",
        "causes": ["System operating normally — status light confirms pilot flame detected"],
        "action": "No action needed. One blink indicates normal operation.",
    },
    "2": {
        "meaning": "Thermopile voltage low — pilot is lit but not generating enough voltage to open gas valve.",
        "causes": [
            "Weak or failing thermopile (most common)",
            "Pilot flame not properly hitting thermopile tip",
            "Dirty or corroded thermopile connections",
            "Bad gas control valve not reading thermopile voltage",
        ],
        "action": "Measure thermopile voltage: should be >400mV open circuit, >250mV under load. Clean thermopile tip and ensure pilot flame envelopes it. If voltage is still low, replace thermopile. If voltage is good but valve won't open, replace gas control valve.",
    },
    "3": {
        "meaning": "Thermopile voltage low with WV circuit closed — likely gas valve failure.",
        "causes": [
            "Internal gas control valve failure (most common for this code)",
            "Wiring fault between thermopile and gas valve",
            "Corroded wire connections at gas valve terminals",
        ],
        "action": "This usually means the gas control valve has failed internally. Check thermopile voltage — if >250mV under load but WV circuit stays closed, replace the gas control valve.",
    },
    "4": {
        "meaning": "Over temperature — ECO (Emergency Cut Off) tripped, water exceeded safe temperature.",
        "causes": [
            "Thermostat set too high",
            "Sediment buildup on tank bottom creating hot spots",
            "Gas control valve thermostat failure (running away)",
            "Gas control valve stuck open, over-firing",
        ],
        "action": "Turn off gas, let tank cool. Check thermostat setting (should be 120°F residential). Flush tank to remove sediment. If ECO trips again at normal setting, gas control valve thermostat has failed — replace it. Do NOT just reset ECO without finding cause.",
    },
    "5": {
        "meaning": "Temperature sensor failure — sensor reading out of range.",
        "causes": [
            "Failed temperature sensor / thermistor (open or shorted)",
            "Wiring issue between sensor and gas control valve",
            "Corroded sensor connections",
        ],
        "action": "Check sensor wiring connections for corrosion. Measure sensor resistance and compare to manufacturer spec. If out of range, replace temperature sensor.",
    },
    "7": {
        "meaning": "Gas control valve failure — internal electronic or mechanical malfunction.",
        "causes": [
            "Internal gas control valve malfunction (solenoid, electronics, or mechanical)",
            "Power surge or electrical event damaged valve electronics",
            "Failed internal safety circuit",
        ],
        "action": "Replace the gas control valve. 7 blinks indicates an internal malfunction that cannot be field-repaired. Verify gas supply is off before replacing.",
    },
    "8": {
        "meaning": "Power supply issue — inadequate voltage to gas control electronics.",
        "causes": [
            "Inadequate thermopile voltage to power electronic gas valve",
            "Loose or corroded wiring connections",
            "Failing thermopile not generating enough power under load",
        ],
        "action": "Measure thermopile millivolt output under load. Should be >250mV. Check all wire connections for corrosion. If thermopile output is good, gas control valve may need replacement.",
    },
}

BRADFORD_WHITE_WATER_HEATER_BLINKS = {
    "1": {
        "meaning": "Normal operation — system is functioning correctly.",
        "causes": ["System operating normally"],
        "action": "No action needed. One blink on the status light indicates normal operation.",
    },
    "2": {
        "meaning": "Thermopile voltage low — pilot is lit but not generating enough voltage.",
        "causes": [
            "Weak or failing thermopile (most common)",
            "Poor flame contact with thermopile — flame not enveloping the tip properly",
            "Bad gas control valve not reading thermopile voltage correctly",
            "Dirty or corroded thermopile connections",
        ],
        "action": "Measure thermopile voltage: should be >400mV open circuit and >250mV under load (connected to gas valve). If low, clean the thermopile tip and ensure pilot flame is hitting it squarely. If still low after cleaning, replace thermopile. If voltage is good but valve won't open, replace gas control valve.",
    },
    "3": {
        "meaning": "Thermopile voltage low with WV circuit closed — likely a gas valve failure.",
        "causes": [
            "Gas control valve internal failure (most common cause of this specific code)",
            "Wiring fault between thermopile and gas control valve",
            "Corroded wire connections at the gas valve terminal block",
        ],
        "action": "This code usually means the gas control valve has failed internally. Measure thermopile voltage — if it's adequate (>250mV under load) but the WV circuit stays closed, replace the gas control valve. Check wiring connections at the valve for corrosion before condemning the valve.",
    },
    "4": {
        "meaning": "Over temperature / ECO (Emergency Cut Off) tripped — water exceeded safe temperature.",
        "causes": [
            "Thermostat set too high (check setting first)",
            "Sediment buildup on tank bottom creating hot spots",
            "Gas control valve thermostat failure (running away)",
            "Gas control valve stuck open, over-firing",
        ],
        "action": "Turn off gas and let tank cool. Check thermostat setting — should be 120°F for residential. Flush tank to remove sediment buildup. If ECO trips again at a normal temperature setting, the gas control valve thermostat has likely failed — replace the gas control valve. Do NOT simply reset ECO without finding the cause.",
    },
    "5": {
        "meaning": "Temperature sensor failure — sensor reading out of range.",
        "causes": [
            "Failed temperature sensor / thermistor (open or shorted)",
            "Wiring issue between sensor and gas control valve",
            "Corroded sensor connections",
        ],
        "action": "Check sensor wiring connections at the gas control valve for corrosion or looseness. Measure sensor resistance and compare to manufacturer spec (varies by model). If connections are good and resistance is out of range, replace the temperature sensor.",
    },
    "6": {
        "meaning": "False pilot detection — electronics detecting flame when none should be present.",
        "causes": [
            "Failed gas control valve electronics (most common)",
            "Electrical interference from nearby equipment or wiring",
            "Moisture or condensation on electronic components inside gas control valve",
        ],
        "action": "This code almost always requires replacing the gas control valve. The internal electronics are falsely detecting a flame. Verify there is no actual residual flame before replacing. If unit is in a high-humidity environment, check for condensation on the valve body.",
    },
    "7": {
        "meaning": "Gas control valve internal failure — valve malfunction detected.",
        "causes": [
            "Internal gas control valve malfunction (solenoid, electronics, or mechanical)",
            "Power surge or electrical event damaged valve electronics",
        ],
        "action": "Replace the gas control valve. This code indicates an internal malfunction that cannot be field-repaired. Do not attempt to disassemble or repair the valve.",
    },
    "8": {
        "meaning": "Power supply issue — inadequate voltage to gas control electronics.",
        "causes": [
            "Inadequate thermopile voltage to power the electronic gas valve",
            "Loose or corroded wiring connections at gas control valve",
            "Failing thermopile not generating enough power under load",
            "Long wire run between thermopile and gas valve causing voltage drop",
        ],
        "action": "Check all wiring connections between thermopile and gas control valve for tightness and corrosion. Measure thermopile output voltage under load. If voltage is borderline, replace the thermopile. If wiring and thermopile are good, the gas control valve electronics may be drawing excessive current — replace the valve.",
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
    "A7": {
        "meaning": "Swing motor (louver motor) fault — airflow direction vane not moving correctly.",
        "causes": [
            "Failed swing/louver motor",
            "Louver mechanism jammed or obstructed",
            "Wiring fault between indoor PCB and swing motor",
        ],
        "action": "Check for physical obstructions preventing louver movement. Listen for motor clicking or humming. Manually move the vane — it should swing freely. Check wiring connector between PCB and motor. Replace swing motor if faulty.",
    },
    "AH": {
        "meaning": "Air filter clogged — filter maintenance required.",
        "causes": [
            "Dirty air filter triggering the filter timer/sensor (most common)",
            "Auto-filter cleaning mechanism jammed (models with auto-clean)",
            "Filter sensor fault giving false reading",
        ],
        "action": "Remove and clean the air filter — wash with warm water and let dry completely. Reset the filter timer on the indoor unit (usually a button on the unit or via remote). If the unit has auto-clean, verify the cleaning mechanism operates freely.",
    },
    "C2": {
        "meaning": "Room temperature sensor (suction air thermistor) fault.",
        "causes": [
            "Failed room air thermistor (open or shorted)",
            "Thermistor connector loose or corroded on indoor PCB",
            "Sensor blocked by excessive dust buildup",
        ],
        "action": "Locate room air sensor in the indoor unit (usually behind the return air intake). Clean dust from around the sensor. Check connector at the PCB. Measure thermistor resistance — compare to manufacturer temp/resistance chart (typically ~10kΩ at 77°F). Replace if out of range.",
    },
    "C7": {
        "meaning": "Float switch activated — condensate overflow detected.",
        "causes": [
            "Clogged condensate drain line (most common)",
            "Failed condensate pump (if equipped)",
            "Cracked or misaligned drain pan",
            "Float switch stuck in the tripped position",
        ],
        "action": "Clear the condensate drain line using compressed nitrogen or a wet/dry vacuum from the outdoor end. Check for kinks or sags in the drain line. If pump-equipped, verify pump runs when float is raised. Check float switch for free movement — clean any algae buildup. After clearing, pour water into the pan to verify proper drainage.",
    },
    "E3": {
        "meaning": "High pressure protection activated — condenser pressure exceeded safe limit.",
        "causes": [
            "Dirty outdoor coil (most common — restricted airflow over condenser)",
            "Outdoor fan motor not running",
            "Refrigerant overcharge",
            "Non-condensable gases in the system (air, nitrogen from improper service)",
        ],
        "action": "Clean the outdoor coil with coil cleaner and rinse thoroughly. Verify outdoor fan is running. Check refrigerant charge with gauges — look for high head pressure. If system was recently serviced, non-condensables may be present — recover, evacuate, and recharge.",
    },
    "E4": {
        "meaning": "Low pressure protection activated — suction pressure dropped below safe limit.",
        "causes": [
            "Low refrigerant charge (leak in system — most common)",
            "Dirty indoor coil or clogged filter restricting airflow",
            "Restricted refrigerant flow (plugged filter-drier, failed TXV/EEV)",
            "Indoor fan not running (no airflow across evaporator)",
        ],
        "action": "Check air filter and indoor coil cleanliness first. Verify indoor fan is running. Connect refrigerant gauges — low suction pressure with low subcooling indicates a low charge (leak). Leak check the system. Check for restriction by looking for temperature drop across the filter-drier or metering device.",
    },
    "EA": {
        "meaning": "4-way reversing valve fault — valve not switching between heating and cooling modes.",
        "causes": [
            "Failed 4-way valve solenoid coil",
            "4-way valve mechanically stuck (internal slide seized)",
            "Wiring fault between outdoor PCB and reversing valve solenoid",
            "Insufficient refrigerant pressure differential to shift valve",
        ],
        "action": "Check for voltage at the reversing valve solenoid when mode changes. If voltage present, check solenoid coil resistance. Tap the valve body while energized to try to free a stuck slide. If valve won't shift, it must be replaced (requires brazing and full refrigerant recovery).",
    },
    "F1": {
        "meaning": "Compressor discharge temperature sensor fault.",
        "causes": [
            "Failed discharge thermistor (open or shorted)",
            "Thermistor dislodged from compressor discharge pipe",
            "Wiring fault between sensor and outdoor PCB",
        ],
        "action": "Check thermistor mounting on the compressor discharge line — must be securely attached with insulation. Measure thermistor resistance at the outdoor PCB connector. Compare to manufacturer spec chart. Replace if out of range.",
    },
    "H3": {
        "meaning": "High pressure switch fault — high pressure switch has opened.",
        "causes": [
            "Dirty outdoor coil (most common)",
            "Outdoor fan motor failure",
            "Refrigerant overcharge",
            "Non-condensable gases in the system",
            "High pressure switch failure (less common)",
        ],
        "action": "Clean outdoor coil. Verify outdoor fan operation. Check refrigerant charge with gauges. If pressures are normal and switch is still open, check switch with a multimeter — replace if it has failed internally.",
    },
    "H8": {
        "meaning": "Compressor CT (current transformer) fault — compressor current sensing error.",
        "causes": [
            "CT sensor failure or disconnection",
            "CT sensor wiring fault at outdoor PCB",
            "Outdoor PCB current sensing circuit failure",
        ],
        "action": "Check CT sensor connections at the outdoor PCB. Verify CT sensor is properly clamped around the compressor power wire. Check CT sensor output with a clamp meter for comparison. Replace CT sensor if faulty. If sensor is good, outdoor PCB may need replacement.",
    },
    "H9": {
        "meaning": "Outdoor air temperature sensor fault.",
        "causes": [
            "Failed outdoor ambient thermistor (open or shorted)",
            "Wiring damage from UV exposure, weather, or rodent chewing",
            "Corroded connector at outdoor PCB",
        ],
        "action": "Locate the outdoor ambient sensor. Inspect wiring for physical damage. Measure resistance and compare to temp/resistance chart. Replace if out of range. Clean connector at PCB if corroded.",
    },
    "J6": {
        "meaning": "Outdoor heat exchanger (coil) temperature sensor fault.",
        "causes": [
            "Failed outdoor coil thermistor",
            "Thermistor dislodged from coil tubing",
            "Wiring damage or corroded connections",
        ],
        "action": "Check thermistor mounting on the outdoor coil — should be securely attached with thermal compound and insulation. Measure resistance at the outdoor PCB connector. Replace if open, shorted, or resistance is out of spec.",
    },
    "L3": {
        "meaning": "Electrical parts temperature high — IPM or power transistor overheating.",
        "causes": [
            "Poor airflow through outdoor unit electrical compartment",
            "Failed cooling fan for electrical components",
            "Outdoor unit in direct sunlight with inadequate clearance",
            "High ambient temperature exceeding operating range",
        ],
        "action": "Check for adequate clearance around the outdoor unit (minimum per installation manual). Verify any electrical compartment cooling fans are running. Clean dust from the electrical compartment heatsink. If unit is in direct sunlight, consider adding a shade structure (maintaining clearance).",
    },
    "L5": {
        "meaning": "IPM (Intelligent Power Module) overcurrent or compressor locked rotor.",
        "causes": [
            "Compressor mechanically locked (seized bearings or scroll)",
            "Low voltage to outdoor unit causing high amp draw",
            "IPM module failure on outdoor PCB",
            "Compressor winding short",
        ],
        "action": "Measure voltage at outdoor unit disconnect — must be within nameplate spec. Check compressor winding resistance (phase-to-phase and phase-to-ground). If windings are shorted or grounded, replace compressor. If voltage is low, address power supply. If compressor and voltage check OK, IPM on the outdoor PCB may have failed.",
    },
    "P3": {
        "meaning": "Electrical parts (inverter board) temperature sensor fault.",
        "causes": [
            "Failed thermistor on the inverter/IPM board",
            "Connector loose or corroded at outdoor PCB",
            "Thermistor wiring fault",
        ],
        "action": "Check thermistor connections on the outdoor inverter board. Measure thermistor resistance and compare to spec. Replace if faulty. Inspect connector for corrosion.",
    },
    "UA": {
        "meaning": "Low voltage compressor overcurrent — compressor drawing excess current due to voltage issues.",
        "causes": [
            "Low supply voltage to outdoor unit (most common — utility brownout or voltage drop)",
            "Undersized power wiring causing voltage drop under compressor load",
            "Loose connections at disconnect, breaker, or unit terminals",
            "Compressor starting to fail mechanically (drawing higher amps at lower voltage)",
        ],
        "action": "Measure voltage at the outdoor unit disconnect while the compressor is running — voltage must be within nameplate range. Check for voltage drop between the breaker and disconnect (should be less than 3%). Tighten all connections. Verify wire gauge is adequate for the circuit length per NEC tables. If voltage is good, check compressor amp draw against RLA.",
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
    "E1": {
        "meaning": "Remote controller communication error.",
        "causes": [
            "Failed remote controller or dead batteries",
            "Wiring fault between remote and indoor unit control board",
            "Indoor unit PCB communication circuit failure",
        ],
        "action": "Replace remote controller batteries first. If still failing, check wiring between wall-mounted remote and indoor unit. Try a different remote if available. If wiring is good, indoor PCB communication circuit may have failed.",
    },
    "E3": {
        "meaning": "Remote temperature sensor fault.",
        "causes": [
            "Failed thermistor in remote controller",
            "Remote controller PCB fault",
        ],
        "action": "If using a wall-mounted remote with built-in sensor, replace the remote. If using a separate sensor, check wiring and sensor resistance. Switch to indoor unit sensor as a temporary workaround.",
    },
    "E4": {
        "meaning": "Outdoor unit address duplication — multiple outdoor units with the same address.",
        "causes": [
            "Two outdoor units set to the same address on multi-zone systems",
            "DIP switch or rotary address switch set incorrectly",
            "Wiring crossed between outdoor units",
        ],
        "action": "Check address settings on each outdoor unit — DIP switches or rotary switch on the outdoor PCB. Each outdoor unit must have a unique address. Verify wiring is not crossed between units.",
    },
    "E5": {
        "meaning": "Communication error with outdoor unit.",
        "causes": [
            "Wiring fault between indoor and outdoor units (most common)",
            "Loose connections at terminal blocks on either unit",
            "Outdoor unit PCB failure",
            "Power supply issue to outdoor unit",
        ],
        "action": "Check wiring between indoor and outdoor units at terminal blocks on both ends. Verify outdoor unit has proper voltage. Measure for continuity on communication wire pair. If wiring is good, outdoor PCB may need replacement.",
    },
    "E7": {
        "meaning": "Indoor fan motor fault — motor not running or running abnormally.",
        "causes": [
            "Failed indoor fan motor (most common)",
            "Fan blade hitting ice buildup or foreign object",
            "Wiring fault between indoor PCB and fan motor",
            "Indoor PCB fan driver circuit failure",
        ],
        "action": "Check for physical obstructions or ice on the fan wheel. Spin the fan by hand — it should rotate freely. Check wiring between PCB and motor. Measure motor resistance. If motor is seized or resistance is out of spec, replace the fan motor.",
    },
    "P3": {
        "meaning": "Drain sensor fault — condensate drain sensor error.",
        "causes": [
            "Failed drain sensor (open or shorted)",
            "Corroded drain sensor connections",
            "Drain sensor wiring fault",
        ],
        "action": "Check drain sensor connections for corrosion. Measure sensor resistance — compare to manufacturer spec. Replace drain sensor if resistance is out of range.",
    },
    "P4": {
        "meaning": "Drain sensor short circuit.",
        "causes": [
            "Shorted drain sensor (water intrusion into sensor body)",
            "Pinched or damaged sensor wiring causing short",
            "Corroded connector shorting sensor leads",
        ],
        "action": "Inspect drain sensor for water intrusion. Check sensor wiring for damage or pinch points. Disconnect sensor and measure resistance — a short will read near 0 ohms. Replace sensor if shorted.",
    },
    "P5": {
        "meaning": "Drain pump fault — condensate pump not operating correctly.",
        "causes": [
            "Failed condensate pump motor",
            "Clogged pump inlet or outlet",
            "Float switch stuck in pump reservoir",
            "Wiring fault between PCB and pump",
        ],
        "action": "Check pump operation — pour water into the reservoir to trigger the float switch. Listen for pump motor. Clean pump inlet filter and outlet line. Check wiring between indoor PCB and pump. Replace pump if motor has failed.",
    },
    "P6": {
        "meaning": "Freeze protection or overheat protection activated.",
        "causes": [
            "Dirty air filter severely restricting airflow (most common for freeze)",
            "Low refrigerant charge causing coil to ice over",
            "Indoor fan running at incorrect speed",
            "Outdoor coil blocked causing high head pressure (overheat)",
        ],
        "action": "Check and clean air filters first. Inspect indoor coil for ice — if iced, check refrigerant charge and look for leaks. Verify indoor fan is running at the correct speed. For overheat, check outdoor coil for dirt or obstructions.",
    },
    "P9": {
        "meaning": "Pipe (coil) temperature sensor fault.",
        "causes": [
            "Failed pipe thermistor (open or shorted)",
            "Thermistor dislodged from pipe — not making good contact",
            "Wiring fault between thermistor and indoor PCB",
        ],
        "action": "Check that the pipe thermistor is securely attached to the refrigerant pipe with proper insulation. Measure thermistor resistance and compare to manufacturer spec chart. Replace if out of range. Ensure wiring connections are tight at the PCB.",
    },
    "U3": {
        "meaning": "Open or short circuit on outdoor thermistor.",
        "causes": [
            "Failed outdoor temperature thermistor (open or shorted)",
            "Corroded thermistor connections at outdoor PCB",
            "Wire damage from UV exposure or rodent chewing",
        ],
        "action": "Check outdoor thermistor wiring for physical damage (common from UV or rodents). Measure thermistor resistance at the outdoor PCB connector — compare to temp/resistance chart. Replace thermistor if open or shorted.",
    },
    "U4": {
        "meaning": "Communication error between indoor and outdoor units.",
        "causes": [
            "Wiring fault on communication cable between units (most common)",
            "Loose terminal connections at indoor or outdoor unit",
            "PCB failure on either indoor or outdoor unit",
            "Voltage drop on communication line due to long wire run or undersized wire",
        ],
        "action": "Check communication wiring between indoor and outdoor units — verify tight connections at both terminal blocks. Check wire gauge is adequate for the run length. Measure voltage between communication terminals. Power cycle both units. If wiring is confirmed good, suspect PCB failure.",
    },
    "U6": {
        "meaning": "Compressor overcurrent — excessive amp draw detected.",
        "causes": [
            "Compressor mechanical failure (locked rotor or tight bearings)",
            "Low voltage to outdoor unit (most common electrical cause)",
            "Refrigerant overcharge causing high head pressure",
            "Failed outdoor PCB inverter circuit",
        ],
        "action": "Measure voltage at outdoor unit disconnect — should be within nameplate spec. Check compressor amp draw against rated load amps (RLA). If voltage is good and amps are high, compressor may be failing. Check refrigerant charge — overcharge causes high amps. If compressor windings check OK, suspect inverter board.",
    },
    "U8": {
        "meaning": "Outdoor fan motor stopped — fan not rotating.",
        "causes": [
            "Failed outdoor fan motor (most common)",
            "Foreign object or ice blocking fan blade",
            "Fan motor wiring fault",
            "Outdoor PCB fan driver circuit failure",
        ],
        "action": "Inspect outdoor fan for physical obstructions, ice, or debris. Try spinning the fan by hand — it should turn freely. Check wiring between outdoor PCB and fan motor. Measure motor resistance. Replace motor if seized or resistance is out of spec.",
    },
    "U9": {
        "meaning": "Low voltage — power supply voltage below acceptable threshold.",
        "causes": [
            "Utility voltage sag or brownout condition",
            "Undersized wire run to outdoor unit (voltage drop)",
            "Loose connections at disconnect or breaker causing voltage drop",
            "Shared circuit with other high-draw equipment",
        ],
        "action": "Measure voltage at outdoor unit disconnect under load — must be within nameplate range (typically 198-253V for 230V units). Check wire size for the run length. Tighten all connections at disconnect, breaker, and unit terminals. Ensure unit is on a dedicated circuit.",
    },
    "FB": {
        "meaning": "Indoor PCB (printed circuit board) fault — board malfunction.",
        "causes": [
            "Indoor PCB component failure (often from power surge)",
            "Water damage to indoor PCB from condensate leak",
            "Insect or rodent damage to PCB components",
        ],
        "action": "Inspect indoor PCB for visible damage — burnt components, water stains, insect debris. Check for condensate leaks that could drip onto the board. If board shows damage or no other cause is found, replace the indoor PCB. Consider installing a surge protector.",
    },
    "PA": {
        "meaning": "Forced compressor lockout — compressor operation inhibited.",
        "causes": [
            "Multiple consecutive compressor protection trips (system locks out to prevent damage)",
            "Persistent overcurrent or overheat condition not resolved",
            "Outdoor PCB forcing lockout due to repeated faults",
        ],
        "action": "This is a protective lockout — do NOT simply reset and restart. Review the fault history to identify the underlying cause (typically overcurrent, high pressure, or overheat). Fix the root cause first. Then power cycle the outdoor unit to clear the lockout. If it locks out again, the underlying problem has not been resolved.",
    },
}

FUJITSU_MINI_SPLIT_CODES = {
    "E0": {
        "meaning": "Communication error between indoor and outdoor units.",
        "causes": [
            "Wiring fault between indoor and outdoor units (most common)",
            "Loose or corroded connections at terminal blocks",
            "Outdoor unit PCB communication circuit failure",
            "Power supply issue preventing outdoor unit from communicating",
        ],
        "action": "Check wiring between indoor and outdoor units at both terminal blocks — look for loose, corroded, or damaged connections. Verify outdoor unit has proper voltage at the disconnect. Measure continuity on the communication wire pair. Power cycle both units. If wiring is confirmed good, suspect PCB failure on either unit.",
    },
    "E1": {
        "meaning": "Communication error within the indoor unit — internal board communication fault.",
        "causes": [
            "Indoor unit PCB failure (communication IC or circuit)",
            "Wiring harness fault between indoor unit sub-boards",
            "Power surge damage to indoor unit electronics",
        ],
        "action": "Power cycle the indoor unit. Check all internal wiring harness connections inside the indoor unit. Inspect the indoor PCB for visible damage (burnt components, corrosion). If connections are good and board looks clean, replace the indoor PCB.",
    },
    "E2": {
        "meaning": "Indoor unit coil (pipe) temperature sensor open or shorted.",
        "causes": [
            "Failed coil thermistor (open or shorted — most common)",
            "Thermistor dislodged from copper pipe — not making good thermal contact",
            "Wiring fault or corroded connector between thermistor and PCB",
        ],
        "action": "Check that the coil thermistor is securely mounted on the refrigerant pipe with insulation tape. Measure thermistor resistance at the indoor PCB connector and compare to the manufacturer temp/resistance chart (typically ~10k ohms at 77°F). If open or shorted, replace the thermistor.",
    },
    "E3": {
        "meaning": "Indoor unit room air temperature sensor fault.",
        "causes": [
            "Failed room air thermistor (open or shorted)",
            "Thermistor blocked by dirt or positioned in direct sunlight/airflow",
            "Wiring fault between sensor and indoor PCB",
        ],
        "action": "Locate the room air sensor (usually behind the return air grille on the indoor unit). Check for dirt buildup blocking the sensor. Measure thermistor resistance and compare to spec. Replace if out of range. Check wiring connections at the PCB.",
    },
    "E4": {
        "meaning": "Indoor unit drain pan temperature sensor fault.",
        "causes": [
            "Failed drain pan thermistor",
            "Sensor submerged in standing water (drain blockage caused water to reach sensor)",
            "Corroded connections from moisture exposure",
        ],
        "action": "Clear the condensate drain first — standing water in the pan may have damaged the sensor. Check sensor wiring for corrosion from moisture. Measure sensor resistance and compare to spec. Replace sensor if faulty. Address the root cause of any drain blockage.",
    },
    "E5": {
        "meaning": "Outdoor coil temperature sensor fault.",
        "causes": [
            "Failed outdoor coil thermistor (open or shorted)",
            "Thermistor dislodged from outdoor coil",
            "Wiring damage from UV exposure or rodent chewing",
        ],
        "action": "Check outdoor coil thermistor mounting — it should be securely attached to the coil with thermal paste and insulation. Inspect wiring for UV damage or rodent chew marks. Measure thermistor resistance at outdoor PCB and compare to spec chart. Replace if out of range.",
    },
    "E6": {
        "meaning": "Outdoor air/ambient temperature sensor fault.",
        "causes": [
            "Failed outdoor ambient thermistor",
            "Wiring damage from UV exposure or weather",
            "Corroded connections at outdoor PCB",
        ],
        "action": "Locate the outdoor ambient sensor (usually clipped to the outdoor coil or mounted on the PCB). Check wiring for physical damage. Measure resistance and compare to manufacturer spec. Replace if faulty.",
    },
    "E7": {
        "meaning": "Outdoor discharge pipe temperature sensor fault.",
        "causes": [
            "Failed discharge thermistor (open or shorted)",
            "Thermistor not properly secured to discharge pipe",
            "Wiring fault between sensor and outdoor PCB",
        ],
        "action": "Check that the discharge pipe thermistor is tightly mounted to the compressor discharge line with proper insulation. Measure resistance and compare to spec. Replace if out of range. This sensor is critical for compressor protection — do not bypass.",
    },
    "E8": {
        "meaning": "Indoor fan motor fault — motor not running or running erratically.",
        "causes": [
            "Failed indoor fan motor (most common)",
            "Fan wheel hitting ice or foreign object",
            "Wiring fault between indoor PCB and fan motor",
            "Indoor PCB fan driver circuit failure",
        ],
        "action": "Check for ice buildup or foreign objects on the fan wheel. Spin the fan by hand — it should rotate freely without grinding or resistance. Check wiring between PCB and motor connector. Measure motor winding resistance. If motor is seized or resistance is out of spec, replace the fan motor.",
    },
    "E9": {
        "meaning": "Drain level high — condensate drain pan is full or overflowing.",
        "causes": [
            "Clogged condensate drain line (most common)",
            "Failed condensate pump (if equipped)",
            "Drain pan cracked or not level",
            "Float switch stuck or failed",
        ],
        "action": "Clear the condensate drain line — use compressed nitrogen or a wet/dry vac from the outside. Check for kinks or sags in the drain line. If pump-equipped, verify pump operation. Check that the indoor unit is level (slight tilt toward drain side). Inspect float switch for proper operation.",
    },
    "EA": {
        "meaning": "4-way reversing valve switching error — valve did not switch to the commanded position (heat pump models).",
        "causes": [
            "Failed 4-way valve solenoid coil",
            "4-way valve mechanically stuck (internal slide seized)",
            "Wiring fault between outdoor PCB and reversing valve solenoid",
            "Insufficient pressure differential to shift the valve",
        ],
        "action": "Check for 24V or 12V (model-dependent) at the reversing valve solenoid coil when mode switches. If voltage is present, tap the valve body lightly while energized — sometimes frees a stuck slide. Check solenoid coil resistance. If coil is good and valve won't shift, the valve is mechanically stuck and must be replaced (requires brazing and refrigerant recovery).",
    },
    "EE": {
        "meaning": "Communication error on the outdoor unit PCB — board-level communication fault.",
        "causes": [
            "Outdoor PCB internal communication failure",
            "Power surge damage to outdoor unit electronics",
            "Corroded or damaged PCB from moisture intrusion into outdoor unit electrical box",
        ],
        "action": "Check outdoor unit electrical box for moisture intrusion — water damage to the PCB is common if the box seal is compromised. Inspect PCB for visible damage (burnt components, corrosion). Power cycle the outdoor unit. If code persists, replace the outdoor PCB.",
    },
}

# ---------------------------------------------------------------------------
# Brand aliases — maps variations to the canonical brand key
# ---------------------------------------------------------------------------

BRAND_ALIASES = {
    # Rheem — STT often garbles this as "ream", "reem", "ream", "re em"
    "rheem": "rheem",
    "reem": "rheem",
    "ream": "rheem",
    "re em": "rheem",
    "ruud": "rheem",  # Same manufacturer
    "rude": "rheem",  # STT misspelling of Ruud
    # Carrier — STT is usually fine but "bryant" can become "brian"
    "carrier": "carrier",
    "bryant": "carrier",  # Same parent company
    "brian t": "carrier",  # STT misspelling of Bryant
    "payne": "carrier",  # Same parent company
    "pain": "carrier",  # STT misspelling of Payne
    # Goodman
    "goodman": "goodman",
    "amana": "goodman",  # Same manufacturer
    # Lennox — STT may say "lenox" or "lennocks"
    "lennox": "lennox",
    "lenox": "lennox",
    "lennocks": "lennox",
    # Trane — STT may say "train"
    "trane": "trane",
    "train": "trane",
    "american standard": "trane",  # Same manufacturer
    # Rinnai — STT may say "rin eye", "rennai"
    "rinnai": "rinnai",
    "rin eye": "rinnai",
    "rennai": "rinnai",
    "rinai": "rinnai",
    # AO Smith
    "ao smith": "ao_smith",
    "a.o. smith": "ao_smith",
    "a o smith": "ao_smith",
    "aosmith": "ao_smith",
    # Daikin — STT may say "dakin" or "dykin"
    "daikin": "daikin",
    "dakin": "daikin",
    "dykin": "daikin",
    # Mitsubishi — STT is usually close enough
    "mitsubishi": "mitsubishi",
    # Fujitsu — STT may say "fu jitsu"
    "fujitsu": "fujitsu",
    "fu jitsu": "fujitsu",
    # Bradford White
    "bradford white": "bradford_white",
    "bradford": "bradford_white",
}

# ---------------------------------------------------------------------------
# Brand → equipment type → code dictionary mapping
# ---------------------------------------------------------------------------

ERROR_CODE_DB = {
    "rheem": {
        "furnace": RHEEM_FURNACE_BLINKS,
        "water heater": RHEEM_WATER_HEATER_BLINKS,
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
    "bradford_white": {
        "water heater": BRADFORD_WHITE_WATER_HEATER_BLINKS,
    },
    "fujitsu": {
        "mini split": FUJITSU_MINI_SPLIT_CODES,
        "minisplit": FUJITSU_MINI_SPLIT_CODES,
        "air conditioner": FUJITSU_MINI_SPLIT_CODES,
        "heat pump": FUJITSU_MINI_SPLIT_CODES,
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
    "hot water heater": "water heater",
    "hot water tank": "water heater",
    "water tank": "water heater",
    "mini split": "mini split",
    "mini-split": "mini split",
    "minisplit": "mini split",
    "ductless": "mini split",
    "air conditioner": "air conditioner",
    "ac": "air conditioner",
    "a/c": "air conditioner",
    "heat pump": "heat pump",
    "boiler": "boiler",
    "air handler": "air handler",
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
    # "code 34", "code E228", "code AH"
    re.compile(r"code\s+([A-Za-z]?\d+)", re.I),
    # "error AH", "code EA", "fault EE" (two-letter codes preceded by keyword)
    re.compile(r"(?:code|error|fault)\s+([A-Z]{2})\b", re.I),
    # "AH error", "EA fault", "PA code" (two-letter codes followed by keyword)
    re.compile(r"\b([A-Z]{2})\s+(?:error|fault|code)", re.I),
    # "AH", "EA", "EE", "FB", "PA", "UA" (two-letter codes at end of query string)
    # Only matches at end of string to avoid matching brand abbreviations like "AO" from "AO Smith"
    re.compile(r"\b([A-Z]{2})\s*$", re.I),
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


# Number words → digits for STT transcripts ("three blinks" → "3 blinks")
_NUMBER_WORDS = {
    "zero": "0", "one": "1", "two": "2", "three": "3", "four": "4",
    "five": "5", "six": "6", "seven": "7", "eight": "8", "nine": "9",
    "ten": "10", "eleven": "11", "twelve": "12", "thirteen": "13",
}


def _normalize_number_words(text: str) -> str:
    """Convert spoken number words to digits so regex patterns can match."""
    result = text
    for word, digit in _NUMBER_WORDS.items():
        result = re.sub(rf"\b{word}\b", digit, result, flags=re.I)
    return result


def _extract_code(text: str) -> str | None:
    """Try to extract an error/fault code from the query text."""
    # First, convert number words to digits ("three blinks" → "3 blinks")
    normalized = _normalize_number_words(text)
    for pattern in _CODE_PATTERNS:
        match = pattern.search(normalized)
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

    return f"""## ✅ VERIFIED Error Code — Use This EXACT Information
**{brand_display} {result['equipment'].title()} — Code {result['code']}**
Meaning: {result['meaning']}
Common causes (ranked by likelihood):
{causes_list}
Recommended action: {result['action']}

CRITICAL: This error code data is FROM THE MANUFACTURER'S DOCUMENTATION and is VERIFIED CORRECT.
- Use this EXACT meaning and cause ranking. Do NOT substitute your own interpretation.
- Do NOT add causes that aren't listed here.
- Do NOT change the order of causes.
- Lead with the meaning in plain language, then give the #1 cause and diagnostic step.
- If the user asks follow-up questions, stay within this diagnostic framework."""
