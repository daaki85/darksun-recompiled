# A test session on Windows

What to try, in an order that finds the most with the least time, and what
to send back when something is off. Everything here was run on Linux and
under Wine before this build was packed; the mouse and the window have not
been tried on Windows itself since the last fix.

## Setting up

1. Unzip `darksun-recompiled-windows-x64.zip` into the mod's folder (the
   one with *Start Obsidian Edition.bat*) or next to it. The zip holds
   `dsun.exe`, `SDL2.dll` and a `build` folder; keep them together.
2. Start the mod once with *Start Obsidian Edition.bat*. The Loader's window
   should say the game runs as Dark Sun Recompiled, not DOSBox. If it says
   DOSBox, the Loader did not find the program: run
   `python -m dsloader launch --recompiled <path to dsun.exe>` once.
3. For the plain game, double-click `dsun.exe`: a box of buttons offers
   *Shattered Lands*, *with the Obsidian Edition*, *Wake of the Ravager*,
   *Transfer a party*.

## The mouse, first

This is the one thing never confirmed on Windows.

- Move the pointer to each corner of the game window. The game's own
  pointer should reach each corner, and sit under the Windows pointer.
- Resize the window (drag a corner), then try the corners again. Press F11
  for full screen, try again, F11 back.
- Click the main menu's START GAME; right-click a figure on the map (the
  look pointer appears).

If the pointer is off: say whether it is offset, limited to part of the
window, or jumping, at which window size, and whether F11 changes it. A
run with `set DS_TRACE_MOUSE=1` before starting `dsun.exe` puts a line per
mouse event in `dsun.log` (beside `dsun.exe`); that log settles it.

## Then, in this order

1. **Intro and menu.** Escape through the intro. The menu's music plays.
2. **Create a character.** The roster's NEW opens the mod's screen with
   SUM. Roll the die a few times; STORE, roll again, RECALL (this crashed
   until this build). Click the class off and another on; KITS; DONE and
   pick weapon specialties. The dice log shows each roll.
3. **Start the game.** After the announcer's box (click it away) the
   scripted bout plays, then the party stands at the gate, all four,
   dressed, with shadows (this was one figure until this build).
4. **Walk south** into the arena. The first real fight starts after the
   Monster Trainer's lines. In the fight: Tab chooses an enemy (red ring),
   Enter attacks it; right-click a monster for the Look box; L opens the
   combat log. Watch the Loader's dice log fill.
5. **Screens.** V, I, U, E, M, O and Escape out of each; the inventory's
   THAC0 per weapon; the Effects screen's kit lines.
6. **Save and load.** Escape, SAVE, a row, a name, SAVE: the game saves
   and exits (that is the game's EXIT menu). Start again, LOAD SAVED GAME,
   PgDn and PgUp between the pages, load the save.
7. **After the fight**, into the pens: talk to people (Kalzith is in a pen
   of his own in the middle column), the Trustee, a shop.

## When something goes wrong

- **A crash or "Stack overflow!"**: the screen stops with a text message
  until a key is pressed. Send `dsun.log` and, when the Loader ran the
  game, the newest zip in the mod's `crash-logs` folder. Say what you
  clicked last.
- **A freeze**: wait ten seconds (a slow scene is not a freeze), then
  send the log and a screenshot.
- **Wrong picture or sound**: a screenshot and the log.
- **The game says a file is missing**: the log's first lines name the
  folders it used.

The log is overwritten on every start, so copy it before starting again.
