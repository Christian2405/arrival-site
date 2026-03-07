# Appliance Expert Diagnostic Knowledge

## Washer Troubleshooting

### Top-Load vs Front-Load: What You Need to Know

After fifty years of fixing washing machines, the single biggest shift I have seen is the move from top-load agitator machines to front-load and high-efficiency top-load washers. The failure modes are fundamentally different and you need to approach them differently.

**Top-load traditional (agitator style):** These machines use a transmission (also called a gearcase) that converts the motor rotation into the back-and-forth agitation stroke and the high-speed spin. The transmission is filled with oil and has internal gears, a cam mechanism, and a brake assembly. When the transmission fails, you will see oil leaking from the bottom of the tub, the agitator will stop moving or move weakly in one direction, or the machine will not shift from agitate to spin. On Whirlpool/Kenmore direct-drive machines (the most common top-loaders made from 1984 to the mid-2010s), the transmission is coupled directly to the motor through a motor coupling -- a small plastic and rubber coupler that absorbs the shock between the motor and transmission. This motor coupling is the single most common failure part on direct-drive Whirlpool top-loaders. It costs about three dollars and takes twenty minutes to replace. Symptoms: machine fills and hums but does not agitate or spin, or agitates weakly.

**Top-load HE (no agitator, impeller plate):** These machines use an impeller plate on the bottom of the wash basket and rely on the clothes rubbing against each other to clean. The main issues are: the bearing and shaft seal assembly (called a hub kit on some brands), the suspension rods or springs that dampen vibration, and the drain pump. These machines are much more sensitive to unbalanced loads because they spin at higher RPMs (up to 1100 RPM) compared to traditional top-loaders (600-700 RPM).

**Front-load:** Front-loaders use a large main bearing pressed into the rear tub half, a shaft connected to the drum spider (the three-armed metal piece bolted to the back of the drum), and a direct-drive motor or belt-drive motor. The main bearing is the most expensive and labor-intensive repair on any front-loader -- typically 3-4 hours labor plus a $150-$300 bearing kit. Front-loaders also have a rubber door boot (bellow) that seals the door opening, and this boot commonly tears, develops mold, or leaks.

### Drain Pump Issues

The drain pump is the most commonly failed component across all modern washing machines, regardless of brand or type. Here is why: the pump has a small impeller spinning at high speed, and it encounters coins, bobby pins, bra underwires, small screws, and pocket debris that damage the impeller or jam the pump.

**Symptoms of a failing drain pump:**
- Machine fills but will not drain -- water sits in the tub after the wash cycle
- Machine drains very slowly
- Loud humming or buzzing during the drain cycle
- Error codes: Whirlpool F21 or F9E1, LG OE, Samsung 5E or SE, GE E2 or drain error

**Diagnosis:** Remove the pump and inspect the impeller. On most front-loaders, the pump is accessible from the front lower panel. On most top-loaders, you need to lay the machine on its side or access from the back. Check the impeller for cracks, broken fins, or debris. Spin the impeller by hand -- it should turn freely with slight magnetic resistance. If it is seized or grinds, replace the pump.

**Important:** Before replacing the pump, always check the drain hose and the coin trap (filter) if the machine has one. Samsung and LG front-loaders have an accessible filter on the front lower-right. Whirlpool front-loaders often do not have a user-accessible filter -- you need to pull the pump to clear debris.

### Door Lock Mechanisms (Front-Load)

Every front-loader has a door lock (also called a door latch or door switch assembly) that must engage before the machine will start. The lock serves two purposes: it proves the door is closed (safety interlock) and it physically locks the door so it cannot be opened during the cycle (especially during high-speed spin).

Most door locks use a PTC (Positive Temperature Coefficient) heating element that expands a bimetallic strip to push the locking pin into the door catch. This takes 3-8 seconds after you press start -- you will hear a click when it locks. The PTC element wears out over time and is the most common door lock failure.

**Testing the door lock:**
- Unplug the machine. Remove the door lock (usually two Torx screws behind the door boot clamp)
- Check continuity across the lock switch contacts in the locked and unlocked positions
- On a three-wire lock: two wires are for the PTC heater (you should read 500-1500 ohms across them at room temperature), and the third wire completes the interlock circuit when locked
- If the PTC resistance is open (infinite ohms), the lock will never engage. Replace it

**Common door lock error codes:** Whirlpool F5E2 or F5E1, LG dE, Samsung dC or dE, GE E4.

### Unbalanced Load Diagnosis

An unbalanced load during spin is the most common customer complaint on HE washers. The machine detects the imbalance through a rotor position sensor or accelerometer on the tub, and it will attempt to redistribute the load by stopping, adding water, and re-spinning. If it fails after 3-6 attempts, it throws an error code and stops.

**When the machine is actually fine and the load is the problem:**
- A single heavy item (jeans, towel, blanket) bunched on one side
- Very small loads that cannot distribute evenly
- A mix of heavy and lightweight items

**When there is a mechanical issue causing persistent imbalance:**
- Broken suspension springs or shock absorbers (front-load) -- the tub bounces excessively during spin. You should be able to push down on the tub and it returns smoothly without bouncing more than once or twice
- Broken or stretched suspension rods (top-load HE) -- same concept, dampens tub movement
- Worn main bearing (front-load) -- grab the drum through the door opening and try to move it up and down. Any play means the bearing is worn. A good bearing has zero detectable play
- Broken drum spider (front-load) -- the aluminum spider corrodes over time (especially in humid environments or with liquid detergent overuse). When it breaks, the drum wobbles severely. Pull the drum from the tub and inspect all three arms of the spider for cracks at the hub or arm base

### Inlet Valve Failures

The water inlet valve controls hot and cold water flow into the machine. Modern valves are electrically operated solenoid valves -- 120VAC energizes the solenoid coil, which lifts a plunger off the valve seat to allow water flow.

**Common failures:**
- Valve will not open: Check for 120VAC at the valve coil during fill. Voltage present but no water means the valve is stuck closed or the inlet screen is clogged. Pull the hoses off and inspect the screens -- sediment buildup is very common on well water
- Valve will not close: The valve leaks water into the tub when the machine is off. This is a mechanical failure of the valve diaphragm or plunger and requires replacement. A leaking inlet valve will slowly fill the tub and can cause overflow if left unattended
- Valve solenoid coil resistance: Should read 500-1500 ohms across the coil. Open (infinite ohms) means the coil is burned out

## Dryer Troubleshooting

### Gas vs Electric Differences

The heating system is the only fundamental difference between gas and electric dryers. Everything else -- the motor, drum, belt, rollers, blower, moisture sensor, control board -- is essentially the same.

**Electric dryer heating:** A heating element (nichrome wire coil) typically rated at 4500-5400 watts draws 20-25 amps on a 240V circuit. The element is contained in a housing with a high-limit thermostat and cycling thermostat. Measure element resistance: a good 5000-watt element at 240V should read about 11-12 ohms (R = V^2 / P = 57600 / 5000 = 11.5 ohms). Open (infinite ohms) means the element is broken. Visually inspect for breaks in the coil -- the coil can sag and touch the housing, creating a ground fault that trips the breaker.

**Gas dryer heating:** A gas burner assembly consists of the gas valve (with two or three solenoid coils), an igniter (flat silicon carbide or round ceramic type), and a flame sensor. The igniter must draw enough current to open the gas valve -- typically 3.2 to 3.6 amps for a good igniter. The gas valve coils (also called booster coils or coil kit) are energized by the flame sensor circuit through the igniter. There are usually two coils on older models (holding coil and booster coil) and three on some newer models. When the coils fail, the symptom is intermittent heating: the dryer lights initially, runs for a few minutes, then the flame goes out and will not relight until the dryer cools down. This is the most common gas dryer repair. The coil kit costs about $15-$25 and takes twenty minutes to replace. Always replace the coils as a set.

### Vent Restriction Diagnosis

A restricted vent is the root cause of the majority of dryer service calls. Before replacing any part, always check the vent first.

**Back pressure test:** Run the dryer on high heat with no load. Go to the exterior vent termination and hold your hand in front of the exhaust. You should feel a strong, warm airflow. If the flow is weak, the vent is restricted. For a more precise measurement, drill a small hole in the vent pipe near the dryer and insert a manometer probe. Normal back pressure is 0.5-1.0 inches of water column (WC). Above 2.0 inches WC, the vent is significantly restricted and will cause overheating, long dry times, and thermal fuse failures.

**Common vent restrictions:**
- Lint buildup in the vent pipe -- especially at elbows and transitions
- Crushed or kinked flex hose behind the dryer
- Bird or rodent nests in the exterior vent hood
- Vent runs that are too long -- maximum recommended is 35 feet for 4-inch rigid duct, minus 5 feet for each 90-degree elbow and 2.5 feet for each 45-degree elbow

### Thermal Fuse vs Cycling Thermostat vs High Limit

These three components are the most commonly confused parts in dryer diagnosis. Understanding what each one does will save you from replacing the wrong part.

**Thermal fuse:** A one-time-use safety device. When it opens, it does not reset. On most dryers, the thermal fuse is on the blower housing or exhaust duct. When it blows, the dryer will not heat (on some brands, it will not run at all). Test with a continuity check -- it should have continuity (zero ohms). If open, replace it. But always find out why it blew -- a restricted vent is the cause 90% of the time. If you replace the fuse without fixing the vent restriction, it will blow again within weeks.

**Cycling thermostat:** This is the normal operating thermostat that cycles the heater on and off to maintain the selected temperature. It is a resettable bimetallic disc. When the air temperature reaches the upper setpoint (approximately 155°F for high heat), the cycling thermostat opens and shuts off the heater. When the temperature drops to the lower setpoint (approximately 135°F), it closes and turns the heater back on. If the cycling thermostat fails open, the dryer will not heat. If it fails closed (stuck closed), the dryer will overheat. Test with continuity at room temperature -- it should have continuity. Then use a heat gun to warm it and verify it opens at approximately the rated temperature.

**High-limit thermostat:** A safety backup. If the cycling thermostat fails closed and the dryer overheats, the high-limit thermostat opens at approximately 250°F. On most models, the high limit is resettable -- it will reset once the dryer cools. On some models, the high limit is a one-time thermal fuse. If the high-limit keeps tripping, the cycling thermostat is likely failed closed, or the vent is restricted.

### Gas Valve Coils (Booster Coils)

On gas dryers, the gas valve solenoid coils are the most common part failure. There are typically two coils stacked on the valve stem. The first coil (booster coil) provides a strong pull to initially open the valve against the spring and gas pressure. The second coil (holding coil) maintains the valve open with less current. The booster coil energizes first, then both coils hold together. After a few seconds, the booster drops out and the holding coil alone keeps the valve open.

**Intermittent no-heat symptom:** The dryer ignites, burns for a few minutes, then the flame goes out. The igniter glows again but the gas valve does not open. This cycle repeats: glow, no gas, glow, no gas. Eventually the dryer may light again after cooling for twenty minutes. This is the classic coil failure pattern. The coils develop increased resistance when hot, and the weakened magnetic field cannot open the valve. When they cool down, resistance drops enough to work again.

**Diagnosis:** Watch the igniter through the front panel or burner access. If the igniter glows but the valve does not open, and you have confirmed 120VAC at the coils, the coils need replacement. Coil resistance should be 300-2000 ohms each. But resistance alone does not catch heat-related failures -- the real test is watching the operation.

## Refrigerator Troubleshooting

### Sealed System Diagnosis

The sealed system (compressor, condenser, evaporator, metering device, and refrigerant lines) is the heart of the refrigerator. Before condemning the sealed system, always verify that the simpler components are working: the defrost system, the evaporator fan, the condenser fan, and the temperature controls.

**When to suspect a sealed system problem:**
- Compressor runs continuously but the refrigerator is warm
- Compressor runs but both the evaporator and condenser are the same temperature (restriction or no refrigerant)
- Compressor will not start (clicks and shuts off on overload)
- Compressor runs but you hear gurgling or hissing noises (usually a restriction at the metering device or a partial leak)

### Start Relay Shake Test

The compressor start relay (on single-speed compressors with a PTC relay or current relay) is one of the most common failures. The PTC (Positive Temperature Coefficient) relay is a solid-state device that provides the starting boost to the compressor start winding. When it fails, the compressor tries to start on the run winding alone, cannot get going, draws locked-rotor amps, and the overload protector kicks it off within 2-5 seconds. You hear a click (compressor trying to start), a hum for a few seconds, then another click (overload tripping).

**The shake test:** Unplug the refrigerator. Pull the relay off the compressor pins. Hold it upright (the way it mounts on the compressor) and shake it gently. If you hear a rattle inside, the PTC disc has broken and the relay is bad. A good relay makes no rattling sound. This is a quick field test with about 90% accuracy. For a definitive test, measure resistance across the relay start contacts -- a good PTC relay reads about 3-12 ohms cold between the start terminals. If it reads open (infinite ohms), it is defective.

**Important:** The overload protector is usually attached to the relay or mounted separately on the compressor. If the compressor has been clicking on and off repeatedly, the overload may be open from overheating. Let it cool for 30 minutes and test continuity. If open when cool, replace it. If closed when cool, it was just thermally tripped -- the relay failure is the root cause.

### Defrost System Testing

Modern frost-free refrigerators use a defrost system to prevent ice buildup on the evaporator coil. The three components of the defrost system are the defrost timer (or adaptive defrost board), the defrost heater, and the defrost termination thermostat (also called the bimetal thermostat).

**Defrost timer/board:** Initiates defrost at set intervals. Mechanical timers trigger every 6-12 hours of compressor run time. Adaptive defrost boards (ADC -- Adaptive Defrost Control) use a more sophisticated algorithm based on door openings, compressor run time, and other factors. To test, manually advance the timer into defrost (turn the timer shaft with a screwdriver or press the test button on the ADC board). The compressor should stop and the defrost heater should energize.

**Defrost heater:** A resistance heater (calrod type or glass tube type) mounted under or within the evaporator coil. Typical resistance is 20-40 ohms. Check continuity -- if open (infinite ohms), the heater is burned out and the evaporator will frost over completely, blocking airflow. On Samsung and LG models, the heater is often a glass tube type that is very fragile.

**Defrost termination thermostat (bimetal):** A normally closed thermostat mounted on the evaporator tubing. It opens at approximately 45-50°F to end the defrost cycle and prevent the evaporator from getting too warm. At room temperature, it should have continuity (closed). At 50°F and above, it should be open. If the bimetal fails open (stuck open), the defrost heater will never energize and the evaporator will frost up -- same symptom as a bad heater. If the bimetal fails closed (stuck closed), the defrost heater will run too long and can melt plastic parts or cause a water leak.

### Compressor Diagnosis

**Amp draw test:** With the compressor running, measure amp draw on the common wire using a clamp meter. Compare to the rating plate on the compressor. A healthy compressor typically draws close to the RLA (Rated Load Amps) on the nameplate. If it draws significantly above RLA (approaching LRA -- Locked Rotor Amps), the compressor is struggling -- possibly due to high head pressure (dirty condenser), a restriction, or internal mechanical wear. If it draws well below RLA, the compressor may be running but not pumping (broken valve reed or worn cylinder).

**Winding resistance test:** Unplug the refrigerator. Remove the start relay from the compressor. You will see three pins: Common (C), Start (S), and Run (R). Measure resistance between all three combinations. The rule is: C to S plus C to R equals S to R (approximately). Typical values for a domestic refrigerator compressor: C to R = 5-15 ohms, C to S = 10-30 ohms, S to R = 15-45 ohms. If any winding reads open (infinite), the compressor has a burned open winding. If any winding reads near zero (less than 1 ohm), it has a shorted winding.

**Megohm test (insulation resistance):** With the relay removed, set your megger or insulation resistance tester to 500V DC. Measure from each compressor pin to the compressor housing (ground). A good compressor should read infinity (or at least 500 megohms). Any reading below 2 megohms indicates a grounded winding -- the insulation has broken down and the compressor must be replaced. Do not skip this test when the compressor will not start, especially after an electrical event (lightning strike, power surge).

## Dishwasher Troubleshooting

### Bosch Aquastop E15 Fix

The Bosch E15 error code is one of the most common service calls on Bosch dishwashers. E15 means the Aquastop system has detected water in the base pan. Bosch dishwashers have a polystyrene float in the base pan -- when water accumulates, the float rises and activates a microswitch that shuts down the machine and energizes the drain pump continuously.

**The fix:**
1. Unplug the dishwasher and shut off the water supply
2. Pull the dishwasher out and tilt it backward approximately 45 degrees to drain water from the base pan into a towel. You will hear the water sloshing around in the base
3. Tilt it to the left side as well to get all the water out
4. Find the source of the leak -- the most common causes are: a loose or cracked sump seal, a leaking spray arm seal, a cracked pump housing, or a leaking water inlet connection
5. Fix the leak, reinstall, and run a test cycle

**Important:** On many Bosch models, the drain pump will run continuously whenever the machine is plugged in with E15 active. This is by design -- the Aquastop system is trying to pump the base pan dry. But the base pan does not have a drain connection, so the pump just runs and runs. Tilting the machine is the only way to empty the base pan.

### Drain Pump Issues

Dishwasher drain pumps fail for the same reasons as washer drain pumps: glass shards, broken dishes, food debris, and small objects that jam or damage the impeller.

**Symptoms:** Water standing in the bottom of the tub after the cycle, the machine gives a drain error (E24 on Bosch, 5-2 or F5E2 on Whirlpool/KitchenAid, OE on LG).

**Diagnosis:** Remove the filter basket and inspect the sump area. On most dishwashers, you can see the drain pump impeller through the sump opening. Remove any debris. Check for continuity across the drain pump motor windings -- you should read 5-40 ohms. Open means the motor is burned out.

**Check valve:** Many dishwashers have a check valve on the drain pump outlet or in the drain hose. If the check valve is stuck closed, water will not drain even with a good pump. Remove the drain hose from the pump and blow through it -- you should be able to blow air through easily.

### Spray Arm Diagnosis

Poor cleaning performance is usually not a spray arm failure -- it is usually low water pressure, a clogged inlet valve screen, or too much food debris in the filter. But when the spray arms do fail:

**Check for blockage:** Remove all spray arms (they typically snap or unscrew off). Hold each arm up and look through the nozzle holes against a light. Clogged holes are the most common issue. Clean with a toothpick or thin wire -- never use anything that might break off inside the arm.

**Check for free rotation:** Reinstall each arm and spin it by hand. It should spin freely with no wobble or drag. A worn bearing hole will cause the arm to wobble and not spin properly during the cycle.

**Check the water supply:** While the machine is running, open the door mid-cycle (carefully -- hot water). The tub should have 1-2 inches of water in the bottom, covering the heating element. If the water level is too low, the spray arms will not have enough pressure. Check the float switch, the inlet valve, and the water supply pressure (minimum 20 PSI, recommended 40-60 PSI).

### Heating Element Testing

The heating element in a dishwasher serves two purposes: it heats the water during the wash cycle (some models) and it provides the heat for the drying cycle. The element is a calrod-style loop in the bottom of the tub.

**Testing:** Unplug the dishwasher. Disconnect one wire from the element terminal. Measure resistance across the two element terminals. A good element reads 12-30 ohms (varies by model and wattage). Open (infinite ohms) means the element is burned out. Also test from each terminal to ground (the element housing or the tub) -- any continuity to ground means the element is shorted and must be replaced. A grounded element will trip the breaker or GFCI.

## Oven and Range Troubleshooting

### Temperature Sensor Resistance Testing

Modern ovens use a resistance temperature detector (RTD) instead of a thermocouple or capillary-tube thermostat. The RTD is a thin metal probe that extends into the oven cavity. Its resistance changes linearly with temperature.

**At room temperature (70°F / 21°C):** The sensor should read approximately 1080-1100 ohms for most brands (GE, Whirlpool, Frigidaire, Samsung, LG). Some sources say 1100 ohms at 77°F. The exact value varies slightly by brand, but 1080-1100 is the standard range you will see across the industry.

**At 350°F:** Approximately 1600-1650 ohms.

**At 500°F:** Approximately 2000-2050 ohms.

**Testing:** Unplug the oven. Disconnect the sensor plug at the back of the oven (or behind the control panel). Measure resistance across the two sensor wires. If the resistance is significantly off (more than 5% from expected), or if the reading is erratic (jumps around), or if it reads open or shorted, replace the sensor. Also check the wiring harness for damage -- a broken or chafed wire in the harness gives the same symptoms as a bad sensor.

**Symptoms of a bad sensor:** Oven will not heat (if the sensor reads open, the board sees infinite resistance and assumes extremely high temperature -- it will not turn on the heat). Oven overheats (if the sensor reads too low, the board thinks the oven is cooler than it actually is). Oven temperature is inaccurate (if the sensor resistance is drifted, the oven will be consistently too hot or too cold by a fixed amount).

### Gas Oven Igniter Amp Draw

On gas ovens and ranges, the bake and broil igniters must draw enough current to heat up and also to open the gas valve safety solenoid. This is a critical concept that many technicians miss: the igniter is not just there to light the gas -- it is in series with the gas valve bimetal safety, and the current flowing through the igniter heats the safety bimetal to open the valve.

**Required amp draw:** A good igniter must draw 3.2 to 3.6 amps to open the gas safety valve on most brands. Below 3.0 amps, the bimetal safety will not open and gas will never flow, even though the igniter glows. This is the most common gas oven failure: the igniter glows orange but gas never lights. The igniter has enough resistance to glow but not enough current to open the safety valve.

**Testing:** Clamp your amp meter around one of the igniter wires. Turn on the oven and watch the amp draw as the igniter heats up. It will start high (around 3.5-4.0A when cold) and drop as the igniter heats and resistance increases. If the steady-state draw drops below 3.0-3.2A, the igniter needs replacement even though it still glows.

**Flat igniters vs round igniters:** Older ovens used round (Norton-style) igniters. Newer ovens use flat (mini) igniters. They are not interchangeable without a conversion kit. Flat igniters heat faster and typically have a longer life.

### Relay Board Failures

On electric ovens and ranges, the relay board (also called the power board or element control board) switches the high-voltage circuits to the bake and broil elements. The main control board sends a low-voltage signal to the relay board, which switches the 240V circuit through a mechanical relay.

**Common failures:** Relay contacts weld shut (the element stays on continuously -- dangerous), relay contacts burn open (the element will not heat), or solder joints crack on the board from thermal cycling. If the oven heats to full temperature and does not shut off, immediately turn off the breaker -- a welded relay is a fire hazard.

**Diagnosis:** Listen for the relay click when the oven calls for heat. No click means the relay is not being energized (check the signal from the main board) or the relay coil is open. Remove the relay board and visually inspect for burned or discolored areas, cracked solder joints, and damaged relay contacts. On some boards, the relays can be desoldered and replaced individually -- this is a cost-effective repair when the rest of the board is in good condition.

## Diagnostic Mode Entry Procedures

### LG Washers (Front-Load and Top-Load)

**Front-load (2015+):** Press and hold Spin Speed and Soil Level simultaneously for approximately 3 seconds until the display shows "tE" or a code. Use the Spin Speed button to scroll through error codes. Press Start/Pause to run individual test cycles. Press Power to exit.

**Top-load (2018+):** Press and hold the Spin Speed and Water Temp buttons simultaneously for 3 seconds. The display will show stored error codes. Scroll with Spin Speed.

### Samsung Washers

**Front-load:** Turn the cycle selector knob to the Rinse position. Press and hold the Temp and Delay End buttons for 3 seconds. The display shows "d" for diagnostic mode. Press Start to begin the self-diagnostic test, which runs through each component: door lock, fill, wash, drain, spin.

**Top-load:** With the unit in standby (plugged in but not running), press and hold Delay End + Soil Level for 3 seconds. On some models it is Delay End + Option for 3 seconds.

### Whirlpool / Maytag / KitchenAid Washers

**Front-load (Duet and newer):** With the machine in standby, turn the cycle selector knob three clicks clockwise, three clicks counterclockwise, three clicks clockwise within 12 seconds. The console LEDs will all illuminate and the machine enters diagnostic mode. Press Start to begin the automatic test cycle.

**Top-load (VMW models, Cabrio):** With the machine in standby, rotate the cycle selector dial counterclockwise one click, clockwise three clicks, counterclockwise one click, clockwise one click -- all within 6 seconds. The LEDs will flash to indicate diagnostic mode.

### GE / GE Profile Washers

**Front-load (2015+):** Press and hold the Signal and Delay Start buttons simultaneously for 3 seconds. The display shows "t" for test mode. Turn the cycle knob to scroll through test codes. Press Start to run the selected test.

**Top-load (2018+):** Turn the cycle knob to the 12 o'clock position. Press and hold the Start button for 5 seconds. If that does not work, try rotating the knob one full turn clockwise, then back one click counterclockwise.

### Samsung Refrigerators

Press and hold the Energy Saver and Freezer buttons (top two buttons on the display panel) simultaneously for approximately 8-10 seconds. The display will go into a forced defrost mode ("Fd" on the display). This is particularly useful for Samsung refrigerators that have iced-up evaporators -- a very common problem with Samsung French-door models from 2014-2020.

### LG Refrigerators

Press and hold the Refrigerator and Ice Plus buttons simultaneously for 5 seconds. The display will scroll through error codes. On some models, you need to press Freezer and Colder simultaneously.

### Whirlpool / Maytag Dryers

Press and hold the Start button for 5 seconds while the dryer is in standby. On newer models with a diagnostic LED on the control board, press and hold the cycle selector for 5 seconds. The board will flash error codes through the LED.

## Repair Time Estimates and Part Availability

**Washer drain pump replacement:** 30-60 minutes. Pump is widely available for all brands, typically $25-$60.

**Washer door lock replacement:** 20-30 minutes. Door locks are brand-specific and usually in stock, $30-$80.

**Washer main bearing replacement (front-load):** 3-4 hours. Requires complete tub disassembly. Bearing kit $80-$200. This is the repair where you need to have a conversation with the customer about whether it is worth it on an older machine.

**Dryer gas valve coil kit:** 20-30 minutes. Coil kit $15-$25. One of the most profitable service calls in appliance repair.

**Dryer heating element:** 30-45 minutes. Element $20-$50.

**Dryer thermal fuse:** 15-20 minutes. Fuse $5-$15. But always check the vent -- do not just replace the fuse and leave.

**Refrigerator start relay:** 5-10 minutes. Relay $10-$30. The easiest repair in appliance service.

**Refrigerator defrost heater:** 45-60 minutes. Heater $30-$60. Requires removing the evaporator cover and all frozen food from the freezer.

**Dishwasher drain pump:** 30-45 minutes. Pump $30-$70.

**Oven igniter:** 20-30 minutes. Igniter $20-$40. Handle with care -- do not touch the igniter element with bare fingers.

**Oven temperature sensor:** 10-15 minutes. Sensor $15-$30.

**Part availability note:** Samsung and LG parts can be difficult to source after the model goes out of production (typically 7-10 years). Whirlpool parts have the best long-term availability -- parts for 20+ year old machines are often still available. GE/Haier parts availability has improved since the Haier acquisition. Bosch parts are reliably available but tend to be more expensive. For all brands, always check the model number and cross-reference the part number before ordering -- manufacturers frequently use different parts for what appears to be the same model with different serial number ranges.
