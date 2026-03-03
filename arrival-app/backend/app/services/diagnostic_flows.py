"""
Diagnostic flow lookup — instant troubleshooting guides for common field scenarios.
Works like error_codes.py but matches symptom descriptions instead of error codes.

Usage:
    from app.services.diagnostic_flows import lookup_diagnostic_flow, format_diagnostic_context
    result = lookup_diagnostic_flow("no heat gas furnace")
    if result:
        context = format_diagnostic_context(result)
        # Inject into Claude prompt as system_prompt_prefix
"""

import re
import logging

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Diagnostic Flow Database
# Each flow is a complete troubleshooting sequence a veteran tech would follow.
# Ordered by likelihood — most common causes first.
# ---------------------------------------------------------------------------

DIAGNOSTIC_FLOWS = {
    "no_heat_gas_furnace": {
        "title": "No Heat — Gas Furnace",
        "symptoms": ["no heat", "furnace not heating", "furnace won't start", "furnace not working", "no warm air", "cold air from vents", "furnace not firing", "furnace not igniting", "furnace won't kick on"],
        "equipment": ["furnace", "gas furnace", "heater"],
        "flow": """## No Heat — Gas Furnace Diagnostic Flow

**Step 1: Check thermostat**
- Set to HEAT mode, 5°F above room temp
- Check for 24V between R and W at the furnace control board
- If no 24V: thermostat issue, dead batteries, or broken wire
- If 24V present: proceed to step 2

**Step 2: Check the filter**
- A plugged filter can cause the limit switch to trip before the house heats up
- If the filter is black, replace it and reset power

**Step 3: Check the inducer motor**
- Listen — should start within 30 seconds of a heat call
- If inducer doesn't start: check for 120V at inducer connector. If voltage present, motor is dead. If no voltage, board isn't sending the signal — could be board failure or safety interlock
- If inducer starts but furnace doesn't proceed: pressure switch issue (see step 4)

**Step 4: Check pressure switch**
- With inducer running, check if pressure switch closes (continuity across switch terminals)
- If switch doesn't close: plugged condensate drain (most common on 90%+ furnaces), blocked flue/intake, weak inducer, cracked hose, or bad switch
- Check condensate drain first — blow out with compressed air or shop vac

**Step 5: Check igniter**
- Should glow orange/white within 30 seconds of pressure switch closing
- If no glow: check for 120V at igniter connector. If voltage but no glow, igniter is cracked — replace it
- Silicon carbide igniters: 40-200 ohms. Silicon nitride: 11-17 ohms

**Step 6: Check flame sensor**
- If igniter glows and gas lights but flame goes out within 4-7 seconds: dirty flame sensor
- Pull the sensor, clean with fine emery cloth or steel wool (NOT sandpaper)
- Should read >1.0 µA (ideally 2-5 µA) when in flame
- If clean sensor still can't hold flame: check ground wire, check gas pressure

**Step 7: Check gas valve**
- With 24V at the gas valve and igniter glowing, gas should flow
- If no gas: valve is stuck or failed. Check inlet gas pressure (7" WC for NG, 11" WC for LP)
- If gas flows but won't stay lit after sensor proves: go back to step 6

**Common causes ranked by frequency:**
1. Dirty flame sensor (30% of no-heat calls)
2. Dirty/plugged filter (15%)
3. Failed igniter (12%)
4. Plugged condensate drain — 90%+ furnaces (10%)
5. Bad capacitor on inducer or blower (8%)
6. Thermostat issue (7%)
7. Gas supply off or low pressure (5%)
8. Failed control board (5%)
9. Cracked heat exchanger tripping limit (3%)
10. Other (5%)""",
    },

    "no_cool_ac": {
        "title": "No Cool — Air Conditioning",
        "symptoms": ["no cool", "ac not cooling", "air conditioner not working", "ac won't start", "no cold air", "warm air from vents", "ac not blowing cold", "ac running but not cooling", "compressor not starting", "outside unit not running"],
        "equipment": ["air conditioner", "ac", "a/c", "central air", "condenser"],
        "flow": """## No Cool — AC Diagnostic Flow

**Step 1: Check thermostat**
- Set to COOL mode, 5°F below room temp
- Verify fan is on AUTO (not OFF)
- Check for 24V between R and Y at the air handler

**Step 2: Check the outdoor unit**
- Is the disconnect on? Is the breaker tripped?
- Is the condenser fan running? Is the compressor humming?
- If NOTHING running: check for 24V at the contactor coil. No 24V = thermostat or wiring issue. 24V but contactor doesn't pull in = bad contactor
- If fan runs but compressor doesn't: likely bad capacitor or compressor

**Step 3: Check the capacitor**
- #1 cause of "no cool" on units 5-15 years old
- Visually inspect: swollen top = bad. Leaking oil = bad
- Measure with meter in µF mode. Should be within 10% of rated value
- Dual run cap: one side for compressor, one for fan. Replace the whole cap, not half

**Step 4: Check the contactor**
- Pitted or burnt contacts = voltage drop = weak operation
- Check voltage on LINE side (should be 240V ±10%)
- Check voltage on LOAD side with contactor pulled in (should match line side)
- If big voltage drop across contactor: replace it

**Step 5: Indoor blower**
- If outdoor unit is running but no cold air inside: is the blower running?
- Check blower capacitor, check for ice on the evaporator coil (see "AC Freezing Up" flow)
- If blower runs but airflow is weak: dirty filter, dirty blower wheel, or ductwork issue

**Step 6: Refrigerant charge**
- If system runs but doesn't cool well: check superheat and subcooling
- Low charge symptoms: suction line not cold, low suction pressure, high superheat
- If low: find the leak first. Don't just add refrigerant — that's a bandaid

**Step 7: Compressor**
- If capacitor is good but compressor won't start: check windings (C-R, C-S, R-S)
- Grounded compressor: any winding to ground reads <1MΩ = replace
- Open winding: infinite reading between two terminals = replace
- Shorted winding: R-S doesn't equal C-R + C-S = replace
- If windings check OK: could be internal overload tripped (wait 2hrs to reset)

**Common causes ranked by frequency:**
1. Bad capacitor (25% of no-cool calls)
2. Dirty filter/evaporator (15%)
3. Thermostat/wiring issue (10%)
4. Contactor failure (10%)
5. Low refrigerant (10%)
6. Tripped breaker/blown fuse (8%)
7. Compressor failure (7%)
8. Frozen evaporator coil (5%)
9. Bad blower motor (5%)
10. Control board issue (5%)""",
    },

    "no_hot_water_gas": {
        "title": "No Hot Water — Gas Water Heater",
        "symptoms": ["no hot water gas", "water heater not heating", "gas water heater not working", "pilot won't light", "pilot keeps going out", "water heater pilot out", "no hot water tank"],
        "equipment": ["water heater", "gas water heater", "tank"],
        "flow": """## No Hot Water — Gas Water Heater Diagnostic Flow

**Step 1: Check the pilot light**
- Look through the viewport at the bottom of the tank
- If pilot is out: try relighting per instructions on the label
- If pilot won't light: hold the knob down longer (60 seconds), check gas supply, check if piezo igniter clicks
- If pilot lights but goes out when you release: thermopile/thermocouple issue (step 2)

**Step 2: Check thermopile/thermocouple**
- Older units use a thermocouple (single rod). Newer use a thermopile (two wires)
- Thermocouple test: disconnect from gas valve, measure millivolts with pilot lit. Should be >20mV. Replace if under 15mV
- Thermopile test: disconnect leads from gas valve, measure open-circuit millivolts. Should be >400mV. Under load (connected) should be >250mV
- Also check: is the pilot flame actually touching the thermopile? Dirty pilot orifice can cause a weak flame that doesn't heat the sensor

**Step 3: Check gas control valve**
- If thermopile output is good but valve won't open: gas control valve has failed
- AO Smith/Bradford White use Honeywell or Robertshaw valves
- Don't try to repair — replace the entire gas control valve
- On newer electronic models: check the status LED blinks for a specific error code

**Step 4: Check gas supply**
- Is the gas shutoff valve open (handle parallel to pipe)?
- Is the gas meter running? Other gas appliances working?
- Check manifold pressure: should be 3.5-4" WC for natural gas

**Step 5: Check for sediment (if water is warm but not hot enough)**
- Tank older than 5 years likely has sediment buildup
- Symptoms: rumbling/popping noise, longer recovery time, hot water runs out fast
- Drain 2-3 gallons from the drain valve. If water is rusty/sandy: full flush needed
- Connect hose, open drain valve, open T&P relief to break vacuum

**Common causes ranked by frequency:**
1. Failed thermopile/thermocouple (35%)
2. Pilot orifice dirty/clogged (15%)
3. Gas control valve failure (15%)
4. Sediment buildup (10%)
5. Gas supply issue (8%)
6. Dip tube broken (5%) — cold water shorts to hot outlet
7. Status LED error code (5%)
8. Flue blockage (4%)
9. Other (3%)""",
    },

    "no_hot_water_electric": {
        "title": "No Hot Water — Electric Water Heater",
        "symptoms": ["no hot water electric", "electric water heater not working", "electric water heater not heating", "water heater tripping breaker"],
        "equipment": ["electric water heater", "water heater"],
        "flow": """## No Hot Water — Electric Water Heater Diagnostic Flow

**Step 1: Check power**
- Check the breaker — electric water heaters are typically on a 30A double-pole breaker
- If breaker is tripped: reset once. If trips again immediately, there's a short (step 5)
- Check for 240V at the top of the water heater (disconnect cover plate)
- SAFETY: Turn off breaker before removing cover plates. Use a non-contact voltage tester

**Step 2: Check the high limit reset button (ECO)**
- Behind the upper access panel, under the insulation
- Press the red reset button. If it clicks: the high limit tripped
- Turn power on. If it heats now, monitor it. If it trips again: bad thermostat (stuck on) or shorted element
- The reset button trips at ~170°F — this is a safety device

**Step 3: Check upper thermostat and element**
- Upper element heats first, then lower takes over
- If NO hot water at all: upper element or thermostat is likely the problem
- Test upper element: disconnect wires, measure resistance. Should be 10-16 ohms for a 4500W element at 240V
- Infinite reading = open element (broken). Very low reading = shorted element
- Check for continuity to ground (element to tank). Any continuity = grounded element, must replace

**Step 4: Check lower thermostat and element**
- If you get SOME hot water but it runs out fast: lower element is likely dead
- Test lower element same as upper
- A tank with a dead lower element will produce 1/3 the normal hot water (only the upper portion heats)

**Step 5: Shorted element (breaker keeps tripping)**
- Disconnect both element wires
- Measure element resistance: should be 10-16 ohms
- Measure element to ground (element terminal to tank bolt): should be infinite
- If any reading to ground: element is grounded and will trip the breaker. Replace it
- Check BOTH elements — the grounded one may not be the obvious suspect

**Step 6: Check wiring**
- Verify wire connections are tight at thermostats and elements
- Burned or melted wire nuts indicate a loose connection that overheated
- Check the wire gauge: 10 AWG for 30A circuit (standard residential)

**Common causes ranked by frequency:**
1. Tripped high limit reset button (25%)
2. Failed heating element — upper (20%)
3. Failed heating element — lower (15%)
4. Bad thermostat — upper (12%)
5. Bad thermostat — lower (8%)
6. Tripped/off breaker (8%)
7. Grounded element tripping breaker (5%)
8. Loose wiring connections (4%)
9. Sediment covering element (3%)""",
    },

    "furnace_short_cycling": {
        "title": "Furnace Short Cycling",
        "symptoms": ["short cycling", "furnace turns on and off", "furnace cycles too fast", "furnace runs for a few minutes then shuts off", "furnace starts then stops", "furnace keeps shutting off"],
        "equipment": ["furnace", "gas furnace", "heater"],
        "flow": """## Furnace Short Cycling Diagnostic Flow

**Step 1: Check the filter**
- A dirty filter restricts airflow → heat exchanger overheats → limit switch trips → burner shuts off → cools down → starts again
- This is the #1 cause of short cycling. Replace the filter first before diagnosing anything else
- Check with the furnace door open — if it stops short cycling, the filter or airflow is the issue

**Step 2: Check all supply registers and returns**
- Closed or blocked registers = restricted airflow = same effect as dirty filter
- Common in finished basements where people close vents
- Need at least 80% of registers open for proper airflow

**Step 3: Check the flame sensor**
- Dirty flame sensor causes: ignites → burns for 3-7 seconds → flame sensor can't detect → shuts off gas → retries
- This looks like short cycling but it's actually ignition failure on repeat
- Clean the flame sensor with emery cloth. Check µA reading (>1.0 µA)

**Step 4: Check the high limit switch**
- If the furnace runs for 2-5 minutes then shuts off: likely hitting the high limit
- With a good filter and open registers, measure temperature rise across the heat exchanger
- Should be within the range on the furnace nameplate (usually 35-65°F rise)
- If rise is too high: blower too slow (wrong speed tap, bad capacitor), undersized ductwork

**Step 5: Check the blower motor**
- Is it actually running at full speed?
- On PSC motors: check the capacitor. Weak cap = slow blower = overheating
- On ECM motors: check for error codes on the motor module
- Dirty blower wheel reduces airflow significantly — clean it if it's caked with dust

**Step 6: Check ductwork**
- Measure static pressure at the furnace: should be under 0.5" WC total (supply + return)
- High static = restricted ductwork, too many elbows, undersized ducts
- If this is a replacement furnace in old ductwork, it may be oversized for the existing ducts

**Step 7: Check gas pressure**
- Low gas pressure can cause weak flame → flame sensor drops out → short cycle
- Check manifold pressure: NG should be 3.5" WC (varies by manufacturer — check the nameplate)
- LP should be 10-11" WC

**Common causes ranked by frequency:**
1. Dirty filter (30%)
2. Dirty flame sensor (20%)
3. High limit tripping due to airflow restriction (15%)
4. Bad blower capacitor (10%)
5. Oversized furnace for ductwork (5%)
6. Closed registers (5%)
7. Gas pressure issue (5%)
8. Cracked heat exchanger (3%)
9. Bad control board (3%)
10. Thermostat location issue (hot/cold spot) (4%)""",
    },

    "ac_freezing_up": {
        "title": "AC Freezing Up / Icing",
        "symptoms": ["ac freezing", "ice on ac", "frozen coil", "evaporator icing", "ac iced up", "ice on the line", "suction line frozen", "ac froze up", "frozen evaporator"],
        "equipment": ["air conditioner", "ac", "a/c", "heat pump", "evaporator"],
        "flow": """## AC Freezing Up Diagnostic Flow

**FIRST: Turn the system to FAN ONLY for 1-2 hours to thaw completely. Do NOT scrape ice off the coil — you'll damage the fins.**

**Step 1: Check the filter**
- Dirty filter = restricted airflow over evaporator = coil drops below 32°F = ice forms
- This is the #1 cause. If the filter is dirty, replace it, thaw the coil, and run it
- If it doesn't freeze again, you're done

**Step 2: Check airflow**
- All registers open? Return grilles clear?
- Is the blower running at the correct speed? Check blower motor capacitor
- Is the blower wheel clean? A caked wheel moves significantly less air
- Measure static pressure: should be under 0.5" WC total
- Evaporator coil dirty? If you can see it, look for dirt buildup on the A-side (air entering side)

**Step 3: Check refrigerant charge**
- Low refrigerant = low suction pressure = coil temp drops below freezing
- After full thaw, check superheat (fixed orifice) or subcooling (TXV)
- Fixed orifice target: 10-15°F superheat. TXV target: 8-12°F subcooling
- If undercharged: find the leak, fix it, then recharge. Don't just add refrigerant

**Step 4: Check the metering device**
- On fixed orifice (piston/cap tube): could be partially restricted, causing low evaporator pressure
- On TXV: sensing bulb may have lost charge, or TXV may be stuck. Check superheat — if it's very high (>25°F) with a TXV, the valve may be restricted or stuck closed

**Step 5: Check for blower issues**
- If blower runs intermittently or at low speed, the coil freezes during low-flow periods
- ECM motor fault codes, PSC motor capacitor check
- On some systems, the fan relay on the board can intermittently drop out

**Step 6: Check outdoor ambient conditions**
- AC running below 60°F outdoor temp can cause freezing (especially heat pumps in cool mode)
- If this is a heat pump in heat mode, see defrost board diagnostics instead

**Common causes ranked by frequency:**
1. Dirty filter (30%)
2. Low refrigerant charge (25%)
3. Dirty evaporator coil (10%)
4. Blower motor issue / bad capacitor (10%)
5. Restricted metering device (8%)
6. Closed/blocked registers (7%)
7. Running at low ambient temp (5%)
8. Dirty blower wheel (5%)""",
    },

    "weak_airflow": {
        "title": "Weak Airflow from Vents",
        "symptoms": ["weak airflow", "low airflow", "not enough air", "vents blowing weak", "poor airflow", "hardly any air coming out", "reduced airflow"],
        "equipment": ["furnace", "air conditioner", "ac", "air handler", "blower"],
        "flow": """## Weak Airflow Diagnostic Flow

**Step 1: Check the filter**
- Always check the filter first. Always.
- A dirty filter is the #1 cause of weak airflow. Period.
- Some systems have multiple filters (return in hallway AND at the air handler) — check all of them

**Step 2: Check the blower wheel**
- Remove the blower assembly and inspect the wheel
- A wheel caked with dust/debris moves 30-50% less air than a clean one
- Clean with a brush and shop vac. This is one of the most overlooked maintenance items

**Step 3: Check blower motor and capacitor**
- Is the motor running at full speed?
- PSC motors: check the run capacitor. A weak cap means a slow motor
- ECM/variable speed motors: check for error codes on the motor module. ECM motors adjust speed to maintain airflow — if they can't keep up, there's a big restriction
- Listen for bearing noise — a motor with bad bearings slows down

**Step 4: Check blower speed setting**
- On PSC motors: verify the correct speed tap is connected (usually HIGH for cooling, MED-HIGH or MED for heating)
- Speed taps are colored wires on the motor: typically Black=high, Blue=med-high, Yellow=med, Red=low
- If a new blower motor was installed, the speed taps may have been connected wrong

**Step 5: Measure static pressure**
- Connect a manometer to the supply and return plenum test ports
- Total external static pressure (TESP) should be under 0.5" WC for most residential systems
- If supply is high: ductwork too small, too many fittings, or dampers closed
- If return is high: filter, return grille too small, or return duct undersized

**Step 6: Check ductwork**
- Disconnected or crushed flex duct in attic/crawlspace is very common
- Look for kinks, sags, or runs that are too long
- Check all dampers in the main trunk — sometimes a damper gets closed accidentally

**Step 7: Check the evaporator coil**
- A dirty evaporator coil on the air-entering side creates massive pressure drop
- You may need to remove the coil access panel to see it
- If it's dirty, clean it with coil cleaner — but be careful about draining the cleaner properly

**Common causes ranked by frequency:**
1. Dirty filter (35%)
2. Dirty blower wheel (15%)
3. Bad blower capacitor (12%)
4. Disconnected/damaged ductwork (10%)
5. Dirty evaporator coil (8%)
6. Wrong blower speed setting (5%)
7. Failing blower motor (5%)
8. Closed dampers (5%)
9. Undersized return ductwork (3%)
10. Other (2%)""",
    },

    "breaker_keeps_tripping": {
        "title": "Breaker Keeps Tripping",
        "symptoms": ["breaker keeps tripping", "breaker trips", "tripping breaker", "circuit breaker keeps going off", "keeps tripping the breaker", "breaker won't stay on"],
        "equipment": ["electrical", "panel", "breaker", "circuit"],
        "flow": """## Breaker Keeps Tripping Diagnostic Flow

**SAFETY: If a breaker trips, it's doing its job — protecting the wire. Never upsize a breaker without upsizing the wire.**

**Step 1: Identify WHAT is on the circuit**
- Is it the AC/heat pump breaker? Furnace breaker? Water heater breaker? General circuit?
- Dedicated equipment circuits are easier to diagnose than general circuits with multiple loads

**Step 2: For AC/heat pump breakers:**
- Check the compressor amp draw with a clamp meter. Compare to nameplate RLA (rated load amps)
- If amps are high (near or above LRA): compressor is struggling. Check capacitor first
- Bad capacitor = motor draws excessive current trying to start = breaker trips
- Grounded compressor: check windings to ground with megohmmeter. Any reading < 1MΩ = bad compressor
- Dirty condenser coil = high head pressure = high amp draw = breaker trips
- If breaker trips IMMEDIATELY on reset: likely a direct short. Check wiring in disconnect box, contactor, and compressor terminal connections

**Step 3: For electric water heater breakers:**
- Usually a 30A double-pole breaker, 10 AWG wire
- Most common cause: grounded heating element (element touching tank internally)
- Disconnect both elements, test each one for continuity to ground
- Any reading to ground = replace that element

**Step 4: For general circuits (15A or 20A):**
- Count the loads. Too many devices on one circuit = overload
- Unplug everything, reset breaker. Add devices one at a time to find the overload
- If breaker trips with nothing plugged in: wiring fault (pinched wire, nail through wire, bad outlet)
- Check all outlets and switches on the circuit for signs of heat damage (discolored, melted)

**Step 5: Is the breaker itself bad?**
- Breakers can weaken over time, especially if they've tripped many times
- If the circuit checks out clean but the breaker still trips: replace the breaker
- Use same brand/type: don't mix QO/Homeline, don't put Eaton in a Square D panel
- AFCI breakers can trip from arc-like signatures that aren't actual arcs (vacuum cleaners, dimmer switches, treadmills). Check for nuisance tripping before replacing expensive AFCI breakers

**Step 6: Check wire size**
- 15A breaker → 14 AWG minimum
- 20A breaker → 12 AWG minimum
- 30A breaker → 10 AWG minimum
- If someone put a 20A breaker on 14 AWG wire, that's a code violation and fire hazard — fix it

**Common causes ranked by frequency:**
1. Overloaded circuit — too many loads (25%)
2. Bad capacitor on AC/heat pump (15%)
3. Grounded element in water heater (12%)
4. Short in wiring or device (10%)
5. Failing/grounded compressor (8%)
6. Dirty condenser coil causing high amps (7%)
7. Bad/weak breaker (7%)
8. AFCI nuisance tripping (5%)
9. Loose connections causing heat (5%)
10. Wrong breaker size for wire gauge (6%)""",
    },

    "not_enough_hot_water": {
        "title": "Not Enough Hot Water / Runs Out Fast",
        "symptoms": ["not enough hot water", "hot water runs out", "runs out of hot water", "water not hot enough", "lukewarm water", "water heater not hot enough", "hot water doesn't last"],
        "equipment": ["water heater", "tank", "tankless"],
        "flow": """## Not Enough Hot Water Diagnostic Flow

**Step 1: Check the thermostat setting**
- Gas: dial on the gas valve. Should be at "Hot" or ~120°F for residential
- Electric: check both upper AND lower thermostats. Both should be set to 120°F
- A common mistake: upper thermostat is fine but lower is set too low (or vice versa)
- Measure actual water temp at the faucet — use a thermometer, don't guess

**Step 2: Check the dip tube (tank-style)**
- The dip tube sends cold incoming water to the BOTTOM of the tank
- If it's cracked or broken, cold water mixes with hot at the top → lukewarm water
- Most common on water heaters from late 1990s (defective polypropylene dip tubes)
- Check by removing the cold inlet nipple and pulling out the dip tube. If it's short, crumbled, or missing: replace it

**Step 3: Check for sediment buildup (gas tank)**
- Sediment insulates the bottom of the tank from the burner
- Symptoms: popping/rumbling noise, slow recovery, hot water runs out fast
- Drain 2-3 gallons from the drain valve. If water is rusty/gritty: needs a full flush
- Severe sediment on tanks >10 years old often means it's replacement time

**Step 4: For electric water heaters — check both elements**
- If the lower element is dead, only the upper 1/3 of the tank heats
- This gives you a few minutes of hot water, then lukewarm
- Test both elements: disconnect wires, measure resistance (10-16 ohms for 4500W at 240V)
- Also verify both thermostats are sending power to the elements

**Step 5: For tankless water heaters — check flow rate and sizing**
- Tankless heaters are rated by temperature rise at a given flow rate
- Running too many fixtures at once exceeds the unit's capacity
- Calculate: GPM needed × temperature rise needed = BTU requirement
- Descale the heat exchanger if it's been >1 year since last maintenance — scale reduces efficiency and output

**Step 6: Check for crossover (hot water going cold)**
- A bad mixing valve or single-handle faucet cartridge can let cold water cross into the hot line
- Test: turn off the water heater cold supply. Open a hot faucet. If water still flows, there's a crossover somewhere
- Most common culprit: recirculation systems with bad check valves, or single-handle shower valves with worn cartridges

**Step 7: Is the tank undersized?**
- 40-gallon gas: good for 2-3 people
- 50-gallon gas: good for 3-4 people
- Electric tanks have lower first-hour rating than gas — a 50-gallon electric may only deliver 60 gallons first hour vs 80+ for gas
- If the household has grown or usage patterns changed, the tank may just be too small

**Common causes ranked by frequency:**
1. Thermostat set too low (20%)
2. Sediment buildup (15%)
3. Failed lower element — electric (15%)
4. Broken dip tube (10%)
5. Crossover from mixing valve/faucet (8%)
6. Undersized unit for demand (8%)
7. Scale buildup — tankless (7%)
8. Lower thermostat failure — electric (7%)
9. Gas supply issue — low BTU input (5%)
10. Other (5%)""",
    },

    "thermostat_not_responding": {
        "title": "Thermostat Not Responding / Blank Screen",
        "symptoms": ["thermostat not working", "blank thermostat", "thermostat screen blank", "thermostat dead", "thermostat won't turn on", "thermostat not responding", "thermostat display off"],
        "equipment": ["thermostat"],
        "flow": """## Thermostat Not Responding Diagnostic Flow

**Step 1: Check power source**
- Battery-powered thermostats: replace batteries first. Use name-brand AA or AAA lithiums for best life
- 24V powered (common wire "C"): check for 24V between R and C at the thermostat base
- If the thermostat is powered through the system (no C wire): it steals power through the R wire when the system runs. If the system is off, the thermostat may die. This is a known issue with older "no C wire" installations of smart thermostats

**Step 2: Check the transformer**
- At the furnace/air handler, measure 24V between R and C on the control board
- No 24V: check the transformer. Measure 240V in (or 120V in). If input is good but no 24V output: transformer is blown
- Common cause of blown transformer: shorted thermostat wire (especially during new installs or drywall work)
- Check the 3A or 5A fuse on the board — many boards have a replaceable fuse

**Step 3: Check the fuse on the control board**
- Many furnace boards have a 3A automotive-style fuse on the 24V circuit
- If blown: find the short BEFORE replacing the fuse. Common shorts: wire pinched by furnace door, thermostat wires touching in the wall, bad contactor coil on outdoor unit
- Replace the fuse. If it blows again immediately: disconnect the thermostat wires at the board and try again. If fuse holds: the short is in the thermostat wiring or thermostat itself

**Step 4: Check wiring connections**
- Pull the thermostat off the wall. Check for loose wires at the terminals
- Common on smart thermostat installs: the C wire wasn't connected, or wires were put on wrong terminals
- Standard wiring: R=power, G=fan, Y=cool, W=heat, C=common, O/B=heat pump reversing valve
- If wires are in the wrong terminals, the thermostat may short and blow the fuse

**Step 5: Smart thermostat specific issues**
- Nest/Ecobee/Honeywell Home: check WiFi connection — some features depend on WiFi
- Nest "low battery" or blinking screen: usually needs a C wire added (it can't steal enough power)
- Ecobee: uses a Power Extender Kit (PEK) if no C wire — make sure the PEK is installed correctly at the furnace

**Step 6: Check for wiring damage**
- If a new thermostat was recently installed: check that no wires were cut too short or nicked during installation
- Older homes: thermostat wire can corrode, especially in exterior walls
- Use a multimeter to check continuity on each wire from thermostat to furnace

**Common causes ranked by frequency:**
1. Dead batteries (25%)
2. Blown fuse on control board (20%)
3. Bad/failed transformer (12%)
4. Loose wire connections (10%)
5. Smart thermostat needs C wire (10%)
6. Wiring damage or short (8%)
7. Thermostat itself failed (5%)
8. Power outage / tripped breaker (5%)
9. Wrong wiring on installation (5%)""",
    },
}


# ---------------------------------------------------------------------------
# Symptom matching patterns
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Normalize text for matching."""
    return re.sub(r"[^a-z0-9\s]", "", text.lower()).strip()


def lookup_diagnostic_flow(query: str) -> dict | None:
    """
    Match a user query to a diagnostic flow based on symptom keywords.

    Returns:
        dict with keys: id, title, flow (the full diagnostic text)
        None if no match found.

    Examples:
        lookup_diagnostic_flow("my furnace won't start, no heat")
        lookup_diagnostic_flow("AC is freezing up")
        lookup_diagnostic_flow("breaker keeps tripping on my AC")
    """
    query_lower = _normalize(query)

    if not query_lower or len(query_lower) < 5:
        return None

    best_match = None
    best_score = 0

    for flow_id, flow_data in DIAGNOSTIC_FLOWS.items():
        score = 0

        # Check symptom matches
        for symptom in flow_data["symptoms"]:
            symptom_norm = _normalize(symptom)
            if symptom_norm in query_lower:
                # Longer symptom matches are more specific = higher score
                score += len(symptom_norm)
            else:
                # Check individual words in the symptom
                words = symptom_norm.split()
                matching_words = sum(1 for w in words if w in query_lower and len(w) > 2)
                if matching_words >= 2:
                    score += matching_words * 3

        # Check equipment matches (bonus points)
        for equip in flow_data.get("equipment", []):
            if _normalize(equip) in query_lower:
                score += 5

        if score > best_score:
            best_score = score
            best_match = (flow_id, flow_data)

    # Require a minimum score to avoid false matches
    if best_match and best_score >= 8:
        flow_id, flow_data = best_match
        return {
            "id": flow_id,
            "title": flow_data["title"],
            "flow": flow_data["flow"],
        }

    return None


def format_diagnostic_context(result: dict) -> str:
    """
    Format a diagnostic flow result as context to inject into the Claude prompt.
    """
    return f"""## Diagnostic Reference — {result['title']}

{result['flow']}

IMPORTANT: Use this diagnostic flow as your reference when answering. Walk the tech through the steps in order, starting from where they are in the process. If they mention they've already checked something, skip to the next step. Lead with the most common cause. Be specific and practical — tell them exactly what to check and what readings to expect."""
