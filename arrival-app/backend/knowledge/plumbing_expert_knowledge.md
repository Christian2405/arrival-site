# Plumbing Expert Diagnostic Knowledge

## Water Heater Diagnostics

### Gas Water Heater Troubleshooting

Gas water heaters come in two ignition types: standing pilot and electronic ignition. Understanding which type you are working on determines your entire diagnostic approach.

**Standing pilot systems** use a continuously burning pilot flame that heats a thermocouple or thermopile. The thermocouple generates a small millivolt signal (typically 20-30 millivolts under load) that holds the gas valve electromagnet open. If the pilot goes out, the thermocouple cools, the magnet releases, and the gas valve closes -- this is the safety mechanism.

To diagnose a standing pilot system that will not stay lit:
1. Light the pilot per the instructions on the unit. Hold the pilot button down for 60 seconds to allow the thermocouple to heat fully
2. Release the button. If the pilot goes out immediately: the thermocouple is likely bad or has a poor connection. Pull the thermocouple from the gas valve, clean the connection end with emery cloth, and reinstall. Tighten the nut 1/4 turn past finger tight -- do not overtighten or you will crush the ferrule
3. Test thermocouple output: disconnect from gas valve, hold pilot lit with the button, and measure millivolts between the thermocouple tip and the outer barrel of the connector. Open circuit should read 25-35 millivolts. Under load (connected to gas valve and holding it open), it should read 15-20+ millivolts. Below 10 millivolts under load means replace the thermocouple
4. If the thermocouple tests good but the pilot will not stay lit, the gas valve electromagnet may be weak. Replace the gas control valve

**Thermopile systems** (Honeywell, Robertshaw, White Rodgers) generate more voltage (500-750 millivolts open circuit, 300-400 millivolts under load) and can power an electronic gas valve and even an electronic temperature display. Test the same way as a thermocouple but with higher expected values. Below 300 millivolts under load usually means the thermopile is failing.

**Electronic ignition systems** (power vent and direct vent models) use a hot surface igniter or spark igniter controlled by a circuit board. These operate on 120VAC power. Troubleshooting follows a similar sequence to a furnace: power is verified, the igniter activates, the gas valve opens, and a flame sensor or flame rod proves the flame. Check for error codes via LED flashing on the control board.

**Common gas water heater problems:**
- Yellow or lazy flame: dirty burner, insufficient combustion air, or clogged air intake screen at the base of the unit
- Rumbling or popping sounds: sediment buildup on the bottom of the tank. The water trapped under sediment layers boils and pops. Flush the tank annually to prevent this
- Water not hot enough: check thermostat setting (most are set at 120 degrees F, some homeowners want 125-130). Check for a broken or misread dip tube -- if the cold water inlet dip tube is broken, cold water enters at the top and mixes with hot water near the outlet, resulting in lukewarm water
- Pilot outage due to downdraft: check the vent cap on the roof, check for negative pressure in the utility room (a powerful range hood or dryer running simultaneously can depressurize the room and pull combustion products down the vent, extinguishing the pilot)

### Electric Water Heater Troubleshooting

Electric water heaters use two heating elements and two thermostats. The upper thermostat is the master and includes the high-limit (ECO) reset button. The heating sequence is critical to understand: **the upper element heats first, then the lower element heats**. They never operate simultaneously. This is called a flip-flop or non-simultaneous circuit.

**Sequence of operation:**
1. Cold tank: the upper thermostat energizes the upper element first
2. Once the upper portion of the tank reaches setpoint, the upper thermostat switches power from the upper element to the lower thermostat
3. The lower thermostat energizes the lower element until the lower portion reaches setpoint
4. Both thermostats are now satisfied. If the lower portion cools first (which is normal since cold water enters at the bottom), the lower element reheats it

**Element testing:**
- Turn off the breaker. Verify power is off with a meter at the element terminals
- Disconnect one wire from the element
- Measure resistance across the element terminals. Expected readings vary by wattage: a 4500W/240V element should read about 12.8 ohms. A 3500W/240V element should read about 16.5 ohms. Use Ohm's law: R = V squared / W
- If resistance is infinite (open): the element is burned out. Replace it
- **Grounded element test:** Measure resistance from each element terminal to the tank (ground). You should read infinite ohms (open). Any continuity means the element is grounded -- it is shorting to the tank. This causes the breaker to trip or the high-limit to trip. A grounded element MUST be replaced

**Thermostat testing:**
- With power off, check continuity through the thermostat. Set the thermostat to maximum and touch the meter leads to the input and output terminals. You should have continuity when the water is below the setpoint
- The high-limit reset (red button on the upper thermostat) trips when water exceeds approximately 170 degrees F. If it keeps tripping: check for a grounded element (most common cause), check thermostats for calibration, or check for stacking (hot water rising to the top of the tank faster than the thermostat can react, common with recirculation systems)

**No hot water at all:** Check the breaker first. Then check the high-limit reset. Then test the upper element. If the upper element is burned out, you get no hot water because the sequence never switches to the lower element.

**Some hot water but runs out quickly:** The lower element is likely bad. The upper element heats the top of the tank (giving you some hot water), but the lower element never heats the bulk of the water in the bottom. Replace the lower element.

### Tankless Water Heater Maintenance

Tankless units require annual descaling in areas with hard water (above 7 grains per gallon). The procedure:

1. Turn off the gas or electricity and the cold water supply
2. Connect a submersible pump and two hoses to the isolation valves (service valves) on the cold and hot water lines at the unit. If isolation valves were not installed, you cannot descale without draining and cutting in valves -- this is why every tankless install must include isolation valves
3. Fill a 5-gallon bucket with 4 gallons of food-grade white vinegar
4. Open both isolation valves and circulate the vinegar through the unit for 45-60 minutes. The pump pushes vinegar in through the cold side, it flows through the heat exchanger, and returns via the hot side back to the bucket
5. Flush with clean water for 5 minutes to remove vinegar residue
6. Close isolation valves, restore water supply, and restart the unit
7. Clean the inlet water filter screen (small screen where the cold water enters the unit)

**Minimum activation flow rate:** Most tankless units require 0.5-0.75 GPM minimum flow to activate the burner. Low-flow fixtures (especially bathroom faucets with aerators) may not trigger the unit. This causes the "cold water sandwich" complaint -- brief bursts of cold water between uses.

**Error codes:** Every major brand (Rinnai, Navien, Noritz, Rheem) has its own error code system. The most common codes relate to: ignition failure (check gas supply, venting, condensate drain), flame rod/flame detection failure (clean the flame rod), and overheating (check for scale buildup, check water flow).

### Water Heater Sizing

**First hour rating (FHR)** is the key metric for tank water heaters. It measures how many gallons of hot water the unit can deliver in the first hour of use starting with a fully heated tank. A family of 4 typically needs 60-80 gallons FHR. Match FHR to peak demand, not tank size -- a well-insulated 40-gallon tank with a high BTU burner can have a higher FHR than a poorly designed 50-gallon tank.

**Recovery rate** is how many gallons per hour the unit can heat from cold to the setpoint. Gas water heaters recover 30-50 GPH. Electric water heaters recover only 18-25 GPH. This is why electric water heaters often need larger tanks for the same household demand.

### Anode Rod Inspection

The anode rod is a sacrificial metal rod (usually magnesium or aluminum) that corrodes instead of the tank lining. Check it every 2-3 years. Remove the rod using a 1-1/16" socket. If it is more than 50% depleted (bare wire showing, less than 1/2" of rod material remaining), replace it.

**Magnesium anode rods:** Provide better protection but can react with certain bacteria in the water to produce hydrogen sulfide gas (sulfur/rotten egg smell). If the customer complains of a sulfur smell from hot water only, replace the magnesium rod with an aluminum/zinc rod.

**Aluminum/zinc anode rods:** Less reactive and better for water with sulfur bacteria. They do not protect the tank quite as aggressively as magnesium.

**Powered anode rods** (Corro-Protec and similar): Electronic rods that do not deplete and produce no sulfur smell. Good for problem water. They require a small electrical connection (plugs into an outlet or is hardwired).

### T&P Relief Valve

The temperature and pressure (T&P) relief valve is the primary safety device on a water heater. It opens if water temperature exceeds 210 degrees F or pressure exceeds 150 PSI. Testing procedure: lift the lever briefly and allow a small amount of water to discharge. It should snap shut when released. If it drips continuously after testing, replace it.

**Discharge pipe requirements (code):**
- Must be the same diameter as the valve outlet (usually 3/4")
- Must go downhill all the way to the termination point (no traps, no uphill sections)
- Must terminate within 6 inches of the floor or to an approved drain
- Must not be reduced in size at any point
- Must not be threaded at the termination point (to prevent someone from capping it)
- Must be of approved material (copper or CPVC, not PEX -- PEX may deform at T&P valve discharge temperatures)

If the T&P valve is weeping or dripping during normal operation: check the water heater temperature setting (may be too high), check the house water pressure (thermal expansion in a closed system with no expansion tank can cause pressure to build above 150 PSI), and install a thermal expansion tank if one is not present.

### Water Heater Venting

**Natural draft (atmospheric vent):** Uses a draft hood at the top of the water heater and a metal (type B) vent pipe that runs upward to the roof. Relies on hot combustion gases rising naturally. The draft hood also admits dilution air. These must not be installed in tightly sealed rooms without adequate combustion air. Check for backdrafting by holding a lit match near the draft hood while the burner is firing -- the flame should be drawn toward the hood. If it blows outward, you have a backdraft condition (dangerous CO exposure).

**Power vent:** Uses a blower (usually at the top of the unit or in the vent run) to push exhaust gases through the vent pipe. Can vent horizontally through a sidewall, which is a major advantage when no chimney is available. The vent pipe is typically PVC or CPVC (because the fan cools the exhaust enough). If the blower fails, a pressure switch prevents the burner from firing.

**Direct vent (sealed combustion):** Uses a coaxial vent pipe (pipe within a pipe) through the sidewall. Outer pipe brings in combustion air, inner pipe exhausts products. Completely sealed from the indoor environment, making it the safest option for tight homes and bedrooms. No electricity required for venting on most models (operates on natural draft principles within the sealed vent system).


## Drain and Waste

### Drain Cleaning Methods

**Snake/cable machine:** The workhorse of drain cleaning. Use a 1/4" cable for lavatory sinks, 3/8" cable for kitchen sinks and tubs, 3/8"-1/2" cable for 2-3 inch branch drains, and 3/4"-1" cable for main sewer lines. Feed the cable slowly, let the machine do the work, and do not force it. When you hit the clog, you will feel resistance change. Let the cable cut through, then run water to test flow before retrieving.

**Hydro-jetting:** Uses high-pressure water (1500-4000 PSI) through a specialized nozzle to scour the inside of drain pipes. Best for grease buildup, scale, and root intrusion. Always camera-inspect before jetting -- jetting a pipe with a belly (low spot), offset joint, or structural damage can make things worse or cause a blowout. Jetting should only be done by experienced operators.

**Chemical drain cleaners:** Professional plumbers largely avoid chemical drain cleaners. Sodium hydroxide (lye) and sulfuric acid products can damage pipes (especially older chrome/brass traps and galvanized pipe), create dangerous gas combinations if mixed, and are a burn hazard. They also do not work well on physical blockages like roots or collapsed pipe. Enzymatic drain maintainers (Bio-Clean, etc.) are acceptable as a preventive measure for grease buildup but are not effective on active clogs.

### Common Clog Locations

- **P-trap:** The U-shaped trap under every fixture. Hair and soap scum accumulate in lavatory P-traps. Food and grease accumulate in kitchen P-traps. Remove and clean the trap first before snaking further
- **Kitchen sink drain:** Grease is the primary enemy. Grease coats the pipe walls and builds up over time. The clog is often 3-8 feet downstream of the trap where the pipe turns or connects to a larger drain. In homes with a garbage disposal, food particles combine with grease to form solid blockages
- **Main sewer line:** Root intrusion is the most common cause of main line clogs, especially in older homes with clay tile or Orangeburg pipe. Roots enter through joints. The clog is often at the first joint 5-10 feet from the house. Camera inspection after clearing will show the root entry points and pipe condition
- **Toilet flange:** Objects (toys, hygiene products, wipes) get stuck in the trapway or just past the flange. A closet auger (toilet snake) with a bulb head is designed specifically for this. Do not use a regular snake on a toilet -- it will scratch the porcelain

### Camera Inspection

Sewer cameras are essential for diagnosing recurring drain problems, pre-purchase inspections, and locating problems before excavation. Key things to look for in the footage:

- **Root intrusion:** White/brown fibrous masses penetrating through pipe joints
- **Bellies (sags):** Low spots where the pipe has settled. Water pools in the belly, allowing sediment to accumulate. Minor bellies may be acceptable if they drain. Severe bellies require pipe replacement
- **Offset joints:** Where one pipe section has shifted laterally from the next. Minor offsets restrict flow and catch debris. Severe offsets (more than 25% of pipe diameter) require repair
- **Channeling:** The bottom of the pipe has worn through, creating a groove. Common in older cast iron. Indicates the pipe is nearing the end of its life
- **Scale buildup:** White, rough buildup inside the pipe that reduces effective diameter. Common in cast iron and galvanized pipe
- **Pipe material transitions:** Where different materials connect. These are frequent failure points -- dissimilar materials corrode differently, connections loosen, and sealants break down

### Cast Iron Drain Pipe Issues

Cast iron drain pipe in residential homes typically lasts 50-80 years. In homes built before 1980, the cast iron is approaching or past its expected lifespan. Common issues:

- **Internal scale:** Decades of use create thick scale deposits that narrow the pipe. A 4" pipe may have an effective opening of only 2" once scale builds up. Hydro-jetting can clear scale but it will return
- **Channeling:** Continuous water flow at the 6 o'clock position wears through the pipe bottom first. Once the bottom is channeled through, waste water leaks into the soil below
- **Hub joint failures:** Older cast iron used lead and oakum to seal the hub joints. These joints deteriorate, allowing root intrusion and leaks
- **Horizontal to vertical transitions:** Where horizontal pipes connect to vertical stacks, the fittings and joints are stress points. Look for rust, staining, and dripping at these connections

Repair options: spot repair with rubber couplings (Fernco or Mission bands) for isolated problems, or full replacement with PVC when the system is extensively deteriorated. When replacing, always support PVC properly -- it does not have the structural rigidity of cast iron and will sag without adequate hangers.

### PVC vs ABS

**PVC (white):** Used in most jurisdictions for drain, waste, and vent (DWV) piping. Joined with primer (purple) and solvent cement. The primer softens the pipe surfaces, and the cement fuses them together. This is a chemical weld, not a glue joint. Allow proper cure time (minimum 15 minutes for small diameter, 2+ hours for 4" and larger, longer in cold weather).

**ABS (black):** Used primarily in western states and Canada. Joined with ABS cement only (no primer required in most jurisdictions, though some codes require it). Some jurisdictions allow ABS to PVC transitions using a green transition cement. Others require a mechanical coupling (Fernco or Mission band). Check your local code.


## Supply Side Plumbing

### Water Pressure

Normal residential water pressure is 40-80 PSI. Below 40 PSI causes poor fixture performance. Above 80 PSI causes premature wear on fixtures, water hammer, and increased risk of leaks. Test pressure with a hose bib gauge: screw it onto an outdoor hose bib, open the valve, and read static pressure (no water flowing). Test at different times of day -- municipal pressure can vary.

**Pressure reducing valve (PRV):** Located where the main water line enters the house. Reduces incoming pressure to a set point. To adjust: loosen the locknut and turn the adjusting screw clockwise to increase pressure, counterclockwise to decrease. Replace the PRV if it is not maintaining a consistent output pressure, if it is bypassing (output pressure equals input pressure), or if it is making noise. Typical PRV lifespan is 10-15 years. Always install a pressure gauge downstream to verify the setting.

**Thermal expansion:** In a closed plumbing system (backflow preventer or PRV without a bypass), heating water causes it to expand. This expansion has nowhere to go, causing pressure spikes that can reach 150+ PSI and pop the T&P relief valve on the water heater. The solution is a thermal expansion tank installed on the cold water line near the water heater. The expansion tank has an air bladder pre-charged to the house water pressure. Check the air charge annually with a tire gauge on the Schrader valve. If the tank feels completely full of water (heavy, no air space), the bladder has failed and the tank needs replacement.

### Pipe Materials

**Copper Type L vs Type M:** Type L has thicker walls and is required by code in many jurisdictions for underground and pressurized applications. Type M (thinner) is acceptable for above-ground interior supply lines in most areas. Type L is color-coded blue, Type M is red. Always check local code requirements.

**PEX (cross-linked polyethylene):**
- PEX-A (Engel method, Uponor): Most flexible, can be expanded and returns to shape, best freeze resistance. Uses expansion fittings and rings
- PEX-B (Silane method, Viega, SharkBite): Slightly stiffer, uses crimp rings or push-fit fittings. Most commonly available in home improvement stores
- PEX does not corrode, is not affected by acidic water, and handles freezing better than rigid pipe (it can expand somewhat before bursting). Do not expose PEX to UV light (sunlight degrades it within months). Do not use near hot water heater flue pipes or radiant heat sources

**CPVC (chlorinated polyvinyl chloride):** Cream or light yellow color. Used for hot and cold supply lines. Joined with CPVC primer and cement (similar to PVC DWV but specific CPVC products must be used). CPVC becomes brittle with age and exposure to certain chemicals (some insecticides, petroleum products). In homes over 15 years old, handle CPVC carefully -- it can shatter when stressed.

**Galvanized steel:** Found in homes built before 1960. Corrodes from the inside out, restricting flow. The inside of a 30+ year old galvanized pipe may have an effective opening of less than half its original diameter. When replacing, do not mix galvanized directly with copper (galvanic corrosion) -- use a dielectric union or brass adapter between the two materials.

### PEX Installation Methods

**Expansion (PEX-A):** Heat the ring and expand the pipe end with an expansion tool. Insert the fitting. As the pipe returns to its original size, it grips the fitting tightly. This creates the most reliable connection and has the largest flow area (the pipe opens up over the fitting rather than crimping down).

**Crimp (PEX-B):** Place a copper crimp ring over the pipe, insert the fitting, and compress the ring with a crimp tool. Use a go/no-go gauge to verify every crimp. Crimps that are too loose will leak. Crimps that are too tight will crack the fitting or cut the pipe.

**Push-fit (SharkBite and similar):** Push the pipe into the fitting until it locks. Requires a clean, square-cut pipe end and a depth gauge mark. These are great for repairs and tight spaces but are more expensive per connection and some jurisdictions or inspectors do not approve them for concealed locations (inside walls).

**Manifold systems:** A central manifold with individual runs to each fixture (home-run plumbing). Advantages: each fixture can be shut off individually, fewer fittings in the walls (fewer potential leak points), more consistent pressure. Disadvantages: more pipe used, larger manifold space needed.

### Copper Soldering (Sweating)

Proper technique for a water-tight, code-compliant solder joint:

1. **Cut:** Use a tube cutter for a clean, square cut. Ream the inside burr (this is critical -- the burr creates turbulence and restricts flow)
2. **Clean:** Use emery cloth or a fitting brush to clean the outside of the pipe and inside of the fitting until they are shiny copper color. Fingerprints, oxidation, and dirt prevent solder from bonding
3. **Flux:** Apply a thin, even coat of water-soluble flux (paste) to both the pipe exterior and fitting interior. Flux cleans the surfaces and helps solder flow
4. **Assemble:** Push the fitting onto the pipe fully. Give a slight twist to distribute flux evenly
5. **Heat the fitting, not the solder:** Apply heat to the fitting body (not the pipe, not the solder). The fitting needs to be hot enough to melt solder on contact. Touch solder to the joint opposite the flame -- when it melts and gets pulled into the joint by capillary action, the joint is properly heated. A 1/2" joint takes roughly 1/2" to 3/4" of solder. A 3/4" joint takes 3/4" to 1"
6. **Wipe:** Wipe the joint with a damp rag while still hot to remove excess flux and solder

**Common soldering mistakes:** Overheating (burns the flux, creating a black, dry joint that leaks), not cleaning properly (solder beads up instead of flowing into the joint), water in the line (even a small amount of residual water prevents the joint from reaching soldering temperature -- stuff white bread into the pipe upstream to absorb moisture temporarily), and using leaded solder on potable water (always use lead-free solder on drinking water systems -- it is code and law).

### Water Hammer

Water hammer is a pressure shock wave caused by the sudden stop of water flow. You hear it as a loud bang when a valve closes quickly.

**Causes:** Quick-closing solenoid valves (washing machines, dishwashers, ice makers), single-handle faucets that close quickly, and high water pressure.

**Fixes:**
- **Water hammer arrestors:** Small devices with a sealed air chamber and piston that absorb the shock. Install at the point of use (near the washing machine valve, near the dishwasher connection). Use the correct size for the fixture -- ASSE 1010 rated arrestors are sized AA through F based on fixture units
- **Securing loose pipes:** Pipes that bang may just need to be strapped or supported properly. Copper pipes expand and contract with temperature changes and need to be able to move slightly without banging against framing
- **Air chambers:** Older method using a capped, vertical pipe stub near the fixture. Air in the chamber compresses to absorb the shock. Over time, the air gets absorbed into the water and the chamber fills with water, becoming ineffective. Drain the system and refill to restore the air cushion
- **Reducing water pressure:** If pressure is above 80 PSI, install or adjust the PRV


## Gas Piping

### Gas Pipe Sizing

Proper gas pipe sizing ensures that each appliance receives adequate gas flow at the required pressure. Undersized gas pipe causes low manifold pressure, underfire, and poor appliance performance.

**Sizing procedure:**
1. List all gas appliances and their BTU input ratings (from the appliance rating plates)
2. Measure the distance from the gas meter to each appliance (this is the "length of run")
3. Use the pipe sizing tables in the fuel gas code (IFGC or NFPA 54). The table gives maximum BTU capacity for each pipe size at various lengths for a given pressure drop (typically 0.5" WC for NG)
4. Size the main pipe from the meter for the total BTU load of all appliances. Size each branch for its individual appliance load

**CSST (Corrugated Stainless Steel Tubing):** Flexible gas piping that is faster to install than black iron. Must be properly bonded per manufacturer requirements and code (bonding to the grounding electrode system, not just to the pipe itself). CSST is more susceptible to damage from lightning strikes if not properly bonded. Size CSST using the manufacturer's sizing tables -- CSST uses its own sizing system (EHD equivalent hydraulic diameter) that does not correspond directly to nominal pipe size.

### Gas Leak Testing

**Soap solution (bubble test):** Apply leak detection solution to every joint, valve, and connection. Pressurize the system to operating pressure and watch for bubbles forming. This is the most common field test method. Use a commercially made leak detection solution -- dishsoap solution works in a pinch but commercial solutions form more visible bubbles.

**Electronic leak detector:** Combustible gas detectors sense methane or propane in the air near a leak. Useful for finding the general area of a leak, but soap solution is still needed to pinpoint the exact joint.

**Pressure test with gauge:** Connect a pressure gauge to the system. Pressurize with the system gas or with air/nitrogen to 3 PSI (for new installation testing, some codes require higher). Close the supply valve and monitor the gauge. Any pressure drop over a 15-minute period (after temperature stabilization) indicates a leak. This is the most thorough method and is required by code for new installations and modifications.

### LP vs Natural Gas

**Key differences:**
- LP (propane) is heavier than air and pools in low spots. Natural gas is lighter than air and rises. This affects leak behavior and safety
- LP operates at higher regulator pressure: 11" WC at the appliance vs 7" WC for natural gas (these are the standard values -- some appliances differ)
- LP has higher BTU content per cubic foot (2,516 BTU vs 1,000 BTU for NG), so LP orifices are smaller to deliver the correct BTU input at higher pressure
- Conversion between fuels requires changing orifices, adjusting gas pressure, and on some appliances, replacing the gas valve or regulator. Many furnaces and water heaters have conversion kits available from the manufacturer
- LP tanks require proper setback distances from the building, ignition sources, and property lines. A 500-gallon tank typically needs 10 feet from the building and 10 feet from any ignition source
