#include "EdgeWorldUniverseHud.h"
#include "EdgeWorldUniverseGameMode.h"
#include "Engine/Engine.h"
#include "Engine/Canvas.h"
void AEdgeWorldUniverseHud::Present(const FEdgeWorldUniverseSession& S)
{
 Watermarks=FString::Printf(TEXT("HEAD (%lld,%lld) | viewing (%lld,%lld) %s"),(long long)S.HeadTick,(long long)S.HeadRevision,(long long)S.Observation.Tick,(long long)S.Observation.Revision,S.bHistory?TEXT("history/read only"):TEXT("current"));
 Controls=FString::Printf(TEXT("case %s | %s | %s"),*S.SelectedCase,S.bBusy?TEXT("busy"):S.bUnknown?TEXT("unknown: UniverseRefresh then UniverseRetry"):S.CanWrite()?TEXT("ready"):TEXT("read only/rejected"),*S.Head.StorageState);
 Controls+=FString::Printf(TEXT(" | derived technical proxies %d (separate from D)"),S.DerivedInstances);
 Value=S.Observation.DevelopmentMm.IsSet()?FString::Printf(TEXT("Abstract development: %lld mm (magnified proxy)"),(long long)S.Observation.DevelopmentMm.GetValue()):TEXT("Abstract development: initial");
}
void AEdgeWorldUniverseHud::DrawHUD()
{
 Super::DrawHUD();if(!Canvas)return;DrawRect(FLinearColor(0,0,.03,.85),16,16,FMath::Min(920.f,Canvas->SizeX-32.f),150);auto* F=GEngine?GEngine->GetSmallFont():nullptr;
 DrawText(TEXT("EDGEWORLD / Universe technical proxy"),FLinearColor::White,28,25,F);DrawText(Watermarks,FLinearColor::White,28,48,F);DrawText(Controls,FLinearColor::Yellow,28,70,F);DrawText(Value,FLinearColor::White,28,92,F);DrawText(TEXT("1 weak / 2 strong | Space physical | R retain | [ prior | H latest | WASD/QE camera, arrows look"),FLinearColor::Gray,28,118,F);
}
