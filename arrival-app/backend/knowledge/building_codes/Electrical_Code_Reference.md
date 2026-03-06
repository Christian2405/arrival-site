# Electrical Code Reference — Field Quick Reference

## Wire Sizing (NEC Table 310.16, 75°C Column, Copper THHN)

| Breaker | Wire Size | Typical Use |
|---------|-----------|-------------|
| 15A | 14 AWG | Lighting circuits |
| 20A | 12 AWG | General receptacles, kitchen, bath |
| 30A | 10 AWG | Dryers, water heaters |
| 40A | 8 AWG | Ranges, cooktops |
| 50A | 6 AWG | Sub-panels, large ranges |
| 60A | 6 AWG | Sub-panels, EV chargers |
| 70A | 4 AWG | Sub-panels |
| 100A | 3 AWG (copper) or 1 AWG (aluminum) | Main panels, sub-feeds |
| 125A | 2 AWG (copper) or 1/0 AWG (aluminum) | Main service |
| 150A | 1 AWG (copper) or 2/0 AWG (aluminum) | Main service |
| 200A | 2/0 AWG (copper) or 4/0 AWG (aluminum) | Main service |

**Voltage drop rule:** For runs over 50 feet, bump up one wire size per 50 feet past the first 50. NEC recommends max 3% voltage drop on branch circuits, 5% total (feeder + branch).

## GFCI Protection Requirements (NEC 210.8)

GFCI protection required for all 125V, 15A and 20A receptacles in:
- Bathrooms (all receptacles)
- Kitchens (within 6 feet of sink edge, all countertop receptacles)
- Garages and accessory buildings
- Outdoors (all receptacles)
- Crawl spaces and unfinished basements
- Laundry areas (within 6 feet of sink)
- Boathouses
- Bathtubs and shower stall areas (within 6 feet)
- Indoor damp/wet locations

**2020 NEC added:** Basements (finished and unfinished), laundry areas regardless of sink proximity.
**2023 NEC added:** All 250V outlets in similar locations also require GFCI.

## AFCI Protection Requirements (NEC 210.12)

AFCI protection required for all 120V, 15A and 20A branch circuits supplying outlets in:
- Kitchens
- Family rooms, dining rooms, living rooms
- Bedrooms, sunrooms, closets, hallways
- Laundry areas
- Similar rooms or areas

**Note:** AFCI is about fire prevention (arc fault). GFCI is about shock prevention (ground fault). Some locations require both — combination AFCI/GFCI breakers or AFCI breaker + GFCI receptacle.

## Panel and Clearance Requirements

### Working Space (NEC 110.26)
- **Minimum 3 feet clear** in front of all electrical panels (0-150V to ground)
- **36 inches wide** minimum (or width of panel, whichever is greater)
- **6.5 feet headroom** minimum
- Panel must be accessible — no storage in front, no obstruction
- **Dedicated space** above and below panel: nothing but electrical equipment

### Panel Height
- Maximum height for topmost breaker: 6 feet 7 inches from finished floor
- Overcurrent devices must be readily accessible — no ladders required

### Service Entrance
- Service disconnect must be readily accessible from outside or nearest point of entry
- Maximum 6 throws to disconnect all power (six-disconnect rule)
- **2020 NEC 230.85:** Emergency disconnect required on outside of dwelling unit

## Outdoor and Wet Location Requirements

- All outdoor receptacles: GFCI protected + weather-resistant (WR) rated
- Outdoor receptacle covers: "in-use" type covers required (not just weatherproof when closed)
- Outdoor wiring: UF cable for direct burial (min 24 inches deep for residential), or conduit
- Underground conduit: PVC Schedule 80 for risers, Schedule 40 underground
- Minimum burial depth: 24 inches for direct-buried UF cable, 18 inches for rigid conduit, 12 inches for PVC conduit under concrete

## Grounding and Bonding

- Main bonding jumper: required at service equipment (connects neutral bus to equipment ground bus)
- Grounding electrode system: two or more electrodes bonded together
- Common grounding electrodes: concrete-encased (Ufer ground), ground rods, water pipe (first 10 feet)
- Ground rod: minimum 8 feet long, 5/8 inch diameter for copper-clad
- **Two ground rods required** unless one rod tests 25 ohms or less
- Ground rod spacing: minimum 6 feet apart
- Water pipe ground: supplement with additional electrode (ground rod, Ufer, etc.)
- Gas piping: **NEVER use as grounding electrode**. Must be bonded to grounding system.

## Receptacle Spacing

### General living areas (NEC 210.52)
- No point along floor line more than 6 feet from a receptacle
- Receptacle required every 12 feet of wall space
- Any wall space 2 feet or wider gets a receptacle
- Sliding glass doors: wall space doesn't include the door opening

### Kitchen countertops
- Receptacle within 2 feet of each end of countertop
- No point along the countertop more than 2 feet from a receptacle (24-inch rule)
- Island/peninsula countertops: at least one receptacle required
- Kitchen countertop receptacles must be on dedicated 20A small-appliance branch circuits (minimum 2 circuits)

### Bathrooms
- At least one receptacle within 3 feet of each sink basin
- Must be on a dedicated 20A circuit (can serve multiple bathroom receptacles)

## Smoke and CO Detector Requirements

- Smoke detectors: required in each bedroom, outside each sleeping area, every level of home
- Must be interconnected (hardwired with battery backup preferred)
- CO detectors: required outside each sleeping area on every level with a fuel-burning appliance or attached garage
- Combination smoke/CO units acceptable

## Common Code Violations in the Field

1. Double-tapped breakers (two wires on one breaker terminal — only allowed if breaker is rated for it)
2. No anti-short bushing on NM cable entering metal boxes
3. Open knockouts on panels
4. Missing cable clamps in boxes
5. Overloaded neutral bus bars
6. Improper box fill calculations (too many wires in the box)
7. Extension cords used as permanent wiring
8. White wire used as hot without re-marking (tape or paint)
9. Missing GFCI protection in required locations
10. Panel bonding screw installed in sub-panel (should only be bonded at main panel)

## Permit and Inspection Notes

Most jurisdictions require permits for:
- Any new circuit installation
- Panel upgrades or replacements
- Adding receptacles or circuits
- Service entrance changes
- Any work inside the main panel

Typically NOT requiring a permit:
- Like-for-like device replacement (switch for switch, outlet for outlet)
- Light fixture replacement (same location, same circuit)
- Appliance cord replacement

**Always check with the local authority having jurisdiction (AHJ).** Code requirements vary by state and municipality. Some areas are still on NEC 2017, others have adopted NEC 2023.
