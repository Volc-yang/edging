#ifndef ShaderTypes_h
#define ShaderTypes_h

#include <simd/simd.h>

// Vertex structure for our 3D terrain mesh
typedef struct
{
    vector_float3 position;
    vector_float3 normal;
    vector_float4 color;
} Vertex;

// Data structure for a single God's projection
typedef struct
{
    vector_float2 position; // Position on the XZ plane
    vector_float4 color;
} GodProjection;

// Uniforms structure passed to the shaders
typedef struct
{
    matrix_float4x4 projectionMatrix;
    matrix_float4x4 viewMatrix;
    matrix_float4x4 modelMatrix;
    vector_float3 lightDirection;
    int godCount;
    float time;
} Uniforms;

// Buffer index definitions
#define VertexBufferIndexVertices 0
#define VertexBufferIndexUniforms 1
#define VertexBufferIndexGods     2

#endif /* ShaderTypes_h */
