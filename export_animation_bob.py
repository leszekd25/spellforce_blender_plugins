bl_info = {
	"name": "Export SpelLForce animation (.bob)",
	"description": "Export SpellForce animation (.bob)",
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
from struct import unpack, pack
import os.path


class AnimationBoneData:
	def __init__(self):
		self.positions = []
		self.positions_time = []
		self.positions_max_time = 0
		self.rotations = []
		self.rotations_time = []
		self.rotations_max_time = 0
	def add_rotation(self, t, q):
		self.rotations.append(Quaternion(q))
		self.rotations_time.append(t)
		self.rotations_max_time = max(self.rotations_max_time, t)
	def add_position(self, t, p):
		self.positions.append(Vector(p))
		self.positions_time.append(t)
		self.positions_max_time = max(self.positions_max_time, t)
		
def SaveBOB(context, filepath):
	object = context.object
	armature = object.data
	
	bpy.ops.object.mode_set(mode = 'EDIT')
	
	bone_names = {}
	for i in range(len(armature.edit_bones)):
		print('pose.bones["'+armature.edit_bones[i].name+'"].')
		bone_names['pose.bones["'+armature.edit_bones[i].name+'"].'] = i
	bone_anim = []
	for i in range(len(armature.edit_bones)):
		bone_anim.append(AnimationBoneData())
	
	#pre-processing
	max_time_pos = []
	max_time_rot = []
	max_time = 0
	
	bone_pos_count = []
	bone_rot_count = []
	for i in range(len(armature.edit_bones)):
		bone_pos_count.append(0)
		bone_rot_count.append(0)
	for fc in object.animation_data.action.fcurves:
		if fc.data_path.endswith(('location')):
			bone_n = fc.data_path[:-8]
			bone_i = bone_names[bone_n]
			bone_pos_count[bone_i] += len(fc.keyframe_points)
		elif fc.data_path.endswith(('rotation_quaternion')):
			bone_n = fc.data_path[:-19]
			bone_i = bone_names[bone_n]
			bone_rot_count[bone_i] += len(fc.keyframe_points)
			
		
	for fc in object.animation_data.action.fcurves:
		if fc.data_path.endswith(('location')):
			bone_n = fc.data_path[:-8]
			bone_i = bone_names[bone_n]
			array_pos = []
			array_time = []
			entries = bone_pos_count[bone_i]//3
			array_index = -1
			if len(array_pos) == 0:
				for i in range(entries):
					array_pos.append([0, 0, 0])
					array_time.append(0)
			for i in range(len(fc.keyframe_points)):
				key = fc.keyframe_points[i]
				array_pos[i % entries][fc.array_index] = key.co[1]
				array_time[i % entries] = key.co[0] / 25
				array_index = fc.array_index
			if len(bone_anim[bone_i].positions) == 0:
				for i in range(entries):
					bone_anim[bone_i].add_position(array_time[i], array_pos[i])
			else:
				for i in range(entries):
					bone_anim[bone_i].positions[i][array_index] = array_pos[i][array_index]
		elif fc.data_path.endswith(('rotation_quaternion')):
			bone_n = fc.data_path[:-19]
			bone_i = bone_names[bone_n]
			array_rot = []
			array_time = []
			entries = bone_rot_count[bone_i]//4
			array_index = -1
			for i in range(entries):
				array_rot.append([0, 0, 0, 0])
				array_time.append(0)
			for i in range(len(fc.keyframe_points)):
				key = fc.keyframe_points[i]
				array_rot[i % entries][fc.array_index] = key.co[1]
				array_time[i % entries] = key.co[0] / 25
				array_index = fc.array_index
			if len(bone_anim[bone_i].rotations) == 0:
				for i in range(entries):
					bone_anim[bone_i].add_rotation(array_time[i], array_rot[i])
			else:
				for i in range(entries):
					bone_anim[bone_i].rotations[i][array_index] = array_rot[i][array_index]
		
	
	# transform the values to be correct
	# REFERENCE POSE
	bone_pos = []
	bone_rot = []
	
	bpy.ops.object.mode_set(mode='EDIT')

	for i in range(len(armature.edit_bones)):
		bone = armature.edit_bones[i]
		bone_mat = bone.matrix
		if(bone.parent):
			bone_mat = bone.parent.matrix.inverted() @ bone.matrix
		#print(bone_mat, bone_mat.to_translation(), bone_mat.to_quaternion())
		bone_pos.append(bone_mat.to_translation())
		bone_rot.append(bone_mat.to_quaternion())
	#print(bone_rot)
	#print(bone_pos)
	
	for i, ad in enumerate(bone_anim):
		for j in range(len(ad.positions)):
			ad.positions[j] = ad.positions[j]+bone_pos[i]
		for j in range(len(ad.rotations)):
			ad.rotations[j] = bone_rot[i] @ ad.rotations[j]

	
	bpy.ops.object.mode_set(mode = 'OBJECT')
	
	bobfile = open(filepath.replace(".bob", "")+".bob",'wb')
	
	outdata1 = pack("H", 256)
	bobfile.write(outdata1)
	outdata2 = pack("I", len(bone_anim))
	bobfile.write(outdata2)
	for i in range(len(bone_anim)):
		bone = bone_anim[i]
		outdata3 = pack("IffII", 0, 1.0, bone.rotations_max_time, 3, len(bone.rotations))
		bobfile.write(outdata3)
		for j in range(len(bone.rotations)):
			outdata4 = pack("fffff", bone.rotations[j][0], bone.rotations[j][1], bone.rotations[j][2], bone.rotations[j][3], bone.rotations_time[j])
			bobfile.write(outdata4)
		outdata3 = pack("IffII", 0, 1.0, bone.positions_max_time, 3, len(bone.positions))
		bobfile.write(outdata3)
		for j in range(len(bone.positions)):
			outdata4 = pack("ffff", bone.positions[j][0], bone.positions[j][1], bone.positions[j][2], bone.positions_time[j])
			bobfile.write(outdata4)
	
	bobfile.close()
	
	return 0


class ExportAnimationBOB(bpy.types.Operator, ExportHelper):
	"""Object Cursor Array"""
	bl_idname = "export.msb_static"
	bl_label = "Export SpellForce animation (.bob)"
	bl_options = {'REGISTER'}
	
	filepath: StringProperty(
		name="Output animation",
		subtype='FILE_PATH'
		)

	filename_ext = ".bob"

	filter_glob: StringProperty(
			default="*.bob",
			options={'HIDDEN'},
			)
	
	@classmethod
	def poll(cls, context):
		obj = context.object
		return obj and obj.type == 'ARMATURE'

	def execute(self, context):
		if SaveBOB(context, self.filepath) == 0:
			return {'FINISHED'}
		return {'CANCELLED'}



def menu_func(self, context):
	self.layout.operator(ExportAnimationBOB.bl_idname, text="Export SpellForce animation (.bob)")


def register():
	bpy.utils.register_class(ExportAnimationBOB)
	bpy.types.TOPBAR_MT_file_export.append(menu_func)

def unregister():
	bpy.utils.unregister_class(ExportAnimationBOB)
	bpy.types.TOPBAR_MT_file_export.remove(menu_func)


if __name__ == "__main__":
	register()