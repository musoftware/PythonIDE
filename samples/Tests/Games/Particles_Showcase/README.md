# Particles_Showcase

**pygame particles** - tests the particle system and the Particle Editor (round 6).

- Emitter objects (areas with a *Particles* section in the inspector): two torches (`fire` + `smoke`),
  `Snow` across the whole sky (emit width 800), `Fountain` (texture `star`, spin) that starts switched off.
- Effects are edited in **Add > Particle Editor...** (rate, lifetime, speed, angle / spread, gravity,
  damping, colour and size over life, shape or texture, additive blend, burst count, duration) with a
  live preview (click the preview = Burst).
- Code (`Scene1.py`): `Emit("trail", Player)` follows the orb, a click makes `Burst("explosion", x, y)`,
  collected coins `Burst("coin", other)`, F toggles `Fountain.emitting`, T switches the torches.

**Try it:** F5 and move with the arrows, click, press F / T. Headless:
`set SDL_VIDEODRIVER=dummy & set RADGAME_FRAMES=150 & set RADGAME_KEYS=right:20-120 & set RADGAME_SCREENSHOT=shot.png & python main.py`.
The Godot export turns every emitter and Emit / Burst into CPUParticles2D with the same settings.
