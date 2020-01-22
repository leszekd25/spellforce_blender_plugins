bl_info = {
	"name": "Export static SpellForce mesh (.msb)",
	"description": "Export static SpellForce mesh (.msb)",
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
	
class SFMap:
	def __init__(self):
		self.texID = -1		  #32 bit
		self.unknown1 = 0	  #8 bit
		self.texUVMode = 0	  #8 bit
		self.unused = 0		  #16 bit
		self.texRenderMode = 0#8 bit
		self.texAlpha = 1	  #8 bit
		self.flag = 7		  #8 bit
		self.depthbias = 0	  #8 bit
		self.tiling = 1.0	#float
		self.texName = ""	  #64 char string
	def set(self, table):
		print(table)
		self.texID = table[0]	  #always -1?
		self.unknown1 = table[1]  #idk
		self.texUVMode = table[2] #probably always 0
		self.unused = table[3]	  #anything goes here
		self.texRenderMode = table[4]	#depends, usually 0
		self.texAlpha = table[5]/255
		self.flag = table[6]	  #should be 7 except noted otherwise
		self.depthbias = table[7] #always 0?
		self.tiling = table[8]	  #always 1.0?
		ntable = []
		for c in table[9]:
			if c == 0:
				break
			ntable.append(c)
		self.texName = str(bytearray(ntable), "utf-8")
	def get(self):
		charray = []
		for i in range(64):
			if i >= len(self.texName):
				charray.append(0)
			else:
				charray.append(ord(self.texName[i]))
		charray = bytes(charray)
		return pack("1i2B1H4B1f64s", self.texID, self.unknown1, self.texUVMode, self.unused, self.texRenderMode, self.texAlpha, self.flag, self.depthbias, self.tiling, charray)

		
class SFMaterial:
	def __init__(self):
		self.texMain = SFMap()
		self.texSecondary = SFMap()
		self.diffCol = []
		self.emitCol = []
		self.specCol = []
		


def ContainsVert(list, vert):
	for v in list:
		if(v[0] == vert[0]) and (v[1][0] == vert[1][0]) and (v[1][1] == vert[1][1]):
			return v
	return None		
	

def SaveMSBStatic(context, filepath):
	object = bpy.context.object
	obname=object.name
	mesh = object.data
	
	msbfile = open(filepath.replace(".msb", "")+".msb",'wb')
	modelnum = len(mesh.materials)
	
	triangles_per_material = [[] for i in range(modelnum)]
	for i, p in enumerate(mesh.polygons):
		# tpm[material_index] = [[index[v0], index[v1], index[v2]], [...], ...], v0, v1, v2 directly from blender mesh
		triangles_per_material[p.material_index].append([mesh.loops[i*3+0].vertex_index, mesh.loops[i*3+1].vertex_index, mesh.loops[i*3+2].vertex_index, i*3+0, i*3+1, i*3+2])

	uv_layer = mesh.uv_layers[mesh.name]
	unique_verts_per_material = [[] for i in range(modelnum)]  # unique vert: [vertex index respective to triangle, unique uv, table of indices using this vertex]
	for i, tpm in enumerate(triangles_per_material):
		for j, t in enumerate(tpm):
			for k in range(3):
				vert = [t[k], uv_layer.data[t[k+3]].uv, []]
				found_v = ContainsVert(unique_verts_per_material[i], vert)
				if(found_v == None):
					unique_verts_per_material[i].append(vert)
					vert[2].append(3*j+k)
				else:
					found_v[2].append(3*j+k)
	
	# adjust material count to exclude empty meshbuffers
	mat_offset = 0
	for i in range(modelnum):
		if((len(unique_verts_per_material[i-mat_offset]) == 0) or (len(triangles_per_material[i-mat_offset]) == 0)):
			del unique_verts_per_material[i-mat_offset]
			del triangles_per_material[i-mat_offset]
			mat_offset += 1
	modelnum = len(unique_verts_per_material)

	bbox_per_model = [[10000, 10000, 10000, -10000, -10000, -10000] for i in range(modelnum)]
	bbox_total = [10000, 10000, 10000, -10000, -10000, -10000]
	
	# calculate bounding boxes
	for i in range(modelnum):
		for v in unique_verts_per_material[i]:
			pos = mesh.vertices[v[0]].co
			bbox_per_model[i][0] = min(bbox_per_model[i][0], pos[0])
			bbox_per_model[i][1] = min(bbox_per_model[i][1], pos[1])
			bbox_per_model[i][2] = min(bbox_per_model[i][2], pos[2])
			bbox_per_model[i][3] = max(bbox_per_model[i][3], pos[0])
			bbox_per_model[i][4] = max(bbox_per_model[i][4], pos[1])
			bbox_per_model[i][5] = max(bbox_per_model[i][5], pos[2])
			
	for i in range(modelnum):
		bbox_total[0] = min(bbox_total[0], bbox_per_model[i][0])
		bbox_total[1] = min(bbox_total[1], bbox_per_model[i][1])
		bbox_total[2] = min(bbox_total[2], bbox_per_model[i][2])
		bbox_total[3] = max(bbox_total[3], bbox_per_model[i][3])
		bbox_total[4] = max(bbox_total[4], bbox_per_model[i][4])
		bbox_total[5] = max(bbox_total[5], bbox_per_model[i][5])

			
	# write header
	outdata = pack("BBHBB", 0, 2, modelnum, 0, 0)
	msbfile.write(outdata)
	
	for i in range(modelnum):
		outdata2 = pack("2b4H", 0, 2, len(unique_verts_per_material[i]), 0, len(triangles_per_material[i]), 0)
		msbfile.write(outdata2)
		
		# calculate correct vertex indices in triangles
		ind_array = [0 for k in range(len(triangles_per_material[i])*3)]
		for k, v in enumerate(unique_verts_per_material[i]):
			for ix in v[2]:
				ind_array[ix] = k
		
		# calculate positions and normals
		vertex_positions = []
		for v in unique_verts_per_material[i]:
			vertex_positions.append(mesh.vertices[v[0]].co)
		
		normals_per_triangle = [[] for j in range(len(triangles_per_material[i]))]
		normals_per_vertex = [[0, 0, 0] for j in range(len(unique_verts_per_material[i]))]
		for k in range(len(ind_array)//3):
			v1 = vertex_positions[ind_array[3*k+0]]
			v2 = vertex_positions[ind_array[3*k+1]]
			v3 = vertex_positions[ind_array[3*k+2]]
			
			U = [v2[0]-v1[0], v2[1]-v1[1], v2[2]-v1[2]]
			V = [v3[0]-v1[0], v3[1]-v1[1], v3[2]-v1[2]]
			nm = [U[1]*V[2] - U[2]*V[1], U[2]*V[0] - U[0]*V[2], U[0]*V[1] - U[1]*V[0]]
			nm_l = (nm[0]*nm[0] + nm[1]*nm[1] + nm[2]*nm[2])**0.5
			nm2 = [nm[0]/nm_l, nm[1]/nm_l, nm[2]/nm_l]
			normals_per_triangle[k] = nm2
			
			nmv1 = normals_per_vertex[ind_array[3*k+0]]
			nmv1 = [nmv1[0]+nm2[0], nmv1[1]+nm2[1], nmv1[2]+nm2[2]]
			normals_per_vertex[ind_array[3*k+0]] = nmv1
			nmv2 = normals_per_vertex[ind_array[3*k+1]]
			nmv2 = [nmv2[0]+nm2[0], nmv2[1]+nm2[1], nmv2[2]+nm2[2]]
			normals_per_vertex[ind_array[3*k+1]] = nmv2
			nmv3 = normals_per_vertex[ind_array[3*k+2]]
			nmv3 = [nmv3[0]+nm2[0], nmv3[1]+nm2[1], nmv3[2]+nm2[2]]
			normals_per_vertex[ind_array[3*k+2]] = nmv3
		
		for k, v in enumerate(unique_verts_per_material[i]):
			pos = vertex_positions[k]
			normal = normals_per_vertex[k]
			col = [255, 255, 255, 255]
			uv = v[1]
			ind = v[0]
			outdata3 = pack('6f4B2fI', pos[0], pos[1], pos[2], normal[0], normal[1], normal[2], col[0], col[1], col[2], col[3], uv[0], 1-uv[1], ind)
			msbfile.write(outdata3)
		
				
		for k in range(len(ind_array)//3):
			outdata4 = pack("4H", ind_array[3*k+0], ind_array[3*k+1], ind_array[3*k+2], i)
			msbfile.write(outdata4)
		
		# handle materials
		material = SFMaterial()
		diffuse_color = mesh.materials[i].node_tree.nodes.get('Diffuse Color').outputs[0].default_value
		material.diffCol = [int(diffuse_color[2]*255), int(diffuse_color[1]*255), int(diffuse_color[0]*255), 255]
		specular_color = mesh.materials[i].node_tree.nodes.get('Specular Color').outputs[0].default_value
		material.specCol = [int(specular_color[2]*255), int(specular_color[1]*255), int(specular_color[0]*255), 255]
		material.emitCol = [0, 0, 0, 0]
		if mesh.materials[i].get('SFRenderMode') is not None:
			material.texMain.texRenderMode = mesh.materials[i]["SFRenderMode"]
		else:
			material.texMain.texRenderMode = 0
		if mesh.materials[i].get("SFFlags") is not None:
			material.texMain.flag = mesh.materials[i]["SFFlags"]
		else:
			material.texMain.flag = 7
		material.texMain.texAlpha = 255
		material.texMain.texName = mesh.materials[i].node_tree.nodes.get('Image Texture').image.name
		# write to file
		msbfile.write(pack("2B", 0, 2))
		msbfile.write(material.texMain.get())
		msbfile.write(material.texSecondary.get())
		msbfile.write(pack("4B", material.diffCol[0], material.diffCol[1], material.diffCol[2], material.diffCol[3]))
		msbfile.write(pack("4B", material.emitCol[0], material.emitCol[1], material.emitCol[2], material.emitCol[3]))
		msbfile.write(pack("4B", material.specCol[0], material.specCol[1], material.specCol[2], material.specCol[3]))
		msbfile.write(pack("6f", bbox_per_model[i][0], bbox_per_model[i][1], bbox_per_model[i][2], bbox_per_model[i][3], bbox_per_model[i][4], bbox_per_model[i][5]))
		msbfile.write(pack("2f", 1.0, 0.0))
	#write footer
	
	msbfile.write(pack("6f", bbox_total[0],bbox_total[1],bbox_total[2],bbox_total[3],bbox_total[4],bbox_total[5]))
	msbfile.close()
	return 0


class ExportStaticMSB(bpy.types.Operator, ExportHelper):
	"""Object Cursor Array"""
	bl_idname = "export.msb_static"
	bl_label = "Export SpellForce static mesh (.msb)"
	bl_options = {'REGISTER'}
	
	filepath: StringProperty(
		name="Output mesh",
		subtype='FILE_PATH'
		)

	filename_ext = ".msb"

	filter_glob: StringProperty(
			default="*.msb",
			options={'HIDDEN'},
			)
	
	@classmethod
	def poll(cls, context):
		obj = context.object
		return obj and obj.type == 'MESH'

	def execute(self, context):
		if SaveMSBStatic(context, self.filepath) == 0:
			return {'FINISHED'}
		return {'CANCELLED'}



def menu_func(self, context):
	self.layout.operator(ExportStaticMSB.bl_idname, text="Export SpellForce static mesh (.msb)")


def register():
	bpy.utils.register_class(ExportStaticMSB)
	bpy.types.TOPBAR_MT_file_export.append(menu_func)

def unregister():
	bpy.utils.unregister_class(ExportStaticMSB)
	bpy.types.TOPBAR_MT_file_export.remove(menu_func)


if __name__ == "__main__":
	register()