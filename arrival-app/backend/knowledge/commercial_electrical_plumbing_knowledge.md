# Commercial Electrical & Plumbing Systems — Field Knowledge

This document covers commercial electrical systems (3-phase power, transformers, motor controls, lighting, fire alarm, generators, power quality, grounding, conduit) and commercial plumbing systems (backflow prevention, grease interceptors, commercial water heaters, TMVs, sump/ejector systems, medical gas, fire sprinklers, booster systems, storm drainage, gas piping). Written for field technicians working in commercial buildings.

---

## COMMERCIAL ELECTRICAL

### 3-Phase Power

Commercial buildings run on 3-phase power. Understanding the configurations is fundamental.

**208Y/120V (Wye Configuration)** — The most common service for small to mid-size commercial. Three hot legs plus a neutral, derived from a wye-wound transformer. 120V line-to-neutral on each phase (for receptacles, small loads). 208V line-to-line (for larger single-phase loads like water heaters, small RTUs). 208V 3-phase for motors, larger equipment. The "Y" means there's a neutral. Panel schedules will show 120/208V. This is NOT 240V — a 240V-rated residential appliance may not work correctly on 208V (it'll get about 75% of its rated wattage).

**480Y/277V (Wye Configuration)** — Standard for larger commercial and industrial. Three hot legs plus a neutral. 277V line-to-neutral (used for commercial lighting — fluorescent and LED fixtures). 480V line-to-line (motors, large HVAC equipment, kitchen equipment). 480V 3-phase for large motors, chillers, elevators. Step-down transformers provide 208Y/120V for receptacles and small equipment. Every commercial building over about 50,000 SF is probably 480V primary.

**240V Delta** — Three hot legs, no neutral from the transformer. 240V between any two legs. Older commercial and industrial. You can derive a neutral by center-tapping one transformer winding, giving you 120V on two legs and the infamous high-leg delta on the third.

**High-Leg Delta (Wild Leg, Red Leg)** — In a center-tapped delta system, the third phase (by convention, the B phase) reads 208V to neutral instead of 120V. This is the high leg. NEVER connect 120V loads to the B phase — you'll get 208V and smoke the equipment. NEC 408.3(E) requires the high leg to be orange and in the B (center) position in the panel. Many older buildings have this. Always check with a meter before assuming phase voltages.

### Transformer Types and Sizing

**Dry-Type Transformers** — Most common inside commercial buildings. Air-cooled, no oil. Enclosed in a ventilated metal cabinet. Typical sizes: 15, 30, 45, 75, 112.5, 150, 225, 300, 500, 750, 1000 KVA. Found in electrical rooms stepping 480V down to 208/120V for branch circuits.

**Sizing Example:** A 75 KVA 480V to 208/120V transformer. Primary full-load amps: 75,000 / (480 x 1.732) = 90.2 amps. Secondary full-load amps: 75,000 / (208 x 1.732) = 208.2 amps. Breaker sizing: primary needs at least 100A breaker (NEC 450.3), secondary main breaker sized at 225A or per design.

**Pad-Mount Transformers** — Oil-filled, sitting on a concrete pad outside. Utility-owned or customer-owned. Step down from medium voltage (4160V, 12470V, 13200V) to 480V or 208V service entrance. Locked cabinet, no user-serviceable parts (utility territory usually). Keep clear zone around them per NEC — 10 ft in front of doors minimum.

**K-Rated Transformers** — Designed to handle harmonic currents from non-linear loads (computers, VFDs, LED drivers). K-1 is standard. K-4, K-13, K-20 are increasingly harmonic-tolerant. If you're replacing a transformer in a building full of VFDs and computers, specify K-13 minimum.

### Motor Control Centers (MCCs)

An MCC is a lineup of motor starters, VFDs, and circuit breakers in a single assembly. Standard in mechanical rooms for controlling pumps, fans, compressors.

**Structure:** Vertical sections, each with horizontal drawout units (buckets). Each bucket contains a starter or breaker for one motor. NEMA 1 (indoor), NEMA 3R (outdoor, rain-tight), NEMA 12 (dust-tight).

**Typical buckets:** Combination starter (disconnect + contactor + overload relay), VFD, feeder breaker, control power transformer. Buckets can be drawn out for maintenance without de-energizing the whole MCC (on drawout type).

**Safety:** Always verify lockout/tagout before pulling buckets. Even with the bucket disconnected, the bus bars behind it are still energized at 480V. Arc flash hazard is real — check the arc flash label for PPE requirements. NFPA 70E compliance.

### Motor Starters

**Full-Voltage / Across-the-Line (ATL)** — Simplest. The contactor connects the motor directly to line voltage. Motor sees full inrush current (6-8x full-load amps typically). Fine for smaller motors. Causes voltage dips on the system for large motors.

**NEMA Starter Sizes:**
- Size 00 — up to 2 HP at 480V
- Size 0 — up to 3 HP at 480V
- Size 1 — up to 7.5 HP at 480V
- Size 2 — up to 15 HP at 480V
- Size 3 — up to 30 HP at 480V
- Size 4 — up to 60 HP at 480V
- Size 5 — up to 100 HP at 480V
- Size 6 — up to 200 HP at 480V

**Overload Protection Types:**
- Melting alloy (eutectic) — Older. Heater element melts a solder alloy to trip. Replace the heater element to match motor FLA.
- Bimetallic — Thermal strip bends with heat. Adjustable trip point. Self-resetting.
- Electronic overload relay — Best. Adjustable trip class (10, 20, 30), phase loss protection, ground fault protection. Reads actual current via CTs. Common on new installations.

**Reduced Voltage Starters:**
- Wye-Delta — Motor starts in wye (1/3 voltage), then transitions to delta. Open or closed transition. Simple, reliable. Common on large fans and pumps.
- Autotransformer — Uses taps on a transformer to apply 65% or 80% voltage during start. Smooth transition. Larger and more expensive.
- Soft Starter — Electronic, uses SCRs to gradually ramp voltage from 0 to full over a set ramp time (3-30 seconds typical). Smooth start, adjustable parameters. Good for pumps (prevents water hammer). Common brands: ABB PSE, Siemens 3RW, Eaton S811.
- VFD (Variable Frequency Drive) — The modern solution. Controls both speed and starting. Limits inrush to rated current. Infinite speed control from 0 to full speed. Saves massive energy on variable-load applications (fans, pumps). ABB, Danfoss, Yaskawa, Siemens, Eaton are the major brands.

### Commercial Lighting

**277V Lighting** — Standard for commercial fluorescent and LED fixtures. Derived from 480Y/277V service. One hot (277V) and neutral. More efficient to distribute (lower amps for same wattage). 20A circuits on 277V carry more load than 120V circuits. Ballasts and LED drivers must be 277V-rated.

**0-10V Dimming** — Most common dimming protocol for commercial LED. Two extra wires (violet and gray per convention) carry a 0-10V signal from the dimmer/controller to the driver. 10V = full bright, 0V = minimum (usually 10% — most drivers don't dim to absolute zero). Sinking protocol: the dimmer sinks current from the driver. Compatible with most commercial LED drivers. Check driver compatibility before specifying dimmer.

**Emergency and Egress Lighting** — Life safety requirement. NEC 700 (emergency systems), NEC 701 (legally required standby). Emergency lights must illuminate to 1 foot-candle average along the egress path within 10 seconds of power loss. Options:
- Battery backup packs (90-minute minimum runtime per NEC). Built into the fixture or remote battery packs.
- Generator-backed emergency circuits — separate emergency panel fed from the automatic transfer switch.
- Combo units (bug-eye lights) in stairwells, corridors, exits.
- Exit signs: LED, internally illuminated, with battery backup. Green or red depending on jurisdiction (green is becoming standard per IBC).

Monthly testing: push the test button, verify lamps illuminate. Annual testing: 90-minute full-duration test, document results. Replace batteries that fail the 90-minute test.

### Fire Alarm Systems

**FACP (Fire Alarm Control Panel)** — The brain. Receives signals from initiating devices, processes them, activates notification appliances, and communicates with monitoring station. Major brands: Notifier (Honeywell), EST (Edwards/Carrier), Simplex (Johnson Controls), Siemens, Silent Knight.

**Initiating Devices** — Things that detect fire or tell the panel there's a problem:
- Smoke detectors (photoelectric, ionization, or combination)
- Heat detectors (fixed temp at 135F or 200F, rate-of-rise)
- Duct smoke detectors (mounted in HVAC ductwork, shuts down air handler when triggered)
- Manual pull stations
- Waterflow switches (on sprinkler system — water flowing = alarm)
- Tamper switches (on sprinkler valves — someone closed a valve = supervisory)

**Notification Appliances** — Things that alert people:
- Horns and strobes (horn/strobe combos). 15/75 cd or 110 cd strobes depending on room size.
- Speakers for voice evacuation (in high-rise buildings, larger facilities)
- Visual-only appliances (strobes) required in restrooms and high-ambient-noise areas per ADA

**Conventional vs Addressable:**
- Conventional (zone-based): devices wired in zones. Panel knows which zone is in alarm but not which specific device. Simpler, cheaper. Good for small buildings.
- Addressable: each device has a unique address. Panel knows exactly which device is in alarm. Can display "Smoke Detector — 2nd Floor, Room 203." Required for larger buildings. SLC (Signaling Line Circuit) loop wiring — can be T-tapped or wired in a loop (Class A for redundant path, Class B for single path).

**Common fire alarm troubleshooting:**
- Ground fault — Somewhere in the field wiring, a conductor is touching ground. Trace with a megohmmeter. Check pull stations (water gets in), duct detectors (condensation), devices near roof leaks. Most panels will show which SLC loop or NAC circuit has the ground.
- Supervisory trouble — Tamper switch on a sprinkler valve in the wrong position. Go check the valve — someone may have shut it and not restored it.
- Duct detector trouble — Dirty sensing chamber (clean it or replace the head), wiring issue, air flow too low (fan off, filter clogged).

### Generators and Automatic Transfer Switches

**Generator Sizing:** Based on total emergency and standby load. Include motor starting KVA (larger than running KVA). Typical: diesel generator, 50-2000 kW. Natural gas generators common in smaller applications. Diesel requires fuel storage (belly tank or separate day tank with remote main tank).

**ATS (Automatic Transfer Switch)** — Monitors utility power. When utility fails (voltage drops below threshold, typically 80% of nominal), ATS signals generator to start. Generator starts and reaches rated voltage/frequency (typically 10 seconds). ATS transfers load to generator. When utility returns and is stable for a time delay (adjustable, typically 5-30 minutes), ATS transfers back to utility. Generator runs unloaded for a cooldown period (5 minutes typical), then shuts off.

**Common ATS brands:** ASCO (most common), Generac, Cummins, Russelectric, Zenith (GE).

**ATS Troubleshooting:**
- No transfer — Check utility sensing module (are the voltage-sensing connections correct?). Check control power (ATS needs its own control power, usually from a small transformer). Check generator output voltage and frequency.
- Stuck in emergency — Return-to-normal sequence not triggering. Check utility voltage at ATS input — could be a blown fuse on the sensing circuit. Check time delay settings.
- Generator won't start — Check battery voltage (12V or 24V, must be above 11.5V for 12V system). Check fuel level. Check block heater (cold engine won't start reliably). Check starting circuit: battery charger, starter motor, fuel solenoid.

**Testing:** NFPA 110 requires monthly testing under load (30% minimum) for 30 minutes. Annual 4-hour load bank test if monthly tests don't reach 30% load. Document all tests.

### Power Quality

**Harmonics** — Non-linear loads (VFDs, LED drivers, computers, UPS systems) draw current in pulses, creating harmonic currents (3rd, 5th, 7th, etc. of 60Hz). Harmonics cause transformer overheating (K-rated transformers help), neutral conductor overloading (triplen harmonics — 3rd, 9th, 15th — add on the neutral), voltage distortion, and interference with sensitive equipment. Solutions: harmonic filters (passive or active), K-rated transformers, isolation transformers, line reactors on VFDs.

**Power Factor** — Ratio of real power (kW) to apparent power (kVA). Inductive loads (motors, transformers) cause lagging power factor. Target: 0.95 or higher. Low power factor = utility penalty charges, increased current draw, wasted capacity. Correction: capacitor banks (automatic switching type). Size capacitors carefully — don't overcorrect or you get resonance with harmonic sources.

**Surge Protection** — Type 1 SPD (at service entrance), Type 2 SPD (at distribution panels), Type 3 (at point of use). All three levels recommended for a complete protection strategy. IEEE C62.41 defines surge environments.

### Commercial Grounding and Bonding (NEC 250)

The grounding system keeps people safe and provides a reference for the electrical system.

**Grounding Electrode System:** NEC 250.50 requires bonding together ALL available electrodes — metal water pipe (first 10 ft entering the building), ground rods (two rods minimum if one rod exceeds 25 ohms), concrete-encased electrode (Ufer ground — 20 ft of #4 rebar in the foundation), building steel. Total ground resistance target: 5 ohms or less for commercial. 25 ohms maximum per NEC for a single rod.

**Equipment Grounding:** Every metallic enclosure, raceway, and equipment frame must have a continuous path back to the service entrance bonding jumper. Green wire, bare copper, or the raceway itself (if qualified — EMT, RMC, IMC are equipment grounding conductors per NEC 250.118). Metal piping systems: bond per NEC 250.104.

**Separately Derived Systems:** Transformers create a new neutral-to-ground bond at the transformer secondary. NEC 250.30 — bond the secondary neutral to ground and the transformer frame at the transformer location. Only ONE neutral-ground bond per separately derived system. Multiple bonds cause circulating currents on the ground path.

### Conduit and Wire Sizing for Commercial

**Common conduit types:**
- EMT (Electrical Metallic Tubing) — Thin wall, set-screw or compression fittings. Most common for interior commercial. Easy to bend and work with. Not approved for direct burial.
- RMC (Rigid Metal Conduit) — Thick wall, threaded. For exposed exterior, mechanical rooms where physical protection is needed. Heavy, expensive.
- IMC (Intermediate Metal Conduit) — Between EMT and RMC in wall thickness. Threaded. Lighter than rigid.
- PVC (Schedule 40 or 80) — Underground, concrete-encased, corrosive environments. Needs an equipment grounding conductor inside (PVC is not a ground path). Expansion fittings for long runs.
- MC Cable (Metal-Clad) — Factory assembly, armored cable. Fast to install for branch circuits and feeders. Allowed in commercial above ceiling with proper support (NEC 330).
- Flexible Metal Conduit (Greenfield) and Liquidtight — For connections to vibrating equipment (motors, compressors). 6-foot max for equipment grounding path (NEC 250.118), then you need a bonding jumper.

**Wire sizing considerations:** Voltage drop is the big one on long runs. NEC recommends no more than 3% voltage drop on branch circuits, 5% total (feeder + branch). At 480V, 3% = 14.4V. Calculate using: VD = (2 x K x I x D) / CM, where K = 12.9 for copper, I = amps, D = distance in feet, CM = circular mils. Bump up wire size for long feeders — going from #10 to #8 costs a few dollars per foot but can save hundreds in energy over the building's life.

**Conduit fill:** NEC Chapter 9, Table 1. One wire = 53% fill. Two wires = 31%. Three or more = 40%. Use Table 4 and Table 5 for actual wire and conduit areas. Over 3 current-carrying conductors in a conduit: derate per NEC 310.15(C)(1). More than 30 conductors = 40% derating. Plan large pull boxes and avoid excessive bends (360 degrees maximum between pull points).

---

## COMMERCIAL PLUMBING

### Backflow Prevention

Backflow prevention protects the potable water supply from contamination. Required by code anywhere there's a cross-connection risk.

**Types of Backflow Preventers:**

**RPZ (Reduced Pressure Zone Assembly)** — Highest level of protection for continuous pressure. Two check valves with a relief valve between them. If either check fails, the relief valve opens and dumps water (designed to fail safely). Required for high-hazard connections: boiler makeup, cooling tower makeup, fire sprinkler systems with chemical additives, medical facilities, car washes. Typical sizes: 3/4" to 10". Big ones (4"+) weigh hundreds of pounds — plan your rigging. Must be installed horizontally, 12-36" above floor (accessible for testing), with adequate drainage for the relief valve discharge.

**DCVA (Double Check Valve Assembly)** — Two check valves in series. No relief valve. For low-to-moderate hazard: fire sprinkler systems (no chemicals), irrigation (non-reclaimed), commercial kitchen supply. Cannot be used for high-hazard connections. Can be installed vertically on some models. Less expensive and smaller than RPZ.

**PVB (Pressure Vacuum Breaker)** — Single check valve with an atmospheric vent. Must be installed 12" above the highest downstream outlet. Only for non-continuous pressure applications: irrigation is the most common use. Cannot handle backpressure — only backsiphonage. Simpler and cheaper.

**Annual Testing** — All testable backflow assemblies must be tested annually by a certified tester. Many jurisdictions require reporting to the water authority. Tests verify check valves hold at specified pressures and relief valve opens when required. RPZ: first check must hold 5 PSI minimum, relief valve must open before 2 PSI differential. DCVA: both checks must hold tight at 1 PSI minimum. Document everything — test reports, serial numbers, installation dates.

### Grease Interceptors

**Sizing** — Based on flow rate (GPM) and retention time. UPC method: GPM = number of fixture units draining to the interceptor, cross-referenced with a sizing table. Most jurisdictions use the PDI (Plumbing and Drainage Institute) rating. Small (under-counter) units: 20-50 GPM. Large (in-ground) vaults: 500-2000+ GPM. Size for the worst case — a restaurant with multiple sinks, dishwashers, and floor drains all connecting.

**Maintenance Schedule:**
- Under-counter (hydromechanical): clean out weekly to monthly depending on volume. Remove solidified grease from the baffles and compartments.
- In-ground (gravity): pump out when the grease layer reaches 25% of the liquid depth. Typically monthly for busy restaurants, quarterly for lighter use. Hire a licensed waste hauler with a vacuum truck. Document all cleanings — health departments inspect records.

**Monitoring:** Some jurisdictions require automatic grease monitoring (sensors that measure grease layer thickness and alert when pumping is needed). Required in larger installations and chains.

**Installation Tips:** Install as close to the source fixtures as possible. Dishwashers should NOT drain through the grease interceptor if water temp exceeds 140F (melts grease, passes it through). Separate the dishwasher drain. Floor sinks with grease-rated strainer baskets. Sampling tee downstream for FOG (fats, oil, grease) testing.

### Commercial Water Heaters

**Storage Type** — Large tanks (50-120 gallon commercial, up to 500+ gallon for large buildings). Gas or electric. First-hour rating matters more than tank size. A.O. Smith, Bradford White, Rheem commercial models. ASME-rated tanks for larger installations (over 120 gallons or over 200,000 BTU). Relief valve piped to safe discharge point (within 6" of floor or to drain). Temperature setpoint: 140F storage minimum (Legionella prevention — ASHRAE 188 recommendation), delivered at 120F to fixtures via TMV.

**Tankless Banks** — Multiple tankless units in parallel for commercial demand. Common with Rinnai, Navien, Noritz commercial units. Primary/secondary piping with a buffer tank (40-80 gallons) smooths out demand spikes and prevents short cycling. Flow sensors in each unit must be coordinated. Total flow rate = sum of individual units minus a diversity factor. Manifold the cold water in and hot water out with reverse-return headers for balanced flow.

**Booster Heaters** — Small point-of-use heaters that boost temperature for specific applications. Commercial dishwashers require 180F final rinse water (per health code). Incoming hot water at 140F + booster raises it to 180F. Electric (6-18 kW typical), installed right at the dishwasher. Hatco, Hubbell, and dishwasher OEMs (Hobart) make these. Size based on dishwasher GPM and temperature rise needed.

**Recirculation Systems:** Commercial hot water systems need recirculation to deliver hot water quickly to fixtures far from the heater. Recirc pump runs on a timer or aquastat (activates when return water drops below 110F). Pipe the return line back to the bottom of the tank or to a recirculation inlet. Balancing valves on branch returns to prevent short-circuiting. Insulate all hot water and recirc piping — energy code requirement and reduces heat loss.

### Thermostatic Mixing Valves (TMVs)

**ASSE 1017 Standard** — Governs TMVs for hot water distribution systems. These valves mix hot water (stored at 140F+ for Legionella control) with cold water to deliver a safe, controlled temperature (typically 110-120F) to fixtures.

**Installation:** Installed at the water heater outlet or at branch points serving groups of fixtures. Set outlet temperature to 120F for general use, 110F max for accessible fixtures and healthcare per ADA and plumbing code. Must have check valves on both hot and cold inlets (to prevent crossover if one supply pressure changes). Strainers on both inlets. Unions for serviceability.

**Brands:** Leonard, Powers (Watts), Lawler, Bradley, Caleffi. Size based on flow rate — each valve has a rated GPM range.

**Troubleshooting:**
- Wide temperature swings — Check inlet pressures (should be within 2:1 ratio hot to cold). Check for clogged strainers. Worn internal spool/element. Oversized valve (valve hunting at low flows).
- No hot water at fixtures — TMV failed closed on hot side (safety failure mode). Check that hot water supply to the valve is actually hot.
- Scalding water — TMV failed or set too high. Verify with a thermometer at the nearest fixture. Check setpoint, replace valve if it's not controlling.

### Sump and Sewage Ejector Systems

For fixtures below the sewer main (basement restrooms, locker rooms, kitchens).

**Duplex Pump Systems** — Two pumps in one basin, alternating operation. Lead pump handles normal flow. Lag pump kicks in for high demand. Both run for alarm-level high water. If both fail, alarm activates (building management notified). Common brands: Liberty, Zoeller, Myers, Grundfos.

**Float Controls:**
- Off float — both pumps stop (basin drains to this level)
- Lead pump on float — first pump starts
- Lag pump on float — second pump starts (high demand or lead pump failure)
- High water alarm float — alarm activates (buzzer, light, BAS alarm)

Floats can be tethered or vertical (vertical for smaller basins). Mercury floats being phased out in favor of mechanical or electronic level sensors.

**Maintenance:**
- Inspect and test quarterly minimum. Run each pump manually.
- Check float operation — pour water in to verify activation levels.
- Clean basin annually — remove debris, grease, solids. Sewage basins are confined spaces — follow OSHA confined space procedures.
- Check valve on each discharge — prevents backflow into basin when pump shuts off. Listen for check valve slam (water hammer) — may need a silent check or swing check with dashpot.
- Test high water alarm — critical life safety for occupied basements.

### Medical Gas Systems (Coordination)

As an HVAC/plumbing tech you won't install medical gas but you need to know it exists for coordination.

**Types:** Oxygen (green), medical air (yellow), vacuum (white), nitrous oxide (blue), nitrogen (black), WAGD (waste anesthetic gas disposal, violet). All per NFPA 99 and CGA standards.

**Key coordination points:**
- Medical gas piping is brazed copper — no flux inside the joint (use nitrogen purge). Only certified medical gas installers.
- Source equipment (compressors, vacuum pumps, manifolds) needs dedicated mechanical rooms with proper ventilation.
- Zone valve boxes (ZVBs) at nursing station walls allow shutoff of individual zones during maintenance.
- Alarm panels in multiple locations (master alarm, area alarm, local alarm). Tie into BAS for monitoring.
- Don't run medical gas piping in the same chase with fuel gas, drain lines, or electrical above 50V.

### Fire Sprinkler Systems (Coordination)

Again, a specialized trade, but HVAC and plumbing techs need to know the basics.

**Wet System** — Pipes are filled with pressurized water at all times. Sprinkler head activates when heat melts the fusible link (usually 155F or 200F rated). Water flows immediately. Most common. Antifreeze systems for areas subject to light freezing (NEC/NFPA restrictions now tighter on antifreeze — glycerin or propylene glycol solutions only, concentration limits).

**Dry System** — Pipes are filled with pressurized air or nitrogen. When a head activates, air escapes, dry pipe valve opens, and water fills the system. Delay of 30-60 seconds before water reaches the head. Used in unheated spaces: parking garages, loading docks, attics. Air compressor maintains system pressure. Check air pressure quarterly — should be about 20 PSI above trip pressure of the dry valve.

**Pre-Action System** — Dry system that requires TWO events to discharge: a detection device (smoke or heat detector) activates to open the pre-action valve AND a sprinkler head must fuse. Provides extra protection against accidental discharge. Used in data centers, telecom rooms, museums, archives — places where water damage from accidental discharge is unacceptable.

**Deluge System** — All heads are open (no fusible link). A detection system activates the deluge valve, flooding all heads simultaneously. Used for high-hazard areas: chemical storage, aircraft hangars, flammable liquid areas. Massive water flow.

**Coordination points:**
- Tamper switches on all control valves — wired to fire alarm panel.
- Waterflow switches — detect when water is flowing through the system (alarm condition).
- Inspector's test valve at the hydraulically remote point.
- FDC (Fire Department Connection) on the building exterior — firefighters pump supplemental water into the system.
- Don't hang anything from sprinkler piping. Maintain 18" clearance below sprinkler heads (storage, shelving, nothing closer than 18" per NFPA 13).

### Domestic Water Booster Systems

Buildings taller than about 4-5 stories often need booster pumps for adequate water pressure on upper floors.

**System components:** Variable speed booster pumps (2-4 pumps in parallel), pressure transducer on the discharge header, VFDs on each pump, expansion tank, check valves, isolation valves.

**Control:** Maintain constant discharge pressure regardless of demand changes. VFDs ramp pump speed to match demand. Lead/lag staging: one pump runs at variable speed. When demand exceeds one pump's capacity, the second pump starts. Pumps alternate lead/lag for equal wear.

**Common brands:** Grundfos Hydro MPC, Xylem (Bell & Gossett) e-HydroVar, Wilo, Armstrong.

**Sizing:** Calculate required pressure at the highest fixture (20 PSI minimum at the fixture per code) plus pipe friction loss plus elevation (0.433 PSI per foot of elevation). Subtract incoming city pressure. The difference is what the booster must provide.

**Maintenance:** Check pressure transducer calibration quarterly. Inspect expansion tank pre-charge annually (should match system operating pressure when empty). Listen for unusual pump noise (cavitation, bearing wear). Check VFD for fault codes.

### Storm Water and Roof Drain Systems

Commercial flat roofs need primary and secondary (overflow) drain systems.

**Primary drains:** Sized per code (IPC/UPC) based on rainfall rate (inches per hour for the geographic area), roof area, and number of drains. Typically 4" to 8" roof drains. Connected to the storm sewer (separate from the sanitary sewer). Drain bodies are set flush with the roof membrane with clamping rings. Strainer domes prevent debris from clogging the drain. Clean strainers regularly — a clogged roof drain leads to ponding water and potential roof collapse.

**Secondary (overflow) drains:** Required by code as a safety backup. Set 2" above the primary drain level. If primary clogs, water rises to the secondary level and drains through a separate overflow system. Secondary system typically drains to grade (daylight) on the building exterior so the building owner can SEE water flowing — visual indication that the primary drain has failed.

**Sizing rule:** Each roof drain can typically handle 1-2 square inches of drain opening per 100 SF of roof area, but use local code rainfall rates for exact sizing. A 4" drain handles about 4600 SF at 2" per hour rainfall. A 6" handles about 10,200 SF.

**Scupper drains:** An alternative secondary drainage method. Openings in the parapet wall at the overflow level. Simple, no piping. Water pours off the roof through the scupper. Set the scupper invert 2" above the primary drain level.

**Maintenance:** Inspect roof drains at least twice per year (spring and fall). Remove debris from strainers. Check secondary drains — they should be dry normally; evidence of water means primary is partially or fully blocked.

### Commercial Gas Piping

Larger buildings need larger gas piping with more complex regulation.

**Pipe Sizing:** Based on total connected BTU load, pipe length, allowable pressure drop, and specific gravity of the gas. Use the Longest Length Method per IFC/IFGC tables. Natural gas at standard pressure (under 2 PSI): black steel pipe with threaded or welded fittings. Size every segment from the meter to the appliance. Example: 500,000 BTU boiler at 100 ft from the meter, 0.5" WC pressure drop allowed = 2" pipe (check the specific table — pipe sizing tables are in the gas code and depend on inlet pressure and drop).

**Regulators:**
- Service regulator: utility installs at the meter, drops from distribution pressure (60+ PSI) to 2 PSI or less for building distribution.
- Building regulator: may step down from 2 PSI to 7" WC for standard-pressure appliances.
- Appliance regulators: some equipment has its own built-in regulator. Check inlet pressure requirements — most standard equipment wants 7-14" WC. High-pressure equipment (some commercial kitchen, industrial burners) operates at 2 PSI.

**PRVs and Relief:** Over-pressure protection downstream of each regulator. Spring-loaded relief valve sized for the regulator's lock-up failure capacity. Vented to outdoors.

**Testing:** New gas piping is pressure tested before use. Typical: 3 PSI air test for 15 minutes minimum with no pressure drop (for systems under 14" WC operating pressure). Higher-pressure systems require higher test pressures per code. Use a manometer for accuracy, not just a gauge. Document the test.

**Safety:**
- Drip legs at every appliance connection and at low points (collects moisture and debris).
- Manual shutoff at each appliance within 6 ft. Lever-handle ball valves — yellow handle indicates gas.
- Earthquake shutoff valves where required (seismic zones).
- Gas detector/alarm in mechanical rooms (required by some codes, recommended everywhere).
- Pipe support: every 10 ft for 1" and smaller, every 12 ft for 1-1/4" and larger. Use proper pipe hangers rated for the size and weight.
- Bonding: CSST (corrugated stainless steel tubing) must be bonded per manufacturer requirements and NEC. Inadequate bonding leads to lightning-related fires.

### Backflow Testing Procedures

**What the tester does (overview for coordination):**

1. Notify the building — water will be shut off during the test.
2. Close downstream shutoff to isolate the assembly.
3. Connect test kit (differential pressure gauge) to the test cocks on the backflow preventer.
4. Test #1 (RPZ): Check first check valve — close #2 test cock, open #1, measure differential pressure. Should hold at least 5 PSI.
5. Test #2 (RPZ): Check relief valve opening point — should open before the differential drops to 2 PSI.
6. Test #3: Check second check valve — should hold tight.
7. For DCVA: Test both check valves, both should hold at 1 PSI minimum.
8. Record all readings on the test report form.
9. If the assembly fails, repair (replace check valve disc, clean seats, replace relief valve) and retest.
10. Submit the test report to the local water authority.

**Important:** During RPZ testing, the relief valve WILL dump water. Plan for drainage. In a mechanical room, have a floor drain nearby or buckets. Some large RPZs dump significant volume — 4" RPZ relief can discharge 100+ GPM momentarily.
