# AutoTile_Island

**auto-tiling (terrain sets)** - tests the terrain brush of the tilemap editor (round 6).

- `assets/grass47.png` (47-tile blob: sides and corners) and `assets/wall16.png` (16 tiles: sides) were
  drawn by **Terrains... > Template tileset...** in the Tiles tab; the terrains `grass` (47) and `wall`
  (16, on a collision layer) map every neighbour combination to a tile (standard layouts rad47 / rad16;
  edit the Tile column to use your own tileset).
- Paint: choose the layer, pick **Terrain: Grass** under the tile palette, then Paint / Rect / Fill /
  Erase - edges and inner / outer corners pick themselves; (none) paints single tiles again.
- Run time: B / N add / remove wall blocks under the hero with `SetTerrain("Walls", col, row, "wall")` -
  the neighbours re-tile too (pygame and the Godot export give the same tiles).

**Try it:** open `Scene1.scene`, paint some grass in the water; F5 to walk (arrows) and build (B / N).
