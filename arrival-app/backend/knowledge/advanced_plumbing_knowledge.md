# Advanced Plumbing Knowledge

## Drain, Waste, and Vent (DWV) Systems

### Pipe Sizing by Fixture Unit Count

Every plumbing fixture is assigned a drainage fixture unit (DFU) value that represents its load on the drainage system. Fixture units are not gallons per minute -- they are a weighted value that accounts for flow rate, duration, and frequency of use. The UPC and IPC tables are slightly different, so always check which code your jurisdiction follows.

Common DFU values (UPC Table 702.1):
- Lavatory (bathroom sink): 1 DFU, requires 1-1/4" minimum trap and drain
- Bathtub or shower: 2 DFU, requires 1-1/2" minimum trap and drain
- Kitchen sink (residential): 2 DFU, requires 1-1/2" minimum trap and drain
- Dishwasher (domestic): 2 DFU, connects to kitchen sink tailpiece or disposal
- Clothes washer (residential): 3 DFU, requires 2" minimum standpipe and trap
- Toilet (water closet): 3 or 4 DFU depending on flush volume, requires 3" minimum drain (4" for building drain)
- Floor drain: 2 DFU, minimum 2" trap and drain
- Laundry tray: 2 DFU, requires 1-1/2" minimum trap and drain

Pipe sizing based on cumulative DFU load (horizontal drains at 1/4" per foot slope):
- 1-1/4" pipe: 1 DFU maximum
- 1-1/2" pipe: 3 DFU maximum
- 2" pipe: 6 DFU maximum
- 3" pipe: 20 DFU maximum (this is why a 3" pipe handles a full bathroom group)
- 4" pipe: 160 DFU maximum (building drain and building sewer)

The building drain is the lowest horizontal piping inside the building that collects all waste and carries it to the building sewer (which is outside the building wall). The building drain must be a minimum of 4" for any system with a toilet. Some older codes allowed 3" building drains but current UPC requires 4" if any water closets are connected.

Vertical stacks carry higher DFU loads than horizontal branches because gravity assists flow in the vertical run. A 3" stack can handle 48 DFU (UPC) or more. A 4" stack can handle 256 DFU. The limitation is always at the horizontal branches and the base of the stack where vertical flow transitions to horizontal.

### Grade and Slope Requirements

Drain pipe slope is critical. Too little slope and solids settle and clog. Too much slope and the water outruns the solids, leaving them behind (yes, this actually happens).

Minimum slope requirements (UPC/IPC):
- Pipe 2-1/2" and smaller: 1/4" per foot minimum
- Pipe 3" and larger: 1/8" per foot minimum (some jurisdictions require 1/4" per foot for 3" pipe -- check local amendments)

Maximum slope: 1/2" per foot. Beyond this, the pipe approaches a 45-degree angle and water velocity is too high. At steep slopes, use 45-degree fittings rather than increasing the slope of horizontal runs.

Field tip for checking slope: a 4-foot level with a 1" shim under one end gives you exactly 1/4" per foot (1/4" times 4 = 1"). For 1/8" per foot, use a 1/2" shim under a 4-foot level. Every plumber should carry a torpedo level at minimum, but a 2-foot or 4-foot level gives more accurate readings for longer runs.

When you find a drain with inadequate slope during a renovation, you have three options: lower the downstream end, raise the upstream end, or reroute the pipe. Lowering the downstream end sometimes means cutting into a concrete slab or digging deeper at the building sewer connection. None of these are fun, but a flat drain will clog repeatedly and no amount of snaking fixes a grade problem.

### Vent Sizing and Placement Rules

Vents serve two critical functions: they allow air into the system to prevent siphoning of traps, and they allow sewer gases to escape above the roofline instead of entering the building.

Vent sizing basics (UPC Table 703.2):
- Individual vent serving a 1-1/2" trap: 1-1/4" minimum vent
- Individual vent serving a 2" trap: 1-1/2" minimum vent
- Individual vent serving a 3" trap: 2" minimum vent
- Branch vents and vent stacks: sized by DFU load and developed length using code tables
- The main vent stack through the roof must be the same diameter as the building drain, but never less than 3"

Maximum trap-to-vent distances (UPC Table 1002.2) -- this is how far the trap weir can be from the vent connection:
- 1-1/4" trap arm: 30 inches (2.5 feet)
- 1-1/2" trap arm: 42 inches (3.5 feet)
- 2" trap arm: 5 feet
- 3" trap arm: 6 feet
- 4" trap arm: 10 feet

If the trap is farther from the vent than these maximums, the water in the trap can be siphoned out by the flow of water in the drain pipe. An empty trap lets sewer gas into the building. This is one of the most common code violations in DIY plumbing.

The vent must connect to the drain at or above the flood level rim of the fixture it serves. The flood level rim is the top edge of the fixture (the rim of the sink, the top of the toilet bowl). This prevents waste water from entering the vent pipe during a backup.

### Wet Venting vs Dry Venting

A dry vent carries only air. It connects to the drain system and rises vertically to the roof or connects to another vent that goes through the roof. Dry vents are straightforward -- they are just air pipes.

A wet vent carries both waste from an upstream fixture and serves as the vent for a downstream fixture. The UPC allows wet venting in specific configurations. The classic example: in a bathroom group, the lavatory drain can serve as the wet vent for the toilet and bathtub, provided the lavatory drain is sized one pipe size larger than normally required (2" instead of 1-1/2") and the distances are within code limits.

Wet venting rules (UPC):
- A wet vent must be at least 2" for a single bathroom group
- The wet-vented section must be between the vent connection and the most downstream fixture it serves
- The fixture that generates waste through the wet vent must connect upstream of the fixtures being vented
- Not every jurisdiction allows wet venting -- some local codes prohibit it entirely

Circuit venting is used in commercial applications where multiple fixtures (like a battery of sinks in a restroom) are on a common horizontal branch. One vent serves the entire circuit, but the branch must meet specific sizing and distance requirements.

### Air Admittance Valves (AAVs)

An AAV (often called a Studor vent or cheater vent) is a one-way mechanical valve that opens to admit air when negative pressure develops in the drain (preventing trap siphonage) and closes under positive pressure or no pressure to prevent sewer gas from escaping.

Where AAVs are allowed:
- The IPC generally allows AAVs as an alternative to conventional venting for individual fixtures and branch vents
- The UPC has historically been more restrictive but newer editions are allowing AAVs in more situations
- Many local jurisdictions have their own amendments -- some ban AAVs entirely, some allow them only for island sinks or retrofits, and some allow them broadly
- AAVs are never allowed as a substitute for the main vent stack through the roof. Every building must have at least one open vent to atmosphere

AAV limitations:
- Must be accessible for service or replacement (not buried in a wall with no access)
- Must be installed at least 4 inches above the horizontal branch drain
- Must be installed within the maximum trap-to-vent distance for the fixture
- Cannot be installed in areas that may flood or where they would be submerged
- Have a limited lifespan (10-20 years typical) and must be replaceable

When an AAV fails (stuck closed), the trap siphons and you get sewer gas. When an AAV fails (stuck open), sewer gas leaks at the valve. If you smell sewer gas and trace it to an AAV, replace the valve.

Field tip: AAVs are the right solution for island sinks where running a vent up through the ceiling and back to the main vent stack is impractical. They are not a shortcut for poor planning. If you can run a proper vent, run a proper vent.

### Common DWV Problems

**Slow drains throughout the house:** If every fixture is slow, the problem is downstream -- building drain or building sewer. Camera inspection of the main line is the first step. Common causes: root intrusion, bellied pipe, collapsed section, or heavy scale buildup in cast iron.

**Single slow drain:** The problem is in the fixture drain, trap, or branch line. Start at the trap. Remove and clean it if accessible. If the trap is clear, snake the branch line. Kitchen drains are almost always grease accumulation. Bathroom drains are almost always hair and soap buildup.

**Gurgling at fixtures:** Air is being pulled through the trap water. This means a vent is blocked, missing, or undersized. When a large slug of water goes down a drain (flushing a toilet, draining a tub), it creates negative pressure behind it. If there is no vent to supply air, the system pulls air through the nearest trap -- you hear it as a gurgling sound. Find the vent and check for blockage (bird nests, wasp nests, ice in winter, debris). Check the vent terminal on the roof.

**Sewer gas smell:** Possible causes ranked by likelihood:
1. Dry trap -- a fixture that has not been used in weeks or months loses its trap seal to evaporation. Pour water into floor drains, unused shower drains, and basement fixtures regularly
2. Failed wax ring on a toilet -- the wax seal between the toilet and the flange has deteriorated. Remove the toilet and replace the wax ring
3. Cracked or disconnected vent pipe -- especially in attics where movement and temperature cycling can crack old vent connections
4. Missing cleanout cap -- check all cleanouts, especially in basements and crawl spaces
5. Failed AAV -- replace if present
6. Cracked drain pipe -- camera inspection needed

**Double trapping:** Two P-traps in series on the same fixture drain. This creates an air lock between the traps and causes chronic slow drainage. Common in DIY installations where someone adds a new trap without removing the old one. The fix is to remove one trap. Every fixture gets exactly one trap, no more.

### Drain Cleaning Methods

**Hand snake (closet auger, drum auger):** For small drains (1-1/4" to 2") and toilets. The closet auger has a vinyl boot to protect porcelain and a 3-foot or 6-foot reach -- it is specifically designed for toilets. A 25-foot drum auger with 1/4" or 5/16" cable handles most sink and tub clogs. Feed slowly, let the cable rotate, and pull back periodically to remove debris from the cable head.

**Sectional machine (large snake):** For main lines and larger drains (3" to 6"). Uses 3/4" to 1-1/4" cable in sections that lock together. Different cutter heads for different problems: a retriever head for pulling out rags and debris, a spade head for heavy buildup, a root cutter for roots. Always wear leather gloves -- a spinning cable that catches on something can wrap around your hand in an instant.

**Hydro-jetting:** High-pressure water (typically 2000-4000 PSI at 3-8 GPM for residential, higher for commercial). The nozzle has forward-facing jets (to cut through blockages) and rear-facing jets (to propel the hose forward and scour the pipe walls). Best for grease, scale, and root maintenance. Always camera-inspect before jetting -- jetting a pipe with structural damage (cracks, offset joints, bellied sections) can cause a blowout. Jetting is not a DIY operation. The pressure can cut through skin and the hose can whip violently.

**When to use each method:**
- Hair clog in a bathroom sink: hand snake, 25-foot drum auger
- Grease clog in a kitchen drain: sectional machine, then follow up with hot water and enzymatic drain maintainer
- Toilet clog: closet auger first. If that does not clear it, pull the toilet and snake through the flange
- Main line root intrusion: sectional machine with root cutter head, then camera inspect, then consider hydro-jetting for thorough cleaning
- Recurring main line clogs: hydro-jetting followed by camera inspection to determine if pipe replacement is needed

### Camera Inspection Details

Modern push cameras have a self-leveling color camera head, LED lights, a sonde (locating transmitter) built into the head, and a monitor/recorder. The sonde lets you locate the camera head from above ground using a locator, so you can pinpoint problem areas for excavation.

Common camera findings and what they mean:

**Root intrusion:** Roots enter through joints, cracks, and failed connections. They grow toward moisture. Even a tiny gap lets roots in, and once inside, they expand and catch debris. Roots can be cut with a cable machine or hydro-jetter, but they grow back. Long-term solutions: root killer (copper sulfate or foaming root control applied annually), pipe lining (CIPP -- cured-in-place pipe), or excavation and replacement.

**Bellies (sags):** Low spots where the pipe has settled. You see the camera submerge in standing water. Minor bellies (less than 1" sag in a short section) may function adequately and can be monitored. Significant bellies trap sediment and paper, causing recurring clogs. The only permanent fix is excavation and re-grading the pipe.

**Offsets:** Where one pipe section has shifted relative to the next at a joint. Minor offsets (less than 25% of pipe diameter) restrict flow but may be serviceable. Severe offsets act like a dam and catch everything that passes. Repair requires excavation and replacement of the affected section.

**Scale and tuberculation:** Internal buildup that reduces effective pipe diameter. Common in cast iron (rust scale) and galvanized pipe. A 4" cast iron pipe with 60 years of scale may have an effective opening of 2" or less. Hydro-jetting can restore flow temporarily but scale returns. Pipe lining or replacement is the long-term answer.

**Orangeburg pipe:** Bituminous fiber pipe used from the 1940s to 1970s. It looks like tar paper rolled into a tube. It crushes, deforms, and collapses. If the camera finds Orangeburg, the recommendation is full replacement -- there is no effective repair for this material.

**Clay tile:** Vitrified clay pipe used through the 1960s. Individual sections are typically 2-3 feet long connected with mortar or rubber gasket joints. The pipe material itself is nearly indestructible, but every joint is a potential entry point for roots. Joints can also shift due to ground movement. If the pipe body is intact and only a few joints are compromised, point repairs or pipe lining may be cost-effective. If the entire run has problems, replacement with PVC is the answer.


## Water Supply Systems

### Pipe Sizing Based on Fixture Units and Demand

Water supply pipe sizing uses water supply fixture units (WSFU), which account for both flow rate and probability of simultaneous use. The tables in the UPC (Table 610.3) and IPC (Table E103.3) convert WSFU to GPM demand, then size pipe based on available pressure, pipe length, and friction loss.

Common WSFU values:
- Lavatory faucet: 1 WSFU (0.5 hot, 0.5 cold)
- Kitchen faucet: 1.4 WSFU
- Bathtub faucet: 1.4 WSFU
- Shower: 1.4 WSFU
- Toilet (tank type): 2.2 WSFU (cold only)
- Dishwasher: 1.4 WSFU (hot only)
- Clothes washer: 1.4 WSFU
- Hose bib: 2.5 WSFU (cold only)

Quick sizing guidelines for residential (based on typical 40-60 PSI supply, copper or PEX):
- 3/4" main supply from meter: serves most single-family homes up to about 30 WSFU
- 1" main supply: for larger homes, long runs from the meter, or lower supply pressure
- 1/2" branches to individual fixtures: standard for lavatory, kitchen sink, toilet
- 3/4" branches: clothes washer, bathtub, and where multiple 1/2" branches tee off

The water meter itself creates a significant pressure drop. A standard 5/8" x 3/4" residential meter drops 5-10 PSI at normal flow rates. A 3/4" meter drops less. Factor this into your available pressure calculations.

### Water Pressure Details

**Normal operating range:** 40-80 PSI static (no fixtures open). Below 40 PSI, shower performance suffers and some appliances (tankless water heaters, irrigation systems) may not operate properly. Above 80 PSI, code requires a pressure reducing valve and fixture life decreases significantly. Washing machine hoses, toilet fill valves, and ice maker lines are the most common failure points when pressure is too high.

**Testing procedure:**
1. Screw a pressure gauge (0-200 PSI, hose-thread) onto a hose bib or laundry faucet
2. Close all fixtures in the house. Make sure the ice maker, irrigation, and water softener are not cycling
3. Read static pressure. This is your starting number
4. Open a fixture (flush a toilet or run a hose bib wide open) and read dynamic pressure. A drop of more than 10-15 PSI suggests undersized piping, a partially closed valve, or restriction in the system

**PRV installation and adjustment:**
- Located after the meter and before the first branch, typically near the main shut-off
- Standard residential PRVs (Watts LF25AUB, Zurn Wilkins 70XL) are preset to 50 PSI from the factory
- To adjust: loosen the locknut on top, turn the adjustment screw clockwise to increase pressure, counterclockwise to decrease. Check with a gauge downstream while adjusting
- Install a gauge port downstream of the PRV for ongoing monitoring
- PRVs fail in two ways: they stop reducing (output equals input, fixtures get full street pressure) or they close off (little or no flow). Average life is 10-15 years. Replace proactively if the home has a PRV over 12 years old and the homeowner is concerned about potential water damage
- A PRV creates a closed system. Thermal expansion from the water heater has nowhere to go. Install an expansion tank on the cold side of the water heater whenever a PRV is present

### Pipe Materials in Depth

**Copper -- Type K, L, M:**
- Type K (green stripe): Thickest walls. Required for underground water service and in some jurisdictions for any below-slab application. Also used for medical gas and refrigerant lines. Available in soft coil (for underground) and hard drawn (rigid)
- Type L (blue stripe): Medium wall. The most commonly specified for residential and commercial water supply. Required by many codes for all interior supply piping. Available in both soft and hard drawn
- Type M (red stripe): Thinnest wall. Allowed by some codes for above-ground interior supply lines only. Less expensive than Type L. Some jurisdictions and some inspectors do not allow Type M at all -- check before using it
- Copper is naturally antimicrobial, handles high temperatures, and has a proven track record spanning decades. Downsides: expensive, requires skilled soldering, can corrode in acidic water (pH below 6.5), and is a target for theft on job sites

**PEX Types:**
- PEX-A (Engel/peroxide method): Most flexible and has the best thermal memory. You can expand it with a tool, and it shrinks back to grip the fitting. Most resistant to freeze damage -- the pipe expands before bursting. Brands: Uponor (formerly Wirsbo). Higher cost but the expansion connection method creates the most reliable joint and the largest flow area
- PEX-B (silane method): Slightly stiffer than A, less expensive. Uses crimp or clamp connections. Brands: Viega, Zurn. The most widely available in retail stores. Perfectly good material -- the stiffness difference from PEX-A is noticeable but not a dealbreaker
- PEX-C (electron beam method): Least common. Made by irradiating the tubing. Similar properties to PEX-B. Less available and not widely specified

All PEX types share these characteristics: no corrosion, quiet (no water hammer transmission through the pipe like copper), excellent freeze resistance, fast installation. All PEX types degrade in UV light -- do not leave exposed to sunlight. Do not install within 18 inches of a water heater flue or any heat source above 200F. Insulate PEX in unconditioned spaces to prevent condensation and protect from physical damage.

**CPVC:**
- Joined with CPVC solvent cement and primer. The joint is a chemical weld
- Rated for 180F at 100 PSI (adequate for domestic hot water)
- Becomes brittle with age. In homes over 15 years old, handle existing CPVC with extreme care. Grabbing a CPVC pipe hard can snap it. Vibration from nearby work can crack fittings
- Certain chemicals destroy CPVC: petroleum-based products, some insecticides (commonly sprayed near water heaters in basements), and some pipe thread sealants. Use only CPVC-compatible compounds
- CPVC is being phased out in many markets in favor of PEX. Some jurisdictions have restricted or banned it

**Galvanized steel:**
- Common in homes built before 1960
- Corrodes internally, building up iron deposits (tuberculation) that progressively reduce flow
- When a customer complains of low water pressure throughout a house built in the 1950s and the street pressure tests fine, galvanized pipe is almost always the cause
- Do not attempt partial replacement. Removing one section of galvanized often reveals the next section is just as bad. Plan for a full repipe
- Never connect copper directly to galvanized -- galvanic corrosion accelerates rapidly at the connection. Use a dielectric union (steel to copper) or a brass transition fitting

### PEX Installation Methods Compared

**Expansion (PEX-A only):**
Best connection method available. The expansion tool enlarges the pipe and ring, the fitting slides in easily, and as the PEX memory shrinks the pipe back to original size it locks onto the fitting with tremendous force. The flow area is the largest of any PEX method because the pipe expands over the fitting rather than being compressed onto it. Works even in cold weather (warm the pipe end with a heat gun if it is below 40F). Downsides: requires proprietary tool (Milwaukee, DeWalt, or Uponor brand), PEX-A tubing costs more, and the expansion rings are more expensive than crimp rings.

**Crimp (PEX-B primarily):**
Copper crimp rings are placed over the pipe, the fitting is inserted, and a crimp tool compresses the ring onto the pipe. Must verify every crimp with a go/no-go gauge -- no exceptions. A crimp that is 0.002" too loose will leak in a week. A crimp that is too tight will crack the fitting body over time. The crimp tool must be calibrated regularly. Advantages: tools are inexpensive, rings are cheap, and the method is well-proven. Disadvantage: the brass insert fitting reduces the internal diameter significantly (a 3/4" crimp fitting has roughly the flow area of a 1/2" pipe).

**Stainless steel cinch clamps (PEX-B):**
An alternative to copper crimp rings. A stainless steel band with a ratcheting tab is placed over the pipe and squeezed with a cinch clamp tool. The advantage over crimp rings is that one tool size works for all pipe sizes (crimp tools need specific jaws for each size). The ratchet mechanism makes consistent clamping easier. Many pros prefer cinch clamps over crimps for this reason.

**Push-fit (SharkBite, Tectite, etc.):**
Push the pipe in until it clicks. Fastest connection method. No special tools. Excellent for repair work, tight spaces, and transitions between materials (SharkBite fittings accept copper, PEX, and CPVC). Disadvantages: most expensive per fitting, some jurisdictions do not allow them in concealed spaces, and the O-ring seal has a finite lifespan (SharkBite rates them for 25 years, but real-world experience is still accumulating). For exposed utility areas and repairs, push-fit is perfectly acceptable. For new construction behind walls, expansion or crimp is the better long-term choice.

### Manifold vs Trunk-and-Branch

**Trunk-and-branch (traditional):** A main line runs through the house with tees branching off to each fixture. This uses less pipe and fewer fittings at the manifold, but every tee is a potential leak point inside a wall. Pressure drops at each tee, and fixtures at the end of long runs may have noticeably lower pressure and longer wait times for hot water.

**Manifold (home-run):** A central manifold with individual dedicated lines to each fixture. Every fixture has its own shut-off at the manifold. Advantages: balanced pressure at all fixtures, individual shut-offs for any fixture (no hunting for shut-off valves in the wall), fewer concealed fittings (each run is continuous from manifold to fixture). Disadvantages: uses significantly more tubing (each run goes all the way back to the manifold), manifold is an additional cost, and the manifold location must be accessible.

Best practice: Use a hybrid approach. Run 3/4" mains to area manifolds (one for each bathroom zone, one for the kitchen/laundry zone), then home-run 1/2" lines from each area manifold to fixtures. This balances material cost with the benefits of manifold distribution.

### Thermal Expansion in Detail

When water is heated from 50F to 120F in a 50-gallon water heater, it expands by roughly half a gallon. In an open system (no PRV, no backflow preventer), this expanded volume pushes back toward the municipal supply. In a closed system, it has nowhere to go, and pressure rises.

Without an expansion tank in a closed system, pressure can spike to 150 PSI or higher every time the water heater fires. This causes:
- T&P valve dripping (the valve is doing its job by relieving excess pressure)
- Premature failure of flex hoses, fill valves, and mixing valves
- Water hammer when fixtures are opened as the stored pressure releases
- Shortened water heater life

Expansion tank sizing: for a 40-50 gallon residential water heater at 40-80 PSI supply pressure, a 2-gallon expansion tank is standard. For larger water heaters or higher supply pressure, size up to a 5-gallon tank.

Installation: on the cold water supply line to the water heater, between the water heater and the nearest shut-off valve. Can be oriented in any direction but vertical with the air charge on top is preferred. Pre-charge the tank bladder to match the house static water pressure before installing. Check the charge annually with a tire gauge on the Schrader valve. A waterlogged tank (failed bladder) feels heavy and does nothing -- replace it.


## Gas Piping

### Pipe Sizing by BTU Load and Run Length

Gas pipe must deliver adequate volume at adequate pressure to every appliance. Undersized gas pipe results in low manifold pressure, lazy yellow flames, sooting, and potential CO production.

Sizing uses the longest run method: determine the longest pipe run from the meter to the farthest appliance, then size the entire system based on that length. This ensures adequate pressure even at the most remote appliance.

Quick reference for natural gas at 0.5" WC pressure drop (IFGC Table 402.4, Schedule 40 black iron):
- 1/2" pipe, 10-foot run: 175,000 BTU max
- 1/2" pipe, 30-foot run: 99,000 BTU max
- 3/4" pipe, 10-foot run: 360,000 BTU max
- 3/4" pipe, 30-foot run: 203,000 BTU max
- 1" pipe, 10-foot run: 680,000 BTU max
- 1" pipe, 30-foot run: 383,000 BTU max
- 1-1/4" pipe, 30-foot run: 730,000 BTU max

Typical residential appliance BTU loads:
- Furnace: 60,000-120,000 BTU
- Water heater (tank): 30,000-50,000 BTU
- Tankless water heater: 150,000-199,000 BTU (this is why tankless units often require a dedicated 3/4" or 1" gas line)
- Range/oven: 40,000-65,000 BTU
- Dryer: 20,000-25,000 BTU
- Gas fireplace: 20,000-60,000 BTU
- Gas grill (outdoor): 30,000-60,000 BTU

Common sizing mistake: adding a tankless water heater to an existing system without upsizing the gas line from the meter. A tankless unit at 199,000 BTU combined with a furnace at 100,000 BTU is 299,000 BTU total. If the existing 3/4" line from the meter is a 30-foot run, it can only handle 203,000 BTU. The system is undersized. The tankless will fire but cannot reach full output, and when both the furnace and tankless fire simultaneously, both appliances will underperform.

### Gas Pipe Materials

**Black iron (steel):** The standard for interior gas piping. Schedule 40 is standard weight. Threaded joints with pipe dope or Teflon tape rated for gas (yellow tape, not white). Always use pipe joint compound or tape rated specifically for gas -- some thread sealants are for water only and will not seal gas properly or may deteriorate in gas service.

**CSST (Corrugated Stainless Steel Tubing):** Brands include TracPipe, Gastite, and Wardflex. Fast to install -- it snakes through walls like electrical cable. Cut to length, use manufacturer's fittings (proprietary to each brand), and connect to black iron with transition fittings.

CSST bonding requirements (critical): CSST must be bonded to the building grounding electrode system using a minimum 6 AWG copper conductor. This is a direct connection from the CSST to the ground bus in the electrical panel or to the grounding electrode conductor. Standard bonding through the appliance connection and building wiring is not sufficient for CSST. Lightning can induce current in CSST, and without proper bonding, arc damage can burn holes in the tubing, causing gas leaks. This requirement changed around 2007-2012 depending on jurisdiction. Every CSST installation should be verified for proper bonding.

**Copper (type L or K):** Allowed for gas piping in some jurisdictions (not all). Must use flared fittings only (no solder joints for gas). Some codes allow ACR (air conditioning/refrigeration) copper for gas, others require plumbing-grade type L. Check your local code before running copper for gas. Copper is not allowed for LP gas in many areas because propane can react with copper in certain conditions.

### Gas Pressure Testing

**New installation test (code requirement):**
- Pressure test the entire system before connecting appliances
- Test medium: air or nitrogen only (never use gas for a pressure test on a new system)
- Test pressure: 3 PSI minimum (some jurisdictions require higher -- up to 10 or 15 PSI)
- Duration: 15 minutes minimum with no pressure drop on the gauge (after allowing for temperature stabilization -- a warm pipe pressurized with cool air will show a pressure rise as the air warms)
- Use a manometer or low-pressure test gauge for accuracy. Standard mechanical gauges are not precise enough at 3 PSI

**Existing system leak check:**
- Soap solution test at all joints, connections, valves, and union fittings
- Electronic combustible gas detector to sweep the area near piping
- Check with gas at operating pressure (7" WC for NG, 11" WC for LP)

### Natural Gas vs Propane (LP)

**Operating pressures:**
- Natural gas: 7" WC (water column) at the appliance, which equals approximately 0.25 PSI. The house regulator (on the meter) reduces street pressure (which can be 2 PSI or higher) down to 7" WC
- Propane: 11" WC at the appliance, which equals approximately 0.4 PSI. A two-stage system uses a first-stage regulator at the tank (reduces from tank pressure down to 10 PSI) and a second-stage regulator near the building (reduces from 10 PSI to 11" WC)

**Orifice differences:** Because LP operates at higher pressure and has higher BTU content per cubic foot, LP orifices are smaller than NG orifices for the same BTU appliance. Installing an NG appliance on LP without converting the orifices results in a massively oversized flame, sooting, and CO production. Installing an LP appliance on NG without conversion results in a tiny, lazy flame that may not stay lit.

**Safety difference:** NG is lighter than air (specific gravity 0.60) and rises. LP is heavier than air (specific gravity 1.52) and sinks. This is critical: a propane leak in a basement pools on the floor and can reach explosive concentration. LP gas appliances in basements or below-grade spaces require special consideration. Some codes prohibit certain LP installations in basements.

### Drip Legs (Sediment Traps)

A drip leg is a capped tee installed in the gas line just before the appliance connection. The branch of the tee continues up to the appliance, and the bull of the tee continues down 3-6 inches with a cap. Sediment and moisture in the gas line settle into the drip leg instead of entering the appliance gas valve.

Code requires a drip leg (sediment trap) at every appliance connection. The minimum length is 3 inches below the tee (some codes specify 6 inches). Use a nipple and cap -- do not use a plug directly in the tee. The cap should be accessible for cleaning.

Common violation: no drip leg installed at the appliance. You see this on water heaters and furnaces constantly. It is a code violation and a failure point -- sediment in the gas valve causes erratic operation, pilot outages, and valve failure.

### Gas Leak Detection Methods

**Soap solution (bubble test):** The field standard. Apply commercially made leak detection solution (not dish soap -- it does not bubble as visibly) to every fitting, valve, union, and connection. Watch for growing bubbles. A large leak produces rapid, obvious bubbles. A small leak may produce a single slow-growing bubble that takes 30 seconds to form. Be patient and check every joint.

**Electronic combustible gas detector:** Sniffs for methane or propane in the air. Useful for sweeping a room or running along a pipe to find the general area of a leak. Then use soap solution to pinpoint the exact joint. Calibrate or replace per manufacturer instructions. False positives are possible near cleaning products, paint, and solvents.

**Isolation gauge test:** Shut off the gas supply at the meter. Connect a manometer or low-pressure gauge to a convenient fitting. Open a burner cock to pressurize the gauge from the trapped gas in the piping. Close the burner cock and observe the gauge for 15 minutes. Any drop indicates a leak. This is the most definitive field test.

### Common Gas Piping Violations

1. No drip leg at appliance connection (most common violation)
2. CSST not properly bonded to grounding electrode system
3. Undersized piping (inadequate for BTU load, especially after adding appliances)
4. Gas pipe run through a concealed space without being properly supported
5. Improper material (using galvanized pipe for gas in some jurisdictions where it is not allowed)
6. Missing shut-off valve at each appliance (code requires an accessible shut-off within 6 feet of each appliance)
7. Gas pipe used as electrical ground (this is a code violation and a safety hazard)
8. Flex connector through a wall (flex connectors must be in the same room as the appliance and visible)
9. Thread sealant on flare fittings (flare fittings seal metal-to-metal and compound on the threads can migrate into the flare face, causing a leak)
10. No pressure test documentation after work is completed


## Fixture Installation

### Toilet Installation

**Flange height:** The top of the closet flange should be flush with or up to 1/4" above the finished floor. A flange that is too low (common when new flooring is installed over old) requires a flange extender or stacking wax ring. A flange that is too high lifts the toilet off the floor and causes rocking.

**Wax ring vs wax-free:**
- Wax rings (traditional): Cheap, proven, single-use. A standard wax ring works for flanges at floor level. An extra-thick wax ring or one with a horn (plastic extension) works for flanges up to 1/2" below the floor. Wax does not recover after compression -- if you set the toilet and then lift it to reposition, you need a new wax ring
- Wax-free seals (Fluidmaster Better Than Wax, Danco Perfect Seal): Rubber gasket that seals mechanically. Reusable -- you can lift and reset the toilet without replacing the seal. Works on flanges above or below the floor level (some are adjustable). More forgiving of imperfect flange conditions. Costs more than wax but worth it for difficult installations

**Setting the toilet:**
1. Remove the old wax ring completely. Scrape the flange clean. Inspect the flange for cracks, corrosion, or broken bolt slots
2. Install new closet bolts in the flange slots. Tighten them with nuts and washers to hold them upright
3. Place the wax ring on the flange (horn down if it has one) or install the wax-free seal per its instructions
4. Lower the toilet straight down, guiding the closet bolts through the holes in the base. Press down firmly with a slight rocking motion to compress the wax ring
5. Hand-tighten the nuts on the closet bolts. Then alternate sides, tightening 1/4 turn at a time. Stop when the toilet is snug to the floor. Do not overtighten -- porcelain cracks easily
6. Check for level side-to-side. Shim if needed with toilet shims (plastic wedges)
7. Connect the supply line (3/8" compression typically) to the fill valve and the shut-off valve
8. Caulk the base of the toilet to the floor (code requires this in many jurisdictions). Leave a gap at the back so a leak under the toilet is visible

### Faucet Replacement

**Supply line sizing:** Most lavatory and kitchen faucets use 3/8" compression supply lines. Some newer faucets have 1/2" connections. Braided stainless steel supply lines are the standard -- they are flexible, durable, and resist bursting. Avoid chrome-plated ribbed supply tubes -- they kink and leak.

**Shut-off valve types:**
- Compression stop (round handle): Common on older installations. Uses a rubber washer that compresses against a seat. They work fine for years but tend to seize up from mineral deposits. If you turn one that has not been operated in years, it may leak
- Quarter-turn ball valve (lever handle): Modern standard. Full-bore, reliable, and does not seize. When replacing a compression stop, upgrade to a quarter-turn ball valve
- Multi-turn gate valve: Older style, found on main lines. They restrict flow when partially open and are prone to failure. Replace with ball valves when possible

### Garbage Disposal Installation

**Electrical:** Disposals are either hardwired or cord-and-plug connected. A cord-and-plug disposal connects to a standard grounded outlet under the sink (switched or unswitched). A hardwired disposal connects directly to a switch-controlled cable. The switch should be accessible (countertop air switch, wall switch, or sink-mounted push button). Air switches are popular in remodels because they do not require cutting into the wall for a switch box.

**Dishwasher connection:** If a dishwasher is present, knock out the dishwasher inlet plug inside the disposal (use a screwdriver and hammer from the disposal side, then retrieve the plug from inside the disposal before using it). Connect the dishwasher drain hose to this inlet. The drain hose must make a high loop under the countertop (secured with a clamp at the highest point) or connect through an air gap device mounted on the sink deck.

**Mounting:** Most disposals use a three-bolt mounting ring that attaches to a sink flange. Apply plumber's putty under the sink flange before installing it in the drain opening. Tighten the mounting ring evenly. The disposal hangs from this ring and locks in with a twist. Support heavy disposals (3/4 HP and up) with a bracket or strap to prevent the mounting ring from working loose over time.

### Water Heater Connections

**Supply connections:**
- Flexible water heater connectors (braided stainless or corrugated copper) are the standard in most jurisdictions. They accommodate thermal expansion movement and are faster to install
- Rigid copper connections are allowed and some jurisdictions require them
- Dielectric unions are required where dissimilar metals connect (copper pipe to steel water heater nipples). The dielectric union has a plastic insulator that prevents galvanic corrosion. Without it, the joint corrodes and eventually leaks. Some flex connectors have built-in dielectric fittings

**T&P valve discharge:** The relief valve outlet must have a discharge pipe that runs downhill to within 6 inches of the floor or to a floor drain. No valve, cap, or thread at the termination. No reduction in pipe size. Material must handle high temperature (copper or CPVC -- not PEX, which may deform at T&P temperatures).

### Shower Valve Rough-In

**Standard rough-in dimensions:**
- Shower valve center: 48" above the finished floor (adjustable based on homeowner preference, 42-52" typical range)
- Shower head outlet: 72-78" above the finished floor (80" for tall users)
- Tub/shower combination valve: 28-32" above the finished floor (measured from tub bottom)
- Valve must be accessible from the front -- plan the wall depth to accommodate the valve body

**Mixing valve types:**
- Pressure-balance valve (single handle): Maintains a constant ratio of hot to cold water. If cold pressure drops (someone flushes a toilet), the valve reduces hot flow to maintain the ratio. Prevents scalding. Required by code for all new shower installations. Brands: Moen Posi-Temp, Delta Monitor, Kohler Rite-Temp
- Thermostatic valve: Maintains a set temperature regardless of pressure or supply temperature changes. More precise than pressure-balance. Uses a wax element or bimetallic sensor. More expensive, typically used in higher-end installations. Some models have separate volume and temperature controls
- Anti-scald requirement: All new shower valves must limit maximum hot water temperature to 120F per code. The adjustment is usually a rotational limit stop inside the valve body. Set it during rough-in testing before closing the wall

### Bathtub Installation

**Drain assembly:** The tub drain consists of the drain shoe (connects to the tub drain opening), the overflow tube (connects to the overflow opening), and the waste-and-overflow assembly that joins both and connects to the trap. Most modern waste-and-overflow kits use a flexible or semi-flexible tube between the overflow and the tee. Make sure all connections are tight and tested before closing the wall.

**Overflow:** The overflow is not optional -- it prevents the tub from flooding if the water is left running. The overflow plate covers the opening and may contain the trip lever or push-pull drain control mechanism. Cable-operated drains (trip lever type) have a plunger or spring that moves inside the overflow tube to open and close the drain. Toe-touch and push-pull drains operate directly at the drain opening and are simpler to maintain.

**Access panel requirement:** Code requires an access panel on the wall behind the tub or shower valve and drain connections. Minimum 12" x 12" opening. This allows future service of the valve, drain, and trap without demolishing the wall. In practice, many builders install the access panel in a closet or adjoining room. If no access panel exists, note it -- the homeowner will face a wall opening for any future plumbing repair behind the tub.


## Water Treatment

### Water Softener Sizing

Water softeners remove hardness minerals (calcium and magnesium) through ion exchange. The resin bed swaps sodium or potassium ions for the hardness ions. When the resin is exhausted, the softener regenerates (backwashes and recharges the resin with brine).

**Sizing formula:**
1. Determine water hardness in grains per gallon (GPG). If reported in mg/L or PPM, divide by 17.1 to convert to GPG
2. If iron is present, add 5 GPG for each 1 PPM of iron (iron fouls the resin and increases load)
3. Multiply total hardness (GPG) by daily water usage in gallons. A household uses roughly 75 gallons per person per day
4. This gives you daily grain removal requirement
5. The softener should regenerate every 7-10 days for efficiency. Multiply daily grains by 7-10 to get the required grain capacity

Example: 20 GPG hardness, 4-person household.
- 20 GPG x (4 people x 75 gallons/day) = 20 x 300 = 6,000 grains per day
- 6,000 x 7 days = 42,000 grain capacity needed
- A 48,000 grain softener is the right size

Oversizing wastes salt. Undersizing causes frequent regeneration, excessive water use, and premature resin exhaustion.

### Sediment Filters

Sediment filters remove particulate matter (sand, silt, rust, scale) from the water supply. They are installed on the main water line after the meter and before any other treatment equipment.

**Micron ratings:**
- 50-100 micron: Coarse filtration. Removes sand and large sediment. Good as a pre-filter to protect downstream equipment
- 20-50 micron: Standard whole-house sediment filter. Removes visible particulates without restricting flow significantly
- 5-10 micron: Fine filtration. Removes smaller sediment but creates more pressure drop. May need more frequent replacement
- 1-5 micron: Very fine. May be needed for specific water quality problems but will clog quickly in water with significant sediment

**Filter types:**
- Spin-down/flush filter: Reusable screen that can be flushed clean without removing. Good as a first-line sediment filter on well systems
- Pleated cartridge: More surface area, longer life between changes. Good for moderate sediment
- String-wound/melt-blown: Depth filtration that traps sediment throughout the filter body. Good for high sediment loads

Change frequency depends on water quality. On a well with sandy sediment, a filter may last 2-4 weeks. On a clean municipal supply, 3-6 months. Install a pressure gauge before and after the filter -- when the pressure drop across the filter exceeds 10-15 PSI, it is time to change.

### Carbon Filters

Carbon filtration removes chlorine, chloramine, volatile organic compounds (VOCs), bad taste, and odor. It does not remove hardness, TDS, bacteria, or heavy metals (with some exceptions).

**Granular activated carbon (GAC):** Loose carbon granules in a cartridge or tank. Water flows through the carbon bed. Good contact time provides good removal. Used in whole-house and point-of-use applications. Eventually the carbon becomes saturated and must be replaced.

**Carbon block:** Compressed carbon in a solid block. More effective than GAC because the water is forced through the carbon with more contact. Also provides some sediment filtration. Used in under-sink and refrigerator filters.

**Catalytic carbon:** Specifically designed to remove chloramine (which is harder to remove than chlorine). If your municipal water uses chloramine as a disinfectant, standard carbon filters are inadequate -- specify catalytic carbon.

### Reverse Osmosis (RO) Systems

RO pushes water through a semipermeable membrane that removes 95-99% of dissolved solids, including minerals, salts, heavy metals, fluoride, nitrates, and many contaminants that other filters miss.

**Under-sink RO:** The standard residential installation. Includes a pre-filter (sediment), pre-filter (carbon to protect the membrane from chlorine), the RO membrane, a post-filter (carbon polishing), and a storage tank. Produces 50-100 gallons per day typically. Waste ratio is 3:1 to 4:1 (3-4 gallons of waste water for every 1 gallon of permeate). A dedicated faucet at the sink dispenses the filtered water.

**Maintenance schedule:**
- Pre-filters and post-filters: replace every 6-12 months
- RO membrane: replace every 2-3 years (or when TDS readings rise above acceptable levels)
- Storage tank: check air pressure annually (should be 7-8 PSI with an empty tank)

**Whole-house RO:** Commercial-scale equipment. Requires a large membrane array, a storage tank (often 200+ gallons), a repressurization pump, and remineralization to prevent the acidic RO water from corroding the plumbing. Expensive to install and maintain. Generally only justified for severe water quality issues.

### UV Sterilization

UV (ultraviolet) water purification uses UV-C light at 254 nanometers to inactivate bacteria, viruses, and protozoa by damaging their DNA. It does not remove chemicals or sediment -- it is strictly a disinfection method.

**When to recommend UV:**
- Well water systems where bacterial contamination is a risk
- After other treatment (softener, filters) as a final disinfection step
- Where a positive coliform test has occurred
- For vacation homes or seasonal properties where standing water in pipes may develop bacteria

**Installation requirements:**
- Install after all other filtration (the water must be clear for UV to work -- sediment and turbidity block UV light)
- Water turbidity should be below 1 NTU for effective UV treatment
- Flow rate must match the UV unit rating. Undersized units do not deliver adequate UV dose
- The UV lamp requires replacement annually regardless of water quality -- UV output degrades over time even if the lamp still appears to be working
- The quartz sleeve (glass tube around the lamp) should be cleaned every 6-12 months and replaced if etched or clouded

### Common Water Quality Problems

**Hard water (above 7 GPG):** Scale buildup in pipes, water heater, and fixtures. White spots on glass and dishes. Reduced soap lathering. Solution: water softener.

**Iron (above 0.3 PPM):** Orange/brown staining on fixtures, laundry, and toilet bowls. Metallic taste. Low levels (under 3 PPM) can be removed by a water softener. Higher levels require an iron filter (manganese greensand, birm, or air injection system).

**Sulfur (hydrogen sulfide):** Rotten egg smell. If present in hot water only, the magnesium anode rod in the water heater is the likely cause -- replace with aluminum/zinc rod. If present in both hot and cold, the source water contains sulfur. Treatment: aeration, chlorine injection, or catalytic carbon.

**Low pH (below 6.5):** Acidic water corrodes copper piping (blue-green stains on fixtures) and can leach lead from solder joints. Treatment: acid neutralizer (calcite/corosex media).

**Bacteria (positive coliform test):** Immediate concern for well systems. Shock-chlorinate the well (pour chlorine solution into the well, run it through the system, let it sit for 12-24 hours, then flush). Install UV sterilization for ongoing protection. Retest 2 weeks after treatment.


## Commercial Plumbing Basics

### Backflow Prevention

Backflow is the reverse flow of contaminated water into the potable water supply. It occurs from backpressure (downstream pressure exceeds supply pressure) or backsiphonage (negative pressure in the supply). Every connection to the potable water system that could be a contamination source requires a backflow preventer.

**Types of backflow preventers (from least to most protection):**

**Atmospheric Vacuum Breaker (AVB):** Simplest device. A small valve that opens to admit air when supply pressure drops. Used on hose bibs, irrigation systems, and similar low-hazard connections. Must be installed above the highest downstream outlet. Cannot be used on continuous pressure applications (irrigation systems with downstream shut-offs) because it will vent water continuously. Not testable.

**Double Check Valve Assembly (DCVA):** Two independently operating check valves in series with test cocks. Used for low to moderate hazard situations: fire sprinkler connections, irrigation with no chemical injection, commercial dishwasher supply. Must be tested annually by a certified backflow tester.

**Reduced Pressure Zone (RPZ) Assembly:** The highest level of protection for testable assemblies. Has two check valves and a pressure-differential relief valve between them. If either check valve fails, the relief valve opens and dumps water rather than allowing contamination to pass. Used for high-hazard situations: boiler make-up water, chemical feed systems, medical facilities, and any connection where contamination could be harmful. Must be installed in a location where the relief valve discharge will not cause damage (it can dump significant water). Must be tested annually.

**When each is required:** Your local water authority dictates this. Generally: residential hose bibs get an AVB or vacuum breaker at the sillcock. Irrigation systems get a DCVA or RPZ depending on chemical use. Commercial properties get an RPZ on the building service entrance. Fire sprinkler connections typically get a DCVA.

### Grease Traps and Interceptors

Any commercial kitchen that discharges grease-laden waste water requires a grease trap or interceptor. The device slows the flow of waste water, allowing grease (which is lighter than water) to float and accumulate while cleaner water continues to the sewer.

**Under-sink grease traps:** Small units (20-50 GPM capacity) installed under individual sinks or dishwashers. Must be cleaned frequently (every 1-2 weeks) or they become ineffective and pass grease.

**In-ground grease interceptors:** Large buried tanks (500-2000 gallons or more) that serve the entire kitchen. Sized by flow rate and retention time (typically 30 minutes). Must be pumped regularly (monthly or quarterly, depending on volume and usage). Health departments and sewer authorities inspect and enforce maintenance schedules.

**Sizing:** Determined by the fixture flow rate, number of fixtures draining through the interceptor, and local code requirements. The basic formula: flow rate (GPM) x retention time (minutes) x storage factor = tank volume. Manufacturers provide sizing guides based on number and type of fixtures.

### Thermostatic Mixing Valves (TMVs)

Commercial hot water systems often store water at 140F or higher to prevent Legionella bacteria growth (Legionella thrives at 77-113F). TMVs blend the high-temperature stored water with cold water to deliver safe, consistent water at 120F or less to fixtures.

**Where required:**
- Lavatory faucets in public restrooms (ADA requires max 120F)
- Showers (anti-scald requirement)
- Healthcare facilities (ASSE 1017 or ASSE 1070 rated valves)
- Any application where stored water temperature exceeds the safe delivery temperature

**Point-of-use vs point-of-distribution:** A single large TMV at the water heater serves the entire building (point-of-distribution). Individual TMVs at each fixture group provide more precise control (point-of-use). Healthcare and high-precision applications often use point-of-use TMVs.

### Sump Pumps and Ejector Pumps

**Sump pumps:** Remove ground water that collects in a sump pit (crock). The pit is typically 18-24" diameter and 24-30" deep, set below the basement floor. A float switch activates the pump when water reaches a set level. The pump discharges to a storm sewer, dry well, or to grade (never to the sanitary sewer in most jurisdictions).

**Sewage ejector pumps:** Handle waste water from fixtures below the sewer line (basement bathrooms, laundry rooms below grade). The ejector pump sits in a sealed basin (to contain sewer gas) with a vented cover. It pumps waste up to the gravity sewer line above. A check valve on the discharge prevents backflow into the basin.

**Sizing considerations:**
- Flow rate: the pump must handle the GPM demand of all connected fixtures
- Head pressure: vertical lift from the pump to the discharge point, plus friction loss in the pipe
- Basin size: must be large enough to handle the flow without short-cycling the pump

**Maintenance:**
- Test the pump annually by pouring water into the pit until the float activates
- Check valve: verify it is holding (a failed check valve causes the pump to cycle repeatedly as water flows back into the pit)
- Install a high-water alarm on every sump and ejector pit. A $25 alarm prevents thousands in water damage
- Battery backup or water-powered backup pump for sump pits in areas with frequent power outages


## Troubleshooting

### No Hot Water

**Gas water heater -- systematic approach:**
1. Check the pilot light. If out, attempt to relight per the instructions on the unit
2. Pilot will not light: verify gas supply (other gas appliances working?), check the gas valve is in the ON position, check the thermocouple connection
3. Pilot lights but will not stay lit: thermocouple is bad (most common) or gas valve electromagnet is weak. Test thermocouple millivolt output (see water heater diagnostics section)
4. Pilot stays lit but burner does not fire: thermostat on the gas valve may be bad, or the thermostat is set too low. Turn up the setting and listen for the burner to fire
5. Burner fires but water is not hot enough: check the thermostat setting, check the dip tube (a broken dip tube lets cold water mix with hot), check for sediment buildup (flush the tank)

**Electric water heater -- systematic approach:**
1. Check the breaker. Reset if tripped. If it trips again immediately, there is a grounded element or wiring short
2. Press the high-limit reset button (red button on the upper thermostat behind the access panel). If it clicks and the heater starts working, monitor it. If it trips again, test the elements for grounding (see electric water heater section)
3. No hot water at all, breaker is on, high-limit is not tripped: test for power at the upper element. If power is present and the element reads open (infinite ohms), the upper element is burned out. Replace it
4. Some hot water but runs out fast: lower element is likely bad. The upper element heats the top of the tank, but the bulk of the water in the lower portion never gets heated
5. Water is too hot: thermostat is stuck in the on position or is miscalibrated. Replace the thermostat

### Low Water Pressure

**Single fixture -- low pressure:** The problem is local to that fixture.
1. Check the shut-off valve -- is it fully open?
2. Remove the aerator from the faucet. Inspect for debris (sediment, calcium chunks, rubber gasket pieces). Clean or replace
3. Check the supply line for kinks (braided supply hoses can kink at the angle stop)
4. On a faucet with a cartridge: remove the cartridge and check for debris inside the valve body
5. On a shower: remove the shower head and check the flow restrictor (built-in washer that limits flow). Debris can clog it

**Whole-house -- low pressure:**
1. Test static pressure at the hose bib nearest the meter. Below 40 PSI indicates a supply issue (contact the water utility) or a failing PRV
2. Check the main shut-off valve -- is it fully open? Gate valves partially closed reduce pressure dramatically
3. Check the water meter valve -- if the utility recently worked on the meter, the meter valve may not be fully open
4. Check the PRV -- a failing PRV restricts flow. Test by temporarily bypassing it (plumb around it with a temporary hose connection) and checking pressure downstream. If pressure improves, replace the PRV
5. Galvanized piping: if the house has galvanized supply pipes and is over 40 years old, internal corrosion is almost certainly the cause. A repipe is the permanent solution

### Running Toilet

A running toilet wastes 200+ gallons per day. Three possible causes, check in this order:

1. **Flapper:** Lift the lid and push down on the flapper. If the running stops, the flapper is not sealing. Check for warping, mineral buildup, or chain tangling. Replace the flapper (universal flappers fit most toilets, but Kohler, American Standard, and Toto sometimes require brand-specific flappers). The chain should have 1/2" of slack -- too tight and the flapper cannot seal, too loose and the chain gets under the flapper

2. **Fill valve:** The fill valve controls the water level in the tank. If the water level is above the overflow tube, the fill valve is not shutting off. Adjust the float (screw on the top of the valve for modern fill valves, bend the float rod on older ballcock-style valves). The water level should be about 1 inch below the top of the overflow tube. If adjustment does not work, replace the fill valve

3. **Overflow tube:** If the overflow tube is cracked below the water line, water continuously drains into the bowl. Replace the flush valve assembly (which includes the overflow tube). This requires removing the tank

### Leaking Under Sink

**Identify the source before disassembling anything.** Dry everything, place paper towels under the sink, and run water. Check:

1. **Supply line connections:** Drip at the shut-off valve or at the faucet connection. Tighten the compression nut 1/4 turn. If it still leaks, the ferrule may be damaged -- replace the supply line
2. **Faucet base:** Water running down the back of the faucet into the cabinet. The faucet O-rings or base gasket need replacement
3. **Drain connections:** P-trap slip nuts are the most common drain leak. Tighten the slip nuts by hand (plastic) or with slip-joint pliers (chrome). If the nylon washer inside the slip nut is worn, replace it
4. **Garbage disposal flange:** Water dripping from the top of the disposal means the mounting flange seal has failed. Remove the disposal, replace the plumber's putty seal, and remount
5. **Dishwasher drain hose:** The hose connection at the disposal or tailpiece can loosen. Check the hose clamp

### Sewer Gas Smell

Sewer gas contains hydrogen sulfide, methane, and other gases. It is unpleasant and in high concentrations can be a health hazard.

**Check in this order:**
1. **Dry traps:** Run water in every drain in the building, especially floor drains, basement drains, and unused fixtures. Each trap needs at least a cup of water to maintain its seal. In basements with floor drains that are rarely used, pour a tablespoon of mineral oil on top of the water in the trap -- it slows evaporation
2. **Toilet wax ring:** Rock the toilet gently. If it moves, the wax ring has likely failed. Remove and replace
3. **Missing cleanout cap:** Check all accessible cleanouts. A missing cap is an open pipe to the sewer
4. **Cracked vent pipe:** Inspect accessible vent pipes in the attic. PVC vent connections can crack, especially at fittings where thermal movement creates stress. ABS and cast iron vents can crack with age
5. **Failed AAV:** If air admittance valves are present, they may be stuck open. Replace
6. **Ejector pump basin:** If the basement has an ejector pump, the basin cover must be sealed and the basin must be vented. A loose or cracked cover leaks sewer gas
7. **Blocked vent stack:** A blocked vent can cause pressure fluctuations that siphon traps. Check the roof vent terminal for obstructions

### Frozen Pipes

**Thawing methods (safe):**
- Open the faucet first so melting water and steam can escape
- Apply heat from the faucet end working back toward the frozen section (this allows water to drain as it melts)
- Heat gun or hair dryer: direct warm air at the frozen section. Slow but safe
- Heat tape or heat cable: wrap around the pipe and plug in. Takes time but works on accessible pipes
- Hot towels: wrap the pipe with towels soaked in hot water. Replace as they cool
- Space heater: aim at the general area for enclosed spaces (crawl spaces, cabinets against exterior walls)

**Do not use:** Open flame (torch, propane heater) directly on pipes. This can cause steam explosions in trapped sections, damage PEX/CPVC/PVC pipes, and start fires in walls. Torches on copper are acceptable with extreme caution and a fire shield, but other methods are safer.

**Prevention:**
- Insulate all pipes in unconditioned spaces (crawl spaces, attics, exterior walls, garages)
- In extreme cold, open cabinet doors under sinks on exterior walls to allow warm air circulation
- Keep the thermostat at 55F minimum in unoccupied buildings
- Heat cable on vulnerable pipes (self-regulating heat cable is preferred -- it adjusts output based on temperature)
- Seal air leaks near pipes (rim joists, sill plates, penetrations through exterior walls)
- Know where the main shut-off is so you can close it quickly if a pipe bursts

### Water Heater Not Keeping Up

**Possible causes by likelihood:**
1. **Undersized unit:** The first hour rating does not match the household demand. A family that upgraded from 2 to 4 showerheads may have outgrown their 40-gallon heater. Calculate the demand and compare to the FHR on the rating plate
2. **Broken dip tube:** The dip tube directs incoming cold water to the bottom of the tank. If it breaks, cold water enters at the top and mixes with hot water at the outlet, resulting in lukewarm water. Dip tubes on water heaters manufactured between 1993-1997 (especially those with a Perflex dip tube) are notorious for deterioration. Replace the dip tube
3. **Sediment buildup:** Sediment insulates the bottom of the tank from the burner (gas) or lower element (electric), reducing heat transfer. The heater runs longer, recovers slower, and costs more to operate. Flush the tank. If sediment is heavy and will not flush (chunks clogging the drain valve), the tank may need replacement
4. **Failing heating elements (electric):** A lower element coated in scale heats less efficiently. A partially failed element (high resistance) heats more slowly. Test element resistance
5. **Cross-connection:** A single-handle faucet or mixing valve somewhere in the system is passing cold water into the hot line. To test: close the cold shut-off at the water heater and open a hot-water-only faucet. If water still flows, there is a cross-connection through a mixing valve somewhere
6. **Long pipe runs:** The hot water line from the water heater to the fixture is too long, and too much heat is lost in the pipe before the water arrives. Consider a recirculation pump or point-of-use tankless heater for distant fixtures
