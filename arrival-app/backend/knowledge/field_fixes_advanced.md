# Field Fixes and Tribal Knowledge

This file contains real-world field fixes that come from decades of hands-on experience. These are the things that save you hours on a call -- the stuff that experienced techs know but nobody writes down. Every entry follows the same pattern: the symptom you see, the wrong diagnosis most techs jump to, and the actual fix that works.

---

## HVAC Field Fixes

### Capacitor and Compressor Issues

**Carrier outdoor unit capacitor keeps failing (replacement every 1-2 seasons):**
Symptom: you replace the run capacitor on a Carrier or Bryant condenser and within a year or two it fails again. The homeowner is frustrated and the parts house is getting to know you by name.
Wrong diagnosis: bad capacitor batch, or the compressor is pulling too many amps and killing the cap.
Actual fix: Carrier factory-ships many units with a capacitor that is right at the minimum edge of the tolerance range for the compressor and fan motor combined. Upsize the dual run capacitor by 5 microfarads on the compressor side. If the factory cap is 35/5, go to 40/5. This gives the compressor a stronger start and reduces the thermal stress on the capacitor. Do NOT exceed 10% over the compressor nameplate rating. Verify amp draw after the swap -- it should drop slightly on a properly charged system. This fix applies broadly to the 24ACC, 24ANB, and 25HCC series but always verify against the compressor data plate.

**Compressor hums but will not start, trips on overload:**
Symptom: condenser fan runs fine, you hear the compressor trying to start (a humming/buzzing), then it clicks off on the internal overload. Repeat every few minutes.
Wrong diagnosis: compressor is seized, needs replacement ($2,000-$4,000 installed).
Actual fix: install a hard start kit first. A 5-2-1 CSR-U1 or Supco SPP6 will handle most residential compressors up to 5 tons. The hard start kit adds a start capacitor and potential relay that gives the compressor a massive torque boost for the first half-second of startup. This fixes about 80% of hard-start and single-hum situations on compressors that are 8+ years old where the motor windings have developed slightly more resistance. The compressor is not seized -- it just cannot overcome the startup torque on its own anymore. This is a $30 part that saves a $3,000 compressor replacement. Only condemn the compressor if it still will not start with the hard start kit installed, or if you measure a direct short between windings or winding to ground.

**Condenser fan motor runs backwards after replacement:**
Symptom: you replaced the condenser fan motor, wired it up, and the fan spins but it is blowing air down into the unit instead of up and out. The compressor overheats and shuts down on high-pressure cutout within 10 minutes.
Wrong diagnosis: wrong motor, wrong rotation.
Actual fix: on a 3-wire PSC condenser fan motor (common, brown, and brown/white or purple), swapping any two of the three wires reverses rotation. The motor itself spins either direction -- it is the capacitor wiring that determines rotation. If you have a 4-wire motor with separate high and low speed taps, the rotation is determined by which pair of leads connects through the capacitor. Check the wiring diagram on the motor or in the box. If in doubt, connect it and briefly power it on while watching the blade rotation from the top. Correct before running the system.

### Furnace Diagnostics

**Goodman furnace intermittent ignition failure:**
Symptom: Goodman or Amana furnace fires up fine sometimes, other times goes through lockout after 3 ignition attempts. No consistent pattern. Flame sensor checks out clean and pulls 3+ microamps when it does light.
Wrong diagnosis: bad igniter, bad gas valve, or bad control board.
Actual fix: pull the inducer motor wiring harness connector where it plugs into the control board or into the inducer motor itself. These Goodman/Amana units use a connector that corrodes at the pins, especially in humid climates or basements. The corrosion creates an intermittent connection -- sometimes the inducer gets full voltage and works perfectly, other times the voltage drop across the corroded pins means the inducer spins too slowly to close the pressure switch. Clean the connector pins with DeoxIT or electrical contact cleaner, or replace the connector entirely with weatherproof connectors. Also check the wiring harness where it runs near the flue pipe -- radiant heat from the flue degrades the wire insulation over time on these units.

**Lennox SLP98 error code 292 (inducer motor fault):**
Symptom: Lennox SLP98 or SLP99 displays error code 292 on the diagnostic screen. Tech reads the code, sees "inducer motor fault," and quotes a $600-$900 inducer motor replacement.
Wrong diagnosis: inducer motor failure.
Actual fix: on the SLP98 and SLP99, error 292 is triggered about 70% of the time by the collector box gasket leaking, not the inducer motor itself. The collector box is the plastic assembly where the condensate collects before draining. When that gasket fails, you get a slight air leak that the inducer cannot overcome, the pressure switch will not reliably close, and the board logs it as an inducer fault. Pull the collector box, inspect the gasket, and replace it (Lennox part number 10M17 or 10M18 depending on the model). It is a $15 part and a 30-minute job versus a $600+ inducer replacement. Always check the gasket before condemning the inducer.

**Rheem furnace 3 flash error (pressure switch stuck open):**
Symptom: Rheem or Ruud furnace flashing 3 times on the diagnostic LED. Manual says "pressure switch stuck open." Tech starts testing the pressure switch, checking the inducer, looking at the vent pipe.
Wrong diagnosis: pressure switch failure, vent blockage, or weak inducer motor.
Actual fix: on Rheem 90%+ condensing furnaces, 3 flashes means the pressure switch is not closing, and 90% of the time the root cause is a clogged condensate drain line or a full condensate trap. The condensate backs up into the inducer housing and blocks enough airflow that the inducer cannot pull sufficient vacuum to close the pressure switch. Clear the drain line, clean the trap, verify water flows freely. Use a wet/dry vac on the drain outlet or blow compressed air backward through the line. If the trap is the molded plastic type with no clean-out, consider replacing it with a clear trap that you can visually inspect. On Rheem units specifically, the condensate trap design from the 2010-2018 era is prone to building up a calcium/mineral sludge that restricts flow. Tell the homeowner to pour a cup of white vinegar down the condensate drain every 6 months during maintenance.

**Trane XV80 fires then shuts down within 10 seconds:**
Symptom: Trane XV80 or XR80 goes through normal startup -- inducer starts, igniter glows, burners light, flame looks good -- then shuts down in 4-7 seconds. Classic flame sensor issue timing.
Wrong diagnosis: dirty flame sensor (and it IS dirty, but cleaning it does not fix it).
Actual fix: on the XV80 and XR80 series, the flame sensor is mounted with a bracket that positions it in the burner flame. Trane redesigned this bracket at some point, and the older version positions the sensor rod at an angle where only the tip sits in the flame instead of the full length of the rod. When you pull the sensor to clean it, check the orientation -- the rod should be positioned so the flame wraps around as much of the rod length as possible, not just kissing the tip. If the bracket is the old style, bend it slightly (5-10 degrees) so the rod extends further into the flame path. You should see flame sense current jump from 1-2 microamps to 3-5 microamps. On some units, the sensor was literally installed backwards at the factory with the rod curving away from the flame.

**Draft inducer runs but no ignition (any 90%+ furnace):**
Symptom: inducer starts and runs, but the furnace never advances to the ignition step. Pressure switch will not close.
Wrong diagnosis: bad pressure switch, weak inducer motor.
Actual fix: check the condensate trap FIRST. On 90%+ condensing furnaces, the condensate trap must be full of water to create a water seal. When the furnace has not run for a while (new install, beginning of season, or after maintenance where the trap was drained), the trap is empty and air leaks through it. The inducer pulls air through the empty trap instead of through the heat exchanger, so it cannot build enough negative pressure to close the pressure switch. Pour water into the trap until it flows out the drain side. This primes the trap and creates the water seal. The furnace will fire immediately. This accounts for a huge percentage of no-heat calls at the start of the heating season on condensing furnaces.

**Furnace cycles on high limit switch:**
Symptom: furnace runs for 5-10 minutes, then shuts off. Blower keeps running. Furnace restarts after it cools down, then shuts off again. Limit switch is tripping.
Wrong diagnosis: bad limit switch. Tech replaces the limit switch.
Actual fix: the limit switch is doing its job -- it is protecting the heat exchanger from overheating. The actual problem is restricted airflow in almost every case. Check in this order: dirty air filter (the number one cause of limit trips across all brands), closed or blocked supply registers, undersized return ductwork, dirty blower wheel (pull the blower and look -- a blower wheel caked with dust and debris moves 30-40% less air even though the motor sounds fine), collapsed flex duct in the attic, or closed dampers. If all airflow checks good and the limit still trips, verify the blower speed is set correctly for heating mode. A blower set to cooling speed during heating will move too much air on some systems and not enough on others depending on the static pressure. On ECM/variable speed blowers, check the programmed airflow in the setup -- it may be configured too low.

### Refrigeration and Cooling

**R-410A system low on charge:**
Symptom: system is not cooling well, superheat is high, subcooling is low, suction pressure is low. Clearly low on refrigerant.
Wrong diagnosis: just add refrigerant and send the bill.
Actual fix: R-410A systems are critical-charge systems. Unlike the old R-22 days where you could top off a system that was a pound low and come back next year, R-410A operates at significantly higher pressures (about 1.6 times higher than R-22) and is a near-azeotropic blend. You must find and repair the leak before adding charge. If you just top it off, you will be back in 3-6 months, the customer loses trust, and the system may have been running with low charge long enough to cause compressor oil migration and eventual compressor failure. Use electronic leak detection (heated diode or infrared type, not the cheap corona discharge detectors that false-alarm on everything), nitrogen pressure testing, or UV dye. Check the indoor coil, outdoor coil, line set connections, Schrader valves, and the service valve packing nuts. Schrader cores and flare connections at the service valves account for 40%+ of residential leaks.

**High head pressure on a hot day (no-cool call):**
Symptom: system running but not cooling. Head pressure is sky high (450+ PSI on R-410A). Homeowner says it was fine until the heat wave hit.
Wrong diagnosis: system is overcharged, or the compressor is weak.
Actual fix: look at the condenser coil. In 80% of summer no-cool emergency calls, the condenser coils are clogged with cottonwood fuzz, grass clippings, dog hair, dryer lint (if the dryer vent exhausts near the condenser), or just accumulated dirt. A clogged condenser coil means the system cannot reject heat, so head pressure climbs, efficiency drops, and eventually the high-pressure switch trips or the compressor overheats. Hose the condenser coils from the inside out (not outside in, which packs debris deeper). Use a coil cleaner if heavily soiled. Also check that the condenser has adequate clearance -- at least 12 inches on all sides, 24 inches preferred. Shrubs, fences, and deck structures built too close to the condenser kill efficiency and lead to premature compressor failure.

**Ice on suction line at the outdoor unit:**
Symptom: suction line (the big insulated copper line) is covered in ice from the indoor coil all the way back to the compressor. Customer says it stopped cooling.
Wrong diagnosis: low on refrigerant, needs a charge.
Actual fix: check the airflow FIRST. A dirty air filter is the number one cause of suction line icing. When airflow is restricted, the evaporator coil gets too cold, the refrigerant does not absorb enough heat, and it returns to the compressor as a cold liquid/vapor mix that ices up the suction line. Other airflow causes: closed supply registers (homeowners close vents in unused rooms, reducing total airflow), collapsed flex duct, dirty evaporator coil, or a blower motor running at wrong speed. Only after verifying good airflow should you check the refrigerant charge. If it IS low on charge, the reduced refrigerant mass causes the evaporator pressure and temperature to drop, also resulting in icing. But airflow is the cause 60-70% of the time.

**Mini-split short cycling (runs 5-10 minutes, stops, restarts):**
Symptom: ductless mini-split runs for a short time, stops, then restarts. Customer complains it cannot keep up.
Wrong diagnosis: low on refrigerant, outdoor unit problem.
Actual fix: check the thermistor on the indoor unit return air sensor. Mini-splits use thermistors to sense room temperature and coil temperature, and a failing thermistor gives erratic readings that make the board think the room is at setpoint when it is not. The return air thermistor is usually clipped to the evaporator coil or mounted in the return air path behind the filter. Test it with a meter in resistance mode and compare to the temperature/resistance chart in the service manual (most use a 10K ohm NTC thermistor -- at 77 degrees F it should read about 10K ohms, at 90 degrees about 7K ohms). If it is out of spec, replace it. This is a $5 part that takes 10 minutes. Also check that the indoor unit filter is clean -- restricted airflow on a mini-split causes the coil thermistor to read too cold and the unit shuts down thinking the coil is about to freeze.

**Thermostat says "cool on" but nothing is happening:**
Symptom: homeowner calls panicking because the thermostat shows cooling is active but nothing is running outside.
Wrong diagnosis: contactor is bad, wiring issue, control board problem.
Actual fix: most modern thermostats and control boards have a built-in 5-minute compressor time delay to prevent short cycling. If the system just ran (or the thermostat was just switched from off to cool, or the power blipped), the compressor delay is active and nothing will happen for 5 minutes. Tell the customer to wait 5-8 minutes before diagnosing further. This is normal and protects the compressor from starting against high head pressure. If you jump the contactor and force-start the compressor during this delay, you risk compressor damage. If nothing happens after 8 minutes, then begin normal diagnostics at the thermostat, wiring, contactor, and compressor.

**Heat pump not defrosting:**
Symptom: heat pump outdoor unit is coated in ice during heating season. Not going into defrost.
Wrong diagnosis: bad reversing valve, needs refrigerant.
Actual fix: diagnose in this order because it matters. First, check the defrost control board -- it initiates defrost based on time and temperature (or time and pressure on some units). The board may have failed or a solder joint may have cracked. Second, check the defrost thermostat/sensor -- this is clipped to the liquid line or the outdoor coil and tells the board when the coil is cold enough to need defrost. If it has shifted position or fallen off, it reads ambient air temperature instead of coil temperature and never calls for defrost. Third, check the reversing valve solenoid -- 24V should appear at the solenoid during defrost. If you get 24V but the valve does not shift, the valve may be stuck (try tapping the valve body with a wrench handle while energized). Replace the solenoid coil first ($20) before condemning the entire valve ($200+ and a recovery/recharge job).

### UV Lights and Indoor Air Quality

**UV light destroyed the drain pan:**
Symptom: customer had a UV light installed in the air handler 1-3 years ago. Now the drain pan is cracked, warped, or disintegrating and water is leaking.
Wrong diagnosis: defective drain pan.
Actual fix: certain UV-C germicidal lights, especially the higher-wattage units mounted close to the evaporator coil, degrade PVC, ABS, and other plastics through photodegradation. The UV radiation breaks down the polymer chains in the plastic drain pan, condensate drain fittings, and even flexible drain tubing. The pan becomes brittle and cracks. This is a known issue that UV light manufacturers do not always disclose. If installing a UV light, make sure the light is aimed so it does not directly illuminate plastic components for extended periods. Use UV-resistant drain pans (stainless steel or UV-stabilized polymer). If the damage is done, replace the drain pan with a metal one and consider repositioning the UV light or adding a UV shield between the light and the plastic components.

### Gas Smell and Safety

**Gas furnace smells like burning on first startup:**
Symptom: customer turns on heat for the first time in the fall and smells burning. Calls in a panic.
Wrong diagnosis: cracked heat exchanger, gas leak.
Actual fix: dust accumulates on the heat exchanger, burners, and inside the cabinet over the summer months when the system is idle. On the first heating cycle, this dust burns off and creates a distinct burning smell that can last 15-30 minutes. This is completely normal and happens every year. Advise the customer to open windows if the smell is strong. However -- if the smell persists beyond the first hour of operation or has a chemical/aldehyde quality (like formaldehyde), that is a red flag for a cracked heat exchanger allowing combustion products into the airstream. Perform a visual inspection with a mirror and flashlight, a combustion analysis, or a heat exchanger leak test using a smoke or tracer gas.

### Noise Diagnostics

**Noisy indoor blower motor -- rattling, scraping, or vibrating:**
Symptom: indoor air handler or furnace makes a rattling, scraping, or vibrating noise when the blower runs.
Wrong diagnosis: bad blower motor bearings, needs motor replacement.
Actual fix: pull the blower assembly and inspect the blower wheel first. A blower wheel caked with dust and debris becomes unbalanced, causing vibration. A blower wheel with a loose set screw on the motor shaft wobbles and scrapes against the housing. Clean the wheel, tighten the set screw, and re-check. If the wheel is clean and tight, check the motor mounts -- rubber isolation grommets dry out and crack after 8-10 years, allowing the motor to vibrate against the blower housing. Replace the grommets (generic HVAC motor mount grommets are universal) before replacing the motor. Also check for debris (screws, zip ties, wire nuts) that may have fallen into the blower housing during previous service work.

### Thermostat and Controls

**Thermostat reads wrong temperature (offset from actual):**
Symptom: thermostat displays a temperature that is 3-5 degrees different from what a separate thermometer reads in the same room. Customer says the house never feels comfortable.
Wrong diagnosis: thermostat is defective, replace it.
Actual fix: check the thermostat mounting location. If it is on an exterior wall, near a supply register, in direct sunlight from a window, above a lamp or TV, or near a kitchen, it is reading a localized temperature that does not represent the room. Relocate if possible. If the location is fine, many modern thermostats have a temperature offset or calibration setting buried in the installer setup menu. Adjust by the measured difference. Also check: is the thermostat mounted on a hollow wall with no insulation behind it? Cold air drafts through the wall cavity behind the thermostat and affects the sensor. A small piece of foam insulation behind the thermostat base plate solves this.

**System blows cold air in heat mode for 30 seconds when blower starts:**
Symptom: furnace fires up, heater runs for a minute, then the blower starts and blows noticeably cool air for 30-60 seconds before it feels warm.
Wrong diagnosis: heat exchanger problem, not heating the air properly.
Actual fix: this is the blower-on delay being set too short. The heat exchanger has not reached full temperature when the blower kicks on. On most furnace control boards, there are DIP switches or jumper pins that set the blower-on delay (30, 60, 90, or 120 seconds after burner ignition). Increase the delay by one step. On ECM/variable-speed systems, the blower ramps up gradually and this is less of an issue, but on single-speed PSC blowers, the full-speed blast of air over a not-yet-hot heat exchanger feels cold.

---

## Electrical Field Fixes

### AFCI and GFCI Breaker Issues

**AFCI breaker keeps tripping -- no apparent cause:**
Symptom: AFCI breaker trips repeatedly. No specific appliance causes it, or it trips at random times. Homeowner is frustrated.
Wrong diagnosis: defective AFCI breaker, or the wiring has a real arc fault somewhere.
Actual fix: shared neutrals are the number one cause of AFCI nuisance tripping. In older homes that were rewired or had circuits added, it is common to find two circuits sharing a single neutral wire back to the panel. When an AFCI breaker monitors the current on its hot wire and compares it to the current on its neutral wire, a shared neutral means current is returning on a different path than expected. The AFCI sees this imbalance and trips. Trace the neutral for the tripping circuit all the way back to the panel and verify it is not shared with any other circuit. If it is, run a dedicated neutral. This one diagnosis accounts for probably 40% of "random" AFCI trips in retrofit situations. Other common causes: backstab connections on outlets (pull every device on the circuit and check for backstab connections -- pigtail them to screw terminals instead), and damaged wire insulation where a drywall screw or nail nicked the wire during construction.

**GFCI outlet will not reset:**
Symptom: GFCI receptacle is dead. Push the reset button and it either does not click or clicks and immediately pops back.
Wrong diagnosis: GFCI is bad, replace it.
Actual fix: before replacing, check for a bootleg ground (hot and neutral reversed on a downstream outlet). A bootleg ground exists when someone connected the hot wire to the neutral terminal and the neutral wire to the hot terminal on an outlet downstream of the GFCI. This creates an immediate ground fault that prevents the GFCI from resetting. Also check: is there actually power at the LINE terminals of the GFCI? Use a non-contact voltage tester or meter. If there is no power, the GFCI is not going to reset no matter what -- the problem is upstream (tripped breaker, loose wire, or another GFCI upstream that has tripped). If power is present at LINE and it still will not reset, disconnect the LOAD wires entirely and try to reset with only the LINE connected. If it resets, the fault is downstream. Reconnect LOAD wires one at a time to isolate the bad device or wire.

**LED lights flicker on a dimmer:**
Symptom: LED bulbs or LED fixtures flicker, buzz, or do not dim smoothly. They may flash at the low end of the dimmer range or have a visible strobe effect.
Wrong diagnosis: bad LED bulbs, cheap LEDs.
Actual fix: the dimmer must be CL-rated (or specifically rated for LED/CFL loads). Standard incandescent dimmers use a triac that chops the AC waveform to reduce power. LEDs draw so little current that the triac cannot hold its gate signal open, causing the LED driver to cycle on and off rapidly (flicker). Replace the dimmer with a CL-rated model. Lutron Caseta, Lutron Diva CL, and Leviton Decora Smart dimmers work with almost every LED on the market. Also check the minimum load requirement -- some older dimmers need a minimum wattage (40-60W) to operate, and a single 9W LED does not meet that threshold. If you have a bank of recessed LEDs on one dimmer and they still flicker, try a different LED brand. Compatibility between dimmer and LED driver varies, and the dimmer manufacturers publish compatibility lists on their websites.

### Panel and Wiring Issues

**Panel buzzing or humming:**
Symptom: electrical panel makes a buzzing or humming sound. Customer is concerned.
Wrong diagnosis: overloaded panel, or the main breaker is failing.
Actual fix: turn off individual breakers one at a time while listening to identify which one is buzzing. A buzzing breaker usually just needs to be reseated -- turn it fully off, then push it firmly toward the bus bar and back on. The stab connection to the bus bar can loosen slightly over time, especially on panels that experience thermal cycling from high-load circuits. If the buzz is coming from the main lugs or main breaker, shut off the main and check the lug connections for proper torque. On a 200A service, loose main lugs are a fire hazard and will show signs of heat damage (discolored wire insulation, darkened lugs). Tighten to manufacturer torque specs with a calibrated torque screwdriver. If a breaker continues to buzz after reseating, replace it -- the internal contact may be pitted or weakened.

**Outlet tester shows "open ground" but ground wire is present:**
Symptom: plug-in outlet tester lights show "open ground" pattern. You open the box and there is a bare copper ground wire connected.
Wrong diagnosis: broken ground wire in the wall, need to rewire.
Actual fix: check the device first. If the outlet was wired using the backstab (push-in) connections on the back of the receptacle, the ground connection is made through the device mounting strap to the box and then through the ground wire. But backstab connections are notorious for loosening over time -- the spring tension weakens and the wire barely makes contact. Pull the receptacle out, cut off the stripped ends, re-strip fresh wire, and connect to the screw terminals (side screws, not backstabs). Also check: is the ground wire actually connected to the receptacle green screw, or is it just connected to the metal box? If the receptacle is not self-grounding (most cheap receptacles are not truly self-grounding despite being in a grounded metal box), you need a pigtail from the ground wire to the receptacle green screw AND to the box.

**240V outlet only reading 120V:**
Symptom: 240V appliance (dryer, range, water heater, etc.) is not working. Meter reads 120V at the outlet instead of 240V.
Wrong diagnosis: bad outlet, wiring issue at the outlet.
Actual fix: you have lost one leg of the 240V circuit. Check the breaker first -- a double-pole breaker has two poles that should be mechanically linked so they trip together, but sometimes one pole trips and the other stays on, or one pole has a bad internal contact. Turn the breaker off and back on. If the problem persists, check voltage at the breaker terminals with the breaker on -- you should read 120V from each terminal to neutral/ground, and 240V across the two terminals. If one terminal shows 0V, the breaker is bad or the bus bar connection is bad. Also check: is the breaker actually a double-pole, or did someone use two single-pole breakers with a handle tie? Two singles with a handle tie on the same bus phase give you 0V across them, not 240V. They must be on opposite phases.

### Code and Safety

**Old house with 2-prong outlets -- customer wants 3-prong:**
Symptom: customer has an older home with ungrounded 2-prong receptacles and wants to plug in modern 3-prong devices.
Wrong diagnosis: need to rewire the entire house with grounded circuits.
Actual fix: per NEC 406.4(D)(2), you can legally replace a 2-prong ungrounded receptacle with a GFCI receptacle and label it "No Equipment Ground." This provides personal protection (the GFCI will trip on a ground fault) without requiring a ground wire. You can also feed downstream receptacles from the LOAD side of that GFCI and label each one "GFCI Protected" and "No Equipment Ground." This is a fraction of the cost of rewiring and is 100% code-compliant. However, certain equipment (surge protectors, some computer equipment) needs an actual equipment ground to function properly, so advise the customer of the limitation.

**Aluminum wiring -- any connection work:**
Symptom: home built in the 1960s-1970s has aluminum branch circuit wiring. Any connection work, device replacement, or repair.
Wrong diagnosis: just wire-nut the aluminum to the new copper pigtails.
Actual fix: NEVER directly connect aluminum to copper without an approved method. Aluminum and copper have different rates of thermal expansion, and galvanic corrosion at the junction creates high-resistance connections that overheat and start fires. Approved methods: Alumiconn connectors (the most widely accepted -- a set-screw lug connector with anti-oxidant compound built in), COPALUM crimp connectors (requires a special tool and certified installer), or CO/ALR rated devices (receptacles and switches rated for direct aluminum termination). Purple wire nuts (Ideal 65) are rated for aluminum-to-copper splices but are less reliable than Alumiconn in practice. On every aluminum wire connection, apply anti-oxidant paste (NoAlox or equivalent) to the stripped aluminum before making the connection. This prevents the oxide layer from re-forming.

**FPE (Federal Pacific) or Zinsco panel identified:**
Symptom: you open a panel and see Federal Pacific Electric (FPE Stab-Lok) or Zinsco breakers.
Wrong diagnosis: panel is old but still working, just replace individual breakers as needed.
Actual fix: FPE Stab-Lok and Zinsco/Sylvania panels are documented fire hazards. Independent testing has shown that FPE breakers fail to trip on overcurrent at a rate far higher than other brands. Zinsco breakers have a known issue with the bus bar connection where the aluminum bus bars corrode and the breakers fuse to the bus, preventing them from tripping. Always recommend full panel replacement to the customer. Do not try to source replacement breakers -- aftermarket FPE breakers are not reliable either. Document the panel type and your recommendation in writing. If the customer declines replacement, note it on the invoice. Many insurance companies will not cover fire damage if an FPE or Zinsco panel is found.

**EV charger installation -- wire sizing:**
Symptom: customer wants a Level 2 EV charger installed. Charger is rated 40 amps.
Wrong diagnosis: 40A charger, use a 40A breaker and 8 AWG wire.
Actual fix: EV chargers are considered a continuous load (running for more than 3 hours), so NEC requires the circuit to be rated at 125% of the load. A 40A charger requires a 50A breaker and wire sized for 50A (6 AWG copper or 4 AWG aluminum for typical residential runs). A 48A charger (like the Tesla Wall Connector at full output) requires a 60A breaker and 6 AWG copper (for short runs) or 4 AWG copper (for longer runs -- always calculate voltage drop on runs over 50 feet). The charger manufacturer will specify the breaker size, but always verify against NEC 625.41 and local amendments. Many jurisdictions also require a dedicated circuit with no other loads.

**Smart switch installation -- no neutral wire:**
Symptom: customer wants smart switches installed. You open the switch box and there is no neutral (white) wire -- just the hot (switched and unswitched) and ground.
Wrong diagnosis: cannot install smart switches, need to rewire.
Actual fix: most smart switches require a neutral wire for their internal electronics, and most older homes do not have a neutral at the switch box (the neutral goes directly from the panel to the fixture). However, Lutron Caseta switches and dimmers do NOT require a neutral wire. They work by leaking a tiny current through the load to power their internal radio and processor. This makes Caseta the go-to solution for older homes without neutral wires at the switch. The Caseta system uses a bridge (hub) and Pico remotes, and integrates with almost every smart home platform. Other options: some Inovelli and C by GE switches also work without a neutral, but Caseta has the widest compatibility and best reliability track record.

**Smoke detector chirping -- not the battery:**
Symptom: smoke detector chirps every 30-60 seconds. Customer replaced the battery and it still chirps.
Wrong diagnosis: bad battery, or the detector is dusty.
Actual fix: smoke detectors have a 10-year lifespan. After 10 years, the detector chirps to indicate end of life, and no amount of battery replacement or cleaning will stop it. Flip the detector over and look for a date of manufacture on the back. If it is more than 10 years old, replace it. This is the number one unnecessary service call in residential electrical. Also: if it is a hardwired detector with battery backup, the chirp may indicate that the AC power has been lost (tripped breaker or disconnected wire) and it is running on battery. Check for AC voltage at the connector before just swapping the battery.

**Microwave tripping the breaker:**
Symptom: microwave trips the kitchen breaker, especially when another appliance is also running.
Wrong diagnosis: bad microwave, or the breaker is weak.
Actual fix: microwaves pull 12-15 amps on high power. If the microwave is on a shared kitchen circuit with other countertop appliances, the combined load exceeds the 20A breaker. Per current code (NEC 210.52), kitchen countertop receptacles require at least two 20A small-appliance branch circuits, and the microwave should ideally be on its own dedicated circuit. Check what else is on the circuit. If the microwave is the only thing running and it still trips, the breaker may be an AFCI that is nuisance-tripping on the microwave's magnetron startup surge -- some older AFCI breakers are sensitive to the inrush. Verify the breaker type and consider replacing with a newer generation AFCI that handles motor/magnetron loads better.

**GFCI does not protect the wiring upstream of itself:**
Symptom: tech installs a GFCI at the first outlet in a circuit run, believes everything is now GFCI protected.
Wrong diagnosis: the whole circuit is protected.
Actual fix: a GFCI receptacle protects itself and everything wired from its LOAD terminals downstream. It does NOT protect the wiring between the panel and the GFCI LINE terminals. If the first receptacle in the circuit is 50 feet from the panel, those 50 feet of wire are not GFCI protected. If GFCI protection is needed for the entire circuit (as in a bathroom, kitchen, or outdoor circuit), install a GFCI breaker at the panel instead of a GFCI receptacle. This is particularly important for outdoor circuits where wire damage from landscaping, rodents, or weather could occur anywhere in the run.

**Knob and tube wiring with blown-in insulation:**
Symptom: older home has knob and tube wiring in the attic or walls. Someone blew insulation over it or wants to add insulation.
Wrong diagnosis: knob and tube is old but still safe, insulation is fine.
Actual fix: knob and tube wiring was designed to dissipate heat into open air. The conductors run through open air spaces with ceramic knob and tube insulators keeping them away from framing. When you cover this wiring with blown-in insulation (cellulose or fiberglass), the wire cannot dissipate heat and runs hotter. This dramatically increases the fire risk, especially at splices and connection points where resistance is already higher. NEC 394.12 prohibits installing insulation over knob and tube wiring. If the homeowner wants to insulate the attic, the knob and tube circuits in the insulation zone must be replaced with modern Romex first. Insurance companies are increasingly refusing to cover or renew policies on homes with active knob and tube wiring, especially if insulation has been added.

---

## Plumbing Field Fixes

### Toilet Issues

**Toilet runs intermittently (phantom flush):**
Symptom: toilet randomly starts filling for 10-15 seconds every hour or so, even though nobody flushed it. Customer hears it running at night.
Wrong diagnosis: bad fill valve, the ballcock is worn out.
Actual fix: this is almost always the flapper, and it is a $4 fix. The flapper rubber degrades over time (chlorine in the water accelerates this) and develops a slow leak. Water trickles past the flapper from the tank into the bowl. When the tank water level drops enough, the fill valve kicks on to refill. Replace the flapper with a Korky or Fluidmaster universal flapper -- not the cheap no-name ones that come in multi-packs. If you have replaced the flapper and it still leaks, check the flush valve seat for mineral buildup or pitting. You can resurface a rough valve seat with a flush valve repair kit (abrasive disc that smooths the seat) rather than replacing the entire flush valve.

**Toilet rocks on the floor:**
Symptom: toilet moves when you sit on it. There is a slight gap between the base and the floor.
Wrong diagnosis: broken flange, need to pull the toilet and replace the flange.
Actual fix: most rocking toilets just need shimming. Use plastic toilet shims (available at any hardware store), insert them at the gaps around the base until the toilet is stable, then score and snap off the excess. Caulk around the base with silicone caulk to keep the shims in place and prevent water from getting under the toilet. Important: leave a 1-2 inch gap at the back of the toilet uncaulked. This gap serves as a leak indicator -- if the wax ring fails, water will seep out the back where you can see it, rather than being trapped under a fully caulked toilet where it rots the subfloor silently. If the toilet rocks significantly (more than 1/4 inch gap) AND the flange is broken or below floor level, then you need flange repair. But check the simple fix first.

### Water Heater Issues

**Water heater making popping or rumbling sounds:**
Symptom: gas or electric water heater makes popping, crackling, or rumbling noises, especially when heating.
Wrong diagnosis: water heater is about to explode, needs immediate replacement.
Actual fix: this is sediment buildup at the bottom of the tank. Minerals in the water (calcium carbonate primarily) settle and form a layer on the bottom. When the burner fires (gas) or the lower element heats (electric), water trapped under the sediment layer boils and pops, creating the noise. Flush the tank by connecting a garden hose to the drain valve, opening the valve, and letting water flow until it runs clear. On badly sediment-loaded tanks, you may need to shut off the inlet, drain fully, then briefly open the inlet to flush in surges. If the tank has never been flushed and it is over 5 years old, also check the anode rod -- it is probably depleted. A depleted anode rod means the tank itself is corroding, and once the tank starts leaking there is no repair. Replace the anode rod (magnesium or powered type) to extend tank life by another 5+ years.

**Tankless water heater cold-hot-cold sandwich:**
Symptom: customer runs hot water, gets a burst of hot (from water sitting in the pipes), then cold for 10-15 seconds, then hot again. This happens on short draws (hand washing) and when going from one fixture to another.
Wrong diagnosis: tankless unit is undersized, or the gas pressure is too low.
Actual fix: this is an inherent characteristic of tankless water heaters called the "cold water sandwich" effect. It happens because the water sitting in the pipes between the heater and the fixture cools off, and the tankless unit takes a few seconds to fire and bring the heat exchanger up to temperature when flow resumes. A recirculation system (dedicated return line or crossover valve with pump and timer) keeps hot water moving through the pipes and virtually eliminates the sandwich. If a full recirc system is too expensive, install a small 2-4 gallon mini tank water heater in series between the tankless unit and the most-used fixture as a buffer. Also, some newer tankless units (Navien, Rinnai with recirc built in) have internal buffer tanks and recirc pumps that handle this from the factory.

**Tankless water heater error code on startup (ignition failure):**
Symptom: tankless water heater displays an error code on startup. Most common codes: Rinnai 11 (no ignition), Navien E003 (ignition failure), Noritz 11 (no ignition).
Wrong diagnosis: bad igniter, bad gas valve, or bad control board.
Actual fix: the number one cause of ignition failure on tankless water heaters is gas supply pressure that is too low. Tankless units have a much higher BTU input than tank-style heaters (199,000 BTU is common for a whole-house unit vs 40,000 BTU for a standard tank). The gas line feeding the unit must be sized to deliver the full BTU load at the correct pressure. Measure gas pressure at the unit's test port: natural gas should be 3.5-5.0 inches WC minimum at the inlet with the unit firing at full capacity. If the pressure drops below 3.5 inches WC when the unit fires, the gas line is too small, too long, or has too many fittings restricting flow. This is an installation deficiency that shows up as an intermittent ignition failure, usually when other gas appliances (furnace, dryer, stove) are also running and competing for gas volume.

### Drain and Waste Issues

**Sewer gas smell from shower or floor drain:**
Symptom: bathroom or basement smells like sewer gas, especially from a shower or floor drain that is not used frequently.
Wrong diagnosis: broken vent pipe, cracked drain line, sewer backup.
Actual fix: dry P-trap. Every drain has a P-trap that holds water to create a seal against sewer gases. If a drain is not used for several weeks (guest bathroom, basement floor drain, rarely used tub), the water in the trap evaporates and sewer gas comes up through the open trap. The fix: pour water down the drain. For floor drains that are rarely used, pour a cup of mineral oil on top of the water in the trap -- it floats on top and prevents evaporation for months. If the smell persists after filling the trap, then investigate further: check the wax ring on nearby toilets, check for cracked vent pipes in the wall or attic, and check that the vent pipe termination on the roof is not blocked.

**Garbage disposal humming but not spinning:**
Symptom: flip the switch, disposal hums loudly but the grinding plate does not rotate. May trip the reset button.
Wrong diagnosis: motor is burned out, need a new disposal.
Actual fix: the grinding plate is jammed, not the motor. Every garbage disposal has an Allen wrench socket on the bottom center of the unit (usually 1/4 inch hex). Insert an Allen wrench and turn it back and forth to free the jammed flywheel. The jam is usually caused by a bone fragment, fruit pit, or utensil that fell in. After freeing the jam, reach in (with the power OFF at the breaker, not just the switch) and remove the obstruction. Press the reset button on the bottom of the unit and test. If the flywheel turns freely with the Allen wrench but the motor still only hums, the motor start capacitor may have failed. On higher-end disposals (InSinkErator Evolution series), the capacitor is replaceable. On cheaper units, motor failure means replacement.

### Drain Clearing Tips

**Bathtub drains slowly -- snake does not help:**
Symptom: bathtub drains slowly. Tech runs a snake through the overflow and it comes out clean, but the drain is still slow.
Wrong diagnosis: main line problem, or the vent is blocked.
Actual fix: the clog is in the shoe (the fitting directly under the drain opening in the tub). Hair wraps around the crossbar in the drain and builds up over years. A snake goes past this clog because it enters through the overflow, which connects to the drain BELOW the shoe. Remove the drain strainer/stopper, and use a Zip-It drain cleaning tool or needle-nose pliers to pull the hair ball out of the shoe fitting. This $2 tool clears the problem in 2 minutes. If the tub has a trip lever stopper mechanism, the linkage assembly inside the overflow pipe may also be clogged with hair and soap -- pull the whole mechanism out through the overflow plate and clean it.

**Kitchen sink drains slowly but only on one side (double bowl):**
Symptom: one side of a double-bowl kitchen sink drains slowly, the other side is fine.
Wrong diagnosis: clog in the drain line below the sink.
Actual fix: the baffle tee (the tee fitting that connects both sink bowls to a single drain) often has food debris buildup inside, especially at the junction. Disconnect the baffle tee, clean it out, and reconnect. Also check the garbage disposal outlet if one side has a disposal -- when a new disposal is installed, there is a knockout plug in the dishwasher inlet that must be removed if a dishwasher is connected. If not removed, it restricts the drain path significantly.

### Supply Line and Fitting Issues

**Low hot water pressure but cold pressure is fine:**
Symptom: hot water pressure at a fixture (usually a kitchen faucet or bathroom faucet) is noticeably weaker than cold.
Wrong diagnosis: failing water heater, sediment restricting the dip tube or outlet.
Actual fix: check the flex supply lines under the fixture first. Braided stainless steel flex lines have a rubber liner inside, and on the hot side, years of thermal cycling cause the rubber liner to deteriorate and partially collapse internally, creating a restriction that you cannot see from the outside. The line looks fine but is 60% blocked inside. Replace the hot side flex line and the pressure returns to normal. If both hot and cold supply lines are old, replace both. This is a $10 fix that takes 15 minutes and solves the problem 70% of the time. If the supply lines are fine, then check the faucet cartridge or aerator for sediment/debris and the water heater outlet shutoff valve for a partially closed condition.

**PEX crimp ring fitting leaking:**
Symptom: PEX crimp ring fitting is dripping at the connection. Slow, steady drip.
Wrong diagnosis: bad fitting, need to cut it out and redo the whole connection.
Actual fix: the crimp ring was not fully compressed. Use a go/no-go gauge to check the crimp ring dimension. If it is out of spec, you can re-crimp over the existing ring with the crimp tool -- give it another firm squeeze and re-check with the gauge. If it still leaks, cut the fitting out and redo it with a new ring and fitting (you will lose about 2 inches of PEX). For future reference, expansion-type PEX fittings (ProPEX / Uponor style) almost never leak because the fitting relies on the memory of the expanded PEX to shrink back around the fitting, creating a mechanical seal that gets tighter over time. In any high-risk area (inside a wall, above a finished ceiling), expansion fittings are worth the extra cost of the tool.

### Pressure and Expansion Issues

**Water hammer when washing machine or dishwasher fills:**
Symptom: loud banging or hammering in the pipes when the washing machine or dishwasher solenoid valve snaps shut.
Wrong diagnosis: loose pipes, need to add pipe straps.
Actual fix: install water hammer arrestors at the washing machine supply valves. Water hammer occurs when a fast-closing solenoid valve (unlike a slow-closing faucet) slams shut and the momentum of the moving water column creates a pressure shock wave. Pipe straps help with loose pipes rattling, but they do not fix the pressure wave itself. Sioux Chief mini-rester arrestors screw directly onto the washing machine valve threads and absorb the shock. They are about $10 each and take 5 minutes to install. For dishwashers, install an arrestor on the hot water supply line under the sink. If the hammer is severe and occurs at multiple fixtures, the water pressure may be too high -- check with a gauge and install or adjust the PRV if pressure exceeds 80 PSI.

**Expansion tank failed (waterlogged):**
Symptom: water heater T&P relief valve drips or weeps periodically. PRV is set correctly, water pressure is normal.
Wrong diagnosis: bad T&P valve, replace it.
Actual fix: tap on the expansion tank (the small tank connected to the cold water line near the water heater). A properly functioning expansion tank sounds hollow at the top and solid at the bottom (air bladder on top, water on bottom). If the entire tank sounds solid and heavy when you tap it, the internal bladder has failed and the tank is waterlogged -- it is completely full of water and no longer absorbs thermal expansion. When the water heater fires and the water expands, there is nowhere for the pressure to go, so it pushes past the T&P valve. Replace the expansion tank. Pre-charge the new tank to match the incoming water pressure (check with a gauge) before installing. Most residential expansion tanks come pre-charged to 40 PSI, but if your system pressure is 60 PSI, you need to add air with a tire pump to 60 PSI through the Schrader valve on the tank.

**PRV (pressure reducing valve) failing:**
Symptom: water pressure in the house is too high (over 80 PSI) or fluctuates wildly.
Wrong diagnosis: city water pressure surged, temporary problem.
Actual fix: PRVs have a lifespan of 7-12 years depending on water quality. When they fail, they typically fail open (allowing full city pressure through) rather than closed. Check the pressure with a gauge on a hose bib. If it reads above 80 PSI, the PRV needs replacement. If the pressure varies throughout the day (high in the morning, lower in the afternoon), the PRV diaphragm is worn and not regulating consistently. Replace the entire PRV -- they are not worth rebuilding. Also install an expansion tank on the water heater side of the PRV if one is not present, because a properly functioning PRV creates a closed system, and thermal expansion from the water heater has nowhere to go without an expansion tank.

**Sump pump runs constantly:**
Symptom: sump pump cycles on and off every few minutes, or runs nearly continuously even when it is not raining.
Wrong diagnosis: high water table, need a bigger pump.
Actual fix: check the check valve on the discharge line FIRST. If the check valve has failed (stuck open or missing entirely), water that the pump pushes up the discharge line flows right back into the sump pit when the pump shuts off, and the pump immediately kicks on again to pump the same water. This short cycling burns out the pump motor prematurely. Replace the check valve. If the check valve is fine, check the float switch -- make sure it is not tangled on the discharge pipe or the power cord. A float switch that cannot drop freely keeps the pump running. Also check: is the discharge line frozen or blocked outside? Water that cannot exit backs up and the pump runs against a dead head.

**Kitchen faucet single handle hard to turn:**
Symptom: single-handle kitchen faucet is stiff, hard to move, or jerky when adjusting temperature/flow.
Wrong diagnosis: faucet is worn out, needs replacement.
Actual fix: the cartridge needs replacement, not the faucet. Single-handle faucets (Moen, Delta, Kohler, and others) use a cartridge or ball assembly that controls both flow and temperature. After years of use, mineral deposits build up on the cartridge surfaces and it becomes stiff. Replace the cartridge -- it is a $15-$30 part specific to the faucet brand and model. Moen 1225 and 1222 cartridges cover the vast majority of Moen single-handle faucets. Delta RP46074 covers most Delta single-handle kitchen models. The cartridge swap takes 15-20 minutes and restores the faucet to like-new operation. The entire faucet body, spout, sprayer, and finish are all fine -- it is just the internal moving part that wears.

**Outdoor frost-proof faucet dripping:**
Symptom: outdoor hose bib is dripping from the spout when turned off.
Wrong diagnosis: just like a regular faucet, the washer at the front is worn.
Actual fix: on a frost-proof (freeze-proof) sillcock, the valve seat and washer are located at the BACK of the long stem, 6-12 inches inside the wall, not at the front where the handle is. When you unscrew the handle packing nut and pull the stem out, the washer is on the very end of the long stem. Replace that washer (and the brass screw holding it). While you have it apart, inspect the valve seat inside the pipe body with a flashlight. If it is rough or pitted, use a valve seat grinder or replace the entire sillcock. Also critical: a frost-proof sillcock MUST be installed with a slight downward pitch toward the outside so it can drain when shut off. If it is pitched inward (toward the house), water stays in the tube past the valve and freezes, splitting the tube. The leak will not show until spring when you turn it on.

---

## General Construction Field Fixes

### Drywall and Interior

**Drywall nail pops:**
Symptom: small circular bumps or cracks appear on walls or ceilings, usually in newer homes (1-3 years old).
Wrong diagnosis: bad drywall tape, house is falling apart.
Actual fix: nail pops occur when framing lumber shrinks as it dries, and the nails stay in place while the stud moves away from the drywall. The nail head pushes out and creates a bump. Do NOT just spackle over the bump -- it will come back. The proper fix: drive a drywall screw 2 inches above or below the popped nail, pulling the drywall tight to the stud. Then use a nail set to countersink the popped nail below the drywall surface (or pull it out entirely). Now spackle both the screw and the old nail hole. The screw provides the actual holding power -- the original nail is no longer doing its job.

**Squeaky floor:**
Symptom: floor squeaks when walking on it. Drives the homeowner crazy.
Wrong diagnosis: subfloor is separating from the joists, need to rip up the floor and re-nail.
Actual fix: from below (if accessible), have someone walk on the squeaky spot while you watch the subfloor from the basement or crawl space. You will see the subfloor flex away from the joist. Drive a 2-inch drywall screw up through the subfloor into the finish floor at an angle where the gap is. Construction adhesive (PL Premium or Liquid Nails Subfloor) in the gap first is even better. If you cannot access from below (second floor, slab), use Squeeeeek No More screws (O'Berry Enterprises) -- they are designed to drive through carpet and pad into the joist, then the screw head snaps off below the carpet surface. For hardwood floors, Counter-Snap screws drive through the hardwood, grab the subfloor, pull it tight, and snap off below the surface.

**Sticking door -- will not close or latch:**
Symptom: interior door sticks, drags on the frame, or will not latch.
Wrong diagnosis: need to plane the door edge, or the house has settled.
Actual fix: check the hinge screws FIRST. In 80% of sticking door cases, the top hinge screws have pulled out of the jamb because the original screws were short (3/4 inch) and only grabbed into the jamb, not the framing behind it. Replace the top hinge screws (at least the ones closest to the door stop) with 3-inch screws that bite into the jack stud behind the jamb. This pulls the top of the jamb toward the stud and lifts the door back into alignment. Do one screw at a time with the door on. This fix takes 2 minutes and zero tools beyond a drill/driver. Only if the hinge screws are tight and the door still sticks should you consider planing, and even then, check if the jamb is square first using a level.

### Foundation and Structure

**Crack in foundation wall:**
Symptom: homeowner sees a crack in the basement foundation wall and panics.
Wrong diagnosis: house is going to collapse, foundation is failing.
Actual fix: the orientation of the crack tells you almost everything. Vertical cracks (running up and down) and diagonal cracks radiating from window/door corners are almost always from normal concrete shrinkage and settling. They are cosmetic and can be sealed with hydraulic cement or polyurethane crack injection to prevent water intrusion, but they are not structural. HORIZONTAL cracks (running side to side, especially in the middle third of the wall) are a different story -- these indicate lateral pressure from soil, hydrostatic pressure, or frost heave pushing the wall inward. Horizontal cracks that are wider than 1/4 inch or show inward displacement need a structural engineer evaluation. Stair-step cracks in block walls follow the mortar joints and indicate differential settlement -- also get an engineer for these if they are progressing.

### Roof and Exterior

**Roof leak -- where is it actually coming from:**
Symptom: water stain on the ceiling, customer says the roof is leaking.
Wrong diagnosis: replace the shingles in the area above the stain.
Actual fix: the stain location rarely corresponds to the leak location. Water enters at one point and travels along rafters, sheathing, and other surfaces before dripping down at a distant spot. In 90% of roof leaks, the source is a flashing failure, not the field shingles. Check in this order: pipe boot flashings (the rubber boots around plumbing vent pipes crack and split after 10-15 years), step flashing where the roof meets a wall (siding installers often do not properly integrate the step flashing with the wall weather barrier), valley flashing (especially closed-cut valleys where shingles overlap), chimney flashing (counter-flashing that should be embedded in the mortar joint, not surface-mounted with caulk), and skylight flashing. Only after ruling out all flashing sources should you look at the shingle field for missing, cracked, or lifted shingles.

**Ice dams in winter:**
Symptom: icicles hanging from the gutter edge, ice building up at the eave, water leaking into the house at the wall/ceiling junction.
Wrong diagnosis: gutters are blocked, need heated gutter cables.
Actual fix: ice dams are caused by heat loss from the living space warming the roof deck unevenly. Snow melts higher on the roof (where the attic is warm), runs down to the eave (where the roof extends past the exterior wall and is cold), and refreezes into a dam. Water backs up behind the dam and gets under the shingles. The real fix is in the attic: air seal all penetrations (can lights, plumbing vents, electrical boxes, attic hatch) to stop warm air from leaking into the attic, and add insulation to R-49 or higher. The attic should be cold -- the same temperature as outside. Heated gutter cables are a band-aid that burns electricity and does not address the root cause. Proper air sealing and insulation eliminates ice dams permanently.

### Ventilation and Moisture

**Bathroom fan not actually venting outside:**
Symptom: bathroom is always humid, mildew on the ceiling, fan seems to run but makes no difference.
Wrong diagnosis: fan is too small, need a bigger CFM fan.
Actual fix: go up in the attic and trace where the bathroom fan duct goes. In a disturbing percentage of homes (especially those built by production builders in the 1990s-2000s), the bathroom fan duct either terminates in the attic (just blowing moist air into the attic space), is disconnected from the roof cap, or was never connected in the first place. Moist air dumped into the attic causes mold on the sheathing, rotted framing, and destroyed insulation. Connect the duct to a proper roof cap or soffit vent (roof cap preferred -- soffit venting can be drawn back into the attic through other soffit vents). Use insulated flex duct or rigid metal duct to prevent condensation inside the duct. Duct should slope slightly toward the exit point so condensation drains out rather than back into the fan housing.

**Musty crawl space:**
Symptom: crawl space smells musty, may have visible moisture on surfaces, mold on joists or subfloor.
Wrong diagnosis: need more ventilation, open the crawl space vents.
Actual fix: building science has reversed course on crawl space ventilation. In most climates (especially humid ones), vented crawl spaces actually make moisture problems WORSE because you are pulling hot, humid outdoor air into a cool space where it condenses on every surface. The modern best practice is a sealed (encapsulated) crawl space: install a 6-mil or thicker polyethylene vapor barrier on the ground (overlapped 12 inches at seams, sealed with tape, run up the walls 6 inches and attached with termination bar or adhesive), seal the foundation vents closed, and install a dehumidifier rated for the square footage. The crawl space humidity should stay below 60% relative humidity year-round. This approach eliminates musty odors, prevents mold growth, improves indoor air quality, and reduces heating/cooling costs because you are no longer conditioning a leaky space under the house.

### Windows and Insulation

**Condensation between window panes (foggy windows):**
Symptom: double-pane window has a milky, foggy, or wet appearance between the two glass panes.
Wrong diagnosis: something is wrong with the window frame, or the window needs cleaning.
Actual fix: the seal between the two panes of the insulated glass unit (IGU) has failed. When the seal breaks, moist air enters the space between the panes, and the argon or krypton gas that was there for insulation escapes. You cannot fix this with cleaning or caulk -- the entire IGU needs replacement. The good news is that on most modern windows, the IGU is a replaceable component within the existing frame/sash. You do not need to replace the entire window. Measure the glass size, the overall thickness, and the spacer bar width, then order a replacement IGU from a glass supplier. This costs $75-$200 per window depending on size, versus $400-$1,000+ for a full window replacement. The labor to swap the IGU is 30-45 minutes per window. However, if the window frame itself is rotted, damaged, or the hardware is failing, a full replacement may make more sense.

**Exterior door drafty at the bottom:**
Symptom: cold air coming in under an exterior door. Customer can see daylight under the door.
Wrong diagnosis: door is warped, or the house has settled and the door does not fit anymore.
Actual fix: the door sweep or threshold is worn or out of adjustment. Most exterior doors have an adjustable threshold with screws that raise or lower it. Turn the adjustment screws to raise the threshold until it contacts the door sweep evenly across the full width. If the door sweep is torn, cracked, or compressed flat, replace it. On doors without an adjustable threshold, install a new door sweep (surface-mount or wrap-around style) on the bottom of the door. For a proper seal, the sweep should contact the threshold with slight compression when the door is closed. If the gap is uneven (wider on one side than the other), the door or frame is out of square -- check the hinge screws (same fix as the sticking door above) before anything else.

---

## Cross-Trade Pro Tips

**When the real problem is not in your trade:**
Experienced techs learn to recognize when the symptom is in their trade but the cause is in another. A few common crossovers:

- HVAC tech called for humidity problems: check the bathroom fans (plumbing/general), dryer vent (general), and crawl space moisture (general) before looking at the HVAC system itself.
- Electrician called for a tripping breaker on an outdoor circuit: check if the conduit is full of water (plumbing/general) before looking for a wiring fault.
- Plumber called for a water stain on a ceiling: verify it is actually plumbing and not a roof leak, condensation from an HVAC duct, or an ice dam. Water stains on exterior walls near the roofline are almost never plumbing.
- HVAC tech called for poor airflow in one room: check if the ductwork in the attic or crawl space is crushed, disconnected, or was never connected. Also check if someone closed the damper on that run and forgot.

**Temperature and weather affect everything:**
- Electrical connections expand and contract with temperature cycles, causing intermittent faults that only show up in extreme heat or cold.
- Plumbing leaks at solder joints may only appear when the system goes from cold to hot (thermal expansion opens a pinhole that is sealed when cold).
- HVAC refrigerant pressures are meaningless without knowing the outdoor ambient and indoor wet bulb temperatures. A system that looks "low on charge" on a cool morning may be perfectly charged on a hot afternoon.
- Foundation cracks open and close with seasonal ground moisture changes. Measure and photograph them in different seasons before concluding they are active.

**The "last tech" left you a surprise:**
- Previous tech used duct tape on a flue vent: duct tape adhesive fails at 140 degrees F. The joint separated and combustion gases are leaking. Re-do with aluminum foil tape or proper mechanical fasteners.
- Previous tech jumped out the pressure switch and left the jumper: the furnace runs but has zero safety protection against blocked vents or heat exchanger failure. Remove the jumper immediately and fix the actual problem.
- Previous tech installed a 30A breaker on 14 AWG wire: the wire is rated for 15A. This is a fire hazard. The breaker should match the wire gauge, not the load.
- Previous tech spliced romex with electrical tape inside a wall: no box, no wire nuts, just tape. This is a code violation and a fire waiting to happen. Open the wall, install a junction box, and make proper connections.
- Previous tech used a sharkbite fitting in a wall without access panel: sharkbite fittings are not universally accepted inside walls and they can fail. If local code allows them in walls, at minimum install an access panel.

**The homeowner "fixed" it themselves:**
- Homeowner poured drain cleaner down a slow drain repeatedly: chemical drain cleaners damage pipes (especially older cast iron and ABS), destroy the chrome on drain components, and create a chemical hazard for the next person who works on the drain. If the drain is still slow after chemicals, it needs mechanical clearing (snake or jetter), and warn them about the chemicals before you open anything.
- Homeowner replaced a thermostat and now the AC runs but heat does not: they probably connected the wires to the wrong terminals. The most common error is swapping W (heat) and Y (cool), or not connecting the C (common) wire properly on a smart thermostat. Pull the old thermostat base off the wall and compare wire positions to the new one.
- Homeowner added refrigerant themselves with a recharge kit: those kits (A/C Pro, etc.) are R-134a with leak sealer mixed in. The leak sealer will clog the TXV, plug the filter drier, and contaminate the recovery machine. If someone used one of these on a home system (they are meant for automotive), the system may need a full flush, new TXV, new filter drier, and fresh charge.
- Homeowner caulked around a leaking toilet base: now you cannot tell if the wax ring is leaking because the water is trapped under the caulk. Pull the toilet, check the flange and wax ring, reset properly, and caulk with a gap at the back for future leak detection.

**Diagnostic shortcuts that experienced techs use:**
- Furnace flame color tells you a story: blue with small yellow tips is normal natural gas combustion. Lazy yellow/orange flames mean insufficient primary air (dirty burners, blocked orifices, or wrong orifice size). Lifting/floating flames mean too much primary air. A flame that rolls out the front of the burner box when the blower starts indicates a cracked heat exchanger (combustion gases are finding a new path when the blower pressurizes the cabinet).
- On any HVAC motor that will not start, check the capacitor first: a $15 capacitor is the most common failure point in any HVAC system. Carry a universal capacitor kit (assorted microfarad values) and a capacitor tester. You will use them every day.
- On any electrical problem that is intermittent: backstab connections are the cause until proven otherwise. Pull every receptacle and switch on the circuit and check for push-in backstab connections. Pigtail them to screw terminals. This single fix resolves an enormous percentage of intermittent electrical problems including AFCI trips, flickering lights, and dead outlets.
- Smell the air at the return grille: you can detect mold, gas leaks, sewer gas, electrical burning, and overheating components by smell alone. Train your nose -- it is one of the best diagnostic tools you have.
- Touch the suction and liquid lines at the outdoor unit: the suction line (big one) should be cold and sweating on a hot day. The liquid line (small one) should be warm to hot. If the suction line is room temperature, the compressor may not be running or the charge is very low. If the liquid line is barely warm, the system may be overcharged or the condenser fan is not running.
