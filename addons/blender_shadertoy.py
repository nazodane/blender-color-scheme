# ##### BEGIN GPL LICENSE BLOCK #####
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENCE BLOCK #####
#
# Shadertoy Viewer Addon for Blender
#
# Copyright (C) 2022 Toshimitsu Kimura <lovesyao@gmail.com>

import bpy
import gpu
from gpu_extras.batch import batch_for_shader

bl_info = {
    "name": "Shadertoy Viewer",
    "author": "Toshimitsu Kimura",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "Template > Shadertoy",
    "description": "Shadertoy Viewer addon for Blender",
    "warning": "",
    "support": "COMMUNITY",
    "doc_url": "",
    "tracker_url": "",
    "category": "System"
}

# Shadertoy workspace:
# hide headers in viewport
# hide tools in viewport
# hide overlays in viewport
# hide gizmos in viewport
# hide object type visibilities in viewport

from gpu.types import (
    GPUBatch,
    GPUIndexBuf,
    GPUVertBuf,
)

from bpy.props import (
    StringProperty,
#    IntProperty,
)

from urllib import request
import ssl
import json
# https://www.shadertoy.com/howto

import time
from math import modf

shader = None

def shadertoy_draw():
    if True:
        sc = bpy.context.screen
        scene = bpy.context.scene
#        print(sc.name)
        if not sc.name.startswith('Shadertoy'):
            return
#        if not "shader" in scene or not scene["shader"]:
#            return
#        shader = scene["shader"]

        if not "code" in scene:
            return
        code = scene["code"]

        shader = gpu.types.GPUShader("""
in vec2 pos;
void main()
{
   gl_Position = vec4(pos, 0.0, 1.0);
}
""", """
out vec4 FragColor; // todo: compatible name

uniform vec3 iResolution;
uniform float iTime;
//uniform float iTimeDelta;
uniform int iFrame;
//uniform float iChannelTime[4];
//uniform vec3 iChannelResolution[4];
//uniform vec4 iMouse;
//uniform samplerXX iChannel0..3;
//uniform vec4 iDate;
//uniform float iSampleRate;
""" + code + """
void main(){
    mainImage(FragColor, gl_FragCoord.xy);
}
""")

        rg = [[region for region in area.regions if region.type == "WINDOW"][0] \
            for area in sc.areas if area.type == "VIEW_3D"][0]

#        print(rg)

        vertices = (
            (-1.0, -1.0), (1.0, -1.0),
            (-1.0,  1.0), (1.0,  1.0))

        indices = (
            (0, 1, 2), (2, 1, 3))

        shader.bind()
        shader.uniform_float("iResolution", (rg.width, rg.height, 1.0)) # TODO: pixel aspect ratio
        shader.uniform_float("iTime", scene.frame_float/scene.render.fps)
#        shader.uniform_int("iFrame", int(modf(scene.frame_float)[1]))

        batch = batch_for_shader(shader, 'TRIS', {"pos":vertices}, indices=indices)

        # 描画
        batch.draw(shader)



def shadertoy_inputmenu(self, context):
    layout = self.layout
    scene = context.scene
    layout.label(text="Shadertoy ID:")
    layout.prop(scene, "shadertoy_id", text="")
#    layout.prop(scene, "shadertoy_id", text="Shadertoy ID")

import re

def shadertoy_shader_update(self, context):
    scene = self
    shadertoy_id = scene.shadertoy_id
    if shadertoy_id == "":
        return
    shadertoy_id = re.sub("^.*shadertoy\\.com\\/[a-zA-Z0-9]+\\/([a-zA-Z0-9]+)", "\\1", shadertoy_id)

    req = request.Request('https://www.shadertoy.com/shadertoy')
    req.add_header('Referer', 'https://www.shadertoy.com/view/' + shadertoy_id)
    req.add_header('User-Agent', 'Mozilla/5.0')
    data = 's={ "shaders" : ["'+ shadertoy_id +'"] }&nt=1&nl=1&np=1'
    res = request.urlopen(req, data=data.encode(), context = ssl._create_unverified_context())\
                .read().decode('utf-8')
    db = json.loads(res)
    code = (((db[0]["renderpass"][0]["code"] if "code" in db[0]["renderpass"][0] else "") \
                                          if len(db[0]["renderpass"]) else "") \
                                          if "renderpass" in db[0] else "") \
                                          if len(db) else ""
    if code == "":
        print("ERROR: shadertoy_id: %s"%shadertoy_id)
        return

    txt = bpy.data.texts.new(shadertoy_id)
    txt.write(code)
    context.space_data.text = txt

    scene["code"] = code
#    code = """
#void mainImage(out vec4 fragColor, in vec2 fragCoord) {
#  fragColor = vec4(1.0, 0.0, 0.0, 1.0);
#}
#"""
    # https://www.shadertoy.com/view/XsjGDt -> ok
    # https://www.shadertoy.com/view/3sySRK -> ok
    # https://www.shadertoy.com/view/MdX3zr -> ok


#import addon_utils
from pathlib import Path

def init_props():
    scene = bpy.types.Scene
    scene.shadertoy_id = StringProperty(name="Shadertoy ID", 
                                          default="",
                                          update=shadertoy_shader_update)
    bpy.types.TEXT_HT_header.append(shadertoy_inputmenu)
    bpy.types.SpaceView3D.draw_handler_add(shadertoy_draw, (), 'WINDOW', 'POST_PIXEL')
    if not Path(bpy.utils.script_path_user() + "/startup/bl_app_templates_user/Shadertoy/startup.blend").exists():
        #self.report({"WARNING"}, 
        print("The Shadertoy Viewer addon will not work correctly: the application template is not installed. You should ensure to install the template to {BLENDER_USER_SCRIPTS}/startup/bl_app_templates_user directory.")
        # TODO: error reporting in GUI

#    if not "Shadertoy" in bpy.data.workspaces:
#        for mod in addon_utils.modules():
#            if mod.bl_info['name'] == "Shadertoy Viewer":
#                filepath = mod.__file__.replace(".py", ".blend")
#                bpy.ops.wm.append(filename="Shadertoy", directory=filepath+"/WorkSpace/")                
                

def clear_props():
    scene = bpy.types.Scene
    bpy.types.TEXT_HT_header.remove(shadertoy_inputmenu)
    del scene.shadertoy_id
    try:
        bpy.types.SpaceView3D.draw_handler_remove(shadertoy_draw, 'WINDOW')
    except: pass

classes = [
]

def register():
    for c in classes:
        bpy.utils.register_class(c)
    init_props()

def unregister():
    clear_props()
    for c in classes:
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()