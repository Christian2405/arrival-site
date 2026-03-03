# HVAC Expert Diagnostic Knowledge

## Furnace Diagnostics

### Gas Furnace Startup Sequence

Every gas furnace follows the same fundamental ignition sequence. Understanding this sequence is the single most important diagnostic skill because when a furnace fails, it almost always fails at a specific step. Here is the complete sequence:

1. **Thermostat calls for heat** -- The R-W circuit closes, sending 24VAC to the furnace control board. On a communicating system (Carrier Infinity, Trane ComfortLink, Lennox iComfort), the thermostat sends a digital signal instead. Verify 24VAC between R and W at the board terminals. If you get 24V there but the furnace does nothing, the board is likely bad.

2. **Inducer motor (draft inducer) starts** -- The control board energizes the inducer motor to purge the heat exchanger of residual gases and establish draft. The inducer should reach full speed within 15-30 seconds. Listen for bearing noise, grinding, or the motor struggling to start (bad capacitor on PSC inducer motors, or failing ECM module on variable-speed inducers). Measure voltage at the inducer -- you should see 120VAC. If the inducer hums but does not spin, check the capacitor or look for a seized bearing.

3. **Pressure switch closes** -- Once the inducer creates sufficient draft, the negative pressure pulls the pressure switch diaphragm closed. The switch proves that combustion gases will vent properly. Normal pressure switch ratings are -0.40" to -1.0" WC for single-stage, -1.0" to -2.0" WC for two-stage high fire, and -0.20" to -0.50" WC for 90%+ condensing furnaces. If the pressure switch will not close: check the inducer for proper operation, check the drain hose/trap on condensing furnaces (a clogged condensate drain is the number one cause of pressure switch failures on 90%+ furnaces), check the vent pipe for blockage (bird nests, ice in winter, disconnected joints), and check the pressure switch hose for cracks, water, or blockage. You can jumper the pressure switch briefly to confirm the rest of the sequence works, but never leave it jumped -- that switch protects against CO poisoning.

4. **Hot surface igniter (HSI) heats up** -- The board sends 120VAC to the igniter for a pre-heat period, typically 15-60 seconds depending on the board timing. Silicon carbide igniters glow bright orange (they are fragile -- never touch with bare fingers as skin oil creates hot spots that cause cracking). Silicon nitride igniters (blue-gray color, used in newer furnaces) are more durable and heat faster. Measure resistance: a good silicon carbide igniter reads 40-150 ohms cold. A good silicon nitride reads 10-25 ohms cold. Open (infinite ohms) means replace. If the igniter glows but the gas valve does not open, the board may have a timing issue or the flame sensor circuit may be open.

5. **Gas valve opens** -- After the igniter pre-heat period, the board energizes the gas valve (24VAC). You should hear a click and then a whoosh as gas ignites. If the valve does not open: verify 24VAC at the valve terminals during the ignition window (the board only sends voltage for a few seconds). No voltage means the board is not sending the signal. Voltage present but no gas means: bad gas valve, no gas supply (check manual shutoff, check meter), or gas pressure too low to overcome the valve spring.

6. **Flame sensor proves flame** -- The flame sensor is a thin metal rod that sits in the burner flame. It works by flame rectification: the flame allows a tiny DC microamp current to flow from the sensor to ground through the burner. Normal flame sense current is 1-6 microamps (measure with your meter in DC microamp mode in series with the flame sensor wire). Below 1 microamp, the board will shut down the gas valve within 4-7 seconds. A dirty flame sensor is the single most common furnace repair. Clean it with fine emery cloth or a dollar bill -- never use sandpaper or steel wool. If flame current is low even with a clean sensor: check the burner ground (rust, paint on mounting screws), check the flame -- it must engulf the sensor rod, and check for a cracked sensor insulator.

7. **Blower motor starts after delay** -- The board waits 30-90 seconds (adjustable on most boards via DIP switches or jumpers) for the heat exchanger to warm up, then starts the blower. This delay prevents blowing cold air. On two-stage furnaces, the blower may start at a lower speed for first stage and ramp up for second stage. After the thermostat is satisfied and the gas valve closes, the blower continues to run for 60-180 seconds to extract remaining heat from the heat exchanger (blower off delay).

### Common Furnace Problems by Age

**0-5 years (installation issues dominate):**
- Improper gas pressure -- always check manifold pressure on new installs. Natural gas should be 3.5" WC for most manufacturers. LP should be 10.0" WC. Carrier and Bryant specify 3.5" NG / 10.0" LP. Goodman often specifies 3.5" NG / 10.0" LP. Rheem sometimes specifies 3.2" NG. Always check the rating plate.
- Undersized or oversized ductwork causing high static pressure, limit switch tripping, and short cycling
- Improper venting (wrong pipe size, too many elbows, improper termination clearances)
- Wiring errors: reversed line and load on condensate pump, missing common wire to thermostat

**5-10 years:**
- Flame sensor fouling -- annual cleaning is the best preventive measure
- Run capacitors failing on PSC blower motors and inducer motors. A weak capacitor (more than 10% below rated microfarads) causes the motor to run hot, draw high amps, and eventually fail
- Igniter failure -- silicon carbide igniters commonly fail in this age range. Replace with silicon nitride if available for that model
- Thermostat battery failure causing erratic operation

**10-15 years:**
- Control board failures -- look for burnt relay contacts, blown fuses on the board, bulging capacitors, or discolored areas on the circuit board
- Igniter replacement (second round)
- Inducer motor bearings wearing out -- listen for rumbling or squealing
- Condensate drain issues on 90%+ furnaces from years of buildup
- Blower motor capacitor or motor failure

**15-20 years:**
- Heat exchanger cracks -- especially on the secondary (condensing) heat exchanger on 90%+ furnaces. Carrier secondary heat exchangers from the early 2000s (models 58MVC, 58MVP) had known issues
- Inducer motor replacement
- Gas valve failures become more common
- At this age, a major component failure often means replacement is more cost-effective than repair. A heat exchanger replacement is typically 60-70% of the cost of a new furnace

### Heat Exchanger Inspection

Visual inspection alone is not sufficient. Use a combustion analyzer to check CO levels in the supply air (not flue gas). Any CO in the supply air above 0 PPM indicates a cracked heat exchanger. With the blower running and burners firing, use a mirror and flashlight to look for visible cracks in the primary heat exchanger cells. Common crack locations by brand:

- **Carrier/Bryant:** Look at the crimp joints where the heat exchanger cells connect to the header. Cracks often develop at the fold/crimp line.
- **Trane/American Standard:** Cracks commonly appear on the backside of the cell near the bend. The "clam shell" style cells crack at the seam.
- **Lennox:** The stamped steel cells tend to crack along the raised ridges where metal fatigue concentrates.
- **Goodman/Amana:** Check the cell crimps and the vestibule panel area. Some models from 2005-2012 had recall-worthy issues.

On 90%+ condensing furnaces, the secondary heat exchanger is even more critical and harder to inspect. Look for condensate leaking where it should not, corrosion on the secondary cells, and any signs of exhaust gas escaping into the blower compartment. A camera scope can be inserted through the inducer housing to view the secondary heat exchanger interior.

### Blower Motor Types: PSC vs ECM

**PSC (Permanent Split Capacitor):**
- Single-speed or multi-speed using color-coded speed taps
- Common speed tap colors: Black = high, Blue or Yellow = medium-high, Red = medium-low, White (with stripe) = low. These vary by manufacturer -- always check the wiring diagram on the motor
- Requires a run capacitor (typically 5-10 microfarad). Test the capacitor: discharge it first (short the terminals with an insulated screwdriver), then use a meter with capacitance function. Replace if more than 10% below rating
- PSC motors draw more power and are less efficient but are simpler and cheaper to replace
- Diagnosis: check capacitor first, then check motor windings (should read 2-20 ohms depending on the winding). Infinite ohms means open winding. Very low ohms (near zero) means shorted winding

**ECM (Electronically Commutated Motor):**
- Variable speed, controlled by the furnace control board or by the integrated module on the motor
- Constant torque design: the motor adjusts speed to maintain consistent airflow even as the filter gets dirty (which is why you see the amp draw increase as filters load up)
- The motor module is the most common failure point. Some modules can be replaced separately (GE 2.3 and 3.0 modules are commonly available), but some motors require complete replacement
- ECM diagnosis: the module communicates with the main board. If the motor does not run, check for 240VAC supply to the motor, then check the 24V communication signal from the board. Most ECM motors have a set of diagnostic LEDs on the module
- ECM motors cost significantly more ($400-$800+ for motor and module) compared to PSC ($100-$250)

### Gas Pressure Setup

Manifold pressure is the gas pressure at the burner orifices and determines BTU input. Always check both inlet and manifold pressure.

- **Natural gas:** Inlet should be 5.0"-7.0" WC minimum (check local codes). Manifold should be 3.5" WC for most manufacturers
- **LP gas:** Inlet should be 11.0"-14.0" WC from the regulator. Manifold should be 10.0" WC for most manufacturers
- **Clocking the meter:** Shut off all other gas appliances. Run only the furnace. Watch the gas meter dial and time it. The formula: (3600 / seconds per revolution) x BTU per cubic foot of gas (1000 BTU for NG, 2500 BTU for LP) x cubic feet per revolution (read the meter dial label). Compare to the furnace rating plate input BTU. You should be within 5%
- **BTU input calculation from gas pressure:** Orifice flow rate changes with the square root of pressure change. A 10% increase in gas pressure results in roughly a 5% increase in BTU input

### Furnace Temperature Rise

Measure supply and return air temperatures after the furnace has been running for at least 10 minutes. Place thermometers in the center of the duct, not touching metal. Temperature rise = supply temp minus return temp. The acceptable range is listed on the rating plate (typically 30-60 degrees F for standard furnaces, 35-65 degrees F for high-efficiency). Low temperature rise means too much airflow (blower too fast, ductwork oversized) or underfire (low gas pressure, wrong orifices). High temperature rise means not enough airflow (dirty filter, blower too slow, ductwork undersized, dirty coil) or overfire. High temperature rise is more dangerous because it can trip the limit switch and, over time, stress and crack the heat exchanger.

### Condensate Drain Troubleshooting (90%+ Furnaces)

All condensing furnaces produce acidic condensate (pH 3-4) that must be drained. Every 90%+ furnace has a condensate trap built into the drain system. The trap must maintain a water seal to prevent flue gases from escaping through the drain. Common issues:

- **Clogged trap:** The number one cause of pressure switch failures on condensing furnaces. Clean the trap annually. Remove it, flush with warm water, and reinstall. Some traps have a cleanout port
- **Improper trap design:** The trap must be deep enough to overcome the negative pressure in the inducer/collector box. A trap that is too shallow will get blown dry, allowing flue gases out and eventually causing the pressure switch to open
- **Frozen drain line:** If the condensate line runs to an exterior wall or through an unheated space, it can freeze in winter. Route to a floor drain or condensate pump instead
- **Condensate pump failure:** If a pump is used, test it by pouring water into the reservoir. The float should rise and activate the pump. Clean the reservoir and float annually
- **Missing or cracked drain hose:** Condensate leaking inside the furnace causes rust and corrosion on the secondary heat exchanger, burners, and control board


## AC Diagnostics

### System Pressures by Refrigerant Type

These are approximate operating pressures at 95 degrees F outdoor temperature with proper charge. Use manufacturer-specific charging charts for precision.

**R-410A:** Suction 118-130 PSI (evaporator saturation ~40-45 degrees F), Discharge 350-420 PSI (condensing temp ~110-120 degrees F)

**R-22:** Suction 65-75 PSI (evaporator saturation ~40-45 degrees F), Discharge 210-260 PSI (condensing temp ~110-120 degrees F)

**R-32:** Suction pressures similar to R-410A but slightly lower. Discharge pressures are slightly higher. Always use manufacturer charts since R-32 is still relatively new in North American markets

Remember: pressures vary significantly with outdoor temperature, indoor conditions, airflow, and line set length. Never diagnose charge level on pressures alone -- always use superheat or subcooling methods.

### Superheat and Subcooling

**Superheat** is how many degrees the suction gas temperature is above the evaporator saturation temperature. Measure suction pressure at the service valve, convert to saturation temperature using a PT chart or your gauge manifold, then measure the actual suction line temperature 6 inches from the compressor with a pipe clamp thermometer. Superheat = actual temp minus saturation temp. Target superheat for a fixed orifice (piston) system is determined by the charging chart (typically 10-20 degrees F depending on indoor wet bulb and outdoor dry bulb). Low superheat means too much refrigerant (liquid flooding back to compressor -- dangerous). High superheat means not enough refrigerant or poor evaporator performance (low airflow, dirty coil).

**Subcooling** is how many degrees the liquid line temperature is below the condensing saturation temperature. Measure discharge (high side) pressure, convert to condensing saturation temperature, then measure the liquid line temperature near the condenser outlet or at the liquid service valve. Subcooling = saturation temp minus actual temp. Target subcooling for a TXV system is typically 10-15 degrees F (check manufacturer specs -- Carrier often targets 12-15, Trane often targets 10-12, Goodman often targets 10-15). Low subcooling means undercharged. High subcooling means overcharged or restriction in the liquid line.

### Capacitor Testing

Capacitors store electrical energy and can shock you severely. Always discharge before testing: use an insulated screwdriver across the terminals, or better yet, a discharge resistor (20,000 ohm 5-watt resistor). For a dual-run capacitor (common on condensing units), there are three terminals: C (common), HERM (compressor), and FAN. The capacitor rating is printed on the side: for example, 45/5 MFD means 45 microfarads for the compressor side and 5 microfarads for the fan side. Test with a capacitance meter: put leads on C and HERM for the compressor side, C and FAN for the fan side. Replace if the reading is more than 10% below the rated value. A visually bulging or leaking capacitor should be replaced immediately regardless of meter reading.

### Compressor Diagnostics

**Winding resistance test:** With power off and all wires removed from the compressor, measure resistance between the three terminals: C (common), S (start), R (run). You should get three readings. The two smaller readings should add up to the larger reading (C-S + C-R = S-R). If any reading is open (infinite), the winding is burned open. If any reading is near zero, the winding is shorted.

**Megohmmeter test (megger):** Tests insulation resistance between the motor windings and the compressor shell (ground). Connect one lead to any compressor terminal and the other to a clean spot on the compressor shell. At 500V test voltage, you should read at least 500 megohms on a good compressor. Below 50 megohms indicates deteriorating insulation. Below 2 megohms means the compressor is grounded and must be replaced.

**Amp draw:** Compare running amps to the RLA (Rated Load Amps) on the data plate. Running at or above RLA continuously indicates a problem (high head pressure, low voltage, mechanical wear). LRA (Locked Rotor Amps) is the inrush current at startup -- if the compressor pulls LRA and does not start, it is locked up mechanically or has a bad start circuit.

**Hard start kit:** If the compressor struggles to start (hums, trips on overload, breaker trips), a hard start kit (start capacitor + potential relay or PTCR) provides extra starting torque. Wire the start capacitor between S and R terminals through the relay. This is often a good temporary solution for aging compressors but does not fix the underlying wear.

### TXV vs Fixed Orifice Troubleshooting

**TXV (Thermostatic Expansion Valve):** Maintains a constant superheat at the evaporator outlet. If subcooling is correct but superheat is high, the TXV may be restricted or the sensing bulb may have lost its charge. If superheat is very low (flooding), the TXV may be stuck open or the sensing bulb may not be making good contact with the suction line. Check bulb contact and insulation. A TXV that has a clogged inlet screen can mimic an undercharge -- subcooling will be high at the condenser, but the evaporator will starve.

**Fixed orifice (piston):** No moving parts to fail, but the orifice can become restricted with debris. Always install a filter-drier when replacing components. With a piston system, charge by superheat method using the manufacturer's charging chart. A restricted piston causes high subcooling, high superheat, low suction pressure, and the liquid line will be cold (possibly sweating or frosting) at the piston location.

### Refrigerant Leak Detection

1. **Electronic leak detector:** Use a heated diode or infrared detector rated for the refrigerant type. Check all braze joints, service valve connections, Schrader valve cores, and the evaporator coil. Move slowly -- refrigerant is heavier than air so check below joints
2. **UV dye:** Inject into the system with the charge. Run the system for several hours or days. Return with a UV light and yellow glasses. Dye shows bright green/yellow at leak points. Works great for slow leaks
3. **Nitrogen pressure test:** Pressurize the system with dry nitrogen to 150 PSI (never exceed nameplate test pressure). Isolate sections. Monitor the gauge for pressure drop over several hours. A 1-2 PSI drop in 24 hours can indicate a very small leak. Temperature changes affect pressure so do this in a stable environment or use a temperature-compensated calculation
4. **Bubble solution:** Apply to suspected areas while system is pressurized with nitrogen. Watch for bubbles forming. Good for pinpointing after you have narrowed the area with other methods


## Heat Pump Specifics

### Reversing Valve Operation

The reversing valve switches the refrigerant flow direction to change between heating and cooling modes. It is controlled by the O or B terminal on the thermostat:

- **Carrier, Trane, Lennox, Goodman, and most brands:** Use the **O terminal** -- the reversing valve is energized in cooling mode. De-energized = heat mode. If the reversing valve solenoid fails or loses power, the system defaults to heating mode
- **Rheem and Ruud:** Use the **B terminal** -- the reversing valve is energized in heating mode. De-energized = cool mode. If it fails, the system defaults to cooling mode

This is critical when troubleshooting a heat pump that heats when it should cool or vice versa. Check the thermostat O/B setting first.

### Defrost Mode

In heating mode, the outdoor coil acts as the evaporator and runs below freezing. Moisture from outdoor air freezes on the coil. The defrost cycle reverses the system temporarily to melt this ice:

- The system switches to cooling mode (hot gas goes to outdoor coil)
- The outdoor fan shuts off (to prevent blowing cold air across the coil and slowing the defrost)
- Supplemental heat strips energize (to prevent blowing cold air into the house during defrost)
- The cycle runs for 3-10 minutes until a termination temperature is reached (typically 57-65 degrees F at the outdoor coil sensor) or a maximum time expires

**Time-temperature defrost:** Initiates every 30, 60, or 90 minutes regardless of ice buildup. Less efficient because it defrosts even when not needed.

**Demand defrost:** Uses sensors (temperature, pressure, or air pressure drop across the coil) to detect actual ice buildup and only defrosts when needed. More efficient.

If the unit never defrosts: check the defrost board (if equipped), defrost thermostat/sensor, and reversing valve solenoid. If it defrosts too often: check the outdoor coil sensor location and calibration, and look for low refrigerant charge causing the coil to run too cold.

### Heat Pump Balance Point

The balance point is the outdoor temperature where the heat pump capacity equals the building heat loss. Below this temperature, supplemental heat (electric strips or gas furnace in a dual-fuel system) must make up the difference. Typical balance points are 30-35 degrees F for standard heat pumps. Cold climate heat pumps (Mitsubishi Hyper Heat, Carrier Greenspeed, Bosch IDS) can maintain capacity down to 5 degrees F or lower.

Aux heat should energize only when the heat pump cannot keep up. Emergency heat should only be selected manually by the homeowner when the heat pump fails completely. If aux heat runs constantly, check: refrigerant charge, outdoor coil cleanliness, defrost operation, and whether the system is properly sized.


## Mini-Split / Ductless Systems

### Installation Best Practices

- **Line set length:** Most systems are pre-charged for 25 feet of line set. Maximum lengths vary: Mitsubishi allows up to 65-100 feet depending on model, Fujitsu up to 65 feet, Daikin up to 75 feet. Additional refrigerant charge is typically 0.6 oz per foot of line set beyond the pre-charged length, but always check the specific model installation manual
- **Height difference:** Maximum vertical distance between indoor and outdoor units is typically 30-50 feet. If the outdoor unit is above the indoor unit, the maximum is often reduced (check manufacturer specs for oil return considerations)
- **Flare connections:** Use proper flare tools (eccentric flare tools produce better flares than hammer-type). Use a torque wrench for flare nut tightening -- overtightening cracks the flare, undertightening causes leaks. Torque values: 1/4" = 10-14 ft-lbs, 3/8" = 24-33 ft-lbs, 1/2" = 38-51 ft-lbs, 5/8" = 50-62 ft-lbs
- **Vacuum:** Pull to 500 microns minimum (300 microns is better). Hold for 15 minutes. Rise should not exceed 200 microns. If it rises above that, you have a leak or moisture

### Cleaning Indoor Units

Dirty indoor units cause poor performance, bad odors, and mold growth. Clean annually at minimum:

1. Remove and wash the filters (warm water and mild soap)
2. Remove the front panel and housing to access the blower wheel
3. Apply coil cleaner to the evaporator coil. Let it dwell, then rinse with a pump sprayer. Protect the electronics with plastic
4. Clean the blower wheel with a coil cleaner or specialized blower wheel brush. This is the most neglected component and often has heavy buildup
5. Clean the condensate drain pan and drain line. Flush with warm water and a small amount of bleach or vinegar
6. Reassemble and run in fan mode to dry

### Communication and WiFi Errors

Mini-split systems use communication wiring between indoor and outdoor units, typically 3 or 4 conductor (14-16 AWG, stranded). Common wiring issues:

- **Polarity matters** on many brands (Mitsubishi, Daikin). Reversing wires causes communication errors. Match terminal numbers exactly: 1-to-1, 2-to-2, 3-to-3
- **Loose connections** at terminal blocks cause intermittent errors. Ensure wires are fully inserted and screws are tight
- **Voltage between terminals:** You can measure AC voltage between communication terminals to verify the signal. Typically 20-50VAC pulsing indicates communication

Multi-zone systems use a branch box (distribution box) between the outdoor unit and multiple indoor units. If one zone fails while others work, the issue is likely in the wiring or the individual indoor unit board, not the outdoor unit.
