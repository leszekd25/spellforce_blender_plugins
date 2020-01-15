# spellforce_blender_plugins
all blender plugins i came up with regarding import/export of 3D stuff from spellforce 1

all of those should work from blender 2.8 onwards

# how to install plugins
open blender -> Edit -> User Preferences... -> Add-ons -> Install... -> choose plugin file (.py extension) -> enable plugin by checking the checkbox

read further for specific usage of each plugin

# import_static_msb.py
you can choose any .msb file to import (and edit) in blender

requirements:

-textures have to be in the same directory as the .msb file (pulling them from spellforce data is enough, look for texture names that are suspiciously similar to the .msb file name)

usage: File -> Import...

# export_static_msb.py
any edited model can be exported to .msb file

requirements:

-all faces must be triangles

-no two points on the UV map may overlap (edges and faces can intersect alright though)

-all materials in a mesh must have an exact node layout (import_static_msb.py takes care of that, you can look up models loaded through that plugin for node layout lookup)

usage: File -> Export...

# import_skinned_msb.py

if you have .bor file to associate with the .msb mesh file, you can import both as a mesh and skeleton

requirements:

-skeleton file (.bor) is in the same folder as mesh file (.msb)

-both files have the same name (except file format)

-both .msb and .bor file must be either original ones, or ones generated with export_skinned_msb.py plugin

-same requirements as with base mesh import plugin

usage: File -> Import... (only select .msb file)

NOTE: bone orientations do not look properly in blender for now, but the model and skeleton receive transformations properly

# export_skinned_msb.py

after editing models/skeletons loaded in through import_skinned_msb.py, you can save the changes using this plugin

requirements:

-selected object in blender is mesh object, and it has a parent, which is the skeleton

-mesh vertex groups and skeleton bones are in a 1:1 relation (one vertex group per bone, both have the same name) (files loaded via import_skinned_msb.py are already set up for that)

-all vertices are assigned to at least one vertex group

usage: File -> Export... (only specify .msb file

**note**: 4 files will be generated upon using this plugin: name.msb, name.bor, name.bsi and name_SKIN.msb

name.msb goes to mesh folder

name.bor goes to animation folder

name.bsi goes to skinning/b20 folder

name_SKIN goes to skinning/b20 folder, and you must REMOVE the _SKIN part of the filename
