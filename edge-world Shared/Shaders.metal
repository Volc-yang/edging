#include <metal_stdlib>
#include "ShaderTypes.h"

using namespace metal;

typedef struct {
    float4 position [[position]];
    float4 color;
    float3 world_position;
    float3 world_normal;
} ColorInOut;

vertex ColorInOut vertexShader(const device Vertex *vertex_array [[buffer(VertexBufferIndexVertices)]],
                                const device Uniforms &uniforms [[buffer(VertexBufferIndexUniforms)]],
                                uint vertex_id [[vertex_id]])
{
    ColorInOut out;
    float4 in_position = float4(vertex_array[vertex_id].position, 1.0);
    
    // For simplicity, we assume modelMatrix is identity for terrain and handle it on CPU for gods.
    // Here we just use the view and projection matrices.
    out.world_position = in_position.xyz;
    out.world_normal = vertex_array[vertex_id].normal;
    
    out.position = uniforms.projectionMatrix * uniforms.viewMatrix * in_position;
    out.color = vertex_array[vertex_id].color;
    return out;
}

fragment float4 fragmentShader(ColorInOut in [[stage_in]],
                                const device Uniforms &uniforms [[buffer(VertexBufferIndexUniforms)]],
                                const device GodProjection *gods [[buffer(VertexBufferIndexGods)]])
{
    // 1. Calculate base lit terrain color
    float3 normal = normalize(in.world_normal);
    float diffuse_factor = saturate(dot(normal, uniforms.lightDirection));
    float4 base_color = in.color * diffuse_factor + in.color * 0.15; // Ambient light

    // 2. Calculate God Projection influence
    float4 god_influence_color = float4(0.0);
    float total_influence = 0.0;
    float god_radius = 4.0;

    for (int i = 0; i < uniforms.godCount; ++i) {
        float2 god_pos = gods[i].position;
        float2 pixel_pos = in.world_position.xz;

        float dist = distance(god_pos, pixel_pos);
        
        // Calculate influence with a smooth falloff
        float influence = 1.0 - saturate(dist / god_radius);
        influence = smoothstep(0.0, 1.0, influence);
        influence *= influence; // Square for a brighter core

        if (influence > 0.01) {
            god_influence_color += gods[i].color * influence;
            total_influence += influence;
        }
    }

    // 3. Blend the colors
    float4 final_color = base_color;
    if (total_influence > 0.0) {
        // Normalize the summed god colors before blending
        god_influence_color /= total_influence;
        // Blend based on the strength of the strongest influence
        final_color = mix(base_color, god_influence_color, saturate(total_influence * 0.7));
    }

    return float4(final_color.rgb, 1.0);
}
