# spellforce_blender_plugins
all blender plugins i came up with regarding import/export of 3D stuff from spellforce 1

all of those should work with blender 2.78, probably some earlier versions too

**new:** there's also a set of plugins for 2.8, they are much better than the plugins below, so i recommend using those; read the readme file in the 2.8 directory above

**everything below only applies to plugins in this directory, not to the 2.8 plugins**

# how to install plugins
open blender -> User Preferences... -> Add-ons -> Install add-on from file... -> choose plugin file (.py extension) -> enable plugin by checking the checkbox

read further for specific usage of each plugin

# spellforce_import.py
you can choose any .msb file to import (and edit) in blender

requirements:

-textures have to be in the same directory as the .msb file (pulling htem from spellforce data is enough, look for texture names that are suspiciously similar to the .msb file name)

usage: File -> Import...

# spellforce_export.py
any edited model can be exported to .msb file

requirements:

-all faces must be triangles

-no two points on any single UV map may overlap (edges and faces can intersect alright though)

usage: File -> Export...

# spellforce_import_with_skeleton

if you have .bor file to associate with the .msb mesh file, you can import both as a mesh and skeleton

requirements:

-skeleton file (.bor) is in the same folder as mesh file (.msb)

-both files have the same name (except file format)

-mesh is in original, unedited form (as in, exact same mesh as it was bundled with spellforce)

same requirements as with base mesh import plugin

usage: File -> Import... (only select .msb file)

WARNING: meshes loaded with skeleton are no longer editable due to mesh transformations required for animations to work (more work on it in the future)

NOTE: bone orientations do not look properly in blender for now, but the model and skeleton receive transformations properly

# spellforce_import_animation

you can choose any .bob file to open and edit in blender

requirements:

-selected object in blender is armature (skeleton)

-number of bones in skeleton and animation must match

for obvious reasons, animations only work with skeleton files imported with the spellforce_import_with_skeleton plugin

usage: File -> Imoprt...

# spellforce_export_animation

any edited animation can be exported to .bob animation file

for same reasons, this will work properly only if animation was first imported using the plugin mentioned above

requirements:

-selected object in blender is armature (skeleton)

usage: File -> Export...
