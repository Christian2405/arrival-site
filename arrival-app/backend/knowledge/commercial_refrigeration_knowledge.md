# Commercial Refrigeration Expert Diagnostic Knowledge

## Commercial Refrigeration Fundamentals

### Walk-In Coolers and Freezers

A walk-in is just a big insulated box with a refrigeration system bolted to it, but the scale changes everything. The box itself is made of foam-core insulated panels -- typically 4 inches thick for coolers (R-25 to R-28) and 5-6 inches thick for freezers (R-32 to R-38). The panels interlock with cam-lock fasteners and the joints are sealed with silicone caulk and sometimes metal flashing.

**Walk-in cooler typical conditions:** Box temperature 35-38°F. Evaporator coil temperature approximately 20-25°F (10-15°F below box temp). Condensing temperature approximately 105-115°F on air-cooled systems in summer.

**Walk-in freezer typical conditions:** Box temperature -10°F to 0°F. Evaporator coil temperature approximately -20°F to -25°F. Condensing temperature approximately 105-115°F on air-cooled systems. Suction pressure on R-404A at -20°F evaporator is approximately 18 PSIG.

The biggest mistake I see on walk-in installations is undersized refrigeration. A walk-in cooler might need 8,000 BTU/hr for the box load, but if you add product load (a restaurant pulling cases of warm produce in daily), door openings (busy kitchen -- the door is open 2-3 hours per day total), and infiltration, the actual load can be 15,000-20,000 BTU/hr. Always calculate the full load -- do not just match the box size to a manufacturer's quick-select chart.

### Reach-In Units

Reach-in refrigerators and freezers (the glass-door units in convenience stores, the solid-door units in restaurant kitchens) are self-contained systems. The compressor, condenser, evaporator, and controls are all built into the unit. Most use capillary tube metering devices, though higher-end commercial units use TXVs.

**Common reach-in issues:**
- Condenser coil fouling -- these units are often in hot, greasy kitchen environments. The condenser (usually underneath) gets caked with grease and dust. A dirty condenser raises head pressure, reduces capacity, and burns out compressors. Clean condensers quarterly in restaurant environments, monthly in bakeries or areas with flour dust
- Fan motor failures -- both evaporator and condenser fan motors. The condenser fan motor runs in a hot environment near the compressor and fails more frequently. ECM fan motors are becoming common on newer units and are significantly more expensive to replace
- Door gasket failures -- torn, compressed, or loose gaskets let warm moist air in, causing frost buildup, elevated temperatures, and compressor overwork. The dollar-bill test: close the door on a dollar bill and try to pull it out. You should feel moderate resistance all the way around the door. If the bill slides out easily at any point, the gasket is not sealing

### Prep Tables (Sandwich/Pizza Prep)

Prep tables are refrigerated units with a cutting board top and refrigerated well for food pans. They are one of the most service-intensive pieces of commercial refrigeration because the top is open to the kitchen environment, food spillage gets into the refrigeration components, and the compressor is usually crammed into a small space underneath.

**Common prep table problems:**
- The refrigerated top well does not hold temperature -- usually caused by overloading the pans, leaving the lid open, or a failed fan that should circulate cold air up into the well
- Compressor overheating due to poor airflow under the unit -- make sure the condenser has clearance and the kitchen floor is not pushed up against the condenser intake
- Drain line clogs from food particles and condensation

## Compressor Diagnostics

### Copeland Scroll Compressors

Copeland Scroll compressors are the workhorses of commercial refrigeration. They use two spiral-shaped scrolls -- one stationary (fixed scroll) and one orbiting -- to compress refrigerant. The scrolls do not actually rotate against each other; the orbiting scroll wobbles in a precise pattern that creates progressively smaller pockets of gas, compressing it.

**Key diagnostic points:**

**Amp draw analysis:** Measure amp draw on the common wire and compare to the nameplate RLA (Rated Load Amps). A healthy compressor running at design conditions draws within 10% of RLA. Important: scroll compressors have different amp draw characteristics than reciprocating compressors.
- High amps (above RLA): High head pressure (dirty condenser, overcharge, non-condensables), high suction pressure (overfeeding TXV, high load), or mechanical issue
- Low amps (below 70% of RLA): Low charge, restriction, or low load condition
- LRA (Locked Rotor Amps): If the compressor draws LRA and trips on the protector, suspect a mechanical seizure, locked scroll, or single-phasing on three-phase units

**Scroll compressor rotation:** Scroll compressors must rotate in the correct direction. If wired backwards on a three-phase system, the scrolls will spin in reverse and the compressor will not pump -- it will run, draw near-normal amps, but suction and discharge pressures will equalize. The compressor will also be noticeably louder than normal. Swap any two of the three power leads to correct rotation.

**Oil level checking:** On semi-hermetic compressors with a sight glass, the oil level should be between 1/4 and 3/4 of the sight glass during running conditions. Oil level drops when oil is logging in the evaporator or suction line. Oil level rises when refrigerant is migrating to the crankcase during the off cycle (liquid slugging risk on startup). On hermetic compressors without a sight glass, you cannot directly check oil level -- you diagnose oil problems by symptoms (compressor noise, elevated temperature, repeated protector trips).

### Semi-Hermetic Compressors

Semi-hermetic compressors (Copeland Discus, Bitzer, Carlyle) can be opened in the field for valve plate replacement, head gasket replacement, and internal inspection. This is a dying skill but still valuable for large systems where compressor replacement is extremely expensive.

**Valve plate diagnosis:** A leaking suction valve or discharge valve reduces compressor efficiency. Symptoms: the compressor runs but capacity is reduced, suction pressure is higher than expected, discharge pressure is lower than expected, and the compressor runs longer. You can confirm by performing a pump-down test: close the liquid line service valve (king valve) and let the compressor pump down the low side. A healthy compressor should pull the suction pressure down to 0-2 PSIG within a few minutes. If the suction pressure stalls at a high reading (above 10 PSIG) and will not come down, the valves are leaking internally.

**Oil pressure:** Semi-hermetic compressors with a forced-oil lubrication system have an oil pressure safety switch. Net oil pressure (oil pump pressure minus crankcase/suction pressure) should be 30-60 PSI. If net oil pressure drops below 9-12 PSI for 90-120 seconds, the oil pressure safety trips and locks out the compressor. Common causes: low oil level, worn oil pump, diluted oil (refrigerant in the oil), or a plugged oil filter.

### Copeland CoreSense Diagnostics

Copeland CoreSense protection modules are built into many newer Copeland scroll compressors. The module monitors discharge temperature, suction temperature, current, voltage, and compressor contactor status. It communicates through LED flash codes on the module and through optional BACnet or Modbus communication.

**Flash code reference:**
- **1 flash:** High discharge temperature -- the discharge line temperature has exceeded the safe limit (typically 250-275°F). Causes: low charge, high superheat, restricted condenser, non-condensables, high compression ratio
- **2 flashes:** Low suction superheat -- the compressor is receiving liquid or near-liquid refrigerant. Causes: overcharged system, overfeeding TXV/EEV, low load condition, short-cycling
- **3 flashes:** Protector trip -- the internal overload protector has opened due to high motor temperature or high current. Causes: low voltage, high amp draw, poor motor cooling (loss of suction gas), locked rotor
- **4 flashes:** Contactor issue -- the module detects that the contactor is cycling abnormally (chattering) or that there is a voltage imbalance across phases
- **5 flashes:** High current -- current has exceeded the module's threshold but the internal protector has not yet tripped
- **6 flashes:** Low voltage -- supply voltage has dropped below the acceptable range
- **Steady on:** Normal operation, no faults

## Evaporator and Condenser Coil Maintenance

### Evaporator Coils

Commercial evaporator coils in walk-ins, reach-ins, and display cases accumulate frost during normal operation. The defrost system melts this frost periodically. But between defrosts, the coil condition directly affects system performance.

**Diagnosis of coil problems:**
- Frost pattern: A healthy evaporator should frost evenly across the entire coil surface during operation. If frost is concentrated on the first few rows (inlet side) and the rest of the coil is warm, the system is low on charge or the TXV is underfeeding. If the entire coil including the suction line is frosted solid back to the compressor, the metering device is overfeeding or stuck open
- Air temperature split: Measure the air temperature entering and leaving the coil. The split should be 8-12°F for cooler applications and 10-15°F for freezer applications. A low split means reduced capacity (dirty coil, low airflow, low charge). A high split means reduced airflow (frost buildup, failed fan motor, blocked coil)
- Coil cleaning: In kitchen environments, evaporator coils accumulate grease, dust, and food particles. Clean with a commercial coil cleaner designed for evaporators (not the same as condenser coil cleaner). Spray the cleaner on, let it foam and penetrate for 10-15 minutes, then rinse with low-pressure water. High-pressure water can damage the aluminum fins

### Condenser Coils

**Air-cooled condensers** must reject all the heat absorbed by the evaporator plus the heat of compression. The condenser must be clean and have adequate airflow. Target condensing temperature is 15-25°F above ambient air temperature for air-cooled condensers. If the condensing temperature is more than 30°F above ambient, the condenser is fouled or airflow is restricted.

**Cleaning frequency:**
- Restaurant kitchens: Monthly
- Grocery stores: Quarterly
- Clean environments (warehouse, walk-in only): Semi-annually
- Use a commercial coil cleaner and a garden hose. Rinse from the clean side (air exit side) to push debris out the same way it came in. Never use a pressure washer -- it will flatten the fins and reduce airflow

## TXV and EEV Diagnosis

### Thermostatic Expansion Valve (TXV)

The TXV regulates refrigerant flow into the evaporator to maintain a target superheat at the evaporator outlet. The sensing bulb, clamped to the suction line at the evaporator outlet, controls the valve opening.

**Normal TXV operation:** The TXV maintains 8-12°F superheat at the evaporator outlet. If superheat is too high (above 15°F), the valve is underfeeding -- either the valve is undersized, the sensing bulb has lost its charge, or there is a restriction upstream of the valve (clogged filter drier, kinked liquid line). If superheat is too low (below 5°F), the valve is overfeeding -- the valve is oversized, the sensing bulb is improperly mounted, or there is a high load condition.

**Sensing bulb placement:** The bulb must be clamped tightly to a clean section of the suction line at the evaporator outlet, insulated from ambient air. On suction lines 7/8 inch and smaller, mount the bulb at the 12 o'clock position (top of the pipe). On lines larger than 7/8 inch, mount at the 4 or 8 o'clock position to avoid the oil film at the bottom of the pipe. A poorly mounted sensing bulb causes erratic superheat control.

**TXV hunting:** If the TXV oscillates between overfeeding and underfeeding (superheat swings wildly from 2°F to 25°F and back), the valve is hunting. Causes: oversized valve, liquid line pressure drop (valve sees varying inlet pressure), sensing bulb issue, or low load condition.

### Electronic Expansion Valve (EEV)

EEVs are increasingly common in commercial refrigeration. They offer tighter superheat control (5-8°F subcooling target, 5-10°F superheat at evaporator) and can modulate capacity to match varying loads. The EEV is controlled by a stepper motor or pulse-width-modulated solenoid, driven by a controller that reads suction and liquid line temperature sensors and pressure transducers.

**Diagnosis:** Check the controller display or LED status. Verify that the temperature sensors are reading correctly (compare to a thermocouple). Verify that the pressure transducers are accurate (compare to gauge readings). If the EEV is fully open and superheat is still high, the system is low on charge or has a restriction. If the EEV is at minimum steps and superheat is still low, the system is overcharged or the valve is leaking through.

## Superheat and Subcooling Targets for Commercial Equipment

**Walk-in coolers (R-404A, TXV):**
- Evaporator superheat: 6-10°F
- Subcooling at condenser outlet: 8-12°F
- Suction pressure at 25°F evaporator: approximately 40 PSIG (R-404A)

**Walk-in freezers (R-404A, TXV):**
- Evaporator superheat: 6-10°F
- Subcooling at condenser outlet: 8-12°F
- Suction pressure at -20°F evaporator: approximately 18 PSIG (R-404A)

**Reach-in coolers (R-404A or R-134a, cap tube):**
- Superheat at compressor: 10-20°F (cap tube systems run higher superheat)
- If R-134a: suction pressure at 25°F evaporator approximately 18 PSIG

**Display cases (R-404A, TXV or EEV):**
- Evaporator superheat: 5-8°F (EEV)
- Subcooling: 5-10°F

## Defrost Systems

### Electric Defrost

Most common in walk-in coolers and freezers. Calrod-type heaters are attached to the evaporator coil and drain pan. A defrost timer or controller energizes the heaters for 15-30 minutes per defrost cycle, typically 2-4 times per day for coolers and 4-6 times per day for freezers.

**Diagnosis:** Check heater resistance -- a typical defrost heater bank reads 8-30 ohms depending on the number and wattage of heaters. Infinite ohms means an open heater element. Check the defrost termination thermostat -- it should be closed at evaporator temperatures below 45-55°F and open above that temperature. The termination thermostat prevents the evaporator from getting too warm during defrost. If the termination thermostat is failed open (stuck open), the heaters will never energize during defrost. If failed closed (stuck closed), the heaters will run the full timer duration regardless of coil temperature, wasting energy and potentially overheating the evaporator area.

**Drain pan heater:** Freezer evaporators have a drain pan heater (separate from the coil heaters) that prevents defrost water from refreezing in the drain pan and drain line. If the drain pan heater fails, ice builds up in the pan, blocks the drain, and eventually the ice grows up into the coil. This is a very common walk-in freezer problem -- ice buildup on the coil that keeps coming back after manual defrost. Check the drain pan heater first.

### Hot Gas Defrost

Used on larger commercial systems, particularly supermarket rack systems. A solenoid valve diverts hot discharge gas from the compressor directly into the evaporator coil, using the heat of compression to melt frost. Hot gas defrost is faster and more energy-efficient than electric defrost because you are using waste heat that would otherwise be rejected by the condenser.

**Key components:** Hot gas solenoid valve, check valve (prevents liquid refrigerant from flowing backward during normal operation), pressure regulator (limits evaporator pressure during defrost to prevent coil damage), and defrost termination thermostat.

**Diagnosis:** If the coil is not defrosting, verify the hot gas solenoid is energizing (listen for the click, check the coil for 24VAC or 120VAC depending on the system). Check the solenoid valve -- a stuck-closed valve will prevent hot gas from reaching the evaporator. A stuck-open valve will allow hot gas into the evaporator during normal operation, causing high suction pressure and poor cooling.

### Off-Cycle Defrost

Used on walk-in coolers and medium-temperature applications where the evaporator temperature is above 32°F during operation. The compressor cycles off, and the warm air in the box (35-38°F) naturally melts any frost on the coil. This works because the coil temperature during operation (20-25°F) is below freezing but the box temperature is above freezing. Off-cycle defrost requires no heaters and no additional energy -- it is the simplest and most efficient defrost method when applicable.

## Ice Machine Diagnostics

### Hoshizaki Ice Machines

Hoshizaki machines use an innovative individual-cell evaporator design where water flows over a flat plate with individual cells. Ice forms in each cell during the freeze cycle, then hot gas from the compressor is briefly passed through the evaporator to release the ice cubes, which fall into the bin. Hoshizaki machines are known for producing clear, hard, slow-melting cubes.

**Long harvest cycle:** The ice does not release from the evaporator within the normal harvest time (typically 2-5 minutes). Causes: low hot gas pressure (low charge, weak compressor), scale buildup on the evaporator plate (minerals in the water insulate the ice from the hot gas), or a failing hot gas valve. Check the harvest: hot gas solenoid should be energized, and you should feel the evaporator plate warm up quickly. If the plate stays cold during harvest, the hot gas is not flowing -- check the solenoid valve and the charge.

**Short freeze cycle:** The machine enters harvest before the ice is fully formed. Causes: the thickness control sensor is misfiring or positioned incorrectly. On Hoshizaki, the thickness sensor is a probe that contacts the ice surface. When ice grows thick enough to touch the probe, the board initiates harvest. If the probe is bent inward or water is bridging to it, it triggers premature harvest. Also check water distribution -- if water is not flowing evenly across the evaporator plate, some cells fill before others.

**No water:** The water inlet valve does not open, or the water pump does not run. Check the inlet valve solenoid (24VAC should be present when calling for water, valve resistance 200-500 ohms). Check the water pump -- it should run during the freeze cycle to circulate water over the evaporator plate. If the pump hums but does not spin, the impeller may be jammed with scale. Remove and clean.

### Manitowoc Ice Machines

Manitowoc machines use a vertical evaporator with water flowing down the surface. They are common in restaurants and hotels.

**Common Manitowoc issues:**
- Water curtain problems: The water curtain distributes water evenly across the evaporator surface. If the curtain holes are clogged with scale, water distribution is uneven, producing thin or partial cubes on some areas and thick cubes on others. Clean the curtain with a descaling solution
- Harvest assist: Manitowoc uses a combination of hot gas and a mechanical water release (water runs over the back of the evaporator to help release cubes). If the harvest water solenoid fails, cubes hang on the evaporator and do not drop into the bin
- Long freeze or long harvest codes on the Indigo series display usually indicate a water quality or scale buildup issue. Run a cleaning cycle with approved descaler

## Walk-In Common Issues

### Door Seals and Gaskets

Walk-in door gaskets take more abuse than any other gasket in commercial refrigeration because the doors are opened dozens of times per day by staff in a hurry. A torn or compressed gasket allows warm, humid air to infiltrate the box, causing frost buildup on the evaporator, elevated box temperatures, and increased energy consumption.

**Testing:** Close the door on a piece of paper or a dollar bill at multiple points around the perimeter. If you can pull the paper out easily at any point, the gasket is not sealing. Also check the door closer and the door hinges -- if the door does not close and seal completely on its own, the gasket cannot do its job.

**Heater wire (anti-sweat heaters):** Walk-in cooler and freezer door frames have heater wire embedded in the frame perimeter. This heater prevents condensation and ice from forming on the door frame and gasket surface, which would freeze the door shut and destroy the gasket. If the heater wire fails, you will see ice forming on the door frame and the gasket will tear when the door is opened. Test the heater circuit for continuity and correct voltage. Typical heater wire draws 2-8 watts per linear foot. On a standard walk-in door, the heater circuit should draw approximately 0.5-2.0 amps at 120VAC or 208VAC.

### Evaporator Fan Motors

Walk-in evaporator units typically have 2-4 fan motors that pull air through the coil and circulate it through the box. These motors run in cold, moist environments and fail regularly.

**Common failures:** Seized bearings (motor hums but does not spin), failed winding (motor is dead, no hum), or failed capacitor (on PSC motors -- motor hums, tries to start but cannot). Shaded-pole motors (the most common type in smaller evaporator units) do not have capacitors and are less efficient but simpler.

**When replacing fan motors:** Match the shaft diameter, shaft length, rotation direction, mounting style, speed (RPM), and wattage. Using a motor with the wrong wattage or speed changes the airflow through the coil and affects system performance. Evaporator fan motor wattage ratings commonly range from 6 watts (small reach-in) to 35 watts (large walk-in).

### Liquid Line Solenoid Valves

The liquid line solenoid is a normally-closed valve in the liquid line that shuts off refrigerant flow when the system is not calling for cooling. On pump-down systems (the standard control scheme for commercial refrigeration), the thermostat controls the solenoid, not the compressor directly. When the thermostat is satisfied, the solenoid closes, the compressor pumps down the low side, the low-pressure switch opens and stops the compressor. When the thermostat calls for cooling, the solenoid opens, liquid refrigerant flows to the evaporator, suction pressure rises, the low-pressure switch closes, and the compressor starts.

**Solenoid valve diagnosis:** If the compressor short-cycles on the low-pressure switch, the solenoid may be leaking through (passing refrigerant when it should be closed). Front-seat the liquid line service valve and watch the suction pressure -- if it rises, refrigerant is leaking through the solenoid. Replace the valve or the coil. If the system will not cool and the compressor does not start, the solenoid may be stuck closed or the coil may be burned out. Check for voltage at the coil (24VAC or 120VAC depending on the system). Measure coil resistance -- a good coil reads 20-100 ohms depending on the voltage rating. Open (infinite ohms) means the coil is burned out.

## Commercial Refrigerant Types

### R-404A

The dominant commercial refrigeration refrigerant for the past 20+ years. R-404A is a near-azeotropic blend (R-125/143a/134a at 44/52/4%) with a GWP of 3922. It is being phased down under the AIM Act and Kigali Amendment, but it is still widely used in existing equipment. R-404A operates at relatively high pressures -- about 260 PSIG discharge pressure at 110°F condensing temperature.

### R-448A (Solstice N40) and R-449A (Opteon XP40)

These are the primary HFC/HFO blends replacing R-404A in new commercial refrigeration equipment. They have GWPs of approximately 1387 (R-448A) and 1397 (R-449A) -- about 65% lower than R-404A. Both are zeotropic blends with noticeable temperature glide (approximately 10-12°F), which means the evaporating temperature is different at the inlet and outlet of the evaporator. When checking superheat on these refrigerants, you must use the dew point temperature (from a PT chart or manifold set with the correct refrigerant selected), not the bubble point.

**Retrofit considerations:** R-448A and R-449A can be used as replacements in existing R-404A systems with some modifications. The oil (POE) is compatible. The TXV may need to be adjusted or replaced (the pressure-temperature relationship is different). Charge amounts are typically 85-90% of the original R-404A charge. Performance is generally similar to R-404A at medium temperatures but slightly reduced at low temperatures.

### R-290 (Propane)

R-290 is a natural refrigerant (hydrocarbon) with a GWP of 3 and excellent thermodynamic properties. It is increasingly used in self-contained commercial refrigeration equipment (reach-in coolers, display cases, ice machines). The charge is limited to 150 grams (5.3 oz) per circuit in commercial equipment due to its flammability (A3 classification).

**Safety requirements:** R-290 systems require specific safety features: leak detectors, enhanced ventilation, proper signage, and no ignition sources near the refrigerant circuit. Technicians must be trained and certified for flammable refrigerants. Do not use traditional leak detection methods (soap bubbles are fine, but electronic detectors must be rated for flammable gases). Never braze on an R-290 system without a thorough nitrogen purge -- the consequences of igniting hydrocarbon refrigerant are severe.

## Temperature Logging and HACCP Compliance

### HACCP Basics for the Refrigeration Technician

HACCP (Hazard Analysis and Critical Control Points) is a food safety management system required by law for commercial food operations. As a refrigeration technician, you need to understand that the temperatures you maintain are not just about equipment performance -- they are legal requirements for food safety.

**Critical temperatures:**
- Refrigerated storage: 41°F (5°C) or below
- Frozen storage: 0°F (-18°C) or below
- The danger zone: 41°F to 135°F (5°C to 57°C) -- bacteria grow rapidly in this range
- Time in danger zone: Perishable food that has been in the danger zone for more than 4 hours cumulative must be discarded

**What this means for service calls:** When a walk-in cooler fails and the box temperature rises above 41°F, the clock is ticking. If you cannot get the system running quickly, advise the customer to move perishable food to another unit or pack it in ice. Document the failure time and the temperature you found on arrival -- this information may be needed for health department records.

**Temperature logging requirements:** Many jurisdictions require commercial food establishments to maintain temperature logs for all refrigeration equipment. Digital temperature monitoring systems with remote alerts are becoming standard. When you install or service a commercial refrigeration system, verify that the temperature monitoring is working and the customer knows how to read it. Setting up a monitoring system with high-temperature alerts is a valuable upsell for commercial customers -- it can prevent thousands of dollars in food loss from an overnight equipment failure.

**After a repair:** Always verify that the system pulls down to the required temperature before you leave the job. For a walk-in cooler, this means staying until the box hits 41°F or below. For a walk-in freezer after a complete defrost or major repair, full pulldown to 0°F may take several hours -- set a return check or use a remote monitoring alert.
