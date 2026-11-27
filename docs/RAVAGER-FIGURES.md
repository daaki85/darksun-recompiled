# Wake of the Ravager's figures, before and after

Each row is a Wake of the Ravager figure and what was changed. The pictures (front, side and combat frames as shipped beside the same frames after the change, in Tyr's palette at twice the game's size) are made locally: see below. How each change is made: [FIGURES.md](FIGURES.md).

- **Party:** the Obsidian Edition's figures (Shattered Lands' party with the mod's elves and half-elves).
- **Creature:** a Shattered Lands figure of the same kind swapped in.
- **Person:** a Shattered Lands figure matched by look, dressed in Ravager's colours part by part, as the Obsidian Edition makes its half-elves (`tools/proto/people_dress.py`); where Shattered Lands' nearest figure had the wrong shape (no legs, a loincloth for a robe, the wrong size), Ravager's own art restyled instead (`tools/proto/people-restyle.json`).
- **No SL equivalent:** Ravager's own figure restyled to sit with Shattered Lands' figures.
- **Map artwork (squashed):** tables, chairs, beds and other objects on the map, lowered to two-thirds of
  their height toward their base, as Shattered Lands' steeper view shows them (walls keep their height).

The before-and-after pictures are not kept in this repository: they are made from the game's art, which stays out of git. `tools/proto/figure_table.py` makes them from the owner's own copies of the games into `docs/img/ravager-figures/` (git-ignored); the owner's private gallery shows them too.

The redrawn figures' sheets (`tools/proto/restyle/walks/` and `knights/`, read by `figure_walks.py` and `knight_melee.py`) are kept with the figure catalogue in the mod's repository (`reports/ravager-figure-redraws/` in darksun-obsidian-edition, moved there from the owner's private installation files on 2026-11-27) and copied into those two folders, which git ignores, before a build.

**The approved redraws** of the figure catalogue (in the mod's repository,
`reports/ravager-figure-redraws/catalogue/`, reviewed there figure by figure; a package's chunks that
were byte-for-byte the shipped game's were taken out, and the import takes them from STOCK_DIR) go in last:
`tools/proto/import_catalogue.py CATALOGUE BASE_DIR OUT_DIR [STOCK_DIR]` reads the catalogue's
`approved.json` (which package holds each approved picture, in the order they apply), writes them
over the build in BASE_DIR, moves the greater elementals' objects to their own figures (428 to 3954,
429 to 3955) and writes the region chunks a scene needs (the Mines3 dining table, `RGN03A.GFF`). A
still figure's package may hold only its pictures; its script then comes from the shipped game in
STOCK_DIR, since the dressing gives some of those pictures a walking script. Every frame written is
decoded and every script step checked against the frames it shows, before the game sees it.

## Party (14)

| WR picture | What it is | Used for | Change | Status |
|---|---|---|---|---|
| 25 | human man | the party | the Obsidian Edition's figure | done, seen in the game |
| 448 | human woman | the party | the Obsidian Edition's figure | done, seen in the game |
| 592 | dwarf man | the party | the Obsidian Edition's figure | done, seen in the game |
| 593 | dwarf woman | the party | the Obsidian Edition's figure | done, seen in the game |
| 691 | elf man | the party | the Obsidian Edition's figure | done, seen in the game |
| 599 | elf woman | the party | the Obsidian Edition's figure | done, seen in the game |
| 780 | half-elf man | the party | the Obsidian Edition's figure | done, seen in the game |
| 779 | half-elf woman | the party | the Obsidian Edition's figure | done, seen in the game |
| 598 | half-giant man | the party | the Obsidian Edition's figure | done, seen in the game |
| 692 | half-giant woman | the party | the Obsidian Edition's figure | done, seen in the game |
| 594 | halfling man | the party | the Obsidian Edition's figure | done, seen in the game |
| 595 | halfling woman | the party | the Obsidian Edition's figure | done, seen in the game |
| 596 | mul | the party | the Obsidian Edition's figure | done, seen in the game |
| 3917 | thri-kreen | the party | the Obsidian Edition's figure | done, seen in the game |

## Creature (8)

| WR picture | What it is | Used for | Change | Status |
|---|---|---|---|---|
| 915 | water elemental | water elemental | SL figure swapped in | done |
| 2538 | air elemental | air elemental | SL figure swapped in | done |
| 2540 | fire elemental | fire elemental | SL figure swapped in | done |
| 1881 | earth elemental | earth elemental | SL figure swapped in | done |
| 2425 | defiler | defiler | SL figure swapped in | done |
| 3893 | shadow | shadow | SL figure swapped in | done |
| 2409 | notaku | notaku | SL figure swapped in | done |
| 2420 | templar (purple robe) | templar (purple robe) | SL figure swapped in | done |

## Person (76)

| WR picture | What it is | Used for | Change | Status |
|---|---|---|---|---|
| 650 | small villager, green shirt (halfling-sized) | branch, strongrip, villager | SL 2470 dressed in WR's colours | dressed, not yet seen in the game |
| 651 | small villager, red (halfling-sized) | greshard, halfling, leaftop, soothsurg, villager | SL 2472 dressed in WR's colours | dressed, not yet seen in the game |
| 714 | innkeeper, teal (behind a counter, no walking) | innkeeper | SL 1669 dressed in WR's colours | dressed, not yet seen in the game |
| 715 | shopkeeper, dark (no walking) | shopkeeper | SL 2131 dressed in WR's colours | dressed, not yet seen in the game |
| 718 | man, teal, holding cloth (no walking) | stitches | SL 1669 dressed in WR's colours | dressed, not yet seen in the game |
| 719 | merchant woman, purple robe (no walking) | merchant | SL 154 dressed in WR's colours | dressed, not yet seen in the game |
| 720 | merchant, black (no walking) | merchant | SL 2131 dressed in WR's colours | dressed, not yet seen in the game |
| 721 | woman, pink dress (no walking) | tasarla | SL 2059 dressed in WR's colours | dressed, not yet seen in the game |
| 722 | merchant, black (no walking) | merchant | SL 2131 dressed in WR's colours | dressed, not yet seen in the game |
| 914 | beast-headed giant, skull head, loincloth | beasthead giant x2, ptar | SL 48 dressed in WR's colours | dressed, not yet seen in the game |
| 1268 | beast-headed giant, crouched | ptar | SL 48 dressed in WR's colours | dressed, not yet seen in the game |
| 1412 | beast-headed giant, horned, loincloth | beasthead giant x2, ptar's friend | SL 48 dressed in WR's colours | dressed, not yet seen in the game |
| 2022 | big woman, orange hair | melody | SL 2468 dressed in WR's colours | dressed, not yet seen in the game |
| 2405 | greater air elemental (white cloud) | grt air elem | WR's own art restyled (SL's nearest figure had the wrong shape) | restyled, not yet seen in the game |
| 2408 | dark-skinned man, purple sash | caravan master, guard, miner | SL 2131 dressed in WR's colours | dressed, not yet seen in the game |
| 2410 | woman, white top, green skirt | fayina | SL 2059 dressed in WR's colours | dressed, not yet seen in the game |
| 2411 | thief: man, white shirt, red headband | thief | Ravager figure with custom directional walks | walk verified in the built game data |
| 2412 | dark-skinned man, black shorts | draxan, kitchen slave, mercenary, miner, va guard | SL 924 dressed in WR's colours | dressed, not yet seen in the game |
| 2413 | jann (blue skin, yellow trousers) | jann | SL 2252 dressed in WR's colours | dressed, not yet seen in the game |
| 2414 | man, red shirt (Draxan soldier) | draxan x5, pedestrian, prisoner, slave, zeegrat | SL 239 dressed in WR's colours | dressed, not yet seen in the game |
| 2415 | man, purple and red | guard, halik, miner, pedestrian | SL 195 dressed in WR's colours | dressed, not yet seen in the game |
| 2416 | dark-skinned woman, orange robe | pedestrian | SL 154 dressed in WR's colours | dressed, not yet seen in the game |
| 2417 | blonde woman, green skirt | pedestrian, thesisa, zombie | SL 1053 dressed in WR's colours | dressed, not yet seen in the game |
| 2419 | dark-skinned man in black | guard, miner, slave x2, va guard, warrior | SL 246 dressed in WR's colours | dressed, not yet seen in the game |
| 2421 | bald muscular man, blue loincloth (soldier) | tyrian soldier x2, warrior | SL 559 dressed in WR's colours | dressed, not yet seen in the game |
| 2422 | red-haired man, purple | ladel, miner x3, slave, warrior, winchester | SL 424 dressed in WR's colours | dressed, not yet seen in the game |
| 2423 | red-haired man, red | arslan, mug, slave | SL 195 dressed in WR's colours | dressed, not yet seen in the game |
| 2424 | Receptionist, purple sash | Receptionist | Dressed SL body from 2408 with the original 27 action slots | seen in Tyr using a stand-in |
| 2426 | long blonde hair, slender, light dress | preserver, va member | SL 2059 dressed in WR's colours | dressed, not yet seen in the game |
| 2427 | blonde woman in red robe, green skirt | deathraker, draxan x7, jumah, kranix, templar x6, zorani | SL 154 dressed in WR's colours | dressed, not yet seen in the game |
| 2428 | bald muscular man, wristbands (Draxan/gladiator) | draxan x9, gladiator x4 | SL 563 dressed in WR's colours | dressed, not yet seen in the game |
| 2429 | huge muscular man, green bands (half-giant) | draxan, fighter x3, guard x2, miner x2, slave, thug, zombie | SL 1781 dressed in WR's colours | dressed, not yet seen in the game |
| 2430 | woman, teal dress | chander, va member | SL 2059 dressed in WR's colours | dressed, not yet seen in the game |
| 2431 | man, blue shirt | ulbin | SL 1669 dressed in WR's colours | dressed, not yet seen in the game |
| 2432 | man, green tunic | wren | SL 630 dressed in WR's colours | dressed, not yet seen in the game |
| 2433 | man, purple robe | blick, va member | SL 354 dressed in WR's colours | dressed, not yet seen in the game |
| 2434 | dark-haired man, bare chest | guard x2, miner x2 | SL 246 dressed in WR's colours | dressed, not yet seen in the game |
| 2435 | grey-haired man | citizen x2, dream, granger, miner, zombie | SL 493 dressed in WR's colours | dressed, not yet seen in the game |
| 2436 | bald man, pink loincloth | guard x3, mercenary, miner, slave, switchman | SL 924 dressed in WR's colours | dressed, not yet seen in the game |
| 2437 | huge man, teal (half-giant) | brainsniffer, slave | SL 2072 dressed in WR's colours | dressed, not yet seen in the game |
| 2438 | woman, red top, teal skirt | drisha, guard x2 | SL 1252 dressed in WR's colours | dressed, not yet seen in the game |
| 2439 | woman, purple | victim | SL 2059 dressed in WR's colours | dressed, not yet seen in the game |
| 2451 | small dark-haired man | donno, scout, snaggle, warrior | SL 676 dressed in WR's colours | dressed, not yet seen in the game |
| 2452 | small grey-haired man (dwarf-sized) | axestopper, cleave, firegazer, runner | SL 2454 dressed in WR's colours | dressed, not yet seen in the game |
| 2453 | orange-haired man, purple | dmitri, va member | SL 424 dressed in WR's colours | dressed, not yet seen in the game |
| 2454 | small woman, yellow | dodger, glade, halla, irma | SL 2472 dressed in WR's colours | dressed, not yet seen in the game |
| 2455 | small man, purple | ash, halfling, sureshot | SL 2470 dressed in WR's colours | dressed, not yet seen in the game |
| 2456 | woman, pink top | dariya, silvain | SL 1053 dressed in WR's colours | dressed, not yet seen in the game |
| 2457 | jann (blue skin, yellow) | asim drac, jann, jerrid | SL 2252 dressed in WR's colours | dressed, not yet seen in the game |
| 2458 | jann (blue skin, orange) | guard x2, masina, treasure guard | SL 2252 dressed in WR's colours | dressed, not yet seen in the game |
| 2459 | jann (blue skin, grey) | guard x7, treasure guard | SL 2252 dressed in WR's colours | dressed, not yet seen in the game |
| 2460 | jann (blue skin, green) | magnolia | SL 2252 dressed in WR's colours | dressed, not yet seen in the game |
| 2461 | woman, green loincloth | surrakina | SL 2095 dressed in WR's colours | dressed, not yet seen in the game |
| 2462 | grey-haired man, brown robe | warrior | SL 493 dressed in WR's colours | dressed, not yet seen in the game |
| 2463 | dark-skinned man, white robe | merchant, raenika | SL 724 dressed in WR's colours | dressed, not yet seen in the game |
| 2464 | man, blue shirt | acar, dhukkar, merchant, va member | SL 1669 dressed in WR's colours | dressed, not yet seen in the game |
| 2466 | white-haired old man, purple robe | nnamdi | SL 354 dressed in WR's colours | dressed, not yet seen in the game |
| 2467 | woman, red and orange | romila | SL 1252 dressed in WR's colours | dressed, not yet seen in the game |
| 2468 | grey-haired man, grey | matthias | SL 1750 dressed in WR's colours | dressed, not yet seen in the game |
| 2469 | huge bald muscular man | davin, gilad, velden | SL 2072 dressed in WR's colours | dressed, not yet seen in the game |
| 2470 | big woman, red hair, purple | kiril | SL 2468 dressed in WR's colours | dressed, not yet seen in the game |
| 2471 | big woman, dark hair, teal | helmine | SL 2468 dressed in WR's colours | dressed, not yet seen in the game |
| 2472 | grey-haired old woman, long grey robe | melantha | SL 1124 dressed in WR's colours | dressed, not yet seen in the game |
| 2473 | woman, white robe, pink hair | aravinda | SL 154 dressed in WR's colours | dressed, not yet seen in the game |
| 2474 | dark-armoured man, white headband | leader | SL 246 dressed in WR's colours | dressed, not yet seen in the game |
| 2475 | woman, purple | miner | SL 2095 dressed in WR's colours | dressed, not yet seen in the game |
| 2476 | red-haired man, grey | miner x2 | SL 424 dressed in WR's colours | dressed, not yet seen in the game |
| 2536 | revenant (grey ghostly man) | revenant | SL 1342 dressed in WR's colours | dressed, not yet seen in the game |
| 2557 | fire elemental (flames) | fire elem, grt fire elem | WR's own art restyled (SL's nearest figure had the wrong shape) | restyled, not yet seen in the game |
| 2558 | man, dark green | butler, leader | SL 2131 dressed in WR's colours | dressed, not yet seen in the game |
| 2575 | lord warrior, black armour | lord warrior | SL 1179 dressed in WR's colours | dressed, not yet seen in the game |
| 2778 | tavernkeeper, green (no walking) | tavernkeeper | SL 1448 dressed in WR's colours | dressed, not yet seen in the game |
| 3605 | white knight, silver armour | alhena, white knight | Ravager plate with redrawn side stance, walk and side-melee recovery | tested in the opening ambush using stand-in slots |
| 3606 | black knight, black armour | black knight | Ravager plate with redrawn side stance, walk and side-melee recovery | tested in the opening ambush using stand-in slots |
| 3612 | woman, purple (miner) | miner x2 | SL 2095 dressed in WR's colours | dressed, not yet seen in the game |
| 3613 | miner with pick | miner | SL 559 dressed in WR's colours | dressed, not yet seen in the game |

## No SL equivalent (45)

| WR picture | What it is | Used for | Change | Status |
|---|---|---|---|---|
| 693 | magma golem (orange blob giant) | magma golem | WR's own art restyled | restyled |
| 716 | beggar, seated | beggar | WR's own art restyled | restyled |
| 1753 | skeleton (white bones) | skeleton | Ravager figure with custom directional walks | walk seen in Tyr using a stand-in |
| 1754 | skeleton warrior, red cloak, sword | skeletonwarrior x3 | Ravager figure with custom directional walks | walk verified in the built game data |
| 1755 | yuan-ti (purple serpent) | yuan-ti x2 | WR's own art restyled | restyled |
| 1756 | giant snake (white) | giant snake x3 | WR's own art restyled | restyled |
| 1757 | snake (orange) | kartang | WR's own art restyled | restyled |
| 1758 | snake (teal) | kartang, traxiss | WR's own art restyled | restyled |
| 2345 | sundew (plant blob) | sundew | WR's own art restyled | restyled |
| 2394 | obsidian golem (black) | obsidian golem | WR's own art restyled | restyled |
| 2403 | snappersaw (spiky plant) | snappersaw | WR's own art restyled | restyled |
| 2526 | mushroom lady, crouched | mushroom lady | WR's own art restyled | restyled |
| 2537 | aurumvorax (small golden beast) | aurumvorax | WR's own art restyled | restyled |
| 2539 | soulshard (grey stone man) | soulshard | Ravager figure with custom directional walks | walk seen in Tyr using a stand-in |
| 2554 | great feyr (tentacled maw) | great feyr x2, greater feyr | WR's own art restyled | restyled |
| 2555 | umber hulk | umber hulk x3 | Ravager figure with custom directional walks | walk verified in the built game data |
| 2556 | shambling mound (green) | shambling mound | WR's own art restyled | restyled |
| 2570 | Zorani, seated cross-legged | zorani | WR's own art restyled | restyled |
| 2843 | yuan-ti (red and gold serpent) | yuan-ti | WR's own art restyled | restyled |
| 2844 | yuan-ti (red serpent) | yuan-ti | WR's own art restyled | restyled |
| 2845 | serpent (purple) | tantris | WR's own art restyled | restyled |
| 2846 | serpent (teal) | jestris | WR's own art restyled | restyled |
| 2847 | serpent (orange) | solurnis | WR's own art restyled | restyled |
| 2849 | serpent (green) | senturnis | WR's own art restyled | restyled |
| 2850 | verini (tan ape-lizard) | guard x2, verini x2 | Ravager figure with custom directional walks | walk verified in the built game data |
| 2852 | verini (yellow) | prosser, verini child, winter | Ravager figure with custom directional walks | walk verified in the built game data |
| 2853 | verini (dark red) | galinix, rhone, silvan, speaker | Ravager figure with custom directional walks | walk verified in the built game data |
| 2854 | verini (grey) | nortemus, zydeko | Ravager figure with custom directional walks | walk verified in the built game data |
| 2855 | verini (white) | fori | Ravager figure with custom directional walks | walk seen in Tyr using a stand-in |
| 2858 | verini (green) | elovan, farmer, xarax | Ravager figure with custom directional walks | walk verified in the built game data |
| 2859 | verini (orange) | guard, jakath, verini x2 | Ravager figure with custom directional walks | walk verified in the built game data |
| 2860 | verini (purple) | kell, yerath | Ravager figure with custom directional walks | walk verified in the built game data |
| 2861 | verini (red) | brotel, guard x2, talo | Ravager figure with custom directional walks | walk verified in the built game data |
| 2863 | verini (brown) | guard x3, verini | Ravager figure with custom directional walks | walk verified in the built game data |
| 2884 | mind flayer, green robe | mindflayer | WR's own art restyled | restyled |
| 2885 | mind flayer, pink robe | mindflayer x3 | WR's own art restyled | restyled |
| 2887 | mind flayer, orange robe | mind flayer | WR's own art restyled | restyled |
| 2888 | mind flayer, red robe | mind flayer | WR's own art restyled | restyled |
| 2889 | mind flayer, teal robe | mindflayer | WR's own art restyled | restyled |
| 2890 | mind flayer, black robe | prim | WR's own art restyled | restyled |
| 2891 | mind flayer, purple robe | mind flayer, mindflayer x6 | WR's own art restyled | restyled |
| 2895 | yuan-ti (white serpent) | yuan-ti | WR's own art restyled | restyled |
| 3461 | Sirah, crouched | sirah | WR's own art restyled | restyled |
| 3509 | tree creature |  | WR's own art restyled | restyled |
| 3866 | Generoe, plant woman | generoe | WR's own art restyled | restyled |

## Map artwork (squashed) (60)

| WR picture | What it is | Used for | Change | Status |
|---|---|---|---|---|
| 1 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 243 | map object | placed 14 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 252 | map object | placed 4 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 255 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 327 | map object | placed 3 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 341 | map object | placed 8 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 449 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 455 | map object | placed 6 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 516 | map object | placed 9 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 519 | map object | placed 3 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 520 | map object | placed 2 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 521 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 524 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 525 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 530 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 531 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 542 | map object | placed 6 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 547 | map object | placed 3 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 703 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2215 | map object | placed 5 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2219 | map object | placed 4 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2226 | map object | placed 4 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2352 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2355 | map object | placed 3 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2359 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2360 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2361 | map object | placed 3 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2365 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2371 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2374 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2375 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2376 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2377 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2379 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2581 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2586 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2587 | map object | placed 2 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2817 | map object | placed 4 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2818 | map object | placed 3 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2819 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2820 | map object | placed 2 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2822 | map object | placed 2 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2828 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2829 | map object | placed 5 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2835 | map object | placed 2 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2836 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2838 | map object | placed 3 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2839 | map object | placed 3 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2841 | map object | placed 2 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2899 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2923 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2924 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2925 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 2926 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 3262 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 3263 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 3554 | map object | placed 6 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 3555 | map object | placed 1 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |
| 3559 | map object | placed 4 times in Tyr | lowered to two-thirds toward its base | done, seen in the game |

