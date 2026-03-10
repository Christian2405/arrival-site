# HVAC Installation Procedures

## About This Guide
Installing HVAC equipment is where theory meets reality. A bad installation ruins even the best equipment — I've seen $15,000 systems perform like junk because someone skipped the evacuation or didn't size the ductwork. This guide covers the procedures that separate a professional installation from a hack job. Follow every step, every time. The callbacks you don't get are worth more than the time you "save" by cutting corners.

---

## Split System Installation (Air Conditioning and Heat Pump)

### Outdoor Unit Placement
- Minimum 24 inches clearance on the service side (where the valves are), 12 inches on other sides, and 60 inches above the unit (for vertical discharge units). Check the manufacturer's installation manual — Carrier, Trane, Lennox, and Goodman all have slightly different clearance requirements.
- Set the unit on a composite or concrete pad, level, at least 3 inches above grade (4-6 inches in snow regions). Condenser pads should be larger than the unit footprint by at least 2 inches on each side.
- Keep the unit away from dryer vents (lint clogs the coil), garden areas (dirt and debris), and bedroom windows (noise).
- Run the disconnect within sight of and within 25 feet of the unit. Non-fused disconnect for systems with breaker protection, fused disconnect with time-delay fuses (HACR type) sized per the maximum fuse/breaker size on the unit nameplate.
- Heat pumps: in areas with snow, elevate the unit on a riser stand — at least 4-6 inches above expected snow depth. Snow blocking the coil starves the system during heating season.

### Indoor Unit (Evaporator Coil and Air Handler)
- The evaporator coil mounts on the furnace or air handler in the airflow direction — check the arrow on the coil for proper orientation (there's usually an arrow stamped on the end plate showing the airflow direction).
- Cased coils: match the coil to the air handler/furnace width. An A-coil or N-coil sits on top of an upflow furnace. A slab coil goes in horizontal applications. Uncased coils are cheaper but must be properly supported inside the plenum.
- Condensate drain: primary drain goes to the nearest drain or exterior. In attic installations, a secondary (emergency) drain pan under the air handler with a separate drain line is code-required. Many jurisdictions also require a float switch on the primary drain pan that shuts off the system if the drain clogs. The primary drain should have a P-trap — the trap depth equals the negative static pressure at the coil (typically 3/4" to 1" of water column). Without the trap, the blower suction pulls air through the drain instead of water.
- Seal the coil enclosure to the furnace with metal tape (not duct tape — it fails in months). Air leaks here bypass the filter and coil, reducing efficiency and depositing dirt on the blower.

### Line Set Sizing and Installation
The line set connects the outdoor and indoor units — a smaller liquid line and a larger suction line.

Standard line set sizes (always verify with manufacturer specifications):
- 1.5 to 2 ton system: 3/8" liquid line, 3/4" suction line
- 2.5 to 3 ton system: 3/8" liquid line, 7/8" suction line
- 3.5 to 5 ton system: 3/8" liquid line, 7/8" or 1-1/8" suction line (varies by manufacturer and line set length)

Line set length limits: most residential systems are rated for up to 50 feet. Some are rated to 75 feet. Beyond the rated length, you may need to add refrigerant (typically 0.6 oz per foot of 3/8" liquid line beyond the factory charge length — but check the specific unit's documentation). Line sets shorter than 15 feet can cause operational issues with some systems — Carrier and Trane both note minimum line lengths in their manuals.

Insulate the suction line (the big one) with 3/4" wall thickness closed-cell foam insulation (Armaflex, Rubatex). The liquid line does not require insulation unless it runs through an unconditioned space where heat gain is a concern (in extremely hot climates, insulating the liquid line can improve efficiency by 1-2%). Never insulate the liquid and suction lines together in the same wrap — this defeats the purpose of the thermal separation.

When routing through walls, use a sleeve with sealant or fire-rated caulk. Keep line sets away from electrical wires (at least 6 inches separation) and never run them through a chimney or flue.

Oil traps: on vertical suction line runs greater than 20 feet, install an oil trap at the base of the riser. A trap is a small U-bend (6 inch loop in the suction line) that collects oil and returns it to the compressor. Without it, oil pools at the bottom of the riser and the compressor runs low on oil. On extremely long vertical runs (40+ feet), add a second trap halfway up.

### Brazing and Nitrogen Flow
Every braze joint on a refrigerant system must be made with flowing nitrogen inside the lines. This prevents copper oxide scale (the black flaky stuff) from forming inside the tube, which will migrate to the metering device and compressor valves, causing restriction and wear.

Set your nitrogen regulator to 2-5 PSI — just a gentle flow. Connect to a service port or an open end of the system. You should be able to feel a light flow at the opposite end while brazing.

Use Sil-Fos (BCuP-6) for copper-to-copper joints — it's self-fluxing on copper. For copper-to-brass joints (like connecting to service valves), use Stay-Silv 15% with flux. Heat the fitting, not the rod. When the joint reaches brazing temperature (about 1200 degrees F), the alloy will flow into the joint by capillary action. A good joint has a fillet of alloy visible around the entire circumference — no gaps.

Never overheat the joint. Cherry red copper is too hot — you'll burn the flux, oxidize the copper, and get a weak joint. Proper temperature shows as a dull red to dark orange glow.

### Evacuation Procedure
This is where most hack installers fail. Proper evacuation removes moisture and non-condensable gases (air) from the system. Moisture + refrigerant + oil = acid, which destroys compressor windings and valves over time.

Equipment needed: two-stage vacuum pump (5-6 CFM minimum for residential), micron gauge (NOT your manifold gauges — they're not accurate enough at vacuum levels), core removal tool, and large-bore vacuum hoses (3/8" minimum, 1/2" preferred — BluVac, Appion, or Fieldpiece make good ones).

Procedure:
1. Remove Schrader valve cores from both service ports using a core removal tool. This dramatically increases vacuum speed — a Schrader core restricts flow and can double or triple evacuation time.
2. Connect the vacuum pump to the center (yellow) hose. Connect the blue and red hoses to the service ports. Use the shortest, largest-diameter hoses possible.
3. Connect the micron gauge as close to the system as possible — ideally directly at the service port, not at the pump end. If your gauge reads 500 microns at the pump but the system is at 2000 microns, you've been fooled.
4. Start the vacuum pump and open both manifold valves fully.
5. Pull the system down to 500 microns or below. For most residential systems with a standard line set (25-50 feet), this takes 30-60 minutes with a good pump and large-bore hoses. For long line sets, large systems, or systems with residual moisture, it can take hours.
6. Close the manifold valves and shut off the pump.
7. Monitor the micron gauge for the decay test. The system should hold below 500 microns for at least 10 minutes. A slight rise to 600-700 microns and then stabilizing is acceptable (outgassing from compressor oil and residual moisture). Rising steadily above 1000 microns indicates a leak or significant moisture.
8. If it rises above 1500 microns: re-pull the vacuum and repeat. If the system consistently fails to hold, there's a leak — nitrogen pressure test to find and fix it before trying again.
9. Once the vacuum holds, reinstall the Schrader cores (while still under vacuum if using a core removal tool with valve, or quickly to minimize air entry), then release refrigerant from the condenser by opening the service valves (liquid side first, then suction side).

Common evacuation mistakes:
- Using manifold compound gauges to measure vacuum instead of a micron gauge. Manifold gauges bottom out around 29.9" Hg, which equals roughly 25,000 microns — 50 times too high for a proper evacuation.
- Using small-bore hoses (1/4" ID). Standard charging hoses add massive restriction during vacuum. Use 3/8" or 1/2" ID vacuum hoses.
- Not removing Schrader cores. A Schrader core turns a 30-minute evacuation into a multi-hour struggle.
- Declaring it "good enough" at 1500 microns. It's not. The moisture that 1500 microns leaves behind will form acid and eat the compressor windings within 2-5 years. Get to 500 microns. Your reputation depends on it.
- Running the pump for a set time without checking microns. Time alone means nothing — you must verify with a micron gauge.

---

## Mini-Split Installation

### Selecting the Location
Indoor unit (wall-mounted cassette): mount on an exterior or interior wall, centered in the room for best air distribution. Minimum clearances: 6 inches from ceiling, 4 inches from each side wall. The unit should not be above a TV or electronics (condensation drip risk). Avoid locations that receive direct sunlight or are near heat sources.

Mount the backing plate level — even 1/4" off and it'll look wrong on the wall forever. Use a laser level. The plate must be on solid backing — ideally into studs. Use toggle bolts or screw anchors if you can't hit studs, but make sure they'll hold the weight of the unit (25-40 lbs for a wall-mount).

Outdoor unit: same clearance rules as split systems. For multi-zone systems (one outdoor unit serving 2-5 indoor heads), verify that the combined indoor capacity doesn't exceed 130% of the outdoor unit rating (most manufacturers allow oversizing of indoor heads for zoning flexibility — Mitsubishi and Daikin both allow this, Fujitsu has tighter limits). Place multi-zone outdoor units where the line set runs to each indoor head are as equal in length as practical.

### Wall Penetration and Line Set Routing
Drill the wall penetration with a 3" to 3-1/2" core drill or hole saw, sloping slightly downward toward the outside (2-3 degree pitch minimum) for condensate drainage. The hole should be behind the indoor unit — either directly behind or to one side (left or right, depending on the model — check the installation manual for pipe routing options).

Install a wall sleeve or pass-through fitting. Line hide systems (SpeediChannel, Slimduct) on the exterior provide a clean, professional look — much better than exposed line sets. Route from the wall penetration down to the outdoor unit.

The condensate drain line must slope continuously downward — 1/4" per foot minimum. No sags, no traps (unless the manufacturer specifically calls for one — some Daikin models do), no uphill runs. If the condensate must travel upward to reach a drain point, install a mini condensate pump (Rectorseal Aspen, Little Giant VCMA-15). These pumps are small enough to fit inside the indoor unit housing or on the wall behind it.

Line set lengths for mini-splits: maximum varies by brand and model. Mitsubishi M-Series: up to 98 feet (49 feet max height difference). Daikin: up to 65 feet for residential units. Fujitsu: up to 65 feet. LG: up to 82 feet. Always check the specific model's installation manual — longer runs require additional refrigerant charge and may reduce capacity.

### Electrical Requirements
Most mini-splits require a dedicated circuit:
- 9,000-12,000 BTU (3/4 to 1 ton): 15 or 20 amp, 208/230V single phase (some 115V models exist — Mitsubishi GL, Friedrich, some Pioneer units)
- 18,000-24,000 BTU (1.5 to 2 ton): 20-25 amp, 208/230V
- Multi-zone outdoor units (2-5 zones): 30-50 amp, 208/230V (check the nameplate MCA and MOCP)

Power goes to the outdoor unit in most configurations. The outdoor unit powers the indoor head through the communication cable. Communication wire between indoor and outdoor units: typically 14/4 or 16/4 stranded (varies by brand — Mitsubishi uses 14/3 for many single-zone models, Daikin uses 14/4). Run the communication wire with the line set through the wall penetration.

---

## Furnace Installation

### Venting Categories
This is one of the most critical aspects of furnace installation. Get the venting wrong and you risk carbon monoxide poisoning or house fires.

- **Category I (natural draft, non-condensing):** Flue gas temperature is above the dew point, negative pressure in the vent. Uses Type B double-wall vent (galvanized inner wall, aluminum outer). Must terminate above the roof per code — typically minimum 5 feet above the highest connected draft hood and at least 2 feet above any roof surface within 10 feet horizontally. Common in 80% AFUE furnaces and atmospheric water heaters. When replacing a furnace from Category I to Category IV, if a water heater remains on the old chimney, the chimney may now be oversized for the water heater alone — causing draft problems and potential CO spillage. Re-evaluate the venting when you change any connected appliance.

- **Category II:** Negative pressure, condensing flue gases. Rare in residential — mostly commercial boilers. Uses special corrosion-resistant vent materials.

- **Category III (power-vented, non-condensing):** Positive pressure in the vent, non-condensing flue gases. Uses special stainless steel venting (AL29-4C, such as Z-Flex Z-Vent or DuraVent FasNSeal). Can vent through a sidewall. Common in power-vented water heaters and some mid-efficiency furnaces.

- **Category IV (direct-vent, condensing):** Positive pressure, condensing flue gases. Uses PVC or CPVC vent pipe (Schedule 40 minimum — some jurisdictions require Schedule 40 specifically, others accept cellular core PVC). Can vent through a sidewall or roof. The standard for 90%+ AFUE furnaces. Intake and exhaust pipes must be separated by the distance specified by the manufacturer (typically 12 inches minimum between terminations) or use a concentric vent kit (pipe-in-pipe). Vent terminations must be at least 12 inches above grade (some codes require 12 inches above expected snow depth), 12 inches from any window or door opening, 12 inches from any soffit or outside corner, and 3 feet above any forced air inlet within 10 feet.

### Combustion Air Requirements
Every fuel-burning appliance needs air for combustion and dilution/draft. The air supply calculation depends on whether the equipment is in a confined or unconfined space.

**Unconfined space:** At least 50 cubic feet of room volume per 1,000 BTU/hr of total input rating of all fuel-burning appliances in the room. A 100,000 BTU furnace and 40,000 BTU water heater together need 140,000/1,000 x 50 = 7,000 cubic feet. That's a room roughly 18' x 18' with a 9' ceiling. Most closets and utility rooms don't qualify.

**Confined space (the more common scenario):** You need two combustion air openings — one within 12 inches of the ceiling and one within 12 inches of the floor.
- If drawing air from outdoors through ducts: each opening must have a free area of at least 1 square inch per 4,000 BTU/hr (for direct vent to outdoors) or 1 square inch per 2,000 BTU/hr (for horizontal duct runs over 10 feet).
- If drawing air from adjacent indoor rooms: each opening must have a free area of at least 1 square inch per 1,000 BTU/hr, and the connecting rooms must have sufficient total volume.

Direct-vent (Category IV) furnaces draw their own combustion air through the intake pipe and don't rely on room air — they're sealed combustion. This is a major advantage in tight construction and is why Category IV furnaces are preferred in new construction.

### Clearances to Combustibles
Check the rating plate on every furnace — it specifies the required clearance to combustible materials on all sides. Typical for a sealed-combustion Category IV furnace: 0 inches on the sides (but you still need service access — typically 24 inches on the service side), 0-1 inches on top, 0 inches at the back. But an 80% furnace with a draft hood might need 6 inches on the sides and 6 inches above the draft hood. Some older furnaces require 2 inches on the back and 6 inches on top.

The vent connector (pipe from the furnace to the chimney/vent) has its own clearance requirements: Type B vent needs 1 inch clearance to combustibles. Single-wall vent pipe needs 6 inches. PVC vent (Category IV) has no clearance requirement because the pipe is cool to the touch (flue gases are already condensed).

### Gas Pipe Sizing
The gas pipe must be large enough to deliver adequate gas volume at proper pressure. Undersized gas pipe = low gas pressure at the appliance = incomplete combustion, low heat output, and potential CO production.

Sizing depends on: total BTU load of all appliances on the line, pipe length from the meter to the farthest appliance, type of gas (natural gas or propane), inlet pressure, allowable pressure drop, and pipe material.

Quick reference for natural gas (low pressure, under 2 PSI delivery, 0.3" WC pressure drop allowed):
- 1/2" black iron pipe: up to 92,000 BTU at 20 feet, 65,000 BTU at 50 feet, 52,000 BTU at 80 feet
- 3/4" pipe: up to 199,000 BTU at 20 feet, 141,000 BTU at 50 feet, 112,000 BTU at 80 feet
- 1" pipe: up to 372,000 BTU at 20 feet, 264,000 BTU at 50 feet, 210,000 BTU at 80 feet
- 1-1/4" pipe: up to 678,000 BTU at 20 feet, 480,000 BTU at 50 feet, 382,000 BTU at 80 feet

These are from IFGC tables for Schedule 40 iron pipe. When in doubt, go one size larger — you never regret oversizing gas pipe. The installation manual for the furnace will specify the minimum supply gas pressure under load (typically 5.0 inWC for natural gas, 11.0 inWC for LP).

CSST (corrugated stainless steel tubing, like TracPipe CounterStrike or Gastite FlashShield) must be bonded per manufacturer requirements and local code. Bonding connects a #6 AWG copper conductor from a CSST fitting directly to the grounding electrode system. This protects against lightning-induced arcing through the thin stainless steel wall. Some newer CSST products (CounterStrike, FlashShield) have a conductive jacket that provides some arc resistance, but bonding is still required.

---

## Ductwork Design and Installation

### Sizing by CFM
Every room needs a specific amount of conditioned air (CFM — cubic feet per minute). General guideline: 400 CFM per ton of cooling capacity. A 3-ton system needs approximately 1200 CFM total. But this is the starting point — actual room-by-room CFM comes from the Manual J load calculation (which tells you BTU load per room) and the Manual D duct design (which sizes ducts for the CFM required).

Individual room CFM is determined by dividing the room's heating or cooling load by the system's delivery capacity. In practice, most residential bedrooms need 80-150 CFM, living rooms 150-300 CFM, kitchens 100-200 CFM, and bathrooms 50-80 CFM. But these vary widely based on window area, insulation, exposure, and climate.

Duct sizing by CFM (for round duct at the standard friction rate of 0.08 inWC per 100 feet equivalent length):
- 80 CFM: 6" round duct
- 120 CFM: 7" round duct
- 160 CFM: 8" round duct
- 225 CFM: 9" round duct
- 300 CFM: 10" round duct
- 400 CFM: 12" round duct
- 700 CFM: 14" round duct
- 1000 CFM: 16" round duct
- 1200 CFM: 18" round duct (or equivalent rectangular)

For rectangular duct, use the equivalent round diameter chart. An 8x8 rectangular duct is roughly equivalent to a 9" round duct — not 8". A common mistake is assuming the height and width of rectangular duct directly translates to a round diameter. It doesn't. Use the chart.

### Static Pressure Design
Total system static pressure should not exceed the equipment's rated external static pressure — typically 0.5 inWC for most residential air handlers and furnaces. Some higher-end units (variable speed, ECM blower equipped) rate at 0.7-0.8 inWC. Never exceed the manufacturer's rating.

Budget your static pressure across the system:
- Filter: 0.10 to 0.25 inWC (fiberglass flat filter on the low end, MERV 13 pleated on the high end — MERV 16 filters can be 0.35+ inWC and may require a larger filter cabinet)
- Evaporator coil (wet, with condensation): 0.15 to 0.30 inWC
- Supply ductwork (trunk and branches): 0.10 to 0.20 inWC
- Return ductwork: 0.05 to 0.15 inWC
- Supply registers and grilles: 0.02 to 0.05 inWC each
- Return grilles: 0.02 to 0.03 inWC each

If your components total exceeds the unit's rated external static, you need bigger ducts, a bigger return, or a lower-restriction filter. High static pressure is the single most common installation deficiency in residential HVAC — it reduces airflow, increases energy consumption, shortens equipment life, and makes the system loud.

### Flex Duct Installation Rules
Flex duct is convenient and widely used, but easy to install wrong. Rules per IRC M1601.4.1 and ACCA Manual D:
- Stretch it fully — compressed flex duct has dramatically higher resistance. A flex duct compressed to 70% of its length has roughly double the friction loss compared to fully stretched. Pull it tight and cut to length.
- Support every 4 feet maximum. Use wide hangers (at least 1-1/2" wide) to prevent the hanger from compressing the duct. No sags greater than 1/2" per foot between supports.
- Maximum total length per run: check your local code — IRC says 14 feet in some editions, but many jurisdictions allow longer runs. Regardless, shorter is always better. For runs over 15 feet, consider using rigid metal duct for the trunk with flex branches.
- Connections: pull the inner liner over the metal collar at least 2 inches, secure with a zip tie or stainless steel clamp, then pull the outer jacket and vapor barrier over the connection and secure with a second zip tie. Seal with mastic at all connections — both the inner liner and the outer jacket.
- Never route flex duct through a sharp turn — it kinks and closes off the airflow. Use a rigid metal elbow and connect flex to each end. Flex should not turn more than 90 degrees, and even that should be a gentle, sweeping bend.
- Keep flex duct away from heat sources — it's plastic and will melt near flue pipes or recessed lights (unless rated for the application).
- Don't use flex duct for return air plenums — the corrugated interior is too restrictive for the large airflow returns require. Use rigid sheet metal or duct board for return trunks.

### Register Placement Strategy
Supply registers should be located on exterior walls, under windows, when possible. This counteracts the cold drafts from windows in winter and the heat gain from windows in summer. In heating-dominated climates, floor registers under windows are the gold standard — the warm air rises and washes the cold window surface. In cooling-dominated climates, ceiling registers work well because cool air drops.

High sidewall registers (6-8 inches below the ceiling) work for both heating and cooling if the throw is adequate to reach the opposite wall. Adjustable-blade registers allow you to direct air along the ceiling (cooling mode) or toward the floor (heating mode).

Return air sizing is consistently the most undersized element in residential duct systems. A 3-ton system needs approximately 1200 CFM of return air. At a face velocity of 500 FPM (to keep noise down), that's 2.4 square feet of net free area for the return grille(s). A single 20x25 return grille has about 2.2 square feet of free area — barely enough for a 3-ton system. Two return locations is better. Every bedroom with a door needs a return air path — either a dedicated return grille in the room, a jump duct or transfer grille to the hallway, or (least effective) a 1" undercut on the door.

---

## Thermostat Wiring

### Standard Wire Colors
The industry "standard" (often followed, but never rely on color alone in older homes — always verify with a meter):
- **R (Red):** 24V power from the transformer. R is always hot. Some systems have separate Rh (heating power) and Rc (cooling power) terminals — these are jumpered together in a single-transformer system. If the system has two transformers (separate heating and cooling equipment with independent transformers), do not jumper Rh and Rc — back-feeding between transformers can burn them out.
- **Y (Yellow):** Cooling call — energizes the contactor on the condensing unit. Y1 for single-stage cooling, Y2 for second-stage. On a heat pump, Y also starts the compressor for heating (through the reversing valve).
- **G (Green):** Fan call — energizes the indoor blower relay. In most systems, G runs the blower independently of heating/cooling (fan-only mode). In some heat pump systems, G is energized automatically with every mode.
- **W (White):** Heating call — energizes the gas valve relay or electric heat sequencer. W1 for first-stage heat, W2 for second-stage or auxiliary/emergency heat on heat pumps. On a heat pump, W2 or AUX energizes backup electric heat strips.
- **C (Common, usually Blue):** The common (return) side of the 24V transformer. Provides the return path for 24V power. Smart thermostats (Ecobee, Nest, Honeywell Home T6/T9/T10 Pro) require a C wire for continuous power. If no C wire exists in the thermostat cable, options include: pulling a new thermostat cable (best solution), using an add-a-wire adapter kit (Venstar ACC0410 — converts the existing cable to provide C), or using the Nest power connector (for Nest only, converts the existing cable).
- **O (Orange):** Reversing valve — energizes in cooling mode. Standard for Carrier, Trane, Lennox, Rheem (newer), Goodman, Amana, Daikin, Mitsubishi, and most heat pump brands.
- **B (Dark Blue):** Reversing valve — energizes in heating mode. Used by Rheem (some older models) and Ruud. Rarely used now. Some thermostats combine O and B into a single O/B terminal with a software setting to select the mode.
- **Y2 (Light Blue or Pink):** Second-stage cooling call for two-stage systems.
- **W2/AUX (Brown or other):** Second-stage heating or auxiliary heat.
- **L (other color):** Emergency heat indicator (on some older systems).
- **S1/S2:** Outdoor temperature sensor wires (used by some smart thermostats for heat pump balance point control).

### Heat Pump vs Conventional Wiring
The key difference: a heat pump system uses the outdoor compressor for both heating and cooling via a reversing valve. A conventional system uses the outdoor unit for cooling only, with a completely separate furnace or boiler for heating.

Heat pump thermostat wiring typically uses: R, Y, G, O/B, W2 (aux heat), C. The thermostat handles the changeover between heating and cooling modes by controlling the reversing valve (O/B wire). In heating mode, Y energizes the compressor and O de-energizes (for O-type systems) so the reversing valve switches to heating. In cooling, Y energizes the compressor and O energizes to switch to cooling.

Conventional wiring uses: R, Y, G, W, C. W goes to the gas valve or electric heat relay. The thermostat simply calls for heat (W) or cooling (Y) with no reversing valve involvement.

### Common Miswires and How to Diagnose Them
- **O and B reversed (heat pump):** The system heats when it should cool and cools when it should heat. You'll feel warm air from the registers in cooling mode and cool air in heating mode. Fix: swap O and B at the thermostat, or change the O/B configuration setting in the thermostat software (most modern thermostats let you select "O energize in cooling" vs "B energize in heating").
- **Y and G swapped:** The fan runs when cooling is called (but no cooling), and the compressor runs when fan-only is called (compressor running without indoor airflow). This is dangerous — the evaporator will ice up, liquid refrigerant will slug back to the compressor, and you'll kill the compressor. Fix: swap Y and G at the thermostat.
- **Missing or broken C wire causing erratic thermostat behavior:** Smart thermostats without a C wire try to "steal" power through the Y or W circuit, which can cause the system to short-cycle (turning on for a second, then off). The thermostat may also reboot randomly, lose its schedule, or show a low battery warning. Fix: install a proper C wire or add-a-wire kit.
- **R and C shorted:** This blows the transformer fuse or burns out the transformer. If you replace a transformer and it immediately blows, check for a short between R and C in the thermostat cable — often caused by a nick in the wire insulation or a miswired thermostat.
- **Ground fault in thermostat cable:** An intermittent short between any thermostat wire and ground (the cable sheath or a metal junction box) can cause phantom calls — the system turns on or off randomly. Test each wire to ground with an ohmmeter. It should read infinite resistance (OL). Any measurable resistance indicates a fault — replace the cable.

---

## Refrigerant Handling

### EPA 608 Certification
Required by federal law to purchase or handle regulated refrigerants:
- **Type I:** Small appliances containing 5 lbs or less of refrigerant (window units, PTACs, household refrigerators, dehumidifiers). Self-contained, factory-charged systems.
- **Type II:** High-pressure appliances (residential A/C, heat pumps, supermarket refrigeration, commercial rooftops). Refrigerants include R-410A, R-22, R-134a, R-404A, R-407C.
- **Type III:** Low-pressure appliances (centrifugal chillers using R-11, R-123, R-245fa). These operate below atmospheric pressure.
- **Universal:** Covers all three types. This is the certification to get — it covers any system you'll encounter.

### Recovery Procedures
Before opening a refrigerant system for repair, you must recover the refrigerant. Intentional venting is illegal under the Clean Air Act (Section 608), with fines up to $44,539 per day per violation. Even "just a little" venting is illegal.

Recovery procedure:
1. Connect your recovery machine between the system and a recovery cylinder. Standard setup: manifold gauges on the system, yellow center hose from manifold to recovery machine inlet, recovery machine outlet to the recovery cylinder. Some techs connect directly without manifold gauges for faster recovery.
2. Place the recovery cylinder on a refrigerant scale. Record the starting weight. Do not exceed the cylinder's rated weight (tanks are rated to 80% capacity for liquid — the remaining 20% is vapor space for thermal expansion).
3. Open the appropriate system valves and manifold valves. Start the recovery machine.
4. Recover until the system reaches the required vacuum level: for R-410A and other high-pressure refrigerants in equipment with less than 200 lbs charge, recover to 0 psig (atmospheric pressure). For systems above 200 lbs, also recover to 0 psig. Some refrigerants have different recovery requirements — check the current EPA regulations.
5. After reaching the required level, close all valves, shut off the recovery machine, and wait 5 minutes. If the system pressure rises above the recovery requirement (outgassing from oil), restart recovery and pull it down again.
6. Record the amount of refrigerant recovered (ending weight minus starting weight). Document on your service ticket.
7. Label the recovery cylinder with the refrigerant type and condition (clean, contaminated, mixed). Never mix different refrigerants in a single cylinder — contaminated mixed refrigerant must be sent to a reclamation facility (most suppliers accept returns).

### Weigh-In Charging
The most accurate charging method, used for new installations and after complete system evacuation.

Procedure:
1. After proper evacuation (below 500 microns, held for 10+ minutes), leave the system under vacuum.
2. Place the virgin refrigerant tank on an accurate refrigerant scale (resolution of 0.1 oz or better — CPS, Inficon, Testo, and Fieldpiece all make good ones).
3. Connect the tank to the center (yellow) manifold hose. Purge the hose of air.
4. Record the starting tank weight.
5. For R-410A: always charge as a liquid (invert the tank or use the liquid dip tube). R-410A is a near-azeotropic blend of R-32 and R-125 — charging as a vapor will fractionate the blend, changing the composition and operating characteristics. R-22 can be charged as liquid or vapor, but liquid is faster.
6. Open the manifold liquid (high side) valve to allow liquid refrigerant to flow into the high side of the system. For initial fill with the system off, liquid can be pushed in by tank pressure alone. Once the pressures equalize, start the system and meter liquid into the suction side through the low-side gauge port, throttling the flow to prevent liquid slugging the compressor.
7. Charge to the nameplate weight. For a system with a factory-charged condenser and a standard 25-foot line set: the factory charge (stated on the nameplate) is the correct total charge. For longer line sets, add per the manufacturer's instructions — typically 0.6 oz per foot of 3/8" liquid line beyond the standard charge length. For shorter line sets, some manufacturers require removing refrigerant.
8. Verify the charge by checking superheat and subcooling against the manufacturer's target values at stable operating conditions (after running 15+ minutes, with stable outdoor and indoor temps).

---

## Start-Up Procedures

### New Installation Checklist
Before starting a newly installed system:
1. Verify all electrical connections are tight — use a calibrated torque screwdriver on all lug connections. Check wire sizing against the nameplate minimum circuit ampacity (MCA). Verify the breaker or fuse size matches the maximum overcurrent protection (MOCP) on the nameplate — never exceed MOCP.
2. Verify gas pipe is tested and gas pressure is correct at the manifold under load (if gas furnace or dual fuel).
3. Confirm line set connections are leak-free (nitrogen pressure test completed and held for at least 30 minutes).
4. Confirm evacuation was successful (held below 500 microns for 10+ minutes).
5. Confirm condensate drain is functional — pour water into the primary pan and verify it flows freely out the drain line. Check the secondary pan and float switch if applicable.
6. Install a clean filter of the correct size and MERV rating.
7. Verify all duct connections are sealed with mastic or approved tape. Check for obvious disconnects or damage.
8. Set the thermostat to the desired mode (heating or cooling).
9. Turn on the disconnect and the thermostat.
10. Watch the start-up sequence: thermostat calls for conditioning, indoor blower starts (after a brief delay on many systems — 30-90 seconds), outdoor unit starts. Listen for unusual noises — banging (liquid slugging), screeching (bearing failure or belt), hissing (refrigerant leak), or clicking (electrical issue).

### Temperature Split Verification
After the system runs for 15-20 minutes with stable conditions:
- Measure supply air temperature at the closest register to the air handler (use a digital probe thermometer — Testo, Fieldpiece, or even a good kitchen thermometer)
- Measure return air temperature at the return grille (before the filter)
- Calculate the temperature split (delta T): supply temp subtracted from return temp (for cooling, the supply should be colder than the return)
- Target delta T for cooling: 14-22 degrees F across the coil
- Below 14 degrees F delta T: suspect low refrigerant charge, restricted airflow, dirty coil, oversized ductwork, or a metering device problem
- Above 22 degrees F delta T: suspect low airflow (dirty filter, restrictive ductwork, blower speed too low), which reduces total capacity and can cause coil icing

For heating (gas furnace):
- Measure the temperature rise across the furnace (supply temp minus return temp)
- Compare to the rated temperature rise range on the furnace nameplate (typically 30-60 degrees F or 35-65 degrees F depending on the model)
- Too high: insufficient airflow (dirty filter, ductwork restriction, blower speed too low) — this overheats the heat exchanger and can crack it over time
- Too low: excessive airflow (blower speed too high for the BTU output, or ductwork is oversized for the furnace) — reduces comfort (lukewarm air from the registers)

---

## R-22 to R-410A Changeout Procedures

### Why You Cannot Simply Swap Refrigerants
R-22 and R-410A operate at fundamentally different pressures. R-410A operates at approximately 50-60% higher pressure than R-22 at the same temperature. R-22 system components (compressors, coils, valves, safety switches) are pressure-rated for R-22 operating levels — they are NOT rated for R-410A pressures. Putting R-410A into an R-22 system risks exceeding the pressure rating of the condenser coil, the compressor shell, the refrigerant piping, and the safety devices. This creates a genuine explosion risk.

Additionally, R-22 systems use mineral oil, while R-410A uses POE (polyolester) oil. These oils are not compatible — mineral oil doesn't dissolve in R-410A, and POE oil absorbs moisture aggressively from any system contamination.

### Full System Replacement Procedure
When replacing an R-22 system with R-410A:
1. **Recover all R-22** from the old system into an approved recovery cylinder. Document the amount recovered.
2. **Remove old equipment** — outdoor condenser, indoor evaporator coil, filter-drier, and (ideally) the line set.
3. **Line set decision:** Existing copper line sets can be reused in many cases IF the copper is in good condition (no kinks, no corrosion, no evidence of prior burnout) AND it's properly cleaned. Flush the line set with an approved solvent (Rx-11 Flush from Diversitech, or Nu-Calgon Rx Acid Scavenger). Push the solvent through with nitrogen, followed by a nitrogen purge to dry the lines. Install a new liquid line filter-drier to catch any residual contaminants. Carrier, Lennox, and Trane all publish technical bulletins allowing line set reuse with proper flushing. If the line set has ever experienced a compressor burnout (acid contamination), replace it — flushing may not remove all acid residue from the tubing walls.
4. **Line set sizing:** Verify the existing line set diameter is correct for the new R-410A equipment. In many cases, R-410A systems use the same line set sizes as the R-22 system they replace — but not always. A 3-ton R-22 system uses 3/8" x 3/4" line set, and most 3-ton R-410A systems also use 3/8" x 3/4". But check the installation manual for the specific new equipment.
5. **Install new equipment:** new condenser, new matched evaporator coil, new liquid line filter-drier (bi-flow drier for heat pumps), new disconnect if the amperage requirements changed.
6. **Electrical verification:** R-410A systems often draw different amperage than R-22 systems. Check the new unit's MCA and MOCP. You may need to upgrade the wire gauge, breaker size, or disconnect.
7. **Evacuation and charge:** evacuate to below 500 microns, hold for 10+ minutes, then charge with R-410A per the new system's nameplate.
8. **Full start-up and verification:** run the system, check superheat/subcooling, temperature split, amp draw, gas pressures (if dual fuel), and condensate drainage.

### Common Changeout Mistakes
- Reusing the old line set without flushing. Mineral oil residue from the R-22 system doesn't mix with POE oil — it causes oil logging in the evaporator coil (reducing heat transfer) and can starve the compressor of lubrication. A failed compressor at 6 months on a brand-new system is almost always caused by oil contamination from a dirty line set.
- Not installing a new filter-drier. The old drier is saturated with moisture and may contain desiccant incompatible with R-410A/POE oil. Always install a new drier — it's a $30 part that prevents $3,000 failures.
- Ignoring the ductwork. If the old R-22 system was a 3-ton and the new R-410A is a 3-ton, the ductwork should already be sized correctly. But if the old system was undersized (running on inadequate ductwork for years — very common), the new system will amplify the problem because modern equipment is less tolerant of airflow restriction. Measure static pressure and fix ductwork issues during the changeout — you'll never have easier access.
- Not matching the indoor and outdoor unit. Mismatched systems (AHRI "not rated" combinations) void warranties, reduce efficiency, and may not meet code requirements. Always verify the combination is AHRI-certified by looking it up on the AHRI directory (ahridirectory.org). The indoor coil, outdoor unit, and furnace/air handler must all be matched.
