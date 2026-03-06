# HVAC Refrigerant & Charging — Technical Field Reference

## Superheat and Subcooling Targets

### Cap Tube / Fixed Orifice Systems
Cap tube (capillary tube) and fixed orifice (piston) systems use SUPERHEAT to determine proper charge.

**Target superheat: 10-15°F** (varies slightly by manufacturer and conditions)

How to measure superheat:
1. Measure suction line temperature at the service valve with a clamp thermometer
2. Read suction pressure at the gauge port
3. Convert suction pressure to saturation temperature using a PT chart
4. Superheat = Suction line temperature - Saturation temperature

**Charging a cap tube system:**
- Low superheat (below 5°F) = overcharged, liquid could slug the compressor
- High superheat (above 20°F) = undercharged, compressor running hot
- Add refrigerant to lower superheat, recover refrigerant to raise superheat
- Always weigh in charge when possible on cap tube systems

### TXV (Thermostatic Expansion Valve) Systems
TXV systems regulate superheat automatically. Use SUBCOOLING to determine proper charge.

**Target subcooling: 10-12°F** (check manufacturer specs, some are 8-14°F)

How to measure subcooling:
1. Measure liquid line temperature at the condenser outlet with a clamp thermometer
2. Read high-side (discharge/liquid) pressure at the gauge port
3. Convert liquid pressure to saturation temperature using a PT chart
4. Subcooling = Saturation temperature - Liquid line temperature

**Charging a TXV system:**
- Low subcooling (below 5°F) = undercharged
- High subcooling (above 20°F) = overcharged or restriction
- Add refrigerant to raise subcooling, recover to lower subcooling
- Superheat on a TXV system is controlled by the valve — don't use it for charging

### EEV (Electronic Expansion Valve) Systems
- Follow manufacturer-specific charging procedures
- Most use subcooling method similar to TXV
- Superheat is actively controlled by the EEV controller
- Always refer to the specific unit's service manual

## Common Refrigerant Operating Pressures

### R-410A (Puron)
Most common in systems manufactured after 2010.
| Outdoor Temp | Suction (Low) | Discharge (High) |
|-------------|---------------|-------------------|
| 75°F | 118 psi | 340 psi |
| 85°F | 128 psi | 390 psi |
| 95°F | 138 psi | 440 psi |
| 105°F | 148 psi | 490 psi |

**R-410A key facts:**
- Operates at ~60% higher pressure than R-22
- Requires POE (polyolester) oil
- Must use gauges rated for 800+ psi
- Near-zeotropic blend — must be charged as liquid
- Cannot be topped off if significant leak occurred — recover and weigh in full charge

### R-22 (Freon)
Phased out, no longer manufactured but still in many existing systems.
| Outdoor Temp | Suction (Low) | Discharge (High) |
|-------------|---------------|-------------------|
| 75°F | 68 psi | 250 psi |
| 85°F | 73 psi | 275 psi |
| 95°F | 78 psi | 300 psi |
| 105°F | 83 psi | 325 psi |

**R-22 key facts:**
- Being phased out under Montreal Protocol
- Uses mineral oil
- Can be topped off (single-component refrigerant)
- Do NOT mix with R-410A — different oils and pressures

### R-454B (Opteon XL41) — Next Generation
Replacing R-410A in new equipment (starting 2025).
- A2L (mildly flammable) refrigerant
- ~4% lower GWP than R-410A
- Similar operating pressures to R-410A but slightly lower
- Requires R-454B-specific equipment and training

### R-134a (Automotive / Small Commercial)
| Condition | Low Side | High Side |
|-----------|----------|-----------|
| Normal operation | 25-45 psi | 200-250 psi |

## Common Diagnostic Checks

### Low Suction Pressure Causes
1. Low on charge (most common) — check for leaks
2. Restricted metering device (TXV, cap tube, or orifice)
3. Restricted filter drier (feel for temperature drop across it)
4. Low airflow across evaporator (dirty filter, collapsed duct, frozen coil)
5. Restricted liquid line

### High Head Pressure Causes
1. Dirty condenser coil (wash it)
2. Condenser fan motor failure or running slow
3. Overcharge
4. Non-condensables in system (air or nitrogen)
5. Restricted airflow through condenser

### Compressor Not Starting
1. Check power — voltage at disconnect and contactor
2. Check capacitor with meter (should be within 5% of rated microfarads)
3. Check contactor — contacts pitted or burnt?
4. Hard start kit may help an aging compressor
5. If locked rotor — check amp draw, may need hard start or compressor replacement
6. Internal overload tripped — let it cool, check cause

### Furnace Not Igniting
1. Check pressure switch — inducer must prove before ignition
2. Check hot surface igniter — visible crack = replace, ohm it (should read 40-90 ohms)
3. Check flame sensor — dirty sensor is #1 cause of no-heat calls. Clean with emery cloth.
4. Check gas valve — 24V at valve? If yes and no gas, valve is bad
5. Check board — LED blink code tells the story

## Temperature Splits and Airflow

### Normal Temperature Split (Supply vs Return)
- Cooling: 14-22°F delta T across evaporator
- Heating (gas furnace): 35-75°F temperature rise (check rating plate for exact range)
- Heat pump heating: 15-25°F delta T

### Airflow Requirements
- Standard residential: 400 CFM per ton of cooling
- High-efficiency systems: 350-450 CFM per ton
- Minimum duct velocity: 600 FPM supply, 400 FPM return
- Static pressure target: 0.5" WC total external (most residential systems)
- If static pressure exceeds 0.8" WC, ductwork is likely undersized

## Water Heater Quick Reference

### Gas Water Heater Status Light Codes
Most modern gas water heaters use a status light (LED) on the gas control valve that blinks to indicate condition. The number of blinks indicates the diagnostic code. Check the label on the unit for the specific code chart, as codes vary by manufacturer (Honeywell, White-Rodgers, Robertshaw gas valves).

### Electric Water Heater Troubleshooting
- No hot water: Check breaker, then upper thermostat reset button (red button), then upper element
- Runs out of hot water fast: Lower element likely failed (most common)
- Water too hot: Thermostat failed closed, check both upper and lower
- Element testing: Disconnect power, disconnect wires, ohm across element terminals. Typical reading: 10-16 ohms for 4500W element at 240V. Infinity = open element. Very low/zero = shorted element.

### Tankless Water Heater Common Issues
- Error code 11 (Rinnai): No ignition — check gas supply, igniter, flame rod
- Error code 12 (Rinnai): Flame failure — flame rod dirty, gas pressure low
- Minimum flow rate: Most units need 0.5-0.75 GPM to activate
- Descaling: Run white vinegar through unit every 12 months in hard water areas
