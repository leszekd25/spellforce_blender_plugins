bl_info = {
	"name": "Import SpellForce animation (.bob)",
	"description": "Import SpellForce animation (.bob)",
	"author": "leszekd25",
	"blender": (2, 80, 0),
	"location": "Import/Export",
	"warning": "totally untested...", # used for warning icon and text in addons panel
	"category": "Import-Export",
}

import bpy
from bpy.props import (
	StringProperty,
	FloatProperty,
	IntProperty,
	BoolProperty,
	EnumProperty,
)
from bpy_extras.io_utils import (
	ImportHelper,
	ExportHelper,
	orientation_helper,
	axis_conversion,
)
from mathutils import *
from struct import unpack
import os.path


class AnimationBoneData:
	def __init__(self):
		self.positions = []
		self.positions_time = []
		self.rotations = []
		self.rotations_time = []
	def add_rotation(self, t, q):
		self.rotations.append(q)
		self.rotations_time.append(t)
	def add_position(self, t, p):
		self.positions.append(p)
		self.positions_time.append(t)

def LoadBOB(context, filepath):
	object = context.object
	
	anim_bones = []
	
	msbfile = open(filepath,'rb')

	indata = unpack("H", msbfile.read(2))
	indata = unpack("I", msbfile.read(4))
	print(indata[0])
	bonecount = indata[0]
	
	for i in range(bonecount):
		#print(i)
		anim_data = AnimationBoneData()
		indata2 = unpack("IffII", msbfile.read(20))
		anim_rot_count = indata2[4]
		#print(anim_rot_count)
		for j in range(anim_rot_count):
			indata3 = unpack("fffff", msbfile.read(20))
			q = Quaternion([indata3[0], indata3[1], indata3[2], indata3[3]])
			#print(j, q, indata3[4])
			anim_data.add_rotation(indata3[4], q)
		indata2 = unpack("IffII", msbfile.read(20))
		anim_pos_count = indata2[4]
		#print(anim_pos_count)
		for j in range(anim_pos_count):
			indata3 = unpack("ffff", msbfile.read(16))
			p = Vector([indata3[0], indata3[1], indata3[2]])
			#print(p, indata3[3])
			anim_data.add_position(indata3[3], p)
		anim_bones.append(anim_data)
	
	msbfile.close()
	
	b_skel = object.pose
	armature = object.data
	
	if bonecount != len(b_skel.bones):
		print("BONES DON'T MATCH")
		return -1
		
	# REFERENCE POSE
	bone_pos = []
	bone_rot = []
	
	bpy.ops.object.mode_set(mode='EDIT')

	for i in range(bonecount):
		bone = armature.edit_bones[i]
		bone_mat = bone.matrix
		if(bone.parent):
			bone_mat = bone.parent.matrix.inverted() @ bone.matrix
		#print(bone_mat, bone_mat.to_translation(), bone_mat.to_quaternion())
		bone_pos.append(bone_mat.to_translation())
		bone_rot.append(bone_mat.to_quaternion())
	#print(bone_rot)
	#print(bone_pos)
	
	for i, ad in enumerate(anim_bones):
		for j in range(len(ad.positions)):
			ad.positions[j] = ad.positions[j]-bone_pos[i]
		for j in range(len(ad.rotations)):
			ad.rotations[j] = bone_rot[i].rotation_difference(ad.rotations[j])
	
	bpy.ops.object.mode_set(mode='POSE')
	
	for i in range(bonecount):
		for j in range(len(anim_bones[i].positions)):
			b_skel.bones[i].location = anim_bones[i].positions[j]
			b_skel.bones[i].keyframe_insert(data_path = "location", frame = anim_bones[i].positions_time[j] * 25)
		for j in range(len(anim_bones[i].rotations)):
			b_skel.bones[i].rotation_quaternion = anim_bones[i].rotations[j]
			b_skel.bones[i].keyframe_insert(data_path = "rotation_quaternion", frame = anim_bones[i].rotations_time[j] * 25)
			
	return 0


class ImportAnimationBOB(bpy.types.Operator, ImportHelper):
	"""Object Cursor Array"""
	bl_idname = "import.bob_animation"
	bl_label = "Import SpellForce animation (.bob)"
	bl_options = {'REGISTER', 'UNDO'}
	
	filepath: StringProperty(
		name="Input animation",
		subtype='FILE_PATH'
		)

	filename_ext = ".msb"

	filter_glob: StringProperty(
			default="*.bob",
			options={'HIDDEN'},
			)
			
	@classmethod
	def poll(cls, context):
		obj = context.object
		return obj and obj.type == 'ARMATURE'

	def execute(self, context):
		if LoadBOB(context, self.filepath) == 0:
			return {'FINISHED'}
		return {'CANCELLED'}



def menu_func(self, context):
	self.layout.operator(ImportAnimationBOB.bl_idname, text="Import SpellForce animation (.bob)")


def register():
	bpy.utils.register_class(ImportAnimationBOB)
	bpy.types.TOPBAR_MT_file_import.append(menu_func)

def unregister():
	bpy.utils.unregister_class(ImportAnimationBOB)
	bpy.types.TOPBAR_MT_file_import.remove(menu_func)


if __name__ == "__main__":
	register()