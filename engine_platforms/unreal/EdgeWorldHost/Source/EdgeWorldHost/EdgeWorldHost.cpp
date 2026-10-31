#include "EdgeWorldHost.h"

// The host intentionally contains no world authority. Runtime behavior belongs
// to the edgeWorld worker; this project only proves the plugin can be hosted.
IMPLEMENT_PRIMARY_GAME_MODULE(FDefaultGameModuleImpl, EdgeWorldHost, "EdgeWorldHost");
