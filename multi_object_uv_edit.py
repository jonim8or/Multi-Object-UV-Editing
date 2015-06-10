# ##### BEGIN GPL LICENSE BLOCK #####

#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

bl_info = {
    "name": "Multi Object UV Editing",
    "author": "Andreas Esau",
    "version": (0,9,2),
    "blender": (2, 7, 4),
    "location": "Object Tools",
    "description": "This Addon enables a quick way to create one UV Layout for multiple objects.",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "UV"}

import bpy
from bpy.props import IntProperty, FloatProperty

def get_selected_mesh_objects(context):
    return [obj for obj in context.selected_objects if obj.type=='MESH']

def deselect_all(context):
    for obj in context.selected_objects:
        obj.select = False
        
        
class MultiObjectUVEdit(bpy.types.Operator):
    """This operator gives you the ability to edit the uv of multiple objects at once."""
    bl_idname = "object.multi_object_uv_edit"
    bl_label = "Multi object UV edit"
    
    multi_object = None
    initial_objects = []
    initial_objects_hide_render = []
    active_object = None

    def leave_editing_mode(self,context):
        deselect_all(context)
        
        mesh_select_mode = list(context.tool_settings.mesh_select_mode)
        context.tool_settings.mesh_select_mode = (True,False,False)
        
        ### copy uvs based on the vertex groups to its final object
        for v_group in self.multi_object.vertex_groups:            
            ### select object vertex group and separate mesh into its own object
            num_verts = self.select_vertex_group(self.multi_object,v_group.name)
            if num_verts > 0:
                bpy.ops.mesh.separate(type="SELECTED")
                tmp_obj = context.selected_objects[0] #we had nothing selected before, so this should be the separated object
                tmp_obj.name = v_group.name+"_tmp"                
                
                ### go into object mode select newely created object and transfer the uv's to its final object
                bpy.ops.object.mode_set(mode='OBJECT')
                
                deselect_all(context)
                
                #find original object and unhide it, otherwise we can't use an operator on it
                original_obj = bpy.data.objects[v_group.name]
                original_obj.select = True
                original_obj.hide = False
                tmp_obj.select = True   
                context.scene.objects.active = tmp_obj
                for tmp_tex in tmp_obj.data.uv_textures:
                    if tmp_tex.name not in original_obj.data.uv_textures:
                        new_uv_layer = original_obj.data.uv_textures.new(tmp_tex.name)
                        original_obj.data.uv_textures.active = new_uv_layer
                    else:
                        original_obj.data.uv_textures.active = original_obj.data.uv_textures[tmp_tex.name]
                    tmp_obj.data.uv_textures.active = tmp_tex
                    bpy.ops.object.join_uvs()                    
                    
                ### delete the tmp object and return to editing our multi_object
                original_obj.select = False
                tmp_obj.select = False
                context.scene.objects.active = self.multi_object
                bpy.context.scene.objects.unlink(tmp_obj)
                bpy.data.objects.remove(tmp_obj)
                bpy.ops.object.mode_set(mode='EDIT')        
        
        ### restore everything
        context.tool_settings.mesh_select_mode = mesh_select_mode
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.scene.objects.unlink(self.multi_object)
        bpy.data.objects.remove(self.multi_object)
        for i, obj in enumerate(self.initial_objects):
            obj.select = True
            obj.hide_render = self.initial_objects_hide_render[i]
            
        context.scene.objects.active = self.active_object   
    
    
    def select_vertex_group(self,ob,group_name):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='DESELECT')
        bpy.ops.object.mode_set(mode='OBJECT')
        
        num_selected_verts = 0
        for i,vert in enumerate(ob.data.vertices):
            try:
                ob.vertex_groups[group_name].weight(i)
                vert.select = True
                num_selected_verts += 1
            except:
                pass
        bpy.ops.object.mode_set(mode='EDIT')
        return num_selected_verts
        
    def merge_selected_objects(self,context):        
        dupli_objects = []
        
        ### deselect objects
        for ob in self.initial_objects:
            ob.select = False

        for ob in self.initial_objects:
            #no need to use modifier for copying,
            #also no need to duplicate the meshes. We will duplicate only for the object we'll be joining into,
            #and that we do later on.
            dupli_ob = ob.copy()
            context.scene.objects.link(dupli_ob)
            dupli_objects.append(dupli_ob)
            for group in dupli_ob.vertex_groups:
                dupli_ob.vertex_groups.remove(group)
            v_group = dupli_ob.vertex_groups.new(name=ob.name)
            v_group.add(range(len(dupli_ob.data.vertices)),1,"REPLACE")
        
        #select all the new objects, and make the first one active, so we can do a join
        for ob in dupli_objects:
            ob.select = True
        self.multi_object = context.scene.objects.active = dupli_objects[0]     
        #copy the mesh, because we will join into that mesh 
        self.multi_object.data = self.multi_object.data.copy()
        bpy.ops.object.join()
        self.multi_object.name = "Multi_UV_Object"
    
    def modal(self, context, event):        
        if event.type in ['TAB'] or context.active_object.mode == "OBJECT":
            self.report({'INFO'}, "Multi Object UV Editing done.")
            self.leave_editing_mode(context)
            return {'CANCELLED'}
        return {'PASS_THROUGH'}

    def invoke(self, context, event):
        ### reset variables
        self.multi_object = None        
        context.window_manager.modal_handler_add(self)
       
        ### store active and selected objects
        self.initial_objects = get_selected_mesh_objects(context)
        self.initial_objects_hide_render = [obj.hide_render for obj in self.initial_objects]
        self.active_object = context.scene.objects.active
        
        ### make merged copy of all selected objects, that we can edit
        self.merge_selected_objects(context)
        self.multi_object.hide_render = False
        self.multi_object.hide = False
        
        #hide the initial objects
        for obj in self.initial_objects:
            obj.hide = True
            obj.hide_render = True
        
        #switch to edit mode
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action='SELECT')
       
        return {'RUNNING_MODAL'}

def add_button_to_panel_if_allowed(self,context):
    if len(context.selected_objects) > 1 and len(get_selected_mesh_objects(context)) > 1:
        # we only handle selected mesh-objects, but other objects can be selected as well
        self.layout.operator_context = "INVOKE_DEFAULT"
        self.layout.separator()
        self.layout.label("UV Tools:")
        self.layout.operator("object.multi_object_uv_edit",text="Multi Object UV Editing",icon="IMAGE_RGB")
  

def register():
    bpy.types.VIEW3D_PT_tools_object.append(add_button_to_panel_if_allowed)
    bpy.utils.register_class(MultiObjectUVEdit)


def unregister():
    bpy.types.VIEW3D_PT_tools_object.remove(add_button_to_panel_if_allowed)
    bpy.utils.unregister_class(MultiObjectUVEdit)


if __name__ == "__main__":
    register()
