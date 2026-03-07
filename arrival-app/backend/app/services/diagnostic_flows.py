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

    "mini_split_not_heating_cooling": {
        "title": "Mini-Split Not Heating/Cooling",
        "symptoms": ["mini split not heating", "mini split not cooling", "ductless not working", "mini split blowing warm air in cool mode", "mini split blowing cool air in heat mode"],
        "equipment": ["mini split", "mini-split", "ductless", "heat pump"],
        "flow": """## Mini-Split Not Heating/Cooling Diagnostic Flow

**Step 1: Check remote/thermostat settings**
- Verify the mode is correct — HEAT, COOL, or AUTO. A surprising number of callbacks are just wrong-mode selection
- Make sure the set temp makes sense: in COOL mode set temp must be BELOW room temp, in HEAT it must be ABOVE
- Check if a timer or sleep mode was accidentally set — that can shut the unit down on a schedule
- Replace remote batteries if the display is dim or unresponsive

**Step 2: Check for error codes on the indoor unit display**
- Most mini-splits blink an LED or show an alphanumeric code on the display panel when something is wrong
- Write down the exact blink pattern (e.g., 3 blinks, pause, 5 blinks) or error code (E1, P4, F6, etc.)
- Look up the code in the manufacturer's service manual — each brand has unique codes
- Common codes: E1/E6 = communication error, F3/P4 = pipe temp sensor, H1 = defrost mode (not a fault)

**Step 3: Check filters**
- Dirty filter is the #1 cause of poor performance on mini-splits — accounts for 35% of no-heat/no-cool calls
- Open the front panel (lifts up on most units), slide the filters out
- If they're gray/black with dust: wash them with warm water and mild soap, air dry completely before reinstalling
- Clogged filters cause the coil to ice up in cool mode and trigger overheat protection in heat mode

**Step 4: Check outdoor unit**
- Is the outdoor unit running? Go outside and listen/look
- If completely dead: check the breaker/disconnect. Check for error LEDs on the outdoor control board (remove the service panel)
- If the fan runs but the compressor doesn't: check the inverter board for fault codes, check compressor winding resistance
- If the compressor runs but cycles off quickly: likely a refrigerant or sensor issue

**Step 5: Check reversing valve (heat mode issues)**
- The reversing valve switches between heating and cooling. If it's stuck, you get cool air in heat mode (or vice versa)
- With the unit calling for heat: feel the large suction line at the outdoor unit — it should be warm/hot in heat mode
- If the suction line is cold in heat mode: reversing valve is stuck or the solenoid coil is bad
- Check for 12V DC or 24V (varies by brand) at the reversing valve solenoid coil. If voltage present but valve doesn't shift: valve is stuck. Try tapping it lightly or cycling the mode rapidly to unstick it

**Step 6: Check refrigerant charge**
- Connect gauges to the service ports on the outdoor unit
- Low charge symptoms: poor heating/cooling, long run times, ice on indoor coil in cool mode, ice on outdoor coil in heat mode
- Mini-splits use R-410A (most common) or R-32 (newer models). Check the nameplate
- Proper charge is verified by superheat and subcooling. Typical targets: 5-8°F superheat at the evaporator, 5-10°F subcooling at the condenser
- If low: find and fix the leak before recharging. Flare connections are the most common leak point on mini-splits

**Step 7: Check communication wiring between indoor and outdoor units**
- Mini-splits use 2-4 conductor communication cable between indoor and outdoor units
- A communication fault means the indoor unit can't tell the outdoor unit what to do
- Check for 24V or DC voltage on the signal wires (varies by brand)
- Look for damaged, pinched, or corroded wires — especially where they enter the wall or connect at terminals
- Loose terminal screws on either end cause intermittent faults that are maddening to chase — tighten all connections

**Common causes ranked by frequency:**
1. Dirty filters (35%)
2. Wrong mode/settings on remote (15%)
3. Communication error between units (10%)
4. Low refrigerant charge (10%)
5. Faulty outdoor inverter board (8%)
6. Bad reversing valve or solenoid (7%)
7. Sensor fault (pipe temp or room temp) (6%)
8. Outdoor unit not getting power (5%)
9. Stuck compressor (2%)
10. Other (2%)""",
    },

    "heat_pump_not_defrosting": {
        "title": "Heat Pump Not Defrosting",
        "symptoms": ["heat pump iced up", "heat pump frozen", "ice on heat pump", "outdoor unit covered in ice", "heat pump not defrosting", "frost on outdoor coil"],
        "equipment": ["heat pump", "mini split", "outdoor unit"],
        "flow": """## Heat Pump Not Defrosting Diagnostic Flow

**IMPORTANT: A thin layer of frost on a heat pump outdoor coil in heating mode is NORMAL. A thick, solid ice block that covers the entire coil is NOT normal and must be addressed.**

**Step 1: Understand the defrost cycle**
- Heat pumps extract heat from outdoor air. The outdoor coil runs below freezing, so moisture condenses and freezes on it — that's normal physics
- The defrost cycle reverses the refrigerant flow briefly (switches to cooling mode) to melt the ice off the outdoor coil
- During defrost: outdoor fan stops, you may see steam rising from the unit, and the indoor unit blows cool air for 2-10 minutes
- Defrost should initiate every 30-90 minutes depending on conditions and run for 2-10 minutes

**Step 2: Check the defrost control — timer vs demand**
- Older systems use a timed defrost board: initiates every 30, 60, or 90 minutes regardless of ice buildup
- Newer systems use demand defrost: uses temperature sensors and/or pressure to detect when ice is actually present
- Timer-based: check the defrost timer motor — if it's not advancing, defrost never initiates. Manually advance the timer to test
- Demand-based: check the defrost board for fault LEDs or diagnostic codes

**Step 3: Check the outdoor coil temperature sensor**
- Demand defrost systems rely on a thermistor mounted on the outdoor coil to detect frost conditions
- If the sensor reads incorrectly, the board never sees "frost temperature" and never initiates defrost
- Measure the sensor resistance and compare to the manufacturer's resistance-temperature chart
- Typical: 10kΩ at 77°F, increasing as temperature drops. A reading of 0Ω or infinite = bad sensor
- Check the sensor is properly mounted to the coil — if it's fallen off or shifted, readings will be wrong

**Step 4: Check the reversing valve solenoid**
- Defrost works by energizing (or de-energizing, depending on brand) the reversing valve to briefly switch to cooling mode
- Check for 24V at the reversing valve solenoid coil during a defrost call
- If voltage is present but the valve doesn't shift: solenoid coil may be bad (check coil resistance — typically 50-200 ohms), or the valve is mechanically stuck
- Listen for a "whoosh" sound when the valve shifts. No sound = valve isn't moving refrigerant

**Step 5: Check refrigerant charge**
- Low refrigerant charge causes the outdoor coil to run excessively cold → more ice → defrost can't keep up
- Low charge also means defrost cycles are less effective because there's less hot gas available to melt the ice
- Check suction pressure in heating mode. If it's significantly below normal, the system is probably low
- Find and fix the leak before recharging. A slow leak combined with poor defrost will destroy the outdoor coil over a season

**Step 6: Check airflow across outdoor coil**
- Debris, leaves, grass clippings, or a missing fan shroud can restrict airflow and promote excessive ice buildup
- Make sure there's at least 24 inches of clearance around the unit
- If the unit is in a corner or recess where cold air pools and airflow is blocked, ice formation is much worse
- Check the outdoor fan motor — if it's running slow (bad capacitor or bearing), airflow is reduced

**Step 7: Manual defrost procedure**
- If the coil is heavily iced, you need to defrost it manually before diagnosing further
- Switch the thermostat to EMERGENCY HEAT (this runs the backup heat strips only and shuts down the heat pump)
- Use a garden hose with lukewarm water to melt the ice. NEVER use a sharp tool to chip ice — you'll puncture the coil
- Once thawed, run the system in heat mode and watch for a defrost cycle. Time how long it runs before ice starts building again
- If ice returns within 1-2 hours and defrost never kicks in: the defrost control or sensor is the problem

**Common causes ranked by frequency:**
1. Failed defrost control board or timer (25%)
2. Bad outdoor coil temperature sensor (20%)
3. Stuck or failed reversing valve solenoid (15%)
4. Low refrigerant charge (15%)
5. Restricted outdoor airflow / dirty coil (8%)
6. Bad outdoor fan motor or capacitor (7%)
7. Wiring issue to defrost components (5%)
8. Defrost board relay contacts welded or burnt (5%)""",
    },

    "tankless_no_hot_water": {
        "title": "Tankless Water Heater No Hot Water",
        "symptoms": ["tankless not heating", "tankless no hot water", "on-demand not working", "tankless water heater cold water", "tankless won't ignite"],
        "equipment": ["tankless", "tankless water heater", "on-demand"],
        "flow": """## Tankless Water Heater No Hot Water Diagnostic Flow

**Step 1: Check the error code display**
- Every tankless worth servicing has a digital display or LED that shows error codes when something's wrong
- Write down the exact code — brand-specific, but common ones across manufacturers:
  - Rinnai: 11 = no ignition, 12 = flame failure, 14 = thermal fuse, LC = scale buildup
  - Navien: E003 = ignition failure, E012 = flame loss, E016 = overheating, E515 = flow sensor
  - Noritz: 11 = no ignition, 12 = flame out, 16 = overheating, 29 = condensate drain
- The error code tells you exactly where to start — don't skip this step

**Step 2: Check gas supply**
- Is the gas shutoff valve open? (Handle parallel to pipe = open, perpendicular = closed)
- Are other gas appliances in the house working?
- Tankless heaters need HIGH gas volume — typically 3/4" or 1" gas line. A 1/2" line can starve the unit
- Check inlet gas pressure: should be 7-14" WC for natural gas at full fire. Below 5" WC and the unit will lock out
- If pressure drops when unit fires: gas line is undersized or regulator can't keep up

**Step 3: Check minimum flow rate**
- Tankless heaters won't fire unless water flow exceeds the minimum activation rate
- This is the #1 "not-really-a-problem" on tankless units. Minimum flow is typically 0.4-0.75 GPM depending on brand and model
- A partially open faucet, low-flow fixture, or recirculation pump with low flow won't trigger ignition
- Check the flow sensor — a sticking or failed flow sensor makes the unit think there's no demand
- Some units have a flow adjustment screw or sensor that can be cleaned

**Step 4: Check for scale buildup — descale the unit**
- This is the #1 maintenance issue on tankless heaters, especially in hard water areas (>7 grains per gallon)
- Scale coats the heat exchanger, reducing heat transfer and flow. Eventually the unit can't heat at all or throws a scale/overheating error
- Descale procedure: connect a pump and bucket with white vinegar to the service valves, circulate for 45-60 minutes
- If the unit hasn't been descaled in >2 years in hard water, the heat exchanger may be permanently damaged
- Descaling should be done annually in hard water areas, every 2-3 years in soft water areas

**Step 5: Check venting for blockages**
- Direct vent (concentric) or power vent (PVC) — both can get blocked by bird nests, ice, or debris
- A blocked vent triggers an ignition failure or flame rollout/overheating error
- Inspect the termination point outside — is it clear? Is the screen clogged with lint or ice?
- Check for proper vent length and number of elbows — exceeding the maximum vent run causes poor combustion
- If vent pipe is PVC: check for sags where condensate can pool and block airflow

**Step 6: Check the inlet filter screen**
- Every tankless has a small inlet water filter screen where the cold water enters the unit
- It catches debris and sediment — if it's clogged, water flow is restricted below the minimum activation rate
- Remove it, clean it, reinstall. Takes 2 minutes and solves more problems than people realize
- On Rinnai: bottom of the unit on the cold inlet side. On Navien: behind the front cover, cold side

**Step 7: Check the flame rod**
- If the unit ignites but the flame goes out within 2-5 seconds: dirty or failed flame rod (same concept as furnace flame sensors)
- Remove the flame rod and clean with fine emery cloth
- Check the µA reading: should be >1.0 µA with flame present. Below that, the unit shuts off gas
- If the rod is clean and readings are low: check the grounding of the unit. Poor ground = poor flame sensing

**Step 8: Check the igniter**
- If you hear clicking but no ignition: igniter is working but gas isn't reaching it, or gas isn't being ignited
- If NO clicking: igniter module or wiring issue. Check for voltage to the igniter during a call for heat
- Spark gap should be clean and at the correct distance (varies by model, usually 3-4mm)
- Some units use hot surface ignition instead of spark — check for glow like a furnace igniter

**Common causes ranked by frequency:**
1. Scale buildup in heat exchanger (25%)
2. Ignition failure — gas supply or venting (20%)
3. Minimum flow rate not met (15%)
4. Dirty flame rod (12%)
5. Error code lockout — needs reset after fixing root cause (8%)
6. Clogged inlet filter screen (7%)
7. Flow sensor failure (5%)
8. Blocked vent termination (4%)
9. Bad igniter or igniter module (2%)
10. Other (2%)""",
    },

    "slow_drain_clogged": {
        "title": "Slow/Clogged Drain",
        "symptoms": ["slow drain", "clogged drain", "drain clogged", "sink draining slow", "tub draining slow", "drain backed up", "water won't drain"],
        "equipment": ["drain", "sink", "tub", "shower", "plumbing"],
        "flow": """## Slow/Clogged Drain Diagnostic Flow

**Step 1: Determine scope — single fixture or multiple?**
- If ONE fixture is slow: the clog is in that fixture's drain line or P-trap
- If MULTIPLE fixtures on the same floor are slow: the clog is in a branch line
- If the WHOLE HOUSE is slow, or drains back up when you flush a toilet: main sewer line is the problem
- This distinction tells you exactly where to focus — don't snake a bathroom sink when the main line is blocked

**Step 2: Try a plunger first**
- A cup plunger (flat bottom) works best on sinks. A flange plunger (extended rubber lip) works best on toilets
- For sinks: block the overflow hole with a wet rag, fill the basin with 2-3 inches of water, then plunge vigorously 15-20 times
- For tubs: remove the stopper assembly, block the overflow plate, plunge the drain
- Plunging clears 60%+ of simple drain clogs — it's the most effective first step and costs nothing

**Step 3: Check and clean the P-trap**
- If plunging doesn't work on a sink: put a bucket under the P-trap and remove it
- P-traps collect hair, soap scum, grease, and small objects. A plugged P-trap is the #2 most common cause
- Clean the trap thoroughly, inspect for cracks, and reinstall with new washers if the old ones are compressed
- For bathroom sinks: hair and toothpaste buildup in the pop-up stopper assembly is extremely common. Pull the stopper out and clean it

**Step 4: Snake the drain line**
- If the P-trap is clear, the clog is further down the line
- Use a hand snake (drum auger) for sink and tub drains — 1/4" cable, 15-25 feet is usually enough
- Feed the cable in slowly, crank the handle when you hit resistance. You'll feel the cable break through the clog
- For kitchen drains: grease clogs are common 5-15 feet down the line where the pipe temperature drops and grease solidifies
- Pull the cable back slowly and clean it. Run hot water for 2-3 minutes to flush debris

**Step 5: Check the vent stack**
- If drains are slow AND you hear gurgling from other fixtures when one drains: the vent is likely blocked
- A blocked vent prevents proper air flow in the drain system — water drains slowly because air can't enter behind it (like holding your finger over a straw)
- Check the vent termination on the roof for bird nests, leaves, ice dams, or debris
- Run a garden hose down the vent from the roof. If water backs up and overflows, the vent is blocked. Snake it from the top

**Step 6: Camera inspection for persistent or recurring clogs**
- If the clog keeps coming back within weeks: something structural is wrong
- Camera inspection reveals: root intrusion, bellied pipe (sag where waste collects), offset joints, collapsed pipe, or buildup
- Root intrusion is extremely common on older clay or cast iron sewer lines — tree roots find joints and grow into the pipe
- A camera inspection typically costs $150-400 and saves thousands in unnecessary digging

**Step 7: Main line — when multiple fixtures are affected**
- Access the main cleanout (usually a 3-4" capped fitting in the basement, crawlspace, or outside)
- Use a main line machine (3/8" to 3/4" cable) — this is NOT a job for a hand snake
- Feed the cable to the clog, let the machine do the work. Don't force it around turns
- If the cable won't pass: root intrusion, offset joint, or collapsed pipe. Camera inspection is the next step
- After clearing: run water for 5+ minutes to confirm flow. Check multiple fixtures

**Common causes ranked by frequency:**
1. Hair and soap scum buildup — bathroom (30%)
2. Grease and food buildup — kitchen (20%)
3. Tree root intrusion — main line (15%)
4. Foreign objects (toys, wipes, cotton swabs) (10%)
5. Mineral/scale buildup in old pipes (8%)
6. Vent stack blockage (5%)
7. Bellied or sagging pipe (5%)
8. Collapsed or offset pipe joint (4%)
9. Undersized drain line (2%)
10. Other (1%)""",
    },

    "running_toilet": {
        "title": "Running Toilet / Toilet Won't Stop Running",
        "symptoms": ["running toilet", "toilet won't stop running", "toilet keeps running", "toilet running constantly", "toilet fills then runs", "phantom flush"],
        "equipment": ["toilet", "plumbing"],
        "flow": """## Running Toilet Diagnostic Flow

**Step 1: Identify the type of running**
- Constant running (water never stops): flapper not seating, fill valve stuck open, or water level above overflow tube
- Intermittent/phantom flush (toilet runs for 10-30 seconds every few minutes then stops): flapper is leaking slowly — water level drops, fill valve kicks on to refill
- Hissing sound from fill valve: fill valve not shutting off completely — water level issue or bad fill valve
- This distinction tells you exactly which component to focus on

**Step 2: Check the flapper (most common cause — 40% of running toilets)**
- Lift the tank lid and look at the rubber flapper at the bottom of the tank
- The "lift chain test": push down on the flapper with your finger. If the running stops, the flapper isn't seating properly
- Common flapper issues: warped, cracked, hardened with age (rubber degrades over 5-7 years), mineral buildup on sealing surface, wrong size flapper
- Also check: is the lift chain too tight? A chain with no slack holds the flapper slightly open
- Replace the flapper — universal flappers fit 90% of toilets. Match 2" or 3" flush valve size

**Step 3: Check the fill valve**
- If you hear a constant hissing: the fill valve isn't shutting off
- Check the float — on cup-type fill valves (FluidMaster style), the float rides on the valve shaft. Adjust it DOWN to lower the water level
- On ball-float valves (older style): bend the float arm down slightly, or adjust the screw at the top
- If adjusting the float doesn't stop the hissing: the fill valve diaphragm is worn. Replace the entire fill valve — they're $8 and take 15 minutes
- A fill valve that's 8+ years old is living on borrowed time. When in doubt, replace it

**Step 4: Check the water level vs overflow tube**
- The water level should be about 1/2" to 1" BELOW the top of the overflow tube
- If water is flowing INTO the overflow tube: the fill valve isn't shutting off, or the float is set too high
- Lower the float adjustment until water stops 1" below the overflow tube
- If you can't get the water level to stabilize below the overflow: bad fill valve — replace it

**Step 5: Check the flush valve seat**
- If you've replaced the flapper and it still leaks: the flush valve seat (the ring the flapper sits on) may be the problem
- Run your finger around the seat — feel for mineral buildup, pitting, or warping
- Light mineral deposits: clean with fine emery cloth or a Scotch-Brite pad
- If the seat is cracked or deeply pitted: you can install a seat repair kit (an adhesive ring that goes over the old seat) or replace the entire flush valve
- On very old toilets (20+ years), the flush valve seat can corrode enough that no flapper will seal

**Step 6: Check the refill tube**
- The small rubber tube that clips to the top of the overflow tube refills the bowl after a flush
- If this tube is INSERTED DOWN INTO the overflow tube (pushed too far in), it can create a siphon that continuously drains the tank
- The refill tube should clip to the TOP of the overflow tube and drip water in — it should NOT be stuffed down into it
- This is a common mistake during fill valve replacement — an easy fix that people miss

**Step 7: Check for cracked overflow tube or tank**
- Rare but possible: a hairline crack in the overflow tube lets water leak from the tank into the bowl constantly
- If you've replaced the flapper and fill valve and it STILL runs: look carefully at the overflow tube for cracks
- A cracked tank (below the water line) will leak water onto the floor. Check the base of the tank and the tank-to-bowl bolts

**Common causes ranked by frequency:**
1. Worn or warped flapper (40%)
2. Fill valve not shutting off (20%)
3. Float set too high — water above overflow (12%)
4. Mineral buildup on flush valve seat (8%)
5. Lift chain too tight or tangled (5%)
6. Refill tube siphoning (5%)
7. Cracked overflow tube (3%)
8. Wrong flapper size (3%)
9. Leaking flush valve gasket (2%)
10. Other (2%)""",
    },

    "no_water_pressure": {
        "title": "Low/No Water Pressure",
        "symptoms": ["low water pressure", "no water pressure", "weak water pressure", "water pressure dropped", "barely any water coming out", "low flow"],
        "equipment": ["plumbing", "faucet", "water heater"],
        "flow": """## Low/No Water Pressure Diagnostic Flow

**Step 1: Determine scope — one fixture, one area, or whole house?**
- ONE fixture low: the problem is at that fixture (aerator, supply valve, supply line)
- Hot side only weak: water heater related (dip tube, scale, shutoff valve)
- ONE area of the house: a branch line issue (partially closed valve, corroded pipe, leak)
- WHOLE house suddenly low: main shutoff partially closed, PRV failure, municipal supply issue, or a major leak
- Ask: "Did this just start, or has it been getting worse over time?" Sudden = valve or leak. Gradual = buildup or corrosion

**Step 2: Check the aerator (single fixture — most common cause)**
- Remove the aerator from the faucet — it screws off the end of the spout
- Inspect for debris, mineral buildup, or sediment. Sediment after work on the water lines is extremely common
- Clean or replace the aerator. Run the faucet without the aerator to confirm good flow
- If flow is good with the aerator off: the aerator was the only problem. This fixes 40% of single-fixture low pressure complaints

**Step 3: Check shutoff valves**
- The angle stops (shutoff valves under sinks/toilets) may be partially closed — especially if someone recently worked on the plumbing
- Gate valves are notorious for breaking internally — the handle turns but the gate is corroded and only partially opens
- Check the main shutoff at the meter and at the house entry. Even 1/4 turn closed on a gate valve drops pressure significantly
- Quarter-turn ball valves should be either fully open (handle parallel to pipe) or fully closed. No in-between

**Step 4: Check the PRV (pressure reducing valve)**
- Most houses with municipal water have a PRV — a bell-shaped brass device on the main water line, usually near where it enters the house
- Normal setting: 50-60 PSI. Failing PRV can drop pressure to 20-30 PSI or fluctuate wildly
- Test with a pressure gauge on a hose bib: should read 45-75 PSI. Below 40 = problem
- PRVs have a lifespan of 10-15 years. A failed PRV is replaced, not repaired. Typical cost: $50-150 for the part
- After replacing a PRV, bleed air from the system by opening the highest faucet in the house

**Step 5: Check for leaks (whole house pressure loss)**
- The meter test: turn off all water in the house. Go to the water meter and watch the dial or digital display
- If the meter is still moving with everything off: you have a leak somewhere between the meter and the house
- Check: toilets running (put food coloring in the tank — if it appears in the bowl, flapper is leaking), irrigation system, water heater T&P valve dripping, hose bibs, slab leaks (listen for hissing near the floor)
- A slab leak (pipe under the foundation) can waste 1-2 GPM continuously and drops pressure system-wide

**Step 6: Check water heater dip tube (hot side only is weak)**
- If ONLY the hot water side has low pressure/flow: the dip tube inside the water heater may be broken
- Broken dip tubes (common on late-1990s tanks) crumble into small pieces that clog faucet aerators and fixture strainers
- Symptoms: low hot water flow, tiny white plastic pieces in the aerator screens
- Also check: is the water heater shutoff valve fully open? And check for scale buildup inside the heater — particularly on old tanks

**Step 7: Check pipe condition (gradual pressure loss in older homes)**
- Galvanized steel pipes (common in pre-1970s homes) corrode internally over time. The pipe ID shrinks from 3/4" to the size of a pencil
- If you have galvanized pipes and pressure has been declining for years: repipe is the real fix. No amount of valve replacement or PRV adjustment will restore flow through corroded pipes
- Check by removing a section of horizontal pipe and looking inside. If it's nearly closed off with rust scale: that's your answer
- Copper and PEX don't have this issue. CPVC can develop scale in hard water areas but much less than galvanized

**Common causes ranked by frequency:**
1. Clogged aerator — single fixture (25%)
2. Partially closed shutoff valve (20%)
3. Failed PRV (15%)
4. Corroded galvanized pipes — older homes (10%)
5. Water leak reducing system pressure (8%)
6. Water heater dip tube failure (7%)
7. Municipal supply issue (5%)
8. Scale buildup in pipes or water heater (5%)
9. Faulty pressure gauge (misdiagnosis) (3%)
10. Other (2%)""",
    },

    "gfci_keeps_tripping": {
        "title": "GFCI Keeps Tripping",
        "symptoms": ["gfci keeps tripping", "gfci won't reset", "gfci tripping", "ground fault", "gfci outlet not working", "gfci won't stay on"],
        "equipment": ["electrical", "gfci", "outlet", "receptacle"],
        "flow": """## GFCI Keeps Tripping Diagnostic Flow

**IMPORTANT: A GFCI trips when it detects even a tiny (5mA) difference between hot and neutral current — meaning current is leaking to ground somewhere. This is a safety device. The goal is to find WHERE the current is leaking, not to bypass the GFCI.**

**Step 1: Unplug everything and test**
- Unplug ALL devices from the GFCI outlet AND from all outlets downstream of it (outlets that lose power when the GFCI trips)
- Press the RESET button on the GFCI
- If it HOLDS with nothing plugged in: one of the devices is the culprit. Plug them back in one at a time until it trips. That's your bad device
- If it TRIPS immediately with nothing plugged in: the problem is in the wiring or the GFCI itself (proceed to step 2)

**Step 2: Check for moisture**
- Moisture is the #1 cause of GFCI tripping with no load — accounts for 30% of all GFCI trip calls
- Check the GFCI box itself — pull the outlet out and look for dampness, condensation, or water intrusion
- Outdoor GFCIs: check the in-use cover. Rain, sprinkler spray, and condensation get into boxes constantly
- Bathroom GFCIs: steam from showers migrates into boxes through gaps. Check for moisture behind the cover plate
- Kitchen GFCIs: splashing water from sinks. Check under the counter for water tracking down the wall into the box
- If you find moisture: dry everything out, seal the box, and test again

**Step 3: Check downstream outlets and wiring**
- A GFCI protects all outlets wired on its LOAD terminals (downstream)
- A fault ANYWHERE downstream trips the GFCI — the problem may not be at the GFCI location
- Disconnect the LOAD wires from the GFCI (leave only LINE wires connected). If the GFCI now holds: the fault is downstream
- Reconnect downstream circuits one at a time (if there are junction points) to isolate which run has the fault

**Step 4: Check for neutral-to-ground contact downstream**
- If neutral and ground wires are touching anywhere downstream, the GFCI sees a current imbalance and trips
- This is the #1 WIRING cause of nuisance tripping — loose wires in a downstream box, a nail through a cable, or a miswired outlet
- At each downstream outlet: verify neutral (white) and ground (bare/green) are NOT touching or connected together
- Also check: a shared neutral from another circuit landed on the GFCI load side will cause instant tripping

**Step 5: Check for damaged wire insulation**
- Old wiring (especially in unfinished spaces) can have nicked, cracked, or rodent-chewed insulation
- Current leaks through damaged insulation to the metal box or other grounded surfaces
- Inspect visible wiring runs, especially in crawlspaces, attics, and garages
- A megohmmeter (insulation resistance tester) can identify insulation breakdown without visible damage — readings below 1MΩ indicate compromised insulation

**Step 6: Check for worn appliance or tool cords**
- Appliances with damaged power cords leak current to ground — especially in wet environments
- Common offenders: portable heaters, hair dryers, power tools, old refrigerators, washing machines
- Inspect the cord for cuts, fraying, or melted spots near the plug
- Test each suspect device on a known-good GFCI circuit — if it trips there too, the device is bad

**Step 7: Replace the GFCI itself**
- GFCIs have a lifespan of 10-15 years. After that, they become unreliable — either failing to trip (dangerous) or nuisance tripping (annoying)
- If the GFCI is old, discolored, or won't reset even with no load and dry conditions: replace it
- When replacing: connect LINE wires (from panel) to the LINE terminals, LOAD wires (to downstream outlets) to the LOAD terminals. Getting this backwards = no downstream protection
- After replacement: press TEST, then RESET. The GFCI should trip and reset cleanly. Test monthly

**Common causes ranked by frequency:**
1. Moisture/water intrusion in box or wiring (30%)
2. Faulty appliance or damaged cord (20%)
3. Neutral-ground contact downstream (12%)
4. Worn-out GFCI device (10%)
5. Damaged wire insulation (8%)
6. Shared neutral from another circuit (7%)
7. Downstream wiring fault (5%)
8. GFCI installed incorrectly (LINE/LOAD reversed) (4%)
9. Bad GFCI out of the box — rare but happens (2%)
10. Other (2%)""",
    },

    "washer_not_draining": {
        "title": "Washer Not Draining",
        "symptoms": ["washer won't drain", "washer not draining", "washing machine not draining", "washer full of water", "washer drain error", "washer OE error", "washer 5E error"],
        "equipment": ["washer", "washing machine"],
        "flow": """## Washer Not Draining Diagnostic Flow

**Step 1: Check the drain hose**
- The drain hose runs from the back of the washer to a standpipe, laundry sink, or direct drain connection
- Check for KINKS — a kinked hose blocks all drainage. Straighten it out and test
- Check the standpipe height — the hose should go 6-8 inches into the standpipe, NOT jammed all the way down. If it's pushed in too far, it creates a siphon lock or an airtight seal that prevents drainage
- Check that the standpipe isn't clogged — pull the hose out and pour a bucket of water down it. If it backs up: the standpipe or branch drain is clogged, not the washer
- Maximum recommended drain hose height is 96 inches. If the hose goes higher than the washer's pump can push, it won't drain

**Step 2: Check the drain pump filter (front-load washers)**
- LG, Samsung, and most front-loaders have an accessible drain pump filter behind a small panel at the bottom front of the machine
- BEFORE opening: place towels down and have a shallow pan ready — water WILL pour out
- Slowly turn the filter cap counterclockwise. Let water drain into the pan
- Pull the filter out and inspect — you'll commonly find: coins, bobby pins, small socks, hair ties, bra underwires, and lint buildup
- Clean the filter, check the filter housing for debris, reinstall finger-tight
- This single step fixes 40%+ of front-load washer drain failures

**Step 3: Check for objects blocking the pump impeller**
- If the pump hums but water doesn't drain: something is lodged in the impeller (the spinning part inside the pump)
- Common objects: coins, buttons, broken bra underwires, small toy parts, bobby pins
- On some models you can access the pump from the bottom of the washer (tip it back carefully)
- On others you need to remove the back panel or front lower panel to reach the pump
- Manually spin the impeller — it should spin freely. If it's jammed or won't move: remove the obstruction

**Step 4: Check the drain pump motor**
- If the pump makes no sound at all during the drain cycle: the motor may be dead or not getting power
- Listen during a drain cycle: you should hear the pump motor running (a distinct humming/whirring sound)
- If the motor HUMS but the impeller doesn't spin: the motor coupling is broken or the impeller is jammed (step 3)
- If complete silence during drain: check for 120V AC at the pump motor connector during a drain cycle. Voltage present but no motor operation = dead pump motor. No voltage = control board or wiring issue

**Step 5: Check the control board and wiring**
- If the pump isn't getting power during drain: the control board isn't sending the signal
- Check the wire harness connection from the board to the pump — corrosion, loose connector, or a burnt pin are common
- Some boards have a relay that controls the drain pump — a stuck or burnt relay means no signal to the pump
- Error codes help here: OE (LG), 5E/SE (Samsung), F21/F5E2 (Whirlpool), E2/F5 (GE) all point to drain issues
- Try a hard reset: unplug the washer for 5 minutes, plug it back in, and run a drain/spin cycle

**Step 6: Check the lid switch/door lock (top-loaders and front-loaders)**
- Top-loaders: the washer won't drain or spin if the lid switch is broken — this is a safety interlock
- Test the lid switch: with the washer in a drain cycle, press the lid switch manually with a pen. If the pump starts: the lid switch actuator is broken or misaligned
- Front-loaders: the door lock must be engaged for any cycle to proceed. A faulty door lock can prevent drain/spin
- Check the door lock latch, the strike plate alignment, and the lock mechanism itself

**Step 7: Check the drain system beyond the washer**
- If the washer pumps water out but it backs up and overflows at the standpipe: the problem is the drain system, not the washer
- Standpipe minimum diameter: 2 inches. A 1.5" pipe can't handle the flow rate of modern washers
- Snake the standpipe drain — lint, soap residue, and debris build up over years
- If the washer drains into a laundry sink: check the sink drain for clogs (same thing — lint and soap buildup)

**Common causes ranked by frequency:**
1. Clogged drain pump filter — front-load (30%)
2. Object stuck in pump impeller (15%)
3. Kinked or improperly installed drain hose (15%)
4. Clogged standpipe or branch drain (10%)
5. Failed drain pump motor (10%)
6. Lid switch / door lock failure (7%)
7. Control board or wiring issue (5%)
8. Drain hose pushed too far into standpipe (4%)
9. Hose routed too high for pump capacity (2%)
10. Other (2%)""",
    },

    "refrigerator_not_cooling": {
        "title": "Refrigerator Not Cooling",
        "symptoms": ["fridge not cooling", "refrigerator warm", "freezer not freezing", "fridge not cold", "refrigerator temperature high", "refrigerator stopped cooling"],
        "equipment": ["refrigerator", "fridge", "freezer"],
        "flow": """## Refrigerator Not Cooling Diagnostic Flow

**Step 1: Check condenser coils (the #1 cause on units over 5 years old)**
- Condenser coils dissipate heat from the refrigerant. When they're coated with dust, pet hair, and grease, the compressor can't reject heat efficiently
- Location: bottom front (behind a kick plate) or on the back of the unit
- Pull the fridge out, remove the kick plate, and look. If the coils look like a fur coat: that's your problem
- Clean with a condenser coil brush and vacuum. Do this annually as preventive maintenance
- Dirty coils account for 25-30% of "fridge not cooling" calls on units 5+ years old

**Step 2: Check the condenser fan**
- The condenser fan blows air across the condenser coils. If it's not running, the coils can't dissipate heat even if they're clean
- Located next to the compressor, at the bottom rear of the unit
- Listen for the fan running when the compressor is on. If the compressor runs but the fan doesn't: check for debris jammed in the fan blade, then check the fan motor
- Spin the fan blade by hand — it should spin freely. If it's stiff or frozen: replace the fan motor
- Check for 120V at the fan motor connector when the compressor is running

**Step 3: Check the evaporator fan**
- The evaporator fan circulates cold air from the freezer coil into the fridge and freezer compartments
- Open the freezer door and press the door switch (the button/plunger that turns the light on/off). You should hear the evaporator fan running
- If the fan doesn't run: check for ice blocking the fan blade (common after defrost failure), then check the fan motor
- If the evaporator fan isn't running: the freezer gets cold near the coil, but the fridge section stays warm because no air is being circulated
- On modern units with multiple evaporators (like French-door models), each section has its own fan and damper

**Step 4: Check for frost/ice buildup on the evaporator (defrost problem)**
- Open the freezer and remove the back panel (inside the freezer) to expose the evaporator coil
- If the coil is a solid block of ice: the defrost system has failed
- Defrost system components: defrost heater (under the coil), defrost thermostat (on the coil, opens at 40-50°F to stop the heater), defrost timer or control board
- Test the defrost heater: disconnect it, measure resistance. Should be 20-40 ohms. Infinite = open heater, replace it
- Test the defrost thermostat: at room temp it should be open (infinite). In a freezer or when cold it should be closed (continuity)
- If it's a defrost timer: manually advance it to defrost. If the heater kicks on, the timer motor is stuck — replace it

**Step 5: Check the compressor**
- Feel the compressor (black dome at the bottom rear). Is it vibrating/running?
- If the compressor clicks on for a few seconds and clicks off: the overload protector is tripping. Could be a bad start relay, overloaded compressor, or electrical issue
- Remove the start relay (plugs into the side of the compressor). Shake it — if it rattles, the relay is bad. This is a $15-50 part that's easy to replace
- If the relay is good but the compressor still won't run: check compressor windings (ohms between the three pins). Open or grounded windings = bad compressor

**Step 6: Check the temperature control/thermostat**
- The thermostat controls when the compressor runs. If it's failed: the compressor never gets the signal to start
- Turn the dial from lowest to highest setting. You should hear a click as it turns on. No click = bad thermostat
- On electronic-control models: the main control board sends a signal to the compressor relay. Check for error codes on the display
- Some models have a separate damper control that regulates airflow between freezer and fridge. A stuck-closed damper means the fridge gets no cold air even though the freezer is fine

**Step 7: Check for sealed system issues (last resort)**
- If the compressor runs, both fans run, coils are clean, and defrost is working — but it's still not cold: the sealed system may have a problem
- Low refrigerant (leak in the sealed system), restricted capillary tube, or a failing compressor that can't build pressure
- Check compressor amp draw: should be near the nameplate rating. Very low amps with the compressor running = not pumping (internal failure)
- Sealed system repairs (recharging, replacing evaporator/condenser) often cost $500-1000+. On a fridge over 10-12 years old, replacement is usually more economical

**Common causes ranked by frequency:**
1. Dirty condenser coils (25%)
2. Defrost system failure (evaporator iced up) (20%)
3. Bad evaporator fan motor (12%)
4. Bad start relay on compressor (10%)
5. Condenser fan not running (8%)
6. Failed compressor (7%)
7. Bad temperature control/thermostat (5%)
8. Damper stuck closed (fridge warm, freezer cold) (5%)
9. Sealed system leak (4%)
10. Control board failure (4%)""",
    },

    "dryer_not_heating": {
        "title": "Dryer Not Heating",
        "symptoms": ["dryer not heating", "dryer no heat", "dryer clothes still wet", "dryer takes too long", "dryer tumbles but no heat", "dryer cold air"],
        "equipment": ["dryer", "clothes dryer"],
        "flow": """## Dryer Not Heating Diagnostic Flow

**Step 1: Check the vent FIRST (most common cause overall — 35% of all dryer heat complaints)**
- A clogged vent restricts airflow, causing the dryer to overheat internally. Safety devices (thermal fuse, high limit thermostat) shut off the heat to prevent fire
- LG dryers specifically show d80, d90, d95 codes indicating vent blockage percentage — if you see these, the vent is the problem
- Disconnect the vent from the back of the dryer. Run the dryer for 5 minutes. If it heats up: the vent is clogged, not the dryer
- Clean the vent run from the dryer to the exterior termination. Use a vent brush kit or leaf blower
- Check the exterior vent flap — birds love to nest in dryer vents. A blocked flap = zero airflow
- Maximum recommended vent length: 25 feet with no elbows. Each 90° elbow reduces effective length by 5 feet

**Step 2: Check the heating element (electric dryers)**
- The heating element is a coil of resistance wire inside a housing, usually behind the back panel or under the drum
- Disconnect power. Remove the back panel. Locate the element housing
- Measure resistance across the element terminals: should be 8-20 ohms (varies by wattage — 5400W element at 240V = ~10.7 ohms)
- Infinite reading = open element (broken coil). Replace the entire element assembly
- Visually inspect: you can often SEE a break in the coil. The coil should be intact and evenly spaced
- Also check for coil sag — if the coil is touching the housing, it'll short and blow the thermal fuse

**Step 3: Check the thermal fuse**
- The thermal fuse is a one-time safety device — once it blows, it stays open. The dryer tumbles but produces no heat
- Location: usually on the blower housing or exhaust duct, behind the back panel
- Test with a multimeter: should have continuity (near 0 ohms). If open (infinite): it's blown
- CRITICAL: a blown thermal fuse is a SYMPTOM, not a root cause. You MUST find why it blew — usually a clogged vent or failed cycling thermostat. If you just replace the fuse without fixing the root cause, it'll blow again
- Thermal fuses blow at 196°F to 307°F depending on the model

**Step 4: Check the gas igniter (gas dryers)**
- Gas dryers use a hot surface igniter (glowing bar) to light the gas burner
- Open the bottom front panel and observe during a heat cycle: the igniter should glow bright orange/white
- If the igniter glows but gas never lights: the gas valve solenoid coils are bad (step 5)
- If the igniter DOESN'T glow: measure resistance. Should be 50-400 ohms depending on model. Infinite = broken igniter. Replace it
- Igniters are fragile — don't touch the element with your fingers (oils cause hot spots and premature failure)

**Step 5: Check flame sensor / gas valve solenoid coils (gas dryers — most common gas dryer issue)**
- The gas valve has 2-3 solenoid coils that open the valve when the igniter reaches temperature
- Classic gas dryer failure pattern: igniter glows → gas ignites → runs for a while → flame goes out → igniter glows again → gas doesn't ignite this time. The dryer cycles between glowing igniter and no flame
- This is caused by failing solenoid coils that work when cool but fail when hot
- Replace ALL solenoid coils as a set — if one is weak, the others aren't far behind
- Coil resistance: typically 1000-2000 ohms each. But resistance testing alone won't catch heat-sensitive failures

**Step 6: Check the high limit thermostat**
- The high limit thermostat is a safety device that cuts power to the heater if exhaust temperature exceeds the safe limit (usually around 250°F)
- Unlike the thermal fuse, the high limit thermostat is usually resettable (it resets when it cools down)
- Test with multimeter: should have continuity at room temperature. If open: it's failed or there's an overheating condition
- Located on or near the heating element housing (electric) or burner assembly (gas)

**Step 7: Check the cycling thermostat**
- The cycling thermostat regulates the dryer temperature during normal operation — it turns the heater on and off to maintain the set temperature
- Located on the blower housing or exhaust duct
- Test with multimeter: should have continuity at room temperature. If open: the heater never gets power during the cycle
- A failed cycling thermostat can also cause overheating (stuck closed) which blows the thermal fuse

**Step 8: Check power supply (electric dryers need 240V)**
- Electric dryers need BOTH legs of 240V. If one leg is lost (tripped single-pole breaker, bad connection, burnt prong on the plug), the dryer runs the motor (120V) but not the heater (240V)
- Check the dryer outlet with a multimeter: L1 to L2 should be 240V, L1 to neutral = 120V, L2 to neutral = 120V
- Check the breaker: a 30A double-pole breaker can trip on one side only — push it fully OFF then back ON
- Inspect the dryer cord plug and outlet for burnt or corroded prongs — a common cause of intermittent heat loss

**Common causes ranked by frequency:**
1. Clogged dryer vent (35%)
2. Blown thermal fuse (15%)
3. Failed gas valve solenoid coils — gas dryers (12%)
4. Bad heating element — electric dryers (10%)
5. Failed igniter — gas dryers (8%)
6. Bad cycling thermostat (5%)
7. High limit thermostat failure (5%)
8. Lost one leg of 240V — electric dryers (4%)
9. Broken belt (drum doesn't turn = clothes don't dry) (3%)
10. Control board issue (3%)""",
    },

    "water_leak_ceiling": {
        "title": "Water Leak from Ceiling/Wall",
        "symptoms": ["water leaking from ceiling", "water stain on ceiling", "water dripping", "leak in ceiling", "pipe leak", "water coming through wall", "wet ceiling"],
        "equipment": ["plumbing", "water heater", "drain"],
        "flow": """## Water Leak from Ceiling/Wall Diagnostic Flow

**FIRST: If water is actively dripping or flowing, take immediate action: turn off the main water supply if it appears to be a supply line (pressurized) leak. If it's intermittent (only when a fixture is used), stop using that fixture. Put a bucket under the drip. Then diagnose.**

**Step 1: Identify the likely source based on location**
- Leak directly below a bathroom: toilet wax ring, shower pan, supply lines, tub drain
- Leak below a kitchen: sink drain connections, dishwasher supply/drain, refrigerator water line
- Leak near an exterior wall or chimney: roof leak tracking along a rafter or pipe
- Leak near the HVAC system: condensate drain pan overflow, clogged condensate line
- Leak that appears during or after rain: roof or flashing issue, not plumbing
- Leak that appears only when a specific fixture is used: drain or supply line for that fixture

**Step 2: Check for toilet wax ring failure (most common cause below bathrooms — 25%)**
- A failed wax ring leaks water every time the toilet is flushed — the leak appears on the ceiling below
- Rock the toilet gently — if it moves at all, the wax ring has likely failed and the toilet needs to be pulled and reset
- Check the base of the toilet for any seepage, staining, or soft/damaged flooring
- Check the toilet supply line connection and the fill valve for drips — sometimes the leak is from a supply line, not the wax ring
- To confirm: flush the toilet and have someone watch the ceiling below. If it drips during/after flush = wax ring or drain connection

**Step 3: Check supply lines for corrosion or failure**
- Supply lines (hot and cold) are under constant pressure — they leak whether fixtures are in use or not
- Braided stainless steel supply lines are more reliable than old chrome or plastic ones, but they still fail
- Check all supply line connections in the area above the leak: sink supply lines, toilet supply lines, washing machine hoses
- Look for pinhole leaks in copper pipes — green corrosion/patina around a joint or fitting = leak
- Old brass compression fittings and gate valves are prone to failure — replace with quarter-turn ball valves when possible

**Step 4: Check AC condensate drain pan and line**
- Air handlers in attics or above living spaces have a secondary drain pan as a safety catch
- If the primary condensate line clogs (algae, sludge, rust), the pan fills up and overflows onto the ceiling
- Check the primary drain line: blow it out with compressed air or a wet-dry vac from the outdoor end
- Check the secondary (overflow) drain: if water is coming from this line, the primary is definitely clogged
- Install a float switch or wet switch on the drain pan if one isn't already present — it shuts the system off before overflow

**Step 5: Check for shower pan or tub drain leaks**
- Shower pans can develop cracks or the drain gasket can fail, allowing water to seep through the floor
- Tub drain connections (overflow and shoe) can loosen over time
- The "plug and fill" test: plug the shower drain, fill with 1-2 inches of water, and wait 30 minutes. If the leak below appears: it's the pan or drain
- Shower door or curtain splash-out can look like a shower pan leak — water gets under the door frame and seeps through the floor
- Check the caulk/grout around the shower: deteriorated grout lets water behind tiles and into the wall cavity

**Step 6: Check the roof (leak near exterior wall, chimney, or after rain)**
- Water can travel a long distance along rafters, decking, and pipes before dripping through the ceiling — the drip point is NOT always directly below the roof leak
- Check the attic (if accessible) with a flashlight during or right after rain. Follow the water trail upward to find the entry point
- Common roof leak spots: around plumbing vents (cracked boot), at flashing (chimney, valley, wall-to-roof transition), and at damaged/missing shingles
- A roof leak that only appears during heavy rain or wind-driven rain may be hard to replicate

**Step 7: Do NOT cut open the ceiling until the source is identified**
- Cutting open drywall creates dust, debris, and a bigger repair job. Only cut when you've narrowed down the source and need access for repair
- If you must cut for diagnosis: make a small exploratory hole (6"x6") with a drywall saw, away from any known pipe locations
- Before cutting: check for wires and pipes with a stud finder that detects AC wiring and metal
- If significant water has pooled above the ceiling (sagging drywall): carefully poke a small hole with a screwdriver to drain it into a bucket. Waterlogged drywall can collapse suddenly and is heavy enough to cause injury

**Common causes ranked by frequency:**
1. Toilet wax ring failure — below bathroom (25%)
2. Supply line leak or failed fitting (20%)
3. AC condensate drain overflow (15%)
4. Roof/flashing leak (10%)
5. Shower pan or tub drain leak (8%)
6. Drain pipe connection failure (7%)
7. Pinhole leak in copper pipe (5%)
8. Washing machine hose failure (4%)
9. Ice dam / frozen pipe burst (seasonal) (3%)
10. Other (3%)""",
    },

    "boiler_no_heat": {
        "title": "Boiler Not Heating",
        "symptoms": ["boiler not heating", "boiler no heat", "radiators cold", "baseboard not heating", "boiler won't fire", "boiler lockout"],
        "equipment": ["boiler", "radiator", "baseboard", "hydronic"],
        "flow": """## Boiler Not Heating Diagnostic Flow

**Step 1: Check error code on display**
- Modern boilers (Weil-McLain, Buderus, Viessmann, Navien, Triangle Tube) have digital displays or LED blink codes
- Write down the exact code. Common lockout codes: ignition failure, low water pressure, high limit, flame loss
- Many boilers have a RESET button — try resetting once. If it locks out again within minutes, don't keep resetting — diagnose the root cause
- If the display is completely dead: check power. Is the boiler switch on? Is the breaker tripped? Is the transformer OK?

**Step 2: Check the circulator pump**
- The circulator pump moves hot water from the boiler through the piping to the radiators/baseboards and back
- Feel the pump body — it should be warm (from the water) and you should feel a slight vibration when it's running
- If the pump is not running: check for power at the pump. On zone systems, the pump is controlled by the zone valve end switch — if the zone valve doesn't open, the pump never starts
- If the pump hums but water isn't moving: the impeller may be stuck. Some circulators have a slot on the front for a flathead screwdriver to manually spin the impeller and free it
- A failed circulator means the boiler water stays in the boiler and the radiators stay cold

**Step 3: Check zone valves (if the system has zones)**
- Zone valves control which areas get heat. Each zone valve has a power head (motor) that opens the valve when the thermostat calls for heat
- Listen/feel for the zone valve motor when the thermostat calls — it takes 1-2 minutes for the motor to fully open the valve
- Check for 24V at the zone valve motor terminals when the thermostat is calling. No voltage = thermostat or transformer issue
- Zone valve end switch: when the valve is fully open, an internal switch closes and calls the boiler to fire AND starts the circulator. If the end switch is bad: the valve opens but the boiler never fires
- Zone valves fail frequently — the motor or the valve body can fail. Replace the power head first ($40-60) before replacing the whole valve ($80-150)

**Step 4: Check water pressure**
- The boiler pressure gauge should read 12-18 PSI when cold (most residential systems)
- If pressure is below 12 PSI: the system has lost water. Check the automatic fill valve (pressure reducing valve) — it should maintain 12-15 PSI
- If the gauge reads 0 PSI: major water loss. Check for leaks at fittings, radiators, expansion tank, and the boiler itself
- DO NOT fire the boiler with low water — this can crack the heat exchanger (cast iron) or trigger the low water cutoff
- If the system keeps losing pressure: find the leak. Check all accessible piping, especially threaded connections and older radiator valves

**Step 5: Check the expansion tank**
- The expansion tank absorbs the pressure increase as water heats up. If it's waterlogged (lost its air charge), pressure spikes when the boiler fires
- High pressure trips the relief valve (30 PSI) — you'll see water dripping from the relief valve discharge pipe
- Test: tap on the tank. Air side should sound hollow (top half), water side should sound solid (bottom half). If the WHOLE tank sounds solid: it's waterlogged
- Check the air charge: the Schrader valve on the tank should read 12 PSI (matching the cold fill pressure). If 0 PSI: the bladder has ruptured — replace the tank
- A waterlogged expansion tank is one of the most common boiler service issues — 15% of all boiler calls

**Step 6: Check ignition (gas boilers)**
- Same basic process as a furnace: inducer runs → pressure switch closes → igniter glows → gas valve opens → flame sensor proves flame
- Check the flame sensor: pull it, clean with emery cloth, check for >1.0 µA in flame. This is the #1 ignition-related failure
- Check the igniter: should glow within 30 seconds. Resistance should be 40-200 ohms (silicon carbide) or 11-17 ohms (silicon nitride)
- Check gas pressure: manifold should be 3.5" WC for NG. Low gas pressure = weak flame = flame sensor dropout
- If the boiler fires but locks out on flame failure after a few minutes: flame sensor, gas pressure, or venting issue

**Step 7: Check for air in the system — bleed radiators**
- Air trapped in radiators prevents hot water from circulating fully through the radiator — the top stays cold while the bottom is warm
- Each radiator has a bleeder valve (usually a small square-head valve at one end, near the top)
- Use a radiator key or flathead screwdriver. Open the valve slowly — air hisses out first, then water follows. Close it when you get a solid stream of water
- Start with the radiator highest in the system and farthest from the boiler, then work your way back
- If you bleed a LOT of air: check the system for an air leak (bad fill valve, loose fitting, failed air separator) and re-check boiler pressure after bleeding — you may need to add water

**Step 8: Check the low water cutoff (LWCO)**
- The low water cutoff is a safety device that prevents the boiler from firing if the water level is too low
- On steam boilers: this is critical. The LWCO sits at the waterline and has a float that shuts down the boiler if water drops
- On hot water boilers: some have a flow switch or pressure switch that serves the same purpose
- If the LWCO is dirty or stuck, it can prevent the boiler from firing even with adequate water
- Flush the LWCO by opening the drain valve briefly. On older units (McDonnell Miller), this should be done monthly

**Common causes ranked by frequency:**
1. Zone valve failure (power head or end switch) (20%)
2. Waterlogged expansion tank / relief valve dripping (15%)
3. Ignition failure — flame sensor, igniter, gas issue (15%)
4. Air in the system (10%)
5. Circulator pump failure (10%)
6. Low water pressure / water loss (8%)
7. Thermostat or wiring issue (7%)
8. Failed control board or aquastat (5%)
9. Stuck low water cutoff (3%)
10. Other (7%)""",
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
