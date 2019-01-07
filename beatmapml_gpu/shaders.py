DISK_VERTEX_SHADER = """#version 440
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

DISK_GEOMETRY_SHADER = """#version 440
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

vec4 toScreen(const in vec2 source) {
    return projection * osuToCanvas * vec4(source, 0.0f, 1.0f);
}

void main() {
    progressF = progress[0];
    vec2 position = gl_in[0].gl_Position.xy;

    gl_Position = toScreen(position + vec2(-radius, -radius));
    texCoord = vec2(-1.0f, -1.0f);
    EmitVertex();
    gl_Position = toScreen(position + vec2(radius, -radius));
    texCoord = vec2(1.0f, -1.0f);
    EmitVertex();
    gl_Position = toScreen(position + vec2(-radius, radius));
    texCoord = vec2(-1.0f, 1.0f);
    EmitVertex();
    gl_Position = toScreen(position + vec2(radius, radius));
    texCoord = vec2(1.0f, 1.0f);
    EmitVertex();
    EndPrimitive();
}
"""

DISK_FRAGMENT_SHADER = """#version 440
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

SLIDER_VERTEX_SHADER = """#version 440
// Coordinate of center in osu!pixel
in vec2 position;
// Cumulative position of the note
in float cumLength;

out float cumLengthG;

void main() {
    gl_Position = vec4(position, 0.0f, 1.0f);
    cumLengthG = cumLength;
}
"""

SLIDER_GEOMETRY_SHADER = """#version 440
const float PI_R = 0.31830988618379067153776752674503f;

// Radius of note in osu!pixel
uniform float radius;
// osu! coordinate to canvas transformation
uniform mat4 osuToCanvas;
// Projection matrix
uniform mat4 projection;
// Precomputed rotation matrices
uniform mat2 rotate[48];

layout (lines_adjacency) in;
layout (triangle_strip, max_vertices = 194) out;

in float cumLengthG[];
smooth out float cumLengthF;

vec4 toScreen(const in vec2 source) {
    return projection * osuToCanvas * vec4(source, 0.0f, 1.0f);
}

float cross2d(const in vec2 a, const in vec2 b) {
    return a.x * b.y - a.y * b.x;
}

void emitJoint(const in vec2 endpoint, const in vec2 start, const in vec2 end,
               const in float cumLength) {
    // Start edge
    cumLengthF = cumLength;
    gl_Position = toScreen(endpoint + radius * start);
    EmitVertex();

    float angle = acos(dot(start, end));
    int pieces = int(radius * angle * PI_R);

    for(int i = 0; i < pieces - 2; i++) {
        // Return to endpoint
        cumLengthF = cumLength;
        gl_Position = toScreen(endpoint);
        EmitVertex();
        // Go out
        cumLengthF = cumLength;
        gl_Position = toScreen(endpoint + radius * rotate[i] * start);
        EmitVertex();
    }

    //End edge
    cumLengthF = cumLength;
    gl_Position = toScreen(endpoint);
    EmitVertex();
    cumLengthF = cumLength;
    gl_Position = toScreen(endpoint + radius * end);
    EmitVertex();
    EndPrimitive();
}

bool isColocate(const in vec2 d) {
    return dot(d, d) < 1e-6f;
}

void calcJoint(const in vec2 leg1, const in vec2 leg2,
               const in vec2 leg1N, const in vec2 leg2N,
               out vec2 leftWing, out vec2 rightWing,
               out vec2 fanStart, out vec2 fanEnd) {
    vec2 miter = normalize(leg1N + leg2N);
    float miterScale = radius / dot(miter, leg1N);
    if(cross2d(leg1, leg2) > 0) {
        // Slider bend to left
        leftWing = miterScale * miter;
        rightWing = -radius * leg2N;
        fanStart = -miter;
        fanEnd = leg2N;
    }
    else {
        leftWing = radius * leg2N;
        rightWing = -miterScale * miter;
        fanStart = leg2N;
        fanEnd = miter;
    }
}

void main() {
    vec2 d[3], n[3];
    vec2 left[2], right[2];
    vec2 fanStart, fanEnd;
    for(int i = 0; i < 3; i++) {
        d[i] = gl_in[i + 1].gl_Position.xy - gl_in[i].gl_Position.xy;
        // Possible divide-by-zero but I don't care since
        // the result is never used.
        n[i] = normalize(vec2(-d[i].y, d[i].x));
    }
    if(isColocate(d[0])) {
        left[0] = radius * n[1];
        right[0] = -radius * n[1];
        fanStart = n[1];
        fanEnd = -n[1];
    }
    else {
        calcJoint(d[0], d[1], n[0], n[1],
                  left[0], right[0], fanStart, fanEnd);
    }
    emitJoint(gl_in[1].gl_Position.xy, fanStart, fanEnd, cumLengthG[1]);
    if(isColocate(d[2])) {
        left[1] = radius * n[1];
        right[1] = -radius * n[1];
        fanStart = -n[1];
        fanEnd = n[1];
    }
    else {
        calcJoint(-d[2], -d[1], -n[2], -n[1],
                  right[1], left[1], fanStart, fanEnd);
    }
    emitJoint(gl_in[2].gl_Position.xy, fanStart, fanEnd, cumLengthG[2]);

    cumLengthF = cumLengthG[1];
    gl_Position = toScreen(gl_in[1].gl_Position.xy + right[0]);
    EmitVertex();
    cumLengthF = cumLengthG[2];
    gl_Position = toScreen(gl_in[2].gl_Position.xy + right[1]);
    EmitVertex();
    cumLengthF = cumLengthG[1];
    gl_Position = toScreen(gl_in[1].gl_Position.xy);
    EmitVertex();
    cumLengthF = cumLengthG[2];
    gl_Position = toScreen(gl_in[2].gl_Position.xy);
    EmitVertex();
    cumLengthF = cumLengthG[1];
    gl_Position = toScreen(gl_in[1].gl_Position.xy + left[0]);
    EmitVertex();
    cumLengthF = cumLengthG[2];
    gl_Position = toScreen(gl_in[2].gl_Position.xy + left[1]);
    EmitVertex();
    EndPrimitive();
}
"""

SLIDER_FRAGMENT_SHADER = """#version 440
// Current time
uniform float tick;
// Start tick of the slider
uniform float activationTime;
// Time of the slider
uniform float totalTime;
// Number of repetitions
uniform int repeat;
// Approach rate in ms
uniform float lookahead;

smooth in float cumLengthF;
// Shaded pixel color
layout (location = 0) out vec2 color;

void main() {
    float passTime = totalTime / float(repeat);
    float oddIndicator = mod(float(repeat), 2.0f);
    float endDelta = passTime * oddIndicator +
                      (1 - 2 * oddIndicator) * cumLengthF;
    float appearance = totalTime - endDelta;
    float delta = 2 * (passTime - endDelta);
    color = vec2(0.0f, 0.0f);
    for(int i = repeat; activationTime + appearance >= tick && i > 0; i--) {
        color += vec2((tick - activationTime + lookahead) /
                      (appearance + lookahead), 1.0f);
        appearance -= delta;
        delta = 2 * passTime - delta;
    }
}
"""

AVG_VERTEX_SHADER = """#version 440
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


AVG_FRAGMENT_SHADER = """#version 440
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
