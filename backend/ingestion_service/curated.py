"""Curated domain knowledge that complements the PSI records.

Everything here comes from the Space Apps challenge brief or from the NASA pages linked
in it (sources listed per record). The PSI API supplies the investigations
themselves; this module adds the fire-safety framing used for ranking and
interpretation: which pillar (prevention / detection / suppression) each investigation
informs, its hardware family and its fuel phase.
"""

# ---------------------------------------------------------------------------------------
# Crewed-environment atmosphere scenarios
# ---------------------------------------------------------------------------------------
HABITATS = [
    {
        "slug": "iss",
        "name": "International Space Station",
        "short": "ISS",
        "o2_min": 19.5, "o2_max": 23.5, "p_min_psi": 14.2, "p_max_psi": 14.9,
        "gravity_g": 0.0, "flow_min": 5, "flow_max": 20,
        "description": "Sea-level-like cabin air in microgravity with forced ventilation. "
                       "Nearly all PSI combustion data was collected here.",
        "basis": "Earth-normal cabin atmosphere (14.7 psi, ~21% O2) per challenge brief.",
        "is_assumption": False, "sort": 1,
    },
    {
        "slug": "spacecraft",
        "name": "Crew spacecraft cabin (e.g. Orion)",
        "short": "Spacecraft",
        "o2_min": 20, "o2_max": 30, "p_min_psi": 10.2, "p_max_psi": 14.7,
        "gravity_g": 0.0, "flow_min": 5, "flow_max": 20,
        "description": "Transit vehicle in free fall. May drop cabin pressure ahead of EVAs, "
                       "raising the O2 fraction.",
        "basis": "Microgravity; pressure band from 14.7 psi nominal to the 10.2 psi intermediate "
                 "atmosphere in the challenge brief.",
        "is_assumption": True, "sort": 2,
    },
    {
        "slug": "lunar_base",
        "name": "Moon Base surface habitat",
        "short": "Moon Base",
        "o2_min": 30, "o2_max": 36, "p_min_psi": 8.2, "p_max_psi": 10.2,
        "gravity_g": 0.166, "flow_min": 0, "flow_max": 15,
        "description": "Intermediate, O2-enriched atmosphere to shorten EVA pre-breathe. "
                       ">40% more O2 than Earth air makes materials much more flammable.",
        "basis": "Challenge brief: 'likely 30% or greater, with a corresponding pressure of 10.2 psi "
                 "or less'. Lower bound of 8.2 psi is an assumption for the exploration atmosphere.",
        "is_assumption": False, "sort": 3,
    },
    {
        "slug": "rover",
        "name": "Pressurized lunar rover",
        "short": "Rover",
        "o2_min": 30, "o2_max": 36, "p_min_psi": 8.2, "p_max_psi": 10.2,
        "gravity_g": 0.166, "flow_min": 0, "flow_max": 10,
        "description": "Small free volume, frequent EVAs and limited escape options. "
                       "Smoke spreads through the cabin quickly and the crew has little time to react.",
        "basis": "Challenge brief: Moon Base and pressurized rovers share the intermediate atmosphere.",
        "is_assumption": False, "sort": 4,
    },
    {
        "slug": "mars",
        "name": "Mars transit & surface habitat",
        "short": "Mars",
        "o2_min": 26, "o2_max": 36, "p_min_psi": 8.2, "p_max_psi": 10.2,
        "gravity_g": 0.38, "flow_min": 0, "flow_max": 15,
        "description": "Long-duration missions with no rescue option. Partial gravity on the "
                       "surface brings back weak buoyant flow.",
        "basis": "Planning assumption: reuse of the lunar exploration atmosphere. Mars gravity 0.38 g.",
        "is_assumption": True, "sort": 5,
    },
    {
        "slug": "spacesuit",
        "name": "Spacesuit / pre-breathe",
        "short": "Spacesuit",
        "o2_min": 95, "o2_max": 100, "p_min_psi": 4.0, "p_max_psi": 4.5,
        "gravity_g": 0.166, "flow_min": 0, "flow_max": 30,
        "description": "Pure oxygen at low pressure. This is the most oxidizing environment crews occupy.",
        "basis": "Challenge brief: suits are filled with 100% O2 to 4.3 psi.",
        "is_assumption": False, "sort": 6,
    },
    {
        "slug": "earth",
        "name": "Earth (terrestrial buildings, vehicles)",
        "short": "Earth",
        "o2_min": 20.5, "o2_max": 21.5, "p_min_psi": 14.0, "p_max_psi": 14.8,
        "gravity_g": 1.0, "flow_min": 0, "flow_max": 50,
        "description": "Terrestrial fire safety. Microgravity results remove buoyancy and expose "
                       "the underlying physics, which feeds back into detectors, extinguishers and firefighter gear.",
        "basis": "Standard sea-level atmosphere.",
        "is_assumption": False, "sort": 7,
    },
]

# ---------------------------------------------------------------------------------------
# Historical incidents
# ---------------------------------------------------------------------------------------
INCIDENTS = [
    {
        "slug": "apollo-1",
        "name": "Apollo 1 cabin fire",
        "date": "1967-01-27", "year": 1967,
        "vehicle": "Apollo Command Module (AS-204), Launch Complex 34",
        "atmosphere": "100% oxygen cabin atmosphere during a pre-launch ground test",
        "cause": "Ignition source never definitively identified. Evidence of arcing in wiring near the "
                 "environmental control system. The pure-O2 atmosphere drove rapid fire spread.",
        "outcome": "Crew of three (Grissom, White, Chaffee) died, mainly from carbon monoxide and toxic "
                   "gas inhalation. The cabin pressure vessel ruptured and the hatch could not be opened in time.",
        "lessons": [
            "Combustible materials in the cabin restricted and controlled",
            "Unified hatch that opens in ~3 seconds",
            "Fire-resistant spacesuit materials",
            "Management and safety-culture changes",
        ],
        "pillars": ["prevention", "suppression"],
        "related_investigations": ["PSI-26", "PSI-25", "PSI-98", "PSI-159"],
        "source_url": "https://sma.nasa.gov/sma-disciplines/accllp/apollo-1#history",
    },
    {
        "slug": "apollo-13",
        "name": "Apollo 13 oxygen tank explosion",
        "date": "1970-04-13", "year": 1970,
        "vehicle": "Apollo 13 Service Module",
        "atmosphere": "Supercritical cryogenic oxygen tank",
        "cause": "Tank heater thermostats were not upgraded when supply voltage went from 28 V to 65 V. "
                 "During a pre-launch test the heaters reached ~1,000 °F and damaged the Teflon wire "
                 "insulation, which later failed inside the oxygen tank.",
        "outcome": "Fuel cells and the lunar landing were lost. The crew survived by using the Lunar "
                   "Module as a lifeboat and splashed down on 17 April 1970.",
        "lessons": [
            "Match component ratings when changing electrical parameters",
            "Wiring sheathed in stainless steel; materials compatibility in O2",
            "Redesigned O2 tanks: third tank, upgraded thermostats, fans removed",
        ],
        "pillars": ["prevention"],
        "related_investigations": ["PSI-159", "PSI-102", "PSI-99"],
        "source_url": "https://sma.nasa.gov/sma-disciplines/accllp/apollo-13",
    },
    {
        "slug": "mir-1997",
        "name": "Mir oxygen-generator fire",
        "date": "1997-02-24", "year": 1997,
        "vehicle": "Mir space station, Kvant-1 module",
        "atmosphere": "Station cabin air; fire fed by a solid-fuel oxygen generator (SFOG) canister",
        "cause": "An SFOG candle ignited during activation. The likely contaminant was latex glove "
                 "material that had got into the canister.",
        "outcome": "Flame burned for several minutes. Smoke filled the modules and blocked one Soyuz. "
                   "Crew wore masks and used foam extinguishers. The station had no structural damage.",
        "lessons": [
            "Crew emergency training and ground support changed",
            "Ground preparation of SFOG canisters changed",
            "Lessons shaped ISS oxygen-generation design and operations",
        ],
        "pillars": ["detection", "suppression", "prevention"],
        "related_investigations": ["PSI-102", "PSI-101", "PSI-69", "PSI-26"],
        "source_url": "https://www.nasa.gov/history/25-years-ago-fire-aboard-space-station-mir/",
    },
    {
        "slug": "artemis-ii",
        "name": "Artemis II smoke alarm",
        "date": "2026-04", "year": 2026,
        "vehicle": "Orion spacecraft, Artemis II lunar flyby",
        "atmosphere": "Crew cabin, ~80,000 miles from Earth",
        "cause": "Smoke alarm activation during the mission, as described in the challenge brief.",
        "outcome": "Commander: \"[If] you want to get somebody's attention really quick, make the fire "
                   "alarm go off in your spacecraft when you're still about 80,000 miles from home.\"",
        "lessons": [
            "Detectors must tell real smoke from dust and other aerosols (see SAME, SAME-R, DAFT)",
        ],
        "pillars": ["detection"],
        "related_investigations": ["PSI-102", "PSI-101", "PSI-47"],
        "source_url": "https://www.spaceappschallenge.org/",
    },
]

# ---------------------------------------------------------------------------------------
# NASA Spinoffs: Earth applications
# ---------------------------------------------------------------------------------------
SPINOFFS = [
    {
        "slug": "fire-detector",
        "title": "Fire Detector (Incipient Fire Detector)",
        "year": 1978,
        "origin": "Brunswick Incipient Fire Detector flown on the Space Shuttle orbiters.",
        "application": "Samples air and tells combustion particles apart from dust, which cuts false "
                       "alarms. Networked sensors can monitor large areas such as mines and locate an incipient fire.",
        "pillar": "detection",
        "related_investigations": ["PSI-102", "PSI-101", "PSI-47"],
        "source_url": "https://spinoff.nasa.gov/node/9407",
    },
    {
        "slug": "firefighter-air-tanks",
        "title": "Firefighter's Air Tanks",
        "year": 1976,
        "origin": "NASA Johnson Space Center with Scott Aviation; composite pressure-vessel technology.",
        "application": "Composite-wrapped aluminum tank ~13 lb lighter than conventional ones with a "
                       "30-minute supply. Redesigned mask for visibility and a personal low-air warning.",
        "pillar": "suppression",
        "related_investigations": [],
        "source_url": "https://spinoff.nasa.gov/node/9582",
    },
    {
        "slug": "fire-attire",
        "title": "New Technology for the Fire Attire (Project FIRES)",
        "year": 1982,
        "origin": "NASA Marshall and the U.S. Fire Administration adapted spacesuit and spacecraft "
                  "thermal-protection materials.",
        "application": "Lighter, more heat-protective firefighter ensembles. Field-tested with 14 municipal "
                       "fire departments to inform national gear standards.",
        "pillar": "prevention",
        "related_investigations": ["PSI-26", "PSI-98"],
        "source_url": "https://spinoff.nasa.gov/node/9918",
    },
    {
        "slug": "water-mist",
        "title": "Fine-Water-Mist Extinguisher & Zero-Leak Valve",
        "year": 2016,
        "origin": "ISS portable fine-water-mist extinguishers (micro-atomized water + N2) replaced CO2 units. "
                  "Developed through Glenn SBIR contracts.",
        "application": "Works in any orientation and avoids the CO2 breathing hazard. The zero-leak valve now "
                       "serves industrial and military systems on Earth.",
        "pillar": "suppression",
        "related_investigations": ["PSI-69", "PSI-68"],
        "source_url": "https://spinoff.nasa.gov/node/11065",
    },
]

# ---------------------------------------------------------------------------------------
# Per-investigation fire-safety tags
# hardware: family; phase: fuel phase; pillars: weights 0..1; tier: direct|supporting
# ---------------------------------------------------------------------------------------
HW_ACME = "CIR / ACME modular gaseous-flame hardware"
HW_MDCA = "CIR / Multi-user Droplet Combustion Apparatus (MDCA)"
HW_MSG = "MSG / SPICE fan-driven flow duct"
HW_SAFFIRE = "Saffire flow unit in Cygnus cargo vehicle"
HW_SAME = "MSG / Smoke & aerosol measurement hardware"
HW_DAFT = "Hand-held aerosol instruments (P-Trak, DustTrak)"
HW_GROUND = "Ground / analysis of flight data"

INVESTIGATION_TAGS = {
    "PSI-26": dict(hardware=HW_MSG, phase="solid", tier="direct", geometry="Flat slabs, spheres and cylinders",
                   pillars=dict(prevention=1.0, detection=0.2, suppression=0.7),
                   summary="Solid-material flammability and extinguishment vs. flow and O2 in microgravity."),
    "PSI-25": dict(hardware=HW_MSG, phase="solid", tier="direct", geometry="Thin films, slabs and rods",
                   pillars=dict(prevention=1.0, detection=0.3, suppression=0.6),
                   summary="Follow-on to BASS: flame spread and extinction over solids incl. reduced O2."),
    "PSI-98": dict(hardware=HW_SAFFIRE, phase="solid", tier="direct", geometry="Large fabric sheet (~40 x 94 cm)",
                   pillars=dict(prevention=1.0, detection=0.4, suppression=0.2),
                   summary="First large-scale spacecraft fire: concurrent vs opposed flame spread over SIBAL fabric."),
    "PSI-99": dict(hardware=HW_SAFFIRE, phase="solid", tier="direct", geometry="Nine 5 x 29 cm material coupons",
                   pillars=dict(prevention=1.0, detection=0.4, suppression=0.2),
                   summary="Ignition and flammability of nine spacecraft materials, compared with NASA-STD-6001 1-g results."),
    "PSI-100": dict(hardware=HW_SAFFIRE, phase="solid", tier="direct", geometry="Large fabric sheet (~40 x 94 cm)",
                    pillars=dict(prevention=1.0, detection=0.4, suppression=0.2),
                    summary="Large-scale fabric flame spread with combustion product monitoring."),
    "PSI-62": dict(hardware=HW_GROUND, phase="solid", tier="supporting", geometry="Thin solid (model)",
                   pillars=dict(prevention=0.9, detection=0.1, suppression=0.3),
                   summary="Flamelet-manifold CFD of concurrent flame spread over solids, validated against BASS data."),
    "PSI-20": dict(hardware=HW_ACME, phase="gas", tier="direct", geometry="Porous burner 25 / 50 mm",
                   pillars=dict(prevention=0.9, detection=0.2, suppression=0.4),
                   summary="Burning Rate Emulator: gaseous fuels emulate condensed-phase material flammability in still air."),
    "PSI-21": dict(hardware=HW_ACME, phase="gas", tier="supporting", geometry="Coflow nozzle burner",
                   pillars=dict(prevention=0.4, detection=0.4, suppression=0.3),
                   summary="Coflow laminar diffusion flames: soot, lift-off and stability."),
    "PSI-22": dict(hardware=HW_ACME, phase="gas", tier="supporting", geometry="Coflow burner + mesh electrode",
                   pillars=dict(prevention=0.4, detection=0.2, suppression=0.3), partial_gravity=True,
                   summary="Electric fields act on flame ions to mimic buoyancy, a proxy for partial gravity."),
    "PSI-23": dict(hardware=HW_ACME, phase="gas", tier="supporting", geometry="Counterflow/porous burners",
                   pillars=dict(prevention=0.5, detection=0.2, suppression=0.4),
                   summary="Structure and response of spherical diffusion flames, extinction limits."),
    "PSI-10": dict(hardware=HW_ACME, phase="gas", tier="supporting", geometry="Spherical porous burner",
                   pillars=dict(prevention=0.5, detection=0.5, suppression=0.3),
                   summary="Flame Design: normal & inverse spherical flames; soot-free flame design via stoichiometric mixture fraction."),
    "PSI-159": dict(hardware=HW_ACME, phase="gas", tier="supporting", geometry="Spherical porous burner",
                    pillars=dict(prevention=0.7, detection=0.2, suppression=0.3),
                    summary="Cool flames with gaseous fuels, including the highest O2 (up to ~85%) microgravity tests in PSI."),
    "PSI-69": dict(hardware=HW_MDCA, phase="liquid", tier="direct", geometry="Free/tethered droplets 1.5-5 mm",
                   pillars=dict(prevention=0.5, detection=0.1, suppression=1.0),
                   summary="Flame Extinguishment Experiment: CO2 and He dilution limits for droplet flames."),
    "PSI-68": dict(hardware=HW_MDCA, phase="liquid", tier="direct", geometry="Droplets 1.5-5 mm",
                   pillars=dict(prevention=0.6, detection=0.1, suppression=0.7),
                   summary="FLEX-2: multi-component fuels, sooting and convective effects on droplet burning and extinction."),
    "PSI-39": dict(hardware=HW_MDCA, phase="liquid", tier="supporting", geometry="Droplets",
                   pillars=dict(prevention=0.6, detection=0.2, suppression=0.4),
                   summary="Cool flames: low-temperature burning that persists after hot-flame extinction, a hidden hazard."),
    "PSI-117": dict(hardware=HW_GROUND, phase="liquid", tier="supporting", geometry="Droplets (analysis)",
                    pillars=dict(prevention=0.5, detection=0.1, suppression=0.5),
                    summary="Thermo-convective perturbation of cool-flame dynamics (analysis of droplet data)."),
    "PSI-142": dict(hardware=HW_GROUND, phase="liquid", tier="supporting", geometry="Droplets (analysis)",
                    pillars=dict(prevention=0.5, detection=0.1, suppression=0.5),
                    summary="Quantitative cool-flame transitions at radiative/stretch extinction (FLEX data)."),
    "PSI-107": dict(hardware=HW_MSG, phase="gas", tier="supporting", geometry="Nozzle burners (0.4-1.6 mm)",
                    pillars=dict(prevention=0.5, detection=0.6, suppression=0.2),
                    summary="Smoke point in coflow: when flames emit soot, which feeds smoke-detector design and radiation models."),
    "PSI-106": dict(hardware=HW_MSG, phase="gas", tier="supporting", geometry="Nozzle burners",
                    pillars=dict(prevention=0.4, detection=0.3, suppression=0.4),
                    summary="Flame structure and lift-off; stability limits relevant to blow-off and extinction."),
    "PSI-60": dict(hardware=HW_GROUND, phase="gas", tier="supporting", geometry="Nozzle burners (analysis)",
                   pillars=dict(prevention=0.4, detection=0.5, suppression=0.2),
                   summary="Computational and experimental analysis of SPICE soot data sets."),
    "PSI-102": dict(hardware=HW_SAME, phase="aerosol", tier="direct", geometry="Heated material samples",
                    pillars=dict(prevention=0.1, detection=1.0, suppression=0.0),
                    summary="Smoke particle size from overheated spacecraft materials, used to design detectors."),
    "PSI-101": dict(hardware=HW_SAME, phase="aerosol", tier="direct", geometry="Heated material samples",
                    pillars=dict(prevention=0.1, detection=1.0, suppression=0.0),
                    summary="SAME reflight: smoke aging, new materials and detector responses."),
    "PSI-115": dict(hardware=HW_GROUND, phase="aerosol", tier="supporting", geometry="Smoke aerosol (model)",
                    pillars=dict(prevention=0.1, detection=0.9, suppression=0.0),
                    summary="Advanced modeling of smoke aerosol using SAME data."),
    "PSI-47": dict(hardware=HW_DAFT, phase="aerosol", tier="direct", geometry="Dust aerosol (ARD)",
                   pillars=dict(prevention=0.0, detection=0.8, suppression=0.0),
                   summary="Dust measurement on ISS: background aerosols that can cause false smoke alarms."),
}

# Sensor / diagnostic vocabulary used to extract "measurements" from PSI text fields.
MEASUREMENT_TERMS = {
    "Video / imaging": ["video", "camera", "imaging", "images", "photograph"],
    "Radiometry": ["radiometer", "radiometry", "radiative flux"],
    "Thermocouples": ["thermocouple"],
    "Pyrometry / soot temperature": ["pyrometry", "pyrometer", "soot temperature"],
    "Soot volume fraction / laser extinction": ["soot volume", "laser extinction", "light extinction"],
    "OH* / CH* chemiluminescence": ["chemiluminescence", "oh*", "ch*"],
    "Gas analyzers (O2, CO2, CO)": ["gas analyzer", "co2 sensor", "o2 sensor", "carbon monoxide", "oxygen sensor",
                                    "gas sampling", "combustion product"],
    "Smoke/particle counters": ["particle counter", "p-trak", "ptrak", "dusttrak", "particle size", "aerosol monitor",
                                "condensation nuclei"],
    "Smoke detectors (ionization / photoelectric)": ["ionization", "photoelectric", "smoke detector"],
    "Droplet diameter / burning rate": ["droplet diameter", "burning rate", "burn rate"],
    "Flame spread rate": ["flame spread", "spread rate"],
    "Pressure / flow sensors": ["pressure transducer", "flow meter", "mass flow"],
    "Electric field / ion current": ["electric field", "ion current", "ionic wind"],
    "Numerical modeling / CFD": ["simulation", "numerical", "computational", "cfd", "model"],
}

FUEL_ALIASES = {
    "c2h4": "Ethylene", "ch4": "Methane", "c2h6": "Ethane", "c3h8": "Propane",
    "c12h26": "n-Dodecane", "c7h16": "n-Heptane", "c8h18": "Octane", "c10h22": "n-Decane",
    "ch3oh": "Methanol", "c2h5oh": "Ethanol", "pmma": "PMMA (acrylic)",
}
