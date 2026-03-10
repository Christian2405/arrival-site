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

NAVIEN_TANKLESS_CODES = {
    "E003": {
        "meaning": "Ignition failure — unit tried to light and couldn't.",
        "causes": [
            "Gas supply off or low gas pressure (most common)",
            "Igniter failure or weak spark",
            "Dirty or corroded flame rod",
            "Condensate backup blocking exhaust",
            "Improper venting — termination too close to obstruction",
        ],
        "action": "Verify gas is on and meter/regulator is supplying correct pressure. Check igniter for spark — pull the igniter and look for cracks or carbon buildup. Clean the flame rod with fine emery cloth. Check condensate trap and drain line for blockage. On newer Navien units, also check the inlet gas filter screen for debris.",
    },
    "E004": {
        "meaning": "False flame detection — unit sees flame when there shouldn't be one.",
        "causes": [
            "Flame rod short to ground or touching heat exchanger",
            "Residual flame from slow gas valve closure",
            "PCB fault — flame detection circuit malfunction",
        ],
        "action": "SAFETY FIRST — shut off gas supply. Inspect flame rod for carbon bridging or contact with the burner/heat exchanger. Check flame rod wiring for shorts. If rod and wiring are clean, suspect the PCB.",
    },
    "E010": {
        "meaning": "Abnormal exhaust temperature — likely blocked vent.",
        "causes": [
            "Blocked or partially obstructed vent termination (bird nests, ice, debris)",
            "Vent pipe too long or too many elbows for the model",
            "Exhaust temp sensor failure",
            "Recirculation — exhaust being sucked back into intake",
        ],
        "action": "Inspect vent termination outside for blockage — ice dams in winter are very common on Navien units. Check total vent length against installation manual limits. Ensure intake and exhaust have proper separation. If vent is clear, check the exhaust thermistor resistance.",
    },
    "E012": {
        "meaning": "Flame loss during operation — unit lit successfully but flame went out.",
        "causes": [
            "Wind blowing down the vent (intermittent issue)",
            "Gas pressure dropping under load (undersized gas line)",
            "Dirty flame rod losing signal as it gets hot",
            "Condensate drain backup causing exhaust restriction",
            "Loose wiring at flame rod connection",
        ],
        "action": "If intermittent, check outdoor vent termination for wind exposure — may need a wind guard. Check gas pressure at the unit while firing at full rate — should hold steady. Clean flame rod. Clear condensate trap. Check flame rod wire connection at the PCB.",
    },
    "E016": {
        "meaning": "Overheating — overheat protection tripped.",
        "causes": [
            "Scale buildup in heat exchanger (hard water areas)",
            "Low water flow through the unit",
            "Circulation pump failure on recirculation systems",
            "Inlet filter screen clogged",
        ],
        "action": "Flush the heat exchanger with descaling solution — white vinegar or commercial descaler, circulate for 45-60 minutes. Check the inlet water filter screen. If on a recirculation system, verify the pump is running and check for closed isolation valves. In hard water areas, this is almost always scale.",
    },
    "E030": {
        "meaning": "Air/fuel ratio imbalance — combustion not within parameters.",
        "causes": [
            "Partially blocked vent or intake",
            "High altitude installation without proper dip switch setting",
            "Dirty or failing APS (air pressure sensor)",
            "Gas pressure out of spec",
            "Cracked heat exchanger (rare but serious)",
        ],
        "action": "Check venting first — look for partial obstruction, sagging vent pipe, or improper termination. Verify altitude dip switch settings match installation elevation. Check APS sensor for moisture or contamination. Verify gas pressure. Run combustion analysis if you have the equipment.",
    },
    "E021": {
        "meaning": "Outlet water temperature sensor fault.",
        "causes": [
            "Failed outlet thermistor (open or shorted)",
            "Loose connector at the sensor or PCB",
            "Corroded sensor wiring from condensate exposure",
        ],
        "action": "Check the outlet temp sensor resistance with a meter — compare to the spec chart in the manual. Check the connector for corrosion or looseness. If the reading is out of range, replace the sensor.",
    },
    "E022": {
        "meaning": "Inlet water temperature sensor fault.",
        "causes": [
            "Failed inlet thermistor (open or shorted)",
            "Loose or corroded connector",
            "Water damage to sensor wiring",
        ],
        "action": "Check inlet temp sensor resistance. Inspect connector at PCB. Same diagnostic process as E021 — just on the inlet side. Replace sensor if resistance is out of spec.",
    },
    "E027": {
        "meaning": "Overvoltage — power supply issue.",
        "causes": [
            "Voltage at the outlet exceeding 130V",
            "Power surge or unstable utility power",
            "Bad surge protector or UPS causing voltage spikes",
        ],
        "action": "Check voltage at the outlet — Navien units are sensitive to overvoltage. Should be 120V +/- 10%. If voltage is high, check with the utility or install a voltage regulator. If the area has frequent surges, install a dedicated surge protector.",
    },
    "E028": {
        "meaning": "Abnormal outlet water temperature detected — temp higher than expected.",
        "causes": [
            "Scale buildup reducing heat exchanger efficiency",
            "Outlet temp sensor reading incorrectly",
            "Internal bypass valve stuck",
        ],
        "action": "Flush the heat exchanger with descaler. Check outlet temp sensor against actual water temperature with a probe thermometer. If sensor reads correctly and heat exchanger is clean, check the bypass servo valve operation.",
    },
    "E032": {
        "meaning": "Outgoing water temperature sensor misconnection.",
        "causes": [
            "Sensor plugged into the wrong port on the PCB",
            "Sensors swapped during service or installation",
            "Damaged connector",
        ],
        "action": "Verify sensor wiring matches the wiring diagram — inlet and outlet sensors may have been swapped. Check that each sensor connector is seated in the correct port on the PCB.",
    },
    "E034": {
        "meaning": "Exhaust temperature sensor fault.",
        "causes": [
            "Failed exhaust thermistor",
            "Connector melted or damaged from heat",
            "Wiring damaged by high exhaust temps",
        ],
        "action": "Check exhaust temp sensor resistance. Inspect the sensor and its wiring for heat damage — these run hot and the connectors can melt over time. Replace sensor and inspect connector for damage.",
    },
    "E038": {
        "meaning": "APS (air pressure sensor) fault.",
        "causes": [
            "Failed APS sensor",
            "Moisture in the APS sensing tubes",
            "Clogged or disconnected sensing tubes",
            "Condensate in the sensor housing",
        ],
        "action": "Check APS sensor tubes for moisture or blockage — blow them out. Inspect the sensor for condensate intrusion. If the tubes are clear and dry, replace the APS sensor. On some models, the APS is on the fan assembly.",
    },
    "E046": {
        "meaning": "Cascade communication error — multi-unit system communication failure.",
        "causes": [
            "Cascade cable loose or damaged between units",
            "Incorrect cascade wiring (polarity reversed)",
            "PCB failure on one unit in the cascade",
            "Dip switch settings incorrect for cascade position",
        ],
        "action": "Check cascade communication cable connections between all units. Verify polarity is correct. Check dip switch settings on each unit — each must have a unique cascade address. Try disconnecting units one at a time to isolate the faulty one.",
    },
    "E047": {
        "meaning": "Main PCB error — board-level fault.",
        "causes": [
            "PCB failure from power surge",
            "Moisture damage to the PCB",
            "Component failure on the board",
        ],
        "action": "Power cycle the unit — leave it off for 30 seconds. If code returns immediately, inspect the PCB for visible damage (burnt components, corrosion, water stains). Check for moisture inside the unit that could have reached the board. PCB replacement is likely needed.",
    },
    "E109": {
        "meaning": "Fan motor fault — combustion blower not operating correctly.",
        "causes": [
            "Fan motor failure",
            "Wiring issue to fan motor",
            "Debris or buildup on fan blades causing imbalance",
            "PCB not sending signal to fan",
        ],
        "action": "Listen for the fan — does it try to spin? Check voltage at the fan motor connector during a call for heat. Inspect fan blades for debris buildup. Check wiring from PCB to motor. If voltage is present but motor doesn't spin, replace the fan motor.",
    },
    "E110": {
        "meaning": "Exhaust blockage detected — similar to E010 but specifically blockage.",
        "causes": [
            "Blocked vent termination (ice, debris, bird nest)",
            "Vent pipe disconnected or separated at a joint",
            "Condensate drain clogged causing backpressure",
        ],
        "action": "Go outside and check the vent termination first — this is the #1 cause. Inspect the entire vent run for separations or sags. Clear the condensate trap and drain line. In cold climates, ice buildup on the exhaust termination is extremely common with Navien units.",
    },
    "E302": {
        "meaning": "Low water flow — not enough flow to activate the unit.",
        "causes": [
            "Flow sensor dirty or failing",
            "Inlet filter screen clogged with debris",
            "Closed or partially closed isolation valve",
            "Recirculation pump not running or check valve stuck",
            "Low water pressure from the street",
        ],
        "action": "Check the inlet filter screen first — remove and clean it. Verify all isolation valves are fully open. Check water pressure at the unit. If on a recirculation system, verify pump operation and check valve function. If all that checks out, the flow sensor may need replacement.",
    },
    "E407": {
        "meaning": "Thermistor short — DHW (domestic hot water) temperature sensor shorted.",
        "causes": [
            "Shorted thermistor (internal failure)",
            "Pinched or damaged sensor wire",
            "Water intrusion into the sensor connector",
        ],
        "action": "Check thermistor resistance — a short will read near 0 ohms. Inspect wiring for pinch points or damage. Check connector for moisture. Replace the thermistor.",
    },
    "E421": {
        "meaning": "Thermistor open — DHW temperature sensor open circuit.",
        "causes": [
            "Open thermistor (internal failure)",
            "Broken wire or disconnected sensor",
            "Corroded connector at PCB or sensor end",
        ],
        "action": "Check thermistor resistance — an open circuit reads infinite (OL on meter). Check wiring continuity from sensor to PCB. Inspect connectors for corrosion. Replace the thermistor if open.",
    },
    "E439": {
        "meaning": "Abnormal PCB temperature — board is overheating.",
        "causes": [
            "Poor ventilation around the unit",
            "Ambient temperature too high in the installation area",
            "PCB component failure generating excess heat",
        ],
        "action": "Check the area around the unit for adequate ventilation. Navien units need clearance per the installation manual. If the area isn't hot and airflow is fine, the PCB may have a failing component and need replacement.",
    },
    "E515": {
        "meaning": "Abnormal water flow — mixing valve issue.",
        "causes": [
            "Mixing valve motor stalled or failed",
            "Mixing valve stuck due to scale or debris",
            "Flow sensor reading inconsistent with valve position",
        ],
        "action": "Check mixing valve operation — try running in manual mode if available. Listen for the mixing valve motor. Scale buildup can jam the valve — may need to flush or replace the mixing valve assembly.",
    },
    "E517": {
        "meaning": "Mixing valve motor fault — motor not responding.",
        "causes": [
            "Mixing valve motor failure",
            "Wiring issue to mixing valve motor",
            "PCB not sending control signal",
        ],
        "action": "Check for voltage at the mixing valve motor connector. If voltage present but motor doesn't move, replace the mixing valve motor. If no voltage, check wiring and PCB.",
    },
    "E590": {
        "meaning": "Neutralizer fill alert — condensate neutralizer needs attention.",
        "causes": [
            "Neutralizer media depleted",
            "Neutralizer cartridge needs replacement",
            "Timer-based alert (not necessarily a malfunction)",
        ],
        "action": "This is a maintenance alert, not a fault. Replace or refill the condensate neutralizer media. Reset the alert per the manual — usually involves holding a button on the PCB.",
    },
    "E593": {
        "meaning": "Neutralizer flow switch fault — condensate flow switch issue.",
        "causes": [
            "Condensate flow switch stuck or failed",
            "Condensate drain line clogged",
            "Neutralizer cartridge overfilled or blocked",
        ],
        "action": "Check the condensate drain line for clogs. Clean the flow switch. Verify the neutralizer isn't overfilled. If drain is clear and switch is clean, replace the flow switch.",
    },
    "E610": {
        "meaning": "Abnormal combustion detected.",
        "causes": [
            "Vent system issue causing poor combustion",
            "Gas pressure too high or too low",
            "Dirty burner or clogged burner ports",
            "Air intake restriction",
        ],
        "action": "Check venting for any obstruction or improper installation. Verify gas pressure matches the rating plate. Inspect the burner for debris or clogging. Run combustion analysis if possible. This code is serious — don't ignore it.",
    },
}

NORITZ_TANKLESS_CODES = {
    "10": {
        "meaning": "Air supply or exhaust blockage — combustion air problem.",
        "causes": [
            "Blocked vent termination (bird nest, ice, leaves)",
            "Vent pipe too long or too many elbows",
            "Intake air supply restricted",
            "Fan motor weakening",
        ],
        "action": "Check vent termination outside first. Verify vent length and number of elbows meets the manual spec. Ensure air intake isn't blocked. Check fan motor operation — if it sounds strained, measure amp draw against spec.",
    },
    "11": {
        "meaning": "Ignition failure — no flame established.",
        "causes": [
            "Gas supply off or gas pressure too low",
            "Igniter failure or weak spark",
            "Dirty flame rod (most common in hard-water areas)",
            "Gas line undersized — not enough BTU delivery",
            "Condensate drain clogged causing exhaust backup",
        ],
        "action": "Verify gas is on and pressure is correct at the unit. Clean the flame rod with fine emery cloth. Check igniter for spark. Check condensate drain. If gas line was recently run, verify it's sized for the unit's BTU input.",
    },
    "12": {
        "meaning": "Flame loss — unit ignited but flame went out.",
        "causes": [
            "Wind gusts blowing out the flame through the vent",
            "Gas pressure fluctuation under load",
            "Dirty flame rod losing signal",
            "Loose flame rod wire connection",
            "Vent issue causing intermittent exhaust restriction",
        ],
        "action": "If intermittent/windy-day issue, check vent termination for wind exposure. Check gas pressure at the unit while firing at full rate. Clean flame rod. Secure all wiring connections. Check for loose vent joints.",
    },
    "14": {
        "meaning": "Thermal fuse tripped — overheat safety activated.",
        "causes": [
            "Overheat condition from scale buildup",
            "Airflow restriction through the unit",
            "Thermal fuse degraded (one-time use on some models)",
        ],
        "action": "This is a safety device — find the root cause before resetting. Check for scale buildup and flush if needed. Ensure proper clearances around the unit. On some Noritz models the thermal fuse is a one-shot device and must be replaced even after the cause is fixed.",
    },
    "16": {
        "meaning": "Overheating — water temperature exceeded safe limits.",
        "causes": [
            "Scale buildup in heat exchanger (hard water)",
            "Low water flow rate",
            "Recirculation pump issue",
            "Temperature setting too high",
        ],
        "action": "Flush the heat exchanger with descaling solution. Check water flow rate — minimum is usually 0.5 GPM. If on a recirculation system, verify pump and check valve operation. In hard water areas, set up an annual flushing schedule.",
    },
    "29": {
        "meaning": "Condensate drain issue — condensate not draining properly.",
        "causes": [
            "Clogged condensate drain line",
            "Condensate trap full or blocked",
            "Neutralizer cartridge plugged",
            "Drain line frozen (cold climates)",
        ],
        "action": "Clear the condensate drain line — blow it out with compressed air or flush with water. Clean the condensate trap. Check the neutralizer if equipped. In cold climates, check for frozen drain lines.",
    },
    "31": {
        "meaning": "Inlet water temperature sensor fault.",
        "causes": [
            "Failed inlet thermistor",
            "Loose or corroded sensor connector",
            "Wiring damage",
        ],
        "action": "Check sensor resistance with a meter and compare to the spec chart. Inspect connector for corrosion. Replace sensor if out of spec.",
    },
    "32": {
        "meaning": "Outgoing water temperature sensor fault.",
        "causes": [
            "Failed outlet thermistor",
            "Loose connector",
            "Corroded or water-damaged wiring",
        ],
        "action": "Check outlet temp sensor resistance. Inspect connector and wiring. Replace if out of spec. Same process as code 31 but on the outlet side.",
    },
    "33": {
        "meaning": "Heat exchanger temperature sensor fault.",
        "causes": [
            "Failed heat exchanger thermistor",
            "Sensor displaced from its mounting position",
            "Connector issue",
        ],
        "action": "Check sensor resistance. Verify the sensor is properly seated in its well on the heat exchanger. Inspect connector at the PCB. Replace if readings are out of spec.",
    },
    "43": {
        "meaning": "Abnormal discharge temperature — exhaust too hot.",
        "causes": [
            "Scale buildup causing inefficient heat transfer",
            "Exhaust restriction",
            "Fan motor running slowly",
            "High gas pressure overfiring the unit",
        ],
        "action": "Flush the heat exchanger. Check the vent run for obstructions. Verify fan motor speed. Check gas pressure against the rating plate — overfiring causes high exhaust temps.",
    },
    "51": {
        "meaning": "Gas solenoid valve fault — main gas valve issue.",
        "causes": [
            "Gas valve coil failure",
            "Wiring issue to gas valve",
            "PCB not sending signal",
        ],
        "action": "Check for voltage at the gas valve coils during ignition. If voltage present but valve doesn't open, replace the gas valve. If no voltage, check PCB output and wiring.",
    },
    "52": {
        "meaning": "Modulating solenoid valve fault — proportional valve issue.",
        "causes": [
            "Modulating valve coil failure",
            "Wiring fault",
            "PCB modulation circuit failure",
        ],
        "action": "Check the modulating valve coil for continuity. Verify wiring between PCB and valve. If the coil is good and wiring intact, the PCB modulation output may be faulty.",
    },
    "57": {
        "meaning": "Bypass valve fault — water bypass servo issue.",
        "causes": [
            "Bypass valve motor failure",
            "Scale or debris jamming the valve",
            "Wiring disconnected",
        ],
        "action": "Check for voltage/signal at the bypass valve motor. Try running the valve manually if accessible. Scale can jam these — flush the unit. If motor has power but doesn't move, replace it.",
    },
    "61": {
        "meaning": "Fan motor fault — combustion blower issue.",
        "causes": [
            "Fan motor failure",
            "Wiring issue",
            "Debris on fan blades",
            "PCB fan output failure",
        ],
        "action": "Check for voltage at the fan motor connector. Listen for the motor — does it hum but not spin? That indicates a seized bearing. Inspect blades for buildup. If voltage present and motor won't run, replace it.",
    },
    "70": {
        "meaning": "PCB fault — main control board failure.",
        "causes": [
            "Power surge damage",
            "Moisture intrusion",
            "Component failure",
        ],
        "action": "Power cycle the unit (off for 30 seconds). If code returns, inspect PCB for visible damage. Check for moisture inside the unit. PCB replacement is likely needed — check for updated part numbers as Noritz has revised some boards.",
    },
    "71": {
        "meaning": "Gas valve circuit fault — electrical issue in the gas valve wiring.",
        "causes": [
            "Open circuit in gas valve wiring",
            "Gas valve relay on PCB failed",
            "Gas valve coil burned open",
        ],
        "action": "Check gas valve coil resistance. Verify wiring continuity from PCB to gas valve. If coil and wiring are good, the PCB relay is likely failed.",
    },
    "72": {
        "meaning": "Flame detection after shutoff — flame signal present when gas should be off.",
        "causes": [
            "Gas valve not sealing completely (internal leak)",
            "Flame rod signal due to moisture or carbon bridging",
            "Residual flame from slow valve closure",
        ],
        "action": "SAFETY CONCERN — this means gas may be leaking through the valve. Shut off gas supply. Check for flame presence visually. If gas is leaking through the valve, replace the gas valve immediately. If no actual flame, check flame rod for false signal.",
    },
    "73": {
        "meaning": "Abnormal combustion temperature rise — temp climbing too fast.",
        "causes": [
            "Scale buildup on heat exchanger",
            "Low water flow",
            "Gas pressure too high",
        ],
        "action": "Flush the heat exchanger. Check water flow rate and inlet filter. Verify gas pressure. A fast temp rise means the heat exchanger isn't transferring heat efficiently — scale is the usual culprit.",
    },
    "90": {
        "meaning": "Combustion abnormality — general combustion fault.",
        "causes": [
            "Vent system issue",
            "Gas quality problem",
            "Dirty burner",
            "Air/fuel ratio out of spec",
        ],
        "action": "Run combustion analysis if possible. Check venting thoroughly. Inspect burner for debris or clogging. Verify gas type matches the unit (natural gas vs LP). Check gas pressure.",
    },
    "99": {
        "meaning": "Freeze prevention error — anti-freeze system activated or failed.",
        "causes": [
            "Unit exposed to freezing temperatures without power",
            "Freeze prevention heater failure",
            "Drain-back system failure",
            "Power outage during freezing weather",
        ],
        "action": "Check for freeze damage — inspect heat exchanger and water connections for cracks or leaks. If the unit froze, water damage may be extensive. Verify the freeze prevention circuit is working. If the unit has power and is still showing this code, the freeze prevention heater may be failed.",
    },
}

LG_MINI_SPLIT_CODES = {
    "CH01": {
        "meaning": "Indoor temperature sensor error — room temp thermistor fault.",
        "causes": [
            "Failed room temperature thermistor",
            "Loose connector at sensor or PCB",
            "Wiring damage between sensor and board",
        ],
        "action": "Check the room temp sensor resistance — compare to the resistance/temperature chart in the service manual. Inspect the connector at the indoor PCB. If resistance is out of range, replace the thermistor.",
    },
    "CH02": {
        "meaning": "Indoor pipe (coil) temperature sensor error.",
        "causes": [
            "Failed coil thermistor (most common)",
            "Sensor displaced from its clip on the coil",
            "Corroded connector",
        ],
        "action": "Check coil sensor resistance against the chart. Make sure the sensor is properly clipped to the coil — if it falls off it reads ambient instead of coil temp. Replace if out of spec.",
    },
    "CH03": {
        "meaning": "Drain sensor error — condensate overflow detection.",
        "causes": [
            "Clogged condensate drain line causing water backup",
            "Drain sensor float stuck in the up position",
            "Failed drain sensor",
        ],
        "action": "Check the condensate drain first — this is usually a clogged drain, not a bad sensor. Clear the drain line with compressed air or a wet/dry vac. Clean the drain pan. If drain is clear, check the float switch or sensor.",
    },
    "CH04": {
        "meaning": "Indoor freeze protection — coil temperature too low.",
        "causes": [
            "Dirty air filter restricting airflow",
            "Indoor fan motor running slow or failing",
            "Low refrigerant charge",
            "Restricted metering device (TXV or capillary tube)",
        ],
        "action": "Check and clean the air filter first. Verify indoor fan is running at proper speed. Check refrigerant pressures — low charge is common. If charge is correct, check the metering device for restriction.",
    },
    "CH05": {
        "meaning": "Indoor to outdoor communication error.",
        "causes": [
            "Communication wire loose or disconnected",
            "Communication wire damaged (rodent damage, pinched)",
            "Incorrect wiring between indoor and outdoor units",
            "Outdoor PCB failure",
            "Power issue to outdoor unit",
        ],
        "action": "Check communication wire connections at both indoor and outdoor units. Verify wiring matches the diagram — LG uses specific comm wire configurations. Check for voltage at the outdoor unit. Inspect wire run for damage. If wiring is good, try swapping the indoor PCB first (cheaper than outdoor).",
    },
    "CH06": {
        "meaning": "Outdoor coil temperature sensor error.",
        "causes": [
            "Failed outdoor coil thermistor",
            "Connector corroded from weather exposure",
            "Wiring damage in the outdoor unit",
        ],
        "action": "Check outdoor coil sensor resistance against the spec chart. Inspect connector for corrosion — outdoor sensors take a beating from weather. Replace sensor if out of range.",
    },
    "CH07": {
        "meaning": "Outdoor discharge temperature sensor error.",
        "causes": [
            "Failed discharge temp sensor",
            "Sensor not properly attached to the discharge line",
            "Wiring issue",
        ],
        "action": "Check discharge temp sensor resistance. Verify it's clamped tightly to the discharge line with proper insulation. Replace if readings are out of spec.",
    },
    "CH09": {
        "meaning": "Indoor EEPROM error — memory chip fault on indoor PCB.",
        "causes": [
            "Indoor PCB EEPROM corruption from power surge",
            "Indoor PCB hardware failure",
            "Incorrect firmware for the model",
        ],
        "action": "Power cycle the indoor unit — unplug for 2 minutes. If code persists, the indoor PCB needs replacement. Make sure the replacement board has the correct firmware for the model number.",
    },
    "CH10": {
        "meaning": "Indoor fan motor error — motor not running or running abnormally.",
        "causes": [
            "Indoor fan motor failure",
            "Fan blade hitting something or out of balance",
            "Motor connector loose",
            "Indoor PCB motor driver circuit failure",
        ],
        "action": "Listen for the motor — is it humming but not spinning? Check for debris blocking the fan wheel. Verify motor connector is secure. Check voltage/signal at the motor connector during operation. If power is present but motor doesn't run, replace the motor. LG uses DC motors — check the hall sensor if applicable.",
    },
    "CH21": {
        "meaning": "Outdoor inverter compressor overcurrent.",
        "causes": [
            "Compressor electrical fault (winding-to-winding or winding-to-ground)",
            "Inverter board failure",
            "Locked rotor condition from liquid slugging",
            "Loose compressor wiring",
        ],
        "action": "Check compressor windings — measure resistance between all three phases (should be balanced) and from each phase to ground (should be infinite). If windings check out, inspect the inverter board. Check for liquid refrigerant at the compressor (frosted suction line at compressor = possible liquid flood).",
    },
    "CH22": {
        "meaning": "Outdoor current sensor (CT) error.",
        "causes": [
            "Current transformer sensor failure",
            "CT sensor wiring issue",
            "Outdoor PCB fault reading the CT signal",
        ],
        "action": "Inspect the CT sensor on the compressor power leads — it's a ring that the wire passes through. Check its connector at the outdoor PCB. If the sensor is cracked or damaged, replace it.",
    },
    "CH23": {
        "meaning": "Outdoor DC link voltage error — inverter power supply issue.",
        "causes": [
            "Power supply voltage too high or too low",
            "Inverter board capacitor failure",
            "Incoming power issue (brownout, phase loss)",
        ],
        "action": "Check incoming power voltage at the outdoor unit disconnect. Should be within 10% of nameplate rating. If voltage is good, the inverter board likely has a failed capacitor or rectifier — inspect for bulging capacitors. Replace inverter board if damaged.",
    },
    "CH25": {
        "meaning": "Outdoor AC voltage error — power supply voltage out of range.",
        "causes": [
            "Utility voltage too high or too low",
            "Bad connection at disconnect or breaker",
            "Undersized wire run causing voltage drop",
        ],
        "action": "Check voltage at the outdoor unit disconnect — must be within 10% of nameplate. Check all connections from breaker to disconnect to unit for hot spots or loose terminals. If voltage is consistently out of range, contact the utility.",
    },
    "CH26": {
        "meaning": "Outdoor compressor overheat protection — discharge temp too high.",
        "causes": [
            "Low refrigerant charge (most common cause of high discharge temp)",
            "Restricted metering device",
            "Dirty outdoor coil blocking heat rejection",
            "Compressor valve damage",
        ],
        "action": "Check refrigerant charge — low charge is the #1 cause of high discharge temp. Clean the outdoor coil thoroughly. Check superheat and subcooling. If charge is correct and coil is clean, the compressor may have valve damage.",
    },
    "CH27": {
        "meaning": "Outdoor communication error with inverter board.",
        "causes": [
            "Communication cable between outdoor main PCB and inverter board loose",
            "Inverter board failure",
            "Main outdoor PCB failure",
        ],
        "action": "Check the ribbon cable or connector between the outdoor main PCB and the inverter PCB. Reseat it firmly. If code persists, try replacing the inverter board first.",
    },
    "CH32": {
        "meaning": "Outdoor coil temperature sensor error.",
        "causes": [
            "Failed outdoor coil thermistor",
            "Corroded connector (outdoor exposure)",
            "Wiring damage",
        ],
        "action": "Check sensor resistance. Inspect for weather-related corrosion on the connector. Replace if out of spec. Same process as CH06 — LG uses multiple coil sensors on some models.",
    },
    "CH33": {
        "meaning": "Outdoor suction temperature sensor error.",
        "causes": [
            "Failed suction line thermistor",
            "Sensor not properly mounted on suction line",
            "Wiring or connector issue",
        ],
        "action": "Check suction temp sensor resistance. Verify sensor is firmly clamped to the suction line with insulation tape over it. Replace if out of spec.",
    },
    "CH34": {
        "meaning": "High pressure switch activated — system pressure too high.",
        "causes": [
            "Dirty outdoor coil (most common)",
            "Outdoor fan motor not running",
            "Overcharged system",
            "Non-condensable gases in the system (air)",
            "Restricted condenser airflow (debris, vegetation)",
        ],
        "action": "Clean the outdoor coil thoroughly. Verify outdoor fan is running. Check for debris or vegetation blocking airflow. Check head pressure — if high with clean coil and good fan, system may be overcharged or have non-condensables. May need to recover, evacuate, and recharge.",
    },
    "CH38": {
        "meaning": "Outdoor ambient temperature sensor error.",
        "causes": [
            "Failed ambient temp thermistor",
            "Sensor exposure to direct sunlight giving false readings",
            "Connector corroded",
        ],
        "action": "Check ambient temp sensor resistance. Verify sensor placement — it should be shielded from direct sunlight. Replace if out of spec.",
    },
    "CH40": {
        "meaning": "Outdoor CT (current transformer) sensor error.",
        "causes": [
            "CT sensor failure",
            "CT sensor disconnected or improperly installed",
            "Outdoor PCB input circuit failure",
        ],
        "action": "Inspect the CT sensor — make sure the compressor power wire passes through the center of the ring. Check connector. Replace CT sensor if damaged.",
    },
    "CH44": {
        "meaning": "Outdoor air temperature sensor error.",
        "causes": [
            "Failed outdoor air temp sensor",
            "Wiring damage from UV exposure or rodents",
            "Connector corrosion",
        ],
        "action": "Check sensor resistance. Inspect wiring — outdoor sensor wiring is exposed to UV and weather. Replace sensor if out of spec.",
    },
    "CH53": {
        "meaning": "Indoor/outdoor unit mismatch — incompatible combination.",
        "causes": [
            "Indoor unit model not compatible with outdoor unit",
            "Incorrect DIP switch or jumper settings",
            "Wrong indoor unit connected during multi-zone installation",
        ],
        "action": "Verify the indoor and outdoor model numbers are a compatible match using LG's compatibility chart. Check DIP switch settings on both units. On multi-zone systems, verify each indoor unit is connected to the correct port.",
    },
    "CH67": {
        "meaning": "Outdoor fan motor lock — motor is stuck.",
        "causes": [
            "Fan blade physically blocked by debris or ice",
            "Fan motor bearing seized",
            "Motor winding failure",
            "Fan blade cracked and rubbing on shroud",
        ],
        "action": "Check for physical obstruction of the fan — debris, ice, or a cracked blade hitting the housing. Try spinning the fan by hand (power off!) — it should spin freely. If the motor is seized or has a burnt smell, replace it.",
    },
}

SAMSUNG_MINI_SPLIT_CODES = {
    "E101": {
        "meaning": "Communication error between indoor and outdoor units.",
        "causes": [
            "Communication wire loose or disconnected at either unit",
            "Damaged communication cable (rodent damage, pinched wire)",
            "Incorrect wiring between units",
            "Power supply issue to one of the units",
            "PCB failure on either unit",
        ],
        "action": "Check communication wire connections at both units — pull and reseat each connector. Verify wiring matches the diagram. Check for voltage at both units. Inspect wire run for damage. If wiring is sound, try power cycling both units.",
    },
    "E121": {
        "meaning": "Indoor room temperature sensor error.",
        "causes": [
            "Failed room temp thermistor",
            "Loose or corroded connector",
            "Wiring damage",
        ],
        "action": "Check room temp sensor resistance against the spec chart. Inspect connector at the indoor PCB. Replace the thermistor if resistance is out of range.",
    },
    "E122": {
        "meaning": "Indoor coil (pipe) temperature sensor error.",
        "causes": [
            "Failed coil thermistor",
            "Sensor displaced from the coil",
            "Connector corroded or loose",
        ],
        "action": "Check coil sensor resistance. Verify sensor is properly clipped to the coil. Replace if out of spec.",
    },
    "E154": {
        "meaning": "Indoor fan motor error — motor not operating correctly.",
        "causes": [
            "Indoor fan motor failure",
            "Fan wheel blocked or out of balance",
            "Motor connector loose on the PCB",
            "PCB motor driver circuit failure",
        ],
        "action": "Check for debris blocking the fan wheel. Verify motor connector is seated firmly. Check voltage at the motor connector during operation. If power is present but motor won't run, replace the motor.",
    },
    "E162": {
        "meaning": "Indoor EEPROM error — memory chip fault.",
        "causes": [
            "EEPROM corruption from power surge",
            "Indoor PCB hardware failure",
        ],
        "action": "Power cycle the indoor unit for 2 minutes. If code persists, the indoor PCB needs replacement.",
    },
    "E201": {
        "meaning": "Outdoor temperature sensor error.",
        "causes": [
            "Failed outdoor temp thermistor",
            "Corroded connector due to weather exposure",
            "Wiring damage",
        ],
        "action": "Check outdoor temp sensor resistance. Inspect connector for corrosion — outdoor sensors are exposed to the elements. Replace if out of range.",
    },
    "E202": {
        "meaning": "Outdoor coil temperature sensor error.",
        "causes": [
            "Failed outdoor coil thermistor",
            "Corroded or weather-damaged connector",
            "Sensor displaced from coil",
        ],
        "action": "Check outdoor coil sensor resistance. Verify sensor is clipped to the coil properly. Replace if readings are out of spec.",
    },
    "E221": {
        "meaning": "Outdoor compressor overload — mechanical or electrical overload.",
        "causes": [
            "Compressor winding fault",
            "Locked rotor from liquid slugging or mechanical seizure",
            "Power supply issue (low voltage)",
            "Overcharged system causing high head pressure",
        ],
        "action": "Check compressor windings for shorts and grounds. Measure supply voltage. Check refrigerant pressures. If compressor is mechanically locked (no start, high amp draw), it may need replacement.",
    },
    "E236": {
        "meaning": "Compressor overcurrent — drawing too many amps.",
        "causes": [
            "Compressor starting to fail electrically",
            "Low voltage at the unit",
            "High head pressure from dirty coil or overcharge",
            "Inverter board issue sending incorrect drive signal",
        ],
        "action": "Measure compressor amp draw and compare to nameplate RLA. Check supply voltage. Clean outdoor coil. Check refrigerant charge. If amps are high with correct voltage and charge, compressor is likely failing.",
    },
    "E251": {
        "meaning": "Outdoor DC link voltage error — inverter power stage issue.",
        "causes": [
            "Power supply voltage fluctuation",
            "Inverter board capacitor or rectifier failure",
            "Incoming power quality issue",
        ],
        "action": "Check incoming voltage at the unit. Inspect the inverter board for bulging capacitors or burnt components. If voltage is stable and board looks clean, replace the inverter board.",
    },
    "E301": {
        "meaning": "Communication error between outdoor PCBs — board-to-board comm fault.",
        "causes": [
            "Ribbon cable or connector loose between boards",
            "PCB failure",
            "Moisture damage to outdoor electronics",
        ],
        "action": "Open the outdoor electrical box and reseat all ribbon cables and connectors between boards. Check for moisture intrusion. If connections are solid and dry, one of the PCBs needs replacement.",
    },
    "E401": {
        "meaning": "Condensate drain error — indoor unit drain problem.",
        "causes": [
            "Clogged condensate drain line (most common)",
            "Drain pan full — drain sensor triggered",
            "Drain pump failure (if equipped)",
            "Drain sensor fault",
        ],
        "action": "Clear the condensate drain line — use compressed air or a wet/dry vac from outside. Clean the drain pan. If the unit has a condensate pump, verify pump operation. This is almost always a clogged drain line.",
    },
    "E416": {
        "meaning": "Freeze protection activated — indoor coil too cold.",
        "causes": [
            "Dirty air filter (check this first)",
            "Low refrigerant charge",
            "Indoor fan motor running too slow",
            "Metering device restriction",
        ],
        "action": "Check and replace the air filter. Verify refrigerant charge. Check indoor fan speed. If filter is clean and charge is correct, check the metering device.",
    },
    "E441": {
        "meaning": "High pressure protection activated.",
        "causes": [
            "Dirty outdoor coil (most common)",
            "Outdoor fan not running",
            "Overcharged system",
            "Restricted airflow around outdoor unit",
            "Non-condensable gases in system",
        ],
        "action": "Clean outdoor coil thoroughly. Verify outdoor fan is operating. Check for vegetation, fencing, or debris restricting airflow around the outdoor unit. Check head pressure and charge.",
    },
    "E442": {
        "meaning": "Low pressure protection activated.",
        "causes": [
            "Refrigerant leak / low charge (most common)",
            "Indoor coil iced up",
            "Metering device restriction",
            "Dirty indoor filter",
        ],
        "action": "Check refrigerant pressures. If low, find and repair the leak, then recharge. Check for ice on the indoor coil. Clean the air filter. If pressures are correct, check the metering device.",
    },
    "E464": {
        "meaning": "PFC (Power Factor Correction) circuit error — outdoor board.",
        "causes": [
            "PFC circuit failure on the inverter board",
            "Power surge damage",
            "Input power quality issue",
        ],
        "action": "Check incoming power quality and voltage. Inspect the inverter/PFC board for visible damage. This is typically a board-level failure requiring inverter board replacement.",
    },
}

WEIL_MCLAIN_BOILER_CODES = {
    "E01": {
        "meaning": "Ignition failure — boiler failed to light.",
        "causes": [
            "Gas supply off or low gas pressure",
            "Igniter failure",
            "Dirty flame sensor / flame rod",
            "Condensate drain blocked causing exhaust restriction",
            "Vent termination blocked",
        ],
        "action": "Verify gas is on and pressure is correct. Check igniter for spark. Clean flame sensor with fine emery cloth. Check condensate drain and vent termination. Reset the boiler and try again — if it fails 3 times, dig deeper.",
    },
    "E02": {
        "meaning": "Flame failure — flame was established but lost.",
        "causes": [
            "Dirty flame sensor (most common)",
            "Gas pressure dropping under load",
            "Loose flame sensor wiring",
            "Wind downdraft through vent",
            "Condensate drain restriction",
        ],
        "action": "Clean the flame sensor first — this resolves most E02 codes. Check gas pressure while the boiler is firing. Secure all wiring connections. Check vent termination for wind exposure. Clear condensate drain.",
    },
    "E03": {
        "meaning": "High limit / overheat — temperature exceeded safe limit.",
        "causes": [
            "Air in the system (most common after new install or repair)",
            "Circulation pump failure",
            "Flow restriction in the piping",
            "Faulty high limit switch",
        ],
        "action": "Bleed air from the system — check all high points and radiators. Verify circulation pump is running (feel for vibration, check amp draw). Check for closed valves or restrictions in the piping. Let the boiler cool before resetting.",
    },
    "E04": {
        "meaning": "Low water cutoff activated — insufficient water in the system.",
        "causes": [
            "System water level low (leak in the system)",
            "Auto-fill valve not working",
            "Low water cutoff sensor faulty",
            "Air in the system causing sensor misread",
        ],
        "action": "Check system pressure gauge — is water pressure low? If so, there may be a leak. Check the auto-fill valve (pressure reducing valve) — it should maintain 12-15 PSI cold. Top up the system and look for leaks. If pressure is fine, the low water cutoff sensor may be faulty.",
    },
    "E05": {
        "meaning": "Pressure switch fault — combustion air pressure switch issue.",
        "causes": [
            "Blocked vent or intake pipe",
            "Inducer motor not running or weak",
            "Pressure switch hose cracked, kinked, or water-logged",
            "Pressure switch failure",
        ],
        "action": "Check the vent and intake for blockage. Verify inducer motor is running. Inspect the pressure switch hose — look for cracks, kinks, or water in the tubing. Test the pressure switch with a manometer to verify it's making/breaking at the right pressure.",
    },
    "E06": {
        "meaning": "Blower (inducer) motor fault.",
        "causes": [
            "Inducer motor failure",
            "Motor capacitor (if equipped) failure",
            "Wiring issue to the motor",
            "Debris in the inducer housing",
        ],
        "action": "Listen for the inducer — does it try to start? Check for voltage at the motor during ignition sequence. Inspect inducer housing for debris. If motor hums but doesn't spin, bearings may be seized. Replace motor if faulty.",
    },
    "E08": {
        "meaning": "Gas valve fault — gas valve not operating correctly.",
        "causes": [
            "Gas valve coil failure",
            "Wiring issue from control board to gas valve",
            "Control board relay failure",
            "Gas valve stuck closed",
        ],
        "action": "Check for voltage at the gas valve during ignition. If voltage present but valve won't open, replace the gas valve. If no voltage, check wiring and control board output.",
    },
    "E10": {
        "meaning": "Sensor fault — temperature sensor error.",
        "causes": [
            "Failed supply or return water temperature sensor",
            "Loose sensor connector",
            "Corroded sensor wiring",
        ],
        "action": "Check temperature sensor resistance and compare to the chart in the manual. Weil-McLain uses thermistors — their resistance changes with temperature. Check connectors and wiring. Replace sensor if out of spec.",
    },
    "E12": {
        "meaning": "Water pressure low — system pressure below minimum.",
        "causes": [
            "Leak in the heating system (piping, radiators, fittings)",
            "Expansion tank waterlogged or failed (pre-charge lost)",
            "Pressure relief valve leaking",
            "Auto-fill valve not feeding water",
        ],
        "action": "Check system pressure gauge. Inspect the expansion tank (press the Schrader valve — if water comes out, the tank bladder is ruptured). Check the pressure relief valve for dripping. Look for leaks throughout the system. Verify auto-fill valve is working.",
    },
    "E28": {
        "meaning": "Condensate drain issue — condensate not draining properly.",
        "causes": [
            "Clogged condensate drain line",
            "Condensate trap blocked",
            "Frozen drain line (cold climates)",
            "Neutralizer (if equipped) plugged",
        ],
        "action": "Clear the condensate drain line. Clean the condensate trap. In cold climates, check for frozen drain lines. If there's a neutralizer, check it for blockage.",
    },
    "E30": {
        "meaning": "Flame signal low — flame rod detecting weak flame.",
        "causes": [
            "Dirty flame sensor (most common)",
            "Flame sensor corroded or deteriorated",
            "Low gas pressure causing weak flame",
            "Improper grounding of the boiler",
        ],
        "action": "Clean the flame sensor with fine emery cloth — this is almost always the fix. If it keeps coming back, check the flame sensor microamp reading (should be above 1.0 uA for most Weil-McLain boilers). Check gas pressure. Verify the boiler has a good ground — poor grounding affects flame sensing.",
    },
    "E31": {
        "meaning": "Communication error — control board communication fault.",
        "causes": [
            "Communication cable loose between control modules",
            "Control module failure",
            "Power surge damage to communication circuits",
        ],
        "action": "Check all communication cables between the boiler control modules — reseat each connector. Power cycle the boiler. If code persists, one of the control modules may need replacement.",
    },
}

NAVIEN_BOILER_CODES = {
    "E003": {
        "meaning": "Ignition failure — boiler failed to light.",
        "causes": [
            "Gas supply off or low gas pressure (most common)",
            "Igniter failure or weak spark",
            "Dirty or corroded flame rod",
            "Condensate drain backup",
            "Vent termination blocked",
        ],
        "action": "Verify gas is on and pressure is correct. Check igniter for spark. Clean flame rod with fine emery cloth. Check condensate drain. Inspect vent termination. Same diagnostic process as the tankless E003.",
    },
    "E012": {
        "meaning": "Flame loss during heating operation.",
        "causes": [
            "Gas pressure dropping under load",
            "Dirty flame rod",
            "Wind downdraft in vent system",
            "Loose flame rod wiring",
        ],
        "action": "Check gas pressure while unit is firing at full rate. Clean flame rod. Check vent termination for wind exposure. Secure wiring connections.",
    },
    "E016": {
        "meaning": "Overheating — overheat protection activated.",
        "causes": [
            "Scale buildup in heat exchanger",
            "Circulation pump failure",
            "Air in the heating system",
            "Flow restriction (closed valve, clogged strainer)",
        ],
        "action": "Flush the heat exchanger with descaling solution. Verify circulation pump is running. Bleed air from the system. Check all valves are open and strainers are clear.",
    },
    "E030": {
        "meaning": "Air/fuel ratio imbalance in heating mode.",
        "causes": [
            "Vent system obstruction",
            "High altitude without proper setup",
            "APS sensor issue",
            "Gas pressure out of spec",
        ],
        "action": "Check venting for obstructions. Verify altitude settings. Check APS sensor. Verify gas pressure against the spec plate.",
    },
    "E302": {
        "meaning": "Low water flow in the heating circuit.",
        "causes": [
            "Circulation pump not running or weak",
            "Air lock in the piping",
            "Closed isolation valve",
            "Clogged strainer or filter",
            "System piping undersized for the flow rate needed",
        ],
        "action": "Verify circulation pump is running — feel for vibration, check amp draw. Bleed air from the system at all high points. Check all isolation valves are open. Clean strainers. Check system pressure — low pressure may indicate a leak or waterlogged expansion tank.",
    },
    "E351": {
        "meaning": "DHW (domestic hot water) thermistor fault on combi boiler.",
        "causes": [
            "Failed DHW temperature sensor",
            "Loose connector",
            "Corroded wiring",
        ],
        "action": "Check DHW thermistor resistance. Inspect connector and wiring. Replace sensor if out of spec.",
    },
    "E407": {
        "meaning": "Thermistor short — heating circuit temperature sensor shorted.",
        "causes": [
            "Shorted thermistor (internal failure)",
            "Pinched sensor wire",
            "Water intrusion into connector",
        ],
        "action": "Check thermistor resistance — a short reads near 0 ohms. Inspect wiring for damage. Replace the thermistor.",
    },
    "E421": {
        "meaning": "Thermistor open — heating circuit temperature sensor open circuit.",
        "causes": [
            "Open thermistor (internal failure)",
            "Broken wire or disconnected sensor",
            "Corroded connector",
        ],
        "action": "Check thermistor resistance — open circuit reads OL on meter. Check wiring continuity. Replace the thermistor.",
    },
    "E515": {
        "meaning": "Mixing valve flow abnormality in heating mode.",
        "causes": [
            "Mixing valve motor stuck or failed",
            "Scale or debris in the mixing valve",
            "Flow sensor disagreement with valve position",
        ],
        "action": "Check mixing valve motor operation. Flush if scale is suspected. Verify flow sensor readings. May need mixing valve assembly replacement.",
    },
}

# ---------------------------------------------------------------------------
# Appliance Error Codes — split by brand for precise matching
# ---------------------------------------------------------------------------

APPLIANCE_LG_WASHER_CODES = {
    "LE": {
        "meaning": "Motor overload or locked motor — motor can't turn.",
        "causes": [
            "Overloaded drum (too many clothes)",
            "Motor rotor position sensor failure",
            "Stator winding damage",
            "Worn motor brushes (older models)",
            "Object lodged between drum and tub",
        ],
        "action": "Remove some clothes and try again — overloading is the #1 cause. If it happens with a normal load, check for objects between the inner drum and outer tub. Inspect the rotor position sensor (hall sensor). On direct-drive models, check the stator for burnt windings.",
    },
    "LE1": {
        "meaning": "Motor locked — rotor cannot turn.",
        "causes": [
            "Object jammed between drum and tub",
            "Motor rotor magnet cracked or detached",
            "Stator failure",
        ],
        "action": "Same as LE — check for foreign objects first. Inspect the rotor magnet assembly for cracks. Check stator windings for continuity.",
    },
    "UE": {
        "meaning": "Unbalanced load — washer can't balance the drum during spin.",
        "causes": [
            "Single heavy item (blanket, comforter)",
            "Small load bunched to one side",
            "Washer not level",
            "Shock absorbers or suspension springs worn",
        ],
        "action": "Redistribute the load — add a few towels to balance a single heavy item. Level the washer with a bubble level. If it happens frequently with normal loads, check the suspension system (shock absorbers and springs) for wear.",
    },
    "OE": {
        "meaning": "Drain pump fault — water won't drain.",
        "causes": [
            "Drain filter clogged with coins, lint, or debris (most common)",
            "Drain hose kinked or clogged",
            "Drain pump impeller jammed or motor failed",
            "Drain hose too high (siphon issue)",
        ],
        "action": "Clean the drain filter first — it's behind the small door at the bottom front. You'll find coins, hair ties, lint, and small socks. Check the drain hose for kinks. If the filter is clean, check the pump motor — you should hear it try to run.",
    },
    "IE": {
        "meaning": "Water inlet fault — washer not filling with water.",
        "causes": [
            "Water supply turned off (check both hot and cold)",
            "Inlet screens clogged with sediment",
            "Water inlet valve failure",
            "Low water pressure",
        ],
        "action": "Check that both hot and cold faucets are on. Inspect the inlet hose screens — unscrew the hoses at the washer and clean the screens. If water pressure is good and screens are clear, the inlet valve may be failed.",
    },
    "PE": {
        "meaning": "Pressure sensor fault — water level sensor issue.",
        "causes": [
            "Pressure switch (transducer) failure",
            "Pressure hose kinked, cracked, or disconnected",
            "Clogged pressure hose (suds or debris)",
        ],
        "action": "Check the pressure hose that runs from the tub to the pressure sensor — it may be kinked, cracked, or clogged with soap residue. Blow through it gently to clear it. If the hose is good, replace the pressure sensor.",
    },
    "FE": {
        "meaning": "Overfill error — too much water in the tub.",
        "causes": [
            "Water inlet valve stuck open",
            "Pressure sensor misreading",
            "Control board sending incorrect fill signal",
        ],
        "action": "CAUTION — if water is overflowing, turn off the water supply. Check if the inlet valve closes when power is removed — if water keeps flowing, the valve is stuck open and must be replaced. If valve is okay, check the pressure sensor.",
    },
    "DE": {
        "meaning": "Door lock error — door latch isn't engaging.",
        "causes": [
            "Something caught in the door seal preventing closure",
            "Door lock mechanism failure",
            "Door latch broken or misaligned",
            "Wiring issue to door lock",
        ],
        "action": "Check the door seal for clothing or debris preventing full closure. Try closing the door firmly. If the door closes but doesn't lock, the door lock mechanism is likely failed — they're a common wear part on LG washers.",
    },
    "TE": {
        "meaning": "Thermistor/heater error — water temp sensor fault.",
        "causes": [
            "Failed thermistor (temperature sensor)",
            "Heater element failure (on models with internal heater)",
            "Wiring issue",
        ],
        "action": "Check the water temperature sensor resistance — it's usually on or near the tub. If the washer uses an internal heater, check the heater element for continuity as well.",
    },
    "PF": {
        "meaning": "Power failure — washer lost power during a cycle.",
        "causes": [
            "Brief power outage during operation",
            "Loose power cord connection",
            "Outlet issue",
        ],
        "action": "Press start to resume the cycle. If it keeps happening, check the power cord and outlet. Consider plugging the washer directly into the wall (not an extension cord or power strip).",
    },
    "CL": {
        "meaning": "Child lock active — not an error, it's a feature.",
        "causes": [
            "Child lock was activated (intentionally or accidentally)",
        ],
        "action": "Press and hold the Child Lock button for 3-5 seconds to deactivate. On some models it's a button combination. Check the owner's manual for the specific model.",
    },
    "SUD": {
        "meaning": "Excessive suds detected — too much soap.",
        "causes": [
            "Too much detergent used",
            "Wrong type of detergent (non-HE detergent in HE washer)",
            "Cheap or low-quality detergent that over-suds",
        ],
        "action": "Use HE (High Efficiency) detergent only, and use less than you think you need — 1 to 2 tablespoons for a full load. The washer will try to rinse out the extra suds. Run an empty cycle with no detergent to clear residual soap buildup.",
    },
    "SD": {
        "meaning": "Excessive suds — same as Sud.",
        "causes": [
            "Too much detergent (most common)",
            "Non-HE detergent used",
        ],
        "action": "Same as Sud code — reduce detergent amount and use HE formula only.",
    },
}

APPLIANCE_SAMSUNG_WASHER_CODES = {
    "1E": {
        "meaning": "Water level sensor error — pressure sensor fault.",
        "causes": [
            "Pressure sensor (frequency sensor) failure",
            "Pressure hose clogged or disconnected",
            "Control board issue",
        ],
        "action": "Check the pressure hose from the tub to the sensor — it may be kinked or clogged with soap residue. Blow through it gently. If the hose is clear, the pressure sensor or main board may be faulty.",
    },
    "SE": {
        "meaning": "Water level sensor error — same as 1E on some models.",
        "causes": [
            "Pressure sensor failure",
            "Clogged pressure hose",
        ],
        "action": "Same as 1E — check pressure hose first, then sensor.",
    },
    "5E": {
        "meaning": "Drain error — water won't drain from the tub.",
        "causes": [
            "Drain filter clogged (coins, lint, small items)",
            "Drain hose kinked or clogged",
            "Drain pump failure",
            "Drain hose too high",
        ],
        "action": "Clean the debris filter at the bottom front of the washer — this catches coins, buttons, and lint. Check the drain hose for kinks. If the filter is clean, listen for the drain pump — if it hums but doesn't pump, the impeller may be jammed or motor failed.",
    },
    "E2": {
        "meaning": "Drain error — same as 5E on older models.",
        "causes": [
            "Drain filter clogged",
            "Drain hose issue",
            "Pump failure",
        ],
        "action": "Same as 5E — clean the filter first.",
    },
    "5C": {
        "meaning": "Drain error — same as 5E on newer models.",
        "causes": [
            "Drain filter clogged",
            "Drain hose kinked",
            "Pump failure",
        ],
        "action": "Same as 5E — clean the debris filter, check drain hose, check pump.",
    },
    "4E": {
        "meaning": "Water supply error — washer not filling.",
        "causes": [
            "Water faucets turned off",
            "Inlet hose screens clogged with sediment",
            "Water inlet valve failure",
            "Low water pressure",
        ],
        "action": "Verify both hot and cold faucets are fully open. Clean the inlet screens — unscrew hoses at the washer and clean the mesh filters. If screens are clear and pressure is good, the inlet valve may be failed.",
    },
    "E1": {
        "meaning": "Water supply error — same as 4E on older models.",
        "causes": [
            "Water supply off",
            "Clogged inlet screens",
            "Inlet valve failure",
        ],
        "action": "Same as 4E.",
    },
    "4C": {
        "meaning": "Water supply error — same as 4E on newer models.",
        "causes": [
            "Water supply off",
            "Clogged inlet screens",
            "Inlet valve failure",
        ],
        "action": "Same as 4E.",
    },
    "DC": {
        "meaning": "Door open error — door not fully closed or locked.",
        "causes": [
            "Door not fully closed",
            "Clothes caught in the door seal",
            "Door lock mechanism failure",
            "Door latch worn or broken",
        ],
        "action": "Make sure the door is fully closed and nothing is caught in the seal. If the door closes but won't lock, the door lock assembly needs replacement. It's a common failure part on Samsung front-loaders.",
    },
    "UE": {
        "meaning": "Unbalanced load — drum can't balance for spin cycle.",
        "causes": [
            "Single bulky item",
            "Small load bunched together",
            "Washer not level",
            "Suspension components worn",
        ],
        "action": "Redistribute the load. Level the washer. If it happens regularly with normal loads, check the suspension rods and springs.",
    },
    "E4": {
        "meaning": "Unbalanced load — same as UE on older models.",
        "causes": [
            "Unbalanced items in drum",
            "Machine not level",
        ],
        "action": "Same as UE.",
    },
    "UB": {
        "meaning": "Unbalanced load — same as UE on some models.",
        "causes": [
            "Unbalanced items",
            "Machine not level",
        ],
        "action": "Same as UE.",
    },
    "LE": {
        "meaning": "Water leak detected — moisture where it shouldn't be.",
        "causes": [
            "Leak from door boot seal",
            "Leak from hose connections inside the machine",
            "Leak sensor false alarm from humidity",
            "Cracked tub",
        ],
        "action": "Check for visible leaks — inspect the door boot seal for tears. Check internal hose connections. If no leak is found, the leak sensor may be giving a false alarm from excess humidity or suds.",
    },
    "LE1": {
        "meaning": "Water leak — same as LE.",
        "causes": [
            "Door boot seal leak",
            "Internal hose leak",
            "Tub seal leak",
        ],
        "action": "Same as LE — check for visible leaks starting at the door boot seal.",
    },
    "LC": {
        "meaning": "Water leak — same as LE on newer models.",
        "causes": [
            "Door boot seal leak",
            "Internal hose leak",
        ],
        "action": "Same as LE.",
    },
    "LC1": {
        "meaning": "Water leak — same as LE on newer models.",
        "causes": [
            "Door boot seal leak",
            "Internal hose leak",
        ],
        "action": "Same as LE.",
    },
    "HE": {
        "meaning": "Heater error — water heater circuit fault.",
        "causes": [
            "Heater element burned out",
            "Thermistor (temp sensor) failure",
            "Wiring issue to heater",
        ],
        "action": "Check heater element for continuity. Check thermistor resistance. Inspect wiring. If the washer only uses cold water, this won't affect basic wash function.",
    },
    "HE1": {
        "meaning": "Heater error — overheating detected.",
        "causes": [
            "Thermistor failure reading incorrect temp",
            "Heater relay stuck on",
            "Water level too low in the tub",
        ],
        "action": "Check thermistor first. Verify water level is correct. If the heater is stuck on, the main board relay may be faulty.",
    },
    "HE2": {
        "meaning": "Heater error — dryer heater circuit fault (washer/dryer combos).",
        "causes": [
            "Dryer heater element failure",
            "Thermistor failure",
            "Wiring fault",
        ],
        "action": "Check the dryer heater circuit — element continuity and thermistor resistance.",
    },
    "3E": {
        "meaning": "Motor error — drive motor fault.",
        "causes": [
            "Motor hall sensor failure (position sensor)",
            "Motor winding failure",
            "Overloaded drum",
            "Control board motor driver issue",
        ],
        "action": "Reduce load size and retry. Check the motor hall sensor connector. Test motor windings for continuity between all three phases. If motor checks out, the main board motor driver circuit may be faulty.",
    },
    "3E1": {
        "meaning": "Motor error — overloaded.",
        "causes": [
            "Too many clothes in the drum",
            "Motor weakening",
        ],
        "action": "Reduce load size. If it happens with normal loads, check motor windings.",
    },
    "3E2": {
        "meaning": "Motor error — insufficient signal from motor.",
        "causes": [
            "Motor hall sensor failure",
            "Wiring issue between motor and board",
        ],
        "action": "Check the hall sensor connector on the motor. Check wiring between motor and main board.",
    },
    "8E": {
        "meaning": "Overcurrent error — electrical overload.",
        "causes": [
            "Motor drawing too much current",
            "Main board power circuit issue",
            "Voltage problem at the outlet",
        ],
        "action": "Check outlet voltage. Reduce load and retry. If persistent, check motor amp draw and main board.",
    },
}

APPLIANCE_WHIRLPOOL_WASHER_CODES = {
    "F0E2": {
        "meaning": "Load detected during clean cycle — items in drum during self-clean.",
        "causes": [
            "Clothes or items left in the drum during a clean washer cycle",
        ],
        "action": "Remove all items from the drum before running the clean washer cycle. This is a normal safety check, not a malfunction.",
    },
    "F1E1": {
        "meaning": "Control board error — main electronic control fault.",
        "causes": [
            "Control board failure from power surge",
            "Software glitch",
            "Component failure on the board",
        ],
        "action": "Unplug the washer for 5 minutes and plug back in. If code returns, the main control board likely needs replacement. Check for power surge damage.",
    },
    "F2E1": {
        "meaning": "Stuck key error — user interface button stuck.",
        "causes": [
            "Button physically stuck on the control panel",
            "Moisture behind the control panel",
            "User interface board failure",
        ],
        "action": "Check if any button on the panel is visibly stuck. If moisture got behind the panel, let it dry completely. If no button is stuck, the user interface board may need replacement.",
    },
    "F5E1": {
        "meaning": "Door lock error — door switch/lock malfunction.",
        "causes": [
            "Door lock mechanism failure (very common)",
            "Door latch broken or misaligned",
            "Wiring issue to door lock",
            "Main board door lock circuit failure",
        ],
        "action": "Try closing the door firmly. Check the latch for damage. The door lock assembly is a high-failure part on Whirlpool front-loaders — it's usually the lock mechanism itself. Replace the door lock assembly.",
    },
    "F5E2": {
        "meaning": "Door won't lock — unable to engage the lock.",
        "causes": [
            "Door lock actuator failure",
            "Something preventing door from fully closing",
            "Door strike misaligned",
        ],
        "action": "Check for obstructions in the door area. Verify the door strike aligns with the lock. Replace door lock assembly if mechanism is failed.",
    },
    "F7E1": {
        "meaning": "Motor drive error — motor not responding properly.",
        "causes": [
            "Motor rotor position sensor (hall sensor) failure",
            "Motor winding issue",
            "Main board motor driver circuit failure",
            "Wiring harness problem between motor and board",
        ],
        "action": "Check the motor position sensor (hall sensor) and its connector. Test motor windings. Check wiring harness between motor and control board. If motor checks out, the main board motor driver may be faulty.",
    },
    "F8E1": {
        "meaning": "Water supply error — washer not filling properly.",
        "causes": [
            "Water supply faucets turned off",
            "Inlet hose screens clogged",
            "Water inlet valve failure",
            "Low water pressure",
        ],
        "action": "Check that both hot and cold faucets are fully open. Clean inlet screens at the washer connection. If screens are clean and pressure is good, replace the water inlet valve.",
    },
    "F8E3": {
        "meaning": "Overflow / overfill — too much water in the tub.",
        "causes": [
            "Water inlet valve stuck open",
            "Pressure sensor/hose issue causing incorrect water level reading",
            "Siphoning from drain standpipe",
        ],
        "action": "Check if water keeps flowing when the washer is unplugged — if so, the inlet valve is stuck open and must be replaced. Check the pressure sensor hose. Verify the drain hose has an air gap at the standpipe to prevent siphoning.",
    },
    "F9E1": {
        "meaning": "Drain pump error — long drain time.",
        "causes": [
            "Drain pump filter clogged with debris",
            "Drain hose kinked or clogged",
            "Drain pump motor failure",
            "Drain hose too high",
        ],
        "action": "Clean the drain pump filter (access from the front lower panel). Check the drain hose for kinks. If filter is clean, check pump motor operation — it should spin freely. Replace pump if motor is failed.",
    },
    "F3E1": {
        "meaning": "Pressure switch error — water level sensor malfunction.",
        "causes": [
            "Pressure switch failure",
            "Pressure hose disconnected or clogged",
            "Air leak in the pressure system",
        ],
        "action": "Check the pressure hose from the tub to the pressure switch. Make sure it's connected and not clogged with soap residue. If hose is good, replace the pressure switch.",
    },
}

APPLIANCE_LG_DRYER_CODES = {
    "D80": {
        "meaning": "80% exhaust restriction — dryer vent partially blocked.",
        "causes": [
            "Lint buildup in the dryer vent duct",
            "Vent duct too long or too many bends",
            "Crushed or kinked vent duct",
            "Vent termination flap stuck closed",
        ],
        "action": "Clean the dryer vent duct from the dryer to the outside termination. Check the vent hood outside — make sure the flap opens freely. If the duct is flexible foil, replace it with rigid or semi-rigid metal duct. Keep runs under 25 feet equivalent (deduct 5 feet for each 90-degree bend).",
    },
    "D90": {
        "meaning": "90% exhaust restriction — dryer vent seriously blocked.",
        "causes": [
            "Severe lint buildup in vent duct",
            "Vent duct disconnected inside the wall",
            "Bird nest in the vent termination",
            "Vent duct crushed behind the dryer",
        ],
        "action": "This is a fire hazard level of restriction. Clean the entire vent run professionally. Check for disconnections inside the wall. Inspect the outside termination. Replace any flexible foil duct with rigid metal.",
    },
    "D95": {
        "meaning": "95%+ exhaust restriction — critical blockage.",
        "causes": [
            "Nearly complete vent blockage",
            "Vent completely disconnected from dryer",
            "Vent crushed or collapsed",
        ],
        "action": "FIRE HAZARD — do not continue using the dryer until this is resolved. Completely clean or replace the vent duct from dryer to outside. This level of restriction causes overheating and is a leading cause of house fires.",
    },
    "TE1": {
        "meaning": "Thermistor error — primary temperature sensor fault.",
        "causes": [
            "Failed thermistor",
            "Loose connector at thermistor or PCB",
            "Wiring damage",
        ],
        "action": "Check thermistor resistance — compare to spec chart. Inspect connector. Replace if out of spec.",
    },
    "TE2": {
        "meaning": "Thermistor error — secondary temperature sensor fault.",
        "causes": [
            "Failed secondary thermistor",
            "Connector issue",
        ],
        "action": "Same as tE1 — check resistance and replace if faulty.",
    },
    "TE3": {
        "meaning": "Thermistor error — exhaust temperature sensor fault.",
        "causes": [
            "Failed exhaust thermistor",
            "Sensor displaced from its mounting",
        ],
        "action": "Check exhaust temp sensor resistance. Verify it's properly mounted. Replace if faulty.",
    },
    "NP": {
        "meaning": "No power or voltage error — electrical supply issue.",
        "causes": [
            "Only getting 120V instead of 240V (half voltage)",
            "One leg of the 240V circuit tripped at the breaker",
            "Loose connection at the outlet, cord, or terminal block",
        ],
        "action": "Check the breaker — on a 2-pole breaker, one side can trip without the other visually appearing tripped. Reset both sides. Check voltage at the outlet — should be 240V between the two hots. If only 120V, one leg is dead.",
    },
    "PS": {
        "meaning": "Power supply error — similar to nP.",
        "causes": [
            "Incorrect voltage supply",
            "Power cord issue",
            "Terminal block loose or corroded",
        ],
        "action": "Check voltage at the outlet. Inspect the power cord for damage. Check terminal block connections inside the dryer access panel.",
    },
    "CL": {
        "meaning": "Child lock active — not an error.",
        "causes": [
            "Child lock feature activated",
        ],
        "action": "Press and hold the Child Lock button for 3-5 seconds to deactivate.",
    },
    "PF": {
        "meaning": "Power failure — dryer lost power during a cycle.",
        "causes": [
            "Power outage",
            "Loose plug",
        ],
        "action": "Press start to resume. If frequent, check the power cord and outlet connection.",
    },
    "HS": {
        "meaning": "Humidity sensor error — moisture detection fault.",
        "causes": [
            "Humidity sensor bars dirty (fabric softener buildup)",
            "Humidity sensor failure",
            "Wiring issue to sensor",
        ],
        "action": "Clean the humidity sensor bars inside the drum (metal bars near the lint filter) with rubbing alcohol and a soft cloth. Fabric softener residue coats these bars and causes false readings. If cleaning doesn't help, replace the sensor.",
    },
    "F1": {
        "meaning": "Control board error — main PCB fault.",
        "causes": [
            "Control board failure",
            "Power surge damage",
        ],
        "action": "Unplug for 5 minutes and try again. If code returns, the main control board needs replacement.",
    },
}

APPLIANCE_SAMSUNG_DRYER_CODES = {
    "HE": {
        "meaning": "Heater circuit error — heating element or circuit fault.",
        "causes": [
            "Heater element burned out (open circuit)",
            "Thermal fuse blown (most common with clogged vents)",
            "Heater relay on main board stuck",
            "Wiring issue in the heater circuit",
        ],
        "action": "Check the thermal fuse first — it's on the blower housing and blows when the vent is clogged. Test heater element for continuity. Check the high-limit thermostat. If the thermal fuse blew, also clean the vent — it blew for a reason.",
    },
    "TE": {
        "meaning": "Temperature sensor error — thermistor fault.",
        "causes": [
            "Failed thermistor (temperature sensor)",
            "Loose connector",
            "Wiring damage",
        ],
        "action": "Check thermistor resistance against the spec chart. Inspect connector and wiring. Replace if out of range.",
    },
    "TS": {
        "meaning": "Temperature sensor error — same as tE on some models.",
        "causes": [
            "Failed thermistor",
            "Connector issue",
        ],
        "action": "Same as tE — check thermistor resistance and connector.",
    },
    "DC": {
        "meaning": "Door switch error — door not detected as closed.",
        "causes": [
            "Door not fully closed",
            "Door switch failure",
            "Door latch worn or broken",
            "Wiring issue to door switch",
        ],
        "action": "Close the door firmly. Check the door switch with a multimeter — it should show continuity when pressed. Replace the door switch if faulty. Check the latch for wear.",
    },
    "DF": {
        "meaning": "Door switch error — same as dC on some models.",
        "causes": [
            "Door switch failure",
            "Door not closing fully",
        ],
        "action": "Same as dC.",
    },
    "BE": {
        "meaning": "Button/control panel error — stuck button.",
        "causes": [
            "Button stuck on the control panel",
            "Moisture behind the panel",
            "Control panel overlay delaminating",
        ],
        "action": "Check for stuck buttons. If moisture got behind the panel, let it dry. If the overlay is peeling, it can cause false button presses — replace the control panel overlay.",
    },
    "FE": {
        "meaning": "Power frequency error — AC frequency out of range.",
        "causes": [
            "Generator power (non-standard frequency)",
            "Power quality issue from utility",
            "Main board power sensing circuit fault",
        ],
        "action": "If running on a generator, the frequency may not be stable enough. On utility power, this is rare — check incoming power. May indicate a main board issue.",
    },
    "9E1": {
        "meaning": "Voltage error — supply voltage out of range.",
        "causes": [
            "Low or high voltage at the outlet",
            "One leg of 240V circuit lost",
            "Breaker issue",
        ],
        "action": "Check voltage at the outlet — should be 240V. Check both breakers. If voltage is correct, the main board power sensing circuit may be faulty.",
    },
    "9C1": {
        "meaning": "Low voltage to unit — underpowered.",
        "causes": [
            "Low utility voltage",
            "Undersized wire run to the dryer",
            "Loose connection at breaker, outlet, or terminal block",
        ],
        "action": "Check voltage at the outlet and at the breaker. If voltage drops significantly from breaker to outlet, the wire gauge may be undersized for the run length. Check all connections for tightness.",
    },
    "ET": {
        "meaning": "Communication error — board-to-board communication fault.",
        "causes": [
            "Ribbon cable or connector loose between control boards",
            "Control board failure",
        ],
        "action": "Check ribbon cable connections between the main board and display board. Reseat connectors. If code persists, one of the boards needs replacement.",
    },
    "AE": {
        "meaning": "Signal error — communication fault between boards.",
        "causes": [
            "Communication cable issue",
            "Board failure",
        ],
        "action": "Check all cable connections between boards. Power cycle the unit. If persistent, replace the faulty board.",
    },
    "AE3": {
        "meaning": "Signal error — variant of AE.",
        "causes": [
            "Sub-board communication failure",
        ],
        "action": "Same as AE — check connections and boards.",
    },
    "AE4": {
        "meaning": "Signal error — variant of AE.",
        "causes": [
            "Sub-board communication failure",
        ],
        "action": "Same as AE — check connections and boards.",
    },
    "AE5": {
        "meaning": "Signal error — variant of AE.",
        "causes": [
            "Sub-board communication failure",
        ],
        "action": "Same as AE — check connections and boards.",
    },
    "EE": {
        "meaning": "EEPROM error — memory chip fault.",
        "causes": [
            "EEPROM corruption from power surge",
            "Main board failure",
        ],
        "action": "Power cycle the dryer. If code persists, the main control board needs replacement.",
    },
}

APPLIANCE_SAMSUNG_REFRIGERATOR_CODES = {
    "1E": {
        "meaning": "Freezer sensor error — freezer temperature sensor fault.",
        "causes": [
            "Failed freezer thermistor",
            "Connector corroded or loose",
            "Wiring damage",
        ],
        "action": "Check freezer temp sensor resistance against the spec chart. Inspect connector. Replace sensor if out of range.",
    },
    "2E": {
        "meaning": "Fridge sensor error — refrigerator compartment sensor fault.",
        "causes": [
            "Failed fridge thermistor",
            "Connector issue",
        ],
        "action": "Check fridge temp sensor resistance. Replace if out of spec.",
    },
    "5E": {
        "meaning": "Defrost sensor error — defrost thermistor fault.",
        "causes": [
            "Failed defrost sensor/thermistor",
            "Sensor displaced from evaporator",
            "Ice buildup around sensor",
        ],
        "action": "Check defrost sensor resistance. Make sure it's clipped to the evaporator properly. If there's heavy ice buildup around it, the defrost system may have other issues (heater, timer, or board).",
    },
    "6E": {
        "meaning": "Ambient temperature sensor error.",
        "causes": [
            "Failed ambient temp sensor",
            "Wiring damage",
        ],
        "action": "Check ambient temp sensor resistance. Replace if out of spec.",
    },
    "8E": {
        "meaning": "Ice maker sensor error.",
        "causes": [
            "Ice maker temperature sensor failure",
            "Connector issue in the ice maker assembly",
        ],
        "action": "Check ice maker sensor. May require ice maker assembly replacement if the sensor is not separately replaceable.",
    },
    "13E": {
        "meaning": "Ice dispenser sensor error.",
        "causes": [
            "Failed ice dispenser sensor",
            "Connector issue",
        ],
        "action": "Check sensor and connector. Replace if faulty.",
    },
    "14E": {
        "meaning": "Ice maker sensor error — secondary ice sensor fault.",
        "causes": [
            "Ice maker sensor failure",
            "Wiring issue within the ice maker",
        ],
        "action": "Check ice maker sensor and wiring. Replace ice maker assembly if needed.",
    },
    "21E": {
        "meaning": "Freezer fan motor error — evaporator fan not running.",
        "causes": [
            "Fan motor failure",
            "Fan blade blocked by ice buildup (most common)",
            "Wiring issue to fan motor",
        ],
        "action": "Check for ice buildup around the evaporator fan — this is very common on Samsung fridges. Defrost the freezer manually (hair dryer or leave doors open). If no ice, check the fan motor for continuity and replace if failed.",
    },
    "22E": {
        "meaning": "Fridge fan motor error — fresh food compartment fan fault.",
        "causes": [
            "Fridge fan motor failure",
            "Fan blocked",
            "Wiring issue",
        ],
        "action": "Check fridge compartment fan for blockage. Test motor for continuity. Replace if failed.",
    },
    "25E": {
        "meaning": "Defrost circuit error — defrost heater or circuit fault.",
        "causes": [
            "Defrost heater burned out (check continuity)",
            "Defrost thermostat (bi-metal) failed",
            "Main board defrost relay failure",
        ],
        "action": "Check defrost heater for continuity. Test the bi-metal thermostat. If both are good, the main board defrost relay circuit is likely faulty. Samsung fridges are notorious for defrost issues — the main board is often the culprit.",
    },
    "26E": {
        "meaning": "Ice maker water valve error.",
        "causes": [
            "Water inlet valve failure",
            "Low water pressure to the fridge",
            "Frozen water line inside the fridge door",
        ],
        "action": "Check water pressure at the fridge supply line. Inspect the water inlet valve. On Samsung French door models, the water line in the door can freeze — this is a known issue. Thaw the line carefully.",
    },
    "33E": {
        "meaning": "Ice pipe heater error — anti-frost heater fault.",
        "causes": [
            "Ice pipe heater failed",
            "Wiring issue",
        ],
        "action": "Check ice pipe heater for continuity. Replace if open circuit.",
    },
    "39E": {
        "meaning": "Ice maker function error.",
        "causes": [
            "Ice maker motor failure",
            "Ice maker module malfunction",
            "Ice bucket not seated properly",
        ],
        "action": "Make sure the ice bucket is seated correctly. Check ice maker motor operation. May need ice maker assembly replacement.",
    },
    "39C": {
        "meaning": "Ice maker function error — same as 39E on newer models.",
        "causes": [
            "Ice maker malfunction",
        ],
        "action": "Same as 39E.",
    },
    "40E": {
        "meaning": "Ice room fan error — ice compartment fan fault.",
        "causes": [
            "Ice room fan motor failure",
            "Fan blocked by ice",
        ],
        "action": "Check for ice blocking the fan. Test motor. Replace if failed.",
    },
    "40C": {
        "meaning": "Ice room fan error — same as 40E.",
        "causes": [
            "Fan motor failure or ice blockage",
        ],
        "action": "Same as 40E.",
    },
    "41C": {
        "meaning": "Ice maker fan error.",
        "causes": [
            "Ice maker fan motor failure",
            "Ice obstruction",
        ],
        "action": "Check for ice obstruction. Replace fan motor if failed.",
    },
    "84C": {
        "meaning": "Compressor lock error — compressor not starting.",
        "causes": [
            "Compressor mechanically locked (seized bearing or piston)",
            "Compressor start relay or overload failure",
            "Inverter board failure (on inverter models)",
            "Low voltage",
        ],
        "action": "Try a hard reset — unplug for 10 minutes. Check voltage. On non-inverter models, check the start relay and overload. On inverter models, check the inverter board. If the compressor is mechanically seized, it needs replacement.",
    },
    "85C": {
        "meaning": "Compressor communication error — inverter board communication fault.",
        "causes": [
            "Inverter board failure",
            "Communication cable between main board and inverter loose",
            "Main board failure",
        ],
        "action": "Check the cable between the main board and the inverter/compressor board. Reseat connectors. If code persists, try the inverter board first — it's the more common failure point.",
    },
}

APPLIANCE_LG_REFRIGERATOR_CODES = {
    "ERIF": {
        "meaning": "Ice maker fan motor error.",
        "causes": [
            "Ice fan motor failure",
            "Fan blade blocked by ice",
            "Wiring issue to fan motor",
        ],
        "action": "Check for ice blocking the fan blade. Test motor for continuity. Replace if failed.",
    },
    "ERFF": {
        "meaning": "Freezer fan motor error — evaporator fan not running.",
        "causes": [
            "Fan motor failure",
            "Ice buildup around evaporator fan (common)",
            "Wiring issue",
        ],
        "action": "Check for ice around the fan — defrost manually if needed. Test fan motor. Replace if motor is bad.",
    },
    "ERCF": {
        "meaning": "Condenser fan motor error — not circulating air over the compressor.",
        "causes": [
            "Condenser fan motor failure",
            "Fan blade blocked by debris",
            "Connector loose at motor",
        ],
        "action": "Check condenser fan at the bottom rear of the fridge. Make sure the blade spins freely. Clean any dust or debris. Test motor and replace if failed.",
    },
    "ERCO": {
        "meaning": "Communication error — board-to-board communication fault.",
        "causes": [
            "Ribbon cable or connector loose between boards",
            "Main board or display board failure",
            "Power surge damage",
        ],
        "action": "Check all ribbon cables and connectors between the main board and display board. Power cycle the fridge for 10 minutes. If code persists, suspect a board failure.",
    },
    "ERDH": {
        "meaning": "Defrost heater error — defrost circuit fault.",
        "causes": [
            "Defrost heater burned out",
            "Defrost thermostat (bi-metal) open",
            "Main board defrost circuit failure",
        ],
        "action": "Check defrost heater for continuity. Test bi-metal thermostat. If both are good, the main board defrost relay is likely faulty.",
    },
    "ERDS": {
        "meaning": "Defrost sensor error — defrost thermistor fault.",
        "causes": [
            "Failed defrost thermistor",
            "Sensor displaced from evaporator",
            "Connector corroded",
        ],
        "action": "Check defrost sensor resistance. Ensure it's clipped to the evaporator properly. Replace if out of spec.",
    },
    "ERFS": {
        "meaning": "Freezer sensor error — freezer temperature sensor fault.",
        "causes": [
            "Failed freezer thermistor",
            "Connector issue",
        ],
        "action": "Check freezer temp sensor resistance. Replace if out of range.",
    },
    "ERRS": {
        "meaning": "Fridge sensor error — refrigerator compartment sensor fault.",
        "causes": [
            "Failed fridge thermistor",
            "Wiring issue",
        ],
        "action": "Check fridge temp sensor resistance. Replace if out of spec.",
    },
    "ERIS": {
        "meaning": "Ice maker sensor error.",
        "causes": [
            "Failed ice maker sensor",
            "Connector issue in ice maker assembly",
        ],
        "action": "Check ice maker sensor. May need ice maker assembly replacement.",
    },
    "ERHS": {
        "meaning": "Humidity sensor error.",
        "causes": [
            "Failed humidity sensor",
            "Connector corrosion",
        ],
        "action": "Check humidity sensor and replace if faulty.",
    },
    "ERGF": {
        "meaning": "Flow sensor error — water flow sensor fault.",
        "causes": [
            "Failed water flow sensor",
            "Low water pressure",
            "Kinked water supply line",
        ],
        "action": "Check water pressure at the supply line. Inspect for kinks. Test the flow sensor. Replace if faulty.",
    },
    "ERSS": {
        "meaning": "Pantry sensor error — pantry/deli drawer sensor fault.",
        "causes": [
            "Failed pantry thermistor",
            "Connector issue",
        ],
        "action": "Check pantry temp sensor resistance. Replace if out of spec.",
    },
}

APPLIANCE_BOSCH_DISHWASHER_CODES = {
    "E01": {
        "meaning": "Heating fault — water not reaching target temperature.",
        "causes": [
            "Heating element burned out",
            "NTC temperature sensor fault causing incorrect reading",
            "Control module relay failure",
        ],
        "action": "Test heating element for continuity. Check the NTC sensor resistance against the spec. If both are good, the control module is likely at fault.",
    },
    "E02": {
        "meaning": "NTC temperature sensor fault.",
        "causes": [
            "Failed NTC thermistor (open or shorted)",
            "Connector corroded from moisture",
            "Wiring issue",
        ],
        "action": "Check NTC sensor resistance — at room temperature it should be around 50k ohms (varies by model). Replace if out of range.",
    },
    "E09": {
        "meaning": "Heating element fault — specific to the heater.",
        "causes": [
            "Heating element open circuit",
            "Heater relay failure on control board",
            "Wiring damage to heater",
        ],
        "action": "Test the heating element for continuity. If open, replace it. Also check for ground fault (heater to chassis). If element is good, the control board heater relay is suspect.",
    },
    "E14": {
        "meaning": "Flow meter error — no water detected entering the dishwasher.",
        "causes": [
            "Water supply turned off",
            "Inlet hose kinked",
            "Water inlet valve failure",
            "Flow meter (impeller sensor) failure",
        ],
        "action": "Check water supply — is the valve under the sink turned on? Check inlet hose for kinks. If water is available, the inlet valve or flow meter may be failed.",
    },
    "E15": {
        "meaning": "Leak protection activated — Aquastop system triggered.",
        "causes": [
            "Water in the base pan (actual leak)",
            "Leak sensor triggered by moisture or condensation",
            "Hose connection leaking inside the machine",
            "Aquastop valve failure",
        ],
        "action": "Tilt the dishwasher back slightly (carefully) to drain water from the base pan. Look inside the base for the source of the leak — check the main wash pump seal, hose connections, and door seal. The float switch in the base triggers this code. Clean and dry the base pan. If no actual leak, the float switch may be stuck.",
    },
    "E16": {
        "meaning": "Uncontrolled water inlet — water filling when it shouldn't be.",
        "causes": [
            "Water inlet valve stuck open",
            "Inlet valve leaking through when closed",
        ],
        "action": "Turn off water supply immediately. The inlet valve is stuck open or leaking — replace it. Check the valve even when the machine is off — if water seeps in with power off, the valve is definitely leaking through.",
    },
    "E17": {
        "meaning": "Overfill error — too much water in the tub.",
        "causes": [
            "Water inlet valve not closing properly",
            "Drainage siphon effect pulling water back in",
            "Pressure sensor issue giving wrong water level",
        ],
        "action": "Check inlet valve for proper shutoff. Verify drain hose has a high loop or air gap to prevent siphoning. Check water level pressure switch.",
    },
    "E22": {
        "meaning": "Filter blocked — restricted water flow through the filter system.",
        "causes": [
            "Dirty filter screens (food debris buildup)",
            "Filter not properly seated after cleaning",
        ],
        "action": "Remove and clean all filter components — the cylindrical micro-filter and the flat mesh filter. Rinse under running water. Make sure they're properly reassembled and seated. Clean filters monthly to prevent this.",
    },
    "E24": {
        "meaning": "Drain hose kinked or clogged — water not draining.",
        "causes": [
            "Drain hose kinked behind the dishwasher",
            "Drain hose clogged with food debris",
            "Connection to garbage disposal or drain blocked",
            "Knockout plug not removed from garbage disposal",
        ],
        "action": "Pull the dishwasher out and check the drain hose for kinks. If connected to a garbage disposal, make sure the knockout plug was removed when the disposal was installed. Check for food debris in the hose. Run the garbage disposal to clear the drain path.",
    },
    "E25": {
        "meaning": "Drain pump blocked — pump can't drain water.",
        "causes": [
            "Drain pump impeller jammed with glass, bones, or debris",
            "Drain pump motor failure",
            "Drain pump cover not properly seated",
        ],
        "action": "Remove the drain pump cover inside the dishwasher (at the bottom of the tub) and check for debris jamming the impeller. You'll often find broken glass, fruit pits, or toothpicks. Clear the impeller and test. If it spins freely and still won't pump, the motor is failed.",
    },
}

APPLIANCE_GE_DISHWASHER_CODES = {
    "H2O": {
        "meaning": "Water supply issue — dishwasher not getting water.",
        "causes": [
            "Water supply valve under sink turned off",
            "Inlet hose kinked",
            "Water inlet valve failure",
            "Low water pressure",
        ],
        "action": "Check that the water supply valve under the sink is fully open. Inspect the inlet hose for kinks. If water supply is good, the inlet valve may need replacement.",
    },
    "PRS": {
        "meaning": "Pressure sensor error — water level sensor fault.",
        "causes": [
            "Failed pressure sensor",
            "Clogged or disconnected sensor tube",
            "Main board issue",
        ],
        "action": "Check the pressure sensor tube for clogs or disconnection. Replace the pressure sensor if faulty.",
    },
    "LE": {
        "meaning": "Leak detected — water in the base pan.",
        "causes": [
            "Actual water leak inside the dishwasher",
            "Door gasket leaking",
            "Pump seal leaking",
            "Leak sensor false alarm from condensation",
        ],
        "action": "Check the base pan for water. Inspect door gasket, pump seals, and hose connections for leaks. Clean and dry the base pan. If no actual leak, the leak sensor may need replacement.",
    },
}

APPLIANCE_LG_DISHWASHER_CODES = {
    "OE": {
        "meaning": "Drain error — water not draining.",
        "causes": [
            "Drain hose kinked or clogged",
            "Drain pump jammed or failed",
            "Garbage disposal knockout plug not removed",
            "Filter system clogged",
        ],
        "action": "Check drain hose for kinks. Clean the filter system. If connected to a disposal, verify knockout was removed. Check drain pump for debris.",
    },
    "IE": {
        "meaning": "Water inlet error — not filling with water.",
        "causes": [
            "Water supply off",
            "Inlet valve failure",
            "Low water pressure",
        ],
        "action": "Check water supply valve. Test inlet valve. Check water pressure.",
    },
    "FE": {
        "meaning": "Overfill error — too much water.",
        "causes": [
            "Inlet valve stuck open",
            "Float switch stuck or failed",
        ],
        "action": "Turn off water supply. Replace inlet valve if stuck open. Check float switch.",
    },
    "HE": {
        "meaning": "Heater circuit error — water not heating.",
        "causes": [
            "Heating element burned out",
            "NTC sensor failure",
            "Control board relay issue",
        ],
        "action": "Test heating element for continuity. Check NTC sensor resistance. If both good, suspect control board.",
    },
    "TE": {
        "meaning": "Thermistor error — temperature sensor fault.",
        "causes": [
            "Failed thermistor",
            "Connector issue",
        ],
        "action": "Check thermistor resistance and replace if out of spec.",
    },
    "LE": {
        "meaning": "Motor error — wash motor fault.",
        "causes": [
            "Wash motor failure",
            "Motor winding issue",
            "Main board motor circuit failure",
        ],
        "action": "Check wash motor for continuity. Listen for motor during cycle. Replace motor if failed.",
    },
    "CE": {
        "meaning": "Overcurrent error — motor drawing too much current.",
        "causes": [
            "Motor or pump jammed",
            "Main board issue",
            "Wiring short",
        ],
        "action": "Check for debris jamming the wash motor or drain pump. Inspect wiring for damage. If pumps are clear, suspect main board.",
    },
    "PF": {
        "meaning": "Power failure — lost power during cycle.",
        "causes": [
            "Power outage",
            "Loose connection",
        ],
        "action": "Press start to resume. Check power connections if frequent.",
    },
    "CL": {
        "meaning": "Child lock active — not an error.",
        "causes": [
            "Child lock activated",
        ],
        "action": "Press and hold Child Lock button for 3 seconds to deactivate.",
    },
}

APPLIANCE_GE_OVEN_CODES = {
    "F0": {
        "meaning": "Control board stuck key — a key input is held.",
        "causes": [
            "Button stuck on the control panel",
            "Control board touch key circuit failure",
            "Moisture behind the panel",
        ],
        "action": "Check for a physically stuck button. Power off and clean the panel with a damp cloth (not dripping). If no button is stuck, the control board or keypad membrane may need replacement.",
    },
    "F1": {
        "meaning": "Control board fault — ERC (Electronic Range Control) failure.",
        "causes": [
            "Control board component failure",
            "Power surge damage",
            "Relay stuck on the board",
        ],
        "action": "Power cycle the oven (breaker off for 2 minutes). If code returns, the control board needs replacement. This is the most common GE oven repair.",
    },
    "F2": {
        "meaning": "Oven too hot — temperature exceeded safe limit.",
        "causes": [
            "Temperature sensor (RTD probe) failure reading low (oven overshoots)",
            "Control board relay stuck closed (keeps heating)",
            "Vent blocked causing heat buildup",
        ],
        "action": "TURN OFF BREAKER immediately if oven is excessively hot. Check the oven temp sensor — measure resistance at room temp (should be about 1080 ohms at 70F for most GE ovens). If the relay is stuck, the control board must be replaced.",
    },
    "F3": {
        "meaning": "Open oven temperature sensor — sensor circuit open.",
        "causes": [
            "Oven temp sensor (RTD probe) failed open",
            "Sensor wire disconnected or broken",
            "Loose connector at sensor or control board",
        ],
        "action": "Check oven temp sensor resistance — should read about 1080 ohms at 70F. If it reads infinite (OL), the sensor is open — replace it. If the sensor is good, check the wiring and connector to the control board.",
    },
    "F4": {
        "meaning": "Shorted oven temperature sensor — sensor reading too low.",
        "causes": [
            "Oven temp sensor shorted (reading near 0 ohms)",
            "Sensor wires touching each other",
            "Sensor harness pinched against oven cavity",
        ],
        "action": "Check oven temp sensor resistance. If it reads near 0 ohms, the sensor is shorted — replace it. Also inspect the sensor wire harness for pinch points or melted insulation where wires may be touching.",
    },
    "F5": {
        "meaning": "Control board relay failure — board not switching properly.",
        "causes": [
            "Control board relay welded closed (stuck on)",
            "Relay driver circuit failure on the board",
        ],
        "action": "This is a control board failure. The relay that controls the heating elements may be stuck. Replace the control board. If the oven was running very hot before this code, the relay was probably stuck closed.",
    },
    "F7": {
        "meaning": "Stuck function key — a button on the control panel is stuck.",
        "causes": [
            "Physical button stuck",
            "Keypad membrane deteriorated",
            "Moisture behind the control panel",
        ],
        "action": "Check for a stuck button. The keypad membrane (flexible layer over the buttons) may be deteriorated — especially on older models. Replace the keypad/membrane panel. On some GE models the keypad is separate from the control board.",
    },
    "F8": {
        "meaning": "Control board configuration error — EEPROM fault.",
        "causes": [
            "Control board EEPROM corrupted",
            "Wrong replacement control board installed",
            "Power surge damage to EEPROM",
        ],
        "action": "Power cycle the oven. If code persists, the control board EEPROM is corrupted and the board needs replacement. If this appeared after a board replacement, verify the correct part number was installed.",
    },
    "F9": {
        "meaning": "Door lock fault — door lock mechanism not working.",
        "causes": [
            "Door lock motor/latch assembly failure",
            "Door lock switch failure",
            "Wiring issue to door lock",
        ],
        "action": "Check the door lock mechanism. If the oven was in self-clean mode, let it cool completely before troubleshooting. Check the lock motor and switches for continuity. Replace the lock assembly if faulty.",
    },
    "FF": {
        "meaning": "Safety lockout — oven locked out for safety.",
        "causes": [
            "Multiple failed attempts or persistent fault",
            "Control board safety circuit activated",
        ],
        "action": "Power off the oven at the breaker for 5 minutes. This is a safety lockout that requires a full power reset. If it keeps locking out, address the underlying fault code that caused it.",
    },
}

APPLIANCE_WHIRLPOOL_OVEN_CODES = {
    "F1E0": {
        "meaning": "Control board EEPROM error — memory fault.",
        "causes": [
            "EEPROM corrupted from power surge",
            "Control board failure",
        ],
        "action": "Power cycle the oven (breaker off for 2 minutes). If code persists, the control board needs replacement.",
    },
    "F2E0": {
        "meaning": "Shorted keypad — input stuck.",
        "causes": [
            "Keypad membrane deteriorated or damaged",
            "Moisture behind the control panel",
            "Keypad connector issue",
        ],
        "action": "Disconnect the keypad ribbon cable from the control board. If the code clears, the keypad needs replacement. If the code stays, the control board is faulty.",
    },
    "F2E1": {
        "meaning": "Stuck touch key — a key input is continuously triggered.",
        "causes": [
            "Button stuck physically",
            "Keypad membrane wear",
            "Moisture intrusion",
        ],
        "action": "Same as F2E0 — disconnect keypad to isolate the problem. Replace keypad if it's the cause.",
    },
    "F3E0": {
        "meaning": "Open oven sensor — temperature sensor circuit open.",
        "causes": [
            "Oven temp sensor (RTD) failed open",
            "Sensor wire disconnected",
            "Connector loose at sensor or board",
        ],
        "action": "Check oven sensor resistance — should be about 1080 ohms at room temperature. If infinite (OL), sensor is open. Replace sensor. Check wiring and connector if sensor is good.",
    },
    "F3E1": {
        "meaning": "Shorted oven sensor — sensor reading near zero.",
        "causes": [
            "Oven temp sensor shorted internally",
            "Sensor wires touching or pinched",
        ],
        "action": "Check sensor resistance — if near 0 ohms, replace the sensor. Inspect wire harness for pinch points.",
    },
    "F3E2": {
        "meaning": "Open meat probe — meat probe circuit open.",
        "causes": [
            "Meat probe not plugged in (code appears if oven expects it)",
            "Meat probe failed",
            "Jack (outlet) in oven cavity corroded or damaged",
        ],
        "action": "If meat probe is plugged in, try a different probe. Check the jack inside the oven for corrosion. If no probe is being used, unplug any probe from the jack.",
    },
    "F3E3": {
        "meaning": "Shorted meat probe — meat probe reading near zero.",
        "causes": [
            "Meat probe failed internally (shorted)",
            "Probe cord damaged",
            "Jack corroded causing a short",
        ],
        "action": "Unplug the meat probe. If code clears, the probe is shorted — replace it. If code persists, check the jack and wiring.",
    },
    "F5E1": {
        "meaning": "Door latch not working — lock mechanism fault.",
        "causes": [
            "Door lock motor/latch failure",
            "Lock switch failed",
            "Wiring issue",
        ],
        "action": "Check the door lock mechanism. If stuck mid-cycle during self-clean, let it cool completely. Test lock motor and switches. Replace lock assembly if needed.",
    },
    "F9E0": {
        "meaning": "Door latch not reset — door latch stuck in locked position.",
        "causes": [
            "Door latch stuck from self-clean cycle",
            "Latch motor failure",
            "Latch switch out of position",
        ],
        "action": "Try running a self-clean cycle briefly then canceling — sometimes this resets the latch. If that doesn't work, power off and manually check the latch mechanism for binding.",
    },
    "F1E1": {
        "meaning": "Control board fault — main board failure.",
        "causes": [
            "Control board component failure",
            "Power surge damage",
        ],
        "action": "Power cycle the oven. If code returns, replace the control board.",
    },
}

APPLIANCE_SAMSUNG_OVEN_CODES = {
    "SE": {
        "meaning": "Key short error — button stuck on the panel.",
        "causes": [
            "Button physically stuck",
            "Membrane keypad deteriorated",
            "Moisture behind panel",
        ],
        "action": "Check for stuck buttons. Clean and dry the control panel. If persistent, replace the membrane keypad or control panel assembly.",
    },
    "E08": {
        "meaning": "Oven temperature sensor error.",
        "causes": [
            "Oven temp sensor (RTD) failure",
            "Connector loose or corroded",
            "Wiring damage",
        ],
        "action": "Check oven temp sensor resistance. Replace if out of spec. Check connectors and wiring.",
    },
    "E0A": {
        "meaning": "Gas igniter fault — igniter not reaching temperature.",
        "causes": [
            "Weak or failed igniter (most common)",
            "Gas valve safety solenoid failure",
            "Wiring issue to igniter",
        ],
        "action": "Check the igniter — it should glow bright orange/white in about 30-60 seconds. If it glows but the gas doesn't flow, it may be too weak to pull in the gas valve safety. Check igniter amp draw — most need 3.2-3.6 amps to open the valve. Replace igniter if weak.",
    },
    "E27": {
        "meaning": "Oven temperature sensor range — reading out of expected range.",
        "causes": [
            "Oven sensor degraded (reading drifting over time)",
            "Sensor exposed to excessive heat from self-clean cycle",
            "Wiring issue",
        ],
        "action": "Check sensor resistance at room temp. If slightly off spec, the sensor is degrading — replace it. Sensors can drift after many self-clean cycles due to the extreme heat.",
    },
    "C10": {
        "meaning": "Communication error — board-to-board communication fault.",
        "causes": [
            "Ribbon cable or connector loose between boards",
            "Control board failure",
            "Display board failure",
        ],
        "action": "Check cable connections between the main board and display board. Reseat all connectors. Power cycle the oven. If persistent, one of the boards needs replacement.",
    },
    "CF0": {
        "meaning": "Door lock error — lock mechanism fault.",
        "causes": [
            "Door lock mechanism failure",
            "Lock switch issue",
            "Wiring problem",
        ],
        "action": "Check door lock mechanism. If stuck from self-clean, let it cool completely. Test lock motor and switches. Replace if faulty.",
    },
}

APPLIANCE_WHIRLPOOL_DRYER_CODES = {
    "F1E1": {
        "meaning": "Control board fault — main electronic control error.",
        "causes": [
            "Control board failure",
            "Power surge damage",
        ],
        "action": "Unplug for 5 minutes. If code returns, replace the main control board.",
    },
    "F2E1": {
        "meaning": "Stuck key error — button stuck on control panel.",
        "causes": [
            "Button physically stuck",
            "Moisture behind panel",
            "User interface board failure",
        ],
        "action": "Check for stuck buttons. Let panel dry if moisture is suspected. Replace UI board if needed.",
    },
    "F3E1": {
        "meaning": "Exhaust thermistor open — exhaust temp sensor fault.",
        "causes": [
            "Exhaust thermistor failed open",
            "Connector loose or corroded",
            "Wiring break",
        ],
        "action": "Check exhaust thermistor resistance. Replace if open circuit. Check connector and wiring.",
    },
    "F3E2": {
        "meaning": "Exhaust thermistor shorted.",
        "causes": [
            "Exhaust thermistor failed short",
            "Wiring pinched",
        ],
        "action": "Check exhaust thermistor resistance. Replace if reading near 0 ohms.",
    },
    "F5E1": {
        "meaning": "Door switch error — door not detected as closed.",
        "causes": [
            "Door switch failure",
            "Door latch worn",
            "Wiring to door switch",
        ],
        "action": "Test door switch with a multimeter. Replace if no continuity when pressed. Check wiring.",
    },
    "F6E2": {
        "meaning": "Communication error between boards.",
        "causes": [
            "Ribbon cable loose",
            "Board failure",
        ],
        "action": "Check cable connections between control boards. Reseat connectors. Replace board if needed.",
    },
}

APPLIANCE_GE_REFRIGERATOR_CODES = {
    "FF": {
        "meaning": "Freezer fan circuit fault — evaporator fan issue.",
        "causes": [
            "Freezer evaporator fan motor failure",
            "Fan blocked by ice buildup",
            "Wiring issue",
        ],
        "action": "Check for ice around the evaporator fan. Test fan motor. Replace if failed.",
    },
    "CC": {
        "meaning": "Condenser fan circuit fault.",
        "causes": [
            "Condenser fan motor failure",
            "Fan blocked by debris",
            "Connector issue",
        ],
        "action": "Check condenser fan at bottom rear. Clean debris. Test motor and replace if failed.",
    },
    "CI": {
        "meaning": "Compressor inverter fault.",
        "causes": [
            "Inverter board failure",
            "Compressor issue",
            "Wiring fault",
        ],
        "action": "Check inverter board. Test compressor windings. Replace inverter board if faulty.",
    },
    "DI": {
        "meaning": "Defrost issue — defrost circuit problem.",
        "causes": [
            "Defrost heater burned out",
            "Defrost thermostat failed",
            "Main board defrost timer/relay failure",
        ],
        "action": "Check defrost heater continuity. Test defrost thermostat. If both good, suspect main board.",
    },
    "TF": {
        "meaning": "Temperature sensor fault — fridge sensor issue.",
        "causes": [
            "Thermistor failure",
            "Connector corroded",
        ],
        "action": "Check thermistor resistance. Replace if out of spec.",
    },
}

HONEYWELL_THERMOSTAT_CODES = {
    "E1": {
        "meaning": "Room temperature sensor failure.",
        "causes": ["Internal thermistor failure", "Wiring damage to sensor", "Board-level fault"],
        "action": "Check room sensor wiring. If hardwired sensor, test resistance. Replace thermostat if internal sensor failed.",
    },
    "E2": {
        "meaning": "Outdoor temperature sensor failure.",
        "causes": ["Outdoor sensor disconnected", "Wire damage from UV/weather", "Sensor out of range"],
        "action": "Check outdoor sensor wiring and connections. Test sensor resistance against spec. Replace sensor if faulty.",
    },
    "E3": {
        "meaning": "Communication error — thermostat can't reach equipment interface.",
        "causes": ["Wiring issue between thermostat and equipment", "Equipment interface module failure", "Incompatible equipment"],
        "action": "Check thermostat wiring connections. Verify equipment interface module is powered. Check compatibility.",
    },
    "E4": {
        "meaning": "Power failure — insufficient power to thermostat.",
        "causes": ["C-wire missing or disconnected", "Transformer undersized", "Wiring short"],
        "action": "Verify 24VAC at thermostat terminals. Check C-wire connection. If no C-wire, install one or use an add-a-wire kit.",
    },
    "E5": {
        "meaning": "HVAC system not responding — no equipment response.",
        "causes": ["Equipment turned off or breaker tripped", "Control board failure", "Wiring disconnect at equipment"],
        "action": "Check equipment power and breakers. Verify wiring at both thermostat and equipment terminals. Check control board for faults.",
    },
    "E6": {
        "meaning": "Humidity sensor failure.",
        "causes": ["Internal humidity sensor fault", "Excessive moisture damage", "Board failure"],
        "action": "Try power cycling the thermostat. If error persists, replace the unit.",
    },
    "80": {
        "meaning": "Low battery warning.",
        "causes": ["Batteries depleted", "Battery contacts corroded"],
        "action": "Replace batteries with fresh alkaline AA or AAA (model-dependent). Clean battery contacts.",
    },
    "90": {
        "meaning": "Wiring error — incorrect thermostat wiring detected.",
        "causes": ["Wires connected to wrong terminals", "Shorted wire", "Incompatible system wiring"],
        "action": "Turn off power. Verify wire connections match the wiring diagram for your system type. Check for shorts.",
    },
}

EMERSON_THERMOSTAT_CODES = {
    "E1": {
        "meaning": "Short in room temperature sensor.",
        "causes": ["Internal sensor shorted", "Moisture damage", "Board-level fault"],
        "action": "Power cycle the thermostat. If error persists, the internal sensor has failed — replace the thermostat.",
    },
    "E2": {
        "meaning": "Open room temperature sensor.",
        "causes": ["Internal sensor open circuit", "Loose internal connection"],
        "action": "Power cycle. If error persists, replace the thermostat.",
    },
    "E3": {
        "meaning": "Short in outdoor/remote sensor.",
        "causes": ["Outdoor sensor wire shorted", "Sensor failed short", "Water intrusion at sensor"],
        "action": "Check outdoor sensor wiring for damage. Disconnect sensor and test resistance. Replace if shorted.",
    },
    "E4": {
        "meaning": "Open outdoor/remote sensor.",
        "causes": ["Outdoor sensor wire broken", "Sensor disconnected", "Sensor failed open"],
        "action": "Check wiring continuity to outdoor sensor. Reconnect or replace sensor.",
    },
    "E5": {
        "meaning": "EEPROM communication error — memory fault.",
        "causes": ["Internal memory corruption", "Power surge damage", "Manufacturing defect"],
        "action": "Try factory reset. If error persists after reset, replace the thermostat.",
    },
    "E6": {
        "meaning": "Keypad or button stuck.",
        "causes": ["Button physically stuck", "Moisture behind faceplate", "Debris in button mechanism"],
        "action": "Clean around all buttons. Remove faceplate and check for debris or moisture. Replace if button mechanism is damaged.",
    },
}

YORK_FURNACE_CODES = {
    "1": {
        "meaning": "No previous error code stored.",
        "causes": ["Normal operation — no faults in history"],
        "action": "No action needed. Informational code only.",
    },
    "2": {
        "meaning": "System lockout — unit locked out after repeated failed ignition.",
        "causes": [
            "Gas supply issue (shut-off valve, meter, low pressure)",
            "Failed igniter",
            "Dirty flame sensor",
            "Gas valve failure",
        ],
        "action": "Cycle power to reset lockout. Check gas supply first, then clean flame sensor, inspect igniter. If relocks, check gas valve.",
    },
    "3": {
        "meaning": "Pressure switch fault — didn't close or opened during operation.",
        "causes": [
            "Plugged condensate drain or trap (most common on 90%+ units)",
            "Failed or weak inducer motor",
            "Blocked flue or intake pipe",
            "Cracked or water-logged pressure switch hose",
            "Defective pressure switch",
        ],
        "action": "Check condensate drain/trap first — blow out with compressed air. Verify inducer is running and pulling proper vacuum. Inspect hose from inducer to switch for cracks or water. Check flue/intake for blockages.",
    },
    "4": {
        "meaning": "High temperature limit switch open.",
        "causes": [
            "Dirty air filter (check first — most common)",
            "Blocked or closed supply/return registers",
            "Failed blower motor or weak capacitor",
            "Dirty blower wheel",
            "Cracked heat exchanger (if limit trips repeatedly with good airflow)",
        ],
        "action": "Replace filter. Open all registers. Check blower operation and capacitor. If trips with good airflow, suspect heat exchanger — run combustion analysis.",
    },
    "5": {
        "meaning": "Flame sensed when no flame should be present.",
        "causes": [
            "Leaking gas valve (internal valve seal failure)",
            "Flame sensor wiring shorted to ground",
            "Residual flame or hot surface near sensor",
        ],
        "action": "SAFETY — shut off gas supply immediately. Check gas valve for internal leak. Inspect flame sensor wiring for shorts to chassis ground.",
    },
    "6": {
        "meaning": "Power or low voltage problem.",
        "causes": [
            "24V transformer failure or weak output",
            "Blown low-voltage fuse on control board",
            "Thermostat wiring short",
            "Loose connections on control board terminals",
        ],
        "action": "Check 24V transformer output (should read 24-28VAC). Check board fuse. Inspect thermostat wiring for shorts. Tighten board connections.",
    },
    "7": {
        "meaning": "Gas valve circuit failure — board can't energize gas valve.",
        "causes": [
            "Failed gas valve (coil open or shorted)",
            "Open wiring between board and gas valve",
            "Control board gas valve relay failed",
        ],
        "action": "Check for 24V at gas valve terminals during call for heat. If voltage present but valve doesn't open, replace gas valve. If no voltage at valve, check wiring then board.",
    },
    "8": {
        "meaning": "Igniter failure — igniter not reaching temperature.",
        "causes": [
            "Cracked or worn-out hot surface igniter",
            "Open circuit in igniter wiring",
            "Board igniter relay failure",
            "Wrong igniter resistance for control board",
        ],
        "action": "Check igniter resistance (silicon nitride: 40-90 ohms cold, silicon carbide: 9-45 ohms cold). If open or out of range, replace. Check for 120V at igniter connector during ignition sequence.",
    },
    "9": {
        "meaning": "Ignition failure — no flame detected after ignition trial.",
        "causes": [
            "Dirty flame sensor (most common — carbon buildup)",
            "Gas supply off or low gas pressure",
            "Cracked or weak igniter not getting hot enough",
            "Gas valve not opening",
        ],
        "action": "Clean flame sensor with fine emery cloth first — this fixes it 80% of the time. Check gas supply and pressure. Verify igniter glows bright orange/white during trial.",
    },
    "10": {
        "meaning": "Polarity or grounding issue.",
        "causes": [
            "Hot and neutral reversed at furnace outlet",
            "Poor or missing chassis ground",
            "Floating neutral in electrical panel",
        ],
        "action": "Check polarity at furnace outlet — hot on narrow blade. Verify solid chassis ground. Check panel neutral connection.",
    },
    "11": {
        "meaning": "Rollout switch open — flames escaping combustion chamber.",
        "causes": [
            "Cracked heat exchanger (PRIMARY concern — most serious cause)",
            "Blocked flue or vent pipe causing backdraft",
            "Blocked heat exchanger cells (debris/scale buildup)",
        ],
        "action": "SAFETY — do NOT reset rollout without thorough inspection. Inspect heat exchanger for cracks with mirror/flashlight. Run combustion analyzer — check CO in supply duct. If heat exchanger is cracked, condemn unit. Check flue for blockages.",
    },
    "12": {
        "meaning": "Blower motor fault — motor didn't reach target speed or failed to start.",
        "causes": [
            "Failed blower motor",
            "Bad motor capacitor (PSC motors)",
            "ECM motor control fault",
            "Dirty blower wheel causing excessive load",
            "Wiring issue between board and motor",
        ],
        "action": "PSC motors: check capacitor with meter (must be within 5% of rated µF). ECM motors: check for power at motor connector (3-4 pin Molex). Clean blower wheel. Check wiring connections.",
    },
    "13": {
        "meaning": "Limit circuit lockout — high temp limit tripped 3+ consecutive cycles.",
        "causes": [
            "Dirty/clogged air filter (most common)",
            "Multiple closed registers restricting airflow",
            "Failed blower motor or weak capacitor",
            "Undersized or restricted ductwork",
        ],
        "action": "Replace filter immediately. Open all registers. Check blower operation. Measure static pressure (should be under 0.5\" WC). If static is high with clean filter, ductwork is undersized.",
    },
}

TAKAGI_TANKLESS_CODES = {
    "3": {
        "meaning": "Exhaust temperature too high — exhaust thermistor reading above limit.",
        "causes": [
            "Scale buildup in heat exchanger (most common — restricts flow, increases temps)",
            "Blocked or restricted exhaust vent",
            "Failed exhaust thermistor giving false reading",
        ],
        "action": "Flush the heat exchanger with white vinegar (descale procedure). Check exhaust vent for blockages or restrictions. If recently flushed, check exhaust thermistor resistance.",
    },
    "11": {
        "meaning": "No ignition — unit failed to ignite.",
        "causes": [
            "Gas supply off or low gas pressure",
            "Failed igniter (no spark)",
            "Gas valve not opening",
            "Air in gas line (new install or after gas work)",
        ],
        "action": "Verify gas supply is on and pressure is correct (Takagi typically needs 3.5-10.5\" WC for NG). Check igniter for spark. If new install, purge air from gas line. Check error history — if intermittent, suspect gas pressure fluctuation.",
    },
    "12": {
        "meaning": "Flame loss — flame established then lost during operation.",
        "causes": [
            "Low gas pressure or pressure fluctuation",
            "Dirty flame rod",
            "Wind causing flame blowout (exterior venting)",
            "Scale buildup in heat exchanger",
        ],
        "action": "Check gas pressure during firing (should be stable). Clean flame rod with emery cloth. If exterior vented, check for wind conditions and vent termination. Descale heat exchanger if overdue.",
    },
    "31": {
        "meaning": "Low water flow — flow below minimum activation threshold.",
        "causes": [
            "Inlet water filter clogged (check this first)",
            "Scale buildup restricting flow through heat exchanger",
            "Flow sensor failure",
            "Partially closed isolation valve",
        ],
        "action": "Clean the inlet water filter screen first (most common fix). Check isolation valves are fully open. If filter is clean, descale the unit. If flow still low, test flow sensor.",
    },
    "101": {
        "meaning": "Abnormal combustion — incomplete combustion detected.",
        "causes": [
            "Insufficient combustion air supply",
            "Blocked or undersized venting",
            "Scale buildup in heat exchanger",
            "Gas pressure out of spec",
        ],
        "action": "Check combustion air supply — make sure intake isn't blocked or too close to exhaust. Verify vent sizing matches installation manual. Descale heat exchanger. Check gas pressure.",
    },
    "111": {
        "meaning": "Ignition failure — repeated no-ignition attempts.",
        "causes": [
            "Gas supply issue",
            "Igniter failure",
            "Gas solenoid valve stuck",
            "Ground wire issue",
        ],
        "action": "Same as code 011 but indicates persistent problem. Check ground wire connection. If igniter sparks but no flame, focus on gas supply. Replace igniter if no spark visible.",
    },
    "121": {
        "meaning": "Flame failure — repeated flame loss.",
        "causes": [
            "Chronic low gas pressure",
            "Failing flame rod",
            "Heat exchanger heavily scaled",
            "Condensation dripping onto burner",
        ],
        "action": "Same as code 012 but persistent. Measure gas pressure during operation — if it drops when unit fires, gas line may be undersized. Replace flame rod if corroded. Descale unit.",
    },
    "200": {
        "meaning": "Fuse blown on PC board.",
        "causes": [
            "Power surge or lightning damage",
            "Short in wiring",
            "PC board failure",
        ],
        "action": "Check fuse on PC board — if blown, look for the short before replacing. Inspect wiring for damage. May need new PC board if surge damaged it.",
    },
    "251": {
        "meaning": "Overheat protection — water temperature exceeded limit.",
        "causes": [
            "Scale buildup in heat exchanger (most common)",
            "Flow rate too low",
            "Temperature sensor failure",
        ],
        "action": "Descale the heat exchanger — this is the #1 cause. Check for adequate flow. Test temperature sensor.",
    },
    "281": {
        "meaning": "Fan (combustion blower) fault — fan not running at expected speed.",
        "causes": [
            "Fan motor failure",
            "Debris in fan assembly",
            "Wiring issue to fan motor",
            "PC board fan circuit failure",
        ],
        "action": "Check fan for debris or obstruction. Verify fan spins freely by hand. Check wiring connections. If wiring good and fan is clear, likely fan motor or PC board.",
    },
    "311": {
        "meaning": "Inlet thermistor short — temperature sensor reading abnormally low resistance.",
        "causes": [
            "Thermistor failed short",
            "Wiring short in thermistor circuit",
            "Water damage to connector",
        ],
        "action": "Measure thermistor resistance (should match Takagi spec chart for current water temp). If shorted, replace thermistor. Check connector for corrosion.",
    },
    "321": {
        "meaning": "Inlet thermistor open — temperature sensor reading infinite resistance.",
        "causes": [
            "Thermistor failed open",
            "Disconnected or broken wire",
            "Corroded connector",
        ],
        "action": "Check thermistor connector — push firmly. Measure resistance. If open, replace thermistor.",
    },
    "391": {
        "meaning": "Exhaust bypass servo fault — bypass damper not responding.",
        "causes": [
            "Servo motor failure",
            "Mechanical obstruction in bypass",
            "Wiring issue to servo",
        ],
        "action": "Check servo motor operation. Look for mechanical obstruction. Check wiring. May need servo motor replacement.",
    },
    "611": {
        "meaning": "Flow control / water valve fault.",
        "causes": [
            "Water flow control valve stuck or failed",
            "Debris in flow control mechanism",
            "Wiring issue",
        ],
        "action": "Check flow control valve for debris. Verify valve moves freely. Check electrical connections. Replace valve if stuck.",
    },
    "710": {
        "meaning": "Gas solenoid valve fault — valve not responding properly.",
        "causes": [
            "Gas solenoid coil failure",
            "Wiring issue to solenoid",
            "PC board output failure",
        ],
        "action": "Check for voltage at solenoid during operation. If voltage present but valve doesn't open, replace solenoid. If no voltage, check PC board.",
    },
    "991": {
        "meaning": "Communication error — remote controller or external device communication failure.",
        "causes": [
            "Loose or damaged communication wire",
            "Remote controller failure",
            "PC board communication circuit failure",
        ],
        "action": "Check wiring between unit and remote. Try disconnecting remote — if error clears, replace remote. If error persists, check PC board.",
    },
}

LOCHINVAR_BOILER_CODES = {
    "E01": {
        "meaning": "Ignition failure — no flame established.",
        "causes": [
            "Gas supply off or low pressure",
            "Failed igniter/spark electrode",
            "Gas valve not opening",
            "Air in gas line",
        ],
        "action": "Verify gas supply and pressure. Check spark electrode for proper gap and condition. If new install, purge gas line. Check gas valve operation.",
    },
    "E02": {
        "meaning": "False flame — flame signal detected before ignition sequence.",
        "causes": [
            "Flame sensor contaminated or failing",
            "Gas valve leaking internally",
            "Residual heat near sensor",
        ],
        "action": "Clean flame sensor rod. Check gas valve for internal leak. Inspect for any residual combustion.",
    },
    "E03": {
        "meaning": "Fan/blower fault — combustion fan not reaching target speed.",
        "causes": [
            "Fan motor failure",
            "Debris in fan housing",
            "Wiring issue to fan",
            "PCB fan circuit failure",
        ],
        "action": "Check fan for obstruction. Verify fan spins freely. Check wiring. If mechanical and electrical are good, suspect fan motor or PCB.",
    },
    "E04": {
        "meaning": "High limit — water temperature exceeded safety limit.",
        "causes": [
            "Low water flow through boiler",
            "Circulator pump failure",
            "Air locked in system",
            "Dirty heat exchanger (scale buildup)",
        ],
        "action": "Check circulator pump operation. Bleed air from system. Verify adequate flow. Descale heat exchanger if needed.",
    },
    "E05": {
        "meaning": "Sensor fault — supply or return temperature sensor out of range.",
        "causes": [
            "Temperature sensor failure",
            "Loose or corroded sensor connector",
            "Wiring issue",
        ],
        "action": "Check sensor resistance against Lochinvar spec chart. Check connector. Replace sensor if out of spec.",
    },
    "E06": {
        "meaning": "Low water pressure — system pressure below minimum.",
        "causes": [
            "Leak in system piping or components",
            "Expansion tank waterlogged (failed bladder)",
            "Pressure relief valve weeping",
            "Fill valve not maintaining pressure",
        ],
        "action": "Check system for leaks. Check expansion tank pre-charge (should be at fill pressure with tank isolated). Inspect pressure relief valve. Verify auto-fill valve operation.",
    },
    "E07": {
        "meaning": "Exhaust temperature too high — exhaust thermistor above limit.",
        "causes": [
            "Scale buildup in heat exchanger",
            "Low water flow",
            "Blocked or restricted exhaust vent",
            "Over-firing (gas pressure too high)",
        ],
        "action": "Check water flow rate. Descale heat exchanger. Verify exhaust vent is clear and properly sized. Check gas pressure — should match nameplate.",
    },
    "E10": {
        "meaning": "Flame loss during operation — flame established then lost.",
        "causes": [
            "Gas pressure fluctuation",
            "Dirty flame sensor",
            "Condensate drain blocked (condensing models)",
            "Wind downdraft on venting",
        ],
        "action": "Check gas pressure during firing (should be stable). Clean flame sensor. Check condensate drain. Verify vent termination for wind exposure.",
    },
    "E12": {
        "meaning": "Freeze protection activated — low temperature detected.",
        "causes": [
            "Unit exposed to near-freezing temperatures",
            "Temperature sensor in cold draft",
            "Sensor failure giving false low reading",
        ],
        "action": "If actually cold, address heating of mechanical space. Check sensor location. Test sensor resistance against temp chart.",
    },
    "E15": {
        "meaning": "DHW (domestic hot water) sensor fault — sensor out of range.",
        "causes": [
            "DHW sensor failure",
            "Loose connector",
            "Wiring damage",
        ],
        "action": "Check DHW sensor resistance. Check connector and wiring. Replace sensor if faulty.",
    },
    "L01": {
        "meaning": "Lockout — unit locked out after repeated ignition failures.",
        "causes": [
            "Persistent gas supply issue",
            "Failed ignition components",
            "Venting issue",
        ],
        "action": "Requires manual reset. Address root cause from E01 diagnostics before resetting. Check error history to identify pattern.",
    },
    "L02": {
        "meaning": "Lockout — safety limit exceeded.",
        "causes": [
            "Repeated high limit trips (E04)",
            "System flow issue not resolved",
            "Critical sensor failure",
        ],
        "action": "Manual reset required. Must resolve underlying flow/temperature issue before resetting. Check circulator, air locks, and heat exchanger.",
    },
}

LOCHINVAR_TANKLESS_CODES = {
    "E01": {
        "meaning": "Ignition failure — no flame established.",
        "causes": [
            "Gas supply off or low pressure",
            "Igniter failure",
            "Gas valve not opening",
        ],
        "action": "Check gas supply and pressure. Inspect igniter. If new install, purge gas line.",
    },
    "E02": {
        "meaning": "False flame detection.",
        "causes": ["Contaminated flame sensor", "Gas valve leak", "Sensor wiring issue"],
        "action": "Clean flame sensor. Check gas valve. Inspect wiring.",
    },
    "E03": {
        "meaning": "Fan fault — combustion fan issue.",
        "causes": ["Fan motor failure", "Obstruction in fan", "Wiring fault"],
        "action": "Check fan for debris. Verify fan operation. Check wiring and motor.",
    },
    "E04": {
        "meaning": "Over temperature — water too hot.",
        "causes": [
            "Scale buildup in heat exchanger (most common)",
            "Low water flow",
            "Temperature sensor issue",
        ],
        "action": "Descale heat exchanger. Check for adequate water flow. Test temperature sensor.",
    },
    "E05": {
        "meaning": "Temperature sensor fault.",
        "causes": ["Sensor failure", "Loose connector", "Wiring issue"],
        "action": "Check sensor resistance. Inspect connector. Replace if out of spec.",
    },
    "E10": {
        "meaning": "Flame loss during operation.",
        "causes": [
            "Gas pressure fluctuation",
            "Dirty flame sensor",
            "Vent blockage or wind issue",
        ],
        "action": "Check gas pressure under load. Clean flame sensor. Inspect venting.",
    },
}

MIDEA_MINI_SPLIT_CODES = {
    "E1": {
        "meaning": "Indoor unit coil temperature sensor fault.",
        "causes": [
            "Coil thermistor failed (open or short)",
            "Connector loose or corroded",
            "Wiring issue between sensor and PCB",
        ],
        "action": "Check coil thermistor resistance (typically 10kΩ at 77°F). Check connector. Replace thermistor if out of spec.",
    },
    "E2": {
        "meaning": "Indoor ambient temperature sensor fault.",
        "causes": [
            "Room temp thermistor failed",
            "Loose connector on indoor PCB",
            "Wiring damage",
        ],
        "action": "Check room sensor resistance. Inspect connector on PCB. Replace sensor if faulty.",
    },
    "E3": {
        "meaning": "Outdoor unit coil temperature sensor fault.",
        "causes": [
            "Outdoor coil thermistor failure",
            "Connector issue at outdoor PCB",
            "Wire damage from UV exposure or rodents",
        ],
        "action": "Check outdoor coil sensor resistance. Inspect wiring for physical damage. Replace if faulty.",
    },
    "E4": {
        "meaning": "Indoor unit EEPROM error — memory chip fault.",
        "causes": [
            "Power surge corrupted EEPROM data",
            "PCB failure",
            "Manufacturing defect",
        ],
        "action": "Try power cycling (disconnect for 30 seconds). If error persists, replace indoor PCB.",
    },
    "E5": {
        "meaning": "Communication error between indoor and outdoor units.",
        "causes": [
            "Wiring issue between indoor and outdoor units (most common)",
            "Loose terminal connections",
            "Indoor or outdoor PCB failure",
            "Voltage mismatch",
        ],
        "action": "Check communication wiring between units — must be proper gauge and properly terminated. Check terminal connections at both boards. Verify voltage at outdoor unit. Try power cycling both units.",
    },
    "E6": {
        "meaning": "Indoor fan motor fault.",
        "causes": [
            "Fan motor failure",
            "Fan blade obstructed or frozen",
            "Wiring issue to fan motor",
            "PCB fan driver failure",
        ],
        "action": "Check fan for obstructions. Verify motor spins freely. Check wiring connections. If motor hums but doesn't spin, motor is likely failed.",
    },
    "E8": {
        "meaning": "Indoor unit overload or overcurrent.",
        "causes": [
            "Indoor fan motor drawing excessive current",
            "Dirty indoor coil restricting airflow",
            "PCB issue",
        ],
        "action": "Clean indoor coil. Check fan motor current draw. If motor is drawing high amps, replace motor.",
    },
    "F1": {
        "meaning": "Outdoor ambient temperature sensor fault.",
        "causes": [
            "Outdoor temp sensor failure",
            "Connector corrosion from weather exposure",
            "Wire damage",
        ],
        "action": "Check outdoor ambient sensor resistance. Inspect for weather damage. Replace sensor if faulty.",
    },
    "F2": {
        "meaning": "Outdoor coil (condenser) temperature sensor fault.",
        "causes": [
            "Condenser coil sensor failure",
            "Loose or corroded connection",
            "Wire damage",
        ],
        "action": "Check condenser coil sensor resistance. Clean connector. Replace if out of spec.",
    },
    "F3": {
        "meaning": "Outdoor discharge temperature sensor fault.",
        "causes": [
            "Discharge temp sensor failure",
            "Sensor not properly mounted on discharge line",
            "Wiring issue",
        ],
        "action": "Verify sensor is firmly clamped to discharge line with insulation. Check resistance. Replace if faulty.",
    },
    "F4": {
        "meaning": "Outdoor unit EEPROM error.",
        "causes": ["Power surge", "PCB failure"],
        "action": "Power cycle outdoor unit. If persists, replace outdoor PCB.",
    },
    "P0": {
        "meaning": "IPM (Intelligent Power Module) protection — inverter module fault.",
        "causes": [
            "IPM module overheating",
            "Compressor winding fault",
            "DC bus voltage issue",
            "Insufficient refrigerant causing compressor overheating",
        ],
        "action": "Check refrigerant charge. Verify outdoor coil is clean. Check compressor winding resistance. If IPM module is shorted, replace outdoor PCB.",
    },
    "P1": {
        "meaning": "Over/under voltage protection — power supply out of acceptable range.",
        "causes": [
            "High or low line voltage (should be 198-253V for 220V units)",
            "Voltage fluctuation from utility",
            "Loose power connections causing voltage drop",
        ],
        "action": "Measure line voltage at outdoor unit disconnect. Check for loose connections. If voltage is consistently out of range, install a voltage stabilizer or address utility issue.",
    },
    "P2": {
        "meaning": "Compressor overcurrent protection.",
        "causes": [
            "Compressor mechanical fault (locked rotor)",
            "Low refrigerant charge",
            "Dirty outdoor coil restricting heat rejection",
            "Compressor winding fault",
        ],
        "action": "Check refrigerant pressures. Clean outdoor coil. Measure compressor winding resistance (check for shorts to ground). If compressor is locked, try a hard start kit — if still won't start, compressor is failed.",
    },
    "P3": {
        "meaning": "Compressor high discharge temperature protection.",
        "causes": [
            "Low refrigerant charge (most common — superheat too high)",
            "Restriction in refrigerant circuit (filter drier, TXV, kink in line)",
            "Dirty outdoor coil",
            "Compressor valve failure",
        ],
        "action": "Check refrigerant charge — low charge causes high discharge temps. Check superheat. Inspect for restrictions (frosted component = restriction). Clean outdoor coil.",
    },
    "P4": {
        "meaning": "High pressure protection — head pressure exceeded limit.",
        "causes": [
            "Dirty outdoor coil (most common)",
            "Outdoor fan not running",
            "Refrigerant overcharge",
            "Restriction in liquid line",
            "High ambient temperature exceeding unit rating",
        ],
        "action": "Clean outdoor coil thoroughly. Verify outdoor fan is running. Check refrigerant charge (subcooling). If fan is good and coil is clean, check for liquid line restriction.",
    },
    "P5": {
        "meaning": "Low pressure protection — suction pressure dropped below limit.",
        "causes": [
            "Low refrigerant charge (leak)",
            "Dirty indoor coil or filter restricting airflow",
            "Indoor fan not running",
            "Restriction in refrigerant circuit",
            "TXV stuck closed or underfeeding",
        ],
        "action": "Check indoor filter and coil. Verify indoor fan operation. Check refrigerant pressures — low suction with normal-to-low subcooling = low charge (find and fix leak). Low suction with high subcooling = restriction.",
    },
    "P6": {
        "meaning": "Outdoor unit overheating — PCB or module temperature too high.",
        "causes": [
            "Poor ventilation around outdoor unit",
            "Outdoor unit in direct sun with restricted airflow",
            "Fan motor failure reducing airflow across PCB",
        ],
        "action": "Check outdoor unit airflow. Verify fan is running. Ensure unit has proper clearance. Clean outdoor coil.",
    },
}

GREE_MINI_SPLIT_CODES = {
    "E1": {
        "meaning": "High pressure protection — system head pressure exceeded limit.",
        "causes": [
            "Dirty outdoor coil",
            "Outdoor fan motor failure",
            "Refrigerant overcharge",
            "Restriction in liquid line",
        ],
        "action": "Clean outdoor coil. Verify outdoor fan runs. Check subcooling (overcharge shows high subcooling). Check for restrictions.",
    },
    "E2": {
        "meaning": "Indoor unit freeze protection — indoor coil temperature below threshold.",
        "causes": [
            "Dirty air filter (most common)",
            "Low refrigerant charge",
            "Indoor fan running too slow",
            "Dirty indoor coil",
        ],
        "action": "Check/replace air filter first. Clean indoor coil. Check fan speed. If filter and coil are clean, check refrigerant charge.",
    },
    "E3": {
        "meaning": "Low pressure protection — suction pressure below minimum.",
        "causes": [
            "Low refrigerant charge (likely a leak)",
            "Restriction in refrigerant circuit",
            "Dirty indoor coil/filter",
            "TXV or EEV malfunction",
        ],
        "action": "Check refrigerant pressures. If low, find and fix leak before recharging. Check indoor filter/coil. Check for restrictions (frosted components indicate restriction point).",
    },
    "E4": {
        "meaning": "Compressor discharge temperature too high.",
        "causes": [
            "Low refrigerant charge (high superheat causes high discharge temp)",
            "Restriction in system",
            "Compressor valve wear",
            "Dirty condenser coil",
        ],
        "action": "Check refrigerant charge. Check superheat. Clean outdoor coil. If charge and airflow are good, suspect compressor valve leak.",
    },
    "E5": {
        "meaning": "Compressor overcurrent protection — compressor drawing too many amps.",
        "causes": [
            "Compressor mechanical fault",
            "Low or high voltage",
            "Dirty outdoor coil (high head pressure = high amps)",
            "Compressor winding short",
        ],
        "action": "Measure voltage at outdoor unit. Clean outdoor coil. Measure compressor amp draw vs nameplate RLA. Check winding resistance for shorts to ground.",
    },
    "E6": {
        "meaning": "Communication error between indoor and outdoor units.",
        "causes": [
            "Communication wiring fault (loose, broken, wrong gauge)",
            "PCB failure on indoor or outdoor unit",
            "Power supply issue to one unit",
            "Terminal connection loose at board",
        ],
        "action": "Check wiring between units — verify proper gauge, tight connections, no damage. Check power to both units. Try power cycling. If wiring is good, suspect PCB.",
    },
    "E7": {
        "meaning": "Mode conflict — indoor units requesting different modes (multi-zone systems).",
        "causes": [
            "One indoor unit requesting heat while another requests cool",
            "Indoor unit DIP switch misconfiguration",
        ],
        "action": "Set all active indoor units to the same mode (all heat or all cool). Check DIP switch settings on indoor PCBs match installation requirements.",
    },
    "E8": {
        "meaning": "Indoor unit anti-high temperature protection — indoor coil too hot in heat mode.",
        "causes": [
            "Indoor fan not running or running too slow",
            "Dirty indoor coil",
            "Indoor fan motor failure",
        ],
        "action": "Check indoor fan operation. Clean indoor coil. If fan is failed, replace fan motor.",
    },
    "E9": {
        "meaning": "Full water protection — condensate pan full (cooling mode).",
        "causes": [
            "Plugged condensate drain line",
            "Condensate pump failure (if equipped)",
            "Drain line not properly pitched",
            "Float switch triggered",
        ],
        "action": "Clear condensate drain line — use compressed air or wet/dry vac. Check drain pitch. If pump equipped, verify pump operation. Check float switch.",
    },
    "F0": {
        "meaning": "Refrigerant charge insufficient — low charge detection.",
        "causes": [
            "Refrigerant leak",
            "Undercharged at installation",
            "Schrader valve leak",
        ],
        "action": "Check pressures. Perform leak detection — soap bubbles, electronic detector, or nitrogen pressure test. Fix leak and recharge to nameplate spec.",
    },
    "F1": {
        "meaning": "Indoor ambient temperature sensor fault.",
        "causes": ["Sensor failure", "Loose connector", "Wiring damage"],
        "action": "Check sensor resistance (typically 10kΩ at 77°F). Replace if out of spec.",
    },
    "F2": {
        "meaning": "Indoor coil temperature sensor fault.",
        "causes": ["Sensor failure", "Connector issue", "Sensor not properly mounted to coil"],
        "action": "Check sensor resistance. Ensure sensor is firmly attached to coil with thermal paste/clip. Replace if faulty.",
    },
    "F3": {
        "meaning": "Outdoor ambient temperature sensor fault.",
        "causes": ["Sensor failure", "Weather damage to wiring", "Connector corrosion"],
        "action": "Check outdoor ambient sensor resistance. Inspect for physical damage. Replace if needed.",
    },
    "F4": {
        "meaning": "Outdoor coil temperature sensor fault.",
        "causes": ["Sensor failure", "Corrosion from outdoor exposure", "Wire damage"],
        "action": "Check condenser coil sensor resistance. Inspect wiring for damage. Replace sensor.",
    },
    "F5": {
        "meaning": "Outdoor discharge temperature sensor fault.",
        "causes": ["Sensor failure", "Not properly clamped to discharge line", "Wiring issue"],
        "action": "Verify sensor is clamped tightly to discharge line with insulation. Check resistance. Replace if faulty.",
    },
    "H1": {
        "meaning": "Defrosting — unit is in defrost mode (heat pump mode).",
        "causes": [
            "Normal operation — outdoor coil frosted and unit is melting ice",
            "If defrost is too frequent: low charge, dirty outdoor coil, or outdoor fan issue",
        ],
        "action": "H1 is usually normal — wait 5-10 minutes for defrost to complete. If unit is constantly defrosting, check refrigerant charge, clean outdoor coil, and verify outdoor fan operation.",
    },
    "H3": {
        "meaning": "Compressor overload protection.",
        "causes": [
            "Compressor running at maximum capacity for extended period",
            "High ambient temperature",
            "Dirty coils reducing heat transfer efficiency",
        ],
        "action": "Clean both indoor and outdoor coils. Verify adequate airflow. May indicate unit is undersized for the load. Check refrigerant charge.",
    },
    "H5": {
        "meaning": "IPM (Intelligent Power Module) protection — inverter fault.",
        "causes": [
            "IPM module overheating",
            "Compressor winding issue",
            "Voltage fluctuation",
            "Outdoor PCB failure",
        ],
        "action": "Check voltage at outdoor unit. Check compressor winding resistance (phase-to-phase should be balanced, no shorts to ground). If windings are good, suspect IPM module on outdoor PCB.",
    },
    "H6": {
        "meaning": "Indoor fan motor no-feedback protection — motor not sending speed signal.",
        "causes": [
            "Indoor fan motor failure",
            "Fan motor feedback wire disconnected",
            "Indoor PCB issue",
        ],
        "action": "Check fan motor connector — ensure feedback wire (usually thin wire separate from power wires) is connected. If connected, check motor operation. Replace motor if failed.",
    },
    "H7": {
        "meaning": "Compressor desynchronization — compressor lost sync with inverter.",
        "causes": [
            "Compressor mechanical issue",
            "Refrigerant liquid slugging",
            "IPM or inverter board issue",
        ],
        "action": "Check refrigerant charge (overcharge can cause liquid slugging). Check compressor winding resistance. If intermittent, may be liquid return during startup — check TXV/EEV operation.",
    },
}

COOPER_HUNTER_MINI_SPLIT_CODES = {
    "E1": {
        "meaning": "Indoor/outdoor communication error.",
        "causes": [
            "Communication wiring fault between units",
            "Loose terminal connections",
            "PCB failure",
        ],
        "action": "Check wiring between indoor and outdoor units. Verify tight connections. Power cycle both units. If persists, check PCBs.",
    },
    "E2": {
        "meaning": "Zero-crossing signal error — power supply issue.",
        "causes": [
            "Unstable power supply",
            "Indoor PCB fault",
            "Power line interference",
        ],
        "action": "Check power supply voltage. Try dedicated circuit. If voltage is stable, suspect indoor PCB.",
    },
    "E3": {
        "meaning": "Indoor fan motor speed fault.",
        "causes": [
            "Fan motor failure",
            "Fan blade obstruction",
            "Motor feedback signal lost",
        ],
        "action": "Check fan for obstructions. Verify motor feedback wire connected. Replace motor if failed.",
    },
    "E4": {
        "meaning": "Indoor coil temperature sensor fault.",
        "causes": ["Sensor failure", "Loose connector", "Wiring issue"],
        "action": "Check sensor resistance (10kΩ at 77°F typical). Replace if out of spec.",
    },
    "E5": {
        "meaning": "Indoor ambient temperature sensor fault.",
        "causes": ["Sensor failure", "Connector issue"],
        "action": "Check sensor resistance. Replace if faulty.",
    },
    "F1": {
        "meaning": "Outdoor ambient temperature sensor fault.",
        "causes": ["Sensor failure", "Weather damage", "Connector corrosion"],
        "action": "Check outdoor sensor resistance. Replace if needed.",
    },
    "F2": {
        "meaning": "Outdoor coil temperature sensor fault.",
        "causes": ["Sensor failure", "Corrosion", "Wire damage"],
        "action": "Check condenser coil sensor. Replace if faulty.",
    },
    "F3": {
        "meaning": "Outdoor discharge temperature sensor fault.",
        "causes": ["Sensor failure", "Improper mounting", "Wire damage"],
        "action": "Verify sensor clamped to discharge line. Check resistance. Replace if needed.",
    },
    "P0": {
        "meaning": "IPM module protection — inverter fault.",
        "causes": [
            "Module overheating",
            "Compressor winding fault",
            "Voltage issue",
        ],
        "action": "Check voltage. Check compressor winding resistance. Clean outdoor coil for better heat rejection. If windings and voltage good, suspect outdoor PCB.",
    },
    "P1": {
        "meaning": "Over/under voltage protection.",
        "causes": ["Line voltage out of range", "Loose connections", "Utility fluctuation"],
        "action": "Measure voltage at disconnect. Should be within ±10% of nameplate. Fix loose connections or install voltage stabilizer.",
    },
    "P2": {
        "meaning": "Compressor overcurrent.",
        "causes": ["Compressor fault", "Low/high voltage", "Dirty outdoor coil"],
        "action": "Check voltage. Clean outdoor coil. Measure compressor amps. Check windings.",
    },
    "P3": {
        "meaning": "High compressor discharge temperature.",
        "causes": ["Low charge", "Restriction", "Dirty coil", "Compressor valve wear"],
        "action": "Check refrigerant charge and superheat. Clean outdoor coil. If charge is correct, suspect compressor.",
    },
    "P4": {
        "meaning": "High pressure protection.",
        "causes": ["Dirty outdoor coil", "Fan not running", "Overcharge", "Restriction"],
        "action": "Clean outdoor coil. Check fan. Check subcooling (high = overcharge, low = restriction).",
    },
    "P5": {
        "meaning": "Low pressure protection.",
        "causes": ["Low charge (leak)", "Dirty filter/coil", "Indoor fan issue", "Restriction"],
        "action": "Check filter and indoor coil. Verify fan operation. Check pressures — if low, find leak before recharging.",
    },
}

HAIER_MINI_SPLIT_CODES = {
    "E1": {
        "meaning": "Indoor/outdoor communication error.",
        "causes": [
            "Communication wiring fault (most common)",
            "Terminal connections loose",
            "Indoor or outdoor PCB failure",
        ],
        "action": "Check communication wiring between units. Tighten all terminal connections. Power cycle both units. If wiring is good, check PCBs.",
    },
    "E2": {
        "meaning": "Zero-crossing detection fault — AC power issue.",
        "causes": [
            "Unstable AC power supply",
            "Indoor PCB zero-crossing circuit failure",
            "Electrical noise on power line",
        ],
        "action": "Check power supply voltage and stability. Try a different circuit. If voltage is stable, indoor PCB may need replacement.",
    },
    "E3": {
        "meaning": "Indoor fan motor fault — motor not running or no speed feedback.",
        "causes": [
            "Fan motor failure",
            "Fan blade jammed or obstructed",
            "Motor connector disconnected",
            "PCB fan driver circuit failure",
        ],
        "action": "Check for obstructions on fan wheel. Verify motor connector is firmly plugged in. Check if motor hums (locked rotor) or is silent (no power/dead motor). Replace motor if confirmed failed.",
    },
    "E4": {
        "meaning": "Indoor coil temperature sensor fault.",
        "causes": ["Thermistor failure", "Loose connection", "Wiring damage"],
        "action": "Check coil sensor resistance (10kΩ at 77°F typical for NTC). Replace if out of spec.",
    },
    "E5": {
        "meaning": "Indoor ambient (room) temperature sensor fault.",
        "causes": ["Sensor failure", "Connector loose", "Wire break"],
        "action": "Check room temp sensor resistance. Replace if faulty.",
    },
    "E7": {
        "meaning": "Water overflow protection — condensate pan full.",
        "causes": [
            "Plugged condensate drain line",
            "Condensate pump failure",
            "Drain line not pitched properly",
        ],
        "action": "Clear drain line with compressed air or wet/dry vac. Check drain pitch. Verify pump operation if equipped.",
    },
    "F1": {
        "meaning": "Outdoor ambient temperature sensor fault.",
        "causes": ["Sensor failure", "Weather/UV damage to wiring", "Corrosion"],
        "action": "Check outdoor ambient sensor resistance. Inspect for physical damage. Replace if needed.",
    },
    "F2": {
        "meaning": "Outdoor coil temperature sensor fault.",
        "causes": ["Sensor failure", "Corroded connector", "Wire damage"],
        "action": "Check condenser coil sensor resistance. Replace if out of range.",
    },
    "F3": {
        "meaning": "Outdoor discharge temperature sensor fault.",
        "causes": ["Sensor failure", "Sensor not clamped to discharge line properly"],
        "action": "Verify sensor is tightly clamped to discharge line with insulation wrap. Check resistance. Replace if faulty.",
    },
    "F5": {
        "meaning": "Outdoor defrost temperature sensor fault.",
        "causes": ["Sensor failure", "Weather damage"],
        "action": "Check defrost sensor resistance. Replace if out of spec.",
    },
    "F6": {
        "meaning": "Overload protection — system overloaded.",
        "causes": [
            "Dirty coils (indoor or outdoor)",
            "High ambient temperature beyond unit rating",
            "Refrigerant charge issue",
        ],
        "action": "Clean both coils. Check refrigerant charge. Verify unit isn't undersized for the load.",
    },
    "F7": {
        "meaning": "Compressor overcurrent protection.",
        "causes": [
            "Compressor mechanical fault",
            "Voltage out of range",
            "Winding short",
        ],
        "action": "Check voltage. Measure compressor current vs RLA. Check winding resistance for shorts to ground.",
    },
    "F8": {
        "meaning": "Compressor discharge temperature too high.",
        "causes": [
            "Low refrigerant charge",
            "Restriction in refrigerant circuit",
            "Dirty outdoor coil",
            "Compressor valve failure",
        ],
        "action": "Check refrigerant charge and superheat. Clean outdoor coil. If charge is correct and coil is clean, suspect compressor.",
    },
    "F9": {
        "meaning": "Outdoor fan motor fault.",
        "causes": [
            "Fan motor failure",
            "Fan blade obstructed",
            "Motor connector disconnected",
        ],
        "action": "Check fan for obstructions. Verify motor spins freely. Check connector. Replace motor if failed.",
    },
    "FA": {
        "meaning": "Low pressure protection — suction pressure too low.",
        "causes": [
            "Low refrigerant charge (leak)",
            "Dirty indoor filter/coil",
            "Indoor fan not running",
            "Restriction (TXV/EEV, filter drier)",
        ],
        "action": "Check indoor filter and coil. Verify indoor fan operation. Check refrigerant pressures. If low, find and fix leak before recharging.",
    },
    "FC": {
        "meaning": "High pressure protection — head pressure too high.",
        "causes": [
            "Dirty outdoor coil (most common)",
            "Outdoor fan not running",
            "Refrigerant overcharge",
            "Non-condensables in system",
        ],
        "action": "Clean outdoor coil. Verify outdoor fan operation. Check subcooling. If coil is clean and fan is running, may have non-condensables — recover, evacuate, and recharge.",
    },
}

BUDERUS_BOILER_CODES = {
    "A01": {
        "meaning": "Burner fault — no flame established after ignition attempt.",
        "causes": [
            "Gas supply off or low pressure",
            "Ignition electrode failed or dirty",
            "Gas valve not opening",
            "Air in gas line (new install or after service)",
        ],
        "action": "Check gas supply and pressure. Inspect ignition electrode — clean or replace. Check gas valve operation. If new install, purge gas line.",
    },
    "A11": {
        "meaning": "Flame signal during standby — flame detected when burner should be off.",
        "causes": [
            "Ionization electrode dirty or cross-wired",
            "Gas valve leaking internally",
            "Residual ionization from hot electrode",
        ],
        "action": "Clean ionization electrode. Check gas valve for internal leak. Check electrode wiring.",
    },
    "A21": {
        "meaning": "Flue gas temperature too high.",
        "causes": [
            "Scale buildup in heat exchanger",
            "Low water flow through boiler",
            "Flue gas sensor failure",
            "Over-firing",
        ],
        "action": "Check water flow through boiler. Descale heat exchanger if needed. Check firing rate against nameplate. Test flue gas sensor.",
    },
    "C01": {
        "meaning": "Fan fault — combustion fan not reaching target speed.",
        "causes": [
            "Fan motor failure",
            "Debris in fan housing",
            "Wiring issue to fan",
            "PCB fan circuit failure",
        ],
        "action": "Check fan for obstruction. Verify fan spins freely. Check wiring. If all good mechanically, suspect fan motor or PCB.",
    },
    "C04": {
        "meaning": "Flame loss during operation — flame established then lost.",
        "causes": [
            "Gas pressure fluctuation",
            "Dirty ionization electrode",
            "Condensate backup (condensing models)",
            "Vent/intake issue",
        ],
        "action": "Check gas pressure during firing. Clean ionization electrode. Check condensate drain. Verify vent/intake not blocked.",
    },
    "C32": {
        "meaning": "Pressure differential fault — air pressure switch issue.",
        "causes": [
            "Blocked flue or intake pipe",
            "Fan not providing adequate pressure",
            "Pressure switch failure",
            "Condensate blocking flue",
        ],
        "action": "Check flue and intake for blockages. Verify fan operation. Check condensate drain (condensate can back up into flue on condensing models). Test pressure switch.",
    },
    "C42": {
        "meaning": "Coding plug missing or fault — boiler configuration plug not detected.",
        "causes": [
            "Coding plug not installed",
            "Coding plug not fully seated",
            "Wrong coding plug for boiler model",
        ],
        "action": "Check that the coding plug is properly inserted on the PCB. It's a small plug that identifies the boiler model to the control. Reseat or replace if damaged.",
    },
    "C64": {
        "meaning": "Gas valve fault — abnormal gas valve operation.",
        "causes": [
            "Gas valve coil failure",
            "Wiring issue between PCB and gas valve",
            "PCB gas valve driver failure",
        ],
        "action": "Check gas valve wiring. Measure coil resistance. If coil is open, replace gas valve. If coil is good, suspect PCB.",
    },
    "C73": {
        "meaning": "Water pressure sensor fault — pressure reading out of range.",
        "causes": [
            "Pressure sensor failure",
            "Air in system near sensor",
            "Wiring issue to sensor",
        ],
        "action": "Compare sensor reading to an external gauge. Check wiring. Replace sensor if reading doesn't match actual pressure.",
    },
    "C76": {
        "meaning": "Supply temperature sensor short — sensor reading below range.",
        "causes": ["Temperature sensor shorted", "Wiring short", "Water damage to connector"],
        "action": "Measure sensor resistance (should match NTC curve for current temp). If zero or near-zero ohms, sensor is shorted — replace it.",
    },
    "C77": {
        "meaning": "Supply temperature sensor open — sensor reading above range.",
        "causes": ["Temperature sensor open circuit", "Disconnected wire", "Corroded connector"],
        "action": "Check sensor connector. Measure resistance — if infinite, sensor is open. Replace sensor.",
    },
    "D01": {
        "meaning": "Outdoor temperature sensor fault.",
        "causes": ["Sensor failure", "Wire damage (outdoor exposure)", "Connector issue"],
        "action": "Check outdoor sensor resistance. Inspect wiring for weather damage. Replace if faulty.",
    },
    "D30": {
        "meaning": "Flue gas temperature sensor short.",
        "causes": ["Sensor shorted", "Wiring issue"],
        "action": "Check flue gas sensor resistance. Replace if shorted.",
    },
    "D31": {
        "meaning": "Flue gas temperature sensor open.",
        "causes": ["Sensor open", "Disconnected wire"],
        "action": "Check connector. Measure resistance. Replace if open.",
    },
    "H01": {
        "meaning": "Return temperature sensor fault.",
        "causes": ["Sensor failure", "Connector issue", "Wiring damage"],
        "action": "Check return temp sensor resistance against spec chart. Replace if out of range.",
    },
    "H11": {
        "meaning": "DHW (domestic hot water) temperature sensor fault.",
        "causes": ["DHW sensor failure", "Connector corrosion", "Wiring issue"],
        "action": "Check DHW sensor resistance. Inspect connector. Replace sensor if faulty.",
    },
}

VIESSMANN_BOILER_CODES = {
    "C": {
        "meaning": "Burner flame failure during startup — no flame established.",
        "causes": [
            "Gas supply off or low pressure",
            "Ignition electrode fouled or failed",
            "Gas valve fault",
            "Air in gas line",
        ],
        "action": "Check gas supply and pressure. Clean or replace ignition electrode. Verify gas valve operation. Purge air from gas line if recently serviced.",
    },
    "F": {
        "meaning": "Unit lockout — safety shutdown requiring manual reset.",
        "causes": [
            "Repeated ignition failures",
            "Safety limit exceeded",
            "Critical sensor fault",
        ],
        "action": "Check error history to identify root cause. Address underlying issue before resetting. Press reset button to clear lockout.",
    },
    "10": {
        "meaning": "Outdoor temperature sensor fault.",
        "causes": [
            "Sensor failure",
            "Wire damage from weather exposure",
            "Sensor not connected",
        ],
        "action": "Check outdoor sensor resistance against Viessmann spec chart. Inspect wiring. Replace sensor if faulty.",
    },
    "18": {
        "meaning": "Mixing valve / actuator fault.",
        "causes": [
            "Mixing valve actuator motor failure",
            "Actuator disconnected",
            "Valve mechanically stuck",
        ],
        "action": "Check actuator power and wiring. Verify valve moves freely by hand (with actuator disconnected). Replace actuator if failed.",
    },
    "20": {
        "meaning": "Supply temperature sensor fault — reading out of range.",
        "causes": [
            "Temperature sensor failure",
            "Connector loose or corroded",
            "Wiring damage",
        ],
        "action": "Check supply temp sensor resistance (NTC sensor — compare to Viessmann chart). Check connector. Replace sensor if out of spec.",
    },
    "28": {
        "meaning": "Flue gas temperature too high — exhaust temp exceeded limit.",
        "causes": [
            "Scale buildup in heat exchanger reducing heat transfer",
            "Low water flow through boiler",
            "System pump failure",
            "Boiler firing rate too high for current conditions",
        ],
        "action": "Check system pump operation and flow rate. Descale heat exchanger. Verify firing rate. Check flue gas sensor for accuracy.",
    },
    "30": {
        "meaning": "Burner control unit fault.",
        "causes": [
            "Burner controller failure",
            "Wiring issue between controller and main PCB",
            "Power supply issue to controller",
        ],
        "action": "Check wiring connections to burner controller. Power cycle. If error persists, controller may need replacement.",
    },
    "38": {
        "meaning": "Gas valve fault — valve not operating correctly.",
        "causes": [
            "Gas valve coil failure",
            "Wiring issue to gas valve",
            "Control PCB gas valve circuit failure",
        ],
        "action": "Check gas valve coil resistance. Verify wiring. If coil and wiring are good, suspect control PCB.",
    },
    "40": {
        "meaning": "Return temperature sensor fault.",
        "causes": ["Sensor failure", "Connector issue", "Wiring damage"],
        "action": "Check return sensor resistance against spec chart. Inspect connector. Replace if out of range.",
    },
    "50": {
        "meaning": "Short circuit — supply temperature sensor reading abnormally low resistance.",
        "causes": ["Sensor shorted", "Wiring short", "Moisture in connector"],
        "action": "Check sensor resistance — if near zero, sensor is shorted. Check connector for moisture. Replace sensor.",
    },
    "58": {
        "meaning": "Open circuit — supply temperature sensor reading infinite resistance.",
        "causes": ["Sensor open", "Disconnected wire", "Broken connector"],
        "action": "Check sensor connector. If disconnected, reconnect. If connected and reading infinite, replace sensor.",
    },
    "60": {
        "meaning": "DHW temperature sensor fault.",
        "causes": ["DHW sensor failure", "Connector corrosion", "Wiring issue"],
        "action": "Check DHW sensor resistance. Inspect connector for corrosion. Replace sensor if faulty.",
    },
    "A0": {
        "meaning": "Low water pressure — system pressure below minimum threshold.",
        "causes": [
            "Leak in system piping, fittings, or components",
            "Expansion tank bladder failure (waterlogged tank)",
            "Pressure relief valve weeping",
            "Air removal causing gradual pressure loss",
        ],
        "action": "Check system for visible leaks. Check expansion tank pre-charge (isolate tank and check air side with tire gauge — should match cold fill pressure). Inspect PRV. Top off system and monitor.",
    },
    "F0": {
        "meaning": "Internal control fault — controller self-diagnostic failure.",
        "causes": [
            "Control PCB failure",
            "Power surge damage",
            "Firmware corruption",
        ],
        "action": "Try power cycling (off 30 seconds, then on). If error persists, control board likely needs replacement.",
    },
    "F2": {
        "meaning": "Safety shutdown — burner lockout on critical fault.",
        "causes": [
            "Repeated flame failures",
            "High limit switch tripped repeatedly",
            "Critical component failure detected",
        ],
        "action": "Check error log for specific failure sequence. Address root cause. Manual reset required after fixing issue.",
    },
    "F3": {
        "meaning": "Flame signal fault — abnormal flame signal reading.",
        "causes": [
            "Ionization electrode dirty or mispositioned",
            "Electrode ceramic cracked (grounding to burner)",
            "Wiring issue in flame sense circuit",
        ],
        "action": "Clean ionization electrode. Check electrode gap and position per manual. Inspect electrode ceramic for cracks. Check wiring.",
    },
    "F4": {
        "meaning": "No flame established — ignition failure.",
        "causes": [
            "Gas supply issue",
            "Ignition electrode failure",
            "Gas valve not energizing",
            "Flue/intake blocked",
        ],
        "action": "Check gas supply. Inspect ignition electrode. Verify gas valve gets signal from controller. Check flue and combustion air intake for blockages.",
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
    # "pain" removed — too common a word, causes false positives
    # Goodman
    "goodman": "goodman",
    "amana": "goodman",  # Same manufacturer
    # Lennox — STT may say "lenox" or "lennocks"
    "lennox": "lennox",
    "lenox": "lennox",
    "lennocks": "lennox",
    # Trane — STT often transcribes as "train" or "traine"
    "trane": "trane",
    "trane error": "trane",
    "train error": "trane",
    "train furnace": "trane",
    "train code": "trane",
    "train unit": "trane",
    "train ac": "trane",
    "train heat": "trane",
    "train hvac": "trane",
    "train blink": "trane",
    "traine": "trane",
    "trayne": "trane",
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
    # Navien — STT may say "navian" or split it
    "navien": "navien",
    "navian": "navien",
    "navi en": "navien",
    # Noritz — STT may truncate
    "noritz": "noritz",
    "norit": "noritz",
    # LG
    "lg": "lg",
    "l.g.": "lg",
    "l g": "lg",
    "life's good": "lg",
    # Samsung — STT usually gets it
    "samsung": "samsung",
    "sam sung": "samsung",
    # Weil-McLain — STT often garbles this
    "weil mclain": "weil_mclain",
    "weil-mclain": "weil_mclain",
    "weil mclane": "weil_mclain",
    "wile mclane": "weil_mclain",
    # Whirlpool — STT may split; includes Maytag & KitchenAid (same parent)
    "whirlpool": "whirlpool",
    "whirl pool": "whirlpool",
    "maytag": "whirlpool",
    "may tag": "whirlpool",
    "kitchenaid": "whirlpool",
    # GE / GE Appliances
    "ge": "ge",
    "g.e.": "ge",
    "general electric": "ge",
    "ge appliances": "ge",
    # Bosch — STT may say "bosh"
    "bosch": "bosch",
    "bosh": "bosch",
    # Honeywell — STT usually gets it
    "honeywell": "honeywell",
    "honey well": "honeywell",
    "honeywell home": "honeywell",
    # Emerson / Sensi — same parent company
    "emerson": "emerson",
    "sensi": "emerson",
    "white rodgers": "emerson",
    "white-rodgers": "emerson",
    # York / Coleman / Luxaire — Johnson Controls family
    "york": "york",
    "coleman": "york",  # Same parent company (Johnson Controls)
    "luxaire": "york",  # Same parent company
    "evcon": "york",  # Same parent company
    # Takagi — STT may say "takagi" or "ta kagi"
    "takagi": "takagi",
    "ta kagi": "takagi",
    "tokagi": "takagi",
    # Lochinvar — STT may split it
    "lochinvar": "lochinvar",
    "lock in var": "lochinvar",
    "loch in var": "lochinvar",
    # Midea — also sold as Mr. Cool, Klimaire, Pioneer
    "midea": "midea",
    "mr cool": "midea",  # Midea subsidiary
    "mrcool": "midea",
    "mr. cool": "midea",
    "mister cool": "midea",
    "klimaire": "midea",  # Uses Midea internals
    "pioneer": "midea",  # Uses Midea internals (Pioneer mini-splits)
    # Gree — world's largest AC manufacturer
    "gree": "gree",
    # "grey" removed — too common a word, causes false positives
    "gri": "gree",
    # Cooper & Hunter — STT may split or garble
    "cooper hunter": "cooper_hunter",
    "cooper & hunter": "cooper_hunter",
    "cooper and hunter": "cooper_hunter",
    "c&h": "cooper_hunter",
    # Haier — GE Appliances parent company
    "haier": "haier",
    # "higher" removed — too common a word, causes false positives
    "hi er": "haier",
    # Buderus — Bosch subsidiary, common in northeast US
    "buderus": "buderus",
    "bud eris": "buderus",
    "boo deris": "buderus",
    # Viessmann — premium European boiler brand
    "viessmann": "viessmann",
    "veesman": "viessmann",
    "v s man": "viessmann",
    "vis man": "viessmann",
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
    "navien": {
        "tankless": NAVIEN_TANKLESS_CODES,
        "water heater": NAVIEN_TANKLESS_CODES,
        "boiler": NAVIEN_BOILER_CODES,
        "combi": NAVIEN_BOILER_CODES,
    },
    "noritz": {
        "tankless": NORITZ_TANKLESS_CODES,
        "water heater": NORITZ_TANKLESS_CODES,
    },
    "lg": {
        "mini split": LG_MINI_SPLIT_CODES,
        "minisplit": LG_MINI_SPLIT_CODES,
        "air conditioner": LG_MINI_SPLIT_CODES,
        "heat pump": LG_MINI_SPLIT_CODES,
        "washer": APPLIANCE_LG_WASHER_CODES,
        "washing machine": APPLIANCE_LG_WASHER_CODES,
        "dryer": APPLIANCE_LG_DRYER_CODES,
        "refrigerator": APPLIANCE_LG_REFRIGERATOR_CODES,
        "fridge": APPLIANCE_LG_REFRIGERATOR_CODES,
        "dishwasher": APPLIANCE_LG_DISHWASHER_CODES,
    },
    "samsung": {
        "mini split": SAMSUNG_MINI_SPLIT_CODES,
        "minisplit": SAMSUNG_MINI_SPLIT_CODES,
        "air conditioner": SAMSUNG_MINI_SPLIT_CODES,
        "heat pump": SAMSUNG_MINI_SPLIT_CODES,
        "washer": APPLIANCE_SAMSUNG_WASHER_CODES,
        "washing machine": APPLIANCE_SAMSUNG_WASHER_CODES,
        "dryer": APPLIANCE_SAMSUNG_DRYER_CODES,
        "refrigerator": APPLIANCE_SAMSUNG_REFRIGERATOR_CODES,
        "fridge": APPLIANCE_SAMSUNG_REFRIGERATOR_CODES,
        "oven": APPLIANCE_SAMSUNG_OVEN_CODES,
        "range": APPLIANCE_SAMSUNG_OVEN_CODES,
    },
    "weil_mclain": {
        "boiler": WEIL_MCLAIN_BOILER_CODES,
    },
    "whirlpool": {
        "washer": APPLIANCE_WHIRLPOOL_WASHER_CODES,
        "washing machine": APPLIANCE_WHIRLPOOL_WASHER_CODES,
        "dryer": APPLIANCE_WHIRLPOOL_DRYER_CODES,
        "oven": APPLIANCE_WHIRLPOOL_OVEN_CODES,
        "range": APPLIANCE_WHIRLPOOL_OVEN_CODES,
    },
    "ge": {
        "oven": APPLIANCE_GE_OVEN_CODES,
        "range": APPLIANCE_GE_OVEN_CODES,
        "dishwasher": APPLIANCE_GE_DISHWASHER_CODES,
        "refrigerator": APPLIANCE_GE_REFRIGERATOR_CODES,
        "fridge": APPLIANCE_GE_REFRIGERATOR_CODES,
    },
    "bosch": {
        "dishwasher": APPLIANCE_BOSCH_DISHWASHER_CODES,
    },
    "honeywell": {
        "thermostat": HONEYWELL_THERMOSTAT_CODES,
    },
    "emerson": {
        "thermostat": EMERSON_THERMOSTAT_CODES,
        "controller": EMERSON_THERMOSTAT_CODES,
    },
    "york": {
        "furnace": YORK_FURNACE_CODES,
    },
    "takagi": {
        "tankless": TAKAGI_TANKLESS_CODES,
        "water heater": TAKAGI_TANKLESS_CODES,
    },
    "lochinvar": {
        "boiler": LOCHINVAR_BOILER_CODES,
        "tankless": LOCHINVAR_TANKLESS_CODES,
        "water heater": LOCHINVAR_TANKLESS_CODES,
    },
    "midea": {
        "mini split": MIDEA_MINI_SPLIT_CODES,
        "minisplit": MIDEA_MINI_SPLIT_CODES,
        "air conditioner": MIDEA_MINI_SPLIT_CODES,
        "heat pump": MIDEA_MINI_SPLIT_CODES,
    },
    "gree": {
        "mini split": GREE_MINI_SPLIT_CODES,
        "minisplit": GREE_MINI_SPLIT_CODES,
        "air conditioner": GREE_MINI_SPLIT_CODES,
        "heat pump": GREE_MINI_SPLIT_CODES,
    },
    "cooper_hunter": {
        "mini split": COOPER_HUNTER_MINI_SPLIT_CODES,
        "minisplit": COOPER_HUNTER_MINI_SPLIT_CODES,
        "air conditioner": COOPER_HUNTER_MINI_SPLIT_CODES,
        "heat pump": COOPER_HUNTER_MINI_SPLIT_CODES,
    },
    "haier": {
        "mini split": HAIER_MINI_SPLIT_CODES,
        "minisplit": HAIER_MINI_SPLIT_CODES,
        "air conditioner": HAIER_MINI_SPLIT_CODES,
        "heat pump": HAIER_MINI_SPLIT_CODES,
    },
    "buderus": {
        "boiler": BUDERUS_BOILER_CODES,
    },
    "viessmann": {
        "boiler": VIESSMANN_BOILER_CODES,
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
    "combi": "boiler",
    "combi boiler": "boiler",
    "air handler": "air handler",
    "washer": "washer",
    "washing machine": "washer",
    "clothes washer": "washer",
    "dryer": "dryer",
    "clothes dryer": "dryer",
    "refrigerator": "refrigerator",
    "fridge": "refrigerator",
    "freezer": "refrigerator",
    "dishwasher": "dishwasher",
    "dish washer": "dishwasher",
    "oven": "oven",
    "range": "oven",
    "stove": "oven",
}

# Patterns to extract error codes from natural language queries
# Order matters — more specific patterns come first to avoid partial matches.
_CODE_PATTERNS = [
    # LG fridge "ERXX" codes — pre-normalized from "Er IF" → "ERIF", etc.
    re.compile(r"\b(ER[A-Z]{2})\b"),
    # Whirlpool compound codes — "F0E2", "F5E1", "F8E3", "F1E1"
    re.compile(r"\b([A-Za-z]\d[A-Za-z]\d)\b"),
    # Two-letter prefix + digits — "CH01", "CH67" (LG mini-split), "CF0" (Samsung oven)
    re.compile(r"\b([A-Za-z]{2}\d{1,2})\b"),
    # Digit + letter codes — "1E", "5E", "4E", "9E1", "84C", "39C" (Samsung washer/fridge)
    # Must come BEFORE general "error code N" pattern to capture the trailing letter(s)
    re.compile(r"\b(\d{1,2}[A-Za-z]\d?)\b"),
    # "error code 11", "fault code E228", "code 34"
    re.compile(r"(?:error|fault|diagnostic|status)\s*(?:code)?\s*#?\s*([A-Za-z]?\d+)", re.I),
    # "E228", "E6", "U4", "d80", "D95" (letter + number codes, case insensitive)
    re.compile(r"\b([A-Za-z]\d{1,3})\b"),
    # Letter + digit + letter codes — "H2O", "E0A" (GE dishwasher, Samsung oven)
    re.compile(r"\b([A-Za-z]\d[A-Za-z])\b"),
    # 2-3 letter text codes — "SUD", "PRS" preceded by keyword
    re.compile(r"(?:code|error|fault)\s+([A-Za-z]{2,3})\b", re.I),
    # "blinking 3 times", "3 blinks", "flashing 3", "3 flashes"
    re.compile(r"(?:blink(?:ing|s)?|flash(?:ing|es)?)\s*(\d{1,2})\s*(?:times?)?", re.I),
    re.compile(r"(\d{1,2})\s*(?:blinks?|flash(?:es)?|times?)", re.I),
    # "code 34", "code E228", "code AH"
    re.compile(r"code\s+([A-Za-z]?\d+)", re.I),
    # "error AH", "code EA", "fault EE" (two-letter codes preceded by keyword)
    re.compile(r"(?:code|error|fault)\s+([A-Z]{2})\b", re.I),
    # "AH error", "EA fault", "PA code" (two-letter codes followed by keyword)
    re.compile(r"\b([A-Z]{2})\s+(?:error|fault|code)", re.I),
    # Letter + letter + digit codes — "LE1", "LC1", "HE1", "HE2" (Samsung/LG appliance codes)
    re.compile(r"\b([A-Za-z]{2}\d)\b"),
    # "AH", "EA", "EE", "SUD", "PRS" etc. (2-3 letter codes at end of query string)
    # Only matches at end of string to avoid matching brand abbreviations like "AO" from "AO Smith"
    re.compile(r"\b([A-Z]{2,3})\s*$", re.I),
    # Just a number in context like "rheem 3" or "carrier 34"
    re.compile(r"(\d{1,3})$"),
]


def _extract_brand(text: str) -> str | None:
    """Try to find a brand name in the query text."""
    text_lower = text.lower()
    for alias, canonical in sorted(BRAND_ALIASES.items(), key=lambda x: -len(x[0])):
        if alias in text_lower:
            return canonical

    # Fallback: STT transcribes "Trane" as "train" (standalone word).
    # Only match if the query also contains error/code/furnace context words.
    if re.search(r"\btrain\b", text_lower):
        _trade_context = {"error", "code", "blink", "fault", "furnace", "ac", "unit",
                          "heat", "cool", "hvac", "flash", "light", "blinking", "pump"}
        if any(w in text_lower for w in _trade_context):
            return "trane"

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
    # Normalize hyphens in codes like "E-08" → "E08", "C-F0" → "CF0"
    normalized = re.sub(r"\b([A-Za-z])-(\d)", r"\1\2", normalized)
    # Normalize "Er IF" / "er ff" → "ERIF" / "ERFF" (LG fridge codes)
    normalized = re.sub(r"\b[Ee][Rr]\s+([A-Za-z]{2})\b", lambda m: "ER" + m.group(1).upper(), normalized)
    for pattern in _CODE_PATTERNS:
        match = pattern.search(normalized)
        if match:
            # If the pattern has 2 groups (e.g., hyphenated codes), combine them
            if match.lastindex and match.lastindex >= 2:
                raw = match.group(1) + match.group(2)
            else:
                raw = match.group(1)
            return raw.upper().lstrip("0") or "0"  # Normalize: strip leading zeros
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
