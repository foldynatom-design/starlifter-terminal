# -*- coding: utf-8 -*-
"""
rp_stories.py — Narrative Lore & Dispatch Template Pool for Starlifter Terminal.
Expanded with 60+ high-immersion military logistics templates across LOW, MEDIUM, and HIGH threat levels.
Includes dynamic placeholders: {cargo_type}, {ship}, {captain}, {officer}, {crew}, {location}, {env_note}.
"""

stories = [
    # ══════════════════════════════════════════════════════════════════════════
    # ── LOW SEVERITY (0-19): Smooth military operations & precision loading ──
    # ══════════════════════════════════════════════════════════════════════════
    (
        "Loading operations completed without a single registry discrepancy at {location}. "
        "Under the direct oversight of {officer}, the deck crew aligned every {cargo_type} onto the primary cargo grid of the {ship}. "
        "{captain}, magnetic clamps are drawing nominal power and mass distribution is centered within Navy tolerances. "
        "{crew} has fully cleared the pad. Spool quantum drives at your discretion — departure corridor is clear."
    ),
    (
        "Shipping manifest officially verified and uploaded to UEE Fleet Command from {location}. "
        "{crew} reports a textbook grid alignment across all cargo bays on the {ship}. "
        "All external loading arms and umbilical cables for {cargo_type} have been fully retracted. "
        "{captain}, orbital departure vector looks completely clear. Safe journey through the jump point."
    ),
    (
        "Standard naval logistics cycle finalized at {location}. Every unit of {cargo_type} was scanned, weighed, and secured under {officer}. "
        "The deck detail {crew} ensured optimal balance for quantum transition on the {ship}. "
        "{captain}, the manifest is signed, sealed, and synced with the 44th Battle Group network. Clear skies ahead."
    ),
    (
        "Navy dock workers have completed stacking the final {cargo_type} into the hold of the {ship}. "
        "{crew} has secured all equipment. {officer} confirms magnetic locks active across all deck sectors. "
        "{captain}, cargo is stabilized even for combat-evasive maneuvers. Flight clearance transmitted to HUD."
    ),
    (
        "Cargo hold of the {ship} is officially sealed, locked down, and pressurized at {location}. "
        "{officer} supervised the staging while {crew} loaded {cargo_type} into designated grid slots. "
        "Environmental sensors show standard military baseline. {captain}, exterior ramp sealed. Launch pad cleared."
    ),
    (
        "Routine supply turnaround verified by the logistics detachment at {location}. "
        "The {cargo_type} aboard the {ship} was inspected by {officer}, confirming 100% barcode readability. "
        "{crew} finished staging twenty minutes ahead of schedule. {captain}, zero anomalies detected. You are cleared for VTOL ascent."
    ),
    (
        "All {cargo_type} aboard the {ship} safely stacked and inspected for mass displacement at {location}. "
        "{crew} completed their final deck sweep. {officer} confirms tie-downs and tension nets are calibrated. "
        "{captain}, nominal thruster response predicted during atmospheric exit. Fly safe."
    ),
    (
        "Pre-flight cargo manifest officially signed off at {location}. Every crate of {cargo_type} matches UEE Navy logistics protocols. "
        "{officer} reports zero staging bottlenecks on the {ship}. {crew} handled the freight with extreme care. "
        "{captain}, departure corridor assigned. Clear the landing pad when ready."
    ),
    (
        "Ship cargo grid fully energized, balanced, and locked down on the {ship}. "
        "Every container of {cargo_type} passed naval customs inspection at {location} under {officer}. "
        "{crew} has vacated the loading elevator. {captain}, docking clamps release upon engine ignition. Have a smooth transit."
    ),
    (
        "Manifest locked and external gantries disconnected from the {ship} at {location}. "
        "Hold secured for long-range quantum jump with {cargo_type}. {officer} completed the final walkthrough. "
        "{crew} has stowed all heavy lifters. {captain}, center of mass is optimal for fuel efficiency. Good hunting."
    ),
    (
        "Precision military staging complete at {location}. High-grade magnetic fields engaged on the {ship} to secure {cargo_type}. "
        "{officer} verified the manifest checksum against the fleet database. {crew} reports zero hydraulic drift. "
        "{captain}, ATC has reserved your departure window. Spool drives at will."
    ),
    (
        "Freight transfer concluded flawlessly at {location}. {officer} signed off on the balance matrix for the {ship}. "
        "Containers containing {cargo_type} are double-latched with auxiliary magnetic failsafes. "
        "{crew} has returned all tractor equipment to the maintenance bay. {captain}, your flight path is uninhibited."
    ),
    (
        "Logistics division at {location} confirms all {cargo_type} is locked down in the primary hold of the {ship}. "
        "Deck inspection by {officer} confirmed structural grid integrity at 100%. "
        "{crew} executed the load plan with military precision. {captain}, nav-computer has ingested the route coordinates. Safe flight."
    ),
    (
        "Fast-turnaround loading achieved at {location}. The {cargo_type} freight was transferred onto the {ship} in record time. "
        "{officer} confirms mass counters match the official bill of lading. {crew} has cleared the flight deck. "
        "{captain}, shields are pre-cycled and quantum fuel feed is nominal. Clear for immediate liftoff."
    ),
    (
        "Full cargo manifest validation achieved at {location}. {officer} supervised the placement of {cargo_type} across all grid partitions on the {ship}. "
        "{crew} reports zero clearance issues along the access walkways. {captain}, atmospheric pressurization is complete. Fly safe."
    ),
    (
        "All freight units on the {ship} logged and locked at {location}. {officer} confirms magnetic grid draw is within green parameters for {cargo_type}. "
        "{crew} has disconnected ground power conduits. {captain}, primary thrusters are clear for ignition."
    ),
    (
        "Navy cargo specialists finished securing {cargo_type} into the pressurized bay of the {ship}. "
        "{officer} signed the physical dispatch ledger at {location}. {crew} confirmed tie-downs are seated. "
        "{captain}, local sector traffic is light. You have unrestricted departure clearance."
    ),
    (
        "Dispatch validation finalized at {location}. {officer} personally inspected the tie-down integrity on the {ship}. "
        "The shipment of {cargo_type} is isolated from primary avionics harnesses. {crew} has exited via airlock 2. "
        "{captain}, orbital telemetry is clear. Safe travels through the sector."
    ),
    (
        "Logistics manifest cleared through naval customs at {location}. The hold of the {ship} is balanced to within 0.1% of baseline. "
        "{officer} signed off on all {cargo_type}. {crew} cleared the gantry. {captain}, enjoy the smooth quantum run."
    ),
    (
        "Final checklist signed at {location}. {officer} confirms all {cargo_type} containers on the {ship} meet Grade-A transport standards. "
        "{crew} reports zero pad debris. {captain}, launch authority granted by sector control. Fly safe, Captain."
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # ── MEDIUM SEVERITY (20-39): Elevated operational risk & sector hazards ─
    # ══════════════════════════════════════════════════════════════════════════
    (
        "Cargo secured at {location}, but caution is advised, {captain}. Navy intel reports increased outlaw activity along quantum routes near the {ship}. "
        "{officer} recommends powering up primary shield emitters immediately. {crew} worked under elevated protocols to load {cargo_type} quickly. "
        "Pirate scouts may be tracking departure corridors. Keep your turrets manned."
    ),
    (
        "Loading complete at {location}, but a mechanical snag was detected during final inspection on the {ship}. "
        "While {crew} was moving the final {cargo_type}, a minor hydraulic seepage occurred near the elevator manifold. "
        "{officer} had seals re-torqued, but monitor component thermal levels on your MFD during quantum jump. Fly carefully, {captain}."
    ),
    (
        "Logistics delay encountered at {location}, {captain}. Station customs flagged two crates of {cargo_type} for secondary scanning on the {ship}. "
        "{officer} resolved the paperwork, but the delay compressed the launch window. "
        "{crew} had to expedite final mag-lock checks. Double-check cargo hold sensors once clear of the gravity well."
    ),
    (
        "Freight on the {ship} is locked down at {location}, but proximity sensors are picking up minor interference. "
        "{crew} detected electrostatic buildup across the outer hull while loading {cargo_type}. "
        "{officer} verified internal grid locks are holding firm. {captain}, cycle external shields before initiating quantum alignment."
    ),
    (
        "We loaded the {cargo_type} onto the {ship} at {location}, but sensors show an intermittent yellow warning. "
        "During grid activation, the power relay to the secondary cooling line spiked. {crew} verified fuses are intact, but cooler efficiency is down 4%. "
        "{officer} advises monitoring hold ambient temperature during travel. Proceed with vigilance, {captain}."
    ),
    (
        "Cargo manifest for the {ship} signed at {location}, but naval datalink suffered an avionics packet drop during upload. "
        "{officer} had {crew} manually re-sync the telemetry bus twice. Nav-computer may require an extra moment to compute jump vectors for {cargo_type}. "
        "Starboard maneuver thruster shows 3% calibration variance. Stay alert, {captain}."
    ),
    (
        "Pre-flight staging on the {ship} completed at {location}, but an atmospheric storm warning has been posted, {captain}. "
        "Weather radar indicates severe ion turbulence in the upper stratosphere. {officer} recommends steep ascent. "
        "{crew} placed additional physical tie-downs over {cargo_type} to prevent micro-vibrations."
    ),
    (
        "Cargo grid engaged on the {ship} at {location}, but slight acoustic vibration was detected near the lower ramp hinge. "
        "{crew} discovered hairline surface wear on the locking pins under the weight of {cargo_type}. "
        "{officer} confirms it will hold standard transit, but avoid aggressive high-G atmospheric maneuvers. Fly safe, {captain}."
    ),
    (
        "The {ship} is packed at {location}, but security is on high alert. Civil unrest reported near the logistics perimeter. "
        "{crew} was forced to seal hangar blast doors early. {officer} confirms all {cargo_type} is accounted for, but watch for rogue interceptors upon exit. "
        "{captain}, clear the airspace without delay."
    ),
    (
        "All {cargo_type} logged on the {ship} at {location}, but life support scrubbers are drawing auxiliary power. "
        "{officer} noticed the primary particulate filter was saturated with local industrial dust. "
        "{crew} did not have a spare filter in stock. {captain}, secondary filters will suffice, but avoid extended hold occupancy."
    ),
    (
        "Staging at {location} completed under tight ATC constraints. Magnetic grid lock on the {ship} is drawing 15% more current than usual. "
        "{officer} suspects localized electromagnetic interference from {cargo_type}. {crew} reinforced the mechanical clamps. "
        "{captain}, monitor power distribution when charging quantum spools."
    ),
    (
        "Hold secured on the {ship} at {location}, but pirate jamming signals detected on UHF frequencies. "
        "{officer} hurried the loading of {cargo_type} to prevent tracking by local cartels. "
        "{crew} reports all locks seated, but recommends immediate spooling to quantum altitude. Watch your six, {captain}."
    ),
    (
        "Cargo operations concluded at {location}, but ambient gravity fluctuations were noted on the lower deck of the {ship}. "
        "{crew} re-anchored all {cargo_type} with heavy-duty tension cables. {officer} issued an advisory for turbulence during jump entry. "
        "{captain}, maintain standard sub-light speed until clear of local gravity contours."
    ),
    (
        "Manifest registered at {location}, though cargo elevator 4 jammed halfway through loading the {ship}. "
        "{crew} manually hauled the remaining {cargo_type} using localized tractor beams. "
        "{officer} verified full accountability, but workers were fatigued. {captain}, verify mag-lock readouts before breaking orbit."
    ),
    (
        "High-tension turnaround at {location}. Local authorities issued an emergency security sweep while loading {cargo_type} on the {ship}. "
        "{officer} cleared the vessel after a rigorous physical check. {crew} locked the bay doors under navy supervision. "
        "{captain}, departure corridor modified to bypass high-risk zones."
    ),

    # ══════════════════════════════════════════════════════════════════════════
    # ── HIGH SEVERITY (40-59): Critical incidents, emergency evac & combat ──
    # ══════════════════════════════════════════════════════════════════════════
    (
        "Critical emergency in the hangar bay at {location}, {captain}. During staging for the {ship}, an overhead crane suffered localized gravity failure. "
        "A heavy pallet of {cargo_type} broke loose, causing electrical arcing and structural damage to deck sector 3. "
        "{officer} deployed emergency fire teams while {crew} secured the remaining crates with heavy steel bracing. "
        "Outlaw interdictors reported near the orbital perimeter. Punch the throttle and get clear."
    ),
    (
        "Emergency scramble loading on the {ship} at {location} while the sector was under hostile missile alert. "
        "Hangar doors sustained minor blast damage during a pirate raid. {officer} bypassed non-critical safety checks for immediate departure. "
        "{crew} worked under extreme pressure as sirens blared, securing {cargo_type} with emergency magnetic overrides. "
        "{captain}, spool quantum now and jump to the nearest naval rendezvous point."
    ),
    (
        "Hazardous condition during loading at {location}, {captain}. A volatile container among the {cargo_type} suffered a pressure micro-rupture in the hold of the {ship}. "
        "{crew} donned emergency EVA suits, vented the bay into space, and sealed the compromised container. "
        "{officer} reports hold sensors are glitching from vapor residue. Keep suit helmets on until atmosphere scrubbers complete cycling. Extreme caution required."
    ),
    (
        "Severe incident on the landing pad at {location}. A structural support gave way under a heavy load of {cargo_type}, nearly crushing two workers. "
        "{officer} had emergency medical teams evacuate the injured while {crew} stabilized the crane on the {ship}. "
        "Hold is packed to capacity but weight distribution is off by 4%. {captain}, trim maneuvering thrusters before entering warp."
    ),
    (
        "Emergency tactical manifest issued at {location}, {captain}. Hostile Nine Tails interceptors have set up an interdiction snare outside the armistice zone. "
        "{crew} panic-loaded the {ship} under blackout conditions, throwing the last of {cargo_type} onto the grid. "
        "{officer} had to manually bypass safety interlocks. Clamps are at critical load. Break orbit immediately and prepare for evasive action."
    ),
    (
        "Catastrophic crane failure at {location} — a tractor beam emitter surged, dropping two crates of {cargo_type} against the cargo bulkhead of the {ship}. "
        "{officer} patched the damaged power circuits while {crew} chained the compromised containers to the floor ribs. "
        "Rear ramp seal is holding, but hull integrity is down 8% in the aft bay. {captain}, avoid high-pressure atmospheric descents."
    ),
    (
        "Hostile incursion at {location}! Station defences engaged unidentified gunships while loading {cargo_type} onto the {ship}. "
        "{crew} had to abandon the last loading pallet on the lift as explosions rocked the lower hangar. "
        "{officer} signed the manifest via remote datalink from the bunker. {captain}, doors are jammed at 90% open — liftoff immediately and don't look back."
    ),
    (
        "Emergency dispatch under total blackout at {location}. Power grid failed mid-load on the {ship}, forcing {crew} to use auxiliary manual dollies. "
        "{officer} warns that two containers of {cargo_type} could not be laser-scanned before sealing the bay. "
        "Comms are experiencing heavy jamming. {captain}, you are flying with high-risk cargo into an active conflict zone. Godspeed."
    ),
    (
        "Critical loading shift on the {ship} at {location}. Ramp hydraulic line ruptured under the weight of {cargo_type}, triggering an auxiliary fire. "
        "{crew} suppressed the blaze and installed temporary titanium braces. {officer} sealed the damaged sector. "
        "{captain}, do not lower the ramp in high-gravity environments. Jump to naval repair depot immediately."
    ),
    (
        "Final warning, {captain}! Station at {location} is entering full lockdown due to incoming enemy fleet. "
        "Logistics detail {crew} scrambled to seal the {ship} while sirens screamed across all channels. "
        "{officer} logged the shipment of {cargo_type} under emergency wartime code 9-B. "
        "Skip standard departure corridors, power weapons, and burn full afterburner to clear the sector."
    ),
]
