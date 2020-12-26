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

-all materials in a mesh must have an exact node layout (import_static/skinned_msb.py takes care of that, you can look up models loaded through that plugin to see how it looks like)

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

-all requirements for exporting static models also apply here

usage: File -> Export... (only specify .msb file)

**note**: 4 files will be generated upon using this plugin: name.msb, name.bor, name.bsi and name_SKIN.msb

name.msb goes to mesh folder

name.bor goes to animation folder

name.bsi goes to skinning/b20 folder

name_SKIN.msb goes to skinning/b20 folder, and you must REMOVE the _SKIN part of the filename

# import_animation_bob.py

selecting a skeleton in 3D view allows you to open animation file that matches the skeleton

requirements:

-selected skeleton has the same number of bones as the chosen animation file

usage: File -> Import...

# export_animation_bob.py

if your skeleton has any animation data (position/rotation keyframes), you should be able to export that data as a spellforce-compatible .bob animation file

requirements:

-selected object is a skeleton and it has animation keyframes

usage: File -> Export...

**note**: .bob animation files go to animation folder in spellforce directory

# import_static_skin_msb.py

this is something you can use on original SKIN .msb files, to see how they look like (specifically normals, since they differ from the STATIC .msb file normals, sometimes significantly)

files imported with this plugin are not very good for anything else, so don't get any ideas :^)

usage: File -> Import...
