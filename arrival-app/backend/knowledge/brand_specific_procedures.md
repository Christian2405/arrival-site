# Brand-Specific Service Procedures & Diagnostics

Field-level diagnostic procedures, common failures, and the gotchas that trip techs up on brands that don't get enough coverage in generic training. Written from the truck, not the classroom.

---

## CARRIER / BRYANT (Same Manufacturer, Different Label)

### Accessing Fault History — Infinity/Evolution Communicating Systems

Carrier Infinity and Bryant Evolution are the same system with different badges. The Infinity Control (Systxccitc01) stores the last 10 faults.

To access fault history:
1. Press and hold MODE + FAN simultaneously for about 5 seconds
2. Display changes to service mode — you'll see "SERVICE" or a wrench icon
3. Scroll with up/down arrows to navigate fault codes
4. Each fault shows: code number, date/time, outdoor temp at time of fault
5. To exit, press MODE + FAN again or wait 10 minutes for auto-exit

If you have the older Infinity Control (non-touchscreen), the button combo is the same but you navigate with the physical arrows.

On systems with a standard (non-communicating) thermostat, fault codes display as LED blinks on the furnace control board. Count the RED LED blinks — that's your code. The board also has a code history if you look at the diagnostic LEDs during the startup sequence.

### Common Infinity/Evolution Fault Codes

**Code 46 — Low Pressure Lockout**
- System detected low refrigerant pressure
- Check charge first — Carrier systems are notoriously sensitive to undercharge
- Check for restrictions: filter drier, TXV, kinked lineset
- On Greenspeed units, the EEV can stick partially closed and mimic a restriction
- If charge is correct and pressures look normal at the gauges, check the low pressure transducer. These fail. They read incorrectly and the board locks out on a phantom fault
- Transducer is on the suction line at the outdoor unit. Measure actual pressure with your gauges and compare to what the board is reading (visible in service mode)

**Code 47 — High Pressure Lockout**
- Dirty outdoor coil is #1 cause. These coils pack up with cottonwood and dandelion fuzz
- Check condenser fan motor — is it running? Is it running at the right speed?
- On variable speed units, the fan might be running slow due to a failing motor or board issue
- Verify outdoor fan capacitor (on single-speed units)
- Check for refrigerant overcharge — previous tech may have dumped in too much
- Non-condensables in the system (air) from a bad vacuum or previous leak repair
- Ambient temperature lockout — some older models lock out above 115F outdoor temp

**Code 76 — Communication Loss Between Indoor and Outdoor**
- This is the most common Infinity system fault, and it drives techs crazy
- The communicating bus uses 4 wires: R, C, and two data lines (1 and 2)
- First: verify you have 24VAC between R and C at both ends
- Check for damaged communication wires — rodent damage is common
- Verify the SAM (System Access Module) on the outdoor unit is functioning — the green LED should be blinking steadily
- If you replaced ANY component (board, thermostat, SAM), you may need to re-commission the system. The Infinity system auto-detects components but sometimes needs a full reset
- Reset procedure: turn off power to ALL equipment for 60 seconds, restore indoor first, then outdoor. Wait 5 minutes for auto-detection
- If that doesn't work, you may need to manually configure via the Infinity Control: go to service mode, select "Install," and run through the component detection
- Common gotcha: if someone ran standard thermostat wire (4-conductor) instead of shielded communication cable, you'll get intermittent comm faults. Carrier specs shielded cable for the data bus

**Code 84 — Outdoor Coil Temperature Sensor Fault**
- Sensor is a thermistor clipped to the outdoor coil
- Check resistance: should be approximately 10K ohms at 77F (25C)
- Common failure: sensor clip breaks and sensor falls off coil, reads ambient instead of coil temp
- On heat pump systems, this causes defrost issues — system can't tell when the coil is actually frozen
- Replace with OEM sensor. Aftermarket thermistors with different curves will cause charging errors since the board uses this sensor for charge verification

### 59MN7 / 59TP6 Furnace Common Issues

**Inducer Motor Failure**
- The 59MN7 (Carrier) and 58TP (Bryant) modulating furnaces use a variable-speed inducer
- The inducer on these is a known failure point after 8-10 years
- Symptoms: unit tries to start, inducer runs but sounds rough, pressure switch won't close
- Before replacing the inducer, check for condensate drain blockage. A plugged drain backs water into the inducer housing and kills the motor. If you replace the inducer without clearing the drain, you'll be back in 6 months
- Inducer motor part numbers changed several times — verify by serial number, not model number

**Pressure Switch Issues**
- Modulating furnaces often have TWO pressure switches (one for each stage or a redundant safety)
- If pressure switch won't close: check inducer operation, drain lines, flue for blockage, and vent termination for ice/debris
- Measure actual draft with a manometer — compare to the switch rating stamped on the switch body
- Common trick: temporarily bypass with a jumper to confirm the switch is the problem vs. actual draft issue. Never leave a jumper in place
- On the 59MN7, a cracked collector box (where the inducer mounts) causes draft leaks that prevent the switch from closing

**Ignition Sequence**
- Carrier furnaces use HSI (hot surface igniter) — silicon carbide or silicon nitride
- Sequence: thermostat call → inducer starts → pressure switch closes → igniter heats (15-30 seconds) → gas valve opens → flame sensor confirms flame
- If igniter doesn't glow: check 120VAC at igniter harness. If voltage present and no glow, igniter is cracked or open (they crack invisibly — you can't always see it)
- Silicon nitride igniters (white/gray) last longer than silicon carbide (black). Carrier switched to nitride in newer models
- Don't touch silicon carbide igniters with bare hands — oils from skin create hot spots that cause cracking

**Flame Sensor**
- Carrier flame sensors get coated with a white oxide layer
- Clean with fine emery cloth or a dollar bill — just rough enough to remove the oxide
- Normal flame sense current: 1-6 microamps DC. Below 1 microamp, the board will shut off gas
- Carrier boards are pickier about flame sense than some other brands — 1.5 microamps might work on a Rheem but cause intermittent lockout on a Carrier
- If cleaning doesn't fix it, check the ground. Poor furnace ground = low flame sense current

### 24ACC / 24ANB Condenser Common Failures

**Contactor**
- Single most common failure on these condensers
- Symptoms: outdoor fan runs but compressor doesn't (or neither runs)
- Check: 24VAC at the coil terminals. If present and contactor won't pull in, replace
- If contactor is welded closed (contacts stuck together), compressor runs nonstop, even with no call. This burns up compressors
- Inspect contact points for pitting — pitted contacts increase resistance and cause voltage drop to the compressor

**Capacitor**
- Carrier uses dual-run capacitors (combined compressor + fan motor cap)
- Test with a capacitance meter, not just an ohm meter
- Spec is printed on the capacitor body — a 45/5 MFD cap should test within 5-10% of rated value
- Swollen or bulging top = definitely bad. But capacitors can test bad without visible damage
- If the cap is even slightly low on the compressor side, you'll see high amp draw and eventually a compressor overheat lockout

**Fan Motor**
- These condensers use PSC motors with a run capacitor
- Common failure after 12-15 years
- If motor hums but won't start, check capacitor first — it's cheaper than the motor
- Replacement motors: match HP, RPM, rotation direction, shaft size, and number of speeds
- Carrier-specific gotcha: some models have a slinger ring on the fan motor shaft that slings condensate onto the outdoor coil to improve efficiency. If you install a universal motor without the slinger feature, efficiency drops and head pressure runs higher

### Greenspeed / Variable-Speed Heat Pump Diagnostics

- Greenspeed uses a variable-speed inverter compressor
- The inverter board is the most expensive component — don't condemn it without thorough testing
- Common symptoms of inverter failure: unit cycles on and off rapidly, compressor won't ramp up, error codes related to compressor current or IPM (Intelligent Power Module)
- Check DC voltage from inverter board to compressor: should see variable DC (not AC) during operation
- If compressor windings are shorted, the inverter board may also be damaged — always check compressor resistance before powering up a new inverter board
- Compressor winding resistance should be balanced (all three legs within 0.5 ohms of each other) and no reading to ground
- Charge procedure on Greenspeed: use the subcooling method. These systems are critical on charge — even 2 oz off affects performance noticeably because the EEV compensates and masks the problem until it can't anymore

### Carrier Refrigerant Charge Procedures (R-410A / Puron)

- Carrier recommends subcooling method for TXV systems and superheat for piston/orifice
- Target subcooling: typically 8-12F, but CHECK THE DATA PLATE on the specific unit
- Weigh in the charge whenever possible — Carrier publishes factory charge and charge-per-foot of lineset
- For linesets longer than factory spec (usually 15-25 feet depending on model), add refrigerant per the chart on the unit data plate
- Carrier units with the Infinity system can display live subcooling and superheat on the thermostat in service mode — use this to verify your gauge readings
- Never charge in heat mode on a heat pump unless you specifically follow the heat mode charging chart (different target values)
- R-410A operates at significantly higher pressures than R-22. Don't use R-22 gauge hoses — they'll blow out. Use 800 PSI rated hoses minimum

---

## MITSUBISHI ELECTRIC (Mini-Split / Hyper-Heating Leader)

### Error Code System

Mitsubishi uses two error display methods:
1. **LED blink codes on the indoor unit** — the operation light blinks a pattern
2. **Alphanumeric codes on the remote control** — shows letter + number combo

To see the error code on the remote: some models display it automatically. On others, press the "CHECK" button if your remote has one.

On the indoor unit, count the blinks of the operation (green) light. The pattern repeats after a pause. Some units also use the timer (orange) light for a second digit.

### Common Mitsubishi Error Codes

**P8 — Piping (Refrigerant) Error**
- System detected abnormal refrigerant conditions
- Most common cause: refrigerant leak or incorrect charge
- Check all flare connections — Mitsubishi flares are the #1 leak point
- Verify charge by measuring superheat and subcooling, compare to Mitsubishi's charging chart (different from other brands)
- On multi-zone systems, P8 on one zone might actually be a system-wide charge issue
- Also check: kinked lineset, plugged filter drier (if one was installed — Mitsubishi doesn't use them stock on most residential units), or a stuck EEV

**E6 — Indoor/Outdoor Communication Error**
- Communication between indoor and outdoor units has failed
- Check wiring: Mitsubishi uses 3-wire communication (power + signal on the same cable). The three wires are typically labeled S1, S2, S3 (or numbered 1, 2, 3)
- Verify 230VAC between terminals 1 and 2 at the outdoor unit
- Signal voltage between terminal 3 and terminal 2 should be pulsing (you'll see varying DC voltage with a meter)
- If voltage is correct at outdoor but indoor shows E6: check the cable run for damage
- Common cause: incorrect wire gauge. Mitsubishi requires minimum 14 AWG for most residential units. 18 AWG thermostat wire will NOT work — the power circuit draws too much current
- After any board replacement, power cycle the entire system (both indoor and outdoor) for at least 60 seconds off

**U4 — Outdoor Unit Board Failure or Abnormality**
- Usually means the outdoor control board has detected an internal fault
- This can be a board failure, but check these first: loose board connector (vibration causes them to work loose), water intrusion into the electrical box, or a shorted sensor feeding the board bad data
- Check the outdoor board for visible damage — burned components, swollen capacitors, corroded pins
- If the board looks clean, check all sensors connected to it. A shorted thermistor can cause U4

**P1 — Intake Air Temperature Sensor Error**
- The room temperature sensor in the indoor unit is reading out of range
- Sensor is a thermistor, usually clipped near the air intake grille
- Check resistance: approximately 10K ohms at 77F
- Common cause: sensor wire pinched during installation or filter change
- Quick test: measure resistance and compare to Mitsubishi's thermistor chart. If it reads open or shorted, replace

**E1 — Remote Controller Signal Error**
- Indoor unit isn't receiving signal from the remote
- First: replace remote batteries (yes, really — this is the fix 40% of the time)
- Check for IR interference — some LED lights interfere with the IR sensor on the indoor unit
- If using a wired remote (PAR series), check wiring continuity
- The IR receiver on the indoor unit can fail — it's on the right side of the unit behind the front panel. You can test by using a phone camera to see if the remote is transmitting IR (you'll see a purple flash through the camera)

### Entering Test Mode on Mitsubishi

This varies by model, but the most common method:

**For MSZ wall units with wireless remote:**
1. Turn the unit off
2. On the indoor unit, there's a small button behind the front panel (usually lower right, behind a small flap). Press it twice rapidly
3. The unit enters forced cooling test mode — compressor and fan run regardless of thermostat setting
4. Press twice again to switch to forced heating
5. Press once to stop test mode

**For units with wired remote (PAR-series):**
1. Press and hold the FILTER and SET buttons simultaneously for 3-5 seconds
2. The display changes to show test mode options
3. Navigate with the arrows

Test mode forces the system to run without waiting for normal startup delays. Useful for quickly verifying refrigerant operation, fan speeds, and compressor function.

### MXZ Multi-Zone Troubleshooting

Multi-zone systems (MXZ-2C, MXZ-3C, MXZ-4C, MXZ-5C, MXZ-8C) add complexity because multiple indoor units share one outdoor unit.

**Individual Zone Fault vs System Fault:**
- If one indoor unit shows an error and the others work fine, the problem is usually with that specific indoor unit or its lineset connection
- If ALL indoor units show errors or none work, the problem is the outdoor unit, power supply, or communication bus
- Exception: a refrigerant leak anywhere in the system can cause all zones to malfunction, even if the leak is at one indoor unit's flare connection

**Branch Box Troubleshooting (PAC-MKA Series):**
- Multi-zone systems with more than 2-3 zones may use branch boxes (distribution headers) to split the refrigerant lines
- The branch box contains solenoid valves and sometimes EEVs for each zone
- If one zone has no cooling/heating but others are fine: check the solenoid valve for that zone in the branch box. Listen for a click when the zone calls. No click = bad solenoid coil or no signal from the board
- Branch box wiring: each zone has a specific port assignment on the outdoor unit board. If someone swapped wires during installation, the wrong zone responds to calls
- Temperature sensing in the branch box: some models have thermistors in the branch box. A failed thermistor there causes erratic zone operation

### Flare Connections — The #1 Mitsubishi Leak Source

Mitsubishi flare fittings are where most leaks happen. Their copper linesets are thin-wall and soft — standard HVAC flaring techniques cause leaks.

**Critical Torque Specs:**
- 1/4" flare nut: 13-18 ft-lbs
- 3/8" flare nut: 33-42 ft-lbs
- 1/2" flare nut: 51-62 ft-lbs
- 5/8" flare nut: 62-75 ft-lbs

**Proper Technique:**
- Use a Mitsubishi-specific or mini-split flaring tool that creates a slight lip/ridge on the flare
- Deburr the cut end inside and out — burrs cause leaks and contaminate the system
- Apply a thin layer of Nylog (not Refrigeration Technologies thread sealant — Nylog specifically) to the flare face
- Use two wrenches — hold the fitting body with one wrench while tightening the nut with the other. If you don't hold the body, you'll twist the tubing and crack the flare
- Never reuse a flare. If you disconnect, re-cut and re-flare

### Common Failures by Age

**5-Year Mark:**
- EEV (Electronic Expansion Valve) sticking — especially on older FH-series units
- Outdoor board failures in humid/coastal environments (salt air corrodes)
- Drain pan cracks on some MSZ-FH models

**10-Year Mark:**
- Compressor failures begin — usually a winding short to ground
- Outdoor fan motor bearings
- Capacitors on the outdoor board
- Indoor blower wheel balance issues (dust accumulation causes vibration)

**15-Year Mark:**
- Heat exchangers on indoor units develop leaks (refrigerant-to-air)
- Outdoor coil corrosion in coastal areas
- Wiring harness degradation from UV exposure on outdoor units
- Complete board failures (capacitors age out)

### Lineset Length and Height Limits

This varies by model, so always check the specific installation manual, but general guidelines:

- **Single-zone MSZ/MUZ:** Max lineset length 65-98 feet (model dependent). Max height difference 40-50 feet. Additional charge required for runs over 25 feet
- **Multi-zone MXZ:** Max total piping length varies widely. Max height difference: indoor above outdoor typically 50 feet, indoor below outdoor typically 25 feet
- Height difference matters because of oil return — if the indoor unit is too far below the outdoor, oil pools in the low points and starves the compressor
- For long vertical runs, install oil traps every 30 feet (U-shaped loop in the suction line)

### kumo cloud / MELCloud Troubleshooting

- kumo cloud requires the PAC-USWHS002-WF-2 WiFi adapter (or newer USB adapter on current models)
- Adapter installs inside the indoor unit, plugs into the CN105 connector on the indoor board
- If kumo cloud shows the unit offline: check WiFi signal strength at the unit location. The adapter has a weak antenna — signal that works for your phone might not work for the adapter
- Factory reset the adapter: press and hold the button on the adapter for 10+ seconds until the LED blinks rapidly
- After a power outage, the adapter sometimes doesn't reconnect. Power cycle the indoor unit (breaker off/on) to force a reconnect
- kumo cloud has a 1-2 minute delay between app commands and unit response — this is normal, not a malfunction

### H2i Hyper-Heating Models — What's Different

H2i (Hyper-Heating INVERTER) models are designed for cold-climate operation. Key differences:

- **Flash injection circuit:** Uses a secondary expansion device and heat exchanger to inject vapor refrigerant into the compressor during low-ambient heating. This prevents liquid slugging and maintains capacity
- **Enhanced base pan heater:** Keeps the outdoor unit base pan warm to prevent ice buildup. If the heater fails, ice accumulates and blocks the outdoor coil
- **Lower operating range:** H2i operates down to -13F (-25C). Standard models cut out around 5-15F
- **Higher defrost frequency:** In cold weather, these units defrost more aggressively. If a customer complains about frequent defrost cycles in cold weather, that's normal — explain it
- **Diagnostic difference:** H2i models have additional sensor data for the injection circuit. In test mode, you can monitor injection pressure and temperature
- Common H2i failure: the injection solenoid valve sticks open, flooding the compressor with liquid. Listen for liquid slugging sounds during startup

---

## DAIKIN

### Error Code System

Daikin uses a letter prefix to categorize errors:

- **U codes:** Usage/operational errors (often user-correctable)
- **A codes:** Indoor unit protection faults
- **E codes:** Outdoor unit protection faults
- **F codes:** Refrigerant circuit faults
- **H codes:** Sensor faults
- **J codes:** Thermistor faults
- **L codes:** System protection faults
- **P codes:** Component faults

Error codes display on the wired remote, LED blinks on the indoor unit, or through the Daikin One+ app.

### Common Daikin Error Codes

**U4 — Communication Error Between Indoor and Outdoor**
- Same as every other brand — communication is the most common fault
- Daikin uses 2-wire communication (F1/F2) carried on dedicated signal wires
- Check for proper polarity — unlike some brands, Daikin F1/F2 polarity matters on some models
- Measure between F1 and F2: you should see a fluctuating DC voltage (communication pulses)
- Common cause: someone used the F1/F2 wires for 24V power (they're signal wires, not power). This fries the communication chip
- After board replacement, you may need to set the unit address again using DIP switches on the indoor board

**A3 — Drain System Fault**
- The condensate drain is blocked or the float switch tripped
- Daikin indoor units have a float switch in the drain pan — if water backs up, it kills the unit before water damage occurs
- Check: drain line for clogs, drain pan for cracks, float switch operation (gently lift the float — unit should stop within seconds)
- Common gotcha: Daikin mini-splits use a condensate pump on some models. The pump is tiny and inside the unit. If it fails, water backs up and triggers A3
- On ducted units, check the secondary drain pan too

**E7 — Outdoor Fan Motor Error**
- The outdoor fan isn't operating correctly
- Check: fan motor resistance (should not be open or shorted), fan blade for damage or debris blocking rotation, capacitor (on PSC motors)
- On inverter-driven fan motors: check the DC voltage from the drive board to the motor. No voltage = board issue. Voltage present but no spin = motor issue
- After replacing the fan motor on Daikin units, you sometimes need to run a "fan motor calibration" through the field settings. Without this, the board doesn't know the new motor's characteristics and may fault again

**H6 — Position Detection Error (Compressor)**
- The inverter board can't detect the compressor rotor position
- This is usually a bad compressor or inverter board
- Check compressor winding resistance first: all three legs should be balanced and no reading to ground
- If windings are good, the inverter board's IPM (Intelligent Power Module) may have failed
- Don't just replace the board — if the compressor has a winding issue, it'll take out the new board too

**L3 — Electrical Box Temperature Too High**
- The temperature inside the outdoor unit's electrical box has exceeded the safe limit
- Check: is the outdoor unit in direct sun with restricted airflow? Is the electrical box cover missing or poorly sealed (causing hot air recirculation)?
- Check the cooling fan inside the electrical box (some models have one). If it's failed, the box overheats on hot days
- On VRV systems, this often means overloaded electrical components — verify amp draw on all circuits

### Daikin One+ Ecosystem Troubleshooting

- The Daikin One+ smart thermostat communicates via 2-wire bus to compatible Daikin equipment
- If the thermostat shows "Connecting..." indefinitely: verify the indoor unit is a Daikin One+ compatible model. Not all Daikin equipment works with it
- WiFi issues: the thermostat has limited WiFi range. If it keeps dropping off the network, check distance to router
- After a firmware update, the thermostat may need to re-discover equipment. Go to Installer Settings > Equipment and run auto-detect
- The One+ thermostat stores fault history — access it through the Installer menu (default code is usually 5555 or 1234)

### VRV/VRF System Basics for Residential Techs

You might encounter Daikin VRV (Variable Refrigerant Volume) systems in large homes or light commercial jobs. Here's what you need to know:

**Refrigerant Charge Calculations:**
- Factory charge covers the outdoor unit and approximately 25-30 feet of lineset per indoor unit (varies by model)
- For additional lineset length, add refrigerant per the piping chart in the installation manual
- Weigh it in — VRV systems are extremely charge-sensitive
- The system uses R-410A on most residential-scale models (newer ones may use R-32)

**Branch Selector Box (BSB):**
- Routes refrigerant to individual zones
- Contains solenoid valves and control electronics
- If one zone doesn't heat or cool while others do: listen for the solenoid click in the BSB. No click = electrical issue (wiring or board). Click but no temperature change = mechanical failure in the valve
- BSB needs to be installed with proper orientation — the manual specifies which side faces up. Installed wrong, the valves don't function correctly

**Refrigerant Address Setting:**
- Every indoor unit must have a unique address set on its board (usually via DIP switches or rotary dial)
- If two units have the same address, one or both will show communication faults
- After any board replacement, re-verify the address setting matches the original

### Entering Field Setting Mode

On most Daikin wall-mounted units:
1. With the unit running, press and hold the CANCEL button on the remote for 5+ seconds
2. The display enters field setting mode
3. Use the mode and temperature buttons to navigate
4. Settings here include: cooling-only lockout, fan speed limits, auto-restart after power failure, LED display on/off

On ducted units with a wired controller, field settings are accessed through the controller's installer menu. The access code varies — check the installation manual for the specific controller model.

---

## NAVIEN

### Tankless Water Heater Error Codes

**E003 — Ignition Failure**
- The unit tried to ignite 3 times and failed
- Check: gas supply (is the gas valve open? is there adequate gas pressure?), ignition electrodes (gap should be approximately 3mm, clean with a wire brush), ground wire connection
- Verify gas pressure at the unit: 3.5" WC for natural gas, 8" WC for propane (with unit firing)
- Common cause on newer installations: the installer didn't purge the gas line. There's air in the pipe. Open a nearby gas appliance to purge, then retry
- If electrodes are sparking but no ignition: check the flame rod (separate from the ignition electrode on Navien). If the flame rod is dirty, the unit may ignite briefly then shut down — that's a different issue (E012)

**E012 — Flame Loss (Flame Detected Then Lost)**
- Unit ignites but flame goes out during operation
- Flame rod is dirty — clean it. This is the #1 cause
- Also check: inadequate gas supply (gas pressure drops under load), flue blockage (bird nest, ice in winter, long vent run with too many elbows)
- Vent termination: Navien requires specific clearances. If the exhaust termination is too close to a wall or corner, wind can blow exhaust back into the intake and snuff the flame
- On condensing models (NPE series), check the condensate drain. If plugged, water backs into the heat exchanger and disrupts the flame

**E016 — Overheating**
- Heat exchanger outlet temperature exceeded the limit
- Low flow through the unit — check for scale buildup in the heat exchanger, flow restrictions downstream (partially closed valve, kinked flex connector), or a failed flow sensor reading lower than actual
- Scale is the #1 cause on units over 3 years old in hard water areas
- Also check the mixing valve downstream — if it's failed partially closed, it restricts flow through the unit

**E030 — Exhaust Temperature High**
- Exhaust gas temperature sensor is reading too high
- Causes: scaled heat exchanger (heat isn't transferring to water efficiently, so exhaust stays hot), inadequate water flow, dirty burner
- If the unit is over 5 years old in hard water, flush it before anything else

**E109 — Fan Motor Abnormal**
- The combustion fan isn't operating correctly
- Check: fan motor wiring, debris in the fan housing, fan blade condition
- On condensing models, condensate can back up into the fan housing if the drain is plugged — this kills the fan motor
- Fan motor is brushless DC and controlled by the main board. If the motor tests good (no open windings), the board's fan drive circuit may have failed

### Annual Maintenance Procedure

Navien tankless heaters need annual maintenance. Skipping this is the #1 cause of premature failure.

**Descaling Procedure:**
1. Turn off gas and power to the unit
2. Close both cold water inlet and hot water outlet isolation valves
3. Connect a circulation pump and bucket with hoses to the service valves (cold side = pump outlet, hot side = return to bucket)
4. Fill bucket with white vinegar or commercial descaler solution (Navien recommends their own brand but any citric acid-based descaler works)
5. Run the pump for 45-60 minutes. The solution circulates through the heat exchanger and dissolves scale
6. Flush with clean water for 5 minutes
7. Remove hoses, open isolation valves, restore power and gas
8. Run the unit and verify operation

**Intake Filter Cleaning:**
- Navien units have a cold water inlet filter — a small screen at the cold water connection
- Remove it, clean debris, reinstall. Takes 2 minutes but prevents flow restriction errors
- On NPE-A and NPE-A2 models, there's also an air intake filter on the unit itself. Pull it out and rinse it

**Flame Rod and Ignition Electrode Cleaning:**
- Access the burner assembly by removing the front cover
- Clean the flame rod with fine sandpaper or emery cloth
- Check the ignition electrode gap (approximately 3mm)
- Inspect the burner for debris or carbon buildup

### Navien Combi-Boiler (NCB Series) Troubleshooting

**DHW Priority vs Space Heating:**
- NCB units prioritize domestic hot water over space heating by default
- When there's a DHW call, the unit switches from heating loop to DHW. This means radiators/floor heat stops temporarily during showers
- If the customer complains about heat dropping out periodically, explain the DHW priority
- Some NCB models have a "buffer tank" option that mitigates this. The tank stores heated water for the heating loop during DHW calls

**Minimum Activation Flow Rate:**
- Navien tankless units have a minimum flow rate to activate: typically 0.5 GPM
- Low-flow fixtures (water-saving showerheads, faucet aerators) may not trigger the unit
- If a customer says "hot water is inconsistent," check the flow rate at the fixture. If it's borderline 0.5 GPM, flow fluctuations can cause the unit to cycle on and off
- Solution: remove the flow restrictor from the showerhead, or install a small recirculation loop that maintains minimum flow

**Cascading Multiple Units:**
- Navien supports cascading up to 16 units using their NaviLink system
- Each unit must have a unique unit address set on the board DIP switches
- The primary unit (address 01) controls staging — it fires first and calls secondary units as demand increases
- Common issue: communication bus wiring. The cascade uses RS-485 communication — requires shielded cable with proper termination
- If one unit in the cascade isn't responding: check its address setting and verify the communication bus connection at that specific unit

### Common Navien Hardware Failures

**Flow Sensor:**
- The flow sensor is a turbine type (small paddle wheel) that measures water flow through the unit
- Failures: sensor gets gunked up with scale and reads low or zero flow. Unit won't fire or fires intermittently
- Cleaning sometimes helps but replacement is more reliable
- Part is relatively inexpensive and easy to replace

**Ignition Electrode:**
- Degrades over time, especially in humid environments
- The gap opens up as the electrode erodes. If the gap exceeds about 4mm, ignition becomes unreliable
- Replace every 2-3 years as preventive maintenance in high-use applications

**Heat Exchanger Scale:**
- The #1 killer of Navien units. Hard water areas (above 7 grains per gallon) will scale up the heat exchanger in 2-3 years without descaling
- Once scale gets bad enough, the heat exchanger is not recoverable — descaling won't remove heavy scale
- Prevention: annual descaling and/or a water softener upstream

### Recirculation Pump Settings

Navien NPE-A and NPE-A2 units have a built-in recirculation pump:

- **Internal Pump Mode:** The built-in pump circulates hot water back through the cold water line (no dedicated return line needed). This works but means the cold water runs warm for a few seconds at first
- **External Pump Mode:** Uses a dedicated return line and an external pump. Better performance but requires additional plumbing
- Pump schedule is set on the unit's front panel — set it to match the household's usage pattern to save energy
- If the recirc pump is running but there's no hot water at distant fixtures: check for a check valve at the furthest fixture (required for internal pump mode) or verify the return line isn't cross-connected

---

## BOSCH

### Tankless Water Heater Error Codes

**A7 — Faulty DHW Outlet Temperature Sensor**
- The hot water outlet sensor is reading out of range
- Check: sensor resistance (NTC thermistor, approximately 10K at 77F), wiring, connector at the board
- If sensor checks good, possible board issue

**AA — Flue Gas Temperature Too High**
- Scale in the heat exchanger causing poor heat transfer
- Descale the unit (same procedure as Navien — circulation pump with descaler)
- Also check: gas pressure too high, improper combustion (dirty burner, blocked air intake)

**C6 — Fan Speed Not Achieved**
- Fan motor can't reach the commanded speed
- Check: blocked flue, blocked intake, fan motor failure, wiring
- On condensing models, condensate backing up can interfere with the fan

**C7 — Fan Not Running**
- No fan operation detected
- Check: power to fan motor (board sends DC voltage), fan wiring, motor windings
- If power is present at the motor but no spin: fan motor is dead

**E2 — NTC Temperature Sensor (Outlet) Fault**
- Similar to A7 — sensor is reading abnormally
- Common after a long period of no use (sensor can drift)

**E9 — High Limit Fault**
- Unit exceeded safe temperature limit
- Scale, low flow, or failed high limit switch
- Reset: power cycle the unit. If it trips again immediately, address the root cause

**EA — No Flame Detected**
- Ignition failure — same diagnostic approach as Navien E003
- Check gas supply, ignition electrode, flame rod, gas valve
- Bosch-specific: some models have a dual-function electrode (ignition and flame sensing in one). If this electrode is worn, you lose both functions at once

### Greentherm Condensing Tankless Maintenance

- Same descaling procedure as other tankless brands — circulate descaler for 45-60 minutes
- Additionally: check the condensate neutralizer (if installed). These fill up with calcium over time and need replacement every 1-2 years
- Clean the air intake screen — it's usually at the bottom of the unit
- Inspect the condensate trap and drain line for blockage
- Clean or replace the burner if it shows signs of carbon buildup
- Check combustion: measure CO in the flue. Bosch Greentherm should be under 100 PPM CO air-free. Higher readings indicate dirty burner or combustion air restriction

### Bosch Heat Pump (IDS 2.0)

This is a communicating system similar to Carrier Infinity or Trane XL:

- Uses the BCC100 thermostat as the system controller
- Communication is over a 4-wire bus (R, C, D+, D-)
- Error codes display on the BCC100 thermostat under the diagnostics menu
- To access installer settings: press and hold the Bosch logo on the thermostat for 5 seconds. Default code: 1234
- Common issue: after power outage, the system takes up to 5 minutes to re-establish communication between all components. Customers call saying the system "isn't working" — tell them to wait 5 minutes
- The outdoor unit has a green LED visible through the top grate. Steady = normal. Blinking patterns indicate specific faults — count the blinks, refer to the installation manual
- IDS 2.0 uses an inverter compressor. Same diagnostics as other inverter systems: check winding resistance, check inverter board DC output, verify input power is clean (no voltage sags or spikes)

### Bosch Appliance Error Codes (Dishwashers — Common Service Calls)

Techs working in the trades sometimes get asked about appliance codes. Here are the Bosch dishwasher ones you'll actually see:

**E01 — Heating Element or Control Board**
- The water isn't heating
- Check heating element resistance (typically 10-30 ohms). Open circuit = replace
- If element is good, control board isn't sending power to it

**E09 — Heating Element Failure**
- Specific to heating circuit
- Same diagnosis as E01

**E15 — Water in Base Pan (Leak Protection)**
- The anti-flood system detected water in the base pan
- Tilt the machine forward slightly to drain the base pan
- Check: door seal, internal hose connections, pump seals, spray arm connections
- The float switch in the base pan triggers this. Sometimes the switch itself sticks

**E22 — Filter/Pump Blockage**
- The drain filter is clogged
- Clean the filter assembly at the bottom of the tub — remove the screen and the cylindrical filter
- Check the drain impeller behind the filter for debris

**E24 / E25 — Drain Issues**
- E24: drain hose kinked or clogged
- E25: drain pump issue or blocked drain path
- Check the drain hose for kinks, the air gap (if installed), and the garbage disposal connection (if the knockout wasn't removed, the dishwasher can't drain)

---

## FUJITSU

### Error Code System

Fujitsu uses a combination of LED blink patterns on the indoor unit:
- **Operation light (green)** and **Timer light (orange)** blink in patterns
- Count the green blinks, then the orange blinks — that gives you a two-digit code
- Example: 2 green blinks + 3 orange blinks = Error 23

### Common Fujitsu Error Codes

**EE:EE on the Remote Display**
- This indicates a major control board failure on the indoor unit
- Before condemning the board: unplug the unit for 5 minutes and restore power. Sometimes a transient surge causes this and a power cycle clears it
- If it returns immediately: the indoor board has failed and needs replacement
- Common after lightning storms or power surges — recommend a surge protector on the outdoor disconnect

**Operation Light Blinks Continuously (no pattern)**
- Usually a refrigerant issue: low charge, high pressure, or compressor protection
- Check charge and pressures
- Also check: outdoor coil for blockage, outdoor fan operation, ambient temperature limits

**Error 23 — Discharge Pipe Temperature Abnormality**
- Compressor discharge temp is too high
- Low charge, dirty outdoor coil, failed outdoor fan, restriction in refrigerant circuit
- On heat pump models, this can trigger during cold-weather heating with a dirty outdoor coil (coil ices up, starves the compressor of refrigerant)

### Entering Test Mode on Fujitsu

**Wall-mounted units (ASU/AOU series):**
1. Turn the unit off with the remote
2. Press the "Economy" and "Powerful" buttons on the remote simultaneously (some models use different button combos — check the service manual)
3. Alternatively, there's a manual test button behind the front panel of the indoor unit — usually a small recessed button on the right side of the unit
4. Press it once for cooling test, again for heating test

**Ducted units (ARU/AOU series):**
- Test mode button is on the indoor unit control board
- Open the access panel and look for a small pushbutton labeled "TEST" or "CHECK"

### Common Fujitsu Failures

**Outdoor Board:**
- The most common failure point on Fujitsu units
- Often caused by power surges, lightning, or voltage spikes
- Symptoms: unit does nothing, LEDs on outdoor board don't light up, or various fault codes
- Before replacing: check fuses on the board (small glass fuses, sometimes hidden behind a cover). A blown fuse is cheap and quick
- If the board is burned/visibly damaged, check the compressor windings before installing a new board — a shorted compressor will kill the new board

**Compressor:**
- Fujitsu uses scroll compressors on most models
- Common failure mode: internal valve plate failure, causing loss of compression
- Symptom: system runs but doesn't cool/heat effectively. Pressures equalize quickly when the compressor shuts off (normal systems take a few minutes to equalize; a bad valve equalizes in seconds)
- Another common failure: winding to ground short. Test with megohmmeter — should read infinity. Anything below 1 megohm is a failed compressor

**EEV (Electronic Expansion Valve):**
- Fujitsu EEVs are controlled by a stepper motor
- Failure modes: stuck open (flooding, high suction pressure, liquid slugging), stuck closed (starving, low suction pressure, high superheat), or inconsistent (hunting)
- Listen for the stepper motor clicking during operation — you should hear periodic adjustments
- If the EEV is stuck, sometimes cycling power resets it. If it keeps sticking, replace it
- When replacing the EEV, you'll need to recover refrigerant. The EEV is brazed into the refrigerant circuit

---

## LG

### Error Code System

LG uses two different code formats:
- **CH codes** on the indoor unit display (CHxx format)
- **Numbered codes** on the outdoor unit display or LED

### Common Indoor Unit Codes

**CH01 — Indoor Temperature Sensor Error**
- Room air temp sensor is reading out of range
- Sensor is an NTC thermistor, typically near the return air grille
- Check resistance vs. LG's thermistor chart
- Common: sensor wire gets pinched during filter cleaning

**CH02 — Indoor Pipe Temperature Sensor Error**
- The evaporator coil temperature sensor is faulty
- Same diagnosis: check thermistor resistance
- This sensor is clipped to the indoor coil. If it falls off, readings go erratic

**CH05 — Communication Error Between Indoor and Outdoor**
- Most common LG error
- LG uses 3-wire communication: power (L, N) and signal (S)
- Verify 230VAC at the outdoor terminal block
- Signal wire (S) should show fluctuating voltage when communicating
- LG is sensitive to wire length — max distance varies by model but typically 50-75 feet for residential units
- Common cause: wrong wire type. Use stranded copper, minimum 14 AWG for power legs

**CH10 — Indoor Fan Motor (BLDC) Error**
- The indoor brushless DC fan motor isn't responding
- Check: motor connector (unplug and reseat), motor winding resistance, board output to the motor
- LG indoor fan motors are BLDC and require the board to drive them. You can't test them with direct power like a PSC motor
- If the motor hums but doesn't spin: the motor hall sensor may have failed. The board needs the hall sensor feedback to commutate the motor properly

### Common Outdoor Unit Codes

**Code 21 — DC Peak Current (Compressor)**
- Compressor drew too much current
- Check: compressor winding resistance, compressor terminals, power supply voltage
- Low voltage at the outdoor unit causes high current draw. Verify line voltage under load
- If voltage is good and windings test fine, the inverter board's power module (IPM/IGBT) may be failing

**Code 22 — CT (Current Transformer) Sensor Error**
- The current sensor on the compressor circuit is reading abnormally
- This can be a bad CT sensor (check wiring) or a bad board
- Less common: actual overcurrent from a partially shorted compressor winding

**Code 26 — DC Compressor Position Detection Error**
- The inverter can't detect the compressor rotor position
- Same as Daikin H6 — check compressor windings first, then inverter board
- If the compressor sat for a long time, the rotor may be stuck (seized bearings or liquid refrigerant holding it). Try an LRA (locked rotor amps) start kit

**Code 40 — CT2 Sensor Error**
- Secondary current sensor fault
- Wiring issue or failed sensor

**Code 44 — Outdoor Air Sensor Error**
- The outdoor ambient temperature sensor is reading out of range
- Thermistor check: same as all other brands, approximately 10K at 77F
- Sensor is usually on the inlet side of the outdoor coil

**Code 51 — Overcapacity (Compressor)**
- System is trying to run beyond rated capacity
- Usually caused by incorrect system configuration (indoor capacity exceeds outdoor capacity) or a refrigerant issue forcing the compressor to work too hard
- On multi-zone systems, verify the total indoor capacity doesn't exceed the outdoor unit's rated output

**Code 53 — DC Peak Current (Outdoor Fan)**
- Outdoor fan motor drew too much current
- Check: fan blade for debris, motor bearings, motor winding resistance
- LG outdoor fan motors are often BLDC — same diagnostics as the indoor fan motor

### LGMV Software for Diagnostics

- LG provides LGMV (LG Multi V) software for diagnostics on VRF systems but it's also useful for residential multi-split
- Requires a USB-to-serial adapter and connects to the outdoor unit's diagnostic port
- The software shows real-time data: pressures (from transducers), temperatures (all sensors), compressor speed (Hz), fan speeds, EEV position, error history
- Much faster for diagnosing intermittent faults than reading codes one at a time
- Download from LG's partner portal (LATS — LG Air Solution Technical Support website)

### Common LG Failures

**EEV (Electronic Expansion Valve):**
- LG EEVs are a common failure point, especially on models 5+ years old
- Symptom: high superheat or low subcooling that doesn't respond to charge adjustment
- The EEV coil can fail electrically (check resistance, should be 30-60 ohms) or the valve can stick mechanically
- LG EEVs are controlled by step motor — listen for the motor clicking

**Outdoor Board:**
- LG outdoor boards are expensive ($400-800+)
- Before condemning: check all input sensors and power supply. A bad sensor feeding the board bad data can mimic a board failure
- Check for obvious damage — burned components, cracked solder joints, corroded connectors
- LG boards are sensitive to power quality. In areas with frequent outages or brownouts, recommend a surge protector

**Compressor:**
- LG uses their own compressors, which are generally reliable but can fail
- Typical failure mode: winding to ground short
- Test: megohmmeter to ground, winding-to-winding resistance balance
- LG offers a 10-year compressor warranty on most models — verify with the serial number before quoting a replacement

---

## SAMSUNG

### Error Code System

Samsung uses an E-series code format: E followed by a 3-digit number.

### Common Error Codes

**E101 — Communication Error Between Indoor and Outdoor**
- Same story as every other brand — communication is the #1 fault
- Samsung uses 3-wire or 4-wire communication depending on model
- Check wiring, verify power at both ends, check for damaged cable
- Samsung-specific: the communication wire must be separate from the power cable. Running signal wires in the same conduit as power wires causes interference and communication faults
- Some Samsung models require specific communication wire (shielded twisted pair). Check the installation manual for the specific model

**E121 — Indoor Room Temperature Sensor Error**
- Thermistor reading out of range
- Standard diagnosis: check sensor resistance, wiring, connector

**E154 — Indoor Fan Motor Error**
- BLDC fan motor fault
- Check: motor connector, motor winding resistance, hall sensor
- Samsung indoor fan motors are similar to LG — BLDC driven by the board

**E201 through E237 — Outdoor Sensor Errors**
- Various outdoor sensors reading abnormally
- Each code maps to a specific sensor: outdoor air, coil, discharge, suction, etc.
- Diagnose by checking the specific sensor's thermistor resistance
- E201: outdoor ambient. E202: outdoor coil. E226: discharge pipe. E237: suction pipe

**E301 — Compressor Error**
- Compressor overcurrent, position detection failure, or winding fault
- Full compressor diagnostic: winding resistance (balanced, no ground), megohm test, amp draw during operation
- On inverter models, also check the inverter board and its power supply

### Wind-Free System Specifics

Samsung's Wind-Free models have a unique feature: a perforated panel that disperses air without creating a direct draft.

- **Wind-Free mode**: Compressor runs at low speed, fan runs at very low speed, and air disperses through thousands of micro-holes
- Cleaning the Wind-Free panel is critical — if the micro-holes get plugged with dust, airflow drops and the unit can't condition the room effectively
- The panel is removable for cleaning. Wash with warm water and mild soap, dry completely before reinstalling
- Don't use a pressure washer or compressed air on the panel — the holes are delicate
- If a customer complains about reduced cooling in Wind-Free mode: dirty panel is the #1 cause

### Common Samsung Failures by Model Line

**Residential Wall-Mount (AR series):**
- Indoor board failures after power surges (install surge protection)
- EEV sticking (similar to other brands — listen for stepper motor clicks)
- Condensate pump failures on models with built-in pumps

**Residential Ducted (AC/AD series):**
- Drain issues (A3-type faults) — the condensate drain on ducted Samsung units is finicky about fall/grade. Needs minimum 1/8" per foot slope
- Communication faults when duct runs exceed max distance — Samsung has tighter length limits than some competitors

**Multi-Zone / FJM System:**
- Individual zone faults can affect the whole system depending on how the system is configured
- When one indoor unit locks out on a fault, the outdoor unit may reduce capacity for all zones
- Diagnose by isolating: disconnect the faulty zone at the outdoor unit terminal block. If other zones recover, the fault is definitely isolated to that zone

### DVM VRF System Basics

Samsung DVM (Digital Variable Multi) is their commercial VRF system, but techs encounter it in large residential and light commercial:

- Uses Samsung's proprietary communication protocol
- DVM Pro software (similar to LGMV) connects to the system for diagnostics
- Refrigerant address setting is done through DIP switches on each indoor unit's board
- Charge calculation follows the same pattern as other VRF: factory charge + additional per foot of piping beyond factory length
- Samsung DVM uses R-410A. Newer DVM S2 systems may use R-32

---

## GENERAL DIAGNOSTIC TIPS ACROSS ALL BRANDS

### Inverter Compressor Testing (Universal)

All these brands use inverter compressors. Here's the universal approach:

1. **Check input power:** Verify correct voltage at the outdoor unit disconnect. Low voltage causes overcurrent faults on every brand
2. **Check compressor windings:** Disconnect the 3-phase wiring from the compressor terminals. Measure resistance between U-V, V-W, and U-W. All three readings should be within 0.5 ohms of each other. Any reading to ground should be infinity (megohm test)
3. **Check inverter board output:** With the system trying to run, measure DC voltage from the inverter board to the compressor terminals. You should see varying voltage as the compressor ramps up. No voltage = board issue. Voltage but no operation = compressor issue
4. **Check the reactor/choke coil:** Some systems have a reactor between the board and compressor. Measure its resistance — it should be very low (near zero) but not zero. Open circuit = failed reactor

### EEV Troubleshooting (Universal)

EEV (Electronic Expansion Valve) issues are increasingly common across all brands:

1. **Listen:** You should hear periodic clicking as the stepper motor adjusts the valve. No clicking = electrical issue. Constant clicking = the valve may be hunting (trying to find the right position but can't)
2. **Measure coil resistance:** Disconnect and measure. Typical range: 30-100 ohms depending on brand. Open = replace
3. **Power cycle test:** Turn off the unit, wait 5 minutes, turn it back on. Some EEVs reset to a default position on power-up. If the system works briefly after power-up then faults again, the EEV is sticking during operation
4. **Superheat/subcooling:** An EEV stuck open shows high suction pressure and low superheat. Stuck closed shows low suction pressure and high superheat

### Communication Bus Troubleshooting (Universal)

Communication faults are the most common error across all brands. Universal approach:

1. Verify power at both indoor and outdoor units
2. Check signal wire continuity end-to-end
3. Verify correct wire gauge (14 AWG minimum for most brands)
4. Check for damaged or rodent-chewed wires
5. Verify signal wire is not in the same conduit as high-voltage power lines
6. After any board replacement, power cycle the entire system (all indoor and outdoor units off for 60+ seconds)
7. Check for correct polarity/terminal assignments — one swapped wire kills communication
8. On multi-zone systems, disconnect zones one at a time to isolate which unit is pulling down the bus

### Thermistor Testing (Universal)

Every brand uses NTC thermistors for temperature sensing. The testing approach is the same:

1. Disconnect the sensor from the board
2. Measure resistance with a multimeter
3. Compare to the brand's resistance-temperature chart (approximately 10K at 77F is the most common spec, but verify)
4. Open circuit (infinite resistance) = broken sensor wire or failed sensor
5. Short circuit (zero or near-zero resistance) = shorted sensor
6. If resistance is in range but the board shows a fault: check the wiring between sensor and board. A high-resistance connection (corroded pin, loose connector) throws off the reading
7. Quick field test: warm the sensor with your hand and watch the resistance change. If it doesn't change, sensor is dead

### When to Suspect the Board vs the Component

A common dilemma: is it the board or the component the board is driving?

**Suspect the component when:**
- The board is sending correct output voltage/signal to the component, but the component doesn't respond
- Winding resistance is out of spec
- The component makes unusual noises (grinding, buzzing, clicking)
- The problem occurs immediately on startup every time (consistent failure)

**Suspect the board when:**
- Output voltage/signal to the component is absent or abnormal, but input power to the board is correct
- The problem is intermittent — works sometimes, fails other times, with no pattern
- Multiple unrelated faults occur simultaneously
- Visible damage on the board (burn marks, swollen capacitors, corroded pins)
- The problem appeared after a power event (lightning strike, brownout, surge)

### Refrigerant Leak Detection Best Practices (All Brands)

1. **Electronic leak detector:** Sweep all joints, flares, valves, and the evaporator/condenser coils. Move slowly — 1 inch per second. Start at the top and work down (most refrigerants are heavier than air)
2. **Soap bubbles:** Apply to suspected areas. Look for growing bubbles, not just foam
3. **UV dye:** Add UV dye to the system and run it for a few days. Return with a UV light and yellow glasses — leaks glow brightly. This is the best method for slow/small leaks
4. **Nitrogen pressure test:** For large or hard-to-find leaks, pressurize with dry nitrogen to 300-400 PSI (never exceed system rated pressure) and use soap bubbles or an ultrasonic leak detector
5. **Most common leak locations by brand:**
   - Mitsubishi: Flare connections (improper torque or no Nylog)
   - Carrier: Service valves and Schrader cores
   - Daikin: Brazed joints, especially factory joints on the outdoor coil
   - Fujitsu: Indoor coil U-bends (vibration stress cracks)
   - LG/Samsung: EEV connections and distributor tubes
   - Navien/Bosch (not applicable — water heating, no refrigerant)
