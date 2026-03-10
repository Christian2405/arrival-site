# Commercial HVAC Systems — Field Knowledge

This document covers commercial HVAC systems including chillers, cooling towers, rooftop units, VAV systems, building automation, commercial boilers, walk-in refrigeration, and commercial kitchen ventilation. Written for field technicians working in commercial buildings.

---

## CHILLERS

### Chiller Types Overview

Chillers fall into two broad categories by how they reject heat: air-cooled and water-cooled.

**Air-Cooled Chillers** sit outside on a pad or rooftop. They have condenser fans blowing ambient air across finned coils. Simpler install — no cooling tower, no condenser water piping, no water treatment. Downside is they lose efficiency fast once ambient temps climb past 95F. Typical efficiency around 1.0-1.3 kW/ton. You see these on buildings under 200 tons usually. Common units: Trane RTAC, Carrier 30XA, York YCAL, Daikin.

**Water-Cooled Chillers** reject heat to a cooling tower through condenser water piping. Much more efficient — 0.5-0.7 kW/ton for centrifugal machines. More complex system: you need the tower, condenser water pumps, water treatment, and all the associated piping and controls. But for big buildings, the efficiency savings pay for the extra infrastructure. Common units: Trane RTWD/RTHD, Carrier 19XR/30HXC, York YCIV/YK, Daikin Magnitude.

### Compressor Types

**Scroll Compressors** — Found on smaller chillers, typically under 60 tons. Simple, reliable, fewer moving parts. Common on air-cooled units. When a scroll goes bad you replace the whole compressor. Trane CGAM uses scrolls. Multiple scrolls stage on and off for capacity control.

**Screw Compressors** — Mid-range, 70 to 400 tons typically. Use a slide valve for capacity modulation — can unload down to 25% or less. Good part-load efficiency. Listen for the distinctive steady hum. Common on Trane RTAC, York YCAL. Oil management is critical — check the oil separator, oil heater, and oil level sight glass every PM.

**Centrifugal Compressors** — The big boys, 200 tons and up to 2000+ tons. Use an impeller spinning at high RPM to compress refrigerant vapor. Inlet guide vanes or variable speed drives handle capacity control. Extremely efficient at design conditions. Trane CenTraVac (RTHD) is the classic — uses low-pressure R-123 or R-1233zd in a vacuum vessel. Carrier 19XR uses R-134a at positive pressure. York YK uses R-134a. Magnetic bearing centrifugals (Danfoss Turbocor, used in Smardt and some Daikin units) eliminate oil entirely and are very efficient at part load.

### Common Chiller Brands and Models

**Trane:**
- CGAM — Air-cooled scroll, 20-130 tons. Reliable workhorse.
- RTAC — Air-cooled screw, 140-500 tons. Adaptive Frequency Drive option.
- RTWD — Water-cooled screw, 70-400 tons.
- RTHD (CenTraVac) — Water-cooled centrifugal, 250-2000+ tons. Low-pressure refrigerant, purge unit required.
- Tracer AdaptiView or CH530 controller.

**Carrier:**
- 30XA — Air-cooled screw, popular in the 100-500 ton range. Uses AquaForce branding.
- 30HXC — Water-cooled screw.
- 19XR/19XRV — Water-cooled centrifugal, VFD option on the V model.
- 23XRV — Water-cooled centrifugal with variable speed. Very efficient.
- ProductVision or MicroTech III controller.

**York (Johnson Controls):**
- YCAL — Air-cooled screw, 40-230 tons.
- YCIV — Variable speed screw, water-cooled. One of the most efficient screws on the market.
- YK — Water-cooled centrifugal, 300-3000 tons. Workhorse of the industry.
- OptiView or Micro Panel controller.

**Daikin:**
- Magnitude — Water-cooled magnetic bearing centrifugal. Oil-free, extremely quiet.
- Pathfinder — Air-cooled screw.
- Trailblazer — Air-cooled scroll.

### Chiller Troubleshooting

**Low Superheat** — Means too much liquid refrigerant getting to the compressor, risk of liquid slugging. Check TXV or EEV operation. Could be overcharged, dirty evaporator (low water flow or fouled tubes reduce heat transfer, refrigerant doesn't boil off). Check evaporator water flow rate — low GPM kills superheat. Target superheat is typically 6-12F depending on manufacturer. On flooded evaporators, you watch approach temperature instead.

**High Head Pressure** — On water-cooled: check condenser water flow and entering temperature. Dirty condenser tubes (scale, mud) will drive head pressure up. Verify tower is operating — fans running, proper water level, clean fill. On air-cooled: dirty condenser coils (cottonwood, dirt), failed condenser fans, high ambient. Normal head pressure for R-134a at 85F condenser water: about 115-130 PSIG.

**Oil Pressure Faults** — Screw chillers need oil pressure differential (oil pressure minus suction/discharge depending on type) of at least 20-30 PSI typically. Check oil level in sight glass. Oil heater should be energized when compressor is off to drive refrigerant out of oil. Failed oil heater = diluted oil = low oil pressure on startup. Check oil filter differential — clogged filters restrict flow.

**Compressor Staging Issues** — Multi-compressor chillers stage based on load. If a compressor won't come online: check for active alarms on that circuit, check motor starter or VFD status, look for high or low pressure lockouts, check oil heater run time (most require 4-12 hours of oil heater before allowing start).

**Evaporator Freeze Protection** — If leaving chilled water drops below about 36F, chiller shuts down to prevent ice forming in the evaporator tubes. Causes: low water flow (failed pump, closed valve, air-bound system), setpoint too low, control sensor bad. A frozen evaporator is a catastrophic failure — tubes crack, refrigerant contaminates the water, water contaminates the refrigerant. Costs six figures to fix.

### Key Chiller Error Codes

**Trane (CH530/AdaptiView):**
- Diagnostic 1 — High pressure cutout
- Diagnostic 2 — Low pressure cutout
- Diagnostic 3 — Oil pressure failure
- Diagnostic 4 — Motor overload/high amps
- Diagnostic 7 — Freeze protection (low evap temp)
- Diagnostic 12 — Low oil temperature (oil heater issue)
- Diagnostic 14 — Condenser pressure too high
- Diagnostic 37 — Starter fault

**Carrier (MicroTech III/ProductVision):**
- Alert 1/AL01 — Compressor discharge high pressure
- Alert 2/AL02 — Low evaporator pressure/temperature
- Alert 3/AL03 — Oil pressure differential low
- Alert 4/AL04 — Motor overcurrent
- Alert 10 — Low evaporator water temperature (freeze)
- Alert 29 — Condenser water flow loss

**York (OptiView):**
- Trip A — High discharge pressure
- Trip B — Low evaporator pressure
- Trip C — Oil pressure fault
- Trip D — Motor overload
- Trip H — Freeze protection
- Trip L — Loss of charge (low refrigerant)

### Chiller Water Temperatures

**Chilled Water (Evaporator Side):**
- Standard design: 44F entering, 54F leaving (10F delta-T)
- Low-temp applications: 40F or lower leaving
- Evaporator approach temperature: 1-3F for clean tubes. If approach exceeds 5F, tubes are fouling.

**Condenser Water (Water-Cooled):**
- Standard design: 85F entering from tower, 95F leaving to tower (10F delta-T)
- Hotter entering water = higher head pressure = lower efficiency
- Condenser approach temperature: 1-2F clean. Over 3F means scale or fouling — pull heads and clean the tubes.

---

## COOLING TOWERS

### Tower Types

**Crossflow** — Air enters the sides, water falls vertically through fill. Open sump at the bottom. Easier to maintain because you can access the fill and distribution pans from the side. Marley, BAC, Evapco all make crossflow.

**Counterflow** — Air enters the bottom and moves upward against the falling water. More compact footprint, slightly more efficient. But harder to access fill for inspection. Marley NC series, BAC Series 3000.

**Induced Draft** — Fan on top pulling air through (most common in commercial). Lower noise, better air distribution.

**Forced Draft** — Fan on the side pushing air through. More common in industrial. Higher energy use but useful where you need to duct the discharge air.

### Cooling Tower Maintenance

**Water Treatment** — Absolutely critical. You need a water treatment vendor testing weekly at minimum. They manage:
- Conductivity and cycles of concentration (typically 3-6 cycles)
- pH (target 7.0-8.5 typically)
- Biocide (prevent Legionella, algae, biofilm)
- Scale inhibitor (prevent calcium carbonate/sulfate scale on tubes and fill)
- Corrosion inhibitor (protect piping and tower metals)
- Blowdown controller keeps conductivity in range by dumping water

Legionella is the big one — Legionnaires disease kills people. ASHRAE 188 requires a water management program for all buildings with cooling towers. Test quarterly minimum, many jurisdictions require registration and regular testing.

**Basin Cleaning** — Drain and clean the sump basin at least twice a year. Sediment, sludge, biological growth accumulate. Side-stream filtration helps but doesn't replace physical cleaning.

**Fan Motor and Drive** — Check belt tension if belt-driven (many newer towers are direct drive). Lubricate motor bearings per schedule. Check vibration — bad bearings, unbalanced fan, loose hardware. Fan blade pitch affects capacity — factory set, don't adjust without engineering calcs.

**Drift Eliminators** — Keep water droplets from leaving the tower. Damaged or missing eliminators waste water and can spread Legionella. Inspect annually, replace if cracked or warped.

**Fill Media** — The corrugated sheets where heat transfer happens. PVC film fill is common. Scale buildup on fill reduces capacity. Inspect with a flashlight — you should see daylight through clean fill. Heavily scaled fill must be replaced.

### Common Cooling Tower Problems

**Scale Buildup** — Hard water deposits on fill, tubes, and basin. Drives up condenser water temperature, reduces tower capacity. Caused by poor water treatment, high cycles, or pH too high. Acid cleaning may help but prevention is better.

**Biological Growth** — Algae (green slime), biofilm (slimy coating inside pipes), Legionella bacteria. Caused by inadequate biocide treatment, stagnant water, dead legs in piping. If you see green or slimy growth, water treatment program is failing.

**Vibration** — Usually fan-related. Check blade balance, bearing condition, coupling alignment (on direct drive), belt tension. Also check for structural issues — loose bolts, corroded supports. Towers on roofs can transmit vibration into the building.

**Freeze Protection** — In cold climates, tower basins can freeze. Options: basin heaters (electric immersion heaters, 5-15 kW typical), indoor sump tank (pump water to inside tank when tower is off), pan deicing. Some systems drain the tower in winter. At minimum, keep condenser water flowing during cold weather to prevent dead legs from freezing.

### Tower Performance Calculations

**Range** = Entering water temp minus leaving water temp. Typically 10F for standard HVAC. Higher range means smaller tower needed but higher pump energy.

**Approach** = Leaving water temp minus ambient wet-bulb temperature. A 7F approach is standard design. Approach under 5F requires a very large tower. If your approach is climbing over the years, tower capacity is declining (dirty fill, reduced airflow, water treatment issues).

---

## ROOFTOP UNITS (RTUs)

### Common RTU Brands and Models

**Trane:**
- Voyager — Light commercial, 3-25 tons. Very common on strip malls, small offices.
- IntelliPak — 20-130 tons. Higher-end, VAV capable, integrated controls.
- ReliaTel or Tracer UC600 controller.

**Carrier:**
- 48/50 series — Light commercial, 3-25 tons. Weathermaker, WeatherExpert.
- 50XC/50XCW — 25-77 tons. More features, better efficiency.
- Carrier Comfort Network (CCN) or i-Vu controller.

**Lennox:**
- Energence — 3-25 tons. Common on smaller commercial.
- Strategos — 25-50 tons. Good units,?"Prodigy controller.

**York:**
- Predator/Sun series — Light commercial.
- YVAA — Air-cooled variable speed screw chiller-RTU hybrid. Newer technology.
- Simplicity controller.

**Daikin:**
- Rebel — 3-25 tons. High-efficiency, variable speed.
- DPS — Packaged rooftop.

### Economizer Operation

The economizer is a set of dampers that brings in outdoor air for free cooling when conditions allow. Two control methods:

**Dry-Bulb Economizer** — Opens outdoor air dampers when outdoor temp is below a setpoint (typically 55-65F depending on climate zone). Simple, reliable. Most common in dry climates. High-limit shutoff: 75F is typical for climate zones 1-3.

**Enthalpy Economizer** — Compares outdoor enthalpy (heat content considering humidity) against return air enthalpy. Opens dampers when outdoor enthalpy is lower. Better for humid climates because a 60F day at 90% humidity has more total heat than a 65F day at 30% humidity. Requires enthalpy sensors that tend to drift — calibrate or replace annually. Comparative enthalpy uses two sensors (outdoor and return). Single-enthalpy uses outdoor sensor and fixed return assumption.

**Economizer Troubleshooting:**
- Dampers stuck closed — check actuator, linkage, control signal (0-10V or 2-10V is common). Apply signal manually to test. Check for broken linkage pins, stripped gears, seized damper shafts (corrosion).
- Dampers stuck open — unit runs constantly, high energy bills, humidity problems. Common cause: failed actuator spring return, broken linkage.
- Short cycling when economizer active — outdoor air sensor reading wrong, mixing plenum sensor issue, damper hunting (PID tuning needed).
- Minimum outdoor air not met — required by code for ventilation. Adjust minimum position on actuator. Measure actual CFM with a flow hood at a representative diffuser or use duct traverse.

### Staged Heating and Cooling

Most RTUs have staged capacity:
- Cooling: 2-stage scroll compressors, or multiple compressors staging (stage 1 = 1 compressor, stage 2 = 2 compressors). Newer units use variable speed compressors for modulating capacity.
- Gas Heat: 2-stage gas valves are standard. High fire and low fire. Some larger units have 3 or 4 stages (multiple heat exchangers).
- Electric Heat: Staged electric strip heaters, typically 5-15 kW per stage. 3-phase 208V or 480V. Check sequencer relays, fuse links, and heating elements.

### RTU Error Codes

**Trane ReliaTel:**
- LED1 flash code 1 — High pressure switch open
- LED1 flash code 2 — Low pressure switch open
- LED1 flash code 3 — High discharge temp
- LED1 flash code 4 — Outdoor coil sensor fault
- LED1 flash code 7 — Communication fault (to UC or BAS)
- LED1 flash code 9 — Low ambient lockout

**Carrier WeatherExpert:**
- Status 1 — Normal operation
- Alert 01 — Compressor high pressure
- Alert 02 — Compressor low pressure
- Alert 06 — Discharge temp high
- Alert 13 — Economizer fault
- Alert 17 — Supply air temp sensor fault
- Alert 22 — Communication loss

**Lennox Prodigy:**
- E1 — Pressure switch fault
- E3 — Flame rollout
- E5 — Gas valve fault
- E7 — Ignition lockout (3 tries, no flame)
- E201 — Compressor locked rotor
- E301 — Economizer actuator fault

### RTU Practical Tips

Curb adapters: RTUs mount on a roof curb. Match the curb to the unit footprint. When replacing an RTU with a different brand, you often need an adapter curb. Get the curb dimensions from both the old and new unit submittals. Measure before ordering. Duct connections are inside the curb — make sure supply and return openings align.

Gas piping to rooftop: needs to be properly supported, drip leg at the unit connection, manual shutoff before the unit, proper sizing for the BTU rating and pipe run length. Check gas pressure at the unit manifold — natural gas should be 3.5" WC minimum at the inlet with all burners firing.

Filter access: commercial RTUs should have filter racks accessible from outside the unit. Standard filter sizes: 20x20, 20x25, 24x24. MERV-8 minimum for general commercial. MERV-13 for healthcare and high-quality filtration. Check pressure drop across filters — replace when delta-P exceeds 1.0" WC on standard filters.

---

## VARIABLE AIR VOLUME (VAV) SYSTEMS

### How VAV Works

A central air handler blows cold air (typically 55F supply air) into a duct system. At each zone, a VAV box (terminal unit) modulates a damper to control how much cold air enters the zone. More cooling needed = damper opens wider. Less cooling needed = damper closes down. This saves massive fan energy compared to constant volume systems because the fan can slow down as dampers close.

### VAV Box Types

**Cooling-Only VAV** — Just a damper, no heating element. Used in interior zones where internal heat gains (people, lights, computers) provide enough warmth. The box modulates from maximum airflow (full cooling) down to a minimum airflow (prevents stagnant air). Minimum is typically 30-50% of max CFM for ventilation.

**VAV with Reheat** — Has a damper plus a hot water coil or electric strip heater downstream. When the zone needs cooling, damper modulates. When the zone needs heating, damper goes to minimum position and the reheat coil activates. Common on perimeter zones (exterior walls, windows) where you need heating in winter. Hot water reheat is more efficient than electric. Electric reheat is simpler to install.

**Fan-Powered VAV (Series)** — Has a small fan that runs continuously, drawing air from the plenum and mixing with primary air. The primary air damper modulates for cooling. Fan keeps running even when primary air is at minimum. Used on perimeter zones. Provides constant airflow to the space regardless of primary air damper position.

**Fan-Powered VAV (Parallel)** — Small fan only kicks on when heating is needed. Draws warm plenum air and mixes with primary air. Fan is off during cooling. More efficient than series because the fan doesn't run during cooling mode. Very common on perimeter zones.

### VAV Actuator Troubleshooting

The actuator opens and closes the damper based on a control signal from the zone controller.

**Types:** Spring-return (fail to minimum or maximum position on power loss), non-spring-return (holds position on power loss). Spring return is standard for safety — you want the damper to go to a known position on failure.

**Control Signals:** 0-10VDC is most common. 2-10VDC on some systems. 4-20mA on older or industrial. Floating point (open/close signals) on some older systems.

**Common problems:**
- Actuator not moving — Check power (24VAC is standard). Check control signal from controller (measure voltage at actuator terminals). Override manually to verify actuator motor works. Check for stripped coupling or broken shaft linkage.
- Actuator hunting (constantly adjusting) — PID tuning issue on the controller. Deadband too tight. Also check for air leaks around the damper causing turbulence.
- Wrong direction — Actuator wired for normally open when it should be normally closed, or vice versa. Check the configuration in the controller or DIP switches on the actuator.
- Slow response — Some actuators take 60-90 seconds for full stroke. That's normal for spring return models. If it takes longer, motor may be failing or gear train is worn.

### Static Pressure Control

The air handler fan speed is controlled to maintain a duct static pressure setpoint. As VAV boxes close (low load), static pressure rises, fan slows down. As boxes open (high load), static pressure drops, fan speeds up.

**Sensor location matters.** Put the static pressure sensor about 2/3 of the way down the longest duct run. Putting it right at the air handler gives a false reading — you'll be controlling to duct pressure at the fan, not at the remote boxes. Typical setpoint: 1.0" to 1.5" WC for a standard system. Higher setpoints waste energy.

**Static pressure reset:** Advanced strategy where the BAS resets the setpoint down when most VAV boxes are less than 80% open. If the most-open box is only 60% open, you can reduce static setpoint and save fan energy. Resets can save 10-30% of fan energy.

### Minimum Airflow Settings

Every VAV box has a minimum airflow setpoint. This is required for:
- Ventilation (ASHRAE 62.1 requires minimum outdoor air per person and per square foot)
- Air circulation (prevent stagnant air, maintain thermostat accuracy)
- Heating mode (enough air to distribute reheat effectively)

Typical minimums: 30-50% of maximum CFM for perimeter zones with reheat. Interior zones can go lower (20-30%) if ventilation requirements allow. Zero-minimum boxes exist for unoccupied spaces but you need CO2 sensing or occupancy-based ventilation to make it work with code.

### Balancing VAV Systems

**Test and balance (TAB)** on VAV systems:
1. Set all boxes to maximum position (full open dampers).
2. Set AHU fan to design speed.
3. Measure total system CFM at the air handler.
4. Walk each box — measure CFM at each box with the onboard flow sensor or a duct traverse.
5. If boxes are reading wrong, calibrate the flow sensor (K-factor adjustment on the controller).
6. Set boxes back to auto and verify minimum and maximum setpoints.
7. Check that the static pressure sensor is reading correctly with a manometer.
8. Verify the AHU is maintaining setpoint and modulating properly.

---

## BUILDING AUTOMATION SYSTEMS (BAS)

### Common BAS Brands

**Trane Tracer** — Tracer SC/SC+ is the building controller. Tracer TU controllers for terminal units. Tracer Ensemble or Tracer Concierge for the front-end software. BACnet and proprietary protocols.

**Johnson Controls Metasys** — NAE (Network Automation Engine) is the main controller. FEC (Field Equipment Controller) for terminal equipment. Metasys UI or Metasys Launcher for the front-end. BACnet, N2 (legacy), and LonWorks.

**Honeywell Niagara (Tridium)** — JACE controllers running Niagara Framework. WEBs-AX or Niagara 4 platform. Strong on integration — Niagara can talk to almost anything. BACnet, LonWorks, Modbus, and custom drivers.

**Siemens Desigo** — PXC controllers (Automation Stations). Desigo CC front-end. BACnet native. Previously Apogee (P1/P2 bus — legacy, being phased out).

**Carrier i-Vu** — CCN (Carrier Comfort Network) bus for Carrier equipment. i-Vu Pro front-end. BACnet integration for non-Carrier devices. Mostly found in Carrier-dominant buildings.

### Communication Protocols

**BACnet** — The industry standard. Most new equipment speaks BACnet. Two main transport layers:
- BACnet/IP — Runs on the building's Ethernet network. Standard IT infrastructure. Most common today.
- BACnet MS/TP — Runs on RS-485 twisted pair wiring. Slower but simple, daisy-chain wiring. Common for terminal unit controllers. 9600 to 76800 baud. Max 128 devices per trunk. Polarity matters — miswired MS/TP is the #1 commissioning headache.

**LonWorks** — Echelon protocol. Was common in the 2000s, less common now. Free-topology wiring (bus, star, loop). FTT-10 transceivers. Still found in many existing buildings. Johnson Controls and Honeywell used it heavily.

**Modbus** — Simple serial protocol. Modbus RTU (RS-485) and Modbus TCP (Ethernet). Common for boilers, chillers, VFDs, meters, and other standalone equipment. Register-based — you read/write to numbered registers. Easy to integrate but no autodiscovery — you need the register map for every device.

### BAS Points

**AI — Analog Input:** Reads a sensor. Temperature (10K thermistor, 1K RTD, or 4-20mA transmitter), humidity, pressure, CO2 level. Wired to the controller's AI terminal. Typical: space temp sensor = 10K Type II or III thermistor.

**AO — Analog Output:** Sends a modulating signal. 0-10VDC to an actuator or VFD. 4-20mA to a valve actuator or damper actuator. Typical: AO commanding a VAV damper actuator 0-10V, where 0V = closed, 10V = full open.

**BI — Binary Input:** Reads an on/off status. Dry contact closure. Equipment run status (current switch), alarm contact, flow switch, pressure switch. Wired as normally open (NO) or normally closed (NC) — document which.

**BO — Binary Output:** Commands an on/off device. Relay output to start/stop a fan, pump, or compressor. Open or close a two-position valve or damper. 24VAC switched through a relay.

### Trending and Alarming

**Trending** — Record point values over time. Critical for troubleshooting. Set up trends on:
- Supply air temperature
- Space temperatures for problem zones
- Valve and damper positions (shows if they're hunting or maxed out)
- Static pressure and setpoint
- Chiller/boiler operating parameters

Trend intervals: 1-5 minutes for troubleshooting, 15-minute intervals for long-term data. Store locally on the controller or pull to a server. Change-of-value (COV) trending is more efficient — only records when the value changes by a threshold.

**Alarming** — Set high/low limits on critical points. Equipment failure alarms (loss of flow, high temperature). Return-to-normal notifications. Alarm routing: email, text, BAS front-end popup. Priority levels: critical (immediate response), high (respond within hours), low (routine attention). Don't alarm everything — alarm fatigue is real and dangerous.

### Common Integration Issues

- **BACnet device instance conflicts** — Every device on a BACnet network needs a unique device instance number. Duplicate instances cause communication failures. Map all instances before commissioning.
- **MS/TP wiring errors** — Reversed polarity (+/-), missing bias resistors, EOL (end-of-line) terminators not installed, excessive cable length (4000 ft max for FTT-10, varies for MS/TP). Use a BACnet scanner tool to verify communication.
- **IP address conflicts** — BACnet/IP devices need unique IPs on the building network. DHCP vs static addressing — use static for controllers. Subnet configuration must be correct.
- **Modbus register mapping** — Wrong register numbers, wrong data format (16-bit integer vs 32-bit float), wrong byte order (big-endian vs little-endian). Get the correct register map from the equipment manufacturer and verify with a Modbus scanner.

---

## COMMERCIAL BOILERS

### Boiler Types

**Fire-Tube** — Hot combustion gases pass through tubes surrounded by water. Most common for commercial hot water and low-pressure steam. Simple, robust. Cleaver-Brooks CB, Hurst, Burnham. Typical sizes 500 MBH to 12,000 MBH (million BTU/hr).

**Water-Tube** — Water flows through tubes surrounded by combustion gases. Higher pressure capability. Used for high-pressure steam (hospitals, industrial). Less common in standard commercial HVAC.

**Condensing Boilers** — Extract additional heat by condensing flue gases. Require return water temps below 130F to achieve condensing (below the dewpoint of flue gases, around 135F for natural gas). Efficiency up to 96-98%. Stainless steel or aluminum heat exchangers resist corrosive condensate. Common brands: Lochinvar CREST/KNIGHT XL, Aerco Benchmark, Weil-McLain SlimFit, Laars Rheos. PVC or CPVC venting (big cost savings over stainless steel chimney). Drain the condensate to a neutralizer kit before the floor drain — it's acidic (pH 3-4).

**Non-Condensing Boilers** — Traditional design. Must maintain return water temps above 140F to prevent flue gas condensation in the heat exchanger (which causes corrosion in carbon steel or cast iron). Efficiency 80-87%. Need proper chimney — metal or masonry, Category I or III venting. Brands: Weil-McLain 88, Cleaver-Brooks, Burnham.

### Operating Pressures

**Low-Pressure Steam** — Under 15 PSI. Most commercial heating. ASME Section IV. Operating typically at 2-10 PSI. Safety valve set at 15 PSI.

**High-Pressure Steam** — 15 PSI and above. ASME Section I. Requires a licensed stationary engineer on-site in most jurisdictions. Found in hospitals, large campuses, industrial.

**Hot Water Boilers** — Typical operating pressure 12-30 PSI (depends on building height — need enough pressure to push water to the top floor). Temperature setpoint 140-180F typically. Outdoor air reset: lower water temp in mild weather (saves energy). Standard reset schedule: 180F water at 0F outdoor, down to 140F water at 60F outdoor. Adjust to building.

### Flame Safeguard Controls

The flame safeguard (burner management system) controls the ignition sequence and monitors the flame.

**Honeywell** — RM7800 series (widely used), S7800 (upgraded). 7800 series modules control pre-purge timing, ignition trial, main flame proving. Lockout after failed trial — check flame signal (UV scanner or flame rod), check ignition electrode gap, check gas valve operation. Flame signal: UV scanner reads in microamps — typically needs 2-5 uA minimum to prove flame. Check the scanner lens for soot.

**Fireye** — EP, MicroM, NexusII, Flame-Monitor. Similar function. Fireye uses InSight display for diagnostics on newer models. Check chassis indicator lights for fault codes.

**Common Lockout Causes:**
- No flame detected during trial for ignition — gas valve not opening (check power to valve, check safety circuit), no spark/pilot (check electrode gap 1/8" typical, check ignition transformer), flame rod/UV scanner dirty or failed.
- Flame loss during run — fluctuating gas pressure, dirty flame rod, cracked UV scanner lens, intermittent gas valve, combustion air problem.
- Safety circuit open — high limit tripped (check water temp, check aquastat), low water cutoff (check water level in steam boiler, test the LWCO), gas pressure switch (high or low gas pressure).

### Boiler Error Codes

**Lochinvar KNIGHT/CREST (SMART SYSTEM):**
- E01 — Ignition failure (3 attempts, no flame)
- E02 — False flame (flame signal when there shouldn't be)
- E03 — Low water flow (check pump, check flow switch, check strainer)
- E04 — High limit exceeded (over 200F or setup value)
- E05 — Sensor failure (inlet or outlet temp sensor open/shorted)
- E10 — Fan fault (blower not proving)

**Aerco Benchmark:**
- Fault 01 — Flame failure during run
- Fault 02 — Ignition failure
- Fault 04 — High limit lockout
- Fault 11 — Inlet sensor fault
- Fault 12 — Outlet sensor fault
- Fault 20 — Low water flow
- Fault 40 — Fan speed fault

**Weil-McLain (Ultra Series):**
- Code 0 — No fault
- Code 1 — Ignition lockout
- Code 2 — False flame
- Code 3 — High limit
- Code 6 — Sensor error
- Code 7 — Low water (flow switch)

### Water Treatment for Boilers

Critical for steam boilers. Hot water systems need treatment too but less intensively.

**Steam Boiler Treatment:**
- Blowdown removes dissolved solids. Bottom blowdown (sludge) daily on manual valve. Surface blowdown (continuous) for dissolved solids control.
- Chemical treatment: oxygen scavenger (sodium sulfite), scale inhibitor, alkalinity control (maintain pH 10.5-11.5 for steel boilers).
- Makeup water: softened water minimum, dealkalized or RO water for high-pressure systems.
- Condensate return: test for pH and contamination. Low pH condensate indicates CO2 corrosion — add amine treatment.

**Hot Water System Treatment:**
- Closed loop so minimal makeup water.
- Glycol systems need inhibitor package to prevent corrosion from glycol breakdown.
- Check pH annually (target 8.0-10.0). Check inhibitor levels.
- Automatic air vents and dirt separators help keep the system clean.

---

## COMMERCIAL REFRIGERATION (Walk-ins, Reach-ins)

### Walk-in Cooler/Freezer Components

**Box construction:** Insulated panels (4" for coolers, typically 4-6" for freezers). Cam-lock or tongue-and-groove assembly. Floor panels rated for forklift traffic in some applications. Vapor barrier on the warm side — critical for freezers to prevent moisture migration and ice formation in the panels.

**Door:** Strip curtains inside, gaskets on the door frame, door closer (spring or pneumatic). Heater wire in the door frame on freezers (prevents gasket from freezing to the frame). Kick plate on the bottom.

**Condensing Unit:** Located outside or on the roof. Contains the compressor, condenser coil, condenser fan, receiver (on larger units), and electrical controls. Common brands: Heatcraft (Bohn, Larkin, Climate Control), Copeland/Emerson, Tecumseh, KeepRite. Sizes from 1/2 HP (small reach-in) to 15+ HP (large walk-in freezer).

**Evaporator:** Inside the box. Coil with fan(s) that blow cold air into the space. Low-profile units for limited ceiling height. Centered units hang from the ceiling. Proper airflow pattern is critical — air should sweep across the product and back to the return side of the coil.

### Evaporator Coil Sizing and TD

**TD (Temperature Differential)** = Coil temperature minus box temperature (actually, box temp minus coil temp stated as a positive number). For walk-in coolers (35F box), a 10F TD is standard — evaporator runs at 25F SST. For walk-in freezers (-10F box), use 8-10F TD — evaporator runs at -18F to -20F SST.

Lower TD means higher humidity in the box (good for fresh produce, bad for ice cream). Higher TD means more moisture removal (lower humidity).

**Coil sizing:** Match the BTU capacity at the design TD. A cooler coil rated at 20,000 BTU at 10F TD will only deliver about 10,000 BTU at 5F TD. Always check the TD rating in the spec sheet.

### Defrost Types

**Off-Cycle Defrost** — Turn off the compressor, let the coil warm up above 32F from the ambient box temperature. Only works on coolers (box above 35F). Simplest, no extra components. Timer just shuts down the compressor and fans for 20-30 minutes.

**Electric Defrost** — Heater elements embedded in the evaporator coil. Timer initiates defrost, energizes heaters, fan(s) off during defrost. Typical defrost duration 20-30 minutes, plus 5-minute fan delay after defrost (let coil drain before blowing water). Standard on freezers. 2-6 defrosts per day depending on application. Check heater amp draw to verify elements are working — compare to nameplate.

**Hot Gas Defrost** — Routes hot discharge gas directly to the evaporator coil. Fast, efficient. More complex piping. Common on larger rack systems (supermarket refrigeration). Requires hot gas solenoid valve, check valves, and proper piping.

### TXV Adjustment

The thermostatic expansion valve (TXV) controls superheat at the evaporator outlet.

**Target Superheat:** 8-12F for walk-in coolers, 6-10F for freezers. Measure suction line temp at the bulb location minus saturation temp at suction pressure.

**Adjusting:** Turn the stem clockwise to increase superheat (close the valve slightly — less refrigerant flow). Counterclockwise to decrease superheat (open the valve — more flow). Adjust 1/4 turn at a time, wait 15-20 minutes for the system to stabilize before measuring again. The bulb must be properly mounted (good thermal contact, insulated from ambient air) at the 4 or 8 o'clock position on a horizontal suction line.

**Common TXV Problems:** Bulb lost contact (fell off or insulation missing), wax in the power element (old valve), plugged screen (inlet debris), hunting (oversized valve, system issue, or defective valve).

### Defrost Timer/Board Settings

**Mechanical Timer (Paragon, Grasslin):** Pins or trippers on the dial set defrost initiation times. A separate timer or termination thermostat ends defrost. Set pins for the number of defrosts needed — typically 2-4 per day for freezers. Termination temp: 55-65F on the coil (ensures all ice is melted). Failsafe time termination: 30-45 minutes max.

**Electronic Defrost Board (Heatcraft DTX, Beacon II):** More precise. Set parameters via DIP switches or digital interface. Settings include: number of defrosts per day, defrost duration, termination temperature, drain time, fan delay. Adaptive defrost boards adjust defrost frequency based on actual frost accumulation — saves energy.

### Common Refrigeration Problems

- **Iced evaporator coil** — Defrost not working (check heaters, timer, termination thermostat). Defrost frequency too low. Door left open (moisture ingress). Damaged door gaskets.
- **Short cycling** — Low refrigerant (check for leaks). Dirty condenser (clean with coil cleaner and rinse). Thermostat differential too tight. Oversized equipment.
- **High suction pressure** — Overcharge, TXV stuck open, compressor valve failure (not pumping efficiently), hot gas bypass stuck open.
- **Low suction pressure** — Low charge, TXV restricted or closed, dirty evaporator, low airflow (failed fan motor, iced coil), liquid line restriction (kinked line, clogged filter-drier).
- **Compressor running but not cooling** — Bad compressor valves (do a pump-down test), refrigerant leak (system empty), TXV not feeding.
- **High discharge pressure** — Dirty condenser, failed condenser fan motor, overcharge, air in system (non-condensables), high ambient without head pressure control.

---

## COMMERCIAL KITCHEN VENTILATION

### Hood Types

**Type I Hood** — For equipment that produces grease-laden vapors. Fryers, grills, charbroilers, ovens, ranges, woks. Must have grease filters (baffle type, stainless steel), grease gutters, and a fire suppression system. Exhaust duct must be welded or listed grease duct. 16-gauge stainless minimum for the hood.

**Type II Hood** — For equipment that produces heat, steam, or moisture but NO grease. Dishwashers, steam tables, ovens (sometimes). No grease filters required, no fire suppression required. Lighter construction acceptable.

### Makeup Air (MUA)

Kitchen exhaust removes a huge volume of air from the building. That air has to be replaced or the building goes negative pressure — doors won't close, combustion appliances backdraft, exhaust performance drops.

**Makeup air rules of thumb:** Replace 80-90% of exhaust air with conditioned makeup air. Short-cycle (or tempered) MUA: heated to at least 55F in winter to prevent cold drafts on kitchen staff. Some codes require transfer air from the dining room to count toward a portion of MUA. Direct-fired gas MUA units (Captive-Aire, CaptiveAire,?"Accurex) are common — 100% combustion efficiency since combustion products go directly into the airstream (only acceptable for MUA, never for general HVAC).

**ASHRAE 154 and local codes** govern kitchen ventilation rates. CFM requirements depend on hood type, equipment type, and cooking volume. Proximity hoods (close to the appliance) need less CFM than wall canopy hoods. Example: charbroiler under a wall canopy hood needs about 350-400 CFM per linear foot of hood.

### Fire Suppression Systems

**Ansul R-102** — Wet chemical system. Most common in commercial kitchens. Nozzles positioned to cover each piece of cooking equipment. Wet chemical (potassium-based) agent. Fusible links melt at 360F or manual pull station activates. System shuts off gas and electric to cooking equipment on activation. Inspect and service semi-annually (most jurisdictions). Full recharge after any activation.

**Kidde (Badger)** — Similar wet chemical system. Competing brand to Ansul.

**Key maintenance:** Check fusible links (replace at 360F or per schedule), verify nozzle aim (kitchens rearrange equipment), check gas shutoff valve operation, verify manual pull station is accessible, check expiration date on agent cylinder (6-year or 12-year depending on type), test detection line for continuity.

### Grease Duct Requirements

- Welded black steel (16-gauge minimum) or listed grease duct system
- Continuous weld, liquid-tight — grease fires can spread through any gap
- Maintain clearance to combustibles (18" minimum for unprotected, less with listed enclosure/wrap)
- Cleanout access every 12 feet on horizontal runs and at every change of direction
- Slope horizontal runs at least 1/4" per foot back toward the hood (so grease drains back)
- No fire dampers in grease ducts — they would be destroyed in a fire and trap grease
- Grease duct cleaning: quarterly minimum for heavy-use kitchens (charbroilers, fryers), semi-annually for moderate use. Document cleaning with before/after photos.

### Exhaust Fan Maintenance

Kitchen exhaust fans are typically upblast centrifugal fans on the roof. They run in a harsh environment — hot, greasy air.

- Inspect and clean fan blades, housing, and grease trap quarterly
- Grease builds up on the blades and causes vibration — unbalanced fan = bearing failure
- Check belt tension (if belt-driven) or motor bearings (if direct drive)
- Hinged fan base allows the fan to tip up for cleaning access
- Grease containment: rooftop grease catcher or curb with drip gutter. Clean regularly to prevent roof damage and fire risk.
- Fan speed: verify airflow meets design CFM with a capture test or smoke test at the hood. If capture is poor, check belt slippage, motor RPM, ductwork integrity, and MUA balance.
