# Building Codes Practical Reference for Tradespeople

This document covers the practical requirements from major building codes that tradespeople encounter daily. This is not a substitute for the actual code books -- always verify against the adopted code edition in your jurisdiction. Code cycles change every three years, and local amendments can modify or override national code requirements.

## NEC (National Electrical Code) Practical Requirements

### GFCI Requirements — NEC 210.8

GFCI (Ground-Fault Circuit Interrupter) protection is required for 125-volt, 15- and 20-ampere receptacles in the following locations. The 2023 NEC expanded these requirements significantly.

**Bathrooms (210.8(A)(1)):** All receptacles. No exceptions. This has been in the code since 1975 and should never be missed.

**Garages and accessory buildings (210.8(A)(2)):** All receptacles, including dedicated receptacles for refrigerators and freezers. The 2020 NEC removed the exception for non-readily accessible receptacles. If it is in the garage, it needs GFCI protection.

**Outdoors (210.8(A)(3)):** All receptacles. This includes receptacles on the roof, on balconies, and in carports. Dedicated receptacles for outdoor equipment (heat pumps, condensing units) are exempt if they are not readily accessible.

**Crawl spaces (210.8(A)(4)):** All receptacles at or below grade level.

**Unfinished basements (210.8(A)(5)):** All receptacles. Dedicated sump pump receptacles still require GFCI protection (the exception was removed in 2020 NEC).

**Kitchens (210.8(A)(6)):** All receptacles serving countertop surfaces, plus all receptacles within 6 feet of the outside edge of a sink. The 2020 NEC expanded this to include the dishwasher receptacle and any receptacle within 6 feet of a sink.

**Sinks (210.8(A)(7)):** All receptacles within 6 feet of the outside edge of any sink, in any location. This is the catch-all provision -- laundry sinks, wet bars, utility sinks, all of them.

**Boathouses (210.8(A)(8)):** All receptacles.

**Laundry areas (210.8(A)(10)):** All receptacles. Added in the 2014 NEC.

**Indoor damp/wet locations (210.8(A)(11)):** Bathtub and shower stall areas -- receptacles within 6 feet of those fixtures.

**250-volt receptacles (210.8(A)):** The 2023 NEC now requires GFCI protection for 250-volt receptacles (up to 50 amps) in many of the same locations. This affects kitchen ranges, dryers, and other 240V appliances.

### AFCI Requirements — NEC 210.12

AFCI (Arc-Fault Circuit Interrupter) protection is required for 120-volt, 15- and 20-ampere branch circuits supplying outlets and devices in the following areas of dwelling units:

- Kitchens
- Family rooms, dining rooms, living rooms, parlors, libraries, dens, bedrooms, sunrooms, recreation rooms, closets, hallways, laundry areas, and similar rooms or areas

**Practical impact:** Essentially every 120-volt branch circuit in a dwelling unit except the bathroom, garage, and outdoor circuits requires AFCI protection. The 2023 NEC allows AFCI protection to be provided by the circuit breaker (most common), by the first outlet on the circuit (outlet-branch-circuit type AFCI), or by a listed combination of devices.

**AFCI nuisance tripping:** This is the single biggest headache with AFCI breakers. Common causes include shared neutrals between circuits (multiwire branch circuits), certain types of motors (vacuum cleaners, treadmills), and fluorescent lighting with electronic ballasts. When troubleshooting nuisance trips, start by isolating loads to identify the culprit. Check for shared neutrals -- each AFCI circuit must have its own dedicated neutral back to the panel.

### Receptacle Spacing Rules — NEC 210.52

**General rule for dwelling unit wall receptacles (210.52(A)):** Any point along the floor line of a wall must be within 6 feet of a receptacle. In practice, this means a receptacle every 12 feet along the wall. Any wall space 2 feet or wider needs a receptacle. This includes space between doorways, behind doors, and on walls between windows if the space is 2 feet or wider.

**Kitchen countertop receptacles (210.52(C)):** Every countertop space 12 inches or wider must have a receptacle. No point along the countertop wall line can be more than 24 inches (2 feet) from a receptacle. Receptacles must be no more than 20 inches above the countertop surface. Island countertops and peninsular countertops each require at least one receptacle.

**Bathroom receptacles (210.52(D)):** At least one receptacle on a dedicated 20-amp circuit within 3 feet of each bathroom basin. Each bathroom can have its own dedicated circuit, or a single 20-amp circuit can serve receptacles in multiple bathrooms (no other outlets allowed on that circuit).

**Laundry receptacles (210.52(F)):** At least one receptacle on a dedicated 20-amp circuit for the laundry area.

### Wire Sizing and Ampacity — NEC Table 310.16 (75°C Column, Copper)

This is the table you will use 95% of the time. The 75°C column applies when using NM-B cable (Romex) terminated on 75°C rated devices, which is the standard residential configuration.

- **14 AWG:** 15 amps (15-amp circuits only)
- **12 AWG:** 20 amps
- **10 AWG:** 30 amps
- **8 AWG:** 40 amps
- **6 AWG:** 55 amps
- **4 AWG:** 70 amps
- **3 AWG:** 85 amps
- **2 AWG:** 95 amps
- **1 AWG:** 110 amps
- **1/0 AWG:** 125 amps
- **2/0 AWG:** 145 amps
- **3/0 AWG:** 165 amps
- **4/0 AWG:** 195 amps

**Derating:** When more than 3 current-carrying conductors are in the same raceway or cable, the ampacity must be derated per NEC Table 310.15(C)(1). Four to six conductors: derate to 80%. Seven to nine conductors: derate to 70%. This comes up frequently on commercial jobs with multiple circuits in one conduit.

### Box Fill Calculations — NEC 314.16

Every device box has a maximum number of conductors allowed, based on the box volume (in cubic inches) and the conductor size.

**Volume allowance per conductor (Table 314.16(B)):**
- 14 AWG: 2.0 cubic inches per conductor
- 12 AWG: 2.25 cubic inches per conductor
- 10 AWG: 2.5 cubic inches per conductor

**Counting conductors:**
- Each insulated wire entering the box counts as one conductor
- All equipment grounding conductors together count as one conductor (of the largest ground wire size)
- Each device (switch, receptacle) counts as two conductors (of the largest wire connected to it)
- Internal cable clamps count as one conductor (of the largest wire present)
- External cable clamps (NM connectors on the outside of the box) do not count

**Common box volumes:**
- Single-gang plastic old-work box: 14-18 cubic inches (varies by manufacturer)
- Single-gang metal box (common 3x2x2.5): 12.5 cubic inches
- Two-gang plastic box: 28-32 cubic inches
- 4-inch square box (4x4x1.5): 21 cubic inches
- 4-inch square box (4x4x2.125): 30.3 cubic inches

### Grounding Requirements — NEC Article 250

**Service equipment grounding:** The main bonding jumper must connect the neutral bus to the equipment grounding bus at the service entrance panel (and only at the service entrance panel -- in sub-panels, the neutral and ground must be separated).

**Grounding electrode system (250.50):** All of the following that are present must be bonded together: metal underground water pipe (at least 10 feet in contact with earth), metal building frame, concrete-encased electrode (Ufer ground -- at least 20 feet of 4 AWG bare copper in the footing), and ground ring. If none of these are available, install two ground rods at least 6 feet apart.

**Ground rod requirements (250.52):** 8 feet long, 5/8-inch diameter copper-clad or 1/2-inch galvanized steel. Must be driven to a full 8 feet depth. If rock prevents full depth, drive at a 45-degree angle or bury in a 30-inch deep trench.

### Dedicated Circuit Requirements

The NEC requires dedicated circuits for specific appliances and locations:
- **Dishwasher:** Dedicated 15- or 20-amp, 120V circuit
- **Garbage disposal:** Dedicated 15- or 20-amp, 120V circuit (can be shared with dishwasher if local code permits -- check your jurisdiction)
- **Laundry:** Dedicated 20-amp, 120V circuit for the receptacle
- **Bathroom:** Dedicated 20-amp, 120V circuit for receptacles (one circuit per bathroom, or one circuit serving multiple bathroom receptacles only)
- **Garage:** Dedicated 20-amp, 120V circuit for receptacles
- **Kitchen:** At least two dedicated 20-amp small-appliance branch circuits serving the countertop receptacles (210.52(B)). These circuits cannot serve any other outlets except the kitchen, pantry, breakfast nook, and dining room receptacles
- **Refrigerator:** An individual 15- or 20-amp circuit is recommended but not specifically required by the NEC (check local amendments -- many jurisdictions require it)

### Conduit Fill — NEC Chapter 9, Table 1

Maximum conduit fill percentages:
- **1 conductor:** 53% of the conduit cross-sectional area
- **2 conductors:** 31%
- **3 or more conductors:** 40%

These percentages apply to the total cross-sectional area of all conductors (including insulation) relative to the internal area of the conduit. Use Chapter 9, Tables 4 and 5 for the actual cross-sectional areas of conduits and conductors.

### Service Entrance Requirements — NEC Article 230

**Service entrance conductors:** The service entrance conductors (the wires from the utility meter to the main panel) must be sized for the calculated load of the dwelling. For most single-family homes:
- 100-amp service: Minimum 4 AWG copper or 2 AWG aluminum (for older/smaller homes). 100-amp service is the minimum allowed by most jurisdictions for a single-family dwelling, but it is increasingly insufficient for modern homes with electric dryers, ranges, heat pumps, and EV chargers
- 200-amp service: Minimum 2/0 AWG copper or 4/0 AWG aluminum. This is the current standard for new single-family home construction
- 400-amp service: Requires a meter-main or CT (current transformer) metering. Increasingly common in all-electric homes with EV charging, heat pumps, and electric water heaters

**Working clearance (NEC 110.26):** The main panel requires a minimum 30 inches wide, 36 inches deep (in front of the panel), and 78 inches high clear working space. The panel cannot be located in a bathroom (NEC 240.24(E)) or over steps. The panel must be accessible (not blocked by shelving, equipment, or storage). Breaker handles must be no higher than 6 feet 7 inches above the floor (NEC 240.24(A)).

**Grounding electrode conductor sizing (NEC Table 250.66):**
- 100-amp service (4-2 AWG copper service conductors): 8 AWG copper GEC minimum
- 200-amp service (2/0-3/0 AWG copper service conductors): 4 AWG copper GEC minimum
- 400-amp service (over 3/0 to 350 kcmil copper): 2 AWG copper GEC minimum

**Service disconnect:** Every building must have a readily accessible means to disconnect all conductors from the service entrance. The 2020 NEC added a requirement for an emergency disconnect on the exterior of the building (NEC 230.85) for one- and two-family dwellings. This exterior disconnect must be readily accessible and marked as an emergency disconnect. This is a significant change that affects every new residential service installation.

## IPC/UPC (Plumbing Codes) Practical Requirements

### Drain Pipe Sizing and Slope

**Minimum slope requirements:**
- Pipe 3 inches and smaller: 1/4 inch per foot minimum slope
- Pipe 4 inches and larger: 1/8 inch per foot minimum slope
- Maximum slope: Generally should not exceed 1/2 inch per foot. Excessive slope causes liquids to flow faster than solids, leaving solids behind in the pipe

**Minimum drain pipe sizes:**
- Lavatory (bathroom sink): 1-1/4 inch
- Kitchen sink: 1-1/2 inch (2 inch if it has a disposal)
- Bathtub: 1-1/2 inch
- Shower: 2 inch
- Toilet (water closet): 3 inch minimum (4 inch for the building drain/sewer)
- Washing machine standpipe: 2 inch
- Floor drain: 2 inch minimum

### Venting Rules — Maximum Trap-to-Vent Distance

The maximum distance from the trap weir to the vent fitting depends on the pipe size:

- **1-1/4 inch pipe:** 5 feet (IPC) / 3.5 feet (UPC)
- **1-1/2 inch pipe:** 6 feet (IPC) / 5 feet (UPC)
- **2 inch pipe:** 8 feet (IPC) / 5 feet (UPC)
- **3 inch pipe:** 12 feet (IPC) / 6 feet (UPC)
- **4 inch pipe:** 16 feet (IPC) / 10 feet (UPC)

**Practical note:** The IPC (International Plumbing Code) is generally more lenient on trap-to-vent distances than the UPC (Uniform Plumbing Code). Know which code your jurisdiction uses. Most eastern and central states use the IPC. Most western states use the UPC.

**Vent pipe sizing:** The vent must be at least half the diameter of the drain it serves, with a minimum of 1-1/4 inch. A 3-inch toilet drain requires at least a 1-1/2-inch vent (2 inches is more common and easier to run).

### Fixture Unit Values (DFU)

Drainage Fixture Units are used to size drain piping, vent piping, and the building sewer:

| Fixture | DFU |
|---------|-----|
| Lavatory (bathroom sink) | 1 |
| Bathtub/shower | 2 |
| Kitchen sink | 2 |
| Dishwasher | 2 |
| Washing machine | 3 |
| Toilet (1.6 GPF or less) | 3 |
| Toilet (greater than 1.6 GPF) | 4 |
| Floor drain | 2 |
| Laundry sink | 2 |
| Bar sink | 1 |

**Building drain and sewer sizing by DFU:**
- 3 inch pipe at 1/4"/ft slope: Up to 20 DFU (IPC) or 35 DFU (UPC)
- 4 inch pipe at 1/8"/ft slope: Up to 180 DFU (IPC) or 216 DFU (UPC)

### P-Trap Requirements

Every fixture connected to the drainage system must have a P-trap (or integral trap). The trap provides a water seal that prevents sewer gases from entering the building.

**Key requirements:**
- Trap seal depth: 2 to 4 inches of water (the water column in the trap). Less than 2 inches is too shallow and may evaporate or be siphoned. More than 4 inches creates excessive resistance to flow
- Each fixture must have its own trap (except for a bathtub and shower in the same bathroom, which can share under some codes, and except for fixtures with integral traps like toilets)
- S-traps are prohibited -- they can self-siphon. Use P-traps only
- Double-trapping (two traps in series) is prohibited -- it creates an air lock
- The trap must be accessible for cleaning (either through the fixture drain or through a cleanout)
- Drum traps are generally prohibited in new construction (some codes allow them for specific applications)

### Water Heater Installation Requirements

**T&P (Temperature and Pressure) relief valve:**
- Required on every water heater
- Must be rated for the working pressure of the water heater (typically 150 PSI) and the temperature (typically 210°F)
- The discharge pipe must terminate within 6 inches of the floor or to an indirect waste receptor. It must not be threaded on the end (to prevent capping). It must not have any valves or restrictions. The pipe diameter must be at least as large as the valve outlet (typically 3/4 inch)
- No reduction in pipe size is allowed along the discharge pipe
- The discharge pipe must be piped to a safe location where the hot water discharge will not cause injury or property damage

**Expansion tank:** Required when a backflow preventer, pressure-reducing valve, or check valve is installed on the cold water supply to the water heater. These devices create a closed system -- when the water heats and expands, the pressure has nowhere to go. The expansion tank absorbs the expanded water volume and prevents the T&P valve from dripping.

**Drain pan:** Required under tank-type water heaters installed in locations where a leak would cause damage (attics, upper floors, finished basements). The pan must have a 3/4-inch minimum drain to a safe location.

**Seismic strapping:** Required in seismic zones. Two straps: one in the upper one-third and one in the lower one-third of the water heater.

### Backflow Prevention Requirements

**Backflow** occurs when contaminated water flows backward into the potable water supply. The plumbing code requires backflow prevention at every cross-connection point.

**Types of backflow prevention:**
- **Air gap:** The most reliable method. The discharge pipe must terminate at least twice the pipe diameter above the flood rim of the receiving fixture (minimum 1 inch). Required for dishwashers in many jurisdictions (the dishwasher drain hose must loop up to the underside of the counter or connect to an air gap device mounted on the sink or countertop)
- **Reduced Pressure Zone (RPZ) assembly:** Required for high-hazard connections (irrigation systems with chemical injection, boiler feeds, fire sprinkler connections where antifreeze is used). RPZ assemblies must be tested annually by a certified backflow tester
- **Double check valve assembly (DCVA):** Suitable for low-to-medium hazard connections (fire sprinkler systems without chemical additives, irrigation systems without chemical injection). Also requires annual testing
- **Atmospheric vacuum breaker (AVB):** Used on hose bibbs (garden faucets), utility sinks, and irrigation connections. Cannot be installed where back-pressure is possible (no downstream shutoff valves)
- **Pressure vacuum breaker (PVB):** Used on irrigation systems. Must be installed at least 12 inches above the highest downstream point

**Dishwasher air gap requirement:** Many jurisdictions require either an air gap device on the countertop or a high loop in the dishwasher drain hose (looped up to the underside of the countertop). The high loop prevents backflow from the garbage disposal or drain into the dishwasher. Some jurisdictions specifically require the air gap device and do not accept the high loop -- check your local code.

### Gas Pipe Sizing Basics

Gas pipe sizing is based on the total BTU load of all gas appliances, the length of the longest run, and the allowable pressure drop (typically 0.5 inches WC for natural gas residential systems).

**Basic approach:**
1. List all gas appliances and their BTU input ratings
2. Measure the longest pipe run from the gas meter to the farthest appliance
3. Use the gas pipe sizing table (in the fuel gas code or manufacturer's tables) to find the minimum pipe diameter for each section
4. Size each section for the cumulative BTU load downstream of that point

**Rule of thumb for common residential pipe sizes (natural gas, 0.5" WC pressure drop, less than 0.6 specific gravity):**
- 1/2 inch black iron pipe, 20 feet: approximately 92,000 BTU/hr
- 3/4 inch, 20 feet: approximately 199,000 BTU/hr
- 1 inch, 20 feet: approximately 402,000 BTU/hr
- 1/2 inch CSST (corrugated stainless steel tubing): typically sized by the CSST manufacturer's tables -- generally equivalent to 3/4 inch rigid pipe

### Water Supply Pipe Sizing and Pressure

**Minimum water pressure:** The plumbing code requires a minimum of 8 PSI at the highest and most remote fixture. Most fixtures require 8-20 PSI to operate properly. Recommended supply pressure at the meter is 40-80 PSI. If the street pressure exceeds 80 PSI, a pressure reducing valve (PRV) is required to protect the plumbing system and appliances.

**Pipe sizing method:** Water supply pipes are sized based on the total fixture count (Water Supply Fixture Units -- WSFU), the developed length of the longest run, the available pressure, and the type of pipe material. Friction loss in the pipe reduces the available pressure at remote fixtures. Longer runs, more fittings, and smaller pipe all increase friction loss. When in doubt, go up one pipe size -- an oversized supply pipe never causes problems, but an undersized one always does.

**Hot water pipe insulation:** The energy code (IECC) requires insulation on hot water supply pipes in several scenarios: when the pipe runs through unconditioned spaces, when a hot water recirculation system is installed, and when the pipe is within the building envelope for energy compliance. R-3 minimum insulation is typical for residential hot water pipes.

## IMC/IFGC (Mechanical and Gas Code) Practical Requirements

### Furnace Clearance Requirements

**Clearance to combustibles:** The rating plate on every furnace specifies minimum clearances to combustible materials on all sides. Typical clearances: 1-3 inches on the sides, 1 inch on the top, and 1-6 inches at the back. Zero-clearance on one side is allowed on many models. Always check the installation manual -- clearances are specific to the model.

**Working clearance:** The code requires a minimum 30-inch working space in front of the service access panel. This is for the technician to safely service the unit. Do not install a furnace in a space where you cannot get the blower or heat exchanger out.

**Combustion air requirements (IFGC 304):** Gas appliances in confined spaces (less than 50 cubic feet per 1,000 BTU/hr of total input) require combustion air from outside the space. Two openings are required: one within 12 inches of the top of the enclosure and one within 12 inches of the bottom. Each opening must provide 1 square inch of free area per 4,000 BTU/hr for outside air, or 1 square inch per 1,000 BTU/hr for air from inside the building. Direct-vent (sealed combustion) appliances that draw combustion air through a dedicated pipe from outside do not require these openings.

### Vent and Flue Sizing and Termination

**Category I venting (natural draft, non-positive pressure):** Use the vent tables in the fuel gas code (NFPA 54/IFGC Chapter 5, Tables 504.2 and 504.3) to size the vent based on BTU input, height of the vent, and length of the lateral (horizontal) run. Common residential vent sizes: 3-inch for water heaters up to about 65,000 BTU, 4-inch for furnaces up to about 100,000 BTU, 5 or 6-inch for larger furnaces.

**Category IV venting (high-efficiency condensing, positive pressure):** 90%+ furnaces use PVC, CPVC, or polypropylene vent pipe. The furnace manufacturer specifies the pipe type, diameter, and maximum equivalent length. Do not mix pipe types unless the manufacturer allows it. CPVC is rated for higher temperatures than PVC and is required by some manufacturers.

**Vent termination clearances (general, always check local code):**
- At least 12 inches above grade (snow line may require more)
- At least 12 inches from any opening into the building (windows, doors, vents)
- At least 4 feet below, 4 feet horizontally from, or 1 foot above any opening
- At least 3 feet above any forced air intake within 10 feet
- Some manufacturers require 12-inch clearance from inside corners, and 12-inch clearance above anticipated snow level

### Gas Piping Requirements and Testing

**Gas pipe materials (IFGC 403):**
- Black iron (steel) pipe: The standard. Threaded or welded connections. Pipe compound or Teflon tape rated for gas on all threaded joints
- CSST (corrugated stainless steel tubing): Must be installed per manufacturer's instructions. Must be bonded to the grounding electrode system per 250.104(B) or the CSST manufacturer's instructions. The bonding conductor must be at least 6 AWG copper in most jurisdictions
- Copper tubing: Allowed in some jurisdictions for interior gas piping. Check local code
- PE (polyethylene) pipe: Exterior underground only. Must transition to metallic pipe before entering the building

**Pressure testing:** New gas piping must be pressure tested before being put into service. Typical residential test: 3 PSI (about 83 inches WC) air pressure for 15 minutes with no pressure drop. Do not use gas for the pressure test. After testing, purge the air from the piping before lighting any appliances.

**Gas shut-off valves:** Every gas appliance must have a shut-off valve within 6 feet of the appliance and upstream of the union or connector. The valve must be accessible and in the same room as the appliance.

### Carbon Monoxide Detection Requirements

The IMC and the International Residential Code (IRC) require carbon monoxide detectors in dwelling units with fuel-burning appliances or attached garages. Requirements vary by jurisdiction, but the general standard is:

- CO detectors are required outside each sleeping area (within 10 feet of bedroom doors) and on every level of the dwelling
- CO detectors must be listed to UL 2034 and installed per manufacturer's instructions
- Some jurisdictions require combination smoke/CO detectors
- CO detectors are required when any fuel-burning appliance is present (furnace, water heater, fireplace, gas range, generator) or when the dwelling has an attached garage

**This is a code requirement that is frequently missed on service calls.** When you install a new gas furnace or water heater and notice there are no CO detectors in the home, you should inform the customer that CO detection is required by current code. Some jurisdictions require the installing contractor to verify CO detector compliance as part of the permit inspection.

### Refrigerant Line Requirements

**Refrigerant piping is covered under the IMC (International Mechanical Code) Chapter 11 and ASHRAE 15.**

**Key requirements:**
- Refrigerant piping must be properly supported and protected from physical damage
- Piping penetrations through walls, floors, and ceilings must be sleeved and sealed
- Joints must be brazed (silver braze or phosphor-copper) for refrigerant lines. Soft solder is not acceptable
- Nitrogen must be flowing through the lines during brazing to prevent oxidation inside the pipe
- Refrigerant lines in occupied spaces must not have mechanical joints (flare fittings) except at equipment connections and service valves. Brazed joints are required in concealed spaces
- Refrigerant piping exposed to outdoor weather must be supported and protected from UV damage (insulation or paint)
- Line sizing: Suction lines must be sized for proper velocity (to carry oil back to the compressor) and minimal pressure drop. Liquid lines must be sized to prevent flash gas before the metering device. Use manufacturer's line sizing charts based on the refrigerant type, capacity, and equivalent pipe length
