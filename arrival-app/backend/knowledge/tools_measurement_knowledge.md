# Tools & Measurement Knowledge — Field Reference

This document covers hands-on tool usage, measurement techniques, and diagnostic procedures across HVAC, plumbing, electrical, and general construction trades. Written for field technicians who need real numbers and practical sequences, not textbook theory. Your tools are extensions of your hands. A good tradesman knows not just how to use each tool, but what the readings mean and what they tell you about the system. Taking readings without understanding the numbers is theater, not diagnostics.

---

## Multimeter / Electrical Testing

### Basic Multimeter Operation

Every technician needs a Cat III or Cat IV rated meter. Fluke 87V, 117, and 116 are the workhorses. For HVAC, the Fluke 116 with temperature probe is ideal. Fieldpiece SC680 is solid with wireless capability. Budget option: Klein CL800 for residential work. Always check leads before testing. Frayed or damaged leads give false readings and can be dangerous. Replace leads annually even if they look fine — internal wire fatigue is not visible.

**AC Voltage (VAC):**
- Set dial to VAC (squiggly line symbol, not straight)
- Red lead in V/ohm jack, black in COM
- Standard outlet: 120V nominal. Acceptable range: 114-126V (120V +/- 5%). Below 110V means voltage drop — undersized wire, loose connection, or overloaded circuit
- 240V circuit (dryer, range, A/C): 240V nominal, acceptable 228-252V. Measure between two hot legs. Also check each hot to neutral — should be within 2V of each other. If one reads 125V and the other 115V, you have a utility imbalance or loose neutral
- Control circuit (HVAC): 24VAC from transformer secondary. Normal range 24-28V. Below 22V indicates failing transformer, shorted wire, or excessive load from accessories (smart thermostats, damper motors, add-on modules all draw from that transformer)
- Three-phase: check L1-L2, L2-L3, L1-L3 — all three should be within 2% of each other. Voltage imbalance over 2% on three-phase will destroy motors
- Ghost voltage on abandoned wires is common — use Lo-Z mode on your meter to bleed off phantom readings

**DC Voltage (VDC):**
- Straight line symbol on dial
- Flame sensor signal: 1-6 microamps DC (need a meter that reads microamps or use DC millivolt scale across a known resistance). Below 1 microamp and the furnace locks out. Clean flame sensor with fine emery cloth, not sandpaper
- Thermostat batteries: 1.5V for AA/AAA (replace below 1.2V), 3V for lithium coin (replace below 2.5V)
- 12V systems (generators, vehicles): 12.6V fully charged, 12.4V at 75%, 12.0V at 25%. Below 11.8V the battery is functionally dead
- Control boards: 24VDC on some, 5VDC logic circuits
- Solar panel open circuit voltage: varies by panel, check nameplate Voc. A 60-cell panel is typically 30-38V open circuit

**Resistance (Ohms):**
- Always de-energize the circuit before measuring resistance — measuring ohms on a live circuit will damage your meter or give false readings
- Disconnect at least one side of the component to isolate it
- Touch leads together first — should read 0.1-0.3 ohms (lead resistance)
- OL (over limit) means open circuit — broken wire, blown element, bad connection
- Zero ohms means dead short
- Gas valve coil (standing pilot): 100-200 ohms per coil. OL means burned out coil
- Electric heating element (5kW): approximately 10-12 ohms. Calculate expected: R = V squared / W. For 5kW at 240V: (240 x 240) / 5000 = 11.5 ohms
- Flame sensor: should read infinite (OL) to ground when clean. Any measurable resistance means carbon buildup

**Continuity:**
- The beep test — set to continuity (speaker/diode symbol)
- Touch leads together first to confirm the beep
- Beep means current flows, silence means open
- Use for: tracing wires, checking fuses (should beep, no beep means blown), verifying switches (beep when closed, no beep when open), checking motor windings for open circuits, tracing wire colors through conduit
- Power MUST be off — the meter sends a small test current

**Amperage (Amps):**
- Most field meters use a clamp jaw — do not break into the circuit
- Clamp around ONE conductor only — clamping around a cable with hot and neutral cancels the reading to near zero
- If reading is low, wrap the wire 10 times around the jaw and divide reading by 10 for better resolution on small loads
- Inrush current on motors can be 6-8x running amps — do not panic at startup spike

### Clamp Meter Usage

Use a clamp meter when you cannot break the circuit or need quick amperage readings.

- Ideal for verifying compressor amp draw against nameplate RLA (Rated Load Amps)
- A/C compressor running amps should be at or below RLA. If actual amps exceed RLA by 10%+ something is wrong — low voltage, high head pressure, failing windings, or mechanical binding
- LRA (Locked Rotor Amps) on the nameplate is the stall current — if you see this during run, the compressor is locked up
- Blower motor: depends on speed tap and static pressure. A 1/2 HP PSC motor on high typically draws 4-6 amps. ECM motors adjust — check manufacturer specs. Rising amps over time usually means dirty blower wheel
- Electric heat strip: a 5kW strip at 240V draws approximately 21 amps. Zero amps means open element. Partial amps means one element in a bank is open
- For three-phase motors: check all three legs — imbalance over 5% indicates a problem
- True RMS clamp meters are required for VFD-driven motors — non-true-RMS meters give garbage readings on variable frequency drives

### Megohmmeter (Megger) Testing

Used for insulation resistance on motor windings, cables, and high-voltage equipment. This is the definitive test for a grounded compressor or motor.

**Procedure for compressor testing:**
1. Disconnect ALL wires from the compressor terminals
2. Set megger to 500V DC for motors under 480V, 1000V DC for 480V+ motors
3. Connect one lead to a compressor terminal, the other to the copper suction line (ground/chassis)
4. Press the test button for 10 seconds minimum
5. Read the insulation resistance:
   - Above 500 megohms: excellent insulation
   - 100-500 megohms: good, normal for an older compressor
   - 50-100 megohms: fair, beginning to deteriorate, monitor it
   - 20-50 megohms: suspect, insulation breaking down, plan replacement
   - Below 20 megohms: failed, ground fault, replace the compressor
   - Zero or near-zero: hard ground, dead compressor

- Test all three terminals to ground: Common to ground, Start to ground, Run to ground. Any one reading low means failure
- Test winding to winding (C-R, C-S, R-S) — these should show normal low winding resistance, confirming no open windings
- Temperature affects readings — hot windings read lower. Let the compressor cool 30 minutes before testing or note temperature and apply correction factors
- Record readings over time — trending downward means insulation is degrading even if numbers are still above minimum
- General rule: minimum acceptable is 1 megohm per 1,000V of operating voltage plus 1 megohm — so a 480V motor needs at least 1.48 megohms, but in practice you want 50+ megohms on a healthy motor

### Common Electrical Measurements & What They Mean

**24V Transformer Secondary Check:**
- Measure across secondary terminals with the system running
- Should read 24-28VAC — most transformers put out 26-27VAC under load
- Below 22V: transformer is undersized, overloaded, or failing. Check VA rating vs connected load
- A 40VA transformer on a system with a 50VA draw will sag low and cause erratic control board behavior
- If secondary reads 0V but primary has voltage, the transformer is dead or the secondary is shorted — disconnect secondary wires and re-measure to confirm

**Capacitor Testing (Microfarad Reading):**
- Discharge the capacitor first — short terminals with an insulated screwdriver or a 20,000 ohm 5W discharge resistor (resistor is safer)
- Set meter to capacitance (uF symbol)
- Disconnect at least one wire from the capacitor
- Reading should be within +/-6% of the rated value printed on the capacitor
- A 45uF cap reading 38uF is weak — replace it
- A 45uF cap reading 0 is shorted or open — replace immediately
- Dual-run capacitors have three terminals: C (common), FAN, and HERM (compressor) — test C-to-FAN and C-to-HERM separately
- Bulging or leaking capacitors do not need testing — replace on sight

**Motor Winding Resistance:**
- Disconnect power and all wires from the motor
- Single-phase: measure between Run and Start windings, and each to Common
- R-to-C plus S-to-C should roughly equal R-to-S
- If any reading is OL (open), the winding is burned open
- If any reading is near zero, windings are shorted together
- Three-phase motors: all three phase-to-phase readings should be within 5% of each other
- Typical small HVAC motor (1/4 to 1 HP): Run winding 2-8 ohms, Start winding 8-30 ohms
- PSC motor start winding will be higher resistance than run winding
- Any reading from any terminal to ground (motor frame) should be OL/infinity — any measurable reading to ground means the motor is grounded and must be replaced

**Amperage Draw vs Nameplate:**
- Every motor, compressor, and heater has a nameplate with rated amps
- Measure actual draw and compare:
  - Running at 80-100% of nameplate: normal operation
  - Running at 110%+: overloaded, low voltage, or failing component
  - Running well below nameplate: light load (could be normal or could mean loss of load like a compressor with no refrigerant)
- For compressors: low amps + high superheat = low charge. High amps + low superheat = overcharge or restricted airflow

### Troubleshooting Sequence: Voltage, Amperage, Resistance

Always follow this order:

1. **Voltage first** — Is power present? Is it correct? Check supply voltage at the equipment, then trace through switches, contactors, and safeties to find where voltage stops. Voltage present on one side of a switch but not the other = open switch or open safety
2. **Amperage second** — Is the load drawing current? Voltage present but amps zero means the load is open (burned winding, tripped internal overload). Amps high means the load is working too hard (mechanical binding, electrical short, excessive load)
3. **Resistance last** — De-energize and isolate the component. Measure windings, heating elements, or wire runs to confirm what you found in steps 1 and 2. Resistance testing confirms the diagnosis

---

## HVAC-Specific Tools & Measurements

### Manifold Gauge Set

**Setup and Connection:**
- Blue hose = low side (suction), connects to the larger suction line service port
- Red hose = high side (discharge), connects to the smaller liquid line service port
- Yellow hose = center port, goes to vacuum pump, refrigerant tank, or recovery machine
- Before connecting: crack each hose fitting briefly to purge air from hoses — prevents introducing non-condensables into the system
- Hand-tight on service port fittings plus 1/8 turn — overtightening damages Schrader valves

**Reading Pressures — R-410A:**
At 75F outdoor temp:
- Suction (low side): 118-130 psig
- Discharge (high side): 300-350 psig

At 95F outdoor temp:
- Suction: 125-145 psig
- Discharge: 375-425 psig

**Reading Pressures — R-22 (legacy systems):**
At 75F outdoor temp:
- Suction: 60-70 psig
- Discharge: 200-230 psig

At 95F outdoor temp:
- Suction: 70-80 psig
- Discharge: 250-290 psig

**Diagnostic Patterns:**
- High suction + high discharge = overcharge, bad TXV, or non-condensables
- Low suction + low discharge = undercharge or restriction
- Low suction + high discharge = restriction (likely liquid line or TXV)
- High suction + low discharge = weak compressor (valves not sealing)
- Never diagnose off pressure alone — always calculate superheat and subcooling

### Superheat and Subcooling Calculations

**Superheat (for systems with fixed metering — piston or capillary tube):**
- Formula: Superheat = Actual suction line temperature minus saturation temperature at suction pressure
- Measure suction line temp with a pipe clamp thermocouple, insulate the sensor from ambient air
- Read suction pressure, convert to saturation temp using PT chart (or gauge set does it automatically)
- Target: 10-15F for most residential AC with fixed metering
- High superheat (20F+): low charge, restricted liquid line, insufficient evaporator airflow, bad metering device
- Low superheat (below 5F): overcharged, TXV stuck open, excess liquid flooding back — this will kill the compressor

**Subcooling (for systems with TXV):**
- Formula: Subcooling = Saturation temperature at high-side pressure minus actual liquid line temperature
- Measure liquid line temp near the condenser outlet
- Read high-side pressure, convert to saturation temp
- Target: 8-14F for most residential TXV systems (check manufacturer spec — Carrier, Trane, Lennox, Goodman all publish specific targets)
- High subcooling (18F+): overcharged or restriction downstream
- Low subcooling (below 5F): undercharged, condenser fan problem, dirty condenser

**Charging by Superheat (Fixed Metering):**
- Use the manufacturer's charging chart if available — accounts for outdoor temp and indoor wet bulb
- No chart: target 10-15F superheat at 75-80F outdoor ambient
- Add refrigerant slowly to lower superheat, recover to raise it
- Wait 10-15 minutes between adjustments for system to stabilize

**Charging by Subcooling (TXV):**
- Much more reliable for TXV systems because the TXV controls superheat
- Target the manufacturer's specified subcooling (usually 8-14F)
- Add refrigerant to raise subcooling, recover to lower it
- Wait for stabilization between adjustments

**Cross-checking:**
- When both superheat is high and subcooling is low = undercharged
- When superheat is low and subcooling is high = overcharged
- When both are off in the same direction = airflow problem or restricted metering device

### Airflow Measurement

**Anemometer (Vane or Hot-Wire):**
- Measure velocity at supply registers in feet per minute (FPM)
- CFM = velocity (FPM) x area of register opening (sq ft)
- A 10"x6" register = 0.416 sq ft. At 500 FPM, that is 208 CFM through that register
- Hot-wire anemometers are more accurate at low velocities (under 200 FPM)
- Traverse the register face — take multiple readings across the opening and average them

**Static Pressure:**
- Use a manometer or digital pressure gauge — measure in inches of water column (in. WC)
- Drill small test holes (3/8") in supply and return plenums close to the air handler
- Insert static pressure probes
- Total external static pressure (TESP) = supply static + return static (both positive numbers when added)
- Supply side: typically +0.3 to +0.5 in. WC
- Return side: typically -0.1 to -0.3 in. WC (negative because it is suction)
- Most residential systems are rated for 0.50 in. WC TESP
- If you measure 0.80 in. WC, you have 60% more restriction than designed — dirty filter (check this first), undersized ductwork, collapsed flex, closed dampers, or blocked returns
- High static = reduced airflow = poor comfort, frozen coils, high amp draw, premature equipment failure

**CFM Calculation from Temperature Split:**
- BTU = 1.08 x CFM x temperature delta
- Rearrange: CFM = BTU / (1.08 x delta-T)
- A 3-ton (36,000 BTU) system with 20F split: CFM = 36,000 / (1.08 x 20) = 1,667 CFM
- Rule of thumb: 400 CFM per ton for standard efficiency systems
- 350 CFM/ton for high SEER units, 450 CFM/ton for dry climates

### Combustion Analyzer

**What It Measures and Acceptable Ranges (Natural Gas):**
- CO (carbon monoxide): ideally below 50 ppm air-free in the flue. Below 100 ppm generally acceptable for older equipment. Above 100 ppm = combustion problem (dirty burners, cracked heat exchanger, improper air/fuel ratio, flame impingement). Above 400 ppm air-free, shut it down immediately
- CO2: 8.5-9.5% for natural gas. Indicates air/fuel ratio. Low CO2 = excess air (dilution, draft issues). High CO2 = insufficient air (potential CO production)
- O2: 4-9% for natural gas. Inversely related to CO2. High O2 = excess air
- Stack temperature: 300-500F for standard efficiency (80% AFUE), 100-150F for condensing (90%+ AFUE). Standard furnace at 600F+ means scaled heat exchanger or unit oversized for ductwork
- Efficiency: 78-82% standard efficiency, 90-97% condensing. Calculated from other readings

**For Oil Appliances:**
- CO under 200 ppm air-free
- CO2 target 10-13%
- Stack temp 350-600F
- Smoke test: Bacharach smoke scale 0-1 (clean burn). Smoke number 3+ means dirty nozzle, wrong size nozzle, poor air adjustment, or failing heat exchanger

**Combustion Testing Procedure:**
1. Run the furnace for at least 5-10 minutes to reach steady state
2. Insert probe into flue pipe 6-12 inches from draft hood or vent connector
3. For condensing furnaces, insert in the PVC exhaust pipe before the first elbow (not the intake)
4. Wait 30-60 seconds for readings to stabilize
5. Record all readings
6. Check CO in the supply air plenum (not the flue) — should be 0 ppm. Any CO in supply air means cracked heat exchanger

**If CO is High, Check in Order:**
- Dirty burners (clean with a brush, no chemicals)
- Cracked heat exchanger (visual inspection plus combustion analyzer in all stages of fan operation)
- Gas pressure too high (check manifold pressure)
- Flame impingement (flame touching heat exchanger tubes — dirty or misaligned burner)
- Insufficient combustion air (blocked intake, inadequate room volume)

Brands: Testo 310 (entry-level workhorse), Testo 320, Bacharach Fyrite InTech, UEI C161. Calibrate sensors annually per manufacturer requirements.

### Temperature Split

- Cooling mode: supply air should be 16-22F cooler than return air
  - Below 15F split: low refrigerant charge, dirty evaporator, blower running too fast
  - Above 24F split: airflow too low (dirty filter, low fan speed), possibly iced coil
- Heating mode (gas furnace): supply air should be 40-70F warmer than return air
  - Below 35F split: blower running too fast, undersized furnace
  - Above 75F split: airflow too low, limit switch will trip
- Heat pump heating: supply air 15-30F warmer than return (much lower than gas because heat pump output is lower temperature)
- Measure at the register closest to the air handler for most accurate split, or at supply and return plenums directly

### Vacuum Pump and Micron Gauge

**Proper Evacuation Procedure:**
1. Connect vacuum pump to the center (yellow) hose of manifold set or directly to the system with a dedicated vacuum-rated hose (larger diameter = faster pulldown)
2. Open both manifold valves fully
3. Connect micron gauge directly to the system — not on the manifold, not on the hose. Valve core removers with ports are ideal
4. Run vacuum pump — change the oil if it is milky or dark before starting
5. Pull to 500 microns or below — this is the target
6. Close valves, shut off pump, watch micron gauge for 10 minutes
7. Decay test: if microns rise above 500 within 10 minutes and keep climbing steadily = leak. Find and fix it
8. If microns rise quickly to 1,000-2,000 then stabilize = moisture boiling off. Keep pulling vacuum longer
9. If microns hold below 500 for 10+ minutes = clean and tight. Proceed to charge

**Micron Scale Reference:**
- 25,400 microns = 1 inch Hg (standard rough vacuum gauges are useless for HVAC work)
- 1,000 microns = moisture may still be present
- 500 microns = industry standard target
- 200 microns = excellent, new install quality
- Below 50 microns = laboratory grade, not necessary for field work

### Refrigerant Scale Usage

- Always use a digital refrigerant scale when charging — guessing by feel or sight glass alone is not acceptable
- Tare the scale with the tank on it before opening valves
- Add refrigerant in liquid form to the high side (system off) or vapor to the low side (system running) — never liquid into the suction with the compressor running unless using a charging cylinder
- Weigh the charge — nameplate tells you factory charge (usually includes a set length of lineset, like 15 or 25 feet). Add or subtract refrigerant for different lineset lengths per manufacturer specs (typically 0.6 oz per foot of 3/8" liquid line for R-410A)
- For new installs: total system charge = factory charge + lineset adder. Weigh in the exact amount
- For service calls: if the system is empty, recover any remaining refrigerant, repair the leak, evacuate, then weigh in the full nameplate charge

### Leak Detection Methods

1. **Electronic leak detector:** Primary tool. Inficon D-TEK Select, Fieldpiece SRL2, Bacharach H-10 Pro. Sensitivity down to 0.1 oz/year. Move sensor slowly (1 inch per second) around joints, valves, Schrader caps. Start at the top and work down — most refrigerants are heavier than air. False positives near cleaning solvents, solder flux, adhesives. Change sensors annually
2. **Soap bubbles:** Spray commercial leak detector solution (Nu-Calgon Bubble Plus) or Big Blu on suspected joints. Pressurize system to at least 100 psig with nitrogen first. Bubbles = leak. Reliable but only works on accessible joints you can see
3. **UV dye:** Inject dye into the system, run for several hours, scan with UV flashlight. Bright yellow-green glow at leak site. Excellent for slow leaks electronic detectors miss. Use AC&R grade dye only, not automotive. Some manufacturers void warranties if dye is found
4. **Nitrogen pressure test:** Pressurize with dry nitrogen to 150-300 psig (check system rating — never exceed test pressure on nameplate). Isolate and watch gauge. Drop = leak. Use soap bubbles to pinpoint. Record pressure and ambient temp — pressure changes with temperature
5. **Standing pressure test:** Charge the system, let it sit overnight, re-check pressures. Account for temperature changes. Steady drop not correlating with temp change = leak

---

## Plumbing Tools & Measurements

### Pipe Sizing Calculations

**Fixture Unit Method (Residential):**
Each plumbing fixture has a fixture unit (FU) value:
- Toilet (tank type): 3 FU (flush valve type: 6 FU)
- Lavatory: 1 FU
- Bathtub/shower: 2 FU
- Kitchen sink: 2 FU
- Dishwasher: 2 FU
- Clothes washer: 2 FU
- Hose bib: 3 FU

Total the fixture units, then use your local code sizing chart (IPC or UPC):
- Up to 9 FU: 3/4" supply
- 10-22 FU: 1" supply
- 23-36 FU: 1-1/4" supply
- These assume 40-80 psi static pressure and reasonable developed lengths
- For long runs (over 100 feet from meter to furthest fixture), upsize by one diameter

**Drain Pipe Sizing:**
- 1-1/2" for single lavatory or bar sink
- 2" for bathtub, shower, or laundry standpipe
- 3" for toilet (some codes allow only 4" for building drain)
- 4" building drain/sewer for residential
- Slope: 1/4" per foot for pipes 3" and smaller, 1/8" per foot for 4" and larger (some codes require 1/4" per foot on everything — check local)

### Water Pressure Testing

**Static Pressure:**
- Attach a pressure gauge to a hose bib with nothing running
- Normal residential: 40-80 psi
- Below 40 psi: may need booster pump, check for partially closed valves, clogged aerators, galvanized pipe buildup
- Above 80 psi: install a pressure reducing valve (PRV) — high pressure damages fixtures, causes water hammer, wastes water
- Municipal water can vary 20+ psi between day and night — test at peak demand if you suspect pressure issues

**Dynamic Pressure:**
- Open a fixture (farthest from the meter) and read the gauge
- Pressure drop more than 10-15 psi from static indicates undersized pipe, partially closed valve, or heavy mineral buildup
- Run multiple fixtures simultaneously to stress-test the system

**Hydrostatic Pressure Test (New Piping):**
- Fill system with water, pressurize to 1.5x working pressure (typically 150 psi for residential supply)
- Hold 2-4 hours minimum (some codes require 24 hours)
- No drop in pressure = pass. Any drop = leak, find and repair

### Gas Pressure Testing

**Natural Gas:**
- Measured in inches of water column (in. WC) with a manometer
- Standard residential supply pressure at the meter: 7-14 in. WC (varies by utility)
- Manifold pressure at the furnace gas valve: 3.5 in. WC for natural gas
- Measure at the pressure tap on the gas valve while the burner is firing
- Below 3.2 in. WC: undersized gas line, low supply pressure, or regulator problem
- Above 3.8 in. WC: regulator set too high
- Also check inlet pressure: should be 5.0-7.0 in. WC minimum at the appliance under fire. Below 5.0 when firing = gas line undersized or restricted
- Gas valve regulator adjustment: on Honeywell VR8205 or White-Rodgers 36J, the adjustment is under a cap on the valve body. Clockwise to increase, counterclockwise to decrease
- Gas line pressure test: pressurize to 3 psig (83 in. WC) with a diaphragm gauge, hold 15 minutes — no drop = pass. Some codes require 10 psig for 24 hours on new installs

**Propane (LP):**
- Supply pressure at first-stage regulator: 10 psi
- Second-stage regulator outlet: 11 in. WC (standard residential)
- Manifold pressure at appliance: 10-11 in. WC for propane
- Propane has roughly 2x the BTU content of natural gas per cubic foot — orifices must be sized smaller for LP
- Never operate a natural gas appliance on propane without converting — higher pressure and BTU content will cause overfire, CO production, and potential fire

### Drain Camera Basics

**What to Look For:**
- Roots: hairy intrusions through joints, most common in clay and cast iron
- Bellies: low spots where water pools and debris collects, causing slow drains
- Offsets: pipe joints that have shifted — one pipe higher or lower than the next. Minor offsets may not need repair; severe offsets snag solids
- Cracks and fractures: longitudinal cracks in clay pipe are common. If still round, a liner may work. If collapsed, you are digging
- Scale and buildup: cast iron develops tuberculation (rust nodules) reducing effective diameter. Old galvanized drain lines are often 50%+ occluded
- Orangeburg pipe: compressed tar paper from the 1950s-70s — deforms, collapses, must be replaced. Cannot be reliably lined

**Locating:** Use the camera's built-in sonde (transmitter) and a locator on the surface to mark exact position and depth. Mark with paint before digging.

### Soldering and Brazing Techniques

**Soldering (Copper Supply Lines):**
- Clean pipe and fitting with emery cloth or sandpaper — bright copper, no oxidation
- Apply flux (water-soluble preferred for potable water) to both surfaces
- Assemble the joint, heat the fitting (not the solder) with propane or MAP gas torch
- Touch solder to the joint opposite the flame — capillary action pulls it in when temperature is right (roughly 450F for lead-free solder)
- Lead-free solder required on all potable water systems — no exceptions
- Wipe joint with damp rag while still hot for clean finish
- Drain and dry pipes before soldering — steam pressure in a wet pipe will blow out the solder. Bread trick: stuff white bread into the pipe upstream to absorb residual water, it dissolves and flushes out later

**Brazing (Refrigerant Lines):**
- Use 15% silver brazing alloy (silfos/Sil-Fos) for copper-to-copper — no flux needed (self-fluxing)
- Use 45% silver with flux for copper-to-brass or dissimilar metals
- Flow nitrogen through the pipe while brazing at 2-5 CFH (just a whisper) — prevents copper oxide scale inside the pipe which clogs metering devices and compressor oil passages
- Heat with oxy-acetylene or air-acetylene — propane does not get hot enough for brazing
- Cherry red color on copper means brazing temperature (1,100-1,500F depending on alloy)
- Keep flame moving — do not burn through the pipe wall
- Let cool naturally, do not quench with water (thermal shock can crack the joint)
- Pressure test with nitrogen to 150% of working pressure before evacuation

### PEX Connection Methods

**Crimp (Copper Rings):**
- Slide copper crimp ring over PEX, insert brass fitting, position ring 1/8" to 1/4" from end, compress with crimp tool
- Use go/no-go gauge to verify every crimp — if the go side does not pass, re-crimp or cut and redo
- Advantages: cheapest tooling and fittings, widely accepted
- Disadvantages: copper rings can corrode in aggressive water, crimp tool needs annual calibration

**Expansion (ProPEX / Uponor):**
- Slide expansion ring over PEX, expand PEX end with expansion tool (3-4 expansions), insert fitting quickly while PEX is still expanded
- PEX memory shrinks it back around the fitting — connection gets tighter over time
- Must use PEX-a tubing (not PEX-b or PEX-c)
- Advantages: strongest connection, full-flow fittings (no ID reduction), can be buried in concrete
- Disadvantages: most expensive tooling, PEX-a tubing costs more

**Push-Fit (SharkBite):**
- Deburr and mark insertion depth on the PEX, push straight into fitting until it hits the stop
- Stainless steel teeth grip the pipe, O-ring seals
- Advantages: no tools needed, fastest method, can join PEX to copper to CPVC
- Disadvantages: most expensive per fitting, O-rings can fail in high-heat or UV exposure, not all codes allow them concealed in walls. Many inspectors flag concealed SharkBites

### Thread Sealant Selection

- **PTFE (Teflon) tape:** Yellow for gas (thicker, rated for gas), white for water. Wrap 3-5 times clockwise (as you look at the threads facing you). Do not use white tape on gas — it is thinner and not rated
- **Pipe dope (thread sealant compound):** Use on all metal-to-metal threaded joints. Apply to male threads only. Rectorseal No. 5 or Megaloc are common. Use gas-rated dope on gas lines
- **Combination:** Many pros use tape plus dope together — tape fills thread valleys, dope lubricates and fills micro-gaps. Belt and suspenders approach
- **When NOT to use sealant:** Flare fittings (metal-to-metal cone is the seal), compression fittings (ferrule is the seal), any fitting with a built-in O-ring or gasket

---

## General Construction Measurement

### Laser Level Usage

**Line Laser (Self-Leveling):**
- Projects one or more laser lines on walls and surfaces
- Best for: interior finish work, cabinet installation, tile layout, electrical box heights, drop ceiling grids
- Range: 30-100 feet depending on model, less in bright sunlight
- Green lasers (Bosch GLL3-330CG, DeWalt DW089K) are more visible than red in bright conditions
- Always verify level by rotating 180 degrees and checking if the line hits the same mark — this is your calibration check

**Rotary Laser:**
- Projects a spinning dot creating a 360-degree horizontal (or vertical) plane
- Best for: grading, foundation work, large commercial spaces, setting forms, bulk excavation
- Use with a detector/receiver on a grade rod for outdoor work where you cannot see the beam
- Range: 100-2,000 feet with detector depending on model (Spectra Precision, Topcon, DeWalt)
- Setup: mount on tripod over known benchmark, shoot rod at benchmark to establish reference, then shoot all other points relative to that

### Transit / Builder's Level for Grading

- Optical instrument on a tripod — look through eyepiece, read a stadia rod at the target point
- Set up on tripod, level the instrument, sight through eyepiece to grade rod held by helper
- Read the rod where the crosshair intersects — if rod reads 4'6" at the benchmark and 5'2" at the target, the target is 8" lower than the benchmark
- Accuracy: 1/8" per 100 feet for a basic builder's level
- Always turn instrument 180 degrees and re-shoot to verify — average two readings to cancel instrument error (two-peg test)
- For establishing grade (slope): calculate needed drop per foot. Sewer is 1/4" per foot for 4" pipe, 1/8" per foot for 6" pipe. Starting invert at 100.00' going 50 feet at 1/4" per foot = ending invert at 98.96' (100.00 - (50 x 0.0208))

### Tape Measure Tricks

**Reading Fractions:**
- Every mark has a value: 1/16" smallest, then 1/8", 3/16", 1/4", 5/16", 3/8", 7/16", 1/2", and so on
- Taller marks = larger fractions. Use mark height to quickly identify the fraction
- When calling out: "six and three-eighths" means 6-3/8". Always reduce fractions (say 3/8, not 6/16)

**Burning an Inch:**
- The hook on the end has deliberate play which can introduce error on precise measurements
- Instead of hooking the end, align the 1" mark with your starting point, measure from there, subtract 1" from your reading
- Essential for cabinet work, finish carpentry, layout work where 1/16" matters

**Inside Measurements:**
- Extend tape into opening, press case against one side, add case length (usually 3" or 3-1/4" — printed on the case) to the tape reading
- Or use two tape measures overlapping from each side and add readings

### Speed Square Usage

**Roof Pitch:**
- Hold square with pivot point against rafter edge, lip hooked on top edge
- Pivot until desired pitch number on the common rafter scale aligns with rafter edge
- Mark along the body = plumb cut (vertical) line
- Perpendicular to that = level cut (seat cut)
- Common pitches: 4/12 (low slope, minimum for shingles), 6/12 (standard), 8/12 (steep), 12/12 (45 degrees)

**Angle Cuts:**
- Degree scale goes 0 to 90
- For 45-degree miter: align 45-degree mark with board edge
- Pitch to degree conversion: 4/12 = 18.4 degrees, 6/12 = 26.6 degrees, 8/12 = 33.7 degrees, 12/12 = 45 degrees

**Stair Layout:**
- Total rise / desired riser height = number of risers (round to nearest whole number)
- Total rise / number of risers = actual riser height
- Tread depth: code minimum usually 10" residential (check local code)
- Riser + tread should equal 17-18" for comfortable stairs (7" riser + 11" tread = 18")
- Use the speed square to mark stringer cuts: set rise on one leg, run on the other, step along the stringer

### String Line for Straight Runs

- For fence, footer, block wall, or grading alignment
- Pull tight — sag is the enemy of accuracy. Use intermediate stakes on runs over 50 feet
- Nylon line stretches less than cotton
- For block/brick walls: set string at top of each course, move up as you go — string is your straight edge for the entire wall face
- Use line blocks (L-shaped clips) on corner blocks to hold string at the right height without nails

### Plumb Bob and Digital Level

**Plumb Bob:**
- Hang from point overhead, wait for bob to stop swinging, point below is directly plumb (vertical) under the hang point
- Used for transferring points ceiling to floor, checking wall plumb, centering overhead fixtures
- Brass or steel, 8-16 oz typical — heavier bobs settle faster in wind
- Outdoors: shelter from wind or it is useless

**Digital Level:**
- Reads degrees, percent slope, and pitch (rise/run)
- More readable than bubble level for precise work
- Place on surface: 0.0 degrees = level, 90.0 = plumb
- Most accurate within 0.1 degree — far better than eyeballing a bubble
- Check calibration by reading a surface, then rotating 180 degrees on the same surface — readings should match

### Measuring for Square

**3-4-5 Method:**
- From a corner, measure 3 feet along one wall and mark
- Measure 4 feet along the other wall and mark
- Diagonal between those two marks should be exactly 5 feet if the corner is 90 degrees
- Scale up for larger areas: 6-8-10, 9-12-15, 12-16-20 — any multiple works
- Accuracy increases with larger triangles — use 12-16-20 on foundation layout

**Diagonal Measurement:**
- For a rectangle to be square, both diagonals must be equal
- Measure corner to corner both ways — if they match, it is square
- If diagonal A is 1/2" longer than diagonal B, shift one side until they equalize
- Fastest way to square a deck frame, foundation, or wall section

---

## Power Tools

### Circular Saw

**Blade Selection:**
- 24-tooth: fast ripping in framing lumber, rough cuts, rougher edge
- 40-tooth: general purpose crosscutting and ripping in plywood and dimensional lumber
- 60-80 tooth: finish cuts in plywood, melamine, hardwood — slower but clean
- Carbide-tipped blades last 10x longer than steel on treated lumber
- Fiber cement (Hardie board): use polycrystalline diamond (PCD) blade or 4-tooth fiber cement blade. Standard wood blades create dangerous silica dust and dull instantly

**Depth Adjustment:**
- Set blade depth so only 1/4" of tooth protrudes below material — less exposure = cleaner cut, less kickback risk
- For plywood: shallow depth reduces tearout on bottom face
- Cut good face down with standard circular saw (blade enters from bottom)

**Kickback Prevention:**
- Support material so the cut-off piece falls away freely — never let the kerf close on the blade
- Do not force the saw — let blade speed do the cutting
- Never start saw with blade touching material
- Keep blade guard functional — do not pin it back
- Riving knife or splitter should be installed for ripping cuts

### Reciprocating Saw

**Blade Selection by Material:**
- Wood with nails (demolition): bi-metal, 6-12 TPI, 6-9" long
- Clean wood: 6 TPI, aggressive cut
- Metal pipe and conduit: 18-24 TPI, bi-metal — more teeth for thinner material
- Cast iron: carbide-grit blade (no teeth, abrasive edge)
- PVC/ABS pipe: 10-14 TPI wood blade works fine
- Pruning: special pruning blades with wide set teeth for green wood
- General rule: at least 3 teeth in contact with material at all times. If you see daylight between teeth and material, use a finer blade

### Drill vs Impact Driver

**Drill (Standard Chuck):**
- Use for: drilling holes, driving screws into soft material, mixing compounds
- Has a clutch for torque control — set low for small screws, high for lag bolts
- 3-jaw chuck accepts round and hex shank bits
- Variable speed trigger gives fine control

**Impact Driver:**
- Use for: driving screws and bolts, especially long fasteners and lag screws
- Delivers rotational impacts (concussive blows) multiplying torque without twisting your wrist
- 1/4" hex collet — only accepts hex shank bits
- No clutch — control depth with trigger and feel
- Will snap small screws and strip cam-out heads if not careful
- Do not use for drilling precision holes — impacts cause bit wander

**When to Use Which:**
- Drilling into wood, metal, concrete: standard drill (or hammer drill for concrete)
- Driving 3" deck screws: impact driver
- Driving #6 finish screw: drill with clutch set low
- Driving 1/2" lag bolts: impact driver with socket adapter
- Tapping threads: standard drill at low speed

### Rotary Hammer for Concrete

- For drilling into concrete, block, brick, stone
- SDS or SDS-Max bit system (bits lock in, no chuck key)
- Three modes: drill only, hammer-drill (standard concrete mode), hammer only (light chiseling)
- Use hammer-drill with carbide-tipped SDS bits for anchor holes
- Always use depth stop rod for consistent anchor hole depth
- Let tool do the work — pushing hard does not make it faster, overheats the bit
- Dust collection shroud or HEPA vacuum required in many jurisdictions for OSHA silica compliance (Table 1)
- Common anchor hole sizes: 1/4" for 1/4" sleeve anchors, 3/8" for 3/8" wedge anchors, 1/2" for 1/2" wedge anchors, 5/8" for 1/2" Tapcons

### Oscillating Multi-Tool Applications

- The Swiss army knife of power tools — vibrates a blade in a small arc
- Flush-cut wood: trim door casings for flooring, cut nails behind trim
- Plunge cuts in drywall or plywood: cut outlet boxes, register openings without pilot hole
- Scrape adhesive, thinset, or caulk: flat scraper blade
- Sand in tight corners: triangle sanding pad
- Cut PVC, copper, galvanized in tight spaces where full-size saw will not fit
- Let blade speed do the work, do not force sideways. Use the right blade for the material. Blades dull fast — buy in bulk

### Angle Grinder

**Disc Selection:**
- Cutting metal: thin cut-off wheel (0.045" for steel/stainless). Use only the edge, never the face
- Grinding welds: grinding disc (1/4" thick). Use face at 15-30 degree angle
- Cutting masonry/concrete: diamond blade (continuous rim for clean cuts, segmented for fast cuts)
- Wire wheel/cup brush: removing paint, rust, scale
- Flap disc: blending welds, smoothing metal — more forgiving than grinding disc for finish work

**Safety:**
- Always use guard — position between disc and your body
- Face shield plus safety glasses, not just glasses
- RPM rating on disc must meet or exceed grinder RPM (4-1/2" grinder typically runs 10,000-11,000 RPM)
- Never use cut-off wheel for grinding (side load) — it can shatter
- Let grinder reach full speed before engaging workpiece
- Secure workpiece — never grind anything that can spin or catch

### Pipe Threader Operation

- For threading black iron, galvanized, sometimes stainless
- Manual (ratchet type) or power (motor-driven) — power threaders for 2" and up
- Cut pipe square with a pipe cutter (not hacksaw — uneven cuts = leaky threads)
- Ream inside edge to remove burr (burr restricts flow and catches debris)
- Always use cutting oil — flood dies during the cut. Dry threading produces rough, leaking threads and destroys dies
- Die head must match pipe size exactly: 1/2", 3/4", 1", 1-1/4", 1-1/2", 2"
- Thread length standards: 1/2" pipe = 0.5" thread, 3/4" = 0.55", 1" = 0.68", 1-1/4" = 0.71", 1-1/2" = 0.72", 2" = 0.76"
- After threading: deburr inside with reamer (built into most pipe cutters). Metal shavings inside gas pipe end up in appliance gas valves
- Check threads with ring gauge or thread a fitting on — should start by hand and tighten snugly with wrench within 3-4 turns past hand-tight

---

## Diagnostic Equipment

### Thermal Imaging Camera

**What Patterns Mean:**
- Hot spots on electrical panels: loose connections, overloaded breakers. Connection 20F+ hotter than adjacent is a problem. 50F+ above ambient is an emergency
- Cold spots on walls in winter: missing insulation, air infiltration. Thermal bridging at studs is normal — cold patches between studs are not
- Hot suction line on AC: system starved for refrigerant (high superheat)
- Wet spots on ceilings/walls: show as cooler areas from evaporative cooling — reveals leaks before visible damage
- Radiant floor heating: verify even heat distribution and locate buried tubing runs
- Ductwork: find disconnected or leaking joints — cold air in the attic in summer stands out clearly
- Overheating motors or bearings: compare to adjacent identical equipment for reference

**Emissivity Settings:**
- Emissivity = how well a surface radiates heat, affects reading accuracy
- Painted surfaces, wood, drywall: 0.90-0.95 (most cameras default to 0.95, close enough for field work)
- Bare metal (aluminum, copper, galvanized): 0.05-0.30 — shiny metal gives wildly inaccurate readings. Clean copper reads falsely low. Apply electrical tape or paint a spot and measure that instead
- Oxidized or rusted metal: 0.60-0.80 — more reliable but still lower than painted surfaces
- For comparison shots (finding relative differences), exact emissivity does not matter as long as surfaces are the same material — you are looking for anomalies, not absolute numbers

Camera brands: FLIR C5, C3X for entry-level field work. FLIR E-series or Fluke TiS for higher resolution. The difference shows in detail — a $300 camera finds obvious problems, a $1,500 camera finds subtle ones.

### Borescope / Inspection Camera

- Flexible camera on a cable, 3-10 mm diameter, viewed on handheld screen or phone
- Use for: looking inside walls through small holes, inspecting equipment interiors (heat exchangers, drain lines), checking behind panels and above ceilings without full demolition
- LED lights on tip, adjustable brightness
- Articulating tips (on better models) let you steer around corners
- HVAC uses: check evaporator coils for blockage, inspect secondary heat exchangers for cracks, look inside ductwork for mold or debris
- Plumbing: temporary camera for short drain runs where full sewer camera is overkill
- Drill a 1/2" hole to peek inside a wall cavity — far less damage than cutting drywall

### Smoke Pencil for Air Leak Detection

- Generate a small stream of visible smoke and hold near suspected leak points
- Smoke deflects toward low-pressure areas (leaks pulling air in) or blows away from high-pressure leaks (air pushing out)
- Common uses:
  - Check draft on atmospheric water heaters and furnaces — smoke should pull into draft hood, not push out. Pushing out = backdrafting = carbon monoxide hazard
  - Find ductwork leaks — pressurize duct system with blower, watch smoke at joints
  - Building envelope leaks during blower door test — smoke shows exactly where air infiltrates
  - Verify negative pressure in mechanical rooms — smoke should be drawn in at the door
- Chemical smoke tubes (break-the-tip style) are single-use, produce fine consistent smoke
- Fog machines produce more visible smoke for larger areas but harder to control for pinpoint location

### Refrigerant Identifiers

- Portable device that analyzes a refrigerant sample and identifies what is in the system
- Absolutely essential before recovery — mixing incompatible refrigerants contaminates recovery equipment and your tank
- Identifies R-22, R-134a, R-410A, R-404A, hydrocarbons (propane/isobutane), and most common blends
- If identifier shows a mix or unknown, the system is contaminated — recover into a dedicated contaminated tank and send for reclamation
- Some identifiers also detect air (non-condensables) — more than 2% air means recovery and proper evacuation needed before recharging
- Cost justified by one avoided cross-contamination event — a contaminated 50 lb recovery tank costs hundreds to deal with

### Combustible Gas Detector

- Handheld electronic sniffer detecting natural gas (methane) and propane
- Sensitivity ranges from 50 ppm to LEL (lower explosive limit) — field detectors typically alarm at 10% of LEL
- LEL for natural gas: approximately 5% concentration in air (50,000 ppm). LEL for propane: approximately 2.1% (21,000 ppm)
- Move slowly along pipe joints, unions, valves, flex connectors — leaks are most common at connections
- Cross-sensitivity: some detectors pick up solvents, cleaning chemicals, sewer gas — do not mistake Windex for a gas leak
- If detector alarms at a specific point, confirm with soap bubbles — electronic detector gets you to the area, bubbles pinpoint the exact spot
- Calibrate per manufacturer schedule — uncalibrated detector is worse than no detector because it gives false confidence
- In enclosed spaces, check with detector BEFORE entering — combustible gas in a confined space is an explosion and asphyxiation risk
- Top brands: Tif 8800A, Bacharach Leakator 10, Sensit Gold G2. Gas company odor (mercaptan): if you smell gas, trust your nose. Evacuate, do not operate electrical switches, call the gas company
- Never use a flame to check for gas leaks

---

## Quick Reference: Key Numbers

| Measurement | Target / Normal Range |
|---|---|
| Residential voltage (120V circuit) | 114-126 VAC |
| Residential voltage (240V circuit) | 228-252 VAC |
| 24V transformer secondary | 24-28 VAC |
| Capacitor tolerance | +/- 6% of rated value |
| R-410A suction pressure (cooling, 75F) | 118-130 psig |
| R-410A discharge pressure (cooling, 75F) | 300-350 psig |
| R-22 suction pressure (cooling, 75F) | 60-70 psig |
| R-22 discharge pressure (cooling, 75F) | 200-230 psig |
| Superheat target (fixed metering) | 10-15F |
| Subcooling target (TXV) | 8-14F |
| Vacuum evacuation target | 500 microns |
| Cooling temperature split | 16-22F |
| Gas heating temperature split | 40-70F |
| Heat pump heating split | 15-30F |
| Total external static pressure (residential) | 0.50 in. WC design |
| Airflow per ton of cooling | 400 CFM standard |
| Residential water pressure | 40-80 psi |
| Natural gas manifold pressure | 3.5 in. WC |
| Propane manifold pressure | 10-11 in. WC |
| Drain slope (3" and smaller) | 1/4" per foot |
| Drain slope (4" and larger) | 1/8" per foot (varies by code) |
| CO in supply air | 0 ppm (any is a problem) |
| CO in flue gas (air-free, gas furnace) | Under 100 ppm |
| CO in flue gas (air-free, oil) | Under 200 ppm |
| Motor insulation resistance (minimum) | 1 megohm per kV + 1 megohm |
| Three-phase voltage imbalance max | 2% |
| Three-phase amp imbalance max | 5% |
| Comfortable stair formula | Riser + tread = 17-18" |
| 3-4-5 squaring check | 3' x 4' x 5' (or any multiple) |
| Hydrostatic test pressure (residential) | 150 psi (1.5x working) |
| Nitrogen leak test (refrigerant) | 150-300 psig |
| Compressor winding to ground (megger) | 50+ megohms healthy |
| Riser height code max (residential) | 7-3/4" (check local) |
| Tread depth code min (residential) | 10" (check local) |
