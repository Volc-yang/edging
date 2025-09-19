#ifndef ShaderTypes_h
#define ShaderTypes_h

#include <simd/simd.h>

// A simple vertex structure for our 2D grid cells.
// It contains just the position and color for each vertex.
typedef struct
{
    // Position in normalized device coordinates (-1 to 1 on X and Y)
    vector_float2 position;

    // Color of the vertex
    vector_float4 color;

} GridVertex;

#endif /* ShaderTypes_h */