# FIRST-PERSON DUNGEON ARPG — GAMEPLAY & TECHNICAL DESIGN SPECIFICATION

**Document version:** 1.1 · **Date:** 2026-11-18 · **Status:** Normative feature specification (single-player)

> **Interpretation rule:** This document describes the game to build. All systems, content, interactions, persistence rules, and acceptance conditions specified here are requirements. Values labeled *default* are starting balance parameters and must be editable in data, rather than scattered through code. Any unspecified artistic details may be original, but unspecified mechanics must be resolved consistently with the principles and invariants below.

## 0. Product definition

A real-time **first-person, dark-fantasy action RPG** organized around **one persistent town hub and one multi-floor, procedurally assembled dungeon**. The player chooses a class; explores in real time; fights with directional weapons, bows, magic, blocking, and physical kicks; finds randomized weapons, armor, gold, books, and consumables; levels attributes and class skills; returns to town to identify, repair, sell, and restock; then descends deeper through increasingly dangerous environments, bosses, and story events. The game is **single-player only**: no online, LAN, or shared-world multiplayer features are in scope.

**Inspiration boundaries:** Reproduce the *systems and genre feel*, not the characters, places, names, quests, dialogue, monsters, meshes, textures, UI artwork, audio, animations, or source code of any existing game. All named content below is new placeholder fiction that may be replaced with other original content without changing the mechanics.

### 0.1 Gameplay pillars

1. **One town, one dungeon:** A readable, recurring home base anchors a long, dangerous descent.
2. **Tactile first-person combat:** Weapons have range, arcs, windups, hit reactions, stamina costs, distinct sounds, and environmental consequences.
3. **Loot worth examining:** Random item statistics, meaningful affixes, unidentified finds, equipment appearance, usable constraints, and exceptional unique effects.
4. **RPG decisions:** Four primary attributes, three classes, class ability trees, spell learning, item requirements, resistances, and multiple viable builds.
5. **Structured procedural exploration:** Meaningful main paths, side rooms, alternate routes, secrets, traps, and special encounters—not arbitrary corridors.
6. **Risk/reward:** Limited supplies, carrying space, elite foes, resource management, tactical retreats, and valuable deeper rewards.
7. **Atmosphere:** Darkness, readable silhouettes, strong light sources, distinct biomes, environmental narrative, and increasing supernatural distortion.

### 0.2 Player-facing loop

`Create character → Town preparation → Enter dungeon → Explore rooms → Fight / interact / solve → Collect loot & XP → Spend points / equip → Continue downward OR return to town → Sell / identify / repair / restock / talk → Resume descent → Boss → New dungeon region → Final encounter → Ending / continued play`

This is continuous real-time gameplay. Combat, loot, and exploration occur in the same 3D world; there are no separate combat screens or turns.

---

## 1. World, progression and content structure

### 1.1 Location model

- **Town: Hollowmere.** A persistent, navigable outdoor village with central square, merchants, blacksmith, healer, mystic, stash, quest NPCs, ambient inhabitants, a dungeon entrance, and a return-portal anchor. Town is safe: no hostile spawns or player damage.
- **Dungeon: The Underkeep.** One descending network of **16 numbered floors** in **four themed regions of four floors each**. Staircases connect adjacent floors; shortcut routes unlock from deeper floors to town or higher floors.
- **Regions:** Floors 1–4 *Abandoned Barracks* (wood, masonry, scavengers); 5–8 *Ossuary* (crypts, undead, bone); 9–12 *Flooded Works* (channels, industrial ruins, cultists); 13–16 *The Unraveling* (warped architecture, eldritch creatures). Each has its own room kits, props, traps, enemy pool, color/light palette, music, and boss.
- **Floor identity:** Show region, dungeon floor number, discovered-map overlay, active quests, discovered shortcuts, local exits, and boss status. Floor numbering and biome progress are persistent for the character/campaign.
- **Town and dungeon connection:** Physical entrance at town; exiting an explored floor via stairs or a portal returns the player to town without wiping character, loot, XP, quest progress, explored map, or enemies already defeated in that dungeon instance.

### 1.2 Main campaign structure

| Floors | Region | Primary function | Milestone |
|---|---|---|---|
| 1–4 | Abandoned Barracks | Introduce movement, combat, keys, loot, traps, first branching floor | Floor 4 gatekeeper boss; opens Region 2 |
| 5–8 | Ossuary | Poison/curse and undead, locked tombs, optional puzzle rooms | Floor 8 boss; unlocks deeper shortcut |
| 9–12 | Flooded Works | Elemental threats, moving mechanisms, vertical traversal | Floor 12 boss; changes town dialogue |
| 13–16 | The Unraveling | Hybrid encounters, environmental anomalies, rare drops | Floor 16 final boss and ending |

- Every floor contains a reachable start, guaranteed reachable stairs onward (except final floor), a directed main path, and optional branching content.
- Story-critical items and boss keys are **guaranteed obtainable** in that floor's seed. No random layout may make a campaign unwinnable.
- Boss arenas are authored room chunks chosen from a pool; boss phases and loot are driven by data.
- Clearing the final boss resolves the main quest and unlocks continued dungeon play or a New Descent mode with regenerated layouts while retaining the character.

### 1.3 Campaign vs expedition state

- **Persistent character:** level, XP, stats, skills, equipment, inventory, currency, unlocked spells, completed quests, discovered lore, waypoint unlocks, stash, and cosmetic choices.
- **Persistent campaign instance:** dungeon seed, region/floor layouts, unlocked doors, killed bosses, opened one-time chests, quest-object state, exploration fog, discovered secret rooms, floor shortcuts, and dropped ground items.
- **Transient combat state:** enemy positions, active projectiles, temporary buffs, current animations, physics impulses, current audio; resolved or serialized as appropriate when changing floors/saving.
- **Repeatable New Descent:** Explicit menu action creates a new dungeon seed and resets floor enemies, treasure containers, and ordinary floor events; main storyline completion and player progression remain. Quest-specific one-off rewards cannot be duplicated.
- **No unannounced reset:** Ordinary town trips, quitting/loading, and switching floors never reroll a previously generated floor.

---

## 2. Character creation, classes and progression

### 2.1 Character creation

Fields: character name, one of three classes, body/presentation preset, skin/face/hair options, cosmetic colors, voice preset, starting difficulty, character-slot selection. Appearance affects the first-person hands, equipment visuals, character screen, and reflections when available; it confers no stat benefit. Show class summary, initial attributes, starting weapon/armor/consumables, and unique class abilities before confirmation.

### 2.2 Primary attributes

| Attribute | Rules |
|---|---|
| **Strength (STR)** | Increases melee physical damage, stagger force, carrying-free equipment requirement qualification, and heavy-weapon efficiency. Required for many armor/weapons. |
| **Dexterity (DEX)** | Increases bow damage, physical critical chance, attack speed, trap interaction, and dodge efficiency. Required for bows/finesse gear. |
| **Intellect (INT)** | Increases mana, spell damage, magical healing, and spellbook-learning eligibility; required for magical foci. |
| **Vitality (VIT)** | Increases maximum health, stamina, physical status tolerance, and health regeneration. |

- Each level grants **5 unallocated attribute points** and **1 class talent point**. Level cap **30**, initial level **1**; XP threshold is `floor(100 * L^1.55)` for going from level `L` to `L+1` (cumulative XP tracked separately).
- Each class has distinct starting attributes, resource modifiers, and primary equipment. Base attributes cannot be reduced below 1; equipment may modify effective attributes. A character may bank unspent points. Class selection cannot be changed; respec of allocated talent points is available through a town NPC for gold.
- Level-up shows notification, increases max health/mana/stamina, and does **not** silently heal health to full. If max resource changes, preserve the previous current-resource percentage, then cap appropriately.
- Attribute points have immediate effect when spent. If unequipping an attribute-boosting item invalidates a different item's requirements, the invalid item remains equipped but is **disabled** (no stats/abilities) until requirements are restored or it is unequipped; the UI marks the reason. This avoids forced drops and circular auto-equip behavior.

### 2.3 Classes (original archetypes)

| Class | Starting STR/DEX/INT/VIT | Starting gear | Identity |
|---|---|---|---|
| **Vanguard** | 20 / 12 / 8 / 18 | One-handed sword, shield, padded armor, 2 health potions | Block, armor conversion to offense, staggering melee |
| **Stalker** | 12 / 20 / 10 / 14 | Short bow, dagger, leather armor, 1 health + 1 stamina potion | Mobility, bow precision, bleeding and traps |
| **Arcanist** | 8 / 12 / 22 / 12 | Staff, cloth robe, basic spellbook, 1 health + 2 mana potions | Spell manipulation, elemental effects, mana economy |

Class resource modifiers: Vanguard `+15 max health, +10 stamina`; Stalker `+5 stamina, +5% move speed`; Arcanist `+20 max mana, +0.5 mana/sec`. All classes can equip any item whose requirements they satisfy and can use discovered general spells; specialization changes effectiveness, not hard access.

### 2.4 Class skill system

- Each class has **8 class talents**: 5 active abilities and 3 passives. Every talent has **5 ranks**; first point unlocks an active, further points increase magnitude or reduce cooldown. Passives apply continuously; active abilities may be assigned to **Q**, **E**, or the optional action bar slots not currently occupied by consumables.
- Points may be invested only when prerequisites are met: second-tier skills require 3 total points in that class tree; third-tier skills require 8. No arbitrary mutually exclusive build lock unless specified by a skill.
- Active cooldowns start on successful activation, cannot be bypassed by unequip/re-equip, and persist when switching floor or using town portals.

**Vanguard talents**

| Talent | Type | Effect at rank 1; each added rank |
|---|---|---|
| Bulwark Rush | Active | Dash up to 5 m, deal 12 radiant damage + 0.15×current Armor to first target, 10 s cooldown; +15% damage/rank |
| Crushing Verdict | Active | Next heavy strike adds 10 radiant damage and 25 stagger, 8 s cooldown; +5 damage/rank |
| Shield Pulse | Active | Frontal 3 m knockback, 8 physical damage, 12 s cooldown; +10% force/rank |
| Rally | Active | Heal 15% missing health and grant +20 armor for 8 s, 25 s cooldown; +3 armor/rank |
| Defiant Stand | Active | 4 s guard stance, stamina drain on block halved, 24 s cooldown; +0.5 s/rank |
| Iron Training | Passive | +8% base armor; +4%/rank |
| Retaliation | Passive | Successful perfect block adds +10% next melee damage; +5%/rank |
| Heavy Hands | Passive | +6% two-handed damage and stagger; +4%/rank |

**Stalker talents**

| Talent | Type | Effect at rank 1; each added rank |
|---|---|---|
| Shadow Step | Active | 5 m evasion dash, 10 s cooldown; +0.5 m/rank |
| Piercing Shot | Active | Next arrow pierces 2 targets for 120% weapon damage, 12 s cooldown; +10% damage/rank |
| Rend | Active | Next dagger strike inflicts 4 s bleed for 12 total damage, 9 s cooldown; +25% bleed/rank |
| Caltrops | Active | Trap lasting 12 s; slows enemies 35% in a 2.5 m area, 20 s cooldown; +2 s/rank |
| Quickdraw | Active | For 6 s, +25% bow attack speed; 25 s cooldown; +5%/rank |
| Keen Eye | Passive | +4% critical chance; +2%/rank |
| Trap Sense | Passive | Trap highlight from 2 m; +1 m/rank |
| Evasive Footwork | Passive | -8% dodge stamina cost; -4%/rank |

**Arcanist talents**

| Talent | Type | Effect at rank 1; each added rank |
|---|---|---|
| Arc Bolt | Active | Hitscan magic projectile, 16 arcane damage, 5 mana, 1.5 s cooldown; +20% damage/rank |
| Ember Wave | Active | 5 m cone, 18 fire damage, ignite chance 35%, 12 mana, 8 s cooldown; +15% damage/rank |
| Frost Ring | Active | 3 m radius, 12 frost damage, slow 40% for 3 s, 14 mana, 12 s cooldown; +10% slow duration/rank |
| Mana Ward | Active | 10 s ward absorbs 30 damage and consumes 1 mana per 3 damage taken, 20 s cooldown; +10 ward/rank |
| Blink | Active | Teleport up to 6 m to visible navigable location, 15 mana, 13 s cooldown; +1 m/rank |
| Channeler | Passive | +10% mana regeneration; +5%/rank |
| Elementalist | Passive | +6% fire/frost/lightning damage; +3%/rank |
| Spell Echo | Passive | 5% chance to repeat non-ultimate projectile at 40% damage; +3% chance/rank |

Cooldown reduction from Ability Haste follows Section 3; cost, active slot, damage type, range and status effect must be data-defined, with collision/LOS verification. Skill upgrades and scaling appear in tooltips.

---

## 3. Character derived statistics and damage model

### 3.1 Derived stat formulas (defaults)

Let `L` be character level, `A` worn armor rating, and `B` total flat bonuses from active, valid gear and passive effects.

| Stat | Formula / rule |
|---|---|
| Maximum health | `40 + 2*VIT + 5*(L-1) + class_health_bonus + B_health` |
| Maximum mana | `10 + 2*INT + 3*(L-1) + class_mana_bonus + B_mana` |
| Maximum stamina | `40 + VIT + floor(DEX/2) + class_stamina_bonus + B_stamina` |
| Physical armor | `max(0, sum(item_armor) + buffs + B_armor)` |
| Armor reduction | `armor / (armor + 100 + 8*(attacker_level-1))`, capped at 75% |
| Melee additive damage | `0.25*STR` one-hand; `0.35*STR` two-hand; finesse weapons may use `max(0.18*STR,0.3*DEX)` |
| Bow additive damage | `0.28*DEX` |
| Spellpower multiplier | `1 + 0.015*INT + B_spellpower_fraction` |
| Base critical chance | `2% + 0.12%*DEX + B_crit`, capped at 60% |
| Critical damage | `1.5×` final outgoing damage before target mitigation, plus bonuses |
| Melee speed modifier | `1 + min(0.60,0.004*DEX + B_attack_speed)`, weapon baseline varies |
| Movement speed | `4.5 m/s * (1 + B_move_speed)`, class bonuses included |
| Life regeneration | `0.1 + VIT/100 + B_life_regen` HP/s, paused for 3 s after taking damage unless special effect overrides |
| Mana regeneration | `0.5 + INT/40 + class_mana_regen + B_mana_regen` mana/s |
| Stamina regeneration | `15 + 0.15*VIT` stamina/s, beginning 0.8 s after last stamina expenditure |
| Effective skill cooldown | `base_cooldown / (1 + ability_haste_percent/100)` |
| Magic/element resistance | Clamp each element's total between **-50% and +75%**; damage multiplier `1 - resistance_fraction` |
| Status resistance | Clamp 0–80%; reduces incoming status duration and buildup, but cannot negate explicitly unavoidable boss mechanics |
| Life steal / mana steal | Percent of **actual post-mitigation direct weapon damage**, capped per second at 12% max resource; does not trigger on DoT or self-damage |

**Damage types:** physical (`slash`, `pierce`, `blunt` tags), fire, frost, lightning, arcane, radiant, shadow, poison. Physical uses armor reduction. Non-physical uses matching elemental resistance; arcane/radiant/shadow may use *magic resistance* unless an item adds specific resistances. Poison uses poison resistance. A mixed attack is split by damage component and mitigated independently.

**Damage pipeline:** skill/attack activation → verify animation timing, stamina/mana and cooldown → hit detection and line of sight → base weapon or spell roll → add attacker's attribute and flat bonuses → modifiers/crit/headshot → target block/dodge/parry → armor or typed resistance → status buildup, life-steal and reflected effects → apply HP loss/poise loss → reaction/death/XP/loot. No double-hit from one hitbox/target during a single swing unless explicitly defined multi-hit.

### 3.2 Status effects and rules

| Status | Effect and interaction |
|---|---|
| Bleed | Physical damage over 5 s; stacks intensity up to 3; no effect on bloodless/spectral enemies |
| Burn | Fire damage over 4 s; stacked application refreshes and increases damage to cap 3; water can extinguish |
| Poison | Poison damage over 8 s; stacks up to 3; antidote cures |
| Frost / Chill | -30% movement and -15% attack speed for 4 s; buildup threshold causes 1 s freeze (bosses instead stagger) |
| Shock | +15% incoming lightning damage for 4 s, small chance to interrupt casting |
| Curse | -15% all resistance for 10 s; removed by cleansing shrine or potion |
| Stun | Cannot act for duration; repeated stuns create temporary diminishing returns; bosses gain shorter interrupt windows |
| Fear | Enemy attempts retreat for 3 s, breaking attack windups; immune-tagged bosses resist |
| Slow | Slows movement only unless effect also defines attack-speed penalty |

Every actor has resistance tags (`undead`, `living`, `armored`, `flying`, `construct`, `boss`) and immunities per ability. DoTs have identifiable source/owner for XP and kill credit. Timers are deterministic game simulation time, with pausing behavior specified in the save system.

### 3.3 Displayed character sheet

Display: name, class, level, experience bar and numeric next threshold, unspent points, STR/DEX/INT/VIT with base/gear breakdown, damage range, attack speed, spellpower, ability haste, critical chance/damage, life/mana steal, movement speed, armor, block chance/efficiency, magic resistance and all elemental resistances, status resistance, life/mana/stamina and their regeneration, active status effects, weapon DPS estimate, and total gold. Tooltip any value to see its calculation. Highlight temporary bonuses and unmet requirements.

---

## 4. First-person controls, movement, camera and interaction

### 4.1 Default input scheme (fully remappable)

| Input | Action |
|---|---|
| WASD | Move, strafe and backpedal |
| Mouse | Free-look; first-person perspective |
| Left mouse | Light melee attack / fire current ranged weapon / cast selected attack spell |
| Hold left mouse | Charge heavy attack, release to strike; for bows, draw and release arrow |
| Right mouse | Raise shield / guard with weapon / aim bow or alternate casting action, based on equipment |
| F | Physical kick or shove |
| Space | Jump / mantle low ledge when valid |
| Left Shift | Sprint (drains stamina) |
| Left Alt | Directional dodge / evade, stamina cost |
| C | Crouch / stand, subject to overhead clearance |
| E | Interact; Q and R are class skill slot 1/2 by default (rebind allowed) |
| 1–6 | Six quick-access belt/hotbar slots for consumables, items or slotted skills |
| Tab | Character / inventory sheet (tabs: inventory, character, skills) |
| M | Full map overlay; minimap remains top-left by default |
| J | Journal / quests / lore / bestiary |
| T | Town-return spell/portal when unlocked, or scroll when available |
| Escape | Pause/menu/settings; menu pauses the world |
| G | Drop highlighted inventory item, with confirmation for rare/unique |
| H | Sheathe/unsheathe main weapon; changes first-person posture, no combat advantage |

**Important binding conflict resolution:** `E` is interaction, not a second skill. The on-screen two ability slots are labeled **Q** and **R**. All screenshots are visual inspiration, not binding requirements. All user-visible hints reflect the actual current bindings.

### 4.2 Movement/camera requirements

- Smooth FPS movement, gravity, collision, stairs, slopes, step-up, crouch where clearance requires it, jump and mantle, sprint, and dodge. No double jump or unrestricted wall-running.
- Default walking 4.5 m/s, sprinting 6.3 m/s, crouching 2.2 m/s. Sprint consumes 12 stamina/sec. Dodge travels ~3 m over 0.35 s, costs 20 stamina and grants 0.15 s avoidance window; a collision or invalid destination shortens movement without clipping through solid geometry.
- Grounded camera eye height ~1.7 m; configurable field of view default 85° horizontal-equivalent engine convention; head-bob, weapon sway and camera shake adjustable/disableable. Collision keeps first-person weapon mesh and camera from passing through walls.
- Movement and action inputs may queue for 150 ms. Camera and input remain responsive during attacks, subject to animation turn constraints. Sprint cancels drawn bow/long spell windup when appropriate.
- Water, lava, darkness, slippery surfaces and hazardous platforms change traversal/combat via data-defined surface effects.
- NPCs, doors, chests, items and traps use an interaction ray from camera, default range 2.5 m, with unobstructed line of sight. Show name and action prompt, and change highlight for lootable, locked, usable or quest objects.
- Destructible barrels, furniture and props use physics/health tags and may spill loot, block pathways temporarily, or be kicked aside; no essential path can be permanently obstructed by movable physics objects.

### 4.3 Equipment in world

- Currently held weapon, shield/off-hand, glowing enchantments and affected hands visible in first-person. Weapon shape and material affect attack animations, hit reach, timing and impact sound.
- Equipped gear visibly changes a third-person character preview; item cosmetics should map to an asset variant from a common equipment rig or attachment system.
- Dynamic light from torches, glowing weapons, spells and lanterns affects nearby rooms and is meaningful for navigation.

---

## 5. Real-time combat

### 5.1 Attacks and weapon categories

Every weapon defines: damage min/max, damage type mix, reach, light/heavy animation and windup/recovery, stamina cost, poise damage, critical multiplier modifier, speed class, block compatibility, projectile parameters, directional attack arcs, special weapon tags, durability, equipment requirements, and first-/third-person asset references.

| Category | Behavior |
|---|---|
| Sword | Medium reach, quick slashing chain, balanced critical and stagger |
| Axe | Broad swing, high chopping/severing effectiveness, medium speed |
| Mace / club | Short-mid reach, blunt stagger, improved effect versus armored/undead |
| Dagger | Very fast, short reach, high backstab/crit synergy |
| Spear / polearm | Long straight thrust, poor close-range arcs, normally two-handed |
| Greatsword / maul | Slow two-handed attacks, broad/high impact, greater stamina cost |
| Bow | Draw/release projectile with travel and drop, ammo consumed; aim mode |
| Staff / wand | Weak physical strike plus charged magical action or embedded spell charges |
| Unarmed | Weak fast attack; can kick; fallback when gear removed/broken |

- **Light combo:** 2–3 attacks with distinct timings, brief cancel windows, per-swing collision; no infinite click spam bypassing recovery.
- **Heavy:** charge 0.35–1.0 s; damage multiplier 1.5–2.2× depending on charge time; higher poise/limb damage; costs more stamina and can break guards.
- **Attack arcs:** hit detection must agree with visible weapon motion. Sweeps can hit multiple targets with per-target falloff; thrusts use focused forward trace/projectile-like reach.
- **Shield block:** directional frontal protection within ~100° cone, absorbs 70–95% physical damage and some elemental damage depending on shield. Consumes stamina proportional to blocked damage; broken guard triggers 1 s stun and protection loss.
- **Perfect block/parry:** within first ~0.18 s of raising an eligible guard, negates more damage, staggers most standard enemies and enables counterattacks. Large/boss attacks can be tagged unblockable or unparryable, with clear telegraph.
- **Dodge:** avoidance frames only in dodge window; enemy area hazards remain active outside that window. Attacks cannot originate from an invalid wall position.
- **Ranged:** arrows have speed, gravity, collision, optional penetration, headshot/weak-point bonus and recoverable/consumed ammo rules. Enemy projectiles telegraph direction and can be blocked or dodged.
- **Magic:** spells have cast time, mana cost, cooldown, typed damage, range, projectile/AOE/target rules; interrupts and line-of-sight handling.
- **Aim:** crosshair indicates hit, blocked hit, interactable and out-of-range; damage numbers and enemy HP bar are optional UI settings but accurate when enabled.

### 5.2 Stamina, poise and attack interruption

- Light attacks cost 6–12 stamina; heavies 15–25; kicks 12; blocks cost 2 stamina on initiation plus incoming-damage proportional cost; bow shots cost 6; cast costs are mana-driven unless specified otherwise.
- When stamina is insufficient, actions fail with appropriate feedback; the player cannot enter unlimited negative stamina.
- Each combatant has poise/max poise. Heavy, blunt, shield bash and kicks deal extra poise damage; when threshold is exceeded, trigger stagger and reset poise after recovery. Standard enemies can stagger frequently, elites have resistance, bosses use phase/window-specific poise rules.
- An attack interrupted before its hit frame does not inflict damage. An attack committed after a projectile release retains its projectile even if caster dies. Dodge or block does not generate unintended duplicate attack events.

### 5.3 Kick and physics interaction

- `F` delivers a forward kick: ~2 m melee reach, short cone, 12 stamina, 6 base blunt damage, 20 poise damage and directional impulse. Kicks can interrupt small enemies, push them into pits/traps/fire, knock crates around, open destructible containers, and launch loose severed body parts.
- Equipping special boots may add fire, lightning, poison or greater knockback to kicks; boots with no modifier use ordinary physical damage. Kicked objects retain velocity, collide with world/actors and apply impact damage **once per meaningful collision**, with a speed-based cap to avoid physics exploit loops.
- Environmental kills yield normal XP and loot, credited to the actor that most recently caused the relevant shove/damage within a valid window. Fall damage to monsters follows the same event/credit system.

### 5.4 Dismemberment / targeted anatomy

- Enemies may have per-limb hitboxes: head, torso, left/right arms, left/right legs, wings/tentacles. Damage contributes to both target HP and local limb injury. Slashing/chopping damage has increased sever chance; blunt may cripple without sever; piercing can damage weak points.
- Default sever threshold: local accumulated eligible damage reaches **60% of target max HP** or a single slash hit exceeds **35%**; the target must possess the named limb, the limb must be severable, and the attack must pass weapon/tag checks. Boss body parts use author-defined thresholds.
- Severing has a *gameplay effect*: arm loss disables that arm's attack/weapon; leg loss slows or forces crawl; wing loss grounds flyers; tentacle loss disables a corresponding attack; decapitation kills normal living humanoids but **some undead continue without a head** using alternate behavior.
- Severed parts become temporary physics props. A kicked head can collide with and damage another enemy. Maintain debris limits and despawn lifetime, but do not despawn an in-flight part before its hit resolves. Disable dismemberment gore in settings without changing enemy functionality (substitute neutral break/disable effects).
- Headshot multiplier default 1.5× for susceptible targets. Non-anatomical creatures, spectral beings, constructs and bosses define own weak spots and immunity behavior; they must never receive arbitrary fatal headshots.

### 5.5 Enemy telegraphs and fairness

Enemy attack startup includes silhouette, animation, sound and (where applicable) windup glow; attack hitboxes are active only during the authored hit window. Multiple attackers have spatial collision/separation so enemies cannot perfectly stack. Attacks through walls are prohibited unless explicitly tagged magical wall-piercing and visibly telegraphed. Breaking line of sight resets or changes pursuit intelligently; enemies do not require global knowledge of player position.

---

## 6. Inventory, equipment and item interaction

### 6.1 Inventory grid

- Player backpack is **10 columns × 6 rows** of item cells (default). Every item has defined footprint (`w × h`) and can optionally rotate 90° while dragged if its type permits. Stackable consumables occupy one cell per stack; equipment may occupy 1×2, 2×2, 1×3, 2×3 etc.
- Left-click item to pick up/drag, place on free grid space, or swap with a compatible single item; right-click to use/equip; double-click to equip/use; Shift-click quick-transfer when a vendor/stash is open; Ctrl-click split stack; tooltip on hover (name, rarity, requirements, mods, value, durability, comparison to equipped).
- Grid collisions are exact. No overlapping items, negative stacks, orphaned item IDs, or disappearing items. Pickup fails cleanly if no valid space, with message; item stays in world.
- Sorting button packs items deterministically without destroying manual arrangement; sort only on explicit request. Stack merges only same definition/roll/state when legal. When an equipment item is removed, it must fit in backpack or the action is blocked, unless explicitly dropping it to the ground.
- Gold has a currency counter and never consumes cells; player can inspect gained gold amounts from world pickups. Optional currency drops recoverable on death.

### 6.2 Equipment slots and restrictions

Mandatory slots: **head, chest, gloves, boots, primary hand, off-hand, amulet, ring 1, ring 2**. Optional cosmetic back slot has no stat effect unless data says otherwise. One-handed weapons pair with off-hand shield, focus or second one-handed weapon if that build can dual-wield; two-handed weapons occupy both hand slots. Bow occupies both hands; the ammo pool/arrow quiver is represented as ammo inventory rather than a second physical weapon.

- Slot validation checks item category, requirements, class restrictions if any, dual-wield rules, unique-equip flags, and equipment conflicts *before* mutating inventory.
- Equipping updates all derived stats, visual meshes, attack animations, kick modifiers, passives and inventory footprint. Equipment changes cannot grant resources above max or drop resources below zero.
- **Durability:** gear has `current/max` durability; attacking/receiving strikes erodes gear appropriately. At zero durability, item remains present but provides no stats or valid attack until repaired. Repair UI shows cost and exact before/after values.
- **Requirements:** STR/DEX/INT/level gates shown with red warnings. Loot may be carried without meeting requirements. Failed equip never consumes or replaces an existing item.
- Item comparison displays changed damage range, DPS, armor, resistances and notable effects, not merely one aggregate score.

### 6.3 Belt, quickbar, and consumables

- Six quick-access slots `1–6`, visually centered on lower screen; slots bind a consumable stack, scroll, item action, or active skill. **Q/R** remain class active slots.
- Consuming a potion reduces its stack by exactly 1 and triggers the shared potion cooldown of **1.25 s**; attempting to use an empty slot or potion during cooldown provides feedback without consumption.
- If a stack is depleted, slot stays bound to its item type and automatically rebinds to another legal stack when present; if no stack remains, shows empty icon.
- Potion types: minor/standard/greater health, minor/standard/greater mana, stamina tonic, antidote, cleanse, and temporary resistance elixir. Healing is instantaneous with visual/sound feedback, capped to max; no overheal unless a rare effect explicitly grants a shield.
- Default health/mana potion restore fractions: minor **30%**, standard **50%**, greater **80%** of maximum respective resource. Stamina tonic restores **70%** of maximum stamina. Antidote/cleanse target appropriate statuses. Elixir grants **+25%** selected resistance for 30 s subject to resistance cap.
- Scrolls are consumed on cast, using the scroll's spell and charge rules; do not also deduct mana unless scroll explicitly requires it.

### 6.4 Item rarity and identification

| Rarity | Default display | Generation rule |
|---|---|---|
| Common | Neutral/white | Base item, no magical affixes |
| Enchanted | Blue | 1 random valid magical affix |
| Rare | Yellow | 2–4 compatible magical affixes |
| Relic (unique) | Gold | Authored named effect package, distinct behavior, fixed special identity with bounded rolls |

- Magical rarity is visible on the ground/in bag. Affixes may be **unidentified**; the item appears with a generic magical descriptor until the player uses an identification scroll or town sage. Unknown affix effects can remain mechanically active when equipped, but tooltips do not disclose exact rolls until identified; never show false stat sums.
- Relics may change combat behavior (e.g. flaming sword emits light and adds burn, shield converts blocked damage into radiant pulse, boots alter kick element). Each relic has authored eligibility, drop level, unique effect, base item and non-duplicative identity within one campaign instance where specified.
- Item rarity does not bypass equipment requirements. A common item with better base damage may legitimately beat a magical item.

### 6.5 Loot generation

- Items are instantiated from item bases and randomly rolled affix templates with level bands, applicability constraints, conflicts, weights, and min/max ranges.
- `item_level = max(1, floor_depth + enemy_level_offset + rarity_source_bonus)`; pick from bases with min-level eligibility; select affixes whose level ranges and tags match item type, then roll values with a seeded RNG.
- Default eligible ordinary item rarity distribution: **65% common / 25% enchanted / 9% rare / 1% relic**, adjusted by elite/boss/container source. Bosses always drop one rare-or-better item, plus their quest-locked progression reward where relevant.
- Affix examples: `+STR/DEX/INT/VIT`, `+flat health/mana/stamina`, `+min/max physical damage`, `+spellpower`, `+attack speed`, `+crit chance`, `+crit damage`, `+armor`, `+one or all resistances`, `+regen`, `+life/mana steal`, `+move speed`, `+ability haste`, `+elemental damage`, `on-hit status`, `kick effect`, `light radius`, `shield stamina cost`, `mana cost reduction`.
- Affix restrictions: a shield-only modifier cannot appear on a sword; duplicate exclusive prefixes do not stack within one item; no impossible requirement generated beyond attainable level/attribute caps; mutually exclusive effect tags are enforced.
- Loot-roll random streams are independent from enemy AI/physics random streams. A chest or boss with an already-committed reward cannot be rerolled through save/load.

---
## 7. Magic, spellbooks, scrolls, charges and shrines

### 7.1 Global magic system

- All classes can learn **general spells** using scrolls and books, subject to INT and minimum level requirements. Arcanist starts with one learned attack spell and specializes in the system.
- A spellbook item is a consumable permanent-learning item: on first use, unlock the indicated spell; subsequent uses level the spell to maximum spell rank **5**, increasing damage/utility and sometimes efficiency. If at cap, the book cannot be consumed and may be sold.
- `learn_requirement_INT = base_INT + (new_spell_rank-1)*4`. Failure must show the unmet requirement, without consuming the book.
- Spell casting checks mana, silence/interruption, cooldown, equipped casting requirements, target validity, line of sight, and placement. Mana is deducted at commit/cast-release; canceled pre-commit casts do not spend mana unless the spell explicitly states otherwise.
- Spells are usable from a selectable spellbook, Q/R where compatible, or quickbar slots; the UI shows rank, effect, cost, cast time, cooldown and damage type.
- Staff/wand spells may use **charges**. A charged item has current/max charges; its attached spell can be cast without player mana until charges are depleted, then must be recharged at the mystic or via class/consumable effect. Charges cannot drop below zero.

### 7.2 Required general spell catalog

| Spell | Type | Rank-1 rule |
|---|---|---|
| Magic Dart | Arcane projectile | 10 damage; 4 mana; 0.4 s cast; 0.8 s cooldown; 20 m |
| Ember Orb | Fire projectile + radius | 14 fire direct + 8 in 2 m blast; 12 mana; 1 s cast; 3 s cooldown |
| Ice Lance | Frost projectile | 16 frost, +40 chill buildup; 10 mana; 0.7 s cast; 2 s cooldown |
| Forked Lightning | Chain lightning | 12 lightning, chains to 2 additional targets for 70% previous hit; 16 mana; 4 s cooldown |
| Mend Wounds | Heal | Heal `20 + 0.7*INT` HP; 14 mana; 8 s cooldown; cannot revive the dead |
| Stone Skin | Buff | +25 armor for 20 s; 18 mana; 25 s cooldown |
| Reveal | Utility | Reveals nearby loot/interactables and hidden-door hints for 8 s; 10 mana; 15 s cooldown |
| Phase Step | Mobility | 4 m blink to nearest valid unobstructed navigable destination; 14 mana; 10 s cooldown |
| Venom Mist | AoE poison | 3 m radius cloud for 5 s, applies poison; 16 mana; 10 s cooldown |
| Return Sigil | Travel | Channel 3 s to create a return portal, no combat use within 5 s of taking damage; cost 25 mana or consume portal scroll |

Higher spell ranks primarily increase damage/utility by **+20% per rank**; non-damage spell ranks improve magnitude by **+15% per rank**. Mana cost increases **+10% per rank**, with displayed rounded value, unless the spell defines a different progression. Spellbooks do not confer a known spell above level 5.

### 7.3 Environmental shrines, altars and fountains

- Shrines are rare world objects with displayed name/description after interaction and a defined effect: restorative fountain (health/mana), temporary blessing (armor/damage/resistance), revelation (map reveal), transmutation (change equipment affix within constraints), risk shrine (strong buff plus a curse), cursed altar (summons an elite for reward).
- Each shrine has `one_use_per_instance` or `per_player` policy, an RNG seed for randomized effect, activation sound/VFX and journal discovery. Effects persist for specified duration across floor transitions but not through death unless tagged persistent.
- Health/mana fountains display depleted state after use and cannot be reactivated through save/reload. Shrines never irreversibly delete main-path quest items or make attributes invalid.

---

## 8. Town hub, vendors, economy and services

### 8.1 Required town layout

A walkable village with unique silhouettes and signs for the following interactables, accessible from any world state in which the player is alive:

| Location / NPC role | Functional requirements |
|---|---|
| Smith / armorer | Buys equipment; sells mundane weapons/armor; repairs gear, previews costs and outcomes |
| Alchemist | Sells health/mana/stamina/antidote/elixirs; buys consumables; occasionally sells recipes |
| Mystic / archivist | Identifies magical items; buys scrolls/books/foci; sells spellbooks and identification/portal scrolls; recharges staves |
| Healer | Restores all health and clears poison, curse and wounds for gold; optional conversation choices |
| Quartermaster | Shared stash access; buy equipment and weapon ammunition; can unlock extra stash tabs |
| Chronicler / quest giver | Main and side quest dialogue, rumors, lore, reward claims and journal entries |
| Training master | Respec class skills and display ability descriptions/test dummy interactions |
| Dungeon gate | Physical transition to Floor 1, with shortcut selection for activated deeper waypoints |
| Town portal anchor | Safe arrival point for returns, local VFX and re-entry option to the source portal |

- NPCs have idle schedules/ambient barks, persistent quest dialogue flags, interaction animations, and appropriately labeled menu states. Dialogue never locks mouse/game input after dismissal.
- Shop windows include categories, buy/sell panels, price, stock, tooltip, gold before/after and disabled-state reasons. Shift-click transfer rules apply. Purchases are transactional: either both gold and item change, or neither.
- Town **stash** defaults to **12×10 item grid** with **three tabs**, persistent per account/campaign and safe across character changes when sharing is enabled.

### 8.2 Currency and prices

- **Gold** is the primary currency. Gold from killed enemies, containers and quest rewards is picked up into counter. Display gain/loss logs.
- Base purchase price = `round(base_item_value * (1 + 0.12*item_level) * rarity_multiplier)` with multipliers common `1`, enchanted `2`, rare `4`, relic `8` unless unique authored price overrides.
- Sale price default **25%** of purchase value, rounded down, minimum 1 gold. Quest items cannot be sold or dropped unless explicitly defined; vendor buyback tab retains the last 20 sold eligible items per session/campaign.
- Smith repair cost = `ceil((max_durability-current_durability)/max_durability * base_buy_price*0.2)`, minimum 1 gold; cannot exceed price shown.
- Identification price = `20 + 10*item_level`; identification scroll identifies one item anywhere in player inventory. Staff recharge cost based on missing charges and item level.
- Merchant stock has mundane staple products always available plus finite randomized enchanted goods, initially generated from character level/depth; restocks **once per newly reached dungeon floor** and only once for that milestone. Restocking does not remove items currently involved in an open transaction.
- Selling a rare item, spending gold on services and buying consumables all update in the same save-state ledger to prevent repeat/rollback duplication.

### 8.3 Conversation and quest UX

- NPC dialogue UI: speaker name, portrait or in-world view, subtitle, optional voiced line, player choice options, continue/exit, quest accept/turn-in, merchant/services branch.
- Available dialogue branches depend on main quest flags, dungeon depth, items, side quest results and notable discoveries. Show unplayed/important dialogue without forcing repetition.
- The journal can track a quest and show its objective marker only if the world has a lore-justified location; do not reveal hidden treasure rooms by default.

---

## 9. Procedural dungeon generation (structural specification)

### 9.1 Generation approach

Generate a **connected logical room graph first**, then physically assemble **hand-authored 3D room/corridor chunks** according to connectors and constraints. The floor must feel designed while retaining layout, encounter, loot and secret variation. Every room chunk may contain vertical elevation, stairs, pits, platforms, bridges, alcoves, or deliberate intersections if it declares valid collision/navigation/overlap rules.

**Two layers:**

1. **Logical graph**: rooms as nodes; traversable links, locked edges, secret edges, one-way drops, vertical connections, and quest constraints. Controls pacing and ensures critical-path connectivity.
2. **Spatial realization**: chunks chosen by theme, geometry, connector orientation, footprints, clearance and encounter metadata, then placed in 3D with collision tests, navmesh creation/lookup, light/prop assembly, loot, traps and enemies.

### 9.2 Chunk definition and sockets

Each reusable chunk asset declares:

```yaml
id: ossuary_hall_cross_03
biome_tags: [ossuary]
role_tags: [hallway, junction, combat]
weight: 6
footprint_cells: [4, 4]
height_range_m: [0, 5]
allowed_rotations_deg: [0, 90, 180, 270]
max_uses_per_floor: 2
connectors:
  - {id: north_a, position: [0, 0, 4], facing: north, width: 2, kind: door, traversal: walk}
  - {id: east_a, position: [4, 0, 0], facing: east, width: 2, kind: open, traversal: walk}
  - {id: lower_a, position: [0, -3, 0], facing: down, width: 2, kind: stairs, traversal: walk}
spawn_anchors:
  monsters: [combat_zone_1, combat_zone_2]
  loot: [chest_socket_1]
  traps: [floorplate_2]
  narrative: [inscription_1]
navmesh_profile: human_medium
clearance_tags: [humanoid, bow_line_of_sight]
lighting_profile: cold_torch
```

Chunk contract:

- Every connector has compatible kind/width/elevation/traversal and a world-space transform. Joining two connectors must align positions and facing and avoid visible gaps.
- A chunk has bounding footprint/occlusion and optional safe overlap volumes. Overlap is forbidden unless both chunks explicitly allow the intersection type and navigation remains continuous.
- Doorways, rooms, props and traps cannot clip into each other; stair landings have safe approach space; reachable surfaces have appropriate player/AI clearance.
- A chunk has spawn anchors but **does not independently decide** how many enemies/treasures to contain—that is decided by encounter budgets and logical floor graph.
- Unique set-piece chunks can be constrained to particular graph roles/floors. Reused chunks may rotate and vary props/lights/spawns so repetition is less obvious.

### 9.3 Logical floor graph rules

Per floor generate:

1. `start` node: safe insertion zone and map marker.
2. `critical_path`: **7–12 connected nodes** in Floors 1–4, growing by +1 to +3 nodes in later regions; includes planned pacing labels such as intro, combat, respite, challenge, reward and exit.
3. `side_branches`: **2–5 optional branches** with 1–4 rooms each, some loop back to another main-path room.
4. `exit`: a clearly distinguishable stairs/transition; required boss floors place boss node before the exit.
5. `special`: select lore, shrine, treasure, trap, secret, key/lock or side-quest rooms from per-floor budgets.
6. `loop_edges`: add **1–3 cross-links** when realizable without invalidating progression locks; minimum one meaningful route choice except tutorial Floor 1.
7. `gates`: locked or mechanism-controlled edges with keys/switches guaranteed in areas accessible before the gate. Secret doors **never** gate mandatory critical path.
8. `safezones`: place respite areas after high-threat sequences and a safe approach to boss arenas.

Logical nodes have roles and constraints; e.g. `treasure_after_elite`, `key_before_locked_door`, `boss_last`, `lore_required_on_main`, `shrine_optional`, `no_spawns_at_start`, `upper_floor_elevator_shortcut`. A graph solver ensures reachable path to all mandatory rewards before spatial chunks are selected.

### 9.4 Spatial assembly algorithm

```text
function GenerateFloor(campaignSeed, floorIndex, contentVersion):
    rngGraph  = RNG(Hash(campaignSeed, floorIndex, "graph", contentVersion))
    rngRooms  = RNG(Hash(campaignSeed, floorIndex, "rooms", contentVersion))
    rngFoes   = RNG(Hash(campaignSeed, floorIndex, "enemies", contentVersion))
    rngItems  = RNG(Hash(campaignSeed, floorIndex, "items", contentVersion))
    graph = BuildConstrainedGraph(floorIndex, rngGraph)
    AssertMandatoryReachability(graph)
    place graph.start using biome-compatible safe chunk
    for each unplaced graph node in constraint order:
        choose compatible parent socket + chunk candidate + orientation
        reject blocked, incompatible or unsafe candidate
        commit successful placement and connector linkage
        backtrack or choose another chunk if placement fails
    connect approved cross-links; cap unused sockets with walls/doors
    build/probe navmesh and collision, floor portals and interactables
    place enemies, containers, traps and props from node budgets using independent RNGs
    AssertFloorPlayabilityAndRewardReachability()
    return fully specified FloorInstance including seed and mutable object IDs
```

- If a seed cannot satisfy the layout after a bounded number of candidate attempts, deterministic fallback uses a validated authored room-chain with branches, **not** an unconnected or partially spawned floor.
- Same seed + same content version + same settings generates the same initial floor layout and rewards. Spawning a dynamic physics object or entering a shop must not change committed drop outcomes.
- Store content version with floor instance; when loading after an update, load saved placements if available rather than silently rerolling geometry.
- All critical rooms, doors and interactive objects have stable unique IDs (for example `campaign/floor/room/object`) for persistence.

### 9.5 Placement, enemy and loot budgets

| Floor property | Default |
|---|---|
| Main-path nodes | 7–12, increasing with region |
| Optional branches | 2–5 |
| Secret rooms | 0–2 (one guaranteed on every second floor) |
| Shrines/fountains | 0–2 |
| Common chests | 3–7 |
| Rare/locked chests | 0–2 |
| Enemy groups | 5–12 on ordinary floors; budget grows with depth |
| Elites | 0–1 at Floors 1–2; 1–3 afterward |
| Special event room | 0–1, except fixed story floor |
| Boss | Mandatory Floors 4, 8, 12, 16 |
| Traps | 2–8 according to biome |

- Floor challenge budget scales as `base_budget(floor) * difficulty_multiplier` with authored encounter caps. Enemy tiers have budget costs (`grunt 1`, `ranged 1.5`, `brute 2.5`, `elite 5`, `boss special`). The same budget may produce varied compositions with restrictions on simultaneous ranged enemies in narrow rooms.
- Loot budget is independent of number of monsters killed; hard encounter rooms may receive increased item-roll sources, making optional danger rewarding. Containers and boss drops are committed on initial spawn/opening and cannot be duplicated.
- Do not spawn monsters within 8 m of a floor entry point, directly on occupied player space, behind a locked gate they cannot reach when their presence is mandatory, or inside inaccessible geometry.

### 9.6 Minimap, full map, fog of war

- Minimap top-left uses a simplified line/floor-plan view showing discovered rooms/corridors, player facing arrow, discovered exits, waypoints, key doors and optionally current objective. Unseen cells hidden; visited cells persistent; discovered-but-unvisited cells visually distinct.
- Full-screen overlay supports zoom, pan, floor name and legend. Secret rooms remain hidden until detected/entered. Different vertical floors do not overlap into a confusing single map.
- Map geometry derives from actual generated chunk topology, not an independently guessed maze. As the player explores, reveal local room/corridor volume by visibility/proximity, including door connections when seen.

### 9.7 Navigation and persistence of floors

- Enemy AI can traverse generated stairs, doors, corners, ramps and designated jumps/drops it is capable of. Navigation is rebuilt or linked from chunk navigation regions after assembly; doors update traversability when unlocked/opened.
- A door has persistent states (`closed`, `open`, `locked`, `jammed`, `destroyed`). Player and AI cannot interact across a blocked door except through permitted attacks.
- Revisiting a floor restores the same layout, opened doors, chest states, completed event flags and killed unique enemies. Ordinary enemies remain defeated until explicit New Descent, preventing infinite replay farming by floor swapping. Dropped items persist until picked up, or until an explicit documented cleanup rule applies; quest items never expire.
- Town portal return records the source floor and safe return position. Re-entering through its paired portal restores the location if valid; portals expire only on explicit campaign reset or if their source becomes invalid.

---

## 10. Enemies, combat AI, encounters and bosses

### 10.1 Enemy data and state machine

All enemies have a common actor definition: stable ID, archetype, level, faction, tags/immunities, health, armor, resistances, stamina/poise, perception range/FOV, movement speed, attack list (damage/range/cooldown/telegraph/hitboxes), reaction behavior, loot table, XP, anatomy parts, animation/sound/VFX references and AI parameters.

State machine: `DORMANT → PATROL/IDLE → INVESTIGATE → ALERT → CHASE/REPOSITION → WINDUP → ATTACK → RECOVER → (CHASE or FLEE) → STAGGER/KNOCKDOWN → DEAD`.

- Perception uses hearing events (footsteps, sword clashes, spells, kicked objects), cone/line-of-sight sight, proximity, and last-known position. Optional group alert shouts to nearby allies.
- Melee foes approach appropriate range and try flanking rather than running directly through other enemies. Ranged foes seek firing lanes, maintain spacing, reposition when blocked and avoid friendly occlusion where appropriate.
- Casters choose spells based on cooldown, range and player status; healers/support units prioritize allies; brutes use telegraphed heavy attacks; fearful or injured enemies may retreat.
- Enemy dodge/block/parry depend on archetype. AI must respect actual weapon reach, cooldown and collision, not fake instant hits.
- Enemy persistence: dead enemies remain dead for the current dungeon instance. Aggro and ephemeral projectile state may reset when returning to a floor, but elite rewards must not duplicate.

### 10.2 Required enemy archetypes

Provide **24 ordinary archetype templates** (six per region) with independent stat/asset/behavior identities, plus elite modifiers and four authored bosses. Suggested catalog:

| Region | Six standard archetypes and defining mechanic |
|---|---|
| Barracks | Scavenger (fast melee); Bone Militia (shield); Tower Archer (ranged); Kennel Beast (rush); Armored Reaver (heavy attack); Whisper Wisp (arcane projectile) |
| Ossuary | Rotwalker (slow grab); Headless Guard (decapitation-resistant); Tomb Archer (ranged poison); Grave Hound (pack); Crypt Magus (curse); Bone Colossus (high poise) |
| Flooded Works | Drowned Thrall (water ambush); Salt Caster (lightning); Hook Brigand (pull); Mire Leech (poison); Rust Construct (armor); Sump Horror (multi-limbed grapple) |
| Unraveling | Riftling (short teleport); Hollow Knight (block/counter); Eye Swarm (flying projectile); Many-Hands (multiple severable attacks); Veil Priest (support/curse); Deep Sentinel (elite-like tank) |

- **Elite modifiers:** `Enraged` (speed/attack), `Warded` (shield), `Venomous` (poison attacks), `Stormbound` (lightning zones), `Vampiric` (life steal), `Unstable` (death explosion), `Summoner` (adds), `Thorned` (melee reflect with cap). Elites use one modifier early and up to two later, provided combination rules permit them.
- Enemy level defaults to dungeon floor plus bounded ±1 variation; scaling affects HP, damage, armor, XP and eligible drops, but does not erase archetype identity. Level comparison visible in nameplate/bestiary.
- Corpses have searchable/lootable state where appropriate. Rare drops display world beams or labels without forcing a pickup.

### 10.3 Boss encounters

**Four bosses, each with at least two recognizable phases and unique mechanics.** Boss gates prevent accidental exit during combat but never permanently trap the player after victory or death. The boss health bar, phase cues, arena telegraphs, drop, quest flags and shortcuts are data-driven.

| Floor | Boss concept | Required encounter behavior |
|---|---|---|
| 4 | **The Ashbound Captain** | Shielded armored humanoid; guard-break windows, charge attack, summons a small reinforcement wave at 50% HP |
| 8 | **The Ossuary Bellkeeper** | Undead bell-bearing giant; shockwaves, curse zones, destructible limbs; head removal changes attacks but does not instantly kill |
| 12 | **The Drowned Engineer** | Mechanized/powered enemy; activates water/lightning hazards, switches create vulnerability windows, changes arena traversal |
| 16 | **The Warden Below** | Multi-limbed supernatural adversary; anatomy/phase mechanics, environment transformation, final exposed-core phase |

- Bosses use deterministic phase triggers (HP threshold, elapsed combat event, destroyed weak points); no duplicate phase trigger after save/reload. Respawn behavior follows campaign death rules: an undefeated boss resets when the player leaves the encounter, but once defeated remains permanently defeated until New Descent.
- Boss reward: guaranteed rare-or-better item, gold, XP, one authored quest/shortcut unlock, and chance of region relic.
- Every boss has visible, audible telegraphs, at least one safe response to each major attack, no unavoidable one-hit attack in default mode at an appropriate level, and no invulnerable phase without an interactable resolution.

### 10.4 Combat encounter composition

Rooms declare combat roles (melee pressure, ranged harassment, tank, caster, support, ambush) rather than simply random lists. Encounter planner enforces:

- Multiple enemy types and readable threats; cap simultaneous overlapping hard crowd-control effects.
- Cover and sight lines for ranged opponents, maneuvering space for brute attacks, and meaningful escape routes unless the room is explicitly a trap encounter.
- Spawn reinforcements from believable entrances or visible effects; not in the camera frame at impossible positions.
- No progression objective blocked by an AI actor stuck in unreachable geometry; recovery/teleport-to-valid-nav or encounter completion fallback must exist.

---

## 11. Interactive environment, hazards and puzzles

### 11.1 World objects

Mandatory interactable object types: ordinary/locked/secret doors; door levers; keys; chests of several rarities; destructible crates/barrels; weapon racks; armor stands; bookshelf/lecterns; corpse containers; shrines; fountains; traps; pressure plates; floor switches; chains/pulleys; elevators and stairways; breakable walls; campfires/torches; lore documents; teleport anchors; merchant counters; quest objects and boss entrance triggers.

Each object has: stable ID, interact type, interaction radius, prompt, required condition/item, state, feedback assets, loot or event payload, persistence policy, and collision/navigation effect.

### 11.2 Environmental damage

- Spike plates: telegraph then physical burst; cooldown per activation.
- Dart traps: visible projectile, pierce/poison tags, trigger plate or tripwire.
- Fire vents/lava: periodic fire damage + burn buildup; creates dynamic light.
- Electrified water: applies lightning damage/shock to actors touching wet volume while active.
- Pitfall/void: falling damage based on height, lethal below safe depth; valid respawn/fall recovery for unsupported geometry.
- Curses: zones reduce resistance or apply fear until exited or dispelled.
- Rolling/pendulum hazards: moving collision with damage and physical push; environmental physics has a bounded max damage.
- Enemy and player interact with compatible hazards symmetrically unless immune. Hazard owner credit supports enemy XP/loot on player-caused trap kills.

### 11.3 Puzzles and secrets

- Simple mechanism chains (find lever to open gate, collect key, align two symbols, light a set of braziers, drain water). Every required puzzle has discoverable clues and a verifiable state machine; optional puzzle content can yield extra loot and lore.
- Hidden doors reveal by perception, environmental hint, interacting with suspicious stone, `Reveal` spell, or linked switch; no pixel-hunting required for main progression.
- Puzzle state persists across leaving/re-entering the floor. Repeated activation cannot issue repeated one-time loot/XP rewards.

---

## 12. Narrative, quests and lore

### 12.1 Narrative premise (original)

A ruined fortress above an impossible subterranean complex has become the center of disappearances and strange disturbances. Hollowmere survives by trading with desperate treasure-seekers. The player descends seeking an explanation for the region's collapse, discovers evidence of an engineered catastrophe, and ultimately confronts a surviving guardian who is perpetuating the disaster. **Tone:** bleak, mysterious and occasionally humane; no borrowed characters, town names, quest text or art from the source inspirations.

### 12.2 Quest types and progression

- **Main storyline:** one campaign quest per region + final confrontation, with subobjectives such as speak to NPC, reach depth, locate evidence, overcome locked mechanism, defeat boss, return for reward. Boss requirements follow the region sequence.
- **Side quests:** NPC requests (retrieve an object, find a missing person, kill named elite, cleanse altar, discover journal fragments, repair a mechanism), plus some randomly selected dungeon events with persistent completion flags.
- **Emergent events:** elite guarding treasure, abandoned camp, wandering survivor, cursed room, merchant corpse, trapped chest. Event contents must be compatible with graph and floor state.
- **Lore:** readable pages, inscriptions, environmental scenes, NPC conversations, boss records; journal stores unlocked entries.
- **Quest rewards:** authored item or weighted item grant, gold, XP, spellbook, shortcut access, NPC stock/dialogue updates. Exactly-once grant per quest completion.

### 12.3 Quest data contract

```yaml
id: q_region1_lost_standard
name: The Lost Standard
start_conditions: [visited_town, floor_reached_1]
objectives:
  - {id: speak, type: dialogue, npc: chronicler, dialogue_node: q_intro}
  - {id: find, type: pickup_quest_item, item_id: standard_fragment, floor_range: [2, 3]}
  - {id: return, type: dialogue, npc: chronicler, dialogue_node: q_turnin}
rewards:
  gold: 175
  experience: 140
  item_table: region1_quest_rare
on_complete_flags: [q_lost_standard_done]
repeatable: false
```

- Journal displays quest title, objectives, completed checkboxes, narrative updates and rewards. Quest item is reserved in generation before the floor is built, or the required objective node is injected so the quest can always be completed.
- Story quests have fail-safe restoration if item is lost due to a bug/save migration; main progression must be recoverable.
- Quest dialogue branches are localizable and can be skipped without breaking objective state transitions.

---
## 13. User interface and player feedback

### 13.1 In-game HUD

Required HUD elements:

1. **Left circular orb:** current/maximum health with numeric tooltip and critically-low animation.
2. **Right circular orb:** current/maximum mana, with optional numeric text.
3. **Stamina bar:** displayed near center-bottom, fades when full and out of combat.
4. **Action bar:** six numbered slots `1–6`, icons, stack counts, charges/cooldown shade; separate `Q` and `R` ability slots.
5. **Experience bar:** current progress to next level, level-up notification and **unspent skill/attribute point + button**.
6. **Top-left minimap:** discovered floor outline, player arrow, door/exit/waypoint icons; floor name/number as overlay on entry.
7. **Context prompt:** reticle target name, interact key, object state, required key or stat, accessible affordance.
8. **Loot/combat log:** brief item pickup, XP, gold, status and event messages, optionally hidden in settings.
9. **Target feedback:** enemy name, level, health/elite/boss bar, damage/status indicators, optional numbers.
10. **Quest objective indicator:** optional short current objective, map marker only after discovery/where appropriate.
11. **Status icon row:** active buffs/debuffs with duration and description.

HUD layout must accommodate 16:9 and ultrawide displays without covering essential combat visibility. UI scale and opacity settings apply to all elements. Quickbars always accurately reflect current binding and cooldown/resource state.

### 13.2 Character/inventory screen

- Tabbed or simultaneous panels for character model, equipment slots, 10×6 backpack, attributes with plus buttons, combat/defense summary, gold, experience and talent notifications.
- Class/character level at top, current/next XP progress, unspent points clearly surfaced. Equipped model rotates in 3D preview, with active weapons and armor visible.
- Hovering item opens readable tooltip (rarity, item level, damage/armor, affixes, requirements, item dimensions, durability, sell value, unique effect); compare to equipped equivalent and mark differences.
- Drag/drop works for backpack, equipment, belt, chest, store/stash and ground, with clear placement preview. Inventory is not navigable only by mouse; keyboard/controller UI focus can access all actions.
- Distinguish currently equipped vs unusable gear. Grey out unlearned skills and unmet level/stat requirements. Unspent points use explicit confirmation and update immediately.

### 13.3 Menus and screens

- Main menu: Continue, New Character, Load Character, Options, Credits, Exit.
- In-game menu: Resume, Save & Exit, Options, Help/Controls, Return to Main Menu. ESC pauses simulation time while the menu is open.
- Skills panel: class tree, prerequisites, rank, next-rank change, total points, assign ability slot, spellbook learned spells and ranks.
- Journal panel: active/completed quests, lore notes, discovered bestiary entries, optional objective tracking.
- World map: town and current dungeon floor; floor history/accessibility list; explored fog, waypoints and legend.
- Death screen, victory/end sequence, new descent confirmation, respec transaction, vendor/shop, crafting/repair/identification service.

### 13.4 Feedback and legibility

- Interactions return immediate multimodal feedback (sound, reticle state, screen text, animations). Failed actions show a precise reason: insufficient mana, stamina, required attribute, item space, money, locked door, out of range, unusable target or on cooldown.
- Rare drops are distinguished by effects and color, but also by icon shape/name for color-blind accessibility.
- Ground-item label display supports hold-to-show and hover/proximity variants, adjustable density and a pickup prompt. Item labels avoid severe overlap and do not reveal loot through undiscovered rooms.
- Error messages are informative and non-modal for ordinary gameplay; destructive confirmations (delete character, reset dungeon, discard relic) are modal.

---

## 14. Death, difficulty, saving and continuation

### 14.1 Difficulty profiles

| Setting | Enemy HP | Enemy damage | Loot quality | Death handling |
|---|---:|---:|---|---|
| Wanderer | 0.80× | 0.75× | 1.0× | Standard respawn; lower gold loss |
| Adventurer (default) | 1.00× | 1.00× | 1.0× | Standard respawn |
| Dread | 1.25× | 1.35× | 1.1× | Standard respawn; greater gold loss |
| Ironbound (hardcore toggle) | Uses selected damage profile | Uses selected HP profile | Uses selected loot profile | Permadeath on death |

Difficulty must not arbitrarily invalidate item-drop constraints or required quest rewards. It may change enemy stats, encounter budget, resource drops and death penalty, but does not change floor graph solvability. Difficulty changes during play are allowed only from town and are recorded; hardcore cannot be disabled after character creation.

### 14.2 Death and corpse recovery

**Standard mode:** On death, display death screen and return player to town at full health and mana; equipment and backpack retained. Drop **10% of carried gold** into a recoverable personal corpse/cache at safe reachable location near death (Wanderer 5%, Dread 20%), preserving exactly one recoverable record. If a previous cache exists when dying again, its gold transfers to new cache or is explicitly forfeited with a warning—never silently duplicates. Character XP and level do not decrease by default. Defeated bosses stay defeated; regular enemies slain before death stay dead for that campaign instance. Temporary buffs end on death.

**Hardcore:** Character is marked permanently dead; game prevents reentry as that character. Stash/campaign options follow explicit difficulty mode rules; no accidental deletion of other saved characters.

### 14.3 Saving and loading

- Character creation creates a persistent save slot. Autosave on entering town, changing floors, quest completion, boss kill, service transactions, level-up point allocation, major item pickup and graceful exit; optional manual save in safe non-combat contexts.
- Save includes schema version, content version, character IDs/class/appearance, base stats and unspent points, XP, gear and every item **instance ID + rolls + durability + identification**, inventory cell coordinates, hotbar bindings, gold, stash, spell/talent ranks, quest flags, dialog history, difficulty, current region/floor/position, discovered fog, dungeon seed, all generated room placements, world interactive states, committed loot entitlements, floor actor states, unlocked waypoints and persistent portals.
- **Atomic write:** create complete new snapshot, validate checksum/structure and commit; retain a previous good snapshot. Corrupted/mismatched saves show recoverable error and do not silently replace the file with a fresh character.
- Loading validates references; unknown removed item IDs are migrated to safe placeholder items or compensation entries rather than deleting saves. Changing item definition does not reset a unique instance's already rolled affixes unless migration explicitly says so.
- Save/load never refreshes already opened containers, resets merchant stock without milestone, grants an already claimed quest reward, restores consumed potions, resurrects permanently dead bosses, or multiplies an item by re-joining.
- Pause freezes combat simulation timers. Saving mid-buff stores remaining durations; real-world elapsed time does not secretly drain health or potion effects while game is closed.

### 14.4 Checkpoints and travel

- Activated waypoints/shortcuts persist and permit entry at selected discovered floors from town; do not reveal undiscovered rooms or bypass mandatory boss prerequisites.
- A **Return Sigil** creates temporary paired portals between floor and town, only where collision/placement and combat restrictions allow. A portal is tagged with campaign, source floor, world position, owner, and active state.
- Town is the only permanent services hub. No mobile market, base-building system, open world, fast-travel network to unrelated towns, or separate randomized dungeon selection is part of this specification.

---

## 15. Audio, art direction, lighting and atmosphere

### 15.1 Visual direction

Original stylized, textured dark fantasy: strongly readable weapons, creatures and architecture; varied torchlight and magical colors; deep shadows without making basic navigation impossible. Maintain four visually recognizable dungeon regions plus town. Lighting supports gloom and suspense, with controls for brightness, gamma and high-contrast markers.

- Region 1: torches, dusty stone and broken timber; warm amber against muted blue.
- Region 2: candles, bone, cold green shadows and burial chambers.
- Region 3: wet reflections, machinery, storm-blue lightning and industrial corrosion.
- Region 4: unnatural apertures, shifting geometry/particles, odd silhouettes and unstable light.
- Deeper floors can introduce stronger ambient effects, geometry illusions, distant monster noises, vignette and color shifts **without** disrupting collision or causing unavoidable photic effects.
- Equipment models communicate category and rarity. Enchanted weapons visibly emit a relevant aura/light. Unique items may change first-person idle and swing presentation in addition to gameplay.

### 15.2 Sound and music

- Distinct footsteps by material; weapon whooshes/impacts by type and target material; block/parry/stagger sounds; creature cues by archetype; ambient town dialogue and work sounds; positional enemy threats; room-scale reverb; distant bells/doors/echoes; trap telegraphs; item pickup rarity chimes; UI interaction sounds.
- Dynamic ambient score depends on location, encounter state, boss phase and proximity to danger; transitions crossfade and never restart aggressively on every room threshold.
- Volume categories: master, music, ambience, effects, dialogue. Subtitles for dialogue and significant voice barks. Output channel/device defaults, mute and mono compatibility.

### 15.3 Visual-effects behavior

- Weapon trails only during valid active strike frames; blood/impact particles reflect target material; block spark and damage type are perceptible; status effects and telegraphs readable without excessive opacity.
- Corpses and severed limb props obey a debris budget with priority for active combat interactions. Reduced gore substitutes simpler impacts/neutral fragments, while gameplay effects remain intact.
- UI and effects respect motion reduction, shake reduction, reduced flashes, color-blind palettes and optional damage-number suppression.

---

## 16. Settings, accessibility and quality-of-life

**Video:** display mode, resolution, refresh rate, aspect ratio, V-sync, frame cap, render scale, graphics presets and individual shadows/lights/postprocess/particles; FOV; gamma/brightness; UI scale; subtitle scale; color-blind options.

**Input:** mouse sensitivity/invert axis, key remapping for every action, hold/toggle sprint/crouch/aim, controller mapping, aim sensitivity and dead zone; interaction tooltips show bound keys rather than hard-coded letters.

**Accessibility:** subtitles with speaker names, adjustable text size and contrast, reduce camera shake/headbob/motion blur/flashes, non-gore mode, input rebinding, toggle sprint, optional enemy outline and loot-label visibility, optional hold-interact instead of repeated taps, alternate icon encoding for rarity, pause.

**Gameplay:** difficulty, item-label visibility, auto-pickup gold and/or potions, floating damage numbers on/off, enemy HP bars on/off, objective marker on/off, minimap rotate/fixed, potion key auto-select, combat log verbosity, item comparison toggles.

**Quality-of-life:** sort backpack/stash, item comparison, sell-junk marking, buyback window, shift-click transfers, map legend, journal tracking, persistent key hints, visible status duration, tooltips describing formulas and reason for disabled commands, safe exit/save feedback. None should bypass the intended loot/inventory constraints silently.

---

## 17. Content catalog requirements

To give the rules concrete assets and discoverable gameplay, define the following **minimum authored content catalog**, with data-generated variants on top:

| Content category | Required catalog |
|---|---|
| Playable classes | 3 (Vanguard, Stalker, Arcanist) |
| Class talents | 24 total (8/class, 5 ranks each) |
| Shared spells | 10 (5 possible levels each) |
| Dungeon regions | 4 themes, each with unique modular chunks and audio/lighting set |
| Dungeon floors | 16 procedural numbered floors per descent |
| Bosses | 4 authored multi-phase encounters |
| Standard enemies | 24 archetype templates; elite modifier combinations create variants |
| Town functional NPCs | At least 7 service/quest roles; additional ambient townspeople |
| Base weapon families | 9 (sword, axe, mace, dagger, spear, great weapon, bow, staff, wand) |
| Base armor families | Head, chest, gloves, boots, shields; cloth/leather/mail/plate variants where applicable |
| Accessories | Amulet + two-ring categories with visual and numerical variation |
| Rarity categories | 4, plus unidentified state |
| Magical affix families | At least 20 applicable effect families with constrained roll values |
| Relic item templates | At least 12 authored exceptional items with unique effects |
| Consumables | At least 12 incl. potion grades, antidote, cleanse, resistance, scrolls |
| Interactable object archetypes | At least 16 (doors, chests, traps, shrines, levers, etc.) |
| Trap/hazard patterns | At least 7 |
| Floor event patterns | At least 10 distinct event configurations |
| Main quest stages | 4 region arcs + finale and return-to-town resolution |
| Side quest templates | At least 12, with persistent flags and authored reward pools |
| Lore entries | At least 24 discoverable entries spread across town/floors |
| Town vendor/utility windows | Buy/sell, identify, repair, recharge, heal, stash, respec |
| Save modes | Normal + hardcore; four difficulty profile combinations as defined |
| Play modes | Single-player only |

All catalog entries must reference valid in-game content IDs/assets. Procedural repetition can produce additional item names, enemies, rooms and combinations, but a placeholder entry may not point to missing core behavior.

### 17.1 Specific relic behavior examples

These are authored gameplay templates, not just colored variants:

1. **Coalbrand** (sword): adds fire damage, inflicts burn and emits light.
2. **Breakwater** (shield): successful perfect block sends a short-range shockwave on internal cooldown.
3. **Thunderheels** (boots): kick deals lightning damage and may chain to a wet nearby enemy.
4. **Gravedigger's Grasp** (gloves): melee takedowns restore a capped amount of stamina.
5. **The Quiet Eye** (amulet): reveals secret-door hints but reduces maximum mana.
6. **Hollow Fang** (dagger): bonus backstab damage and stronger bleed; lowered frontal damage.
7. **Warden's Toll** (mace): extra poise damage but slower recovery.
8. **Ashglass Staff** (staff): fire spells gain splash radius at increased mana cost.
9. **Frostvein Ring** (ring): critical hits add chill buildup.
10. **Lantern Mail** (chest): increased armor and light radius; reduced dodge distance.
11. **Serpent Knot** (ring): poison damage converts a portion to self-healing with a cap.
12. **Wayfarer Bow** (bow): arrows pierce one enemy, with reduced per-target damage.

All are level-gated by item base, have correctly reflected tooltips and visuals, and obey status/critical/ability stacking rules.

---

## 18. Data model and interfaces between systems

### 18.1 Core entity/component concepts

Treat content **definitions** as immutable catalog entries and runtime **instances** as uniquely identified mutable objects. Suggested domain objects (names are illustrative, behavior is mandatory):

- `CharacterDefinition / CharacterState`: class, base attributes, level, XP, point allocations, gear refs, bag placements, known spells, talents, resources, quest record, world position.
- `ItemDefinition / ItemInstance`: base metadata, footprint, slot, permitted class/requirements, damage/armor, affix pools, rarity, roll values, durability, charges, identified state, unique effect, quantity, owner and instance ID.
- `SkillDefinition / SkillState`: resource cost, cooldown, windup, hit source, range, statuses, ranks, requirements, assigned slot, cooldown remaining.
- `ActorDefinition / ActorState`: archetype, faction, stats, anatomy, AI state, position, aggro target, statuses, dead/drop flags, stable ID.
- `RoomChunkDefinition / RoomInstance`: geometry asset ID, connectors, anchors, tags, world transform, room role, stable ID, room mutation flags.
- `FloorGraph / FloorInstance`: seed, logical nodes/edges, room placement list, spawned actor IDs, object states, fog, committed rewards, shortcut state.
- `QuestDefinition / QuestState`: prerequisites, objective graph, progress values, completion and reward-claimed flags.
- `VendorDefinition / VendorState`: stock, restock milestone, transaction list/buyback and services.
- `CampaignState`: campaign ID, world seed, difficulty, global story flags, floor states, waypoints, death caches, active portals.
- `SaveEnvelope`: schema/content versions, timestamps, checksum, character/campaign refs and serialized state.

### 18.2 Example item definition and rolled instance

```json
{
  "definition": {
    "id": "sword_iron_sabre",
    "display_name": "Iron Sabre",
    "category": "weapon",
    "weapon_family": "sword",
    "slot": "main_hand",
    "hands_required": 1,
    "footprint": [1, 3],
    "base_damage": {"min": 5, "max": 9, "type": "slash"},
    "attack_timing": {"light_windup_s": 0.22, "light_recovery_s": 0.34,
                      "heavy_charge_min_s": 0.35},
    "reach_m": 2.0,
    "stamina_cost_light": 9,
    "required_level": 1,
    "required_attributes": {"strength": 12},
    "affix_tags": ["melee", "one_handed", "metal"],
    "base_value": 65,
    "first_person_asset": "fp_sword_sabre",
    "third_person_asset": "tp_sword_sabre"
  },
  "instance": {
    "instance_id": "itm_8f9b2",
    "base_id": "sword_iron_sabre",
    "item_level": 4,
    "rarity": "rare",
    "affixes": [
      {"id": "added_fire_damage", "value": 4},
      {"id": "bonus_strength", "value": 2}
    ],
    "identified": false,
    "durability": {"current": 37, "maximum": 50},
    "quantity": 1,
    "ownership": {"character_id": "ch_001", "container": "backpack", "grid_xy": [2, 1]}
  }
}
```

### 18.3 Example enemy and attack definition

```yaml
id: bone_militia
faction: hostile_undead
level_band: [1, 7]
health_at_level_1: 48
armor_at_level_1: 14
poise: 40
move_speed_m_s: 3.2
vision_range_m: 14
hearing_range_m: 18
tags: [undead, humanoid, shield_user, headless_capable]
resistances: {fire: 0, frost: 15, poison: 75, magic: 0}
immunities: [poison_status]
attack_patterns:
  - id: slash
    range_m: 2.1
    windup_s: 0.45
    active_s: 0.16
    recovery_s: 0.7
    physical_damage: [7, 11]
    poise_damage: 8
  - id: shield_bash
    range_m: 1.5
    windup_s: 0.7
    physical_damage: [4, 7]
    poise_damage: 18
anatomy:
  head: {severable: true, fatal_on_sever: false, disable_abilities: [head_bite]}
  left_arm: {severable: true, disable_abilities: [shield_bash]}
  right_arm: {severable: true, disable_abilities: [slash]}
loot_table: region1_undead
experience: 24
```

### 18.4 World event contract

Systems communicate with typed events carrying source and stable IDs; handlers must be idempotent for award/state events. Required events include:

`CharacterCreated`, `FloorGenerated`, `FloorEntered`, `RoomDiscovered`, `InteractionSucceeded`, `DoorStateChanged`, `AttackCommitted`, `HitResolved`, `StatusApplied`, `LimbSevered`, `ActorKilled`, `LootRolled`, `ItemPickedUp`, `ItemEquipped`, `ItemConsumed`, `GoldChanged`, `QuestObjectiveAdvanced`, `QuestCompleted`, `RewardClaimed`, `CharacterLeveled`, `SkillLearned`, `BossDefeated`, `PortalCreated`, `CharacterDied`, `VendorTransactionCommitted`, `SaveCommitted`.

- State changes should occur in domain transactions with unique event IDs; observers for UI/audio/quests may respond without repeating underlying grants.
- An enemy death should emit at most one credited kill and one committed loot allocation per eligible recipient; duplicate `ActorKilled` notifications do not duplicate drops.
- World objects and quest flags reference stable IDs rather than fragile scene-instance ordering.

### 18.5 Ownership and authority

- Definitions (item templates, spell definitions, loot tables, enemy archetypes, rooms) are versioned content data.
- Runtime character/campaign state belongs to an authoritative simulation. UI sends commands and renders state; it cannot directly mint items, change gold or flag quests complete.
- Generated floor remains fully reconstructible from stored placements plus mutable state; persistent rewards maintain separate stable IDs and claim records.
- Floating damage text, HUD states, audio and cosmetic effects are projections of accepted state/events, not sources of truth.

### 18.6 Required sample content configuration

```yaml
game_rules:
  player:
    max_level: 30
    attribute_points_per_level: 5
    class_talent_points_per_level: 1
    backpack_grid: [10, 6]
    quickbar_slots: 6
    movement_walk_m_s: 4.5
    movement_sprint_m_s: 6.3
    stamina_sprint_per_s: 12
    potion_shared_cooldown_s: 1.25
  dungeon:
    floors: 16
    regions: 4
    min_main_path_nodes: 7
    max_main_path_nodes: 15
    branch_range: [2, 5]
    secret_room_range: [0, 2]
    boss_floors: [4, 8, 12, 16]
  loot:
    rarity_weight_percent: {common: 65, enchanted: 25, rare: 9, relic: 1}
    stack_max_default: 20
  difficulty:
    default: adventurer
    normal_gold_loss_fraction: 0.10
```

Configuration controls balance and content references centrally. Behavior must read the corresponding resolved rule rather than hardcoding numbers in UI text or enemy scripts.

---
## 19. System verification and acceptance criteria

All conditions below describe **observable required behavior**. They are expressed as user journeys and mechanical invariants rather than engine-specific implementation steps.

### 19.1 Character creation and the full game loop

- [ ] A new game starts with a selectable class, valid starting gear, configured attributes, health/mana/stamina, and an available save slot.
- [ ] Player can walk around town, talk to services, purchase potions, enter Floor 1, fight, take damage, heal, gain XP/gold, loot a real item, equip it, interact with rooms and stairs, and return to town.
- [ ] Returning to town allows selling, buying, repair, identification, stash transfer, spellbook use and respec without losing campaign progress.
- [ ] Player can complete a floor, move down, use a shortcut or return portal, defeat each region boss, progress to the next region, finish the main story and start another descent with retained character progression.
- [ ] All three classes can progress through the same authored world; no boss or mandatory door requires a class-exclusive skill, unless a universal alternative exists.
- [ ] Each dungeon floor has at least one viable route to its objective, with no impossible key/lock cycle or impassable geometry.

### 19.2 Attributes and combat math

- [ ] Spend STR: melee damage and applicable requirements update correctly. Spend DEX: speed/crit/ranged damage update; INT: mana/magic; VIT: HP/stamina.
- [ ] A 1-point attribute change affects only the intended dependencies, and the character sheet explains the difference.
- [ ] A weapon's damage min/max rolls stay within defined range before explicit modifiers. Defense/resistance calculations produce the documented post-mitigation result, including negative resistances and caps.
- [ ] A mixed physical/fire attack applies armor only to the physical component and fire resistance only to the fire component.
- [ ] Critical chance and life/mana steal obey caps; DoT cannot recursively trigger life steal or status on-hit effects unless explicitly tagged.
- [ ] Low stamina disables resource-gated attacks, dodges and sprint; low mana disables applicable spells; spent resource is deducted exactly once.
- [ ] Shield blocking consumes stamina, reduces frontal damage but not attacks from the rear; perfect parry has a limited valid timing window; shield-break transitions to stagger.
- [ ] Kicks can shove an enemy, scatter a crate, trigger pit/environmental kills and interact with severed body parts; physical projectiles cannot register repeated infinite collision damage.
- [ ] Head/arm/leg/wing severing produces the correct behavior changes on susceptible enemies; headless-capable undead continue, head-sensitive living foes die, non-severable enemies ignore inappropriate limb logic.
- [ ] Spells honor range, line-of-sight, mana, cast time, cooldown, targets, ranks and resistance. A spell canceled before its commitment frame cannot damage or spend mana.
- [ ] Each class talent can be unlocked, leveled, equipped, activated, put on cooldown and saved; passive modifiers persist after reload.

### 19.3 Items, loot and economy

- [ ] Every ground item has a unique instance ID and only one pickup destination; no pickup loses an item when backpack is full.
- [ ] 1×3 sword fits a 10×6 backpack only when three appropriate contiguous cells are available; grid collision/rotation/stack split/merge and sorting obey exact occupancy.
- [ ] Two-handed equipment evicts/conflicts with off-hand gear transactionally; incompatible requirements prevent equip with explicit reason and no item loss.
- [ ] Unidentified magical items have concealed rolled affixes; identification reveals the **committed** rolls without replacing them.
- [ ] A rarity roll selects only eligible affixes/item bases; exclusions and impossible-to-wear gear cases are enforced.
- [ ] Damage and item tooltips display actual values from the combat model; gear changes update visuals, durability behavior and all derived stats.
- [ ] Durability drops through defined events; zero durability disables relevant effects, repair restores using the exact quoted gold, and insufficient funds cancel the transaction.
- [ ] Potions consume one item per accepted use, restore the expected amount no higher than max, respect cooldown and update belt counts immediately.
- [ ] A sale removes exactly one item or declared stack quantity and credits exact gold; buyback cannot clone sold items; purchase cannot make gold negative.
- [ ] A chest produces its reward once and remains opened through travel/save/load; no repeatedly generated items from an item already claimed.
- [ ] Quest items cannot be accidentally sold, dropped irretrievably or deleted by auto-sort.
- [ ] Gold received, spent, dropped on death and recovered from corpse adds up; vendor stock cannot be rerolled through opening/closing a menu.

### 19.4 Procedural geometry and exploration

- [ ] For a reproducible sample set of at least **1,000 different seeds per region** (and all 16 floor indices), graph construction always yields start, required quest/key rooms, boss if required and valid exit, with no unconnected mandatory room.
- [ ] No chunk intersection invalidates navigation, blocks a doorway, seals an exit, traps the player or exposes a drop with no recovery rule where progress is required.
- [ ] Compatible connectors meet precisely; unused connectors are capped; stairs and vertical transitions are navigable for player and relevant enemy types.
- [ ] Key/lock dependency graph has no cycle. Optional secret rooms can contain loot but never the only copy of a mandatory quest key unless that secret has a guaranteed accessible revelation mechanism.
- [ ] Minimap corresponds to actual world connectivity and remembers explored fog across travel/load; secret rooms remain undisclosed until found.
- [ ] Every required encounter spawns in accessible geometry, with navigation to the player or recovery rules. Encounter can finish even if an enemy falls into an unreachable pit.
- [ ] Same world seed and version produces identical **initial** layouts/loot; stepping, particle animation or AI decisions do not reroll committed outcomes.
- [ ] Returning to town or another floor and re-entering restores the same rooms, gates, chests, quest objects and boss flags.

### 19.5 Campaign, quests and saving

- [ ] Save and reload at each major lifecycle event preserves character and world, including the item instance and its cell coordinates; no rollback or duplication of committed rewards.
- [ ] Repeated `ActorKilled`, `QuestCompleted`, `BossDefeated` and `VendorTransactionCommitted` messages do not grant repeated XP/gold/loot or break state.
- [ ] Optional quest and main quest can be accepted, advanced, turned in, tracked and marked completed exactly once, even after session restart.
- [ ] Boss defeat sets correct quest flag, opens relevant exit/shortcut, generates exactly one designated reward and remains defeated across reload/re-entry.
- [ ] All standard death modes restore appropriate state, retain equipment, create at most one valid recoverable gold cache, and cannot create negative gold or permanent trapped respawn.
- [ ] Hardcore dead character cannot re-enter world as alive, and unrelated character slots remain intact.
- [ ] A corrupted save is detected; game offers recovery from prior valid snapshot rather than silently creating an empty campaign.

### 19.6 UI, input, audio and accessibility

- [ ] Every button and binding is functional, rebindable and labeled consistently in menus, HUD and prompts; first-person attack and guard correspond to displayed equipment.
- [ ] Items show requirement warning, rarity, comparisons, exact costs and identified/unknown state accurately.
- [ ] Fullscreen, resolution, UI scale, FOV, gamma, subtitle scale, audio volume, motion-reduction and non-gore settings persist across sessions.
- [ ] Lowering gore hides/severed-body visuals but retains combat-driven loss of enemy limbs/abilities and physics interactions through neutral substitute objects/effects.
- [ ] Audio cues for enemy attacks, traps and rare loot are audible and have visual equivalents as appropriate.
- [ ] Closing inventory, vendor, quest or other overlays returns correct input focus and never leaves the player unable to move/interact.

---

## 20. Cross-system edge cases and resolution rules

| Situation | Required behavior |
|---|---|
| Player fills backpack and tries to pick up quest reward | Reward granted to reserved quest pouch, protected reward cache, or safe town claim; never lost |
| Player tries to equip an item while inventory is full | Swap completes only if removed item fits or can be legitimately placed elsewhere; otherwise cancel unchanged |
| STR-granting item is removed and another item becomes unusable | Ineligible item's effects disabled and UI flagged; it remains owned/equipped, not deleted |
| Item gives extra max HP and is unequipped while player is critically injured | Current HP clamps to new max, never negative and never heals by invalid arithmetic |
| Chest and boss reward trigger simultaneous autosave | Reward transaction commits exactly once before snapshot; saved state has matching item and claimed flag |
| Enemy dies from poison after caster changes floor | Damage source and reward committed appropriately; no phantom enemy attack or duplicate loot |
| Arrow hits an enemy's severed limb in flight | Resolve hit against current valid collision state; no damage twice from stale limb and torso hitbox |
| Boss dies during multi-phase transition | Victory takes precedence; no phase reactivation, invisible invulnerability or double drop |
| Player saves while standing in a closing door, moving lift or trap volume | Restore to validated nearest safe navigation point with consistent object state |
| Return portal created on unstable geometry | Placement fails with a message and no mana/scroll consumed before valid placement commitment |
| Player travels from deep floor to town and quits | Source floor, map, chest state and return location remain preserved |
| Game closes or crashes during a vendor transaction | Commit entirely or roll back entirely; never pay without item or get item without charge |
| Player dies mid boss fight | Encounter resets once, with no loot until boss defeated; progression gates remain intact |
| Quest objective spawns in a secret-only inaccessible branch | Generator rejects/rearranges or adds mandatory discoverable path, preserving completion |
| Two quests request same unique item | Each objective has its own stable completion flag and explicit ownership/consumption policy |
| Different item definitions after software update | Save migration retains owned unique instance IDs and compensates safely for missing catalog IDs |
| Unidentified item grants a stat that enables another item | Effective stats may qualify it, but unidentified tooltip cannot leak hidden affix name; derived total is accurate |
| Inventory auto-sort moves hotbar-bound item | Bind by stable item type/instance ID rather than cell coordinate; hotbar continues functioning |
| Physics kicks propel quest object out of the world | Object is clamped/respawned to persistent recovery anchor or nonphysical when quest-critical |
| Player respecs class tree while a passive modifies resource max | Recalculate derived stats and clamp current resources; cancel abilities no longer learned |
| Status duration expires while game is paused | World simulation time frozen; no duration consumed until gameplay resumes |

---

## 21. Typical end-to-end player journeys

These are precise reference scenarios that together exercise the main game rules.

### Journey A — Fighter's first descent

1. Create Vanguard. Spawn in Hollowmere with sword, shield, armor, two health potions and starter quest.
2. Speak to the chronicler; accept objective, speak to smith, inspect shop, enter dungeon gate.
3. Floor 1 generates from seed and displays a floor title and partially hidden minimap. Player investigates a branching hallway and opens a chest.
4. Engage a scavenger; light attack, shield block and kick deal distinct results. Enemy death awards XP and can roll loot/gold.
5. Pick up a club and an unidentified enchanted boot item. Inspect requirements; stronger boots cannot be equipped until enough STR is allocated.
6. Use potion from quickbar; the stack updates and potion cooldown begins. Fight until level-up grants five attributes and one talent point.
7. Allocate STR and Bulwark Rush, bind skill to Q. Skill performs short charge and deals radiant damage scaling with armor.
8. Descend further, collect more loot, activate shortcut, return to town by Return Sigil/scroll.
9. In town sell unwanted club, identify magical boots, repair shield, purchase potions, stash excess gear and return to identical floor layout.

### Journey B — Systemic combat interaction

1. A humanoid enemy approaches with a sword and shield; player blocks telegraphed strike.
2. Player swings a slashing weapon at exposed arm; damage exceeds local injury threshold and arm is severed, disabling corresponding enemy attack.
3. The enemy remains alive with alternate AI moves; player knocks the enemy back toward a spike trap using kick.
4. Trap kills the enemy; combat credit awards XP and eligible loot to the player responsible for the push.
5. Another enemy is decapitated. A severed head remains a physics prop, can be kicked at a third enemy and registers a single bounded impact.
6. If the target is a headless-capable undead, decapitation changes its behavior without killing it; disabling all relevant limbs or reducing its core HP finishes the encounter.

### Journey C — A full procedural story floor

1. Floor generation picks a logical sequence: safe entry → combat hall → fork → lever room → locked gate → elite room → boss antechamber → boss.
2. Side branch holds a lore book and shrine; cross-link loops back into main route; hidden chamber provides a rare chest.
3. Key/lever required for gate is placed **before** the gate and remains obtainable; minimap reveals only traversed spaces.
4. Player opens gate; gate state persists. Room enemy groups activate when player enters their authored trigger volumes.
5. Player defeats boss and receives unique world-state unlock and guaranteed rare drop. The next staircase becomes usable; quest updated.
6. Player returns home, saves and reloads. Boss does not return; opened chests remain opened; other floors retain generated layouts.

### Journey D — Death and recovery

1. Player dies in the Ossuary after gathering gold and a rare sword.
2. Death transaction records loss of 10% of carried gold in a recoverable cache and respawns player in town; rare sword remains in inventory.
3. Player re-enters through waypoint, fights surviving enemies, retrieves cache, and returns to town.
4. Save/reload before and after recovery produces no duplicated gold cache, item or enemy reward.

---

## 22. Completeness checklist by subsystem

This table is a **feature registry**: each row refers to the normative specification above. All rows are in scope.

| Area | Included feature set |
|---|---|
| Overall game | Town/dungeon loop, class selection, story progress, 16 floors, four regions, finale and replay/new descent |
| World movement | First-person controller, camera, slope/stair traversal, sprint, jump/mantle, dodge, crouch, contextual interaction |
| Melee/ranged | Weapon families, light/heavy attacks, combos, reach, animation-hit timing, bows/ammo, shield guard/parry, weapon durability |
| Physical combat | Kick, shove, props/traps, environmental kills, targeted anatomy, dismemberment, severed limb physics, headless enemy variants |
| Magic | Learned general spells, classes' magical talents, books/ranks, scrolls, wand/staff charges, spell effects/LOS/cooldowns |
| RPG stats | Four attributes, level/XP, spent/unspent points, health/mana/stamina, offense/defense, elemental resistances, status effects |
| Classes | Three classes, distinct start stats/gear/bonuses, 24 talents with prerequisites/ranks, Q/R and quickbar skill assignment |
| Equipment | Main/off-hand, head/chest/gloves/boots, rings/amulet, requirements, stats, previews, comparisons, visual attachments |
| Inventory | 10×6 grid, item dimensions, drag/drop, rotate, sorting, stack splitting, stack limits, six-slot belt, stash |
| Loot | Item base catalogs, rarity, affixes, unidentified items, relic effects, monsters/chests/boss drops, seeded committed rolls |
| Economy | Gold, merchants, buy/sell/buyback, repair, identify, recharge, healing, respec, milestone vendor restock |
| Procedural floors | Graph of critical path/branches/loops/locks, authored room chunks, compatible sockets, verticality, secret rooms, seeded enemy/loot placement, validation |
| Exploration | Fog minimap, full map, discovered doors/exits, lore entries, shortcuts, portals, quest markers |
| Enemies | 24 archetypes, perception/aggro/pathfinding, AI attacks and telegraphs, elite modifiers, statuses, death/loot behavior |
| Bosses | Four multi-phase encounters, arena hazards, weak points/limbs, guaranteed drops, story/shortcut flags |
| Objects | Chests, gates, keys, levers, shrines/fountains, breakables, barrels, traps, puzzles, props and quest items |
| Narrative | Main quest, NPC service dialogue, side quests, procedural events, lore, journal, objective tracking, endings |
| Presentation | HUD, orbs, bars, inventory/character/skills/shop screens, tooltips, damage/loot feedback, dark fantasy audio/lighting |
| Persistence | Atomic saves, item IDs, dungeon layout snapshots, quest flags, fog, transaction protection, death/recovery, New Descent |
| Settings | Audio/video/input, FOV, UI scale, remapping, color-blind/motion reduction, non-gore, subtitle support, play options |
| Validation | Deterministic seed tests, gameplay/math tests, save/load transactions and no-softlock guarantees |

---

## 23. Reference mapping and documentation notes

**Research and design inputs:**

- Gameplay trailer: [Heathen — Official Gameplay Overview Trailer](https://www.youtube.com/watch?v=gULKsVIPNlk), including the user's screenshots of town, HUD, dungeon entrance, combat, and character/inventory sheet.
- Trailer transcript (republished by GameStar): [Dailymotion transcript](https://www.dailymotion.com/video/xbobchi). Details independently described in the trailer include one town/one dungeon, upgrading attributes, class abilities, heavy attacks, melee head/limb severing, kicking severed heads, item equipment requirements, and returning to town to sell, identify and restock.
- Public description: [Heathen Steam page](https://store.steampowered.com/app/4702700/). Establishes class choice, spells, procedural dungeon, loot, single-player and online co-op genre structure.
- Developer interview: [80 Level, May 18 2026](https://80.lv/articles/how-heathen-reimagines-diablo-s-classic-dungeon-crawling-formula-in-first-person). Describes handmade tile chunks, node-graph pacing, impactful magical gear, and the design distinction between action combat and classic RPG backend.
- Classic mechanical reference: [Diablo I manual transcription](https://diablo2.diablowiki.net/Diablo_I_Manual). Informs the one-hub dungeon economy, attributes, equipment requirements, durability, identification, inventory, items, spells/books/scrolls, dungeon exploration and quests.

**Directly visible in provided screenshots:** First-person sword and shield, lower HUD with two resource orbs and stamina/progress bar, six number slots and class ability prompt, small fog-map in upper-left, loot/XP feedback, a dark dungeon labeled by level, outdoor town with NPCs and multi-building architecture, character equipment preview, a grid backpack, numerical character attributes (Strength, Dexterity, Intellect, Vitality), combat/defense stat panels, level XP bar and gold counter.

**Specification decisions/inferences:** Specific formulas, all numbers, new class names and talent names, world fiction, floor count, regional lineup, death rules, room counts, enchantment distribution, item catalog, quest structure, and data schemas are **proposed rules for this independent implementation**, not factual claims about the unseen internals of the referenced game. Where public references differ (for example class naming in trailer versus a store description), this document deliberately defines a consistent original class roster.

**Copyright boundary:** No branded story text, original game assets, trademarked presentation, specific dialogue or source code is required or authorized by this design. The common genre mechanics are expressed using original content labels and independently specified rules.

---

**END OF SPECIFICATION**
