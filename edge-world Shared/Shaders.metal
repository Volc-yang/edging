#include <metal_stdlib>
#include "ShaderTypes.h"

using namespace metal;

// A struct to pass data from the vertex shader to the fragment shader.
typedef struct
{
    float4 position [[position]];
    float4 color;
} ColorInOut;

// Vertex shader for our 2D grid.
// It takes a GridVertex and passes its position and color to the fragment shader.
vertex ColorInOut gridVertexShader(const device GridVertex *vertices [[buffer(0)]],
                                  uint vertexID [[vertex_id]])
{
    ColorInOut out;
    out.position = float4(vertices[vertexID].position, 0.0, 1.0);
    out.color = vertices[vertexID].color;
    return out;
}

// Fragment shader for our 2D grid.
// It simply returns the color passed from the vertex shader.
fragment float4 gridFragmentShader(ColorInOut in [[stage_in]])
{
    return in.color;
}