# spellforce_blender_plugins
all blender plugins i came up with regarding import/export of 3D stuff from spellforce 1

# how to install plugins
open blender -> User Preferences... -> Add-ons -> Install add-on from file... -> choose plugin file (.py extension) -> enable plugin by checking the checkbox

read further for specific usage of each plugin

# spellforce_import.py
you can choose any .msb file to import (and edit) in blender

requirements:

-textures have to be in the same directory as the .msb file (pulling htem from spellforce data is enough, look for texture names that are suspiciously similar to the .msb file name)

# spellforce_export.py
any edited model can be exported to .msb file

requirements:

-all faces must be triangles

-no two points on any single UV map may overlap (edges and faces can intersect alright though)
