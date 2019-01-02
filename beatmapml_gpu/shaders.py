DISK_VERTEX_SHADER = """#version 400
// Current time
uniform float tick;
// Approach rate in ms
uniform float lookahead;

// Coordinate of center in osu!pixel
in vec2 position;
// Time when the disk is activated
in float activationTime;

// The progress of the disk
out float progress;

void main() {
    gl_Position = vec4(position, 0.0f, 1.0f);
    progress = (tick - activationTime + lookahead) / lookahead;
}
"""

DISK_GEOMETRY_SHADER = """#version 400
// Radius of note in osu!pixel
uniform float radius;
// osu! coordinate to canvas transformation
uniform mat4 osuToCanvas;
// Projection matrix
uniform mat4 projection;

layout (points) in;
layout (triangle_strip, max_vertices = 4) out;

in float progress[];

out float progressF;
out vec2 texCoord;

void main() {
    progressF = progress[0];
    vec4 position = gl_in[0].gl_Position;

    gl_Position = projection * osuToCanvas *
                  (position + vec4(-radius, -radius, 0.0f, 0.0f));
    texCoord = vec2(-1.0f, -1.0f);
    EmitVertex();
    gl_Position = projection * osuToCanvas *
                  (position + vec4(radius, -radius, 0.0f, 0.0f));
    texCoord = vec2(1.0f, -1.0f);
    EmitVertex();
    gl_Position = projection * osuToCanvas *
                  (position + vec4(-radius, radius, 0.0f, 0.0f));
    texCoord = vec2(-1.0f, 1.0f);
    EmitVertex();
    gl_Position = projection * osuToCanvas *
                  (position + vec4(radius, radius, 0.0f, 0.0f));
    texCoord = vec2(1.0f, 1.0f);
    EmitVertex();
    EndPrimitive();
}
"""

DISK_FRAGMENT_SHADER = """#version 400
// Progress of the note
in float progressF;
// Texture coordinate of the pixel
in vec2 texCoord;

// Shaded pixel color
layout (location = 0) out vec2 color;

void main() {
    float pct = step(dot(texCoord, texCoord), 1.0f);
    color = vec2(pct * progressF, pct);
}
"""


AVG_VERTEX_SHADER = """#version 400
// Position of the vertex
in vec2 position;
// Texture coordinate of the vertex
out vec2 texCoord;

void main() {
    // Passthrough
    gl_Position = vec4(position, 0.0f, 1.0f);
    texCoord = (position + vec2(1.0f, 1.0f)) / 2.0f;
}
"""


AVG_FRAGMENT_SHADER = """#version 400
// Texture coordinate of the pixel
in vec2 texCoord;
// Average progress of the pixel
out float color;

uniform sampler2D avgSampler;

void main() {
    vec4 sum = texture2D(avgSampler, texCoord);
    if (sum.y > 0.0f) {
        color = sum.x / sum.y;
    }
    else {
        color = 0.0f;
    }
}
"""
