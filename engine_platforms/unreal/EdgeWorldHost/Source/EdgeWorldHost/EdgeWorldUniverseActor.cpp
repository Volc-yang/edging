#include "EdgeWorldUniverseActor.h"
#include "Engine/StaticMesh.h"
#include "Engine/StaticMeshActor.h"
#include "Components/StaticMeshComponent.h"
#include "Materials/MaterialInterface.h"
#include "Dom/JsonObject.h"
#include "Serialization/JsonSerializer.h"
AEdgeWorldUniverseActor::AEdgeWorldUniverseActor(){PrimaryActorTick.bCanEverTick=false;}
bool AEdgeWorldUniverseActor::ApplyVerified(const FEdgeWorldUniverseObservation& O,FString& Error)
{
 Error.Reset();UWorld* W=GetWorld();if(!W||O.ArtifactClass!=TEXT("genesis-runtime")||O.AssetDependencyStatus!=TEXT("runtime-resolved")||O.Bodies.Num()!=2){Error=TEXT("unverified runtime projection");return false;}
 // Assets have already passed installed graph equality; do not load unlisted resources.
 TMap<FString,UStaticMesh*> Meshes;UMaterialInterface* Material=nullptr;
 for(const auto& A:O.Assets)
 {
  if(A.Uri==TEXT("/Engine/BasicShapes/Sphere.Sphere")||A.Uri==TEXT("/Engine/BasicShapes/Cube.Cube")||A.Uri==TEXT("/Engine/BasicShapes/Cylinder.Cylinder"))
  {if(UStaticMesh* M=LoadObject<UStaticMesh>(nullptr,*A.Uri))Meshes.Add(A.AssetId,M);else{Error=TEXT("declared mesh unavailable");return false;}}
  if(A.Uri==TEXT("/Engine/BasicShapes/BasicShapeMaterial.BasicShapeMaterial"))Material=LoadObject<UMaterialInterface>(nullptr,*A.Uri);
 }
 UStaticMesh* Sphere=nullptr;UStaticMesh* Cube=nullptr;
 for(const auto& A:O.Assets){if(A.Uri==TEXT("/Engine/BasicShapes/Sphere.Sphere"))Sphere=Meshes.FindRef(A.AssetId);if(A.Uri==TEXT("/Engine/BasicShapes/Cube.Cube"))Cube=Meshes.FindRef(A.AssetId);}
 if(!Sphere||!Cube||!Material){Error=TEXT("required declared proxy assets missing");return false;}
 for(const auto& D:O.Decorations)if(!Meshes.Contains(D.AssetId)){Error=TEXT("decoration requires undeclared mesh");return false;}
 // Frozen physical dimensions are decoded from the validated config, never inferred from mass.
 FVector DynamicScale(.2),SupportScale(4,4,.2);bool bConfig=false;
 for(const auto& R:O.SelectedRecords)if(R.Kind==TEXT("physics_config"))
 {
  TSharedPtr<FJsonObject> Record;if(!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(R.CanonicalJson),Record)||!Record)return false;
  auto Entities=Record->GetObjectField(TEXT("body"))->GetObjectField(TEXT("config"))->GetArrayField(TEXT("entities"));
  auto F=[](const TSharedPtr<FJsonValue>& X){FString Bits=X->AsObject()->GetStringField(TEXT("$f64"));uint64 U=0;for(TCHAR C:Bits)U=(U<<4)|(C<='9'?C-'0':C-'a'+10);double D;FMemory::Memcpy(&D,&U,8);return D;};
  DynamicScale=FVector(F(Entities[0]->AsObject()->TryGetField(TEXT("radius_m"))))*2.;auto Size=Entities[1]->AsObject()->GetArrayField(TEXT("size_m"));SupportScale=FVector(F(Size[0]),F(Size[1]),F(Size[2]));bConfig=true;
 }
 if(!bConfig){Error=TEXT("validated config unavailable");return false;}
 TArray<TObjectPtr<AActor>> New;
 auto Spawn=[&](UStaticMesh* Mesh,const FVector& P,const FQuat& Q,const FVector& Scale)
 {
  auto* A=W->SpawnActor<AStaticMeshActor>(P,Q.Rotator());if(!A)return false;auto* C=A->GetStaticMeshComponent();C->SetMobility(EComponentMobility::Movable);C->SetStaticMesh(Mesh);C->SetMaterial(0,Material);C->SetCollisionEnabled(ECollisionEnabled::NoCollision);C->SetGenerateOverlapEvents(false);C->SetSimulatePhysics(false);A->SetActorScale3D(Scale);New.Add(A);return true;
 };
 bool OK=Spawn(Sphere,Position(O,O.Bodies[0].PositionM),Quaternion(O.Bodies[0].QuaternionWXYZ),DynamicScale*(O.Scale/100.))&&Spawn(Cube,Position(O,O.Bodies[1].PositionM),Quaternion(O.Bodies[1].QuaternionWXYZ),SupportScale*(O.Scale/100.));
 for(const auto& D:O.Decorations)OK=OK&&Spawn(Meshes[D.AssetId],FVector(D.PositionCm[0],D.PositionCm[1],D.PositionCm[2]),FQuat::Identity,FVector(D.ScaleMilli[0],D.ScaleMilli[1],D.ScaleMilli[2])/1000.);
 if(!OK){for(AActor* A:New)if(A)A->Destroy();Error=TEXT("proxy allocation failed");return false;}
 for(AActor* A:Proxies)if(IsValid(A))A->Destroy();Proxies=MoveTemp(New);
 // Abstract development is displayed separately by the HUD.
 return true;
}
